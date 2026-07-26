# tools/

## pfr-dump

Decodes perplog `.pfr` trade-tape frames to CSV. The tape API serves raw PFR1 bytes and does
no decoding server-side, and `perplog-recorder decode` prints per-file statistics only — this
prints the prints.

```bash
cd tools/pfr-dump && cargo build --release
./target/release/pfr-dump hl BTC hour12.pfr hour13.pfr > hl.csv
```

Output: `venue,coin,ts_ms,px,sz,taker_buy`.

**It will not build outside this machine as written.** `Cargo.toml` takes a path dependency
on `../../../perplog/rust/crates/flow`, a private sibling repo. That is deliberate: the PFR
codec is perplog's and is tested there, and reimplementing the bincode + lz4 framing in Python
to avoid the coupling would mean guessing at a binary format. The failure mode of guessing is
silent wrong numbers, which is the one thing this project cannot afford.

If the tape is ever published as an open dataset, this is the piece that needs replacing —
either by vendoring the codec or by serving decoded CSV from the worker.

Fetching hours (public, no credentials):

```bash
curl -s "https://perplog.com/api/flow/tape/coverage?venue=hl&coin=BTC&date=2026-07-24"
curl -s -o h12.pfr "https://perplog.com/api/flow/tape?venue=hl&coin=BTC&date=2026-07-24&hour=12"
```

Venues: `hl`, `binance`, `okx`, `bybit`. Live recording began 2026-07-17 ~20:31 UTC; a retro
Binance backfill reaches back to 2026-06-17. Absent hours are honest holes, listed by
`/coverage` — never interpolated.
