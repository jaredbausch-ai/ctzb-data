# Audit 36: numbers and labels on real data (independent)

This audit measures entry quality only. Every figure checked is a computed signal, never a fill, and none is a strategy return or a track record.

**What was audited.** The pipeline code is at 2d856f7. The page copy in both frozen states is byte-identical to `docs/artifacts/member-site/index.html` at 2d856f7, which is unchanged since ee91da1. Docs commit 9c177ca came later and was not audited here. The frozen states are `a36/replay_0414` (data from 4aa1208, clock 2026-11-12T04:14:00Z) and `a36/current` (feed generated_at 2026-11-15T05:24:21Z).

**Method.** All code is my own, in `code/`: `mine.py`, `checks.py`, `page.py`, `pagecheck.py` and `replay.py`. It works from the raw candles with exact decimal prices. regimes.py was imported for the gate only. The page was rendered in Playwright as the brief specifies (clock = generated_at + 6 min). I read no earlier audit folder and no AUDIT_LOG.

## Top line

| Group | States | Comparisons (rows) | Distinct figures | Disagreements (rows / distinct) | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| (A) frozen states | 2 | 53,892 | 53,892 | 0 / 0 | 0 | 0 |
| (B) replays of real dates | 328 (326 audited, 2 fail-closed tests) | 5,695,532 | 135,599 (location × label) | 0 / 0 | 0 | 0 |

## Every disagreement

| Group | State | Where | Shown | Yours | Cause |
|---|---|---|---|---|---|
| none | | | | | |

`disagreements.csv` holds only its header.

## Checks declared before results, and the count passed

| # | Check (declared list from the brief) | A passed | B passed |
|---|---|---|---|
| 1 | Ledger rows. Membership: graded 1D–5D, gate on at the trough, 60th day closed, ETH only with funding plus its 90-day median and the 7/14-day windows. Also entryPrice, low, tags with EPS, year, every measure to 6 places, yes/no columns, daysToHigh, grade columns and all day* odds (dayScaled20 leaves out no-vol signals) | 46,002 | 4,692,201 |
| 2 | grade_odds: every field, both assets and all grades, plus the two marker rows and the HTF rows' counts adding up (their split is lens logic, out of scope) | 138 | 22,494 |
| 3 | if_it_misses (every field, per asset/grade) and example_if_it_misses | 172 | 26,896 |
| 4 | odds_fade: the walk-forward tier recomputed by refresh's rule on each chart's own bars as of 1 Jan; bands and day-10 rows on daily candles; past_trades, past_signals, after_day10 fields and their aliases, edge on the exact share, tier_fixed_on, edge_measured_on, the tier date in the sample text | 110 | 17,531 |
| 5 | Every card (forming, open, example). All shares, exact and rounded medians, eras, timing, the sample rule and its text, from_entry, the ladder (shown and exact), and the edge. Also low_date, low_day, confirms_on (bar rule with the 1 Jan restart), bars_to_confirm, must_close_above (own RSI bisection, rounded down), price_now and entry_close. Forming cards only on graded charts with the gate on at the trough and a non-empty sample; every live signal has a card | 3,394 | 404,509 |
| 6 | open_signals: ids, dates, days_elapsed, day10/30/60 on closed bars, best/worst, edge_level, edge_status, membership. prints: last 3 per chart plus forming, regime note on the trough date, forming tags on exact CT/K with EPS. Top level: schema_version, posting_bar_pct, scored_as_of, generated_at, market_regime, trades_a_year/signals_a_year, next_buy_date | 1,047 | 150,489 |
| 7 | past_paths (61 days × 3 quantiles, n) and example_past_paths (ETH A+ closed by 2024-09-22) | 1,108 | 138,880 |
| 8 | The page (figures below) and all 10 chart files equal to the last 70 bars | 1,921 | 242,532 |
| 9 | Labels vs meaning: automated wording checks (sample line, status sentence, forming note, titles/subtitles, cloud note, pools, quiet text) plus a manual read of every label | 262 | 36,074 |
| 10 | Entry quality only: card foot, record footnote, review banner and footer read for return / trade / track-record wording | passed | passed |

Item 8 covers these page elements:

- **Header and banner:** filter pill, scored date and feed time.
- **Footer:** "closed through" date, update time, checks status.
- **Picker:** every Live and Forming button (day, best/worst; share, n, grade word, confirms date).
- **Card:** every displayed number on each card, including big number, never-fell line, sample line, typical high/drop, edge text, misses line and pool, all 8 tiles, ladder rows with n and gone colour (exact vs 70), eras, live status sentence, must-close-above line.
- **Chart tab:**
  - Title, subtitle and sample.
  - "Today" / "Latest bar", "Entry", "Confirms … day 0", "High usually ~day N" and "Day 60", each placed at the slot of my own date (bar rule, 1 Jan restart).
  - Both zones from entry to day 60.
  - The four level lines and their price tags (pxAt on cents).
  - The axis at the alert scaled on known bars only, y-axis labels at their prices, x-axis dates at their slots.
  - Edge line and label, ladder bands at their levels with n and colour, low marker.
  - Side box (prices; live day, best, worst, day 10).
  - The 61-point median path of the cloud, cloud subtitle and note.
  - Example "What happened": +10/+20, best and deepest with day ranges containing my day, day-10 check, day 60, "This one" labels, the example's own 30-point path, full-file axis.
  - The example file equal to the raw 2D bars, entry 2024-09-22, reaching day 60.
