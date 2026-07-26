# EXP-019 — Three checks on the plateau: robust to width and bootstrap, but the Pareto fit is rejected

**Status:** run. **Window width and bootstrap hold. Goodness-of-fit is rejected at every k.**
The number survives as an empirical summary; its parametric reading does not.
**Date:** 2026-07-26
**Data:** `experiments/data/exp017_episodes.csv`, majors only (n = 289,283).
**Script:** `experiments/exp019_plateau_checks.py`.

> **Current position: [FINDINGS.md](FINDINGS.md).** This file is a running record and keeps its original wording plus corrections; the state of claims lives there.

---

## Why

EXP-018 located the plateau with **one** window width and reported an **asymptotic** CI, and
Hill assumes a Pareto tail that was never tested. The number is load-bearing, so all three
needed checking rather than listing as limits.

The GoF machinery is validated first against known answers — Pareto α=1 → p = 0.800 (not
rejected); lognormal → p = 0.000 (rejected). The test discriminates.

## 1. Window-width sensitivity — passes

| width (decades) | k_lo | k_hi | **α** | slope |
|---|---|---|---|---|
| 0.4 | 3,780 | 9,221 | **0.90** | +0.021 |
| 0.5 | 7,056 | 21,515 | **0.94** | −0.011 |
| 0.7 | 2,420 | 12,050 | **0.93** | +0.000 |
| 1.0 | 3,780 | 28,115 | **0.92** | −0.001 |
| 1.3 | 3,780 | 28,115 | **0.92** | −0.001 |

α holds at **0.90 – 0.94** across every width. The window moves; the number does not. The
plateau is not an artefact of the search parameter.

## 2. Bootstrap — the asymptotic CI was optimistic

| method | 95% CI | width |
|---|---|---|
| asymptotic (α/√k) | [0.876, 0.926] | 0.050 |
| bootstrap, n-out-of-n | [0.880, 0.926] | 0.046 |
| subsampling, n/4 | [0.858, 0.944] | 0.086 |
| **subsampling, n/16** | **[0.831, 0.998]** | **0.167** |

The naive bootstrap agrees with the asymptotic figure — but n-out-of-n bootstrap is **known to
be inconsistent** for tail-index estimation, so that agreement is worth nothing. Subsampling,
which is the consistent method, more than triples the width. At n/16 the upper bound reaches
**0.998**: α < 1 still holds, but **narrowly**, not with the margin the asymptotic CI implied.

## 3. Goodness of fit — rejected everywhere

| k | α | KS | p | |
|---|---|---|---|---|
| 2,500 | 0.98 | 0.0249 | 0.010 | **rejected** |
| 5,000 | 0.90 | 0.0310 | 0.000 | **rejected** |
| 10,000 | 0.99 | 0.0999 | 0.000 | **rejected** |
| 12,000 | 0.98 | 0.0769 | 0.000 | **rejected** |

**The plateau region is not Pareto**, at any depth.

One necessary nuance: KS is very powerful at these sample sizes, and a distance of 0.031 over
5,000 tail observations is modest in absolute terms. No real distribution is exactly Pareto,
and a large-n rejection is close to guaranteed. But the rejection is unambiguous, and 0.93 can
no longer be presented as "the Pareto exponent".

## What this forces

**Retracted.** EXP-018's reading that "the fitted tail is heavy enough that the sample mean is
not a stable statistic" rested on α < 1 **inside a Pareto model** — the model the data rejects.
That framing is withdrawn.

**What stands:**

- **α ≈ 0.93 as an empirical tail-heaviness summary** — robust to window width, and to the
  bootstrap once it is done correctly.
- **α < 1**, but narrowly, once uncertainty is estimated by subsampling rather than asymptotics.
- **The episode/fill gap (0.93 vs 3.07)** — and this is the most robust result of the three,
  because it compares two curves computed identically on the same data. It rests on no
  parametric assumption, so rejecting Pareto does not touch it.

The core finding survives; its parametric dressing does not.

## Limits

- Subsampling rate m was not chosen by a rule (n/4 and n/16 are illustrative). A principled
  choice would give one interval rather than a range of them.
- GoF was tested only against Pareto. What the tail *is* — lognormal-with-heavy-body, stretched
  exponential, a mixture — is untested, and the answer would change how the number should be
  described.
- Majors only. HIP-3 has no plateau to check.

## Next

1. Fit alternatives (lognormal, stretched exponential, Pareto with cutoff) and compare by
   likelihood ratio — the Clauset-Shalizi-Newman procedure, of which this ran only the first
   half.
2. A rule-based subsampling rate.
3. Restate the headline in EXP-016/017/018 in non-parametric terms, since that is what the data
   supports.
