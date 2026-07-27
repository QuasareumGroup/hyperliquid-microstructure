"""Revue FABLE — suites de la partie 1 : 4,776 fills, episodes isoles, heure 19, 12 h.

    .venv/bin/python review/r1b_followups.py
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
EP = REPO / "experiments" / "data" / "exp017_episodes.csv"

rows = list(csv.DictReader(EP.open()))
ts = np.array([int(r["ts"]) for r in rows], dtype=np.int64)
coin = np.array([r["coin"] for r in rows])
user = np.array([r["user"] for r in rows])
fills = np.array([int(r["fills"]) for r in rows], dtype=np.int64)
ntl = np.array([float(r["notional"]) for r in rows])
n_ep = ts.size


def when(t: int) -> str:
    return dt.datetime.fromtimestamp(t / 1000, dt.UTC).strftime("%Y-%m-%d %H:%M:%S")


print("=== 1. le plus gros episode par notionnel vs par fills ===")
i = int(np.argmax(ntl))
print(f"max notionnel : ${ntl[i]:,.0f}  fills={fills[i]:,}  coin={coin[i]}  ts={when(ts[i])}")
j = int(np.argmax(fills))
print(f"max fills     : {fills[j]:,} fills  ${ntl[j]:,.0f}  coin={coin[j]}  ts={when(ts[j])}")
big = np.argsort(ntl)[::-1][:5]
print("top 5 par notionnel :")
for k in big:
    print(f"  ${ntl[k]:>15,.0f}  {fills[k]:>6,} fills  {coin[k]:<10} {when(ts[k])}")
bigf = np.argsort(fills)[::-1][:5]
print("top 5 par fills :")
for k in bigf:
    print(f"  {fills[k]:>6,} fills  ${ntl[k]:>15,.0f}  {coin[k]:<10} {when(ts[k])}")

print("\n=== 2. definitions possibles de 'episodes isoles' (annonce $1,902) ===")
okey = np.lexsort((ts, coin, user))
u_s, c_s, t_s, n_s = user[okey], coin[okey], ts[okey], ntl[okey]
same = (u_s[1:] == u_s[:-1]) & (c_s[1:] == c_s[:-1])
link = same & ((t_s[1:] - t_s[:-1]) <= 90_000)
in_chain = np.zeros(n_ep, dtype=bool)
li = np.nonzero(link)[0]
in_chain[li] = True
in_chain[li + 1] = True
starts = np.nonzero(link & ~np.concatenate([[False], link[:-1]]))[0]

print(f"(a) tous les episodes hors chaine                  : mediane ${np.median(n_s[~in_chain]):,.0f}  n={int((~in_chain).sum()):,}")
has_prev = np.concatenate([[False], same])
has_next = np.concatenate([same, [False]])
in_pairs = has_prev | has_next
m = (~in_chain) & in_pairs
print(f"(b) hors chaine, avec au moins un voisin même clef : mediane ${np.median(n_s[m]):,.0f}  n={int(m.sum()):,}")
first_of_key = ~has_prev
m2 = first_of_key & ~in_chain
print(f"(c) premiers de leur clef, hors chaine             : mediane ${np.median(n_s[m2]):,.0f}  n={int(m2.sum()):,}")
seul = first_of_key & ~has_next
print(f"(d) clefs a episode unique (jamais re-liquide)     : mediane ${np.median(n_s[seul]):,.0f}  n={int(seul.sum()):,}")
gaps = t_s[1:] - t_s[:-1]
pair_far = same & (gaps > 90_000)
iso_pair_first = np.zeros(n_ep, dtype=bool)
pf = np.nonzero(pair_far)[0]
iso_pair_first[pf] = True
m3 = iso_pair_first & ~in_chain
print(f"(e) premier d'une paire espacee > 90 s, hors chaine: mediane ${np.median(n_s[m3]):,.0f}  n={int(m3.sum()):,}")

print("\n=== 3. les 3 episodes a l'heure 19 UTC ===")
h = ((ts // 3_600_000) % 24).astype(int)
for k in np.nonzero(h == 19)[0]:
    print(f"  {when(ts[k])}  {coin[k]:<12} fills={fills[k]}  ${ntl[k]:,.2f}")

print("\n=== 4. jour au facteur 28.96 ===")
day = (ts // 86_400_000).astype(int)
udays = np.unique(day)
for d in udays:
    m = day == d
    f = fills[m].sum() / m.sum()
    if f > 20:
        print(f"  {dt.datetime.fromtimestamp(int(d)*86400, dt.UTC).date()}  episodes={m.sum():,} "
              f"fills={fills[m].sum():,} facteur={f:.2f}")

print("\n=== 5. echantillon 12 h (exp016) : correlation, compression, top 1% ===")
u16 = list(csv.DictReader((REPO / "experiments" / "data" / "exp016_units.csv").open()))
f16 = list(csv.DictReader((REPO / "experiments" / "data" / "exp016_fills.csv").open()))
n16 = np.array([float(r["notional"]) for r in u16])
fl16 = np.array([int(r["fills"]) for r in u16])
txs16 = np.array([int(r["txs"]) for r in u16])
fn16 = np.array([float(r["notional"]) for r in f16])
pos = n16 > 0
print(f"episodes 12 h = {n16.size:,} (annonce 6,546)   fills 12 h = {fn16.size:,} (annonce 24,566)")
print(f"facteur 12 h  = {fn16.size / n16.size:.4f} (annonce 3.8 avec unite (user,tx) 6,412)")
print(f"somme txs par episode = {txs16.sum():,} ; unites (user,tx) annoncees 6,412 "
      f"(non recomputable : pas de hash dans les fichiers publies)")
print(f"Pearson(ln ntl, ln fills) 12 h = "
      f"{np.corrcoef(np.log(n16[pos]), np.log(fl16[pos]))[0,1]:+.4f} (annonce +0.509)")
for q, a in ((50, 1.6), (90, 2.1), (99, 3.4), (99.9, 10.9)):
    r = np.percentile(n16, q) / np.percentile(fn16, q)
    print(f"  compression 12 h p{q}: {r:.2f} (annonce {a})")
sf = np.sort(fn16)[::-1]
k1 = max(1, int(round(0.01 * fn16.size)))
print(f"top 1% des FILLS, part du notionnel 12 h = {100*sf[:k1].sum()/fn16.sum():.1f}% (annonce 30.7%)")
k5, k10 = int(round(0.05 * fn16.size)), int(round(0.10 * fn16.size))
print(f"top 5% = {100*sf[:k5].sum()/fn16.sum():.1f}% (annonce 61.8%)   "
      f"top 10% = {100*sf[:k10].sum()/fn16.sum():.1f}% (annonce 76.6%)")

print("\n=== 6. fills_by_size.dat (3 colonnes ?) ===")
raw = (REPO / "paper" / "fig_data" / "fills_by_size.dat").read_text().splitlines()
print(raw[0])
for line in raw[1:4]:
    print(line)
dat = np.array([[float(v) for v in line.split()] for line in raw[1:]])
print(f"{dat.shape[0]} bins ; colonnes = {dat.shape[1]}")
lg = np.log10(ntl[ntl > 0])
fl_pos = fills[ntl > 0]
bad = 0
for row in dat:
    x, y = row[0], row[1]
    n_in = row[2] if dat.shape[1] > 2 else None
    # bins log : essaie une largeur de 0.4 decade centree
    for w in (0.2, 0.25, 0.4, 0.5):
        m = (lg >= np.log10(x) - w / 2) & (lg < np.log10(x) + w / 2)
        if m.sum() >= 30 and abs(np.median(fl_pos[m]) - y) <= max(1.0, 0.25 * y):
            break
    else:
        bad += 1
print(f"bins sans correspondance approx (largeur inconnue, tolerance 25%) : {bad}/{dat.shape[0]}")
