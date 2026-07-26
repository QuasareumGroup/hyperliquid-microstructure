"""Continuous recorder for public Hyperliquid mainnet data.

Read-only, no credentials, no risk.

**Scope is deliberately narrow.** `perplog-recorder` (see `~/perplog`) already
records trades and L2 book 24/7 across HL, Binance, OKX and Bybit into R2, with
gap sidecars and a cost-tuned write strategy. Duplicating that here would be
waste, and worse data: cross-venue coverage is what makes liquidation-cascade
contagion observable at all for track O2.

What `perplog-recorder` does *not* subscribe to is `activeAssetCtx` — so funding,
premium, impact prices and open interest are captured nowhere. That stream is
precisely what tracks O1 and O3 need, and it is the only reason this recorder
exists. Default capture is therefore:

  asset_ctx  all assets   funding, premium, OI, impact prices  -> O1, O3
  funding    all assets   settled hourly rates, ground truth   -> O1, O3

Trades and book capture remain available behind `--full` for a standalone run
with no perplog dependency, but that is not the intended mode.

Historical depth comes from S3 rather than from waiting: `market_data/…/l2Book`
and `asset_ctxs` are documented, and `misc_events_by_block` carries historical
funding events. `perplog/rust/crates/archive` already implements the SigV4
signing and lz4 decoding for those.

Usage:
    python -m qfr.data.recorder --status
    python -m qfr.data.recorder            # funding/context only (default)
    python -m qfr.data.recorder --full     # add trades and book
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import shutil
import signal
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import websockets

from qfr.data.hl_client import InfoClient
from qfr.data.store import DEFAULT_DATA_DIR, ParquetWriter, Store

logger = logging.getLogger("qfr.recorder")

#: Hyperliquid closes idle sockets; the docs' reference client pings well
#: inside that window.
PING_INTERVAL = 30.0

#: Fields of a trade already named in the `trade` schema. Anything else the API
#: starts returning is preserved as JSON in `extra` rather than dropped.
_KNOWN_TRADE_FIELDS = frozenset({"coin", "side", "px", "sz", "time", "hash", "tid", "users"})


@dataclass
class RecorderConfig:
    """What to capture, and how much of it.

    Throttles exist because disk, not bandwidth, is the binding constraint.
    Unthrottled, `activeAssetCtx` alone emits ~130 rows/s across the full perp
    universe (~11M rows/day), and the whole capture set runs to roughly
    330 MB/day — enough to fill a nearly-full disk within weeks.

    The defaults below are chosen from what each research track actually needs,
    not from what the feed can deliver:
      - funding settles hourly, so 60s context sampling is already generous
        for O1;
      - the protocol samples its own funding premium every 5s, so focus assets
        are sampled at 5s for O3 and nothing is gained by going faster.
    """

    #: Assets tracked for funding/OI context. Empty means "every listed perp".
    ctx_coins: list[str] = field(default_factory=list)
    #: Capture trades and book too. Off by default: perplog-recorder already
    #: covers both, multi-venue, and duplicating it costs ~55 MB/day for a
    #: strictly worse dataset.
    full_capture: bool = False
    #: Assets whose public trades are recorded, ranked by 24h notional.
    #: Only used when `full_capture` is set.
    n_trade_coins: int = 20
    #: Assets with top-of-book and depth capture. Only used with `full_capture`.
    focus_coins: list[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL", "HYPE"])

    root: Path = DEFAULT_DATA_DIR
    #: Minimum seconds between stored context rows, per asset.
    ctx_throttle_seconds: float = 60.0
    #: Same, for focus assets — matches the protocol's own 5s premium sampling.
    ctx_focus_throttle_seconds: float = 5.0
    #: Minimum seconds between stored depth snapshots, per asset.
    book_throttle_seconds: float = 10.0
    #: Book levels kept per side.
    book_depth: int = 10
    #: Minimum seconds between stored top-of-book rows, per asset.
    bbo_throttle_seconds: float = 1.0
    #: How often settled funding is polled as ground truth.
    funding_poll_seconds: float = 3600.0
    #: Subscriptions per websocket connection (protocol cap is 1000).
    subs_per_connection: int = 180
    #: How often a progress line is logged.
    status_seconds: float = 300.0
    #: Stop recording if free disk falls below this. The machine this targets
    #: runs close to full; silently consuming the last gigabytes would be worse
    #: than losing capture.
    min_free_gb: float = 5.0


class Recorder:
    def __init__(self, config: RecorderConfig | None = None) -> None:
        self.config = config or RecorderConfig()
        self.client = InfoClient()
        self.writers = {
            name: ParquetWriter(name, root=self.config.root)
            for name in ("asset_ctx", "trade", "bbo", "book", "funding")
        }
        self._stop = asyncio.Event()
        self._focus = set(self.config.focus_coins)
        # Per-dataset, per-asset time of last stored row, for throttling.
        self._last_write: dict[str, dict[str, float]] = {
            "asset_ctx": {},
            "bbo": {},
            "book": {},
        }
        self._counts: dict[str, int] = dict.fromkeys(self.writers, 0)
        self._dropped: dict[str, int] = dict.fromkeys(self.writers, 0)
        self._started = time.monotonic()

    def _throttled(self, dataset: str, coin: str, interval: float) -> bool:
        """True if `coin` was stored for `dataset` too recently to store again."""
        now = time.monotonic()
        last = self._last_write[dataset]
        if now - last.get(coin, 0.0) < interval:
            self._dropped[dataset] += 1
            return True
        last[coin] = now
        return False

    # --- message handling ------------------------------------------------

    def _on_trades(self, data: list[dict[str, Any]]) -> None:
        rows = []
        for trade in data:
            extra = {k: v for k, v in trade.items() if k not in _KNOWN_TRADE_FIELDS}
            rows.append(
                {
                    "time": trade.get("time"),
                    "coin": trade.get("coin"),
                    "side": trade.get("side"),
                    "px": trade.get("px"),
                    "sz": trade.get("sz"),
                    "hash": trade.get("hash"),
                    "tid": trade.get("tid"),
                    "users": trade.get("users"),
                    "extra": json.dumps(extra) if extra else None,
                }
            )
        self.writers["trade"].extend(rows)
        self._counts["trade"] += len(rows)

    def _on_active_asset_ctx(self, data: dict[str, Any]) -> None:
        coin = data.get("coin")
        interval = (
            self.config.ctx_focus_throttle_seconds
            if coin in self._focus
            else self.config.ctx_throttle_seconds
        )
        if self._throttled("asset_ctx", coin, interval):
            return

        ctx = data.get("ctx") or {}
        impact = ctx.get("impactPxs") or [None, None]
        self.writers["asset_ctx"].append(
            {
                # activeAssetCtx carries no timestamp; stamp on receipt.
                "time": int(time.time() * 1000),
                "coin": coin,
                "funding": ctx.get("funding"),
                "open_interest": ctx.get("openInterest"),
                "mark_px": ctx.get("markPx"),
                "oracle_px": ctx.get("oraclePx"),
                "mid_px": ctx.get("midPx"),
                "prev_day_px": ctx.get("prevDayPx"),
                "day_ntl_vlm": ctx.get("dayNtlVlm"),
                "day_base_vlm": ctx.get("dayBaseVlm"),
                "premium": ctx.get("premium"),
                "impact_bid": impact[0] if len(impact) > 0 else None,
                "impact_ask": impact[1] if len(impact) > 1 else None,
            }
        )
        self._counts["asset_ctx"] += 1

    def _on_bbo(self, data: dict[str, Any]) -> None:
        coin = data.get("coin")
        if self._throttled("bbo", coin, self.config.bbo_throttle_seconds):
            return

        levels = data.get("bbo") or [None, None]
        bid = levels[0] if len(levels) > 0 else None
        ask = levels[1] if len(levels) > 1 else None
        self.writers["bbo"].append(
            {
                "time": data.get("time"),
                "coin": coin,
                "bid_px": (bid or {}).get("px"),
                "bid_sz": (bid or {}).get("sz"),
                "bid_n": (bid or {}).get("n"),
                "ask_px": (ask or {}).get("px"),
                "ask_sz": (ask or {}).get("sz"),
                "ask_n": (ask or {}).get("n"),
            }
        )
        self._counts["bbo"] += 1

    def _on_book(self, data: dict[str, Any]) -> None:
        coin = data.get("coin")
        if self._throttled("book", coin, self.config.book_throttle_seconds):
            return

        timestamp = data.get("time")
        levels = data.get("levels") or [[], []]
        rows = []
        for side_name, side_levels in (("bid", levels[0]), ("ask", levels[1])):
            for index, level in enumerate(side_levels[: self.config.book_depth]):
                rows.append(
                    {
                        "time": timestamp,
                        "coin": coin,
                        "side": side_name,
                        "level": index,
                        "px": level.get("px"),
                        "sz": level.get("sz"),
                        "n": level.get("n"),
                    }
                )
        self.writers["book"].extend(rows)
        self._counts["book"] += len(rows)

    def _dispatch(self, message: dict[str, Any]) -> None:
        channel = message.get("channel")
        data = message.get("data")
        if channel == "trades":
            self._on_trades(data)
        elif channel == "activeAssetCtx":
            self._on_active_asset_ctx(data)
        elif channel == "bbo":
            self._on_bbo(data)
        elif channel == "l2Book":
            self._on_book(data)
        elif channel in ("subscriptionResponse", "pong", "error"):
            if channel == "error":
                logger.warning("ws error frame: %s", data)
        else:
            logger.debug("unhandled channel %s", channel)

    # --- websocket ---------------------------------------------------------

    async def _ws_worker(self, name: str, subscriptions: list[dict[str, Any]]) -> None:
        """One connection. Reconnects with backoff and resubscribes."""
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    self.client.ws_url, ping_interval=None, max_queue=4096
                ) as ws:
                    for subscription in subscriptions:
                        await ws.send(
                            json.dumps({"method": "subscribe", "subscription": subscription})
                        )
                    logger.info("[%s] connected, %d subscriptions", name, len(subscriptions))
                    backoff = 1.0

                    async def ping() -> None:
                        while True:
                            await asyncio.sleep(PING_INTERVAL)
                            await ws.send(json.dumps({"method": "ping"}))

                    ping_task = asyncio.create_task(ping())
                    try:
                        while not self._stop.is_set():
                            raw = await ws.recv()
                            try:
                                self._dispatch(json.loads(raw))
                            except Exception:
                                logger.exception("[%s] dispatch failed", name)
                    finally:
                        ping_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await ping_task
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._stop.is_set():
                    return
                logger.warning("[%s] disconnected (%s) — reconnecting in %.0fs", name, exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    # --- REST polling ------------------------------------------------------

    async def _funding_poller(self, coins: list[str]) -> None:
        """Settled hourly funding, the ground truth for streamed premiums."""
        # First pass reaches back a day so a fresh install is not empty.
        lookback_ms = 24 * 3600 * 1000
        while not self._stop.is_set():
            start = int(time.time() * 1000) - lookback_ms
            for coin in coins:
                if self._stop.is_set():
                    return
                try:
                    history = await self.client.funding_history(coin, start)
                except Exception:
                    logger.exception("fundingHistory failed for %s", coin)
                    continue
                rows = [
                    {
                        "time": entry.get("time"),
                        "coin": entry.get("coin", coin),
                        "funding_rate": entry.get("fundingRate"),
                        "premium": entry.get("premium"),
                    }
                    for entry in history
                ]
                if rows:
                    self.writers["funding"].extend(rows)
                    self._counts["funding"] += len(rows)

            lookback_ms = int(self.config.funding_poll_seconds * 1000) + 3600 * 1000
            await self._sleep_or_stop(self.config.funding_poll_seconds)

    async def _flusher(self) -> None:
        """Time-based flush so quiet datasets still reach disk."""
        while not self._stop.is_set():
            await self._sleep_or_stop(30.0)
            for writer in self.writers.values():
                if writer.should_flush():
                    writer.flush()

    def _free_gb(self) -> float:
        usage = shutil.disk_usage(self.config.root if self.config.root.exists() else Path.cwd())
        return usage.free / 1024**3

    def _stored_mb(self) -> float:
        if not self.config.root.exists():
            return 0.0
        return sum(p.stat().st_size for p in self.config.root.rglob("*.parquet")) / 1024**2

    async def _status(self) -> None:
        while not self._stop.is_set():
            await self._sleep_or_stop(self.config.status_seconds)
            if self._stop.is_set():
                return

            uptime_hours = (time.monotonic() - self._started) / 3600
            summary = "  ".join(f"{name}={count:,}" for name, count in self._counts.items())
            stored = self._stored_mb()
            free = self._free_gb()
            rate = stored / uptime_hours * 24 if uptime_hours > 0 else 0.0
            logger.info(
                "uptime %.1fh | %s | on disk %.1f MB (~%.0f MB/day) | free %.1f GB",
                uptime_hours,
                summary,
                stored,
                rate,
                free,
            )

            if free < self.config.min_free_gb:
                logger.error(
                    "free disk %.1f GB is below the %.1f GB floor — stopping the recorder "
                    "so it cannot consume the remainder. Free space or move QFR_DATA_DIR "
                    "to another volume, then restart.",
                    free,
                    self.config.min_free_gb,
                )
                self.request_stop()

    async def _sleep_or_stop(self, seconds: float) -> None:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)

    # --- orchestration -----------------------------------------------------

    def _build_subscriptions(self, ctx_coins: list[str], trade_coins: list[str]) -> list[dict]:
        subscriptions: list[dict[str, Any]] = [
            {"type": "activeAssetCtx", "coin": c} for c in ctx_coins
        ]
        if self.config.full_capture:
            subscriptions += [{"type": "trades", "coin": c} for c in trade_coins]
            subscriptions += [{"type": "bbo", "coin": c} for c in self.config.focus_coins]
            subscriptions += [{"type": "l2Book", "coin": c} for c in self.config.focus_coins]
        return subscriptions

    async def run(self) -> None:
        free = self._free_gb()
        if free < self.config.min_free_gb:
            raise RuntimeError(
                f"only {free:.1f} GB free, below the {self.config.min_free_gb:.1f} GB floor. "
                "Free space, lower --min-free-gb, or point --data-dir at another volume."
            )

        universe = await self.client.perp_universe()
        ctx_coins = self.config.ctx_coins or universe
        trade_coins = universe[: self.config.n_trade_coins]

        subscriptions = self._build_subscriptions(ctx_coins, trade_coins)
        chunk = self.config.subs_per_connection
        chunks = [
            subscriptions[i : i + chunk] for i in range(0, len(subscriptions), chunk)
        ]
        if len(chunks) > 10:
            raise RuntimeError(
                f"{len(chunks)} connections needed but the protocol caps at 10; "
                "raise subs_per_connection or narrow the capture set"
            )

        if self.config.full_capture:
            logger.info(
                "recording %d assets: context + trades (%d) + book (%d focus) "
                "over %d connection(s) -> %s",
                len(ctx_coins),
                len(trade_coins),
                len(self.config.focus_coins),
                len(chunks),
                self.config.root,
            )
        else:
            logger.info(
                "recording funding/context for %d assets over %d connection(s) -> %s "
                "(trades and book left to perplog-recorder; --full to include them)",
                len(ctx_coins),
                len(chunks),
                self.config.root,
            )

        tasks = [
            asyncio.create_task(self._ws_worker(f"ws{i}", part), name=f"ws{i}")
            for i, part in enumerate(chunks)
        ]
        tasks.append(asyncio.create_task(self._funding_poller(ctx_coins), name="funding"))
        tasks.append(asyncio.create_task(self._flusher(), name="flusher"))
        tasks.append(asyncio.create_task(self._status(), name="status"))

        await self._stop.wait()
        logger.info("stopping — flushing buffers")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.close()

    def close(self) -> None:
        total = 0
        for name, writer in self.writers.items():
            written = writer.flush()
            if written:
                logger.info("flushed %d rows to %s", written, name)
            total += writer.rows_written
        logger.info("recorded %d rows this session", total)

    def request_stop(self) -> None:
        self._stop.set()


async def _amain(config: RecorderConfig) -> None:
    recorder = Recorder(config)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, recorder.request_stop)
    try:
        await recorder.run()
    finally:
        await recorder.client.close()


def print_status(root: Path) -> None:
    """Summarise what is already on disk."""
    store = Store(root)
    available = store.available()
    if not available:
        print(f"No data recorded yet under {root}/")
        return
    print(f"Datasets under {root}/\n")
    for dataset, files in sorted(available.items()):
        try:
            row = store.sql(
                f"SELECT count(*) n, min(time) lo, max(time) hi, count(DISTINCT coin) coins "
                f"FROM read_parquet('{store.path_glob(dataset)}', hive_partitioning = true)"
            ).fetchone()
            span = ""
            if row[1] is not None:
                span = f"  {row[1]:%Y-%m-%d %H:%M} -> {row[2]:%Y-%m-%d %H:%M}"
            print(f"  {dataset:<10} {row[0]:>12,} rows  {row[3]:>4} assets  {files:>4} files{span}")
        except Exception as exc:  # a dataset may hold only a partial file
            print(f"  {dataset:<10} unreadable: {exc}")
    store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--status", action="store_true", help="summarise stored data and exit")
    parser.add_argument(
        "--full",
        action="store_true",
        help="also capture trades and book (perplog-recorder covers both already)",
    )
    parser.add_argument("--trade-coins", type=int, default=20, help="assets with trade capture")
    parser.add_argument(
        "--focus", nargs="*", default=["BTC", "ETH", "SOL", "HYPE"], help="assets with book capture"
    )
    parser.add_argument(
        "--min-free-gb",
        type=float,
        default=5.0,
        help="stop recording if free disk falls below this",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.status:
        print_status(args.data_dir)
        return

    config = RecorderConfig(
        root=args.data_dir,
        full_capture=args.full,
        n_trade_coins=args.trade_coins,
        focus_coins=list(args.focus),
        min_free_gb=args.min_free_gb,
    )
    started = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info("recorder starting at %s — Ctrl-C to stop cleanly", started)
    asyncio.run(_amain(config))


if __name__ == "__main__":
    main()
