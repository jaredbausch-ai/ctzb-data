# Audit 22: numbers and labels on real data (independent)

Scope: every figure and label a member sees on the ETHKROS member site, checked against raw candles with the auditor's own code (`code/`). Only `regimes.py` was imported, for the gate. Nothing in the repo was edited. These are computed signals, not fills. There is no exit in the data, so this is entry quality only and is not a return or a track record.

## Top line

| Group | States | Comparisons | Disagreements (rows) | Distinct disagreements | Wrong figure | Wrong wording / state |
|---|---|---|---|---|---|---|
| (A) Frozen states (replay_0414, current) | 2 | 64,525 | 0 | 0 | 0 | 0 |
| (B) Replays of real dates (Sep 2020 to Nov 2026) | 302 | 5,947,341 | 12 | 1 | 0 | 1 (a state: the page reads "Setups held back" on good data) |

## Every disagreement

| Group | State | Where | Shown | Yours | Cause |
|---|---|---|---|---|---|
| B | Replays 2020-09-01 to 2020-09-11 (11 dates; 12 runs, since 09-03 also ran at 20:13) | Pipeline run, so the whole page | Feed withheld: `feed_live` strict check fails (`open_signals[k].card.rose10_within60d_pct: missing` ...). The page says "Setups held back. A data check failed on the latest run" | A published feed | A live ETH grade-A signal (e.g. ETH 1D 2020-08-05, ETH 5D 2020-07-13) gets a card with an empty sample ("all 0 past signals of the same grade across all ETH charts"), because no ETH grade-A signal had closed its 60 days until 2020-09-11. The page schema rejects a card with no figures, so the whole feed is withheld for 11 days of real data. The empty-sample guard (audit #18) covers forming lows only, not live cards. 2020-09-12 to 09-14 publish normally. |

No other figure, date, price, count, share or label disagreed in either group.

## Declared check list (fixed before any results), with results

| # | Check | Group A comparisons, disagreements | Group B comparisons, disagreements |
|---|---|---|---|
| 1 | Ledger rows: membership; entryPrice, tags, low and entry dates, every forward measure (6-place values, yes/no flags, daysToHigh, scaled20); grade-record columns; odds on the day, including dayScaled20 without signals that lack a year of volatility | 51,928 / 0 | 4,564,964 / 0 |
| 2 | grade_odds: every field, including sample dates and the two diamond-or-prime-dot rows. The HTF rows are lens logic and were not checked | 164 / 0 | 23,370 / 0 |
| 3 | if_it_misses and example_if_it_misses: every field present | 176 / 0 | 23,456 / 0 |
| 4 | odds_fade, recomputed from scratch: tier on each ETH chart's own bars as of 1 Jan, groups and outcomes on daily candles, both lists, aliases, each edge mark tested on the exact share, tier_fixed_on; trades_a_year | 122 / 0 | 16,889 / 0 |
| 5 | Cards (forming, example, every live card): every field, including ladder shown and exact, edge, low_day, confirms_on by the bar rule, must_close_above rounded down (solved analytically), price_now, entry_close, medians, eras, timing, sample text and n. Also: cards only where they are allowed, and every live signal has one | 280 + 146 + 3,784 / 0 | 45,850 + 5,986 + 442,642 / 0 |
| 6 | open_signals (ids, dates, days_elapsed, day 10/30/60, best/worst, edge level and status); prints (last 3 per chart plus the forming low, note read on the trough date, exact-tag diamonds); top-level fields | (in 5) + 640 + 12 / 0 | (in 5) + 97,900 + 1,710 / 0 |
| 7 | past_paths and example_past_paths: every quartile on every day | 1,470 / 0 | 159,740 / 0 |
| 8 | The page in Playwright: header, banner, footer, How to read, picker (Live and Forming), every card, Chart tab (both views on the example), Past signals (all, ETH, BTC), Previous signals, quiet card | 5,801 / 0 | 564,418 / 0 |
| 9 | Labels against meaning: every card label and tile, ladder and era captions, sample sentence, pools named on miss tiles, chart labels, side box, How to read | covered in 5 and 8 / 0 | covered / 0 |
| 10 | Entry quality only: card foot, record caption and heading, feed labels | covered in 5 and 8 / 0 | covered / 0 |
| | 2D-8D candle files equal their daily candles bucketed (context) | 2 / 0 | 285 / 0 |
| | Fail-closed runs: clock on D+1, candles ending on D | n/a | 119 / 0 (5 runs, all withheld, page "Setups held back") |

Chart-tab checks include: Entry, Today and Confirms lines on the right bar; Day 60 and "High usually ~day N" lines on the bar that holds that calendar day (including year-end short bars); every date tick; line heights and price tags from exact cents; price-axis labels at their own prices. For the example "At the alert" view, the scaling uses only bars up to the entry and no outcome candle is drawn. Ladder bands carry their n and colour on the exact share. The "This one" labels and the side box match the daily candles. The example chart file equals the 2D candles. Cloud medians are checked point by point.

## Coverage of group B (302 replays; declared in plan.json before running)

| Kind (as planned) | Replays | Observed in the published runs (285) | Replays |
|---|---|---|---|
| Market filter off (random) | 40 | Header "Market filter: off" | 124 |
| First and last day of each filter episode, ±1 day (6 flips) | 24 | Top-grade forming card present | 57 |
| Every date where a forming low's trough sits on the other side of a filter flip | 60 | Any forming card | 178 |
| Year-ends 26 Dec to 4 Jan, 2020/21 to 2025/26 | 60 | Live top-grade signal | 169 |
| Top-grade forming low (candidate dates) | 47 | Nothing live or forming; quiet card rendered | 66; 83 |
| Nothing live or forming | 12 | Worked example present / absent (before 22 Nov 2024) | 82 / 203 |
| 20 signals: day 60 in progress, and the day after it closes | 40 | Clock other than 04:14 (00:00:30 to 23:59) | 14 |
| Day after a confirmation | 15 | Year-end dates | 63 |
| Other clock times | 15 | | |
| Fail-closed (clock D+1 00:10, candles to D) | 5 | | |
| Sep 2020 boundary (added after the finding, 1 to 14 Sep 2020) | 13 | | |

One replay can be of several kinds. Per-replay check files are in `replays/<date>[_clock].csv.gz`, with page dumps in `replays/*_page.json.gz` and the run log in `replays/summary.jsonl`. `all_checks.csv` holds every group-A row and one row per replay and area.

## Testing the checker (planted errors, on copies of replay_0414)

40 errors were planted one at a time: 7 ledger, 21 feed and 12 page code. **36 changed something a check could see, and 36 were caught at the planted place.** That covers ledger values, tags, membership and odds-on-the-day; grade_odds, misses, odds_fade shares and edge marks; card exact medians, must_close_above, low_day, ladder, sample n, eras and price_now; open-signal days, status, best and card share; path quartiles; print price and note; trades_a_year. Page plants: day count, +10% level, Day 60 line, footer date, record column, ladder n, outcome candles drawn at the alert, and a double-rounded drop.

The other 4 were not caught, for these reasons:
- 1 was never planted, because its target ledger row did not exist. It was re-planted on a real row and caught.
- 1 would have tested the ladder bar on the whole-percent share. No shown share equals 70 in that state, so nothing changed.
- 1 would have scaled the example's alert axis on the whole path. The later bars sit inside the range already set by the drop and high levels, so nothing changed.
- In both no-change cases I checked that nothing rendered differently, and I replaced each with a plant that does change something. Both replacements were caught.

Details are in `plants*.json` and `plants.log`.

## Definitional notes (not counted as disagreements)

- I applied the brief's items (a) to (ai) as stated. None of them is contradicted by the repo's own code or output in any state checked.
- Specifically confirmed:
  - The gate is read on the trough date. The header shows today's filter.
  - The flash clamp is applied, and lows are taken before highs within a day.
  - must_close_above assumes today's open bar closes at the current price, and is rounded down.
  - "Day N of 60" is the day in progress. peaked_10_or_more is always 0.
  - The odds_fade tier is in-sample from 2016. The "known by then" rule is entry + 60.
  - The live card is the card as issued at the entry close.
  - Grades and lenses (including the HTF rows and confluence cells) are taken as given.
- The Live picker and Previous signals list top-grade live signals only. The feed carries all grades. This is layout.
- The example button is typed "Sep 2024". Dates elsewhere print "Sept". These are typed definitions, item (y).
- past_paths use the ledger's 2-decimal entry price. Every exchange close has 2 decimals, so this makes no difference.
- No float sits on a threshold: no percent-space vs price-space test, EPS test or must-close-above cent boundary came within tolerance in any state.

## Doc sentence that contradicts the code

- CARD_SPEC ("that only happened in early history") and FEED_SPEC Audit #18 ("Early history only (a replay of Aug 2020)") say empty samples are an Aug 2020 matter. A live card's empty sample withholds the whole feed on 1 to 11 Sep 2020.
