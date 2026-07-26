# FINDING-001 — Funding controller deadband on Hyperliquid: full-archive measurement

**Status:** closed. **No discovery.** One validated dataset, one unplanned observation.
**Date:** 2026-07-26
**Data:** full `asset_ctxs` archive — 1,137 days (2023-05-20 → 2026-06-29),
4,169,753 asset-hours, 230 assets. Folded by `qfr/data/archive.py`.

---

## Scoreboard

| hypothesis | outcome |
|---|---|
| H1 — the deadband is a novel finding | **killed by prior art** (textbook algebra) |
| H2 — deadband occupancy is trending upward | **killed by the full archive** (artifact of partial data) |
| H3 — book depth explains the trend | **rejected, and backwards** |
| *(unplanned)* — premium-sign regime flip | **survives, and is the most interesting thing here** |

Three of four dead. A normal day.

## H1 — killed by prior art

The deadband is published algebra, not a discovery: *"If (I − P) is within [−β, β], then
F = I … the funding rate becomes insensitive to the premium index."* It follows in one line
from the clamp applying to `interest − P` rather than to `F`.

The control-system framing was also anticipated:

- **Zhang (2026), "Funding Rate Mechanism in Perpetual Futures"** (SSRN 6185958) — funding
  *"as an algorithmic feedback rule rather than a passive transfer"*; analyses how clamp-style
  piecewise-linear rules affect basis volatility **and funding tails**. Essentially the whole
  O3 programme.
- **Kim & Park (2025), [arXiv:2506.08573](https://arxiv.org/pdf/2506.08573)** — clamp as key
  design factor, model-free no-arbitrage bounds.
- **[arXiv:2605.06405](https://arxiv.org/abs/2605.06405)** — funding-aware market making,
  *calibrated on Hyperliquid ETH/BTC/SOL*. HL funding is already an academic dataset.
- **Ackerer (2026), Mathematical Finance** — perpetual futures pricing.

**Method error worth recording:** novelty was first checked against the *quantum-finance*
literature, where nothing matched. The result lives in **market microstructure**, a different
field with a different bibliography. Checking novelty requires first knowing which field
would already own the result.

## H2 — killed by the full archive

An interim run on 871 of 1,137 days showed 36.5% → 60.4% → 66.2% → 76.3% and was reported as
a monotonic doubling. **That was an artifact**: the fold completes days in thread-pool order,
which is not uniform across the date range, so the partial sample was biased.

Full archive, live assets only (`day_ntl_vlm > 0`):

| quarter | asset-hours | assets | deadband | premium high | premium low |
|---|---|---|---|---|---|
| 2023Q2 | 25,063 | 28 | 40.8% | 2.8% | 56.5% |
| 2023Q3 | 87,907 | 53 | 40.9% | 5.7% | 53.3% |
| 2023Q4 | 177,389 | 100 | 33.8% | 51.0% | 15.2% |
| 2024Q1 | 246,341 | 122 | 36.8% | 55.6% | 7.6% |
| 2024Q2 | 283,157 | 139 | 70.1% | 14.9% | 14.9% |
| 2024Q3 | 274,826 | 139 | 70.9% | 4.8% | 24.4% |
| 2024Q4 | 295,206 | 156 | 61.1% | 31.1% | 7.8% |
| 2025Q1 | 363,358 | 175 | 63.5% | 5.9% | 30.6% |
| 2025Q2 | 367,335 | 185 | 62.2% | 4.7% | 33.1% |
| 2025Q3 | 381,943 | 185 | 72.3% | 12.2% | 15.4% |
| 2025Q4 | 405,437 | 189 | 48.5% | 3.4% | 48.1% |
| 2026Q1 | 409,168 | 192 | 52.1% | 1.8% | 46.1% |
| 2026Q2 | 394,692 | 191 | 64.5% | 2.7% | 32.8% |

Daily occupancy across all 1,137 days: **mean 56.2%, σ = 18.8, range 5.8% – 87.7%.**

There is one level shift (2024Q1 → Q2, 36.8% → 70.1%) and then oscillation in a 48–72% band
with no trend. With a daily σ of 18.8, occupancy is a **market-state variable, not a slow
structural drift**. Any two-point comparison of it is meaningless.

## H3 — rejected, and in the opposite direction

Hypothesis: deeper books → tighter premium → more time in the deadband. Tested with the
impact spread `(impact_ask_px − impact_bid_px) / oracle_px`, the archive's direct measure of
executable depth, over 5,223 coin-months with ≥200 asset-hours each.

| impact spread | coin-months | mean deadband |
|---|---|---|
| < 1 bps (deepest) | 88 | 52.2% |
| 1–3 bps | 480 | 53.5% |
| 3–10 bps | 2,154 | 56.2% |
| 10–30 bps | 2,060 | 59.8% |
| > 30 bps (thinnest) | 441 | 66.8% |

`corr(ln(impact spread), deadband) = +0.137`

The sign is **opposite** to the hypothesis — deeper markets spend *less* time in the deadband —
and the effect is weak. A plausible reading is that liquid assets carry real basis positioning
that pushes the premium outside the band, while thin assets sit on stale near-zero premiums by
default. Untested, and not worth pursuing at r = 0.137.

## What survives

**1. The controller is exactly validated.** On live assets whose published rate is stable
within the hour, the documented formula reproduces it bit-exactly:

| population | asset-hours | exact |
|---|---|---|
| live, stable rate | 1,577,881 | **99.23%** |
| live, all | 3,711,822 | 57.3% |
| dead markets (`vol = 0`) | 457,931 | **0.3%** |

The `live, all` figure is low only because hours where the rate changes mid-hour cannot be
compared to a single hourly mean. The separation between live (99.2%) and dead (0.3%) is the
result: deviations are entirely an artifact of stale markets, not of the model.

This is reproducibility infrastructure, not a discovery — but anyone building on Hyperliquid
funding data needs it, and no one appears to have published it.

**2. An unplanned observation: the premium-sign regime flipped and stayed flipped.**
`premium high` (perp rich, longs pay more) collapses from 51.0% / 55.6% in 2023Q4–2024Q1 to
**1.8% – 2.7%** through 2026, while `premium low` runs 32.8% – 48.1%. Hyperliquid perps moved
from persistently rich to persistently cheap, and have stayed there for four quarters.

This was not looked for. It is the most interesting thing in the file, and it has an obvious
follow-up: does the discount coincide with the growth of delta-neutral basis capital
(short perp, long spot), which mechanically pushes the perp below spot?

## Reusable output

`data/ctx_hourly/` — 1,137 Parquet files, 344 MB, one per archive day, holding hourly folds
of the whole perp universe: premium (mean/min/max), funding published and modelled, OI,
mark/oracle/mid, both impact prices, volume, plus derived `regime` and `model_exact`.

Rebuild: `python -m qfr.data.archive --all --out data/ctx_hourly`
