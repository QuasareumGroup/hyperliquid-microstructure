"""Revue FABLE — complements : IC des ratios de segments, GoF dans la bande
« rien n'ajuste », variantes Spearman du drapeau, plancher sur ETH/SOL/HYPE,
facteur par heure au sein des majors, la clause « three decimal places ».

    .venv/bin/python review/r5_complements.py
"""
from __future__ import annotations

import csv
import gzip
import math
from pathlib import Path

import numpy as np
from scipy import optimize, stats

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "experiments" / "data"


def sec(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


# ------------------------------------------------------------------- donnees
ts_l, hip_l, fills_l, ntl_l = [], [], [], []
with (DATA / "exp017_episodes.csv").open() as fh:
    fh.readline()
    for line in fh:
        p = line.rstrip("\n").split(",")
        ts_l.append(int(p[0])); hip_l.append(int(p[2]))
        fills_l.append(int(p[4])); ntl_l.append(float(p[5]))
ts = np.array(ts_l, dtype=np.int64); hip = np.array(hip_l, dtype=np.int8)
fills = np.array(fills_l, dtype=np.int64); ep = np.array(ntl_l)

fh_l, fv_l = [], []
with gzip.open(DATA / "exp024_fill_notionals.csv.gz", "rt") as fh:
    fh.readline()
    for line in fh:
        a, b = line.split(",")
        fh_l.append(int(a)); fv_l.append(float(b))
fhip = np.array(fh_l, dtype=np.int8); fl = np.array(fv_l)


def beta_q(sx, q, nd, rng):
    n = sx.size
    m = int(np.ceil(q / 100 * n))
    v = rng.beta(m, n - m + 1, nd)
    return sx[np.clip(np.ceil(n * v).astype(np.int64) - 1, 0, n - 1)]


sec("1. IC des ratios de facteurs majors/HIP-3 (Beta independant, 20k tirages)")
em, eh = np.sort(ep[hip == 0]), np.sort(ep[hip == 1])
fm, fh3 = np.sort(fl[fhip == 0]), np.sort(fl[fhip == 1])
pub = {50: (1.06, 1.03, 1.09), 90: (1.30, 1.24, 1.36),
       99: (0.82, 0.74, 0.90), 99.9: (0.85, 0.65, 1.11)}
for q in (50, 90, 99, 99.9):
    r1 = beta_q(em, q, 20000, np.random.default_rng(101)) / beta_q(fm, q, 20000, np.random.default_rng(102))
    r2 = beta_q(eh, q, 20000, np.random.default_rng(103)) / beta_q(fh3, q, 20000, np.random.default_rng(104))
    rr = r1 / r2
    lo, hi = np.percentile(rr, [2.5, 97.5])
    print(f"  p{q:<5} ratio={np.median(rr):5.2f}  IC [{lo:5.2f}, {hi:5.2f}]   publie {pub[q]}")

sec("2. GoF absolu DANS la bande exclue ($49k-$163k) : quelque chose ajuste-t-il ?")
x = ep[hip == 0]; x = x[x > 0]
desc = np.sort(x)[::-1]


def fit_ln(t, xmin):
    lx, lxm = np.log(t), math.log(xmin)
    B_MU, B_LS = (-60.0, 40.0), (math.log(0.05), math.log(25.0))

    def nll(p):
        mu, ls = p
        s = math.exp(ls)
        v = stats.norm.logpdf(lx, mu, s) - lx - stats.norm.logsf((lxm - mu) / s)
        return -float(v.sum()) if np.all(np.isfinite(v)) else 1e12

    best = None
    for mu0 in (lx.mean(), lxm, lxm - 5, 0.0, -20.0):
        for s0 in (max(lx.std(), 0.3), 1.0, 3.0, 8.0):
            r = optimize.minimize(nll, [mu0, math.log(s0)], method="L-BFGS-B",
                                  bounds=[B_MU, B_LS])
            if best is None or r.fun < best.fun:
                best = r
    return best.x[0], math.exp(best.x[1])


def ks_ln(t, xmin, mu, s):
    xs = np.sort(t)
    num = stats.norm.sf((np.log(xs) - mu) / s)
    den = stats.norm.sf((math.log(xmin) - mu) / s)
    cdf = 1.0 - num / den
    n = xs.size
    i = np.arange(n)
    return max(float(np.max(np.abs(cdf - i / n))), float(np.max(np.abs(cdf - (i + 1) / n))))


def fit_wb(t, xmin):
    u = t / xmin
    lu = np.log(u)
    B_LB, B_LL = (math.log(0.01), math.log(20.0)), (-45.0, 45.0)

    def nll(p):
        b, lam = math.exp(p[0]), math.exp(p[1])
        llam = math.log(lam)
        if b * (float(lu.max()) - llam) > 690 or b * (-llam) > 690:
            return 1e12
        z, z0 = np.exp(b * (lu - llam)), math.exp(b * (-llam))
        v = math.log(b / lam) + (b - 1) * (lu - llam) - z + z0
        return -float(v.sum()) if np.all(np.isfinite(v)) else 1e12

    best = None
    for b0 in (0.05, 0.15, 0.5, 1.0):
        for l0 in (1e-6, 1e-3, 0.5, 5.0):
            r = optimize.minimize(nll, [math.log(b0), math.log(l0)], method="L-BFGS-B",
                                  bounds=[B_LB, B_LL])
            if best is None or r.fun < best.fun:
                best = r
    return math.exp(best.x[0]), math.exp(best.x[1])


def ks_wb(t, xmin, b, lam):
    u = np.sort(t / xmin)
    z0 = (1.0 / lam) ** b
    cdf = 1.0 - np.exp(-((u / lam) ** b) + z0)
    n = u.size
    i = np.arange(n)
    return max(float(np.max(np.abs(cdf - i / n))), float(np.max(np.abs(cdf - (i + 1) / n))))


for k in (26113, 18871):
    xm = float(desc[k]); t = desc[:k]
    mu, s = fit_ln(t, xm)
    d = ks_ln(t, xm, mu, s)
    rng = np.random.default_rng(3)
    worse, nb = 0, 200
    p0 = stats.norm.cdf((math.log(xm) - mu) / s)
    for _ in range(nb):
        u = p0 + (1 - p0) * rng.random(t.size)
        syn = np.exp(mu + s * stats.norm.ppf(u))
        mu2, s2 = fit_ln(syn, xm)
        worse += ks_ln(syn, xm, mu2, s2) >= d
    print(f"  k={k:,} xmin=${xm:,.0f} lognormale mu={mu:.2f} sigma={s:.2f} "
          f"KS={d:.4f} GoF p={worse/nb:.3f}")
    b, lam = fit_wb(t, xm)
    d = ks_wb(t, xm, b, lam)
    rng = np.random.default_rng(4)
    worse = 0
    z0 = (1.0 / lam) ** b
    for _ in range(nb):
        u = rng.random(t.size)
        syn = xm * lam * (z0 - np.log1p(-u)) ** (1.0 / b)
        b2, lam2 = fit_wb(syn, xm)
        worse += ks_wb(syn, xm, b2, lam2) >= d
    print(f"  k={k:,} xmin=${xm:,.0f} weibull beta={b:.4f} lam={lam:.3e} "
          f"KS={d:.4f} GoF p={worse/nb:.3f}")
print("  (bornes larges : mu dans [-60,40], ln lam dans [-45,45] — les fits convergent")
print("   a l'interieur ou pres des bornes, et le GoF rejette quand meme)")

sec("3. Spearman(activite, drapeau) : sur quelles heures les +0.034/-0.015 vivent-ils ?")
rows = list(csv.DictReader((DATA / "exp021_hours.csv").open()))
for r in rows:
    r["flagged"] = int(r["flagged"] == "1"); r["usable"] = r["usable"] == "1"
    r["range_bps"] = float(r["range_bps"]); r["n_hl"] = int(r["n_hl"])
allr = np.array([r["range_bps"] for r in rows]); allf = np.array([r["flagged"] for r in rows], float)
alln = np.array([r["n_hl"] for r in rows], float)
us = [r for r in rows if r["usable"]]
ur = np.array([r["range_bps"] for r in us]); uf = np.array([r["flagged"] for r in us], float)
un = np.array([r["n_hl"] for r in us], float)
print(f"  toutes 193 h : {stats.spearmanr(allr, allf).statistic:+.3f} / "
      f"{stats.spearmanr(alln, allf).statistic:+.3f}")
print(f"  usable 191 h : {stats.spearmanr(ur, uf).statistic:+.3f} / "
      f"{stats.spearmanr(un, uf).statistic:+.3f}   (annonce +0.034 / -0.015)")

sec("4. plancher 5 evts : silences >= 60 s et comptes attendus, 4 actifs")
for asset, path in (("BTC", "exp021_hours.csv"), ("ETH", "exp023_ETH.csv"),
                    ("SOL", "exp023_SOL.csv"), ("HYPE", "exp023_HYPE.csv")):
    rows2 = list(csv.DictReader((DATA / path).open()))
    n_sil = {"hl": 0, "binance": 0, "okx": 0}
    crit = 0
    for r in rows2:
        for v in n_sil:
            ms = int(r[f"maxsil_{v}"])
            if ms >= 60_000:
                n_sil[v] += 1
                others = [w for w in n_sil if w != v]
                if max(int(r[f"n_{w}"]) / 3.6e6 * ms for w in others) < 20:
                    crit += 1
    print(f"  {asset}: silences>=60s hl/bin/okx = {n_sil['hl']}/{n_sil['binance']}/"
          f"{n_sil['okx']} ; heures ou le plancher PEUT decider : {crit}")

sec("5. facteur par heure UTC, au sein des majors seuls")
h = (ts // 3_600_000) % 24
print(f"  {'h UTC':>6}{'tous':>8}{'majors':>8}{'HIP-3':>8}{'part ep HIP-3':>14}")
for hh in (2, 8, 14, 20):
    m = h == hh
    mm = m & (hip == 0); mh = m & (hip == 1)
    print(f"  {hh:>6}{fills[m].sum()/m.sum():>8.3f}{fills[mm].sum()/mm.sum():>8.3f}"
          f"{fills[mh].sum()/mh.sum():>8.3f}{100*mh.sum()/m.sum():>13.1f}%")

sec("6. « reproduces every count statistic to three decimal places »")
f1, f2 = 2_010_042 / 351_540, 2_010_314 / 351_648
print(f"  facteur 1re passe {f1:.5f} -> {f1:.3f} ; 2e passe {f2:.5f} -> {f2:.3f} ; "
      f"egaux a 3 decimales ? {round(f1,3) == round(f2,3)}")
