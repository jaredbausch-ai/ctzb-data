# Audit 9: ETHKROS member site, independent recomputation (12 Nov 2026)

**Top line: 56,383 comparisons across both states. 0 disagreements between a shown figure and my own value (0 rows, 0 distinct figures).** 6 places where the docs and the code disagree. None of them changes a figure on screen in either state. They are listed separately below.

Everything here measures entry quality only. The data has no exit, so nothing in it is a strategy return, a trade or a track record.

## Scope, declared before running

States: REPLAY (`a9/replay_0414`, clock 2026-11-12T04:14Z, 4 forming setups) and CURRENT (`a9/current`, feed 18:05:19Z, nothing forming). Both have 919 ledger rows and 23 open signals; 1 of the open signals is A+ (BTC 2D, 2026-09-21).

1. Ledger: membership, low date, entryPrice (also against the daily close on the entry date), tags, every forward measure, the yes/no columns, scaled20, the grade* columns and the odds-on-the-day columns.
2. `grade_odds`: every field of A+/A/B/C for both assets and of the two diamond/prime rows. The two HTF-divergence rows are lens logic (note h).
3. `if_it_misses`: every field, all 8 rows.
4. `odds_fade`: the walk-forward tier re-derived on chart bars, then the bands, n, +10% and +20% shares, the after_day10 fields and their aliases, and each edge mark tested against 70% on the exact share.
5. Cards: 4 forming cards (REPLAY), `example_card`, and all 23 `open_signals[].card`. Every field, plus forming-card membership on all 10 charts.
6. `open_signals`: membership, ids, dates, days_elapsed, day10/30/60 from closed bars only, best and worst so far.
7. `past_paths` (ETH, BTC) and `example_past_paths`: all 61 days times 3 quantiles.
8. The page under Playwright. Covered every picker button, the example, the Chart tab in both modes (titles, subtitles, side box, price tags, level labels, ladder zones and their colours, every vertical line's position, x-axis dates, y-axis scale, candle count, outcome markers, cloud line and band), the Past signals tab (All, ETH, BTC: rows, counts, summaries), the Previous signals column, How to read, the banner and the footer. Also checked the served candle files and the static example JSON against raw data.
9. Labels against meaning.
10. Entry quality only.

Method: my own code throughout (`core.py`, `build.py`, `checks*.py`, `page*.py`, `ledger_extra.py`). I wrote it from the definitions: RSI, stochastic, pivots, tags, 2D+ year-restart buckets, the flash clamp, daily 60-calendar-day windows, low before high, and half-away rounding on the exact binary value. `regimes.py` was imported for the gate only. None of the earlier audit folders were read.

## Disagreements: shown value against my value

| state | where | shown | yours | cause |
|---|---|---|---|---|
| none | | | | |

`disagreements.csv` has only its header row, because there are no rows to put in it.

## Docs against code (nothing on screen is affected in either state)

| # | what the docs say | what the code does | effect |
|---|---|---|---|
| 1 | CARD_SPEC wording rule and FEED_SPEC Rules: a forming low reads "Setup forming … It can still vanish before it confirms" | `index.html` line 520 prints the vanish line only for below-grade cards (`below`). I tested this with a synthetic feed where the forming card is A+: the card has no vanish line | Latent. No A+ forming card exists in either state. It would hit exactly the setups members are alerted on |
| 2 | FEED_SPEC audit #8: the 70% bar is tested once, on the exact share; "the page tests the bar on those" | Chart ladder-zone colours compare the rounded share (`v >= sf.bar`, line 739). `openStatus` compares the 1dp `best_so_far_pct >= 10` and `worst_so_far_pct <= edge` and ignores which came first (lines 608-612) | Latent. No exact share falls in [69.5, 70) and no rounding edge exists now; I checked every zone colour and the BTC 2D status on exact values |
| 3 | CONTEXT (item 18 and 17b): no member-facing number is typed by hand; the misses come from the feed (`missstats.csv`) | The page hard-codes "about 22 times a year (2020 to 2025 average)" (line 501) and a fallback entry of 2580.92. The example's misses are computed in the page from `ledger.csv`, not taken from the feed | The 22 is right today (130 A+ signals over 2020-25, /6 = 21.7) but is not shown in either state. The example's misses match my values |
| 4 | CONTEXT standing instructions: `verify_cards.py` "re-derives every figure on every card" | It does not re-derive `must_close_above`, `price_now`, `entry_close`, `low_day`, `low_date` or `confirms_on`. CARD_SPEC #2's own list is accurate | Doc overstates. I checked all of these and they are correct |
| 5 | CARD_SPEC #1: stack_live refuses the cards if "the dip-table counts don't shrink row by row" | The code accepts non-increasing counts, so ties pass (REPLAY ETH 1D has 8, 8). Its internal checks run on `cards.csv` only. `cards_open.csv` and `cards_example.csv` are written before those checks and are not covered by them (verify_cards does cover them) | Wording and coverage |
| 6 | Rule for what was knowable then | The example card and example paths use entry + 60 days <= 2024-09-22. The ledger's odds-on-the-day use + 61 days <= entry | Code against code. Both match my recomputation of their own rule. The odds-on-the-day are not shown on the page |

Doc against doc: the CONTEXT paragraph "Member card redesign (10-11 Nov)" still describes the edge read as the pooled early-dip (56% / 47%). Only its misses part is marked superseded; the later "+10% switch" paragraph replaces it with the setup's own ladder.

## Checks passed, by item

| item | REPLAY | CURRENT |
|---|---|---|
| 1 Ledger (919 rows; membership, measures, grade* and day* columns) | 24,813 | 24,813 |
| 2 grade_odds | 82 | 82 |
| 3 if_it_misses | 80 | 80 |
| 4 odds_fade | 61 | 61 |
| 5 Cards (forming, example, 23 open, forming membership) | 1,701 | 1,457 |
| 6 open_signals (23) | 253 | 253 |
| 7 past_paths + example_past_paths | 560 | 560 |
| 8 Page | 943 | 584 |
| **Total (all pass)** | **28,493** | **27,890** |

Selected confirmations:
- Walk-forward tier as of 1 Jan 2026, re-derived: ETH 1D hollow; 2D diamond, hollow and prime dot; 3D prime dot; 5D any trough, A, B, diamond, prime dot and zone-exit B; 8D any trough and C.
- Odds fade, both states: bands n 34/50/36/29/19, rose 10% after day 10: 91/92/89/79/42. Day 10 green 104 at 96%; red 64 at 62.5%, shown as 63 (a half-away tie, correct).
- Live BTC 2D card: 85% rose 10%, 76% without falling 25.3%, n 33. From entry 82%; falls 5% first 60% (n 15), so the edge is −5%.
- Example card: 87% / 80%, n 75. Edge −10% (falls 10% first, 66%). Misses 10 of 10, median best +5.3%. What happened: best +33.6% on days 51–52; deepest −10.5% on days 11–12; day 10 red at −8.4%; day 60 +30.2%.
- Kill closes recomputed by my own bisection: ETH 1D $2,047.21 and BTC 1D $73,533.06.
- "At the alert" on the example is scaled only from bars up to the entry, and only those candles are drawn. It shows no outcome markers.
- The served candle files equal the last 70 raw bars. All 52 bars of the static example JSON equal raw ETH 2D.

## Definitional notes (not counted as disagreements)

a. The regime gate is read on the trough date. b. The flash-print clamp is applied (0.5 of body; none in any recent window). c. Within a day the low is taken before the high (ladder, from-entry, the Previous-signals status). d. "Must close above" assumes today's open bar closes at the current price. e. days_elapsed and "day N of 60" are the day in progress. f. `peaked_10_or_more` is 0 by construction. g. The odds_fade tier is picked by refresh.py's rule on chart bars. h. Confluence cells and the two HTF-divergence grade_odds rows were not checked (lens logic). i. The pooled odds_fade is in-sample, as its label says.

Also:
- Card `*_exact_pct` is the full-precision median stored to 6dp, as FEED_SPEC #8 states. Taken from the 6dp ledger values, 6 even-n open-card medians land 1e-6 away (for example BTC 1D 2026-09-18 deepest dip: −9.710938 shown, −9.7109385 from 6dp). No displayed figure changes.
- Past-path quantiles use linear interpolation (numpy default). The docs do not name a method; I used the same one.
- Grades and lenses are taken from each ledger row. Card samples were rebuilt from my ledger with those grades and lenses, and every sample text and n matched.

## Labels against meaning (item 9)

All page wording matches what is computed. Observations on the feed's frozen field names, which Joe's AI parses, not counted:
- `rose10_never_fell25_within60d_pct` and `went_on_to_fall25_pct` say 25 but measure 25.3%.
- `odds_fade.*.rose10_within60d_pct` / `rose20_within60d_pct` hold days 11-60 shares (a documented alias).
- `past_trades` and `trades_a_year` count signals, not trades (documented, with twins).
- `up_first` means "went above entry" (documented).

Other observations, not counted:
- The live-setup chart never draws the Low marker. `c.low_date` is read from the open-signal object, which has none; it is on `c.card`.
- The footer's "closed through" date is taken from the feed clock, not from the data. It is right in both states.
- How to read says "By the time you get an alert, the signal is final and can't vanish", but the feed also emits `forming` alerts, which can vanish. Question: do members get forming alerts?

## Entry quality only (item 10)

Every card footer, the Past signals title ("computed, never traded") and its footnote, and the feed `label` on every record say entry quality only, not a trade or a track record. Nothing on the page reads as a strategy return. The lead-trader panel is his own real trades and is kept separate from the signals.

Out of scope, one line: the live site is still deploy 656d67c3 with the audit fixes pending (docs/SITE_CHANGES.md). I audited the repo page.

## Files (`/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit9/`)

`AUDIT9.md`; `all_checks.csv` (56,383 rows); `disagreements.csv` (header only); per-state `checks_*.csv`, `pagechecks_*.csv`, `ledgerextra.csv`; `page_*.json` (full page dumps); screenshots; and the scripts.
