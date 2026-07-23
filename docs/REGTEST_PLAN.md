# Regtest plan for 8–10 real operators

## Purpose

The scale simulator validates population math. Regtest must validate the real
BLS keys, DKG phases, final commitments, recovered signatures, CLSIG relay,
restart, reindex, and partition behavior with 20–30 logical nodes distributed
across 8–10 operators.

## Test-only configuration

- Use regtest/devnet-only LLMQ parameter overrides.
- Use accelerated DKG intervals and block production only in test config.
- Create unique real BLS operator keys and collateral for every logical MN.
- Never copy test keys into a public report.
- Use a fixed test-only profile activation height `H`.

## Required sequence

1. Register all nodes and mine two successful baseline DKG cycles.
2. Verify legacy CLSIG at `H-1`, Q60 V2 at `H`, and cross-profile rejection.
3. Re-verify pre-activation ChainLocks at `H+100`.
4. Stop 1, 3, 10, 16, 19, then 20 selected members during DKG and signing.
5. Run 50/50 and 60/40 partitions based on selected quorum membership.
6. Delay and reorder contributions, commitments, recovered signatures and CLSIGs.
7. Exercise 10%, 25%, and 40% legacy/non-participating binaries.
8. Restart before DKG, during DKG, after first CLSIG, and during test conflict.
9. Run normal restart, `-reindex-chainstate`, and `-reindex`.
10. Export run events as JSON and convert them with
    `regtest/export_summary.py`.

## Acceptance gates

- Historical profile resolution is identical before and after restart/reindex.
- No side below threshold creates a valid ChainLock.
- Both valid test conflict evidences survive restart and reindex.
- Signing stops in the specified `FINALITY_CONFLICT` state.
- No unplanned PoSe ban occurs in the baseline or supported delay envelope.
- All test artifacts identify Core commit, config, seed and timeline.

Production Core does not yet implement all conflict-state gates. Those cases
remain expected-failure/specification tests until the production feature exists.
