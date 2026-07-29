//! Dump perplog `.pbq` BBO frames to CSV on stdout — the quote twin of `pfr-dump`.
//!
//! `quote/v1/…/*.pbq` holds PBS1 records with ONE level a side: a best bid and a
//! best ask, pushed on every change by HL's `bbo` and Binance's `bookTicker`.
//! `perplog-recorder decode` prints per-file statistics only; this prints the
//! quotes, which is what a lead-lag estimator needs.
//!
//! Crossed and empty-sided snapshots are DROPPED and counted on stderr rather
//! than repaired. A crossed book is either a venue artefact or a decode fault,
//! and silently fixing one would put a fabricated midpoint into a measurement.
//!
//! Usage:
//!   pbq-dump <venue> <coin> <file.pbq> [more.pbq ...] > out.csv
//!
//! Output: `venue,coin,ts_ms,bid,ask,mid`

use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() < 3 {
        eprintln!("usage: pbq-dump <venue> <coin> <file.pbq> [more.pbq ...]");
        return ExitCode::FAILURE;
    }
    let (venue, coin, files) = (&args[0], &args[1], &args[2..]);

    println!("venue,coin,ts_ms,bid,ask,mid");
    let (mut total, mut dropped) = (0usize, 0usize);
    for path in files {
        let bytes = match std::fs::read(path) {
            Ok(b) => b,
            Err(e) => {
                eprintln!("skip {path}: {e}");
                continue;
            }
        };
        let decoded = match perplog_archive::book_snap::decode_frames(&bytes) {
            Ok(d) => d,
            Err(e) => {
                eprintln!("skip {path}: decode failed: {e:?}");
                continue;
            }
        };
        for snap in &decoded.snaps {
            // One level a side is what the quote family writes; anything else
            // means the wrong tree was passed in.
            let (Some(&(bid_e8, _)), Some(&(ask_e8, _))) =
                (snap.bids.first(), snap.asks.first())
            else {
                dropped += 1;
                continue;
            };
            if snap.crossed() || bid_e8 <= 0 || ask_e8 <= 0 {
                dropped += 1;
                continue;
            }
            // e8 fixed point throughout the perplog wire layer.
            let bid = bid_e8 as f64 / 1e8;
            let ask = ask_e8 as f64 / 1e8;
            println!("{venue},{coin},{},{bid},{ask},{}", snap.ts_ms, 0.5 * (bid + ask));
            total += 1;
        }
    }
    eprintln!("{total} quotes from {} file(s), {dropped} dropped (crossed/empty)",
              files.len());
    ExitCode::SUCCESS
}
