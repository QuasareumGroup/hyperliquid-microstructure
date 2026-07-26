"""EXP-020 — what IS the liquidation tail, if not Pareto?

EXP-019 ran the first half of Clauset-Shalizi-Newman: a KS test with a
parametric-bootstrap p-value, which rejected the Pareto fit at every k. That
says what the tail is not. This runs the second half — fit the plausible
alternatives on the same exceedances and compare them by likelihood ratio.

Candidates, all fitted conditional on x >= xmin so the comparison is on the same
data:

  pareto              the rejected null, kept as the reference
  lognormal           the classic competitor to a power law
  weibull             stretched exponential (shape < 1 is heavy-tailed)
  pareto_cutoff       power law with an exponential cutoff (NESTED in pareto)
  exponential         light-tailed baseline; should lose badly if the tail is heavy

Non-nested pairs are compared with **Vuong's** normalised likelihood ratio: R > 0
favours the first model, and p is two-sided against R = 0. `pareto_cutoff` is
nested in `pareto`, so that one pair uses a standard likelihood-ratio test
instead — Vuong is not valid for nested models.

The whole procedure is validated on synthetic samples from each family before it
is pointed at the data: if it cannot recover a known generator, its verdict on
real data means nothing.

    python experiments/exp020_alternatives.py
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import duckdb
import numpy as np
from scipy import optimize, stats

REPO = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260726)


# ---------------------------------------------------------------- log-likelihoods
# Each returns the per-observation log density conditional on x >= xmin, so the
# models are compared on identical support.

def ll_pareto(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    a = x.size / np.sum(np.log(x / xmin))
    return np.log(a / xmin) - (a + 1) * np.log(x / xmin), {"alpha": a}


def ll_exponential(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    lam = 1.0 / np.mean(x - xmin)
    return np.log(lam) - lam * (x - xmin), {"lambda": lam}


def ll_lognormal(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    lx = np.log(x)

    def nll(p):
        mu, ls = p[0], p[1]
        s = math.exp(ls)
        tail = stats.norm.sf((math.log(xmin) - mu) / s)
        if tail <= 0:
            return 1e12
        return -np.sum(stats.norm.logpdf(lx, mu, s) - np.log(x) - math.log(tail))

    r = optimize.minimize(nll, [lx.mean(), math.log(lx.std() + 1e-9)], method="Nelder-Mead")
    mu, s = r.x[0], math.exp(r.x[1])
    tail = stats.norm.sf((math.log(xmin) - mu) / s)
    return stats.norm.logpdf(lx, mu, s) - np.log(x) - math.log(tail), {"mu": mu, "sigma": s}


def ll_weibull(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    """Weibull truncated at xmin. Scaled by xmin so (x/lam)**b cannot overflow."""
    u = x / xmin  # u >= 1

    def nll(p):
        b, lam = math.exp(p[0]), math.exp(p[1])
        if not (1e-3 < b < 20) or lam <= 0:
            return 1e12
        with np.errstate(over="ignore", invalid="ignore"):
            z, z0 = (u / lam) ** b, (1.0 / lam) ** b
            v = math.log(b) - math.log(lam) + (b - 1) * (np.log(u) - math.log(lam)) - z + z0
        return 1e12 if not np.all(np.isfinite(v)) else -float(np.sum(v))

    best, bll = None, math.inf
    for b0 in (0.2, 0.4, 0.7, 1.0):
        for lam0 in (0.5, 1.0, 5.0):
            r = optimize.minimize(nll, [math.log(b0), math.log(lam0)], method="Nelder-Mead",
                                  options={"maxiter": 4000, "xatol": 1e-8, "fatol": 1e-8})
            if r.fun < bll:
                best, bll = r.x, r.fun
    b, lam = math.exp(best[0]), math.exp(best[1])
    z, z0 = (u / lam) ** b, (1.0 / lam) ** b
    ll = math.log(b) - math.log(lam) + (b - 1) * (np.log(u) - math.log(lam)) - z + z0
    return ll - math.log(xmin), {"beta": b, "lambda_over_xmin": lam}


def ll_pareto_cutoff(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    """Power law with exponential cutoff, f(x) ~ x^-a exp(-lam x) above xmin.

    Pareto is the lam -> 0 limit, so this NESTS it: its maximised log-likelihood
    can never be lower. A first version returned a worse fit than Pareto, which
    is impossible and meant the optimiser had not converged. Fixed by seeding at
    the Pareto solution with a near-zero cutoff and working in u = x/xmin.
    """
    u = x / xmin
    a_pl = u.size / np.sum(np.log(u))

    def nll(p):
        a, lam = p[0], math.exp(p[1])
        if not (0.01 < a < 10) or lam <= 0:
            return 1e12
        # normaliser on u >= 1: integral_1^inf t^-a e^-lam t dt
        g = float(stats.gamma.sf(lam, 1 - a) * math.gamma(1 - a)) if a < 1 else float("nan")
        if not np.isfinite(g) or g <= 0:
            # a >= 1: integrate numerically, the incomplete gamma is not usable
            t = np.exp(np.linspace(0, math.log(1e6), 4000))
            g = float(np.trapezoid(t ** -a * np.exp(-lam * t), t))
            if not np.isfinite(g) or g <= 0:
                return 1e12
        return -float(np.sum(-a * np.log(u) - lam * u - math.log(g)))

    best, bll = None, math.inf
    for lam0 in (1e-6, 1e-4, 1e-2, 0.1):
        r = optimize.minimize(nll, [a_pl, math.log(lam0)], method="Nelder-Mead",
                              options={"maxiter": 4000, "xatol": 1e-9, "fatol": 1e-9})
        if r.fun < bll:
            best, bll = r.x, r.fun
    a, lam = best[0], math.exp(best[1])
    g = float(stats.gamma.sf(lam, 1 - a) * math.gamma(1 - a)) if a < 1 else float("nan")
    if not np.isfinite(g) or g <= 0:
        t = np.exp(np.linspace(0, math.log(1e6), 4000))
        g = float(np.trapezoid(t ** -a * np.exp(-lam * t), t))
    ll = -a * np.log(u) - lam * u - math.log(g)
    return ll - math.log(xmin), {"alpha": a, "lambda_over_xmin": lam}


MODELS = {
    "pareto": ll_pareto,
    "lognormal": ll_lognormal,
    "weibull": ll_weibull,
    "pareto_cutoff": ll_pareto_cutoff,
    "exponential": ll_exponential,
}


def vuong(l1: np.ndarray, l2: np.ndarray) -> tuple[float, float]:
    """Normalised LR and two-sided p. R > 0 favours model 1."""
    d = l1 - l2
    n = d.size
    s = d.std(ddof=1)
    if s <= 0:
        return 0.0, 1.0
    r = d.sum() / (math.sqrt(n) * s)
    return float(r), float(2 * stats.norm.sf(abs(r)))


def compare(x: np.ndarray, xmin: float) -> dict:
    out = {}
    for name, fn in MODELS.items():
        try:
            ll, par = fn(x, xmin)
            if np.all(np.isfinite(ll)):
                out[name] = (ll, par)
        except Exception:
            continue
    return out


def report(x: np.ndarray, xmin: float, label: str) -> str:
    fits = compare(x, xmin)
    if "pareto" not in fits:
        return "pareto fit failed"
    lp = fits["pareto"][0]
    lines = []
    best = None
    for name, (ll, par) in fits.items():
        if name == "pareto":
            continue
        if name == "pareto_cutoff":
            # Nested: 2*(LL_full - LL_reduced) ~ chi2(1). Vuong is invalid here.
            stat = 2 * (ll.sum() - lp.sum())
            p = float(stats.chi2.sf(max(stat, 0), 1))
            verdict = "cutoff mieux" if stat > 0 and p < 0.05 else "pas mieux"
            lines.append(f"    pareto vs {name:<14} LR chi2={stat:8.1f} p={p:.3f}  {verdict}")
        else:
            r, p = vuong(lp, ll)
            who = "pareto" if r > 0 else name
            verdict = f"{who} favorise" if p < 0.05 else "indecis"
            lines.append(f"    pareto vs {name:<14} R={r:+8.1f} p={p:.3f}  {verdict}")
            if p < 0.05 and r < 0 and (best is None or ll.sum() > fits[best][0].sum()):
                best = name
        _ = par
    head = f"  {label}: gagnant = {best or 'pareto (aucun ne le bat)'}"
    return head + "\n" + "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path,
                    default=REPO / "experiments" / "data" / "exp017_episodes.csv")
    ap.add_argument("--k", type=int, default=5000)
    args = ap.parse_args()

    print("=== validation : la procedure retrouve-t-elle le generateur ? ===")
    n, xm = 30_000, 10.0
    cases = {
        "pareto a=1.0": xm * (1 - RNG.random(n)) ** (-1 / 1.0),
        "lognormale": np.exp(RNG.normal(math.log(xm) + 2, 2.0, n)),
        "weibull b=0.4": xm * (RNG.exponential(1.0, n) + 1.0) ** (1 / 0.4),
    }
    for name, sample in cases.items():
        s = sample[sample >= xm]
        print(report(s, xm, name))

    d = duckdb.sql(
        f"SELECT hip3, notional FROM read_csv('{args.csv}') WHERE notional > 0"
    ).fetchnumpy()
    x = d["notional"].astype(float)[d["hip3"].astype(int) == 0]
    desc = np.sort(x)[::-1]
    xmin = float(desc[args.k])
    tail = desc[: args.k]
    print(f"\n=== donnees reelles : majors, k={args.k:,}, xmin=${xmin:,.0f} ===")
    print(report(tail, xmin, f"liquidations (n={tail.size:,})"))

    print("\n  parametres ajustes :")
    for name, (ll, par) in compare(tail, xmin).items():
        ps = "  ".join(f"{k}={v:.4g}" for k, v in par.items())
        print(f"    {name:<16} logL={ll.sum():12.1f}   {ps}")


if __name__ == "__main__":
    main()
