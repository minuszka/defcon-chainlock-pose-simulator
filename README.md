# DeFCoN ChainLock and PoSe Simulator

A Core-native C++ scale simulator for evaluating DeFCoN ChainLock quorum
selection, DKG availability, operator concentration, correlated outages, and
PoSe-related failure scenarios.

The simulator calls DeFCoN Core's production
`CDeterministicMNList::CalculateQuorum()` implementation directly. It does not
reimplement the quorum selection algorithm.

## Current scope

The first implementation provides:

- synthetic but genuine `CDeterministicMNList` fixtures;
- Q25 (`25/22/17`) and candidate Q60 (`60/44/41`) profiles;
- populations from 150 to 15,000 masternodes;
- deterministic, reproducible simulation seeds;
- independent offline rates from 5% to 30%;
- provider- and ASN-correlated outages;
- flapping nodes;
- 25%, 33%, and 40% operator concentration;
- 10%, 25%, 40%, and 50% mixed-version populations;
- delayed DKG message models;
- quorum overlap and selection distribution measurements;
- DKG `minSize` and signing-threshold availability checks;
- CSV and JSONL output;
- automatic result validation.

This version uses the real Core selection code. DKG network phases are currently
evaluated with deterministic fault models. Execution of the full BLS/DKG message
state machine and Docker/netem network emulation are planned as subsequent
layers.

## Safety boundary

The integration script changes only test-related files in a Core checkout:

- `src/test/llmq_scale_simulator_tests.cpp`;
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

The generated result directory is intentionally excluded from Git.

## Determinism

All fixtures, modifiers, availability events, failure-domain assignments, and
fault schedules are derived from the configured master seed. Re-running the
same Core revision with the same configuration produces byte-identical CSV and
JSONL output.

The quick validation used during development produced:

```text
14,406 result rows
8 scenario families
2 quorum profiles
26,106 passing Boost assertions
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
scripts/
  install-into-core.sh
  run-simulator.sh
  uninstall-from-core.sh
  verify-results.py
docs/
  TEST_PLAN_HU.md
```

## Test plan

The detailed Hungarian audit and multi-layer test plan is preserved in
[docs/TEST_PLAN_HU.md](docs/TEST_PLAN_HU.md).

## Status

Implemented and locally validated:

- compilation and linkage in the real DeFCoN `test_defcon` binary;
- direct use of Core quorum selection;
- quick simulation matrix;
- deterministic repeat runs;
- CSV and JSONL validation;
- clean installation and removal from a Core worktree.

Not implemented yet:

- real multi-participant BLS/DKG phase execution;
- regtest activation and historical ChainLock verification;
- persistent conflicting-CLSIG evidence;
- Docker/netem orchestration;
- testnet shadow-mode telemetry;
- CPU, memory, and bandwidth microbenchmarks.

## License

The simulator source follows the MIT license used by DeFCoN Core.
