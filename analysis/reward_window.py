#!/usr/bin/env python3
"""Dead-MN reward window: how long a STOPPED masternode keeps earning.

A masternode is dropped from the payment queue only when it becomes PoSe-banned
(IsMNValid == !IsBanned). PoSe penalty accrues only when the MN is SELECTED into
a quorum DKG and fails participation (offline). So the "reward window" of a
stopped MN = blocks until it has been selected-and-failed enough DKGs to reach
the ban score.

This quantifies release item #3 and its coupling to #2 (the Q60 resize):
  - size=400 ChainLock (minSize=4) selects EVERY MN every DKG -> stopped MNs ban
    fast (but so does everyone -> the mass-ban wave).
  - Q60 ChainLock selects only 60/N per DKG -> a stopped MN is tested far less
    often -> it KEEPS EARNING LONGER. That is exactly the gap #3 must close.

Model (per block, Monte Carlo over selection draws):
  penalty decays 1/block; on each quorum-type DKG boundary the stopped MN is
  selected w.p. min(size,N)/N and, if that quorum can form (>= minSize online
  members available), fails participation and takes CalcPenalty(66). Ban when
  penalty >= CalcMaxPoSePenalty = max(100, N).

Consensus values are taken from DeFCoN Core (llmq/params.h, chainparams.cpp):
block spacing 2.5 min; dkgInterval in blocks (24 blocks = 1 hour).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path

BLOCK_MINUTES = 2.5
MAX_BLOCKS = 30000  # ~52 days cap; windows beyond this are reported as capped


@dataclass(frozen=True)
class Quorum:
    name: str
    size: int
    min_size: int
    dkg_interval: int  # blocks


# GROUND TRUTH (mainnet `quorum list`, 2026-08-10): the ONLY quorum type that
# actually produces quorums is llmq_400_60 (ChainLock). llmq_400_85 is empty
# (cannot form: minSize=350 on a ~200-MN net); llmq_60_75 (DIP0024 InstantSend)
# and llmq_100_67 (Platform) are not deployed/active and run no DKGs. So the
# ChainLock quorum is the SOLE PoSe tester -> it alone decides how fast a stopped
# MN is banned. This is exactly why the #2 resize couples to #3.
CHAINLOCK_CURRENT = Quorum("llmq_400_60_CL", 400, 4, 72)   # current, every 3h
CHAINLOCK_Q60 = Quorum("q60_44_41_CL", 60, 44, 72)         # #2 resize, same cadence
CHAINLOCK_Q60_HOURLY = Quorum("q60_hourly_CL", 60, 44, 24)  # #3 Layer-1: hourly DKG


def calc_max_penalty(n: int) -> int:
    return max(100, n)


def calc_penalty_66(n: int) -> int:
    return (calc_max_penalty(n) * 66) // 100


def simulate_window(quorum: Quorum, n: int, online: float, trials: int, seed: int,
                    probe_period: int = 0) -> list[int]:
    """probe_period > 0 adds a #3 Layer-2 liveness probe that DETERMINISTICALLY
    tests every MN once every `probe_period` blocks (quorum-attested reachability
    check), independent of ChainLock DKG selection."""
    rng = random.Random(seed)
    max_pen = calc_max_penalty(n)
    pen_per_fail = calc_penalty_66(n)
    selected = min(quorum.size, n)
    forms = selected * online >= quorum.min_size
    p_select = selected / n
    windows = []
    for _ in range(trials):
        penalty = 0
        banned_at = MAX_BLOCKS
        for block in range(1, MAX_BLOCKS + 1):
            if penalty > 0:
                penalty -= 1  # decay, non-banned only (DecreaseScores)
            failed = False
            # ChainLock DKG selection (random, without-replacement approximated)
            if block % quorum.dkg_interval == 0 and forms and rng.random() < p_select:
                failed = True
            # Layer-2 liveness probe: deterministic full coverage every probe_period
            if probe_period and block % probe_period == 0:
                failed = True
            if failed:
                penalty += pen_per_fail
                if penalty >= max_pen:
                    banned_at = block
                    break
        windows.append(banned_at)
    return windows


def blocks_to_hours(b: float) -> float:
    return b * BLOCK_MINUTES / 60.0


def summarize(windows: list[int]) -> dict:
    med = statistics.median(windows)
    p90 = sorted(windows)[min(len(windows) - 1, int(0.9 * len(windows)))]
    capped = sum(1 for w in windows if w >= MAX_BLOCKS)
    return {
        "median_blocks": med,
        "median_hours": round(blocks_to_hours(med), 1),
        "p90_blocks": p90,
        "p90_hours": round(blocks_to_hours(p90), 1),
        "capped_fraction": round(capped / len(windows), 3),
    }


def profiles():
    # (quorum, probe_period_blocks). probe_period=0 means no Layer-2 probe.
    return {
        "current_400_4_3": (CHAINLOCK_CURRENT, 0),
        "q60_44_41": (CHAINLOCK_Q60, 0),
        "q60_L1_hourly_dkg": (CHAINLOCK_Q60_HOURLY, 0),
        "q60_L2_probe_2h": (CHAINLOCK_Q60, 48),
    }


def main() -> None:
    here = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=here / "results" / "reward-window")
    parser.add_argument("--trials", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=12648430)
    parser.add_argument("--online", type=float, default=0.92)
    args = parser.parse_args()

    populations = [150, 300, 500, 1000]
    rows = []
    for profile_name, (quorum, probe_period) in profiles().items():
        for n in populations:
            windows = simulate_window(quorum, n, args.online, args.trials,
                                      args.seed + n, probe_period=probe_period)
            s = summarize(windows)
            rows.append({
                "profile": profile_name,
                "population": n,
                "online_rate": args.online,
                "trials": args.trials,
                **s,
            })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "reward-window.csv").open("w", newline="", encoding="utf-8") as h:
        writer = csv.DictWriter(h, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "reward-window.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(rows)} reward-window rows to {args.output_dir}")
    print()
    print("Median reward window of a STOPPED MN (blocks / hours), by profile & N:")
    print(f"{'profile':>26} {'N=150':>12} {'N=300':>12} {'N=500':>12} {'N=1000':>12}")
    by_profile: dict[str, dict[int, dict]] = {}
    for r in rows:
        by_profile.setdefault(r["profile"], {})[r["population"]] = r
    for profile_name, per_n in by_profile.items():
        cells = []
        for n in populations:
            r = per_n[n]
            if r["capped_fraction"] >= 0.5:
                cells.append(f">{int(blocks_to_hours(MAX_BLOCKS)/24)}d".rjust(12))
            else:
                cells.append(f"{r['median_blocks']}b/{r['median_hours']}h".rjust(12))
        print(f"{profile_name:>26} " + " ".join(cells))


if __name__ == "__main__":
    main()
