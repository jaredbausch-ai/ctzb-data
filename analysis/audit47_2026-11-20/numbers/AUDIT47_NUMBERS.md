# Audit 47: numbers and labels on real data

Independent audit of code frozen at commit 78d8276. Every figure was recomputed by my own code from the raw candles in `code/`, which imports `regimes.py` for the gate only. Nothing in the repo was edited. This work measures entry quality only: the data has no exit, so nothing here is a strategy return, a trade or a track record.

## Top line

| Group | States | Comparisons (rows) | Disagreements (rows) | Distinct figures disagreeing | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| A: two frozen states | current, replay_0414 | 54,254 | 1 | 1 | 0 | 1 |
| B: real-date replays | 315 | 5,460,243 | 2 | 1 (same label) | 0 | 2 |

No wrong figure was found in either group. The only disagreement is one wording issue. It appears in 3 states and is the same label each time.

## Every disagreement

| Group | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| A | current (gen 2026-11-20 00:23Z) | Now card ETH-1D-2026-11-22, note "Best setup forming today." | ETH 1D is called best (18/27 = 66.666667% rose 10%) | ETH 3D has the highest share (75/112 = 66.964286%) | Wording. Three forming cards all show 67%. The page ranks on the whole-percent field and breaks the tie by feed order, so the card labelled "best" is not the highest by the share it is ranked on. |
| B | 2026-09-13 04:14Z | same note, ETH-1D-2026-09-13 | ETH 1D 63.076923% | BTC 1D 63.414634% (both show 63%) | Same as above |
| B | 2026-11-19 00:00:30Z | same note, ETH-2D-2026-11-20 | ETH 2D 66.666667% | ETH 3D 66.964286% | Same as above |

Full rows are in `disagreements.csv`. Which card the page opens on is a layout choice (l). The finding is only that the word "Best" is false when the displayed shares tie.

## Checks declared before results, and counts (A rows / B rows, disagreements)

