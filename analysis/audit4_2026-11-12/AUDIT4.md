# Audit #4: ETHKROS member site, every figure against raw candles (12 Nov 2026)

**Top line: 55,983 comparisons across both states. 46 disagree. Those 46 rows are 23 distinct figures or claims: 17 on the page and 6 in the docs against the code.**
None of the 46 is in the feed or the ledger. Every number in `ctzb_feed.json` and `ledger.csv`, in both states, matches my own recomputation from the raw candles exactly, to the last rounded digit (51,447 data comparisons, 0 disagreements). The disagreements are all on the page, or in the documents: where the chart draws a line, wording that says something other than what the figure measures, and one display artefact.

Entry quality only. There is no exit in the data, so none of these figures is a strategy return or a track record. The page's signals are computed signals, not fills.

## Method
- I wrote all the code myself, in `audit4/`: `lib.py`, `mine.py`, `check.py`, `page.py`, `compare_page.py`, `notes.py` and `assemble.py`. The only pipeline file imported is the state's own `regimes.py`, for the gate `rsi_regime(BTC_2D, 8, 13, 60, 41)`. I read no earlier audit folder.
- **Arithmetic.** Prices are parsed exactly as `Fraction` of the CSV text. Every threshold test is exact (high ≥ entry×1.10, low ≤ entry×(1−0.253), and so on). Every share and median is computed on the exact value, then rounded once, half away from zero.
- **Candles.** The flash-print clamp is applied to every candle file. CT is RSI(14), Wilder style. K is SMA3 of stoch(CT,14). A pivot needs 3 bars each side, strictly lower. A diamond is judged against the previous trough in the chain of all troughs, gated or not, with EPS = 1e-9.
- **Entry.** Entry is the confirmation-bar close at ti+3. It is dated by its close date, which is the next bar's open minus 1 day. In every case it equals the daily close on that date.
- **Window.** The forward window is daily bars for days 1–60 after the entry date. A window counts only once the day-60 bar has closed (UTC).
- **Clocks.** REPLAY uses 2026-11-12T04:14Z. CURRENT uses 2026-11-12T15:41:52Z, the feed's generated_at time.
- **Page.** I served it under Playwright exactly as specified: routed files, fonts aborted, everything else 404, and a page clock of generated_at + 6 min. I clicked every picker button, the example, both chart modes, Past signals (All, ETH, BTC), the Previous signals column and How to read, read every displayed number and checked it against my value. On the chart I also checked where the Entry, Today, Confirms, Day 60, High-day and Low markers sit, and the date labels on the x-axis.

## Checks declared before running
1. **Ledger rows.** Membership: every gated signal on ETH/BTC 1D–5D with a closed 60-day window, and nothing else; ETH only where funding data exists. For each row: low, entryPrice, tags (diamond with EPS), year, bestMove, maxDrawdown, dipBeforeHigh, return60d (6 dp), daysToHigh, reached10/15/20, touched30, surv10 and scaled20. I also checked the columns the page does not display: the grade columns and the odds-on-the-day columns.
2. **feed grade_odds**, every field including `sample`. The two "diamond or prime dot" groups were recomputed from my own tags. The "HTF divergence" pair is lens logic, so I only checked that it sums to the ETH total.
3. **feed if_it_misses**, every field, for all 8 asset/grade rows.
4. **feed odds_fade.** I recomputed the ETH walk-forward tier myself: as of 1 Jan, NMIN 8, win rate ≥ 70% on the 60-day close using chart bars, all 11 tags. Then the kept signals on daily candles from the entry close: the deepest dip over days 1–10, the day-10 close, and outcomes over days 11–60.
5. **Every card.** That is the 4 REPLAY forming cards, the example card (built only from signals whose day 60 had closed by 2024-09-22) and all 23 open-signal cards in each state. Checked for each: which sample rule applied, n, and the counts written into the sample text; all shares; the medians, both rounded and to 6 dp; the eras; the 4-row ladder (n, still rose 10%, went on to fall 25.3%); the four timing medians; low and confirmation dates; bars to confirm; price_now; and the kill close.
6. **feed open_signals**, both assets. Checked the id set and, for each, entry_date, entry_close, days_elapsed, day 10/30/60 (closed daily bars only), best and worst so far, and tags.
7. **feed past_paths**: n, plus q25, median and q75 for all 61 days for both assets.
8. **The page**, every displayed number as listed under Method, including prices and day counts.
9. **Labels against meaning**, for every claim made next to a number.
10. **Entry quality only**: nothing on the page reads as a return, a trade taken or a track record.

