# EXP-005 — Does Hyperliquid lead or follow the major CEX perp venues?

**Status:** run. **Headline superseded by [EXP-006](EXP-006-block-aligned-lead-lag.md).**
The ~500 ms figure below conflates a mechanical sampling artefact with a genuine
informational lead. Block-aligning both series separates them: the offset is largely
mechanical, while a 4–8× directional asymmetry survives. Read EXP-006 for the corrected
result; this file stands as the measurement that motivated it.
**Date:** 2026-07-26
**Data:** perplog tape, tick-level trade prints, `venue ∈ {hl, binance}`, BTC,
2026-07-24 hours 12–14 (sealed, no gaps).

> Predictions below are written before any number is seen.

---

## Why

EXP-004 asked whether the Hyperliquid book leads its CEX-derived oracle and came back
**inconclusive**: the hourly panel is ~1,200× too coarse for a question whose answer resolves
in seconds. The tape is tick-level, so the question becomes answerable — and it generalises.
The oracle is a construct; what actually matters is whether Hyperliquid discovers price or
imports it from the venues that dominate absolute volume.

## Method

Trade prints from each venue are binned onto a common grid (last print in bin), returns are
computed on the grid, and the cross-correlation

```
ρ(k) = corr( r_HL[t] , r_BINANCE[t+k] )
```

is evaluated for k across ± several bins. Peak at **k > 0** means an HL move predicts a
later Binance move — HL leads. Peak at **k < 0** means the reverse.

Run at multiple resolutions (100 ms, 250 ms, 1 s) because the trustworthy resolution is
bounded from below by the timestamp problems described next.

## Predictions

- **P1 — Binance leads.** The prior. It carries far more absolute volume, and the
  conventional view is that on-chain venues import price. Peak at k < 0.
- **P2 — Hyperliquid leads.** Peak at k > 0. EXP-004's hourly hint pointed weakly this way
  (the oracle corrected more than the book), but at R² ≤ 0.003 that is barely a signal.
- **P3 — synchronised.** Peak at k = 0 with symmetric decay: no lead measurable at this
  resolution.

**Falsification:** an asymmetric peak that survives at every resolution decides between P1
and P2. A peak at k = 0 that stays symmetric as resolution coarsens supports P3.

## Known limitations, stated before running

**1. Two clocks, not one.** Timestamps are venue-reported: HL reads the trade's `time`
field, Binance reads `T`. Any systematic clock offset between the two exchanges appears
directly as lead-lag. Both are NTP-disciplined, so the offset should be small, but it is not
zero and it is not measurable from this data.

**2. Hyperliquid timestamps are quantised by block.** HL trades are stamped by the L1 block
that executed them, so HL times cluster on block boundaries while Binance times are
continuous. This is the more serious of the two: it biases any sub-block measurement
regardless of clock accuracy.

Timestamp granularity per venue is therefore **measured first**, and no conclusion is drawn
at a resolution finer than the observed HL quantum.

**3. Trades, not quotes.** The tape carries prints. A venue can lead in quotes while trailing
in prints. This measures trade-price discovery specifically, which is narrower than "price
leadership" in general.

**4. Three hours of one asset on one day.** Enough to detect a strong effect, not enough to
characterise it. If a clear asymmetry appears, the next step is more hours, more assets, and
the other two venues — not a stronger claim from this sample.

## Tooling

`tools/pfr-dump` — a small Rust binary decoding perplog's PFR1 frames to CSV via
`perplog_flow::tape::decode_chunks`. It takes a path dependency on the perplog workspace
deliberately: reimplementing the bincode + lz4 framing in Python to avoid the coupling would
mean guessing at a binary format, and the failure mode there is silent wrong numbers.

## Measured first: timestamp granularity

As pre-registered, before any correlation was computed.

| venue | prints | distinct timestamps | prints/ts | median gap between distinct ts |
|---|---|---|---|---|
| hl | 79,571 | 25,745 | 3.09 | **264 ms** |
| binance | 278,940 | 113,749 | 2.45 | **48 ms** |

Round-number quantisation is **not** present: 8.9% / 9.6% of timestamps are multiples of
10 ms, which is what chance gives. The concern registered above was wrong in that form.

What is present is **block batching**: 3.09 HL prints share a timestamp and distinct HL
timestamps are 264 ms apart at the median, versus 48 ms on Binance. HL's effective time
resolution is ~5.5× coarser. Nothing finer than a 250 ms grid is therefore reported.

## Results

`ρ(k) = corr(r_HL[t], r_BINANCE[t+k])`. **k < 0 ⇒ Binance leads.**

Bins where **both** venues actually traded, consecutive bins only, no forward fill:

