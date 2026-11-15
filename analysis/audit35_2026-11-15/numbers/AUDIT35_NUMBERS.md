# Audit 35: numbers and labels on the member site, real data only

Independent recomputation from raw candles (my own RSI/Stoch/pivots, clamp, windows, ladder, medians, quantiles, odds-on-the-day, walk-forward tier, page formatting and price arithmetic; `regimes.py` imported for the gate only). Nothing in the repo was edited, committed or pushed. Entry quality only: there is no exit in the data, so none of these figures is a strategy return or a track record, and no signal here is a fill.

## Top line

| Group | States | Comparisons | Disagreements (rows) | Distinct figures | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| (A) frozen states (`replay_0414` at 2026-11-12T04:14Z, `current` at 2026-11-15T00:32:18Z) | 2 | 61,882 | 0 | 0 | 0 | 0 |
| (B) replays of real dates, 2020-09-01 to 2026-09-05 | 310 | 6,048,752 | 454 | 2 | 2 (feed fields, not shown on the page) | 0 |

## Every disagreement

| Group | State | Where | Shown | Yours | Cause |
|---|---|---|---|---|---|
| B | all 227 replays dated before 2024-11-22 (2020-09-01 to 2024-11-21) | feed `example_if_it_misses` | an object (e.g. 2020-10-07: figures from the ETH top-grade signals known on that date) | null | `extras_live.py` writes `missstats_example.csv` whenever any ETH top-grade ledger row has entry + 60 <= 2024-09-22, with no check that the worked example exists. FEED_SPEC: no worked example before 22 Nov 2024, and these fields are "the same figures for the worked example ... (the example card's sample)"; `example_card` is null in those replays, so the fields describe no card. The page does not show them (no example card means "Example unavailable"), so no member-visible figure is wrong. |
| B | same 227 replays | feed `example_past_paths` | an object (61 days of quartiles) | null | Same cause (`pastpaths_example.csv`, written whenever `pe["n"]` > 0). |

Detail: `disagreements.csv` (454 rows, one per replay and field). Nothing else disagreed, in either group, on data or page.

## What was checked (declared before results; numbers follow the brief)

1. Every ledger row: membership both ways, low, entryPrice, tags, grade-level columns, every forward measure (6-place values), yes/no columns, year, all seven odds-on-the-day columns (dayScaled20 without signals lacking a year of volatility).
2. `grade_odds` A+/A/B/C per asset, every field incl. `sample` and the alias (ETH flag rows out of scope, (h)).
3. `if_it_misses` (row set and every field) and `example_if_it_misses`.
4. `odds_fade`: tier re-selected by refresh.py's documented rule as of 1 January, bands/checks, counts, after-day-10 shares and aliases, edge marks on the exact share, `tier_fixed_on`; also `trades_a_year`/`signals_a_year`.
5. Every card (forming, open, example): existence rules (graded chart, gate on at trough date, non-empty sample, live signal has a card), sample rule and text, n, every share/median (shown and exact), eras, timing, from-entry row, ladder (shown/exact/fell-25.3%), low_date, low_day, confirms_on (bar rule, 1 Jan restart), bars_to_confirm, must_close_above (value rounded down, and RSI semantics: a close at it does not confirm, one cent above does), price_now, entry_close.
6. `open_signals` (set both ways, entry, tags, days_elapsed, day10/30/60 on closed bars, best/worst, edge_level_pct, edge_status), `prints` (set both ways, every field, notes, forming tags with EPS), top-level fields.
7. `past_paths` and `example_past_paths` (n, 61 x 3 quantiles).
8. The page (Playwright, routes and clock as briefed): header pill, banner date, footer; picker buttons; every card (state, lines, status line, dimming/colour, big number, sample line, stats, misses and pool, tiles, ladder rows and "gone" colour, eras, stale note, foot); Chart tab for every setup (title, subtitle, level labels, four price tags, edge label, ladder band texts and colours, x of Today/Entry/Confirms/Day 60/high-day lines against the bar holding that date, date-axis labels, candle count, entry-level y with axis scaled only by what was known at the alert, low marker and price, side box, live box, "What happened" box and markers checked against daily candles, cloud subtitle and note); Past signals all/ETH/BTC (count line, every row, order, summary boxes); Previous signals both groups; How to read bar; quiet card incl. "about N times a year"; "Example unavailable" before 22 Nov 2024. Also: chart files equal the last 70 scored bars; 2D-8D files equal daily candles bucketed; example chart file equals daily candles, entry bar and day-60 bar.
9. Labels vs meaning: each label above compared with what its number measures (no mismatch found).
10. Entry quality: full page text read on both frozen states; every card foot, Past signals heading and footnote say computed signals, not trades, entry quality only (no mismatch found).

## Checks passed, by number

