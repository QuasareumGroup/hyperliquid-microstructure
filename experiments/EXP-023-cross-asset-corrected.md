# EXP-023 — Cross-asset lead-lag on corrected coverage, and the within-asset regression

**Status:** run. **P1, P2, P3 confirmed — the venue constant now rests on 758 asset-hours
with zero reversals. P4 rejected.** The observability relation is an order of magnitude
weaker within an instrument (ρ ≈ −0.09) than between instruments (−0.656), and it does
not deliver the decomposition EXP-012 hoped for. A second finding arrived unasked:
**volatility invariance is not literal.**
**Registered:** 2026-07-27 · **Run:** 2026-07-27
**Author:** Thomas Erhel / Quasareum
**Scripts:** `experiments/exp021_recovered_hours.py --coin {ETH,SOL,HYPE}`,
`experiments/exp023_analyse.py`
**Data:** perplog tape, 2026-07-18 → 07-26, venues `hl / binance / okx`.
Outputs: `experiments/data/exp023_{ETH,SOL,HYPE}.csv`, BTC reused from `exp021_hours.csv`.

> **Current position: [FINDINGS.md](FINDINGS.md).** This file keeps its original
> pre-registration wording plus results; the state of claims lives there.

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets
> reported.

---

## 1. Why

[EXP-012](EXP-012-cross-asset.md) established the 550–575 ms lag as a venue constant on
576 asset-hours. It ran on hours selected by perplog's `gapped` coverage flag, which
[EXP-021](EXP-021-recovered-quiet-hours.md) showed to be **95.9% false positives** on BTC
over the same window. Re-deriving completeness from the tape took BTC from 144 usable
hours to 191, with the headline unchanged.

ETH, SOL and HYPE were never re-derived. This does that, and then runs the test EXP-012
listed as its own Next item 1.

## 2. Part A — the cross-asset table, corrected

Run `exp021_recovered_hours.py` on ETH, SOL and HYPE: fetch every hour in the window
regardless of flag, classify completeness from the tape by the cross-venue criterion
(a venue was down only if another kept printing through its silence), and run the same
Hayashi-Yoshida scan. BTC is reused from EXP-021.

This is confirmatory, not exploratory — the instrument and the estimator are unchanged,
only the hour selection is fixed.

## 3. Part B — the within-asset regression

EXP-012 found, across **four points**:

```
corr( ln(HL trades/h), median peak ) = −0.630
```

and called it a hypothesis rather than a result, correctly. The less an asset trades on
Hyperliquid, the longer its measured lag — which is what **observability** predicts, and
would be the first purchase on the mechanical/informational decomposition that has been
stuck since EXP-010.

The test EXP-012 named: regress τ on trade frequency **hour by hour within each asset**,
where there are ~190 points per asset instead of 4 across all of them.

**One tension, registered before running.** EXP-021 measured Spearman(`range_bps`, peak)
= **−0.099** over 191 BTC hours — the lag is invariant to volatility. Hourly trade count
and hourly range are strongly correlated. If the lag is invariant to one, it is likely
invariant to the other, and P4 below will fail.

That would not make the cross-asset correlation wrong. It would make it a **between**-
instrument effect that does not reproduce **within** an instrument — the standard shape
of an ecological correlation, and physically coherent: observability would depend on an
instrument's *structural* print rate, not on whether a given hour happened to be busy.
Both outcomes are informative, which is why the prediction is worth making either way.

## 4. Predictions

- **P1.** Each of ETH, SOL and HYPE gains usable hours, ending between 180 and 193 —
  matching BTC's 191, since the flag is uncorrelated with anything asset-specific.
- **P2.** The cross-asset ranking is unchanged: BTC, ETH and HYPE within 500–650 ms,
  SOL highest.
- **P3.** τ > 0 in **100%** of corrected asset-hours, as in all 576 before.
- **P4 (load-bearing).** Within each asset, Spearman(ln(hourly HL trades), peak) is
  **negative and significant** (p < 0.05) — the observability relation reproduces inside
  an instrument.

## 5. Falsification

- **P4 false** — no within-asset relation. The −0.630 was four points in a line. The
  observability lead is withdrawn as a route to the decomposition, and the honest
  restatement is that it operates between instruments and not within one. **This is the
  outcome the tension in §3 predicts, and it must not be softened if it arrives.**
- **P3 false** — a single reversal anywhere. That is a bigger event than anything else
  here: 576 asset-hours without a counterexample is the strongest form of the claim, and
  one reversal on corrected data would make it a tendency rather than a property.
- **P2 false** — an asset moves out of its band once its quiet hours are restored. Then
  the venue-constant reading narrows to the hours the old filter happened to keep.
- **P1 false** — an asset gains nothing. Then the flag *was* asset-specific and EXP-021's
  conclusion that it is noise needs qualifying beyond BTC.

## 6. Success criterion

Part A succeeds by producing a cross-asset table on hour selection that is defensible,
whatever it says. Part B succeeds by **settling whether observability is measurable
within an instrument** — a negative answer closes a lead that has been quoted as
promising since EXP-012, and closing it is worth as much as confirming it.

## 7. Results — Part A

| asset | hours | was | median | mean | 95% CI | σ | τ>0 | ρ | OKX |
|---|---|---|---|---|---|---|---|---|---|
| BTC | **191** | 144 | 575 ms | 607 | [550, 575] | 152 | **100%** | 0.591 | 25 ms |
| ETH | **191** | 144 | 550 ms | 582 | [550, 575] | 126 | **100%** | 0.819 | 25 ms |
| SOL | **185** | 144 | 650 ms | 742 | [625, 675] | 257 | **100%** | 0.339 | 0 ms |
| HYPE | **191** | 144 | 550 ms | 555 | [550, 550] | 120 | **100%** | 0.886 | 25 ms |

