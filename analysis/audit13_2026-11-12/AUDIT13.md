# Audit 13: ETHKROS member site against the raw candles

**Top line: 59,181 comparisons. 0 numbers disagree. 4 rows disagree, all from 1 label (no figure is wrong). 4 docs-vs-code disagreements, counted separately.**

States: REPLAY (`a13/replay_0414`, clock 2026-11-12T04:14Z, 4 forming setups) and CURRENT (`a13/current`, feed 19:53:37Z, no forming setups). All values were computed with my own code from `data/*.csv` (`lib13.py`, `model13.py`). Only `regimes.rsi_regime` was imported, for the gate. I took grades and lenses from each ledger or feed row as given. I compared every value as it is stored: 6-place values to 6 places, and displayed values as the exact text the page shows.

Entry quality only. These are computed signals, not fills. There is no exit in the data, so nothing here is a strategy return or a track record.

## Checks declared before running

1. Ledger, every row. Membership; trough date; entryPrice; tags; year; reached10/15/20, touched30, surv10 and scaled20 (decided on prices); bestMove, maxDrawdown, dipBeforeHigh and return60d to 6 places; daysToHigh; gradeReach20, gradeTouched30 and gradeMedDrawdown; all 7 odds-on-the-day columns. In dayScaled20, signals with no year of volatility are left out.
2. feed `grade_odds`: every field of the 8 grade rows and the 2 marker rows.
3. feed `if_it_misses` (8 rows) and `example_if_it_misses`: every field.
4. feed `odds_fade`, recomputed independently. That covers the walk-forward tier (refresh's original rule on each chart's own bars), the daily windows, the bands, the n counts, the after-day-10 shares and their `*_within60d` aliases, and each edge against 70 on the exact share (exact fractions).
5. Every card: REPLAY's 4 forming cards, 23 open-signal cards per state, and the example card (built only from signals known by 2024-09-22). Every field: sample rule and its wording, n, the shares, the exact (6-place) and rounded medians, eras, timing, from_entry, the 4 ladder rows (shown and exact), low_date, low_day, confirms_on, bars_to_confirm, must_close_above (solved in closed form from my RSI), price_now and entry_close. The edge is the first ladder level whose exact share is below 70. Also: the list of forming setups is complete across all 10 charts, and the active-confluence dates.
6. feed `open_signals`: the list itself, ids, dates, days_elapsed, day10/30/60 on closed daily bars, best and worst so far, edge_level_pct and edge_status.
7. feed `past_paths` (ETH, BTC) and `example_past_paths`: n, and the q25, median and q75 for all 61 days.
8. The page in Playwright Chromium (clock set to generated_at + 6 min, routes as specified):
   - Every picker button and every card, number by number: header line, big number, sample line, stats, 8 tiles, ladder (value, colour, bar width) and eras.
   - The Chart tab for every selection, and for the example both "At the alert" and "What happened". I checked every candle against its date and price; each level line, price tag and ladder zone against its price; Entry, Today, Confirms, High-day and Day-60 lines and the zone edges against the bar containing that calendar day; x-axis dates; the low marker; the y-axis range using only bars known at the alert; the "This one" labels; the side panel; and the cloud (all 61 median points and the 122 band points).
   - Past signals (all, ETH, BTC): every row and cell, the count line, the summary boxes and the sort order.
   - Previous signals, the banner, the market-filter pill, the footer, the lead-trader panel and How to read.
   - The served candles are the chart's last 70 bars. The example JSON matches the ETH 2D data.
9. Labels against meaning: I read every rendered string.
10. Entry quality only: I searched every rendered string for trade, return, profit and track-record wording.

## Disagreements

| State | Where | Shown | Mine | Cause |
|---|---|---|---|---|
| REPLAY | Now, example card, tile "Typical worst drop, misses" | "10 misses of all 75 ETH top-grade signals" | 10 misses among the 75 ETH top-grade signals whose 60 days had closed by 22 Sept 2024. There are 104 ETH top-grade signals in all today. | The label says "all 75". The pool is only the signals known at the example date. The card's sample line says "whose 60 days had closed by then"; this tile doesn't. |
| REPLAY | Now, example card, tile "Typical change by day 60, misses" | same | same | same |
| CURRENT | Now, example card, tile "Typical worst drop, misses" | same | same | same |
| CURRENT | Now, example card, tile "Typical change by day 60, misses" | same | same | same |

Every number agrees: 10, 75, −22.6% and −12.2% are correct for the known-by-then pool. Only the wording "all" is wrong.

## Docs-vs-code disagreements (counted separately)

| # | Doc | Code / page | Effect |
|---|---|---|---|
| 1 | FEED_SPEC: `prints[]` is "every confirmed and forming low" | `stack_live.py` writes only the last 3 confirmed per chart (`sig[-3:]`), plus any forming low. REPLAY has 30 confirmed and 4 forming; CURRENT has 30 confirmed. | Feed only; the page doesn't read prints. |
| 2 | The gate is read on the trough date (CONTEXT, engine) | The `prints[].note` regime flag reads the gate on the confirmation date. ETH-5D-2025-12-06, BTC-3D-2025-12-14 and BTC-5D-2025-12-06 were admitted by the gate but are labelled "regime off" (6 rows in the CSV, ok = DOCS). | Feed only. |
| 3 | CARD_SPEC, "The member site's card": Typical high / Typical drop from entry are shown "with the price" | The Now card shows the percentage only. The price appears only in the Chart tab's "What the card says" box. | Wording or spec. |
| 4 | CARD_SPEC and How to read: "how many had a best price above entry, and their median best" (reads as the median of those above entry) | `carddesign.misses` takes the median over all misses. | No displayed difference. BTC grade C has 94 of 95 misses above entry, and the median is +4.0% either way. The wording is ambiguous. |

