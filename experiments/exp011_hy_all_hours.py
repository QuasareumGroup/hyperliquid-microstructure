"""EXP-011 — Hayashi-Yoshida lead-lag across every usable hour.

EXP-010 validated the estimator and applied it to six hours, giving a median of
~550 ms. Six hours is a median, not a confidence band. This runs the same
estimator over every hour usable on all three venues.

Reuses EXP-009's fetch/decode/delete machinery — tape is fetched, measured and
discarded per hour, so peak disk stays at three files. Only the measurement
changes: Hayashi-Yoshida in physical time rather than a binned cross-correlation.

    python experiments/exp011_hy_all_hours.py

Writes `experiments/data/exp011_hy_hours.csv`.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exp009_volatility_buckets import (
    DUMP,
    REPO,
    VENUES,
    _decode,
    _fetch,
    gapped,
    hourly_range,
)

from hlm.analysis.leadlag import hayashi_yoshida

PAIRS = (("hl", "binance"), ("okx", "binance"))
#: ±2 s at 25 ms resolution. Wide enough to bracket the ~550 ms seen in EXP-010
#: with room either side, fine enough that the peak is not quantised into it.
TAUS = np.arange(-2000, 2001, 25.0)


def _series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with duckdb.connect() as con:
        d = con.sql(f"SELECT ts_ms, px FROM read_csv('{path}') ORDER BY ts_ms").fetchnumpy()
    return d["ts_ms"].astype(float), d["px"].astype(float)


def process_hour(coin: str, date: str, hour: int, rng_bps: float) -> dict | None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        series: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for venue in VENUES:
            pfr, out = tmpd / f"{venue}.pfr", tmpd / f"{venue}.csv"
            if not _fetch(venue, coin, date, hour, pfr) or not _decode(venue, coin, pfr, out):
                return None
            series[venue] = _series(out)

        row = {"date": date, "hour": hour, "range_bps": round(rng_bps, 1)}
        for a, b in PAIRS:
            try:
                r = hayashi_yoshida(*series[a], *series[b], TAUS)
            except ValueError:
                return None
            key = f"{a}_{b}"
            row[f"peak_ms_{key}"] = r.peak_ms
            row[f"peak_corr_{key}"] = round(r.peak_corr, 4)
            row[f"index_{key}"] = round(r.asymmetry(), 4)
            row[f"n_{key}"] = r.n_x
        return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coin", default="BTC")
    ap.add_argument("--start", default="2026-07-18")
    ap.add_argument("--end", default="2026-07-26")
    ap.add_argument("--workers", type=int, default=6)
    default_out = REPO / "experiments" / "data" / "exp011_hy_hours.csv"
    ap.add_argument("--out", type=Path, default=default_out)
    args = ap.parse_args()

    if not DUMP.exists():
        raise SystemExit(f"build the decoder first: cd {DUMP.parents[2]} && cargo build --release")

    ranges = hourly_range(args.start, args.end, args.coin)
    dates = sorted({d for d, _ in ranges})
    holes: dict[str, set[int]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gapped, v, args.coin, d): d for v in VENUES for d in dates}
        for f in as_completed(futs):
            holes.setdefault(futs[f], set()).update(f.result())

    usable = [(d, h, r) for (d, h), r in sorted(ranges.items()) if h not in holes.get(d, set())]
    print(f"{len(usable)}/{len(ranges)} hours usable on all of {', '.join(VENUES)}")

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(process_hour, args.coin, d, h, r) for d, h, r in usable]
        for i, f in enumerate(as_completed(futs), 1):
            row = f.result()
            if row:
                rows.append(row)
            if i % 20 == 0:
                print(f"  {i}/{len(usable)} processed, {len(rows)} kept")

    rows.sort(key=lambda r: (r["date"], r["hour"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} hours -> {args.out}")


if __name__ == "__main__":
    main()
