# Audit 11: member site figures against raw candles (12 Nov 2026)

**Top line: 62,489 comparisons across the two frozen states. Numeric disagreements: 0 (no figure, price, date or
day count differs from my own value). Wording disagreements: 1 distinct item (12 rows). Docs-vs-code disagreements,
counted separately: 1 distinct item (8 rows).**

Everything here measures entry quality only. The data has no exits, so none of it is a strategy return or a track
record, and every signal is a computed signal, never a fill.

## Method

Own code only (`lib.py`, `audit_data.py`, `part2.py`, `page_dump.py`, `page_check.py`, `finalize.py` in this folder);
`regimes.rsi_regime(BTC_2D, 8, 13, 60, 41)` imported for the gate, nothing else from the repo. From each state's raw
`data/{ETH,BTC}_{1D..8D}.csv`: flash-print clamp, my own Wilder RSI / stoch K / pivots / diamond chain (EPS 1e-9),
gate on the trough date, entry = close of bar ti+3 dated by its bucket close, 60 calendar days of daily candles,
window counted only once its day-60 bar has closed. Yes/no outcomes are price tests (high >= entry x 1.10, low <=
entry x 0.747). Grades and lens sets taken from the ledger/card as given. States: REPLAY clock 2026-11-12T04:14Z,
CURRENT clock = generated_at 2026-11-12T19:01:16Z. Page rendered in Chromium (Playwright) exactly as specified,
clock at generated_at + 6 min; every picker button, the example (button and switch), both chart modes, Past signals
(All/ETH/BTC), Previous signals, How to read, banner and footer were dumped and parsed.

## Checks declared (before results)

1. Every ledger row: membership (incl. ETH funding availability), low date, entryPrice, tags, year, all forward
   measures (6-place values and yes/no columns), scaled20, grade whole-sample columns, the 7 odds-on-the-day columns.
   Also: stored 2D-8D bars equal the 1D bars bucketed per fetch.py; entry close equals the daily close.
