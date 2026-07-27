"""Revue FABLE — corrélations partielles (EXP-023) et plancher 5 evenements (EXP-021).

    .venv/bin/python review/r4_leadlag.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "experiments" / "data"
POWER_FLOOR = 200
SOURCES = {"BTC": DATA / "exp021_hours.csv", "ETH": DATA / "exp023_ETH.csv",
           "SOL": DATA / "exp023_SOL.csv", "HYPE": DATA / "exp023_HYPE.csv"}


def load(path):
    rows = list(csv.DictReader(path.open()))
    out = []
    for r in rows:
        if r["usable"] != "1" or int(r["n_hl"]) < POWER_FLOOR:
            continue
        out.append({"range": float(r["range_bps"]), "nret": int(r["nret_hl_binance"]),
                    "peak": float(r["peak_ms_hl_binance"])})
    return out


data = {a: load(p) for a, p in SOURCES.items()}

# ---------------------------------------------------------------- estimateurs
def partial_linres(a, b, c):
    """Leur methode : residus de regressions LINEAIRES sur rangs."""
    ra, rb, rc = (stats.rankdata(v) for v in (a, b, c))
    ra = ra - np.polyval(np.polyfit(rc, ra, 1), rc)
    rb = rb - np.polyval(np.polyfit(rc, rb, 1), rc)
    r = float(np.corrcoef(ra, rb)[0, 1])
    n = len(a)
    t = r * np.sqrt((n - 3) / max(1e-12, 1 - r * r))
    return r, float(2 * stats.t.sf(abs(t), n - 3))


def partial_formula(a, b, c):
    """Formule classique de la partielle sur les rho de Spearman."""
    rab = stats.spearmanr(a, b).statistic
    rac = stats.spearmanr(a, c).statistic
    rbc = stats.spearmanr(b, c).statistic
    r = (rab - rac * rbc) / np.sqrt((1 - rac**2) * (1 - rbc**2))
    n = len(a)
    t = r * np.sqrt((n - 3) / max(1e-12, 1 - r * r))
    return float(r), float(2 * stats.t.sf(abs(t), n - 3))


def partial_poly3(a, b, c):
    """Residus d'une regression cubique sur rangs — teste la linearite."""
    ra, rb, rc = (stats.rankdata(v) for v in (a, b, c))
    ra = ra - np.polyval(np.polyfit(rc, ra, 3), rc)
    rb = rb - np.polyval(np.polyfit(rc, rb, 3), rc)
    r = float(np.corrcoef(ra, rb)[0, 1])
    n = len(a)
    t = r * np.sqrt((n - 3) / max(1e-12, 1 - r * r))
    return r, float(2 * stats.t.sf(abs(t), n - 3))


def kendall_partial(a, b, c):
    tab = stats.kendalltau(a, b).statistic
    tac = stats.kendalltau(a, c).statistic
    tbc = stats.kendalltau(b, c).statistic
    return float((tab - tac * tbc) / np.sqrt((1 - tac**2) * (1 - tbc**2)))


def curvature(y, z):
    """La relation rang-rang est-elle lineaire ? test du terme quadratique."""
    ry, rz = stats.rankdata(y), stats.rankdata(z)
    rz = (rz - rz.mean()) / rz.std()
    X = np.column_stack([np.ones_like(rz), rz, rz**2])
    beta, res, *_ = np.linalg.lstsq(X, ry, rcond=None)
    yhat = X @ beta
    resid = ry - yhat
    dof = len(y) - 3
    se = np.sqrt(np.sum(resid**2) / dof * np.linalg.inv(X.T @ X)[2, 2])
    t = beta[2] / se
    return float(beta[2]), float(2 * stats.t.sf(abs(t), dof))


print("=" * 84)
print("A. par actif : partielle lin-rangs (leur methode) vs formule vs cubique vs Kendall")
print("=" * 84)
print(f"{'actif':<6}{'n':>4} | {'lin(tr|rg)':>11}{'p':>7} | {'formule':>9}{'p':>7} | "
      f"{'cubique':>9}{'p':>7} | {'Kendall':>9} | annonce")
ann = {"BTC": (-0.029, 0.695), "ETH": (-0.101, 0.164), "SOL": (-0.123, 0.096),
       "HYPE": (-0.103, 0.158)}
for a, rows in data.items():
    tr = np.log(np.array([r["nret"] for r in rows], dtype=float))
    rg = np.array([r["range"] for r in rows])
    pk = np.array([r["peak"] for r in rows])
    r1, p1 = partial_linres(tr, pk, rg)
    r2, p2 = partial_formula(tr, pk, rg)
    r3, p3 = partial_poly3(tr, pk, rg)
    r4 = kendall_partial(tr, pk, rg)
    print(f"{a:<6}{len(rows):>4} | {r1:>11.3f}{p1:>7.3f} | {r2:>9.3f}{p2:>7.3f} | "
          f"{r3:>9.3f}{p3:>7.3f} | {r4:>9.3f} | {ann[a]}")

