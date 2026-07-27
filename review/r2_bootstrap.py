"""Revue FABLE — Partie 2 : le bootstrap des quantiles de compression.

Constat prealable : AUCUN code de bootstrap n'est committe (pas de fonction `bq`
dans le depot ; exp024_analyse.py ne calcule que des points). Les IC publies
([4.41,4.76] a p99, [9.24,11.21] a p99.9, et les ratios de segments) ne sont
reproductibles d'aucun script versionne. Ce script les re-derive de trois facons :

  (i)   representation binomiale/Beta de la statistique d'ordre (ce que EXP-024
        dit avoir fait), cotes episode et fill INDEPENDANTS, 20,000 tirages ;
  (ii)  bootstrap naif (re-echantillonnage complet + np.percentile), 3,000 tirages ;
  (iii) bootstrap par grappes d'episodes sur l'echantillon 12 h (exp016_fills.csv,
        qui garde l'appartenance episode->fills), pour mesurer l'effet de la
        DEPENDANCE episode/fill que (i) ignore ;
  (iv)  bootstrap par grappes de JOURS du facteur de comptage 5.72.

    .venv/bin/python review/r2_bootstrap.py
"""
from __future__ import annotations

import csv
import gzip
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(42)
QS = (50.0, 90.0, 99.0, 99.9)
PUB = {50.0: (2.00, 1.97, 2.03), 90.0: (3.26, 3.21, 3.31),
       99.0: (4.58, 4.41, 4.76), 99.9: (10.02, 9.24, 11.21)}
PUB_RATIO = {50.0: (1.06, 1.03, 1.09), 90.0: (1.30, 1.24, 1.36),
             99.0: (0.82, 0.74, 0.90), 99.9: (0.85, 0.65, 1.11)}


def load_episodes() -> tuple[np.ndarray, ...]:
    ts, hip, ntl = [], [], []
    with (REPO / "experiments" / "data" / "exp017_episodes.csv").open() as fh:
        fh.readline()
        for line in fh:
            p = line.rstrip("\n").split(",")
            ts.append(int(p[0])); hip.append(int(p[2])); ntl.append(float(p[5]))
    return (np.array(ts, dtype=np.int64), np.array(hip, dtype=np.int8),
            np.array(ntl))


def load_fills() -> tuple[np.ndarray, np.ndarray]:
    hips, vals = [], []
    with gzip.open(REPO / "experiments" / "data" / "exp024_fill_notionals.csv.gz", "rt") as fh:
        fh.readline()
        for line in fh:
            h, v = line.split(",")
            hips.append(int(h)); vals.append(float(v))
    return np.array(hips, dtype=np.int8), np.array(vals)


def beta_boot_quantile(sorted_x: np.ndarray, q: float, n_draw: int,
                       rng: np.random.Generator) -> np.ndarray:
    """Tirages bootstrap EXACTS du quantile d'ordre (representation Beta).

    Pour un re-echantillon de taille n tire de l'ECDF, la m-ieme statistique
    d'ordre (m = ceil(q n)) vaut x_(K) avec K = ceil(n V), V ~ Beta(m, n-m+1) —
    strictement equivalent a la representation binomiale de l'indice, un tri
    remplace chaque re-echantillon.
    """
    n = sorted_x.size
    m = int(np.ceil(q / 100.0 * n))
    v = rng.beta(m, n - m + 1, size=n_draw)
    idx = np.clip(np.ceil(n * v).astype(np.int64) - 1, 0, n - 1)
    return sorted_x[idx]


def binom_boot_quantile(sorted_x: np.ndarray, q: float, n_draw: int,
                        rng: np.random.Generator) -> np.ndarray:
    """Variante 'binomiale directe' (approximation courante) : K ~ Bin(n, q)."""
    n = sorted_x.size
    k = rng.binomial(n, q / 100.0, size=n_draw)
    return sorted_x[np.clip(k - 1, 0, n - 1)]


def ci(v: np.ndarray) -> tuple[float, float]:
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


ts, hip, ep = load_episodes()
fhip, fl = load_fills()
ep_s, fl_s = np.sort(ep), np.sort(fl)

print("=" * 78)
print("(i) Beta/binomiale, cotes independants, 20,000 tirages — table publiee")
print("=" * 78)
print(f"{'q':>6}{'facteur':>9}{'IC Beta':>18}{'IC binom':>18}{'IC publie':>18}")
draws_beta = {}
for q in QS:
    eb = beta_boot_quantile(ep_s, q, 20_000, np.random.default_rng(1))
    fb = beta_boot_quantile(fl_s, q, 20_000, np.random.default_rng(2))
    rb = eb / fb
    draws_beta[q] = rb
    e2 = binom_boot_quantile(ep_s, q, 20_000, np.random.default_rng(3))
    f2 = binom_boot_quantile(fl_s, q, 20_000, np.random.default_rng(4))
    r2 = e2 / f2
    lo, hi = ci(rb); lo2, hi2 = ci(r2)
    fac = float(np.percentile(ep, q) / np.percentile(fl, q))
    p = PUB[q]
    print(f"p{q:<5}{fac:>9.2f}  [{lo:6.2f}, {hi:6.2f}]  [{lo2:6.2f}, {hi2:6.2f}]"
          f"  [{p[1]:6.2f}, {p[2]:6.2f}]")

print("\ndiscretisation a p99.9 (episodes) :")
eb = beta_boot_quantile(ep_s, 99.9, 20_000, np.random.default_rng(1))
print(f"  tirages distincts du quantile episode p99.9 : {np.unique(eb).size} "
      f"(sur 20,000) ; ecart-type ${eb.std():,.0f} ; "
      f"IC quantile seul [${np.percentile(eb,2.5):,.0f}, ${np.percentile(eb,97.5):,.0f}]")

