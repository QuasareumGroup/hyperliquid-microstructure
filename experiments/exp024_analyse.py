"""EXP-024 analysis — size compression at year scale.

Control first (P1): the re-collected episodes must reproduce the published file, and the
fill rows must reconcile against them exactly. If either fails nothing else is printed.

Then the compression table, computed the way EXP-016 computed it: empirical quantiles of
the episode-notional distribution against empirical quantiles of the fill-notional
distribution, over the same fills. No model. The two distributions have different lengths
by construction — that is the effect being measured — so this compares curves, not pairs.

    python experiments/exp024_analyse.py --episodes <path> --fills <path>
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
PUBLISHED = REPO / "experiments" / "data" / "exp017_episodes.csv"

#: EXP-016's twelve-hour measurement, the figure this run is meant to replace.
TWELVE_HOUR = {50: (661.0, 424.0, 1.6), 90: (18_259.0, 8_842.0, 2.1),
               99: (214_474.0, 63_812.0, 3.4), 99.9: (1_969_302.0, 180_161.0, 10.9)}
QUANTILES = (50, 90, 99, 99.9)


def read(path: Path) -> list[dict]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def line() -> None:
    print("-" * 78)


def compression(ep_ntl: np.ndarray, fl_ntl: np.ndarray, label: str,
                compare: dict | None = None) -> None:
    print(f"\n  {label}   episodes n={ep_ntl.size:,}   fills n={fl_ntl.size:,}   "
          f"inflation {fl_ntl.size / ep_ntl.size:.2f}x")
    head = f"    {'q':>7}{'episode $':>16}{'fill $':>15}{'facteur':>10}"
    if compare:
        head += f"{'12 h':>9}{'ecart':>9}"
    print(head)
    for q in QUANTILES:
        a, b = float(np.percentile(ep_ntl, q)), float(np.percentile(fl_ntl, q))
        f = a / b if b > 0 else float("nan")
        row = f"    p{q:<6}{a:>16,.0f}{b:>15,.0f}{f:>10.1f}x"
        if compare and q in compare:
            was = compare[q][2]
            row += f"{was:>8.1f}x{f - was:>+9.1f}"
        print(row)
    a, b = float(ep_ntl.max()), float(fl_ntl.max())
    print(f"    {'max':<7}{a:>16,.0f}{b:>15,.0f}{a / b:>10.1f}x")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodes", type=Path, required=True)
    ap.add_argument("--fills", type=Path, required=True)
    args = ap.parse_args()

    eps, fills = read(args.episodes), read(args.fills)
    pub = read(PUBLISHED)

    line()
    print("P1 (controle) — la recollecte reproduit-elle le fichier publie ?")
    line()
    n_ep, n_fl = len(eps), len(fills)
    n_pub = len(pub)
    fl_pub = sum(int(r["fills"]) for r in pub)
    fl_new = sum(int(r["fills"]) for r in eps)
    d_ep = abs(n_ep - n_pub) / n_pub
    d_fl = abs(fl_new - fl_pub) / fl_pub
    print(f"  episodes : {n_ep:>10,}  publie {n_pub:>10,}  ecart {100 * d_ep:.3f}%")
    print(f"  fills    : {fl_new:>10,}  publie {fl_pub:>10,}  ecart {100 * d_fl:.3f}%")
    print(f"  lignes du fichier de fills : {n_fl:,}  "
          f"({'coherent' if n_fl == fl_new else 'INCOHERENT'} avec la colonne `fills`)")

    # every episode's notional must equal the sum of its fills
    agg: dict[tuple[str, str, str], float] = {}
    for f in fills:
        k = (f["coin"], f["user"], f["ep_ts"])
        agg[k] = agg.get(k, 0.0) + float(f["notional"])
    bad = miss = 0
    for e in eps:
        k = (e["coin"], e["user"], e["ts"])
        if k not in agg:
            miss += 1
        elif abs(agg[k] - float(e["notional"])) > 0.05:
            bad += 1
    print(f"  reconciliation notional : {bad} ecarts, {miss} episodes sans fills")

    ok = d_ep <= 0.001 and d_fl <= 0.001 and n_fl == fl_new and bad == 0 and miss == 0
    print(f"\n  P1 {'CONFIRMED' if ok else 'REJECTED'}")
    if not ok:
        raise SystemExit("controle echoue — rien d'autre n'est lu")

    ep_all = np.array([float(r["notional"]) for r in eps])
    fl_all = np.array([float(r["notional"]) for r in fills])
    ep_h = np.array([int(r["hip3"]) for r in eps])
    fl_h = np.array([int(r["hip3"]) for r in fills])

    line()
    print("P2 / P3 — compression a l'echelle de l'annee")
    line()
    compression(ep_all, fl_all, "tous instruments", TWELVE_HOUR)
    compression(ep_all[ep_h == 0], fl_all[fl_h == 0], "majors")
    compression(ep_all[ep_h == 1], fl_all[fl_h == 1], "HIP-3")

    facs = [float(np.percentile(ep_all, q)) / float(np.percentile(fl_all, q)) for q in QUANTILES]
    mono = all(a < b for a, b in zip(facs[:-1], facs[1:]))
    print(f"\n  P2 {'CONFIRMED' if mono else 'REJECTED'} — compression croissante avec le quantile")
    p99, p999 = facs[2], facs[3]
    bigger = p99 > TWELVE_HOUR[99][2] and p999 > TWELVE_HOUR[99.9][2]
    smaller = p99 < TWELVE_HOUR[99][2] and p999 < TWELVE_HOUR[99.9][2]
    verdict = "CONFIRMED" if bigger else ("REJECTED (plus faible)" if smaller else "REJECTED (mixte)")
    print(f"  P3 {verdict} — p99 {p99:.1f}x vs 3.4x, p99.9 {p999:.1f}x vs 10.9x")

    line()
    print("P4 — majors et HIP-3 compressent-ils pareil ?")
    line()
    for q in QUANTILES:
        fm = float(np.percentile(ep_all[ep_h == 0], q)) / float(np.percentile(fl_all[fl_h == 0], q))
        fh = float(np.percentile(ep_all[ep_h == 1], q)) / float(np.percentile(fl_all[fl_h == 1], q))
        print(f"    p{q:<6} majors {fm:>7.1f}x   HIP-3 {fh:>7.1f}x   rapport {fm / fh:>5.2f}")


if __name__ == "__main__":
    main()
