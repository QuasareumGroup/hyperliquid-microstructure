# Preprint — counting fills misrepresents liquidations

**Status: draft. Not submitted, and not ready to be.** Two things must be done first, both
listed below. Everything else in it is measured, cross-checked against the versioned data, and
reproducible from this repository.

## Build

```bash
tectonic -X compile liquidation-overcounting.tex --outdir .
```

Tectonic is self-contained and downloads what it needs. Any TeX distribution works;
`liquidation-overcounting.tex` uses only standard packages.

## What the paper claims

Every figure traces to a versioned dataset in `../experiments/data/` and to a pre-registered
experiment in `../experiments/`:

| claim | source |
|---|---|
| 5.72× count inflation, 351,540 episodes from 2,010,042 fills | `exp017_episodes.csv`, [EXP-017](../experiments/EXP-017-year-tail.md) |
| robust across six unit definitions | [EXP-016](../experiments/EXP-016-liquidation-overcounting.md) |
| tranching 2 → 72 fills with size; top 1% of episodes → 23.1% of fills | `exp017_episodes.csv` |
| size compression 3.4× at p99, 10.9× at p99.9 | `exp016_fills.csv`, [EXP-016](../experiments/EXP-016-liquidation-overcounting.md) |
| tail heavy, not a power law, and not nameable | [EXP-020](../experiments/EXP-020-alternatives.md), [EXP-022](../experiments/EXP-022-xmin-selection.md) |
| what CEX feeds publish | venue documentation, [EXP-016](../experiments/EXP-016-liquidation-overcounting.md) |

## Before submission

1. **A systematic literature review.** The paper currently positions itself against venue
   documentation and against the statistical methodology it uses. It does not survey the
   empirical crypto-liquidation literature. Section 9 says so explicitly, and that admission is
   not a substitute for doing the work — a measurement paper whose contribution is "this has
   been measured wrong" has to establish how it has been measured before.

2. **Per-fill notionals at year scale.** The compression table (Section 5) rests on the
   twelve-hour sample because per-fill notionals were not retained during the year-scale
   collection. The count and tranching results are year-scale. Re-collecting is a rerun of
   `../experiments/exp017_year_tail.py` with the per-fill column kept — roughly 50 GB of
   requester-pays egress, inside the free monthly allowance.

Optional, and worth considering: a fifth candidate family (generalised Pareto, log-gamma) for
the threshold band where none of the four fits, per EXP-022.

## Intended venue

arXiv `q-fin.ST` (statistical finance), cross-list `q-fin.TR`. The contribution is a
measurement and a negative result about a widely used data source, not a method.
