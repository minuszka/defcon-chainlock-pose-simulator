#!/usr/bin/env python3
"""Generate an opt-in 20–40 node regtest Docker Compose topology."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("docker-compose.generated.yml"))
    parser.add_argument("--image", default="${DEFCON_IMAGE:-defcon-core:test}")
    args = parser.parse_args()
    if not 20 <= args.nodes <= 40:
        raise SystemExit("--nodes must be between 20 and 40")

    lines = [
        'name: "defcon-finality-lab"',
        "services:",
        "  controller:",
        "    image: ${CONTROLLER_IMAGE:-python:3.12-slim}",
        "    command: [\"sleep\", \"infinity\"]",
        "    networks: [control]",
    ]
    provider_names = [f"provider_{letter}" for letter in "abcd"]
    for index in range(1, args.nodes + 1):
        provider = provider_names[(index - 1) % len(provider_names)]
        rpc_port = 19000 + index
        p2p_port = 20000 + index
        lines.extend(
            [
                f"  mn{index:02d}:",
                f"    image: {args.image}",
                "    cap_add: [NET_ADMIN]",
                "    command:",
                "      - defcond",
                "      - -regtest=1",
                "      - -server=1",
                "      - -listen=1",
                "      - -discover=0",
                "      - -dnsseed=0",
                "      - -printtoconsole=1",
                f"      - -rpcport={rpc_port}",
                f"      - -port={p2p_port}",
                "      - -rpcbind=0.0.0.0",
                "      - -rpcallowip=172.16.0.0/12",
                "    networks:",
                "      - control",
                f"      - {provider}",
                "    volumes:",
                f"      - mn{index:02d}_data:/var/lib/defcon",
            ]
        )

    lines.append("networks:")
    lines.append("  control: {}")
    for provider in provider_names:
        lines.append(f"  {provider}: {{}}")
    lines.append("volumes:")
    for index in range(1, args.nodes + 1):
        lines.append(f"  mn{index:02d}_data: {{}}")

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.nodes}-node topology to {args.output}")


if __name__ == "__main__":
    main()
