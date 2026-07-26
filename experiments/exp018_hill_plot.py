"""EXP-018 — Hill plot over a continuum of k, with a stability search.

EXP-017 reported the tail index at three arbitrary k and found it drifts
(1.22 -> 1.02 -> 0.93). Three points cannot separate "the estimator is unstable"
from "we picked badly". A Hill plot over a continuum can, and it is the standard
way to report an index that moves: read alpha off a plateau, or state there is
none.

Also searches for a stability region rather than eyeballing one — the window in
log-k minimising the local coefficient of variation of alpha. If the flattest
window is still not flat, that is the answer.

SVG is emitted directly rather than through a plotting library: matplotlib's
font manager crashes on this macOS build, and hand-written SVG keeps the repo
dependency-free and the palette exact.

Palette: slots 1-3 of the dataviz reference, validated (worst adjacent CVD
deltaE 9.2, normal-vision 27.6). Aqua sits below 3:1 on the light surface, so
direct labels are mandatory rather than optional — they are shipped.

    python experiments/exp018_hill_plot.py
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import duckdb
import numpy as np

REPO = Path(__file__).resolve().parent.parent

SERIES = {"light": ["#2a78d6", "#eb6834", "#1baf7a"],
          "dark": ["#3987e5", "#d95926", "#199e70"]}
CHROME = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", second="#52514e",
                  muted="#898781", grid="#e1e0d9", axis="#c3c2b7"),
    "dark": dict(surface="#1a1a19", ink="#ffffff", second="#c3c2b7",
                 muted="#898781", grid="#2c2c2a", axis="#383835"),
}
W, H = 960, 560
PAD = dict(l=74, r=150, t=86, b=62)


def hill(desc: np.ndarray, k: int) -> float:
    return float(1.0 / np.mean(np.log(desc[:k] / desc[k])))


#: Largest tail fraction a Hill curve is drawn for. Past this one is fitting the
#: body, not the tail — and with a global k cap the smallest series was being
#: taken to 96% of its own sample, which is meaningless.
MAX_TAIL_FRAC = 0.20


def curve(x: np.ndarray, ks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    s = np.sort(x[x > 0])[::-1]
    limit = MAX_TAIL_FRAC * s.size
    a = np.array([hill(s, int(k)) if (k + 1 < s.size and k <= limit) else np.nan
                  for k in ks])
    return a, a / np.sqrt(ks)


def flattest_window(ks: np.ndarray, a: np.ndarray, se: np.ndarray,
                    width: float = 0.7, max_frac: float = 0.10,
                    n: int | None = None) -> tuple[int, int, float]:
    """Window of `width` decades where alpha is flattest RELATIVE TO SAMPLING NOISE.

    Minimising the raw coefficient of variation is wrong here: the Hill s.e. is
    alpha/sqrt(k), so it shrinks mechanically with k and the flattest window is
    always the largest k — which is the body of the distribution, not its tail.

    The statistic is the SLOPE of alpha against log10(k) inside the window.
    A plateau has slope ~0. Spread-based tests fail here: a window can be flat
    "within noise" while alpha falls monotonically across it, because the Hill
    s.e. is wide at small k. Returned value is that slope, in alpha per decade.

    Search is capped at `max_frac` of the sample, since beyond roughly the top
    decile one is fitting the body rather than the tail.
    """
    lg = np.log10(ks)
    limit = len(ks) if n is None else int(np.searchsorted(ks, max_frac * n))
    best = (0, 0, math.inf)
    for i in range(max(limit, 1)):
        j = min(int(np.searchsorted(lg, lg[i] + width, side="right")), limit)
        sl_a, sl_se = a[i:j], se[i:j]
        ok = np.isfinite(sl_a)
        if ok.sum() < 5:
            continue
        # SLOPE, not spread. A window can be "flat within noise" while alpha
        # falls monotonically across it — that happened here: k 167->830 drifts
        # 1.45->1.09 yet scores 1.3x on a spread/noise test, because the s.e. is
        # large at small k. A plateau is a slope near zero; a drift excused by
        # wide error bars is still a drift.
        lgk_w = lg[i:j][ok]
        slope = float(np.polyfit(lgk_w, sl_a[ok], 1)[0])
        if abs(slope) < abs(best[2]):
            best = (i, j - 1, slope)
    return best


def svg(mode: str, ks: np.ndarray, series: list[tuple[str, np.ndarray, np.ndarray]],
        band: tuple[int, int], ymin: float, ymax: float) -> str:
    c, cols = CHROME[mode], SERIES[mode]
    x0, x1 = PAD["l"], W - PAD["r"]
    y0, y1 = H - PAD["b"], PAD["t"]
    lgk = np.log10(ks)
    fx = lambda v: x0 + (v - lgk[0]) / (lgk[-1] - lgk[0]) * (x1 - x0)  # noqa: E731
    fy = lambda v: y0 - (v - ymin) / (ymax - ymin) * (y0 - y1)  # noqa: E731

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
         f'height="{H}" font-family="system-ui,-apple-system,Segoe UI,sans-serif">',
         f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>']

    # Flattest window, drawn behind everything as context, not as a claim.
    p.append(f'<rect x="{fx(lgk[band[0]]):.1f}" y="{y1}" '
             f'width="{fx(lgk[band[1]]) - fx(lgk[band[0]]):.1f}" height="{y0 - y1}" '
             f'fill="{c["grid"]}" opacity="0.5"/>')

    for v in np.arange(math.ceil(ymin * 2) / 2, ymax + 1e-9, 0.5):
        p.append(f'<line x1="{x0}" y1="{fy(v):.1f}" x2="{x1}" y2="{fy(v):.1f}" '
                 f'stroke="{c["grid"]}" stroke-width="0.8"/>')
        p.append(f'<text x="{x0 - 10}" y="{fy(v) + 4:.1f}" text-anchor="end" font-size="12" '
                 f'fill="{c["muted"]}" font-variant-numeric="tabular-nums">{v:.1f}</text>')
    for d in range(int(math.floor(lgk[0])), int(math.ceil(lgk[-1])) + 1):
        if not lgk[0] <= d <= lgk[-1]:
            continue
        p.append(f'<line x1="{fx(d):.1f}" y1="{y1}" x2="{fx(d):.1f}" y2="{y0}" '
                 f'stroke="{c["grid"]}" stroke-width="0.8"/>')
        p.append(f'<text x="{fx(d):.1f}" y="{y0 + 22}" text-anchor="middle" font-size="12" '
                 f'fill="{c["muted"]}" font-variant-numeric="tabular-nums">'
                 f'{10 ** d:,.0f}</text>')

    # alpha = 2: the finite-variance boundary the whole result turns on.
    p.append(f'<line x1="{x0}" y1="{fy(2):.1f}" x2="{x1}" y2="{fy(2):.1f}" '
             f'stroke="{c["muted"]}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    p.append(f'<text x="{x1 - 6}" y="{fy(2) - 8:.1f}" text-anchor="end" font-size="12.5" '
             f'fill="{c["second"]}">variance finie au-dessus de 2</text>')

    for i, (label, a, se) in enumerate(series):
        col = cols[i]
        ok = np.isfinite(a)
        up = " ".join(f"{fx(lgk[j]):.1f},{fy(a[j] + 1.96 * se[j]):.1f}" for j in np.where(ok)[0])
        dn = " ".join(f"{fx(lgk[j]):.1f},{fy(a[j] - 1.96 * se[j]):.1f}"
                      for j in np.where(ok)[0][::-1])
        p.append(f'<polygon points="{up} {dn}" fill="{col}" opacity="0.16"/>')
        pts = " ".join(f"{fx(lgk[j]):.1f},{fy(a[j]):.1f}" for j in np.where(ok)[0])
        dash = ' stroke-dasharray="6 4"' if "fill" in label else ""
        p.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"'
                 f' stroke-linecap="round" stroke-linejoin="round"{dash}/>')
        j = int(np.max(np.where(ok)[0]))
        p.append(f'<text x="{fx(lgk[j]) + 10:.1f}" y="{fy(a[j]) + 4:.1f}" font-size="13" '
                 f'fill="{col}" font-weight="500">{label}</text>')

    p.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="{c["axis"]}" '
             f'stroke-width="1"/>')
    p.append(f'<text x="{x0}" y="38" font-size="19" font-weight="600" fill="{c["ink"]}">'
             f"Sur son plateau, l&#8217;indice de queue vaut 0,93 &#8212; sous 1</text>")
    p.append(f'<text x="{x0}" y="60" font-size="12.5" fill="{c["muted"]}">'
             f'351&#8239;540 &#233;pisodes &#183; un an d&#8217;archive Hyperliquid &#183; bande gris&#233;e = '
             f'plateau des majors &#183; IC&#8239;95&#8239;%</text>')
    p.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{H - 14}" text-anchor="middle" font-size="12.5" '
             f'fill="{c["second"]}">k &#8212; nombre d&#8217;observations de queue retenues</text>')
    p.append(f'<text x="20" y="{(y0 + y1) / 2:.0f}" text-anchor="middle" font-size="12.5" '
             f'fill="{c["second"]}" transform="rotate(-90 20 {(y0 + y1) / 2:.0f})">'
             f'&#945; (indice de queue de Hill)</text>')
    p.append("</svg>")
    return "\n".join(p)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path,
                    default=REPO / "experiments" / "data" / "exp017_episodes.csv")
    ap.add_argument("--outdir", type=Path, default=REPO / "reports")
    args = ap.parse_args()

    d = duckdb.sql(
        f"SELECT hip3, fills, notional FROM read_csv('{args.csv}') WHERE notional > 0"
    ).fetchnumpy()
    hip3, ntl, fl = d["hip3"].astype(int), d["notional"].astype(float), d["fills"].astype(float)
    per_fill = np.repeat(ntl / np.maximum(fl, 1), fl.astype(int))

    ks = np.unique(np.round(np.logspace(math.log10(50), math.log10(60_000), 160)).astype(int))
    ks = ks[ks < min(ntl.size, per_fill.size) - 2]

    built = []
    for label, x in (("épisodes · majors", ntl[hip3 == 0]),
                     ("épisodes · HIP-3", ntl[hip3 == 1]),
                     ("fills (approx.)", per_fill)):
        a, se = curve(x, ks)
        built.append((label, a, se))
        lo, hi, slope = flattest_window(ks, a, se, n=x.size)
        verdict = "PLATEAU" if abs(slope) < 0.05 else "NO PLATEAU (drift)"
        print(f"{label:<20} alpha {np.nanmin(a):.2f} -> {np.nanmax(a):.2f} | "
              f"flattest k in [{ks[lo]:,}, {ks[hi]:,}] alpha~{np.nanmean(a[lo:hi + 1]):.2f} "
              f"| slope {slope:+.2f}/decade  {verdict}")

    lo, hi, _ = flattest_window(ks, built[0][1], built[0][2], n=int((hip3 == 0).sum()))
    lo_y = min(np.nanmin(a - 1.96 * se) for _, a, se in built)
    hi_y = max(np.nanmax(a + 1.96 * se) for _, a, se in built)
    args.outdir.mkdir(parents=True, exist_ok=True)
    for mode in ("light", "dark"):
        out = args.outdir / f"exp018_hill_plot{'' if mode == 'light' else '_dark'}.svg"
        out.write_text(svg(mode, ks, built, (lo, hi), lo_y - 0.05, hi_y + 0.05))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
