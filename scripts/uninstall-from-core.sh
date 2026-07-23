#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/DEFCON" >&2
  exit 2
fi

core_root="$(cd "$1" && pwd)"
target_file="$core_root/src/test/llmq_scale_simulator_tests.cpp"
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
entry = "  test/llmq_scale_simulator_tests.cpp \\\n"
if entry in text:
    path.write_text(text.replace(entry, "", 1))
    print("Removed llmq_scale_simulator_tests.cpp from BITCOIN_TESTS")
else:
    print("Makefile entry was not present")
PY

if [[ -f "$target_file" ]]; then
  rm -- "$target_file"
fi

echo "Removed simulator integration from: $core_root"