## Every disagreement (full rows in disagreements.csv)
| # | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| 1 | both | Chart tab, live BTC 2D (confirmed 21 Sep 2026): "Entry" line | at the 11 Nov 2026 bar (slot 69, the last bar) | at the 20–21 Sep bar (slot 43) | The page finds the entry bar by `open date == entry_date`. The entry date is a *close* date, and on a 2D+ chart no bar opens on it, so the lookup fails and falls back to the last bar. Every zone, the ladder blocks and the edge line therefore start at today. |
| 2 | both | Same chart: "Day 60" line | ~10 Jan 2027 (slot 99) | the bar closing 20 Nov 2026 (slot 73) | Same cause as #1 |
| 3 | both | Same chart: "High usually ~day 40" line | slot 89 | slot 63 | Same cause as #1 |
| 4 | both | Same chart, side panel | "Prices use today's close as a stand-in for the entry." | not true: $123,756.71, $95,254.43 and the other prices are built from the $86,594.94 entry close | The note is shown for every non-example card, including live ones |
| 5 | both | Chart tab, example, both modes: subtitle | "Its odds use the full history, including signals after it." | The card uses only signals whose 60 days had closed by 22 Sep 2024 (n 75) | Stale label: the example became a no-hindsight card on 12 Nov |
| 6 | both | Previous signals, under "Edge intact" | "No open top-grade setups." | 1 open top-grade setup (BTC 2D) is listed under "Edge lost" | The empty-state text ignores the lost group |
| 7 | both | Past signals (All and BTC), BTC 1D 4 Feb 2024, Deepest drop | −0.0% | 0.0% (true value −0.019417%) | toFixed prints a negative zero; display only |
| 8 | replay | Cards ETH 2D and BTC 2D (forming): card header, chart subtitle, chart low label | "Low 9 Nov 2026 · $2,003.24" / "· $72,643.48" | Both lows printed on 10 Nov 2026 | The 2D trough bar is labelled by its open date. The 1D cards correctly say 10 Nov for the same price. 6 places. |
| 9 | replay | Cards ETH 2D, BTC 2D and ETH 1D (forming) | "Best setup forming today." | Only BTC 1D (84%) is the best | The line is printed on every below-grade forming card |
| 10 | replay | Review banner | "Members see top-grade setups only" | 4 below-grade forming setups are shown in the picker and the card | Banner wording against what the page shows |
| 11 | replay | Forming cards, "If it misses … median peak" (How to read: "median peak before they failed") | BTC C +4.0% (2 cards); ETH C +5.5% (2 cards) | +3.0% / +5.3% if the peak is taken before the deepest drop | The figure is the best price over all 60 days, which comes after the deepest drop for 26 of 95 BTC C misses and 3 of 37 ETH C misses. The "up first" counts hold either way (94 of 95, 37 of 37). |
| 12 | both | Example card, same line | +5.3% | +4.2% | Same cause as #11 |
| 13 | both | Past signals summary ETH, "Misses: median peak first" | +4.8% | +2.6% | Same cause as #11: for 2 of 15 ETH A+ misses the high came after the deepest drop. BTC +6.2% agrees. |
| 14 | docs | CARD_SPEC "Big number", and FEED_SPEC card table | big number = surv10 | the page's big number is reach10 (rose 10%); surv10 is the line under it | Specs were not updated for the +10% headline |
| 15 | docs | refresh.py: walk-forward tier "using only data available by then" | Code takes signals confirmed before 1 Jan and scores them on outcomes ending after 1 Jan | With outcomes known by 1 Jan, the tier also includes ETH 2D prime dot. odds_fade becomes: red day 10 63% (n 64) vs 62% (n 58); <2% dip 91/85 (n 34) vs 90/83 (n 29); >20% dip 42/37 (n 19) vs 44/44 (n 16) | Code and docstring disagree, and the feed follows the code. odds_fade is not displayed in either state, because every card has its own ladder. |
| 16 | docs | FEED_SPEC top-level table, `open_signals` source | forward.csv, status open | datasets/open.csv (stack_live) | Stale row; the 12 Nov section and the code use open.csv |
| 17 | docs | CONTEXT.md inside both state folders | no "Audit #3 corrections" paragraph | present in the working repo's CONTEXT.md | The frozen states carry an older CONTEXT.md (the code is identical) |
| 18 | docs | CARD_SPEC ladder row | "still rose 10% without falling 25.3%" | measured as rose 10% *before* falling 25.3%. Some of those later fell 25.3% (example 5% row: 2) | Wording. The page's footnote ("before ever falling 25.3%") is right. |
| 19 | docs | CARD_SPEC wording | "N past trades", "(N trades)", "trades that got there" | "signals" | Stale; the page says signals |

