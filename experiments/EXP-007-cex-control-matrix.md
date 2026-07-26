# EXP-007 — Is Hyperliquid's lag its own property, or is Binance simply the market's leader?

**Status:** run. **The lag belongs to Hyperliquid.** The three CEX do not lead each other;
all three lead Hyperliquid by 8–12×.
**Date:** 2026-07-26
**Data:** perplog tape, BTC, 2026-07-24 hours 12–14, venues `hl / binance / okx / bybit`.

---

## Why the control decides everything

EXP-006 established that Binance leads Hyperliquid, part mechanically and part
informationally. On its own that is close to uninformative: "Binance leads" is the folk claim
about crypto price discovery, and if Binance also leads OKX and Bybit by a similar margin then
Hyperliquid is merely a normal non-Binance venue and there is nothing to report.

The question is therefore not *does Binance lead Hyperliquid* but **does Hyperliquid lag more
than a CEX does**. That needs CEX–CEX pairs as controls, on the same protocol.

## Design

The block-aligned protocol from EXP-006, applied to every pair. Grid = the events of venue A,
the candidate follower; B is ASOF-joined at or before each instant.
`ρ(k) = corr(r_A[t], r_B[t+k])`, **k < 0 ⇒ B leads A**.

Reported statistic is the **asymmetry ratio** Σρ(k<0) / Σρ(k>0), which is scale-free and so
comparable across pairs sampled at different natural rates.

## Results

| A (follower?) | B (leader?) | n | median step | peak k | ρ at peak | Σ neg | Σ pos | **asymmetry** |
|---|---|---|---|---|---|---|---|---|
| **hl** | binance | 25,744 | 264 ms | −1 | 0.226 | 0.89 | 0.11 | **8.2×** |
| **hl** | okx | 25,744 | 264 ms | −1 | 0.203 | 0.84 | 0.10 | **8.2×** |
| **hl** | bybit | 25,744 | 264 ms | −2 | 0.209 | 0.85 | 0.07 | **11.9×** |
| okx | binance | 116,217 | 30 ms | 0 | 0.097 | 0.39 | 0.31 | **1.2×** |
| bybit | binance | 106,202 | 10 ms | −1 | 0.089 | 0.43 | 0.28 | **1.5×** |
| okx | bybit | 116,212 | 30 ms | +1 | 0.108 | 0.32 | 0.55 | **0.6×** |
| binance | hl | 113,745 | 48 ms | **+6** | 0.041 | 0.06 | 0.14 | 0.4× |
| binance | okx | 113,747 | 48 ms | +4 | 0.087 | 0.33 | 0.42 | 0.8× |

**The three CEX are synchronised with one another.** Asymmetries of 0.6× to 1.5× — symmetric
within noise. Binance does not lead OKX or Bybit to any meaningful degree, and OKX marginally
leads Bybit. There is no single crypto price leader among them at this resolution.

**All three lead Hyperliquid by 8–12×.** The margin is essentially identical against Binance
and OKX and slightly larger against Bybit.

**The reverse direction confirms it.** Measured on Binance's own 48 ms grid, correlation with
Hyperliquid peaks at **k = +6 ≈ +288 ms**: Binance first, Hyperliquid after.

## Why the comparison is conservative

The CEX pairs are sampled on **finer** grids (10–48 ms) than Hyperliquid (264 ms). A finer grid
*reveals more* asymmetry for a given true lead — a 100 ms lead shows at k ≈ −3 on a 30 ms grid
but is swallowed inside a single 264 ms bin. The CEX therefore show less asymmetry despite
conditions that favour detecting it. The gap to Hyperliquid is a lower bound.

The ASOF residual staleness (venue B up to its own inter-arrival stale) also biases against
the leader in every row, uniformly.

## Conclusion

> Hyperliquid follows the CEX market by roughly 250–300 ms, part of it mechanical, and
> **this follower position is specific to it**. The major CEX do not lead one another.

The control is what makes this worth stating. Without it the result reduces to the folk claim
about Binance, which the data contradicts: Binance leads no one else.

## Limits

- Three hours, one day, one asset. Enough to separate venues cleanly; not enough to size the
  lead precisely or to claim stability over time.
- Trades, not quotes.
- Clock skew across four venues is unexcluded, but skew produces a constant offset — it cannot
  produce a *different asymmetry ratio* between pairs, which is the statistic used here.
- Hours 12–14 of a single day may not represent quiet or stressed regimes.

## Next

1. Repeat across days and regimes — especially a high-volatility hour, where leadership is
   most likely to shift.
2. Other assets, particularly ones where Hyperliquid's share of total volume is highest.
3. Whether the lag narrows over the venue's history: the archive covers three years, and the
   tape only reaches back to 2026-06-17, so this needs a different instrument.
