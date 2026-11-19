# Audit 46: numbers and labels on the member site, against raw prices

Code frozen at 0185de1. I wrote every figure with my own code (`mylib.py`, `chk.py`, `page.py`). The only pipeline code I imported is `regimes.rsi_regime` for the gate. Thresholds are tested exactly in decimal on the candle prices. Shares are tested on exact fractions. Medians are taken exactly, then rounded once (half away from zero).

These are entry-quality figures for computed signals. None of them is a fill, a strategy return or a track record.

## Top line

| Group | States | Comparisons | Disagreements: rows | Distinct figures | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| (A) Two frozen states (REPLAY 2026-11-12T04:14Z, CURRENT 2026-11-19T19:15Z) | 2 | 53,320 (data 52,272, page 1,048) | 0 | 0 | 0 | 0 |
| (B) Replays of real dates, Sep 2020 to Nov 2026 | 466 | 7,904,894 (data 7,857,417, page 47,477 in 159 replays) | 0 | 0 | 0 | 0 |
| (B) Envelope tests: clock on D+1 with candles ending on D | 3 | all three failed closed (`cards_withheld` true, no cards, no live signals) | 0 | 0 | 0 | 0 |

## Every disagreement

None. `disagreements.csv` holds only its header.

Two page rows were raised in group B by my own checker, in the replays of 2020-11-02 and 2020-12-27. In both, the "On track" list had several signals with the same day count, and the page orders those ties in feed order. Neither row is a figure. I fixed the checker after those two replays: it now compares the list as a set and checks the day order separately. The summary counts both rows as agreeing.

## Checks declared before the results (counts: A / B)

| # | Check | A | B |
|---|---|---|---|
| 0 | Data. Each daily file starts on the exchange's first day and misses no day. The last bar is today's. Every 2D-8D file equals my own bucketing of the daily candles (1 January restart). The served `candles_*.csv` files equal the last 70 bars. The example's static 2-day file equals my bucketing, its entry bar closes on 22 Sep 2024 at the entry close, and its last bar holds day 60. | 54 | 11,589 |
| 1 | Ledger. Membership (graded charts, gate on at the trough, day 60 closed, ETH only with funding: a value on the day, 60 of the prior 90 days, and 5 of 7 days in each funding_mean window). Every column: entryPrice, low, tags with the EPS guard, the grade's whole-sample odds, yes/no flags, the four 6-place measures, daysToHigh, year, scaled20, and all seven odds-on-the-day columns. dayScaled20 leaves out signals without a year of volatility. | 46,056 | 6,758,923 |
| 2 | `grade_odds`: every field of the A+/A/B/C rows, and the two ETH diamond-or-prime-dot rows (computed from tags) | 136 | 31,688 |
| 3 | `if_it_misses` per asset and grade, and `example_if_it_misses`, from 6-place values | 172 | 38,403 |
| 4 | `odds_fade`. I rebuilt the walk-forward tier from chart bars as of 1 Jan, then recomputed the bands, the day-10 rows, the after_day10 fields and their aliases, the edge against 70% on the exact share, `tier_fixed_on`, and `trades_a_year` with its alias. | 106 | 24,180 |
| 5 | Every card (forming, live and example). Checks: which cards exist; sample rule, wording and n; every share; exact and rounded medians; eras; timing; the from-entry row and the four ladder rows (shown and exact); low_date; low_day; confirms_on by the bar rule; bars_to_confirm; must_close_above (my exact inverse RSI, rounded down); price_now; entry_close. | 3,154 | 472,511 |
| 6 | `open_signals`: ids, dates, days_elapsed, day10/30/60 on closed bars only, best/worst, edge level and status. `prints`: the last 3 per chart plus the forming low, its tags and the gate note. Top level: schema 6, bar 70, `scored_as_of`, `market_regime` (my gate today). | 1,018 | 195,119 |
| 7 | `past_paths` and `example_past_paths`: n, and the q25/median/q75 for every day 0-60 | 1,348 | 253,511 |
| 8 | Page (Playwright, clock at generated_at + 6 min). Checked: every picker button; the card on each one and the example; on the Chart tab, the vertical lines by date (Entry/Today/Latest bar, Confirms, Day 60, high day), the entry and +10% line positions (axis scale, and at the alert the example uses only the bars up to entry), the price tags, the edge line, the ladder bands with their n, the candle count at the alert versus what happened, the low marker, the side box, the cloud, and "What this one did"; the Past signals tab (all/ETH/BTC rows and summaries); Previous signals; the quiet card's "about N times a year"; the bar on How to read; the banner; the footer | 1,048 | 47,477 |
| 9 | Labels against meaning: every feed `label` is the computed-signal text. I also read every rendered page sentence that uses trade/return/profit/result/fill words. | 228 | 71,493 |
| 10 | Entry quality only. Every such sentence is either a disclaimer ("computed, never traded", "not a return or a track record") or about the lead trader's own trades (definitional note n). | pass | pass |

