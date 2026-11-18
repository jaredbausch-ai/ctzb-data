# Audit 37: numbers and labels on real data

Independent recomputation from raw candles with my own code (`chk/mine.py`; only `regimes.rsi_regime` imported, for the gate). This is entry quality only: there is no exit in the data, so nothing here is a strategy return or a track record. The dashboard and member-site signals are computed signals. None of them is a fill.

## Top line

| Group | Comparisons (rows) | Distinct figures | Disagreements (rows / distinct) | Wrong figure | Wording |
|---|---|---|---|---|---|
| (A) Two frozen states: REPLAY (clock 2026-11-12T04:14Z) and CURRENT (feed 2026-11-15T15:56:12Z) | 56,479 | 29,200 | **0 / 0** | 0 | 0 |
| (B) 270 replays of real dates, 2020-09-01 to 2026-11-14, via `tests/replay_at.sh` | 4,895,609 | 199,642 | **0 / 0** | 0 | 0 |
| Synthetic states inside the envelope rule (candles end on day D, clock on D+1) | 44 | 44 | 0 / 0 | 0 | 0 |

A "distinct figure" is a unique combination of location, label and my value. A figure that repeats across states is counted once.

## Every disagreement

None. Five rows differed on first runs, and all five were faults in my own harness, now fixed and re-run:
- On R2022-01-27 with a 23:59 clock, the page was opened 6 minutes after the feed, which crosses midnight. The page then correctly showed its "daily close has passed" note on 4 cards.
- In the envelope test, the Past signals count was read without opening that tab. The page fills it only when the tab is shown.

## Checks declared before results

0. Data: daily files have no missing day; the last daily bar is today's open bar; every 2D-8D file equals its daily candles bucketed with the 1 January restart; every `datasets/candles_*.csv` holds the chart's last 70 bars.
1. Ledger rows: membership (graded charts, ETH funding windows, 60th day closed), order, low, entryPrice (also against the daily close), tags, every forward measure (6 dp), yes/no columns, scaled20, grade columns, and the odds-on-the-day columns including dayScaled20.
2. `grade_odds`: every field for A+, A, B and C per asset. The flag rows are lens logic and out of scope.
3. `if_it_misses` and `example_if_it_misses`: every field.
4. `odds_fade`: the walk-forward tier recomputed with refresh's original rule on chart bars as of 1 January; bands and checks; both shares and their aliases; edge marked on the exact share; `tier_fixed_on`; `trades_a_year` and `signals_a_year`; `next_buy_date`.
5. Cards (forming, `open_signals[].card`, `example_card`): every field. This covers the sample rule, its text and n, eras, timing, exact and rounded medians, the from-entry row, the ladder (shown and exact), the edge, `low_day`, `confirms_on` by bucket rule, `must_close_above` (exact rational solve, rounded down), `price_now` and `entry_close`. Also checked: which forming lows must have a card, and that every live signal has a card.
6. `open_signals` (ids, dates, `days_elapsed`, day10/30/60 on closed bars, best and worst, `edge_level_pct`, `edge_status`), `prints` (last 3 per chart plus any forming low, tags on exact CT/K with the EPS guard, gate note on the trough date), and the top-level fields.
7. `past_paths` and `example_past_paths`: n and every day's q25, median and q75.
8. Page in Playwright (clock = generated_at + 6 min, trades file 404, fonts aborted):
   - every Live and Forming picker button, and the example;
   - every card text;
   - the Chart tab in "At the alert" and "What happened": vertical lines by date (Entry/Today, Confirms, Day 60, High day), level lines and price tags, axis scaling on what was known, x-axis dates, y-axis price labels, the low marker, ladder bands with their n and colour, candles drawn, the side boxes, "What this one did", and the cloud lines;
   - Past signals (All, ETH, BTC), Previous signals, How to read, the banner and the footer;
   - the quiet-market card with "about N times a year", and "Example unavailable" before 22 Nov 2024.
9. Labels vs meaning: I computed every expected value from the meaning of its words, not from the pipeline's code. I also checked label-bearing texts exactly: sample lines, pools, status lines, titles, subtitles and cloud notes.
10. Entry quality only: a wording scan of all 272 rendered pages for profit, return, gain, win, track record, performance, result and similar words.

## Checks passed, by number

| # | (A) frozen | (B) replays |
|---|---|---|
| 0 data | 44 | 5,940 |
| 1 ledger | 49,688 | 4,165,317 |
| 2 grade_odds | 112 | 15,120 |
| 3 misses | 174 | 22,545 |
| 4 odds_fade and tier fields | 108 | 14,188 |
| 5 cards | 2,818 | 282,308 |
| 6 open signals, prints, top level | 1,010 | 122,293 |
| 7 past paths | 1,472 | 152,415 |
| 8 page figures | 767 | 84,161 |
| 9 label texts | 286 | 31,322 |
| 10 wording scan | 272 pages | (included) |

