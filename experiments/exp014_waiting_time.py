"""EXP-014 — empirical observability delay, measured rather than assumed.

EXP-013 compared the measured lead against "half the mean inter-trade interval"
and found it 10x too weak to be observability. That benchmark assumed uniform
arrivals, and its caveat got the direction of the burstiness correction wrong:
under the inspection paradox, information landing at an arbitrary instant is
*more* likely to fall inside a long gap, so the true waiting time is
E[I^2]/(2E[I]) >= E[I]/2 — longer, not shorter.

Rather than patch the formula, this measures the thing directly. For every
Binance print — a proxy for when information arrives — it computes the time
until the next Hyperliquid print. That is exactly the delay observability would
impose, under the real arrival processes of both venues rather than a model of
them. Weighted by |Binance return|, because that is what Hayashi-Yoshida weights.

Reports, per hour:
  w_mean      unweighted mean waiting time
  w_weighted  |return|-weighted mean — the HY-relevant one
  w_renewal   E[I^2]/(2E[I]), the renewal/inspection-paradox estimate
  w_half      E[I]/2, EXP-013's benchmark, kept for comparison

    python experiments/exp014_waiting_time.py --coin BTC --hours 30

Writes `experiments/data/exp014_waiting_{coin}.csv`.
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

from exp009_volatility_buckets import DUMP, REPO, _decode, _fetch, gapped, hourly_range

from hlm.analysis.leadlag import hayashi_yoshida

VENUES = ("hl", "binance")
TAUS = np.arange(-2000, 2001, 25.0)


def _series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with duckdb.connect() as con:
        d = con.sql(f"SELECT ts_ms, px FROM read_csv('{path}') ORDER BY ts_ms").fetchnumpy()
    return d["ts_ms"].astype(float), d["px"].astype(float)


def waiting_times(ts_hl: np.ndarray, ts_bin: np.ndarray, px_bin: np.ndarray) -> dict:
    """Time from each Binance print to the next Hyperliquid print."""
    hl = np.unique(ts_hl)
    order = np.argsort(ts_bin, kind="stable")
    tb, pb = ts_bin[order], px_bin[order]
    keep = np.concatenate([[True], np.diff(tb) > 0])
    tb, pb = tb[keep], pb[keep]

    # |return| carried by each Binance print, the weight HY effectively applies.
    r = np.abs(np.diff(np.log(pb)))
    tb = tb[1:]

    idx = np.searchsorted(hl, tb, side="left")
    valid = idx < hl.size  # prints after the last HL trade have no "next"
    w = hl[idx[valid]] - tb[valid]
    rw = r[valid]

    gaps = np.diff(hl)
    renewal = float((gaps**2).sum() / (2 * gaps.sum())) if gaps.size else float("nan")

    return {
        "w_mean": float(w.mean()),
        "w_weighted": float(np.average(w, weights=rw)) if rw.sum() > 0 else float("nan"),
        "w_median": float(np.median(w)),
        "w_renewal": renewal,
        "w_half": float(gaps.mean() / 2) if gaps.size else float("nan"),
        "n_wait": int(w.size),
    }


def process_hour(coin: str, date: str, hour: int, rng_bps: float) -> dict | None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        s = {}
        for venue in VENUES:
            pfr, out = tmpd / f"{venue}.pfr", tmpd / f"{venue}.csv"
            if not _fetch(venue, coin, date, hour, pfr) or not _decode(venue, coin, pfr, out):
                return None
            s[venue] = _series(out)
        try:
            hy = hayashi_yoshida(*s["hl"], *s["binance"], TAUS)
        except ValueError:
            return None
        row = {"date": date, "hour": hour, "range_bps": round(rng_bps, 1), "tau_ms": hy.peak_ms}
        row.update({k: round(v, 1) for k, v in waiting_times(s["hl"][0], *s["binance"]).items()})
        return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coin", default="BTC")
    ap.add_argument("--start", default="2026-07-18")
    ap.add_argument("--end", default="2026-07-26")
    ap.add_argument("--hours", type=int, default=30, help="evenly spaced sample of usable hours")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    out = REPO / "experiments" / "data" / f"exp014_waiting_{args.coin}.csv"

    if not DUMP.exists():
        raise SystemExit("build tools/pfr-dump first")

    ranges = hourly_range(args.start, args.end, args.coin)
    dates = sorted({d for d, _ in ranges})
    holes: dict[str, set[int]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gapped, v, args.coin, d): d for v in VENUES for d in dates}
        for f in as_completed(futs):
            holes.setdefault(futs[f], set()).update(f.result())

    usable = [(d, h, r) for (d, h), r in sorted(ranges.items()) if h not in holes.get(d, set())]
    step = max(1, len(usable) // args.hours)
    sample = usable[::step][: args.hours]
    print(f"{args.coin}: {len(usable)} usable, sampling {len(sample)}")

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(process_hour, args.coin, d, h, r) for d, h, r in sample]
        for f in as_completed(futs):
            if (row := f.result()) is not None:
                rows.append(row)

    rows.sort(key=lambda r: (r["date"], r["hour"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} hours -> {out}")


if __name__ == "__main__":
    main()
