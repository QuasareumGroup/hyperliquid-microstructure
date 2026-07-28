# EXP-028 — Does endogenous sampling inflate the 575 ms?

**Status:** run. **P2 confirmed; P1, P3 and P4 rejected.** Endogenous sampling does not move the
peak — tested with a sampler *more* coupled to price than Hyperliquid actually is. With noise and
density already excluded, **no estimator-side explanation for the cross-asset pattern survives**,
and the EXP-026 caveat on Result 1's magnitude closes.
**Registered:** 2026-07-28
**Author:** Thomas Erhel / Quasareum
**Data:** perplog tape, BTC/ETH/SOL/HYPE, 2026-07-18 → 07-26 — already on disk, no new download.

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets reported.

---

## 1. The tension this resolves

Two measurements in this repository point in opposite directions about whether Hyperliquid's
sparse printing inflates the 575 ms:

| | says |
|---|---|
| EXP-023, **across assets** | ρ(trade frequency, lag) = **−0.656** — sparser instruments show longer lags |
| EXP-023, **within an asset** | partial = **−0.090**, beside a volatility partial of the same size |
| EXP-027, **synthetic** | follower density does not bias the peak at all, flat from 0.5× HL to full Binance |

Either the cross-asset correlation is confounded — sparser instruments are less liquid and
genuinely slower, so the association is real but not a bias — or EXP-027's synthetic follower is
missing the ingredient that produces it. This experiment tests the one candidate that survived
EXP-027, and it is a candidate with teeth: unlike independent noise, it is **not** structurally
harmless to a cross-covariance.

## 2. What EXP-027's model actually got wrong

EXP-027 built the follower's price path from Binance and took its observation times from
Hyperliquid. Those two came from different sources, so **the follower's sampling times were
independent of the follower's own price innovations, by construction.**

Real venues are not sampled that way. A venue prints **because a trade happened**, and trades
happen when the price is moving. Sampling times and price innovations are the same event stream.

Note the asymmetry this created and which nobody registered at the time: EXP-027's *leader* kept
Binance's real timestamps, so the leader was endogenously sampled while the follower was not.
The real pair has **both** sides endogenous. That is the gap, stated precisely.

## 3. Design

### Part 1 — is Hyperliquid's sampling endogenous at all? *(measurement, real data)*

Per 1-second bin, per hour: Spearman correlation between the venue's **print count** and
**|Binance log return|** in that bin. Binance's return is the price-movement proxy, so the
statistic asks "does this venue print more when the market moves?" without the circularity of
measuring a venue's activity against its own observed returns.

Run for Hyperliquid **and for Binance**, because Binance is a venue too and there is no reason
to assume its sampling is exogenous. The comparison is the point.

### Part 2 — does endogenous sampling move the peak? *(synthetic, known lag)*

Reuse EXP-027's latent follower — Binance lagged by `L = 575 ms` plus an independent random walk
at the calibrated κ̂ — and change only **how it is observed**:

