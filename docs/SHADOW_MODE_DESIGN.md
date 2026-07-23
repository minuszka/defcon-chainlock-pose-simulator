# Non-consensus Q60 shadow telemetry design

## Contract

Shadow mode is telemetry, not consensus truth.

It may:

- calculate candidate Q60 members from the local historical chain state;
- observe candidate member readiness and DKG timing;
- report valid-member counts and threshold reachability;
- aggregate provider, ASN, region and operator concentration;
- compare legacy and candidate availability.

It must never:

- create, sign or relay a Q60 ChainLock;
- change chain selection, mempool, PoSe, rewards or deterministic MN state;
- choose a profile from live MN count;
- modify mainnet chainparams;
- claim that local telemetry proves network-wide consensus behavior.

## Suggested event schema

```json
{
  "schema": 1,
  "kind": "q60_shadow_telemetry",
  "core_commit": "...",
  "base_block_hash": "...",
  "base_height": 123456,
  "candidate_type": "q60_44_41",
  "selected": 60,
  "observed_valid": 55,
  "threshold_reachable": true,
  "provider_hhi": 0.12,
  "telemetry_only": true
}
```

## Advancement gate

- At least four weeks and 100 complete candidate cycles.
- No consensus-state difference between shadow-on and shadow-off nodes.
- No unexplained selection divergence at an identical tip.
- DKG availability and latency meet a precommitted testnet gate.
- Privacy review for IP-to-ASN/provider aggregation.