| # | A comparisons | A disagree | B comparisons | B disagree |
|---|---|---|---|---|
| 1 ledger | 49,680 | 0 | 4,724,838 | 0 |
| 2 grade_odds | 112 | 0 | 17,360 | 0 |
| 3 misses (incl. example) | 174 | 0 | 25,815 | 227 |
| 4 odds_fade, signals a year | 110 | 0 | 16,448 | 0 |
| 5 cards | 3,140 | 0 | 351,115 | 0 |
| 6 open signals, prints, top level | 1,072 | 0 | 147,537 | 0 |
| 7 past paths (incl. example) | 1,348 | 0 | 167,399 | 227 |
| 8 page (9 and 10 within it) | 6,202 | 0 | 592,328 | 0 |
| candle, chart and example files | 44 | 0 | 5,912 | 0 |

Totals: A 61,882; B 6,048,752.

## Coverage of group B (310 replays, 304 dates, every one through `tests/replay_at.sh` on untouched real candles; pipeline passed every step in all 310, none withheld)

| Kind of state (classified from what the replay actually published) | Replays |
|---|---|
| Market filter off in the header | 136 |
| First/last day of each of the 6 filter episodes since Sep 2020, and the days either side (F-3..F+2) | 36 |
| A forming low whose trough opened before a filter flip, today after it | 60 |
| Year ends, 26 Dec to 4 Jan, 2020/21 to 2025/26 | 60 |
| Top-grade forming card on the page | 59 |
| Live top-grade setup on the page | 183 |
| No card and no live signal | 79 (17 with no forming low on any chart either) |
| 20 signals on day 60 in progress / the day after it closed | 20 / 20 |
| Day after a confirmation | 20 |
| Other clock times (00:00:30, 00:13, 03:59:59, 08:13, 12:43, 16:13, 20:13, 23:59) | 24 (3 after 23:54 show the "daily close has passed" note) |
| Forming lows needing 0 / 1 / 2 bars | 193 / 211 / 217 cards |
| Quiet card text checked (filter on, "about N times a year" / filter off) | 11 / 95 |
| Worked example in feed / not (before 22 Nov 2024) | 83 / 227 |

## Self-test of the checker

Two planted-error copies (not states for the report): `current` with 25 errors (13 feed fields, 4 ledger cells, 1 chart file, 7 page-code changes: +10% level, Past-signals day, Day 60 line, a worst-drop format, a live day count, the example's day-10 check, a live high-day tile): 25 caught. A year-end replay (2023-12-31 23:59, need 0/1/2, 3D short bar) with 12 errors (two must-close-above cents, a low_day, an exact median, a worst-so-far, a print note, tier_fixed_on, two ledger cells, the "estimate" wording, the stale-close note, and barNextOpen without the 1 January restart): 11 caught on first run; the restart bug moved only date-axis labels, so a date-axis check and a candle-count check were added: 12/12. All of group A and B were then re-run with the final checker. Total 37 planted, 37 caught.

## Definitional notes (not counted)

The brief's (a) to (al) all apply and none was contradicted by the repo; in particular (a) gate on the trough date and header as of today, (b) clamp (ETH 2017-06-21, BTC 2017-04-15), (c) low before high, (d) need-1 estimate, (e) day in progress, (g)/(i) tier rule and in-sample pool, (j) known-by-then, (m) from-entry live cards, (n) lead trader "unavailable", (r) years 2020 to last full closed year, (t) n/a before a closed bar, (u) replay keeps the date's bar whole, (w) empty sample gets no card (checked with the low's grade taken from the same run's `liveread.csv`), (x)/(ab) static example file, (ac) group order, (ae) fell-first counts, (ah) footer date, (al). My own choices, stated: thresholds (+10/+15/+20%, -25.3%, -30%, ladder levels, edge level) tested in exact decimal on the cent prices; the definition and the pipeline's float agreed on every signal. "First" day of the 60-day high / deepest dip is the earliest day on a tie. A bar of a 2D-8D file is keyed by its first existing day (ETH 21-22 May 2016 missing).

## Other notes

- The repo's `analysis/tagstats.py`, `extras_live.py` and `analysis/carddesign.py` changed on disk during this audit (another agent). Both frozen states and every replay ran on a copy of `a35/current` taken at the start, so these results are for that frozen code.
- Typography only, not counted: the cloud's y-axis labels print "-20%", "-40%" with a hyphen; every other negative on the page uses the minus sign. The quiet card reads "(2020 to 2020 average ...)" on 19-24 Aug 2021 (correct by (r), awkward wording).
- Doc sentence vs code: none found that contradicts the code, beyond the example-extras behaviour above (FEED_SPEC implies the example extras exist only with the worked example; `extras_live.py` writes them regardless).

Files: `all_checks.csv` (group A every check; group B every disagreement plus one summary row per replay naming its gzipped detail in `replay_checks/`), `disagreements.csv`, `replays_summary.csv`, `progress.log`, code in `code/`.
