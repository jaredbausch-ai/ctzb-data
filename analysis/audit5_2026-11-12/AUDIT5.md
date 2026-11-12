# Audit 5: ETHKROS member site against raw candles

Independent audit, 12 Nov 2026. Everything was computed with new code in `audit5/code/` from the raw `data/*.csv` candles of each frozen state. Only `regimes.rsi_regime(BTC_2D, 8, 13, 60, 41)` was imported, and only for the gate. No earlier audit and no AUDIT_LOG were read. Nothing in the repo was edited. This work measures entry quality only: these are computed signals, never fills. Nothing here is a strategy return or a track record.

**Top line: 61,226 comparisons across the two states. 92 disagree. They reduce to 47 distinct (place, figure) pairs from 9 root causes:**
- **4 number problems:**
  - the first-fall step of the ladder checks the high before the low inside a day;
  - the Day-60 line is drawn one bar early when the window crosses 1 Jan;
  - in "At the alert", the example chart's price axis is scaled by bars after the entry;
  - `price_now` on open cards holds the entry close (feed only).
- **5 label problems.**

Every ledger row, grade_odds, if_it_misses, odds_fade, past_paths and open-signal figure agrees exactly.

## Checks declared before running

1. Every ledger row: membership (both directions), low/entry dates, entryPrice, entry close against the daily close, tags, year, bestMove, maxDrawdown, dipBeforeHigh, return60d (6 places), daysToHigh, reached10/15/20, touched30, surv10, scaled20, the grade columns and the seven "odds on the day" columns.
2. feed `grade_odds`: every field. The two ETH HTF-divergence rows are a lens flag and out of scope.
3. feed `if_it_misses`: every field, all 8 asset×grade rows.
4. feed `odds_fade`: my own ETH walk-forward tier as of 1 Jan 2026 (outcomes closed by then), then every early_dip and day10 row on daily candles from the entry close, the edge marks and the "2016 on" claim.
5. Every card: the 4 REPLAY forming cards, `example_card` (known by 2024-09-22) and the 23 `open_signals[].card` in each state. Every field: ids, low_date, low_day, confirms_on, bars_to_confirm, must_close_above (solved exactly), price_now, n, sample line, the four shares, beat_normal_move, the three medians (rounded and 6-place), eras, ladder, timing, and confluence window dates.
6. feed `open_signals` (ETH and BTC): the set, ids, dates, entry close, tags, days_elapsed, day10/30/60 (closed bars only), best/worst so far.
7. feed `past_paths`: n and the q25/median/q75 for days 0–60, both assets.
8. The page, in Playwright with the clock at generated_at + 6 min: banner, filter pill, footer, every picker button (Live and Forming), the arrival card, every card's head/odds/stats/tiles/ladder/eras, the example (button and switch), the Chart tab for every selection in "At the alert", "What happened" and back again, and the Past signals tab (all/ETH/BTC, every row and the summary boxes). Also the Previous signals column and How to read.
   - Chart items checked: every candle, wick, level line, price tag and zone, the line positions against dates, the axis dates, the side panel, and the cloud path and band.
9. Labels against meaning.
10. Entry quality only: page wording and feed labels.

## Disagreements

| state | where | shown | mine | cause |
|---|---|---|---|---|
| both | example card ladder "Falls 5% first": feed, Now card (button and switch) and the chart zone label | n 41 · 76% | n 43 · 77% | Ladder first-fall step checks the HIGH before the LOW within a daily bar. Stated choice (c) is low first, which the code's second step does use. The two cases are ETH 3D 2021-01-03 (day 1: H +19.2%, L −9.6%) and ETH 5D 2021-05-10 (day 2: H +11.0%, L −6.3%) |
| both | open card BTC-1D-2026-09-18 (grade B; feed only), "Falls 15% first" | n 18 · 22% · 61% | n 19 · 26% · 58% | Same cause. BTC 1D 2017-02-28, day 10: H +13.8%, L −19.9% |
| REPLAY | Chart, forming ETH 2D and BTC 2D (confirm 16 Nov), "Day 60" line, 3 views each | x 946.31 = bar of 13 Jan 2027 (days 58–59) | x 955.44 = bar of 15 Jan 2027 (day 60) | The page steps 60/tf bars from the confirmation bar and ignores the 1-day bar on 31 Dec and the restart on 1 Jan |
| both | Chart, example, "At the alert": price-axis range | top $3,745.00 (= the $3,500 high of bar 52, days 61–62, × 1.07) | $3,729.11 from bars up to the entry plus the typical-high level | lo/hi are taken over all 52 bars, so a bar after the alert sets the axis. The outcome leaks into "At the alert" (scale only, no candle drawn) |
| both | feed `open_signals[].card.price_now`, all 23 open cards (not shown on the page) | the entry close, e.g. 86,594.94 | price now: 73,736.44 (REPLAY), 72,989.23 (CURRENT) | The field name says price now. Open and example cards copy the entry close into it |
| REPLAY | ladder top row "From entry", forming ETH 2D / BTC 2D | 67% / 67% | 63% / 60% | Label: the top row is "rose 10% in 60 days in any order". The rows under it, and the note, are "rose 10% before ever falling 25.3%" |
| both | same, live BTC 2D (card ladder and chart zone) | 85% | 82% | Same |
| REPLAY | chart side, all 4 forming setups: "Prices use today's close as a stand-in for the entry" | today's close | the latest price of a bar still open at 04:14 UTC | Label: it is not a close. The subtitle correctly says "today's price" |
| both | footer "Data through 12 Nov 2026" | 12 Nov | last closed daily bar 11 Nov; 12 Nov in progress (04:14 / 16:07) | Label |
| both | How to read, "Where the odds fade" | "…still rose 10%" | "…still rose 10% before ever falling 25.3%" | Label: it omits the condition the rows measure. The card note and CARD_SPEC include it |
| both | Chart toggle on live and forming charts (6 in REPLAY, 1 in CURRENT) | visible, "At the alert" pressed | hidden | `.toggle {display:flex}` overrides `[hidden]`. "At the alert" shows as pressed over a live path, and "What happened" does nothing |

