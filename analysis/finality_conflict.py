#!/usr/bin/env python3
"""Dual-ChainLock (finality-conflict) partition model, calibrated on live data.

This is the metric that matches DeFCoN's ACTUAL mainnet failure mode: not a
malicious threshold capture, but a benign network partition in which two
disjoint subsets of the active quorum each independently reach the signing
threshold and sign competing tips -> two valid CLSIGs at one height -> a
dual ChainLock (the 2026-07 fork wave).

Key property proven here
------------------------
A single active quorum has `n` members. Two DISJOINT signing sets each need
>= threshold `t` members. Disjoint subsets of an n-set satisfy |A|+|B| <= n, so
both can reach `t` only if 2*t <= n. Therefore:

    2*t > n   =>  a single-quorum dual ChainLock is MATHEMATICALLY IMPOSSIBLE.

    q25_22_17 : 2*17 = 34 > 25   -> impossible
    q60_44_41 : 2*41 = 82 > 60   -> impossible
    mainnet 400/4/3 (n_eff=min(400,N)) : 2*3 = 6 <= N -> POSSIBLE for any N>=6

For the profiles where it is possible, the exact trinomial probability of a
dual sign under a partition (split ratio r, per-member online rate q) is
computed and reported. For the safe profiles the impossibility bound is stated
and the probability is exactly 0.

The threshold>size/2 rule is exactly why the resize kills the dual-ChainLock
class of bug that the low threshold=3 permits today.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    name: str
    size: int
    min_size: int
    threshold: int


# The two resize candidates plus the CURRENT (broken) mainnet profile as the
# contrast baseline. The current profile is why this analysis exists.
PROFILES = [
    Profile("mainnet_400_4_3", 400, 4, 3),
    Profile("q25_22_17", 25, 22, 17),
    Profile("q60_44_41", 60, 44, 41),
]


def effective_size(size: int, population: int) -> int:
    """A quorum cannot be larger than the valid MN set it is drawn from."""
    return min(size, population)


def dual_sign_probability(n: int, t: int, split_ratio: float, online: float) -> float:
    """Exact P(both partition sides independently reach the threshold).

    Each of the n quorum members is independently:
      - on the larger side AND online    w.p. split_ratio * online
      - on the smaller side AND online    w.p. (1 - split_ratio) * online
      - unavailable (offline)             w.p. 1 - online
    Dual sign  <=>  (#larger-online >= t) AND (#smaller-online >= t).
    Trinomial tail, summed in log space for numerical safety.
    """
    if 2 * t > n:
        return 0.0  # impossible by the disjoint-subset bound
    p_a = split_ratio * online
    p_b = (1.0 - split_ratio) * online
    p_0 = 1.0 - online
    if p_a <= 0.0 or p_b <= 0.0:
        return 0.0
    log_fact_n = math.lgamma(n + 1)
    log_a, log_b = math.log(p_a), math.log(p_b)
    log_0 = math.log(p_0) if p_0 > 0.0 else None
    total = 0.0
    for a in range(t, n - t + 1):
        for b in range(t, n - a + 1):
            c = n - a - b
            if c > 0 and log_0 is None:
                continue  # online==1.0 and there is leftover mass: impossible cell
            log_coeff = (
                log_fact_n
                - math.lgamma(a + 1)
                - math.lgamma(b + 1)
                - math.lgamma(c + 1)
            )
            log_p = a * log_a + b * log_b + (c * log_0 if c > 0 else 0.0)
            total += math.exp(log_coeff + log_p)
    return min(1.0, total)


def load_calibration(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def rows(calibration: dict):
    fm = calibration["fault_model"]
    populations = [
        ("healthy_floor", calibration["network"]["enabled_healthy_floor"]),
        ("observed_low", calibration["network"]["enabled_observed_low"]),
    ]
    regimes = [
        ("quiet", fm["member_online_rate_quiet"]),
        ("cascade", fm["member_online_rate_cascade"]),
    ]
    for pop_label, population in populations:
        for profile in PROFILES:
            n = effective_size(profile.size, population)
            possible = 2 * profile.threshold <= n
            for split_ratio in fm["partition_split_ratios"]:
                for regime_label, online in regimes:
                    p = dual_sign_probability(n, profile.threshold, split_ratio, online)
                    yield {
                        "population_label": pop_label,
                        "population": population,
                        "profile": profile.name,
                        "size": profile.size,
                        "effective_size": n,
                        "min_size": profile.min_size,
                        "threshold": profile.threshold,
                        "two_t_le_n": 2 * profile.threshold <= n,
                        "dual_sign_possible": possible,
                        "partition_split_ratio": split_ratio,
                        "regime": regime_label,
                        "online_rate": online,
                        "p_dual_sign": f"{p:.6e}",
                        "method": "exact_trinomial_or_impossibility_bound",
                    }


def main() -> None:
    here = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path,
                        default=here / "configs" / "deftrack-calibration.json")
    parser.add_argument("--output-dir", type=Path, default=here / "results" / "finality-conflict")
    args = parser.parse_args()

    calibration = load_calibration(args.calibration)
    data = list(rows(calibration))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "finality-conflict.csv").open("w", newline="", encoding="utf-8") as h:
        writer = csv.DictWriter(h, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    (args.output_dir / "finality-conflict.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(data)} finality-conflict rows to {args.output_dir}")
    print()
    print("Dual-ChainLock feasibility by profile (2*threshold <= effective_size?):")
    seen = set()
    for r in data:
        key = (r["population_label"], r["profile"])
        if key in seen:
            continue
        seen.add(key)
        verdict = "POSSIBLE" if r["dual_sign_possible"] else "IMPOSSIBLE (2t>n)"
        print(f"  pop={r['population']:>4} {r['profile']:>16}  n_eff={r['effective_size']:>3}"
              f"  t={r['threshold']:>2}  -> {verdict}")
    print()
    print("Worst-case dual-sign probability (split=0.5), by profile & regime:")
    for r in data:
        if r["partition_split_ratio"] == 0.5:
            print(f"  pop={r['population']:>4} {r['profile']:>16} {r['regime']:>8}"
                  f"  online={r['online_rate']}  P(dual)={r['p_dual_sign']}")


if __name__ == "__main__":
    main()
