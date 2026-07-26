"""Derived account identifiers for published datasets.

Liquidation records carry the liquidated account's address. Those addresses are
public on-chain — Hyperliquid publishes them and anyone can read the archive —
so this is not a confidentiality problem. It is a *compilation* problem: a
published CSV mapping 350k addresses to their losses is far more usable for
profiling than the same facts scattered across an archive, and no analysis here
needs the address itself. Every result depends on **grouping** by account, never
on which account it is.

`account_id` replaces the address with a truncated SHA-256 of it. Grouping,
counting and episode construction are unchanged, so every number is identical.

**What this does and does not do.** The hash is unsalted and therefore
deterministic: anyone can hash a known address and test whether it appears in
the dataset. That is deliberate — a salt would make the dataset irreproducible
by a third party, which matters more here than defeating a targeted lookup of
already-public data. What it removes is the browsable list. Do not describe the
result as anonymised.

Truncation is 16 hex characters (64 bits). At ~350k accounts the birthday
collision probability is on the order of 1e-8.
"""

from __future__ import annotations

import hashlib

_WIDTH = 16


def account_id(address: str) -> str:
    """Stable derived id for an account address. Deterministic, unsalted."""
    return hashlib.sha256(address.strip().lower().encode()).hexdigest()[:_WIDTH]
