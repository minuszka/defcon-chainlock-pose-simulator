# Docker and netem finality lab

Generate a 20–40 node topology:

```bash
python docker/generate-compose.py --nodes 20 \
  --output docker/docker-compose.generated.yml
docker compose -f docker/docker-compose.generated.yml up -d
```

The generated topology creates four provider networks plus a control network.
Nodes receive `NET_ADMIN` only for opt-in test traffic shaping.

Examples:

```bash
./docker/netem.sh defcon-finality-lab-mn01-1 latency 100ms
./docker/netem.sh defcon-finality-lab-mn02-1 jitter 100ms 30ms
./docker/netem.sh defcon-finality-lab-mn03-1 loss 5%
./docker/netem.sh defcon-finality-lab-mn03-1 clear
```

Planned orchestrator scenarios:

- symmetric latency and jitter;
- packet loss and burst loss;
- one-way DKG/CLSIG relay delay using a proxy or directional firewall rule;
- 50/50 partition;
- provider bridge isolation;
- 5/10/20-node restart storms;
- staggered peer reconnection after partition;
- two-miner fork and reordered CLSIG delivery.

The generated Compose file is intentionally untracked. No mainnet ports,
wallets, keys or live datadirs are mounted.
