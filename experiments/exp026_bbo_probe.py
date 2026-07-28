"""EXP-026 Test C sizing — how much does a native-cadence BBO capture actually cost?

Measures only. Writes no market data to disk: it counts messages and wire bytes for
a bounded window and prints a projection. Nothing here decides to start a capture;
it produces the number that decision needs, because a permanent recorder on a
machine with a history of filling up is not something to switch on unsized.

Both channels are push-on-change with no venue-imposed interval, which is exactly
why they can resolve 575 ms where the recorded depth books cannot -- and also why
their volume is unknown in advance.

    python experiments/exp026_bbo_probe.py --seconds 120
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter

import websockets

HL_URL = "wss://api.hyperliquid.xyz/ws"
#: Same host perplog already uses for Binance perps (see recorder book_venues.rs).
BN_URL = "wss://fstream.binance.com/stream?streams={}"
COINS = ("BTC", "ETH", "SOL", "HYPE")
#: Nominal on-disk record: ts_ms + bid/ask px and sz, e8-normalized, plus coin and
#: venue tags -- the shape perplog's .pbs codec already writes.
REC_BYTES = 32


async def probe_hl(secs: float, msgs: Counter, wire: Counter) -> None:
    async with websockets.connect(HL_URL, ping_interval=20, max_queue=None) as ws:
        for c in COINS:
            await ws.send(json.dumps({"method": "subscribe",
                                      "subscription": {"type": "bbo", "coin": c}}))
        end = time.monotonic() + secs
        while time.monotonic() < end:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=end - time.monotonic())
            except (asyncio.TimeoutError, ValueError):
                break
            wire["hl"] += len(raw)
            try:
                m = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if m.get("channel") == "bbo":
                msgs[f"hl/{m['data'].get('coin', '?')}"] += 1


async def probe_bn(secs: float, msgs: Counter, wire: Counter) -> None:
    streams = "/".join(f"{c.lower()}usdt@bookTicker" for c in COINS)
    async with websockets.connect(BN_URL.format(streams), ping_interval=20,
                                  max_queue=None) as ws:
        end = time.monotonic() + secs
        while time.monotonic() < end:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=end - time.monotonic())
            except (asyncio.TimeoutError, ValueError):
                break
            wire["binance"] += len(raw)
            try:
                m = json.loads(raw)
            except json.JSONDecodeError:
                continue
            s = m.get("data", {}).get("s")
            if s:
                msgs[f"binance/{s}"] += 1


async def main_async(secs: float) -> None:
    msgs: Counter = Counter()
    wire: Counter = Counter()
    print(f"probing {secs:.0f}s — HL bbo + Binance bookTicker, {len(COINS)} coins, "
          f"nothing written to disk")
    res = await asyncio.gather(probe_hl(secs, msgs, wire),
                               probe_bn(secs, msgs, wire),
                               return_exceptions=True)
    for venue, r in zip(("hl", "binance"), res):
        if isinstance(r, Exception):
            print(f"  !! {venue} failed: {type(r).__name__}: {r}")

    total = sum(msgs.values())
    if not total:
        raise SystemExit("no messages received — nothing to size")

    print(f"\n{'stream':<20}{'msgs':>10}{'per sec':>10}{'per day':>14}")
    for k in sorted(msgs, key=lambda x: -msgs[x]):
        n = msgs[k]
        print(f"  {k:<18}{n:>10,}{n/secs:>10.1f}{n/secs*86400:>14,.0f}")

    print(f"\n{'venue':<12}{'wire B/s':>12}{'wire GB/day':>14}{'GB/month':>12}")
    for v in ("hl", "binance"):
        bps = wire[v] / secs
        print(f"  {v:<10}{bps:>12,.0f}{bps*86400/1e9:>14.2f}{bps*86400*30/1e9:>12.1f}")

    rate = total / secs
    enc_day = rate * 86400 * REC_BYTES / 1e9
    print(f"\n  combined {rate:,.0f} msg/s over {len(COINS)} coins x 2 venues")
    print(f"  wire (JSON, what arrives)   {sum(wire.values())/secs*86400/1e9:>7.2f} GB/day")
    print(f"  encoded at {REC_BYTES} B/record {enc_day:>18.2f} GB/day"
          f"   {enc_day*30:>6.1f} GB/month")
    print(f"\n  a 2-week Test C window ≈ {enc_day*14:.1f} GB encoded"
          f" ({enc_day*14/len(COINS):.1f} GB per coin)")
    print("  compression not modelled — perplog's codec would cut this further.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seconds", type=float, default=120.0)
    args = ap.parse_args()
    asyncio.run(main_async(args.seconds))


if __name__ == "__main__":
    main()
