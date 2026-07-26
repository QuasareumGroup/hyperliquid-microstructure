"""EXP-021 — does the 575 ms lag hold on the quiet hours the gap filter discarded?

EXP-011 used 144 of the 216 hours available over 2026-07-18 → 07-26. The rest were
removed by perplog's `gapped` coverage flag, which marked a gap on every reconnect
using `missed_ms = now - last_event` — a measure of market silence, not downtime.
Hyperliquid has the lowest event rate of the three venues and drew the most spurious
flags, so the surviving sample skews toward *active* hours.

This script does not trust that flag. perplog's recorder has since been fixed, but the
fix is forward-looking: July's flags are stored metadata written at record time. So
completeness is re-derived **from the tape**, using the one signal that separates
silence from downtime — during a real outage the other venues keep recording, during a
quiet market they fall silent together.

Every hour in the window is fetched and classified, whatever its flag says. Hours
complete on all three venues get the same Hayashi-Yoshida scan EXP-011 ran, so
previously-retained and newly-recovered hours are measured identically.

    python experiments/exp021_recovered_hours.py

Writes `experiments/data/exp021_coverage.csv` and `experiments/data/exp021_hy.csv`.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exp009_volatility_buckets import (  # noqa: E402
    DUMP,
    REPO,
    VENUES,
    _decode,
    _fetch,
    gapped,
    hourly_range,
)

from hlm.analysis.leadlag import hayashi_yoshida  # noqa: E402

PAIRS = (("hl", "binance"), ("okx", "binance"))
#: Same grid as EXP-011, so recovered and retained hours are directly comparable.
TAUS = np.arange(-2000, 2001, 25.0)

HOUR_MS = 3_600_000

# --- classifier thresholds, fixed before the run (EXP-021 §3) ---------------
#: A silence shorter than this is never evidence of anything.
SILENCE_MS = 60_000
#: Another venue counts as live if its rate inside the window is at least this
#: fraction of its own rate across the hour.
RATE_FRAC = 0.25
#: Absolute floor, NOT in the pre-registration — added here and reported as a
#: deviation. Without it the rate test degenerates: on a genuinely quiet hour the
#: expected count inside a 60 s window can be under two events, so a single print
#: elsewhere clears the 25% bar and the classifier reproduces the very false
#: positive it exists to remove. Requiring the other venue to have actually
#: printed 5 events makes "the market was live" a claim about observed activity
#: rather than about a ratio between two small numbers.
MIN_EVENTS = 5
#: Below this, an hour's HY estimate is too thin to read (EXP-021 §4).
POWER_FLOOR = 200


def hour_bounds(date: str, hour: int) -> tuple[float, float]:
    start = dt.datetime.strptime(date, "%Y-%m-%d").replace(hour=hour, tzinfo=dt.UTC)
    t0 = start.timestamp() * 1000
    return t0, t0 + HOUR_MS


def silences(ts: np.ndarray, t0: float, t1: float) -> list[tuple[float, float]]:
    """Silence windows of at least SILENCE_MS, including the hour's edges.

    The edges matter: a venue that starts recording twenty minutes into the hour
    has no *inter-event* gap to find, and would otherwise pass as complete.
    """
    edges = np.concatenate([[t0], ts, [t1]])
    d = np.diff(edges)
    return [(edges[i], edges[i + 1]) for i in np.nonzero(d >= SILENCE_MS)[0]]


def _live_during(window: tuple[float, float], other: np.ndarray) -> bool:
    a, b = window
    if other.size == 0:
        return False
    cnt = int(np.searchsorted(other, b, "right") - np.searchsorted(other, a, "left"))
    expected = (other.size / HOUR_MS) * (b - a)
    return cnt >= MIN_EVENTS and cnt >= RATE_FRAC * expected


def classify(ts: np.ndarray | None, others: list[np.ndarray], t0: float, t1: float) -> str:
    """absent | incomplete | complete — from the tape, never from the flag."""
    if ts is None:
        return "absent"
    for window in silences(ts, t0, t1):
        if any(_live_during(window, o) for o in others):
            return "incomplete"
    return "complete"


def _series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with duckdb.connect() as con:
        d = con.sql(f"SELECT ts_ms, px FROM read_csv('{path}') ORDER BY ts_ms").fetchnumpy()
    return d["ts_ms"].astype(float), d["px"].astype(float)


def load_hour(coin: str, date: str, hour: int) -> dict[str, tuple[np.ndarray, np.ndarray] | None]:
    """Fetch, decode, read, delete. Peak disk stays at three tape files."""
    out: dict[str, tuple[np.ndarray, np.ndarray] | None] = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        for venue in VENUES:
            pfr, csv_out = tmpd / f"{venue}.pfr", tmpd / f"{venue}.csv"
            if not _fetch(venue, coin, date, hour, pfr) or not _decode(venue, coin, pfr, csv_out):
                out[venue] = None
                continue
            try:
                out[venue] = _series(csv_out)
            except Exception:
                out[venue] = None
    return out


def process_hour(coin: str, date: str, hour: int, rng_bps: float, flagged: bool) -> dict:
    t0, t1 = hour_bounds(date, hour)
    data = load_hour(coin, date, hour)
    ts = {v: (data[v][0] if data[v] else None) for v in VENUES}

    klass = {}
    for v in VENUES:
        others = [ts[w] for w in VENUES if w != v and ts[w] is not None]
        klass[v] = classify(ts[v], others, t0, t1)

    row: dict = {
        "date": date,
        "hour": hour,
        "range_bps": round(rng_bps, 1),
        "flagged": int(flagged),
    }
    for v in VENUES:
        row[f"class_{v}"] = klass[v]
        row[f"n_{v}"] = 0 if ts[v] is None else int(ts[v].size)
        row[f"maxsil_{v}"] = (
            -1 if ts[v] is None else int(max((b - a for a, b in silences(ts[v], t0, t1)), default=0))
        )

    row["usable"] = int(all(klass[v] == "complete" for v in VENUES))

    # Synthetic control: punch a known 5-minute hole in HL and confirm the
    # classifier calls it. Only on hours it just called complete, so a failure
    # here is unambiguous (method rule 5).
    row["synthetic_caught"] = ""
    if row["usable"] and ts["hl"] is not None:
        mid = t0 + HOUR_MS / 2
        holed = ts["hl"][(ts["hl"] < mid) | (ts["hl"] > mid + 300_000)]
        others = [ts[w] for w in VENUES if w != "hl" and ts[w] is not None]
        row["synthetic_caught"] = int(classify(holed, others, t0, t1) == "incomplete")

    if row["usable"]:
        for a, b in PAIRS:
            try:
                r = hayashi_yoshida(*data[a], *data[b], TAUS)  # type: ignore[misc]
            except ValueError:
                row["usable"] = 0
                break
            key = f"{a}_{b}"
            row[f"peak_ms_{key}"] = r.peak_ms
            row[f"peak_corr_{key}"] = round(r.peak_corr, 4)
            row[f"index_{key}"] = round(r.asymmetry(), 4)
            row[f"nret_{key}"] = r.n_x
    return row


FIELDS = (
    ["date", "hour", "range_bps", "flagged"]
    + [f"{p}_{v}" for v in VENUES for p in ("class", "n", "maxsil")]
    + ["usable", "synthetic_caught"]
    + [f"{p}_{a}_{b}" for a, b in PAIRS for p in ("peak_ms", "peak_corr", "index", "nret")]
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coin", default="BTC")
    ap.add_argument("--start", default="2026-07-18")
    ap.add_argument("--end", default="2026-07-26")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=REPO / "experiments" / "data" / "exp021_hours.csv")
    args = ap.parse_args()

    if not DUMP.exists():
        raise SystemExit(f"build the decoder first: cd {DUMP.parents[2]} && cargo build --release")

    ranges = hourly_range(args.start, args.end, args.coin)
    dates = sorted({d for d, _ in ranges})
    print(f"{len(ranges)} hours in window, {len(dates)} days")

    holes: dict[str, set[int]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gapped, v, args.coin, d): d for v in VENUES for d in dates}
        for f in as_completed(futs):
            holes.setdefault(futs[f], set()).update(f.result())
    n_flagged = sum(len(h) for h in holes.values())
    print(f"{n_flagged} hours flagged `gapped` by the coverage API (union over venues)")
    print("every hour is processed regardless — the flag is recorded, not obeyed\n")

    rows = []
    todo = [(d, h, r, h in holes.get(d, set())) for (d, h), r in sorted(ranges.items())]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(process_hour, args.coin, d, h, r, fl) for d, h, r, fl in todo]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 20 == 0:
                print(f"  {i}/{len(todo)} processed, {sum(r['usable'] for r in rows)} usable")

    rows.sort(key=lambda r: (r["date"], r["hour"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} hours -> {args.out}")


if __name__ == "__main__":
    main()
