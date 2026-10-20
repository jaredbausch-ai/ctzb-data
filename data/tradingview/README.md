# TradingView exports — 19 Oct 2026

The five files Jared exported with the CTZB indicator and MFI both applied.
Columns are positional, and several names repeat (`Plot` three times, `Signal`
twice), so read them by index, not by header name:

| index | column |
|---|---|
| 0–4 | time, open, high, low, close |
| 8 | charts signalling within the window |
| 9 | CT RSI |
| 11, 12 | Stoch %K, %D |
| 13–17 | diamond rows T/S/N/L/H |
| 18–22 | prime dot rows T/S/N/L/H |
| 23, 24, 25 | MFI, its signal line, histogram |

Two uses. First, MFI here is computed on **real volume**, which `data/*.csv`
does not carry — this is what made the money-flow test possible without the
backfill. Second, columns 9 and 11 are TradingView's own values for the
indicator, so they cross-check the engine directly: mean absolute difference
on ETH 2D is 0.037 on CT RSI over 1,891 bars and 0.076 on Stoch %K, with a
few larger gaps traceable to 2D bar-boundary differences.

ETH 1D only reaches back to 2020-01-27; TradingView caps export length. The
others start 2016.

Do not glob the uploads folder to refresh these. It holds many older exports
of the same timeframes plus 240 (4H) and 720 (12H) files, and a careless glob
silently overwrites one timeframe with another version. Copy by exact filename.
