# ETHKROS member site: independent audit 3 (12 Nov 2026)

Two frozen states at HEAD 70313e5: **REPLAY** (data of the 04:14 UTC run, clock 2026-11-12T04:14Z, 4 forming cards) and **CURRENT** (candles to the 12:00 UTC 4H bar, feed 15:09 UTC, no cards). All figures recomputed with my own code (`mine.py`, `build.py`, `c1_ledger.py`, `c4_fade.py`, `c5_cards.py`, `capture.py`, `c7_page.py`, `c8_misc.py`, `assemble.py`); only `regimes.rsi_regime` was imported. Nothing in the repo was edited. Entry quality only: there is no exit in the data, so nothing here is a strategy return or a track record.

## Top line

**41,834 comparisons. 2,167 disagree, covering 133 distinct figures.**
- **2,035 rows (46 figures)** come from the documented flash-print clamp. The raw BTC 1D candle for 2017-04-15 has a $0.06 low; the repo pulls it back to the bar body. **None of these figures is displayed on the page.** All are in the ledger or the feed.
- **132 rows (87 figures)** are other disagreements. On the page: 38 rows (28 in REPLAY, 10 in CURRENT), plus 30 label or entry-quality findings.
- These all match: ledger membership (919 of 919 rows), every ledger per-signal figure apart from the clamp, all of `if_it_misses`, and every card figure that follows the code's definitions.

## Declared checks (fixed before results)
1. Every ledger row: entry, tags (diamond included), reached10/15/20, surv10, touched30, bestMove, maxDrawdown, dipBeforeHigh, return60d, daysToHigh, year and scaled20. Also the grade columns, and membership.
2. `grade_odds`: every field, including `sample`. There is no per-year field in the feed. The HTF-divergence rows were not recomputed because that flag logic is out of scope.
3. `if_it_misses`: every field.
4. `odds_fade`, recomputed from scratch: the walk-forward tier as of 1 Jan 2026, then the early-dip and day-10 tables. I compared them against the repo's method and against the documented definition.
5. REPLAY cards: every field, including the sample rule, eras, timing, the fade ladder, the kill close and the active confluences.
6. `past_paths`: every day, at q25, median and q75.
7. The page, served with Playwright: every picker button, card, chart in both modes, side box, Record tab (all, ETH, BTC), Previous signals, How to read, header and footer, the switch-off empty card, and the example JSON bars against raw candles.
8. Whether each label means what the number measures.
9. Entry quality only.
10. (Added) feed `open_signals`. None is A+, so none of them is on the page.

