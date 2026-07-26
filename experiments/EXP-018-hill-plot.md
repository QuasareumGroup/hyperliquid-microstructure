# EXP-018 — Hill plot over a continuum of k: the plateau sits at α ≈ 0.93

**Status:** run, then **largely undone by [EXP-020](EXP-020-alternatives.md)**. The plateau is
real as an artefact and empty as an estimate: the tail is lognormal/Weibull, not Pareto, and a
lognormal tail is *known* to make the Hill estimator drift. EXP-017's drift was the signature of
the true distribution; this file smoothed over a real symptom and read a parameter off it.
The plateau location and its robustness (EXP-019) still stand as facts about the estimator.
**Date:** 2026-07-26
**Data:** `experiments/data/exp017_episodes.csv` — 351,540 episodes, one archive year.
**Script:** `experiments/exp018_hill_plot.py`. Figure: `reports/exp018_hill_plot.svg` (+ dark).

---

## Why

EXP-017 read the tail index at three arbitrary k (500 / 2,000 / 5,000), saw 1.22 → 1.02 → 0.93,
and concluded the index was "not stable in k". Three points cannot separate *the estimator is
unstable* from *we picked badly*. A Hill plot over a continuum can, and reading α off a plateau
— or stating there is none — is the standard way to report an index that moves.

## Three stability criteria, two of them wrong

The result depended entirely on how "flat" was defined, and the first two definitions were
broken in ways worth recording.

| criterion | verdict | why it fails |
|---|---|---|
| lowest coefficient of variation | plateau at k ∈ [50,198 – 60,000], α ≈ 0.64 | the Hill s.e. is α/√k, so it shrinks **mechanically** with k. The flattest window is always the largest k — which is the body, not the tail. |
| lowest spread ÷ sampling noise | plateau at k ∈ [167 – 830], α ≈ 1.26 | a window can be flat *within noise* while α falls monotonically across it. This one drifts **1.45 → 1.25 → 1.09** and still scored 1.3×, because the s.e. is wide at small k. |
| **slope of α vs log k** | **plateau at k ∈ [2,420 – 12,050], α ≈ 0.93, slope +0.00/decade** | a plateau is a slope near zero. A drift excused by wide error bars is still a drift. |

**Between criteria two and three the wrong answer was reported aloud** — "there is a plateau at
α ≈ 1.26" — on the strength of the summary statistic, without looking at the underlying values.
They read 1.45, 1.25, 1.09: a clean monotone decline. Fourth instance the same day of trusting
a computed summary over the numbers under it.

## Results

| series | flattest window | α | slope / decade | verdict |
|---|---|---|---|---|
| **episodes · majors** | k ∈ [2,420 – 12,050] | **0.93** | +0.00 | **plateau** |
| episodes · HIP-3 | k ∈ [372 – 1,852] | 1.09 | −0.06 | drift, no plateau |
| fills (approx.) | k ∈ [10,081 – 50,198] | **3.07** | −0.03 | plateau |

The majors plateau spans 0.8%–4.2% of the sample — a defensible tail fraction, not the body.

**α ≈ 0.93 is below 1.** At k = 5,000 the CI is [0.88, 0.93], excluding 1.

> **Retracted by [EXP-019](EXP-019-plateau-checks.md).** The sentence that stood here — that the
> fitted tail is heavy enough that the sample mean is not a stable statistic — rested on α < 1
> **inside a Pareto model**, and a KS test with parametric-bootstrap p-values rejects that model
> at every k tested (p ≤ 0.01). The asymptotic CI was also optimistic: correct subsampling
> widens it to [0.831, 0.998], so α < 1 holds only narrowly. What survives is α ≈ 0.93 as an
> **empirical** tail-heaviness summary, robust to window width — and the episode/fill gap, which
> assumes no parametric form at all.

**The episode/fill gap is wider than previously reported**: plateau to plateau, **0.93 vs 3.07**,
against EXP-016's 1.15 vs 2.05. The two curves do not converge at any depth — visible in the
figure more clearly than in any table.

## Figure

`reports/exp018_hill_plot.svg`, light and dark. Palette: slots 1–3 of the dataviz reference,
validated (worst adjacent CVD ΔE 9.2, normal-vision 27.6; aqua below 3:1 on the light surface,
so direct labels are mandatory and shipped). Confidence bands are 95%; the shaded span is the
majors plateau.

Each curve is capped at **20% of its own sample**. A first version capped k globally, which took
the HIP-3 curve to 96% of its 62,257 episodes — the whole distribution treated as tail. That
version was sent before the error was caught.

## Correction to EXP-017

Its "the index is not stable in k, α ∈ [0.9, 1.2]" was drawn from three points, one of which
(k = 5,000 out of 289,283 majors = 1.7%) sits inside what is now the plateau, and one (k = 500 =
0.17%) in the noisy small-k region. The index **is** stable, in a region neither of those
bracketed.

## Limits

- Slope-based plateau detection still needs a window width (0.7 decades here); a different width
  moves the window. Not tested for sensitivity.
- HIP-3 shows no plateau at n = 62,257 — that may be sample size rather than a real difference.
- Hill assumes a Pareto tail throughout. A plateau is consistent with that but does not prove it;
  a goodness-of-fit test on the plateau region has not been run.
- Asymptotic CIs; no bootstrap.

## Next

1. Sensitivity of the plateau to window width, and a bootstrap CI on the plateau α.
2. A goodness-of-fit check that the plateau region is genuinely Pareto.
3. HIP-3 with more hours, to see whether its missing plateau is sample size or substance.
