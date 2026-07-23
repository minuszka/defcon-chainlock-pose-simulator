#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/DEFCON" >&2
  exit 2
fi

core_root="$(cd "$1" && pwd)"
makefile="$core_root/src/Makefile.test.include"

if [[ ! -f "$makefile" ]]; then
  echo "Not a compatible DeFCoN Core source tree: $core_root" >&2
  exit 1
fi

python3 - "$makefile" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
entries = [
    "  test/llmq_scale_simulator_tests.cpp \\\n",
    "  test/chainlock_profile_resolver_tests.cpp \\\n",
    "  test/chainlock_finality_conflict_model_tests.cpp \\\n",
]
for entry in entries:
    text = text.replace(entry, "", 1)
path.write_text(text)
print("Removed simulator/specification tests from BITCOIN_TESTS")
PY

for source in \
  llmq_scale_simulator_tests.cpp \
  chainlock_profile_resolver_tests.cpp \
  chainlock_finality_conflict_model_tests.cpp; do
  target_file="$core_root/src/test/$source"
  if [[ -f "$target_file" ]]; then
    rm -- "$target_file"
  fi
done

echo "Removed simulator integration from: $core_root"
