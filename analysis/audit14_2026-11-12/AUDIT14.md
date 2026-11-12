# AUDIT 14 — ETHKROS member site vs raw candles (independent)

**Top line.** 61,267 comparisons across the two frozen states (REPLAY 31,034; CURRENT 30,233).
**Numeric disagreements: 0 rows, 0 distinct figures.** Every number a member sees in either state equals
my own value computed from the raw candles. **Docs-vs-code disagreements: 11** (counted separately, table
below); none changes a number shown in either frozen state, two were demonstrated on a gate-off replay copy.

All code is mine (`lib.py`, `lib2.py`, `lib3.py`, `expect.py`, `c0`–`c9`, `harness.py`); only `regimes.py`
was imported, for the gate, and my own state machine agrees with it on every day since 2016. No earlier
audit, AUDIT_LOG or other scratch folder was read. Nothing in the repo was edited. Entry quality only:
nothing here is a strategy return or a track record; the signals are computed, none was taken.

## What was checked (declared before results)

1. Every ledger row, every column, and membership.
2. feed `grade_odds`, every field (the two HTF-divergence rows excluded, out of scope).
3. feed `if_it_misses` and `example_if_it_misses`.
4. feed `odds_fade`, recomputed from the candles (tier by the original rule, outcomes on daily candles days 11–60), aliases, edge marks on the exact share.
5. Every card: REPLAY forming cards, `example_card`, every `open_signals[].card`.
6. feed `open_signals` (ids, dates, days, day 10/30/60, best/worst, edge level and status) and `prints`.
7. feed `past_paths` and `example_past_paths`.
8. The rendered page (Playwright, clock = generated_at + 6 min): every picker button, the example, Chart tab (both modes), Past signals (all/ETH/BTC), Previous signals, How to read, banner, footer.
9. Labels vs meaning. 10. Entry quality only.
0. (added) Raw data: 2D–8D bars rebuilt from 1D, 1D vs 4H, clamp list, gate, chart close = daily close on the entry date.

## Disagreements

**Numeric: none.**

**Docs vs code (11).** "Copy" = a copy of CURRENT cut at 2026-06-11 and replayed with `CTZB_NOW=2026-06-11T04:14Z` (`exp_gateoff/`), not one of the two frozen states.

| # | State | Where | Code / page does | Docs say | Note |
|---|---|---|---|---|---|
| D1 | Copy, gate off | stack_live forming cards, feed alerts, page | 10 forming cards ("BTC 1D 79% rose 10% in 60 days") and 10 forming alerts while the header reads "Market filter: off" | How to read: "Signals only fire while our market filter says the trend is on your side. In a downtrend the system stays quiet" | stack_live builds a card for every forming low with no gate test; odds come from gate-on signals; a gate-off low can never confirm |
| D2 | Copy | 8D forming cards | ETH 8D card graded C on "110 signals across all ETH charts"; BTC 8D card on 19 8D signals that are not in the ledger; verify_cards checked 9 of 11 cards | CARD_SPEC #2: verify_cards re-derives every card; grade_live: 8D is not graded | verify_cards skips 8D. No 8D card in either frozen state |
| D3 | Both | `schema_version` | 5, with 20+ fields added on 11–12 Nov | FEED_SPEC Rules: goes up by one whenever a field is added | later sections say "schema stays 5" |
| D4 | Both | page medians | shows `*_exact_pct` rounded once | FEED_SPEC audit #3: "Show the rounded fields" | audit #8 text says the opposite; same figure on all 52 cards |
| D5 | Both | live BTC 2D card | day 52 of 60, edge_status lost, yet the card shows the from-entry 85%, the $123,756.71 typical-high level and the live frame colour; only the Previous-signals column says "Edge lost" | CONTEXT 31 Oct: "Never put a from-entry figure beside a live trade" | 12 Nov design gives live setups a from-entry card (choice m); the standing rule was not amended. Figures are correctly labelled |
| D6 | Both | index.html 367, 553 | typed fallback `?? 70` | FEED_SPEC audit #9: the page types no figures | only reached if `odds_fade` is withheld |
| D7 | Both | prints[].tags of a forming low | diamond / filled / prime from CT and K rounded to 1 decimal, no EPS | CONTEXT tag table (exact values, EPS) | can differ within 0.05 of a threshold; the 4 REPLAY forming prints agree. Not on the page |
| D8a | Both | Chart tab ladder zones | four shares (82 / 60 / 38 / 17%) with no caption and no n | CARD_SPEC: each ladder row shows its own n | n (33 / 15 / 8 / 6) is on the Now card only |
| D8b | Both | Chart tab, example | "ETH 2D · example", "from 75 past signals" | CARD_SPEC: the sample rule is said "again on the chart view" | live and forming views restate it |
| D9 | Both | liveread.csv "Regime gate" row | gate read on the entry / confirmation date | stack_live's own comment: trough date "as everywhere else" | dashboard dataset only |
| D10 | Both | feed `trades_a_year` | 16.6383 → 16.6 → "17", second step by Python's built-in format (half to even) | CONTEXT: one rounding rule, once | same result today; not on the page |

## Checks passed (comparisons, all agreeing)