2. feed grade_odds: every field of every A+/A/B/C row and the two tag rows (HTF rows out of scope, (h)).
3. feed if_it_misses (8 rows) and example_if_it_misses: every field.
4. feed odds_fade: my own walk-forward tier (refresh.py's original rule, chart bars), my own daily windows; every
   field, aliases, row counts, and each edge mark on the exact share.
5. Every card (4 forming in REPLAY, example_card, 23 open-signal cards per state): every field incl. sample text and
   rule counts, from_entry, ladder shown and exact shares, eras, timing, exact and rounded medians (and that the
   rounded field equals the 6-place value rounded once), low_date, low_day, confirms_on, bars_to_confirm,
   must_close_above (solved in closed form), price_now, entry_close, edge.
6. feed open_signals: id set, dates, entry close, tags, days_elapsed, day10/30/60 on closed bars, best/worst so far,
   edge_level_pct, edge_status.
7. feed past_paths (ETH, BTC) and example_past_paths: n and all 61 x 3 quantiles.
8. The page: header, banner, footer, picker, every card element, every chart (prices, line and zone positions by date,
   axis scale at the alert, every candle wick, grid and date labels, ladder zones and colours, side boxes, cloud path
   and note, "What happened" circles and side box), Previous signals, Past signals tables and summaries.
9. Labels against meaning. 10. Entry-quality wording.

## Disagreements

| State | Where | Shown | Mine | Cause |
|---|---|---|---|---|
| REPLAY (8 rows), CURRENT (4 rows) | Chart tab side box, every chart view (5 live/forming + 3 example renders in REPLAY; 1 + 3 in CURRENT) | "The lead trader's real entries and exits show on the chart as markers. None on this one." | Unknown: `data/trades.json` was unreadable (404), and the card on the same screen says "Lead trader: unavailable" | Wording: the page asserts there were no lead-trader trades without the data to know it |

No number disagrees. Every figure, price, date and day count matched in both states.

## Docs vs code (counted separately)

| State | Where | Page shows | Docs say |
|---|---|---|---|
| REPLAY (6 cards), CURRENT (2 cards) | Card tiles "Typical worst drop, misses · 5 misses of all 33 BTC **A+**" (or "... 312 BTC **C**"); the feed's sample line also reads "grade A+ signals" / "graded C" | Internal grade letters | CONTEXT, member card redesign (10-11 Nov): "the card says 'Confirmed setup' (the grade stays internal)". That paragraph is marked "partly superseded", but not on this point. CARD_SPEC wording rules also say no internal names on a card |

I found no other place where the docs (CONTEXT 12 Nov paragraphs, FEED_SPEC including every 12 Nov section, CARD_SPEC)
and the code disagree on a definition behind a member-facing figure.

## Checks passed, by item

| Item | REPLAY | CURRENT | Failed |
|---|---|---|---|
| 1 Ledger (919 rows x 27 fields, membership, bucket rule, entry = daily close) | 24,815 | 24,815 | 0 |
| 2 grade_odds | 80 | 80 | 0 |
| 3 if_it_misses + example | 87 | 87 | 0 |
| 4 odds_fade (tier: 13 chart/tag pairs; 5 dip bands, 2 day-10 rows) | 60 | 60 | 0 |
| 5 Cards (4 forming + example + 23 open in REPLAY; example + 23 open in CURRENT) | 1,624 | 1,396 | 0 |
| 6 open_signals (23 per state) | 323 | 323 | 0 |
| 7 past_paths + example_past_paths | 557 | 557 | 0 |
| 8 Page (6 views REPLAY, 2 views CURRENT, 3 Past-signals filters) | 3,955 | 3,614 | 0 |
| 9-10 Labels and entry-quality wording | 18 of 32 | 18 of 24 | 20 (above) |

Worth knowing from the passed checks: REPLAY's four forming cards (ETH 1D, ETH 2D, BTC 1D, BTC 2D, all grade C) are
exactly the forming troughs I find on all 10 charts; CURRENT has none, as the feed says. Must-close-above matches
($2,047.21 ETH 1D, $73,533.06 BTC 1D). The live BTC 2D A+ (21 Sep 2026) is day 52, best +0.8%, worst -16.1%, edge
level -5%, edge lost, in both states. The example's "At the alert" view draws 21 candles and scales the price axis on
them alone; "What happened" draws all 52, and its best/deepest/day-10/day-60 figures match the daily candles. All
chart candles (70-bar files and the example JSON) equal the raw candles.

## Definitional notes (not counted as disagreements)

- (a) Regime gate read on the trough date. (b) Flash-print clamp: ETH 2017-06-21 low $0.10 and BTC 2017-04-15 low
  $0.06, clamped to the body on every chart that contains them. (c) Low before high within a day (ladder, from-entry
  row, dip before the high, edge status). (d) "Must close above" for a setup one bar from confirming assumes today's
  open bar closes at the current price. (e) days_elapsed / "day N of 60" is the day in progress. (f)
  peaked_10_or_more is 0 by construction. (g) odds_fade tier chosen by refresh.py's rule on each chart's own bars.
  (h) Confluence cells and the two ETH HTF-divergence grade_odds rows not checked. (i) The pooled odds_fade is
  in-sample, as its label says. (j) "Known by then" = entry + 60 on or before the date. (k) Field aliases
  (`past_trades`, `trades_a_year`, `*_within60d_pct` on odds_fade, `*fell25*`). (l) The page opens on the best
  forming card (REPLAY: BTC 1D), not the live A+.
- Also matched as choices, not stated in the docs: past-path quartiles use linear interpolation between order
  statistics; the day of the 60-day high or deepest dip is the first such day on a tie; an open signal's card uses
  every signal closed by now (like a forming card), not only those known at its own confirmation; chart date ticks
  show each bar's open date (a 2D bar ticked "21 Sept" closes 22 Sept); ETH ledger membership also needs the
  funding-cooling windows (5 of 7 days now and 14 days earlier), which excluded no signal here.
- Not shown on the page in either state, so not checked as page figures: "about N times a year" (only on an empty
  card), `trades_a_year`, prints, confluence windows, the pooled odds-fade rows (no card falls back to them).

## Files

- `all_checks.csv`: every comparison (state, location, label, shown, yours, ok, cause).
- `disagreements.csv`: the 20 failing rows (12 wording, 8 docs-vs-code).
- Code: `lib.py`, `audit_data.py`, `part2.py`, `page_dump.py`, `page_check.py`, `finalize.py`. Run order is
  `audit_data.py`, `page_dump.py`, `page_check.py` for each state (`<name> <state_root> <clock>`), then
  `finalize.py`.
