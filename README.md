# CTZB price pipeline

Pulls daily candles from Coinbase's public market-data API and rebuilds the
multi-day bars the CTZB engine reads. Runs itself once a day; no exports and
no API key.

## What it writes

`data/ETH_1D.csv`, `ETH_2D`, `ETH_3D`, `ETH_5D`, `ETH_8D`, and the same for
`BTC`. Columns are `time,open,high,low,close`, one row per bar, oldest first.
`BTC_2D.csv` is what the regime filter runs on.

## Why it rebuilds rather than downloads

Coinbase serves 1D natively and nothing longer. TradingView builds its 2D, 3D,
5D and 8D bars by bucketing days **within each calendar year, restarting the
count on 1 January** — not from a fixed epoch. That rule was derived from the
TradingView exports and then verified against them:

| Chart | Bars matching | Signals matching |
|---|---|---|
| ETH 2D | 100% | 138 / 138 |
| ETH 3D | 100% | 88 / 88 |
| ETH 5D | 100% | 47 / 47 |
| ETH 8D | 100% | 24 / 24 |

Coinbase's daily candles were also checked against the same TradingView
exports: 68 of 68 open/high/low/close values identical to the cent.

## Rate limits

The public endpoint returns at most 300 candles per request, so the first run
pages backwards to 2016 and takes a few minutes. Later runs touch only recent
days. There is a 0.25s pause between requests and a retry with backoff.

## Schedule

01:20 UTC daily, after the day's candle has closed. Also runnable by hand from
the Actions tab.

## The last bar

The newest multi-day bar is usually still forming — its close moves until the
bucket fills. Comparing a rebuild against a TradingView export taken at a
different moment will therefore show exactly one differing bar, the last one.
That is expected, not a fault: 1,901 of 1,902 ETH 2D bars matched exactly, and
the single difference was the bar in progress.

Nothing downstream is affected. A trough needs three confirmed bars to its
right before the engine will call it, so an unfinished final bar can never
produce a signal — only a provisional one, which is the intended behaviour.

## Consuming it

The CTZB engine reads these files directly:

```python
import engine as E, regimes as R
reg = R.rsi_regime("data/BTC_2D.csv", 8, 13, 60, 41)
signals, bars = E.signals("data/ETH_3D.csv", regime=reg)
```
