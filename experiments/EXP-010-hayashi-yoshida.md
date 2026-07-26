# EXP-010 — Resolving the grid tension: Hayashi-Yoshida

**Status:** run. **Tension resolved.** Binance leads Hyperliquid by **~550 ms**, stable across
volatility regimes. Revises EXP-006's mechanical/informational split, which no longer holds.
**Date:** 2026-07-26
**Code:** `hlm/analysis/leadlag.py`

---

## The tension

EXP-006 through EXP-009 all binned both venues onto a grid, and every grid choice was wrong in
a different direction:

- a **fixed wall-clock grid** makes Hyperliquid look late for free — its prints are sparser, so
  its last-price-in-bin is staler than the CEX's;
- **Hyperliquid's own event grid** removes that, but its step tracks activity (993 ms quiet,
  361 ms volatile), and a finer grid exposes more asymmetry at an unchanged true lead. EXP-009
  showed that artefact accounted for *all* of the apparent widening under stress.

Block alignment and step invariance cannot both be had from a grid.

## The resolution

**Hayashi-Yoshida** removes the choice. It never synchronises: it sums products of returns whose
observation intervals overlap, with one series shifted by a lag `tau` in **milliseconds**.

```
U(tau) = Σ_{i,j} dX_i dY_j · 1{ (t_{i-1}, t_i] ∩ (s_{j-1}+tau, s_j+tau] ≠ ∅ }
```

No bins, no resampling, no interpolation — and `tau` is physical, so estimates compare directly
across regimes and assets. Implemented O(n log m) per tau: once both interval lists are sorted,
the overlapping run is contiguous and the inner sum is a prefix-sum lookup.

Reference: Hoffmann, Rosenbaum & Yoshida (2013), on Hayashi & Yoshida (2005).

## Validation first, on a known answer

Synthetic: a latent random walk, Y observing it directly, X observing it delayed by a known lag,
both sampled asynchronously at different rates (X sparse like HL, Y dense like Binance).

| true lag | estimated peak | error |
|---|---|---|
| 0 ms | 0 | 0 |
| 100 | 100 | 0 |
| 300 | 300 | 0 |
| 600 | 600 | 0 |
| −300 | −300 | 0 |

Exact on all five, sign included.

**The first version was sign-inverted.** It shifted Y backward rather than forward, so every
recovered lag came out negated — magnitudes perfect, direction reversed. On real data that
would have read as *"Hyperliquid leads Binance by 550 ms"*, with ρ = 0.55 and clean invariance
across regimes: spectacular, coherent, publishable, and exactly backwards.

> **An estimator is not validated on the data you want to analyse.** It is validated on a case
> whose answer is known in advance — including the sign.

## Results on the tape

BTC, per hour, calm and stressed pools from EXP-008. `tau > 0` ⇒ Binance leads Hyperliquid.

| regime | hourly peaks | median | ρ at peak |
|---|---|---|---|
| calm | 550, 775, 500 ms | **550 ms** | 0.42–0.55 |
| stress | 600, 575, 525 ms | **575 ms** | 0.39–0.66 |

**The lead is stable at ~550 ms across a 15× volatility contrast.** This confirms EXP-009 by a
far more direct route than partial correlation: with `tau` in physical units, regimes are
comparable by construction rather than after statistical correction.

The follower index still moves between hours (0.21–0.80), but the **peak location** — the
parameter of interest — does not.

## Revision to EXP-006

EXP-006 concluded that roughly half the lag was mechanical, from the estimate falling from
500 ms on a wall-clock grid to 264 ms once block-aligned. **That inference does not survive.**

Hayashi-Yoshida returns ~550 ms — close to the raw wall-clock figure, not half of it. The
reduction seen under block alignment was most likely **grid coarsening**, not the removal of a
mechanical component: a coarse grid pulls the peak toward zero, because a lead shorter than the
step is split between k = 0 and k = −1.

And HY does not rescue the decomposition either — **it does not separate the two**. It measures
the total *observable* lead correctly, mechanical component included. If Hyperliquid's price is
genuinely observable later because of block execution, that delay is part of the 550 ms.

**The mechanical/informational split is therefore reopened, not answered.**

## What stands

- Binance leads Hyperliquid by **~550 ms** on BTC — grid-free, physical units, validated
  estimator.
- The lead is **invariant to volatility** across a 15× contrast.
- Combined with EXP-007's control, where the CEX do not lead each other: this is Hyperliquid's
  own property, and a stable one.

## Limits

- One asset, six hours, one CEX. HY is cheap enough to run on all 144 hours — that is next, not
  a caveat to leave standing.
- HY assumes the lead is a single scalar delay. If the true structure is a distribution of
  delays or state-dependent, the peak is a summary of it, not a description.
- Total lead only. Mechanical versus informational remains open, and no current method here
  separates them.

## Next

1. Run HY across all 144 hours to put a confidence band on the 550 ms rather than a median of
   six.
2. Other assets: is ~550 ms a Hyperliquid constant or a BTC one?
3. The decomposition, which now needs a genuinely different idea — comparing grids does not do
   it.
