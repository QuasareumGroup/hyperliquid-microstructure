# EXP-022 — Select xmin properly, then re-rank the candidate tails

**Status:** pre-registered, not yet run
**Registered:** 2026-07-27
**Author:** monproweb / Quasareum
**Script:** `experiments/exp022_xmin.py` (not written yet)
**Data:** `experiments/data/exp017_episodes.csv`, majors (n = 289,283) — already in the
repo, no collection needed.

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets
> reported.

---

## 1. Why

EXP-020 compared five candidate tails at **one** threshold, `xmin = $312,751`, chosen
by fixing `k = 5,000` by hand. Its own Limits say the ranking may move with `xmin`, and
its own Next item 1 — select `xmin` by minimising KS, per Clauset-Shalizi-Newman — was
never run. Two further loose ends came out of the same experiment:

- **Lognormal and Weibull are not separated** (Vuong R = −4.8 and −5.0 against Pareto,
  indistinguishable from each other). That is the current state of FINDINGS.md open
  item 2.
- **`pareto_cutoff` is unfitted, not rejected.** It pinned at its constraint boundary
  α = 0.01 and was excluded from the results. An untested candidate, which is not the
  same as a dismissed one.

This closes all three, or reports why it cannot.

## 2. One honest complication, registered up front

CSN select `xmin` by minimising the KS distance **of the power-law fit**. EXP-019 and
EXP-020 already rejected the power law here. Selecting a threshold to best fit a model
the data rejects, then using that threshold to rank *other* models, is not obviously
sound — the selected `xmin` optimises the reference, not the comparison.

So the ranking question is answered **twice**, and the two answers are reported side by
side:

- **(a) At the CSN-selected `xmin`** — the standard procedure, comparable to the
  published literature, run because it is what a referee will expect.
- **(b) Across a grid of `xmin`** — the ranking recomputed at each threshold. If the
  ranking is stable across the grid, the choice of `xmin` is not load-bearing and (a)'s
  soundness stops mattering. **This is the question that actually matters**, and it is
  the one EXP-020's Limits raised.

If (a) and (b) disagree, (b) is reported as the result and (a) as the convention.

## 3. Procedure

**Selection.** Candidate `xmin` = order statistics at `k ∈ [100, 50,000]`, log-spaced,
~200 values. At each, fit Pareto by MLE (closed form) and compute the KS distance
between the empirical CDF of the exceedances and the fitted one. Select the minimising
`xmin`. Uncertainty by nonparametric bootstrap, 500 resamples, reporting the
distribution of the selected `xmin` and of `k`.

**Goodness of fit at the selection.** KS with a parametric-bootstrap p-value, 1,000
synthetic samples, reusing EXP-019's machinery — which was validated there against a
known Pareto (p = 0.800, not rejected) and a known lognormal (p = 0.000, rejected).

**Ranking.** All five models from EXP-020, fitted conditional on `x ≥ xmin`, compared by
Vuong for non-nested pairs and by a χ²(1) likelihood-ratio test for `pareto_cutoff`,
which is nested in Pareto. Run at the selected `xmin` and at 20 log-spaced grid points.

**`pareto_cutoff`.** Widen the α bracket and reseed. If it still lands on a boundary it
is reported as **not fitted** rather than as a result — method rule 8.

**Validation before use, per method rule 5.** The selector runs first on synthetic
samples with a known `xmin`: Pareto tails grafted onto a lognormal body at a known
threshold. If it cannot recover the graft point, its answer on real data means nothing.

## 4. Predictions

- **P1.** The CSN-selected `xmin` differs from the hand-fixed $312,751 by more than a
  factor of 2 in either direction. *(The hand choice was arbitrary; agreement would be
  luck.)*
- **P2 (load-bearing).** The ranking is **stable across the grid**: lognormal and
  Weibull beat Pareto at every `xmin` where the fit is estimable, and exponential loses
  at every one. *This is what makes the EXP-020 conclusion independent of its arbitrary
  threshold.*
- **P3.** Lognormal and Weibull remain **unseparated** at the selected `xmin` — the
  Vuong test between them returns p > 0.05.
- **P4.** `pareto_cutoff`, once it converges off the boundary, does **not** beat
  lognormal or Weibull.

## 5. Falsification

- **P2 false** — the ranking flips somewhere on the grid. Then EXP-020's conclusion is
  threshold-dependent, "lognormal and Weibull beat Pareto" must be restated as holding
  only over a stated range of `xmin`, and FINDINGS.md result 3 narrows accordingly.
  **This is the load-bearing risk.**
- **P3 false** — they separate. That closes FINDINGS.md open item 2 outright and names
  the tail, which would be the most substantive outcome available here.
- **P1 false** — the hand-fixed threshold was near-optimal after all. Harmless, and
  worth saying plainly rather than quietly dropping.
- **P4 false** — the cutoff model wins. Then the tail is a power law *with* an
  exponential cutoff, which is a different object from either candidate and would
  require restating result 3 rather than refining it.

## 6. Success criterion

Success is **knowing whether the EXP-020 ranking survives its own threshold choice**,
and saying so either way. Naming the tail — P3 falsified — would be more, but it is not
the bar, and the sample may simply not contain enough tail to separate two models that
differ only far out.

## 7. Results

*(empty until the experiment runs)*
