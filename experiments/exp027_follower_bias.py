"""EXP-027 — how much of the measured 575 ms is follower sparsity?

EXP-026 Test A showed that thinning a follower to Hyperliquid's print times costs
nothing when that follower is a deterministic shift of the leader. So any bias in
the real measurement must come from sparsity interacting with the follower having
price innovations of its OWN -- the case Test A could not build. This maps that
interaction and inverts it to a corrected lag.

The synthetic follower is a lagged Binance plus an independent random walk of
calibrated variance, observed at HL's real print times (real count AND real
burstiness, which a uniform subsample would lose).

Reuses EXP-026's fetch/decode/thin machinery and the same estimator, so kappa = 0
must reproduce Test A -- that is prediction P1, and it is a check on this code.

    python experiments/exp027_follower_bias.py --coin BTC --hours 24
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exp009_volatility_buckets import DUMP, REPO, _decode, _fetch, hourly_range  # noqa: E402
from exp026_staleness import TAUS, peak, series, thin_to  # noqa: E402

#: True lags imposed. Four points are enough to fit measured(L) and invert at 575.
LAGS = (200.0, 400.0, 575.0, 800.0)
#: Noise ratios as multiples of the calibrated kappa-hat. 0 is the anchor that
#: must reproduce EXP-026 Test A.
KAPPA_MULT = (0.0, 0.25, 1.0, 4.0)
#: Follower observation counts as multiples of HL's real count, for the density
#: curve. `None` means "every Binance timestamp".
DENSITY_MULT = (0.5, 1.0, 2.0, 4.0, 8.0, None)
#: The lag Result 1 reports, used both to align the kappa calibration and as the
#: value to invert.
L_REPORTED = 575.0
#: Below this correlation the kappa estimate is not identified and the hour is
#: dropped rather than fitted with a meaningless residual ratio.
RHO_MIN = 0.10


def seed_for(coin: str, date: str, hour: int) -> int:
    """Deterministic per-hour seed — the run must reproduce exactly."""
    h = hashlib.sha256(f"{coin}|{date}|{hour}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def grid_returns(ts: np.ndarray, px: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Log returns of `px` sampled last-at-or-before each grid edge."""
    j = np.searchsorted(ts, edges, side="right") - 1
    v = np.where(j >= 0, px[np.clip(j, 0, None)], np.nan)
    return np.diff(np.log(v))


def calibrate_kappa(hl_ts, hl_px, bn_ts, bn_px) -> tuple[float, float]:
    """kappa-hat = (1-rho^2)/rho^2 on a common 1 s grid, Binance shifted by 575 ms.

    Deliberately an UPPER bound: microstructure noise and tick discretisation land
    in the residual. Overstating kappa overstates the bias and so understates the
    corrected lag — conservative against our own result.
    """
    lo = max(hl_ts[0], bn_ts[0] + L_REPORTED)
    hi = min(hl_ts[-1], bn_ts[-1] + L_REPORTED)
    if hi - lo < 600_000:                       # under 10 minutes of overlap
        return float("nan"), float("nan")
    edges = np.arange(lo, hi, 1000.0)
    r_hl = grid_returns(hl_ts, hl_px, edges)
    r_bn = grid_returns(bn_ts + L_REPORTED, bn_px, edges)
    ok = np.isfinite(r_hl) & np.isfinite(r_bn)
    if ok.sum() < 120 or r_hl[ok].std() == 0 or r_bn[ok].std() == 0:
        return float("nan"), float("nan")
    rho = float(np.corrcoef(r_hl[ok], r_bn[ok])[0, 1])
    if not np.isfinite(rho) or rho <= RHO_MIN:
        return rho, float("nan")
    return rho, (1.0 - rho**2) / rho**2


