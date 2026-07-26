"""EXP-016 — what is "one liquidation"? Counting at every plausible unit.

EXP-015 reported that counting liquidation fills overstates liquidations 3.4x,
using (user, transaction) as the unit. That unit was chosen without argument,
and it is not obviously the right one: a large position can be force-closed
across several consecutive transactions, which is one liquidation from the
trader's side and several from the ledger's.

So rather than impose a definition, this counts at all of them:

  fills                     raw liquidation fills
  (user, tx)                one liquidation action inside one transaction
  (user, coin, episode_1s)  maximal runs separated by > 1 s
  (user, coin, episode_5s)  ... > 5 s
  (user, coin, episode_60s) ... > 60 s
  (user, coin, hour)        one trader, one asset, one hour

The inflation factor is fills / unit. Reporting the range is the honest output;
picking one and quoting 3.4x is not.

Also tests whether the factor **grows with cascade size**. If it does, the bias
is concentrated exactly on the events that get studied, which is a sharper claim
than a flat multiplier.

    python experiments/exp016_liquidation_units.py --hours 12

Writes `experiments/data/exp016_units.csv` (per-episode) and prints the summary.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import subprocess
import tempfile
from pathlib import Path

import lz4.frame
import numpy as np

REPO = Path(__file__).resolve().parent.parent
BUCKET = "s3://hl-mainnet-node-data/node_fills_by_block/hourly"

#: Hours sampled across the archive. Spread over months and over the day so the
#: factor is not measured on one regime; two are known heavy-cascade hours.
DEFAULT_HOURS = [
    ("20251015", 14), ("20251115", 3), ("20251215", 20), ("20260115", 9),
    ("20260215", 16), ("20260315", 7), ("20260415", 22), ("20260515", 11),
    ("20260615", 5), ("20260715", 18), ("20260720", 15), ("20260724", 13),
]


def fetch_hour(date8: str, hour: int, dest: Path) -> bool:
    """Requester-pays download of one hour of node fills."""
    r = subprocess.run(
        ["aws", "s3", "cp", f"{BUCKET}/{date8}/{hour}.lz4", str(dest),
         "--request-payer", "requester", "--quiet"],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists()


def liquidation_fills(path: Path) -> list[dict]:
    """Every fill carrying a `liquidation` object, flattened."""
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
                        "tx": fill["hash"],
                        "ntl": float(fill["px"]) * float(fill["sz"]),
                        "method": liq.get("method", "?"),
                    })
                except (KeyError, ValueError, TypeError):
                    continue
    return out


def episodes(fills: list[dict], gap_ms: int) -> list[list[dict]]:
    """Maximal runs per (user, coin) separated by more than `gap_ms`."""
    by_key: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for f in fills:
        by_key[(f["user"], f["coin"])].append(f)
    out = []
    for group in by_key.values():
        group.sort(key=lambda f: f["ts"])
        run = [group[0]]
        for f in group[1:]:
            if f["ts"] - run[-1]["ts"] > gap_ms:
                out.append(run)
                run = [f]
            else:
                run.append(f)
        out.append(run)
    return out


def summarise(fills: list[dict]) -> dict:
    n = len(fills)
    units = {
        "fills": n,
        "(user, tx)": len({(f["user"], f["tx"]) for f in fills}),
        "episode_1s": len(episodes(fills, 1_000)),
        "episode_5s": len(episodes(fills, 5_000)),
        "episode_60s": len(episodes(fills, 60_000)),
        "(user, coin, hour)": len({(f["user"], f["coin"], f["ts"] // 3_600_000) for f in fills}),
    }
    return units


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours", type=int, default=len(DEFAULT_HOURS))
    ap.add_argument("--out", type=Path, default=REPO / "experiments" / "data" / "exp016_units.csv")
    args = ap.parse_args()

    all_fills: list[dict] = []
    for date8, hour in DEFAULT_HOURS[: args.hours]:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "h.lz4"
            if not fetch_hour(date8, hour, p):
                print(f"  {date8} h{hour}: absent")
                continue
            f = liquidation_fills(p)
            all_fills += f
            print(f"  {date8} h{hour}: {len(f):>6,} liquidation fills")

    if not all_fills:
        raise SystemExit("no liquidation fills collected")

    units = summarise(all_fills)
    n = units["fills"]
    print(f"\n{n:,} liquidation fills across {args.hours} hours\n")
    print(f"{'unit':<22}{'count':>10}{'inflation':>12}")
    print("-" * 44)
    for k, v in units.items():
        print(f"{k:<22}{v:>10,}{n / v:>11.1f}x")

    # Does tranching grow with size? One row per 5s episode.
    eps = episodes(all_fills, 5_000)
    rows = [
        {
            "ts": min(f["ts"] for f in e),
            "coin": e[0]["coin"],
            "user": e[0]["user"],
            "fills": len(e),
            "notional": round(sum(f["ntl"] for f in e), 2),
            "txs": len({f["tx"] for f in e}),
        }
        for e in eps
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    ntl = np.array([r["notional"] for r in rows])
    fl = np.array([r["fills"] for r in rows], dtype=float)
    keep = ntl > 0
    print(f"\ncorr( ln(notional), ln(fills per episode) ) = "
          f"{np.corrcoef(np.log(ntl[keep]), np.log(fl[keep]))[0, 1]:+.3f}   n={keep.sum():,}")
    print("\nfills per 5s episode, by episode size:")
    qs = np.quantile(ntl[keep], [0, 0.5, 0.9, 0.99, 1.0])
    for lo, hi, lbl in zip(qs[:-1], qs[1:], ["p0-50", "p50-90", "p90-99", "p99-100"], strict=False):
        m = keep & (ntl >= lo) & (ntl < hi if hi < qs[-1] else ntl <= hi)
        if m.sum():
            print(f"  {lbl:<9} notional {lo:>12,.0f} - {hi:>12,.0f}  "
                  f"n={m.sum():>6,}  median fills {np.median(fl[m]):>5.0f}  mean {fl[m].mean():>6.1f}")
    print(f"\nwrote {len(rows):,} episodes -> {args.out}")


if __name__ == "__main__":
    main()
