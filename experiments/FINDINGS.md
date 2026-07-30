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

Estimator: Hayashi-Yoshida, grid-free, validated to zero error against known lags (EXP-010)
**and re-validated at Hyperliquid's own observation density (EXP-026)**: impose a lag of zero,
thin the follower to HL's real print times, and the estimator returns zero — exactly, in every
hour, on BTC, ETH and HYPE, and within 25 ms on the sparsest instrument. The lag is not
manufactured by unequal observation rates.

**The sparsity caveat is closed (EXP-027, EXP-028).** Thinning Binance to HL's cadence moves the
measured peak up (+25 ms on the densest asset, +212 on the sparsest), and across assets
ρ(trade frequency, lag) = −0.656 — both the signature of a density effect on the magnitude. Three
candidate mechanisms were pre-registered and tested on 92 asset-hours, and none survives:

| mechanism | verdict | basis |
|---|---|---|
| independent follower innovations | **excluded** | structural — a cross-covariance is blind to them at every lag |
| follower observation density | **excluded** | bias flat from 0.5× HL's cadence to Binance's full density |
| endogenous sampling times | **excluded** | zero shift under a *maximally* price-coupled sampler |

With no estimator-side explanation left, the cross-asset association is attributed to market
structure — sparser instruments really are slower — and **575 ms stands unqualified on the
sparsity axis.**

**Still unexplained, on a different measurement:** no synthetic pair reproduces the leader-thinning
inflation (EXP-027 P5). But that manipulation degrades the *leader*, which Result 1 never does.

**Deliberately left open, with a trigger — decided 2026-07-28.** P5 is a question about a model,
and the exclusion that matters most (independent noise) rests on algebra rather than on that
model. Test C's quote capture started the same day and attacks the same question with a different
instrument, so a fourth synthetic robustness check would be work on the wrong object — and past
some point, insistence reads as motivated rather than rigorous. It stands as a limitation in the
paper, stated plainly.

**Reopen if Test C disagrees** — if quotes give a magnitude materially different from 575 ms.
The model's failure would then stop being a loose end and become a lead, since the two anomalies
would likely share a cause. The diagnostic to run at that point is *the shape of the HY curve*,
real pair against synthetic: if the real lag is a **distribution** where the synthetic has a sharp
peak, that explains P5 in one plot, and "median 575 ms" and "a lag distribution centred on 575 ms"
are not the same claim. Worth more with quotes in hand than on trades alone. Enough quote data to
judge: on or after **2026-08-11**.

**New, from EXP-028 Part 1 — the two venues run on different clocks.** Binance prints markedly
more when the market moves (Spearman with |return| +0.28 to +0.77); Hyperliquid barely does
(+0.06 to +0.17). Its quotes update ~7.9×/s on BTC, about once per block, so its trade arrival
looks gated by block production rather than by price events. Consistent with two measurements,
not yet tested directly.
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

Everything below is year-scale — the 1,460-hour stratified sample: **351,648 episodes,
1,005,157 fills**, 380 instruments, 151,775 accounts, **$7.77bn** notional. Collected with the
`event[0] == liquidatedUser` filter; see the correction notice in EXP-016/017/024 for why the
earlier figures were exactly twice these.

| | |
|---|---|
| fills per liquidation | **median 1**, mean **2.86×** (day-resampled 95% CI [2.72, 3.00]) |
| robustness of that factor | 1.9× across six different definitions of "one liquidation" *(12 h)*; every definition returns the same episode counts, so the unit is not doing the work |
| tranching vs size | **median 1 fill below the 90th percentile**, 4 in p90–99, **36** in the top 1% (mean 66, max 2,388) |
| share of fills from the top 1% of episodes | **23.1%** |
| concentration | top 1% of **episodes** carry **67.3%** of liquidated notional; top 5% carry 85.6%, top 10% carry 92.6% |
| corr(ln notional, ln fills) | **+0.545** (Pearson of logs; Spearman rank +0.468) |

**The bias is the size, not a multiplier on top of it.** A liquidation below the 90th percentile
is a *single fill* and is counted exactly right. All of the inflation comes from the largest
decile:

| size bucket | episodes | median fills | mean fills |
|---|---|---|---|
| p0–50 ($0 – $558) | 175,824 | **1** | 1.10 |
| p50–90 ($558 – $19,644) | 140,659 | **1** | 1.97 |
| p90–99 ($19,644 – $274,461) | 31,648 | 4 | 9.55 |
| **p99–100** ($274,461 – $97,057,547) | 3,517 | **36** | 66.13 |

**Size distribution compression**, quantile by quantile against true episode sizes (not
modelled), bootstrap 95% CI:

