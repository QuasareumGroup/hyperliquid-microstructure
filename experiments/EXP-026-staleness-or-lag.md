# EXP-026 — Is the 575 ms an information lag or a sampling artefact?

**Status:** pre-registered, not yet run
**Registered:** 2026-07-27
**Author:** Thomas Erhel / Quasareum
**Data:** perplog tape, BTC/ETH/SOL/HYPE, 2026-07-18 → 07-26, venues `hl / binance / okx`
— already collected, no new download.

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets reported.

---

## 1. The question, and why the obvious experiment is not available

Result 1 says Binance leads Hyperliquid by a median 575 ms in 100% of 758 asset-hours.
FINDINGS open item 1 asks how much of that is mechanical and how much is price discovery. The
same question, asked commercially, is whether anything can be done with it.

**The decisive measurement would be on quotes, not trades.** If Hyperliquid's *book* lags
Binance's by 575 ms, there are resting orders at stale prices. If only its *prints* lag, the last
traded price is merely old and there is nothing to take. Trades and quotes answer different
questions and we have only trades.

**That measurement cannot be made from existing data**, and it is worth recording why:

| source | cadence | usable for a 575 ms question |
|---|---|---|
| perplog tape (`.pfr`) | trades, median gap **266 ms** on HL/BTC | yes, and it is what Result 1 uses |
| perplog book (`.pbs`) | REST keyframes, **~2 s** | **no** — cannot resolve below ~4 s |
| BBO | **not recorded** — the recorder subscribes to `trades` only | — |

So this experiment attacks the same question with the data that exists, and separately starts the
capture that would answer it properly.

## 2. The mechanism under test

Hyperliquid prints every 266 ms at the median; Binance prints far more often. Hayashi-Yoshida is
built for asynchronous observation and needs no grid — that is why EXP-010 chose it. But "needs
no grid" is not "immune to sparsity". If a peak at 575 ms can be produced by unequal observation
rates alone, Result 1 measures the venue's print cadence rather than its price discovery.

**EXP-010 validated the estimator to zero error against known lags. It did not validate it at
the observation density of this data.** That is the gap.

## 3. Three tests

### Test A — does the estimator survive HL's sparsity? *(gating)*

Take Binance's own series for an hour. Build a synthetic follower by shifting it by a **known**
lag `L ∈ {0, 100, 300, 575, 1000} ms`, then **thin it to Hyperliquid's observed print times for
that same hour** — so the follower is exactly as sparse as HL, with a lag we chose.

Run the unmodified estimator. It must recover `L`.

*If it does not — if thinning alone shifts the recovered peak toward 575 ms — then Result 1 is an
artefact of sparsity and the whole of it comes down.* This is the gate: nothing below matters if
Test A fails.

### Test B — impose HL's sparsity on Binance

Thin the **real** Binance series to HL's print times and re-measure the HL/Binance lag.

Under an information lag, HY handles asynchrony and the peak should be roughly unchanged. Under a
sampling artefact, making both series equally sparse should collapse it.

### Test C — start the capture that settles it

Launch a BBO recorder for `hl / binance / okx`, native cadence, into
`experiments/data/bbo/`. It answers nothing today; it accumulates the only data that can
distinguish a stale book from a stale print. Reported separately when a week exists.

This is deliberately additive rather than duplicative: `perplog-recorder` records trades and
2-second book keyframes, not BBO. Recording it is also a perplog gap worth closing.

## 4. Predictions

- **P1 (gating).** Test A recovers every known `L` to within **±50 ms**, including `L = 0`,
  under HL-density thinning. *A recovered peak near 575 ms at `L = 0` would falsify Result 1
  outright.*
- **P2.** In Test B the peak stays above **400 ms** — thinning Binance does not collapse it.
- **P3.** The recovered peak in Test B **rises** relative to the unthinned 575 ms rather than
  falling, because removing Binance observations removes the fine structure that locates the
  peak, and coarser observation biases a lag estimate away from zero, not toward it.
- **P4.** Across the four assets, the Test-B peak tracks the unthinned peak with rank
  correlation above **+0.5** — whatever thinning does, it does consistently.

## 5. Falsification

- **P1 false** — the estimator manufactures a lag from sparsity. **Result 1 is withdrawn**, the
  paper that would rest on it is not written, and this becomes the most consequential experiment
  in the repository. Nothing else here is examined.
- **P2 false, peak collapses** — the 575 ms is an artefact of unequal observation rates. Result 1
  narrows to "HL prints late", which is a statement about the venue's trading frequency and not
  about price discovery. No tradeable reading survives.
- **P3 false** — thinning moves the peak *down*. That would contradict the mechanism assumed in
  P2's reasoning and mean neither direction is understood; report and stop rather than pick a
  story.

## 6. What this can and cannot settle

It can rule out the sparsity explanation, or establish it. It **cannot** show that Hyperliquid's
book is stale, because no book data at this resolution exists yet — only Test C's capture will.

Result 1's headline does not depend on the outcome: 100% of 758 asset-hours with zero reversals
is a fact about the estimator's output either way. What is at stake is its **interpretation**,
and whether the second paper can be written.

## 7. Results

*(empty until the experiment runs)*
