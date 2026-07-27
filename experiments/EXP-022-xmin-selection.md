# EXP-022 — Select xmin properly, then re-rank the candidate tails

**Status:** run. **P2 confirmed — the EXP-020 ranking survives its threshold choice at
every estimable `xmin`. P1, P3 and P4 rejected.** Lognormal and Weibull *do* separate,
but in opposite directions depending on where the tail is cut, so **the tail cannot be
named** from this data. That is the answer to FINDINGS open item 2, not a deferral of it.
**Registered:** 2026-07-27 · **Run:** 2026-07-27
**Author:** Thomas Erhel / Quasareum
**Scripts:** `experiments/exp022_xmin.py`
**Output:** `experiments/data/exp022_grid.csv` (18 thresholds)

**Data:** `experiments/data/exp017_episodes.csv`, majors (n = 289,283) — already in the
repo, no collection needed.

> **Current position: [FINDINGS.md](FINDINGS.md).** This file keeps its original
> pre-registration wording plus results; the state of claims lives there.

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

### Validation — passed

The selector recovers a known graft point on lognormal-body/Pareto-tail samples:
1,000 → 1,113 (×1.11), 5,000 → 5,019 (×1.00), 200 → 281 (×1.40), with `α̂` within 3% of
the generator each time.

### The selection

| | |
|---|---|
| CSN-selected `xmin` | **$560,627** (k = 3,104, KS = 0.0234, α̂ = 0.960) |
| EXP-020's hand-fixed | $312,751 (k = 5,000) — **factor 1.79** |
| bootstrap 95% CI on `xmin` (500 resamples) | **[$193,877, $986,963]** |
| bootstrap 95% CI on k | [1,909, 7,509] |
| Pareto goodness of fit at the selection | KS p = **0.010, rejected** |

**P1 rejected**, and worth stating plainly rather than dropping: the factor is 1.79, not
the >2 predicted. EXP-020's arbitrary threshold sits comfortably inside the bootstrap
interval — it was a better guess than it had any right to be.

The interval spans **a factor of five**. `xmin` is barely determined by this data, which
is itself the reason the grid check below is the load-bearing one.

### P2 — confirmed. The ranking does not depend on the threshold.

At **all 14 estimable thresholds**, spanning `xmin` from $14,912 to $8,845,704 — nearly
three orders of magnitude — lognormal and Weibull both beat Pareto (Vuong R from −1.78
to −27.38), and exponential never beats it at any threshold.

This is what EXP-020's Limits asked and could not answer. Its conclusion is not an
artefact of `k = 5,000`.

**Four thresholds are excluded as not estimable**, k ∈ [9,856, 26,113] (`xmin` $49k–$163k).
There both alternatives sit on a parameter bound: lognormal at μ = −30, Weibull at
λ/xmin = 10⁻⁹. Neither is an optimiser failure — with multi-start they land there
reliably, and the likelihood genuinely improves toward the bound. **Both are converging
on the power-law limit of their own family**: a lognormal with μ → −∞, σ → ∞ and a
Weibull with λ → 0, β → 0 both approach a Pareto over any bounded range. In that band
the extra parameter buys nothing and the models are unidentified, so their Vuong
statistics are reported as no-result (method rule 8), not as "Pareto wins".

> **Caught by a non-monotone sequence, and worth recording as a near-miss.** The first
> run used EXP-020's single-start fitters and printed R = −5.93, **+1.68**, −0.30, −4.72
> across consecutive thresholds. Read as a summary that is a sign flip — exactly what P2
> was testing, and it would have been reported as P2 falsified. The parameters
> underneath were μ = −778 and λ = 6×10⁻³⁰⁶, a denormal at the floating-point floor.
> Method rule 7 is what caught it; the bounds and multi-start only made the degeneracy
> visible instead of letting it produce noise.

### P3 — rejected. They separate, and the direction reverses.

At the selected `xmin`, Weibull beats lognormal: **R = −3.53, p < 0.001**. The
prediction that they stay indistinguishable is wrong.

But the separation is not a property of the tail — it is a property of where the tail is
cut:

| `xmin` range | lognormal vs Weibull | winner |
|---|---|---|
| $199k – $1.33M | R = −2.74 to −3.67, p < 0.01 | **Weibull** |
| $1.85M – $8.85M | R = −1.00 to −1.86, p > 0.05 | indistinguishable |
| $14.9k – $28.3k | R = **+13.42 to +15.92**, p ≪ 0.001 | **lognormal** |

