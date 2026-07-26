# EXP-006 — Block-aligned lead-lag: how much of Hyperliquid's lag is mechanical?

**Status:** run. **Part mechanical, part informational — and the split is measurable.**
Supersedes EXP-005's headline, which conflated the two.
**Date:** 2026-07-26
**Data:** perplog tape, BTC and HYPE, 2026-07-24 hours 12–14.

---

## The problem EXP-005 left

EXP-005 measured Binance leading Hyperliquid by ~500 ms on a wall-clock grid, and flagged that
some of it could be mechanical: HL trades are stamped by the L1 block that executed them, so
HL's price is *observable* later than a continuous venue's even if discovery were simultaneous.
It guessed "roughly half". That guess was made without measuring the block quantum.

## First: the block quantum, measured

Gaps between consecutive **distinct** HL timestamps, BTC:

| | min | p1 | p5 | p25 | median |
|---|---|---|---|---|---|
| **hl** | **40 ms** | 55 | 65 | 132 | 264 |
| binance | 1 ms | — | 1 | 7 | 48 |

HL has a **hard floor at 40 ms** with almost nothing below 55. Binance has none — it reaches
1 ms. That floor is the block cadence. The 264 ms median is **trade arrival**, not block
cadence: blocks that carry no BTC trade produce no timestamp.

**This corrects EXP-005's caveat.** Block quantisation can account for at most ~30–60 ms of a
500 ms lag, not half of it. The larger mechanical effect is elsewhere: *within-bin staleness*.
With `last(px)` per bin, Binance — printing every 48 ms — lands near the bin's right edge while
HL, printing every 264 ms, lands earlier on average. HL's binned price therefore reflects an
earlier instant, which reads as HL lagging.

## Design

Remove the asymmetry by sampling **both** series at the same instants: HL's own block times.

- grid = every distinct HL timestamp
- HL price = the HL print at that instant
- Binance price = last Binance print **at or before** that instant (ASOF join)
- returns on that grid, cross-correlated in **HL-event units**

Residual bias now runs *against* the finding: the ASOF join leaves Binance up to its own
48 ms inter-arrival stale, which handicaps Binance. Any surviving Binance lead is a lower bound.

## Results

`ρ(k) = corr(r_HL[t], r_BINANCE[t+k])`, **k < 0 ⇒ Binance leads**, k in HL events.

| | wall-clock grid (EXP-005) | **block-aligned grid** |
|---|---|---|
| **BTC** peak | −500 ms, ρ = 0.474 | **−264 ms (1 event), ρ = 0.226** |
| BTC asymmetry (Σneg/Σpos) | 16× | **8.2×** (0.89 / 0.11) |
| **HYPE** peak | −500 ms, ρ = 0.322 | **k = 0, ρ = 0.413** |
| HYPE asymmetry | — | **4.5×** (0.51 / 0.11) |

n = 25,744 HL events (BTC, median step 264 ms); 10,269 (HYPE, median step 662 ms).

**The mechanical component is real and large.** Correcting the sampling asymmetry halves ρ at
the peak on BTC (0.47 → 0.23) and pulls the peak in to a single HL event. On HYPE it removes
the offset **entirely** — the peak becomes contemporaneous, and at the highest correlation in
the test.

**The informational component survives.** Asymmetry remains 8.2× on BTC and 4.5× on HYPE with
both series sampled at identical instants. Binance's *past* moves predict HL's current move
several times more than the reverse.

Autocorrelation cannot produce this: a smooth series yields a **symmetric** profile, not an
8-to-1 ratio between sides.

## Revised conclusion

> Hyperliquid's lag behind Binance is **part mechanical, part informational**. The mechanical
> part is large — it accounts for the entire offset on HYPE and about half on BTC. The
> informational part survives block alignment: Binance retains a directional edge of 4–8×.

This supersedes EXP-005's "Binance leads by ~500 ms", which conflated the two and would not
have been separable without this correction.

## Limits

- Three hours, one day, two assets, one CEX. Enough to separate the two components, not to
  size them precisely.
- Trades, not quotes. A venue can lead in quotes while trailing in prints.
- The ASOF join's residual staleness biases against the finding, so the asymmetry is a lower
  bound — but it is not zero-bias, and its size was not quantified.
- Clock skew between venues remains unexcluded, though it cannot explain an *asymmetry ratio*,
  only a constant offset — and the offset is what alignment removed.

## Next

1. OKX and Bybit: does the asymmetry hold against every CEX, or is it Binance-specific?
2. Widen to more days and assets, now that the protocol has a defensible bias direction.
3. Quotes, if a book feed at tick resolution becomes available.