| # | Check | A | B | Disagree |
|---|---|---|---|---|
| 0 | Raw data: the last daily bar is today; there are no daily gaps (ETH 21-22 May 2016 excepted); every 2D-8D file equals my own bucketing of the daily candles; every signal's chart close equals the daily close on its entry date; each `candles_*.csv` equals the last 70 raw bars | 64 | 9,952 | 0 |
| 1 | Every ledger row: membership (graded chart, gate on at the trough, day 60 closed, and ETH funding present with 60 of the prior 90 days and 5 of 7 in both FCOOL windows), low, entryPrice, tags (exact CT/K, EPS), every forward measure, reached/surv10/scaled20, grade columns, the 7 odds-on-the-day columns | 47,900 | 4,641,230 | 0 |
| 2 | grade_odds, every field, including the two ETH "diamond or prime dot" rows (the HTF rows are out of scope under (h)) | 160 | 24,879 | 0 |
| 3 | if_it_misses (every asset/grade, every field) and example_if_it_misses | 174 | 25,957 | 0 |
| 4 | odds_fade, recomputed from refresh's tier rule on each chart's own bars: rows, n, +10%/+20% after day 10, aliases, edge against 70% on the exact share, tier_fixed_on, sample date; also trades_a_year and signals_a_year | 96 | 14,586 | 0 |
| 5 | Every card (forming, every open_signals[].card, example): sample rule and text, n, every share, exact and rounded medians, eras, timing, from_entry, the ladder (shown and exact), low_date, low_day, confirms_on (bar rule with the 1 January restart), bars_to_confirm, must_close_above (my own bisection, floored to the cent, never within 1e-6 cent of a cent boundary), price_now, entry_close, the edge; forming cards exist only on 1D-5D charts with the gate on at the trough; every live signal has a card | 3,138 | 371,185 | 0 |
| 6 | open_signals (ids, dates, days_elapsed, day 10/30/60 on closed bars only, best/worst, edge_level_pct, edge_status); prints (last 3 per chart plus any forming low, tags, regime note on the trough date, n bars to confirm); schema_version, posting_bar_pct, scored_as_of, market_regime | 1,268 | 180,708 | 0 |
| 7 | past_paths and example_past_paths: n, and all 183 quantiles per asset | 14 | 1,959 | 0 |
| 8 | Page (Playwright, harness as briefed, clock = generated_at + 6 min): header pill, banner, footer, picker buttons, every Live, Forming and example card (each line, tile, ladder row and its "gone" mark, era, pool), the Chart tab for every setup (title, subtitle, side boxes, live box, the 4 level lines' heights, which recover the axis scaling from only what was known at the alert, the price tags, edge line, ladder band labels and heights, Today/Entry/Confirms/High/Day-60 lines on the right bars, x-axis dates, grid labels, low marker, the example's "What happened" circles and "What this one did" box against daily candles, cloud median and band points, cloud note), Previous signals (both groups, order, badges), Past signals (All/ETH/BTC: every row's 9 cells, count line, summary boxes), the quiet card's "about N times a year", the stale/daily-close note, How to read "70% bar" | 1,410 | 185,666 | 0 |
| 9-10 | Labels vs meaning, and entry quality only. Automated: the "Best" label, card and side feet, the review banner. Manual: every label on the page was read against its definition | 30 | 4,121 | 3 (the wording issue above) |

On check 10, nothing on the page reads as a return, a trade taken or a track record. Every card, the chart side and the Past signals tab carry the "entry quality only / computed, never traded" text.

## Coverage of group B (315 replays, every one through tests/replay_at.sh with real candles and no file changed)

| Kind | Planned | Achieved in the replayed state |
|---|---|---|
| Within a forming low's reach of a filter flip (flip day to flip + 20, all 6 flips since Sep 2020) | 126 | — |
| First and last day of every filter episode, and the days either side (flips 2021-06-08, 2021-08-19, 2022-01-27, 2023-01-25, 2025-12-05, 2026-09-02) | 24 | — |
| Year-ends, 26 Dec to 4 Jan, 2020/21 to 2025/26 | 60 | — |
| Market filter off | 19 extra mid-episode dates planned | 111 replays read Bearish |
| Top-grade forming low | 39 candidate dates | 66 replays had a top-grade forming card |
| Nothing live or forming on any chart (my own scan) | 18 | 18 replays had no card, no open signal and no forming print |
| 60th day in progress / the day after it closes (20 top-grade signals) | 20 + 20 | — |
| Days just after a confirmation | 15 | — |
| Other clock times (00:00:30, 03:59:59, 08:13, 12:13, 16:13, 20:13, 23:59) | 12 | — |
| Clock on D+1, candles to D | 4 | All 4 failed closed: withheld, with no cards, live signals or example |
| Live top-grade setup present / worked example present | — | 188 / 93 replays |

## Test of my own checker (planted errors, `out/plant_results.json`)

I planted 29 errors in copies of the current state. 19 were in data, the ledger and the feed: 6th-decimal medians, a 1-cent must_close_above, low_day, a ladder count, a path quantile, odds-fade figures, trades_a_year, prints, the example, and a chart-file close. 10 were in the page's code: pxAt truncation, a swapped tile, Day 60 a day early, the record's Day 60 column, the Previous signals order, the edge text, the footer date, axis scaling, a ladder band n, and the cloud note day.

The first run caught 27 of 29. The two misses were plants with no effect on this data: one wrote low_day's true value, and one widened the example's alert axis, which its typical-high level already sets. I replaced both with plants that change something, and the second run caught 29 of 29.

## Definitional notes (not counted as disagreements)

(a) to (al) apply as briefed. These were exercised on real data:

- **(a) and (ad):** forming and live cards under an "off" header in the 114 flip-reach replays. The gate is read on low_date.
- **(b):** the flash-print clamp on all candles. The 2017 BTC and ETH clamps feed ledger membership measures.
- **(c):** low before high in every ladder and edge walk.
- **(d):** must_close_above "about" on 1-bar cases.
- **(e):** days_elapsed is the day in progress. The BTC 2D A+ of 21 Sep 2026 is on day 60 in the current state.
- **(f):** peaked_10 is 0.
- **(g) and (i):** the tier rule on chart bars, from 2016.
- **(j):** "known by then" means entry + 60 ≤ the date.
- **(m):** live cards are measured from the entry close and rebuilt each run.
- **(n):** the lead trader reads "unavailable", and a live chart draws no low marker.
- **(r):** "about N times a year" was checked on the quiet replays, for example 2023-01-28: 28 a year, 2020 to 2021.
- **(t), (u), (w), (x), (ac), (ae), (af) and (ah)** were all exercised as briefed.

## Doc sentences contradicting the code

None found within my scope.
