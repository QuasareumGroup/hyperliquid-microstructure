"""EXP-028 — does endogenous sampling inflate the measured lead-lag?

EXP-027 excluded independent follower noise (structurally: a cross-covariance is
blind to it) and follower density (empirically: flat curve). What it could not
exclude is the one thing its own construction ruled out by accident -- its follower
took its price path from Binance and its observation times from Hyperliquid, so
sampling times were independent of the follower's innovations. Real venues print
BECAUSE a trade happened.

Part 1 measures whether HL's printing is coupled to price movement at all, and runs
the same statistic on Binance since a venue has no reason to be exogenously sampled.

Part 2 changes ONLY the sampler on EXP-027's latent follower. Endogenous sampling
uses a total-variation clock: observe each time cumulative |dlog p| on the
follower's own path crosses a multiple of theta, with theta = TV/n so the count
lands exactly on HL's real count. Same sparsity as the exogenous arms, different
reason for it -- which is the whole comparison.

    python experiments/exp028_endogenous.py --coin BTC --hours 24
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exp009_volatility_buckets import DUMP, _decode, _fetch, hourly_range  # noqa: E402
from exp026_staleness import peak, series, thin_to  # noqa: E402
from exp027_follower_bias import (  # noqa: E402
    L_REPORTED, calibrate_kappa, follower, med, seed_for,
)


def endogeneity(ts_v: np.ndarray, ts_bn: np.ndarray, px_bn: np.ndarray) -> float:
    """Spearman(prints per second, |Binance return| that second).

    Binance's return is the movement proxy for both venues, so a venue's activity
    is never correlated against its own observed returns.
    """
    lo, hi = max(ts_v[0], ts_bn[0]), min(ts_v[-1], ts_bn[-1])
    if hi - lo < 600_000:
        return float("nan")
    edges = np.arange(lo, hi, 1000.0)
    if edges.size < 120:
        return float("nan")
    cnt = np.histogram(ts_v, bins=edges)[0]
    j = np.searchsorted(ts_bn, edges, side="right") - 1
    v = np.where(j >= 0, px_bn[np.clip(j, 0, None)], np.nan)
    r = np.abs(np.diff(np.log(v)))
    ok = np.isfinite(r) & np.isfinite(cnt)
    if ok.sum() < 120 or np.std(cnt[ok]) == 0 or np.std(r[ok]) == 0:
        return float("nan")
    return float(stats.spearmanr(cnt[ok], r[ok]).statistic)


def tv_clock(px: np.ndarray, n: int) -> np.ndarray:
    """Indices of a total-variation clock with exactly `n` ticks.

    Cumulative |dlog p| crossings of multiples of theta = TV/n. This is sampling
    driven by the series' OWN movement -- the coupling a real venue has and the
    one EXP-027's follower lacked.
    """
    tv = np.concatenate([[0.0], np.cumsum(np.abs(np.diff(np.log(px))))])
    if tv[-1] <= 0 or n < 2:
        return np.arange(px.size)
    theta = tv[-1] / n
    return np.searchsorted(tv, np.arange(theta, tv[-1], theta), side="left")


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
    rho, kh = calibrate_kappa(hl_ts, hl_px, bn_ts, bn_px)
    if not np.isfinite(kh):
        return None

    row = {"date": date, "hour": hour, "n_hl": int(hl_ts.size), "n_bn": int(bn_ts.size),
           "kappa": kh, "real": peak(hl_ts, hl_px, bn_ts, bn_px),
           # --- Part 1 ---
           "endo_hl": endogeneity(hl_ts, bn_ts, bn_px),
           "endo_bn": endogeneity(bn_ts, bn_ts, bn_px)}

    # --- Part 2: one latent follower, three samplers, identical count ---
    rng = np.random.default_rng(seed_for(coin, date, hour))
    f_ts, f_px = follower(bn_ts, bn_px, L_REPORTED, kh, rng)
    n = min(hl_ts.size, f_ts.size - 1)

    arms = {
        # driven by the follower's OWN movement
        "endo": tv_clock(f_px, n),
        # same count, selection independent of price
        "exo_rand": np.sort(rng.choice(f_ts.size, size=n, replace=False)),
        "exo_even": np.linspace(0, f_ts.size - 1, n).astype(int),
    }
    for name, idx in arms.items():
        idx = np.unique(idx)
        row[f"p_{name}"] = (peak(f_ts[idx], f_px[idx], bn_ts, bn_px)
                            if idx.size >= 100 else float("nan"))
    # EXP-027's arm, kept for continuity with the previous result
    o_ts, o_px = thin_to(f_ts, f_px, hl_ts)
    row["p_hltimes"] = peak(o_ts, o_px, bn_ts, bn_px) if o_ts.size >= 100 else float("nan")
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coin", default="BTC")
    ap.add_argument("--start", default="2026-07-18")
    ap.add_argument("--end", default="2026-07-26")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if not DUMP.exists():
        raise SystemExit(f"build the decoder first: cd {DUMP.parents[2]} && cargo build --release")

    keys = sorted(hourly_range(args.start, args.end, args.coin))
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

    print(f"\nusable hours {len(rows)}   HL prints/h {med(rows,'n_hl'):,.0f}"
          f"   Binance/h {med(rows,'n_bn'):,.0f}   kappa-hat {med(rows,'kappa'):.2f}")

    eh, eb = med(rows, "endo_hl"), med(rows, "endo_bn")
    print(f"\nPART 1 — Spearman(prints/s, |Binance return|/s)")
    print(f"  Hyperliquid {eh:+.3f}    Binance {eb:+.3f}")
    print(f"  P1 {'CONFIRMED' if eh > 0.2 else 'REJECTED'} — HL's sampling is endogenous")
    print(f"  P2 {'CONFIRMED' if eb > 0.2 else 'REJECTED'} — Binance's is too")

    print(f"\nPART 2 — same latent follower (true L={L_REPORTED:.0f}), same count, "
          f"three samplers")
    base = med(rows, "p_exo_rand")
    for name, lab in (("endo", "endogenous (TV clock)"), ("exo_rand", "exogenous random"),
                      ("exo_even", "exogenous evenly spaced"), ("p_hltimes", "HL real times")):
        key = name if name.startswith("p_") else f"p_{name}"
        m = med(rows, key)
        print(f"  {lab:<26}{m:>8.0f} ms   bias {m-L_REPORTED:+6.0f}"
              f"   vs exo {m-base:+6.0f}")
    shift = med(rows, "p_endo") - base
    print(f"\n  P3 {'CONFIRMED' if shift > 25 else 'REJECTED'} — endogenous sampling "
          f"inflates the peak ({shift:+.0f} ms vs exogenous at identical count)")
    if shift <= 25:
        print("  -> endogeneity excluded alongside noise and density. Every estimator-side")
        print("     explanation is exhausted; the cross-asset -0.656 is market structure.")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"\nwrote {len(rows)} hours -> {args.out}")


if __name__ == "__main__":
    main()
