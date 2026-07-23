#!/usr/bin/env python3
"""Validate simulator CSV/JSONL output and cross-format consistency."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys


REQUIRED_SCENARIOS = {
    "availability_classes",
    "collateral_owner_concentration",
    "independent_offline",
    "largest_asn_failure",
    "largest_provider_failure",
    "largest_region_failure",
    "provider_outage",
    "asn_outage",
    "multiple_provider_failure",
    "mixed_version",
    "operator_concentration",
    "flapping",
    "delayed_dkg_messages",
    "partial_network_partition",
    "restart_storm",
    "selection_summary",
}

REQUIRED_PROFILES = {"q25_22_17", "q60_44_41"}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: verify-results.py RESULT_DIRECTORY")

    result_dir = Path(sys.argv[1])
    csv_path = result_dir / "results.csv"
    jsonl_path = result_dir / "results.jsonl"
    overlap_csv_path = result_dir / "overlap.csv"
    overlap_jsonl_path = result_dir / "overlap.jsonl"
    if not all(
        path.is_file()
        for path in (csv_path, jsonl_path, overlap_csv_path, overlap_jsonl_path)
    ):
        fail(f"missing result or overlap CSV/JSONL below {result_dir}")

    csv_count = 0
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for _ in csv.DictReader(handle):
            csv_count += 1

    if csv_count == 0:
        fail("result set is empty")

    scenarios: set[str] = set()
    profiles: set[str] = set()
    json_count = 0
    with jsonl_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                fail(f"invalid JSONL at line {line_number}: {error}")
            json_count += 1
            scenarios.add(row["scenario"])
            profiles.add(row["profile"])
            selected = int(row["selected"])
            valid = int(row["valid"])
            adversarial = int(row["adversarial"])
            if selected < 0 or valid < 0 or adversarial < 0:
                fail(f"negative count at JSONL row {line_number}")
            if row["scenario"] != "selection_summary":
                if valid > selected:
                    fail(f"valid > selected at JSONL row {line_number}")
                if adversarial > selected:
                    fail(f"adversarial > selected at JSONL row {line_number}")

    if csv_count != json_count:
        fail(f"CSV/JSONL row count differs: {csv_count} != {json_count}")
    if not REQUIRED_SCENARIOS <= scenarios:
        fail(f"missing scenarios: {sorted(REQUIRED_SCENARIOS - scenarios)}")
    if profiles != REQUIRED_PROFILES:
        fail(f"unexpected profile set: {sorted(profiles)}")

    overlap_csv_count = 0
    with overlap_csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            overlap_csv_count += 1
            if int(row["observed_consecutive_overlap"]) > int(
                60 if row["profile"] == "q60_44_41" else 25
            ):
                fail(f"invalid observed overlap at overlap CSV row {overlap_csv_count}")

    overlap_json_count = 0
    with overlap_jsonl_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                json.loads(line)
            except json.JSONDecodeError as error:
                fail(f"invalid overlap JSONL at line {line_number}: {error}")
            overlap_json_count += 1
    if overlap_csv_count != overlap_json_count:
        fail(
            "overlap CSV/JSONL row count differs: "
            f"{overlap_csv_count} != {overlap_json_count}"
        )
    print(
        f"Verified {json_count} rows; "
        f"{overlap_json_count} overlap rows; {len(scenarios)} scenarios; "
        f"profiles={','.join(sorted(profiles))}"
    )


if __name__ == "__main__":
    main()
