# EXP-032 — Test C: do Hyperliquid's quotes trail, or only its prints?

**Pre-registered 2026-08-03**, eight days before the read. **Author:** Thomas
Erhel / Quasareum. Written by Claude Science.

**Why this document exists.** EXP-026 §7 calls this "Test C's registered
measurement", and paper 2 reserves \S\ref{sec:quotes} for it. Neither carries a
prediction with odds. The capture has been running since 2026-07-28 and is read
on 2026-08-11 into a paper submitted the same day — so the odds have to be
written now or not at all. This is that document, and it registers nothing that
requires touching the archive.

**Seal position.** A021's §5 forbids relating any predictor to any post-07-28
price. This is a lead–lag measurement between two venues' quote series with no
predictor and no forecast; A021 §5 names paper 2's Test C explicitly as *not*
forbidden. Nothing here is computed today.

---

## 1. The question, and why it decides the paper's meaning

Result 1 measures a **575 ms** Hyperliquid lag on **trade prints** (bootstrap
95% CI on the median $[550, 575]$, mean 607 ms, 100% of 191 measured hours,
zero reversals). Prints and quotes answer different questions:

- **If quotes trail too**: resting orders sit at stale prices. The lag is
  something a participant could act on, subject to fees.
- **If quotes track and only prints trail**: the book is current and the last
  traded price is merely old. Nothing to take — and, as EXP-026 §8 puts it, the
  more interesting result of the two.

Both outcomes are publishable. The paper is written to absorb either without
restructuring.

## 2. Instrument and data — what will be read, decided now

- **Archive**: `quote/v1/{venue}/{coin}/{date}/{hh}.pbq` on R2, BTC/ETH/SOL/HYPE
  × {hl, binance}, `RECORDER_QUOTE_INTERVAL_MS=0` (push-on-change, no grid).
  Capture opened 2026-07-28; first sealed hour verified at the time
  (`avg levels 1.0/1.0, crossed 0, non-monotonic 0` on all eight streams).
- **Window**: 2026-07-28 through 2026-08-10 inclusive — **whole days only**,
  ending the day before the read so no partial final hour enters. The realised
  hour count is reported, not assumed.
- **Price**: BBO **mid** = (bid+ask)/2 per update. Not microprice, not
  last-trade. Fixed here because "which price" is the kind of choice that
  otherwise gets made after seeing three versions of the answer.
- **Estimator**: Hayashi–Yoshida, identical to Result 1 — 25 ms grid over ±2 s,
  τ > 0 means Binance leads. Same code path, no re-tuning. Per asset-hour, as
  in Result 1, so the two results are comparable hour for hour.
- **Exclusions, fixed in advance**: hours where either stream has a gap > 60 s
  (recorder restart), and hours with fewer than 200 HL updates on the asset.
  Both counts reported.

**The known hard part.** On quotes the venues differ in observation rate by
**12.4× to 33.8×** (measured, EXP-026 §7: BTC 7.3 vs 137/s, ETH 4.8 vs 162,
SOL 3.9 vs 49, HYPE 4.1 vs 51) against roughly 3× on trades. EXP-026 §7
validated the estimator at an asymmetry **24× worse** than the trade case and it
recovered imposed lags of 0/100/300/575/1000 ms exactly, zero included. The
instrument is checked for this regime; the answer was deliberately not computed.

## 3. Predictions, with odds, before the data is touched

- **P1 (60%) — the quote peak is positive and above 200 ms.** Binance leads on
  quotes too. Rationale: block cadence is a floor under any Hyperliquid update,
  quote or print, and EXP-031 established the chain is not the bottleneck but
  the cadence is real.
- **P2 (45%, the one that decides the reading) — the quote peak lands within
  ±150 ms of the print peak, i.e. inside [425, 725] ms.** If quotes and prints
  trail by the same amount, the lag is a venue-level property rather than a
  print artefact. Deliberately under 50%: I do not have a mechanism that
  requires the two to agree, and the density asymmetry is an order of magnitude
  worse here.
- **P3 (25%) — the quote peak is below 100 ms while the print peak stays near
  575.** This is the "prints only" world. Registered low because block cadence
  makes a near-zero quote lag hard to produce, not because it would be
  unwelcome — it is the more interesting outcome.
- **P4 (70%) — no sign reversal in any qualifying asset-hour.** Result 1 had
  zero reversals in 191 hours on prints. Quotes are noisier and the sample is
  smaller, so this is registered below the print result's unanimity.
- **P5 (registered to fail, 15%) — the peak differs by more than 300 ms across
  the four assets.** If the quote lag is a venue property it should be roughly
  common; wide dispersion would mean the estimator is picking up something
  asset-specific and the section needs rewriting rather than filling in.
- **P6 (80%) — at least 150 qualifying asset-hours survive the §2 exclusions.**
  14 days × 24 h × 4 assets = 1,344 asset-hours before exclusions. This is a
  data-integrity prediction, not a result: failing it means the recorder had
  gaps I do not know about.

**Multiplicity, stated in advance.** Six predictions, one window, one estimator,
one price definition. P2 and P3 are mutually exclusive and jointly incomplete —
the residual (peak between 100 and 425, or above 725) is unclaimed at 30%, and
if it lands there the honest report is that neither registered story fits.

**Coherence, checked before registering** — A017's odds were incoherent in
exactly this way (a subset carrying more mass than its superset), so this set was
audited rather than assumed. P2's interval sits inside P1's half-line (425 > 200)
and 45 ≤ 60. P3 is disjoint from P1 and 25 ≤ 40, the mass P1 leaves. P2 ∩ P3 = ∅
and their sum is 70. **The tight consequence, named rather than left implicit:**
that leaves only 15% for a peak between 100 and 200 ms — a real commitment, made
because block cadence should keep any Hyperliquid update off the near-zero
range, not an artefact of the other numbers.

## 4. What each outcome costs

| outcome | consequence for paper 2 |
|---|---|
| P2 holds (quotes trail like prints) | \S\ref{sec:quotes} reports a venue-level lag; \S\ref{sec:implications} keeps the actionability discussion, still fee-bounded. **The +575 ms is not tradeable at 9 bps taker** — A001 killed that and this does not revive it. |
| P3 holds (prints only) | \S\ref{sec:quotes} reports that the book is current. The result becomes about *when trades happen*, not what prices are available. Stronger paper, weaker trading story, and \S\ref{sec:implications} needs its actionability paragraph cut rather than softened. |
| Residual (unclaimed 30%) | Report the number and say plainly that neither registered prediction fits. Do not construct a third story after the fact. |
| P6 fails (<150 hours) | The section says so and reports on what exists. A thin sample is a limitation, not a reason to widen the window after seeing it. |

## 5. What this cannot settle

- **Not the mechanical-vs-informational split.** Paper 2 \S\ref{sec:limits}
  already restricts that claim to *our* instrument: neither venue's BBO stream
  sees an order being submitted. Albers et al. publish submission timestamps for
  one venue, which is not a cross-venue instrument. Test C narrows the question;
  it does not close it.
- **Not tradeability.** A quote lag is not an edge. A001 measured the print
  version dead through taker fees, and A024's arithmetic is the general lesson:
  a real effect can die on costs and capacity without any statistical problem.
- **Not causality.** Hayashi–Yoshida locates a cross-correlation peak. It is a
  timing measurement, and the paper says so.
- **One regime.** Two summer weeks, four assets.

## 6. Results

*(empty until 2026-08-11 — the read fills this section and adjudicates P1–P6.
Do not rewrite §3.)*