**758 asset-hours, zero reversals.** EXP-012 had 576.

Medians move by 0 ms on BTC, ETH and HYPE, and by +12 ms on SOL. **P1, P2 and P3 all
confirmed**, and P3 is the one that matters: the strongest form of the claim — no
counterexample anywhere — now rests on 32% more observations, on hour selection derived
from the tape rather than from a flag known to be 96% false positives.

**A measurement correction, not a market change.** EXP-012's "HL trades/h" column
reported Hayashi-Yoshida *returns*, not raw tape events. The first version of this
analysis used raw events and showed BTC at 10,869/h against EXP-012's 4,870 — a
doubling that would have looked like a market change and was a definitional difference.
Raw events run 2.11× higher because Hyperliquid stamps a whole block at one millisecond.
`nret_hl_binance` was verified byte-identical to EXP-011's column, and the corrected
figures are used throughout. **The observability hypothesis is about how often HL's
price refreshes, so returns are also the correct regressor**, not merely the comparable
one — a block of forty fills at one timestamp is one price observation.

## 8. Results — Part B: observability within an asset

**Marginal**, Spearman(ln HY returns, peak) hour by hour:

| asset | n | ρ(returns, peak) | p | ρ(range, peak) | p |
|---|---|---|---|---|---|
| BTC | 191 | −0.090 | 0.213 | −0.096 | 0.185 |
| ETH | 191 | **−0.227** | 0.002 | **−0.223** | 0.002 |
| SOL | 185 | **−0.300** | 0.000 | **−0.348** | 0.000 |
| HYPE | 191 | **−0.197** | 0.006 | **−0.180** | 0.013 |

**P4 rejected** — it required all four, and BTC does not show it.

But the registered falsification clause does not fit either. It anticipated *no*
within-asset relation. Three of four assets show one.

### The confound is real, and it is what decides this

Trade count and hourly range correlate at **0.60–0.74** within each asset. The two
columns above are nearly identical because they are largely the same variable. A raw
correlation with either cannot attribute the relation (method rule 4).

**Partial correlations:**

| asset | returns \| range | p | range \| returns | p |
|---|---|---|---|---|
| BTC | −0.029 | 0.695 | −0.044 | 0.548 |
| ETH | −0.101 | 0.164 | −0.092 | 0.209 |
| SOL | −0.123 | 0.096 | **−0.221** | 0.003 |
| HYPE | −0.103 | 0.158 | −0.065 | 0.374 |

No asset individually reaches significance on trade count once volatility is held.
Fisher's combination of the three non-BTC partials gives **p = 0.063** — not significant.

Pooled over all four assets, each standardised within itself so that between-asset
levels cannot manufacture a within-asset relation (**n = 758**):

| | ρ | p |
|---|---|---|
| marginal, returns vs peak | −0.213 | < 0.0001 |
| **partial, returns \| range** | **−0.090** | **0.0138** |
| **partial, range \| returns** | **−0.100** | **0.0057** |

Non-BTC pooled (n = 567): partial returns \| range = −0.119, p = 0.0045.

### What this settles

**Observability operates between instruments, and barely within one.** The cross-asset
correlation recomputes at **−0.656** on corrected data (was −0.630). The within-asset
partial is **−0.090** — an order of magnitude weaker, detectable only by pooling 758
hours, and explaining under 1% of variance.

That is the ecological-correlation reading registered in §3, and it arrived — not as the
clean zero predicted there, but as *an order of magnitude weaker*, which is the same
conclusion with a number attached. An instrument's **structural** print rate is
associated with its lag; whether a given hour happens to be busy is very nearly not.

**It does not deliver the decomposition.** EXP-012 hoped this regression would quantify
the observability component. At ρ = −0.09, sitting beside a volatility partial of the
same size and opposite claim, it quantifies nothing. The mechanical/informational split
stays open, and this route to it is now measured rather than merely hoped for.

### The finding nobody asked for: volatility invariance is not literal

The pooled partial ρ(range, peak | returns) = **−0.100, p = 0.0057** is as strong as the
trade-count one. Over 758 asset-hours, higher volatility goes with a *slightly shorter*
lag, net of trade frequency.

FINDINGS.md says the result "survives volatility regimes", established on BTC (EXP-009,
EXP-011) and reconfirmed on BTC by EXP-021 at ρ = −0.099. **BTC is the asset where it
holds** — its partial here is −0.044, p = 0.548. It was never tested hour-by-hour on the
other three, and on those the marginal association is −0.18 to −0.35.

The claim survives in magnitude: an effect explaining 1% of variance does not move a
575 ms median. It does not survive as stated. "Invariant" becomes "no material
dependence, with a small detectable residual at n = 758".

## 9. Limits

- Nine days, four assets — the whole recorded universe, but still four.
- Partial Spearman by rank-residual regression assumes the rank relation is roughly
  linear. Not checked.
- Fisher's combination treats the three assets as independent tests. They share the same
  hours and the same market, so the true p is likely larger than 0.063, not smaller.
- The pooled partials survive at p ≈ 0.01 with n = 758. Effects that size are exactly the
  ones that fail to replicate on a different window, and this is one window.
- SOL remains the outlier on every measure and the only asset where volatility survives
  the control. Still the fewest prints, the lowest ρ, the widest σ.