| grid | peak | ρ at peak | ρ(+1) | asymmetry | n |
|---|---|---|---|---|---|
| 250 ms | **k = −2 (−500 ms)** | 0.266 | −0.003 | — | 8,832 |
| 500 ms | **k = −1 (−500 ms)** | **0.474** | +0.029 | **16×** | 10,125 |
| 1000 ms | k = −1 (−1000 ms) | **0.534** | +0.031 | **17×** | 8,277 |

The peak lands on **−500 ms** at both grids fine enough to resolve it, and moves to the
finest available bin at 1 s. The Hyperliquid-leads side is flat at zero throughout.

**P1 confirmed. P2 rejected.** Binance leads Hyperliquid by roughly half a second in BTC
trade prints.

This **overrides EXP-004's hint** that the book led its oracle. That came from R² ≤ 0.003 on
an hourly panel; this is ρ = 0.53 at tick resolution with a 16× asymmetry. A strong
measurement beats a weak one.

It also **closes the loop on EXP-003.** If Binance leads, then CEX spot leads, then the
oracle leads — and `premium = (HL impact − oracle)/oracle` moves opposite to HL returns by
construction. EXP-003's unstable negative β has a credible mechanical origin after all.

## How much of the 500 ms is real?

**Block batching is the serious alternative.** HL trades are stamped by the L1 block that
executed them, and distinct HL timestamps sit 264 ms apart at the median. HL's price is
therefore *observable* later than a continuous venue's even if discovery were simultaneous.
Roughly half the measured 500 ms could be this. The remainder is unexplained and plausibly
informational, but this experiment cannot separate them.

**Clock skew** cannot be excluded from this data, but 500 ms between two NTP-disciplined
exchanges is not credible as the main cause.

Separating mechanism from information needs block-time alignment (stamp HL prints by block
index, not wall clock) or quote data. Both are follow-ups, not corrections.

## A near miss worth recording

The first run binned with `ts_ms/step` in DuckDB, where `/` is **real** division, not
integer. There were no bins at all — each "bin" was a near-unique float. A full result table
was produced from it and was one step from being reported.

It was caught by a robustness check aimed at something else entirely: suspicion about
forward-fill, not about binning. Restricting to bins where both venues traded returned **17
observations instead of thousands**, which made no sense and exposed the bug.

The finding survived the fix — same peak, same magnitude, same asymmetry, now on 8k–10k real
observations. But it survived by luck of the check, not by design.

**Rule: when a filter returns an implausible n, the bug is upstream of the filter.**

## Follow-up run — HYPE, the asset where Hyperliquid holds primary liquidity

**Registered:** P1 flip (peak k > 0, HL leads) / P2 no flip / P3 synchronised.

HYPE is the case where the answer could plausibly reverse: Hyperliquid is the native venue,
holds primary spot liquidity, and its oracle uses **HL spot instead of external sources** for
exactly this class of asset. The block-cadence bias works *against* HL here, so a flip would
have to overcome a handicap — which would make it strong evidence.

Same hours, same method, BTC kept as control:

| grid | BTC peak | HYPE peak | HYPE ρ | HYPE n |
|---|---|---|---|---|
| 250 ms | k = −2, ρ 0.266 | k = 0, ρ 0.153 | Σ neg +0.36 / pos +0.04 | 739 |
| 500 ms | k = −1, ρ 0.474 | **k = −1 (−500 ms)**, ρ 0.322 | Σ neg +0.58 / pos **−0.09** | 1,838 |
| 1000 ms | k = −1, ρ 0.534 | **k = −1**, ρ 0.470 | Σ neg +0.72 / pos +0.05 | 3,178 |

**P1 rejected.** Same sign, same shape, slightly smaller. Binance leads Hyperliquid even on
Hyperliquid's own token. The HL-leads side is flat, briefly negative.

### But this result carries less weight than the BTC one

| | median gap between distinct HL timestamps |
|---|---|
| BTC | 264 ms |
| **HYPE** | **662 ms** |

HL trades HYPE less often, so its distinct timestamps are 2.5× further apart — **wider than
the 500 ms grid itself**. The mechanical handicap is not merely present, it is amplified, and
n is 4–5× smaller.

**The methodological consequence outweighs the test.** Block sparsity and apparent lag are the
same quantity, so this protocol penalises Hyperliquid *in proportion to how thinly the asset
trades there*. It therefore cannot answer the question for thin assets at all — and at this
resolution HYPE is a thin asset, despite its status.

The honest conclusion is not "HL leads nowhere". It is **no evidence of a flip, on a
measurement too confounded to settle it.**

## Next

1. **Align HL prints by block index rather than wall clock.** Now the top priority, not the
   second: every result of this shape carries the same bias, and the bias grows as liquidity
   falls. Nothing else should be run at scale until this is stripped.
2. More hours, more assets, and OKX/Bybit — this is three hours on one day.
3. Quotes rather than prints: a venue can lead in quotes while trailing in trades.
