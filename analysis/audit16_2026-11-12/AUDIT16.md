# Audit #16 — ETHKROS member site, every member-facing number against the raw candles

Independent: all code is mine (`a16lib.py`, `mycalc.py`, `chk_*.py`, `render.py`, `synth.py`, `my_replay.py`); only `regimes.py` was imported, for the gate. No earlier audit folder or log was read. Nothing in the repo or the two frozen states was edited. Grades and lenses were taken as given. Entry quality only: nothing here is a strategy return or a track record; the signals are computed, none was traded.

## Top line

| Scope | Comparisons | Disagreements |
|---|---|---|
| REPLAY (12 Nov 04:14 UTC, 4 forming) | 43,696 | 2 rows, **1 distinct figure** (a 1-cent wording point, D1) |
| CURRENT (12 Nov 22:07 UTC) | 42,729 | **0** |
| Other dates: 64 replays (5 more dates could not run, O4) | 1,941,841 | 85 rows, 3 causes (O1–O3) |
| One "clock ahead of candles" state | 34,436 | 29 rows, 1 cause (O6) |
| Synthetic page states (11 kinds, 17 renders) | 82 | 6 rows, 3 defects (S1–S3) |
| Docs vs code | — | 7 (C1–C7) |

Every ledger, feed and page number in both frozen states equals my value. The one frozen-state item is a "must close above" price that is one cent too high for its wording.
Checker strength: 16 errors planted in the feed and ledger served to the page were all caught (`mutation_test.py`).

## Checklist declared before results

1 ledger rows (entryPrice, tags, forward measures, odds-on-the-day incl. dayScaled20, membership) · 2 grade_odds · 3 if_it_misses and example_if_it_misses · 4 odds_fade (tier by refresh.py's rule, my code; after-day-10 fields, aliases, edge on the exact share) · 5 every card (forming, example, every open signal's) · 6 open_signals, prints, top-level fields · 7 past_paths and example_past_paths · 8 the page in Playwright (every picker button, example, Chart tab both modes, Past signals all/ETH/BTC, Previous signals, How to read, banner, footer) · 9 labels vs meaning · 10 entry quality only. Added by me: 0 raw candles (2D–8D bars rebuilt from the daily candles, served chart candles, clamps).

## Every disagreement

| # | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| D1 | REPLAY (frozen) | `cards[ETH-1D-2026-11-13].must_close_above`; Now card line "confirms 13 Nov 2026 if it closes above $2,047.21" | $2,047.21 | $2,047.20 | The threshold is $2,047.2081. It is rounded to the nearest cent, here upward, so a close at exactly $2,047.21 also confirms (CT 29.64647 vs trough 29.64636). The figure follows the rounding rule; the words "closes above" are off by a cent |
| O1 | 41 replays | 67 forming cards, 52 distinct figures (of 137 with a figure) | e.g. $2,256.92 | $2,256.91 | Same as D1: rounds up about half the time |
| O2 | 8 replays, 5 live top-grade setups, 16 rows | Now card: "On track. It has not fallen to its edge level." | e.g. ETH 3D 28 Nov 2024 on 28 Dec 2024: same card shows worst −13.5%, edge −10% | sentence false | It rose 10% first, so `edge_status` is "intact" by the documented rule; it then fell through the edge level. Status right, sentence wrong |
| O3 | Replay 2024-11-21 | Chart: "Edge gone below $3,191.90 (−5%)" (label and side box), top-grade forming ETH 1D, price $3,359.90 | $3,191.90 | $3,191.91 | −5% of $3,359.90 is exactly $3,191.905. The page multiplies in binary floating point (3191.90499…) and lands a cent low. Any price on a half-cent can do this (+10% level, −5/−10/−15% edge) |
| O4 | Replays 2020-12-27, 2020-12-31, 2021-01-01, 2021-03-15, 2021-11-05 | `extras_live.py` | crash | a row with 0 misses | `carddesign.misses()` takes a median of an empty list when an asset/grade has signals but no miss. The zero-miss guard in `extras_live.py` is never reached. Cannot recur on today's ledger (all 8 groups have a miss) |
| O5 | 167 top-grade card renders in replays | Now card row "If it misses: went above entry" | e.g. "6 of 6 · median best +6.5%" beside "88% … from all 25 past ETH 1D signals" | pool named on the row | The count is from all 55 ETH top-grade signals; that pool is named only in the detail tiles. Below-grade cards carry it on the row |
| O6 | Candles to 11 Nov, clock 12 Nov 00:05 UTC | `open_signals[*].days_elapsed` (23), page day counts (6) | 51 (BTC 2D live) | 52 | `stack_live.py` takes today from the last ETH daily candle; `refresh.py` and `tagstats.py` take it from the clock. Only when a run has no candle yet for the new UTC day |
| S1 | Feed down; setups held back | Picker Live row; Previous signals | "No live top-grade setups right now." / "No open top-grade setup with its edge intact." | unknown / held back, not none | The card and the Forming row say "unavailable" / "held back"; these two lines still state "none" |
| S2 | `ledger.csv` unavailable | Past signals count line | "0 signals · 0 missed +10%" | unavailable | Reads as an empty record (the summary boxes above it still say 104 and 33 signals) |
| S3 | A chart's candle file unavailable, after another chart was viewed | Chart tab heading, side box, cloud | The previous setup's heading and figures beside "Chart data unavailable for BTC 2D" | cleared | `renderChart` returns before resetting them |