| quantile | episode | fill | factor | 95% CI |
|---|---|---|---|---|
| p50 | $558 | $558 | **1.00** | [0.99, 1.01] |
| p90 | $19,644 | $12,046 | **1.63** | [1.60, 1.66] |
| p99 | $274,461 | $119,919 | **2.29** | [2.21, 2.39] |
| p99.9 | $2,917,253 | $582,474 | **5.01** | [4.62, 5.62] |

The p50 factor is **1.00 with a CI of [0.99, 1.01]** — at the median the fill record is not
distorted at all, measured rather than assumed.

Largest episode by notional **$97,057,547** (BTC, 1,284 fills); most-tranched episode **2,388
fills** ($16.2M, ZEC); largest single fill **$10,990,000**.

**Majors and HIP-3 share a tail *index* (EXP-017) but not compression (EXP-024).** Majors
compress more in the body (ratio 1.30 at p90), HIP-3 more in the tail (0.82 at p99), crossing
over between them. Compression is produced by slicing a position against a book, and HIP-3 books
are thinner; a tail index is a property of the liquidation mechanism. Majors run 2.89× against
HIP-3's 2.72×, carrying 90.7% of notional against 9.3%.

**The protocol's own chunking does not explain any of this.** Hyperliquid sends 20% of a
position above $100k as the first market order, then waits 30 s. Of 98,983 consecutive
same-account-same-instrument episode pairs, 94.7% are more than ten minutes apart — unrelated
events. Merging every chain within 90 s touches 1.4% of episodes and moves the factor by less
than 0.05. Chains are strongly size-selected, but their gap distribution decays monotonically
from the 5 s floor with **no 30 s mode**, so the size selection is consistent with the cooldown
without identifying it. Tranche identification needs position accounting, not elapsed time —
EXP-025.

→ EXP-016, EXP-017, EXP-024

### 3. The liquidation size tail is heavy, and it is not a power law

Exponential is rejected decisively, so the tail is genuinely heavy. **Lognormal and Weibull
both beat Pareto**, and a KS test with parametric-bootstrap p-values rejects Pareto at every
threshold tried (p ≤ 0.01).

**Threshold-independent (EXP-022).** EXP-020 established this at one hand-fixed cut-off and
listed the arbitrariness as a limit. Selecting `xmin` by minimising KS gives **$280,314** — the bootstrap 95% CI is [$97k, $496k] — and
the ranking holds at **all 14 estimable thresholds**, `xmin` from $7.5k to $4.42M — nearly
three orders of magnitude, individually significant at 13 of the 14 (p = 0.07 at the highest
cut-off).

**But the tail cannot be named**, and this is the closed form of what used to be open item 2.
Lognormal and Weibull *do* separate — they simply separate in **opposite directions** depending
on where the tail is cut: Weibull for `xmin` ∈ [$100k, $663k] (p < 0.01), lognormal decisively
for `xmin` ≤ $14k (R > +13). Any name given to this tail would report the threshold, not the
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
   narrower — over `xmin` ∈ [$25k, $81k] **no candidate fits**. The Weibull pins at a numerical
   bound and the lognormal drifts to extreme parameters (both toward the power-law limit of
   their own family), and a direct GoF test rejects every fitted candidate in the band
   (parametric-bootstrap KS, p ≤ 0.01) while KS rejects the power law itself. A fifth family
   (generalised Pareto, log-gamma) might cover that band; none was tried.
   **Pre-registered as EXP-029 (2026-07-29), and urgent rather than merely open**: the paper in
   SSRN's approval queue states "cannot be named" in its abstract and twice in its body, so a
   submitted claim rests on four families with the named fifth candidate never run. If a *fully
   parametric* family (log-gamma, Burr XII, generalised gamma) fits the band interior, the
   wording is corrected in the revision before the paper is public. A generalised Pareto fitting
   would **not** count: Pickands–Balkema–de Haan makes convergence to a GPD the generic outcome
   for exceedances, so it names nothing about liquidations.
3. **Venue decoupling during cascades** — coupling roughly halves (EXP-015), on 8 windows. Needs
   many more, and a bounded coupling statistic.
4. **The premium-sign regime flip** — measured, then explained by the market cycle (r = 0.786).
   Whether a residual survives the cycle is untested at daily frequency.
5. ~~Whether the lag holds on the hours the coverage filter removed~~ — **closed by EXP-021.**
   It holds, on all 47 of them, and the filter turned out not to be selective.

---

### The liquidation tranching mechanism (EXP-025)

Hyperliquid documents closing positions above $100k in 20% chunks with a 30-second cooldown.
**The chunking is real and recoverable; the cooldown is not observable.**

Tranche boundaries are an arithmetic fact of position accounting, not of elapsed time: 70.8% of
pauses inside a forced close fall within ±0.02 of a multiple of 0.2, against 16.3% under a
uniform null. But among 7,963 multi-tranche closes above $100k, the median gap between tranche
boundaries is **0.0 s** and 75% are under two seconds — boundaries are crossed inside a
continuous sweep, not after a wait.

