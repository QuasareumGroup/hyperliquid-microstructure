"""EXP-031 — the anatomy of Hyperliquid's clock. Registration + amendment.

Five committed days (2026-07-21..25), four majors. HL blocks and fills from
node_fills_by_block; Binance from the perplog tape. D1 descriptives, H1
(cadence exogeneity), H2 (intensive vs extensive margin), H3 at the native
tick per the amendment, plus the minute-scale sample check against paper 2's
published ranges.

    python experiments/exp031_block_clock.py
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import lz4.frame
import numpy as np
from scipy.stats import spearmanr

BUCKET = "s3://hl-mainnet-node-data/node_fills_by_block/hourly"
MICRO = Path.home() / "hyperliquid-microstructure"
PFR_DUMP = MICRO / "tools" / "pfr-dump" / "target" / "release" / "pfr-dump"
R2_ACCOUNT = "98a4368e20fe27701f67bd2f19d53a21"
TCACHE = Path.home() / ".cache" / "bn-tape"
SCRATCH = Path("/private/tmp/claude-501/-/59f6bb52-0f12-4aae-99f2-59c8d43d4f6d/scratchpad/e031")
COINS = ("BTC", "ETH", "SOL", "HYPE")
DAYS = [f"2026-07-{d}" for d in range(21, 26)]
BUCKET_MS = 68


def parse_iso_ms(s: str) -> int:
    base, frac = s.split(".")
    dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000) + int(frac[:3])


def bn_hour(coin: str, date: str, hour: str):
    """68-ms bucket counts + last px, and per-minute counts, from the tape."""
    TCACHE.mkdir(parents=True, exist_ok=True)
    f = TCACHE / f"{coin}-{date}-{hour}.pfr"
    if not f.exists() or f.stat().st_size == 0:
        key = f"perplog-flow-days/tape/v1/binance/{coin}/{date}/{hour}.pfr"
        subprocess.run(
            ["npx", "--yes", "wrangler@latest", "r2", "object", "get", key,
             "--file", str(f), "--remote"],
            capture_output=True,
            env={**os.environ, "CLOUDFLARE_ACCOUNT_ID": R2_ACCOUNT})
    if not f.exists() or f.stat().st_size == 0:
        return None
    out = subprocess.run([str(PFR_DUMP), "binance", coin, str(f)],
                         capture_output=True, text=True).stdout.splitlines()[1:]
    ev = []
    for line in out:
        p = line.split(",")
        try:
            ev.append((int(p[2]), float(p[3])))
        except (IndexError, ValueError):
            continue
    return ev or None


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    gaps, lags = [], []
    # per coin accumulators
    unit_hl = {c: ([], []) for c in COINS}        # (counts, |dlogpx|) per block, active
    unit_bn = {c: ([], []) for c in COINS}
    unit_bn_1s = {c: ([], []) for c in COINS}
    minute = {c: defaultdict(lambda: [0, 0, None, 0.0])
              for c in COINS}   # min -> [fills, nonempty_blocks, last_px, bn_trades]
    blocks_min = defaultdict(int)
    zero_share = {c: [0, 0] for c in COINS}       # [empty, total] HL blocks

    hours = [(d, f"{h:02d}") for d in DAYS for h in range(24)]
    prev_bt = None
    last_hl_px = {c: None for c in COINS}
    last_bn_px = {c: None for c in COINS}

    for date, hour in hours:
        date8 = date.replace("-", "")
        p = SCRATCH / f"{date8}-{hour}.lz4"
        for _ in range(3):
            r = subprocess.run(
                ["aws", "s3", "cp", f"{BUCKET}/{date8}/{int(hour)}.lz4",
                 str(p), "--request-payer", "requester", "--quiet"],
                capture_output=True)
            if r.returncode == 0 and p.exists():
                break
            time.sleep(20)
        if r.returncode != 0 or not p.exists():
            print(f"  {date8}-{hour}: HL absent", flush=True)
            continue
        try:
            with lz4.frame.open(p, "rt") as fh:
                for line in fh:
                    try:
                        blk = json.loads(line)
                        bt = parse_iso_ms(blk["block_time"])
                        lt = parse_iso_ms(blk["local_time"])
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                    if prev_bt is not None and 0 < bt - prev_bt < 10000:
                        gaps.append(bt - prev_bt)
                    prev_bt = bt
                    lags.append(lt - bt)
                    blocks_min[bt // 60000] += 1
                    per = defaultdict(lambda: [0, None])
                    for ev in blk.get("events", []):
                        if not (isinstance(ev, list) and len(ev) > 1):
                            continue
                        f = ev[1]
                        c = f.get("coin")
                        if c not in COINS:
                            continue
                        try:
                            px = float(f["px"])
                        except (KeyError, ValueError, TypeError):
                            continue
                        per[c][0] += 1
                        per[c][1] = px
                    for c in COINS:
                        zero_share[c][1] += 1
                        n, px = per.get(c, (0, None))
                        if n == 0:
                            zero_share[c][0] += 1
                            continue
                        if last_hl_px[c] is not None and last_hl_px[c] > 0:
                            unit_hl[c][0].append(n)
                            unit_hl[c][1].append(
                                abs(np.log(px / last_hl_px[c])))
                        last_hl_px[c] = px
                        m = minute[c][bt // 60000]
                        m[0] += n
                        m[1] += 1
                        m[2] = px
        finally:
            p.unlink(missing_ok=True)

        for c in COINS:
            ev = bn_hour(c, date, hour)
            if ev is None:
                continue
            bkt = defaultdict(lambda: [0, None])
            for ts, px in ev:
                b = bkt[ts // BUCKET_MS]
                b[0] += 1
                b[1] = px
                minute[c][ts // 60000][3] += 1
            for _, (n, px) in sorted(bkt.items()):
                if last_bn_px[c] is not None and last_bn_px[c] > 0:
                    unit_bn[c][0].append(n)
                    unit_bn[c][1].append(abs(np.log(px / last_bn_px[c])))
                last_bn_px[c] = px
            b1 = defaultdict(lambda: [0, None])
            for ts, px in ev:
                b = b1[ts // 1000]
                b[0] += 1
                b[1] = px
            prev = None
            for _, (n, px) in sorted(b1.items()):
                if prev is not None and prev > 0:
                    unit_bn_1s[c][0].append(n)
                    unit_bn_1s[c][1].append(abs(np.log(px / prev)))
                prev = px
        if hour == "23":
            print(f"  {date} fait", flush=True)

    g = np.array(gaps)
    l = np.array(lags)
    print("\n=== D1 — la cadence et le retard d'observation ===")
    print(f"blocs: {g.size:,}  gap median {np.median(g):.0f} ms  "
          f"IQR [{np.percentile(g,25):.0f}, {np.percentile(g,75):.0f}]  "
          f"p99 {np.percentile(g,99):.0f} ms")
    print(f"local-block lag: median {np.median(l):.0f} ms  "
          f"p90 {np.percentile(l,90):.0f}  p99 {np.percentile(l,99):.0f} ms")
    for c in COINS:
        e, tot = zero_share[c]
        print(f"  {c}: blocs vides {e/tot*100:.1f}%")

    print("\n=== H1 — le pouls est-il exogene ? ===")
    h1 = {}
    for c in COINS:
        mins = sorted(minute[c])
        vol, bpm = [], []
        prev = None
        for m in mins:
            px = minute[c][m][2]
            if px is None:
                continue
            if prev is not None:
                vol.append(abs(np.log(px / prev)))
                bpm.append(blocks_min.get(m, 0))
            prev = px
        rho = float(spearmanr(vol, bpm)[0])
        h1[c] = rho
        print(f"  {c}: Spearman(vol, blocs/min) = {rho:+.3f}")
    p1 = all(-0.10 <= h1[c] <= 0.10 for c in COINS)
    print(f"H1 (tous dans [-0.10,+0.10]): {'CONFIRMEE' if p1 else 'INFIRMEE'}")

    print("\n=== H2 — marge intensive contre extensive ===")
    h2n = 0
    for c in COINS:
        mins = sorted(minute[c])
        vol, inten, exten = [], [], []
        prev = None
        for m in mins:
            fills, nblk, px, _ = minute[c][m]
            if px is None:
                continue
            if prev is not None and nblk > 0:
                vol.append(abs(np.log(px / prev)))
                inten.append(fills / nblk)
                exten.append(nblk)
            prev = px
        ri = float(spearmanr(vol, inten)[0])
        re = float(spearmanr(vol, exten)[0])
        h2n += ri > re
        print(f"  {c}: intensive {ri:+.3f}  extensive {re:+.3f}"
              f"  -> {'intensive' if ri > re else 'EXTENSIVE'}")
    print(f"H2 (intensive > extensive dans >=3/4): {h2n}/4 "
          f"{'CONFIRMEE' if h2n >= 3 else 'INFIRMEE'}")

    print("\n=== H3 (amendee) — le couplage au tick natif ===")
    h3n = 0
    for c in COINS:
        rh = float(spearmanr(unit_hl[c][0], unit_hl[c][1])[0])
        rb = float(spearmanr(unit_bn[c][0], unit_bn[c][1])[0])
        rb1 = float(spearmanr(unit_bn_1s[c][0], unit_bn_1s[c][1])[0])
        ratio = rh / rb if rb > 0 else float("nan")
        h3n += ratio < 0.5
        print(f"  {c}: HL/bloc {rh:+.3f} (n={len(unit_hl[c][0]):,})  "
              f"BN/68ms {rb:+.3f} (n={len(unit_bn[c][0]):,})  "
              f"BN/1s {rb1:+.3f}  ratio {ratio:.2f}")
    print(f"H3 (ratio < 0.5 dans >=3/4): {h3n}/4 "
          f"{'CONFIRMEE — informationnel' if h3n >= 3 else 'INFIRMEE — la plomberie converge'}")

    print("\n=== controle d'echantillon — l'echelle minute du papier 2 ===")
    for c in COINS:
        mins = sorted(minute[c])
        vol, cnt, bcnt = [], [], []
        prev = None
        for m in mins:
            fills, _, px, bn = minute[c][m]
            if px is None:
                continue
            if prev is not None:
                vol.append(abs(np.log(px / prev)))
                cnt.append(fills)
                bcnt.append(bn)
            prev = px
        print(f"  {c}: HL arrivee/vol {float(spearmanr(vol, cnt)[0]):+.3f} "
              f"(papier 2: +0.06..+0.17)   BN {float(spearmanr(vol, bcnt)[0]):+.3f} "
              f"(papier 2: +0.28..+0.77)")

    out = MICRO / "experiments" / "data" / "exp031_results.json"
    out.write_text(json.dumps({
        "gap_median_ms": float(np.median(g)),
        "gap_p99_ms": float(np.percentile(g, 99)),
        "lag_median_ms": float(np.median(l)),
        "h1": h1,
        "empty_block_share": {c: zero_share[c][0] / zero_share[c][1]
                              for c in COINS},
    }, indent=1))
    print(f"\n-> {out}")
    print("EXP-031 TERMINE")


if __name__ == "__main__":
    main()