## Disagreements (each line is one group; every row is in `disagreements.csv`)
| state | where | shown | mine | cause |
|---|---|---|---|---|
| both | **Page**, example card: "Red on day 10" tile, the ladder row "Red day 10", and the chart label "Day 10 · red here" | 67% still rose 10% | 64% | holdcheck counts highs from day 1. The box says "between day 10 and day 60", and "still rose" implies after day 10. |
| both | **Page**, cloud note "Day 60 … middle half": example chart, plus the ETH 1D and ETH 2D charts in REPLAY | −1.0% to **+47.4%** | +47.3% | carddesign rounds path values to 2 places before taking quantiles (double rounding) |
| REPLAY | **Page**, chart price tags and side box, Typical high / Typical drop: ETH 1D | $2,325.66 / $1,689.34 | $2,325.58 / $1,688.34 | price = today × (1 + the 1-place rounded %), so it is rounded twice |
| REPLAY | same, ETH 2D | $2,354.40 / $1,703.71 | $2,354.33 / $1,702.93 | same |
| REPLAY | same, BTC 1D | $87,820.10 / $66,731.48 | $87,819.56 / $66,739.49 | same |
| REPLAY | same, BTC 2D | $84,133.28 / $62,086.08 | $84,147.61 / $62,082.86 | same |
| both | same, example: Typical drop (tag and side box) | $2,299.60 | $2,300.73 | same; it uses `grade_odds` −10.9 rather than the true median. The example's Typical high is exact. |
| both | **Page**, example chart "At the alert" | outcome markers drawn ("This one: $3,446.98 · +33.6% · days 51–52", "$2,309.17 · −10.5% · days 11–12") | none | shows the future. The side box says "This is all a member had at the alert". |
| both | **Page**, example ladder label | "Dip < −2%" | dips of 0 to −2% | "< −2%" reads as a deeper dip |
| REPLAY | **Page**, card ladder "still rose 10% after first falling that far", ETH 2D at 5/10/15/20% | 50/36/25/11% | 75/67/67/50% | counts only +10% reached before −25.3%. The page does not say so. |
| REPLAY | same, BTC 2D at 5/10/15/20% | 40/25/14/0% | 50/38/29/17% | same |
| REPLAY | **Page**, BTC 1D card "did it without ever falling 25%", overall and before 2022 | 78% / 73% | 76% / 68% at a 25% line | the line used is 25.3%. One signal fell between 25% and 25.3% and is counted as never falling 25%. |
| both | **Page**, example card ladder and "Edge gone below" | pooled ETH tier table (all grades), −20% | the setup's own record | CONTEXT (11 Nov): "never the pooled early-dip table". How to read defines Edge gone as this setup's odds. |
| both | **Page**, example tile "Price on day 60" | +22.4% | +30.2% for this signal (22.4% is the median of 104) | the label does not say "typical" or "median" |
| REPLAY | **Page**, 2D charts: "Confirms 16 Nov" line | slot of the bar opening 17 Nov | bar opening 15 Nov | `confIdx` divides the close date by the bar length, so it lands one bar late |
| REPLAY | **Page**, all 4 forming charts: "High usually ~day N" and "Day 60" lines | measured from today's bar | from the entry close (1 to 2 bars later) | day counts are from entry, but the lines start at today |
| REPLAY | **Page**, chart side box sample line (4 cards) | "from the last 17 ETH 1D trades…" | every such computed signal | "trades" for signals nobody took, and "last N" for what is all N (check 9) |
| both | **Page**, Record tab and link | "Record", "See the full record" | — | can read as a track record. The table footnote disclaims it; the tab and link do not (check 9). |
| both | feed `past_paths` | ETH d2 q75 4.5, d24 med 8.7, d40 med 13.9, d41 med 14.2, d55 q25 −0.3, d60 q75 47.4. BTC d9 q75 13.6, d28 q25 3.0, d32 q25 5.2, d42 q75 46.3, d48 med 24.9, d49 q75 40.5, d53 med 25.6 | 4.4, 8.6, 14.0, 14.1, −0.4, 47.3; 13.5, 2.9, 5.1, 46.2, 25.0, 40.6, 25.7 | double rounding (above) |
| both | feed `odds_fade.day10` red, compared with its own sample text ("highs from day 10 to day 60") | rose10 67 | 64 | holdcheck counts from day 1 |
| both | feed `odds_fade` on the stated clock (daily candles from the entry close): early-dip shallower-than-2% rose20; day-10 green rose20, red rose10 and rose20 | 86; 92, 67, 47 | 83; 88, 64, 48 | measured on chart bars counted from the confirmation bar's **open** date. The +10% early-dip column and every n agree. |
| REPLAY | feed card ladders compared with the CARD_SPEC literal ("rose 10% without falling 25.3%"): ETH 1D 5%, ETH 2D 5%, BTC 2D 5% and 10% | 57, 50, 40, 25 | 50, 40, 30, 13 | the code counts +10% reached before −25.3%, even when −25.3% comes later |
| both | feed `open_signals` `entry_date` and `signal_id`: ETH 2D 09-20, ETH 3D 09-22, ETH 5D 09-28, ETH 2D 11-03 | open date of the confirmation bar | 09-21, 09-24, 10-02, 11-04 (entry-close date) | forward.csv uses `edate`. Prints, cards and the ledger use the close date, so one signal carries two ids (FEED_SPEC: "the same at every stage"). |
| both | feed `open_signals` days_elapsed: ETH 3D, ETH 5D | 51, 45 | 49, 41 | counted between chart bar open dates |
| both | feed `open_signals` day10_pct: ETH 3D 09-22 | −0.0 | +1.5 (daily close on day 10) | the bar-open clock reads the close of day 9 |
| both | feed `open_signals` day10_pct: ETH 1D 11-02 | −8.8 (REPLAY), −10.0 (CURRENT) | blank | read from the 12 Nov daily bar, which had not closed |
| both | ledger: 10 BTC rows (2017-02-15 to 2017-04-10) maxDrawdown / touched30 / surv10 / dipBeforeHigh; all BTC grade columns | e.g. −12.27, no, yes | −99.99, yes, no | documented flash-print clamp |
| both | feed `grade_odds` BTC: A surv10, B surv10, B median dip, C surv10, C median dip | 70, 67, −10.0, 60, −12.0 | 69, 64, −10.6, 59, −12.5 | clamp (BTC A+ is unaffected) |
| REPLAY | feed BTC 1D card, active confluence "ETH 2D any", fell30 | 13 | 15 | clamp. Not shown on the page. |

