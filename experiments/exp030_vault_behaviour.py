"""EXP-030 — what do the most active accounts on Hyperliquid actually do?

Descriptive, on public on-chain data. The question it answers is one that is
usually guessed at: the accounts running large books on this venue — are they
automated, do they post or take, and where does their money come from?

Hyperliquid makes this answerable rather than speculative. Every fill in
`node_fills_by_block` carries the account, whether it `crossed` the spread, the
`fee` actually paid, and the `closedPnl` realised. Vault addresses are public
entities and `userRole` identifies them, so a vault can be named; every other
address is hashed on output, matching the discipline the rest of this repository
uses.

    python experiments/exp030_vault_behaviour.py --hours 20260728-08 20260728-14
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tempfile
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import lz4.frame
import numpy as np

BUCKET = "s3://hl-mainnet-node-data/node_fills_by_block/hourly"
INFO = "https://api.hyperliquid.xyz/info"


def short(addr: str) -> str:
    """Public vault addresses are named by the caller; everything else is hashed."""
    return hashlib.sha256(addr.encode()).hexdigest()[:16]


def info(payload: dict) -> dict | list | None:
    req = urllib.request.Request(
        INFO, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return None


def scan_hour(spec: str) -> dict[str, dict]:
    """Per-account aggregates for one archive hour."""
    date8, h = spec.split("-")
    acc: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "vol": 0.0, "fee": 0.0, "pnl": 0.0, "maker": 0,
                 "twap": 0, "coins": set(), "times": []})
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "h.lz4"
        r = subprocess.run(
            ["aws", "s3", "cp", f"{BUCKET}/{date8}/{int(h)}.lz4", str(p),
             "--request-payer", "requester", "--quiet"], capture_output=True)
        if r.returncode != 0 or not p.exists():
            return {}
        with lz4.frame.open(p, "rt") as fh:
            for line in fh:
                try:
                    block = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for ev in block.get("events", []):
                    if not (isinstance(ev, list) and len(ev) > 1):
                        continue
                    user, f = ev[0], ev[1]
                    try:
                        px, sz = float(f["px"]), float(f["sz"])
                        a = acc[user]
                        a["n"] += 1
                        a["vol"] += px * sz
                        a["fee"] += float(f.get("fee", 0) or 0)
                        a["pnl"] += float(f.get("closedPnl", 0) or 0)
                        a["maker"] += 0 if f.get("crossed", True) else 1
                        a["twap"] += 1 if f.get("twapId") is not None else 0
                        a["coins"].add(f.get("coin", "?"))
                        a["times"].append(int(f["time"]))
                    except (KeyError, ValueError, TypeError):
                        continue
    return acc


def merge(into: dict, add: dict) -> None:
    for u, a in add.items():
        t = into[u]
        for k in ("n", "vol", "fee", "pnl", "maker", "twap"):
            t[k] += a[k]
        t["coins"] |= a["coins"]
        t["times"].extend(a["times"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours", nargs="+",
                    default=["20260728-04", "20260728-08", "20260728-12",
                             "20260728-16", "20260728-20", "20260729-00"])
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path,
                    default=Path("experiments/data/exp030_accounts.csv"))
    args = ap.parse_args()

    total: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "vol": 0.0, "fee": 0.0, "pnl": 0.0, "maker": 0,
                 "twap": 0, "coins": set(), "times": []})
    print(f"scanning {len(args.hours)} archive hours\n")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(scan_hour, s): s for s in args.hours}
        for fut in as_completed(futs):
            got = fut.result()
            merge(total, got)
            print(f"  {futs[fut]}: {len(got):,} accounts")

    ranked = sorted(total.items(), key=lambda kv: -kv[1]["vol"])[: args.top]
    print(f"\n{len(total):,} accounts total; classifying the top {len(ranked)} by volume\n")

    rows = []
    for addr, a in ranked:
        role = info({"type": "userRole", "user": addr}) or {}
        is_vault = role.get("role") == "vault"
        name = ""
        if is_vault:
            d = info({"type": "vaultDetails", "vaultAddress": addr}) or {}
            name = (d or {}).get("name", "") if isinstance(d, dict) else ""
        t = np.sort(np.array(a["times"], dtype=np.int64))
        gaps = np.diff(t) if t.size > 1 else np.array([np.nan])
        rows.append({
            "id": addr if is_vault else short(addr),
            "role": role.get("role", "?"),
            "vault_name": name,
            "fills": a["n"],
            "volume_usd": round(a["vol"], 0),
            "fee_usd": round(a["fee"], 2),
            "closed_pnl_usd": round(a["pnl"], 2),
            "maker_frac": round(a["maker"] / a["n"], 4) if a["n"] else 0.0,
            "twap_frac": round(a["twap"] / a["n"], 4) if a["n"] else 0.0,
            "n_coins": len(a["coins"]),
            "median_gap_ms": float(np.median(gaps)) if np.isfinite(gaps).any() else float("nan"),
            "p10_gap_ms": float(np.percentile(gaps, 10)) if np.isfinite(gaps).any() else float("nan"),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}\n")

    vaults = [r for r in rows if r["role"] == "vault"]
    print(f"{len(vaults)} of the top {len(rows)} are vaults\n")
    print(f"{'':<34}{'fills':>9}{'volume':>14}{'maker':>8}{'gap p50':>10}{'fees':>12}{'pnl':>13}")
    for r in sorted(rows, key=lambda x: -x["volume_usd"])[:25]:
        tag = (r["vault_name"] or "vault")[:30] if r["role"] == "vault" else r["id"][:12]
        mark = "V " if r["role"] == "vault" else "  "
        print(f"{mark}{tag:<32}{r['fills']:>9,}{r['volume_usd']:>14,.0f}"
              f"{r['maker_frac']:>8.1%}{r['median_gap_ms']:>9,.0f}ms"
              f"{r['fee_usd']:>12,.0f}{r['closed_pnl_usd']:>13,.0f}")

    print("\n" + "=" * 74)
    a = np.array([[r["maker_frac"], r["median_gap_ms"], r["fee_usd"], r["closed_pnl_usd"]]
                  for r in rows], dtype=float)
    sub = a[np.isfinite(a[:, 1])]
    print(f"  median maker fraction, top {len(rows)}: {np.median(sub[:,0]):.1%}")
    print(f"  median inter-fill gap             : {np.median(sub[:,1]):,.0f} ms")
    print(f"  accounts with median gap < 1 s    : {int((sub[:,1] < 1000).sum())} / {len(sub)}")
    print(f"  accounts paying net fees          : {int((sub[:,2] > 0).sum())} / {len(sub)}")


if __name__ == "__main__":
    main()
