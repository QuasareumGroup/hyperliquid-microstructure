# EXP-017 — Does α ≈ 1.15 survive a year and an unbiased sample? Majors vs HIP-3

**Status:** **pre-registered, campaign running.** Predictions below are written before any
number from this run has been seen.
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

*(empty — the campaign is running; results and the verdict on P1–P4 go here)*
