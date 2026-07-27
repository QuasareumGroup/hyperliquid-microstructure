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
**758 asset-hours** across BTC/ETH/SOL/HYPE, with **zero reversals**. The same estimator returns
**25 ms** between OKX and Binance, a factor of 23.

Per asset (EXP-023, tape-derived coverage): BTC 575 ms, ETH 550, HYPE 550, SOL 650.

Survives: trade sparsity (EXP-014), liquidation cascades (EXP-015), and every asset the recorder
covers (EXP-012, EXP-023). The CEX do not lead one another (EXP-007), which is what makes it
Hyperliquid's property rather than Binance's.

**Volatility: no material dependence, but not literal invariance (EXP-023).** The invariance was
established on BTC (EXP-009, EXP-011) and reconfirmed there (EXP-021, ρ = −0.099; EXP-023
partial −0.044, p = 0.55). It was never tested hour-by-hour on the other three, and on those the
marginal association runs −0.18 to −0.35. Pooled over 758 asset-hours, holding trade frequency
constant, **ρ(range, peak) = −0.100, p = 0.006** — higher volatility, marginally shorter lag. An
effect explaining 1% of variance does not move a 575 ms median, so the result stands; the word
"invariant" does not.

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

Everything below is year-scale — the 1,460-hour stratified sample: 351,540 episodes,
2,010,042 fills, 380 instruments, 151,730 accounts, $15.53bn notional. Per-fill notionals come
from a second pass over the same hours (EXP-024), which reproduces every count statistic here to
three decimal places. The two rows still marked *(12 h)* are checks that were only ever run on
the smaller sample; neither is load-bearing.

| | |
|---|---|
| fills per liquidation | median 2, mean **5.72×** (day-resampled 95% CI [5.47, 5.99]) over a fixed-hour archive year |
| robustness of that factor | 3.7–3.8× across six different definitions of "one liquidation" *(12 h)*; the choice of unit is not doing the work |
| tranching vs size | median 2 fills below the median episode, **72** in the top 1% (mean 132, max 4,776) |
| share of fills from the top 1% of episodes | **23.1%** |
| concentration | top 1% of **episodes** carry **67.3%** of liquidated notional; top 5% carry 85.6%, top 10% carry 92.6% |
| | *(12 h, by fill: top 1% of fills carry 30.7%, top 10% carry 76.6%)* |
| corr(ln notional, ln fills) | **+0.545** (Pearson of logs; Spearman rank +0.468) |

**The protocol's own chunking does not undo this.** Hyperliquid sends only 20% of a position
above 100,000 USDC as the first market order, then waits **30 s** before sending more. One forced
close can therefore span several transactions, which the `(account, transaction)` unit would
split. Measured: of 98,983 consecutive same-account-same-instrument episode pairs, none are
under 5 s apart (empty **by construction** of the 5-second episode unit), 1.8% fall in 5–35 s, and **94.7% are more than 10 minutes apart** — unrelated
events, not chunks. Merging every chain within 90 s touches 1.4% of episodes and moves the factor
from 5.72× to **5.76×**, so the reported figure is mildly conservative. Chains are strongly size-selected —
median **$72,326** against **$1,083** for episodes outside any chain (factor 67), against a
$100k threshold — but that **does not identify the cooldown**: their gap distribution decays
monotonically from the 5 s floor (median 17.9 s, only 6% in [25, 40] s), with no 30 s mode even
on chains above $1M. Size selection is consistent with the rule; the timing is not evidence for
it. Identifying tranches needs position accounting, not elapsed time — see EXP-025. *(An earlier $1,902 figure used an undeclared
subset — accounts with a second episode in the year; caught in review.)*

**Size distribution compression**, measured quantile by quantile against true episode sizes
(not modelled). **Year scale since EXP-024** — 2,010,314 fills, bootstrap 95% CI:

| quantile | episode | fill | factor | 95% CI | *(12 h)* |
|---|---|---|---|---|---|
| p50 | $1,117 | $558 | **2.00** | [1.97, 2.03] | *1.6* |
| p90 | $39,288 | $12,046 | **3.26** | [3.21, 3.31] | *2.1* |
| p99 | $548,922 | $119,919 | **4.58** | [4.41, 4.76] | *3.4* |
| p99.9 | $5,834,505 | $582,486 | **10.02** | [9.24, 11.21] | *10.9* |

