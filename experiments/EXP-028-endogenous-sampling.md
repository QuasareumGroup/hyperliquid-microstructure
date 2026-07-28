# EXP-028 — Does endogenous sampling inflate the 575 ms?

**Status:** pre-registered, not yet run
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

*(empty until the experiment runs)*