Every row is in `disagreements.csv`.

## Checks passed

| # | section | REPLAY | CURRENT |
|---|---|---|---|
| 1 | ledger (406 rows, plus the ETH absences explained by no funding read before 2020-03-21) | 25,016 / 25,016 | 25,016 / 25,016 |
| 2 | grade_odds | 70 / 70 | 70 / 70 |
| 3 | if_it_misses | 88 / 88 | 88 / 88 |
| 4 | odds_fade (tier: 13 chart×tag pairs; pool 168) | 32 / 32 | 32 / 32 |
| 5 | cards (4 forming + example + 23 open / example + 23 open) | 1,161 / 1,189 | 981 / 1,009 |
| 6 | open_signals (23) | 276 / 276 | 276 / 276 |
| 7 | past_paths (ETH 104, BTC 33) | 372 / 372 | 372 / 372 |
| 8 | page (30 / 14 snapshots) | 4,162 / 4,174 | 3,078 / 3,084 |
| 9 | labels vs meaning | 11 / 25 | 9 / 13 |
| 10 | entry quality only | 12 / 12 | 12 / 12 |

Highlights of what agreed exactly:
- every forward measure of all 406 ledger rows, to 6 places;
- must_close_above for ETH 1D ($2,047.21) and BTC 1D ($73,533.06);
- every low_day;
- all 23 open signals in each state, including days_elapsed, the closed-bar-only day marks and best/worst;
- every card median, share, era and timing figure;
- the odds_fade tier and tables;
- every Past-signals row (137 / 104 / 33) and its count line ("137 signals · 20 missed +10%");
- every candle on every chart against the raw bars (example JSON included: entry_index 20 is the bar closing 22 Sept 2024, close $2,580.92);
- every Entry/Today, Confirms, High-day and low-marker position, apart from the Day-60 line above;
- every price tag and level y;
- the cloud path and band (61 days).

"At the alert" draws no candle after the entry and no outcome marker. "What happened" matches my daily data:
- best $3,446.98, +33.6%, days 51–52;
- deepest $2,309.17, −10.5%, days 11–12;
- day 10 red, −8.4%;
- day 60 +30.2%.

The label "If it misses: up first" is exact under "above entry on a day before its deepest low": 5/5, 10/10, 37/37 and 94/95. Check 10 found no wording that reads as a return, a trade taken or a track record. Every "trade" mention is negated or is about the lead trader.

## Definitional notes (not counted)

- (a) The gate is read on the trough bar's open date. The pipeline agrees on every signal.
- (b) The flash-print clamp applies to all candles. It fires only on ETH 2017-06-21 ($0.10) and BTC 2017-04-15 ($0.06), on every timeframe.
- (c) Low before high inside a day. The second ladder step follows it. The first-fall step does not, and that is counted above.
- (d) must_close_above assumes today's open bar closes at the current price. Solved in closed form from Wilder's averages; it matches to the cent.
- (e) days_elapsed / "day N of 60" is the day in progress. "Day 52" for BTC 2D 21 Sept matches.
- (f) peaked_10_or_more is 0 in all 8 rows, by construction.
- Multi-day bars restart on 1 Jan, so the last bar of a year can be 1–6 days long. I date a bar's close as the next bar's open − 1 day, not open + tf − 1. Every signal date here agrees with the pipeline.
- Ties: the day of the 60-day high or low is the first such day; low_day takes the earliest day on a tie. Price thresholds are evaluated in exact rational arithmetic. No float boundary changed any figure.
- The odds-fade tier is chosen on each chart's own bars (60-day close vs entry, from the confirmation bar's open), as `refresh.fw` does. Choosing it on daily-from-entry outcomes would add ETH 3D "D" and drop ETH 8D "any trough".
- Not checked (lens logic): the confluence cells' n and rates (only their window dates were checked) and the HTF-divergence grade_odds rows.
- The "Edge lost" badge in Previous signals comes from the pooled ETH-tier day-10 row, not the setup's own ladder. For the live BTC 2D both say edge gone.
- The empty-card claim "about 22 times a year (2020 to 2025 average)" is not shown in either state. My figure is 130 / 6 = 21.7, which supports it.

## Docs vs code

- **FEED_SPEC:** open_signals cover "1D/2D/3D/5D", but `stack_live.py` loops over 8D too, and grades 8D, which `grade_live` does not. No 8D signal is open in either state.
- **stack_live `low_day`:** it scans `tf` calendar days from the trough's open, so on a short year-end bar it would read the next bar's days. No card here is affected.
- **Ladder:** CARD_SPEC defines the rows as falling first, then rising 10% before −25.3%. The code's first step resolves same-day ties high-first (counted above).
- **CTZB_NOW:** `refresh.ds_status` ("Updated (UTC)") and the `stack_status.txt` stamps use the real clock, so REPLAY shows 16:07 UTC. This is not member-visible.
- **missstats.csv:** the column `aplus_signals` holds the count for every grade. The feed renames it to `signals`.

Files:
- report: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit5/AUDIT5.md`
- every comparison: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit5/all_checks.csv`
- the 92 disagreeing rows: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit5/disagreements.csv`
- code: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit5/code/`
