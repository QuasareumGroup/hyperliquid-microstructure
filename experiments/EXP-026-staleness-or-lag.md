# EXP-026 — Is the 575 ms an information lag or a sampling artefact?

**Status:** run. **P1 confirmed decisively, P2 and P3 confirmed, P4 rejected on 3 of 4 assets.**
The 575 ms is **not** manufactured by sparsity — but sparsity **inflates** it, so the measured
value carries an upward bias of unknown size. Result 1 survives its most adversarial test.
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
| perplog book (`.pbs`), HL | WS `l2Book` depth-20, **thinned to 2 s on write** | **no** — 2 s cannot resolve 575 ms |
| perplog book (`.pbs`), Binance | WS `depth20@500ms` — a **venue-imposed grid** | **no**, and no setting fixes it |
| HL `bbo`, Binance `bookTicker` | native, push-on-change, **no grid either side** | **yes — and neither is subscribed** |

> **Correction, 2026-07-27.** This table first read "BBO not recorded — the recorder subscribes to
> `trades` only". That is **wrong**: `perplog-recorder` also runs a book path (`book_venues.rs`)
> subscribing to HL `l2Book` and Binance partial depth. The conclusion survives, the reason does
> not, and the real reason is sharper. Two distinct obstacles, only one of which is ours:
> perplog thins books to `RECORDER_BOOK_INTERVAL_MS` (default 2 000, clamp floor 250) — that one
> is a config change; but Binance publishes partial depth **on a fixed 500 ms grid**, which no
> configuration touches. Measuring a 575 ms lead-lag on two series where one is gridded at 500 ms
> is not a resolution one can buy back. The BBO channels avoid both: HL's `bbo` and Binance's
> `bookTicker` are documented push-on-change with no interval. See method rule 12.

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

84 hours across four assets, sampled evenly through the window. Test C was not launched — see §8.

### P1 — confirmed, and it is the result that matters

Binance shifted by a known lag, then thinned to Hyperliquid's actual print times for the same
hour. Median recovered peak:

| imposed | BTC | ETH | SOL | HYPE |
|---|---|---|---|---|
| **0 ms** | **0** | **0** | **25** | **0** |
| 100 ms | 100 | 100 | 125 | 100 |
| 300 ms | 300 | 300 | 312 | 300 |
| 575 ms | 575 | 575 | 575 | 575 |
| 1000 ms | 1000 | 1000 | 1025 | 1000 |

On BTC, ETH and HYPE the recovery is **exact in every hour** — interquartile range zero. On SOL,
the sparsest instrument at 2,051 prints per hour, errors reach 25 ms, still half the registered
tolerance.

**The line that decides it is `L = 0`.** Impose no lag, thin the follower to HL's print
cadence, and the estimator returns **zero**. It does not drift toward 575 ms, or toward anything.
Whatever produces Result 1, it is not the estimator inventing a lag from unequal observation
rates.

### P2 and P3 — confirmed. Sparsity inflates the estimate.

Real HL measured against a Binance thinned to HL's own cadence:

| | HL prints/h | unthinned | thinned | change |
|---|---|---|---|---|
| BTC | 12,500 | 562 ms | 600 ms | **+38** |
| HYPE | 6,700 | 525 ms | 550 ms | **+25** |
| ETH | 4,672 | 562 ms | 750 ms | **+188** |
| SOL | 2,051 | 625 ms | 838 ms | **+212** |

The peak never collapses, so P2 holds at every asset. And it moves **up** in all four, as P3
registered with its reason: coarser observation biases a lag estimate away from zero. The
sparsest instruments shift most.

**This is the finding worth carrying forward, and it cuts against us.** Sparsity does not create
the lag, but it does exaggerate it. Hyperliquid's own prints are sparse, so the 575 ms measured
against a dense Binance plausibly carries an upward bias of its own. How large is **not
measured** — Test B makes the *leader* sparse, which is not the same experiment as making the
*follower* dense, and nothing here quantifies the latter.

### P4 — rejected on 3 of 4

Rank correlation between thinned and unthinned peaks across hours: BTC +0.328 (p = 0.117),
ETH +0.353 (p = 0.127), HYPE +0.272 (p = 0.247), SOL +0.605 (p = 0.005). Thinning does not merely
shift the peak, it adds hour-to-hour noise. The registered claim that it "does it consistently"
is wrong for the three denser assets.

### One limitation of Test A, stated because it bounds the conclusion

The synthetic follower is a deterministic shift of the leader — same price path, sampled
sparsely. It therefore tests whether sparsity alone creates lag between series that are otherwise
identical. It does **not** test the case where the follower has its own price innovations, which
is what Hyperliquid actually is. A stronger version would add independent noise to the follower
before thinning. Not run.

## 8. What this settles, and what it does not

**Settles:** Result 1 is not a sparsity artefact. The estimator recovers zero when zero is
imposed, at HL's real observation density, on every asset. The most damaging explanation
available for the 575 ms is eliminated.

**Does not settle:** whether the lag is mechanical or informational — the original question. It
narrows it: observation density is out, so what remains is block cadence, network latency, and
genuine price discovery. And it adds a new caveat, that the *magnitude* is inflated by an
unmeasured amount.

### Test C is now sized — 2026-07-28

`exp026_bbo_probe.py` opened both native BBO channels for 120 s and counted, writing nothing to
disk. Per second, and per day if run continuously:

| | HL `bbo` | Binance `bookTicker` | quote asymmetry | trade asymmetry |
|---|---|---|---|---|
| BTC | 7.9/s | 183.5/s | **23×** | 2.9× |
| ETH | 7.2 | 285.7 | **40×** | 5.1× |
| SOL | 4.8 | 125.5 | **26×** | 2.9× |
| HYPE | 6.4 | 96.9 | **15×** | 2.4× |

**Cost.** 718 msg/s combined, 12.5 GB/day arriving as JSON, **≈2.0 GB/day encoded** at 32 B per
record and before compression — 60 GB/month, or **28 GB for a two-week window**. Tractable, and
worth sizing rather than assuming on a machine with a history of filling up.

**A warning the sizing produced for free.** Quotes are far *more* asymmetric between the two
venues than trades are — 15× to 40× against 2.4× to 5.1×. Test C will therefore measure a much
sparser follower against a much denser leader than Result 1 does. That is survivable rather than
fatal, because EXP-027 and EXP-028 have since established that follower sparsity does not bias
this estimator, but it is the reason Test C should not be read as the *easier* measurement.

**Hyperliquid's quotes update about 7.9 times a second on BTC**, roughly once per block. That is
one update per ~127 ms, against a 575 ms lag — so block cadence is not on its own an explanation,
and it is the likely reason Hyperliquid's trade arrival is so weakly coupled to price movement
(EXP-028 Part 1).

**Test C was not launched**, and it is smaller than §3 implied. It does not need a new recorder:
`perplog-recorder` already has the venue-shard machinery, and what is missing is two
subscriptions — HL `bbo` and Binance `bookTicker`, both push-on-change. It is still calendar-
bound, which is the whole argument for starting it before anything else here: an hour not
recorded is an hour that cannot be recovered later at any price.

It also remains the only route to the question that decides whether Result 1 is worth a second
paper. If HL's *quotes* trail Binance's by ~575 ms, resting orders sit at stale prices and there
is something there. If the quotes track and only the *prints* trail, then the lag is about when
trades happen rather than what prices are available — no stale book, nothing to take, and a more
interesting result than the first reading. Both outcomes are publishable; neither is reachable
from trades.