## Checks passed, by number (REPLAY / CURRENT; disagreements in brackets)

| # | Area | REPLAY | CURRENT |
|---|---|---|---|
| 1 | Ledger membership: 919 rows match my closed signals exactly. The 203 ETH signals before 2020-03-21 are left out, as CARD_SPEC states. | 920 (0) | 920 (0) |
| 1 | Ledger fields, odds on the day included | 22,975 (0) | 22,975 (0) |
| 2 | grade_odds | 80 (0) | 80 (0) |
| 3 | if_it_misses + example_if_it_misses | 87 (0) | 87 (0) |
| 4 | odds_fade (13 tier pairs, 168 signals, 5 + 2 rows) | 60 (0) | 60 (0) |
| 5 | Cards: forming list, every field, confluence dates | 1,503 (0) | 1,273 (0) |
| 6 | open_signals (23 each) | 322 (0) | 322 (0) |
| 7 | past_paths + example_past_paths (ETH 104, BTC 33, example 75) | 740 (0) | 740 (0) |
| 8 | Page: Now cards (6 / 2 selections + the example switch) | 351 (2) | 119 (2) |
| 8 | Page: Chart tab (lines, zones, axis, candles, side, cloud) | 330 (0) | 137 (0) |
| 8 | Page: Past signals (137 / 104 / 33 rows) | 2,502 (0) | 2,502 (0) |
| 8 | Page: picker, Previous signals, banner/footer/How to read, example data | 20 (0) | 16 (0) |
| 9–10 | Label and entry-quality review (manual, every rendered string) | the 1 label above | the 1 label above |
| – | Outside the list: prints regime notes | 30 (3, docs) | 30 (3, docs) |

Other things confirmed:
- The 2D–8D bars equal my own year-bucketed aggregation of the 1D candles, with no mismatches.
- Both flash prints are clamped.
- The 4 forming setups are the only ones on all 10 charts, and their must-close-above prices ($2,047.21 and $73,533.06) match my closed-form RSI solution.
- No displayed value hit a binary-versus-decimal rounding tie. Zero values show no sign: the BTC 1D 2024-02-07 drop of −0.019% displays as "0.0%".
- At the alert, the example's y-axis comes from bars up to the entry only (the full-history scale would differ). It draws exactly entry_index + 1 candles and shows no outcome. "What happened" matches my daily figures: +10/+20 Yes/Yes; best +33.6% on days 51–52; deepest −10.5% on days 11–12; day 10 Red at −8.4%; day 60 +30.2%.
- Every member-facing "trade" word refers to the lead trader's own account or says "not a trade". Nothing reads as a return or a track record.

## Definitional notes (not counted)

- (a) The regime gate is read on the trough date.
- (b) Flash-print clamp: a low below 0.5 × the body is pulled up to the body, and a high above 2 × the body down to it. Only ETH 2017-06-21 and BTC 2017-04-15 are affected. On 2D+ bars the clamp works on that bar's own body.
- (c) Within a day, the low is taken before the high.
- (d) "Must close above" assumes today's open bar closes at the current price.
- (e) days_elapsed and "day N of 60" count the day in progress.
- (f) peaked_10_or_more is 0 by construction.
- (g) The odds_fade tier uses refresh's rule on each chart's own bars.
- (h) Confluence counts and the 2 ETH HTF-divergence grade_odds rows were not checked. I did check the confluence dates.
- (i) The pooled odds_fade is in-sample.
- (j) "Known by then" means entry + 60 ≤ the date.
- (k) Legacy field names.
- (l) The page opens on the best forming card (REPLAY: BTC-1D-2026-11-13), not the live BTC 2D. I logged this as a layout choice.
- (m) Open cards use every signal whose 60 days have closed.
- (n) Trades feed 404, so the lead trader shows "unavailable".
- (o) The review banner and the lead-trader panel wording.
- The odds-on-the-day formula is taken from `grade_live.py`'s comment, because no doc defines it: a rate shrunk toward the asset's base rate with weight 5, and blank under 10 same-grade signals.
- scaled20 volatility follows `measures.py`: population standard deviation of 365 daily log returns ending on the entry date, divided by its median over dates up to 2021.
- Displayed medians are rounded from the 6-place value. Prices are entry × (1 + exact %), rounded to the cent.
- The example's "What happened" day ranges come from 2D bars (e.g. "days 51–52").

## Independence

I did not read or import any earlier audit folder or other scratchpad folder. One `grep` for "odds on the day" ran across `docs/*.md` and printed 3 matching lines from `docs/AUDIT_LOG.md`. I used nothing from them.

The scripts are in this folder: `lib13.py`, `model13.py`, `audit_data.py`, `audit_cards.py`, `page_dump.py`, `page_check.py`, `extra13.py`. The page dumps are `page_*.json`. I edited nothing in the repo.