def follower(bn_ts, bn_px, L: float, kappa: float, rng) -> tuple[np.ndarray, np.ndarray]:
    """Latent follower: leader lagged by L, plus its own independent random walk.

    Per-increment noise variance is kappa x the leader's, so the follower's
    idiosyncratic realized variance over the hour is kappa x the leader's.
    """
    lp = np.log(bn_px)
    if kappa <= 0:
        return bn_ts + L, bn_px
    sd = float(np.std(np.diff(lp))) * np.sqrt(kappa)
    w = np.concatenate([[0.0], np.cumsum(rng.normal(0.0, sd, lp.size - 1))])
    return bn_ts + L, np.exp(lp + w)


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

    rng = np.random.default_rng(seed_for(coin, date, hour))
    row = {"date": date, "hour": hour, "n_hl": int(hl_ts.size), "n_bn": int(bn_ts.size),
           "rho": rho, "kappa": kh,
           "real": peak(hl_ts, hl_px, bn_ts, bn_px)}

    # --- main grid: bias(L, kappa) at HL's real print times ---
    for km in KAPPA_MULT:
        for L in LAGS:
            f_ts, f_px = follower(bn_ts, bn_px, L, kh * km, rng)
            o_ts, o_px = thin_to(f_ts, f_px, hl_ts)
            row[f"m_k{km:g}_L{L:.0f}"] = (
                peak(o_ts, o_px, bn_ts, bn_px) if o_ts.size >= 100 else float("nan")
            )

    # --- density curve at the reported lag and calibrated kappa ---
    f_ts, f_px = follower(bn_ts, bn_px, L_REPORTED, kh, rng)
    for dm in DENSITY_MULT:
        if dm is None:
            tgt = bn_ts
        else:
            n = min(int(hl_ts.size * dm), bn_ts.size)
            tgt = np.sort(rng.choice(bn_ts, size=n, replace=False))
        o_ts, o_px = thin_to(f_ts, f_px, tgt)
        key = "d_full" if dm is None else f"d_{dm:g}"
        row[key] = peak(o_ts, o_px, bn_ts, bn_px) if o_ts.size >= 100 else float("nan")

    # --- P5: reproduce Test B's manipulation on a pair whose true lag is KNOWN.
    # Paired — the same synthetic follower is measured against a full-density
    # leader and against one thinned to HL's print times, so the only difference
    # between the two columns is the leader.
    rng2 = np.random.default_rng(seed_for(coin, date, hour) ^ 0x5F5)
    tb_ts, tb_px = thin_to(bn_ts, bn_px, hl_ts)
    for km in (0.0, 1.0):
        f_ts, f_px = follower(bn_ts, bn_px, L_REPORTED, kh * km, rng2)
        o_ts, o_px = thin_to(f_ts, f_px, hl_ts)
        good = o_ts.size >= 100 and tb_ts.size >= 100
        row[f"ld_full_k{km:g}"] = peak(o_ts, o_px, bn_ts, bn_px) if good else float("nan")
        row[f"ld_thin_k{km:g}"] = peak(o_ts, o_px, tb_ts, tb_px) if good else float("nan")
    return row


