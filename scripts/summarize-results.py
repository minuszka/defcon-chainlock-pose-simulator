#!/usr/bin/env python3
"""Stream a compact availability/safety summary from simulator CSV output."""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
import sys


def pct(value: int, count: int) -> str:
    return f"{100.0 * value / count:.4f}%"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: summarize-results.py RESULT_DIRECTORY")

    csv_path = Path(sys.argv[1]) / "results.csv"
    aggregates: dict[tuple[str, str, int], dict[str, int]] = defaultdict(
        lambda: {"count": 0, "dkg": 0, "sign": 0, "breach": 0, "valid": 0}
    )
    selection_rows: list[dict[str, str]] = []

    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["scenario"] == "selection_summary":
                selection_rows.append(row)
                continue
            key = (row["scenario"], row["profile"], int(row["parameter"]))
            item = aggregates[key]
            item["count"] += 1
            item["dkg"] += int(row["dkg_complete"])
            item["sign"] += int(row["signable"])
            item["breach"] += int(row["threshold_breach"])
            item["valid"] += int(row["valid"])

    print("scenario,profile,parameter,runs,dkg_success,signing_success,threshold_breach,mean_valid")
    for key in sorted(aggregates):
        scenario, profile, parameter = key
        item = aggregates[key]
        count = item["count"]
        print(
            f"{scenario},{profile},{parameter},{count},"
            f"{pct(item['dkg'], count)},{pct(item['sign'], count)},"
            f"{pct(item['breach'], count)},{item['valid'] / count:.3f}"
        )

    print("\nselection_summary: population,profile,chi_square_rounded,expected_per_mn,"
          "selection_spread,mean_overlap")
    for row in sorted(selection_rows, key=lambda r: (int(r["population"]), r["profile"])):
        print(
            f"{row['population']},{row['profile']},{row['parameter']},"
            f"{row['valid']},{row['adversarial']},{row['overlap']}"
        )


if __name__ == "__main__":
    main()
