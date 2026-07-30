# EXP-031 — the anatomy of Hyperliquid's clock

**Status: run 2026-07-30. H1 confirmed — the chain is exonerated. H2 and H3 infirmed: at a symmetric native-tick construction the venues couple comparably, so my 70/30 informational bet was wrong, and the asymmetry paper 2 reports is specific to its cross-venue movement proxy — which its own text states, and which nothing here contradicts.**
**Author:** Thomas Erhel / Quasareum

> Paper 2's "two venues, two clocks" section reports that Hyperliquid's trade
> arrival barely tracks volatility (Spearman +0.06–0.17 against absolute
> return) while Binance's tracks it strongly (+0.28–0.77), and says plainly
> that it does not settle whether the asymmetry is mechanical or
> informational. This experiment is built to settle as much of that as the
> public record can.

---

## 1. What a schema probe established before registration

A reconnaissance pass over the fills archive (200 blocks of one hour, schema
only — no estimand computed) established three facts that shape the design:

1. **Each archive line is a block**, carrying `block_number`, `block_time`
   and `local_time` in the clear. Blocks need no inference.
2. **Fills are block-stamped**: within a line, 100% of fills share the
   block's timestamp. Trade time *is* block time, by construction.
3. **The cadence is ~68 ms — roughly 15 blocks per second.** This kills the
   naive quantization story before it is tested: at ~900 execution slots per
   minute, block granularity cannot bind minute-scale trade counts. Whatever
   the two-clocks asymmetry is, it is not coarse quantization, and the
   hypotheses below are framed accordingly.

## 2. Sample — committed

**2026-07-21 → 2026-07-25** (five days, 120 hours), BTC, ETH, SOL, HYPE.
Hyperliquid from `node_fills_by_block` (blocks and fills); Binance from the
perplog tape. Entirely pre-holdout: no post-07-28 byte is touched, and
nothing here relates any predictor to any price — the estimands are
arrival-process properties.

## 3. Hypotheses and thresholds

**D1 (descriptive, reported not tested).** The block-cadence distribution:
median, IQR and tail of inter-block gaps; and the `local_time − block_time`
observation lag distribution — the node's own latency, relevant to paper 2's
mechanical-latency discussion.

**H1 — the chain's pulse is exogenous.** Consensus, not load, paces blocks:
per-minute Spearman between absolute HL return and blocks/minute lies in
**[−0.10, +0.10]** in all four coins. *(If this fails — cadence responds to
volatility — the chain itself is part of the two-clocks story, and that is a
finding about HyperBFT under load.)*

**H2 — where the gap lives.** Decompose HL's per-minute fill count into the
extensive margin (non-empty blocks per minute) and the intensive margin
(fills per non-empty block). Committed claim: the volatility coupling runs
through the **intensive margin** — Spearman(vol, fills per non-empty block)
exceeds Spearman(vol, non-empty blocks/min) in ≥ 3 of 4 coins.

**H3 — central: does the gap survive at block resolution?** Match the
measurement clocks: HL's fills-per-block against Binance's trades per 68-ms
bucket, each correlated with its own venue's within-minute absolute return.
Committed ratio: HL's coupling reaches **less than 50%** of Binance's in
≥ 3 of 4 coins — i.e., **the asymmetry is substantially informational, not
plumbing.** *(Registered prediction at ~70/30, reversing my pre-probe lean:
with 15 blocks a second, plumbing has nowhere left to hide the gap.)*

## 4. What each outcome does to paper 2

- **H3 holds** — the two-clocks section upgrades from observation to
  mechanism: the venue's flow genuinely responds less to information, and
  the clock is exonerated. One paragraph, stronger claim.
- **H3 fails** (coupling converges at block resolution) — the asymmetry was
  measurement aggregation after all; the section gets corrected before
  submission rather than after, and the mechanical reading of the residual
  lag gains weight.
- **H1 fails** — a new finding outranking the original question: block
  production on this chain responds to market state. That would be its own
  section, and worth checking against the Oct 10 2025 stress record.

## 5. What this cannot settle

