# TradingView exports — 20 Oct 2026

Ten files Jared exported with the CTZB indicator applied, covering every ETH
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
| ETH_1W_tv.csv | 544 | 2016-05 | 2026-10-19 | 31 |
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

**The diamond and prime-dot columns are correct but incomplete.** They are
stamped on the ENTRY bar, not the trough bar — line them up against
`s['edate']` from `engine.signals()`, not `s['date']`, or they look like
nonsense. Lined up correctly they have zero false positives: across the eight
charts that carry flags, 67 of 67 diamond flags land on an engine entry bar and
66 of those 67 are bars the engine also calls a diamond; 38 of 38 prime flags
match. Only the scanner's row N populates — rows T/S/L/H export as zero because
TradingView serves only the series for the chart's own resolution.

What they are not is complete. They are a strict subset: on ETH 2D the engine
finds 35 diamonds under the RSI gate and the columns flag 19 of them, all
contained, and the same shape holds on every chart. The gap sits at the recent
end — the last flag is 2025-11-02 on 1D, 2025-10-16 on 2D, 2024-11-11 on 3D,
2025-04-21 on 5D, 2024-07-22 on 1W, 2025-04-23 on 8D, 2024-09-27 on 10D and
2025-05-01 on 12D,
in files that all run to October 2026. Either the plot series truncates, or the
columns carry the `inTradedSet` walk-forward tier rather than the raw tag —
unresolved, and it is the same mechanism behind the 17-vs-14 count Joe queried.
Until it is resolved, derive signals with `engine.signals()` and treat the
columns as confirmation where they exist, not as the record. Columns 9 and 11
are TradingView's own CT RSI and Stoch %K and cross-check the engine directly
(mean absolute difference on ETH 2D is 0.037 on CT RSI, 0.076 on Stoch %K).

**Do not glob the uploads folder to refresh these.** It holds many older
exports of the same timeframes plus 240 (4H) and 720 (12H) files, and a
careless glob silently overwrites one timeframe with another version. Copy by
exact filename.
