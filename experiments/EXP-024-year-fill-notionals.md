# EXP-024 — Size compression at year scale: does the 12-hour measurement hold?

**Status:** run. **P1 and P2 confirmed. P3 confirmed where the data can resolve it and silent
where it cannot. P4 rejected** — majors and HIP-3 compress differently, and they cross over.
The compression table is now year-scale, which closes the last blocker on the preprint.
**Registered:** 2026-07-27 · **Run:** 2026-07-27
**Author:** Thomas Erhel / Quasareum
**Scripts:** `experiments/exp017_year_tail.py --fills-out ...`, `experiments/exp024_analyse.py`
**Data:** `experiments/data/exp024_fill_notionals.csv.gz` (2,010,314 fills) and — since the
adversarial review — `experiments/data/exp024_episodes.csv.gz` (351,648 episodes, the second
pass) plus the interval code `experiments/exp024_ci.py`. Together they reproduce every quantile
and interval below. *(Until the review, the episode side required an uncommitted file and the
CI code was never versioned — findings B2/B4, `review/FABLE.md`.)* The full joinable per-fill
file is 119 MB and is not committed; see §7.

> **Current position: [FINDINGS.md](FINDINGS.md).** This file keeps its original
> pre-registration wording plus results; the state of claims lives there.

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

### Review note (2026-07-27)

The two-pass agreement below was described as holding "to three decimal places"; it holds at
the precision quoted in the paper (the inflation factor is 5.7178 vs 5.7168 — two decimals, not
three). The "0.03% more" figure conflated episodes (+0.031%) and fills (+0.014%).

### P1 — confirmed, with a small non-zero difference worth naming

| | re-collected | published | difference |
|---|---|---|---|
| episodes | 351,648 | 351,540 | **+0.031%** |
| fills | 2,010,314 | 2,010,042 | **+0.014%** |

Inside the registered 0.1% tolerance, and the reconciliation closes exactly: the fill file has
precisely as many rows as the sum of the episode file's `fills` column, **0** episodes fail the
notional check, **0** episodes have no fills.

The difference is not zero, though, and pretending otherwise would be the wrong habit: 108 more
episodes and 272 more fills appeared between the two runs. The archive is append-only for a given
hour, so the likely cause is late-arriving blocks written after the first pass read those hours.
Not investigated. It is 3 parts in 10,000 and changes no figure below.

### P2 — confirmed

Compression grows monotonically with the quantile: 2.00 → 3.26 → 4.58 → 10.02.

### P3 — confirmed where the data can resolve it

Bootstrap 95% intervals, 20,000 draws. (Naively resampling 2M values per draw was intractable;
the intervals use the binomial representation of the bootstrap quantile, so one sort replaces
every resample.)

| quantile | episode | fill | **factor** | 95% CI | 12-hour | verdict |
|---|---|---|---|---|---|---|
| p50 | \$1,117 | \$558 | **2.00** | [1.97, 2.03] | 1.6 | **larger** |
| p90 | \$39,288 | \$12,046 | **3.26** | [3.21, 3.31] | 2.1 | **larger** |
| p99 | \$548,922 | \$119,919 | **4.58** | [4.41, 4.76] | 3.4 | **larger** |
| p99.9 | \$5,834,505 | \$582,486 | **10.02** | [9.24, 11.21] | 10.9 | indistinguishable |
| max | \$194,115,094 | \$10,990,000 | 17.7 | — | 4.3 | — |

At p50, p90 and p99 the year-scale factor is larger and the interval excludes the twelve-hour
value. **The prediction holds, and the reasoning behind it holds**: compression is produced by
tranching, tranching is stronger on the unbiased sample, compression followed.

At p99.9 the point estimate is *lower* (10.02 against 10.9) but the interval spans it. There is
no finding there in either direction — 0.1% of 351,648 episodes is 352 observations, and the
interval says so.

**A note on the verdict logic, which was too coarse.** `exp024_analyse.py` required *both* p99
and p99.9 to be larger and printed `P3 REJECTED (mixte)`. That reading was wrong: it treated a
point estimate inside its own confidence interval as evidence against. The script's rule was
committed before the run, which is the right discipline, but a rule stated on point estimates
cannot express "no answer here." Recorded rather than quietly overridden.

### P4 — rejected. The segments compress differently, and they cross over.

| quantile | majors | HIP-3 | ratio | 95% CI | |
|---|---|---|---|---|---|
| p50 | 2.01 | 1.90 | 1.06 | [1.03, 1.09] | **different** |
| p90 | 3.26 | 2.51 | **1.30** | [1.24, 1.36] | **different** |
| p99 | 4.48 | 5.49 | **0.82** | [0.74, 0.90] | **different** |
| p99.9 | 10.88 | 12.84 | 0.85 | [0.65, 1.11] | indistinguishable |

Majors compress **more** in the body, HIP-3 compresses **more** in the tail, and the crossover
sits between p90 and p99. Three of four intervals exclude 1.

**This does not contradict EXP-017; it is a different statistic.** EXP-017 found the tail *index*
statistically indistinguishable between the segments, and concluded that tail behaviour is a
property of the liquidation mechanism rather than of the market. Compression is not a tail
property — it is produced by how a position is sliced against a book, and HIP-3 books are
thinner. A thin book tranches a large position into more, smaller pieces, which is exactly the
observed direction. The mechanism claim survives; the claim that the segments behave identically
*on every measure* does not, and FINDINGS.md is corrected accordingly.

### An observation, not a finding

The largest single fill is **\$10,990,000** exactly, and only **4** fills exceed \$10M across two
distinct values. A round number at the top of a 2-million-observation distribution is the shape
of a cap or a block trade rather than of a market. Not pursued, and no result here depends on it.

## 7. On the published artifact

The full per-fill file is **119 MB** and joinable to the episode file on `(coin, user, ts=ep_ts)`.
It is not committed. What is committed is `experiments/data/exp024_fill_notionals.csv.gz` —
`(hip3, notional)` for all 2,010,314 fills, **5.6 MB** — which reproduces every quantile in this
file, for every segment, exactly. Verified after writing.

The full file regenerates with:

```
python experiments/exp017_year_tail.py \
  --out /tmp/ep.csv --fills-out /tmp/fills.csv
```

roughly 50 GB of requester-pays egress and about 40 minutes at 8 workers.

## 8. Limits

- Same stratification as EXP-017: four fixed hours per day. Uniform in time; a cascade falling
  entirely outside those hours is invisible.
- The p99.9 and max rows rest on hundreds and on single observations respectively. The max
  compression of 17.7× is one episode against one fill and carries no uncertainty statement.
- The 0.03% drift between collections is unexplained. It is small enough not to matter here and
  large enough that a study needing exact reproducibility should pin an archive snapshot.
- Compression is measured as a ratio of marginal quantiles, not per episode. It answers "how much
  smaller does the observed size distribution look", which is the question, but it is not a
  statement about any individual liquidation.
