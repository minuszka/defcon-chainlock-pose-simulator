#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/DEFCON" >&2
  exit 2
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
core_root="$(cd "$1" && pwd)"
makefile="$core_root/src/Makefile.test.include"

if [[ ! -f "$core_root/src/evo/deterministicmns.h" || ! -f "$makefile" ]]; then
  echo "Not a compatible DeFCoN Core source tree: $core_root" >&2
  exit 1
fi

sources=(
  llmq_scale_simulator_tests.cpp
  chainlock_profile_resolver_tests.cpp
  chainlock_finality_conflict_model_tests.cpp
)

for source in "${sources[@]}"; do
  cp "$project_root/core/src/test/$source" "$core_root/src/test/$source"
done

python3 - "$makefile" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
anchor = "  test/llmq_dkg_tests.cpp \\\n"
if anchor not in text:
    raise SystemExit("Unable to find llmq_dkg_tests.cpp anchor in Makefile.test.include")

entries = [
    "  test/llmq_scale_simulator_tests.cpp \\\n",
    "  test/chainlock_profile_resolver_tests.cpp \\\n",
    "  test/chainlock_finality_conflict_model_tests.cpp \\\n",
]
missing = [entry for entry in entries if entry not in text]
if missing:
    path.write_text(text.replace(anchor, anchor + "".join(missing), 1))
print(f"Ensured {len(entries)} simulator/specification tests in BITCOIN_TESTS")
PY

echo "Installed simulator into: $core_root"
echo "Only test sources/build metadata were changed; consensus parameters were not touched."
