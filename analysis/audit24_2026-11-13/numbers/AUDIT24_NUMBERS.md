# Audit 24: numbers and labels on real data

Independent auditor, 13 Nov 2026. I recomputed every member-facing figure from the raw candles with my own code (`code/core.py`). From the repo I imported only `regimes.py`, and only for the market gate. I checked each figure against the ledger, the datasets, the feed and the rendered page (Playwright, `code/page.py`). Grades and lenses were taken from each state's own files, as the brief says. Nothing in `/home/claude/ctzb-data` was edited.

**Entry quality only.** These are computed signals, not fills. There is no exit in the data, so nothing here is a strategy return or a track record.

## Top line

| Group | States | Comparisons | Disagreements (rows) | Distinct figures disagreeing | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| A: frozen states | replay_0414, current | 60,962 | 0 | 0 | 0 | 0 |
| B: replays of real dates | 371 replays, 357 distinct dates (5 Oct 2020 to 5 Oct 2026) | 7,497,750 | 0 | 0 | 0 | 0 |

No disagreement was found in either group. Every replay ran clean: no pipeline step failed on a real date, the checker never errored, and the page accepted every feed.

## Every disagreement

| Group | State | Where | Shown | Yours | Cause |
|---|---|---|---|---|---|
| none | | | | | |

There are 8 rows in group B that I did not count. On 8 replay dates between 22 Aug and 20 Nov 2024, my own data check "example file bars = ETH 2D candles" failed. The cause is in my checker, not the site: the replay cuts its open 2D bar, while the static example file holds that bar whole (note (ab)). The page does not use the file before 22 Nov 2024, because there is no example card then. These rows are kept in `all_checks.csv`, labelled as artefacts.

## Checks declared before running, and how many passed

| # | Check | A passed | B passed |
|---|---|---|---|
| 0 | Candle data: each daily file starts on the first day with no gaps (ETH 21-22 May 2016 excepted); every 2D-8D bar equals its daily candles bucketed within the year; the served chart files are the last 70 bars; the static example file (bars, entry bar closing 22 Sep 2024, entry close, last bar holds day 60) | 52 | 9,568 |
| 1 | Ledger, every row: membership (gated, graded chart, 60th day closed, ETH funding window), trough date, entryPrice, entry close = daily close, tags (exact CT/K, EPS guard), yes/no measures, the four 6-place measures, daysToHigh, odds on the day incl. dayScaled20 exclusion, grade pooled columns | 49,680 | 5,851,413 |
| 2 | grade_odds, every field (the HTF rows are out of scope, (h)) | 140 | 25,760 |
| 3 | if_it_misses and example_if_it_misses, every field | 156 | 28,704 |
| 4 | odds_fade: the walk-forward tier recomputed on each chart's bars as of 1 Jan, bands and checks, shares, after_day10 fields and aliases, tier_fixed_on, the edge tested on the exact share (integer arithmetic), the datasets' reached10Exact | 136 | 24,511 |
| 5 | Cards (forming, example, every open_signals[].card): every field, the ladder (shown and exact), edge, low_day, confirms_on (1 Jan restart), must_close_above (rounded down, Wilder solved exactly), medians, eras, timing, sample text and n; cards only where they should exist; every live signal has a card | 2,950 | 441,122 |
| 6 | open_signals (ids, dates, days_elapsed, day 10/30/60 on closed bars, best/worst, edge level and status), prints (last 3 per chart plus forming, regime note on the trough date, forming tags), top-level fields (schema, posting bar, regime, trades_a_year, next_buy_date, scored_as_of, generated_at) | 1,062 | 182,616 |
| 7 | past_paths and example_past_paths (61 days x 3 quantiles, n) | 1,104 | 203,136 |
| 8 | The page: header, banner, footer, lead panel, every Live and Forming picker button, every card, the example, the Chart tab (At the alert and What happened: titles, levels and price tags, line heights against an axis scaled only on the bars shown, Entry/Today/Confirms/Day 60/high-day lines placed by date, ladder bands with n, heights and colours on the exact share, the low marker, outcome hidden at the alert, side boxes, cloud), Past signals (All/ETH/BTC, every row and summary), Previous signals, How to read, quiet card | 5,682 | 730,912 |
| 9 | Labels vs meaning: each label was compared as text with what its number measures (inside checks 5-8); no mismatch | yes | yes |
| 10 | Entry quality only: a word scan of every tab on both frozen states for trade/return/profit/win/fill/track record/performance/strategy. Every hit is a disclaimer or the lead-trader panel ((n), (o)) | yes | n/a |
| - | Fail-closed envelope (clock on D+1, candles end on D): feed withheld, no cards, no live signals, no example; the page says "Setups held back" and the footer says FAILED | n/a | 3 replays, 12 checks |

## Coverage of group B (371 replays)

