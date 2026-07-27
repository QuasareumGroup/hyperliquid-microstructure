"""Revue FABLE — Partie 2 : la queue. Ajusteurs independants, selection CSN,
Vuong, GoF, et deux simulations adverses du 'renversement'.

Tout est reecrit ici (aucun import depuis experiments/). Donnees : majors de
exp017_episodes.csv.

    .venv/bin/python review/r3_tail.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy import optimize, stats

REPO = Path(__file__).resolve().parent.parent
GRID_K = [200, 277, 383, 530, 733, 1015, 1404, 1943, 2688, 3720, 5147, 7123,
          9856, 13638, 18871, 26113, 36134, 50000]


# ------------------------------------------------------------------ ajusteurs
def ll_pareto(x: np.ndarray, xmin: float):
    a = x.size / np.log(x / xmin).sum()
    return np.log(a / xmin) - (a + 1) * np.log(x / xmin), {"alpha": a}


def ll_expon(x: np.ndarray, xmin: float):
    lam = 1.0 / np.mean(x - xmin)
    return math.log(lam) - lam * (x - xmin), {"lambda": lam}


def ll_lognorm(x: np.ndarray, xmin: float):
    lx, lxm = np.log(x), math.log(xmin)
    B_MU, B_LS = (-60.0, 40.0), (math.log(0.05), math.log(25.0))

    def nll(p):
        mu, ls = p
        s = math.exp(ls)
        v = stats.norm.logpdf(lx, mu, s) - lx - stats.norm.logsf((lxm - mu) / s)
        return -float(v.sum()) if np.all(np.isfinite(v)) else 1e12

    best = None
    for mu0 in (lx.mean(), lxm, lxm - 5, 0.0):
        for s0 in (max(lx.std(), 0.3), 1.0, 3.0):
            r = optimize.minimize(nll, [mu0, math.log(s0)], method="L-BFGS-B",
                                  bounds=[B_MU, B_LS])
            if best is None or r.fun < best.fun:
                best = r
    mu, s = best.x[0], math.exp(best.x[1])
    v = stats.norm.logpdf(lx, mu, s) - lx - stats.norm.logsf((lxm - mu) / s)
    onb = (min(abs(mu - B_MU[0]), abs(mu - B_MU[1])) < 1e-3
           or min(abs(best.x[1] - B_LS[0]), abs(best.x[1] - B_LS[1])) < 1e-3)
    return v, {"mu": mu, "sigma": s, "on_bound": onb}


def ll_weib(x: np.ndarray, xmin: float):
    u = x / xmin
    lu = np.log(u)
    B_LB, B_LL = (math.log(0.01), math.log(20.0)), (-45.0, 45.0)

    def nll(p):
        b, lam = math.exp(p[0]), math.exp(p[1])
        llam = math.log(lam)
        # garde d'exposant : (u/lam)^b et (1/lam)^b explosent aux bornes explorees
        if b * (float(lu.max()) - llam) > 690.0 or b * (-llam) > 690.0:
            return 1e12
        with np.errstate(over="ignore"):
            z, z0 = np.exp(b * (lu - llam)), math.exp(b * (-llam))
            v = math.log(b / lam) + (b - 1) * (lu - llam) - z + z0
        return -float(v.sum()) if np.all(np.isfinite(v)) else 1e12

    best = None
    for b0 in (0.05, 0.15, 0.5, 1.0):
        for l0 in (1e-3, 0.5, 5.0):
            r = optimize.minimize(nll, [math.log(b0), math.log(l0)], method="L-BFGS-B",
                                  bounds=[B_LB, B_LL])
            if best is None or r.fun < best.fun:
                best = r
    b, lam = math.exp(best.x[0]), math.exp(best.x[1])
    llam = math.log(lam)
    z, z0 = np.exp(b * (lu - llam)), math.exp(b * (-llam))
    v = math.log(b / lam) + (b - 1) * (lu - llam) - z + z0 - math.log(xmin)
    onb = (min(abs(best.x[0] - B_LB[0]), abs(best.x[0] - B_LB[1])) < 1e-3
           or min(abs(best.x[1] - B_LL[0]), abs(best.x[1] - B_LL[1])) < 1e-3)
    return v, {"beta": b, "lam": lam, "on_bound": onb}


def vuong(l1: np.ndarray, l2: np.ndarray):
    d = l1 - l2
    s = d.std(ddof=1)
    if s <= 0:
        return 0.0, 1.0
    r = d.sum() / (math.sqrt(d.size) * s)
    return float(r), float(2 * stats.norm.sf(abs(r)))


def ks_pareto(tail: np.ndarray, xmin: float):
    n = tail.size
    a = n / np.log(tail / xmin).sum()
    xs = np.sort(tail)
    cdf = 1.0 - (xmin / xs) ** a
    i = np.arange(n)
    d = max(float(np.max(np.abs(cdf - i / n))), float(np.max(np.abs(cdf - (i + 1) / n))))
    return d, a


def logspace_k(lo, hi, n):
    return np.unique(np.round(np.exp(np.linspace(math.log(lo), math.log(hi), n))).astype(int))


def select_xmin(desc: np.ndarray, ks_grid):
    best = (math.inf, 0, 0.0, 0.0)
    for k in ks_grid:
        k = int(k)
        if k < 50 or k >= desc.size:
            continue
        xmin = float(desc[k])
        tail = desc[:k]
        if xmin <= 0 or tail[-1] <= xmin:
            continue
        d, a = ks_pareto(tail, xmin)
        if d < best[0]:
            best = (d, k, xmin, a)
    return best[2], best[1], best[0], best[3]


# ------------------------------------------------------------------- donnees
ntl, hips = [], []
with (REPO / "experiments" / "data" / "exp017_episodes.csv").open() as fh:
    fh.readline()
    for line in fh:
        p = line.rstrip("\n").split(",")
        hips.append(int(p[2])); ntl.append(float(p[5]))
x = np.array(ntl)[np.array(hips) == 0]
x = x[x > 0]
desc = np.sort(x)[::-1]
print(f"majors, n = {x.size:,} (annonce 289,283)")

print("\n=== 1. reproduction EXP-020 a k=5,000 (ajusteurs independants) ===")
k = 5000
xm = float(desc[k]); t = desc[:k]
print(f"xmin = ${xm:,.0f} (annonce $312,751)")
lp, pp = ll_pareto(t, xm)
le, pe = ll_expon(t, xm)
ln_, pl = ll_lognorm(t, xm)
lw, pw = ll_weib(t, xm)
print(f"logL: weibull {lw.sum():,.1f} (annonce -74,307.3)  lognormal {ln_.sum():,.1f} "
      f"(annonce -74,308.6)")
print(f"      pareto  {lp.sum():,.1f} (annonce -74,339.1)  exponentielle {le.sum():,.1f} "
      f"(annonce -76,965.1)")
for nom, lo in (("lognormal", ln_), ("weibull", lw), ("exponentielle", le)):
    r, p = vuong(lp, lo)
    print(f"  pareto vs {nom:<14} R={r:+6.2f} p={p:.4f}   (annonce -4.8 / -5.0 / +14.8)")

print("\n=== 2. selection CSN (mon code) ===")
xmin_s, k_s, d_s, a_s = select_xmin(desc, logspace_k(100, 50_000, 200))
print(f"xmin = ${xmin_s:,.0f}  k = {k_s:,}  KS = {d_s:.4f}  alpha = {a_s:.3f}")
print("(annonce $560,627, k=3,104, KS=0.0234, alpha=0.960)")

print("\n--- bootstrap de la selection (500 resamples, grille 60 pts) ---")
rng = np.random.default_rng(5)
coarse = logspace_k(100, 50_000, 60)
sels = []
for i in range(500):
    b = np.sort(rng.choice(x, x.size, replace=True))[::-1]
    sels.append(select_xmin(b, coarse)[0])
sels = np.array(sels)
print(f"IC 95% sur xmin : [${np.percentile(sels, 2.5):,.0f}, ${np.percentile(sels, 97.5):,.0f}]"
      f"   (annonce [$193,877, $986,963])")

print("\n=== 3. au xmin selectionne : Vuong et GoF ===")
t = desc[:k_s]; xm = float(desc[k_s])
lp, pp = ll_pareto(t, xm)
le, _ = ll_expon(t, xm)
ln_, pl = ll_lognorm(t, xm)
lw, pw = ll_weib(t, xm)
r, p = vuong(lp, le)
print(f"pareto vs exponentielle : R={r:+.2f} p={p:.2e}   (papier : +11.96, p<1e-4)")
r, p = vuong(ln_, lw)
print(f"lognormal vs weibull    : R={r:+.2f} p={p:.4f}   (annonce -3.53, p<0.001)")
r, p = vuong(lp, ln_)
print(f"pareto vs lognormal     : R={r:+.2f} p={p:.4f}")

# GoF Pareto, bootstrap parametrique, xmin fixe (comme eux)
rng = np.random.default_rng(9)
d_obs, a_hat = ks_pareto(t, xm)
worse = 0
for _ in range(1000):
    syn = xm * (1.0 - rng.random(t.size)) ** (-1.0 / a_hat)
    d_syn, _ = ks_pareto(syn, xm)
    worse += d_syn >= d_obs
print(f"GoF Pareto (xmin fixe, 1000 boots) : p = {worse/1000:.3f}   (annonce 0.010)")

# GoF ABSOLU de l'exponentielle au même seuil — le papier dit 'rejetee decisivement'
# via Vuong (relatif) ; ceci teste l'absolu.
lam = 1.0 / np.mean(t - xm)
d_obs_e = float(stats.kstest(t - xm, "expon", args=(0, 1 / lam)).statistic)
worse = 0
rng = np.random.default_rng(10)
for _ in range(1000):
    syn = rng.exponential(1 / lam, t.size)
    lam_s = 1.0 / syn.mean()
    d_syn = float(stats.kstest(syn, "expon", args=(0, 1 / lam_s)).statistic)
    worse += d_syn >= d_obs_e
print(f"GoF ABSOLU exponentielle (KS param-boot) : p = {worse/1000:.3f}, KS = {d_obs_e:.3f}")

print("\n=== 4. la grille, mon implementation (18 seuils d'EXP-022) ===")
print(f"{'k':>7}{'xmin$':>12}{'R p-vs-ln':>10}{'p':>8}{'R p-vs-wb':>10}{'p':>8}"
      f"{'R ln-vs-wb':>11}{'p':>8}{'borne?':>8}")
for kk in GRID_K:
    if kk >= desc.size:
        continue
    xm = float(desc[kk]); t = desc[:kk]
    lp, _ = ll_pareto(t, xm)
    ln_, pl = ll_lognorm(t, xm)
    lw, pw = ll_weib(t, xm)
    r1, p1 = vuong(lp, ln_)
    r2, p2 = vuong(lp, lw)
    r3, p3 = vuong(ln_, lw)
    onb = pl.get("on_bound") or pw.get("on_bound")
    print(f"{kk:>7,}{xm:>12,.0f}{r1:>+10.2f}{p1:>8.4f}{r2:>+10.2f}{p2:>8.4f}"
          f"{r3:>+11.2f}{p3:>8.4f}{'OUI' if onb else '':>8}")
print("(comparer aux colonnes R_lognormal / R_weibull / R_ln_vs_wb de exp022_grid.csv ;")
print(" R>0 = le premier modele du couple est favorise)")

print("\n=== 5. simulation adverse A : verite LOGNORMALE globale ===")
print("si le 'renversement' (Weibull gagne loin en queue) apparait aussi sous une")
print("verite lognormale, il ne prouve rien ; sinon il est informatif.")
mu0, s0 = float(np.log(x).mean()), float(np.log(x).std())
print(f"generateur : LN(mu={mu0:.2f}, sigma={s0:.2f}), n = {x.size:,}, 3 replicats")
SIM_K = [200, 733, 1943, 5147, 13638, 36134]
for rep in range(3):
    rng = np.random.default_rng(100 + rep)
    xs = np.exp(rng.normal(mu0, s0, x.size))
    dsc = np.sort(xs)[::-1]
    out = []
    for kk in SIM_K:
        xm = float(dsc[kk]); t = dsc[:kk]
        ln_, pl = ll_lognorm(t, xm)
        lw, pw = ll_weib(t, xm)
        r3, p3 = vuong(ln_, lw)
        onb = pl.get("on_bound") or pw.get("on_bound")
        out.append(f"k={kk}: R={r3:+.2f}{'*' if p3 < 0.01 else ' '}{'B' if onb else ''}")
    print("  rep", rep, " | ".join(out))
print("  (R<0* = Weibull gagne a p<0.01 — le motif observe sur les vraies donnees)")

print("\n=== 6. simulation adverse B : verite WEIBULL globale ===")
lwf, pwf = ll_weib(x[x >= 100.0], 100.0)
print(f"generateur : Weibull tronque ajuste sur x>=100 : beta={pwf['beta']:.3f}, "
      f"lam(x100)={pwf['lam']:.3g}, n = {x.size:,}")
for rep in range(3):
    rng = np.random.default_rng(200 + rep)
    u = rng.random(x.size)
    z0 = (1.0 / pwf["lam"]) ** pwf["beta"]
    xs = 100.0 * pwf["lam"] * (z0 - np.log1p(-u)) ** (1.0 / pwf["beta"])
    dsc = np.sort(xs)[::-1]
    out = []
    for kk in SIM_K:
        xm = float(dsc[kk]); t = dsc[:kk]
        ln_, pl = ll_lognorm(t, xm)
        lw, pw = ll_weib(t, xm)
        r3, p3 = vuong(ln_, lw)
        onb = pl.get("on_bound") or pw.get("on_bound")
        out.append(f"k={kk}: R={r3:+.2f}{'*' if p3 < 0.01 else ' '}{'B' if onb else ''}")
    print("  rep", rep, " | ".join(out))
print("  (R>0* = lognormale gagne a p<0.01 profond dans le corps — motif observe)")
