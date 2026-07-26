# EXP-004 — Does the oracle lead the Hyperliquid perp, or follow it?

**Status:** **inconclusive** — the question is well posed, the data granularity cannot answer it.
One methodological finding does survive, and it constrains everything else in this repo.
**Date:** 2026-07-26
**Data:** `data/ctx_hourly/` — hourly panel, 3.7M live asset-hours.

---

## Why it was asked

EXP-003 found a negative and unstable `β` regressing premium on returns, and flagged a
possible mechanical cause: premium is `(impact − oracle)/oracle`, so if the oracle leads and
the perp follows, premium moves opposite to perp returns **by construction**. Settling the
lead-lag structure would either rescue or bury that result. It also matters on its own —
whether Hyperliquid discovers price or imports it from CEX spot is a real question for a venue
carrying ~70% of on-chain perp volume.

## Specification

Hourly cross-correlation is useless here: at that frequency the two series are already
synchronised. The right form is an **error-correction model** — whichever leg moves to close
the spread is the one that follows.

With `s = ln(price) − ln(oracle)`, regress each leg's *next* hourly return on `s`, demeaned
within asset:

- **P1 (oracle leads)** — `λ_price < 0` and `|λ_price| > |λ_oracle|`.
- **P2 (perp leads)** — `λ_oracle > 0` and `|λ_oracle| > |λ_price|`.
- **Falsification** — both near zero, or inconsistent signs.

## First attempt, and why it was thrown away

Run with `mark_px`, the result looked spectacular: `λ_mark = −0.8015`, t = −124.9,
**R² = 0.142** — the perp doing 80% of the correction within the hour, the oracle none
(`λ_oracle = +0.0098`, t = 1.8). P1 apparently confirmed, and with the best R² of the day.

It is an artefact. Per the docs, mark price is the **median** of three inputs, the first being:

> *Oracle price plus a 150 second EMA of the difference between Hyperliquid's mid price and
> the oracle price.*

When that component is the median, `ln(mark) − ln(oracle)` **is** a 150-second EMA of the
basis. An EMA with a 2.5-minute half-life has decayed roughly twenty times between two hourly
observations, so it mean-reverts definitionally. The result measures the mark price formula,
not the market.

Caught before reporting, unlike the morning's errors.

## Second attempt — `mid_px`, the actual book price

| scope | leg | λ | t | **R²** | n |
|---|---|---|---|---|---|
| BTC/ETH/SOL | mid | −0.1676 | −6.1 | 0.0005 | 80,901 |
| | oracle | **+0.1885** | 6.9 | 0.0006 | |
| liquid > $10M/day | mid | −0.0228 | −4.0 | 0.0000 | 418,811 |
| | oracle | **+0.1873** | 33.9 | 0.0027 | |
| all live assets | mid | −0.0586 | −33.1 | 0.0003 | 3,708,831 |
| | oracle | **+0.0753** | 49.0 | 0.0006 | |

The direction points at **P2, not P1**: the oracle corrects more, by 8× in the liquid bucket
(0.187 vs 0.023). Taken at face value, the Hyperliquid book leads and the CEX-derived oracle
follows — the opposite of the assumption behind EXP-003's mechanical explanation.

**But by this repo's own rule, this is inconclusive.** R² ≤ 0.0027 everywhere: the spread
explains 0.3% of the oracle's next-hour return. The t-statistics of 33.9 and 49.0 measure
3.7M observations, not a finding. On the majors the two λ differ by 0.021 with standard errors
of 0.027 — indistinguishable.

There is a structural reason, and it should have been anticipated: **the oracle republishes
every 3 seconds**, and price discovery between a perp book and CEX spot resolves in seconds.
Hourly sampling is ~1,200× too coarse; any real lead-lag is fully absorbed inside a single
observation.

## What survives

**1. `mark_px` is mechanically entangled with `oracle_px`, and with `premium`.**
The mark formula contains `oracle + EMA_150s(mid − oracle)`. Any analysis combining
`mark_px` with `premium` or `oracle_px` is contaminated — **including EXP-003**, which used
mark returns. That result is now doubly suspect: unstable *and* built on an entangled variable.

> **House rule: use `mid_px` for anything about price dynamics. Never `mark_px`.**
> `mark_px` is fit for margining, liquidation and PnL — which is what it is designed for.

**2. A specific, identified purpose for the live recorder.**
It was narrowed and then stopped this morning because the archive superseded it — correctly,
for funding and context. But the archive is **minute-grain**, and this question needs
sub-minute. The recorder's 5-second sampling on focus assets is exactly the missing
instrument. That is a precise justification, replacing the vague one it had before.

## To settle it

1. **Immediate:** use perplog's tape, already at tick resolution, cross-venue.
2. **Slower:** restart the recorder at 5s on BTC/ETH/SOL and wait weeks.

Route 1 costs nothing extra and is strictly better — it also covers Binance/OKX/Bybit, so the
question generalises from "does HL lead its oracle" to "does HL lead the market".

**Status: open, and now testable with the right instrument.**
