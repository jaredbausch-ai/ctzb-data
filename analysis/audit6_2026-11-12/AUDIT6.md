# Audit 6: ETHKROS member site against raw candles (independent)

**Top line: 56,371 comparisons, 25 disagreement rows: 16 numeric rows (5 distinct figures, all from one cause) and 9 labels-vs-meaning rows (5 distinct issues). The feed and the ledger have 0 numeric disagreements.** The 5 figures are the "Where the past signals went" cloud on the example's **At the alert** view. That cloud is built from all 104 ETH top-grade signals, including 29 whose outcome was not yet known at the 22 Sep 2024 alert. Only 75 were known then.

Entry quality only. These are computed signals, never fills, and there is no exit in the data, so nothing here is a strategy return or a track record.

Method: I wrote all the code myself, under `audit6/`: `core.py`, `state.py`, `checks.py`, `run.py`, `page_dump.py`, `page_check.py`. The only repo import is `regimes.rsi_regime` (the gate). I rebuilt the 2D/3D/5D/8D bars from the 1D candles using the 1 January restart rule; they match `data/*` exactly. On top of that I applied the clamp, Wilder RSI, Stoch K, the pivots, tags (EPS 1e-9), entries and forward windows by calendar date. The +10%, +20%, −25.3% and −30% tests compare exact prices (`Fraction`), and rounding is half away from zero, applied once. The page ran in Playwright with the routes as specified and the clock at generated_at + 6 minutes (REPLAY 04:20 UTC, CURRENT 16:45 UTC). I did not read any earlier audit folder or `AUDIT_LOG.md`, and I did not edit anything in the repo.

## Check list (declared before running)
1. Ledger: membership, low, entryPrice, tags, reached10/15/20, touched30, bestMove, maxDrawdown, dipBeforeHigh, return60d, daysToHigh, year, surv10, scaled20, plus the grade-record and odds-on-the-day columns (grades taken as given).
2. `grade_odds`, every field (the HTF-divergence rows are out of scope, per (h)).
3. `if_it_misses`, every field, per asset and grade.
4. `odds_fade`: tier rebuilt per (g); bands, n, +10%/+20% shares and edge marks rebuilt on daily candles.
5. Every card: 4 forming cards (REPLAY), the `example_card`, and all 23 `open_signals[].card` (each state). Checked every field: sample text and n, rounded and exact medians, shares, eras, timing, from_entry, ladder, low_date, low_day, confirms_on, bars_to_confirm, must_close_above, price_now and entry_close.
6. `open_signals`: membership (graded charts, both assets), ids, dates, entry, tags, days_elapsed, day10/30/60 from closed daily bars, best and worst.
7. `past_paths`: signal count, and q25/median/q75 for each of days 0–60.
8. The page: header and banner, footer, picker (live and forming), Now card for every button and the example, the Previous signals column, the Chart tab for every button (example both At the alert and What happened, including line, zone, band, tag and axis geometry, alert-only scaling, and the cloud), Past signals (all/ETH/BTC, every cell and summary box), and How to read. The served candle and example files were also checked against my own bars.
9. Labels vs meaning.
10. Entry quality only (wording scan).

## Disagreements

