# EXP-008 — Does Hyperliquid's lag change under volatility?

**Status:** **RETRACTED by [EXP-009](EXP-009-volatility-buckets.md).** The widening reported
below is an artefact of the grid step, which this experiment named in its limitations and
failed to quantify. Across 144 hours, the partial correlation between volatility and the
follower index — controlling for grid step — is **−0.001**. The lag does not change with
volatility. This file stands as the error that motivated the correction.
**Date:** 2026-07-26
**Data:** perplog tape, BTC, six hours selected on realised range, all four venues.

---

## Question

EXP-007 established that Hyperliquid follows the CEX market by ~250–300 ms and that this is
specific to it. Volatility is where leadership is most likely to shift: liquidation cascades
are a plausible source of *originating* price moves, and Hyperliquid carries a large share of
on-chain perp open interest.

**P1 — leadership shifts.** HL's asymmetry falls under stress; cascades originate there.
**P2 — it intensifies.** HL follows even more when the market moves fast.
**P3 — unchanged.**

No prior preference: both mechanisms are plausible.

## Selecting the hours

Hourly realised range from HL `candleSnapshot`, 2026-07-18 → 07-26, cross-referenced against
tape coverage on all four venues.

**Only 138 of 193 hours are usable on all four venues** — 28% lost. The dominant cause is a
systematic Hyperliquid gap pattern:

```
2026-07-20  hl  gapped [1, 4, 6, 9, 12, 15, 18, 21]
2026-07-18  hl  gapped [2, 5, 7, 10, 13, 16, 19, 22]
2026-07-19  hl  gapped [1, 4, 7, 10, 13, 16, 19, 22]
```

**A three-hour period, every day.** One HL hour in eight is lost on a regular cadence — the
signature of a restart or rotation, not network loss. Other venues show isolated single gaps.
This is a perplog infrastructure issue, reported separately; it also cost this experiment the
single most volatile hour in the window (2026-07-20 15:00, 188 bps, gapped on HL).

Final pools, both 3 hours:

| regime | hours | mean range |
|---|---|---|
| **stress** | 07-24 13:00, 07-20 11:00, 07-20 00:00 | ~123 bps |
| **calm** | 07-24 23:00, 07-25 23:00, 07-25 19:00 | ~8 bps |

Ratio ≈ 15×. Returns spanning an hour boundary are dropped (gap > 60 s).

## Results

Block-aligned protocol from EXP-006/007. Asymmetry = Σρ(k<0) / Σρ(k>0).

| pair | calm | **stress** |
|---|---|---|
| hl / binance | 4.5× | **8.3×** |
| hl / bybit | 3.4× | **11.4×** |
| hl / okx | *(unusable — see below)* | **7.9×** |
| okx / binance | 1.5× | 1.4× |
| bybit / binance | 2.2× | 1.5× |

**P2 confirmed, P1 rejected.** Hyperliquid's asymmetry roughly doubles against Binance and
triples against Bybit, while the CEX pairs are **unchanged** (1.4–2.2× in both regimes).

The control matters again: this is not "everything desynchronises under stress". The CEX hold
together exactly as before. Hyperliquid alone decouples.

## Two caveats

**The calm hl/okx figure of 55.4× is an artefact and is not reported above.** Its positive-side
sum is 0.00, so the ratio divides by ~zero. The usable statistic is the raw negative sum:
0.15 calm vs 0.89 stress — same direction as the other pairs, but the ratio is meaningless.

**Grid step differs between regimes.** HL's median step is 987 ms calm versus 269 ms stress,
because it trades far more often when the market moves. The asymmetry ratio is dimensionless,
but the ±6 window spans ±5.9 s calm and ±1.6 s stress. The regimes are therefore not compared
over the same horizon, which is a real limitation of this design rather than a detail.

Correlations are also uniformly lower in calm (0.06–0.17) than stress (0.18–0.23), as expected
when little is happening.

## Implication worth stating

Hyperliquid's book is furthest behind the market **exactly when the market moves fastest** —
which is when liquidations trigger. The mark price is a median that includes the CEX-derived
oracle, so the protocol partially insulates margining from this. But the gap between the book
and the rest of the market is widest at the worst moment, and that is measurable rather than
speculative.

This is an observation, not an alarm: quantifying whether it reaches liquidation outcomes
requires the liquidation feed, which perplog exposes at `/api/flow/liquidations` and this
experiment did not touch.

## Next

1. Match the comparison horizon across regimes — resample so the ±k window spans the same
   wall-clock span in both, rather than the same number of HL events.
2. Test whether the widening is continuous in volatility or a threshold effect: bucket all 138
   usable hours by range rather than contrasting two pools.
3. Join to `/api/flow/liquidations` and ask whether the widening coincides with cascades
   specifically or with volatility in general.
