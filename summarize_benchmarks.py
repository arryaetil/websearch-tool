"""Median and range per case and approach over repeated benchmark runs in data/.

Example: python summarize_benchmarks.py --since 2026-09-29T12:00
Prints numbers only; no names, sources or report text.
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from benchmark_person_research import summarize

DATA = Path(__file__).parent / "data"


def spread(values: list[float]) -> str:
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return "n/a"
    return f"{statistics.median(values):.3g} ({min(values):.3g}–{max(values):.3g})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", required=True, help="UTC time, e.g. 2026-09-29T12:00")
    args = parser.parse_args()
    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    rows: dict[str, list[dict]] = {}
    for path in sorted(DATA.glob("comparison-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if datetime.fromisoformat(data["run_at"]) < since:
            continue
        for pair in data["results"]:
            rows.setdefault(pair["id"], []).append(summarize(pair))
    lines = ["| Case | Runs | Seconds: original / LangGraph | USD: original / LangGraph | Verdicts: original / LangGraph |",
             "| --- | ---: | --- | --- | --- |"]
    for case, runs in rows.items():
        verdicts = lambda i: ", ".join(sorted({str(r["verdict"][i]) for r in runs}))
        lines.append(
            f"| {case} | {len(runs)} | {spread([r['seconds'][0] for r in runs])} / {spread([r['seconds'][1] for r in runs])} | "
            f"{spread([r['estimated_usd'][0] for r in runs])} / {spread([r['estimated_usd'][1] for r in runs])} | "
            f"{verdicts(0)} / {verdicts(1)} |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
