# EXP-012 — Is 575 ms a Hyperliquid constant or a BTC one?

**Status:** run. **A venue constant.** Three of four assets sit at 550–575 ms, and τ > 0 in
**100% of 576 asset-hours** without a single reversal.
**Date:** 2026-07-26
**Data:** perplog tape, 144 hours × 4 assets, 2026-07-18 → 07-26, venues `hl / binance / okx`.
Outputs: `experiments/data/exp011_hy_{hours,ETH,SOL,HYPE}.csv`.

---

## Scope

The recorder tracks `["BTC", "ETH", "SOL", "HYPE"]` (`heat_capture::COINS`), so this is the
whole available universe, not a sample of it. DOGE and XRP return zero coverage.

**P1** — venue constant: τ similar across assets.
**P2** — instrument-specific: τ varies, probably with liquidity or trade frequency.

## Results

| asset | median | mean | 95% CI | σ | **% τ > 0** | mean ρ | OKX control | HL trades/h |
|---|---|---|---|---|---|---|---|---|
| BTC | 575 ms | 601 | [577, 624] | 145 | **100%** | 0.582 | 25 ms | 4,870 |
| ETH | **550 ms** | 588 | [565, 610] | 135 | **100%** | 0.804 | 25 ms | 2,258 |
| SOL | 638 ms | 736 | [696, 776] | 244 | **100%** | 0.332 | 0 ms | 1,209 |
| HYPE | **550 ms** | 561 | [540, 582] | 127 | **100%** | 0.884 | 25 ms | 2,730 |

**P1 confirmed.** Three of four cluster at 550–575 ms and the OKX control stays at 0–25 ms
throughout.

**No exceptions anywhere.** τ > 0 in every one of 576 asset-hours. A result with zero
counterexamples across 576 independent observations is a property, not a tendency.

**SOL is the apparent outlier and also the noisiest measurement**: σ = 244 against 127–145
elsewhere, ρ = 0.33 against 0.58–0.88, and the fewest HL trades per hour. Read as estimation
noise rather than a genuinely different lag — though not proven to be.

**HYPE is the one worth naming.** 550 ms with the *cleanest* measurement of the four
(ρ = 0.884, σ = 127). It is Hyperliquid's native token: the venue holds its primary spot
liquidity and its oracle uses HL spot rather than external sources. Price discovery still
happens on Binance first, as sharply as on BTC.

## A lead on the open question

```
corr( ln(HL trades/h), median peak ) = −0.630        (n = 4 assets)
```

The less an asset trades on Hyperliquid, the longer the measured lag. That is what
**observability** predicts: with fewer prints, HL's price refreshes less often, so its
information arrives later on average without price discovery being involved.

This would be the first purchase on the mechanical/informational decomposition, stuck since
EXP-010. **But n = 4.** By this repo's own rules that is a hypothesis, not a result.

The test that would settle it: regress τ on trade frequency **hour by hour within each asset**,
where there are 576 points instead of 4. If the relationship holds within assets, the
observability component is real and quantifiable; if it vanishes, the cross-asset pattern was
four points in a line.

## Limits

- Four assets is the entire recorded universe, but still four. A venue constant established on
  four instruments is a weaker claim than the sample size of 576 hours suggests.
- Nine days.
- Total observable lead, as in EXP-011. The decomposition remains open.
- SOL's deviation is attributed to noise on circumstantial grounds (lowest ρ, highest σ, fewest
  trades) rather than demonstrated.

## Next

1. **The within-asset regression above** — cheapest, and the only current path to the
   decomposition.
2. Whether ρ at the peak tracks trade frequency the same way, which would distinguish "noisier
   estimate" from "genuinely weaker coupling" for SOL.
3. Extending the recorder's coin set would widen this test, but that is a perplog change, not a
   research one.