**Not claimed:** closes with a real gap (≥ 25 s) show +79.9 bps of adverse movement against
+24.7 for continuous ones. That difference is **selection, not anticipation** — a second tranche
is sent only if the account is still under margin, so the gap exists precisely when price moved
against it. The pre-registered discriminator settles it: gapped closes revert *less* than
continuous ones (0.61 vs 0.76 of their move, Mann-Whitney p = 0.971), so the extra movement is
permanent, hence information rather than temporary pressure.

→ EXP-025

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
11. **Reviews audit the analysis; nobody audits the collection.** Everything downstream
    inherits a collector's assumptions silently, so a bug there is invisible to any check
    made on derived data. Two adversarial reviews recomputed eight headline figures from
    the CSVs, flawlessly, with no chance of finding the error that was upstream of them.
    What caught it was needing a new column and having to go back to the source.
12. **"That data does not exist" is a claim about code — go read the code.** Said from memory
    twice. Once it was wrong outright (EXP-025: the liquidation collector was said to have kept
    prices; it discarded them). Once the verdict held but the reason was wrong (EXP-026: BBO was
    said to be unrecorded because "the recorder subscribes to `trades` only" — it also records
    books; the real obstacles are a 2 s write-side thinning and, decisively, Binance's fixed
    500 ms depth grid). A wrong reason is not a harmless slip: it points the next experiment at
    the wrong fix. Here it hid that the answer is two `bbo` subscriptions, not a new recorder.

13. **A denominator is infrastructure — one hour of it poisons everything downstream.** Twice now
    a daily figure has been extrapolated from a single hour (storage projections, then venue
    maker volume), and the second time the hour happened to be the day's peak: 14:00 UTC at
    \$1,012M against a \$152M trough, 6.6× apart. The first error was embarrassing and local.
    The second sat in a *denominator*, so it silently scaled the thresholds in two later
    experiments and made a business look 5.1× harder to enter than it is
    (`hyperliquid-alpha` EXP-A007). Sample a rate across the cycle before dividing anything by it.

14. **A saturating mean is not a usable estimator — pick the horizon on signal-to-noise.**
    A markout was quoted at 30 s because that is where the mean stopped growing, and two
    experiments built economics on it. Over 26 hours its between-hour standard deviation is
    0.224 bps against a mean of 0.272, and the hourly value changes sign — because at that
    horizon the statistic is mostly measuring where the market went, not what the fill cost.
    Variance grew four-fold from 100 ms to 30 s while the mean grew less than twice.
    (`hyperliquid-alpha` EXP-A009, correcting A004 and A008.) Where a mean stabilises and
    where it can be measured are different questions, and only the second licenses a conclusion.

15. **A markout is not a P&L — and when the realised quantity is in the data, read it before
    modelling it.** Six experiments modelled market-maker revenue as `rebate − markout` and got
    +0.028 bps a fill. The fills carried `closedPnl` the whole time; it says +0.9 bps, a factor
    of thirty. A markout prices a position as if closed **at the mid, at a time the analyst
    picks**, so it omits the second half-spread a passive exit captures and ignores that fills
    sit across a ladder. It measures adverse selection, which is real and useful, and it is not
    revenue. (`hyperliquid-alpha` EXP-A012/A013, invalidating the economics of A007, A008 and
    A010.) The related trap: those markouts were also **equal-weighted per fill** while P&L is
    weighted by notional — and the smallest fifth of fills carried 0.1% of the money against the
    largest fifth's 91%, which alone flipped the sign.

16. **A diagnostic that cannot rank is not a diagnostic.** Rule 15 said a markout is not a P&L.
    Worse: across 139 market-making books, the cross-sectional correlation between markout and
    realised P&L is −0.024 at τ=0 and never exceeds 0.07 in magnitude out to 30 s. Given two
    books and their complete markout curves you cannot tell which one makes money — 99% of the
    difference happens later. (`hyperliquid-alpha` EXP-A016.) Before building on a statistic,
    check it separates the outcomes you care about; a quantity everyone agrees is standard can
    still be orthogonal to the question.
17. **Skip one bar before believing any thin-book reversal.** Across 174 instruments, minute
    reversal measured against last-trade prints shows median daily ICs of 0.33 (most liquid
    quartile) to 0.50 (least liquid) — and 99% of it vanishes when the target skips the
    adjacent bar (0.006–0.007 residue; individual cases: IC +0.632 → +0.032, one sign flip).
    Bid–ask bounce grows with spread, so the mirage is largest exactly where "neglected asset"
    stories want to look. (`hyperliquid-alpha` EXP-A022, which also measured the neglect
    hypothesis itself dead: response rates flat across a 70× liquidity gradient.)
