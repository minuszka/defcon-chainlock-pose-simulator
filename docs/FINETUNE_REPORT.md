# Fine-Tuning Report — Live-Calibrated Extensions

Date: 2026-08-10
Adds three analyses on top of the Q60 finality-hardening framework, calibrated
on live DeFCoN network data captured through the deftrack explorer.

These are self-contained Python analyses (no Core build required) that reuse the
existing exact-math primitives. They do **not** modify consensus, chain
parameters, or the ChainLock production path. Like the base framework, passing
them is **not** a mainnet approval.

## What was added

1. **Finality-conflict (dual-ChainLock) model** — `analysis/finality_conflict.py`
2. **Live-calibrated liveness** — `analysis/operational_model.py` (#2)
3. **DKG cost + PoSe-exposure model** — same module (#3)
4. **Live calibration inputs** — `configs/deftrack-calibration.json`

## Calibration source (live data)

Captured 2026-08-10 from the deftrack MongoDB over a 14-day window
(`masternodeevents` = full registered set; `networknoiseobservations` = ~15
monitored nodes).

| Observation | Value | Meaning |
|---|---|---|
| Distinct MNs touching PoSe (14d) | 164 of 212 | 77% of the network churned through PoSe |
| Ban-ward transitions (14d) | 301 | e.g. `POSE_PENALTY->POSE_BANNED` = 124 |
| Revives `POSE_BANNED->ENABLED` (14d) | 76 | the manual ProUpServTx treadmill |
| `pose_instability` active hours | 45 of 336 (13.4%) | failures are **not** steady-state |
| Daily ban spikes | 1–2 typical, up to **246** (08-09) | failures **cascade**, not independent |

**Key modelling consequence:** the base sim's independent-offline assumption
understates reality. Failures are bursty and correlated, so liveness is scored
under a two-regime (quiet / cascade) model blended by the observed 13.4%
cascade-hour fraction. `member_online_rate_cascade = 0.60` is a modeled anchor
(labeled DERIVED/ASSUMED in the config), not a direct measurement.

## Result 1 — dual-ChainLock feasibility (the actual mainnet bug)

A single active quorum of `n` members can be split by a partition into two
disjoint signing sets. Both can reach the threshold `t` only if `2t <= n`.

```
2*threshold > effective_size  =>  dual ChainLock is MATHEMATICALLY IMPOSSIBLE
```

| Profile | eff. size | threshold | 2t vs n | dual-sign |
|---|---:|---:|---|---|
| mainnet 400/4/3 | min(400,N)=N | 3 | 6 ≤ N | **POSSIBLE** |
| q25 22/17 | 25 | 17 | 34 > 25 | impossible |
| q60 44/41 | 60 | 41 | 82 > 60 | impossible |

Exact trinomial probability of a dual sign under a 50/50 partition:

| Profile | P(dual sign), quiet (0.92) | P(dual sign), cascade (0.60) |
|---|---:|---:|
| mainnet 400/4/3 | **1.000** | **1.000** |
| q25 22/17 | 0 | 0 |
| q60 44/41 | 0 | 0 |

**Interpretation.** Under the current `threshold=3`, a network partition
produces a dual ChainLock with near-certainty — exactly the 2026-07 fork wave.
Both resize candidates make it *impossible by construction* because their
threshold exceeds half the quorum size. This is the single cleanest argument for
the resize: it does not merely make the dual lock *unlikely*, it makes it
*mathematically impossible*.

## Result 2 — calibrated liveness (blended quiet+cascade)

| Pop | Profile | P(DKG forms) | P(can sign) | notes |
|---:|---|---:|---:|---|
| 150 | mainnet 400/4/3 | 1.000 | 1.000 | trivially met — but see exposure |
| 150 | q25 22/17 | 0.749 | 0.903 | fragile DKG formation under cascade |
| 150 | q60 44/41 | **0.869** | 0.882 | bigger quorum absorbs correlated loss better |

Under the calibrated (harsher) load, **q60 forms the DKG more reliably than
q25** (0.869 vs 0.749). The blended availability is not near-perfect for either
resize candidate, because deep cascades (online≈0.60) genuinely pause finality —
but a **pause is a safe liveness event**, whereas the mainnet profile's
"perfect" liveness is the very mechanism that bans the whole network.

## Result 3 — DKG cost and PoSe exposure

| Profile | DKG msgs ~size² (× q25) | PoSe exposure/round @N=150 | @N=76 |
|---|---:|---:|---:|
| mainnet 400/4/3 | 266× | **1.000** | 1.000 |
| q25 22/17 | 1.0× | 0.167 | 0.329 |
| q60 44/41 | 5.9× | 0.400 | 0.789 |

`pose_exposure = effective_size / population` = the fraction of the enabled set
pulled into **every** DKG. The mainnet profile's exposure is **1.0** (every MN
in every round) — this is the direct driver of the 77%-of-network PoSe churn we
measured. q60 drops healthy-regime exposure to 0.40 at a 5.9× message-cost
premium over q25 (acceptable on the fleet's VPSs).

## Why q60 over q25 (now explicit and calibrated)

| Criterion | q25 | q60 | winner |
|---|---|---|---|
| Dual-ChainLock safety | impossible | impossible | tie |
| Adversarial capture (33–40%) | 0.97–17 forgeries/yr | ~0 | **q60** |
| DKG liveness under cascade | 0.749 | 0.869 | **q60** |
| DKG message cost | 1.0× | 5.9× | q25 |
| PoSe exposure | lower | higher | q25 |

q25 is cheaper and lower-exposure, but **fails on adversarial safety** and is
**more fragile** under correlated load. q60 wins the two criteria that matter
most (adversarial safety + cascade liveness) at an acceptable cost premium.

## Result 4 — dead-MN reward window (release item #3)

A stopped masternode keeps earning until it is PoSe-banned. Ground truth from
mainnet `quorum list` (2026-08-10): the ONLY quorum type that actually forms is
`llmq_400_60` (ChainLock) — `400_85` is empty (minSize 350), `60_75`/`100_67`
are not deployed. So the ChainLock quorum is the **sole PoSe tester**, which is
exactly why item #3 is coupled to the #2 resize. `reward_window.py` Monte-Carlos
the blocks-until-ban of a stopped MN (penalty +CalcPenalty(66) per selected-and-
failed DKG, −1/block decay, ban at max(100,N)).

Median reward window of a stopped MN:

| Profile | N=150 | N=300 | N=500 | N=1000 |
|---|---|---|---|---|
| current 400/4/3 | 9h | 6h | 6h | 12h |
| **q60 (bare resize)** | **54h** | 57h | 90h | **180h (7.5 days)** |
| q60 + hourly DKG (Layer 1) | 5h | 10h | 17h | 33h |
| q60 + liveness probe /2h (Layer 2) | **4h** | 4h | 4h | **4h** |

**Interpretation.** The bare Q60 resize (#2 alone) blows the dead-MN window up to
days, and it grows with network size (up to ~7.5 days at N=1000) — because the
ChainLock DKG now selects only 60/N members and the −1/block decay erases the
penalty between sparse selections. This is the #3 gap, quantified.

- **Layer 1 (hourly ChainLock DKG):** helps at small N but degrades with scale
  (33h at N=1000) — selection is still 60/N, so it does not solve large networks.
- **Layer 2 (quorum-attested liveness probe every 2h):** a flat ~4h at every N —
  coverage-independent, the actual fix at scale.

This validates the staged plan: ship the resize (#2) together with a #3 mitigation
(Layer 1 tuning is cheap and consensus-safe; the Layer 2 probe is the scale-proof
fix and warrants its own audit/regtest before bundling with a consensus change).

## Caveats

- `member_online_rate_cascade = 0.60` is a modeled anchor; liveness numbers are
  sensitive to it. Treat blended liveness as a band, not a point estimate.
- The dual-sign model covers the **single-active-quorum** split. A
  distinct-quorum cross-fork (two branches selecting different quorums) requires
  a partition to persist across a DKG interval; that path is bounded by the same
  per-side threshold requirement and is left for the regtest layer.
- These analyses are analytic + calibrated; they do not execute the real
  BLS/DKG state machine. Regtest remains the next gate.

## Reproduce

```bash
python3 analysis/finality_conflict.py --output-dir results/finality-conflict
python3 analysis/operational_model.py --output-dir results/operational
```
