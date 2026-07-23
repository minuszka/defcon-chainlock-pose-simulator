#!/usr/bin/env python3
"""Validate simulator CSV/JSONL output and cross-format consistency."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys


REQUIRED_SCENARIOS = {
    "independent_offline",
    "provider_outage",
    "asn_outage",
    "mixed_version",
    "operator_concentration",
    "flapping",
    "delayed_dkg_messages",
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
    if not csv_path.is_file() or not jsonl_path.is_file():
        fail(f"missing results.csv or results.jsonl below {result_dir}")

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
    print(
        f"Verified {json_count} rows; "
        f"{len(scenarios)} scenarios; profiles={','.join(sorted(profiles))}"
    )


if __name__ == "__main__":
    main()