Distinct figures and claims: #1–3 = 3; #4, #5, #6, #7 = 1 each; #8 = 2 dates; #9 = 3 cards; #10 = 1; #11–13 = 4 values; #14–19 = 6. On the label rows (#11–13) the feed agrees with my 60-day-peak value. What disagrees is the wording beside it.

## Checks that passed, by number (rows in all_checks.csv; REPLAY / CURRENT)
| # | Check | Passed | Failed |
|---|---|---|---|
| 1 | Ledger: 919 rows each, membership both ways (no missing or extra row; no ETH signal dropped inside the funding era), 16 displayed fields per row, plus 10 undisplayed grade and odds-on-the-day columns | 23,895 / 23,895 | 0 |
| 2 | grade_odds: 12 entries, every field including sample | 62 / 62 | 0 |
| 3 | if_it_misses: 8 rows × 9 fields | 72 / 72 | 0 |
| 4 | odds_fade: my tier = the 12 coded (chart, tag) pairs; 7 rows × n, +10%, +20%, edge | 31 / 31 | 0 |
| 5 | Cards: 4 forming (replay), the example, 23 open-signal cards, every field | 1,170 / 1,001 | 0 |
| 6 | open_signals: 23 per state, id set and 9 fields each | 208 / 208 | 0 |
| 7 | past_paths: 2 assets × 61 days × 3 quantiles, plus n | 370 / 370 | 0 |
| 8 | Page numbers, prices, dates and day counts (all views) | 2,257 / 2,073 | 7 / 7 (#1–3, #7) |
| 9–10 | Labels against meaning, and entry-quality wording | 112 / 48 | 20 / 6 (#4–6, #8–13) |

Also checked, with no difference found:
- The candle files served to the chart are byte-equal to the last 70 raw bars, on all 10 charts.
- The example JSON's 52 bars equal raw ETH 2D, and its entry_index is the bar opening 2024-09-21.
- "At the alert" never shows the outcome.
- The picker, the header (scored date, feed time, "Market filter: on"), the cloud (n and day 60) and the x-axis date labels are all correct.
- No page errors.

## Definitional notes (not counted as disagreements)
- **Regime gate date.** The gate is evaluated at the trough date, as the engine does. Evaluated at the confirmation date instead, 29 graded signals over the full history would flip in or out.
- **days_elapsed** is today − entry date, which is the number of the day in progress. BTC 2D shows "Day 52" at 04:14 on 12 Nov, while 51 full days have passed since the 21 Sep close. Day 10/30/60 and best/worst use closed daily bars only, which is correct.
- **Ladder same-day order.** Daily bars cannot say which came first within a day, and the repo's convention decides it. Read the other way, two rows change: example 5% shows n 41 / 76%, the other reading gives n 43 / 77%; open BTC 1D 18 Sep, 15% row, shows 18 / 22% / 61%, the other reading gives 19 / 26% / 58%.
- **Forming "must close above" with 1 bar to confirm** (ETH 1D $2,047.21, BTC 1D $73,533.06). It assumes today's still-open bar closes at the current price. `bars_to_confirm` is 1 although two closes remain (today's and the confirmation bar's). That field is not displayed.
- **`if_it_misses.peaked_10_or_more`** is 0 by construction, because a miss never reached +10%.
- **Rounding.** All rounding agrees on the exact values, with no ties. The feed's `*_exact_pct` (6 dp) gave the same cents as the true medians for every price shown.
- **Hard-coded figure.** The quiet-market card's "about 22 times a year (2020 to 2025)" is typed into the page, not taken from the feed. My count is 21.7 (130 A+ signals over 6 years, ETH + BTC). It is not displayed in either state.
- **The "Edge lost" badge** in Previous signals uses the pooled day-10 rule. The card's own-ladder rule gives the same answer here (worst −16.1% against an edge at −5%).

## Files (all in /tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit4/)
- AUDIT4.md (this report), all_checks.csv (55,983 rows) and disagreements.csv (46 rows).
- Captured page text: page_replay.json and page_current.json.
- My values: mine_*.json. Side checks: notes_*.json.
- Scripts: lib.py, mine.py, check.py, page.py, compare_page.py, notes.py and assemble.py.
