# EXP-003 — Is the premium-sign regime flip a real phenomenon?

**Status:** closed. **The flip is largely the market cycle.** No structural finding survives.
**Date:** 2026-07-26
**Data:** `data/ctx_hourly/` — 1,137 days, 4.17M asset-hours, live assets only.

---

## Background

FINDING-001 surfaced, unplanned, that "perp-rich" hours (premium above the clamp band, so
longs pay more) collapsed from 51.0% / 55.6% in 2023Q4–2024Q1 to 1.8% – 2.7% through 2026.
It was described there as the most interesting thing in the file. EXP-002 rejected the
delta-neutral-capital explanation. This experiment tests the two remaining candidates.

## Test A — composition

**Hypothesis.** The universe grew from 100 assets (2023Q4) to 191 (2026). If newly listed
assets systematically trade at a discount, the aggregate flips with no asset changing
behaviour.

**Prediction P1:** on a fixed cohort present in both periods, the flip disappears or
strongly attenuates.

Fixed cohort = 75 assets live in both 2023Q4 and 2026:

| quarter | full universe | fixed cohort |
|---|---|---|
| 2023Q4 | 51.0% | 50.0% |
| 2024Q1 | 55.6% | 56.6% |
| 2024Q2 | 14.9% | 15.5% |
| 2025Q4 | 3.4% | 1.7% |
| 2026Q1 | 1.8% | **0.4%** |
| 2026Q2 | 2.7% | **1.0%** |

**P1 rejected.** The cohort tracks the universe to within a point and falls *further* in
2026. The same 75 assets went from 50% perp-rich hours to 1%. Composition explains nothing.

## Test B — market cycle *(this is the one that should have been run first)*

**Hypothesis.** Perps trade rich when there is directional long demand. 2023Q4–2024Q1 was a
strong bull leg; 2025–2026 mostly was not.

| quarter | BTC/ETH quarterly return | perp-rich % |
|---|---|---|
| 2023Q4 | +46.5% | 51.0% |
| 2024Q1 | +63.4% | 55.6% |
| 2024Q4 | +37.8% | 31.1% |
| 2025Q1 | −28.9% | 5.9% |
| 2026Q1 | −25.9% | 1.8% |
| 2026Q2 | −17.4% | 2.7% |

**`corr(perp-rich %, quarterly major return) = 0.786`** over 13 quarters.

**Confirmed.** The "structural regime flip" is mostly the market cycle. The original
characterisation in FINDING-001 was overstated and was carried for several hours before
being tested.

## Test C — the residual: has premium sensitivity to returns declined?

Two quarters resisted Test B: 2025Q2 (+33.0% return, only 4.7% perp-rich) and 2025Q3
(+36.2%, 12.2%). Comparable returns produced 3–6× less premium than in 2023–24. Candidate:
the premium's sensitivity to directional flow collapsed.

**Specification.** Daily panel, `premium ~ β · return`, demeaned within (coin, quarter) so
level differences between assets cannot produce β. Liquid assets only (`vlm > $1M/day`).

**Prediction P1:** β declines over time by more than its standard error.

| quarter | β (bps per 100% daily return) | t | **R²** |
|---|---|---|---|
| 2023Q2 | +26.5 | 6.9 | 0.063 |
| 2023Q4 | −8.3 | −1.5 | 0.001 |
| 2024Q1 | +20.3 | 12.1 | 0.021 |
| 2024Q4 | +19.7 | 18.0 | 0.042 |
| 2025Q1 | −15.6 | −9.9 | 0.012 |
| **2025Q2** | **+17.0** | 10.7 | 0.015 |
| 2025Q3 | −27.0 | −13.3 | 0.020 |
| 2026Q1 | **−70.3** | −18.5 | 0.051 |
| 2026Q2 | −13.7 | −6.7 | 0.007 |

**P1 not supported.** β does not decline — it flips sign and oscillates. 2025Q2 at +17.0
sits between −15.6 and −27.0, which destroys any monotone story. There is a level shift
between 2023–24 (mostly positive) and 2025–26 (mostly negative), but with a large exception
inside it and no stable trend.

### A mechanical explanation that was not excluded

Negative β means premium moves opposite to the perp's own return. Premium is
`(impact price − oracle) / oracle`, and the oracle is the **weighted median of CEX spot
prices**. If the oracle leads and the Hyperliquid perp follows, then on a rise the oracle
moves first, the perp sits temporarily below it, and premium turns negative while the return
measured on the perp is positive — **β negative by construction.**

This specification cannot separate the two: it regresses a daily *average* premium on a
change in daily *average* price, mixing horizons. Settling it requires regressing on
**oracle** returns, intraday, with an explicit lead-lag structure. That is a real experiment,
not a query.

---

## Two method rules earned here

**1. Test the boring confound first.** The exotic explanations were tested first
(delta-neutral capital in EXP-002, composition in Test A) and the obvious one — the market
cycle — last. It was the cheapest to check and the most likely to be true. The wrong order
cost a day of scaffolding on a phenomenon that mostly was not one.

**2. In a large panel, the t-statistic measures your sample size; R² measures your finding.**
Test C returns t = −18.5 alongside R² = 0.051. With n ≈ 8,000, an economically negligible
effect yields overwhelming significance. A t of −18.5 writes a convincing abstract; an R² of
0.05 says you know nothing. **Report R² beside every t, and disbelieve any panel result whose
case rests on the t alone.**

## Consequence for FINDING-001

Its "unplanned observation that survives" does not survive. FINDING-001 should be read as
what it is: a validated dataset plus an exactly reproduced controller. The regime flip it
flagged is explained.

## Day tally

Seven hypotheses tested, seven dead — six of them ours. What stands: the dataset
(99.23% bit-exact controller reproduction over 1.58M live asset-hours) and a method that
kills bad ideas quickly.
