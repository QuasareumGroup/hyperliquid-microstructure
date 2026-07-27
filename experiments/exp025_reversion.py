"""EXP-025 §8 — does the price revert after a forced close finishes?

The discriminating test, pre-registered before the ambient data existed.

Selection acts on *why* a second tranche exists: the account stayed below maintenance
margin, which happens when the price moved against it. It says nothing about what the
price does once the forced flow has stopped. So the window after the close is
uncontaminated, and the two readings separate there:

  anticipation  price was pushed ahead of known incoming flow -> temporary -> reverts
  selection     price moved for exogenous reasons -> information -> does not revert

P5: gapped closes revert MORE than continuous ones, as a share of their own adverse
move. P6: both revert somewhat, since any marketable sweep has temporary impact.

    python experiments/exp025_reversion.py --ambient <path> --closes <path>
"""

from __future__ import annotations

import argparse
import bisect
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

HORIZONS = (30, 60, 300)
#: A close is "gapped" if its largest inter-tranche gap reaches this; "continuous"
#: if it stays under CONT_S. The band between them is reported but not compared.
GAP_S = 25.0
CONT_S = 2.0
#: Refuse a price more than this far from the instant asked for.
MAX_STALE_S = 60


def load_ambient(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    by: dict[str, list[tuple[int, float]]] = defaultdict(list)
    with path.open() as fh:
        for r in csv.reader(fh):
            if r[0] == "coin":
                continue
            by[r[0]].append((int(r[1]), float(r[2])))
    out = {}
    for c, v in by.items():
        v.sort()
        out[c] = (np.array([a for a, _ in v]), np.array([b for _, b in v]))
    return out


def px_at(series: tuple[np.ndarray, np.ndarray], sec: int) -> float:
    """Last trade at or before `sec`, refusing anything staler than MAX_STALE_S."""
    ts, px = series
    i = bisect.bisect_right(ts, sec) - 1
    if i < 0 or sec - ts[i] > MAX_STALE_S:
        return float("nan")
    return float(px[i])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ambient", type=Path, required=True)
    ap.add_argument("--closes", type=Path, required=True)
    args = ap.parse_args()

    amb = load_ambient(args.ambient)
    print(f"instruments avec serie ambiante : {len(amb)}")

    rows = []
    with args.closes.open() as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            c = r["coin"]
            if c not in amb:
                continue
            t0, t1 = int(r["t0"]) // 1000, int(r["t1"]) // 1000
            sign = 1.0 if "Long" in r["dir"] else -1.0
            p0, p1 = px_at(amb[c], t0), px_at(amb[c], t1)
            if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0:
                continue
            # adverse during the close, in bps, positive = against the account
            A = sign * (p0 - p1) / p0 * 1e4
            rec = {"gap": float(r["maxgap"]), "A": A, "ntl": float(r["ntl"]),
                   "ntr": int(r["ntr"]), "coin": c}
            for k in HORIZONS:
                pk = px_at(amb[c], t1 + k)
                # positive = price came back toward its pre-close level
                rec[f"R{k}"] = (sign * (pk - p1) / p0 * 1e4) if np.isfinite(pk) else np.nan
            rows.append(rec)

    print(f"fermetures avec prix utilisables : {len(rows):,}")
    A = np.array([r["A"] for r in rows])
    gap = np.array([r["gap"] for r in rows])
    cont, gapped = gap < CONT_S, gap >= GAP_S
    print(f"  continues (< {CONT_S:g}s) {cont.sum():,}   espacees (>= {GAP_S:g}s) {gapped.sum():,}")

    print(f"\n  mouvement defavorable pendant la fermeture (bps, prix ambiants)")
    for lab, m in (("continues", cont), ("espacees", gapped)):
        print(f"    {lab:<12} moyenne {A[m].mean():+8.2f}   mediane {np.median(A[m]):+8.2f}")

    print(f"\n  P6 — retour apres la fin de la fermeture (bps, positif = revient)")
    print(f"    {'horizon':<10}{'continues':>22}{'espacees':>22}")
    for k in HORIZONS:
        R = np.array([r[f"R{k}"] for r in rows])
        ok = np.isfinite(R)
        c_, g_ = R[cont & ok], R[gapped & ok]
        print(f"    +{k:<9}s{c_.mean():>12.2f} (n={c_.size:,})"
              f"{g_.mean():>12.2f} (n={g_.size:,})")

    print(f"\n  P5 — part du mouvement qui etait temporaire, R(300)/A")
    R3 = np.array([r["R300"] for r in rows])
    ok = np.isfinite(R3) & (np.abs(A) > 1.0)          # avoid dividing by noise
    share = R3[ok] / A[ok]
    cm, gm = cont[ok], gapped[ok]
    for lab, m in (("continues", cm), ("espacees", gm)):
        v = share[m]
        print(f"    {lab:<12} n={v.size:>6,}  moyenne {v.mean():+.3f}  mediane {np.median(v):+.3f}")
    if cm.sum() > 30 and gm.sum() > 30:
        u = stats.mannwhitneyu(share[gm], share[cm], alternative="greater")
        t = stats.ttest_ind(share[gm], share[cm], equal_var=False)
        print(f"    espacees > continues : Mann-Whitney p={u.pvalue:.3g}   "
              f"Welch t={t.statistic:+.2f} p={t.pvalue:.3g}")
        verdict = "CONFIRMED" if u.pvalue < 0.05 else "REJECTED"
        print(f"\n    P5 {verdict} — les espacees reviennent-elles davantage ?")
        if verdict == "REJECTED":
            print("    -> le supplement de mouvement des fermetures espacees est aussi")
            print("       permanent que le reste : lecture par SELECTION, rien a revendiquer.")


if __name__ == "__main__":
    main()
