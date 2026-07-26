# EXP-014 — Observability, measured instead of assumed

**Status:** run. **Observability explains essentially none of the 550 ms level.** The lag is a
constant floor that does not move when Hyperliquid's price becomes visible 6.5× more slowly.
**Date:** 2026-07-26
**Data:** 120 hours (4 assets × 30 sampled hours), `experiments/data/exp014_waiting_*.csv`.
Script `experiments/exp014_waiting_time.py`.

---

## Fixing EXP-013's benchmark

EXP-013 compared the measured lead against "half the mean inter-trade interval" and found it
10× too weak for observability. Its caveat then claimed burstiness makes the effective wait
*shorter* than that. **That reasoning was wrong in its main term.** Under the inspection
paradox, information landing at an arbitrary instant is more likely to fall inside a long gap,
so the true waiting time is `E[I²]/(2E[I]) ≥ E[I]/2` — **longer**, not shorter.

Rather than patch the formula, this measures the quantity directly: **for every Binance print,
the time until the next Hyperliquid print**, under the real arrival processes of both venues.
Weighted by |Binance return|, since that is what Hayashi-Yoshida weights.

Both effects turn out to be real and partly cancel: `w_renewal > w_half` everywhere
(inspection paradox confirmed), while |return| weighting pulls the figure back down
(information does arrive when trading is active).

## Results

All values in ms. `w_weighted` is the empirical, |return|-weighted waiting time — the
HY-relevant one.

| asset | τ | **w_weighted** | w_renewal | w_half | residual τ−w | 95% CI |
|---|---|---|---|---|---|---|
| BTC | 550 | 520 | 793 | 376 | −14 | [−112, 84] |
| ETH | 575 | **1,453** | 2,081 | 898 | −922 | [−1132, −713] |
| SOL | 625 | **3,404** | 3,733 | 1,601 | −3,101 | [−3776, −2427] |
| HYPE | 550 | **1,055** | 1,657 | 815 | −560 | [−711, −408] |

**Observability delay varies 6.5× across assets (520 → 3,404 ms). The measured lead varies
1.14× (550 → 625 ms).**

```
τ = 547 + 0.03 · w_weighted        R² = 0.103,  n = 120,  p = 3.5e-04
```

Pure observability predicts **intercept ≈ 0 and slope ≈ 1**. Measured: **intercept 547 ms,
slope 0.03**. The intercept alone reproduces the observed τ across every asset.

## What this actually reveals

For three of four assets **τ is far shorter than the waiting time**. SOL prints once every
3.4 s on average yet tracks Binance with a 625 ms lead. That is impossible if Hyperliquid's
price were frozen between trades.

The resolution: **trade sparsity is not price staleness.** Between executions, Hyperliquid's
market makers update quotes continuously — the price is fresh even when nothing prints. The
"observability" framing conflated the two, and the data says so directly: were the price
genuinely frozen between trades, SOL would show ~3,400 ms rather than 625.

It also explains why EXP-012's cross-asset correlation *looked* like observability. BTC is the
one asset where `w` (520) happens to coincide with τ (550). On the other three the story
collapses.

## Conclusion

> **Observability explains essentially none of the ~550 ms level.** It is a constant floor,
> independent of how sparsely Hyperliquid trades and therefore of how slowly its price becomes
> visible.

Stronger than EXP-013's version, and obtained by measuring the arrival processes rather than
assuming a distribution over them. The surviving candidates — network latency, consensus
delay, genuine price discovery — no longer include "Hyperliquid trades less often".

## Limits

- 30 sampled hours per asset, not all 144.
- `w_weighted` weights by per-print |return|, but a Hyperliquid print responds to *accumulated*
  Binance movement, not to one print. The mapping between waiting time and HY delay is
  therefore not exact — which matters for the *level* of `w`, not for the finding that τ fails
  to track it.
- Trades only. A quote feed would measure price staleness directly instead of inferring it,
  and would settle the sparsity-versus-staleness point rather than arguing it from residuals.

## Next

1. A quote-level test of the sparsity/staleness distinction, if book data at tick resolution
   becomes available.
2. With observability removed, the remaining candidates are structural. Separating consensus
   and network latency from price discovery needs an instrument that sees order *submission*,
   not execution — which none of the current instruments do.
