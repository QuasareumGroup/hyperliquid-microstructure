# State of claims

What this repo currently supports, what it has withdrawn, and what is open. Written after
EXP-020 showed that several headline numbers rested on a parametric assumption the data
rejects. **Claims are stated non-parametrically wherever the data only supports that.**

Read this before any individual experiment file. Each of those carries its own corrections
in place, but they are a running record — this is the current position.

---

## Established

### 1. Hyperliquid follows the CEX market by ~550 ms

Binance leads Hyperliquid by a **median 575 ms** (bootstrap 95% CI on the median [550, 575];
mean 607) on BTC, **in 100% of 191 measured hours — every hour in the window** — and in 100% of
576 asset-hours across BTC/ETH/SOL/HYPE. The same estimator returns **25 ms** between OKX and
Binance, a factor of 23.

Survives: volatility regimes (EXP-009, EXP-011), trade sparsity (EXP-014), liquidation cascades
(EXP-015), and every asset the recorder covers (EXP-012). The CEX do not lead one another
(EXP-007), which is what makes it Hyperliquid's property rather than Binance's.

Estimator: Hayashi-Yoshida, grid-free, validated to zero error against known lags (EXP-010).
**Open:** how much is mechanical (block cadence, network) versus price discovery. Observability
is ruled out as the explanation for the *level* (EXP-014); nothing has replaced it.

**Sample selection — checked and closed (EXP-021).** EXP-011 measured 144 of the window's 193
hours; the rest were dropped by perplog's `gapped` flag, later found to fire on reconnects
rather than on real recording holes. Re-deriving completeness **from the tape** — a venue was
down only if another venue kept printing through its silence — shows **95.9% of flagged hours
were complete**, and that the flag is uncorrelated with market activity (Spearman +0.034 with
volatility, −0.015 with event count; Mann-Whitney p = 0.635). The dropped hours were therefore
an unbiased subset, and all 191 complete hours now measure **575 ms, 100%**, over a volatility
range 38% wider at the top (max `range_bps` 135.9 → 187.8).

→ EXP-005 – EXP-015, EXP-021

### 2. Counting liquidation fills misrepresents liquidations

All of the following are **counting facts**. No distributional assumption enters.

| | |
|---|---|
| fills per liquidation | median 2, mean **5.72×** over an unbiased archive year |
| robustness of that factor | 3.7–3.8× across six different definitions of "one liquidation" on the 12-hour sample; the choice of unit is not doing the work |
| tranching vs size | median 2 fills below the median episode, **41** in the top 1% |
| share of fills from the top 1% of episodes | **18%** |
| concentration | top 1% of fills carry **30.7%** of liquidated notional; top 10% carry 76.6% |

**Size distribution compression**, measured quantile by quantile against true episode sizes
(not modelled):

| quantile | episode | fill | factor |
|---|---|---|---|
| p50 | $661 | $424 | 1.6× |
| p90 | $18,259 | $8,842 | 2.1× |
| p99 | $214,474 | $63,812 | **3.4×** |
| p99.9 | $1,969,302 | $180,161 | **10.9×** |

Largest real episode **$3.84M**; largest single fill **$899k**.

**Majors and HIP-3 behave identically** on every measure tested (EXP-017) — this is a property
of the liquidation mechanism, not of the market.

→ EXP-016, EXP-017

### 3. The liquidation size tail is heavy, and it is not a power law

Exponential is rejected decisively (Vuong R = +14.8 against Pareto), so the tail is genuinely
heavy. But **lognormal and Weibull both beat Pareto** (R = −4.8 and −5.0, p < 0.001) and are
indistinguishable from each other. A KS test with parametric-bootstrap p-values rejects Pareto
at every threshold tried (p ≤ 0.01).

→ EXP-019, EXP-020

---

## Withdrawn

| claim | why |
|---|---|
| "tail index α ≈ 1.15", later 0.93 | Hill estimates a Pareto exponent; the tail is not Pareto (EXP-019/020). The number is what Hill returns on a lognormal-ish tail, not a parameter. |
| "infinite variance", "the mean is not a stable statistic" | Both are properties of a fitted Pareto with α < 2 or < 1. The fit is rejected. |
| "the Hill index is not stable in k" (EXP-017) | Right observation, wrong reason — restored by EXP-020: drift with k is the **known signature of a lognormal tail**, not a measurement defect. |
| "the plateau sits at α ≈ 0.93" (EXP-018) | The plateau is a real property of the estimator and empty as an estimate. |
| "Hyperliquid's lag widens under stress" (EXP-008) | Artefact of the sampling grid; the partial correlation controlling for grid step is −0.001 (EXP-009). |
| "the deadband is a novel finding" (FINDING-001) | Published algebra; the control-system framing was also already in the literature. |
| "the gap filter biased the sample toward active hours" (EXP-021 §1) | A mechanism argued from how `missed_ms` is computed, never measured. The flag is uncorrelated with activity on both volatility and event count (EXP-021). It was noise, not bias. |

**The episode-versus-fill comparison is unaffected by any of this.** It contrasts two curves
computed identically on the same data and assumes no parametric form — which is why it is the
only headline that survived the day without correction.

---

## Open

1. **The mechanical/informational split** in the 550 ms. Needs an instrument that sees order
   *submission*, not execution — none of the current ones do.
2. **What the liquidation tail actually is.** Lognormal and Weibull are not separated; xmin was
   fixed by hand rather than selected.
3. **Venue decoupling during cascades** — coupling roughly halves (EXP-015), on 8 windows. Needs
   many more, and a bounded coupling statistic.
4. **The premium-sign regime flip** — measured, then explained by the market cycle (r = 0.786).
   Whether a residual survives the cycle is untested at daily frequency.
5. ~~Whether the lag holds on the hours the coverage filter removed~~ — **closed by EXP-021.**
   It holds, on all 47 of them, and the filter turned out not to be selective.

---

## Method rules earned here

Each cost a real error, and each is recorded where it was paid.

1. **Test the boring confound first.** (EXP-003 — a day spent on the market cycle.)
2. **Read R² before t.** In a large panel the p-value measures sample size. (EXP-003: t = −18.5, R² = 0.05.)
3. **An implausible n means the bug is upstream of the filter.** (EXP-005: a binning that never binned.)
4. **A caveat listed is not a confound controlled.** (EXP-009: an unquantified hedge concealed a wholly artefactual result.)
5. **Validate an estimator against a known answer, sign included.** (EXP-010: a sign inversion that would have read as "Hyperliquid leads".)
6. **Check what a grouping key means before grouping by it.** (EXP-015/016: `hash` is a transaction, not a liquidation.)
7. **Look at the values under a summary statistic.** (EXP-018: a "plateau" that was a monotone decline.)
8. **A fit on its constraint boundary is not a result.** (EXP-020: `pareto_cutoff` at α = 0.01.)
9. **A mechanism read off the code is a hypothesis, not a measured effect.** Knowing *why* a
   filter should bias a sample is not evidence that it did. (EXP-021: the bias was argued from
   `missed_ms = now − last_event`, sounded compelling, and measured to zero.)
