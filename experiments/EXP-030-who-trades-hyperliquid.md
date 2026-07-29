# EXP-030 — who actually trades Hyperliquid, and how

**Status:** run, 2026-07-29.
**⚠️ EXPLORATORY AND DESCRIPTIVE — NOT PRE-REGISTERED.** It answers "what do the biggest accounts
do?" and makes no causal claim. It is filed separately from the pre-registered record so the two
are not confused: nothing here was predicted in advance, so nothing here can be said to have been
tested.
**Author:** Thomas Erhel / Quasareum
**Data:** `node_fills_by_block`, six hours sampled across 2026-07-28/29, 32,201 distinct accounts.

---

## 1. Why this is answerable at all

The question "how do the successful operators on this venue actually work?" is normally guessed
at. On Hyperliquid it is measurable, because every fill in the node archive carries the account
plus four fields that decide the interesting questions:

| field | what it settles |
|---|---|
| `crossed` | maker or taker, fill by fill |
| `fee` | the fee **actually paid** — negative means a rebate was earned |
| `closedPnl` | realised P&L, position by position |
| `time` | inter-fill spacing, which decides manual versus automated |

**Privacy.** Vaults are public entities with published pages, so a vault would be named. Every
other address is hashed on output, the same discipline applied to this repository's history after
raw addresses were found in it.

## 2. The biggest accounts are not vaults — and the largest vault does not appear at all

Of the top 60 accounts by volume:

| role | count |
|---|---|
| `subAccount` | **36** |
| `user` | 18 |
| unresolved (API error) | 6 |
| **`vault`** | **0** |

And separately: **HLP — the protocol's own market-making vault, with roughly \$224M of account
value — has zero fills under its own address** in the inspected hour, absent from all 16,167
accounts that traded.

So vault addresses are not where trading shows up. The documentation offers the likely reason —
vaults "can delegate any number of authorized agents", and legacy vault actions are signed by a
master account with the vault address set as a field — but **the exact attribution path is not
established here**, and it should not be asserted. What is established is that ranking the tape by
volume does not surface vaults.

This reframes the original question. A vault is a **capital-raising wrapper**; the trading happens
under sub-accounts. Sub-accounts being 60% of the top of the distribution is the same fact from
the other side: large operations segregate strategies into separate addresses.

## 3. Is it manual?

No, and it is not close.

| | |
|---|---|
| median inter-fill gap, top 60 | **132 ms** |
| accounts with median gap under 1 second | **54 / 60** |

Several show a median gap of 0 ms — multiple fills within the same millisecond, which is one
marketable order sweeping several resting levels rather than several decisions.

## 4. Maker or taker? Both, at the very top

Median maker fraction is **64.6%**, but the spread is the finding, not the median. Among the
twenty-five largest accounts:

| | fills | volume | maker | gap p50 | fees | realised P&L |
|---|---|---|---|---|---|---|
| largest by volume | 175,977 | \$402M | 12.5% | 0 ms | +\$11,511 | **−\$445,155** |
| a pure taker | 4,262 | \$85M | 0.0% | 0 ms | +\$24,817 | **+\$276,327** |
| the biggest rebate earner | 52,793 | \$84M | 67.6% | 202 ms | **−\$9,821** | +\$103,820 |
| a pure maker | 22,211 | \$76M | 99.8% | 198 ms | −\$226 | +\$11,097 |
| a high-frequency maker | 109,599 | \$34M | 99.9% | 132 ms | −\$126 | +\$841 |

Both extremes are present and both include profitable accounts. There is no single template.

## 5. Most of them still pay

**48 of the top 60 pay net fees.** Only twelve earn a net rebate over the sample.

That is a measured barrier rather than an assumed one: the venue's base maker fee is positive —
the maker pays — so earning a rebate requires climbing the volume tiers, and most of the largest
accounts on the venue have not.

## 6. What this does not say, and the caveats are large

**`closedPnl` is realised on closes only, over six non-consecutive hours.** An account that opened
positions and held them contributes nothing to its own P&L column. The figures in §4 are therefore
partial, noisy, and must not be read as performance. The largest account's −\$445k is six hours of
realised closes, not a result.

**It says what they do, not why it works.** Knowing an account posts 99.8% maker at 200 ms
intervals does not say why its quotes are not adversely selected, and that is the hard part. It is
not in the fills.

**Six hours is a sample**, chosen to span the day rather than consecutively, but a sample.

**Six of sixty roles failed to resolve.** If any were vaults, §2's count is wrong by up to six —
stated rather than rounded away.

## 7. What it does say

Three things, for anyone considering running a book here:

1. **Automation is table stakes.** The top of this venue operates at 132 ms median spacing. There
   is no manual version of this.
2. **The structure is sub-accounts, not vaults.** A vault raises capital; it is not where the
   execution lives.
3. **The fee tier is a real barrier and most have not cleared it.** Eighty percent of the largest
   accounts on the venue still pay to trade.
