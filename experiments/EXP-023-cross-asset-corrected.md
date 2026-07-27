# EXP-023 — Cross-asset lead-lag on corrected coverage, and the within-asset regression

**Status:** pre-registered, not yet run
**Registered:** 2026-07-27
**Author:** monproweb / Quasareum
**Script:** `experiments/exp021_recovered_hours.py --coin {ETH,SOL,HYPE}` + a new analysis
**Data:** perplog tape, 2026-07-18 → 07-26, venues `hl / binance / okx`

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets
> reported.

---

## 1. Why

[EXP-012](EXP-012-cross-asset.md) established the 550–575 ms lag as a venue constant on
576 asset-hours. It ran on hours selected by perplog's `gapped` coverage flag, which
[EXP-021](EXP-021-recovered-quiet-hours.md) showed to be **95.9% false positives** on BTC
over the same window. Re-deriving completeness from the tape took BTC from 144 usable
hours to 191, with the headline unchanged.

ETH, SOL and HYPE were never re-derived. This does that, and then runs the test EXP-012
listed as its own Next item 1.

## 2. Part A — the cross-asset table, corrected

Run `exp021_recovered_hours.py` on ETH, SOL and HYPE: fetch every hour in the window
regardless of flag, classify completeness from the tape by the cross-venue criterion
(a venue was down only if another kept printing through its silence), and run the same
Hayashi-Yoshida scan. BTC is reused from EXP-021.

This is confirmatory, not exploratory — the instrument and the estimator are unchanged,
only the hour selection is fixed.

## 3. Part B — the within-asset regression

EXP-012 found, across **four points**:

```
corr( ln(HL trades/h), median peak ) = −0.630
```

and called it a hypothesis rather than a result, correctly. The less an asset trades on
Hyperliquid, the longer its measured lag — which is what **observability** predicts, and
would be the first purchase on the mechanical/informational decomposition that has been
stuck since EXP-010.

The test EXP-012 named: regress τ on trade frequency **hour by hour within each asset**,
where there are ~190 points per asset instead of 4 across all of them.

**One tension, registered before running.** EXP-021 measured Spearman(`range_bps`, peak)
= **−0.099** over 191 BTC hours — the lag is invariant to volatility. Hourly trade count
and hourly range are strongly correlated. If the lag is invariant to one, it is likely
invariant to the other, and P4 below will fail.

That would not make the cross-asset correlation wrong. It would make it a **between**-
instrument effect that does not reproduce **within** an instrument — the standard shape
of an ecological correlation, and physically coherent: observability would depend on an
instrument's *structural* print rate, not on whether a given hour happened to be busy.
Both outcomes are informative, which is why the prediction is worth making either way.

## 4. Predictions

- **P1.** Each of ETH, SOL and HYPE gains usable hours, ending between 180 and 193 —
  matching BTC's 191, since the flag is uncorrelated with anything asset-specific.
- **P2.** The cross-asset ranking is unchanged: BTC, ETH and HYPE within 500–650 ms,
  SOL highest.
- **P3.** τ > 0 in **100%** of corrected asset-hours, as in all 576 before.
- **P4 (load-bearing).** Within each asset, Spearman(ln(hourly HL trades), peak) is
  **negative and significant** (p < 0.05) — the observability relation reproduces inside
  an instrument.

## 5. Falsification

- **P4 false** — no within-asset relation. The −0.630 was four points in a line. The
  observability lead is withdrawn as a route to the decomposition, and the honest
  restatement is that it operates between instruments and not within one. **This is the
  outcome the tension in §3 predicts, and it must not be softened if it arrives.**
- **P3 false** — a single reversal anywhere. That is a bigger event than anything else
  here: 576 asset-hours without a counterexample is the strongest form of the claim, and
  one reversal on corrected data would make it a tendency rather than a property.
- **P2 false** — an asset moves out of its band once its quiet hours are restored. Then
  the venue-constant reading narrows to the hours the old filter happened to keep.
- **P1 false** — an asset gains nothing. Then the flag *was* asset-specific and EXP-021's
  conclusion that it is noise needs qualifying beyond BTC.

## 6. Success criterion

Part A succeeds by producing a cross-asset table on hour selection that is defensible,
whatever it says. Part B succeeds by **settling whether observability is measurable
within an instrument** — a negative answer closes a lead that has been quoted as
promising since EXP-012, and closing it is worth as much as confirming it.

## 7. Results

*(empty until the experiment runs)*
