# Response to the adversarial reviews

Two independent reviews, run in isolated worktrees with no contact between them:
[`FABLE.md`](FABLE.md) (Claude Fable 5 — same model family as the authoring model, with
verification code in `r1…r5*.py`) and [`GROK.md`](GROK.md) (Grok — different family). The
overlap on the headline figures was deliberate: agreement between decorrelated reviewers is
evidence, divergence is a finding.

Every fix below was applied only after independent re-verification by the authoring session —
neither review was trusted on its own word, including where they agreed.

## Where the reviewers disagreed, and who was right

| point | Fable | Grok | arbitration |
|---|---|---|---|
| Spearman(notional, fills) | 0.383 | 0.468 | **Grok.** 0.383 is the Pearson of ordinal ranks *without* tie correction; 78.8% of episodes have exactly 2 fills, so tie handling dominates. scipy's tie-corrected estimator: **0.468**. Fable made the mistake its own finding C7 flags in the repo's code. |
| the $1,902 isolated-episode median | identified the hidden definition (isolated **and** re-liquidated key, n = 141,417) | could not reproduce (got $1,083) | **Both.** Grok's $1,083 is the natural definition; Fable explained why the published number differed. The paper now uses $1,083 — which *strengthens* the contrast (×67 instead of ×38). |
| submission verdict | "everything correctable locally" | "do not submit until C1, C2, claim A are fixed" | Compatible: same fix list, different emphasis. All three of Grok's blockers are fixed. |

## Findings confirmed by both reviewers — all fixed

| finding | fix |
|---|---|
| **$194,115,094 "across 4,776 fills" is a conflation of two episodes** (largest by notional: BTC, 2,568 fills; most-tranched: ZEC, $32.4M, 4,776 fills) | Corrected in the paper, FINDINGS.md and README.md, with the two maxima now attributed to their own episodes |
| **Implications section still cited the superseded 12-hour compression** (3.4×/10.9×) | Now 4.58×/10.0×, matching Table 4 |
| **"rank correlation +0.545" is the Pearson of logs** | Relabelled; Spearman 0.468 added alongside |
| **Episode-side quantiles of Table 4 not reproducible from committed data** (second-pass file uncommitted) | `exp024_episodes.csv.gz` (351,648 episodes) committed; quantiles verified identical after re-read |
| **The CI code was never versioned** | `experiments/exp024_ci.py` committed; re-run reproduces every published interval exactly |
| **The $1,902 figure** | Replaced by $1,083 under the declared natural definition |

## Grok-only findings

| finding | fix |
|---|---|
| **Abstract's "only public liquidation record complete and attributed" is falsified by GMX and dYdX v4** | Abstract restricted to "a combination no centralised venue publishes"; a new Related Work paragraph credits GMX (protocol events — the unit comes with the data, and with no order book there is no tranching to measure) and dYdX v4 (attributed fills; a second venue where this measurement could be replicated) |
| **"none states its counting unit" too strong — Pinax already aggregates HL fills into liquidation events** | Cited; the claim is now that the *measured factor* is what was missing |
| **Claim C can be strengthened**: Bybit Feb 2025, ~$2.1B internal vs ~$0.33B aggregated; CEO estimate $8–10B vs $2.2B | Added with citation |
| **Inflation rises with activity** (quiet-quintile 3.8× vs active 6.7×) | Folded into the new uncertainty paragraph and the stratification limitation |

## Fable-only findings

| finding | fix |
|---|---|
| **B1 — the year-scale unit is (account, instrument, 5 s gap), not (account, transaction)**; the "<5 s: 0" row is true by construction | Unit correctly described everywhere; table row and caption annotated "by construction". Fable's recount: a true transaction unit would give a *higher* factor (~+2%), so 5.72 is conservative |
| **B3 — 5.72 published with no uncertainty** | Day-cluster bootstrap 95% CI **[5.47, 5.99]** and the hour-strata spread (5.36–6.12) now in the abstract, Section 4 and Limitations; "unbiased" replaced by "fixed-hour" |
| **B7 — "dominate at all 14 thresholds" overclaims at k = 277 (p = 0.07)**; Table 5's mid-band R range wrong at one end (+0.36 at $8.85M) | "Individually significant at 13 of the 14" stated; Table 5 range corrected to −1.86…+0.36 |
| **B8 — the band diagnosis ("both on a parameter bound") is half wrong**: the lognormal converged interior at 2 of 4 thresholds | Rewritten around the solid argument — direct GoF rejects every fitted candidate in the band (p ≤ 0.01; re-verified independently, reproducing Fable's fitted parameters exactly) |
| **B9 — universal pre-registration claim false for EXP-016/018/019/020** (results in the same commit) | Paper and README now say: pre-registered from EXP-017 onward (5 of the 9 used); the four earlier ones are named |
| **B10 — "conservative toward rejection" states the inverse direction** | Corrected: the simplification inflates p (bias *against* rejection), so the rejection holds a fortiori |
| **B2 (part) — independent-sides assumption in the CIs, unstated**; cluster bootstrap widens p50/p90 intervals 24–45% | Declared in `exp024_ci.py` and in a new Limitations bullet, with the cluster check included in the committed code |
| **B11 — last sentence of the COI declaration is advocacy** | Deleted; the declaration now states facts only |
| **C1/C2 — "three decimal places" and "0.03% more" imprecise** | "At the precision quoted"; "+0.031% episodes, +0.014% fills" |
| **C3–C7 cosmetics** (grid 18 vs 20; EXP-021 Spearman subset and tie handling; Hill plot shown without retraction note) | Correction notes appended to EXP-021/EXP-022/EXP-024; README Hill plot captioned as a withdrawn-claim illustration |

## What was attacked and held

Recorded because it is the other half of the reviews' value:

- **The eight headline figures** reproduce independently in both reviews (the ninth being the
  conflation above).
- **Vuong under double misspecification** — the attack's premise was inverted: the test is
  built for misspecified models (QMLE theory); comparing two KS-rejected families is its use
  case. All comparison pairs verified strictly non-nested; the one nested pair uses an LR test.
- **The binomial bootstrap at p99.9** — it is the exact law of the bootstrap quantile, and a
  3,000-resample naive bootstrap agrees to Monte-Carlo noise.
- **The threshold-grid parade** — under simulated single-family truths (lognormal, then
  Weibull), the observed reversal pattern *never appears*. "The tail cannot be named" came out
  of review strengthened.
- **The 5-event floor** (EXP-021) — it never had the opportunity to decide a single
  classification in the published data; the post-registration deviation is immaterial in fact.
- **The partial rank correlations** — verified four ways (classical formula, cubic residuals,
  partial Kendall, curvature test); the declared "not checked" limitation is now checked.
- **The 30-second cooldown merge** (5.72 → 5.76) — reproduced to the digit by both reviewers,
  and robust across merge windows 30–120 s (Grok).
- **Claim C** (CEX rate limits) — re-verified against 2026 documentation by Grok; still true,
  and now quantified.

## Divergence-of-note for the record

Grok found ~29 date×hour slots with no episodes (1,431 of 1,460 non-empty) and three fills
timestamped 19:59:59 (block spillover at an hour boundary). Both are consistent with hours in
which no liquidation printed and with block-boundary mechanics; neither affects any figure.
Flagged here so the observation is not lost.
