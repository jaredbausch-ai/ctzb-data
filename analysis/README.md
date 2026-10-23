# analysis/

Generators that produced numbers someone looked at twice. Committed because
scratch dies — two earlier generators were lost that way.

Run from the repo root with `python3 -I analysis/<script>.py`.

| file | what it does |
|---|---|
| `ctema_build.py` | Builds `ctema.json` — the CT-RSI-vs-Signal-line feature table. 1,015 records across 9 charts, 993 with complete 60-day outcomes. Per record: bucket, diamond, prime, CT, EMA(14), gap, slopes, episode age, cycle day, and up/ret/dd at 30/60/90 days |
| `ctema_grid.py` | Scores the 21 pre-declared features A–U pooled across charts. **The candidate list is declared in the file before it runs** — do not add a feature after seeing results |
| `ctema_wf.py` | Per-chart breakdown, year-by-year stability, and the walk-forward gate for the survivors |
| `RESULTS_ctema_grid.txt` | Full captured output of both, 22 Oct 2026, including every dud and inverse |
| `ctema.json` | The feature table itself, so the grid reruns without a rebuild |
| `board_filters.py` | Live board — current CT, Signal, gap, K and bucket on every chart, plus the last confirmed signal and its step |
| `weekly_stats.py` | ETH weekly signals off the TradingView export. Source of the −18.5% median MAE |
| `mfe.py` | Maximum favourable/adverse excursion and the confirmation-lag cost |
| `conf.py` | Cross-timeframe agreement, backward-only vs symmetric |
| `filters.py` | The earlier filter sweep, including the ones on the do-not-re-test list |
| `situation.py` | Conditional stats for the current setup shape |
| `newsetups.py` | What is forming and when it confirms |
| `twoweek.py` | Market-state rating at 14/30/60/90 days: regime-on base rates, nearest-neighbour analogs on CT/gap/K across 1D–5D, and a walk-forward skill test. Also lists signals since the regime turned on, read against the Tier 1 cells. Both declared blocks are in the docstring |
| `RESULTS_twoweek.txt` | Captured output of `twoweek.py`, 22 Oct 2026. **Walk-forward: no horizon shows skill over the base rate.** Blind replication agreed |
| `lastyear.py` | Replays the `twoweek.py` rating every day from 22 Oct 2025 to 21 Oct 2026 using only data knowable that day, and scores it: direction, Brier, calibration, middle-half band coverage, median miss. Gate-ON days are the primary result; gate-OFF days are rated against a gate-OFF pool as a labelled variant |
| `RESULTS_lastyear.txt` | Captured output of `lastyear.py`, 22 Oct 2026 |
| `RESULTS_2023.txt` | The same replay over 2023 (`--start 2023-01-01 --end 2023-12-31`), a full gate-on year |
| `forecasts_2023.csv`, `forecasts_late2025.csv` | One row per forecast from `lastyear.py --csv`: start price, forecast middle half and median, closest-match median and actual price, in dollars. Source of the line charts shown 22 Oct 2026 |
| `volrange.py` | Volatility-scaled forecast range: past outcomes expressed in units of their own 30-day volatility, rescaled by today's. Walk-forward 2019–2026 against the old range, with a declared accept/reject rule. **Adopted 22 Oct 2026** |
| `RESULTS_volrange.txt` | Captured output of `volrange.py`, including the acceptance check |
| `forecasts_vol_2023.csv`, `forecasts_vol_late2025.csv` | Daily old vs new range and median, in dollars, both assets, all horizons. Source of the vol-scaled charts |
| `fullhistory.py` | The adopted vol-scaled range over all of ETH history, gate ON and OFF (each against its own gate state), with a 5th–95th wide band and how far price breaks past it |
| `RESULTS_fullhistory.txt`, `forecasts_full_eth.csv` | Its captured output and every daily forecast, all horizons |
| `zone_dwell.py`, `RESULTS_zone_dwell.txt` | How many days BTC 2D CT RSI spends per visit in the bull (>=60), neutral and bear (<=40) zones, inside gate-on bull phases vs gate-off, per episode |
| `tagstats.py` | Entry-quality stats for one tag on one chart vs the chart baseline: drawdown from entry (whole window and before the peak), median return and upside, touch rates, days to peak, dead count, every signal listed. Daily-candle paths |
| `RESULTS_btc5d_hollowC.txt` | `tagstats.py --chart BTC_5D --bucket C --diamond hollow`, 22 Oct 2026. n=3 |
| `RESULTS_btc3d_hollowC_prime.txt` | `tagstats.py --chart BTC_3D --bucket C --diamond hollow --prime yes`, 22 Oct 2026. n=2, one still open |
| `xconf.py`, `RESULTS_xconf.txt` | Cross-asset confluence: ETH 1D / 2D signals with a BTC 3D signal already confirmed within 5/10/20 days, per year and inside ETH's own agreement |
| `ethbtc.py`, `RESULTS_ethbtc.txt`, `ethbtc_bars/` | CTZB on the ETH/BTC price ratio, 1D–8D, three gate variants, per tag vs all-days and vs plain oversold bars. `ethbtc_bars/` is rebuilt by the script |
| `gatefix.py`, `RESULTS_gatefix.txt` | Four declared overlays on the regime gate to fix the cycle-top blind spot, judged on the signals each removes. All rejected |
| `xmap.py`, `RESULTS_xmap.txt` | Every BTC chart into every ETH chart and back (32 cells), declared pass criteria. Two passed |
| `RESULTS_late2025.txt` | The same replay over 22 Oct – 31 Dec 2025 (`--start 2025-10-22 --end 2025-12-31`). Source of the late-2025 bars in the charts shown 22 Oct 2026 |

`ctema.json` is a build artifact. Regenerate it with `ctema_build.py` whenever
`data/` moves forward; the Action commits candles roughly six times a day, so
it goes stale.

## The guard that matters

`ctema_grid.py` exists in this form because of how the previous night's result
was produced — by poking at ETH 2D data already stared at for hours, which
returned 90% against a 43% baseline and collapsed to a pooled 67%/50% with 3 of
10 charts inverted. Declare the list, test every chart, report the failures
beside the hits. `docs/PRETRADE.md` has the full set of guards.
