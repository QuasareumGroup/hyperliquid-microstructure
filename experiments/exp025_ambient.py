"""EXP-025 ambient pass — a trade price series for the instruments and hours that
contain a multi-tranche forced close.

The reversion test of EXP-025 §8 needs the price of an instrument *after* a forced
close has finished, which liquidation fills alone cannot give: once the close ends
there are no more liquidation fills to read a price from. This pass keeps **all**
fills, not only liquidations, for the instruments and hours involved, and reduces
them to one last-trade price per second — enough resolution for a 30-second
question and small enough to version.

    python experiments/exp025_ambient.py --hours <file> --coins <file> --out <path>

`--hours` is one `YYYYMMDD-H` per line, `--coins` one instrument per line.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import lz4.frame

BUCKET = "s3://hl-mainnet-node-data/node_fills_by_block/hourly"


def fetch(date8: str, hour: int, dest: Path) -> bool:
    r = subprocess.run(
        ["aws", "s3", "cp", f"{BUCKET}/{date8}/{hour}.lz4", str(dest),
         "--request-payer", "requester", "--quiet"],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists()


def prices(path: Path, coins: set[str]) -> dict[tuple[str, int], float]:
    """Last trade price per (coin, second). Both sides of a trade carry the same
    price, so no de-duplication is needed here — unlike the liquidation counting,
    where taking both sides doubled the count."""
    out: dict[tuple[str, int], float] = {}
    with lz4.frame.open(path, "rt") as fh:
        for line in fh:
            try:
                block = json.loads(line)
            except json.JSONDecodeError:
                continue
            for event in block.get("events", []):
                if not (isinstance(event, list) and len(event) > 1):
                    continue
                f = event[1]
                c = f.get("coin")
                if c not in coins:
                    continue
                try:
                    out[(c, int(f["time"]) // 1000)] = float(f["px"])
                except (KeyError, ValueError, TypeError):
                    continue
    return out


def process(spec: str, coins: set[str]) -> list[tuple[str, int, float]]:
    date8, h = spec.split("-")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "h.lz4"
        if not fetch(date8, int(h), p):
            return []
        return [(c, s, px) for (c, s), px in prices(p, coins).items()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours", type=Path, required=True)
    ap.add_argument("--coins", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    hours = [l.strip() for l in args.hours.read_text().split("\n") if l.strip()]
    coins = {l.strip() for l in args.coins.read_text().split("\n") if l.strip()}
    print(f"{len(hours):,} hours x {len(coins)} instruments")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["coin", "sec", "px"])
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = [pool.submit(process, s, coins) for s in hours]
            for i, fut in enumerate(as_completed(futs), 1):
                try:
                    rows = fut.result()
                except Exception:
                    rows = []
                if rows:
                    w.writerows(rows)
                    written += len(rows)
                if i % 50 == 0:
                    fh.flush()
                    print(f"  {i}/{len(hours)} hours, {written:,} price points")
    print(f"wrote {written:,} price points -> {args.out}")


if __name__ == "__main__":
    main()
