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

`ctema.json` is a build artifact. Regenerate it with `ctema_build.py` whenever
`data/` moves forward; the Action commits candles roughly six times a day, so
it goes stale.

## The guard that matters

`ctema_grid.py` exists in this form because of how the previous night's result
was produced — by poking at ETH 2D data already stared at for hours, which
returned 90% against a 43% baseline and collapsed to a pooled 67%/50% with 3 of
10 charts inverted. Declare the list, test every chart, report the failures
beside the hits. `docs/PRETRADE.md` has the full set of guards.
