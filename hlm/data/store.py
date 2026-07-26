"""Buffered Parquet storage, partitioned by dataset and UTC date.

Schemas are declared explicitly rather than inferred. Inference would let a
column's type drift between files whenever a batch happened to hold only nulls
or only integers, and DuckDB then fails to read the dataset as a whole — a
failure that surfaces weeks later, once the data is expensive to re-collect.

`trade` keeps an untyped `extra` column holding any field the API returns that
the schema does not name. Liquidation markers are the reason: track O2 depends
on them, and their exact shape is confirmed empirically, so nothing observed
should be silently dropped in the meantime.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(os.environ.get("QFR_DATA_DIR", "./data"))

_TS = pa.timestamp("ms", tz="UTC")

SCHEMAS: dict[str, pa.Schema] = {
    # Per-asset context: the primary substrate for tracks O1 and O3.
    #
    # `time` is *receipt* time: the activeAssetCtx feed carries no timestamp of
    # its own. `impact_bid`/`impact_ask` come from `impactPxs` and are what the
    # funding premium is actually computed from, so O3 needs them recorded
    # rather than reconstructed from the book afterwards.
    "asset_ctx": pa.schema(
        [
            ("time", _TS),
            ("coin", pa.string()),
            ("funding", pa.float64()),
            ("open_interest", pa.float64()),
            ("mark_px", pa.float64()),
            ("oracle_px", pa.float64()),
            ("mid_px", pa.float64()),
            ("prev_day_px", pa.float64()),
            ("day_ntl_vlm", pa.float64()),
            ("day_base_vlm", pa.float64()),
            ("premium", pa.float64()),
            ("impact_bid", pa.float64()),
            ("impact_ask", pa.float64()),
        ]
    ),
    # Public trade prints. Raw material for O2 (liquidation cascades).
    #
    # The public feed carries NO liquidation flag — only `users`, the two
    # counterparties. Labelling liquidations is therefore a downstream
    # derivation (see `hlm/problems/liquidation_tail.py`), which is why both
    # counterparties and `extra` are preserved verbatim here: the label can be
    # revised later, but unrecorded fields are gone for good.
    "trade": pa.schema(
        [
            ("time", _TS),
            ("coin", pa.string()),
            ("side", pa.string()),  # "A" = aggressor sold, "B" = aggressor bought
            ("px", pa.float64()),
            ("sz", pa.float64()),
            ("hash", pa.string()),
            ("tid", pa.int64()),
            ("users", pa.list_(pa.string())),
            ("extra", pa.string()),  # JSON: any field not named above
        ]
    ),
    "bbo": pa.schema(
        [
            ("time", _TS),
            ("coin", pa.string()),
            ("bid_px", pa.float64()),
            ("bid_sz", pa.float64()),
            ("bid_n", pa.int32()),
            ("ask_px", pa.float64()),
            ("ask_sz", pa.float64()),
            ("ask_n", pa.int32()),
        ]
    ),
    # Long format: one row per book level. Flexible for DuckDB and compresses
    # well, at the cost of row count — hence book capture is limited to a
    # focus subset of coins in the recorder.
    "book": pa.schema(
        [
            ("time", _TS),
            ("coin", pa.string()),
            ("side", pa.string()),  # "bid" | "ask"
            ("level", pa.int32()),
            ("px", pa.float64()),
            ("sz", pa.float64()),
            ("n", pa.int32()),
        ]
    ),
    # Settled hourly funding, polled from fundingHistory. Ground truth used to
    # cross-check the streamed asset_ctx premium.
    "funding": pa.schema(
        [
            ("time", _TS),
            ("coin", pa.string()),
            ("funding_rate", pa.float64()),
            ("premium", pa.float64()),
        ]
    ),
}


def utc_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d")


def _coerce(value: Any, field: pa.Field) -> Any:
    """Best-effort cast of an API value to the declared column type.

    The API returns numbers as strings throughout, so this is the normal path,
    not an error path. Unparseable values become null rather than killing the
    whole batch: losing one field beats losing a buffer of live market data.
    """
    if value is None:
        return None
    t = field.type
    try:
        if pa.types.is_floating(t):
            return float(value)
        if pa.types.is_integer(t):
            return int(value)
        if pa.types.is_timestamp(t):
            return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
        if pa.types.is_string(t):
            return value if isinstance(value, str) else json.dumps(value)
        if pa.types.is_list(t):
            return [str(v) for v in value] if isinstance(value, (list, tuple)) else None
    except (TypeError, ValueError):
        return None
    return value


class ParquetWriter:
    """Accumulates rows in memory and flushes them to date-partitioned Parquet.

    Flushing is triggered by row count or elapsed time, whichever comes first,
    so a quiet asset still lands on disk instead of sitting in RAM until the
    process dies.
    """

    def __init__(
        self,
        dataset: str,
        *,
        root: Path | str = DEFAULT_DATA_DIR,
        flush_rows: int = 20_000,
        flush_seconds: float = 300.0,
        compression: str = "zstd",
    ) -> None:
        if dataset not in SCHEMAS:
            raise KeyError(f"unknown dataset {dataset!r}; known: {sorted(SCHEMAS)}")
        self.dataset = dataset
        self.schema = SCHEMAS[dataset]
        self.root = Path(root)
        self.flush_rows = flush_rows
        self.flush_seconds = flush_seconds
        self.compression = compression
        self._buffer: list[dict[str, Any]] = []
        self._last_flush = time.monotonic()
        self._seq = 0
        self.rows_written = 0

    def append(self, row: dict[str, Any]) -> None:
        self._buffer.append(row)
        if self.should_flush():
            self.flush()

    def extend(self, rows: list[dict[str, Any]]) -> None:
        self._buffer.extend(rows)
        if self.should_flush():
            self.flush()

    def should_flush(self) -> bool:
        if not self._buffer:
            return False
        return (
            len(self._buffer) >= self.flush_rows
            or time.monotonic() - self._last_flush >= self.flush_seconds
        )

    def flush(self) -> int:
        """Write buffered rows, one file per UTC date. Returns rows written."""
        if not self._buffer:
            return 0

        buffered, self._buffer = self._buffer, []
        self._last_flush = time.monotonic()

        by_date: dict[str, list[dict[str, Any]]] = {}
        for row in buffered:
            raw_time = row.get("time")
            stamp = int(raw_time) if raw_time is not None else int(time.time() * 1000)
            by_date.setdefault(utc_date(stamp), []).append(row)

        written = 0
        for date, rows in by_date.items():
            directory = self.root / self.dataset / f"date={date}"
            directory.mkdir(parents=True, exist_ok=True)
            columns = {
                field.name: [_coerce(row.get(field.name), field) for row in rows]
                for field in self.schema
            }
            table = pa.Table.from_pydict(columns, schema=self.schema)
            path = directory / f"part-{int(time.time() * 1000)}-{self._seq:05d}.parquet"
            pq.write_table(table, path, compression=self.compression)
            self._seq += 1
            written += len(rows)

        self.rows_written += written
        logger.debug("%s: flushed %d rows", self.dataset, written)
        return written

    def close(self) -> None:
        self.flush()


class Store:
    """Read side. Thin DuckDB wrapper over the Parquet tree."""

    def __init__(self, root: Path | str = DEFAULT_DATA_DIR) -> None:
        self.root = Path(root)
        self.con = duckdb.connect()

    def path_glob(self, dataset: str) -> str:
        return str(self.root / dataset / "**" / "*.parquet")

    def available(self) -> dict[str, int]:
        """File count per dataset present on disk."""
        return {
            dataset: len(list((self.root / dataset).rglob("*.parquet")))
            for dataset in SCHEMAS
            if (self.root / dataset).exists()
        }

    def sql(self, query: str) -> duckdb.DuckDBPyRelation:
        """Run SQL. Use `hive_partitioning` so `date` is queryable as a column."""
        return self.con.sql(query)

    def scan(self, dataset: str) -> duckdb.DuckDBPyRelation:
        glob = self.path_glob(dataset)
        return self.con.sql(
            f"SELECT * FROM read_parquet('{glob}', hive_partitioning = true)"
        )

    def close(self) -> None:
        self.con.close()
