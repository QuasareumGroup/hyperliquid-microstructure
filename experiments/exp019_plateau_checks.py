"""EXP-019 — three checks on the alpha ~ 0.93 plateau.

EXP-018 located a plateau by minimising the slope of alpha against log k over a
0.7-decade window, and reported an asymptotic CI. Three things were left
unverified, and the number is now load-bearing:

1. **Window width.** The plateau was found with one arbitrary width. If the
   location or alpha move when the width does, the plateau is an artefact of
   the search.
2. **Bootstrap CI.** alpha/sqrt(k) is asymptotic. The naive n-out-of-n bootstrap
   is known to be inconsistent for tail-index estimation, so m-out-of-n
   SUBSAMPLING is reported alongside it — disagreement between them is itself
   informative.
3. **Goodness of fit.** Hill assumes a Pareto tail. A plateau is consistent with
   that but does not establish it. KS statistic on the exceedances with a
   parametric-bootstrap p-value (Clauset-Shalizi-Newman).

The GoF machinery is validated first on synthetic data where the answer is
known: true Pareto should not be rejected, lognormal should be.

    python experiments/exp019_plateau_checks.py
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import duckdb
import numpy as np

REPO = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260726)


def hill(desc: np.ndarray, k: int) -> float:
    return float(1.0 / np.mean(np.log(desc[:k] / desc[k])))


def plateau(desc: np.ndarray, ks: np.ndarray, width: float,
            max_frac: float = 0.10) -> tuple[int, int, float, float]:
    """Window of `width` decades with the flattest alpha. Returns (k_lo, k_hi, alpha, slope)."""
    lg = np.log10(ks)
    a = np.array([hill(desc, int(k)) if k + 1 < desc.size else np.nan for k in ks])
    limit = int(np.searchsorted(ks, max_frac * desc.size))
    best = (0, 0, math.inf)
    for i in range(max(limit, 1)):
        j = min(int(np.searchsorted(lg, lg[i] + width, side="right")), limit)
        ok = np.isfinite(a[i:j])
        if ok.sum() < 5:
            continue
        slope = float(np.polyfit(lg[i:j][ok], a[i:j][ok], 1)[0])
        if abs(slope) < abs(best[2]):
            best = (i, j - 1, slope)
    lo, hi, slope = best
    return int(ks[lo]), int(ks[hi]), float(np.nanmean(a[lo:hi + 1])), slope


def ks_pareto(x: np.ndarray, alpha: float, xmin: float) -> float:
    """KS distance between exceedances and the fitted Pareto."""
    e = np.sort(x[x >= xmin])
    if e.size < 20:
        return float("nan")
    emp = np.arange(1, e.size + 1) / e.size
    fit = 1.0 - (e / xmin) ** (-alpha)
    return float(max(np.max(np.abs(emp - fit)), np.max(np.abs(emp - 1 / e.size - fit))))


def gof_pvalue(x: np.ndarray, k: int, reps: int = 200) -> tuple[float, float, float]:
    """Parametric-bootstrap p for 'the top k are Pareto'. Returns (alpha, ks, p)."""
    d = np.sort(x[x > 0])[::-1]
    a, xmin = hill(d, k), float(d[k])
    tail = d[:k]
    ks_obs = ks_pareto(tail, a, xmin)
    worse = 0
    for _ in range(reps):
        sim = xmin * (1 - RNG.random(k)) ** (-1 / a)
        sim_sorted = np.sort(sim)[::-1]
        a_sim = float(1.0 / np.mean(np.log(sim_sorted / xmin)))
        if ks_pareto(sim, a_sim, xmin) >= ks_obs:
            worse += 1
    return a, ks_obs, worse / reps


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path,
                    default=REPO / "experiments" / "data" / "exp017_episodes.csv")
    args = ap.parse_args()

    # ---- validate the GoF machinery on known answers -----------------------
    print("=== validation du test d'adequation ===")
    pure = 3.0 * (1 - RNG.random(200_000)) ** (-1 / 1.0)          # Pareto, alpha=1
    logn = np.exp(RNG.normal(0, 2.0, 200_000))                     # lognormal, not Pareto
    for label, x, expect in (("Pareto alpha=1", pure, "non rejete"),
                             ("lognormale", logn, "rejete")):
        a, ksd, p = gof_pvalue(x, 5000, reps=120)
        verdict = "non rejete" if p > 0.10 else "rejete"
        flag = "OK" if verdict == expect else "ECHEC"
        print(f"  {label:<16} alpha={a:.2f}  KS={ksd:.4f}  p={p:.3f}  -> {verdict:<11}[{flag}]")

    d = duckdb.sql(
        f"SELECT hip3, notional FROM read_csv('{args.csv}') WHERE notional > 0"
    ).fetchnumpy()
    x = d["notional"].astype(float)[d["hip3"].astype(int) == 0]
    desc = np.sort(x)[::-1]
    ks = np.unique(np.round(np.logspace(math.log10(50), math.log10(60_000), 160)).astype(int))
    ks = ks[ks < desc.size - 2]

    # ---- 1. window-width sensitivity ---------------------------------------
    print(f"\n=== 1. sensibilite a la largeur de fenetre (majors, n={x.size:,}) ===")
    print(f"  {'largeur':>9}{'k_lo':>9}{'k_hi':>9}{'alpha':>8}{'pente':>9}")
    for w in (0.4, 0.5, 0.7, 1.0, 1.3):
        lo, hi, a, sl = plateau(desc, ks, w)
        print(f"  {w:>9.1f}{lo:>9,}{hi:>9,}{a:>8.2f}{sl:>+9.3f}")

    # ---- 2. bootstrap vs subsampling ---------------------------------------
    k_ref = 5000
    a_ref = hill(desc, k_ref)
    se_asym = a_ref / math.sqrt(k_ref)
    print(f"\n=== 2. incertitude sur alpha a k={k_ref:,} (point alpha={a_ref:.3f}) ===")
    print(f"  {'methode':<24}{'IC 95%':>18}{'largeur':>10}")
    print(f"  {'asymptotique':<24}"
          f"{f'[{a_ref - 1.96 * se_asym:.3f}, {a_ref + 1.96 * se_asym:.3f}]':>18}"
          f"{2 * 1.96 * se_asym:>10.3f}")
    n = x.size
    for label, m in (("bootstrap n-sur-n", n), ("sous-echantillonnage n/4", n // 4),
                     ("sous-echantillonnage n/16", n // 16)):
        out = []
        for _ in range(300):
            s = np.sort(RNG.choice(x, size=m, replace=True))[::-1]
            kk = max(20, int(round(k_ref * m / n)))
            if kk + 1 < s.size:
                out.append(hill(s, kk))
        lo, hi = np.percentile(out, [2.5, 97.5])
        print(f"  {label:<24}{f'[{lo:.3f}, {hi:.3f}]':>18}{hi - lo:>10.3f}")

    # ---- 3. goodness of fit on the plateau ---------------------------------
    print("\n=== 3. adequation Pareto sur la zone de plateau ===")
    print(f"  {'k':>8}{'alpha':>8}{'KS':>9}{'p':>8}   verdict")
    for k in (2500, 5000, 10000, 12000):
        if k + 1 >= desc.size:
            continue
        a, ksd, p = gof_pvalue(x, k, reps=200)
        print(f"  {k:>8,}{a:>8.2f}{ksd:>9.4f}{p:>8.3f}   "
              f"{'compatible Pareto' if p > 0.10 else 'REJETE'}")


if __name__ == "__main__":
    main()