- **Past signals tab** (all/ETH/BTC): count, every row, order, summary boxes.
- **Previous signals:** both groups, badges, newest first.
- **How to read:** the bar.
- **Quiet card:** example auto-on, or "No setup right now" with "about N times a year".
- **Console:** no console errors.

## Coverage of group B (real dates, `tests/replay_at.sh`, no tampering)

| Kind of state | Replays | Notes |
|---|---|---|
| Filter-flip reach: F−2 … F+19 daily, then F+22/25/28/31, for all 6 flips since Sept 2020 (2021-06-08, 2021-08-19, 2022-01-27, 2023-01-25, 2025-12-05, 2026-09-02) | 156 | covers cards whose trough is on the other side of a flip (5D reach 19 days; 8D prints to 31) |
| First/last day of each filter episode and the day either side | 24 | |
| Year-ends 26 Dec – 4 Jan, 2020/21 to 2025/26 | 60 | 1 January restart of 2D+ bars and confirms_on |
| Market filter off on the replay date | 110 | brief asked ≥ 40 |
| A top-grade forming card present | 61 | 43 planned (day before an A+ confirmation); brief asked ≥ 40 |
| Live top-grade signal present | 198 | |
| Nothing live, no card (quiet market) | 39 | 5 with no forming low on any of the 10 charts |
| Day 60 in progress / day after it closed, 20 A+ signals | 20 + 20 | leaves open_signals, enters the ledger the next day |
| Just after a confirmation (day 1) | 15 | |
| Other clock times (00:00:30, 00:13, 03:59:59, 08:13, 12:00, 12:13, 16:43, 20:13, 23:59) | 12 | 23:59 shows the "daily close has passed" note, which is correct at +6 min |
| Clock on D+1 with candles ending on D (fail-closed test) | 2 | feed withheld; page reads "Setups held back", "Market filter: unavailable", "checks FAILED" |
| With / without the worked example (before 22 Nov 2024) | 98 / 228 | example_* null when absent: checked |

Across group B the checks covered 795 forming cards and 5,802 open-signal rows. No replay of a real date failed or was withheld except the two deliberate fail-closed tests. My exact-decimal arithmetic found no near-ties: no float-versus-exact threshold case, cent-edge must-close-above or double-rounding median.

## Definitional notes (not counted)

These were applied as the brief states: (a)–(al).

- The gate is read on the trough bar's open date; the header shows today's filter.
- The flash clamp is applied to all candles; within a day the low is taken before the high.
- Must-close-above assumes the open bar closes at the current price, rounded down.
- Day N is the day in progress. peaked_10_or_more is 0.
- The odds_fade tier uses refresh's chart-bar rule as of 1 Jan and is pooled in-sample from 2016.
- Confluence counts and the ETH HTF-divergence rows are lens logic.
- "Known by then" = entry + 60 ≤ date. Compatibility field names are kept.
- Live cards use every past signal closed by now, measured from each entry close.
- The trades feed is 404, so the lead-trader panel shows "unavailable".
- The "if it misses" median is taken over all misses. "About N a year" counts 2020 to the last full closed year.
- A live setup with no closed bar shows n/a. replay_at keeps the date's bar whole. Labels are drawn over candles.
- Sample rules 1–3 apply; rule 3 is used at any size.
- The page's acceptance rules and load-time validation are as written.
- The "closed through" date is scored_as_of − 1. next_buy_date is not on the page.

One observation, not a figure and not counted: a live setup's chart draws no low marker (the page looks up `low_date` on the open-signal object, not on its card). Forming charts do draw one. CARD_SPEC and FEED_SPEC do not promise a marker for live charts.

## Checker self-test

I planted 35 errors in copies of replay_0414 and ran the full checker. All 35 were caught: 27 data plants and 8 page plants.

- **Data plants:** ledger values at 1e-6 and 1-cent size, an odds column, tags, a removed row, a grade_odds share, miss medians and means, odds_fade share and n, must_close_above +1 cent, exact medians and a ladder exact share at 1e-6, timing, open worst, a card era, price_now, an example field, low_day, two path quantiles, print price and tags, trades_a_year, the example misses, and a chart-file bar.
- **Page plants:** the code was edited to show a drop 0.05 lower, the day-60 line one day late, the +10% level at 10.01%, Previous best +0.5, Record day +1, the never-fell line +1, and the price axis 1% higher.

Three first-draft plants were invisible and were replaced:

- The +10% level computed by float product printed the same cents.
- Previous best +0.05 did not move the 1-decimal display.
- The axis at the alert built from the whole file drew the same axis on the 2024 example.

One first-draft plant hit a chart the page did not show. That led me to add a data-level check of all 10 chart files.

## Doc sentences contradicting the code

None noticed (docs read only for definitions, at 2d856f7).

Files:

- `all_checks.csv`: every group-A row, every group-B disagreement (none), and one status row per replay.
- `disagreements.csv`: header only.
- `replays/<date>[_time].csv.gz`: every check of each replay.
- `progress.log`: the stage log.