## Checks passed (rows that agree, REPLAY / CURRENT)
| # | passed | notes |
|---|---|---|
| 1 | 16,450 / 16,450 | membership is exact: 919 rows. Entry = confirmation close = daily close on the entry date for all 919. Every tag, including diamonds, matches. The rest of check 1 is the clamp. |
| 2 | 57 / 57 | A+ rows exact, including sample "2020-04-18 to 2025-12-04" and "2016-10-26 to 2025-12-04" |
| 3 | 80 / 80 | all 8 asset × grade rows, every field |
| 4 | 58 / 58 | tier, n and edge marks reproduce exactly by the repo's method. 150 signals, ETH 1D–8D, first entry 2016-08-25. |
| 5 | 155 / — | all card fields, sample rules (17, 27, 37, 15), kill closes $2,047.21 and $73,533.06, timing and eras. The ladder matches the code. |
| 6 | 355 / 355 | |
| 7 | 2,745 / 2,583 | picker, cards, Record (137 / 104 / 33 rows, every cell), Previous signals, summaries, example (n 104, 86%, 80%, +34.9%, Day 41, eras 86% and 76%), "about 22 a year" (130 / 6 = 21.7), example JSON (52 bars equal raw) |
| 8 | 24 / 6 | |
| 9 | 1 / 1 | card foot, Record footnote, footer and How to read all say entry quality, not a trade or a track record |
| 10 | 76 / 76 | entry close, best and worst so far |

## Definitional notes
- **Entry.** The close of bar ti+3 on the signal's chart. All 919 rows match. The **entry date** in the ledger, prints and cards is the *last day* of the confirmation bar, so for 2D and longer it is open + tf − 1. forward.csv and `open_signals` use the bar's *open* date. `low` is the trough bar's open date.
- **Forward window.** Daily bars from d0+1 to d0+60. The row counts only once the day-60 bar has closed (UTC). ETH 1D and BTC 1D 2026-09-13 (day 60 = 12 Nov) are correctly held out in both states. No 60-day window crosses a candle gap; the only ETH 1D gap is 2016-05-20 to 2016-05-23.
- **Liquidation line: 25.3%.** A low *at or below* entry × 0.747 counts as liquidated (`measures.LIQ`; the ladder uses `<=`). Every label says "25%". Only How to read mentions 25.3%.
- **Regime gate.** It is read on the **trough** date (`engine.signals`: `inreg(dates[ti])`). Reading it on the confirmation date would change 22 eligible signals (9 in, 13 out).
- **Diamond.** The repo definition (CONTEXT and engine) compares **CT RSI** with K against the previous trough in the chain of **all** troughs, with `EPS`. My code reproduces every ledger tag. The brief's wording ("price vs K at consecutive gated troughs") is different: a gated chain changes 6 ledger tags, and using the trough-bar low instead of CT changes 231. My K arithmetic leaves no residue, so EPS changes nothing here, which is consistent with the fix.
- **Membership.** ETH rows need funding data (a value on d0, 60 of the prior 90 days, and 5 of 7 for FCOOL). This drops 203 gated ETH signals, 2016-06-21 to 2020-03-19. BTC uses full history. 8D is not graded.
- **odds_fade.** The pool is the ETH walk-forward tier as of 1 Jan 2026: 1D hollow; 2D diamond and hollow; 3D prime dot; 5D A, B, any, diamond, prime dot and zone-exit B; 8D C and any. Tier "win" means the 60-day close is above entry. It runs on chart bars with day 0 at the confirmation bar's **open** date. The early-dip +10% counts days 10–60; the day-10 table counts days 1–60.
- **Rounding.** Half away from zero is in force and was exercised. ETH 2D before 2022: 62.5 → 63 (the built-in would give 62). BTC 1D day first +20%: 22.5 → 23. Feed and page agree on every such case. The exceptions are past_paths (2-place inputs) and the derived prices.
- **Code against docs.**
  - The `extras_live.py` docstring and the FEED_SPEC schema-5 table still define a miss as "+20%"; the code uses +10%.
  - FEED_SPEC "Top level" still says schema 3.
  - The `odds_fade.sample` text is wrong for the day-10 rows.
  - The CARD_SPEC ladder wording differs from the code.
  - The card `sample` text says "the last N" when it means all N.
- **Other notes.** The ladder never hit a day with both +10% and the fall on the same bar. "Data through 12 Nov 2026" includes a forming 12 Nov daily bar; the last closed bar is 11 Nov. The lead-trader panel is built to show real trades with Move % and Account % beside the computed odds. It is empty now, but it would be the only real-return figure on the page.

Files: `all_checks.csv` (41,834 rows), `disagreements.csv` (2,167 rows; `[n]` in `location` is the check number), page captures `page_REPLAY.json` and `page_CURRENT.json`.
