#!/usr/bin/env python3
"""Export review-sized result files while leaving raw output untracked."""

import argparse
import csv
import json
from pathlib import Path


def compact(source: Path, destination: Path, fields: list[str]) -> list[dict[str, str]]:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = [{field: row[field] for field in fields} for row in csv.DictReader(handle)]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    destination.with_suffix(".json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--security-dir", type=Path, default=Path("results/security-full"))
    parser.add_argument("--importance-dir", type=Path, default=Path("results/importance-full"))
    parser.add_argument("--output-dir", type=Path, default=Path("summaries"))
    args = parser.parse_args()

    security = compact(
        args.security_dir / "security-probabilities.csv",
        args.output_dir / "security-probabilities.csv",
        [
            "population",
            "controlled_requested_percent",
            "controlled_actual_percent",
            "profile",
            "threshold",
            "exact_probability",
            "expected_per_1000_rotations",
            "expected_per_year",
            "mc_rounds",
            "mc_breaches",
            "mc_wilson_95_low",
            "mc_wilson_95_high",
            "estimate_kind",
        ],
    )
    importance = compact(
        args.importance_dir / "importance-sampling.csv",
        args.output_dir / "importance-sampling.csv",
        [
            "population",
            "controlled_requested_percent",
            "profile",
            "samples",
            "proposal_odds_multiplier",
            "targeted_event_count",
            "importance_estimate",
            "importance_95_low",
            "importance_95_high",
            "effective_sample_size",
            "exact_probability",
            "relative_error_vs_exact",
            "estimate_kind",
        ],
    )
    print(f"Wrote {len(security)} exact and {len(importance)} importance rows")


if __name__ == "__main__":
    main()
