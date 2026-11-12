# Audit #8: ETHKROS member site against raw candles

**Top line: 59,709 comparisons. 0 numeric disagreements in either state. 11 rows disagree, covering 9 distinct items: 1 label that doesn't match what it measures (2 rows, one per state) and 9 places where the docs and the code disagree (one of these repeats the label item).**

Everything was computed with my own code from `data/*.csv` in each frozen state. The only import from the repo is `regimes.py`, used for the gate. No earlier audit folder or AUDIT_LOG was read. No file in the repo was changed.

These checks cover entry quality only. There is no exit in the data, so nothing here is a strategy return or a track record. Every signal is a computed signal; none was traded.

## Scope (declared before running)

| # | Check | States |
|---|---|---|
| 1 | Every ledger row: membership, entryPrice, tags, every forward measure, plus the grade-odds and odds-on-the-day columns | both |
| 2 | feed `grade_odds`, every field (the 8 grade rows and the 2 diamond/prime-dot rows; the HTF rows are out of scope per note h) | both |
| 3 | feed `if_it_misses`, every field | both |
| 4 | feed `odds_fade`, recomputed independently: tier, groupings, outcomes, edge, aliases | both |
| 5 | Every card (4 forming in REPLAY, `example_card`, 23 `open_signals[].card` per state), every field | both |
| 6 | `open_signals`: ids, dates, days_elapsed, day 10/30/60, best/worst | both |
| 7 | `past_paths` (ETH, BTC) and `example_past_paths`, every day and quantile | both |
| 8 | The page in Playwright (clock at generated_at + 6 min): every picker button, the example card, Chart tab ("At the alert" and "What happened") including line, zone, candle, axis and marker positions, Past signals (All/ETH/BTC), Previous signals, How to read, banner, footer | both |
| 9 | Labels against what each number measures | both |
| 10 | Nothing reads as a strategy return, a trade taken or a track record | both |

## Disagreements

