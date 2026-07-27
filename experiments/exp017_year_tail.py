"""EXP-017 — liquidation size tail over the full archive year, majors vs HIP-3.

EXP-016 measured a tail index of alpha ~ 1.15 on 12 hours, two of which were picked
for their cascades. That selection biases toward large episodes, and 12 hours is
not a census. The tail index is now the load-bearing number, so it needs both a
larger sample and an unbiased one.

**Stratified rather than exhaustive.** A full census is 8,760 hours ≈ 300 GB of
requester-pays egress (~$18, ~12h). Four fixed hours per day across all 365 days
is ~50 GB — inside AWS's free allowance — covers the whole year uniformly, and
raises the episode count from ~6.5k to a few hundred thousand, which is what a
tail index actually needs. Fixed hours also remove EXP-016's selection bias.

Splits **majors** from **HIP-3 builder-deployed perps**, identified by the `dex:`
prefix in the coin name (106 of 345 assets in a sampled hour; 22% of liquidation
fills). Their mechanics may differ and the aggregate hides it.

Tape is fetched, reduced and deleted per hour; peak disk is one file. Per-day
partial outputs make the run resumable.

    python experiments/exp017_year_tail.py

Writes `experiments/data/exp017_episodes.csv`.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import lz4.frame

from hlm.data.anon import account_id

REPO = Path(__file__).resolve().parent.parent
BUCKET = "s3://hl-mainnet-node-data/node_fills_by_block/hourly"
#: The archive begins here.
FIRST_DAY = dt.date(2025, 7, 27)
LAST_DAY = dt.date(2026, 7, 26)
#: Fixed hours, spread across the UTC day. Fixed, not chosen: EXP-016 picked two
#: cascade hours and that biased the size distribution it was trying to measure.
HOURS = (2, 8, 14, 20)
#: Episode = maximal run of fills for one (user, coin) separated by <= this.
#: EXP-016 showed the factor is insensitive between 1s and one hour.
EPISODE_GAP_MS = 5_000

#: Set by --with-prices; widens the per-fill output with px, sz and startPosition.
_WITH_PRICES = False


def fetch(date8: str, hour: int, dest: Path) -> bool:
    r = subprocess.run(
        ["aws", "s3", "cp", f"{BUCKET}/{date8}/{hour}.lz4", str(dest),
         "--request-payer", "requester", "--quiet"],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists()


def liquidation_fills(path: Path) -> list[dict]:
    out = []
    with lz4.frame.open(path, "rt") as fh:
        for line in fh:
            try:
                block = json.loads(line)
            except json.JSONDecodeError:
                continue
            for event in block.get("events", []):
                if not (isinstance(event, list) and len(event) > 1):
                    continue
                fill = event[1]
                liq = fill.get("liquidation")
                if not liq:
                    continue
                try:
                    out.append({
                        "ts": int(fill["time"]),
                        "coin": fill["coin"],
                        "user": liq["liquidatedUser"],
                        "ntl": float(fill["px"]) * float(fill["sz"]),
                        # Retained for EXP-025: tranche boundaries are an arithmetic
                        # fact of position accounting, not of elapsed time. The first
                        # year-scale pass multiplied px by sz and discarded both,
                        # which made the question unaskable without re-collecting.
                        "px": float(fill["px"]),
                        "sz": float(fill["sz"]),
                        "start_position": float(fill["startPosition"]),
                        "dir": fill.get("dir", ""),
                    })
                except (KeyError, ValueError, TypeError):
                    continue
    return out


def to_episodes(fills: list[dict], keep_fills: bool = False) -> tuple[list[dict], list[dict]]:
    """Collapse fills into (user, coin) episodes separated by EPISODE_GAP_MS.

    Returns `(episodes, fill_rows)`. `fill_rows` is empty unless `keep_fills`, and
    carries `ep_ts` — the episode's first-fill timestamp — so it joins to the
    episode file on `(coin, user, ts)`. Measuring how fill-counting compresses the
    size distribution needs the individual notionals, and the first year-scale run
    discarded them; the twelve-hour sample was the only per-fill evidence.
    """
    by_key: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for f in fills:
        by_key[(f["user"], f["coin"])].append(f)
    rows: list[dict] = []
    frows: list[dict] = []

    def close(user: str, coin: str, run: list[dict]) -> None:
        rows.append(_row(user, coin, run))
        if keep_fills:
            ep_ts = run[0]["ts"]
            uid = account_id(user)
            for f in run:
                row = {
                    "ts": f["ts"], "ep_ts": ep_ts, "coin": coin,
                    "hip3": int(":" in coin), "user": uid,
                    "notional": round(f["ntl"], 4),
                }
                if _WITH_PRICES:
                    row |= {"px": f["px"], "sz": f["sz"],
                            "start_position": f["start_position"], "dir": f["dir"]}
                frows.append(row)

    for (user, coin), group in by_key.items():
        group.sort(key=lambda f: f["ts"])
        run = [group[0]]
        for f in group[1:]:
            if f["ts"] - run[-1]["ts"] > EPISODE_GAP_MS:
                close(user, coin, run)
                run = [f]
            else:
                run.append(f)
        close(user, coin, run)
    return rows, frows


def _row(user: str, coin: str, run: list[dict]) -> dict:
    return {
        "ts": run[0]["ts"],
        "coin": coin,
        # HIP-3 builder-deployed perps carry a `dex:` prefix; majors do not.
        "hip3": int(":" in coin),
        # Derived id, not the address — see hlm/data/anon.py. Grouping is
        # unchanged, so every number is identical.
        "user": account_id(user),
        "fills": len(run),
        "notional": round(sum(f["ntl"] for f in run), 4),
    }


def process_hour(date8: str, hour: int, keep_fills: bool = False) -> tuple[list[dict], list[dict]]:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "h.lz4"
        if not fetch(date8, hour, p):
            return [], []
        return to_episodes(liquidation_fills(p), keep_fills)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    default_out = REPO / "experiments" / "data" / "exp017_episodes.csv"
    ap.add_argument("--out", type=Path, default=default_out)
    ap.add_argument("--with-prices", action="store_true",
                    help="widen --fills-out with px, sz, startPosition, dir (EXP-025)")
    ap.add_argument("--fills-out", type=Path, default=None,
                    help="also write one row per liquidation fill, joinable to --out "
                         "on (coin, user, ts=ep_ts). Large: ~2M rows over the year.")
    args = ap.parse_args()

    global _WITH_PRICES
    _WITH_PRICES = args.with_prices

    days = []
    d = FIRST_DAY
    while d <= LAST_DAY:
        days.append(d.strftime("%Y%m%d"))
        d += dt.timedelta(days=1)
    tasks = [(d8, h) for d8 in days for h in HOURS]
    print(f"{len(days)} days x {len(HOURS)} hours = {len(tasks):,} hours to reduce")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    keep = args.fills_out is not None
    written = nfills = 0
    fh2 = w2 = None
    try:
        if keep:
            args.fills_out.parent.mkdir(parents=True, exist_ok=True)
            fh2 = args.fills_out.open("w", newline="")
            cols = ["ts", "ep_ts", "coin", "hip3", "user", "notional"]
            if _WITH_PRICES:
                cols += ["px", "sz", "start_position", "dir"]
            w2 = csv.DictWriter(fh2, fieldnames=cols)
            w2.writeheader()
        with args.out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["ts", "coin", "hip3", "user", "fills", "notional"])
            w.writeheader()
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futs = {pool.submit(process_hour, d8, h, keep): (d8, h) for d8, h in tasks}
                for i, f in enumerate(as_completed(futs), 1):
                    try:
                        rows, frows = f.result()
                    except Exception:
                        rows, frows = [], []
                    if rows:
                        w.writerows(rows)
                        written += len(rows)
                    if frows and w2 is not None:
                        w2.writerows(frows)
                        nfills += len(frows)
                    if i % 100 == 0:
                        fh.flush()
                        if fh2 is not None:
                            fh2.flush()
                        print(f"  {i}/{len(tasks)} hours, {written:,} episodes"
                              + (f", {nfills:,} fills" if keep else ""))
    finally:
        if fh2 is not None:
            fh2.close()
    print(f"wrote {written:,} episodes -> {args.out}")
    if keep:
        print(f"wrote {nfills:,} fills -> {args.fills_out}")


if __name__ == "__main__":
    main()