print("\nlinearite des relations rang-rang (terme quadratique, p) :")
for a, rows in data.items():
    tr = np.log(np.array([r["nret"] for r in rows], dtype=float))
    rg = np.array([r["range"] for r in rows])
    pk = np.array([r["peak"] for r in rows])
    for nom, y, z in (("rang(peak)~rang(nret)", pk, tr), ("rang(peak)~rang(range)", pk, rg),
                      ("rang(nret)~rang(range)", tr, rg)):
        b2, p = curvature(y, z)
        flag = " <— courbure significative" if p < 0.05 else ""
        print(f"  {a:<5} {nom:<24} beta2={b2:+8.2f}  p={p:.4f}{flag}")

print("\n" + "=" * 84)
print("B. groupe (n=758) : reproduction des partielles annoncees -0.090 / -0.100")
print("=" * 84)
zt, zr, zp = [], [], []
for a, rows in data.items():
    tr = np.log(np.array([r["nret"] for r in rows], dtype=float))
    rg = np.array([r["range"] for r in rows])
    pk = np.array([r["peak"] for r in rows])
    z = lambda v: (v - v.mean()) / v.std()  # noqa: E731
    zt.append(z(tr)); zr.append(z(rg)); zp.append(z(pk))
zt, zr, zp = np.concatenate(zt), np.concatenate(zr), np.concatenate(zp)
n = zt.size
print(f"n = {n} (annonce 758)")
sp = stats.spearmanr(zt, zp)
print(f"marginale returns vs peak : rho={sp.statistic:+.3f} p={sp.pvalue:.2e} "
      f"(annonce -0.213, <0.0001)")
r, p = partial_linres(zt, zp, zr)
print(f"partielle returns | range : {r:+.4f} p={p:.4f}   (annonce -0.090, 0.0138)")
r, p = partial_linres(zr, zp, zt)
print(f"partielle range | returns : {r:+.4f} p={p:.4f}   (annonce -0.100, 0.0057)")
r, p = partial_poly3(zt, zp, zr)
print(f"  variante cubique returns|range : {r:+.4f} p={p:.4f}")
r, p = partial_poly3(zr, zp, zt)
print(f"  variante cubique range|returns : {r:+.4f} p={p:.4f}")
r, p = partial_formula(zt, zp, zr)
print(f"  variante formule returns|range : {r:+.4f} p={p:.4f}")
r, p = partial_formula(zr, zp, zt)
print(f"  variante formule range|returns : {r:+.4f} p={p:.4f}")
kt = kendall_partial(zt, zp, zr)
kr = kendall_partial(zr, zp, zt)
print(f"  Kendall partiel : returns|range {kt:+.4f}, range|returns {kr:+.4f}")

nb = [a for a in data if a != "BTC"]
zt2 = np.concatenate([ (lambda v: (v-v.mean())/v.std())(np.log(np.array([r['nret'] for r in data[a]], float))) for a in nb])
zr2 = np.concatenate([ (lambda v: (v-v.mean())/v.std())(np.array([r['range'] for r in data[a]])) for a in nb])
zp2 = np.concatenate([ (lambda v: (v-v.mean())/v.std())(np.array([r['peak'] for r in data[a]])) for a in nb])
r, p = partial_linres(zt2, zp2, zr2)
print(f"non-BTC groupe (n={zt2.size}) returns|range : {r:+.4f} p={p:.4f} "
      f"(annonce -0.119, 0.0045)")
ps = []
for a in nb:
    tr = np.log(np.array([r["nret"] for r in data[a]], float))
    rg = np.array([r["range"] for r in data[a]])
    pk = np.array([r["peak"] for r in data[a]])
    ps.append(partial_linres(tr, pk, rg)[1])
chi2 = -2 * np.sum(np.log(ps))
print(f"Fisher (3 partielles non-BTC) : p = {stats.chi2.sf(chi2, 6):.4f} (annonce 0.063)")

print("\n" + "=" * 84)
print("C. EXP-021 : verification des chiffres et sensibilite au plancher 5 evts")
print("=" * 84)
rows21 = list(csv.DictReader((DATA / "exp021_hours.csv").open()))
for r in rows21:
    r["flagged"] = r["flagged"] == "1"
    r["usable"] = r["usable"] == "1"
    for v in ("hl", "binance", "okx"):
        r[f"n_{v}"] = int(r[f"n_{v}"]); r[f"maxsil_{v}"] = int(r[f"maxsil_{v}"])
    r["range_bps"] = float(r["range_bps"])
print(f"heures totales : {len(rows21)} (annonce 193)")
fl = [r for r in rows21 if r["flagged"]]
fl_ok = [r for r in fl if r["usable"]]
print(f"flaggees {len(fl)} (annonce 49), completes {len(fl_ok)} "
      f"({100*len(fl_ok)/len(fl):.1f}%, annonce 47 = 95.9%)")
usable = [r for r in rows21 if r["usable"]]
print(f"usable : {len(usable)} (annonce 191)")

