# EXP-025 — Can liquidation tranches be identified at all, and do they move the price?

**Status:** pre-registered, collection running, **no output inspected**
**Registered:** 2026-07-27
**Author:** Thomas Erhel / Quasareum
**Script:** `experiments/exp017_year_tail.py --with-prices` (per-fill price, size and position)

> Written *before* any result is read. The collection was launched minutes before this file
> because it takes about forty minutes and the collector change is mechanical; **no row of its
> output has been looked at.**

---

## 1. Why — and why the obvious version of this experiment is dead

Hyperliquid closes positions above 100,000 USDC in **20% chunks with a 30-second cooldown**
between them ([EXP-024](EXP-024-year-fill-notionals.md) §, venue documentation). If that holds,
then when the first chunk hits the book the remaining forced flow is **predictable in both size
and timing** — the rare case of a market where a large, directional order is announced by
mechanism rather than inferred. Whether the price drifts ahead of it is a real question.

**The first design was wrong and would have produced a guaranteed, meaningless result.** It took
the 2,200 chains of consecutive same-account-same-instrument episodes (≤ 90 s apart) to be the
cooldown's tranches, and proposed measuring price drift between them. Two objections, found
before running anything:

**(a) Selection on the outcome.** A second chunk is sent only if the account is *still* below
maintenance margin after the first executed. So a chain exists precisely when the price moved
against the account during the cooldown. Measuring "price drift between tranches" on chained
episodes conditions on the very thing being measured. Of 17,075 episodes above $100k, only
**14.1%** chain — the mechanism does not fire on the rest, and what separates the two groups is
not size (median $307k vs $187k, identical median fill counts).

**(b) The chains are not the cooldown.** Their timing carries no trace of a 30-second wait:

| gap | share |
|---|---|
| 5–10 s | **21.5%** (the mode, at the floor imposed by the 5 s episode rule) |
| 10–25 s | 15.9% |
| 25–40 s | **6.0%** |
| > 60 s | 47.2% |

Monotone decay from the 5-second floor, no mode at 30 s. Restricting to chains whose first
episode exceeds $1M — where the rule should bind hardest — gives the same shape (7% in
[25, 40] s). A 30-second minimum wait should produce a *deficit* of short gaps; instead short
gaps dominate. **What the 5-second episode rule is splitting is mostly continuous liquidation
activity with natural lulls, not protocol tranches.**

The paper's §5.2 previously called the size contrast "a useful check that we are seeing what the
documentation describes"; that attribution is withdrawn, and the negative timing result is
reported in its place.

## 2. The instrument that can work: position accounting

Elapsed time cannot separate a tranche boundary from a lull. **Position size can.** Every fill in
the archive carries `startPosition` (the account's position in that instrument before the fill),
`sz`, `px`, `dir` and `closedPnl`. Within one forced close, `|startPosition|` decreases
monotonically by `sz` at each fill. A chunk that stops at 20% of the original position is
therefore visible as an arithmetic fact, independent of how long the pause that follows lasts.

**Tranche definition, fixed now:** within a maximal run of liquidation fills for one
(account, instrument) — grouped at a deliberately loose 10-minute gap so no boundary is imposed
by time — let `P₀` be the first fill's `|startPosition|`. A tranche boundary falls at the fill
after which cumulative closed size crosses a multiple of **0.20 × P₀**, within a tolerance of
±0.02 × P₀ to absorb rounding and partial fills.

This is testable before it is used: if the 20% rule operates, closed-size fractions should
**cluster at 0.2, 0.4, 0.6, 0.8, 1.0**. If they are uniform, the rule is not visible in position
data either, and the experiment stops at that finding.

## 3. Predictions

- **P1 (gating).** Cumulative closed-size fractions at pauses cluster at multiples of 0.2:
  the share within ±0.02 of a multiple exceeds **40%**, against ~20% expected under a uniform
  null. *If P1 fails, nothing below is measurable and the experiment reports that.*
- **P2.** Among positions above $100k that are closed in more than one tranche, the **median
  time between tranche boundaries is ≥ 25 s** — the cooldown appearing once tranches are
  identified correctly rather than by elapsed time.
- **P3 (the question).** Within a multi-tranche close, the **volume-weighted execution price of
  tranche k+1 is worse for the liquidated account than tranche k**, by more than the
  within-tranche impact of tranche k. That is the signature of the market pricing in the
  announced remaining flow.
- **P4.** The per-tranche adverse move **shrinks** with tranche index — later tranches cost less
  because the price has already adjusted.

## 4. Falsification

- **P1 false** — position accounting shows no 20% structure. Then the documented rule is not
  identifiable in the public record by any means we have, and that is the result: a venue
  mechanism that cannot be observed in the venue's own complete fill data. Report and stop.
- **P3 false, no drift** — the market does not price the announced flow. Interesting: a
  predictable, mechanically-announced order flow that is *not* anticipated would be a genuine
  inefficiency statement, and the honest one to make.
- **P3 false, reversed** — later tranches execute *better*. Would suggest liquidity replenishes
  faster than the flow arrives, and would contradict the cascade intuition.
- **P4 false while P3 holds** — impact growing with tranche index means book depletion beats
  anticipation. Also a result, and the one with the clearest risk-management reading.

**The selection problem of §1(a) is handled by design, not by caveat**: every comparison in P3
and P4 is *within* a single forced close. Whether that close was tranched at all is the selected
variable; the relative execution of its own tranches is not.

## 5. Data

Re-collection of the same 1,460 stratified hours, retaining `px`, `sz`, `startPosition` and
`dir` per liquidation fill — the first pass multiplied price by size and discarded both. Roughly
50 GB of requester-pays egress, inside the free monthly allowance, about forty minutes.

An ambient price series, needed to separate tranche impact from market drift, is a **second,
targeted pass** over the 346 archive hours that contain chains (~5 GB), extracting all fills for
the 117 affected instruments. It is not launched now: P1 must hold first, and if it does not,
that pass is never needed.

## 6. Results

*(empty until the analysis runs)*