## Coverage of group B (466 real dates, 2020 to 2026, 20 at clock times from 00:00:30 to 23:59)

| Kind of state | Replays |
|---|---|
| Market filter off (feed `market_regime` Bearish) | 197 (40 chosen for it) |
| First and last day of each filter episode, and the days either side (6 flips: 2021-06-08, 2021-08-19, 2022-01-27, 2023-01-25, 2025-12-05, 2026-09-02) | 24 |
| Within a forming low's reach of a flip (taken as F−2 to F+31, which covers the 8D reach) | 204 |
| Year-ends, 26 Dec to 4 Jan, 2020/21 to 2025/26 | 60. Includes 75 forming-card checks of a confirms_on date in 1-8 January (the bar rule across the year-end) |
| A top-grade forming card in the feed | 97 (73 dates chosen for it) |
| Nothing live or forming on any of the 10 charts | 37 (pre-scanned with my engine) |
| 60th day in progress, and the day after it closes (20 signals) | 20 + 20 |
| Day just after a confirmation (best/worst "n/a" with no closed bar) | 15 (137 such live rows across B) |
| Live top-grade signal in the feed | 250 |
| Worked example present / absent (absent before 22 Nov 2024, as specified) | 135 / 331 |

Figures exercised across B:

| What | Count |
|---|---|
| must_close_above, non-null | 647 (page: 85 exact and 78 "about … an estimate") |
| bars_to_confirm 0 / 1 / 2 | 339 / 308 / 333 |
| edge_status lost / rose10 / intact | 4,394 / 2,018 / 856 |
| Sample rule 1 / 2 / 3 | 2,374 / 2,708 / 3,301 |
| Quiet card per-year text | 7 |
| "What happened" labels | 100 |
| Header reading "off" | 89 |

## Testing my checker with planted errors (copies of CURRENT; baseline with nothing planted gives 0)

| Checker | Caught |
|---|---|
| Data checker | 40 of 40 plants, each by the one check aimed at it. Covered: card and ladder values, a 1e-6 change to an exact median, must_close_above +1 cent, low_day, bars_to_confirm, open-signal fields, edge status, example sample text, grade_odds, misses, odds_fade value/alias/edge/tier date, past paths, print tags and note, trades_a_year, a label, market_regime, and 10 ledger edits (a 1e-6 change to a measure, odds-on-the-day, tags, a deleted row, low date, entryPrice) |
| Page checker | 15 of 16. Covered: feed and ledger values as displayed; the Day 60 line one day early; the axis margin; the footer date; the Previous signals order; pxAt rounding down; the edge tested on a different share; the +10% level |

The one page plant not caught was scaling the example's "At the alert" chart with the later bars. On this example it changes nothing: the axis is set by the typical-high level ($3,485.15) and entry × 0.8, and the realised high ($3,448) and low sit inside both.

## Definitional notes (taken as given, not counted)

(a)-(al) as listed in the brief. The repo does not contradict its own stated choice for any of them. Specifics that bear on these numbers:

- My walk-forward tier, as of 2026-01-01, agrees with the feed's odds_fade on every replay. For the CURRENT state it is: ETH 1D hollow; 2D diamond/hollow/prime dot; 3D prime dot; 5D any/A/B/diamond/prime dot/zone-exit B; 8D any/C (g).
- A forming low allows a later bar equal to the trough's CT (refresh.py's provisional rule). A confirmed pivot needs strictly higher. No case changed a figure.
- 25.3% is taken as the typed definition (y), not re-derived.

Not checked (out of scope):

- Grades, lenses and the confluence cells/windows (h)
- The HTF-divergence grade rows (h)
- `next_buy_date` (al)
- Alerts, `candle_check` and the seal (ai)
- The lead-trader file (n)

## Doc sentences that contradict the code

None noticed in what I read (FEED_SPEC, CARD_SPEC, the CONTEXT sections named in the brief).

## Files

All in this folder.

- `all_checks.csv`: group A row by row, plus one row per group-B replay. Each replay's own rows are in `out/B/<date>[_page].csv.gz`.
- `disagreements.csv`: empty.
- `out/B_summary.csv`: one line per replay, with its kinds.
- `progress.log`
- Code: `plan.py`, `drive.py`, `coverage.py`, `plant.py`, `plant_page.py`, `words.py`
