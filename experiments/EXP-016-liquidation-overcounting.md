# EXP-016 — What is "one liquidation"? Fill-counting inflates 3.8×, and flattens the tail

**Status:** run. The inflation factor is **robust to how a liquidation is defined**, is
**strongly size-dependent** (2× typical, 67× for the top 1%), and fill-counting **compresses the
size distribution**.
**Date:** 2026-07-26
**Data:** `s3://hl-mainnet-node-data/node_fills_by_block` — 24,566 liquidation fills across
12 hours sampled over 10 months (2025-10 → 2026-07).
Script `experiments/exp016_liquidation_units.py`, per-episode output
`experiments/data/exp016_units.csv`.

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

Apparent per-fill size versus true episode size:

| quantile | true | apparent | factor |
|---|---|---|---|
| p50 | $661 | $926 | 0.7× |
| p90 | $18,259 | $11,229 | 1.6× |
| p99 | $214,474 | $37,401 | **5.7×** |
| p99.9 | $1,969,302 | $125,310 | **15.7×** |

Largest real episode **$3,838,207**; largest apparent fill **$242,127**.

> Fill-counting does not merely inflate the *number* of liquidations — it **destroys the tail of
> the size distribution**. A $3.8M liquidation appears as ~40 fills of ~$95k. Any study of
> cascade severity or forced-deleveraging tail risk built on fill counts understates the tail by
> close to an order of magnitude.

### Two caveats, one of which bounds the result

**The compression factor is an upper bound.** "Apparent size" assumes fills within an episode
are **equal-sized**. They are not — an observed sequence ran 0.239 / 0.109 / 0.099 / 0.096 …
If one fill dominates, the largest apparent fill approaches the true episode size and the real
compression is *smaller* than 16×. Settling it needs per-fill notionals, which this run did not
retain.

**No tail index is reported.** The Hill estimator written for this run returned 0.00 on both
series — it mixes scales and is wrong. Rather than report a broken statistic, it is omitted;
the tail index needs doing properly.

**What holds without qualification:** the 3.8× factor, its robustness across unit definitions,
and the growth of tranching with size. All three are measured directly.

## Why this might matter beyond Hyperliquid

Existing cascade work (e.g. Lim 2026, minute-level Binance/Bybit) rests on venue-published
liquidation feeds. Those are throttled and anonymised rather than fill-level, so this specific
bias may not apply to them — **that has not been checked and should not be assumed**. The
defensible claim today is narrower and still useful:

> Anyone building liquidation statistics from Hyperliquid's node-fills archive by counting fills
> overstates event counts ~3.8× and compresses the size tail. The correct unit is the
> (user, transaction) episode, and the choice is robust.

## Limits

- 12 hours over 10 months. Spread deliberately, but not a census.
- Selection includes two known heavy-cascade hours, which raises the share of large episodes
  relative to a uniform sample. The *within-bucket* statistics are unaffected; the aggregate
  3.8× may be slightly high.
- All-asset aggregate. HIP-3 builder perps dominate liquidation counts in some hours and may
  tranche differently from majors.

## Next

1. Re-run retaining per-fill notionals, to replace the upper-bound compression figure with a
   measured one and to fit a tail index properly.
2. Split majors from HIP-3 assets — the mechanics may differ.
3. Check what venue-published CEX feeds actually count, before any claim about the wider
   literature. Not assumed here.
