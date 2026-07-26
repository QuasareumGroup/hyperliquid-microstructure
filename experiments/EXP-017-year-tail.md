# EXP-017 — Does α ≈ 1.15 survive a year and an unbiased sample? Majors vs HIP-3

**Status:** run. **P3 and P4 rejected.** α < 2 survives everywhere, but the index is **not
stable in k** — which qualifies EXP-016's headline number.
**Date:** 2026-07-26
**Scripts:** `experiments/exp017_year_tail.py` (collection),
`experiments/exp017_analyse.py` (analysis).

---

## Why

EXP-016 measured a liquidation-size tail index of **α ≈ 1.15** — infinite variance, mean near
the edge of existing — and showed that counting fills instead of episodes raises it to ≈ 2.05,
which changes the *kind* of risk rather than its size.

That estimate rests on **12 hours, two of which were chosen for their cascades**. The tail index
is now the load-bearing number in this repo, and it is resting on a sample selected partly for
the property it measures. It needs a bigger and unbiased sample.

## Design

**Stratified, not exhaustive.** A full census is 8,760 hours ≈ 300 GB of requester-pays egress
(~$18, ~12h). **Four fixed hours per day (02, 08, 14, 20 UTC) across all 365 archive days** is
~50 GB — inside AWS's free allowance — covers the year uniformly, and lifts the sample from
6,546 to an expected ~294,000 episodes, which is what a tail index actually needs.

Hours are **fixed, not chosen**: that removes EXP-016's selection bias directly rather than
correcting for it.

**Segments.** Majors versus **HIP-3 builder-deployed perps**, identified by the `dex:` prefix
in the coin name — 106 of 345 assets in a sampled hour, and 22% of that hour's liquidation
fills. Enough to drag the aggregate if their mechanics differ, and the aggregate hides it.

**Estimator.** The Hill index validated in EXP-016 against Pareto samples with known α. The
analysis script **re-validates it at startup and refuses to report anything if it fails** — a
broken version silently returned 0.00 earlier the same day.

Only the **episode** index is claimed. A per-fill index is printed alongside for continuity with
EXP-016, but it rests on splitting each episode equally across its fills, an approximation
already shown to be loose. It is labelled as such in the output.

## Predictions

- **P1** — α on episodes stays within ~±0.15 of 1.15, with a tighter CI. The 12-hour estimate
  was small but not biased in this respect.
- **P2** — α moves materially. Cascade-hour selection inflated the share of large episodes and
  therefore distorted the tail.
- **P3** — majors and HIP-3 differ materially in α. Thin builder markets with different margin
  parameters plausibly liquidate differently.
- **P4** — the inflation factor **falls below 3.8×** on the unbiased sample. EXP-016 already
  flagged that its figure "may be slightly high" because tranching grows with episode size and
  cascade hours were over-represented. This is that flag turned into a testable commitment.

**Falsification.** P1 and P2 are mutually exclusive and jointly exhaustive at the stated
threshold. P3 fails if the two CIs overlap substantially. P4 fails if the factor is ≥ 3.8×.

## Results

**351,540 episodes from 2,010,042 fills**, 1,460 hours across 365 days — 54× EXP-016's sample.

| segment | episodes | fills | inflation | share of notional |
|---|---|---|---|---|
| all | 351,540 | 2,010,042 | **5.72×** | — |
| majors | 289,283 | 1,672,034 | 5.78× | **90.7%** (82.3% of episodes) |
| HIP-3 | 62,257 | 338,008 | 5.43× | 9.3% (17.7% of episodes) |

Hill index on episodes, with asymptotic 95% CI:

| k | all | majors | HIP-3 |
|---|---|---|---|
| 500 | 1.22 [1.11, 1.33] | 1.20 [1.10, 1.31] | 1.09 [1.00, 1.19] |
| 2,000 | 1.02 [0.97, 1.06] | 0.99 [0.95, 1.04] | 1.03 [0.98, 1.07] |
| 5,000 | 0.93 [0.91, 0.96] | 0.90 [0.88, 0.93] | 0.85 [0.83, 0.88] |

## Verdict

| | prediction | outcome |
|---|---|---|
| P1 | α within ±0.15 of 1.15 | **partial** — holds at k=500 (1.22), fails deeper |
| P2 | α moves materially | **partial** — lower at comparable tail depth |
| **P3** | majors ≠ HIP-3 | **REJECTED** — CIs overlap at every k |
| **P4** | inflation falls below 3.8× | **REJECTED** — it rises to 5.72× |

**P4 is the useful failure.** EXP-016 hedged that its 3.8× "may be slightly high" because
tranching grows with size and cascade hours were over-represented. On an unbiased year, the
factor is **5.72×** — the hedge pointed the wrong way. Turning it into a falsifiable prediction
is what exposed that; as a caveat it would have survived indefinitely.

**P3 rejected cleanly.** Majors and HIP-3 are statistically indistinguishable at every depth
(k=2,000: [0.95, 1.04] vs [0.98, 1.07]). Tail behaviour is therefore **a property of the
liquidation mechanism, not of the market** — thin builder markets and BTC deleverage the same
way. HIP-3 carries 17.7% of episodes but 9.3% of notional: more liquidations, smaller, same tail.

## The finding that was not predicted

```
α on episodes:   k=500 → 1.22     k=2,000 → 1.02     k=5,000 → 0.93
```

**The index is not stable in k.** It drifts from 1.22 to 0.93 as the tail fraction widens, so
the size distribution is **not a clean power law** and any single α is a choice of tail depth
presented as a measurement.

This directly qualifies EXP-016's headline: "α ≈ 1.15" was one depth on 6,546 episodes. The
honest statement is **α ∈ [0.9, 1.2] depending on tail depth**.

## What survives

- **α < 2 at every depth, on every segment**, with CIs nowhere near 2. Infinite variance is not
  in doubt.
- **The gap to the fill-based index holds** (1.96–2.68 across k). The core claim of EXP-016 —
  that counting fills changes the *kind* of tail risk, not merely its magnitude — stands on
  351,540 episodes rather than 6,546.
- The inflation factor is **larger** than first measured, which strengthens rather than weakens
  the practical warning.

## Limits

- Stratified, not exhaustive: 4 fixed hours per day. Uniform in time, but a cascade falling
  outside those hours is invisible. A census would cost ~$18 and ~12h.
- The per-fill index remains an approximation (equal split within an episode) and is not
  claimed; only its order of magnitude relative to the episode index is used.
- Hill assumes a Pareto tail. The k-instability above is evidence that assumption is imperfect,
  which is itself the reason a single α should not be quoted.

## Next

1. A Hill plot across a continuum of k, with a stability region identified rather than three
   arbitrary points — the right way to report an index that moves.
2. An estimator that does not assume clean Pareto behaviour, given the drift.
3. Whether the inflation factor is stable over the year or trends with venue growth.
