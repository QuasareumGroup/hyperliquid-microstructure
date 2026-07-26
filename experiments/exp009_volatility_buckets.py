"""EXP-009 — lead-lag asymmetry as a continuous function of volatility.

EXP-008 contrasted two pools of three hours and found Hyperliquid's lag roughly
doubles under stress while the CEX pairs hold. That cannot distinguish a smooth
relationship from a threshold. This measures every usable hour instead.

For each hour it computes the block-aligned asymmetry (EXP-006 protocol) for
`hl/binance` and, as the control, `okx/binance`. Tape is fetched, decoded and
deleted per hour, so peak disk stays at three files rather than several hundred
megabytes — the machine this targets runs near-full.

    python experiments/exp009_volatility_buckets.py --start 2026-07-18 --end 2026-07-26

Writes `experiments/data/exp009_hours.csv`.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import subprocess
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
import numpy as np

INFO = "https://api.hyperliquid.xyz/info"
TAPE = "https://perplog.com/api/flow/tape"
VENUES = ("hl", "binance", "okx")
PAIRS = (("hl", "binance"), ("okx", "binance"))
#: ±K events around zero. The asymmetry statistic sums each side.
K = 6
REPO = Path(__file__).resolve().parent.parent
DUMP = REPO / "tools" / "pfr-dump" / "target" / "release" / "pfr-dump"

#: Required. perplog.com sits behind Cloudflare, which 403s urllib's default
#: `Python-urllib/3.x` agent — the same URL works from curl. Without this the
#: whole campaign silently produced "0 usable hours".
UA = "hyperliquid-microstructure/0.1 (research)"


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read()


def _post(payload: dict) -> object:
    req = urllib.request.Request(
        INFO,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)


def hourly_range(start: str, end: str, coin: str) -> dict[tuple[str, int], float]:
    """Realised hourly range in bps, keyed by (date, hour)."""
    to_ms = lambda s: int(  # noqa: E731
        dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.UTC).timestamp() * 1000
    )
    candles = _post(
        {
            "type": "candleSnapshot",
            "req": {
                "coin": coin, "interval": "1h",
                "startTime": to_ms(start), "endTime": to_ms(end),
            },
        }
    )
    out = {}
    for c in candles:
        stamp = dt.datetime.fromtimestamp(c["t"] / 1000, dt.UTC)
        o, h, low = float(c["o"]), float(c["h"]), float(c["l"])
        if o > 0:
            out[(stamp.strftime("%Y-%m-%d"), stamp.hour)] = 10_000 * (h - low) / o
    return out


def gapped(venue: str, coin: str, date: str) -> set[int]:
    """Hours the venue did not record. Absent != error; the API lists holes.

    Raises rather than degrading. An earlier version swallowed the exception
    and returned "all 24 gapped", so a total transport failure was reported as
    "0 usable hours" — a wrong answer dressed as a real one.
    """
    url = f"https://perplog.com/api/flow/tape/coverage?venue={venue}&coin={coin}&date={date}"
    return set(json.loads(_get(url)).get("gapped", []))


def _fetch(venue: str, coin: str, date: str, hour: int, dest: Path) -> bool:
    url = f"{TAPE}?venue={venue}&coin={coin}&date={date}&hour={hour}"
    try:
        data = _get(url, timeout=60)
    except Exception:
        return False
    # A PFR1 frame starts with the magic; an error response is JSON.
    if not data.startswith(b"PFR1"):
        return False
    dest.write_bytes(data)
    return True


def _decode(venue: str, coin: str, pfr: Path, csv_out: Path) -> bool:
    with csv_out.open("w") as out:
        r = subprocess.run(
            [str(DUMP), venue, coin, str(pfr)], stdout=out, stderr=subprocess.DEVNULL
        )
    return r.returncode == 0 and csv_out.stat().st_size > 100


def asymmetry(csv_a: Path, csv_b: Path) -> tuple[int, float, float, float, int]:
    """Block-aligned asymmetry on venue A's event grid. Returns (n, step, neg, pos, peak_k)."""
    q = f"""
      WITH A AS (SELECT ts_ms, last(px ORDER BY ts_ms) pa FROM read_csv('{csv_a}') GROUP BY 1),
           B AS (SELECT ts_ms, last(px ORDER BY ts_ms) pb FROM read_csv('{csv_b}') GROUP BY 1)
      SELECT A.ts_ms, A.pa, B.pb FROM A ASOF JOIN B ON A.ts_ms >= B.ts_ms ORDER BY A.ts_ms
    """
    # A private connection per call: duckdb's module-level default connection
    # is shared, and concurrent use from the worker pool raises
    # "unsuccessful or closed pending query result" partway through a run.
    with duckdb.connect() as con:
        d = con.sql(q).fetchnumpy()
    ts = d["ts_ms"].astype(np.int64)
    if ts.size < 200:
        return 0, 0.0, 0.0, 0.0, 0
    ra = np.diff(np.log(d["pa"].astype(float)))
    rb = np.diff(np.log(d["pb"].astype(float)))
    rows = []
    for k in range(-K, K + 1):
        if k < 0:
            x, y = ra[-k:], rb[:k]
        elif k > 0:
            x, y = ra[:-k], rb[k:]
        else:
            x, y = ra, rb
        if x.size < 50 or np.std(x) == 0 or np.std(y) == 0:
            return 0, 0.0, 0.0, 0.0, 0
        rows.append((k, float(np.corrcoef(x, y)[0, 1])))
    neg = sum(c for k, c in rows if k < 0)
    pos = sum(c for k, c in rows if k > 0)
    peak = max(rows, key=lambda t: abs(t[1]))[0]
    return ra.size, float(np.median(np.diff(ts))), neg, pos, peak


