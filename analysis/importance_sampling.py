#!/usr/bin/env python3
"""Reproducible sequential importance sampling for rare quorum captures."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import json
import math
from pathlib import Path
import random

from security_math import (
    Profile,
    controlled_count,
    fraction_decimal,
    hypergeom_tail_fraction,
    load_config,
    stable_seed,
)


def proposal_odds_multiplier(
    population: int, controlled: int, draws: int, threshold: int
) -> float:
    base = controlled / population
    target = min(0.995, max(base, (threshold + 0.5) / draws))
    if base <= 0.0 or base >= 1.0:
        return 1.0
    return (target / (1.0 - target)) / (base / (1.0 - base))


def one_weighted_sample(
    rng: random.Random,
    population: int,
    controlled: int,
    draws: int,
    odds_multiplier: float,
) -> tuple[int, float]:
    remaining_population = population
    remaining_controlled = controlled
    selected_controlled = 0
    log_weight = 0.0

    for _ in range(draws):
        true_p = remaining_controlled / remaining_population
        if true_p <= 0.0:
            proposal_p = 0.0
        elif true_p >= 1.0:
            proposal_p = 1.0
        else:
            proposal_p = (
                odds_multiplier * true_p
                / (1.0 - true_p + odds_multiplier * true_p)
            )

        choose_controlled = rng.random() < proposal_p
        if choose_controlled:
            selected_controlled += 1
            remaining_controlled -= 1
            if proposal_p > 0.0:
                log_weight += math.log(true_p / proposal_p)
        else:
            if proposal_p < 1.0:
                log_weight += math.log((1.0 - true_p) / (1.0 - proposal_p))
        remaining_population -= 1

    return selected_controlled, math.exp(log_weight)


def estimate_capture(
    population: int,
    controlled: int,
    profile: Profile,
    samples: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    odds = proposal_odds_multiplier(
        population, controlled, profile.size, profile.threshold
    )
    weighted_events = []
    all_weights = []
    targeted_events = 0

    for _ in range(samples):
        selected, weight = one_weighted_sample(
            rng, population, controlled, profile.size, odds
        )
        event = selected >= profile.threshold
        targeted_events += event
        weighted_events.append(weight if event else 0.0)
        all_weights.append(weight)

    estimate = sum(weighted_events) / samples
    if samples > 1:
        variance = sum((value - estimate) ** 2 for value in weighted_events) / (
            samples - 1
        )
        standard_error = math.sqrt(variance / samples)
    else:
        standard_error = float("nan")
    z = 1.959963984540054
    ci_low = max(0.0, estimate - z * standard_error)
    ci_high = estimate + z * standard_error
    weight_sum = sum(all_weights)
    weight_square_sum = sum(weight * weight for weight in all_weights)
    effective_sample_size = (
        weight_sum * weight_sum / weight_square_sum
        if weight_square_sum > 0.0
        else 0.0
    )

    exact = fraction_decimal(
        hypergeom_tail_fraction(
            population, controlled, profile.size, profile.threshold
        )
    )
    return {
        "population": population,
        "controlled_members": controlled,
        "profile": profile.name,
        "samples": samples,
        "proposal_odds_multiplier": odds,
        "targeted_event_count": targeted_events,
        "importance_estimate": estimate,
        "importance_95_low": ci_low,
        "importance_95_high": ci_high,
        "effective_sample_size": effective_sample_size,
        "exact_probability": str(exact),
        "relative_error_vs_exact": (
            float((Decimal(str(estimate)) - exact) / exact)
            if exact != 0
            else None
        ),
        "estimate_kind": "modeled_importance_sampling",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/security-analysis.json")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/importance")
    )
    parser.add_argument("--samples", type=int)
    args = parser.parse_args()

    config = load_config(args.config)
    samples = args.samples or int(config["importance_samples"])
    profiles = [Profile(**item) for item in config["profiles"]]
    rows = []
    for population in config["populations"]:
        for share_raw in config["controlled_shares_percent"]:
            share = Decimal(str(share_raw))
            controlled = controlled_count(population, share)
            for profile in profiles:
                rows.append(
                    {
                        "controlled_requested_percent": str(share),
                        **estimate_capture(
                            population,
                            controlled,
                            profile,
                            samples,
                            stable_seed(
                                int(config["master_seed"]),
                                population,
                                share,
                                profile.name,
                                "importance",
                            ),
                        ),
                    }
                )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "importance-sampling.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(rows, handle, indent=2)
        handle.write("\n")
    with (args.output_dir / "importance-sampling.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} importance-sampling rows to {args.output_dir}")


if __name__ == "__main__":
    main()
