# DeFCoN ChainLock and PoSe Simulator

A Core-native C++ scale simulator for evaluating DeFCoN ChainLock quorum
selection, DKG availability, operator concentration, correlated outages, and
PoSe-related failure scenarios.

The simulator calls DeFCoN Core's production
`CDeterministicMNList::CalculateQuorum()` implementation directly. It does not
reimplement the quorum selection algorithm.

## Current scope

The framework provides:

- synthetic but genuine `CDeterministicMNList` fixtures;
- Q25 (`25/22/17`) and candidate Q60 (`60/44/41`) profiles;
- populations from 150 to 15,000 masternodes;
- deterministic, reproducible simulation seeds;
- exact hypergeometric capture probabilities and direct Monte Carlo confidence bounds;
- reproducible, explicitly modeled importance sampling for rare events;
- independent offline rates from 5% to 30%;
- provider-, ASN-, region-, operator-, and collateral-owner-correlated models;
- flapping nodes;
- 10%, 20%, 33%, and 40% concentration cases;
- 10%, 25%, 40%, and 50% mixed-version populations;
- delayed DKG messages, restart storms, and partial partitions;
- consecutive and active-window quorum overlap and concentration measurements;
- DKG `minSize` and signing-threshold availability checks;
- test-only activation-resolver and finality-conflict specification models;
- 20–40 node Docker/netem topology generation and an 8–10 operator regtest plan;
- a non-consensus shadow-mode telemetry design;
- CSV and JSONL output;
- automatic result validation.

This version uses the real Core selection code. DKG network phases are currently
evaluated with deterministic fault models. Execution of the full BLS/DKG message
state machine and Docker/netem network emulation are planned as subsequent
layers.

## Safety boundary

The integration script changes only test-related files in a Core checkout:

- `src/test/llmq_scale_simulator_tests.cpp`;
- `src/test/chainlock_profile_resolver_tests.cpp`;
- `src/test/chainlock_finality_conflict_model_tests.cpp`;
- `src/Makefile.test.include`.

It does not modify consensus parameters, mainnet configuration, ChainLock
production logic, or live masternode-count rules.

## Requirements

- DeFCoN Core `v22.1.x` source tree;
- a Core build configured with unit tests enabled;
- the regular Core build dependencies;
- Bash;
- Python 3;
- a C++ toolchain supported by the target Core revision.

## Clone

```bash
git clone https://github.com/minuszka/defcon-chainlock-pose-simulator.git
cd defcon-chainlock-pose-simulator
```

## Install into a Core checkout

```bash
./scripts/install-into-core.sh /home/user/DEFCON
```

The installer is idempotent: running it again replaces the simulator source but
does not duplicate the build entry.

## Build

For an in-tree Autotools build:

```bash
cd /home/user/DEFCON
make -C src -j2 test/test_defcon
```

If the Core checkout was configured with tests disabled, reconfigure it with
tests enabled or use a separate test-enabled worktree/build directory.

## Run the quick matrix

```bash
cd /path/to/defcon-chainlock-pose-simulator
./scripts/run-simulator.sh /home/user/DEFCON quick
```

Quick defaults:

```text
populations: 150,300,500
rounds:      100
seed:        12648430
```

## Run the full matrix

```bash
./scripts/run-simulator.sh /home/user/DEFCON full
```

Full defaults:

```text
populations: 150,300,500,1500,5000,10000,15000
rounds:      10000
seed:        12648430
```

For an out-of-tree build, pass the build root containing the compiled
`test_defcon` binary:

```bash
./scripts/run-simulator.sh /home/user/DEFCON/build quick
```

## Custom runs

The simulator is configured through environment variables:

```bash
export DEFCON_SIM_POPULATIONS=150,1500,15000
export DEFCON_SIM_ROUNDS=1000
export DEFCON_SIM_SEED=42
export DEFCON_SIM_OUTPUT_DIR=/tmp/defcon-sim-results

/home/user/DEFCON/src/test/test_defcon \
  --run_test=llmq_scale_simulator_tests/core_native_selection_and_fault_matrix \
  --log_level=message \
  --report_level=short
```

Constraints:

- every population must be between 60 and 15,000;
- rounds must be between 1 and 1,000,000.

## Output

The wrapper writes:

```text
results/quick/results.csv
results/quick/results.jsonl
results/quick/overlap.csv
results/quick/overlap.jsonl
```

Each row contains:

- scenario;
- population;
- profile;
- round and scenario parameter;
- selected and valid member counts;
- DKG completion status;
- signing availability;
- adversarial member count;
- threshold-breach indicator;
- overlap with the previous quorum.

The final `selection_summary` rows also report the expected selection count,
selection spread, mean consecutive-quorum overlap, and a chi-square statistic.

After every wrapper run, `scripts/verify-results.py` verifies:

- CSV/JSONL row-count equality;
- JSON validity;
- required profiles and scenarios;
- non-negative counters;
- `valid <= selected`;
- `adversarial <= selected`.

Generate a compact aggregate report:

```bash
./scripts/summarize-results.py results/full
```

The generated result directory is intentionally excluded from Git.

## Exact probability and rare-event analysis

