#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 CONTAINER clear|latency|loss|jitter ARGS..." >&2
  exit 2
fi

container="$1"
scenario="$2"
shift 2

case "$scenario" in
  clear)
    docker exec "$container" tc qdisc del dev eth0 root 2>/dev/null || true
    ;;
  latency)
    delay="${1:?latency requires DELAY, for example 100ms}"
    docker exec "$container" tc qdisc replace dev eth0 root netem delay "$delay"
    ;;
  jitter)
    delay="${1:?jitter requires DELAY JITTER}"
    jitter="${2:?jitter requires DELAY JITTER}"
    docker exec "$container" tc qdisc replace dev eth0 root netem delay "$delay" "$jitter"
    ;;
  loss)
    loss="${1:?loss requires PERCENT, for example 5%}"
    docker exec "$container" tc qdisc replace dev eth0 root netem loss "$loss"
    ;;
  *)
    echo "Unknown scenario: $scenario" >&2
    exit 2
    ;;
esac