| state | where | shown | mine | cause |
|---|---|---|---|---|
| REPLAY, CURRENT | Chart · example · At the alert (both visits): cloud subtitle | Every past ETH top-grade signal, n 104 | n 75 (60th day closed by 22 Sep 2024) | Cloud reads `feed.past_paths`, which has every A+ signal up to today. That is hindsight at the alert |
| REPLAY, CURRENT | same: cloud note, day-60 middle half | −1.0% to +47.3% | +2.7% to +49.4% | same cause (the median, +22.4%, happens to agree) |
| REPLAY, CURRENT | same: median path polyline | 58 of 61 points off | 0 | same cause |
| REPLAY, CURRENT | same: middle-half band polygon | 112 of 122 points off | 0 | same cause |
| REPLAY, CURRENT | Previous signals badge "Edge lost" / "On track" (BTC 2D 21 Sep) | Rule: red on day 10, or past the first "gone" early-dip band, taken from the pooled `odds_fade`. That table is ETH tier signals only, and here it is applied to a BTC setup | Rule: the setup's own ladder (CONTEXT: "the player, not the league"; How to read: "Edge gone"). The outcome agrees here ("Edge lost") | badge basis differs from the documented definition |
| REPLAY, CURRENT | feed `odds_fade` `rose10_within60d_pct`, `rose20_within60d_pct`, `edge_measured_on: "rose 10% within 60 days"` | "within 60 days" | counts only highs on days 11–60 | field names say a different window than the value measures (the `sample` text explains it; the names don't) |
| REPLAY, CURRENT | tile "Typical price on day 60, misses" | labelled a price | the median day-60 change from entry, in % | label says price, value is a percentage |
| REPLAY | the miss tiles ("Worst drop, misses", "Typical price on day 60, misses") on the 4 forming cards | read as the card's sample, e.g. 37 BTC 1D signals | Every BTC C signal: 95 misses of 312 (BTC 1D, BTC 2D). Every ETH C signal: 37 misses of 111 (ETH 1D, ETH 2D) | The pool note ("all N … signals of this grade") sits only under the stats column. The tiles don't say which sample they use |
| REPLAY, CURRENT | Previous signals header "odds update each close" | promises odds | the column shows best/worst so far and a badge, no odds | header wording |

The full rows are in `disagreements.csv`. "Example" and "example · alert" are the two separate At-the-alert visits; the What-happened view also shows n 104 but is not counted (see the notes).

## Checks passed (state: checks, disagreements)

| area | REPLAY | CURRENT |
|---|---|---|
| 1 Ledger: 919 rows each, membership exact, 25 fields per row | 22,976 / 0 | 22,976 / 0 |
| 2 grade_odds (8 grade rows + 2 marker rows) | 60 / 0 | 60 / 0 |
| 3 if_it_misses (8 rows) | 80 / 0 | 80 / 0 |
| 4 odds_fade (tier, 5 bands, 2 day-10 rows) | 38 / 0 | 38 / 0 |
| 5 Cards (REPLAY 4 forming + example + 23 open; CURRENT example + 23 open) | 1,385 / 0 | 1,197 / 0 |
| 6 open_signals (23 each, identical sets) | 230 / 0 | 230 / 0 |
| 7 past_paths (ETH 104, BTC 33, 61 days) | 370 / 0 | 370 / 0 |
| 8 Page (Now 6/2 buttons, Chart 8/4 views, Past signals 3 tabs × 137/104/33 rows, Previous, header, How to read, data files) | 3,365 / 8 | 2,902 / 8 |
| 9 Labels vs meaning | 5 / 5 | 5 / 4 |
| 10 Wording scan (2 hits, both disclaimers: "not a trade or a track record", "not a return or a track record") | 2 / 0 | 2 / 0 |

Chart geometry passed everywhere except the cloud above:
- Entry and Confirms lines sit on the bar that closes on the entry date.
- Today sits on the bar holding the clock date.
- Day 60 and "High usually ~day N" sit on the bar holding that calendar day, with future slots following the 1 January rule.
- The axis scale is linear through every gridline label. At the alert, the scale uses only bars up to the entry (lo 1,961.4992, hi 3,729.111), and only 21 candles are drawn, with no outcome markers.
- Level prices, tags, zone and band rectangles, band colours and x-axis dates all match.
- The example's "This one" markers and the What-happened side box match the daily candles.

No Day-10 line is drawn on any view: every card has its own ladder, so the page omits that line.

## Docs vs code
1. FEED_SPEC top-level table: `cards[]` is "one per live setup". In the code it is forming setups only; live setups' cards are in `open_signals[].card`.
2. FEED_SPEC: open signals come "with day 10/30/60", but `day60_pct` can never be filled. A signal leaves the list on the day its 60th daily bar closes.
3. FEED_SPEC schema-5 row describes `odds_fade` as "Every kept signal, all grades". In the code (refresh.py `CHARTS`) it is ETH charts only. The feed's own `sample` text does say ETH.
4. CARD_SPEC "airtight" item 1 says "the big number exceeds 'rose 10%'". The big number is now rose 10%, and the code checks surv10 ≤ reach10.
5. CARD_SPEC says "ETH samples start in 2020 (funding data begins then)". The code rule is narrower: funding vs its 90-day median must be computable (60 of the prior 90 days), and 5 of 7 days must be present in both cooling windows. The first ETH row is 2020-04-18; with that rule my membership matches exactly.
6. CONTEXT (member card redesign) still quotes the +20%-era miss figures (ETH +7.1%, 26 of 104; "NOT in the feed yet"). The feed now has the +10% figures: ETH A+ 15 of 104, median +4.8%.
7. The measures.py docstring still calls surv10 the HEADLINE.
8. These read a fixed 60 daily bars by index where the docs say 60 calendar days: the ladder and from-entry rows (stack_live) and past paths (carddesign). The result is the same here, because the daily data has no gap after 2016-05-23. carddesign also finds the entry bar by matching the close within $0.005; nothing was skipped.

## Definitional notes (not counted)
- (a) Gate read on the trough date. (b) Flash-print clamp: ETH 2017-06-21 0.10→325.41 and BTC 2017-04-15 0.06→1,173.13, the only clamps. The served chart candles are raw, and no flash print falls in them. (c) Low before high within a day: the dip-before-high includes the high day's low, and the ladder and from-entry rows check the low first in every step. (d) Kill close assumes the open bar closes at the current price: ETH 1D 2,047.21 and BTC 1D 73,533.06 reproduced to the cent. (e) days_elapsed / "day N of 60" is the day in progress. (f) peaked_10_or_more = 0. (g) The odds_fade tier comes from refresh.py's rule on chart bars, as of 2026-01-01. (h) Confluence cell counts and the HTF-divergence grade_odds rows are not checked.
- Example sample: "60th day closed by 22 Sep 2024" taken as entry + 60 ≤ 2024-09-22. No signal sits on the boundary.
- Day of high and day of deepest dip: the first occurrence. Timing medians of whole days are rounded half away from zero (x.5 → up).
- scaled20: population SD of 365 daily log returns ending on the entry day, divided by the median of that series over ≤2021.
- Quantiles: linear interpolation. Prices built from the 6-dp `*_exact_pct` fields agree at the cent with prices built from the unrounded medians, in every case.
- Percent tests on exact prices (mine) and on float percentages (pipeline) gave the same verdict on every signal.
- The example's What-happened cloud also uses all 104 signals. That view reveals the outcome, so I did not count it.
- The no-setup message's hard-coded "about 22 times a year (2020 to 2025 average)" is not displayed in either state. It checks out: 130 A+ signals in 6 years = 21.7.
