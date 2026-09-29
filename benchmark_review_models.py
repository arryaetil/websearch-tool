"""Replay the review agent on saved evidence with several models. Output stays in data/.

Example: python benchmark_review_models.py data/comparison-A.json data/comparison-B.json
Every model receives the identical evidence packet, so differences come from the model.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

import review_agent

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

# List prices per million tokens (input, output) from the OpenAI pricing page, 29 Sep 2026.
MODELS = {
    "gpt-5.1": (1.25, 10.0), "gpt-5.6-luna": (0.20, 1.20), "gpt-5.6-terra": (2.00, 12.0),
    "gpt-6-luna": (0.10, 0.50), "gpt-6-sol": (2.00, 10.0),
}


def state_from(report: dict) -> dict:
    subject = report.get("subject", {})
    return {**subject, "aliases": subject.get("aliases", []), "assessments": report.get("sources", []),
            "sanction_hits": report.get("sanction_hits", []), "register_hits": [],
            "search_trace": report.get("search_trace", [])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparisons", nargs="+", type=Path)
    args = parser.parse_args()
    data_dir = (ROOT / "data").resolve()
    rows = []
    for path in args.comparisons:
        if not path.resolve().is_relative_to(data_dir):
            parser.error("Comparison files must be in data/")
        for pair in json.loads(path.read_text(encoding="utf-8"))["results"]:
            report = (pair.get("langgraph") or {}).get("report")
            if not report:
                continue
            state = state_from(report)
            for model, (rate_in, rate_out) in MODELS.items():
                os.environ["REVIEW_MODEL"] = model
                started = time.perf_counter()
                review, usage = review_agent.run_review(state, lambda: OpenAI(api_key=os.environ["OPENAI_API_KEY"]))
                seconds = round(time.perf_counter() - started, 2)
                cost = (usage.get("review_input_tokens", 0) * rate_in + usage.get("review_output_tokens", 0) * rate_out) / 1e6
                sections = review.get("sections") or {}
                rows.append({
                    "case": pair["id"], "model": model, "seconds": seconds, "usd": round(cost, 5),
                    "score": review.get("score"), "verdict": review.get("label"), "status": review.get("status"),
                    "cited_summary": len(review.get("summary", [])), "reasons": len(review.get("reasons", [])),
                    "section_items": sum(len(v) for v in sections.values()),
                    "deeper_search": bool(review.get("deeper_search", {}).get("queries")),
                    "output_tokens": usage.get("review_output_tokens", 0),
                })
                print(f"{pair['id']} {model}: {seconds}s ${cost:.4f} score={review.get('score')} {review.get('label')}")
    stamp = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    (data_dir / f"review-models-{stamp}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    header = "| Case | Model | Seconds | USD | Score | Verdict | Cited summary | Reasons | Section items | Deeper search |"
    lines = [header, "|" + " --- |" * 10]
    lines += [f"| {r['case']} | {r['model']} | {r['seconds']} | {r['usd']} | {r['score']} | {r['verdict']} | "
              f"{r['cited_summary']} | {r['reasons']} | {r['section_items']} | {r['deeper_search']} |" for r in rows]
    (data_dir / f"review-models-{stamp}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved data/review-models-{stamp}.md")


if __name__ == "__main__":
    main()
