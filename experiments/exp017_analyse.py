"""EXP-017 analysis — tail index by segment, on the year-long stratified sample.

Reads `experiments/data/exp017_episodes.csv` and reports, for each segment:

  - the Hill tail index with asymptotic CI, at several k
  - the same computed on FILLS rather than episodes, which is the comparison
    EXP-016 made on 12 hours and the reason the whole thing matters
  - the inflation factor, recomputed on an unbiased sample

Segments: all, majors (no `dex:` prefix), HIP-3 (prefixed).

The Hill estimator is the one validated in EXP-016 against Pareto samples with
known alpha (error < 6% across alpha in {1.0, 1.5, 2.0, 3.0}). It is re-validated at
import here rather than trusted, because a broken version of it silently
returned 0.00 earlier the same day.

    python experiments/exp017_analyse.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np

REPO = Path(__file__).resolve().parent.parent


def hill(x: np.ndarray, k: int) -> float:
    """Hill tail index on the top `k` order statistics. Lower = heavier tail."""
    s = np.sort(x[x > 0])
    if s.size <= k + 1:
        return float("nan")
    return float(1.0 / np.mean(np.log(s[-k:] / s[-(k + 1)])))


def _self_check() -> None:
    """Refuse to report anything if the estimator cannot recover a known index."""
    rng = np.random.default_rng(11)
    for alpha in (1.0, 1.5, 2.0, 3.0):
        x = (1 - rng.random(200_000)) ** (-1 / alpha)
        got = hill(x, 1000)
        if abs(got - alpha) / alpha > 0.12:
            raise SystemExit(f"Hill self-check failed: alpha={alpha}, got {got:.3f}")


def report(name: str, episodes: np.ndarray, fills: np.ndarray) -> None:
    print(f"\n=== {name} ===")
    print(f"  episodes {episodes.size:>9,}   fills {int(fills.sum()):>10,}"
          f"   inflation {fills.sum() / episodes.size:>5.2f}x")
    print(f"  {'series':<12}{'k':>7}{'alpha':>8}{'95% CI':>18}{'finite var?':>14}")
    # Per-fill sizes are approximated by splitting each episode across its fills;
    # EXP-016 showed that bound is loose, so only the EPISODE index is a claim.
    per_fill = np.repeat(episodes / np.maximum(fills, 1), fills.astype(int))
    for label, series in (("episodes", episodes), ("fills (approx)", per_fill)):
        for k in (500, 2000, 5000):
            if series.size <= k + 1:
                continue
            a = hill(series, k)
            se = a / np.sqrt(k)
            lo, hi = a - 1.96 * se, a + 1.96 * se
            verdict = "NO (a<2)" if hi < 2 else ("yes" if lo > 2 else "undetermined")
            print(f"  {label:<12}{k:>7,}{a:>8.2f}{f'[{lo:.2f}, {hi:.2f}]':>18}{verdict:>14}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path,
                    default=REPO / "experiments" / "data" / "exp017_episodes.csv")
    args = ap.parse_args()

    _self_check()
    print("Hill self-check passed (recovers known Pareto indices)")

    d = duckdb.sql(
        f"SELECT hip3, fills, notional FROM read_csv('{args.csv}') WHERE notional > 0"
    ).fetchnumpy()
    hip3 = d["hip3"].astype(int)
    ntl = d["notional"].astype(float)
    fl = d["fills"].astype(float)

    for name, mask in (
        ("ALL", np.ones_like(hip3, dtype=bool)),
        ("MAJORS (no dex: prefix)", hip3 == 0),
        ("HIP-3 (dex: prefix)", hip3 == 1),
    ):
        if mask.sum() > 5000:
            report(name, ntl[mask], fl[mask])

    print("\n=== share of liquidated notional ===")
    total = ntl.sum()
    for name, mask in (("majors", hip3 == 0), ("HIP-3", hip3 == 1)):
        print(f"  {name:<8} {100 * ntl[mask].sum() / total:>5.1f}% of notional,"
              f" {100 * mask.mean():>5.1f}% of episodes")


if __name__ == "__main__":
    main()
