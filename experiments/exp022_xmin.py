"""EXP-022 — select xmin by minimising KS, then re-rank the candidate tails.

EXP-020 ranked five candidate tails at one hand-fixed threshold (k = 5,000,
xmin = $312,751) and listed the arbitrariness as a Limit. This runs its Next item 1.

The ranking is answered twice, as registered in EXP-022 §2:

  (a) at the CSN-selected xmin — the convention a referee expects, but built on the
      KS distance of the POWER-LAW fit, which is the model this data rejects;
  (b) across a grid of xmin — whether the ranking depends on the threshold at all.

(b) is the one that matters. If the ranking holds everywhere, (a)'s soundness stops
being load-bearing.

    python experiments/exp022_xmin.py

Writes `experiments/data/exp022_grid.csv`.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
from scipy import optimize, special, stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

from exp020_alternatives import ll_exponential, ll_pareto, vuong  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260727)


# ------------------------------------------------------------ pareto with cutoff
# EXP-020's version bracketed alpha in (0.01, 10) and pinned at the lower bound, so
# it was excluded as unfitted (method rule 8). The bracket was the bug: with lam > 0
# the density x^-a exp(-lam x) is normalisable for ANY real a, so constraining a > 0
# is an assumption, not a regularisation. Widened here, with the normaliser computed
# by quadrature in log space — valid at every a, where the incomplete-gamma form is
# only valid for a < 1.

def _cutoff_norm(a: float, lam: float, n: int = 3000) -> float:
    """int_1^inf t^-a exp(-lam t) dt, substituting t = exp(s)."""
    hi = math.log(max(1e3, 200.0 / lam))
    s = np.linspace(0.0, hi, n)
    return float(np.trapezoid(np.exp(s * (1.0 - a) - lam * np.exp(s)), s))


def ll_pareto_cutoff(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    u = x / xmin
    lu = np.log(u)
    a_pl = u.size / lu.sum()

    def nll(p):
        a, lam = p[0], math.exp(p[1])
        if not (-5.0 < a < 10.0) or not (1e-12 < lam < 1e4):
            return 1e12
        g = _cutoff_norm(a, lam)
        if not np.isfinite(g) or g <= 0:
            return 1e12
        return -float(np.sum(-a * lu - lam * u - math.log(g)))

    best, bll = None, math.inf
    for a0 in (a_pl, 0.5 * a_pl, 0.0):
        for lam0 in (1e-6, 1e-3, 1e-1):
            r = optimize.minimize(nll, [a0, math.log(lam0)], method="Nelder-Mead",
                                  options={"maxiter": 3000, "xatol": 1e-9, "fatol": 1e-9})
            if r.fun < bll:
                best, bll = r.x, r.fun
    a, lam = best[0], math.exp(best[1])
    ll = -a * lu - lam * u - math.log(_cutoff_norm(a, lam))
    #: on_bound is reported, never silently dropped — a fit at its constraint is
    #: not a result (method rule 8).
    on_bound = bool(abs(a - (-5.0)) < 1e-3 or abs(a - 10.0) < 1e-3 or lam <= 1e-11)
    return ll - math.log(xmin), {"alpha": a, "lambda_over_xmin": lam, "on_bound": on_bound}


# ------------------------------------------- lognormal and Weibull, refitted
# EXP-020 fits both from a SINGLE Nelder-Mead start. On this data that fails over a
# band of thresholds (k ≈ 8,000–16,000): the lognormal's mu runs to −778 and the
# Weibull's lambda to 6e-306, a denormal at the floating-point floor. Both are the
# same degeneracy — conditioned on a high xmin, a lognormal with mu → −inf and
# sigma → inf approaches a power law, so the likelihood has a near-flat ridge and a
# lone simplex slides down it. The R values it then reports are noise, and in the
# first run they looked like a sign flip, which is exactly what P2 was testing.
#
# Fixed by multi-starting from data-driven seeds and keeping the best. Parameters
# that still land on a bound are FLAGGED, not silently reported (method rule 8).

_LN_MU = (-30.0, 30.0)
_LN_SIG = (0.05, 12.0)
_WB_BETA = (0.02, 20.0)
_WB_LAM = (1e-9, 1e9)


def ll_lognormal_ms(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    lx = np.log(x)
    lxm = math.log(xmin)

    def nll(p):
        mu, s = p[0], math.exp(p[1])
        if not (_LN_MU[0] <= mu <= _LN_MU[1]) or not (_LN_SIG[0] <= s <= _LN_SIG[1]):
            return 1e12
        tail = stats.norm.sf((lxm - mu) / s)
        if tail <= 1e-300:
            return 1e12
        v = stats.norm.logpdf(lx, mu, s) - lx - math.log(tail)
        return 1e12 if not np.all(np.isfinite(v)) else -float(v.sum())

    seeds = [(lx.mean(), lx.std() + 1e-9), (lxm, 1.0), (lxm, 3.0), (lxm - 5.0, 5.0),
             (0.0, 2.0), (lx.mean(), 1.0)]
    best, bll = None, math.inf
    for mu0, s0 in seeds:
        mu0 = min(max(mu0, _LN_MU[0] + 1e-6), _LN_MU[1] - 1e-6)
        s0 = min(max(s0, _LN_SIG[0] + 1e-6), _LN_SIG[1] - 1e-6)
        r = optimize.minimize(nll, [mu0, math.log(s0)], method="Nelder-Mead",
                              options={"maxiter": 6000, "xatol": 1e-9, "fatol": 1e-9})
        if r.fun < bll:
            best, bll = r.x, r.fun
    mu, s = best[0], math.exp(best[1])
    tail = stats.norm.sf((lxm - mu) / s)
    ll = stats.norm.logpdf(lx, mu, s) - lx - math.log(tail)
    bound = (min(abs(mu - _LN_MU[0]), abs(mu - _LN_MU[1])) < 1e-3
             or min(abs(s - _LN_SIG[0]), abs(s - _LN_SIG[1])) < 1e-3)
    return ll, {"mu": mu, "sigma": s, "on_bound": bool(bound)}


def ll_weibull_ms(x: np.ndarray, xmin: float) -> tuple[np.ndarray, dict]:
    u = x / xmin
    lu = np.log(u)

    def nll(p):
        b, lam = math.exp(p[0]), math.exp(p[1])
        if not (_WB_BETA[0] <= b <= _WB_BETA[1]) or not (_WB_LAM[0] <= lam <= _WB_LAM[1]):
            return 1e12
        with np.errstate(over="ignore", invalid="ignore"):
            z, z0 = (u / lam) ** b, (1.0 / lam) ** b
            v = math.log(b) - math.log(lam) + (b - 1) * (lu - math.log(lam)) - z + z0
        return 1e12 if not np.all(np.isfinite(v)) else -float(v.sum())

    best, bll = None, math.inf
    for b0 in (0.05, 0.1, 0.2, 0.4, 0.7, 1.0):
        for lam0 in (1e-3, 0.1, 1.0, 5.0):
            r = optimize.minimize(nll, [math.log(b0), math.log(lam0)], method="Nelder-Mead",
                                  options={"maxiter": 6000, "xatol": 1e-9, "fatol": 1e-9})
            if r.fun < bll:
                best, bll = r.x, r.fun
    b, lam = math.exp(best[0]), math.exp(best[1])
    z, z0 = (u / lam) ** b, (1.0 / lam) ** b
    ll = math.log(b) - math.log(lam) + (b - 1) * (lu - math.log(lam)) - z + z0
    bound = (min(abs(b - _WB_BETA[0]), abs(b - _WB_BETA[1])) < 1e-4
             or lam <= _WB_LAM[0] * 10 or lam >= _WB_LAM[1] / 10)
    return ll - math.log(xmin), {"beta": b, "lambda_over_xmin": lam, "on_bound": bool(bound)}


MODELS = {
    "pareto": ll_pareto,
    "lognormal": ll_lognormal_ms,
    "weibull": ll_weibull_ms,
    "pareto_cutoff": ll_pareto_cutoff,
    "exponential": ll_exponential,
}


# ------------------------------------------------------------------ xmin selection

def pareto_ks(tail: np.ndarray, xmin: float) -> tuple[float, float]:
    """KS distance of the MLE Pareto fit on exceedances, and the fitted alpha."""
    n = tail.size
    a = n / np.log(tail / xmin).sum()
    xs = np.sort(tail)
    cdf = 1.0 - (xmin / xs) ** a
    i = np.arange(n)
    d = max(float(np.max(np.abs(cdf - i / n))), float(np.max(np.abs(cdf - (i + 1) / n))))
    return d, float(a)


def select_xmin(desc: np.ndarray, ks_grid: np.ndarray) -> tuple[float, int, float, float]:
    """CSN selection: the k minimising the Pareto KS distance.

    `desc` is sorted descending. Returns (xmin, k, ks, alpha).
    """
    best = (math.inf, 0, 0.0, 0.0)
    for k in ks_grid:
        k = int(k)
        if k < 50 or k >= desc.size:
            continue
        xmin = float(desc[k])
        tail = desc[:k]
        if xmin <= 0 or tail[-1] <= xmin:
            continue
        d, a = pareto_ks(tail, xmin)
        if d < best[0]:
            best = (d, k, xmin, a)
    d, k, xmin, a = best
    return xmin, k, d, a


def logspace_k(lo: int, hi: int, n: int) -> np.ndarray:
    return np.unique(np.round(np.exp(np.linspace(math.log(lo), math.log(hi), n))).astype(int))


# ----------------------------------------------------------------------- ranking

def rank_at(tail: np.ndarray, xmin: float) -> dict:
    """Fit every model on the exceedances; return log-likelihoods and Vuong vs pareto."""
    fits = {}
    for name, fn in MODELS.items():
        try:
            ll, par = fn(tail, xmin)
            if np.all(np.isfinite(ll)):
                fits[name] = (ll, par)
        except Exception:
            continue
    return fits


def summarise(fits: dict) -> dict:
    """Vuong R and p of each model against pareto, plus lognormal vs weibull."""
    out = {}
    if "pareto" not in fits:
        return out
    lp = fits["pareto"][0]
    for name, (ll, par) in fits.items():
        if name == "pareto":
            continue
        if name == "pareto_cutoff":
            stat = 2.0 * (ll.sum() - lp.sum())
            out[name] = (float(stat), float(stats.chi2.sf(max(stat, 0.0), 1)), par)
        else:
            r, p = vuong(lp, ll)
            out[name] = (r, p, par)
    if "lognormal" in fits and "weibull" in fits:
        out["lognormal_vs_weibull"] = vuong(fits["lognormal"][0], fits["weibull"][0]) + ({},)
    # P4 needs the cutoff against the alternatives, not only against pareto. It is
    # not nested in either, so Vuong is the right test there.
    for other in ("lognormal", "weibull"):
        if "pareto_cutoff" in fits and other in fits:
            out[f"cutoff_vs_{other}"] = vuong(fits["pareto_cutoff"][0], fits[other][0]) + ({},)
    return out


def estimable(fits: dict) -> bool:
    """True when no alternative sits on a parameter bound.

    A model pinned on its constraint is not a fit (method rule 8). Here both
    two-parameter alternatives degenerate toward the power-law limit of their own
    family over a band of thresholds — lognormal with mu -> -inf, Weibull with
    lambda -> 0 — and the ranking they then produce says nothing.
    """
    return not any(fits.get(m, (None, {}))[1].get("on_bound", False)
                   for m in ("lognormal", "weibull", "pareto_cutoff"))


# -------------------------------------------------------------------- validation

def grafted(n: int, thresh: float, alpha: float, frac_tail: float = 0.1) -> np.ndarray:
    """Lognormal body below `thresh`, exact Pareto tail above it. xmin is known."""
    n_tail = int(n * frac_tail)
    tail = thresh * (1.0 - RNG.random(n_tail)) ** (-1.0 / alpha)
    body = np.array([], dtype=float)
    while body.size < n - n_tail:
        draw = np.exp(RNG.normal(math.log(thresh) - 1.5, 1.0, 4 * (n - n_tail)))
        body = np.concatenate([body, draw[draw < thresh]])
    return np.concatenate([body[: n - n_tail], tail])


def validate() -> bool:
    print("=== validation : le selecteur retrouve-t-il un xmin connu ? ===")
    ok = True
    for thresh, alpha in ((1000.0, 1.5), (5000.0, 1.0), (200.0, 2.5)):
        x = grafted(120_000, thresh, alpha)
        desc = np.sort(x)[::-1]
        xmin, k, d, a = select_xmin(desc, logspace_k(100, 40_000, 120))
        ratio = xmin / thresh
        good = 0.5 <= ratio <= 2.0
        ok &= good
        print(f"  vrai xmin={thresh:>8.0f} alpha={alpha:.1f}  ->  "
              f"selectionne {xmin:>9.1f} (x{ratio:.2f}) k={k:>6,} "
              f"alpha_hat={a:.2f} KS={d:.4f}  {'OK' if good else 'ECHEC'}")
    print(f"  {'PASS' if ok else 'FAIL'}\n")
    return ok


def gof_pvalue(tail: np.ndarray, xmin: float, alpha: float, n_boot: int) -> float:
    """Parametric-bootstrap p for the Pareto fit at a FIXED xmin.

    CSN re-select xmin inside each synthetic; this does not, which makes the p
    conservative in the direction of rejecting. Reported as a limit, and the same
    simplification EXP-019 validated (known Pareto p = 0.800, known lognormal p = 0.000).
    """
    d_obs, _ = pareto_ks(tail, xmin)
    n = tail.size
    worse = 0
    for _ in range(n_boot):
        syn = xmin * (1.0 - RNG.random(n)) ** (-1.0 / alpha)
        d_syn, _ = pareto_ks(syn, xmin)
        worse += d_syn >= d_obs
    return worse / n_boot


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path,
                    default=REPO / "experiments" / "data" / "exp017_episodes.csv")
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--gof-boot", type=int, default=1000)
    ap.add_argument("--grid", type=int, default=14)
    ap.add_argument("--out", type=Path,
                    default=REPO / "experiments" / "data" / "exp022_grid.csv")
    args = ap.parse_args()

    if not validate():
        raise SystemExit("validation failed — results not read")

    d = duckdb.sql(
        f"SELECT hip3, notional FROM read_csv('{args.csv}') WHERE notional > 0"
    ).fetchnumpy()
    x = d["notional"].astype(float)[d["hip3"].astype(int) == 0]
    desc = np.sort(x)[::-1]
    print(f"=== majors : n = {desc.size:,} episodes ===\n")

    fine = logspace_k(100, 50_000, 200)
    xmin, k, ks, alpha = select_xmin(desc, fine)
    print("--- selection CSN ---")
    print(f"  xmin = ${xmin:,.0f}   k = {k:,}   KS = {ks:.4f}   alpha_hat = {alpha:.3f}")
    print(f"  EXP-020 avait fixe   xmin = $312,751   k = 5,000   -> facteur {xmin/312_751:.2f}")

    coarse = logspace_k(100, 50_000, 60)
    sel = []
    for _ in range(args.boot):
        b = np.sort(RNG.choice(desc, size=desc.size, replace=True))[::-1]
        sel.append(select_xmin(b, coarse)[:2])
    bx = np.array([s[0] for s in sel])
    bk = np.array([s[1] for s in sel])
    print(f"  bootstrap ({args.boot}) : xmin 95% [{np.percentile(bx,2.5):,.0f}, "
          f"{np.percentile(bx,97.5):,.0f}]  mediane ${np.median(bx):,.0f}")
    print(f"                        k 95% [{np.percentile(bk,2.5):,.0f}, "
          f"{np.percentile(bk,97.5):,.0f}]  mediane {np.median(bk):,.0f}")

    tail = desc[:k]
    p = gof_pvalue(tail, xmin, alpha, args.gof_boot)
    print(f"  GoF Pareto au xmin selectionne : p = {p:.3f}  "
          f"({'rejete' if p < 0.05 else 'non rejete'})\n")

    print("--- (a) classement au xmin selectionne ---")
    fits = rank_at(tail, xmin)
    res = summarise(fits)
    for name, (ll, par) in sorted(fits.items(), key=lambda t: -t[1][0].sum()):
        ps = "  ".join(f"{a}={b:.4g}" if not isinstance(b, bool) else f"{a}={b}"
                       for a, b in par.items())
        print(f"  {name:<15} logL={ll.sum():13.1f}   {ps}")
    print()
    for name, (r, pv, _) in res.items():
        if name == "pareto_cutoff":
            print(f"  {'pareto vs pareto_cutoff':<32} LR chi2={r:8.1f} p={pv:.3f}")
        elif "_vs_" in name:
            a, b = name.split("_vs_")
            a = "pareto_cutoff" if a == "cutoff" else a
            who = a if r > 0 else b
            print(f"  {a + ' vs ' + b:<32} R={r:+7.2f} p={pv:.3f}  "
                  f"{who + ' favorise' if pv < 0.05 else 'NON SEPARES'}")
        else:
            who = "pareto" if r > 0 else name
            print(f"  {'pareto vs ' + name:<32} R={r:+7.2f} p={pv:.3f}  "
                  f"{who + ' favorise' if pv < 0.05 else 'indecis'}")

    print("\n--- (b) stabilite du classement sur la grille ---")
    rows = []
    print(f"  {'k':>7} {'xmin $':>12} {'lognorm':>9} {'weibull':>9} {'cutoff':>9} "
          f"{'expon':>8}  {'ln vs wb':>9}  {'estimable'}")
    for kk in logspace_k(200, 50_000, args.grid):
        kk = int(kk)
        if kk >= desc.size:
            continue
        xm = float(desc[kk])
        t = desc[:kk]
        f = rank_at(t, xm)
        s = summarise(f)
        est = estimable(f)
        get = lambda n: s.get(n, (float("nan"),) * 3)  # noqa: E731
        ln, wb, ct, ex = get("lognormal"), get("weibull"), get("pareto_cutoff"), get("exponential")
        lw = get("lognormal_vs_weibull")
        cl, cw = get("cutoff_vs_lognormal"), get("cutoff_vs_weibull")
        ct_wins = est and cl[0] > 0 and cl[1] < 0.05 and cw[0] > 0 and cw[1] < 0.05
        print(f"  {kk:>7,} {xm:>12,.0f} {ln[0]:>9.2f} {wb[0]:>9.2f} {ct[0]:>9.1f} "
              f"{ex[0]:>8.2f}  {lw[0]:>9.2f}  "
              f"{('oui' + ('  cutoff gagne' if ct_wins else '')) if est else 'NON — sur borne'}")
        rows.append({
            "k": kk, "xmin": round(xm, 2), "estimable": int(est),
            "R_cutoff_vs_lognormal": round(cl[0], 4), "p_cutoff_vs_lognormal": round(cl[1], 4),
            "R_cutoff_vs_weibull": round(cw[0], 4), "p_cutoff_vs_weibull": round(cw[1], 4),
            "R_lognormal": round(ln[0], 4), "p_lognormal": round(ln[1], 4),
            "R_weibull": round(wb[0], 4), "p_weibull": round(wb[1], 4),
            "LR_cutoff": round(ct[0], 4), "p_cutoff": round(ct[1], 4),
            "R_exponential": round(ex[0], 4), "p_exponential": round(ex[1], 4),
            "R_ln_vs_wb": round(lw[0], 4), "p_ln_vs_wb": round(lw[1], 4),
            "ln_mu": round(f.get("lognormal", (None, {}))[1].get("mu", float("nan")), 4),
            "ln_sigma": round(f.get("lognormal", (None, {}))[1].get("sigma", float("nan")), 4),
            "wb_beta": round(f.get("weibull", (None, {}))[1].get("beta", float("nan")), 6),
            "wb_lambda": f"{f.get('weibull', (None, {}))[1].get('lambda_over_xmin', float('nan')):.3e}",
        })
    print("  R<0 => le modele bat pareto.  'NON' => une alternative est sur sa borne :")
    print("  elle degenere vers la limite loi-de-puissance de sa famille, et son R ne dit rien.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} thresholds -> {args.out}")


if __name__ == "__main__":
    main()
