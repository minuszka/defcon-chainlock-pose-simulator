#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 /path/to/DEFCON/build [quick|full]" >&2
  exit 2
fi

build_root="$(cd "$1" && pwd)"
mode="${2:-quick}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$project_root/configs/$mode.env"

if [[ ! -f "$config" ]]; then
  echo "Unknown mode: $mode" >&2
  exit 2
fi

set -a
# shellcheck source=/dev/null
source "$config"
set +a

export DEFCON_SIM_OUTPUT_DIR="${DEFCON_SIM_OUTPUT_DIR:-$project_root/results/$mode}"
mkdir -p "$DEFCON_SIM_OUTPUT_DIR"

test_binary=""
for candidate in \
  "$build_root/src/test/test_defcon" \
  "$build_root/src/test/test_bitcoin" \
  "$build_root/test/test_defcon"; do
  if [[ -x "$candidate" ]]; then
    test_binary="$candidate"
    break
  fi
done

if [[ -z "$test_binary" ]]; then
  echo "Unable to locate test_defcon below: $build_root" >&2
  exit 1
fi

"$test_binary" \
  --run_test=llmq_scale_simulator_tests/core_native_selection_and_fault_matrix \
  --log_level=message \
  --report_level=short

echo "Results: $DEFCON_SIM_OUTPUT_DIR/results.csv"
echo "Results: $DEFCON_SIM_OUTPUT_DIR/results.jsonl"

python3 "$project_root/scripts/verify-results.py" "$DEFCON_SIM_OUTPUT_DIR"
