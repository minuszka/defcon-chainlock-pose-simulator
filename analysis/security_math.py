#!/usr/bin/env python3
"""Exact hypergeometric security calculations and Monte Carlo comparison."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Iterable

getcontext().prec = 80


@dataclass(frozen=True)
class Profile:
    name: str
    size: int
    min_size: int
    threshold: int


def controlled_count(population: int, share_percent: Decimal) -> int:
    """Map a percentage to an integer population using documented half-up rounding."""
    return int(
        (Decimal(population) * share_percent / Decimal(100)).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )


def hypergeom_tail_fraction(
    population: int, controlled: int, draws: int, threshold: int
) -> Fraction:
    """Return the exact P[X >= threshold] for sampling without replacement."""
    if not 0 <= controlled <= population:
        raise ValueError("controlled population is outside [0, population]")
    if not 0 <= draws <= population:
        raise ValueError("draw count is outside [0, population]")
    if threshold <= 0:
        return Fraction(1, 1)
    upper = min(draws, controlled)
    if threshold > upper:
        return Fraction(0, 1)

    lower = max(threshold, draws - (population - controlled))
    numerator = sum(
        math.comb(controlled, selected)
        * math.comb(population - controlled, draws - selected)
        for selected in range(lower, upper + 1)
    )
    return Fraction(numerator, math.comb(population, draws))


def fraction_decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """95% Wilson score interval for a binomial Monte Carlo observation."""
    if trials <= 0:
        raise ValueError("trials must be positive")
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    centre = proportion + z * z / (2.0 * trials)
    margin = z * math.sqrt(
        proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)
    )
    return max(0.0, (centre - margin) / denominator), min(
        1.0, (centre + margin) / denominator
    )


def stable_seed(master_seed: int, *parts: object) -> int:
    payload = "|".join(str(part) for part in (master_seed, *parts)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def monte_carlo_capture(
    population: int,
    controlled: int,
    draws: int,
    threshold: int,
    rounds: int,
    seed: int,
) -> int:
    rng = random.Random(seed)
    population_range = range(population)
    breaches = 0
    for _ in range(rounds):
        selected_controlled = sum(
            member < controlled for member in rng.sample(population_range, draws)
        )
        breaches += selected_controlled >= threshold
    return breaches


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def calculate_rows(config: dict, run_monte_carlo: bool) -> Iterable[dict]:
    rounds = int(config["monte_carlo_rounds"])
    master_seed = int(config["master_seed"])
    rotations_per_year = int(config["rotations_per_year"])
    profiles = [Profile(**item) for item in config["profiles"]]

    for population in config["populations"]:
        for share_raw in config["controlled_shares_percent"]:
            share = Decimal(str(share_raw))
            controlled = controlled_count(population, share)
            actual_share = Decimal(controlled) * Decimal(100) / Decimal(population)
            for profile in profiles:
                exact = hypergeom_tail_fraction(
                    population, controlled, profile.size, profile.threshold
                )
                exact_decimal = fraction_decimal(exact)
                successes = (
                    monte_carlo_capture(
                        population,
                        controlled,
                        profile.size,
                        profile.threshold,
                        rounds,
                        stable_seed(
                            master_seed, population, share, profile.name, "direct-mc"
                        ),
                    )
                    if run_monte_carlo
                    else None
                )
                ci_low, ci_high = (
                    wilson_interval(successes, rounds)
                    if successes is not None
                    else (None, None)
                )
                yield {
                    "population": population,
                    "controlled_requested_percent": str(share),
                    "controlled_members": controlled,
                    "controlled_actual_percent": str(actual_share),
                    "profile": profile.name,
                    "quorum_size": profile.size,
                    "min_size": profile.min_size,
                    "threshold": profile.threshold,
                    "exact_probability": str(exact_decimal),
                    "exact_fraction_numerator": str(exact.numerator),
                    "exact_fraction_denominator": str(exact.denominator),
                    "expected_per_1000_rotations": str(
                        exact_decimal * Decimal(1000)
                    ),
                    "expected_per_year": str(
                        exact_decimal * Decimal(rotations_per_year)
                    ),
                    "rotations_per_year_assumption": rotations_per_year,
                    "mc_rounds": rounds if run_monte_carlo else 0,
                    "mc_breaches": successes,
                    "mc_probability": (
                        str(Decimal(successes) / Decimal(rounds))
                        if successes is not None
                        else None
                    ),
                    "mc_wilson_95_low": ci_low,
                    "mc_wilson_95_high": ci_high,
                    "estimate_kind": "exact_hypergeometric_and_direct_mc"
                    if run_monte_carlo
                    else "exact_hypergeometric",
                }


def write_outputs(rows: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "security-probabilities.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(rows, handle, indent=2)
        handle.write("\n")
    with (output_dir / "security-probabilities.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/security-analysis.json")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/security"))
    parser.add_argument(
        "--skip-monte-carlo",
        action="store_true",
        help="calculate exact probabilities without direct Monte Carlo",
    )
    args = parser.parse_args()
    rows = list(calculate_rows(load_config(args.config), not args.skip_monte_carlo))
    write_outputs(rows, args.output_dir)
    print(f"Wrote {len(rows)} exact security rows to {args.output_dir}")


if __name__ == "__main__":
    main()
