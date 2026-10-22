# TradingView export index

Drop CTZB chart exports here. One file per symbol/timeframe, named
`<SYM>_<TF>_tv.csv` (e.g. `BTC_2D_tv.csv`). Overwrite in place when you
re-export — the filename is the key, no dates in it. Committing them means
they survive the conversation and every later session can read them without
a re-upload.

## What is here

Subfolders: `btc_binance/` (BTC 1D+2D, different layout, stale, no flag
columns), `alts/` (ADA, BNB, XRP 2D), `wgmi/` (the liquidity export). Each has
a README saying what it can be used for. The table below is the main ETH set.

| Chart | ETH | BTC |
|---|---|---|
| 1D  | yes (to 2026-10-21) | **missing** |
| 2D  | yes (to 2026-10-20) | **missing** |
| 3D  | yes (to 2026-10-20) | **missing** |
| 5D  | yes (to 2026-10-20) | **missing** |
| 8D  | yes (to 2026-10-20) | **missing** |
| 10D | yes (to 2026-10-20) | **missing** |
| 12D | yes (to 2026-10-20) | **missing** |
| 15D | yes (to 2026-10-20) | **missing** |
| 1W  | yes (to 2026-10-19) | **missing** |
| 1M  | yes (to 2026-10-01) | **missing** |

BTC "missing" above means *in this layout*. See `btc_binance/` for what exists.

## What these are for

The engine computes CT RSI, Stoch, buckets and signals itself from the
candles in `../`. The exports are not inputs to it — they are the
verification layer:

1. **The Signal line.** Column 10 is the orange line on the chart. Fitted
   as `ta.ema(ct_rsi, 14)` with zero error over 1,879 ETH 2D bars. Without
   an export there is no way to confirm that on a chart we have not seen.
2. **Flag agreement.** Columns 13-17 (diamond) and 18-22 (prime) let us
   check the engine against what the chart actually painted. 65/65 diamond
   flags and 36/36 prime flags matched on the ETH set.
3. **Live state.** The most recent bar of an export is the only way to read
   the current CT/Signal gap without re-deriving it.

## Export settings

Chart with the CTZB indicator on it → the three-dot menu on the indicator
pane → Export chart data → CSV, **ISO time**, all plots included. 23 columns
is correct. Do not add MFI to the export; nothing reads it.

## Column map (positional — the headers vary)

| Index | Contents |
|---|---|
| 0-4 | time, open, high, low, close |
| 8 | charts-signalling |
| 9 | **CT RSI** (purple) |
| 10 | **Signal** = EMA(14) of CT RSI (orange) |
| 11-12 | Stoch K, Stoch D |
| 13-17 | diamond rows T/S/N/L/H — only N populates |
| 18-22 | prime rows — only the middle row populates |

**Flags are stamped on the ENTRY bar, not the trough bar.** Line them up
against `s['edate']` from `engine.signals()`, not `s['date']`, or they look
like noise.
