"""EXP-023 analysis — cross-asset table on corrected coverage, and the within-asset test.

Part A re-derives EXP-012's table from hours classified by the tape rather than by
perplog's coverage flag. Part B runs EXP-012's Next item 1: whether the observability
relation it saw across four assets reproduces hour by hour *inside* an asset.

Reads `experiments/data/exp021_hours.csv` (BTC) and `exp023_{ETH,SOL,HYPE}.csv`.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "experiments" / "data"
POWER_FLOOR = 200

SOURCES = {
    "BTC": DATA / "exp021_hours.csv",
    "ETH": DATA / "exp023_ETH.csv",
    "SOL": DATA / "exp023_SOL.csv",
    "HYPE": DATA / "exp023_HYPE.csv",
}

#: EXP-012's published table, for the before/after comparison.
EXP012 = {
    "BTC": (144, 575, 601, 145, 100.0, 0.582, 25, 4870),
    "ETH": (144, 550, 588, 135, 100.0, 0.804, 25, 2258),
    "SOL": (144, 638, 736, 244, 100.0, 0.332, 0, 1209),
    "HYPE": (144, 550, 561, 127, 100.0, 0.884, 25, 2730),
}


def load(path: Path) -> list[dict]:
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        if r["usable"] != "1" or int(r["n_hl"]) < POWER_FLOOR:
            continue
        out.append({
            "range_bps": float(r["range_bps"]),
            #: raw tape events. NOT what EXP-012's "HL trades/h" column counted.
            "n_hl": int(r["n_hl"]),
            #: HY returns — same-timestamp prints collapsed, one lost to differencing.
            #: Verified byte-identical to EXP-011's `n_hl_binance`, so this is the
            #: column EXP-012 reported and the only one comparable to it. Raw events
            #: run 2.11x higher, because Hyperliquid stamps a whole block at one ms.
            "nret": int(r["nret_hl_binance"]),
            "flagged": r["flagged"] == "1",
            "peak": float(r["peak_ms_hl_binance"]),
            "corr": float(r["peak_corr_hl_binance"]),
            "okx": float(r["peak_ms_okx_binance"]),
        })
    return out


def partial(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> tuple[float, float]:
    """Spearman(a, b | c): correlation between rank residuals after removing c.

    Trade count and hourly range are 0.71-0.85 correlated here, so a raw
    correlation with either cannot say which one carries the relation — method
    rule 4, a caveat listed is not a confound controlled.
    """
    ra, rb, rc = (stats.rankdata(v) for v in (a, b, c))
    ra = ra - np.polyval(np.polyfit(rc, ra, 1), rc)
    rb = rb - np.polyval(np.polyfit(rc, rb, 1), rc)
    r = float(np.corrcoef(ra, rb)[0, 1])
    n = len(a)
    t = r * np.sqrt((n - 3) / max(1e-12, 1 - r * r))
    return r, float(2 * stats.t.sf(abs(t), n - 3))


def boot_median(v: np.ndarray, n: int = 20_000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    m = np.median(rng.choice(v, size=(n, v.size), replace=True), axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def line() -> None:
    print("-" * 88)


data = {a: load(p) for a, p in SOURCES.items()}

print("EXP-023 — cross-asset on tape-derived coverage, window 2026-07-18 -> 07-26\n")

# --------------------------------------------------------------------- Part A
line()
print("PART A — the cross-asset table, corrected")
line()
print(f"  {'asset':<6}{'hours':>7}{'was':>6}{'median':>9}{'mean':>7}{'95% CI':>16}"
      f"{'sigma':>7}{'tau>0':>8}{'rho':>7}{'OKX':>6}{'HY ret/h':>10}")

summary = {}
for a, rows in data.items():
    pk = np.array([r["peak"] for r in rows])
    lo, hi = boot_median(pk)
    pos = 100.0 * (pk > 0).sum() / pk.size
    rho = float(np.mean([r["corr"] for r in rows]))
    okx = float(np.median([r["okx"] for r in rows]))
    tr = float(np.mean([r["nret"] for r in rows]))
    summary[a] = {"n": pk.size, "median": float(np.median(pk)), "mean": float(pk.mean()),
                  "sigma": float(pk.std(ddof=1)), "pos": pos, "rho": rho, "okx": okx,
                  "trades": tr}
    print(f"  {a:<6}{pk.size:>7}{EXP012[a][0]:>6}{np.median(pk):>9.0f}{pk.mean():>7.0f}"
          f"{f'[{lo:.0f}, {hi:.0f}]':>16}{pk.std(ddof=1):>7.0f}{pos:>7.1f}%"
          f"{rho:>7.3f}{okx:>6.0f}{tr:>10,.0f}")

print(f"\n  {'':<6}{'EXP-012 pour memoire':<28}")
for a, (n, med, mean, sig, pos, rho, okx, tr) in EXP012.items():
    d = summary[a]["median"] - med
    print(f"  {a:<6}{'median ' + str(med) + ' ms':<22}-> {summary[a]['median']:>4.0f} ms "
          f"({d:+.0f})   sigma {sig} -> {summary[a]['sigma']:.0f}   rho {rho:.3f} -> "
          f"{summary[a]['rho']:.3f}")

tot = sum(s["n"] for s in summary.values())
rev = sum(1 for a in data for r in data[a] if r["peak"] <= 0)
print(f"\n  total asset-hours : {tot}   (EXP-012 : 576)")
print(f"  reversals (tau <= 0) : {rev}")
print(f"\n  P1 {'CONFIRMED' if all(180 <= s['n'] <= 193 for s in summary.values()) else 'REJECTED'}"
      f"  — chaque actif entre 180 et 193 heures")
band = all(500 <= summary[a]["median"] <= 650 for a in ("BTC", "ETH", "HYPE"))
sol_top = summary["SOL"]["median"] == max(s["median"] for s in summary.values())
print(f"  P2 {'CONFIRMED' if band and sol_top else 'REJECTED'}"
      f"  — BTC/ETH/HYPE dans 500-650 ms, SOL le plus haut")
print(f"  P3 {'CONFIRMED' if rev == 0 else 'REJECTED'}  — tau > 0 partout")

# --------------------------------------------------------------------- Part B
line()
print("PART B — does observability reproduce WITHIN an asset?")
line()
print("  EXP-012, entre 4 actifs : corr( ln(HL trades/h), median peak ) = -0.630\n")

x4 = np.log([summary[a]["trades"] for a in SOURCES])
y4 = np.array([summary[a]["median"] for a in SOURCES])
r4 = float(np.corrcoef(x4, y4)[0, 1])
print(f"  recalcule sur donnees corrigees (n=4)  : {r4:+.3f}")

print(f"\n  {'asset':<6}{'n':>6}{'rho(ln trades, peak)':>24}{'p':>9}"
      f"{'rho(range, peak)':>19}{'p':>9}")
p4_ok = True
for a, rows in data.items():
    # `nret`, not `n_hl`: the observability hypothesis is about how often HL's
    # PRICE refreshes, and a block stamps many fills at one millisecond. Raw
    # events overstate the refresh rate by 2.11x and are the wrong regressor.
    n = np.array([r["nret"] for r in rows], dtype=float)
    pk = np.array([r["peak"] for r in rows])
    rg = np.array([r["range_bps"] for r in rows])
    s1 = stats.spearmanr(np.log(n), pk)
    s2 = stats.spearmanr(rg, pk)
    sig = s1.pvalue < 0.05 and s1.statistic < 0
    p4_ok &= sig
    print(f"  {a:<6}{len(rows):>6}{s1.statistic:>24.3f}{s1.pvalue:>9.3f}"
          f"{s2.statistic:>19.3f}{s2.pvalue:>9.3f}  {'<- neg. signif.' if sig else ''}")

print(f"\n  P4 {'CONFIRMED' if p4_ok else 'REJECTED'}"
      f"  — relation negative et significative dans CHAQUE actif")

# pooled, standardising the lag within each asset so between-asset levels cannot
# manufacture the within-asset relation the test is about
zx, zy = [], []
for a, rows in data.items():
    n = np.log(np.array([r["nret"] for r in rows], dtype=float))
    pk = np.array([r["peak"] for r in rows])
    zx.append((n - n.mean()) / n.std())
    zy.append((pk - pk.mean()) / pk.std())
sp = stats.spearmanr(np.concatenate(zx), np.concatenate(zy))
print(f"\n  groupe, centre-reduit par actif (n={sum(len(v) for v in data.values())}) : "
      f"rho = {sp.statistic:+.3f}  p = {sp.pvalue:.3f}")

line()
print("PART B (suite) — trade count ou volatilite ? correlations partielles")
line()
print(f"  {'asset':<6}{'n':>5}{'trades | range':>17}{'p':>8}"
      f"{'range | trades':>17}{'p':>8}{'corr(tr,rg)':>13}   lecture")
for a, rows in data.items():
    tr = np.log(np.array([r["nret"] for r in rows], dtype=float))
    rg = np.array([r["range_bps"] for r in rows])
    pk = np.array([r["peak"] for r in rows])
    r1, p1 = partial(tr, pk, rg)
    r2, p2 = partial(rg, pk, tr)
    c = stats.spearmanr(tr, rg).statistic
    if p1 < 0.05 and p2 >= 0.05:
        read = "observabilite"
    elif p1 < 0.05 and p2 < 0.05:
        read = "les deux — indistinguable"
    elif p1 >= 0.05 and p2 < 0.05:
        read = "volatilite"
    else:
        read = "aucune"
    print(f"  {a:<6}{len(rows):>5}{r1:>17.3f}{p1:>8.3f}{r2:>17.3f}{p2:>8.3f}"
          f"{c:>13.3f}   {read}")
print("\n  Le confondant est reel : trades et range sont correles a 0.71-0.85.")
print("  La partielle est ce qui les separe (regle 4).")
