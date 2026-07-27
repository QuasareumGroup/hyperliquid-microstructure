"""EXP-026 — is the 575 ms an information lag or a sampling artefact?

Test A (gating): shift Binance by a KNOWN lag, thin it to Hyperliquid's actual print
times for the same hour, and require the unmodified estimator to recover the lag we
chose. If thinning alone pulls the recovered peak toward 575 ms at L = 0, Result 1 is
an artefact of observation density and gets withdrawn.

Test B: thin the real Binance series to HL's print times and re-measure the real
HL/Binance lag. Under an information lag the peak should survive; under a sampling
artefact it should collapse.

Reuses EXP-009's fetch/decode machinery and the same Hayashi-Yoshida implementation
Result 1 rests on — no reimplementation, so a defect here is a defect there.

    python experiments/exp026_staleness.py --coin BTC --hours 24
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

from exp009_volatility_buckets import DUMP, REPO, _decode, _fetch, hourly_range  # noqa: E402

from hlm.analysis.leadlag import hayashi_yoshida  # noqa: E402

#: Same grid Result 1 used, so the comparison is like for like.
TAUS = np.arange(-2000, 2001, 25.0)
#: Known lags imposed in Test A. 0 is the one that matters: a peak far from 0
#: there means the estimator manufactures lag from sparsity alone.
KNOWN = (0.0, 100.0, 300.0, 575.0, 1000.0)


def series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with duckdb.connect() as con:
        d = con.sql(f"SELECT ts_ms, px FROM read_csv('{path}') ORDER BY ts_ms").fetchnumpy()
    return d["ts_ms"].astype(float), d["px"].astype(float)


def thin_to(ts_src: np.ndarray, px_src: np.ndarray, ts_target: np.ndarray):
    """Observe the source series only at the target's observation times.

    For each target timestamp, take the source's last price at or before it — the
    same staleness a sparsely-printing venue imposes on itself.
    """
    j = np.searchsorted(ts_src, ts_target, side="right") - 1
    keep = j >= 0
    return ts_target[keep], px_src[j[keep]]


def peak(ts_x, px_x, ts_y, px_y) -> float:
    """Peak lag in ms. Positive => y leads x, as in Result 1."""
    try:
        return hayashi_yoshida(ts_x, px_x, ts_y, px_y, TAUS).peak_ms
    except ValueError:
        return float("nan")


def one_hour(coin: str, date: str, hour: int) -> dict | None:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        s = {}
        for v in ("hl", "binance"):
            pfr, out = t / f"{v}.pfr", t / f"{v}.csv"
            if not _fetch(v, coin, date, hour, pfr) or not _decode(v, coin, pfr, out):
                return None
            s[v] = series(out)

    hl_ts, hl_px = s["hl"]
    bn_ts, bn_px = s["binance"]
    if hl_ts.size < 200 or bn_ts.size < 200:
        return None

    row = {"date": date, "hour": hour, "n_hl": int(hl_ts.size), "n_bn": int(bn_ts.size),
           "real": peak(hl_ts, hl_px, bn_ts, bn_px)}

    # --- Test A: known lag, follower thinned to HL's print times ---
    for L in KNOWN:
        f_ts, f_px = thin_to(bn_ts + L, bn_px, hl_ts)
        if f_ts.size < 100:
            row[f"A{L:.0f}"] = float("nan")
            continue
        # follower is the thinned+shifted copy; leader is the untouched Binance
        row[f"A{L:.0f}"] = peak(f_ts, f_px, bn_ts, bn_px)

    # --- Test B: real HL against a Binance thinned to HL's cadence ---
    tb_ts, tb_px = thin_to(bn_ts, bn_px, hl_ts)
    row["thinned"] = peak(hl_ts, hl_px, tb_ts, tb_px) if tb_ts.size >= 100 else float("nan")
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coin", default="BTC")
    ap.add_argument("--start", default="2026-07-18")
    ap.add_argument("--end", default="2026-07-26")
    ap.add_argument("--hours", type=int, default=24, help="how many hours to sample")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if not DUMP.exists():
        raise SystemExit(f"build the decoder first: cd {DUMP.parents[2]} && cargo build --release")

    ranges = hourly_range(args.start, args.end, args.coin)
    keys = sorted(ranges)
    step = max(1, len(keys) // args.hours)
    todo = keys[::step][: args.hours]
    print(f"{args.coin}: {len(todo)} hours sampled from {len(keys)} in the window")

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(one_hour, args.coin, d, h) for d, h in todo]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            if r:
                rows.append(r)
            if i % 6 == 0:
                print(f"  {i}/{len(todo)} processed, {len(rows)} usable")

    if not rows:
        raise SystemExit("no usable hours")
    rows.sort(key=lambda r: (r["date"], r["hour"]))

    print(f"\nusable hours: {len(rows)}")
    print(f"  HL prints/hour   median {np.median([r['n_hl'] for r in rows]):,.0f}")
    print(f"  Binance/hour     median {np.median([r['n_bn'] for r in rows]):,.0f}")
    real = np.array([r["real"] for r in rows])
    print(f"  real HL/Binance peak : median {np.median(real):.0f} ms")

    print("\nTEST A — known lag imposed, follower thinned to HL's print times")
    print(f"  {'imposed':>9}{'recovered median':>19}{'p25':>8}{'p75':>8}{'error':>9}")
    ok = True
    for L in KNOWN:
        v = np.array([r[f"A{L:.0f}"] for r in rows])
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        med = float(np.median(v))
        err = med - L
        flag = "" if abs(err) <= 50 else "   <-- HORS TOLERANCE"
        ok &= abs(err) <= 50
        print(f"  {L:>7.0f} ms{med:>16.0f} ms{np.percentile(v,25):>8.0f}"
              f"{np.percentile(v,75):>8.0f}{err:>+8.0f}{flag}")
    print(f"\n  P1 {'CONFIRMED' if ok else 'REJECTED'} — every known lag recovered within +/-50 ms")
    if not ok:
        print("  -> the estimator manufactures lag from sparsity. Result 1 is in question.")

    print("\nTEST B — real HL against Binance thinned to HL's cadence")
    th = np.array([r["thinned"] for r in rows])
    m = np.isfinite(th) & np.isfinite(real)
    print(f"  unthinned median {np.median(real[m]):.0f} ms   thinned median {np.median(th[m]):.0f} ms")
    print(f"  change {np.median(th[m]) - np.median(real[m]):+.0f} ms")
    print(f"  P2 {'CONFIRMED' if np.median(th[m]) >= 400 else 'REJECTED'} — thinned peak stays above 400 ms")
    direction = "up" if np.median(th[m]) > np.median(real[m]) else "down"
    print(f"  P3 {'CONFIRMED' if direction == 'up' else 'REJECTED'} — thinning moves the peak {direction}")
    if m.sum() >= 8:
        from scipy import stats
        sp = stats.spearmanr(real[m], th[m])
        print(f"  P4 {'CONFIRMED' if sp.statistic > 0.5 else 'REJECTED'} — "
              f"rank correlation thinned vs unthinned = {sp.statistic:+.3f} (p={sp.pvalue:.3f})")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"\nwrote {len(rows)} hours -> {args.out}")


if __name__ == "__main__":
    main()
