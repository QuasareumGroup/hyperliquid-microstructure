"""Async client for the Hyperliquid public `info` API.

Read-only. The recorder uses mainnet, which needs no credentials and carries no
risk. Signing and the `exchange` endpoint live in `qfr.strategy`, testnet only.

The IP rate limit is a weighted budget of 1200 per minute, and the weights are
uneven enough that a naive request counter would be wrong by a factor of 10:
`l2Book` costs 2 while most other info requests cost 20. `RateLimiter` below
tracks the real weight so a caller cannot silently overrun the budget.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAINNET_INFO_URL = "https://api.hyperliquid.xyz/info"
TESTNET_INFO_URL = "https://api.hyperliquid-testnet.xyz/info"
MAINNET_WS_URL = "wss://api.hyperliquid.xyz/ws"
TESTNET_WS_URL = "wss://api.hyperliquid-testnet.xyz/ws"

#: Aggregate REST weight budget per IP, per minute.
REST_WEIGHT_PER_MINUTE = 1200

#: Info request types that cost 2 weight instead of the default 20.
_CHEAP_INFO_TYPES = frozenset(
    {
        "l2Book",
        "allMids",
        "clearinghouseState",
        "orderStatus",
        "spotClearinghouseState",
        "exchangeStatus",
    }
)

#: Info request types billed an extra weight unit per 20 items returned.
_PAGINATED_INFO_TYPES = frozenset(
    {
        "recentTrades",
        "historicalOrders",
        "userFills",
        "userFillsByTime",
        "fundingHistory",
        "userFunding",
        "nonUserFundingUpdates",
        "twapHistory",
        "userTwapSliceFills",
        "userTwapSliceFillsByTime",
        "delegatorHistory",
        "delegatorRewards",
        "validatorStats",
    }
)

_DEFAULT_INFO_WEIGHT = 20
_USER_ROLE_WEIGHT = 60


def request_weight(info_type: str) -> int:
    """Weight charged for an info request *before* the response is seen.

    Paginated endpoints are billed additional weight per items returned; that
    part is only knowable afterwards and is settled by `response_weight`.
    """
    if info_type == "userRole":
        return _USER_ROLE_WEIGHT
    if info_type in _CHEAP_INFO_TYPES:
        return 2
    return _DEFAULT_INFO_WEIGHT


def response_weight(info_type: str, payload: Any) -> int:
    """Extra weight charged for the size of a response, settled after the call."""
    if not isinstance(payload, list):
        return 0
    if info_type == "candleSnapshot":
        return math.floor(len(payload) / 60)
    if info_type in _PAGINATED_INFO_TYPES:
        return math.floor(len(payload) / 20)
    return 0


@dataclass
class RateLimiter:
    """Sliding-window limiter over a weighted budget.

    Hyperliquid bills weight, not calls, so the window holds (timestamp, weight)
    pairs rather than bare timestamps.
    """

    budget: int = REST_WEIGHT_PER_MINUTE
    window_seconds: float = 60.0
    #: Fraction of the budget we actually spend, leaving room for the response
    #: surcharge on paginated endpoints, which is unknown at request time.
    safety: float = 0.8
    _events: deque[tuple[float, int]] = field(default_factory=deque, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def spent(self) -> int:
        """Weight consumed inside the current window."""
        self._prune(time.monotonic())
        return sum(weight for _, weight in self._events)

    async def acquire(self, weight: int) -> None:
        """Block until `weight` fits in the window, then record it."""
        while True:
            async with self._lock:
                now = time.monotonic()
                self._prune(now)
                used = sum(w for _, w in self._events)
                if used + weight <= self.budget * self.safety:
                    self._events.append((now, weight))
                    return
                oldest = self._events[0][0] if self._events else now
            delay = max(0.05, oldest + self.window_seconds - now)
            logger.debug("rate limit: sleeping %.2fs (used %d/%d)", delay, used, self.budget)
            await asyncio.sleep(delay)

    async def settle(self, extra_weight: int) -> None:
        """Charge additional weight discovered after a response was read."""
        if extra_weight <= 0:
            return
        async with self._lock:
            self._events.append((time.monotonic(), extra_weight))


class InfoClient:
    """Async wrapper over `POST /info` with weight accounting and retries."""

    def __init__(
        self,
        *,
        testnet: bool = False,
        timeout: float = 15.0,
        limiter: RateLimiter | None = None,
        max_retries: int = 4,
    ) -> None:
        self.url = TESTNET_INFO_URL if testnet else MAINNET_INFO_URL
        self.ws_url = TESTNET_WS_URL if testnet else MAINNET_WS_URL
        self.limiter = limiter or RateLimiter()
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    async def __aenter__(self) -> InfoClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def post(self, body: dict[str, Any]) -> Any:
        """Send one info request, respecting the weight budget.

        Retries on 429 and 5xx with exponential backoff. Other 4xx are raised
        immediately — they mean the request itself is wrong.
        """
        info_type = body.get("type", "")
        await self.limiter.acquire(request_weight(info_type))

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(self.url, json=body)
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"retryable status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                payload = response.json()
                await self.limiter.settle(response_weight(info_type, payload))
                return payload
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and status < 500 and status != 429:
                    raise
                last_error = exc
                backoff = 2.0**attempt
                logger.warning(
                    "info %s failed (attempt %d/%d): %s — retrying in %.0fs",
                    info_type or "?",
                    attempt + 1,
                    self.max_retries,
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)

        raise RuntimeError(f"info request {info_type!r} failed after {self.max_retries} attempts") from last_error

    # --- typed helpers -------------------------------------------------

    async def meta_and_asset_ctxs(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Perp universe and per-asset context (funding, open interest, mark)."""
        meta, ctxs = await self.post({"type": "metaAndAssetCtxs"})
        return meta, ctxs

    async def spot_meta_and_asset_ctxs(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        meta, ctxs = await self.post({"type": "spotMetaAndAssetCtxs"})
        return meta, ctxs

    async def funding_history(
        self, coin: str, start_time_ms: int, end_time_ms: int | None = None
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_time_ms,
        }
        if end_time_ms is not None:
            body["endTime"] = end_time_ms
        return await self.post(body)

    async def l2_book(self, coin: str) -> dict[str, Any]:
        return await self.post({"type": "l2Book", "coin": coin})

    async def all_mids(self) -> dict[str, str]:
        return await self.post({"type": "allMids"})

    async def perp_universe(self, include_delisted: bool = False) -> list[str]:
        """Names of tradable perp assets, most-liquid-first by 24h notional."""
        meta, ctxs = await self.meta_and_asset_ctxs()
        rows: list[tuple[str, float]] = []
        for asset, ctx in zip(meta["universe"], ctxs, strict=False):
            if asset.get("isDelisted") and not include_delisted:
                continue
            try:
                volume = float(ctx.get("dayNtlVlm", 0.0))
            except (TypeError, ValueError):
                volume = 0.0
            rows.append((asset["name"], volume))
        rows.sort(key=lambda row: -row[1])
        return [name for name, _ in rows]
