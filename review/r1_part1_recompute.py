"""Revue FABLE — Partie 1 : recalcul independant des chiffres porteurs.

N'importe rien depuis experiments/. Lit uniquement les fichiers versionnes :
  experiments/data/exp017_episodes.csv        (1ere passe, 351,540 episodes)
  experiments/data/exp024_fill_notionals.csv.gz (2e passe, fills)

    .venv/bin/python review/r1_part1_recompute.py
"""
from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
EP = REPO / "experiments" / "data" / "exp017_episodes.csv"
FL = REPO / "experiments" / "data" / "exp024_fill_notionals.csv.gz"


def sec(t: str) -> None:
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


# ---------------------------------------------------------------- load episodes
ts_l, coin_l, hip_l, user_l, fills_l, ntl_l = [], [], [], [], [], []
with EP.open() as fh:
    header = fh.readline().strip().split(",")
    assert header == ["ts", "coin", "hip3", "user", "fills", "notional"], header
    for line in fh:
        p = line.rstrip("\n").split(",")
        ts_l.append(int(p[0])); coin_l.append(p[1]); hip_l.append(int(p[2]))
        user_l.append(p[3]); fills_l.append(int(p[4])); ntl_l.append(float(p[5]))

ts = np.array(ts_l, dtype=np.int64)
coin = np.array(coin_l)
hip = np.array(hip_l, dtype=np.int8)
user = np.array(user_l)
fills = np.array(fills_l, dtype=np.int64)
ntl = np.array(ntl_l, dtype=float)
n_ep = ts.size
n_fl_col = int(fills.sum())

sec("A. Comptes et facteur d'inflation (fichier episodes, 1ere passe)")
print(f"episodes                = {n_ep:,}   (annonce 351,540)")
print(f"somme colonne fills     = {n_fl_col:,}   (annonce 2,010,042)")
print(f"facteur                 = {n_fl_col / n_ep:.4f}   (annonce 5.72)")
maj, h3 = hip == 0, hip == 1
print(f"majors  : {maj.sum():,} ep, {fills[maj].sum():,} fills, facteur {fills[maj].sum()/maj.sum():.4f} (annonce 5.78, 289,283 / 1,672,034)")
print(f"HIP-3   : {h3.sum():,} ep, {fills[h3].sum():,} fills, facteur {fills[h3].sum()/h3.sum():.4f} (annonce 5.43, 62,257 / 338,008)")
print(f"instruments             = {np.unique(coin).size:,}   (annonce 380)")
print(f"comptes                 = {np.unique(user).size:,}   (annonce 151,730)")
print(f"notionnel total         = ${ntl.sum()/1e9:.4f} bn   (annonce $15.53 bn)")
print(f"part episodes HIP-3     = {100*h3.sum()/n_ep:.2f}%  (annonce 17.7%)")
print(f"part notionnel HIP-3    = {100*ntl[h3].sum()/ntl.sum():.2f}%  (annonce 9.3%)")

sec("B. Tranchage par taille (buckets de quantiles, methode rang)")
order = np.argsort(ntl, kind="stable")
sn, sf = ntl[order], fills[order]
q50, q90, q99 = (float(np.percentile(ntl, q)) for q in (50, 90, 99))
print(f"bords dollars: p50=${q50:,.0f} p90=${q90:,.0f} p99=${q99:,.0f}"
      f"   (papier Table 2 : $1,117 / $39,307 / $549,060)")
edges = [0, int(round(0.5 * n_ep)), int(round(0.9 * n_ep)), int(round(0.99 * n_ep)), n_ep]
for (lo, hi), lbl in zip(zip(edges[:-1], edges[1:]), ["p0-50", "p50-90", "p90-99", "p99-100"]):
    b = sf[lo:hi]
    print(f"  {lbl:<8} n={hi-lo:>8,}  mediane fills={np.median(b):>6.0f}  moyenne={b.mean():>8.2f}")
print("  (papier Table 2 : 2/2.19, 2/3.94, 8/19.11, 72/132.27 ; n 175,770/140,616/31,638/3,516)")

top1 = sf[edges[3]:]
print(f"\ntop 1% (rang, n={top1.size:,}) : part des fills = {100*top1.sum()/n_fl_col:.2f}%  (annonce 23.1%)")
print(f"  mediane={np.median(top1):.0f} moyenne={top1.mean():.2f} max={top1.max():,}")
for frac, lbl in ((0.01, "1%"), (0.05, "5%"), (0.10, "10%")):
    k = int(round(frac * n_ep))
    print(f"top {lbl:<3} du notionnel : {100*sn[n_ep-k:].sum()/ntl.sum():.2f}%"
          f"   (annonce {'67.3' if frac==0.01 else '85.6' if frac==0.05 else '92.6'}%)")

pos = ntl > 0
pearson_logs = float(np.corrcoef(np.log(ntl[pos]), np.log(fills[pos]))[0, 1])
rk = lambda v: np.argsort(np.argsort(v)).astype(float)  # noqa: E731
spear = float(np.corrcoef(rk(ntl[pos]), rk(fills[pos]))[0, 1])
print(f"\nPearson(ln ntl, ln fills) = {pearson_logs:+.4f}   (annonce +0.545)")
print(f"Spearman(ntl, fills)      = {spear:+.4f}   (le papier dit 'rank correlation')")

