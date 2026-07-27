# EXP-027 — How much of the 575 ms is follower sparsity?

**Status:** run. **P1, P3, P4 confirmed; P2 and P5 rejected.** Follower sparsity does not bias
the estimator — the density curve is flat from 0.5× HL to full Binance, at every κ up to 20.
**But the synthetic follower fails a validation it should pass** (P5), so that result is
established for a model the real pair demonstrably is not. The EXP-026 caveat is **narrowed, not
removed**.
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

## 7. Addendum — registered after P2 was rejected, before the diagnostic was run

**This section is post-hoc and labelled as such.** The main grid ran, P2 was rejected on all four
assets, and that rejection points at an error in §2 rather than at a property of the data. The
prediction below was written before the diagnostic was executed; it is not part of the original
registration.

### What §2 got wrong

§2 argued: Test A (κ = 0) found no bias, Test B found +25 to +212 ms, therefore the difference is
κ. **That is not the difference between them.** Test A thinned the *follower*; Test B thinned the
*leader*. They differ in which series was degraded, not in the follower's noise.

And there is a textbook reason κ cannot be the answer. The Hayashi-Yoshida estimator is a
cross-covariance. If the follower is `x(t−L) + W` with `W` independent of `x`, then
`E[Δx · ΔW] = 0` at every lag, so `W` contributes nothing to the cross-covariance curve at any
τ. Independent noise moves the estimator's **variance**, never its **peak**. §2's mechanism was
ruled out before the data was touched, by algebra that should have been done first.

### Why this matters more than a rejected prediction

**Result 1 does not thin the leader.** Binance enters at its full density. If Test B's inflation
is caused by leader-thinning, then it is a property of an artificial manipulation and has no
bearing on Result 1 — and the "upward bias of unmeasured size" written into EXP-026 §7 and
carried into FINDINGS is an inference I made from an experiment that does not apply.

### The diagnostic

Take the synthetic follower at a known `L = 575 ms`, observed at HL's print times as above — then
**additionally thin the leader** to those same print times, reproducing Test B's manipulation on
a pair whose true lag is known.

- **P5.** Thinning the leader inflates the recovered peak by an amount comparable to EXP-026 Test
  B (+25 to +212 ms, larger on sparser assets), at both κ = 0 and κ = κ̂. That identifies Test B's
  inflation as leader-thinning, absent from Result 1, and the EXP-026 caveat gets withdrawn.
- **P5 false** — leader-thinning does not inflate the synthetic pair. Then Test B's inflation
  comes from something about *real* Hyperliquid that the synthetic follower fails to reproduce,
  the caveat stands, and it stays unmeasured. That outcome is worse for us and more interesting.

## 8. Results

92 asset-hours: BTC 24, ETH 24, HYPE 24, SOL 20 (four hours dropped by the ρ > 0.10 identification
guard).

| | HL prints/h | Binance/h | ρ | κ̂ | real peak |
|---|---|---|---|---|---|
| BTC | 12,500 | 36,517 | 0.534 | 2.52 | 562 ms |
| ETH | 5,548 | 28,387 | 0.407 | 5.07 | 575 ms |
| HYPE | 5,540 | 13,162 | 0.455 | 3.83 | 550 ms |
| SOL | 2,576 | 7,560 | 0.218 | 20.14 | 612 ms |

### P1 confirmed — the code agrees with EXP-026

At κ = 0 the recovered lag equals the imposed lag exactly on BTC, ETH and HYPE at all four `L`,
and within 25 ms on SOL. Two independent implementations agree on the case they share, so what
follows is interpretable.

### P2 rejected — and it could not have been otherwise

Bias at `L = 575` across κ ∈ {0, 0.25κ̂, κ̂, 4κ̂}:

| BTC | ETH | HYPE | SOL |
|---|---|---|---|
| +0, +0, +0, +0 | +0, +0, +0, +0 | +0, +0, +0, +0 | +0, +50, +0, −12 |

Flat, at noise ratios up to 4 × 20.14 = **80× the leader's own variance** on SOL. §7 gives the
reason: an independent additive component contributes zero to the cross-covariance at every lag,
so it cannot move the peak. SOL's ±50 ms wobble is one to two steps of a 25 ms grid on the
sparsest, least correlated instrument — variance, which is precisely what independent noise is
supposed to add.

### P3 and P4 confirmed — follower density does not bias the estimate

Bias at `L = 575`, κ = κ̂, as the follower's observation count varies:

| | 0.5× HL | 1× HL | 2× | 4× | 8× | full Binance |
|---|---|---|---|---|---|---|
| BTC / ETH / HYPE | +0 | +0 | +0 | +0 | +0 | +0 |
| SOL | +62 | +25 | +50 | +50 | +50 | +50 |

Flat — including on SOL, whose offset is the same at HL's density as at Binance's and therefore
is not a density effect. Inverting `measured = a + b·L` at HL's real density gives
**L\* = 575 ms** on BTC, ETH and HYPE and **561 ms** on SOL. The correction this experiment was
built to produce is, on this model, **zero**.

### P5 rejected — the model fails its validation

Same synthetic follower, true lag 575 ms, measured against a full-density leader and against one
thinned to HL's print times — the manipulation EXP-026 Test B performed on the real pair:

| | κ = 0 | κ = κ̂ | Test B found, on the real pair |
|---|---|---|---|
| BTC | +25 | +12 | **+38** |
| ETH | +0 | +0 | **+188** |
| HYPE | −12 | +12 | **+25** |
| SOL | +0 | −38 | **+212** |

Everything in the first two columns is within one or two grid steps of zero. **The synthetic pair
does not reproduce Test B.** By the falsification registered in §7, this is the outcome that goes
against us: Test B's inflation comes from something in *real* Hyperliquid that the model lacks.

## 9. What this settles, and the caveat it leaves standing

**Excluded, with a reason each.** Two candidate mechanisms for a bias on Result 1 are now ruled
out rather than merely unmeasured: independent follower innovations (P2, and the algebra that
makes it structural rather than empirical), and leader-thinning of a co-moving pair (P5). The
density curve is flat across a 16-fold range including HL's real cadence and burstiness.

**Not established: that Result 1 is unbiased.** P5's rejection is a failed validation of the
instrument, not a detail. A model that cannot reproduce a measured behaviour of the real pair is
not evidence about the real pair, and every "+0" above is a statement about that model. The
honest position is that the EXP-026 caveat is **narrower and better characterised**, not lifted.

**The leading candidate for what is missing — endogenous observation times.** In the synthetic,
the follower's price path comes from Binance while its observation times come from Hyperliquid,
so times and innovations are *independent by construction*. In reality they are the same event:
Hyperliquid prints **because** a trade occurred, so its print times are correlated with its own
price moves. Nothing in this design reproduces that coupling, and it is the most plausible source
of a behaviour the model misses. Testing it needs a follower whose sampling times are drawn
conditional on its own path — a different experiment, not run.

**For the paper.** 575 ms stands as the measured value, with follower sparsity excluded as an
explanation on the strongest model available and the model's own inadequacy stated. That is a
weaker claim than "575 ms, corrected and confirmed", and it is the one the evidence supports.
