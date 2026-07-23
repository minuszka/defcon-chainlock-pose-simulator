# Q60 advancement criteria

## Advance to regtest

Q60 may advance to real-protocol regtest when:

- exact hypergeometric calculations and rare-event estimates agree within the
  declared estimator confidence interval;
- direct Monte Carlo output includes Wilson bounds;
- selection and active-quorum overlap show no unexplained bias;
- modeled 15% independent outage DKG success is at least 99%;
- correlated provider/ASN risks are explicitly reported, not averaged away;
- all results are reproducible from fixed seeds and a Core commit.

## Advance to testnet shadow mode

- Real regtest BLS/DKG/CLSIG flow passes activation-boundary tests.
- Legacy ChainLocks verify after restart, reindex and activation.
- Mixed-version failure behavior is measured.
- Conflict specification tests have a documented production implementation gap.
- Shadow mode is proven state-neutral and clearly marked telemetry-only.

## Mainnet

Passing simulation, regtest, or shadow telemetry does **not** approve mainnet
activation. Mainnet requires a separate consensus proposal, implementation,
security review, release process, deployment plan, and explicit activation
decision.
