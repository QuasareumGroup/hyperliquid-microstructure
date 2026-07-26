# EXP-016 — What is "one liquidation"? Fill-counting inflates the count and compresses sizes

**Status:** run, then rerun with per-fill notionals. The inflation factor is **robust to how a
liquidation is defined**, is
**strongly size-dependent** (2× typical, 67× for the top 1%), and fill-counting **compresses the
size distribution**.
**Date:** 2026-07-26
**Data:** `s3://hl-mainnet-node-data/node_fills_by_block` — 24,566 liquidation fills across
12 hours sampled over 10 months (2025-10 → 2026-07).
Script `experiments/exp016_liquidation_units.py`, per-episode output
`experiments/data/exp016_units.csv`.

> **Current position: [FINDINGS.md](FINDINGS.md).** This file is a running record and keeps its original wording plus corrections; the state of claims lives there.

---

## The problem with EXP-015's number

EXP-015 reported 3.4× overcounting using `(user, transaction)` as the unit. That unit was
chosen without argument, and it is not obviously right: a large position can be force-closed
across consecutive transactions — one liquidation from the trader's side, several from the
ledger's. Today has twice shown that an unexamined grouping key does the work of a finding.

So rather than defend a definition, count at all of them.

## The factor does not depend on the definition

| unit | count | inflation |
|---|---|---|
| fills | 24,566 | 1.0× |
| (user, transaction) | 6,412 | **3.8×** |
| episode, 1s gap | 6,582 | 3.7× |
| episode, 5s gap | 6,546 | 3.8× |
| episode, 60s gap | 6,533 | 3.8× |
| (user, coin, hour) | 6,465 | 3.8× |

Grouping by transaction, by second, or by whole hour lands on ~6,500 either way. **Tranching
happens inside a transaction, not across them** — so the choice of unit is not doing the work,
which is the thing that needed checking.

## It is not a flat multiplier — it scales with size

| episode size | n | median fills | mean fills |
|---|---|---|---|
| p0–50 ($0 – 661) | 3,273 | 2 | 2.1 |
| p50–90 ($661 – 18k) | 2,618 | 2 | 2.9 |
| p90–99 ($18k – 214k) | 589 | 4 | 10.0 |
| **p99–100 ($214k – 3.8M)** | **66** | **41** | **67.2** |

`corr(ln notional, ln fills per episode) = +0.509`, n = 6,546.

A typical liquidation is 2 fills. The largest are 41 (median) to 67 (mean). **The bias is
concentrated on exactly the events that get studied** — the top 1% of episodes generate 18% of
all fills.

## Consequence: the tail gets flattened

Rerun retaining **per-fill notionals** (`experiments/data/exp016_fills.csv`, 24,566 rows), so
these are measured rather than approximated. The first pass split each episode equally across
its fills, which only *bounds* the compression; those bounded figures are shown for comparison.

| quantile | true episode | actual fill | factor | *(first pass, bounded)* |
|---|---|---|---|---|
| p50 | $661 | $424 | 1.6× | *0.7×* |
| p90 | $18,259 | $8,842 | 2.1× | *1.6×* |
| p99 | $214,474 | $63,812 | **3.4×** | *5.7×* |
| p99.9 | $1,969,302 | $180,161 | **10.9×** | *15.7×* |
| max | $3,838,207 | $899,224 | 4.3× | — |

The bound held and pointed the right way: real compression is **smaller** than the equal-split
approximation, as predicted.

### The tail index — this is the result

Hill estimator, **validated first** against Pareto samples with known α (error < 6% across
α ∈ {1.0, 1.5, 2.0, 3.0}, n = 200k). Asymptotic s.e. = α̂/√k.

| series | k | α | 95% CI | finite variance? |
|---|---|---|---|---|
| **episodes** (truth) | 100 | 1.14 | [0.92, 1.37] | **no, α < 2** |
| | 200 | **1.15** | [0.99, 1.31] | **no, α < 2** |
| | 400 | 1.00 | [0.90, 1.10] | **no, α < 2** |
| **fills** | 100 | 2.01 | [1.62, 2.41] | undetermined |
| | 200 | **2.05** | [1.77, 2.34] | undetermined |
| | 400 | 1.74 | [1.57, 1.91] | no |

> **Fill-counting does not merely distort the magnitude of tail risk — it changes its kind.**
> The true liquidation size distribution has α ≈ 1.15: variance is infinite and the mean itself
> is near the edge of existing. Measured per fill it rises to α ≈ 2.05, where finite variance
> can no longer be excluded.

