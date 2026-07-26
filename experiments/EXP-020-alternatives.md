# EXP-020 — The tail is heavy but not a power law; the "plateau" was the signature of a lognormal

**Status:** run. **Lognormal and Weibull both beat Pareto and tie with each other.** Exponential
loses decisively, so the tail is genuinely heavy — just not power-law heavy. Closes the loop
back to EXP-017.
**Date:** 2026-07-26
**Data:** `experiments/data/exp017_episodes.csv`, majors, k = 5,000, xmin = $312,751.
**Script:** `experiments/exp020_alternatives.py`.

---

## Why

EXP-019 ran the first half of Clauset-Shalizi-Newman — a KS test with parametric-bootstrap
p-values — which rejected Pareto at every k. That establishes what the tail is *not*. This runs
the second half: fit the plausible alternatives on the same exceedances and compare by
likelihood ratio (Vuong for non-nested pairs).

## The fitters were validated first, and two of them failed

Synthetic samples from each family, checked for whether the procedure recovers its own
generator. On the first pass **two of five fits were broken**:

- **Weibull** — a sample generated from a Weibull was assigned to Pareto. The synthetic
  generator did not match the truncated model being fitted, and the objective overflowed.
  Fixed by scaling to `u = x/xmin`, multi-start, and a correct inverse-CDF generator.
- **Pareto with cutoff** — returned a *worse* maximised log-likelihood than Pareto, which is
  impossible: Pareto is its λ → 0 limit, so it nests it. The optimiser had not converged.

After repair, all three generators are recovered: Pareto → Pareto, lognormal → lognormal,
Weibull → Weibull.

**`pareto_cutoff` is nonetheless excluded from the results.** On real data it returns
α = 0.01 — exactly the lower bound of its constraint — with λ ≈ 1e-18, degenerating toward a
non-normalisable constant density, and a log-likelihood 11,000 units above Pareto for one extra
parameter. The normalisation is wrong outside the region where the incomplete gamma applies. A
fit sitting on its constraint boundary is not a result.

## Results

| model | logL | parameters |
|---|---|---|
| **weibull** | **−74,307.3** | β = 0.1185 |
| **lognormal** | **−74,308.6** | μ = 7.26, σ = 2.87 |
| pareto | −74,339.1 | α = 0.9008 |
| exponential | −76,965.1 | — |

Vuong normalised likelihood ratios against Pareto:

| comparison | R | p | |
|---|---|---|---|
| pareto vs lognormal | **−4.8** | 0.000 | lognormal wins |
| pareto vs weibull | **−5.0** | 0.000 | weibull wins |
| pareto vs exponential | **+14.8** | 0.000 | pareto wins by a wide margin |

**The tail is heavy.** Exponential loses decisively — this is not a sampling artefact.

**But it is not a power law.** Lognormal and Weibull both beat Pareto, and are
**indistinguishable from each other** (1.3 log-units apart on n = 5,000). β = 0.1185 describes
an extremely stretched exponential.

## This closes the loop back to EXP-017

A **lognormal tail produces a Hill estimator that drifts with k** — that is a known property,
not a defect. And drift is exactly what EXP-017 measured (1.22 → 1.02 → 0.93) before EXP-018
found a "plateau" in it.

So the drift was **the signature of the true distribution**, not a measurement problem.
EXP-017's instinct was right for a reason it had not identified, and EXP-018 smoothed over a
real symptom.

**α ≈ 0.93 is therefore not a parameter of anything.** It is what Hill returns when applied to a
lognormal-ish tail over that range of k. The plateau is real as an artefact and empty as an
estimate.

## What survives, and it is the part that mattered

**The episode-versus-fill gap.** It compares two curves computed identically on the same data
and assumes no parametric form at all, so none of the above touches it. Counting fills instead
of episodes still misrepresents the size distribution — that claim never depended on the tail
being Pareto.

The practical warning from EXP-016 also stands unchanged: fills inflate liquidation counts
5.72× on an unbiased year, and the inflation grows with episode size.

## Limits

- One threshold (k = 5,000). The ranking may move with xmin; Clauset et al. select xmin by
  minimising KS, which was not done here.
- Lognormal and Weibull are not separated. Distinguishing them needs more tail data or a
  different discriminator.
- `pareto_cutoff` remains unfitted rather than rejected — an untested candidate, not a
  dismissed one.
- Majors only.

## Next

1. Select xmin properly (KS-minimising) and re-rank, rather than fixing k by hand.
2. Restate the headline across EXP-016 → EXP-019 in non-parametric terms. That is now overdue:
  four files quote a tail index that this experiment shows is not estimating a parameter.