rec = fl_ok
ret = [r for r in rows21 if r["usable"] and not r["flagged"]]
rr = np.array([r["range_bps"] for r in rec]); tr_ = np.array([r["range_bps"] for r in ret])
rn = np.array([r["n_hl"] for r in rec], float); tn = np.array([r["n_hl"] for r in ret], float)
print(f"mediane range rec/ret : {np.median(rr):.1f} / {np.median(tr_):.1f} (annonce 35.5 / 34.8)")
print(f"mediane n_hl rec/ret  : {np.median(rn):.0f} / {np.median(tn):.0f} (annonce 9,442 / 9,760)")
allr = np.array([r["range_bps"] for r in rows21]); allf = np.array([float(r["flagged"]) for r in rows21])
alln = np.array([r["n_hl"] for r in rows21], float)
print(f"Spearman(range, flagged) = {stats.spearmanr(allr, allf).statistic:+.3f} (annonce +0.034)")
print(f"Spearman(n_hl,  flagged) = {stats.spearmanr(alln, allf).statistic:+.3f} (annonce -0.015)")
mw = stats.mannwhitneyu(rr, tr_, alternative="two-sided")
z_ = (mw.statistic - len(rr) * len(tr_) / 2) / np.sqrt(len(rr) * len(tr_) * (len(rr) + len(tr_) + 1) / 12)
print(f"Mann-Whitney rec vs ret (range) : z={z_:+.2f} p={mw.pvalue:.3f} (annonce +0.47, 0.635)")

pk_rec = np.array([float(r["peak_ms_hl_binance"]) for r in rec])
print(f"\nrecuperees : {len(pk_rec)} h, Binance mene {int((pk_rec>0).sum())}/{len(pk_rec)}, "
      f"mediane {np.median(pk_rec):.0f} ms (annonce 47/47, 575)")
ext = [r for r in usable if r["n_hl"] >= POWER_FLOOR]
pk_ext = np.array([float(r["peak_ms_hl_binance"]) for r in ext])
rg_ext = np.array([r["range_bps"] for r in ext])
print(f"etendu : {len(ext)} h, mediane {np.median(pk_ext):.0f} ms, "
      f"Spearman(range, peak) = {stats.spearmanr(rg_ext, pk_ext).statistic:+.3f} "
      f"(annonce 191 h, 575 ms, -0.099)")
print(f"span range_bps etendu : [{rg_ext.min():.1f}, {rg_ext.max():.1f}] (annonce 4.2-187.8)")

print("\n--- le plancher de 5 evenements : quand peut-il mordre ? ---")
print("il ne peut changer une classification que si 0.25 x (compte attendu de l'autre")
print("venue dans la fenetre) < 5, i.e. attendu < 20 evenements.")
for r in rows21:
    r["exp_okx_in_hl_sil"] = r["n_okx"] / 3.6e6 * r["maxsil_hl"] if r["maxsil_hl"] > 0 else 0.0
    r["exp_bin_in_hl_sil"] = r["n_binance"] / 3.6e6 * r["maxsil_hl"] if r["maxsil_hl"] > 0 else 0.0
sil_hl = [r for r in rows21 if r["maxsil_hl"] >= 60_000]
print(f"heures avec silence HL >= 60 s : {len(sil_hl)}")
crit = [r for r in sil_hl if max(r['exp_bin_in_hl_sil'], r['exp_okx_in_hl_sil']) < 20]
print(f"  ... dont attendu max (binance, okx) < 20 : {len(crit)} — le plancher ne peut")
print("      influencer la classe de HL que sur celles-ci")
for v in ("binance", "okx"):
    sil_v = [r for r in rows21 if r[f"maxsil_{v}"] >= 60_000]
    crit_v = [r for r in sil_v
              if (r["n_hl"] / 3.6e6 * r[f"maxsil_{v}"]) < 20 and r["usable"]]
    print(f"heures usable avec silence {v} >= 60 s et attendu HL < 20 : {len(crit_v)}"
          f" (sur {len(sil_v)} silences {v})")
    for r in crit_v[:6]:
        print(f"    {r['date']} {int(r['hour']):02d}h  maxsil_{v}={r[f'maxsil_{v}']/1000:.0f}s "
              f"n_hl={r['n_hl']} attendu={r['n_hl']/3.6e6*r[f'maxsil_{v}']:.1f} "
              f"peak={r['peak_ms_hl_binance']}")

# sensibilite : si on retire ces heures 'floor-dependantes' du jeu etendu
dep = {(r["date"], r["hour"]) for v in ("binance", "okx") for r in rows21
       if r[f"maxsil_{v}"] >= 60_000 and (r["n_hl"] / 3.6e6 * r[f"maxsil_{v}"]) < 20
       and r["usable"]}
kept = [r for r in ext if (r["date"], r["hour"]) not in dep]
pk_k = np.array([float(r["peak_ms_hl_binance"]) for r in kept])
rg_k = np.array([r["range_bps"] for r in kept])
print(f"\nsans les {len(dep)} heures ou le plancher a pu decider : n={len(kept)}, "
      f"mediane {np.median(pk_k):.0f} ms, Binance mene {int((pk_k>0).sum())}/{len(pk_k)}, "
      f"Spearman(range,peak)={stats.spearmanr(rg_k, pk_k).statistic:+.3f}")