> **Qualified by [EXP-017](EXP-017-year-tail.md).** On 351,540 episodes over a full year, the
> index is **not stable in k**: 1.22 at k=500, 1.02 at k=2,000, 0.93 at k=5,000. "α ≈ 1.15" was
> one depth on 6,546 episodes; the honest statement is **α ∈ [0.9, 1.2] depending on tail
> depth**. What survives unchanged: α < 2 everywhere, and the gap to the fill-based index. The
> claim above holds; its single number does not.
>
> The 3.8× inflation figure also **rose to 5.72×** on the unbiased sample — the "may be slightly
> high" caveat below pointed the wrong way.

That is the difference between "extreme events dominate everything" and "extreme events are
manageable". A risk model calibrated on fill counts would conclude the second while the market
is in the first.

Concentration agrees: the **top 1% of fills carries 30.7%** of liquidated notional, the top 5%
carries 61.8%, the top 10% carries 76.6%.

**What holds without qualification:** the 3.8× factor, its robustness across unit definitions,
the growth of tranching with size, the measured compression, and the tail-index gap.

## What CEX feeds actually count — checked, not assumed

The section above originally said this bias "may not apply" to CEX feeds and that it "has not
been checked". It has now been checked, against venue documentation.

| venue | stream | publishes | limitation |
|---|---|---|---|
| **Binance** | `forceOrder` | **orders** | *"only the **largest one** liquidation order within 1000ms will be pushed as the snapshot"* (since April 2021) |
| **OKX** | `liquidation-orders` | orders | at most **one update per second per contract** |
| **Bybit** *(old)* | `liquidation` | orders | at most 1/s per symbol — **deprecated** |
| **Bybit** *(current)* | `allLiquidation` | **all liquidations** | complete, pushed every 500 ms |

**The fill-counting bias does not transfer.** CEX feeds publish *orders*, not fills, so there is
no tranching to inflate. Flagging it as unverified was correct.

**But a heavier problem exists there.** Binance does not publish a sample of liquidations — it
publishes a sequence of **per-second maxima**. That is a different statistical object:

- **event counts are unrecoverable** — nothing states how many liquidations each snapshot
  suppressed;
- **the body of the distribution is destroyed** — small liquidations never appear;
- **the tail index may survive**. Block maxima are a *valid* EVT approach, and a block maximum
  inherits the tail index of its parent distribution. So Binance data can yield a roughly
  correct tail and a worthless count.

That nuance matters: it does not invalidate everything built on these feeds, it invalidates
specific things — anything resting on counting events, or on the shape of the body.

**Caveat.** Lim (2026) works minute-level on Binance and Bybit, but the paper has not been read
here and it is unknown which streams it uses or what it concludes from them. Nothing above is a
claim about that work — only about what the data can support.

### Consequence for Hyperliquid as a substrate

| | completeness | native unit |
|---|---|---|
| Hyperliquid node fills | **complete, per-user** | fill → aggregate to episode |
| Bybit `allLiquidation` | complete since Feb 2025 | order, anonymous |
| Binance / OKX | **per-second maxima** | truncated order |

Hyperliquid is the only venue publishing a complete *and named* record — `liquidatedUser`,
`startPosition`, `closedPnl`. That is what makes the α ≈ 1.15 estimate above hard to reproduce
elsewhere: fitting a tail index needs the body as well as the tail, and Binance withholds it.

> The defensible claim: on Hyperliquid's node-fills archive, counting fills overstates event
> counts ~3.8× and compresses the size tail from α ≈ 1.15 to α ≈ 2.05. The correct unit is the
> (user, transaction) episode, and that choice is robust. On CEX feeds the failure mode is
> different and, for counting purposes, worse.

## Limits

- 12 hours over 10 months. Spread deliberately, but not a census.
- Selection includes two known heavy-cascade hours, which raises the share of large episodes
  relative to a uniform sample. The *within-bucket* statistics are unaffected; the aggregate
  3.8× may be slightly high.
- All-asset aggregate. HIP-3 builder perps dominate liquidation counts in some hours and may
  tranche differently from majors.

## Next

1. ~~Re-run retaining per-fill notionals~~ — **done**; compression is measured and the tail
   index is fitted above.
2. Split majors from HIP-3 assets — the mechanics may differ.
3. ~~Check what venue-published CEX feeds actually count~~ — **done**, see above. The fill
   bias does not transfer; a block-maxima bias applies there instead.
4. Whether the α ≈ 1.15 estimate is stable across assets and over the archive's full year —
   12 hours is not a census, and the tail index is the load-bearing number now.
