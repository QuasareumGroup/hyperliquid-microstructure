"""Streaming reader for the Hyperliquid `asset_ctxs` S3 archive.

`s3://hyperliquid-archive/asset_ctxs/{YYYYMMDD}.csv.lz4` holds the **whole perp
universe at minute grain** back to 2023-05-20 — funding, premium, open interest,
oracle/mark/mid, and both impact prices. That is ~376M rows and 8.7 GB
compressed across 1,137 days.

Nothing is written to disk in raw form. Each day is streamed straight from S3
through the lz4 decoder, folded to (coin, hour) aggregates, and discarded; peak
footprint is one in-flight day. The machine this targets runs near-full, and a
naive `aws s3 sync` of the archive would not fit on it at all.

The fold is chosen so the funding controller can be validated exactly: the
protocol averages the premium over the hour (sampled every 5s), so an hourly
mean is the correct granularity to compare against the published rate. See
`experiments/FINDING-001-funding-deadband.md`.

Requester-pays: the caller's AWS credentials are billed for transfer. At ~8.7 GB
for the full archive this sits inside AWS's 100 GB/month free egress allowance.

Usage:
    python -m qfr.data.archive --list
    python -m qfr.data.archive --all --out data/ctx_hourly
    python -m qfr.data.archive --days 20260601 20260602
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import re
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import lz4.frame
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

BUCKET = "hyperliquid-archive"
PREFIX = "asset_ctxs"
#: The archive begins here; earlier dates are doomed requester-pays 404s.
ARCHIVE_FLOOR = "20230501"

#: Funding controller constants (Hyperliquid docs, "Funding").
INTEREST_8H = 0.0001
CLAMP = 0.0005

#: Columns read from the CSV. Resolved by header name, never by position —
#: position-based access would break silently if the schema ever reorders.
_NUMERIC = (
    "funding",
    "open_interest",
    "prev_day_px",
    "day_ntl_vlm",
    "premium",
    "oracle_px",
    "mark_px",
    "mid_px",
    "impact_bid_px",
    "impact_ask_px",
)

HOURLY_SCHEMA = pa.schema(
    [
        ("date", pa.string()),
        ("hour", pa.int8()),
        ("coin", pa.string()),
        ("n", pa.int16()),  # minute samples folded into this hour
        ("funding", pa.float64()),  # published hourly rate (mode over the hour)
        ("funding_varies", pa.bool_()),  # True if the rate changed mid-hour
        ("premium_mean", pa.float64()),  # the quantity the controller uses
        ("premium_min", pa.float64()),
        ("premium_max", pa.float64()),
        ("open_interest", pa.float64()),
        ("mark_px", pa.float64()),
        ("oracle_px", pa.float64()),
        ("mid_px", pa.float64()),
        ("impact_bid_px", pa.float64()),
        ("impact_ask_px", pa.float64()),
        ("day_ntl_vlm", pa.float64()),
        # Derived, so downstream analysis need not re-derive them inconsistently.
        ("funding_model", pa.float64()),  # controller applied to premium_mean
        ("model_exact", pa.bool_()),  # |model − published| < 1e-9
        ("regime", pa.string()),  # deadband | responsive_high | responsive_low
    ]
)


def model_funding_hourly(premium: float) -> float:
    """Documented controller: F_8h = P + clamp(interest − P, ±0.0005), paid /8."""
    return (premium + max(min(INTEREST_8H - premium, CLAMP), -CLAMP)) / 8.0


def regime_of(premium: float) -> str:
    """Which branch of the clamp the hour sits in.

    `deadband` is where the clamp argument stays inside its bounds — the two
    premium terms then cancel and funding equals the interest constant exactly,
    regardless of the premium. That is the counterintuitive case: the clamp
    being *inactive* is what makes the controller insensitive.
    """
    if abs(INTEREST_8H - premium) <= CLAMP:
        return "deadband"
    return "responsive_high" if premium > INTEREST_8H + CLAMP else "responsive_low"


@dataclass
class DayResult:
    date: str
    rows: list[dict]
    minute_rows: int
    skipped: int


def list_days() -> list[str]:
    """Every `YYYYMMDD` present in the archive, ascending."""
    out = subprocess.run(
        ["aws", "s3", "ls", f"s3://{BUCKET}/{PREFIX}/", "--request-payer", "requester"],
        capture_output=True,
        text=True,
        check=True,
    )
    days = re.findall(r"(\d{8})\.csv\.lz4", out.stdout)
    return sorted(set(days))


def _stream_day(date: str) -> bytes:
    """Fetch one day to memory. Raises CalledProcessError on 404 or auth failure."""
    result = subprocess.run(
        [
            "aws", "s3", "cp",
            f"s3://{BUCKET}/{PREFIX}/{date}.csv.lz4", "-",
            "--request-payer", "requester",
        ],
        capture_output=True,
        check=True,
    )
    return result.stdout


def fold_day(date: str, blob: bytes | None = None) -> DayResult:
    """Stream one archive day into (coin, hour) aggregates."""
    raw = blob if blob is not None else _stream_day(date)

    # `funding_counts` is deliberately not named `funding`: _NUMERIC contains
    # "funding", and a same-named key would be overwritten by the list
    # comprehension below, turning the counter into a list.
    acc: dict[tuple[str, int], dict] = defaultdict(
        lambda: {**{c: [] for c in _NUMERIC}, "funding_counts": defaultdict(int)}
    )
    minute_rows = 0
    skipped = 0

    with lz4.frame.open(io.BytesIO(raw), "rt") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                hour = int(row["time"][11:13])
                coin = row["coin"]
                values = {c: float(row[c]) for c in _NUMERIC}
            except (KeyError, ValueError, TypeError, IndexError):
                skipped += 1
                continue
            minute_rows += 1
            bucket = acc[(coin, hour)]
            for column, value in values.items():
                bucket[column].append(value)
            bucket["funding_counts"][round(values["funding"], 15)] += 1

    rows = []
    for (coin, hour), bucket in acc.items():
        premiums = bucket["premium"]
        if not premiums:
            continue
        premium_mean = fmean(premiums)
        funding_counts = bucket["funding_counts"]
        published = max(funding_counts, key=funding_counts.get)
        modelled = model_funding_hourly(premium_mean)
        rows.append(
            {
                "date": date,
                "hour": hour,
                "coin": coin,
                "n": len(premiums),
                "funding": published,
                "funding_varies": len(funding_counts) > 1,
                "premium_mean": premium_mean,
                "premium_min": min(premiums),
                "premium_max": max(premiums),
                "open_interest": fmean(bucket["open_interest"]),
                "mark_px": fmean(bucket["mark_px"]),
                "oracle_px": fmean(bucket["oracle_px"]),
                "mid_px": fmean(bucket["mid_px"]),
                "impact_bid_px": fmean(bucket["impact_bid_px"]),
                "impact_ask_px": fmean(bucket["impact_ask_px"]),
                "day_ntl_vlm": bucket["day_ntl_vlm"][-1],
                "funding_model": modelled,
                "model_exact": abs(modelled - published) < 1e-9,
                "regime": regime_of(premium_mean),
            }
        )
    return DayResult(date=date, rows=rows, minute_rows=minute_rows, skipped=skipped)


def write_day(result: DayResult, out_dir: Path) -> Path:
    """One Parquet file per archive day, so a failed run resumes by skipping."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.date}.parquet"
    columns = {
        field.name: [row.get(field.name) for row in result.rows] for field in HOURLY_SCHEMA
    }
    pq.write_table(
        pa.Table.from_pydict(columns, schema=HOURLY_SCHEMA), path, compression="zstd"
    )
    return path