- **Exogenous** (EXP-027's sampler): observe at HL's real print times. Times independent of the
  follower's own path.
- **Endogenous** (new): observe whenever cumulative `|Δ log p|` on the *follower's own latent
  path* since the last observation exceeds a threshold θ. Calibrate θ per hour by bisection so
  the resulting count **equals HL's real count for that hour** — same sparsity, different reason
  for it.

The leader stays at Binance's real timestamps in both arms. The only difference between the two
numbers is whether the follower's observation times know about the follower's price.

## 4. Predictions

- **P1.** Hyperliquid's sampling is endogenous: Spearman(prints/s, |Binance return|/s) > **+0.2**
  on all four assets.
- **P2.** Binance's is endogenous too, by the same statistic — so the real pair is endogenous on
  both sides and EXP-027's asymmetry was an artefact of the construction, not a property of the
  data.
- **P3.** Endogenous sampling **inflates** the recovered peak by more than **25 ms** (one grid
  step) relative to exogenous sampling at the identical count. Mechanism: a threshold sampler
  withholds an observation until enough movement has accumulated, inserting a variable delay
  between a price change and its being observed — a delay that adds to the measured lag and has
  no counterpart on the dense side.
- **P4.** The inflation **scales with sparsity** — larger on the assets with fewer prints — and
  its cross-asset ordering matches the ordering behind EXP-023's ρ = −0.656.

## 5. Falsification, and what each outcome costs us

- **P3 false** (shift ≤ 25 ms) — endogeneity is excluded alongside independent noise and follower
  density. Every estimator-side explanation for the cross-asset pattern is then exhausted, the
  ρ = −0.656 is attributed to genuine market structure (sparser instruments really are slower),
  and **575 ms stands unqualified on this axis.** The best outcome for Result 1, and the one that
  finally closes the EXP-026 caveat.
- **P3 true, P4 false** — endogeneity biases the estimator but does not explain the cross-asset
  ordering. Partial: a correction exists but something else is still unaccounted for.
- **P3 and P4 both true** — **the 575 ms is inflated, and by a knowable amount.** Result 1's
  direction is untouched (100% of 758 asset-hours, zero reversals, no estimator artefact can
  produce that), but its **headline number must be corrected downward** before any paper quotes
  it. This is the outcome that costs us the most and it is the one the mechanism in P3 predicts,
  which is why it is registered as a prediction rather than a risk.
- **P1 false** — Hyperliquid's printing is *not* coupled to price movement. Then the premise of
  Part 2 is wrong, Part 2 measures a sampler that does not describe the venue, and its result is
  reported as a null model rather than as a correction.

## 6. What this cannot settle

It still cannot separate mechanical from informational lag — that needs quotes, and quotes need
EXP-026's Test C.

It also tests **one** parametrisation of endogeneity, a pure threshold sampler on the follower's
own path. Real trade arrival is driven by order flow, volatility clustering and queue dynamics
together; a threshold on price movement is the simplest model that couples times to innovations,
not a faithful one. If P3 is confirmed, the *existence* of the bias is established and its
*magnitude* is model-dependent — a distinction to keep in the write-up rather than to discover in
review.

## 7. Results

92 asset-hours, same sample as EXP-027.

### Part 1 — P1 rejected, P2 confirmed, and the asymmetry is the finding

Spearman(prints per second, |Binance return| that second):

| | Hyperliquid | Binance | ratio |
|---|---|---|---|
| HYPE | +0.167 | **+0.771** | 4.6× |
| BTC | +0.126 | **+0.447** | 3.5× |
| ETH | +0.112 | **+0.618** | 5.5× |
| SOL | +0.057 | **+0.280** | 4.9× |

P2 holds everywhere: Binance prints markedly more when the market moves. **P1 fails everywhere** —
Hyperliquid's coupling is +0.06 to +0.17, below the +0.2 registered as the threshold for calling
its sampling endogenous.

So the two venues are sampled by different clocks. Binance's trade arrival tracks price directly;
Hyperliquid's barely does. The BBO probe run for EXP-026 Test C offers the likely reason and is
recorded there: Hyperliquid's quotes update about 7.9 times a second on BTC, roughly one update
per block. **Trade arrival on Hyperliquid is gated by block production, not by price events.**
That is a hypothesis consistent with two measurements, not something this experiment tested.

### Part 2 — P3 rejected, on every asset, at every sampler

Same latent follower, true lag 575 ms, identical observation count, four selection rules:

| sampler | BTC | ETH | SOL | HYPE |
|---|---|---|---|---|
| endogenous (TV clock) | 575 | 575 | 575 | 575 |
| exogenous random | 575 | 575 | 575 | 575 |
| exogenous evenly spaced | 575 | 575 | 575 | 575 |
| HL's real print times | 575 | 575 | 575 | 575 |

Not a grid step between any of them, anywhere. P4 is not evaluable: there is no inflation to scale
with sparsity.

### Why P1's rejection strengthens this rather than weakening it

§5 registered that a false P1 would make Part 2 "a sampler that does not describe the venue", to
be reported as a null model rather than a correction. That reading needs one refinement, and the
direction matters. The total-variation clock is **maximally** endogenous — it samples on nothing
*but* the series' own movement — while Hyperliquid measures at +0.06 to +0.17. Part 2 therefore
tested a condition considerably harsher than reality and found nothing. The mismatch runs in the
conservative direction, so the null is an upper bound rather than an inapplicable model.

## 8. What this closes

Three candidate mechanisms have now been tested for a sparsity-driven bias on Result 1:

| mechanism | verdict | basis |
|---|---|---|
| independent follower innovations | **excluded** | structural — a cross-covariance is blind to them at every lag (EXP-027) |
| follower observation density | **excluded** | flat from 0.5× HL to full Binance, 92 asset-hours (EXP-027) |
| endogenous sampling times | **excluded** | zero shift under a maximally coupled sampler (EXP-028) |

No estimator-side explanation for EXP-023's cross-asset ρ = −0.656 survives. By the registration
in §5 this attributes it to market structure — sparser instruments really are slower — and
**575 ms stands unqualified on the sparsity axis.** The EXP-026 caveat closes.

**What remains open is narrower and belongs to a different measurement.** EXP-027's P5 found that
no synthetic pair reproduces EXP-026 Test B's leader-thinning inflation, and that is still
unexplained. But Test B degrades the *leader*, and Result 1 does not: Binance enters at full
density. It is an unexplained property of a deliberately degraded measurement, not of the
reported one.

**Not settled, and not settleable from trades:** whether the remaining 575 ms is mechanical or
informational. That needs quotes — and EXP-026 Test C now has a sizing, plus a warning about what
it will face.
