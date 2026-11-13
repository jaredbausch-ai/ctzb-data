# Audit 23: numbers and labels on real data

Independent auditor, 13 Nov 2026. Every figure was recomputed with my own code (`code/`: own RSI, stochastic, pivots, bucketing, 60-day windows, ladder, medians, quantiles and rounding; `regimes.py` imported for the gate only). Price thresholds (+10%, +20%, −25.3%, −30%, ladder falls) were tested in exact decimal on the CSV prices. Grades and lenses were taken as given. Nothing in the repo was edited. These are computed signals, not fills. There is no exit in the data, so this audit covers entry quality only.

## Top line

| Group | States | Comparisons (rows) | Distinct figures | Disagreements (rows / distinct) | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| A: the two frozen states | 2 | 56,689 | 28,964 | **0 / 0** | 0 | 0 |
| B: replays of real dates | 286 | 5,421,698 | 210,283 | **0 / 0** | 0 | 0 |
| Outside the member list (feed field the page does not read) | 1 replay | 1 | 1 | 1 / 1 | 1 (`next_buy_date`) | 0 |

The page comparisons are part of these totals: 1,061 in A and 146,434 in B.

## Every disagreement

| Group | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| A | – | – | – | – | none |
| B | – | – | – | – | none |
| Outside | replay 2026-01-01 04:14Z | feed `next_buy_date` (status.csv). The member page does not read it | 2026-01-06 | 2026-01-10. The ETH 5D low of 22 Dec 2025 confirms at the close of the 6–10 Jan bar. Its trough is also gate-off, so it can never confirm as a signal | `refresh.ds_buy` uses the last bar's open plus step × bars needed. That gives the confirmation bar's OPEN date, with a fixed step (no 1 January restart) and no gate check. FEED_SPEC says it is "the date the next forming ETH tier low would confirm" |

## Checks declared before running (both frozen states; B ran the same checker)

