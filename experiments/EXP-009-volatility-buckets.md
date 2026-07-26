# EXP-009 — Is the lag continuous in volatility, or a threshold? Neither.

**Status:** run. **Retracts EXP-008.** Once the grid step is controlled for, volatility has
**no** relationship with Hyperliquid's follower position. The position is stable instead.
**Date:** 2026-07-26
**Data:** perplog tape, BTC, 144 hours across 2026-07-18 → 07-26, venues `hl / binance / okx`.
Script: `experiments/exp009_volatility_buckets.py`. Per-hour output:
`experiments/data/exp009_hours.csv`.

---

## Question

EXP-008 contrasted three stressed hours against three calm ones and concluded the lag widens
under stress. Six hours cannot distinguish a smooth relationship from a threshold, so this
measures every usable hour in the window.

## Statistic

The asymmetry **ratio** used in EXP-006–008 is unstable: it divides by the positive-side sum,
which approaches zero in quiet hours and made one EXP-008 cell read 55×. Replaced by a bounded
**follower index**:

```
index = (Σρ(k<0) − Σρ(k>0)) / (|Σρ(k<0)| + |Σρ(k>0)|)     ∈ [−1, +1]
```

+1 = pure follower, 0 = symmetric, −1 = pure leader. `okx/binance` is carried as the control
in every hour.

## Results by bucket

| range | hours | mean range | **index HL** | index OKX (control) | HL grid step |
|---|---|---|---|---|---|
| < 15 bps | 18 | 12 | 0.614 | 0.102 | 993 ms |
| 15–25 | 25 | 20 | 0.566 | 0.167 | 799 ms |
| 25–40 | 46 | 33 | 0.583 | 0.133 | 583 ms |
| 40–60 | 32 | 49 | 0.608 | 0.112 | 462 ms |
| > 60 bps | 23 | 79 | **0.687** | 0.136 | 361 ms |

The raw picture looked like a threshold: flat to 60 bps, then a jump. And it tested well —
index 0.687 above 60 bps against 0.591 below, **t = 3.01, p = 0.005**, while the OKX control
did not move (t = 0.20, p = 0.845). Specific to Hyperliquid, apparently.

## The control that kills it

| | |
|---|---|
| corr( ln range, index HL ) | +0.16 |
| corr( ln grid step, index HL ) | −0.206 |
| corr( ln range, ln grid step ) | **−0.779** |
| **partial corr( ln range, index \| grid step )** | **−0.001** |

Volatile hours have finer grids — Hyperliquid trades more when the market moves, so its event
step falls from 993 ms to 361 ms across the buckets. A finer grid **reveals more asymmetry for
an unchanged true lead**, because a sub-bin lead partly lands in k = 0 on a coarse grid.

Once the step is partialled out, the volatility relationship is **exactly zero**. The whole
effect was the measurement grid.

## Retraction

**EXP-008's headline is withdrawn.** "Hyperliquid's lag widens under stress" is not supported;
the apparent widening is an artefact of how the protocol samples.

The uncomfortable part: **EXP-008 identified this confound.** Its limitations section states
that the step went from 987 ms to 269 ms and that "the regimes are not compared over the same
horizon, which is a design limitation, not a detail." It was named and left unquantified.

> **A confound listed in the limitations is not a confound controlled for.** An honest but
> unquantified caveat can conceal a result that is entirely artefact. If a caveat could
> plausibly account for the whole effect, it must be measured before the result is stated —
> not filed beneath it.

## What stands, and it is stronger

Hyperliquid's follower index sits at **~0.59, flat across every volatility regime**, against
a CEX control of ~0.13 that is equally flat.

The follower position is therefore **structural, not conditional**. That is a firmer claim
than EXP-008's: it does not depend on regime, so it does not need a regime to be reproduced.

## Limits

- One asset, nine days, one CEX pair as control.
- The follower index inherits the block-alignment protocol's residual biases (EXP-006), which
  run against the finding and are unquantified.
- The grid-step confound is *controlled* here, not *removed*. A protocol that samples both
  venues on a fixed wall-clock grid regardless of trade arrival would remove it, at the cost
  of the block alignment that EXP-006 showed to matter. The two corrections pull against each
  other and that tension is unresolved.

## Next

1. Resolve that tension: a protocol that is simultaneously block-aligned and step-invariant.
2. Other assets, to test whether ~0.59 is a Hyperliquid constant or a BTC one.
3. Whether the index has moved over the venue's life — needs an instrument reaching further
   back than the tape's 2026-06-17.
