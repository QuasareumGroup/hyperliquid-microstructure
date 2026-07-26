# EXP-002 — Does delta-neutral carry capital leave a footprint in open interest?

**Status:** **falsified.** Both specifications reject the hypothesis.
**Date:** 2026-07-26
**Data:** `data/ctx_hourly/` folded to a coin-day panel — 76,596 coin-days, 228 assets,
filtered to `day_ntl_vlm > $1M`.

---

## Hypothesis (registered before running)

Cash-and-carry capital (short perp + long spot) grows open interest **without moving the
price**, unlike directional flow. Its fingerprint should therefore be: OI rising while the
price is flat → premium more negative (perp pushed below spot).

Motivation: the carry on majors collapsed from ~24% APR (2024) to 2.6–3.1% (2026), and the
premium-sign regime flipped over the same period (perp-rich hours fell from 51% to under 3%).
The conjecture was that these are one phenomenon — capital entering the trade and competing
away its own return.

**Predictions, written down first:**

- **P1** — in the low-|return| stratum, premium falls monotonically as OI growth rises.
- **P2** — the effect is weaker at high |return|, where directional flow dominates.
- **Falsification** — if premium *rises* with OI growth at low |return|, the delta-neutral
  explanation is wrong.

## Spec 1 — pooled, contemporaneous

Mean premium (bps, 8h basis) by OI-growth quintile × |return| tercile:

| OI growth quintile | low return | mid return | high return |
|---|---|---|---|
| 1 (shrinking most) | +0.35 | −0.03 | −2.20 |
| 2 | −0.97 | −1.18 | −1.63 |
| 3 | −1.05 | −1.13 | −1.56 |
| 4 | +0.31 | +0.09 | −0.62 |
| 5 (growing most) | **+1.78** | +1.36 | −2.26 |

Not monotonic, and the top quintile is the **most positive** — the opposite of P1.
`corr(ΔlogOI, premium) = −0.0389`.

## Spec 2 — within-asset, lagged

The hypothesis is causal and directional, so it implies a within-asset, lagged test rather
than a pooled contemporaneous one. Premium demeaned per coin, OI growth lagged one day.
**This is a second specification run after the first failed; discount it accordingly.**

| OI growth quintile (t−1) | low return | high return |
|---|---|---|
| 1 (shrinking most) | +1.08 | −1.17 |
| 2 | −0.19 | −0.97 |
| 3 | −0.69 | −0.59 |
| 4 | +0.34 | −0.01 |
| 5 (growing most) | **+1.72** | +0.60 |

Same U shape, top quintile again the most positive. `corr(ΔlogOI[t−1], premium[t]) = +0.0104`
within-asset, n = 76,368.

**P1 rejected in both specifications. P2 untestable — there is no effect to attenuate.**

Correlations of +0.01 and −0.04 may be distinguishable from zero at n = 76k, but they are
economically meaningless.

## The finding that does survive: the deadband absorbs the whole effect

Daily-average premium across the panel:

| p5 | median | p95 | inside the deadband |
|---|---|---|---|
| −9.95 bps | −0.95 bps | +12.58 bps | **53.7%** |

Premiums do range outside the band day to day. But the variation *attributable to OI growth*
is roughly ±2 bps — entirely inside the ±4/+6 bps band. So even if carry flow did move the
premium at this magnitude, **funding would not respond at all**: the clamp cancels it.

This connects EXP-002 back to FINDING-001. The funding mechanism is structurally insensitive
to precisely the kind of marginal-flow effect this hypothesis proposed. Any explanation of
the regime flip that works through small premium shifts is mechanically dead on arrival.

## What this leaves

The **phenomenon stands and is now unexplained**. Perp-rich hours fell from 51.0% / 55.6%
(2023Q4–2024Q1) to 1.8% – 2.7% through 2026, and have stayed there four quarters. That is a
large, persistent, well-measured shift. The proposed explanation is rejected.

An open question with a clean measurement behind it is a better research position than a
shift with a hand-waved cause.

Unexplained residual worth noting: the U shape is consistent across both specifications —
both extremes of OI change carry a more positive premium. Plausibly an activity or volatility
artifact rather than a flow effect, but untested.

## Next candidates

1. Decompose by asset class and venue age — the flip may be composition, not behaviour: the
   asset mix in 2026 (191 assets) differs from 2023Q4 (100).
2. Test against spot-perp basis directly rather than the premium, using `impact_bid_px` /
   `impact_ask_px` versus `oracle_px`.
3. Check whether the flip coincides with the arrival of HIP-3 markets or a change in the
   oracle construction, which would make it mechanical rather than economic.