1. Every ledger row: membership (gated, graded chart, 60th day closed, ETH funding rule), entryPrice, low date, tags, grade-odds columns, every forward measure to 6 places, yes/no flags, daysToHigh, year, scaled20, and the odds-on-the-day columns including dayN and dayScaled20.
2. grade_odds, every field, for A+/A/B/C per asset and both ETH marker rows. The two HTF-divergence rows are out of scope (h).
3. if_it_misses (every asset/grade row and field) and example_if_it_misses.
4. odds_fade: tier rebuilt with refresh.py's rule on each chart's own bars; bands and day-10 rows, both shares, n, aliases, the edge against 70% on the exact share, tier_fixed_on, and trades_a_year.
5. Every card (forming, each open signal's card, example_card), every field: dates (low_date, low_day, confirms_on by the year-restart rule), bars_to_confirm, must_close_above (my own exact RSI inversion, rounded down), price_now / entry_close, sample text and rule, n, all shares, exact and rounded medians, eras, timing, from_entry and ladder (shown and exact), edge. Also checked that cards exist exactly for gate-on forming lows on 1D–5D charts with a non-empty sample, and that every live signal has a card.
6. open_signals: membership, ids, dates, days_elapsed, day 10/30/60 (closed bars only), best/worst so far, edge_level_pct, edge_status. prints: last 3 per chart plus forming lows, with notes on the trough date and exact-CT/K tags. Top level: schema_version, posting_bar_pct, scored_as_of, market_regime, trades_a_year and signals_a_year. The computed-signal label on every card, print, open signal and grade row.
7. past_paths and example_past_paths: all 61 days, three quantiles each.
8. Page (Playwright, clock = generated_at + 6 min):
   - Header, banner, footer and lead panel.
   - Every picker button.
   - Each card: line, status line, big number, line under it, sample, key figures, misses and pool, 8 tiles, 5 ladder rows with "gone" marks, and eras.
   - Chart tab: title, subtitle, side box with prices built from entry and percentage, live box, level and ladder labels, edge label, low marker, Confirms label.
   - Chart positions: x of Entry/Today/Confirms/Day 60/High against the bar holding that date; y of four level lines against an axis built from what is shown at the alert. Candles drawn at the alert vs in "What happened".
   - Cloud: subtitle, day-60 note, 61 median points and 122 band points against my quantiles.
   - Example "What happened": side box, markers, its path, and the example chart file against the 2D candles.
   - Past signals (all/ETH/BTC): count line, summary boxes, every row, order.
   - Previous signals: both groups, badges, the 5 latest closed.
   - Quiet card and "about N times a year", How to read (bar).
9. Labels against meaning: each number above is compared under its own label, against the quantity that label names.
10. Entry quality only: I scanned all rendered text for trade/return/profit/track-record wording. Every hit is a disclaimer ("not a trade or a track record", "not a trading result") or describes the lead trader's own real trades (o). Nothing reads as a strategy return or a track record.

## Checks passed, by area (group A / group B)

| Area | A | B | | Area | A | B |
|---|---|---|---|---|---|---|
| ledger | 49,680 | 4,489,695 | | page card | 210 | 43,804 |
| open_signals (+ cards) | 3,036 | 374,946 | | page chart | 246 | 46,840 |
| past_paths | 980 | 140,140 | | page past signals | 566 | 49,148 |
| example_past_paths | 490 | 70,070 | | page picker / previous | 25 | 4,349 |
| prints | 512 | 78,144 | | page header, footer, read, lead | 14 | 2,002 |
| forming cards | 216 | 32,940 | | page example "What happened" / quiet card | – | 291 |
| example_card | 112 | 4,796 | | labels | 182 | 24,760 |
| grade_odds / if_it_misses / example misses | 296 | 42,328 | | odds_fade + top level | 124 | 17,445 |

All passed (failures: 0).

## Coverage of group B (286 replays, Sep 2020 to 13 Nov 2026, real candles, `tests/replay_at.sh`, no tampering; none withheld, none errored)

| Kind (declared in dates.json before running) | Asked | Run | Actually found in the replays |
|---|---|---|---|
| Market filter off | 40 | 40 | 119 states had the filter off; 35 showed a forming card under "Market filter: off" |
| First/last day of each filter episode and the days either side (flips 2021-06-08, 2021-08-19, 2022-01-27, 2023-01-25, 2025-12-05, 2026-09-02) | 24 | 24 | all |
| Year-ends, 26 Dec–4 Jan, 2020/21 to 2025/26 | 60 | 60 | all |
| Top-grade forming low | 40 | 58 candidates | 74 states held a top-grade forming card |
| Nothing live or forming on any chart | some | 12 | 19 states with no card, no live signal and no forming print |
| 20 signals: day 60 in progress / the day after it closes | 20 signals | 18 + 18 dates (two dates shared) | 63 states had a signal on day 60 |
| Day after a confirmation | – | 15 | all |
| Other clock times (00:00:30, 00:05, 00:20, 01:00, 03:59:59, 06:30, 12:00, 16:13, 20:43, 23:59) | – | 10 | all |
| Every date with a forming low whose trough's filter reading differs from today's | all | 60 (all found by my scan) | 15 with the filter on and a "regime off" forming note |
| Total, distinct dates/clocks | ≥180 | 286 | 610 forming cards, 956 live top-grade displays, 5,434 open-signal statuses (lost 3,372, rose10 1,464, intact 598); example present in all 82 post-22-Nov-2024 states and none of the 204 before |

Envelope test: three runs with the clock on D+1 and candles ending on D (2024-03-11 00:00:30, 2026-01-01 00:00:30, 2026-11-11 00:19). All failed closed: stack "today's bar is missing", cards_withheld true, no cards or live signals, page "Setups held back" (`failclosed.json`).

## Testing my checker (planted errors, `code/plant.py`, `plant_results.json`)

- **Data plants:** 32 single-figure errors in a copy of the replay state. Examples: +1e-6 on a 6-place measure, +1 cent, a tag flipped, a top-grade ledger row deleted, an edge_status flipped, a ladder exact share +1e-6, a sample count in the text, a path quantile +0.1, an odds-fade edge flipped, trades_a_year, market_regime. All 32 were caught.
- **Page plants:** 10 one-line edits to a copy of the page, with the feed untouched. Examples: the +10% level, the Day 60 line one bar late, the cloud median shifted, the 70% gone mark, the closed-through date, the misses count, the axis floor. All 10 were caught.
- **First round:** 39 of 42. One miss was my own matcher, which logged the deleted row under another key. The other two were plants that changed nothing visible on this data: a gone mark tested at 69%, and the at-the-alert axis using every bar. After fixing the matcher and replacing those two with visible plants: **42 of 42**.
- 22 early replays were re-run after I added three page checks (low marker, Confirms label, the example's path). All still agree.

## Definitional notes (known choices; not counted)

All of (a)–(ak) were respected as stated. The ones these states actually exercised:

- (a) 35 filter-off states showed a forming card under "Market filter: off", and 15 filter-on states had a forming low noted "regime off".
- (d) must_close_above for lows one bar from confirming.
- (e) "day N of 60" is the day in progress.
- (f) peaked_10_or_more = 0.
- (g)/(i) odds_fade tier and its in-sample label.
- (j) the example's "known by then" sample.
- (l) the page opens on the best forming card even when a live top-grade setup exists (replay_0414).
- (m) live cards read "as of the entry close"; (n) lead panel "unavailable"; (p) miss tiles name the asset/grade pool.
- (r) about N times a year; (t) n/a before a closed bar; (u)/(ab) example file static; (ac) Previous signals grouping; (ah) closed-through date.
- (w) rule 3 used under 15 (e.g. "all 33 past signals of the top grade across all BTC charts").
- (x) ledger acceptance, (z)/(ag) strict feed check, (aa) candle checks.
- Tie handling: no figure in any state landed on a decimal tie at its display digit. Exact-decimal thresholds and the pipeline's float thresholds never disagreed.

## Doc sentences that contradict the code (one line each)

- FEED_SPEC "Audit #22 corrections" says `open_signals[].confirmations` are "the grade lenses in plain words". The feed carries lens codes ("GAP + UP8 + BTCX + FASTCT", "-"); only the card's `confirmations` are plain words. The page does not show it.
- FEED_SPEC top level says `next_buy_date` is "the date the next forming ETH tier low would confirm". `refresh.ds_buy` gives the confirmation bar's open date with a fixed step and no gate check (see the outside row above).

Files: `all_checks.csv` (group A in full; group B one row per replay per area, with detail in `replays/<id>.csv.gz`), `disagreements.csv`, `dates.json`, `scan.json`, `progress.log`, `code/`.