i_max = int(np.argmax(ntl))
print(f"\nplus gros episode : ${ntl[i_max]:,.0f} en {fills[i_max]:,} fills"
      f"  (annonce $194,115,094 en 4,776)   coin={coin[i_max]} hip3={hip[i_max]}")

sec("C. Fichier de fills exp024 (2e passe) et compression")
fl_hip_l, fl_ntl_l = [], []
with gzip.open(FL, "rt") as fh:
    assert fh.readline().strip() == "hip3,notional"
    for line in fh:
        h, v = line.split(",")
        fl_hip_l.append(int(h)); fl_ntl_l.append(float(v))
fh3 = np.array(fl_hip_l, dtype=np.int8)
fntl = np.array(fl_ntl_l, dtype=float)
print(f"fills 2e passe = {fntl.size:,}   (annonce 2,010,314)")
print(f"plus gros fill = ${fntl.max():,.2f}  (annonce $10,990,000 exactement)")
big = fntl[fntl > 10_000_000]
print(f"fills > $10M : n={big.size}, valeurs distinctes={np.unique(big).size} : {sorted(np.unique(big))}")

print(f"\n{'q':>6}{'episode$ (1ere passe)':>24}{'fill$':>14}{'facteur':>9}   annonce (ep$, fill$, f)")
ann = {50: (1117, 558, 2.00), 90: (39288, 12046, 3.26), 99: (548922, 119919, 4.58),
       99.9: (5834505, 582486, 10.02)}
for q in (50, 90, 99, 99.9):
    a = float(np.percentile(ntl, q)); b = float(np.percentile(fntl, q))
    print(f"p{q:<5}{a:>24,.0f}{b:>14,.0f}{a/b:>9.2f}   {ann[q]}")
print(f"{'max':>6}{ntl.max():>24,.0f}{fntl.max():>14,.0f}{ntl.max()/fntl.max():>9.1f}   (annonce 17.7)")

print("\nsegments (episodes 1ere passe vs fills 2e passe) :")
for q in (50, 90, 99, 99.9):
    fm = float(np.percentile(ntl[maj], q)) / float(np.percentile(fntl[fh3 == 0], q))
    fh_ = float(np.percentile(ntl[h3], q)) / float(np.percentile(fntl[fh3 == 1], q))
    print(f"  p{q:<5} majors {fm:6.2f}x  HIP-3 {fh_:6.2f}x  rapport {fm/fh_:5.2f}"
          f"   (annonce {'2.01/1.90/1.06' if q==50 else '3.26/2.51/1.30' if q==90 else '4.48/5.49/0.82' if q==99 else '10.88/12.84/0.85'})")

sec("D. Chaines / cooldown 30 s (papier §4.2)")
okey = np.lexsort((ts, coin, user))
u_s, c_s, t_s, n_s, f_s = user[okey], coin[okey], ts[okey], ntl[okey], fills[okey]
same = (u_s[1:] == u_s[:-1]) & (c_s[1:] == c_s[:-1])
gaps = (t_s[1:] - t_s[:-1])[same]
print(f"paires consecutives même (compte, instrument) : {gaps.size:,}   (annonce 98,983)")
bins = [(0, 5_000), (5_000, 35_000), (35_000, 90_000), (90_000, 600_000)]
labels = ["< 5 s", "5-35 s", "35-90 s", "90 s-10 min"]
for (lo, hi), lbl in zip(bins, labels):
    c = int(((gaps >= lo) & (gaps < hi)).sum())
    print(f"  {lbl:<12} {c:>7,}  {100*c/gaps.size:5.2f}%")
c = int((gaps >= 600_000).sum())
print(f"  {'> 10 min':<12} {c:>7,}  {100*c/gaps.size:5.2f}%   (annonce 94.7%)")
print("  (annonce : 0 / 1,757 / 922 / 2,545 / 93,759)")

# chaines : episodes consecutifs de la même clef relies par un ecart <= 90 s
link = same & ((t_s[1:] - t_s[:-1]) <= 90_000)
starts = np.nonzero(link & ~np.concatenate([[False], link[:-1]]))[0]
n_links = int(link.sum())
n_chains = starts.size
n_in_chains = n_links + n_chains
print(f"\nchaines (>=2 episodes, ecarts <= 90 s) : {n_chains:,} chaines couvrant "
      f"{n_in_chains:,} episodes ({100*n_in_chains/n_ep:.2f}%)   (annonce 2,200 / 4,879 / 1.4%)")
merged = n_ep - n_links
print(f"apres fusion : {merged:,} unites -> facteur {n_fl_col/merged:.4f}   (annonce 5.76)")

in_chain = np.zeros(n_ep, dtype=bool)
li = np.nonzero(link)[0]
in_chain[li] = True; in_chain[li + 1] = True
chain_start_ntl = n_s[starts]
iso_ntl = n_s[~in_chain]
print(f"debut de chaine : mediane ${np.median(chain_start_ntl):,.0f}  (annonce $72,326)")
print(f"episodes isoles : mediane ${np.median(iso_ntl):,.0f}  (annonce $1,902)")
print(f"episodes > $100k : {100*(ntl>100_000).sum()/n_ep:.2f}%  (annonce 4.86%)")