Weibull wins in the far tail, lognormal wins decisively deep in the body, and the
crossover is inside the unidentified band. **Naming the tail is not possible from this
data** — any name would be a report of the threshold, not of the distribution.

### P4 — rejected, and the rejection is local

`pareto_cutoff` now converges off its boundary (α = 1.842, λ/xmin = 0.0084) once the
α > 0.01 bracket is removed — that bracket was the bug, since with λ > 0 the density
`x^-a e^{-λx}` is normalisable for any real α, so constraining α > 0 was an assumption
rather than a regularisation.

At the selected `xmin` it has the best likelihood of all five and beats both
alternatives — cutoff vs lognormal R = +2.80 (p = 0.005), vs Weibull R = +2.50
(p = 0.012). Taken alone that would restate result 3 as "power law with exponential
cutoff".

**It does not survive the grid.** Across the 14 estimable thresholds it beats both
alternatives at **2** — k = 1,943 and k = 2,688 — is indecisive at 10, and loses
decisively at the two lowest (R = −16.22 and −21.77). The CSN-selected k = 3,104 sits
directly beside that two-point window.

So the selected-`xmin` answer is the threshold-specific one, and the registered rule in
§2 applies: **(b) is the result, (a) is the convention.** This is the concrete case the
complication was registered for, and it arrived.

### Summary

| prediction | outcome |
|---|---|
| P1 — selected `xmin` differs by >2× | **rejected** (1.79×) |
| P2 — ranking stable where estimable | **confirmed** (14/14) |
| P3 — lognormal and Weibull unseparated | **rejected** — they separate, direction reverses |
| P4 — cutoff does not beat the alternatives | **rejected at the selection, holds on the grid** |

## 8. What this settles

**Result 3 in FINDINGS.md stands and is now threshold-independent.** The tail is heavy,
exponential is rejected, Pareto is rejected, and the two-parameter alternatives beat it
across three orders of magnitude of `xmin`. That was the open risk and it is closed.

**FINDINGS open item 2 is closed with a negative answer**, which is still an answer:
lognormal and Weibull cannot be separated *as a description of the tail*, because
whichever wins depends on where the cut is made and the ranking reverses across the
range. Any paper naming this tail lognormal or stretched-exponential would be reporting
its own threshold choice.

**One reusable observation.** Over a band of `xmin`, both two-parameter alternatives
degenerate onto the power-law limit of their own family while the power law is itself
rejected by KS. So no candidate here describes that band — a gap that a bare model
ranking hides completely, since a ranking always returns a winner.

## 8bis. Corrections from adversarial review (2026-07-27)

Three statements above are corrected by the review (`review/FABLE.md`, findings B7, B8, B10;
each verified independently before being applied):

- **§3 says a 20-point grid; the run used 18** (`exp022_grid.csv`), and the script's default is
  14. The registered number was not the executed one.
- **§7's band diagnosis ("lognormal at μ = −30") is half wrong.** At two of the four excluded
  thresholds the lognormal converged *interior* (μ = 1.96 and −17.11); only the Weibull pinned
  at the script's numerical λ bound. What actually holds — and is the stronger argument — is
  that a **direct GoF test rejects every fitted candidate in the band** (parametric-bootstrap
  KS, p ≤ 0.01, re-verified with widened bounds). The "unidentified band" conclusion stands on
  that footing, not on the boundary diagnosis.
- **The GoF simplification's direction was misstated** ("conservative toward rejection"). The
  observed KS is minimised by threshold selection while the synthetics' are not, which inflates
  p — a bias *against* rejection. The rejection at p = 0.010 therefore holds a fortiori.

Also noted in review: excluding the four degenerate thresholds *cost* P2 two thresholds where
lognormal beat Pareto cleanly (R = −7.53, −2.68) — the exclusion rule works against the claim it
protects, not for it.

## 9. Limits

- The GoF bootstrap fixes `xmin` inside each synthetic rather than re-selecting it, as
  CSN prescribe. That makes the p conservative toward rejection. Same simplification as
  EXP-019, where it was validated against known generators.
- Majors only, one year, `notional` per episode. HIP-3 untested here.
- The unidentified band is diagnosed from the fitted parameters hitting bounds, not from
  a formal identifiability analysis. The diagnosis is consistent with the algebra of both
  limits but is not a proof.
- Four candidate families. A fifth (e.g. generalised Pareto, log-gamma) could behave
  differently, and nothing here rules that out.