print("\n" + "=" * 78)
print("(ii) bootstrap naif complet, 3,000 tirages, np.percentile (interpolation)")
print("=" * 78)
n_naive = 3_000
nat_ep = {q: np.empty(n_naive) for q in QS}
nat_fl = {q: np.empty(n_naive) for q in QS}
rng = np.random.default_rng(7)
for i in range(n_naive):
    se = ep[rng.integers(0, ep.size, ep.size)]
    for q in QS:
        nat_ep[q][i] = np.percentile(se, q)
rng = np.random.default_rng(8)
for i in range(n_naive):
    sf = fl[rng.integers(0, fl.size, fl.size)]
    for q in QS:
        nat_fl[q][i] = np.percentile(sf, q)
print(f"{'q':>6}{'IC naif':>18}{'IC Beta (i)':>18}{'IC publie':>18}")
for q in QS:
    r = nat_ep[q] / nat_fl[q]
    lo, hi = ci(r)
    lob, hib = ci(draws_beta[q])
    p = PUB[q]
    print(f"p{q:<5}  [{lo:6.2f}, {hi:6.2f}]  [{lob:6.2f}, {hib:6.2f}]  [{p[1]:6.2f}, {p[2]:6.2f}]")

print("\n" + "=" * 78)
print("(iii) dependance episode/fill — grappes d'episodes, echantillon 12 h")
print("=" * 78)
rows = list(csv.DictReader((REPO / "experiments" / "data" / "exp016_fills.csv").open()))
ep_id = np.array([int(r["episode"]) for r in rows])
fn = np.array([float(r["notional"]) for r in rows])
n_epi = ep_id.max() + 1
ep_tot = np.zeros(n_epi)
np.add.at(ep_tot, ep_id, fn)
order = np.argsort(ep_id, kind="stable")
fn_by_ep = fn[order]
bounds = np.searchsorted(ep_id[order], np.arange(n_epi + 1))
starts, ends = bounds[:-1], bounds[1:]
print(f"12 h : {n_epi:,} episodes, {fn.size:,} fills")

n_cl = 4_000
res_cl = {q: np.empty(n_cl) for q in QS}
res_ind = {q: np.empty(n_cl) for q in QS}
rng = np.random.default_rng(11)
ep_tot_s = np.sort(ep_tot)
fn_s = np.sort(fn)
for i in range(n_cl):
    pick = rng.integers(0, n_epi, n_epi)
    seg = [fn_by_ep[starts[p]:ends[p]] for p in pick]
    f_res = np.concatenate(seg)
    e_res = ep_tot[pick]
    for q in QS:
        res_cl[q][i] = np.percentile(e_res, q) / np.percentile(f_res, q)
for q in QS:
    eb = beta_boot_quantile(ep_tot_s, q, n_cl, np.random.default_rng(21))
    fb = beta_boot_quantile(fn_s, q, n_cl, np.random.default_rng(22))
    res_ind[q] = eb / fb
print(f"{'q':>6}{'grappes (correct)':>20}{'independant':>18}{'rapport largeur':>17}")
for q in QS:
    lo, hi = ci(res_cl[q]); lo2, hi2 = ci(res_ind[q])
    w = (hi - lo) / max(hi2 - lo2, 1e-12)
    print(f"p{q:<5}  [{lo:6.2f}, {hi:6.2f}]   [{lo2:6.2f}, {hi2:6.2f}]   {w:>8.2f}")
print("  rapport < 1 : l'independance SURESTIME la largeur (conservateur) ;")
print("  rapport > 1 : elle la sous-estime (anti-conservateur).")

print("\n" + "=" * 78)
print("(iv) IC par grappes de jours sur le facteur de comptage 5.72")
print("=" * 78)
fills_col = []
with (REPO / "experiments" / "data" / "exp017_episodes.csv").open() as fh:
    fh.readline()
    for line in fh:
        p = line.rstrip("\n").split(",")
        fills_col.append(int(p[4]))
fills_arr = np.array(fills_col, dtype=np.int64)
day = (ts // 86_400_000).astype(np.int64)
udays, inv = np.unique(day, return_inverse=True)
df = np.zeros(udays.size); de = np.zeros(udays.size)
np.add.at(df, inv, fills_arr.astype(float))
np.add.at(de, inv, 1.0)
rng = np.random.default_rng(31)
draws = np.empty(20_000)
for i in range(20_000):
    pick = rng.integers(0, udays.size, udays.size)
    draws[i] = df[pick].sum() / de[pick].sum()
lo, hi = ci(draws)
print(f"facteur 5.72 : IC 95% grappes-jours [{lo:.2f}, {hi:.2f}]  "
      f"(ecart-type {draws.std():.3f})")
iid = np.empty(20_000)
rng = np.random.default_rng(32)
n = fills_arr.size
for i in range(20_000):
    k = rng.binomial(n, 0.5)  # placeholder, remplace ci-dessous
    break
# bootstrap iid episode : re-echantillonner les episodes
for i in range(20_000):
    pick = rng.integers(0, n, n // 10)  # 10% suffit pour l'echelle
    iid[i] = fills_arr[pick].mean()
print(f"pour reference, bootstrap iid episodes (10% sous-echantillon) : "
      f"sd du facteur ~ {iid.std() * np.sqrt(0.1):.4f}")
print("\nLecture : si l'IC grappes-jours est bien plus large que l'IC iid, la")
print("dispersion inter-jours (cascades) domine et un IC episode-iid serait illusoire.")
