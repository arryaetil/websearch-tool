"""Paired, local person-research measurement. Input/output belong in ignored data/.

Example: python benchmark_person_research.py data/evaluation_cases.json
The case file contains {"cases": [{"id": "case-1", "name": "...", "city": "..."}]}.
No API key, case or provider response is committed by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from identity_workflow import run_identity_research
from researcher import SCHEMA, SYSTEM_PROMPT, build_prompt, clean_report, dedupe_sources, parse_response


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


def web_search_run(case: dict) -> dict:
    """Old person prompt with OpenAI's hosted search, not the old Perplexity provider."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    started = time.perf_counter()
    response = client.responses.create(
        model="gpt-5.1",
        instructions=SYSTEM_PROMPT,
        input=build_prompt(
            case["name"], case["city"], str(case.get("age", "")),
            case.get("employer", ""), case.get("context", "")),
        tools=[{"type": "web_search"}],
        tool_choice="required",
        text={"format": {"type": "json_schema", "name": "person_report", "schema": SCHEMA}},
    )
    elapsed = round(time.perf_counter() - started, 2)
    result = clean_report(parse_response(response.output_text or ""))
    result["sources"] = dedupe_sources(result.get("sources", []))
    usage = response.usage.model_dump(exclude_none=True) if response.usage else None
    trace = [item.model_dump(exclude_none=True) for item in response.output
             if getattr(item, "type", "") == "web_search_call"]
    estimate = None
    if usage:
        estimate = round(usage["input_tokens"] * 1.25 / 1_000_000
                         + usage["output_tokens"] * 10 / 1_000_000
                         + len(trace) * 0.01, 5)
    return {"model": "gpt-5.1", "seconds": elapsed, "usage": usage,
            "estimated_usd": estimate, "search_trace": trace, "report": result}


def new_run(case: dict) -> dict:
    result = run_identity_research(
        case["name"], case["city"], case.get("employer", ""), case.get("context", ""),
        birth_year=case.get("birth_year"), profession=case.get("profession", "unknown"),
        aliases=case.get("aliases", ""),
    )
    return {"seconds": result["metrics"]["total_seconds"], "usage": result["metrics"], "report": result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_file", type=Path, help="JSON in data/; use only approved cases")
    args = parser.parse_args()
    if not all(os.environ.get(k) for k in ("SERPER_API_KEY", "OPENAI_API_KEY")):
        parser.error("SERPER_API_KEY and OPENAI_API_KEY are required")
    case_file = args.case_file.resolve()
    data_dir = (ROOT / "data").resolve()
    if not case_file.is_relative_to(data_dir):
        parser.error("Place the case file in the Git-ignored data/ directory")
    cases = json.loads(case_file.read_text(encoding="utf-8"))["cases"]
    if not cases:
        parser.error("At least one approved case is required")
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for old in data_dir.glob("comparison-*.json"):
        if datetime.fromtimestamp(old.stat().st_mtime, timezone.utc) < cutoff:
            old.unlink()
    output = {"run_at": datetime.now(timezone.utc).isoformat(), "results": []}
    for case in cases:
        pair = {"id": case["id"], "input": case}
        for label, runner in (("openai_web_search", web_search_run), ("langgraph", new_run)):
            try:
                pair[label] = runner(case)
            except Exception as exc:
                pair[label] = {"error_type": type(exc).__name__}
        output["results"].append(pair)
    destination = data_dir / f"comparison-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Comparison saved locally: {destination}")
    for pair in output["results"]:
        print(f"{pair['id']}: OpenAI web search {pair['openai_web_search'].get('seconds', 'failed')} s; "
              f"LangGraph {pair['langgraph'].get('seconds', 'failed')} s")


if __name__ == "__main__":
    main()
