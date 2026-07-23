# Reviewable implementation plan

No commit in this plan changes mainnet consensus or production chainparams.

1. **Exact security math**
   - hypergeometric threshold tail;
   - yearly/1,000-rotation expectations;
   - direct Monte Carlo and Wilson intervals.
2. **Rare-event estimation**
   - deterministic sequential importance sampling;
   - likelihood ratios, effective sample size, exact cross-check.
3. **Failure domains and overlap**
   - provider, ASN, region, operator, collateral owner, version and availability;
   - active-quorum overlap output;
   - restart, partition and correlated-outage scenarios.
4. **Test-only finality specifications**
   - signed-height profile boundary;
   - fail-closed configuration checks;
   - dual-evidence persistence model and signing halt.
5. **Protocol test plans**
   - real BLS/DKG regtest matrix;
   - Docker/netem generator and fault commands;
   - non-consensus shadow telemetry contract.
6. **Reports and acceptance gates**
   - small exact/importance summaries;
   - assumptions and limitations;
   - explicit no-mainnet-approval statement.

Each step can be reviewed and committed independently.
