# EXP-001 — Multi-period carry selection under an action budget

**Status:** pre-registered, not yet run
**Track:** O1
**Registered:** 2026-07-26
**Author:** monproweb / Quasareum

> Written *before* running anything. Predictions below are commitments, not
> descriptions. If the results contradict them, the results are what gets
> reported.

---

## 1. Question

Hyperliquid meters actions against traded volume: **1 action per 1 USDC of cumulative
volume**, on top of a 10,000-request starting buffer. Rebalancing is therefore a
scarce resource with a hard ceiling, which has no equivalent in traditional
finance, where rebalancing is limited by cost but never rationed outright.

Two questions follow, and only the second is about quantum computing:

- **Q1.** Does an explicit action budget change the optimal policy in a way that a
  cost-penalty formulation (`γ‖xₜ − xₜ₋₁‖₁`) does not already capture?
- **Q2.** At problem sizes where Q1 matters, which solver class reaches a given
  solution quality fastest?

Q1 must be answered first. If the answer is no, the problem class is not
interesting and Q2 is moot — that outcome ends the track and gets written up.

## 2. Problem instance

```
max  Σₜ [ xₜᵀμₜ − λ·xₜᵀΣₜxₜ − γ‖xₜ − xₜ₋₁‖₁ ]
s.t. Σₜ ‖xₜ − xₜ₋₁‖₀ ≤ B        (action budget — the novel constraint)
     ‖xₜ‖₀ ≤ K                  (cardinality)
     xₜ ∈ {0,1}ⁿ
```

| symbol | meaning | value |
|---|---|---|
| `n` | assets | 40 (highest 24h notional) |
| `T` | hourly periods | 24 |
| `K` | max simultaneous positions | 6 |
| `B` | action budget | {6, 12, 24, 48, ∞} — ∞ is the control |
| `μₜ` | realised funding, next hour | from `fundingHistory` |
| `Σₜ` | covariance of hourly returns | 168h rolling window |
| `λ` | risk aversion | calibrated so the risk term is ~same order as carry |
| `γ` | round-trip cost | 11 bps maker/maker, 23 bps taker/taker |

**Data.** Historical `fundingHistory` is queryable directly from the API, so this
experiment does **not** wait on the recorder. The recorder matters for O2 and O3,
where books and trades are unavailable retrospectively.

**Instance freezing.** Instances are generated once, written to
`experiments/instances/exp001/`, and hashed. Every solver sees byte-identical
inputs. Reruns that do not reproduce the hash are invalid.

**Sample.** 30 non-overlapping 24h windows, sampled across distinct volatility
regimes rather than consecutively, to avoid grading every solver on one market.

## 3. Solvers

| solver | role | library |
|---|---|---|
| CP-SAT | exact ground truth | `ortools` |
| Simulated annealing, tuned | serious classical baseline | `dwave-neal` |
| Simulated bifurcation | quantum-inspired | own implementation |
| Tensor network | quantum-inspired | own implementation |
| QAOA | quantum, simulator first | `qiskit` + Aer |

**Tuning parity.** The annealer gets the same tuning effort as the quantum
methods — sweep count, schedule and restarts tuned on a held-out instance set. An
untuned baseline would make any quantum result meaningless.

QAOA runs on hardware only if it is competitive in simulation. Open Plan gives
10 minutes of QPU per 28 days; spending it on a method already losing on a
simulator would waste the budget and prove nothing.

## 4. Metrics

Primary: **objective value reached at fixed wall-clock budgets** {0.1s, 1s, 10s},
reported as relative gap to the CP-SAT optimum. Time-to-target, not
time-to-optimality — the latter flatters exact solvers and hides how heuristics
are actually used.

Secondary: qubits, circuit depth after transpilation, shots, QPU seconds.

Hardware and thread count are recorded with every run. Wall-clock comparisons
across machines are not valid.

## 5. Predictions

Registered in advance:

- **P1.** CP-SAT solves n=40, T=24 to proven optimality in under 10s for every
  `B`. *If true, there is no room for a quantum advantage at this scale, and the
  honest framing becomes a scaling study, not a competition.*
- **P2.** Simulated bifurcation matches tuned annealing within 1% at equal time
  budget, and neither reaches CP-SAT quality at 0.1s.
- **P3.** QAOA on a simulator needs ≥10× the wall-clock of the best classical
  method for equal quality, at every size tested.
- **P4 (the interesting one).** The action budget binds — the optimal policy under
  `B = 6` differs from `B = ∞` by more than the cost penalty alone would produce,
  measured as Hamming distance between policies. **This is what makes O1 a real
  problem class rather than a reparameterisation.**

## 6. Falsification

- **P4 false** — if the budget-constrained policy is reproducible by tuning `γ`
  alone, O1 collapses into known transaction-cost portfolio theory. The track
  stops and the negative result is published. **This is the load-bearing risk.**
- **P1 false** at n=40 — a genuinely hard combinatorial core exists; scale up
  `n` and `T` until CP-SAT breaks, and report where.
- **P2 false** — investigate before believing it; a large gap between two
  quantum-inspired heuristics usually indicates a tuning bug, not a discovery.

## 7. Success criterion

Success is a **defensible answer to Q1 with a reproducible benchmark**, whichever
way it falls. It is *not* "a quantum method wins". Given the state of the field,
the most likely honest outcome is P1–P3 confirmed and the value sitting entirely
in P4.

## 8. Results

*(empty until the experiment runs)*