Compression is **stronger than the 12-hour sample showed** at p50, p90 and p99, with intervals
excluding the old value at each — the same direction the count inflation moved (3.8× → 5.72×)
when the cascade-selected hours were removed. At p99.9 the two are indistinguishable.

Largest episode by notional **$194,115,094** (BTC, **2,568 fills**); most-tranched episode
**4,776 fills** ($32.4M, ZEC); largest single fill **$10,990,000**. *(An earlier version
conflated the two maxima into one episode — caught in review.)*

**Majors and HIP-3 behave identically on tail *index* (EXP-017) but not on compression
(EXP-024).** Majors compress more in the body (ratio 1.30 at p90, CI [1.24, 1.36]), HIP-3 more in
the tail (0.82 at p99, CI [0.74, 0.90]), crossing over between them. No contradiction: the tail
index is a property of the liquidation mechanism, while compression is produced by slicing a
position against a book, and HIP-3 books are thinner. The mechanism claim stands; "identical on
every measure" does not.

→ EXP-016, EXP-017, EXP-024

### 3. The liquidation size tail is heavy, and it is not a power law

Exponential is rejected decisively, so the tail is genuinely heavy. **Lognormal and Weibull
both beat Pareto**, and a KS test with parametric-bootstrap p-values rejects Pareto at every
threshold tried (p ≤ 0.01).

**Threshold-independent (EXP-022).** EXP-020 established this at one hand-fixed cut-off and
listed the arbitrariness as a limit. Selecting `xmin` by minimising KS gives $560,627 — within
a factor 1.79 of the hand choice, which sits inside the bootstrap 95% CI [$194k, $987k] — and
the ranking holds at **all 14 estimable thresholds**, `xmin` from $14.9k to $8.85M — nearly
three orders of magnitude, individually significant at 13 of the 14 (p = 0.07 at the highest
cut-off).

**But the tail cannot be named**, and this is the closed form of what used to be open item 2.
Lognormal and Weibull *do* separate — they simply separate in **opposite directions** depending
on where the tail is cut: Weibull for `xmin` ∈ [$199k, $1.33M] (p < 0.01), lognormal decisively
for `xmin` ≤ $28k (R > +13). Any name given to this tail would report the threshold, not the
distribution.

**Pareto-with-cutoff wins at the selected `xmin` and only there** — best likelihood of the five,
beating both alternatives (p = 0.005 and 0.012) — but across the grid it wins at 2 of 14
thresholds and loses decisively at the two lowest. A local result, recorded as such.

→ EXP-019, EXP-020, EXP-022

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
| "majors and HIP-3 behave identically on every measure tested" (EXP-017) | True of the tail index, false of size compression: the segments differ at p50, p90 and p99 and cross over between p90 and p99 (EXP-024). The mechanism reading survives; the universal quantifier does not. |

**The episode-versus-fill comparison is unaffected by any of this.** It contrasts two curves
computed identically on the same data and assumes no parametric form — which is why it is the
only headline that survived the day without correction.

---

## Open

1. **The mechanical/informational split** in the 550 ms. Needs an instrument that sees order
   *submission*, not execution — none of the current ones do.
   **One route now closed (EXP-023).** EXP-012 proposed quantifying the observability
   component by regressing the lag on trade frequency *within* each asset. Done, on 758
   asset-hours: the cross-asset correlation is −0.656, the within-asset partial is **−0.090**
   (p = 0.014), sitting beside a volatility partial of the same size. Observability operates
   between instruments and barely within one, so this route quantifies nothing. Measured rather
   than assumed, which is the only progress available here.
2. ~~What the liquidation tail actually is~~ — **closed by EXP-022, negatively.** `xmin` is now
   selected rather than assumed, and the answer is that no name is available: the winner between
   lognormal and Weibull reverses across the threshold range. What remains genuinely open is
   narrower — over `xmin` ∈ [$49k, $163k] **no candidate fits**. The Weibull pins at a numerical
   bound and the lognormal drifts to extreme parameters (both toward the power-law limit of
   their own family), and a direct GoF test rejects every fitted candidate in the band
   (parametric-bootstrap KS, p ≤ 0.01) while KS rejects the power law itself. A fifth family
   (generalised Pareto, log-gamma) might cover that band; none was tried.
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
10. **A ranking always returns a winner — check the winner actually fits.** Model comparison is
    relative and cannot say "none of these". (EXP-022: over a band of thresholds both
    alternatives sat on a parameter bound, degenerate, while the reference they were being
    compared against was itself rejected.)
