"""EXP-021 analysis — validation first, then the four registered predictions.

Reads `experiments/data/exp021_hours.csv` and `experiments/data/exp011_hy_hours.csv`.
Prints validation, P1–P4, and the extended-sample restatement. Nothing here chooses a
threshold; all of them are fixed in EXP-021 §3–4 and in the run script.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "experiments" / "data"
POWER_FLOOR = 200


def load(path: Path) -> list[dict]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def boot_median(v: np.ndarray, n: int = 20_000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    m = np.median(rng.choice(v, size=(n, v.size), replace=True), axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def line() -> None:
    print("-" * 74)


rows = load(DATA / "exp021_hours.csv")
prev = {(r["date"], int(r["hour"])) for r in load(DATA / "exp011_hy_hours.csv")}

for r in rows:
    r["hour"] = int(r["hour"])
    r["flagged"] = r["flagged"] == "1"
    r["usable"] = r["usable"] == "1"
    r["range_bps"] = float(r["range_bps"])
    for v in ("hl", "binance", "okx"):
        r[f"n_{v}"] = int(r[f"n_{v}"])
    if r["usable"]:
        r["peak_hl"] = float(r["peak_ms_hl_binance"])
        r["peak_okx"] = float(r["peak_ms_okx_binance"])

print(f"EXP-021 — {len(rows)} hours, window 2026-07-18 -> 07-26, BTC\n")

# ---------------------------------------------------------------- validation
line()
print("VALIDATION (must pass before any result is read)")
line()

syn = [r["synthetic_caught"] for r in rows if r["synthetic_caught"] != ""]
n_syn_ok = sum(1 for s in syn if s == "1")
print(f"  synthetic 5-min hole caught      : {n_syn_ok}/{len(syn)}")

prev_rows = [r for r in rows if (r["date"], r["hour"]) in prev]
prev_complete = sum(1 for r in prev_rows if r["usable"])
print(f"  hours EXP-011 used, re-classified : {prev_complete}/{len(prev_rows)} complete")
missing = [r for r in prev_rows if not r["usable"]]
for r in missing[:5]:
    cls = {v: r[f"class_{v}"] for v in ("hl", "binance", "okx")}
    print(f"      {r['date']} {r['hour']:02d}h -> {cls}")

ok = n_syn_ok == len(syn) and prev_complete == len(prev_rows)
print(f"\n  {'PASS' if ok else 'FAIL'}")
if not ok:
    raise SystemExit("validation failed — results not read")

# ------------------------------------------------------------------ P1
line()
print("P1 — at least 70% of flagged hours classify complete")
line()
flagged = [r for r in rows if r["flagged"]]
fl_ok = sum(1 for r in flagged if r["usable"])
pct = 100 * fl_ok / len(flagged) if flagged else 0
print(f"  flagged hours          : {len(flagged)}")
print(f"  classified complete    : {fl_ok}  ({pct:.1f}%)")
print(f"  genuinely incomplete   : {len(flagged) - fl_ok}")
print(f"\n  P1 {'CONFIRMED' if pct >= 70 else 'REJECTED'}")

recovered = [r for r in flagged if r["usable"]]
retained = [r for r in rows if r["usable"] and not r["flagged"]]
print(f"\n  recovered = {len(recovered)} hours   retained = {len(retained)} hours")
print(f"  usable total = {len(recovered) + len(retained)} vs EXP-011's {len(prev)}")

# ------------------------------------------------------------------ P2
line()
print("P2 (load-bearing) — recovered hours are quieter than retained")
line()
rec_rng = np.array([r["range_bps"] for r in recovered])
ret_rng = np.array([r["range_bps"] for r in retained])
rec_n = np.array([r["n_hl"] for r in recovered], dtype=float)
ret_n = np.array([r["n_hl"] for r in retained], dtype=float)
print(f"  {'':<22}{'recovered':>12}{'retained':>12}")
print(f"  {'median range_bps':<22}{np.median(rec_rng):>12.1f}{np.median(ret_rng):>12.1f}")
print(f"  {'median HL events':<22}{np.median(rec_n):>12.0f}{np.median(ret_n):>12.0f}")
print(f"  {'mean range_bps':<22}{rec_rng.mean():>12.1f}{ret_rng.mean():>12.1f}")
p2 = np.median(rec_rng) < np.median(ret_rng) and np.median(rec_n) < np.median(ret_n)
print(f"\n  P2 {'CONFIRMED' if p2 else 'REJECTED'}")

# ------------------------------------------------------------------ P3
line()
print("P3 — on recovered hours above the power floor, Binance still leads,")
print("     median peak in [400, 750] ms")
line()
thin = [r for r in recovered if r["n_hl"] < POWER_FLOOR]
rec_ok = [r for r in recovered if r["n_hl"] >= POWER_FLOOR]
print(f"  below power floor ({POWER_FLOOR} HL events), reported separately: {len(thin)}")
if rec_ok:
    pk = np.array([r["peak_hl"] for r in rec_ok])
    lead = int((pk > 0).sum())
    lo, hi = boot_median(pk)
    print(f"  hours measured            : {len(rec_ok)}")
    print(f"  Binance leads             : {lead}/{len(rec_ok)}  ({100*lead/len(rec_ok):.1f}%)")
    print(f"  median peak               : {np.median(pk):.0f} ms   95% CI [{lo:.0f}, {hi:.0f}]")
    print(f"  mean peak                 : {pk.mean():.0f} ms")
    okxp = np.array([r["peak_okx"] for r in rec_ok])
    print(f"  control okx/binance median: {np.median(okxp):.0f} ms")
    p3 = lead == len(rec_ok) and 400 <= np.median(pk) <= 750
    print(f"\n  P3 {'CONFIRMED' if p3 else 'REJECTED'}")
if thin:
    tp = np.array([r["peak_hl"] for r in thin])
    print(f"\n  thin hours (excluded): median {np.median(tp):.0f} ms, "
          f"Binance leads {int((tp > 0).sum())}/{len(tp)}")

# ------------------------------------------------------------------ P4
line()
print("P4 — volatility invariance over the extended sample, |Spearman| <= 0.20")
line()
ext = [r for r in rows if r["usable"] and r["n_hl"] >= POWER_FLOOR]
x = np.array([r["range_bps"] for r in ext])
y = np.array([r["peak_hl"] for r in ext])
rho_ext = spearman(x, y)
xr = np.array([r["range_bps"] for r in retained if r["n_hl"] >= POWER_FLOOR])
yr = np.array([r["peak_hl"] for r in retained if r["n_hl"] >= POWER_FLOOR])
rho_ret = spearman(xr, yr)
print(f"  retained only  (n={len(xr):3d}) : rho = {rho_ret:+.3f}")
print(f"  extended       (n={len(x):3d}) : rho = {rho_ext:+.3f}")
print(f"  range_bps span : retained [{xr.min():.1f}, {xr.max():.1f}]  "
      f"extended [{x.min():.1f}, {x.max():.1f}]")
print(f"\n  P4 {'CONFIRMED' if abs(rho_ext) <= 0.20 else 'REJECTED'}")

# ------------------------------------------------------- extended restatement
line()
print("EXTENDED SAMPLE — the restated headline")
line()
lead_all = int((y > 0).sum())
lo, hi = boot_median(y)
print(f"  hours              : {len(y)}")
print(f"  Binance leads      : {lead_all}/{len(y)}  ({100*lead_all/len(y):.1f}%)")
print(f"  median peak        : {np.median(y):.0f} ms   95% CI [{lo:.0f}, {hi:.0f}]")
print(f"  mean peak          : {y.mean():.0f} ms")
oc = np.array([r["peak_okx"] for r in ext])
print(f"  control okx/binance: median {np.median(oc):.0f} ms  -> factor "
      f"{np.median(y)/max(np.median(oc), 1):.0f}")
print(f"\n  EXP-011 reported   : median 575 ms, 100% of 144 hours")
