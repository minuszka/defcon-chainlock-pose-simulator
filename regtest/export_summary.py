#!/usr/bin/env python3
"""Convert regtest JSON event records into a concise Markdown summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("events", type=Path)
    parser.add_argument("--output", type=Path, default=Path("regtest-summary.md"))
    args = parser.parse_args()
    with args.events.open(encoding="utf-8") as handle:
        events = json.load(handle)

    lines = [
        "# DeFCoN finality regtest summary",
        "",
        "| Scenario | Result | DKG success | ChainLock latency p95 | Notes |",
        "|---|---|---:|---:|---|",
    ]
    for item in events:
        lines.append(
            f"| {item['scenario']} | {item['result']} | "
            f"{item.get('dkg_success', 'n/a')} | "
            f"{item.get('chainlock_latency_p95_ms', 'n/a')} | "
            f"{item.get('notes', '')} |"
        )
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
