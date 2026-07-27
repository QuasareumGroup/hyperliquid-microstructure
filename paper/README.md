# Preprint — counting fills misrepresents liquidations

**Status: draft, no known blockers.** The literature review is done (16 references, Section 2)
and the compression table is now year-scale like the rest of the paper (EXP-024). Every figure is
measured, cross-checked against the versioned data, and reproducible from this repository.

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
| size compression 4.58× at p99, 10.0× at p99.9, majors vs HIP-3 | `exp024_fill_notionals.csv.gz`, [EXP-024](../experiments/EXP-024-year-fill-notionals.md) |
| tail heavy, not a power law, and not nameable | [EXP-020](../experiments/EXP-020-alternatives.md), [EXP-022](../experiments/EXP-022-xmin-selection.md) |
| what CEX feeds publish | venue documentation, [EXP-016](../experiments/EXP-016-liquidation-overcounting.md) |

## What the literature review established

The framing changed as a result, so it is worth recording separately from the paper.

**The documented bias runs the other way.** Since 2021 the major centralised venues rate-limit
their liquidation feeds — Binance publishes only the largest order per 1000 ms per symbol, OKX
one update per second per contract. K33 Research called the result "a vast underrepresentation
of actual liquidation volumes." So the known problem is **under**counting on order feeds, and
what we measure is **over**counting on fill records. Pooling the two combines a downward-biased
count with an upward-biased one.

**The lending literature does not have this problem, and that is instructive.** Qin et al.
(ACM IMC 2021) count DeFi liquidations by scanning protocol-emitted events — Aave's
`LiquidationCall`, Compound's `LiquidateBorrow`. One call, one event: the unit comes with the
data. Perpetual venues emit no such event, so the unit has to be reconstructed, and that
reconstruction is what nobody had priced.

**Existing Hyperliquid work measures dollars, not counts** — Chitra et al. on autodeleveraging
profit overshoot, Sepper on slippage risk — so the counting question had not come up on this
venue.

**It also caught something the paper needed.** Hyperliquid sends only 20% of a position above
100k USDC as the first market order, then waits 30 s. One forced close can span several
transactions, which our unit would split. Tested on the year sample: 1.4% of episodes are
affected and the factor moves 5.72× → 5.76×, so the reported number is mildly conservative. That
check is now Section 4.2, and it exists because the docs were read properly.

## Remaining, none blocking

- A fifth candidate family (generalised Pareto, log-gamma) for the threshold band where none of
  the four fits, per EXP-022. Would strengthen Section 6; its absence is stated as a limitation.
- Two cited works were characterised from abstracts rather than full text — Lim (SSRN,
  registration wall) and Zhivkov et al. (publisher returned 403). Flagged in Limitations; nothing
  in the argument depends on their contents.
- The full per-fill file is 119 MB and is not committed. What is committed reproduces every
  quantile in the paper exactly — see the table above.

## Submission details

| | |
|---|---|
| author | Thomas Erhel — Quasareum, Paris, France — contact@quasareum.com |
| ORCID | [0009-0007-1772-9892](https://orcid.org/0009-0007-1772-9892) |
| affiliation | Quasareum, Paris, France — arXiv accepts at most a city and a country, no postal code or street address |
| copyright | **Quasareum** — conditional on a written assignment of rights from the author to the company, which French law does not grant automatically to a non-salaried founder. Not a blocker for arXiv; worth executing once. |
| licence | **CC BY 4.0** — stated on the title page, `paper/LICENSE`, and to be selected at arXiv submission |

## Intended venue

arXiv `q-fin.ST` (statistical finance), cross-list `q-fin.TR`. The contribution is a
measurement and a negative result about a widely used data source, not a method.
