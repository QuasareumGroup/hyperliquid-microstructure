//! Dump perplog `.pfr` trade-tape frames to CSV on stdout.
//!
//! The tape API serves raw PFR1 bytes and does no decoding worker-side, so the
//! decode has to happen locally. `perplog-recorder decode` prints per-file
//! statistics only; this prints the prints.
//!
//! Usage:
//!   pfr-dump <venue> <coin> <file.pfr> [more.pfr ...] > out.csv
//!
//! Output: `venue,coin,ts_ms,px,sz,taker_buy`

use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() < 3 {
        eprintln!("usage: pfr-dump <venue> <coin> <file.pfr> [more.pfr ...]");
        return ExitCode::FAILURE;
    }
    let (venue, coin, files) = (&args[0], &args[1], &args[2..]);

    println!("venue,coin,ts_ms,px,sz,taker_buy");
    let mut total = 0usize;
    for path in files {
        let bytes = match std::fs::read(path) {
            Ok(b) => b,
            Err(e) => {
                eprintln!("skip {path}: {e}");
                continue;
            }
        };
        let chunks = match perplog_flow::tape::decode_chunks(&bytes) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("skip {path}: decode failed: {e:?}");
                continue;
            }
        };
        for chunk in &chunks {
            for &(ts_ms, px_e8, sz_e8, taker_buy) in &chunk.prints {
                // e8 fixed point throughout the perplog wire layer.
                let px = px_e8 as f64 / 1e8;
                let sz = sz_e8 as f64 / 1e8;
                println!("{venue},{coin},{ts_ms},{px},{sz},{}", u8::from(taker_buy));
                total += 1;
            }
        }
    }
    eprintln!("{total} prints from {} file(s)", files.len());
    ExitCode::SUCCESS
}