| Check | REPLAY | CURRENT | What |
|---|---|---|---|
| 0 raw data | 13 | 13 | 8 multi-day files identical to my rebuild from 1D; 1D identical to 4H on every day both cover; one clamp per chart (BTC 2017-04-15, ETH 2017-06-21); gate identical on 3,969 days; all 1,197 confirmed signals' chart closes equal the daily close on the entry date |
| 1 ledger | 24,817 | 24,817 | 919 rows × 27 fields: membership, entry price, tags, 4 measures to 6 places, day of high, 6 yes/no columns, 3 grade columns, 7 odds-on-the-day columns |
| 2 grade_odds | 81 | 81 | 10 rows × 8 fields (8 asset/grade + 2 marker rows) |
| 3 if_it_misses | 88 | 88 | 8 rows × 10 fields + the example's 7 |
| 4 odds_fade | 61 | 61 | my tier = 13 chart/tag pairs = setups.csv; pool 168; 7 rows × 8 fields incl. aliases and edge marks |
| 5 cards | 1,958 | 1,682 | 28 / 24 cards × ~70 fields: sample text and n, shares, rounded and exact medians, eras, timing, from-entry, 4 ladder rows (shown and exact), low day, dates, must-close-above, prices |
| 6 open signals, prints | 635 | 595 | 23 open signals × 14 fields incl. edge level / status; 34 / 30 prints × 9 fields |
| 7 past paths | 557 | 557 | 3 clouds × 61 days × 3 quantiles, n |
| 8 page | 2,813 | 2,328 | Now cards 369 / 121; Chart tab 420 / 186; Past signals 1,967 each; picker, Previous signals, banner, footer, How to read, served candles, example JSON |
| feed misc | 11 | 11 | clock, labels, trades_a_year, rounding-tie scan |

Check 8 detail. Chart tab, for every selection: title, subtitle, 70 (or 21 / 52) candles' x, high, low, open, close against raw; slot count; date-axis labels; Entry / Today / Confirms on the bar that closes on the entry date; day-10 anchor, typical-high day and Day 60 on the bars containing those calendar days (the ETH and BTC 2D forming charts cross 1 January correctly); zones entry-to-day-60; five level lines and four price tags to the cent; ladder zone shares and colours on the exact share; cloud polyline and band, 183 points each; side panel. Example "At the alert": axis top / bottom match the bars up to the entry only, no later candle, no outcome marker, no own path; "What happened": high $3,446.98 +33.6% on day 51 (shown days 51–52), low $2,309.17 −10.5% on day 11, day 10 −8.4%, day 60 +30.2%.
A mutation test planted 12 errors in the rendered dump (a share, a day, a cent, a line one bar early, a line 0.4 px off, a badge, a count); the checker flagged all 12.

Checks 9 and 10. Every label was compared as exact text against my own wording of the definition (included in the counts above). No grade letter appears in any rendered text or in feed `sample` / `note` values. Every `label` in the feed (111 / 103) carries "not a fill" and "Entry quality only". "Trade", "track record" and "return" appear on the page only for the lead trader's real trades, in denials, or in the risk warning; no "profit", "win rate", "performance" or similar.

## Definitional notes

Known choices (a)–(p) all hold as stated and the repo does not contradict them in anything a member sees (D9 is the one dashboard-only exception to (a)). Specifics observed: (d) REPLAY ETH 1D and BTC 1D are one bar from confirming, thresholds 2,047.2081 and 73,533.0623; (e) BTC 2D shows "Day 52"; (f) `peaked_10_or_more` is 0 on all 8 rows; (i) the pooled odds fade is not rendered on any card in either state; (n) 404 on trades.json only.

Further choices I had to adopt, none documented outside code, none counted:

- Path quartiles use linear interpolation between order statistics.
- Ties take the first day (day of the high, day of the low, low day inside a bar).
- "Dip before the high" includes the low of the high's own day.
- Pooled odds-fade bands: a dip exactly on −2 / −5 / −10 / −20 goes to the shallower band (nearest cases −2.0045, −4.9903, −5.0034).
- 365-day volatility = population standard deviation of the 365 daily log returns ending on the entry date; "2016–21 median" runs over every date to end-2021 that has 365 returns.
- Odds on the day: weight 5 toward the asset's all-grade base rate, blank under 10 prior same-grade signals (defined only in grade_live.py comments).
- "Must close above" is the CT-equality close rounded to the cent, so the ETH figure ($2,047.21) is itself a confirming close.
- ETH ledger membership needs funding with a 90-day median (60+ of the prior 90 days) and 5+ days in both 7-day windows.

Near-threshold cases, all on the right side: ETH 1D 2024-03-26 high 3,947 vs +10% at 3,946.44; BTC 5D 2019-09-12 low 7,296.44 vs −30% at 7,296.60; ETH 3D 2025-12-02 low 2,238.74 vs −25.3% at 2,238.53; BTC 1D 2019-09-01 low 7,296.44 vs −25.3% at 7,295.59. No exact ties anywhere, no stored figure on a display half, no ladder share within half a point of 70. One figure displays as zero and shows no sign (BTC 1D 2024-02-07 deepest drop −0.019 → "0.0%").

Data note: ETH_1D.csv has no bars for 2016-05-21 and 2016-05-22 (before the first gate-on day, 2016-06-09; no member figure touches them).

## Not checked

Grades and lens logic, `active_confluences`, `confluence_windows`, the two HTF-divergence `grade_odds` rows (out of scope); `next_buy_date`, `alerts`, `candle_check` (not on the page); page states that occur in neither frozen state (feed down / held / stale, no setup, a top-grade forming card, an "On track" badge).

## Files

Folder `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit14/`:
`all_checks.csv` (61,278 rows: 61,267 comparisons + the 11 docs-vs-code rows), `disagreements.csv` (11 rows),
`page_REPLAY.json`, `page_CURRENT.json`, `page_EXP_GATEOFF.json` (rendered dumps), `shot_*_now.png`, the scripts, and `exp_gateoff/` (the gate-off replay copy).
