# Audit 45, numbers and labels: independent check of the ETHKROS member site

**Scope.** I checked every number a member sees against the raw daily candles, using my own code (`code/core.py`, `code/check.py`, `code/page.py`). Only `regimes.py` (the gate) was imported. The code is frozen at a0dc979. Nothing in the repo was edited. These are entry-quality figures only: the data has no exit, so nothing here is a strategy return or a track record.

## Checks declared before any results
1. **Ledger.** Every row: membership, entryPrice, tags, the forward measures (to 6 places), and the odds-on-the-day columns (dayScaled20 included). Membership means: a gated signal on 1D–5D with its 60th day closed, and ETH only where funding exists.
2. **grade_odds.** Every field, including the two "diamond or prime dot" rows. The two HTF rows are out of scope (h).
3. **if_it_misses and example_if_it_misses.** Every field.
4. **odds_fade.** Recomputed independently: my own walk-forward tier on each ETH chart's own bars as of 1 January, then grouping and outcomes on daily candles. Covers both lists, the aliases, tier_fixed_on, and each edge mark (tested against 70% on the exact share).
5. **Cards.** Every forming card, every open_signals[].card and example_card, field by field. That includes the sample rule and its text, low_day, confirms_on (bar rule, 1 January restart), must_close_above (exact root of the RSI equation, rounded down) and the ladder (shown and exact shares). It also covers which lows get a card and that every live signal has one. The example chart file and the served chart files are checked against my own 2D–8D bars.
6. **open_signals, prints and top-level fields.** open_signals: ids, days_elapsed, day 10/30/60 (closed bars only), best/worst, edge_level and edge_status. prints: the last 3 per chart plus the forming low, with tags on exact CT/K and the EPS guard, and the regime note on the trough date. Top level: schema_version, posting_bar_pct, trades_a_year (and its alias), scored_as_of, market_regime.
7. **past_paths and example_past_paths.** Every quartile on every day.
8. **The page in Chromium (Playwright).** Clock set to generated_at + 6 min, data served exactly as the brief describes. Covered:
   - every picker button, and every card's text, tiles, ladder (with its below-bar colour) and eras;
   - Previous signals; Past signals (all, ETH and BTC: every row and the summary boxes); How to read; banner; footer; the quiet card's "about N times a year";
   - the Chart tab. Price lines at their prices, with the alert axis scaled only on bars known then. Entry/Today/Confirms/Day 60/High-day lines placed on the bar holding that date. Date and price axis labels, ladder bands with their n, the side box, live and "What happened" boxes and the cloud note. The example is checked in both modes.
9. **Labels against meaning.** Every label was read against the number under it.
10. **Entry quality only.** No wording reads as a return, a trade taken or a track record.

## Top line

| Group | States | Comparisons (rows) | Distinct figures | Disagreements (rows) | Disagreeing figures | Wrong figure | Wording |
|---|---|---|---|---|---|---|---|
| (A) Frozen states (replay_0414, current) | 2 | 53,299 | 28,317 | **0** | **0** | 0 | 0 |
| (B) Replays of real dates, Sep 2020 – Nov 2026 | 400 | 6,867,319 | 227,274 | **0** | **0** | 0 | 0 |

Here "distinct figures" means unique (location, label, value shown) triples. The same signal's ledger row in 300 replays counts once.

## Every disagreement

| Group | State | Where | Shown | Yours | Cause |
|---|---|---|---|---|---|
| — | — | none | — | — | — |

`disagreements.csv` has a header only.

## Checks passed by number

| # | Check | (A) comparisons | (B) comparisons | Disagreements |
|---|---|---|---|---|
| 0 | Raw candle files: 2D–8D equal my bucketing of the daily candles; the last bar is today; the chart files served to the page | 44 | 8,800 | 0 |
| 1 | Ledger (A: 1,842 rows; B: 229,963 row-states) | 46,052 | 5,749,475 | 0 |
| 2 | grade_odds | 136 | 27,200 | 0 |
| 3 | if_it_misses and example_if_it_misses | 156 | 29,795 | 0 |
| 4 | odds_fade, including the tier, aliases and edge marks | 106 | 20,640 | 0 |
| 5 | Cards: 10 forming, 44 live (all of them), 2 example in A; about 936 forming, every live signal and 119 example in B | 2,868 | 406,965 | 0 |
| 6 | open_signals, prints and top-level fields | 1,054 | 185,564 | 0 |
| 7 | past_paths and example_past_paths | 1,348 | 218,177 | 0 |
| 8 | Page: 14 card selections and 16 chart renders in A; 2,594 and 2,363 in B | 1,535 | 220,703 | 0 |
| 9 | Labels against meaning (manual read of every label on the four tabs, against check.py's definitions) | all | all | 0 |
| 10 | Entry quality only: page text grepped and read for return, profit, trade, win, gain, track record and result | all | — | 0 |

## Coverage of group B (400 replays, 4 to 11 per real date-kind; one date can serve several kinds)

| Kind | Asked | Replays | What the replays actually showed |
|---|---|---|---|
| Market filter off | 40 | 40 chosen in off episodes | 146 replays read "Bearish" |
| First and last day of each filter episode, ±1 day (6 flips: 2021-06-08, 2021-08-19, 2022-01-27, 2023-01-25, 2025-12-05, 2026-09-02) | all | 36 (F−3 to F+2 for each flip) | — |
| Every date within a forming low's reach of a flip | all | 126 (F−1 to F+19 for each flip: a 5D low's trough bar open to its confirmation close is 19 days), plus 36 for 8D prints (every other day, F+21 to F+31) | — |
| Year-ends, 26 Dec – 4 Jan | 6 years | 60 (2020/21 to 2025/26, every day) | — |
| Top-grade forming low | 40 | 78 planned from top-grade ledger signals | **100 replays had a top-grade forming card** |
| Nothing live or forming on any chart | some | 10 planned from my own scan | 16 replays with no forming low on any of the 10 charts and no open signal; 69 showed the quiet card |
| 60th day in progress, then the day after it closes | 20 signals | 40 (12 top grade, 8 other grades) | 20 of 20 listed at day 60 with day60 null, then gone the next day |
| Day just after a confirmation | some | 10 (plus 20 on confirmation days) | — |
| Other clock times | some | 11 (00:00:30, 01:30, 06:00, 08:13, 12:00, 16:43, 20:13, 23:30, 23:59 ×2) | — |
| Worked example present (on or after 22 Nov 2024) | — | — | 119 replays; none before 22 Nov 2024, as specified |
| Live top-grade signal on the page | — | — | 236 replays |

