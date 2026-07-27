"""EXP-024 — the uncertainty machinery behind the published intervals.

Committed in response to review finding B2 (review/FABLE.md): the confidence
intervals in the paper's compression table were produced by code that was never
versioned. This is that code, made canonical, with its assumptions stated.

Three sections:

  1. Compression-factor CIs (paper Table 4). Bootstrap draws of a quantile use
     the binomial representation of the order statistic — the resample's index
     is Binomial(n, q) — so one sort replaces every full resample. This is the
     exact law of the bootstrap quantile, not an asymptotic shortcut (verified
     against a naive full bootstrap in review/r2_bootstrap.py).

     **Declared assumption: the episode side and the fill side are drawn
     independently.** They are not independent — fills compose episodes. On the
     12-hour sample, where episode membership is versioned, a cluster bootstrap
     (resampling episodes, taking their fills) widens the p50/p90 intervals by
     20-40% relative to the independent draw and leaves the tail approximately
     unchanged (section 3 reproduces this check). No published conclusion moves:
     the Table 4 intervals exclude the values they are compared against by
     margins far larger than 40%.

  2. Day-cluster bootstrap on the count-inflation factor. The 5.72 figure is a
     ratio over 351,540 episodes, but episodes cluster in days and cascades
     concentrate fills, so iid resampling understates its variance about
     threefold. Days are the sampling unit here.

  3. The cluster-vs-independent check on the 12-hour sample.

    python experiments/exp024_ci.py
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "experiments" / "data"
RNG = np.random.default_rng(20260727)
QUANTILES = (50, 90, 99, 99.9)


def bq(x_sorted: np.ndarray, q: float, B: int) -> np.ndarray:
    """B bootstrap draws of the q-th percentile of x, via Binomial order statistics."""
    n = x_sorted.size
    k = np.clip(RNG.binomial(n, q / 100.0, size=B), 0, n - 1)
    return x_sorted[k]


def main() -> None:
    B = 20_000

    with gzip.open(DATA / "exp024_episodes.csv.gz", "rt") as fh:
        ep = np.sort(np.array([float(r["notional"]) for r in csv.DictReader(fh)]))
    with gzip.open(DATA / "exp024_fill_notionals.csv.gz", "rt") as fh:
        fl = np.sort(np.array([float(r["notional"]) for r in csv.DictReader(fh)]))

    print("--- 1. IC des facteurs de compression (Table 4) ---")
    print(f"    episodes n={ep.size:,}   fills n={fl.size:,}   tirages B={B:,}")
    for q in QUANTILES:
        point = np.percentile(ep, q) / np.percentile(fl, q)
        r = bq(ep, q, B) / bq(fl, q, B)
        lo, hi = np.percentile(r, [2.5, 97.5])
        print(f"    p{q:<6} facteur {point:6.2f}   IC 95% [{lo:.2f}, {hi:.2f}]")

    print("\n--- 2. IC par grappes de jours sur le facteur d'inflation ---")
    rows = list(csv.DictReader(open(DATA / "exp017_episodes.csv")))
    ts = np.array([int(r["ts"]) for r in rows])
    fills = np.array([int(r["fills"]) for r in rows], dtype=float)
    days = np.array([dt.datetime.fromtimestamp(t / 1000, dt.UTC).strftime("%Y%m%d") for t in ts])
    uniq = np.unique(days)
    per_day = {d: fills[days == d] for d in uniq}
    facs = np.empty(2000)
    for i in range(2000):
        pick = RNG.choice(uniq, size=uniq.size, replace=True)
        facs[i] = sum(per_day[d].sum() for d in pick) / sum(per_day[d].size for d in pick)
    print(f"    facteur {fills.sum() / fills.size:.4f}   "
          f"IC jours 95% [{np.percentile(facs, 2.5):.2f}, {np.percentile(facs, 97.5):.2f}]   "
          f"sd {facs.std():.3f}")
    hours = np.array([dt.datetime.fromtimestamp(t / 1000, dt.UTC).hour for t in ts])
    strata = "   ".join(f"h{h:02d} {fills[hours == h].sum() / (hours == h).sum():.2f}"
                        for h in (2, 8, 14, 20))
    print(f"    par strate horaire : {strata}")

    print("\n--- 3. controle grappes vs independant (12 h, appartenance versionnee) ---")
    frows = list(csv.DictReader(open(DATA / "exp016_fills.csv")))
    by_ep: dict[str, list[float]] = {}
    for r in frows:
        by_ep.setdefault(f"{r['user']}|{r['episode']}", []).append(float(r["notional"]))
    eps = [np.array(v) for v in by_ep.values()]
    ep12 = np.sort(np.array([v.sum() for v in eps]))
    fl12 = np.sort(np.concatenate(eps))
    n_ep = len(eps)
    print(f"    {n_ep:,} episodes, {fl12.size:,} fills")
    print(f"    {'q':>7}{'grappes':>18}{'independant':>18}{'rapport largeur':>17}")
    for q in QUANTILES:
        rc = np.empty(4000)
        for i in range(4000):
            pick = RNG.integers(0, n_ep, n_ep)
            sel = [eps[j] for j in pick]
            e = np.array([v.sum() for v in sel])
            f = np.concatenate(sel)
            rc[i] = np.percentile(e, q) / np.percentile(f, q)
        ri = bq(ep12, q, 4000) / bq(fl12, q, 4000)
        lc = np.percentile(rc, [2.5, 97.5])
        li = np.percentile(ri, [2.5, 97.5])
        ratio = (lc[1] - lc[0]) / (li[1] - li[0])
        print(f"    p{q:<6}[{lc[0]:6.2f}, {lc[1]:6.2f}] [{li[0]:6.2f}, {li[1]:6.2f}]{ratio:>15.2f}")


if __name__ == "__main__":
    main()
