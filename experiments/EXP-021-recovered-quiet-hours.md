# EXP-021 — Does the 575 ms lag hold on the quiet hours the gap filter discarded?

**Status:** pre-registered, not yet run
**Registered:** 2026-07-26
**Author:** monproweb / Quasareum
**Script:** `experiments/exp021_recovered_hours.py` (not written yet)

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets
> reported.

---

## 1. Why

EXP-011 measured 144 hours out of the 216 available in the window
2026-07-18 → 07-26. The other 72 were dropped because perplog's coverage endpoint
reported them `gapped`, and `exp011_hy_all_hours.py:100` takes the **union** across
`hl`, `binance` and `okx` — one venue flagging an hour removes it for all three.

That flag has since been found to be a false positive in a specific and biased way.
perplog marked a gap on **every reconnect**, computing `missed_ms = now − last_event`.
What that measures is the interval since the last message, which during an idle period
is **market silence, not downtime**. Hyperliquid has the lowest event rate of the three
venues, so it produced the most spurious flags — today's counts over the same window
are HL **43**, OKX 19, Binance 6.

The consequence is not a smaller sample. It is a **sample biased toward active hours**,
on precisely the axis EXP-009 and EXP-011 claim invariance over. FINDINGS.md currently
says the result "survives volatility regimes"; it was established on a volatility
distribution missing part of its low end. The claim may well be true — it has simply
not been tested where the filter was blindest.

## 2. What the fix does and does not do

perplog's recorder has been corrected. That correction is **forward-looking**: the
`gapped` flags for July 2026 were written at record time and are stored metadata, so
they still carry the old false positives. Today's union over the three venues yields
**165 usable hours against EXP-011's 144** — 21 recovered, not the ~46 a retroactive
clean-up would give.

**Therefore this experiment does not trust the flag.** Trusting a corrected flag on
uncorrected historical data would repeat the original error with more confidence.
Completeness is established from the tape.

*(For perplog: a backfill recomputing coverage from the stored tape would fix this at
the source and is the cleaner remedy. Out of scope here.)*

## 3. Instrument: completeness from the tape, cross-venue

Downtime and silence are indistinguishable within one venue. They are trivially
distinguishable **across** venues: during a genuine outage the other venues keep
recording; during a quiet market they fall silent together.

For every (venue, date, hour) in the window — **all 216, whatever the flag says** —
decode the tape and compute `n_events`, `max_silence_ms`, and the event timestamps.

An hour is classified:

| class | criterion |
|---|---|
| **absent** | fetch fails, or the payload lacks the `PFR1` magic. A true absence. |
| **incomplete** | contains a silence window `[t₀, t₁]` with `t₁ − t₀ ≥ 60_000 ms` during which **another venue's event rate is ≥ 25% of its own median rate for that hour**. The market was live; this venue was not. |
| **complete** | everything else, including hours flagged `gapped` whose silences are matched by silence elsewhere. |

The 25% rate ratio is scale-free and deliberately lenient: it should catch real
outages without reclassifying a genuinely thin market as downtime.

**Recovered hours** := flagged `gapped`, classified **complete**. These are the
subject of the experiment.

**Validation before use, per method rule 5.** The classifier is run first on hours
where the answer is known: hours EXP-011 already used (must classify **complete**),
and synthetic hours built by deleting a known 5-minute span from a complete tape
(must classify **incomplete**). A classifier that fails either is fixed before any
result is read.

## 4. Predictions

- **P1.** At least 70% of HL's 43 flagged hours classify **complete** — the flag is
  mostly false positives.
- **P2 (load-bearing).** Recovered hours are **quieter** than the 144 retained ones:
  strictly lower median `range_bps` and strictly lower median HL event count.
  *This is the mechanism claim. Everything above rests on it.*
- **P3.** On recovered hours meeting the power floor, Binance still leads Hyperliquid
  in **100%** of them, with a median peak lag in **[400, 750] ms**.
- **P4.** Over the extended sample (retained + recovered), Spearman correlation between
  hourly `range_bps` and peak lag stays within **±0.20** — volatility invariance holds
  across the widened range.

**Power floor.** Quiet hours have fewer trades, and Hayashi-Yoshida gets noisier as
the tape thins. Any hour with fewer than **200 HL trades** is reported separately and
excluded from P3/P4, because a null there would be a power problem masquerading as an
effect. EXP-014 showed sparsity does not explain the *level* of the lag; it says
nothing about the variance of the estimate on a thin hour.

## 5. Falsification

- **P2 false** — recovered hours are *not* quieter. Then the exclusion was not
  correlated with market activity, EXP-011's sample was not biased on that axis, and
  the diagnosis in §1 is wrong. It gets retracted in FINDINGS.md and this file, and the
  remaining value of the run is the 21 extra hours.
- **P3 false** — the lag breaks down or reverses on quiet hours. **This is the
  interesting outcome.** It would mean the lead-lag depends on the activity regime,
  which reopens EXP-008 — retracted by EXP-009 as a grid artefact — on evidence that is
  not a grid artefact. It would require restating result 1 conditionally.
- **P4 false** — invariance fails once the low-volatility tail is present. The
  invariance claim narrows to the range actually measured, and FINDINGS.md says so.
- **P1 false** — the flags were mostly correct and perplog really was losing ~20% of HL
  hours. That is an infrastructure finding for perplog, not a research one, and it gets
  handed over rather than pursued here.

## 6. Success criterion

Success is **a lead-lag claim whose stated scope matches the range it was tested on** —
either widened because it held, or narrowed because it did not. Not "the result
survived".

The secondary deliverable is the tape-based completeness classifier itself. Coverage
metadata that a venue writes about its own recording cannot distinguish silence from
downtime; a cross-venue check can. That is reusable beyond this experiment.

## 7. Results

*(empty until the experiment runs)*
