# EXP-025 — Can liquidation tranches be identified at all, and do they move the price?

**Status:** run. **P1 confirmed — tranches are identifiable, and the instrument works.
P2 rejected: the documented 30-second cooldown leaves no trace in the timing even once
tranches are located correctly. P3 and P4 are statistically overwhelming and
NOT INTERPRETABLE**, for the reason §1(a) predicted before the run.
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

Run on the **corrected** collection (`event[0] == liquidatedUser`); the first pass double-counted
every fill and its position accounting was incoherent — 11 runs out of 19,933 satisfied
`cumsum(sz) = P₀ − startPosition`. On corrected data that check passes **19,811 / 20,000**, which
is itself the strongest validation the fix received.

### P1 — confirmed. The 20% rule is identifiable.

Of 8,781 pauses inside a forced close, **70.8%** fall within ±0.02 of a multiple of 0.2, against
**16.3%** under a uniform null. The histogram is not subtle: 53% of all pauses sit in the single
bin 0.15–0.20, with a second peak at 0.35–0.40.

**Position accounting works where elapsed time failed.** That is the reusable result of this
experiment: a venue mechanism invisible in the timing of a public record is recoverable from its
position arithmetic.

### P2 — rejected. The cooldown is not there.

Among 7,963 closes above \$100k split into more than one tranche (17,896 transitions):

| gap between tranche boundaries | share |
|---|---|
| under 2 s | **75.3%** |
| 2–25 s | 15.9% |
| **25 s and over** | **8.8%** |

Median **0.0 s**. Three quarters of tranche boundaries are crossed inside a continuous sweep of
the book, not after a wait. The 20% slicing is real; the 30-second cooldown that the
documentation attaches to it is not visible in the record, by timing or by position accounting.

### P3 and P4 — confirmed, and unusable

Signed so that positive means the liquidated account executes worse:

| | n | mean | median | % adverse |
|---|---|---|---|---|
| all transitions | 17,896 | **+15.3 bps** | +1.3 | 80.1% |
| continuous (< 2 s) | 13,471 | +11.2 | +0.9 | 82.2% |
| **gapped (≥ 25 s)** | 1,578 | **+59.8** | **+42.1** | **94.9%** |
| gapped (≥ 60 s) | 1,276 | +61.6 | +43.3 | 96.2% |

Difference between gapped and continuous: **+48.6 bps**, Mann-Whitney p ≈ 0, Welch t = +23.9.
Impact also declines monotonically with tranche index (+23.7, +12.9, +6.3, +4.8 bps;
Spearman −0.20, p < 0.001), so P4's registered prediction holds.

**None of this can be read as the market pricing in announced flow**, and §1(a) said so before
the data existed. A second tranche is sent only if the account is *still* below maintenance
margin after the first executed. A 25-second-plus gap followed by another tranche therefore
exists **precisely when the price moved against the account during that gap**. The 42 bps median
is the condition for the observation to exist, not a consequence of it.

The §4 claim that within-close comparison "handles the selection by design" was **too strong**.
It holds for continuous transitions, which are pieces of one order and unselected. It fails for
gapped ones, which are exactly the selected subset. That distinction was not drawn in the
pre-registration and is a defect in it.

### What would separate the two

The ambient price move over the same window for the same instrument, from all fills rather than
liquidation fills alone — the "second, targeted pass" §5 describes and deliberately did not
launch. Anticipation predicts that the gapped move exceeds the ambient move; selection predicts
it does not. Roughly 5 GB over the 346 archive hours that contain these closes.

Until that runs, the honest statement is: **the price moves 42 bps against the account during a
cooldown gap, and we cannot yet say whether that is the market or the margin engine.**

## 7. What this experiment produced

- A working instrument: tranche boundaries from `startPosition` and `sz` (P1).
- A negative result on a documented mechanism: the 30-second cooldown is not observable in the
  venue's own complete fill record (P2).
- A measured effect that is real and uninterpretable, with the specific data that would resolve
  it named and costed.
- And, incidentally, the bug that halved the paper's headline — found because this experiment
  needed a column the collector had thrown away.


---

## 8. Addendum — pre-registered 2026-07-27, before the ambient pass runs

> Written after §6 and **before any ambient price data exists**. The collection is launched
> after this file is committed.

### Why a simple ambient comparison would settle nothing

The obvious control — compare the price move during a cooldown gap to the move over a matched
window with no liquidation — **cannot discriminate**. The gapped transitions are selected on
adverse movement (§1a), so they will exceed any unselected control by construction, under either
hypothesis. Running that comparison would produce a large, significant, meaningless number.

### The test that does discriminate: reversion after the close

Selection acts on *why tranche k+1 exists*. It says nothing about what the price does **after the
forced close has finished**. That window is uncontaminated, and the two hypotheses part company
there:

- **Anticipation** — the market pushed price ahead of flow it knew was coming. That is
  liquidity provision under pressure, and it is **temporary**: once the flow stops, price
  reverts.
- **Selection** — price moved for exogenous reasons, which is why the account stayed underwater.
  Exogenous moves are information and **do not revert**.

### Measurement

For each multi-tranche close above \$100k (n = 7,963; 1,536 with a gap ≥ 25 s), from the ambient
trade series of the same instrument:

- `A` = adverse move during the close, `t₀ → t₁`, signed so positive is against the account.
- `R(k)` = reversion at `t₁ + k` seconds, `k ∈ {30, 60, 300}`, signed so **positive means price
  came back** toward its pre-close level.
- Reported as the ratio `R(300) / A` — the share of the move that was temporary.

Closes are split on their **largest inter-tranche gap**: continuous (< 2 s) against gapped
(≥ 25 s). Ambient prices come from *all* fills of that instrument, not liquidation fills.

### Predictions

- **P5 (discriminating).** Gapped closes revert **more** than continuous ones, as a share of
  their own adverse move: `R(300)/A` is higher for the gapped group, difference significant at
  5%. *That is anticipation: the extra 42 bps is temporary pressure, not news.*
- **P6.** Both groups show some reversion (`R(300)/A > 0`), since any marketable sweep has
  temporary impact.

### Falsification

- **P5 false, equal reversion** — the extra move in gapped closes is as permanent as the rest.
  Then the 42 bps is **exogenous price movement that caused the second tranche**, the selection
  reading is correct, and there is no anticipation to report. This is the outcome §1(a) implies
  and it must not be softened.
- **P5 false, reversed** — gapped closes revert *less*. Stronger still for selection: the gap
  coincided with genuine news.
- **P6 false** — no reversion anywhere. Then the ambient series is too coarse to measure
  reversion at all, and the experiment reports a measurement failure rather than a finding.

### What is claimable either way

Whatever P5 returns, **P1 and P2 stand on their own**: tranches are identifiable from position
accounting, and the documented 30-second cooldown is not observable in the venue's complete fill
record. Those do not depend on this addendum.