All passed. Item 10 found only negations ("not a return or a track record", "not a trading result") and the lead-trader panel's description of his own trades (note o).

## Coverage of group B

A replay can fall into several kinds.

| Kind | Replays |
|---|---|
| Market filter off | 40 |
| First or last day of a filter episode, or a day either side (flips 2021-06-08, 2021-08-19, 2022-01-27, 2023-01-25, 2025-12-05, 2026-09-02) | 24 |
| Year-ends, every day from 26 Dec to 4 Jan, 2020/21 to 2025/26 | 60 |
| A top-grade forming card on the feed (target 40) | 66 |
| Nothing live or forming on any of the 10 charts | 10 |
| Quiet market with the filter on (the per-year text is checked) | 19 |
| 20 top-grade signals: day 60 in progress, then the day after it closes | 20 + 20 |
| The day after a confirmation | 12 |
| Other clock times (00:00:30, 00:13, 03:59:59, 08:13, 12:00, 16:20, 20:14, 23:30, 23:59) | 12 |
| Every date where a graded forming low's trough is across a filter flip | 47 |
| Cards under a "Market filter: off" header | 35 |
| Forming cards by bars to confirm (0 / 1 / 2) | 215 / 174 / 178 |
| Replays carrying the worked example (on or after 22 Nov 2024) | 81 |
| Replays before 22 Nov 2024 checked to have no example | 189 |
| Replays that failed to run | 0 |

Envelope tests: four states had candles ending on day D with the clock on D+1:
- 2025-03-10 → 03-11 00:00:30
- 2026-11-11 → 11-12 04:14
- 2023-12-31 → 2024-01-01 00:05
- 2024-09-21 → 09-22 08:13

Each failed closed. The stack step failed and cards were withheld. The feed had no cards, open signals or example, and `market_regime` and `scored_as_of` were null. The page read "Setups held back", "Market filter: unavailable", "checks FAILED" and "Past signals unavailable", and did not switch on the example.

Exact-tie scan: I re-tested every threshold (±5/10/15/20/30%, −25.3% and the odds-fade band edges) in exact decimals on 71,349 daily bars. Float and exact disagreed on 4 bars that sit exactly on a threshold:
- ETH 3D 2023-03-19, day 38 at exactly +10%
- ETH 2D 2021-03-31, day 53 at exactly −10%
- ETH 1D 2017-01-15, at exactly +30%

None changes a published figure. Each falls after an earlier +10% day, outside days 1-10, or before the ETH ledger starts.

## Definitional notes (not counted)

(a) to (al) as listed in the brief, all observed as stated. In particular:
- the gate is read on the trough date and the header shows today's filter (35 replays have cards under an "off" header);
- the clamp and low-before-high hold;
- "must close above" for a one-bar-out setup assumes the open bar closes at the latest price;
- `peaked_10_or_more` is 0 in every replay;
- the tier is fixed on 1 January from chart bars, and the pooled odds fade is in-sample;
- "known by then" uses entry + 60 ≤ date;
- the open card is rebuilt each run from the entry close;
- the trades file returns 404, so "unavailable" shows;
- the "if it misses" median is over all misses;
- "about N times a year" runs from 2020 to the last fully closed year;
- a live setup with no closed bar shows best/worst as "n/a";
- the example chart file is static.

One more layout observation, not a figure: a live setup's chart draws no low marker. Only forming setups get one, because the page reads `low_date` from the open signal, which has none. No number is affected.

## Test of my own checker

I planted 51 errors in a copy of CURRENT (38 in data, ledger and feed, 13 in the page code). **50 were caught.** The one not caught was "axis scaled on all bars at the alert". On this data it changes nothing on screen: the example's typical-high and −20% levels already set the scale, so no displayed position moved. Results are in `plant_results.json`.

## Doc sentences contradicting the code

None found in what I read (CONTEXT audit paragraphs, FEED_SPEC, CARD_SPEC).

## Files

All in `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit37n/`:
- `all_checks.csv`: every group A row, plus one summary row per replay and item.
- `disagreements.csv`: header only, no rows.
- `replays/R*_checks.csv.gz` and `replays/R*_page.csv.gz`: every replay row.
- `replays/ENV_checks.csv.gz`, `replays/*_feed.json.gz`, `progress.log`, `chk/`: the envelope rows, each replay's feed, the progress log, and my code.
