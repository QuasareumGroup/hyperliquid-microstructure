# EXP-024 — Size compression at year scale: does the 12-hour measurement hold?

**Status:** pre-registered, collection running, **no output inspected**
**Registered:** 2026-07-27
**Author:** monproweb / Quasareum
**Script:** `experiments/exp017_year_tail.py --fills-out ...` (per-fill output added today)

> Written *before* any result is read. The collection was launched a few minutes
> before this file, because it takes roughly an hour and the script is unchanged
> apart from an additional output column; **no row of its output has been looked
> at.** The predictions below concern the analysis, which is not yet written.

---

## 1. Why

The size-compression result — fill-counting compresses the liquidation size distribution by
3.4× at p99 and 10.9× at p99.9 — rests on the **12-hour sample**, because the year-scale
collection reduced to episodes and discarded per-fill notionals. Every other headline is
year-scale. This is the one gap flagged in the preprint's Limitations and the only item left
before submission.

The 12-hour sample also has a known defect: two of its twelve hours were chosen because they
contained cascades, which over-represents large episodes. [EXP-017](EXP-017-year-tail.md) already
showed what that did to the *count* inflation — the 12-hour figure was 3.8×, hedged in EXP-016 as
possibly "slightly high", and the unbiased year gave **5.72×**. The hedge pointed the wrong way.

## 2. Predictions

- **P1 (control).** The re-collected episode file reproduces the published one: 351,540 episodes
  and 2,010,042 fills, within 0.1%. *If it does not, the archive is not stable and everything
  downstream needs re-examining before anything else is read.*
- **P2.** Compression is confirmed at year scale and still grows monotonically with the quantile
  — p50 < p90 < p99 < p99.9.
- **P3 (the interesting one).** The year-scale factors at p99 and p99.9 are **larger** than the
  12-hour values of 3.4× and 10.9×. Reasoning, registered so it can be wrong: compression is
  produced by tranching, tranching is stronger on the unbiased sample (5.72× against 3.8×), so
  compression should follow. **This is the same shape of prediction EXP-016 got backwards**, and
  it is stated in the direction its correction implies.
- **P4.** Majors and HIP-3 compress similarly, consistent with EXP-017 finding tail behaviour to
  be a property of the liquidation mechanism rather than of the market.

## 3. Falsification

- **P1 false** — stop. Nothing else in this file is worth reading until the discrepancy is
  explained.
- **P3 false in the other direction** (year-scale compression *smaller*) — then compression and
  count inflation do not move together, the cascade bias affects them oppositely, and the
  mechanism I just gave for P3 is wrong. Report it and say so.
- **P3 false by being equal** — the 12-hour figure was unbiased after all, which would be worth
  knowing given how badly the equivalent hedge failed for the count.
- **P2 false** — non-monotone compression would mean the quantile-by-quantile framing is wrong,
  not merely imprecise.

## 4. Method

Compression is measured the way EXP-016 measured it: the empirical quantiles of the *episode*
notional distribution against the empirical quantiles of the *fill* notional distribution, both
computed on the same fills. No model, no fitting. The two distributions have different lengths by
construction — that is the point — so this compares curves, not paired observations.

Reported for all instruments, and split majors / HIP-3.

**Consistency check before anything is read:** every episode's notional must equal the sum of its
fills' notionals, joining on `(coin, user, ts = ep_ts)`, and the number of fill rows must equal
the sum of the episode file's `fills` column. Verified on one hour before launch (30 episodes,
162 fills, zero mismatches).

## 5. What this settles

If P2 and P3 hold, the preprint's compression table becomes year-scale like the rest of it and
the last submission blocker closes. If P3 fails, the table still becomes year-scale — the
correction is to the number, not to the claim.

## 6. Results

*(empty until the analysis runs)*