def process_hour(coin: str, date: str, hour: int, rng_bps: float) -> dict | None:
    """Fetch, decode, measure, delete. Peak disk is three tape files."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        csvs: dict[str, Path] = {}
        for venue in VENUES:
            pfr = tmpd / f"{venue}.pfr"
            out = tmpd / f"{venue}.csv"
            if not _fetch(venue, coin, date, hour, pfr) or not _decode(venue, coin, pfr, out):
                return None
            csvs[venue] = out
        row = {"date": date, "hour": hour, "range_bps": round(rng_bps, 1)}
        for a, b in PAIRS:
            n, step, neg, pos, peak = asymmetry(csvs[a], csvs[b])
            if n == 0:
                return None
            key = f"{a}_{b}"
            row[f"n_{key}"] = n
            row[f"step_{key}"] = round(step, 0)
            row[f"neg_{key}"] = round(neg, 4)
            row[f"pos_{key}"] = round(pos, 4)
            row[f"peak_{key}"] = peak
        return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coin", default="BTC")
    ap.add_argument("--start", default="2026-07-18")
    ap.add_argument("--end", default="2026-07-26")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=REPO / "experiments" / "data" / "exp009_hours.csv")
    args = ap.parse_args()

    if not DUMP.exists():
        raise SystemExit(f"build the decoder first: cd {DUMP.parents[2]} && cargo build --release")

    ranges = hourly_range(args.start, args.end, args.coin)
    dates = sorted({d for d, _ in ranges})
    print(f"{len(ranges)} hours in range, {len(dates)} days")

    holes: dict[str, set[int]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gapped, v, args.coin, d): (v, d) for v in VENUES for d in dates}
        for f in as_completed(futs):
            _, d = futs[f]
            holes.setdefault(d, set()).update(f.result())

    usable = [(d, h, r) for (d, h), r in sorted(ranges.items()) if h not in holes.get(d, set())]
    print(f"{len(usable)}/{len(ranges)} hours usable on all of {', '.join(VENUES)}")

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(process_hour, args.coin, d, h, r): (d, h) for d, h, r in usable}
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
