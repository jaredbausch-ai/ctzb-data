# ETH/BTC ratio export

`ETHBTC_MCAP_3D_tv.csv` — Jared's TradingView export of CRYPTOCAP:ETH / CRYPTOCAP:BTC
on the 3D chart, 23 Oct 2026, 2017-07-12 to 2026-10-22. Named columns (CT RSI at
index 5, Signal at 6, Stoch %K/%D 7-8, diamond rows 9-13, prime rows 14-18, charts
signalling 19) — a different layout from the ETH exports.

This is the MARKET-CAP ratio: ETH price / BTC price x the supply ratio (5.7-6.2,
drifting slowly; 6.03 in Oct 2026). `analysis/ethbtc.py` builds the PRICE ratio
from the Coinbase candles instead; on this 3D export the two give 107 of 110
signals on the same dates, and the engine reproduces the export's CT RSI column
exactly (max difference 0.0004).
