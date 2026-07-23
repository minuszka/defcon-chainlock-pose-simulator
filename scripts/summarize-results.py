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

    overlap_path = Path(sys.argv[1]) / "overlap.csv"
    overlap_aggregates: dict[tuple[int, str], dict[str, float]] = defaultdict(
        lambda: {
            "count": 0,
            "expected": 0,
            "observed": 0,
            "repeated": 0,
            "provider": 0,
            "asn": 0,
            "operator": 0,
            "owner": 0,
            "outage_overlap": 0,
            "excessive": 0,
        }
    )
    with overlap_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (int(row["population"]), row["profile"])
            item = overlap_aggregates[key]
            item["count"] += 1
            item["expected"] += float(row["expected_consecutive_overlap"])
            item["observed"] += int(row["observed_consecutive_overlap"])
            item["repeated"] += int(row["repeated_members"])
            item["provider"] += int(row["max_provider_members"])
            item["asn"] += int(row["max_asn_members"])
            item["operator"] += int(row["max_operator_members"])
            item["owner"] += int(row["max_collateral_owner_members"])
            item["outage_overlap"] += int(row["top_provider_overlap"])
            quorum_size = 60 if row["profile"] == "q60_44_41" else 25
            item["excessive"] += (
                int(row["max_provider_members"]) * 100 >= quorum_size * 40
            )

    print(
        "\noverlap_summary: population,profile,expected_consecutive,"
        "observed_consecutive,active_repeats,max_provider,max_asn,max_operator,"
        "max_owner,top_provider_overlap,provider_ge_40pct"
    )
    for key in sorted(overlap_aggregates):
        population, profile = key
        item = overlap_aggregates[key]
        count = item["count"]
        means = [
            item[name] / count
            for name in (
                "expected",
                "observed",
                "repeated",
                "provider",
                "asn",
                "operator",
                "owner",
                "outage_overlap",
            )
        ]
        print(
            f"{population},{profile},"
            + ",".join(f"{value:.4f}" for value in means)
            + f",{pct(int(item['excessive']), int(count))}"
        )


if __name__ == "__main__":
    main()