Test harness (not the product): `tests/replay_at.sh` and `tests/test_gate_off.sh` keep the open 2D–8D bar whole, so a replay "as of" a date holds later days. Example: replay 2026-06-11, the BTC 5D bar opening 10 June closes at 65,706.62, the 14 June close; the 11 June close was 63,563.42. Year-end dates are unaffected (bars restart on 1 January). My replays rebuild those bars from the cut daily candles.

## Docs vs code

| # | Doc says | Code does |
|---|---|---|
| C1 | CONTEXT: one rounding rule; "the page's toFixed does the same" as `rounding.py` | Prices use `toLocaleString`. On a half-cent: $2,872.305 → page $2,872.31, `rounding.py` 2872.30; $3,191.905 → page $3,191.90 (O3). Three behaviours for one tie |
| C2 | FEED_SPEC: `days_elapsed` in calendar days since the close, closed daily candles | `stack_live.py`: `today` = last ETH daily candle's date, not the clock (O6) |
| C3 | CARD_SPEC: "closes above X", X = the close below which the low would not confirm | `stack_live.py` rounds X to the nearest cent, not down (D1, O1) |
| C4 | CARD_SPEC: anything on a different sample shows its own n, "the misses (their count and the pool)" | Top-grade cards name the pool only in the detail tiles (O5) |
| C5 | `tests/replay_at.sh`: "candles cut at the end of <date>" | The open multi-day bar keeps later days |
| C6 | FEED_SPEC audit #9: the page's 70% bar comes from `odds_fade.posting_bar_pct` | The page reads top-level `posting_bar_pct` first (audit #14). Sentence out of date |
| C7 | FEED_SPEC: `feed_live.py` "computes nothing of its own" | It derives `odds_fade.tier_fixed_on` and the sample sentence from its own clock, not from `refresh.py`'s tier anchor. Same value in both frozen states |

## Checks passed, frozen states

| Check | REPLAY | CURRENT | Not ok |
|---|---|---|---|
| 0 Raw candles (2D–8D rebuilt from 1D, served chart candles, clamps) | 9,085 | 9,085 | 0 |
| 1 Ledger: 919 rows, membership, every field, grade-record and odds-on-the-day columns | 27,572 | 27,572 | 0 |
| 2 grade_odds (8 graded rows, every field) | 65 | 65 | 0 |
| 3 if_it_misses (8 rows) and example_if_it_misses | 89 | 89 | 0 |
| 4 odds_fade (13 tier pairs, 168 signals, 7 rows, aliases, edge on exact share) | 62 | 62 | 0 |
| 5 Cards: 4 forming / 0, example, 23 open-signal cards | 1,991 | 1,707 | 0 |
| 6 open_signals (23), prints (34 / 30), top-level | 547 | 519 | 0 |
| 7 past_paths (ETH 104, BTC 33) and example_past_paths (75) | 559 | 559 | 0 |
| 8 Page: picker, Now cards, charts, cloud, Past signals, Previous signals, banner, footer | 3,551 | 2,935 | 0 |
| 9 Labels vs meaning | 21 | 10 | 2 (D1) |
| 10 Entry quality only (feed labels, page wording) | 154 | 126 | 0 |

