"""Hayashi-Yoshida lead-lag estimation for asynchronously observed prices.

EXP-006 through EXP-009 measured lead-lag by binning both venues onto a grid,
which forced an unresolvable trade-off:

- a **fixed wall-clock grid** makes Hyperliquid look late for free, because its
  prints are sparser so its last-price-in-bin is staler than the CEX's;
- **Hyperliquid's own event grid** fixes that, but its step moves with activity
  (993 ms quiet, 361 ms volatile), and a finer grid exposes more asymmetry at an
  unchanged true lead. EXP-009 showed that artefact accounted for *all* of the
  apparent widening under stress.

Hayashi-Yoshida removes the choice. It never synchronises: it sums products of
returns whose observation intervals overlap, with one series shifted by a lag
`tau` in **milliseconds**. No bins, no resampling, no interpolation — and `tau`
is physical, so estimates are comparable across regimes and assets.

    U(tau) = sum_{i,j} dX_i dY_j * 1{ (t_{i-1}, t_i] intersects (s_{j-1}-tau, s_j-tau] }

The lead-lag is the `tau` maximising |U|. Sign convention here: **tau > 0 means Y
leads X** — Y's move at `t - tau` matches X's move at `t`.

Reference: Hoffmann, Rosenbaum & Yoshida, *Estimation of the lead-lag parameter
from non-synchronous data* (2013), building on Hayashi & Yoshida (2005).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LeadLag:
    """Result of a Hayashi-Yoshida scan."""

    taus_ms: np.ndarray
    corr: np.ndarray
    #: tau maximising |corr|, in milliseconds. Positive => Y leads X.
    peak_ms: float
    peak_corr: float
    n_x: int
    n_y: int

    def asymmetry(self) -> float:
        """Bounded follower index in [-1, 1]. Positive => X follows Y."""
        pos = float(self.corr[self.taus_ms > 0].sum())
        neg = float(self.corr[self.taus_ms < 0].sum())
        total = abs(pos) + abs(neg)
        return 0.0 if total == 0 else (pos - neg) / total


def _returns(ts: np.ndarray, px: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Log returns with their observation intervals (start, end]."""
    order = np.argsort(ts, kind="stable")
    ts, px = ts[order], px[order]
    keep = np.concatenate([[True], np.diff(ts) > 0])  # collapse same-timestamp prints
    ts, px = ts[keep], px[keep]
    r = np.diff(np.log(px))
    return ts[:-1].astype(np.float64), ts[1:].astype(np.float64), r


def hayashi_yoshida(
    ts_x: np.ndarray,
    px_x: np.ndarray,
    ts_y: np.ndarray,
    px_y: np.ndarray,
    taus_ms: np.ndarray,
) -> LeadLag:
    """Scan the HY cross-correlation over `taus_ms`. Positive tau => Y leads X.

    Complexity is O(n log m) per tau: for each X interval the overlapping Y
    intervals form a contiguous run once both are sorted, so the inner sum is a
    prefix-sum lookup rather than a nested loop.
    """
    ax, bx, rx = _returns(ts_x, px_x)
    ay, by, ry = _returns(ts_y, px_y)
    if rx.size < 50 or ry.size < 50:
        raise ValueError(f"too few returns: x={rx.size}, y={ry.size}")

    norm = np.sqrt((rx**2).sum() * (ry**2).sum())
    cum = np.concatenate([[0.0], np.cumsum(ry)])

    out = np.empty(taus_ms.size, dtype=np.float64)
    for idx, tau in enumerate(taus_ms):
        # Y's intervals shifted FORWARD by tau; overlap iff ay' < bx and ax < by'.
        # Forward, not back: if Y truly leads X by L, advancing Y by L is what
        # aligns the two, so the peak lands at tau = +L. Shifting back inverts
        # the sign — which the synthetic check in tests/ caught, and which would
        # otherwise have read as "Hyperliquid leads" with perfect confidence.
        ay_s, by_s = ay + tau, by + tau
        lo = np.searchsorted(by_s, ax, side="right")
        hi = np.searchsorted(ay_s, bx, side="left")
        hi = np.maximum(hi, lo)
        out[idx] = float(np.dot(rx, cum[hi] - cum[lo])) / norm

    peak = int(np.argmax(np.abs(out)))
    return LeadLag(
        taus_ms=taus_ms,
        corr=out,
        peak_ms=float(taus_ms[peak]),
        peak_corr=float(out[peak]),
        n_x=int(rx.size),
        n_y=int(ry.size),
    )
