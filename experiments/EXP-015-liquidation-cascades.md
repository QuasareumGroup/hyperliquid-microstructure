# EXP-015 — Does the lead invert during liquidation cascades?

> ## ⚠ Correction — 2026-07-27 : le double comptage des fills
>
> **Every figure below that counts fills was overstated by exactly 2.00.** The
> `node_fills` archive records a liquidation trade **twice** — once for the liquidated
> account, once for the counterparty — and *both* records carry
> `liquidation.liquidatedUser`. The account whose fill it is sits in `event[0]`, which
> neither collector read. Verified on 38 hours spread across the year: ratio 2.0000
> everywhere, minimum and maximum.
>
> Corrected: fills and notionals halve, **episode counts do not change** (both sides share
> the same key), so the inflation factor halves. Ratios of fills to fills, and every
> scale-invariant quantity, are unaffected.
>
> The numbers in the body of this file are the original, wrong ones and are kept as the
> record. **[FINDINGS.md](FINDINGS.md) carries the corrected state.**


**Status:** run. **P1 rejected — no inversion.** The venues *decouple* during cascades instead.
Also corrects how ρ has been reported since EXP-010.
**Date:** 2026-07-26
**Data:** HL node fills archive (`s3://hl-mainnet-node-data/node_fills_by_block`) for
liquidation events; perplog tape for prices. BTC, 8 cascade windows and 8 matched controls.

---

## Prior art (checked first)

- **Lim (2026), "Anatomy of a Crypto Cascade"** (SSRN 6579278) — **minute-level** Binance and
  Bybit data on the October 2025 crash. Five stylised facts, including that **futures led the
  crash** and that the mark price created reflexive feedback loops.
- Event studies of the 2025-10-10/11 cascade (~$19B open interest erased in 36h).
- [arXiv:2512.01112](https://arxiv.org/pdf/2512.01112), *Autodeleveraging* — theoretical.

**Not found:** any tick-level study, any using a per-user liquidation record, anything specific
to Hyperliquid, and no discussion of the fill-versus-liquidation overcounting below.

**Caveat, and it is not decoration.** Novelty was claimed once today after searching the wrong
literature (FINDING-001). This search covers crypto microstructure; traditional market-
microstructure journals may cover it better. Treat the opening as **probable, not established**.

Note also that Lim's "futures led the crash" is the CEX-level cousin of this question. Venue-vs-
venue during a cascade appears open; the general direction question does not.

## The data

Hyperliquid's node fills archive carries, per liquidation fill:

```
liquidation.liquidatedUser   the liquidated address
liquidation.markPx           mark price at trigger
liquidation.method           market | backstop
startPosition                position size before
closedPnl                    realised loss
```

365 days available (2025-07-27 → 2026-07-26), complete rather than sampled. CEX feeds publish
an anonymised, throttled subset.

### Measurement finding: counting fills overstates liquidations 3.4×

Over 6 hours (2026-07-20), 7,508 liquidation fills resolve to:

| | |
|---|---|
| distinct liquidated users | 2,062 |
| **(user, transaction) pairs — one liquidation** | **2,220** |
| fills per liquidation | median 2, mean **3.4**, max **202** |
| distinct counterparties absorbing them | **656** |

One position unwound in tranches appears as up to 202 events. Any dataset counting fills
inflates liquidation counts by ~3.4×.

*Getting there took two self-corrections: reading a 44-fill burst as one user (true that hour,
not in general), then grouping by `hash` assuming one hash = one liquidation (a hash is a
transaction and can carry several).*

## The test

**P1** — the lead narrows or inverts during cascades: forced selling originates on Hyperliquid.
**P2** — no change. **P3** — it widens.

Cascade windows: ±60 s around the highest-notional liquidation minutes. Controls: same hour,
matched on |return|, liquidation notional < $10k. Hayashi-Yoshida per window.

The four hours used are all flagged `gapped` by the coverage API except one; each was verified
complete first (60.0 min coverage, max inter-print gap 3–12 s) — see the false-positive finding
in EXP-008/009 follow-up.

| | cascade | control |
|---|---|---|
| median peak τ | **638 ms** | 575 ms |
| median ρ at peak | **~0.35** | **~0.78** |
| n | 8 | 8 |

**P1 rejected.** No inversion. The 638 vs 575 ms difference is not interpretable: cascade peaks
scatter from 400 to 1,700 ms across 8 windows.

**The signal is in the other column.** Coupling roughly halves during cascades. That is not
"Hyperliquid leads" — it is **Hyperliquid decoupling**: forced selling moves its price in a way
Binance does not follow, consistent with a transient dislocation.

Combined with EXP-011 and EXP-012, the follower position now holds across assets, volatility
regimes, and cascades.

## Correction: ρ is not a correlation coefficient

Three control windows returned **ρ = 1.003, 1.054, 1.340**. A correlation cannot exceed 1.

The Hayashi-Yoshida normalisation `sqrt(Σrx² · Σry²)` does not bound the statistic the way
Pearson does, because one Binance return can be counted against several overlapping Hyperliquid
intervals. Over a full hour it stays below 1; over 2-minute windows it does not.

> **Retroactive to EXP-010.** The "ρ" quoted since then is a **normalised cross-statistic**,
> valid for *relative* comparison at equal window length — which is what the cascade/control
> comparison above does — but not readable as "53% correlation".

**Unaffected: the peak location.** That is the validated quantity (zero error against known
lags, EXP-010) and every headline result rests on it. The ~550 ms stands; only the label on its
strength was wrong.

## Limits

- **8 windows.** Enough to reject an inversion, not to size the decoupling.
- ρ needs replacing with a genuinely bounded statistic before the decoupling is quantified.
- One asset, two days.
- Cascade windows were selected from perplog's liquidation API, which caps at 2,000 events per
  coin-day and truncates the day's tail. Large cascades are captured; the selection is not
  exhaustive.

## Next

1. All cascades above a notional threshold across the 365-day archive, with matched controls,
   and a bounded coupling statistic. That is the real version of this test.
2. The overcounting result deserves its own writeup — it is a measurement-quality claim about
   every dataset built on fill counts, and it is cheap to verify.
3. Cascade topology using `liquidatedUser`: distinct accounts versus tranches, counterparty
   concentration, repeat liquidatees. Nobody else has the field.