def build(days: list[str], out_dir: Path, workers: int = 6, resume: bool = True) -> dict:
    """Fold `days` into `out_dir`, one Parquet per day. Returns a run summary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pending = [d for d in days if not (resume and (out_dir / f"{d}.parquet").exists())]
    logger.info(
        "%d day(s) requested, %d already present, %d to fetch",
        len(days),
        len(days) - len(pending),
        len(pending),
    )

    done = failed = total_rows = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fold_day, day): day for day in pending}
        for future in as_completed(futures):
            day = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                failed += 1
                logger.warning("%s failed: %s", day, exc)
                continue
            write_day(result, out_dir)
            done += 1
            total_rows += len(result.rows)
            if done % 25 == 0:
                logger.info("%d/%d folded (%d asset-hours)", done, len(pending), total_rows)

    return {"folded": done, "failed": failed, "asset_hours": total_rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list archive days and exit")
    parser.add_argument("--all", action="store_true", help="fold the entire archive")
    parser.add_argument("--days", nargs="*", default=[], help="specific YYYYMMDD days")
    parser.add_argument("--out", type=Path, default=Path("data/ctx_hourly"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.list:
        days = list_days()
        print(f"{len(days)} days: {days[0]} -> {days[-1]}")
        return

    days = list_days() if args.all else args.days
    if not days:
        parser.error("pass --all or --days YYYYMMDD [...]")

    summary = build(days, args.out, workers=args.workers)
    logger.info(
        "done: %d folded, %d failed, %d asset-hours -> %s",
        summary["folded"],
        summary["failed"],
        summary["asset_hours"],
        args.out,
    )


if __name__ == "__main__":
    main()
