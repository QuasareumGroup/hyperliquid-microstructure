# EXP-027 — How much of the 575 ms is follower sparsity?

**Status:** pre-registered, not yet run
**Registered:** 2026-07-27
**Author:** Thomas Erhel / Quasareum
**Data:** perplog tape, BTC/ETH/SOL/HYPE, 2026-07-18 → 07-26 — already on disk, no new download.

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets reported.

---

## 1. The debt EXP-026 left

EXP-026 closed the dangerous question and opened a smaller one. It established that the estimator
does not manufacture lag from sparsity — impose zero, thin to Hyperliquid's real print times, get
zero. But it also found that thinning **inflates** the measured peak, by +25 ms on the densest
instrument and +212 ms on the sparsest, and it recorded the consequence honestly:

> HL's own prints are sparse, so the 575 ms plausibly carries an upward bias of **unmeasured
> size**. The result holds; its magnitude should be read as an upper estimate.

An unmeasured bias is not a publishable state. This experiment measures it.

## 2. Why the question is sharper than it looks

EXP-026's two tests manipulated different series, and putting them side by side narrows the
mechanism to one candidate:

| | manipulation | κ (follower's own innovations) | bias found |
|---|---|---|---|
| Test A | **follower** thinned to HL density | **0** — deterministic shift of the leader | **none**, exact recovery |
| Test B | **leader** thinned to HL density | real | **+25 to +212 ms** |

Test A already answers "does follower sparsity alone bias the estimate?" — **no**, at κ = 0.
So if the real measurement carries a bias from HL being sparse, it cannot come from sparsity
alone. It has to come from **sparsity interacting with the follower having price innovations of
its own**, which is exactly the case Test A could not construct and recorded as its limitation.

That makes κ the whole story, and it makes the experiment a two-parameter map rather than a
fishing trip: **bias as a function of (κ, follower density)**, anchored at a point we already
know (κ = 0 ⇒ bias = 0).

## 3. Design

### The synthetic follower

For an hour of Binance data with log-prices `p(t)` observed at its own timestamps, a true lag `L`
and a noise ratio `κ`:

```
latent(t + L) = p(t) + W(t),     W = cumsum of N(0, κ · Var[Δp]) at Binance's timestamps
```

`W` is an independent random walk — the follower's *own* price innovations, absent from Test A.
The follower is then **observed only at Hyperliquid's real print times for that same hour**,
carrying HL's actual count *and* its actual burstiness, which a uniform subsample would not.

Measured against untouched Binance, the estimator should return `L`. Whatever it returns instead
is the bias, and it is bias of exactly the kind Result 1 is exposed to.

### Calibrating κ from the real pair

On a common 1 s grid, with Binance shifted by 575 ms, `ρ = corr(r_HL, r_BN)` and

```
κ̂ = (1 − ρ²) / ρ²
```

**κ̂ is an upper bound**, not a point estimate: microstructure noise and tick discretisation land
in the residual and inflate it. The consequence has a direction and it is worth stating in
advance — an overstated κ̂ overstates the bias, hence *understates* the corrected lag. The
correction this experiment produces is therefore conservative against our own result, which is
the side to err on.

### Grids

- `L ∈ {200, 400, 575, 800} ms` — enough to fit `measured(L)` and invert it at 575.
- `κ ∈ {0, 0.25·κ̂, κ̂, 4·κ̂}` — 0 is the anchor that must reproduce Test A.
- Density curve at `L = 575, κ = κ̂`: follower observed at `{0.5, 1, 2, 4, 8}×` HL's count and at
  Binance's full density, drawn from Binance's timestamps with a seed fixed by `(coin, date,
  hour)` so the run is reproducible.

### The number this produces

Solve `L* + bias(L*) = 575` at real density and κ̂. `L*` is the lag corrected for follower
sparsity, and it is what the second paper would report in place of 575.

## 4. Predictions

- **P1 (anchor).** At `κ = 0` the bias is within **±50 ms** of zero at every `L`. This re-runs
  Test A through new code; disagreement means one of the two implementations is wrong and
  nothing else here is interpretable until that is resolved.
- **P2.** Bias is **positive** and **increases with κ** at fixed density.
- **P3.** Bias **decreases as follower density rises**, and is within ±50 ms of zero at Binance's
  full density.
- **P4.** At real density and κ̂, bias is **under 200 ms** — so `L* > 375 ms`, and Result 1
  survives with a corrected magnitude rather than a withdrawn one.

## 5. Falsification

- **P1 false** — the two implementations disagree about a case they share. Stop, reconcile, and
  report the discrepancy rather than either number.
- **P2 false** — bias does not grow with κ. Then the mechanism proposed in §2 is wrong, the
  source of Test B's inflation is unidentified, and the honest output is that the bias is real,
  unexplained, and still unmeasured.
- **P4 false, bias ≥ 400 ms** — `L* < 175 ms`. The *direction* of Result 1 survives (100% of 758
  asset-hours, zero reversals, unaffected), but its **magnitude does not**, and the headline
  becomes a statement about ordering rather than about half a second. The second paper would then
  be about the bias, not about the lag — a smaller and more awkward paper, and the one the data
  would support.

## 6. What this cannot do

It cannot decide whether the remaining lag is mechanical or informational — that needs the quotes,
and the quotes need EXP-026's Test C.

It also inherits one assumption it cannot test from trades alone: that the follower's
idiosyncratic component is an **independent random walk**. If Hyperliquid's own innovations are
autocorrelated or arrive in bursts, the synthetic follower understates their effect, and the
measured bias is too small. Stated here so it is not discovered later.

## 7. Results

*(empty until the experiment runs)*
