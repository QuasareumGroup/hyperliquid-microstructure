# EXP-029 — the fifth family, on the band where nothing fits

**Status:** pre-registered, not yet run
**Registered:** 2026-07-29
**Author:** Thomas Erhel / Quasareum
**Data:** `experiments/data/exp024_episodes.csv.gz` — 351,648 episodes, one archive year.
Already on disk, no collection.

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets reported.

---

## 1. Why this is urgent rather than merely open

FINDINGS open item 2 says, in as many words:

> A fifth family (generalised Pareto, log-gamma) might cover that band; **none was tried.**

And the paper currently sitting in SSRN's approval queue says, in its abstract and twice in its
body:

> it **cannot be named** … over that band **no candidate here describes the data**

A published claim therefore rests on four families, with the fifth — the one named in our own
notes as the plausible candidate — never run. If it fits, the wording is too strong and has to be
qualified **in the revision, before the paper goes public**, not after somebody else finds it.

That is the whole reason this runs now rather than later.

## 2. What EXP-022 actually established, and on what footing

Not the boundary diagnosis — the adversarial review corrected that. The band conclusion stands on
a **direct goodness-of-fit test**: parametric-bootstrap KS rejects every fitted candidate over
`xmin ∈ [$25k, $81k]` at `p ≤ 0.01`. The review also established that the test's simplification
biases `p` **upward**, against rejection, so those rejections hold *a fortiori*.

That is the bar a fifth family has to clear, and it is the same bar, unchanged.

## 3. Design

### Families

Four new, chosen because each **nests** something that degenerated in EXP-022, so a fit would
say where the two-parameter families were failing:

| family | parameters | nests |
|---|---|---|
| generalised Pareto | 2 (shape, scale) | exponential, Pareto |
| log-gamma | 2 | Pareto |
| Burr XII | 3 | log-logistic, Weibull-ish, Pareto tail |
| generalised gamma | 3 | gamma, Weibull, lognormal *limit* |

The four originals — Pareto, lognormal, Weibull, Pareto-with-cutoff — are refitted in the same
run, unchanged, as the anchor.

### The criterion, and why it is not the ranking

**Absolute fit, never relative.** A three-parameter family beats a two-parameter one in-sample by
construction, so a model ranking would "find" a winner for free — the exact failure EXP-022 named
in its own method rule: *a ranking always returns a winner*. The test is therefore the same
**parametric-bootstrap KS** as EXP-022, with the synthetic samples **refitted** at each bootstrap
replicate so the extra parameters pay for themselves in the null distribution.

Same threshold grid, same exceedance construction, same code path. If any of that changes, the
comparison with EXP-022 is void.

### The boundary rule stays in force

Method rule 8 of this repository: *a fit on its constraint boundary is not a result*. Any family
that pins at a parameter bound is reported as **unfitted, not fitting**, whatever its KS says.
Parameter bounds are set wide and the pinning is checked explicitly, as EXP-020 required after its
own multi-start failure.

## 4. Predictions

- **P1 (anchor, gating).** The four original families are rejected across the band exactly as
  EXP-022 found, `p ≤ 0.01`. This is a port check: if the reproduction fails, the machinery moved
  and nothing below is comparable.
- **P2.** The **generalised Pareto survives** the GoF test over a majority of band thresholds
  (`p > 0.05`), without pinning.
- **P3.** The **fully parametric families — log-gamma, Burr XII, generalised gamma — are
  rejected** across the band, like the two-parameter ones.
- **P4.** No surviving family survives by pinning; every reported fit is interior.

## 5. What each outcome costs, and the distinction that matters most

**A GPD fit would not name the tail, and the paper's claim would survive it.** By
Pickands–Balkema–de Haan, exceedances above a high threshold converge to a generalised Pareto for
a very broad class of distributions. A GPD fitting is therefore close to the *generic* outcome and
is a statement about extreme-value theory, not about liquidations. P2 is registered as expected
for that reason, and confirming it changes the paper by at most a clarifying sentence.

**A log-gamma, Burr or generalised-gamma fit would be different.** Those are full parametric
descriptions, not domain-of-attraction statements. If one of them fits the band interior and
survives the bootstrap, then the tail **can** be named there, *"no candidate here describes the
data"* is wrong as written, and the revision must say so. This is the outcome that costs us, and
P3 is the prediction it would falsify.

- **P1 false** — stop. The port is broken and no comparison with EXP-022 is possible.
- **P3 false** — the paper is corrected before it is public. Better found here than in review.
- **P3 true, P2 true** — the negative result gets materially stronger: *eight* families, four of
  them with three or more parameters, and the only survivor is the one EVT hands you for almost
  any distribution. That is a much harder claim to attack than the current four.
- **P4 false** — a family "survives" only by sitting on a bound. Report it as unfitted and treat
  the band as still empty, per rule 8.

## 6. What this cannot settle

It tests families, not the *reason* the band resists them. Whether that band marks a genuine
mixture — a body and a tail with different generating mechanisms, which the episode data would
make plausible — is a different experiment and is not attempted here.

It also inherits EXP-022's threshold grid and its exceedance construction wholesale, deliberately.
Any improvement to those would be a second variable moving.

## 7. Results

*(empty until the experiment runs)*
