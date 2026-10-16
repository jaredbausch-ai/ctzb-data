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

## Rescoring the dashboard

`refresh.py` turns the candles into the ten datasets behind the ETH Setup
Odds dashboard:

```
python refresh.py --data data --out datasets
```

It writes `status`, `buy`, `live`, `levels`, `setups`, `tier`, `walkforward`,
`years`, `confluence` and `invalidation` as CSVs, and prints a summary of the
regime, what is forming on each chart, and the next buy dates.

`engine.py` and `regimes.py` sit beside it. The date comes from the clock;
`--today YYYY-MM-DD` overrides it for testing.

### The traded tier is derived, not stored

`--tier` decides which chart-and-tag combinations get traded. Nothing is
written back to the repo and nothing drifts between runs.

| mode | the tier is | |
|---|---|---|
| `walkforward` | as it stood on 1 January of the current year | default |
| `current` | reselected from all data to date | |
| `frozen` | whatever `keep.json` says | for reproducing an old run |

`walkforward` is the default because it is the rule the walk-forward test
actually measures: pick the tier in January from data available by then, then
trade it blind for the year. It needs no maintenance and rolls over on its
own. `current` is the better estimate of today's odds, but it can change
mid-year and it is not what was validated.

As of October 2026 the two agree exactly, at 13 setups. They can diverge when
a setup crosses the 70% line partway through a year, and `walkforward` is then
the one to trust, since mid-year you could not have known.

`keep.json` is kept only for `--tier frozen`, and its twelve setups are now
out of date — it was written before the horizon fix below.

### Only completed trades are scored

`fw()` returns nothing unless the full 60-day horizon has elapsed. Without
that rule a trade opened three weeks ago was scored on the days available, so
it counted as a win or a loss according to whatever the market had just done.
Ten of 593 trades sat on windows as short as one day, all reading as losses
because ETH was falling.

The bias was not cosmetic. ETH 1D hollow stood at 76% on 21 completed trades
and was being dragged under the 70% cut by two 2026 entries with 41 and 28
days elapsed, which is the only reason the two tier modes ever disagreed.

The invalidation pool skips trades still in flight for the same reason: they
have no final peak or dip to put in a band.

Trades per year divides by the span from the first trade to the last date a
trade could have been scored, not to the last trade taken. Ending it at the
last trade drops a quiet recent stretch out of the denominator and overstates
the frequency.

### Candidate tags

Tier selection and the walk-forward choose from the same eleven candidate
tags, `diamond+dot` included. Two earlier scripts disagreed on this — the
walk-forward omitted that tag — which is why the pooled "All 70%+ setups" row
reads 90 trades at 66% rather than 88 at 67%. The confluence rows, 77% at 3+
charts agreeing and 75% at 4+, are unaffected.

## Figures as of 16 October 2026

Regenerate with `python refresh.py --data data --out datasets` to confirm.

| | |
|---|---|
| Troughs scored across the five ETH charts | 583 |
| Traded tier | 13 setups |
| Tier trades | 150, 15.0 a year |
| Tier win rate | 75% |
| With 3+ other charts agreeing | 98 trades, 81% |
| Walk-forward, all setups | 90 trades, 66% |
| Walk-forward, 3+ agreeing | 47 trades, 77% |
| Walk-forward baseline | 59% |
| Invalidation pool | 559 setups |

### Agreement count

A chart "agrees" when it printed a trough within ten days. That is now scored
against all five charts; an earlier version counted only the charts it had
already loaded, which under-reported agreement for the shorter timeframes.