Check 8 detail: REPLAY renders the live BTC 2D setup, 4 forming setups and the example; CURRENT the live setup and the example. On every chart: candles at the raw prices (within 0.02 px); Entry / Today / Confirms line on the right bar; Day 60 and "High usually ~day N" on the bars holding those calendar days; zones from the entry line to day 60 at my prices; four ladder bands with my share and n, coloured on the exact share; price tags in exact decimal arithmetic. Example "At the alert": axis scaled only from bars up to the entry, no outcome drawn, identical after toggling back. "What happened": high, low, day-10 and day-60 figures equal the daily candles. Cloud: 61 medians and both quartile bands at my values. Past signals: all 137 rows in each of the three views. No "Day 10" line exists on any chart (it is drawn only when a card has no ladder); Day 10 appears as a value in the live box and was checked.

## Other states covered

64 replayed dates (2022-06 to 2026-11): 8 with the market filter off, 11 around year-ends (29 Dec–3 Jan of 2023/24 and 2024/25, 31 Dec 2025), 21 with a top-grade forming low, 6 with nothing top-grade live or forming, 4 pairs on the day a signal's 60th day is open and the day after it closes (including the example signal), the first and last day of a gate episode, day 1 and day 10/11 of the live BTC 2D setup. Every replay ran all of checks 1–8. Year-end confirmation dates, signal ids, forming cards only on graded charts with the gate on at the trough, and signals leaving the open list on the day their 60th bar closes all held. Synthetic: feed down, held back, stale at 299 / 301 / 390 / 1,565 minutes, no setup with filter on and off, a top-grade forming card, an "On track" live card, extras withheld, ledger missing, chart candles missing, example file missing, an empty era and empty ladder row. No raw placeholder or page error in any of them.

## Definitional notes (not counted)

(a) gate read on the trough date — seen on 2025-12-05: header "Market filter: off" with two forming cards whose troughs were gate-on. (b) flash-print clamp: ETH 2017-06-21, BTC 2017-04-15 only. (c) low before high within a day. (d) "must close above" assumes today's open bar closes at the current price. (e) "day N of 60" is the day in progress. (f) peaked_10_or_more is 0 by construction. (g) odds_fade tier chosen by refresh.py's rule on each chart's own bars as of 1 January. (h) confluence cells and the two ETH HTF-divergence grade_odds rows are out of scope. (i) pooled odds_fade is in-sample, as labelled. (j) "known by then" = entry + 60 days on or before the date. (k) compatibility field names. (l) which card opens first — REPLAY opens on the forming, not-top-grade BTC 1D card, not the live top-grade BTC 2D setup. (m) an open signal's card is the card as issued at the entry close. (n) trades feed 404, lead-trader panels say "unavailable". (o) review banner and lead-trader description. (p) "if it misses" median best over all misses. (q) liveread "Regime gate" row. (r) "about N times a year" averages 2020 to last year, bear years included (130 top-grade signals in 2020-2025 / 6 years = 21.7, shown "about 22"; checked in the no-setup states). (s) typical drop is a median.

Two further observations, not counted: a live setup on its first day shows "best n/a · worst n/a" (no closed bar yet); How to read says "Size your position and leverage so this dip doesn't hurt you" of a median, so half of past signals dipped further.

## Files

`all_checks.csv` (frozen states and synthetic, 86,507 rows), `all_checks_replays.csv.gz` (1,941,841 rows), `disagreements.csv`, `dumps/` (page captures), `replays/` (frozen-state and clock-state check files), `batch_all.log`, and the scripts. Replay copies deleted.