Flow *composition* (retail vs automated) is invisible here; "informational"
means "not explained by the clock", not a behavioral attribution. Five days,
one regime. And the Binance 68-ms bucketing is an approximation of a
continuous venue onto HL's grid — reported alongside a 1-second variant as
robustness.

## 6. Amendments

**2026-07-30, at implementation, before any data was read** — H3 as first
written ("each correlated with its own venue's *within-minute* absolute
return") is scale-invariant under per-minute averaging: Spearman ranks are
unchanged by dividing a minute's fill count by a near-constant block count,
so the registered construction would collapse into exactly the minute-scale
coupling paper 2 already publishes — a tautology, not a test.

Operationalization, fixed now: **H3 runs at the native tick.** Per unit —
one block for Hyperliquid, one 68-ms bucket for Binance — Spearman between
the unit's event count and the absolute last-price change across that unit,
pooled over the window, restricted to units with at least one event on that
venue (zero-event units are 80%+ of HL blocks and would inject a mechanical
(0,0) tie mass that differs across venues; their shares are reported as
descriptives instead). Same committed ratio: HL under 50% of Binance in
≥ 3 of 4 coins. The minute-scale construction is still computed, as a
sample check that this window reproduces paper 2's published ranges — not
as a hypothesis.

---

## 7. Results (2026-07-30)

### D1 — the venue's pulse, measured

6,045,296 blocks over the five days. **Median gap 67 ms** (IQR 64–74,
p99 136) — the ~15 blocks/second of the probe, confirmed at scale. The
archive node observes blocks **194 ms after block time** (p99 231 ms) — a
useful bound on observation latency for any consumer of this archive. Empty
blocks per coin: BTC 89.3%, ETH 95.2%, SOL 97.6%, HYPE 94.4%.

### H1 CONFIRMED — the chain is exonerated

Spearman(|return|, blocks/min): **+0.028 / +0.042 / +0.047 / +0.037** — all
four inside the registered [−0.10, +0.10] band. Block production does not
respond to market state. Whatever the two-clocks asymmetry is, the consensus
layer is not it.

### H2 INFIRMED (2/4)

The intensive margin (fills per non-empty block) beats the extensive
(non-empty blocks per minute) on BTC and HYPE only; ETH and SOL run the
other way, and all eight correlations sit in a narrow +0.28–0.50 band. No
clean margin story — the coupling spreads across both.

### H3 INFIRMED (2/4) — and my 70/30 was wrong

At the native tick, own-venue moves, active units only:

| | HL per block | BN per 68 ms | ratio |
|---|---|---|---|
| BTC | +0.219 | +0.339 | 0.65 |
| ETH | +0.160 | +0.471 | **0.34** |
| SOL | +0.199 | +0.055 | 3.63 |
| HYPE | +0.319 | +0.707 | **0.45** |

Only ETH and HYPE clear the <0.5 ratio. Under a symmetric construction,
Hyperliquid's activity couples to its own price movement at the same order
as Binance's — **the "informational asymmetry" reading I registered at 70/30
does not hold.** (SOL's Binance-side coupling of +0.055 is its own oddity,
reported, not explained.)

### The sample check failed — and the failure was mine, resolved

The minute-scale check returned HL couplings of +0.37 to +0.54 against paper
2's published +0.06–0.17. Before touching the paper, its construction was
read: **paper 2 uses one-second bins and the leader's return as the movement
proxy for both venues** — deliberately, "so that no venue's activity is
measured against its own observed returns." The check as implemented here
used minutes and own-venue returns: a different estimand, mechanically
inflated for the sparse venue. **No replication failure occurred; the check
was mis-specified**, and this is recorded as amendment-grade rather than
silently dropped.

### What this settles

Assembled: the chain's pulse is exogenous (H1); at its own tick the venue's
activity tracks its own price formation about as well as Binance's does
(H3's failure); and paper 2's asymmetry lives precisely where its text puts
it — in the coupling of each venue's activity to *market* movement as
measured at the leader. Hyperliquid's clock is locally coupled and
market-decoupled; its chain is innocent. Paper 2 gains two sentences of
mechanism (cadence + exoneration) and needs no correction.

The wrong bet is the record's point: registered at 70/30 for
"informational", measured to "comparable under symmetric construction."
