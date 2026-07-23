# Q60 Finality-Hardening Framework — Final Report

Date: 2026-07-23  
Candidate profile: Q60, size 60, minimum DKG participants 44, signing threshold 41  
Baseline profile: Q25, size 25, minimum DKG participants 22, signing threshold 17

## Decision

Q60 is ready to advance to implementation and execution of the planned
8–10-operator regtest suite. It is not yet ready for testnet shadow mode,
production deployment, or mainnet activation.

This decision means the analytical and test scaffolding is sufficiently mature
to start real protocol-state-machine validation. It is not a security approval.

## What was added

- Exact hypergeometric threshold-capture probabilities for seven populations,
  eight controlled shares, and both quorum profiles.
- Direct 10,000-round Monte Carlo estimates with Wilson 95% confidence bounds.
- A fixed-seed, biased-without-replacement importance sampler with likelihood
  correction, confidence bounds, and effective sample size.
- Core-native selection scenarios for provider, ASN, region, operator,
  collateral owner, software version, availability, flapping, delayed messages,
  restart storms, and partial partitions.
- Consecutive and four-quorum active-window overlap and concentration exports.
- Pure, test-only activation resolver and `FINALITY_CONFLICT` behavior models.
- A generated 20–40 node Docker Compose topology and opt-in `tc/netem` helper.
- An 8–10 operator regtest scenario manifest and concise result exporter.
- A non-consensus, explicitly telemetry-only shadow-mode design.

No mainnet parameter, production chain parameter, production ChainLock path, or
live node was modified.

## Mathematical method and assumptions

For population `N`, controlled members `K`, quorum size `n`, and threshold `t`,
the exact capture probability is:

```text
P(X >= t) =
  sum(x=t..min(K,n)) [C(K,x) C(N-K,n-x)] / C(N,n)
```

The implementation retains an exact rational result and emits a high-precision
decimal. Requested controlled shares are converted to an integer member count
with decimal half-up rounding; the actual modeled share is also exported.

Expected breaches per 1,000 rotations are `1000 * P`. The yearly estimate is
`8760 * P`, explicitly assuming one rotation per hour. This is a reporting
assumption, not a consensus or scheduling claim.

Direct Monte Carlo cannot establish that a rare probability is zero. In
particular, zero observed breaches in 10,000 rounds still produces a nonzero
Wilson upper confidence bound (approximately 0.000384).

Importance sampling biases sequential draws toward controlled members and
applies the exact likelihood ratio for each sampled path. Its rows are labeled
`modeled_importance_sampling`; they are estimates, not direct network events.
Low effective sample sizes in extreme cases are a warning to prefer the exact
hypergeometric result for capture probability.

## Selected exact results

The complete 112-row result is in `summaries/security-probabilities.csv`.

| Population | Controlled | Q25 probability | Q25 expected/year | Q60 probability | Q60 expected/year |
|---:|---:|---:|---:|---:|---:|
| 150 | 33.33% | 1.1048e-4 | 9.6782e-1 | 7.5457e-14 | 6.6100e-10 |
| 150 | 40% | 1.9631e-3 | 1.7196e1 | 7.1983e-9 | 6.3057e-5 |
| 1,500 | 33.33% | 3.7214e-4 | 3.2600 | 1.6451e-8 | 1.4411e-4 |
| 1,500 | 40% | 4.0479e-3 | 3.5460e1 | 5.6330e-6 | 4.9345e-2 |
| 15,000 | 33.33% | 4.1062e-4 | 3.5971 | 3.0437e-8 | 2.6663e-4 |
| 15,000 | 40% | 4.2981e-3 | 3.7652e1 | 8.1872e-6 | 7.1720e-2 |

These results show a large capture-probability reduction for Q60 relative to
Q25, but they do not model key compromise, adaptive corruption, real provider
data, protocol bugs, or correlated cryptographic failure.

## Native simulation result

The quick Core-native run used populations 150, 300, and 500, 100 rotations per
population/profile, and fixed seed 12648430.

- 30,606 scenario rows
- 600 overlap rows
- 17 scenario families
- 26,108 passing Boost assertions
- no threshold-capture assertion failure

Observed consecutive overlap tracked the theoretical `n²/N` expectation:

| Population | Profile | Expected | Observed |
|---:|---|---:|---:|
| 150 | Q25 | 4.1667 | 4.1100 |
| 150 | Q60 | 24.0000 | 23.8600 |
| 300 | Q25 | 2.0833 | 2.0300 |
| 300 | Q60 | 12.0000 | 12.1400 |
| 500 | Q25 | 1.2500 | 1.2000 |
| 500 | Q60 | 7.2000 | 6.9400 |

Q60 substantially improved DKG availability in many independent-loss cases.
For example, at 20% independent offline probability, quick-run DKG success was
92.67% for Q60 and 21.33% for Q25. Severe correlated failures still degraded
both profiles: a modeled 40% single-domain failure produced only 2.33% Q60 DKG
success and 11.67% signing availability.

The provider/ASN/region percentage stress rows use the same exact-size failed
domain construction so their numerical availability is intentionally equal.
Separate fixed metadata assignments (`provider_outage`, `asn_outage`, and
`region_outage`) exercise distinct correlated layouts.

## Test-only state models

The activation resolver scaffold passed 11 assertions covering legacy history,
the exact activation boundary, restart/reindex reconstruction, missing future
type, and invalid configuration.

The finality-conflict scaffold passed 1,024 assertions covering arrival-order
independence, duplicate and invalid messages, persistence/reload, restart and
reindex reconstruction, evidence retention, and disabled signing in conflict.

These are executable specifications, not integration with production
ChainLock persistence or P2P validation.

## What remains untested

- Real BLS key generation, DKG phases, recovered signatures, and CLSIG flow
  across multiple daemons.
- A production-backed height resolver and historical verification across an
  activation boundary.
- Production persistence and RPC/telemetry exposure of both conflict evidences.
- Actual restart, reindex, delayed P2P delivery, invalid-message flood, and
  mixed-version interoperability.
- Measured CPU, memory, bandwidth, and recovery-time impact of Q60.
- Docker/netem execution and operating-system portability.
- Real-world provider, ASN, operator, collateral-owner, and regional labels.
- Testnet shadow telemetry, retention policy, privacy review, and operational
  alerting.

## Advancement gates

Advance to regtest now, using the acceptance criteria in
`docs/ACCEPTANCE_CRITERIA.md`.

Do not advance to shadow mode until the real multi-daemon regtest suite passes,
activation-boundary history remains verifiable after restart/reindex, conflict
evidence persists deterministically, signing halts in `FINALITY_CONFLICT`, and
resource/regression measurements are reviewed.

Passing simulation, regtest, or shadow telemetry must never be interpreted as
automatic approval for mainnet activation. A separate consensus review,
threat-model review, staged deployment decision, and explicit activation
proposal would still be required.

## Reproduction

```bash
./scripts/install-into-core.sh /home/user/DEFCON
make -C /home/user/DEFCON/src -j2 test/test_defcon
./scripts/run-simulator.sh /home/user/DEFCON quick

python3 analysis/security_math.py --output-dir results/security-full
python3 analysis/importance_sampling.py --output-dir results/importance-full
python3 analysis/export_compact_summaries.py
```

On the development host, compilation took about 22 seconds incrementally, the
quick native matrix about 1 second, and the complete exact/Monte Carlo plus
importance analysis about 56 seconds. Raw result size and runtime scale with
round count; the previous 10,000-round native matrix produced roughly 907 MB of
CSV/JSONL raw data. Allow approximately 1 GB of disk and several GB of build
memory for a full Core build and full native matrix.
