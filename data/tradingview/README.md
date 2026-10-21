# TradingView exports — 20 Oct 2026

Nine files Jared exported with the CTZB indicator applied, covering every ETH
timeframe the suite runs on. Columns are positional, and several names repeat
(`Plot` three times, `Signal` twice), so read them by index, not by header name:

| index | column |
|---|---|
| 0–4 | time, open, high, low, close |
| 8 | charts signalling within the window |
| 9 | CT RSI |
| 11, 12 | Stoch %K, %D |
| 13–17 | diamond rows T/S/N/L/H |
| 18–22 | prime dot rows T/S/N/L/H |

`engine.load()` reads these directly — it resolves the repeated headers — so
`engine.signals('data/tradingview/ETH_<tf>_tv.csv')` works without conversion.

## Coverage

| file | rows | starts | last bar | gated signals lifetime |
|---|---|---|---|---|
| ETH_1D_tv.csv | 1985 | 2021-05 | 2026-10-21 | 138 |
| ETH_2D_tv.csv | 1905 | 2016-05 | 2026-10-20 | 138 |
| ETH_3D_tv.csv | 1270 | 2016-05 | 2026-10-19 | 88 |
| ETH_5D_tv.csv | 763 | 2016-05 | 2026-10-18 | 48 |
| ETH_8D_tv.csv | 479 | 2016-05 | 2026-10-16 | 24 |
| ETH_10D_tv.csv | 385 | 2016-05 | 2026-10-18 | 20 |
| ETH_12D_tv.csv | 323 | 2016-05 | 2026-10-16 | 16 |
| ETH_15D_tv.csv | 260 | 2016-05 | 2026-10-13 | 14 |
| ETH_1M_tv.csv | 125 | 2016-05 | 2026-10-01 | 3 |

ETH 1D only reaches back to 2021; TradingView caps export length. The others
start 2016. 10D and above are too thin to carry their own odds — the table in
`odds.json` covers ETH 1D/2D/3D/5D and BTC 1D/2D only.

## Two things that will bite

**No MFI in this set.** The 19 October export carried MFI on real volume in
columns 23–25, which is what made the money-flow test possible without the
volume backfill. These nine do not have it. The MFI-bearing versions of
ETH 1D/2D/3D/5D/8D are preserved in git at commit `bf69ed6`; retrieve with
`git show bf69ed6:data/tradingview/ETH_2D_tv.csv`. The money-flow test itself
failed (money diamond 61% vs 60% base, and it degraded the existing tags), so
nothing open depends on it.

**The diamond and prime-dot columns are not a usable signal record.** Only
row N populates — the scanner's other rows (T/S/L/H) export as zero because
TradingView only serves the series for the chart's own resolution — and even
row N is sparse and stale. ETH 2D's last flagged bar in the export is
2025-10-16 despite the file running to 2026-10-20, and 15D and 1M carry no
flags at all. Derive signals with `engine.signals()` instead; columns 9 and 11
are TradingView's own CT RSI and Stoch %K and cross-check the engine directly
(mean absolute difference on ETH 2D is 0.037 on CT RSI, 0.076 on Stoch %K).

**Do not glob the uploads folder to refresh these.** It holds many older
exports of the same timeframes plus 240 (4H) and 720 (12H) files, and a
careless glob silently overwrites one timeframe with another version. Copy by
exact filename.