Envelope test (clock on day D+1, candles ending on day D), stage "synthetic": I replayed 2026-11-11 at 00:00:30, 2024-09-21 at 04:14, 2023-12-31 at 00:13 (across the year-end) and 2026-09-20 at 23:59, each with the clock moved to the next day. All four fail closed. The stack step fails with "today's bar is missing", and the feed has cards_withheld true with no cards, live signals or example. The page reads "Setups held back" and "Market filter: unavailable", and the footer reads "checks FAILED, cards held back" (`envelope.json`). None of the 400 real-date replays failed a step or withheld cards or extras.

## Testing my own checker
`code/plant.py` plants errors in a copy of the current state (`plant_result.txt`):
- **Data, feed and file plants:** 44 of 44 caught. These covered the ledger, grade_odds, misses, paths, odds_fade, trades_a_year, cards (including a 1e-6 change to an exact median, must_close_above +1 cent, low_day and confirms_on), open signals, prints, the example card and both kinds of chart file.
- **Page-code plants:** 15 of 15 caught, one mutation per run. These covered the big number, rounding, the +10% level, the Day 60 line, the edge rule, the drop tile, the footer date, the record table, the axis padding, misses, the day count, the example's day range, eras, the cloud note and the ladder n.
- **No-op plants:** two first attempts had no visible effect on this data, so they were replaced. "Edge tested on the rounded share" changed nothing because no ladder share lies within 0.5 of 70. "Alert axis scaled on all bars" changed nothing because the example's typical-high level ($3,485.15) is above every later bar.

I also found and fixed two bugs in my own checker during the run, neither of them a pipeline fault. Both were in how I compared against the page: tie order among same-day rows in Previous signals, and JavaScript's half-up `Math.round` in the date-axis step. Both disappeared once corrected. The 46 replays checked before the fix were re-run in full.

## Definitional notes (not counted)
- **Taken as given:** the brief's choices (a)–(al), each consistent with the repo as I found it.
- **My own reading where the docs are silent:**
  - Every rose 10% / fell 25.3% / fell X% / +20% / −30% test is done exactly on decimal prices. No float tie changed any figure in 402 states.
  - The day of the 60-day high or the deepest dip is the first such day when two days tie. low_day is the earliest day when two lows tie.
  - Displayed medians are rounded once from the 6-place stored value.
  - must_close_above is the exact root of the Wilder RSI equation, rounded down. No root lay within 1e-6 cent of a cent boundary.
  - The order of same-date rows in Previous signals, and of buttons in the picker, is treated as layout (l).
- **Out of scope:**
  - next_buy_date (al): not on the page.
  - confluence_windows, active_confluences and alerts: not shown to members.
  - grades and lens sets: taken from the ledger and the feed as given.
- **Observation, not a figure:** on the Chart tab, the "Low ‹date› · $‹price›" trough marker is drawn for forming setups only. A live setup's chart has none, because the page looks for `low_date` on the open-signal object and it sits only inside its card. Nothing documents it either way.

## Doc sentences contradicting the code
None found in what I read (CONTEXT's rule sections, FEED_SPEC, CARD_SPEC). One loose phrase: FEED_SPEC open_signals says "confirmation close is 0 to 60 days before today", but 0 cannot occur because the confirmation bar is still open on that day. In every replay, days_elapsed ran 1 to 60.

## Files
- `all_checks.csv`: every group A row in full. Group B is aggregated per replay, item and label; every B row is in `B/<replay>.checks.csv.gz` and `B/<replay>.page.csv.gz`.
- `disagreements.csv`: header only.
- `B/summary.csv`: one line per replay.
- `plan.tsv`
- `stats.json`
- `envelope.json`
- `plant_result.txt`
- `progress.log`
- `code/`
