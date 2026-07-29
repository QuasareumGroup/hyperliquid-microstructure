"""EXP-029 — does a fifth family fit the band where nothing fits?

Registered in experiments/EXP-029-fifth-family.md. Over `xmin` in [$25k, $81k] the
four families of EXP-022 are all rejected by a parametric-bootstrap KS test. Our
own FINDINGS names generalised Pareto and log-gamma as untried candidates, and
the paper in SSRN's queue says the tail "cannot be named". If a fully parametric
family fits, that wording is corrected before the paper is public.

The criterion is ABSOLUTE fit, never the ranking: a three-parameter family beats
a two-parameter one in-sample by construction, so a ranking would hand back a
winner for free. Every candidate faces the same parametric-bootstrap KS, with the
synthetic samples REFITTED at each replicate so the extra parameters pay for
themselves in the null distribution.

    python experiments/exp029_fifth_family.py --boot 200
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
from scipy import optimize, stats

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments"))

#: The band EXP-022 found empty. Registered, not tuned.
BAND = (25_000.0, 81_000.0)
N_THRESHOLDS = 8


def ks_from_cdf(cdf_sorted: np.ndarray) -> float:
    """Two-sided KS distance of a sorted CDF image against the uniform."""
    n = cdf_sorted.size
    i = np.arange(n)
    return max(float(np.max(np.abs(cdf_sorted - i / n))),
               float(np.max(np.abs(cdf_sorted - (i + 1) / n))))


class Family:
    """A candidate, conditioned on exceeding `xmin`.

    Everything a family needs is (fit, cdf, sample) on the CONDITIONAL law. The
    conditioning is uniform across families -- `(F(x) - F(xmin))/(1 - F(xmin))` --
    so no family gets an easier test than another.
    """

    name: str
    n_params: int

    def fit(self, tail: np.ndarray, xmin: float) -> tuple[tuple, bool]:
        """Return (params, on_bound). `on_bound` disqualifies per method rule 8."""
        raise NotImplementedError

    def _frozen(self, params: tuple, xmin: float):
        raise NotImplementedError

    def ks(self, tail: np.ndarray, xmin: float, params: tuple) -> float:
        d = self._frozen(params, xmin)
        f0 = d.cdf(xmin)
        if f0 >= 1.0 - 1e-12:
            return 1.0
        c = (d.cdf(np.sort(tail)) - f0) / (1.0 - f0)
        return ks_from_cdf(np.clip(c, 0.0, 1.0))

    def sample(self, n: int, xmin: float, params: tuple, rng) -> np.ndarray:
        d = self._frozen(params, xmin)
        f0 = d.cdf(xmin)
        return d.ppf(f0 + (1.0 - f0) * rng.random(n))


class _ScipyFamily(Family):
    """Generic MLE on the conditional likelihood, multi-start, bounded.

    Multi-start is not decoration: EXP-020 found a single-start Nelder-Mead
    degenerating to mu = -778 and producing a fake sign flip. Bounds are wide and
    proximity to them is reported rather than hidden.
    """

    dist = None          # scipy continuous distribution
    shape_bounds: tuple = ()
    seeds: tuple = ()

    def _unpack(self, p):
        shapes = tuple(math.exp(v) for v in p[:-1])
        return shapes, math.exp(p[-1])

    def _frozen(self, params: tuple, xmin: float):
        shapes, scale = params
        return self.dist(*shapes, loc=0.0, scale=scale)

    def fit(self, tail: np.ndarray, xmin: float) -> tuple[tuple, bool]:
        lo = np.array([b[0] for b in self.shape_bounds] + [self.scale_bounds[0]])
        hi = np.array([b[1] for b in self.shape_bounds] + [self.scale_bounds[1]])

        def nll(p):
            if np.any(p < np.log(lo)) or np.any(p > np.log(hi)):
                return 1e12
            shapes, scale = self._unpack(p)
            d = self.dist(*shapes, loc=0.0, scale=scale)
            f0 = d.cdf(xmin)
            if not (0.0 <= f0 < 1.0 - 1e-12):
                return 1e12
            v = d.logpdf(tail) - math.log1p(-f0)
            return 1e12 if not np.all(np.isfinite(v)) else -float(v.sum())

        best, bfun = None, math.inf
        for s in self.seeds:
            p0 = np.log(np.array(s, dtype=float) * np.array([1.0] * len(s)))
            p0 = np.clip(p0, np.log(lo) + 1e-6, np.log(hi) - 1e-6)
            r = optimize.minimize(nll, p0, method="Nelder-Mead",
                                  options={"maxiter": 4000, "xatol": 1e-8, "fatol": 1e-8})
            if r.fun < bfun:
                best, bfun = r.x, r.fun
        if best is None or bfun >= 1e11:
            return None, True
        shapes, scale = self._unpack(best)
        vals = np.array(list(shapes) + [scale])
        on_bound = bool(np.any(np.abs(np.log(vals) - np.log(lo)) < 1e-3)
                        or np.any(np.abs(np.log(vals) - np.log(hi)) < 1e-3))
        return (shapes, scale), on_bound


class GPD(Family):
    """Generalised Pareto on the exceedances, `loc = xmin` so the conditioning is
    the identity. Fitted by scipy's own MLE.

    Registered in §5 as expected to fit and as naming NOTHING:
    Pickands-Balkema-de Haan makes GPD convergence the generic outcome for
    exceedances of almost any distribution.
    """

    name, n_params = "genpareto", 2

    def fit(self, tail, xmin):
        c, loc, scale = stats.genpareto.fit(tail, floc=xmin)
        return (c, scale), not (1e-6 < scale < 1e12)

    def _frozen(self, params, xmin):
        c, scale = params
        return stats.genpareto(c, loc=xmin, scale=scale)


class LogGamma(Family):
    """`log(X) ~ Gamma(a, scale=s)` — the heavy-tailed log-gamma of the tail
    literature, NOT scipy's `loggamma` (which is `log` of a gamma variate and is
    light-tailed). Implemented directly to avoid that trap.
    """

    name, n_params = "loggamma", 2
    A = (1e-3, 1e3)
    S = (1e-4, 1e3)

    def _cdf(self, x, a, s):
        return stats.gamma.cdf(np.log(np.maximum(x, 1.0 + 1e-12)), a, scale=s)

    def fit(self, tail, xmin):
        lt = np.log(tail)
        lxm = math.log(xmin)

        def nll(p):
            a, s = math.exp(p[0]), math.exp(p[1])
            if not (self.A[0] <= a <= self.A[1] and self.S[0] <= s <= self.S[1]):
                return 1e12
            sf = stats.gamma.sf(lxm, a, scale=s)
            if sf <= 1e-300:
                return 1e12
            v = stats.gamma.logpdf(lt, a, scale=s) - lt - math.log(sf)
            return 1e12 if not np.all(np.isfinite(v)) else -float(v.sum())

        best, bf = None, math.inf
        for a0 in (0.5, 2.0, 8.0, 30.0):
            for s0 in (0.05, 0.3, 1.0, 3.0):
                r = optimize.minimize(nll, [math.log(a0), math.log(s0)],
                                      method="Nelder-Mead",
                                      options={"maxiter": 4000, "xatol": 1e-8})
                if r.fun < bf:
                    best, bf = r.x, r.fun
        if best is None or bf >= 1e11:
            return None, True
        a, s = math.exp(best[0]), math.exp(best[1])
        ob = (min(abs(math.log(a / self.A[0])), abs(math.log(a / self.A[1]))) < 1e-3
              or min(abs(math.log(s / self.S[0])), abs(math.log(s / self.S[1]))) < 1e-3)
        return (a, s), bool(ob)

    def ks(self, tail, xmin, params):
        a, s = params
        f0 = self._cdf(xmin, a, s)
        c = (self._cdf(np.sort(tail), a, s) - f0) / (1.0 - f0)
        return ks_from_cdf(np.clip(c, 0.0, 1.0))

    def sample(self, n, xmin, params, rng):
        a, s = params
        f0 = self._cdf(xmin, a, s)
        u = f0 + (1.0 - f0) * rng.random(n)
        return np.exp(stats.gamma.ppf(np.clip(u, 0.0, 1 - 1e-15), a, scale=s))


class Burr12(_ScipyFamily):
    name, n_params = "burr12", 3
    dist = staticmethod(stats.burr12)
    shape_bounds = ((1e-3, 1e2), (1e-3, 1e2))
    scale_bounds = (1e-3, 1e12)
    seeds = ((1.0, 1.0, 1e4), (0.5, 0.5, 1e3), (2.0, 0.3, 1e5), (0.3, 2.0, 1e2))


class GenGamma(_ScipyFamily):
    name, n_params = "gengamma", 3
    dist = staticmethod(stats.gengamma)
    shape_bounds = ((1e-3, 1e2), (1e-3, 1e2))
    scale_bounds = (1e-3, 1e12)
    seeds = ((1.0, 1.0, 1e4), (0.5, 0.5, 1e3), (3.0, 0.3, 1e5), (0.2, 1.5, 1e2))


FAMILIES = [GPD(), LogGamma(), Burr12(), GenGamma()]


def gof(fam: Family, tail: np.ndarray, xmin: float, n_boot: int,
        seed: int) -> tuple[float, float, tuple, bool]:
    """Parametric-bootstrap KS with REFIT inside each replicate."""
    params, on_bound = fam.fit(tail, xmin)
    if params is None:
        return float("nan"), float("nan"), None, True
    d_obs = fam.ks(tail, xmin, params)
    rng = np.random.default_rng(seed)
    worse = 0
    for _ in range(n_boot):
        syn = fam.sample(tail.size, xmin, params, rng)
        syn = syn[np.isfinite(syn) & (syn > xmin)]
        if syn.size < tail.size // 2:
            continue
        p2, _ = fam.fit(syn, xmin)
        if p2 is None:
            continue
        worse += fam.ks(syn, xmin, p2) >= d_obs
    return d_obs, worse / n_boot, params, on_bound


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path,
                    default=REPO / "experiments" / "data" / "exp024_episodes.csv.gz")
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--thresholds", type=int, default=N_THRESHOLDS)
    ap.add_argument("--out", type=Path,
                    default=REPO / "experiments" / "data" / "exp029_band.csv")
    args = ap.parse_args()

    q = duckdb.sql(f"SELECT notional FROM read_csv('{args.csv}') "
                   "WHERE notional > 0").fetchnumpy()["notional"]
    desc = np.sort(q)[::-1]
    lo = int(np.searchsorted(-desc, -BAND[1]))
    hi = int(np.searchsorted(-desc, -BAND[0]))
    ks_grid = np.unique(np.round(np.exp(
        np.linspace(math.log(lo), math.log(hi), args.thresholds))).astype(int))
    print(f"{desc.size:,} episodes   band ${BAND[0]:,.0f}-${BAND[1]:,.0f}"
          f"   k {lo:,}..{hi:,}   {ks_grid.size} thresholds   boot {args.boot}\n")

    # ---- positive control, before anything is believed ----
    # At n = 11k-29k a KS test detects arbitrarily small misspecification, so
    # "nothing fits" could be a statement about sample size rather than about the
    # data. The parametric bootstrap is supposed to absorb that -- it compares the
    # observed KS against correctly-specified synthetics of the SAME size. This
    # checks that it does. A family rejecting its own draws would invalidate the run.
    print("POSITIVE CONTROL — each family tested against its own synthetic draws")
    n_ctrl = int(ks_grid[len(ks_grid) // 2])
    xm_ctrl = float(desc[n_ctrl])
    ctrl_ok = True
    for fam in FAMILIES:
        params, _ = fam.fit(desc[:n_ctrl], xm_ctrl)
        if params is None:
            print(f"    {fam.name:<11} could not fit — control skipped")
            continue
        rng = np.random.default_rng(4242)
        syn = fam.sample(n_ctrl, xm_ctrl, params, rng)
        syn = syn[np.isfinite(syn) & (syn > xm_ctrl)]
        _, p_ctrl, _, _ = gof(fam, syn, xm_ctrl, max(50, args.boot // 4),
                              seed=777)
        ok = p_ctrl > 0.05
        ctrl_ok &= ok
        print(f"    {fam.name:<11} n={syn.size:,}  p={p_ctrl:.3f}  "
              f"{'ok' if ok else 'REJECTS ITS OWN DRAWS'}")
    if not ctrl_ok:
        print("\n  !! the test rejects correctly-specified data at this n.")
        print("     'nothing fits' would be a statement about sample size. STOPPING.")
        return
    print("  -> the bootstrap absorbs the sample size. Rejections below are real.\n")

    rows = []
    for k in ks_grid:
        xmin = float(desc[k]); tail = desc[:k]
        print(f"k={k:,}  xmin=${xmin:,.0f}  n={tail.size:,}")
        for fam in FAMILIES:
            t0 = time.time()
            d, p, params, ob = gof(fam, tail, xmin, args.boot, seed=int(k) % 9973)
            verdict = ("UNFITTED (on bound)" if ob else
                       "FITS" if p > 0.05 else "rejected")
            ps = "—" if params is None else ", ".join(f"{v:.4g}" for v in np.atleast_1d(
                np.array([*np.atleast_1d(params[0]), params[1]], dtype=object)).ravel())
            print(f"    {fam.name:<11} KS {d:.4f}  p {p:.3f}  {verdict:<20}"
                  f" [{time.time()-t0:.0f}s]")
            rows.append({"k": int(k), "xmin": xmin, "n": int(tail.size),
                         "family": fam.name, "n_params": fam.n_params,
                         "ks": d, "p": p, "on_bound": int(ob), "params": ps})
        print()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}\n")

    print("=" * 66)
    for fam in FAMILIES:
        rs = [r for r in rows if r["family"] == fam.name]
        fits = [r for r in rs if r["p"] > 0.05 and not r["on_bound"]]
        bound = [r for r in rs if r["on_bound"]]
        print(f"{fam.name:<11} ({fam.n_params}p)  fits at {len(fits)}/{len(rs)} thresholds"
              f"   unfitted(on bound) {len(bound)}")

    para = [f for f in FAMILIES if f.name != "genpareto"]
    any_para = any(r["p"] > 0.05 and not r["on_bound"]
                   for r in rows if r["family"] in {f.name for f in para})
    print(f"\nP3 {'REJECTED' if any_para else 'CONFIRMED'} — fully parametric families are "
          f"rejected across the band")
    if any_para:
        print("   -> the tail CAN be named in the band. The paper's 'no candidate here")
        print("      describes the data' is wrong as written and the revision must say so.")
    gp = [r for r in rows if r["family"] == "genpareto" and r["p"] > 0.05 and not r["on_bound"]]
    print(f"P2 {'CONFIRMED' if len(gp) > len(ks_grid)//2 else 'REJECTED'} — GPD survives at a "
          f"majority of band thresholds ({len(gp)}/{len(ks_grid)})")
    print("   (a GPD fit names nothing — Pickands-Balkema-de Haan makes it generic)")


if __name__ == "__main__":
    main()
