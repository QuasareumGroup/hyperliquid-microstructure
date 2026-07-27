"""EXP-025 analysis — P1 first: are liquidation tranches identifiable at all?

EXP-025 §2 fixes the instrument: tranche boundaries are an arithmetic fact of position
accounting, not of elapsed time. Within a maximal run of liquidation fills for one
(account, instrument), grouped at a deliberately loose 10-minute gap so that no boundary
is imposed by time, cumulative closed size is measured as a fraction of the position the
run started from. If the documented 20% rule operates, pauses should fall at multiples
of 0.2.

P1 is a gate. If closed-size fractions at pauses are uniform, the rule is not identifiable
in the venue's own complete fill record, and the price question below it is unaskable.

    python experiments/exp025_analyse.py --fills <path>
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

#: Deliberately loose: a boundary must come from position arithmetic, not from a
#: time rule. EXP-024's 5-second episode unit is what contaminated the first design.
RUN_GAP_MS = 600_000
#: Tolerance around a multiple of 0.2, as a fraction of the starting position.
TOL = 0.02
MULTIPLES = (0.2, 0.4, 0.6, 0.8)


def load_runs(path: Path) -> list[list[dict]]:
    """Maximal (account, instrument) runs of liquidation fills, 10-minute gap."""
    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with path.open() as fh:
        for r in csv.DictReader(fh):
            by[(r["user"], r["coin"])].append({
                "ts": int(r["ts"]), "sz": float(r["sz"]),
                "sp": abs(float(r["start_position"])), "px": float(r["px"]),
                "dir": r["dir"],
            })
    runs = []
    for v in by.values():
        v.sort(key=lambda f: f["ts"])
        cur = [v[0]]
        for a, b in zip(v[:-1], v[1:]):
            if b["ts"] - a["ts"] > RUN_GAP_MS:
                runs.append(cur); cur = [b]
            else:
                cur.append(b)
        runs.append(cur)
    return runs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fills", type=Path, required=True)
    ap.add_argument("--pause-ms", type=int, default=1000,
                    help="a gap of at least this long counts as a pause")
    args = ap.parse_args()

    runs = load_runs(args.fills)
    print(f"runs (account, instrument, 10-min gap) : {len(runs):,}")
    multi = [r for r in runs if len(r) > 1]
    print(f"  runs de plus d'un fill               : {len(multi):,}")

    # --- consistency: cumulative size closed must track startPosition ---
    bad = checked = 0
    for r in multi[:20_000]:
        p0 = r[0]["sp"]
        if p0 <= 0:
            continue
        cum = np.cumsum([f["sz"] for f in r])
        implied = p0 - np.array([f["sp"] for f in r])
        checked += 1
        if np.max(np.abs(cum[:-1] - implied[1:])) > 1e-6 * max(p0, 1.0):
            bad += 1
    print(f"  controle cumsum(sz) == P0 - startPosition : {checked - bad}/{checked} coherents")

    # --- P1: where do pauses fall in the position closure? ---
    fracs, gaps = [], []
    for r in multi:
        p0 = r[0]["sp"]
        if p0 <= 0:
            continue
        cum = 0.0
        for a, b in zip(r[:-1], r[1:]):
            cum += a["sz"]
            if b["ts"] - a["ts"] >= args.pause_ms:
                fracs.append(cum / p0)
                gaps.append((b["ts"] - a["ts"]) / 1000.0)
    fracs = np.array(fracs); gaps = np.array(gaps)
    inside = (fracs > 0.01) & (fracs < 0.99)
    f = fracs[inside]
    print(f"\nP1 — pauses (>= {args.pause_ms} ms) a l'interieur d'une fermeture : {f.size:,}")

    hit = np.zeros(f.size, dtype=bool)
    for m in MULTIPLES:
        hit |= np.abs(f - m) <= TOL
    share = 100 * hit.mean() if f.size else 0.0
    #: uniform null: 4 windows of width 2*TOL over the (0.01, 0.99) support
    null = 100 * (len(MULTIPLES) * 2 * TOL) / 0.98
    print(f"  part a +/-{TOL} d'un multiple de 0.2 : **{share:.1f}%**   "
          f"(null uniforme {null:.1f}%)")
    print(f"  P1 {'CONFIRMED' if share > 40 else 'REJECTED'} — seuil pre-enregistre : > 40%")

    print("\n  histogramme des fractions de position fermee a la pause")
    for lo in np.arange(0.0, 1.0, 0.05):
        n = ((f >= lo) & (f < lo + 0.05)).sum()
        star = " <-- x0.2" if any(abs((lo + 0.025) - m) < 0.03 for m in MULTIPLES) else ""
        print(f"   {lo:.2f}-{lo+0.05:.2f} {n:>6}  " + "#" * int(60 * n / max(1, f.size * 0.12)) + star)

    if f.size:
        print(f"\n  ecart a la pause : mediane {np.median(gaps[inside]):.1f}s   "
              f"part dans [25,40]s {100*((gaps[inside] >= 25) & (gaps[inside] <= 40)).mean():.0f}%")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Tranche-level analysis (P2, P3, P4). Runs only if P1 passed: tranche
# boundaries are located by position accounting, never by elapsed time.
# ---------------------------------------------------------------------------

def tranches(run: list[dict]) -> list[list[dict]]:
    """Split a run at fills after which cumulative closed size crosses k*0.2*P0."""
    p0 = run[0]["sp"]
    if p0 <= 0:
        return [run]
    out, cur, cum, nxt = [], [], 0.0, 0.2
    for f in run:
        cur.append(f); cum += f["sz"]
        frac = cum / p0
        while nxt < 1.0 and frac >= nxt - TOL:
            nxt += 0.2
            if frac <= 0.98:
                out.append(cur); cur = []
            break
    if cur:
        out.append(cur)
    return [t for t in out if t]


def vwap(t: list[dict]) -> float:
    s = sum(f["sz"] for f in t)
    return sum(f["px"] * f["sz"] for f in t) / s if s else float("nan")
