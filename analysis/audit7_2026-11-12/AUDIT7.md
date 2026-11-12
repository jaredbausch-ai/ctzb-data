# Audit 7: ETHKROS member site against the raw candles

**Top line: 60,626 comparisons, 32 disagreeing rows, 9 distinct issues. None of them is a wrong number.** Every price, percentage, count, date, day count and chart position matches my own recomputation from the raw candles, in both states.

- 28 rows (6 distinct items) are wording: the label does not say what the number measures.
- 4 rows are places where the docs and the code disagree. One of them is the same issue as the first wording item, which is why there are 9 distinct issues and not 10.

This is entry quality only. The data has no exits, so nothing here is a strategy return or a track record. Every signal is a computed signal, not a fill.

I wrote all the code myself and imported `regimes.py` only for the gate. I read nothing from the earlier audits or `AUDIT_LOG.md`, and I edited nothing in the repo (`git status` is clean). The code is in this folder: `lib.py`, `build.py`, `audit.py`, `page_dump.py`, `page_check.py`, `run_data.py`, `run_page.py` and `final.py`. The page dumps are `page_replay_0414.json` and `page_current.json`.

## Checklist (declared before the results)

1. **Ledger.** Every row: membership, low/entry dates, `entryPrice`, tags, every forward measure (reached10/15/20, touched30, bestMove, maxDrawdown, dipBeforeHigh, return60d, daysToHigh, year, surv10, scaled20), the grade's record columns and the odds-on-the-day columns.
2. **`grade_odds`.** Every field of A+/A/B/C for each asset, plus the two ETH "diamond or prime dot" rows. The HTF-divergence rows are out of scope.
3. **`if_it_misses`.** Every field.
4. **`odds_fade`.** Recomputed independently: the tier by refresh.py's rule on each chart's own bars, then groupings and outcomes on daily candles for days 11–60. Every field, including the `after_day10` fields and their `within60d` aliases.
5. **Every card.** The REPLAY forming cards (4), `example_card`, and all 23 `open_signals[].card` in each state. Every field: sample text and n, figures, exact and rounded medians, from_entry, the ladder, eras, timing, `low_day`, `price_now`/`entry_close`, kill close, and confluence dates.
6. **`open_signals`.** Membership, order, ids, dates, `days_elapsed`, day 10/30/60 (closed daily bars only), and best/worst so far.
7. **`past_paths`** (ETH and BTC A+) and **`example_past_paths`.** n and q25/median/q75 for every day 0–60.
8. **The page, in Playwright.** I followed the harness exactly as specified, with the clock set to `generated_at` + 6 min.
   - Every Live and Forming picker button and the example.
   - The Chart tab in both modes ("At the alert" and "What happened"), including line and zone positions, price tags, axis scale, the date axis, candles, the low circle, the side panel and the cloud.
   - Past signals (all / ETH / BTC), the Previous signals column, the banner, header, footer and How to read.
9. **Labels against meaning.**
10. **Entry quality only.**

## Disagreements

| # | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| 1 | both (8 rows) | Card stat "If it misses: up first"; How-to-read "above entry at some point first"; feed `up_first` | "94 of 95" (BTC C), "Every time" (ETH C 37/37, BTC A+ 5/5, example 10/10) | Read literally (above entry before ever below it, low first within a day): 1 of 95, 0 of 37, 0 of 5, 0 of 10 | Label. The code counts misses whose 60-day high was ever above entry (bestMove > 0). Nothing measures "first". |
| 2 | both (8) | Card tile "Worst drop, misses · all N {asset} {grade}" | e.g. −26.7% (BTC C), −19.1% (BTC A+) | The same values, which are the **median** worst drop of the misses | Label. The value is right but the tile reads as the single worst drop. |
| 3 | REPLAY (4) | Forming picker buttons | Bare "84%", "67%", "67%", "65%" | Rose 10% within 60 days, n 37 / 27 / 15 / 17 | Label. No words and no n (FEED_SPEC: `past_trades` beside every percentage). |
| 4 | both (4) | Past signals title "Every top-grade signal", All and BTC tabs | 104 ETH + 33 BTC rows | The live BTC 2D A+ of 2026-09-21 is not listed | Label. The table covers only signals whose 60 days have closed. |
| 5 | both (2) | Card tiles "Reached +20%", "Touched −30%" | No "within 60 days", no n beside them | CARD_SPEC wording rule and FEED_SPEC n rule | Label |
| 6 | both (2) | Feed `trades_a_year` ("17 on average") and `past_trades` on every card | "trades" | Computed signals; none was traded | Label (feed only). Fields cannot be renamed under FEED_SPEC. |
| 7 | docs | `docs/CARD_SPEC.md` line 26 | "the first graded ETH signal is 18 Apr 2020" | First graded ETH signal is ETH 3D 2020-03-21 (C); 18 Apr 2020 is the first ETH **A+** | Docs vs code |
| 8 | docs | `docs/CARD_SPEC.md` eras row | "The big-number measure split by entry date" | Eras show surv10 (rose 10% and never fell 25.3%); the big number is now reach10. The page labels the eras correctly. | Docs stale since 11 Nov |
| 9 | docs | `docs/FEED_SPEC.md` schema 5, `extras_live.py`, `analysis/carddesign.py` | `up_first` = "how many were above entry first" | Code: ever above entry within 60 days | Docs vs code (same as #1) |
| 10 | docs | CONTEXT.md, 11 Nov "+10% switch" paragraph | "did it without ever falling 25%" | 25.3% on the page and in CARD_SPEC (corrected in the 12 Nov audit #3 paragraph) | Docs stale |

All 32 rows are in `disagreements.csv`.

## Checks passed (both states combined)

| Area | Passed | Failed |
|---|---|---|
| Ledger: 919 rows per state, 26 fields each plus membership (my set = theirs) | 49,626 | 0 |
| `grade_odds` (10 in-scope rows per state) | 144 | 0 |
| `if_it_misses` (8 rows per state) | 160 | 0 |
| `odds_fade` (5 dip bands + 2 day-10 rows, tier of 13 chart/tag pairs, pool 168) | 108 | 0 |
| Forming cards (REPLAY: ETH 1D, ETH 2D, BTC 1D, BTC 2D; kill closes $2,047.21 and $73,533.06) | 222 | 0 |
| `example_card` (n 75, built only from signals known by 2024-09-22) | 110 | 0 |
| `open_signals[].card` (23 per state) | 2,392 | 0 |
| `open_signals` (23 per state, membership, order, all fields) | 646 | 0 |
| `past_paths` (ETH n 104, BTC n 33) and `example_past_paths` (n 75) | 1,118 | 0 |
| Feed labels and top level (market regime, scored date) | 152 | 2 |
| Page cards (6 REPLAY selections, 2 CURRENT selections) | 362 | 18 |
| Page charts (alert and happened modes) | 444 | 0 |
| Page Past signals (every row × 9 columns, counts, summaries) | 5,006 | 4 |
| Page picker / Previous signals / banner / header / footer | 102 | 4 |
| Docs claims (gate dates 2025-26 and "about 22 A+ a year": 21.7, both correct; 4 doc rows above) | 2 | 4 |

What the page checks confirmed:

- **Chart lines.** Entry/Confirms sit on the bar that closes on the entry date. Today sits on the last bar. Day 60 and "High usually ~day N" sit on the bars containing those calendar days, including the 2D bar restart on 1 Jan 2027 for the ETH 2D forming setup.
- **Levels and scale.** Level lines and price tags are at entry × (1 + exact %), correct to the cent. "At the alert" is scaled only from bars up to the entry plus the card's levels.
- **Example, "What happened".** The best and deepest-drop figures and their day ranges contain the true daily days 52 and 11. Day 10 is red at −8.4% and day 60 is +30.2%.
- **Clouds.** Median line, middle-half band and the example's own path all match my quantiles. No quartile is clipped by the −40%/+100% axis.

## Definitional notes (not counted as disagreements)

**The known choices, all as the repo states them:**

- **(a) Gate on the trough date.** The gate dates match CONTEXT: on to 2025-12-04, off to 2026-09-01, on from 2026-09-02.
- **(b) Flash-print clamp.** It applies to two bars only: BTC 2017-04-15 and ETH 2017-06-21. No drawn chart window includes either.
- **(c) Low before high within a day.** Used in the ladder, the from-entry row and dip-before-high (which includes the high day's low).
- **(d) Kill close.** It assumes today's open bar closes at the current price.
- **(e) "Day N of 60".** This is the day in progress (52 for BTC 2D).
- **(f) `peaked_10_or_more` = 0.** True in every row.
- **(g) Tier rule.** refresh.py's rule on each chart's own bars.
- **(h) Out of scope.** Confluence counts and the HTF-divergence rows. For confluences I checked only the dates: the signal exists and closes is +10 days.

**Other observations:**

- **The 25.3% liquidation line.** 25.3% is 1/3.3 − 5%, which treats maintenance as 5% of entry notional. With maintenance on current notional, 3.3x liquidates at −26.6%. The page states 25.3% as where 3.3x with 5% maintenance liquidates.
- **The pooled `odds_fade` table.** The tier is fixed on 1 Jan 2026 from pre-2026 outcomes, so 167 of its 168 signals are in-sample. Its `*_within60d_pct` aliases hold the days 11–60 values, as FEED_SPEC documents. No pooled odds-fade figure is displayed in either state, because every card has its own ladder. Only the 70% bar is used.
- **ETH ledger membership.** A row needs a funding read on the entry day, at least 60 of the prior 90 days of funding, and at least 5 of 7 days in both FCOOL windows. I rebuilt this from the raw funding file.
- **Quantiles.** They use linear interpolation between order statistics.
- **Ties.** BTC 2D and ETH 2D both at 67% in the picker, and two signals on 2020-11-05 in the Past signals table, keep the feed/ledger order. That is not an error.
- **Example sample date.** "Known by 2024-09-22" means day 60 ≤ 2024-09-22. No A+ signal sits on that boundary.
- **Lead trader with no data.** With `data/trades.json` returning 404 in the harness, the page says "No trades posted yet" and "Lead trader: not in". That reads as a quiet state, not as unavailable.
- **Zero values.** "Deepest drop 0.0%" (BTC 1D 2024-02-07) shows no sign, as the rule requires.
- **Year-end bars in refresh.py.** `select_tier` assumes the confirmation bar closes tf − 1 days after it opens, which is wrong for a short year-end bar. No signal sits near a 1 January cut, so it changes nothing.

## Entry quality only (item 10)

The card foot, the Past signals footnote, How to read and every feed record carry the label: computed signals, never traded, no exit, not a return or a track record. I found no page text that reads as a trade taken or a return. The only "trades" wording left is in the feed field names (#6).