| Kind of state (planned) | Replays | Kind of state (observed in the output) | Replays |
|---|---|---|---|
| Within a forming low's reach of a filter flip (F-2 to F+20, all 6 flips) | 138 | Market filter off | 132 |
| First/last day of each filter episode and the days either side | 24 | A top-grade forming card | 77 |
| Year-ends, 26 Dec-4 Jan, 2020/21 to 2025/26 | 60 | Any forming card | 236 |
| Top-grade forming low (confirmation day / bar before) | 37 / 12 | A forming low with the filter off at its trough (print only, no card) | 116 |
| 60th day in progress / day after it closes (19 signals; 14 top grade) | 19 / 19 | A signal on its 60th day | 79 |
| Day after a confirmation | 12 | A live top-grade setup | 223 |
| Filter-off dates (random) | 25 | Nothing live or forming on any chart | 9 |
| Random dates | 40 | No live top-grade setup and no forming card | 81 |
| Candidates for nothing live or forming | 12 | No worked example (before 22 Nov 2024) | 255 |
| Other clock times (00:00:30, 03:59, 08:13, 12:13, 16:13, 20:13, 23:59) | 14 | Clock other than 04:14 | 17 |
| Envelope: clock on D+1 with candles ending on D | 3 | All fail closed | 3 |

The six flips are 8 Jun 2021 (off), 19 Aug 2021 (on), 27 Jan 2022 (off), 25 Jan 2023 (on), 5 Dec 2025 (off) and 2 Sep 2026 (on). The quiet dates were 17 Aug 2021, 26 Aug 2021, 7-8 May 2022, 20 Jul 2022, 28 Oct 2022, 28 and 30 Jan 2023, and 15 May 2026. Replays per year: 2020: 16, 2021: 86, 2022: 54, 2023: 56, 2024: 55, 2025: 56, 2026: 48.

## Test of my own checker

I planted 38 errors, one at a time, on a copy of the current state and ran the full check each time (`plant_results.json`, with the rerun in `plant_results_rerun.json`). They covered 6 ledger fields, 18 feed fields, 1 chart file, 1 daily candle and 7 page changes (a wrong rounding, a day count one off, the +10% level built at 11%, the Day 60 line one bar early, a wrong column, outcome candles shown at the alert, the wrong big number).

- **37 of 38 were caught.**
- Four of the feed plants made the page's strict check reject the feed. The first run's page step crashed on those; after I hardened the page runner, all four were caught (26 to 27 rows each).
- The one not caught swapped the example's "At the alert" axis to use all bars. On this state it changes nothing visible, because the axis limits come from the typical-high and entry x 0.8 levels, not from the bars. Its sibling plant (outcome candles drawn at the alert) was caught.

## Definitional notes (not counted as disagreements)

- I applied the brief's known choices (a) to (al) as given. The ones that bear on the numbers: the gate is read on the trough date and the header shows today's filter (a); the flash-print clamp (b); low before high within a day (c); must_close_above for need 1 assumes today's bar closes at the latest price (d); "day N" is the day in progress (e); peaked_10 is 0 by construction (f); the tier uses refresh.py's own rule on chart bars as of 1 Jan (g); the pooled odds-fade is in-sample (i); the "known by then" rule is entry + 60 (j); the card is as issued at the entry close (m); the misses median is over all misses (p); the replay keeps its own day whole (u); the card sample-rule cascade (w); the static example file is not cut by replays (ab); falls-first shares count falling 25.3% before rising 10% (ae).
- ETH ledger membership: I counted a signal only when the funding series has a value on the entry date, at least 60 of the 90 days before it, and at least 5 of 7 days in both windows (days 0-6 and 14-20). This is lens-adjacent, and it matched the ledger exactly on every state.
- Rose 10%, +20%, -30% and the 25.3% line are tested on prices (entry x 1.10, entry x (1 - 0.253) and so on), not on rounded percentages. Edge marks are tested on the exact share with integer arithmetic (100 x ok < 70 x n). No boundary case arose where this differs from the pipeline's float test.
- Past paths use the exact entry close; the ledger's entryPrice is the same number, because prices are whole cents.
- Row order in Past signals and Previous signals when two signals share a date follows the ledger file's order (ETH rows first). That is a layout choice (l), so I compared rows in that order.

## Doc sentence vs code (one line)

- FEED_SPEC (Audit #20) says `trades_a_year` divides by "the years from the tier's first signal". refresh.py measures that span from the confirmation bar's open date, while every other signal date in the feed is the confirmation close.

## Files

- All in this folder: `all_checks.csv` (all group A rows plus group B disagreements and artefacts), `disagreements.csv` (header only: none), `rp_summary.jsonl` (one line per replay: kinds, counts, what the state held), `rp_checks/*.csv.gz` (every group B comparison, per replay), `progress.log`, `plan.json`.
- `code/`: the checker.
