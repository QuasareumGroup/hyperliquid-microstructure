# quantum-finance-research

Quantum and quantum-inspired methods applied to **on-chain perpetual futures**, using
[Hyperliquid](https://hyperliquid.xyz) as the data substrate.

## Why this, and why here

Quantum-finance work is overwhelmingly benchmarked on synthetic price processes, daily equity
closes, or private credit portfolios. Hyperliquid offers something those cannot: a derivatives
market that is **fully public, on-chain, and tick-resolved**, with order books, funding rates and
liquidation cascades all observable without a data licence.

That matters because the interesting open questions in this field are not "can a quantum solver
beat CPLEX on a textbook portfolio" — that one is settled, and the answer is no
([arXiv:2509.17876](https://arxiv.org/pdf/2509.17876)). They are questions nobody currently has the
data to ask.

### The three research openings

**O1 — The action budget as a resource constraint.**
Hyperliquid grants **1 action per 1 USDC of cumulative traded volume** (plus a 10,000-request
starting buffer). The number of rebalances is therefore a scarce, hard-bounded resource — a
constraint with no equivalent in traditional finance. This defines a problem class:
*multi-period portfolio selection under an action budget*.

```
max  Σₜ [ xₜᵀμₜ − λ·xₜᵀΣₜxₜ − γ‖xₜ − xₜ₋₁‖₁ ]
s.t. Σₜ ‖xₜ − xₜ₋₁‖₀ ≤ B ,  ‖xₜ‖₀ ≤ K ,  xₜ ∈ {0,1}ⁿ
```

The `Σₜ‖xₜ − xₜ₋₁‖₀ ≤ B` term is the novel one. A new problem, not a new method on an old problem.

**O2 — Liquidation tail structure and the QAE crossover.**
Quantum Amplitude Estimation offers a payoff-agnostic quadratic speedup, so its *relative* value is
greatest exactly where classical Monte Carlo struggles: heavy tails and non-Gaussian dependence.
On-chain liquidation cascades produce both and, unlike credit defaults, are **directly observable**.
The open question: *does the tail structure of liquidation cascades move the classical/quantum
crossover point, and in which direction?*

**O3 — Funding as a risk object in its own right.**
Hyperliquid funding has an unusual analytic structure: a fixed interest floor (0.01% / 8h), a hard
clamp at ±4%/hour, and a premium sampled every 5 seconds. A bounded, partly deterministic process
that standard models cover poorly.

### Prior art this builds on (and does not duplicate)

- [*Benchmarking Classical and Quantum Models for DeFi*](https://www.arxiv.org/pdf/2508.02685) —
  quantum × DeFi on Curve AMM pools, for **prediction**; QML loses to tree ensembles. This is why
  quantum-kernel prediction is **out of scope** here: the negative result is already published.
- [*Dynamic Collateral Control for Permissionless Spot Perpetual Basis Trading*](https://arxiv.org/pdf/2605.05089)
  — spot/perp margin siloing. Prior art for the carry engine.
- [*Quantum Computing for Financial Transformation*](https://arxiv.org/abs/2604.08180) — field survey.

Novelty is claimed **narrowly and deliberately**. A precise claim is defensible; a broad one is not.

## Layout

```
hlm/
  data/        recorder.py  hl_client.py  store.py      # substrate — running now
  problems/    action_budget.py  liquidation_tail.py  funding_process.py
  solvers/     classical.py  annealing.py  bifurcation.py  tensor.py  qaoa.py
  montecarlo/  classical_mc.py  qae.py  resources.py
  bench/       harness.py  registry.py
  strategy/    carry.py                                  # testnet only
experiments/   pre-registrations and results
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ".[quantum,solvers]"   # when starting tracks A/B
cp .env.example .env
```

Credentials are only needed for testnet execution and IBM Quantum. **The recorder needs none** —
it reads public mainnet data.

## Relationship to perplog

[`perplog`](https://perplog.com) — the sibling project at `~/perplog` — already operates the
market-data infrastructure this research needs, so this repo **consumes** it rather than competing
with it:

| capability | where it lives | notes |
|---|---|---|
| Trade + book recording | `perplog-recorder` | Rust, 24/7, **multi-venue** (HL/Binance/OKX/Bybit) → R2 |
| Historical L2 + fills | `perplog/rust/crates/archive` | SigV4 signing + lz4 decode of the HL S3 archive |
| Deterministic replay | `perplog/rust/crates/backtest` | causal split, trial ledger, paired block bootstrap |

Multi-venue coverage is not merely a convenience for **O2**: liquidation cascades propagate across
venues, so cross-venue data is what makes contagion observable at all. An HL-only capture would be
strictly worse.

The **methodology is inherited too.** `backtest/validation.rs` already enforces what this project
otherwise had to reinvent — precommitted primary baselines, exposure identities derived by
domain-separated hash rather than supplied by the caller, and fail-closed evidence
("*the bootstrap refuses the whole target stage when required evidence is unknown or causally
invalid; it never runs on a selectively complete subset*"). The benchmark harness here mirrors those
invariants.

## The recorder

Scope is deliberately narrow. `perplog-recorder` subscribes to `trades` and `l2Book` but **not** to
`activeAssetCtx` — so funding, premium, impact prices and open interest are captured nowhere. That
gap is the entire reason this recorder exists, and it happens to be exactly what O1 and O3 need.

```bash
.venv/bin/python -m hlm.data.recorder            # funding/context only (default)
.venv/bin/python -m hlm.data.recorder --status   # summarise what is on disk
.venv/bin/python -m hlm.data.recorder --full     # add trades and book (standalone mode)
```

| dataset | coverage | throttle | purpose |
|---|---|---|---|
| `asset_ctx` | all ~177 perps | 60s (5s for focus) | O1, O3 |
| `funding` | all perps | hourly poll | ground truth |
| `trade` / `bbo` / `book` | `--full` only | — | redundant with perplog |

Unthrottled, `activeAssetCtx` alone emits ~130 rows/s (~11M rows/day). Throttling cuts that ~55×,
to roughly **19 MB/day** in the default mode (~75 MB/day with `--full`).

Historical depth comes from S3 rather than from waiting. `market_data/…/l2Book` and `asset_ctxs`
are documented, and `misc_events_by_block` carries historical **funding** events. Note that
`node_fills_by_block`, which perplog reads for the historical trade tape, is *not* spelled out in
the official docs — perplog parses an observed shape and reports drift. Verify the bucket listing
before any result depends on it.

The recorder **stops itself** if free disk falls below `--min-free-gb` (default 5 GB) rather than
consuming the remainder of the volume.

### Reading it back

```python
from hlm.data.store import Store
store = Store("data")
store.scan("asset_ctx").limit(10).show()
```

Note: the funding poller re-fetches an overlapping window each cycle so gaps cannot open. Deduplicate
on `(coin, time)` at read time.

## Using the folded dataset — one warning

`mark_px` is **mechanically entangled** with `oracle_px`. The mark formula includes
`oracle + EMA_150s(mid − oracle)`, so `ln(mark) − ln(oracle)` is an EMA that mean-reverts by
definition, not by arbitrage. Combining `mark_px` with `oracle_px` or `premium` measures the
formula rather than the market — it produced a spurious R² = 0.14 result here before being
caught ([EXP-004](experiments/EXP-004-oracle-perp-lead-lag.md)).

**Use `mid_px` for anything about price dynamics.** `mark_px` is designed for margining,
liquidation and PnL, and is correct for those.

## Published datasets

`experiments/data/*.csv` are the reduced outputs of each campaign, versioned so results are
checkable without re-running a campaign.

Liquidation datasets carry a **derived account id**, not the address (`hlm/data/anon.py`).
Addresses are public on-chain, so this is not confidentiality — it avoids publishing a
*compiled* map of 350k accounts to their losses, which is far more usable for profiling than
the same facts spread across an archive. No result needs the address: every one depends on
grouping by account, never on which account. Re-running the analyses on the derived ids
reproduces every number bit for bit.

The hash is unsalted and therefore deterministic, so a known address can still be tested for
membership. That is a deliberate trade for third-party reproducibility. **Do not call the
datasets anonymised.**

## Method

Every experiment is **pre-registered**: hypothesis and success criterion written down in
`experiments/` *before* it runs. Findings are reported whether or not they favour the quantum side.
Given the state of the field, most results here are expected to be negative — a rigorous negative
result is the deliverable, not a failure of one.

Classical baselines are tuned properly. Comparing QAE against naive Monte Carlo instead of
quasi-Monte Carlo, or QAOA against an untuned annealer, would invalidate the whole exercise.
