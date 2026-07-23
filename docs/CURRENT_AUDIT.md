# Current simulator and Core coverage audit

## Simulator strengths before this extension

- Calls the production `CDeterministicMNList::CalculateQuorum()` method.
- Covers Q25 and candidate Q60 availability across 150–15,000 synthetic MNs.
- Produces deterministic CSV/JSONL output.
- Models independent outages, basic provider/ASN outages, version skew,
  flapping, delayed DKG messages, and operator concentration.

## Gaps found

- Threshold capture was measured only by direct Monte Carlo.
- Zero observed Q60 captures had no confidence bound and could be misread.
- No exact without-replacement probability was calculated.
- Provider/ASN/operator metadata was too shallow for active-quorum overlap.
- Only consecutive member overlap was reported.
- No restart-storm, regional, multi-provider, or partition model existed.
- No test-only signed-height resolver specification existed.
- Production Core has no persistent dual-evidence `FINALITY_CONFLICT` state.
- No Docker topology generator or regtest result exporter existed.
- Shadow telemetry requirements were documented only at a high level.

## Relevant production limitations

The inspected Core revision still:

- resolves ChainLocks through one global ChainLock LLMQ type;
- does not persist both competing valid CLSIG/recovered-signature evidences;
- logs and discards a second conflicting recovered signature;
- does not expose a finality-safe halt state;
- has no future Q60 activation height in production chainparams.

The added resolver and conflict tests are specification scaffolds, not claims
that production behavior already satisfies them.
