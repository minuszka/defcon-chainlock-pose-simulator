#!/usr/bin/env python3
"""Calibrated liveness + DKG-cost + PoSe-exposure model.

Two fine-tunings over the baseline sim's independent-offline assumption:

(#2) LIVENESS is scored under a two-regime CORRELATED failure model calibrated
     from live deftrack data. The real network is not in independent steady
     state: PoSe/DKG failures cluster into cascades (only ~13% of hours carry
     pose activity, but those hours spike hard). We blend a "quiet" regime and
     a "cascade" regime by the observed cascade-hour fraction, so the liveness
     numbers stop being optimistic.

(#3) DKG COST is scored as O(size^2) message/verification complexity (each DKG
     member exchanges contributions & complaints with every other member), plus
     the per-round PoSe EXPOSURE = effective_size / population (the fraction of
     the enabled set pulled into every DKG). Exposure ~ 1.0 is precisely what
     drives the current PoSe-ban wave under the 400 profile.
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


PROFILES = [
    Profile("mainnet_400_4_3", 400, 4, 3),
    Profile("q25_22_17", 25, 22, 17),
    Profile("q60_44_41", 60, 44, 41),
]


def binom_tail_ge(n: int, p: float, t: int) -> float:
    """Exact P(Y >= t) for Y ~ Binomial(n, p), summed in log space."""
    if t <= 0:
        return 1.0
    if t > n:
        return 0.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    log_fact_n = math.lgamma(n + 1)
    log_p, log_q = math.log(p), math.log(1.0 - p)
    total = 0.0
    for k in range(t, n + 1):
        log_coeff = log_fact_n - math.lgamma(k + 1) - math.lgamma(n - k + 1)
        total += math.exp(log_coeff + k * log_p + (n - k) * log_q)
    return min(1.0, total)


def load_calibration(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def rows(calibration: dict):
    fm = calibration["fault_model"]
    cascade_frac = fm["cascade_hour_fraction"]
    q_quiet = fm["member_online_rate_quiet"]
    q_cascade = fm["member_online_rate_cascade"]

    populations = [
        ("healthy_floor", calibration["network"]["enabled_healthy_floor"]),
        ("observed_low", calibration["network"]["enabled_observed_low"]),
    ]
    base_cost = None  # q25 message cost used as the relative baseline
    cost_lookup = {p.name: p.size * (p.size - 1) for p in PROFILES}
    base_cost = cost_lookup["q25_22_17"]

    for pop_label, population in populations:
        for profile in PROFILES:
            n = min(profile.size, population)
            # ---- (#2) calibrated liveness ----
            form_quiet = binom_tail_ge(n, q_quiet, profile.min_size)
            form_cascade = binom_tail_ge(n, q_cascade, profile.min_size)
            sign_quiet = binom_tail_ge(n, q_quiet, profile.threshold)
            sign_cascade = binom_tail_ge(n, q_cascade, profile.threshold)
            form_blended = (1 - cascade_frac) * form_quiet + cascade_frac * form_cascade
            sign_blended = (1 - cascade_frac) * sign_quiet + cascade_frac * sign_cascade
            # ---- (#3) cost + exposure ----
            dkg_messages = profile.size * (profile.size - 1)
            exposure = n / population  # fraction of enabled set in every DKG
            yield {
                "population_label": pop_label,
                "population": population,
                "profile": profile.name,
                "size": profile.size,
                "effective_size": n,
                "min_size": profile.min_size,
                "threshold": profile.threshold,
                "dkg_form_quiet": f"{form_quiet:.5f}",
                "dkg_form_cascade": f"{form_cascade:.5f}",
                "dkg_form_blended": f"{form_blended:.5f}",
                "sign_quiet": f"{sign_quiet:.5f}",
                "sign_cascade": f"{sign_cascade:.5f}",
                "sign_blended": f"{sign_blended:.5f}",
                "dkg_messages_n2": dkg_messages,
                "dkg_cost_rel_q25": round(dkg_messages / base_cost, 2),
                "pose_exposure_per_round": round(exposure, 3),
            }


def main() -> None:
    here = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path,
                        default=here / "configs" / "deftrack-calibration.json")
    parser.add_argument("--output-dir", type=Path, default=here / "results" / "operational")
    args = parser.parse_args()

    calibration = load_calibration(args.calibration)
    data = list(rows(calibration))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "operational.csv").open("w", newline="", encoding="utf-8") as h:
        writer = csv.DictWriter(h, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    (args.output_dir / "operational.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(data)} operational rows to {args.output_dir}")
    print()
    print("Calibrated liveness (blended quiet+cascade) & cost/exposure:")
    print(f"{'pop':>5} {'profile':>16} {'form_blend':>10} {'sign_blend':>10}"
          f" {'cost_xq25':>9} {'pose_exp':>8}")
    for r in data:
        print(f"{r['population']:>5} {r['profile']:>16} {r['dkg_form_blended']:>10}"
              f" {r['sign_blended']:>10} {r['dkg_cost_rel_q25']:>9} {r['pose_exposure_per_round']:>8}")


if __name__ == "__main__":
    main()
