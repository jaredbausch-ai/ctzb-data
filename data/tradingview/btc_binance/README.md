# BTC exports — Binance BTCUSDC, different layout

Rescued 22 Oct 2026 from session uploads. These are **not** the same shape as
the ETH exports one level up.

| | ETH exports | these |
|---|---|---|
| CT RSI | column 9 | **column 8** |
| Signal | column 10 | **column 9** |
| Stoch K / D | 11, 12 | 10, 11 |
| diamond / prime rows | 13-22 | **absent** |
| extra | — | MACD, histogram, WGMI projection/direction/timing |

Three caveats before using them:

1. **Binance BTCUSDC, not Coinbase BTCUSD.** `data/BTC_*.csv` is Coinbase.
   Prices and bar boundaries differ; do not line these up bar-for-bar against
   the engine's candles.
2. **Stale.** 1D ends 2026-09-21, 2D ends 2026-09-20.
3. **No flag columns**, so they cannot verify diamond or prime alignment the
   way the ETH exports do.

## What they did settle

**The Signal line is `ta.ema(ct_rsi, 14)` on BTC too — confirmed 22 Oct 2026,
zero error.**

| chart | bars compared | max error |
|---|---|---|
| BTC 2D | 1,113 | 0.00000 |
| BTC 1D | 2,228 | 0.00000 |

EMA(13) and EMA(15) both miss by ~0.9 max, so the 14 is exact and not a
coincidence of smoothing. Before this the formula had only been fitted on ETH
2D and the BTC Signal line was inferred. It is now verified on both assets.

A current Coinbase BTC export in the full 23-column CTZB layout is still
wanted — see `../INDEX.md`.
