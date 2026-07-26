# EXP-013 — Is the 550 ms lag just Hyperliquid trading less often?

**Status:** run. **No.** Observability explains part of the *spread between* assets and
**none of the level**. The most obvious mechanical explanation is ruled out.
**Date:** 2026-07-26
**Data:** 576 asset-hours (4 assets × 144 hours) from `experiments/data/exp011_hy_*.csv`.

---

## Question

EXP-012 found `corr(ln HL trades/h, median peak) = −0.630` across four assets: the less an
asset trades on Hyperliquid, the longer the measured lag. That is what **observability**
predicts — a price that refreshes less often carries information later, with no price
discovery involved. With n = 4 it was a hypothesis.

**P1** — the relationship holds within assets: observability is real and quantifiable.
**P2** — it vanishes: the cross-asset pattern was four points in a line.

## Design

Trade frequency and volatility are collinear within an asset (more trades when the market
moves), and EXP-011 found a weak volatility–τ link. Both go in the regression:

```
τ = a + b₁ · mean_inter_trade_interval_ms + b₂ · ln(range_bps)
```

**Quantitative prediction.** If the lag were pure observability, information arriving uniformly
within an inter-trade interval waits half a period on average, so **b₁ ≈ 0.5**.

## Results

| asset | b₁ | s.e. | t | b₂ (vol) | R² |
|---|---|---|---|---|---|
| BTC | **−0.003** | 0.046 | −0.06 | −50.4 | 0.041 |
| ETH | +0.054 | 0.017 | 3.10 | −23.9 | 0.161 |
| SOL | +0.040 | 0.016 | 2.42 | −111.7 | 0.153 |
| HYPE | +0.060 | 0.028 | 2.12 | 0.0 | 0.060 |
| **pooled, asset fixed effects** | **+0.048** | 0.009 | **5.19** | −37.6 | 0.232 |

The relationship **exists** within assets and has the right sign — but at **0.048 against a
predicted 0.5, it is ten times too weak**.

The level check is the harder evidence:

| asset | mean interval | half-interval *(observability prediction)* | **observed τ** |
|---|---|---|---|
| BTC | 739 ms | 370 ms | **575 ms** |
| ETH | 1,595 ms | 797 ms | **550 ms** |
| SOL | 2,977 ms | **1,488 ms** | **638 ms** |
| HYPE | 1,319 ms | 659 ms | **550 ms** |

**SOL's mean interval is 4× BTC's; its τ is 1.1× BTC's.** Pure observability would put SOL near
1,500 ms. And ETH, trading half as often as BTC, should be *slower* — it is faster.

## Conclusion

> Observability contributes to the **spread between** assets. It explains **none of the ~550 ms
> level**. The bulk of the lag is not a consequence of how often Hyperliquid trades.

This is the first real progress on the decomposition since EXP-010. It does not demonstrate
that the remainder is price discovery — but it removes the most obvious mechanical candidate at
the level, which is where the analysis had been stuck.

## Caveats on my own benchmark

The **b₁ ≈ 0.5** prediction assumes uniform arrivals. Trades are **bursty**, and Hayashi-Yoshida
weights by returns — which occur at trade instants — so effective staleness is shorter than half
the mean interval. **0.5 is therefore a rough upper bound, not a sharp prediction**, and the
10× gap should be read with that slack.

> **Correction ([EXP-014](EXP-014-empirical-waiting-time.md)).** The reasoning above is wrong in
> its main term. Under the inspection paradox, information landing at an arbitrary instant is
> more likely to fall inside a *long* gap, so the true wait is `E[I²]/(2E[I]) ≥ E[I]/2` —
> **longer** than half the mean interval, not shorter. Both effects are real and partly cancel;
> EXP-014 measures the quantity empirically instead of arguing about it, and reaches the same
> conclusion far more strongly.

The level check does not depend on that assumption, and it is the more decisive of the two.

The pooled R² of 0.232 comes mostly from the asset fixed effects, not from b₁. It is not
evidence for the regression.

## Limits

- Four assets, nine days.
- Mean inter-trade interval is a crude staleness proxy. A distribution-aware measure — expected
  waiting time under the observed arrival process — would sharpen both the benchmark and b₁.
- Ruling out observability at the level does not identify what *does* produce it. Latency,
  consensus delay, participant overlap and genuine price discovery all remain live and
  unseparated.

## Next

1. Replace the mean-interval proxy with the empirical expected waiting time under each asset's
   arrival process; recompute the benchmark and b₁ against it.
2. If the level survives that too, the remaining candidates are structural — consensus and
   network latency versus discovery — and separating them needs an instrument that sees order
   submission, not just execution.
