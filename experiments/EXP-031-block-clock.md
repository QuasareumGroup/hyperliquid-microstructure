# EXP-031 — the anatomy of Hyperliquid's clock

**Status: PRE-REGISTERED, not yet run.** Registered 2026-07-30.
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

*(none yet)*