```bash
python3 analysis/security_math.py --output-dir results/security-full
python3 analysis/importance_sampling.py --output-dir results/importance-full
python3 analysis/export_compact_summaries.py
```

The exact analysis uses a hypergeometric tail because quorum selection is
without replacement. The configured year estimate assumes 8,760 rotations.
Monte Carlo results include a Wilson 95% interval, including when no breach was
observed. Importance-sampling output is labeled `modeled_importance_sampling`;
it is not presented as a direct observation.

The checked-in `summaries/` files omit enormous exact-fraction numerators and
denominators. Raw output remains under the ignored `results/` directory.

## Live-calibrated fine-tuning analyses

Three additional analyses, calibrated on live DeFCoN data captured through the
deftrack explorer (`configs/deftrack-calibration.json`). They are self-contained
Python (no Core build) and reuse the exact-math primitives:

```bash
python3 analysis/finality_conflict.py --output-dir results/finality-conflict
python3 analysis/operational_model.py  --output-dir results/operational
python3 analysis/reward_window.py      --output-dir results/reward-window
```

- `finality_conflict.py` — dual-ChainLock (finality-conflict) partition model.
  Proves `2*threshold > size` makes a single-quorum dual ChainLock impossible,
  and quantifies the probability for profiles where it is possible (the current
  `threshold=3` mainnet profile: ~1.0). This models DeFCoN's *actual* 2026-07
  failure mode, not just adversarial capture.
- `operational_model.py` — liveness under a two-regime correlated failure model
  calibrated from observed cascade behaviour (#2), plus `O(size²)` DKG cost and
  per-round PoSe exposure (`effective_size / population`) (#3).
- `reward_window.py` — dead-MN reward window: how long a STOPPED masternode keeps
  earning before PoSe-ban, using the ground-truth single-active-quorum (ChainLock)
  model. Shows the bare Q60 resize lets a stopped MN earn for days (growing with
  N), and that a liveness probe restores a flat ~4h window at any scale.

See [docs/FINETUNE_REPORT.md](docs/FINETUNE_REPORT.md) for method, results, and
the live-data provenance.

## Docker topology

Generate an opt-in 20–40 node Compose topology:

```bash
python3 docker/generate-compose.py --nodes 20 --output results/docker-compose.yml
```

See [docs/DOCKER_NETEM_PLAN.md](docs/DOCKER_NETEM_PLAN.md) before running any
network-emulation scenario. Generation alone does not start containers or
modify a live node.

## Determinism

All fixtures, modifiers, availability events, failure-domain assignments, and
fault schedules are derived from the configured master seed. Re-running the
same Core revision with the same configuration produces byte-identical CSV and
JSONL output.

The current quick validation produced:

```text
30,606 result rows
600 overlap rows
17 scenario families
2 quorum profiles
26,108 passing Boost assertions
```

## Remove the integration

```bash
./scripts/uninstall-from-core.sh /home/user/DEFCON
```

The uninstall script removes only the simulator source and its exact
`BITCOIN_TESTS` entry.

## Repository layout

```text
configs/
  quick.env
  full.env
core/src/test/
  llmq_scale_simulator_tests.cpp
  chainlock_profile_resolver_tests.cpp
  chainlock_finality_conflict_model_tests.cpp
analysis/
  security_math.py
  importance_sampling.py
  export_compact_summaries.py
docker/
  generate-compose.py
  netem.sh
regtest/
  scenarios.json
  export_summary.py
scripts/
  install-into-core.sh
  run-simulator.sh
  summarize-results.py
  uninstall-from-core.sh
  verify-results.py
docs/
  FINAL_REPORT.md
  CURRENT_AUDIT.md
  IMPLEMENTATION_PLAN.md
  REGTEST_PLAN.md
  DOCKER_NETEM_PLAN.md
  SHADOW_MODE_DESIGN.md
  ACCEPTANCE_CRITERIA.md
  FULL_RUN_2026-07-23.md
  TEST_PLAN_HU.md
summaries/
  security-probabilities.csv
  importance-sampling.csv
```

## Test plan

The detailed Hungarian audit and multi-layer test plan is preserved in
[docs/TEST_PLAN_HU.md](docs/TEST_PLAN_HU.md).

Results from the first complete 10,000-round matrix are documented in
[docs/FULL_RUN_2026-07-23.md](docs/FULL_RUN_2026-07-23.md).

## Status

Implemented and locally validated:

- compilation and linkage in the real DeFCoN `test_defcon` binary;
- direct use of Core quorum selection;
- quick simulation matrix;
- deterministic repeat runs;
- CSV and JSONL validation;
- clean installation and removal from a Core worktree.

Specification-scaffolded but not implemented in production Core:

- real multi-participant BLS/DKG phase execution;
- regtest activation and historical ChainLock verification;
- persistent conflicting-CLSIG evidence;
- running Docker/netem orchestration;
- emitting testnet shadow-mode telemetry;
- CPU, memory, and bandwidth microbenchmarks.

Passing this framework does not approve Q60 or any activation for mainnet.

## License

The simulator source follows the MIT license used by DeFCoN Core.