def med(rows, key) -> float:
    v = np.array([r[key] for r in rows], dtype=float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else float("nan")


def invert(rows, km: float = 1.0) -> tuple[float, float, float]:
    """Fit measured = a + b*L at calibrated kappa, then solve a + b*L* = 575."""
    xs = np.array(LAGS)
    ys = np.array([med(rows, f"m_k{km:g}_L{L:.0f}") for L in xs])
    ok = np.isfinite(ys)
    if ok.sum() < 2:
        return float("nan"), float("nan"), float("nan")
    b, a = np.polyfit(xs[ok], ys[ok], 1)
    return a, b, (L_REPORTED - a) / b if b != 0 else float("nan")


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

    kh = med(rows, "kappa")
    print(f"\nusable hours {len(rows)}   HL prints/h {med(rows,'n_hl'):,.0f}"
          f"   Binance/h {med(rows,'n_bn'):,.0f}")
    print(f"  rho {med(rows,'rho'):.3f}   kappa-hat {kh:.2f} (upper bound)")
    print(f"  real HL/Binance peak {med(rows,'real'):.0f} ms")

    print("\nBIAS(L, kappa) at HL's real print times — median measured, (bias)")
    hdr = "".join(f"{f'k={km:g}kh':>18}" for km in KAPPA_MULT)
    print(f"  {'true L':>8}{hdr}")
    for L in LAGS:
        cells = ""
        for km in KAPPA_MULT:
            m = med(rows, f"m_k{km:g}_L{L:.0f}")
            cells += f"{m:>10.0f} ({m-L:+.0f})" if np.isfinite(m) else f"{'—':>18}"
        print(f"  {L:>6.0f}ms{cells}")

    b0 = np.array([med(rows, f"m_k0_L{L:.0f}") - L for L in LAGS])
    p1 = np.all(np.abs(b0[np.isfinite(b0)]) <= 50)
    print(f"\n  P1 {'CONFIRMED' if p1 else 'REJECTED'} — kappa=0 reproduces EXP-026 Test A "
          f"(max |bias| {np.nanmax(np.abs(b0)):.0f} ms)")
    if not p1:
        print("  -> this code and EXP-026 disagree on a shared case. Nothing below is usable.")

    bias_by_k = [med(rows, f"m_k{km:g}_L{L_REPORTED:.0f}") - L_REPORTED for km in KAPPA_MULT]
    fin = [b for b in bias_by_k if np.isfinite(b)]
    p2 = all(y >= x - 25 for x, y in zip(fin, fin[1:])) and fin[-1] > 25
    print(f"  P2 {'CONFIRMED' if p2 else 'REJECTED'} — bias grows with kappa "
          f"({', '.join(f'{b:+.0f}' for b in bias_by_k)} ms)")

    print("\nDENSITY CURVE at L=575, kappa=kappa-hat")
    for dm in DENSITY_MULT:
        key = "d_full" if dm is None else f"d_{dm:g}"
        lab = "full Binance" if dm is None else f"{dm:g}x HL"
        m = med(rows, key)
        print(f"  {lab:>14}{m:>10.0f} ms   bias {m-L_REPORTED:+.0f}")
    bf = med(rows, "d_full") - L_REPORTED
    print(f"  P3 {'CONFIRMED' if abs(bf) <= 50 else 'REJECTED'} — bias vanishes at full "
          f"density ({bf:+.0f} ms)")

    print("\nP5 DIAGNOSTIC — same synthetic follower (true L=575), leader full vs thinned")
    p5 = []
    for km in (0.0, 1.0):
        lf, lt = med(rows, f"ld_full_k{km:g}"), med(rows, f"ld_thin_k{km:g}")
        p5.append(lt - lf)
        print(f"  kappa={km:g}kh   leader full {lf:>6.0f} ms   leader thinned {lt:>6.0f} ms"
              f"   inflation {lt-lf:+.0f}")
    fin5 = [d for d in p5 if np.isfinite(d)]
    ok5 = bool(fin5) and all(d >= 25 for d in fin5)
    print(f"  P5 {'CONFIRMED' if ok5 else 'REJECTED'} — thinning the LEADER inflates a "
          f"known-lag pair")
    print("  -> Test B's inflation is leader-thinning. Result 1 does not thin the leader."
          if ok5 else
          "  -> Test B's inflation is NOT reproduced. Its source is unidentified; the "
          "EXP-026 caveat stands.")

    a, b, ls = invert(rows)
    real_bias = med(rows, f"m_k1_L{L_REPORTED:.0f}") - L_REPORTED
    print(f"\nCORRECTION   measured = {a:+.0f} + {b:.3f}*L")
    print(f"  bias at real density and kappa-hat : {real_bias:+.0f} ms")
    print(f"  measured 575 ms  =>  true lag L* = {ls:.0f} ms")
    print(f"  P4 {'CONFIRMED' if real_bias < 200 else 'REJECTED'} — bias under 200 ms")
    if real_bias >= 400:
        print("  -> L* < 175 ms. Result 1's DIRECTION survives; its MAGNITUDE does not.")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"\nwrote {len(rows)} hours -> {args.out}")


if __name__ == "__main__":
    main()