| State | Where | Shown | Mine | Cause |
|---|---|---|---|---|
| REPLAY, CURRENT | feed `odds_fade.sample` (and the page's fallback ladder note) | "ETH signals in the walk-forward tier, every chart, 2016 on" | The tier fixed on 2026-01-01 is applied to every ETH signal from 2016 to 2026. 167 of the 168 signals predate that date and are the signals the tier was chosen on, so the sample is in-sample, not walk-forward | Label vs meaning |
| REPO | CONTEXT (28 Oct card paragraph) and CARD_SPEC "What keeps it airtight" 2 | verify_cards "re-derives every card … any mismatch fails the run" | `verify_cards.py` checks only n, surv10, reach20, touched30, bestMove, maxDip60 and the 4 timing medians. It does **not** check reach10 (the big number), scaled20, dipBeforeHigh, the `*_exact` fields, the eras, from_entry, the ladder, low_day, price_now, entry_close or must_close_above | Docs vs code |
| REPO | CONTEXT line ~1388 | "The big number is rose 10% and never fell 25%" | Since 11 Nov the big number is `rose10_within60d_pct`, and the level is 25.3% | Stale doc |
| REPO | CONTEXT "+10% switch" paragraph (~521) | "Still on +20% and to move: the if it misses stat and the 70% … status" | The code has already moved both to +10% (miss = reached10 no; the edge is marked on reached10) | Stale doc |
| REPO | FEED_SPEC "+10% switch" | `edge_measured_on: "rose 10% within 60 days"` | The feed writes "rose 10% after day 10 (days 11 to 60)" | Stale doc |
| REPO | FEED_SPEC Rules | "shows past_trades beside every percentage and labels forming lows provisional" | Typical high, Typical drop, Dip before the high and the "If it misses" line show no n for their own sample. Forming cards say "Setup forming … can still vanish" and never say "provisional" | Page vs doc |
| REPO | CARD_SPEC Wording rules | "Every percentage that depends on a time window says within 60 days"; n "in the card's corner" | Typical high, Typical drop from entry, Dip before the high, the ladder rows, the era bars, If it misses and the chart's level labels all leave out "within 60 days" (the How to read tab explains it). The n sits under the big number, not in a corner | Page vs doc |
| REPO | CONTEXT audit corrections (1) and FEED_SPEC | "rounded … once, on the exact value" | The page rounds the 6-place feed and ledger values again with toFixed. The 70% edge tests (`carddesign.fade`, page `setupFade`) compare integers that are already rounded. **No displayed value differs in either state**; this is latent only | Docs vs code |
| REPO | `analysis/carddesign.py` docstring; `verify_cards.py` comment | misses are "A+ signals"; "the ledger's dips are rounded to 0.1" | `extras_live` writes all four grades; the ledger stores 6 places | Stale comments |
| REPO | FEED_SPEC schema 5 `odds_fade` | "ETH walk-forward tier signals only" | Same as the first row | Docs vs code |

**How much the label matters.** I re-ran the fade with each signal judged against the tier fixed in January of its own year (the rule `forward.csv` uses), on otherwise identical daily-candle measurement:

| Row | Feed n | Feed rose 10% after day 10 | Feed edge | Own-year n | Own-year rose 10% after day 10 | Own-year edge |
|---|---|---|---|---|---|---|
| −10% to −20% | 29 | 79% | intact | 31 | 58% | gone |
| Red on day 10 | 64 | 63% | gone | 58 | 53% | gone |

This is context for judging the label, not a proposed replacement figure. The fade is not drawn on the page in either state, because every card has its own ladder. It is shown only in the feed, which Joe's AI reads.

## Checks passed, by number

| # | Check | REPLAY | CURRENT | Disagree |
|---|---|---|---|---|
| 1 | Ledger: 919 rows each, membership identical, 26 fields per row plus odds | 23,897 | 23,897 | 0 |
| 2 | grade_odds | 73 | 73 | 0 |
| 3 | if_it_misses (8 rows) | 81 | 81 | 0 |
| 4 | odds_fade: my tier = the same 13 chart/tag pairs, pool 168, 5 + 2 rows | 59 | 59 | 0 |
| 5 | Cards: forming ids, kill close, low_day, sample text and rule, every figure, ladder, eras, timing, exact medians | 1,685 | 1,444 | 0 |
| 6 | open_signals (23 each) | 300 | 300 | 0 |
| 7 | past_paths ETH n 104, BTC n 33; example n 75; 61 days × 3 quantiles | 556 | 556 | 0 |
| 8 | Page: full text of every card, picker, previous signals, chart side panels, record rows and summaries; chart geometry; datasets candles = last 70 raw bars; all 52 example-JSON bars = my ETH 2D bars | 3,541 | 3,090 | 0 |
| 9 | Labels and How to read (3.3x at 5% maintenance → 25.3% checked) | 9 | 9 | 0 |
| 10 | Every feed record carries the computed-signal label; withheld flags; regime | 4 | 4 | 0 |

Chart-specific points verified in both states:
- "Entry" / "Confirms … day 0" sit on the bar that closes on the entry date. "Day 60" and "High usually ~day N" sit on the bar or slot holding that calendar day.
- Zones and level lines run from the entry slot to the day-60 slot.
- Price tags match entry × (1 + exact pct), and edge prices are correct to the cent.
- All 4 ladder-zone values and positions match.
- Every candle wick, body and colour matches my data.
- The x-axis dates are right.
- The example "At the alert" is scaled only on bars up to the entry, draws 21 candles, and shows no outcome markers and no "this signal" line.
- "What happened": both outcome markers, their prices, percentages and day ranges match. The day ranges contain the daily high day and the daily low day. Day 10 and day 60 match.
- The cloud's 61-point median line and 122-point band match my quantiles.
- No displayed value shows −0.0 or +0.0.
- The scan for return, profit, trade and track-record wording found only disclaimers ("not a return or a track record", "computed, never traded") and the lead-trader panel, which reads "unavailable" in both states.

## Definitional notes (not counted)

- (a)–(h) as given. The regime gate is read on the trough date. The flash clamp touched ETH 2017-06-21 and BTC 2017-04-15 on every chart. Within a day the low comes before the high. "Must close above" assumes the open bar closes at the current price: ETH 1D $2,047.21 and BTC 1D $73,533.06, both matched. Day N is the day in progress. peaked_10_or_more is 0. The fade tier uses each chart's own bars. Confluence cells and the HTF rows were skipped.
- Mine, all matching the repo's choice:
  - Path quantiles are linear interpolation between order statistics.
  - Ties for the 60-day high or low take the first day.
  - "Dip before the high" includes the high day's low (low before high).
  - A forming pivot needs its right-hand bars strictly above it; ">=" gives the same 4 setups.
  - ETH ledger membership follows grade_live's funding-availability rule (90-day median and fcool window), treated as lens infrastructure.
  - "Closed by 2024-09-22" is d0 + 60 ≤ 2024-09-22. No signal sits on that boundary.
  - All rounding is half away from zero on exact rationals built from the CSV decimals. The float-based code agreed on every figure.

## Not checked (not shown to members, or out of scope)

`prints`, `confluence_windows`, `alerts`, `candle_check`, `next_buy_date`, `trades_a_year`/`signals_a_year`, `active_confluences` (note h), grades and lenses (taken as given). The empty-state line "about 22 times a year (2020 to 2025 average)" is not displayed in either state; I checked it anyway: 130 A+ signals ÷ 6 = 21.7, which rounds to 22.

## Observations (not counted as disagreements)

- How to read says "How many past signals … rose 10%" for figures shown as percentages.
- Every miss in all three A+ pools went above entry, so the "If it misses" line shows "Every time", and the miss tiles show only the pool size ("all 33 BTC A+"). Those medians rest on 5 BTC signals, and that count is not shown anywhere on the card.

## Files

- `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/all_checks.csv` (59,709 rows)
- `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/disagreements.csv` (11 rows)
- Code: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code/`
  - `lib8.py` (engine), `sigs.py`, `cards8.py`, `model8.py`
  - `page_dump.py` (Playwright)
  - `c_*.py` (the comparisons)
  - `page_REPLAY.json`, `page_CURRENT.json` (the rendered page)