sec("E. Unites alternatives a l'echelle de l'annee (le papier ne les calcule qu'a 12 h)")
hour_key = ts // 3_600_000
uc = np.char.add(np.char.add(user.astype(str), "|"), coin.astype(str))
uch = np.char.add(np.char.add(uc, "|"), hour_key.astype(str))
n_uch = np.unique(uch).size
uh = np.char.add(np.char.add(user.astype(str), "|"), hour_key.astype(str))
n_uh = np.unique(uh).size
print(f"(compte, instrument, heure) : {n_uch:,} unites -> facteur {n_fl_col/n_uch:.3f}")
print(f"(compte, heure) toutes coins: {n_uh:,} unites -> facteur {n_fl_col/n_uh:.3f}")
print("  -> l'unite trans-instruments (cross-margin) donnerait un facteur PLUS grand ;")
print("     5.72 reste du cote conservateur, a verifier ci-dessus.")

sec("F. Stratification : heure du jour et concentration par jour")
h_of_day = ((ts // 3_600_000) % 24).astype(int)
print("distribution des heures UTC presentes :", dict(zip(*np.unique(h_of_day, return_counts=True))))
print(f"\n{'h UTC':>6}{'episodes':>10}{'fills':>11}{'facteur':>9}{'part fills':>11}")
for h in sorted(np.unique(h_of_day)):
    m = h_of_day == h
    print(f"{h:>6}{m.sum():>10,}{fills[m].sum():>11,}{fills[m].sum()/m.sum():>9.3f}"
          f"{100*fills[m].sum()/n_fl_col:>10.1f}%")

day = (ts // 86_400_000).astype(int)
udays = np.unique(day)
df = np.array([fills[day == d].sum() for d in udays], dtype=float)
de = np.array([(day == d).sum() for d in udays], dtype=float)
dfac = df / de
top = np.argsort(df)[::-1][:8]
print(f"\njours: {udays.size} ; facteur journalier mediane {np.median(dfac):.2f}, "
      f"p90 {np.percentile(dfac, 90):.2f}, max {dfac.max():.2f}")
print("top jours par fills :")
for i in top:
    d = dt.datetime.fromtimestamp(udays[i] * 86400, dt.UTC).date()
    print(f"  {d}  fills={int(df[i]):>8,}  episodes={int(de[i]):>7,}  facteur={dfac[i]:.2f}"
          f"  part fills={100*df[i]/n_fl_col:.1f}%")
top5share = np.sort(df)[::-1][:5].sum() / n_fl_col
print(f"part des fills des 5 plus gros jours : {100*top5share:.1f}%")

sec("G. fig_data — verification par points")
ccdf_ep = np.loadtxt(REPO / "paper" / "fig_data" / "ccdf_episode.dat", skiprows=1)
ccdf_fl = np.loadtxt(REPO / "paper" / "fig_data" / "ccdf_fill.dat", skiprows=1)
sn_sorted = np.sort(ntl)
fn_sorted = np.sort(fntl)
err_ep = max(abs(1.0 - np.searchsorted(sn_sorted, x, "right") / n_ep - y)
             for x, y in ccdf_ep[::17])
err_fl = max(abs(1.0 - np.searchsorted(fn_sorted, x, "right") / fntl.size - y)
             for x, y in ccdf_fl[::17])
print(f"ccdf_episode.dat vs 1ere passe : ecart max echantillonne = {err_ep:.2e}")
print(f"ccdf_fill.dat    vs exp024 gz  : ecart max echantillonne = {err_fl:.2e}")
fbs = np.loadtxt(REPO / "paper" / "fig_data" / "fills_by_size.dat", skiprows=1)
lo_edge, hi_edge = fbs[:, 0].min(), fbs[:, 0].max()
print(f"fills_by_size.dat : {fbs.shape[0]} bins (colonnes x y n), x de {lo_edge:,.0f} a "
      f"{hi_edge:,.0f}, n min = {int(fbs[:, 2].min())} (legende : bins >= 30 episodes)")
# compare la mediane de fills par bin, en essayant plusieurs largeurs de bin log
lg = np.log10(ntl[pos])
fl_pos = fills[pos]
bad = 0
for x, y, _n in fbs:
    for w in (0.2, 0.25, 0.4, 0.5):
        m = (lg >= np.log10(x) - w / 2) & (lg < np.log10(x) + w / 2)
        if m.sum() >= 30 and abs(np.median(fl_pos[m]) - y) <= max(1.0, 0.25 * y):
            break
    else:
        bad += 1
        print(f"  bin centre ~{x:,.0f}: dat={y}, aucun binnage teste ne colle")
print(f"fills_by_size : {bad}/{fbs.shape[0]} bins sans correspondance approx "
      f"(binning exact inconnu, tolerance 25%)")
print("\nFIN — comparer chaque ligne aux valeurs annoncees.")
