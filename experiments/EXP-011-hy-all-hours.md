# EXP-011 — Hayashi-Yoshida across 144 hours: 575 ms, in every hour

**Status:** run. **Binance leads Hyperliquid by 575 ms (median), in 100% of 144 hours,
invariant to volatility.** Control: OKX lags Binance by 25 ms — a factor of 23.
**Date:** 2026-07-26
**Data:** perplog tape, BTC, 144 hours over 2026-07-18 → 07-26.
Script `experiments/exp011_hy_all_hours.py`, output `experiments/data/exp011_hy_hours.csv`.

---

## Why

EXP-010 validated the estimator and applied it to six hours, giving a median of ~550 ms. Six
hours is a median, not a confidence band, and the volatility invariance rested on two pools of
three. This runs the same estimator over every usable hour.

## Results

| | median | mean | **95% CI (mean)** | σ | n |
|---|---|---|---|---|---|
| **hl / binance** | **575 ms** | 601 | **[577, 624]** | 145 | 144 |
| okx / binance *(control)* | **25 ms** | 21 | [18, 23] | 15 | 144 |

**A factor of 23 between Hyperliquid and the control.** The control is not zero — Binance does
lead OKX, in 88.2% of hours — but by 25 ms, barely above the estimator's 25 ms scan resolution.
That is what a normal gap between two major venues looks like.

**Every hour agrees.** τ > 0 in **100.0%** of the 144 hours for Hyperliquid. Not a single hour
reverses.

Distribution of the Hyperliquid peak:

| p5 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|
| 500 ms | 525 | **575** | 625 | 846 |

## Volatility invariance

| range | hours | median peak | mean ρ at peak |
|---|---|---|---|
| < 25 bps | 43 | **575 ms** | 0.554 |
| 25–60 bps | 78 | **575 ms** | 0.606 |
| > 60 bps | 23 | **575 ms** | 0.553 |

Identical to the estimation step across a wide volatility range.
`corr(ln range, peak) = −0.203, p = 0.015` — weak (r² = 4%), and by this repo's own rule the
p-value reflects n = 144 rather than a finding. Note also the **sign**: negative means the lag
is marginally *shorter* when the market moves.

EXP-008 claimed the lag widens under stress. It was not merely an artefact — it was
directionally backwards as well.

## The statement this supports

> On BTC, Binance leads Hyperliquid by **575 ms** (95% CI on the mean 577–624 ms), in **100%**
> of 144 measured hours, invariant to volatility. The same estimator returns **25 ms** between
> OKX and Binance.

Grid-free, in physical units, from an estimator validated to zero error against known lags
(EXP-010), with a control bounding what a normal inter-venue gap looks like (EXP-007).

## Limits

- **One asset.** Whether 575 ms is a Hyperliquid constant or a BTC one is untested.
- **Nine days.** No claim about stability over the venue's life; the tape only reaches
  2026-06-17.
- **Total observable lead only.** How much of the 575 ms is mechanical — Hyperliquid's price
  being observable only at block boundaries — versus genuine price discovery remains open. HY
  measures the sum. EXP-010 showed grid comparison cannot separate them.
- HY assumes a single scalar delay. If the truth is a distribution of delays, the peak
  summarises it rather than describing it.

## Next

1. Other assets — the cheapest test of whether 575 ms belongs to the venue or the instrument.
2. The mechanical/informational decomposition, which needs a new idea rather than a new grid.
   One candidate: compare against a venue with comparable block-like batching, isolating the
   discreteness from the venue.
3. Whether the lead has narrowed as Hyperliquid grew — blocked on instrument reach, not method.
