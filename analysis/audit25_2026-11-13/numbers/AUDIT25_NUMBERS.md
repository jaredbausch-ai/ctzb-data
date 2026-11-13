# Audit #25: numbers and labels on real data (ETHKROS member site)

Independent auditor, 13 Nov 2026. Every figure was recomputed with my own code (`code/`) from the raw candles. I imported `regimes.py` for the market filter only. Nothing in the repo was edited. These are computed signals, not fills. There is no exit in the data, so nothing here is a return or a track record: this is entry quality only.

## Top line

| Group | States | Comparisons | Disagreements: rows | Disagreements: distinct | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| (A) Frozen states (`replay_0414`, `current`) | 2 | 59,234 | 0 | 0 | 0 | 0 |
| (B) Replays of real dates (Sep 2020 to Nov 2026), plus envelope runs | 395 + 3 | 7,771,248 | 268 | 1 | 0 | 1 |

On real data I found **no wrong figure** in either group. The single group-B finding is wording, and it only appears in states before 22 Nov 2024. The live site can never be in such a state today.

## Every disagreement

| Group | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| B | all 268 replays dated before 22 Nov 2024 (2020-09-14 … 2024-11-21) | Chart tab, example picked; the feed has no `example_card` | "The example's chart data couldn't be loaded." / "Chart data unavailable" | "Example unavailable", as the Now card says and FEED_SPEC audit #19 states | Wording. The chart file did load; it is the feed that has no worked example. The Now card's text is correct ("The worked example isn't in the latest data"). Replays only: since 22 Nov 2024 every clean feed carries the example. |

Each row is in `disagreements.csv`.

## Checks declared before the results, and what each covered

| # | Check | A: comparisons / disagreements | B: comparisons / disagreements |
|---|---|---|---|
| data | Daily candles gap-free and ending today; every 2D-8D file equals the daily candles bucketed (1 Jan restart); each chart file is the last 70 bars | 44 / 0 | 8,690 / 0 |
| 1 | Ledger: membership, entryPrice, tags, every forward measure (6 places), yes/no columns, scaled20, grade* columns, odds-on-the-day incl. dayScaled20 and dayN | 47,840 / 0 | 6,056,310 / 0 |
| 2 | `grade_odds`, every field (the HTF rows are lens logic, not checked) | 160 / 0 | 31,600 / 0 |
| 3 | `if_it_misses`, `example_if_it_misses` | 174 / 0 | 34,365 / 0 |
| 4 | `odds_fade`: my own walk-forward tier as of 1 Jan, bands, shares and aliases, edge marked on the exact share, `tier_fixed_on`, the sample's date | 108 / 0 | 20,931 / 0 |
| 5 | Forming and example cards, every field: dates, low_day, confirms_on, must_close_above (my exact Wilder solve, rounded down), price_now / entry_close, sample text and n, rounded and exact medians, eras, timing, ladder, edge; which cards exist | 350 / 0 | 58,975 / 0 |
| 5/6 | Live signals: which are listed, days, day 10/30/60, best/worst, edge level and status; each signal's own card | 3,124 / 0 | 446,661 / 0 |
| 6 | Prints (last 3 per chart plus forming; filter note on the trough date; EPS tags) and top level (schema, posting bar, scored date, filter, signals a year) | 524 / 0 | 110,450 / 0 |
| 7 | `past_paths`, `example_past_paths` (61 days, three quantiles) | 1,358 / 0 | 268,205 / 0 |
| 8 | Page in Playwright, clock = generated_at + 6 min: header, banner, footer, picker, every Live/Forming/example card, Chart tab (line and zone positions by date, axis scaling at the alert, ladder bands with n, price tags, axis dates and prices, outcome markers, side boxes, cloud drawn at my quantiles), Past signals (all/ETH/BTC), Previous signals, quiet card, How to read | 5,552 / 0 | 735,049 / 268 |
| 9 | Labels vs meaning: each card label is compared word for word with what its figure measures (inside #5 and #8). Text scan of every tab | inside #5 and #8 | inside #5 and #8 |
| 10 | Entry quality only. Every sentence on the page with trade/return/profit/win/result/track record was read (9 sentences, all disclaimers: "not trades", "entry quality, not a return or a track record", the lead trader's real-trade panel) | 0 found | 0 found |
| env | Clock on D+1 with candles ending on D (3 dates incl. 1 Jan): fails closed, i.e. cards withheld, no live signals, filter "unknown" not "off" | — | 12 / 0 |

Cards checked in group B: 883 forming (129 of them top grade), 6,291 live signals with cards (1,117 top grade), and 127 worked-example cards.

## Coverage of group B (395 replays, `tests/replay_at.sh` on copies of `current`, real candles, nothing altered)

| Kind of state | Replays |
|---|---|
| Market filter off today | 167 |
| Every date from 8 days before to 20 days after each of the 6 filter flips since Sep 2020 (first/last day of each episode and the days either side included) | 174 |
| Year-ends, 26 Dec to 4 Jan, 2020/21 to 2025/26 | 60 |
| Top-grade forming card present | 75 |
| Forming card while the header reads filter off (trough before the flip) | 37 |
| Nothing live or forming on any graded chart | 91 (120 with nothing at the top grade) |
| 20 top-grade signals: day 60 in progress, and the day after it closes | 20 + 20 |
| Day after a confirmation (planned) | 10; most other replays include some |
| Clock other than 04:14 (00:00:30, 00:13, 00:43, 03:59, 08:13, 11:47, 12:13, 16:13, 20:13, 23:59) | 30 |
| No worked example (before 22 Nov 2024) / with one | 268 / 127 |
| Pipeline failed on a real date | 0 |

The replay list was declared in `plan.csv` before any replay ran. Then 8 replays were re-run because my checker had crashed on states with no example, and 2 replays were added to reach 20 day-60 signals.

## Self-test (planted errors)

I planted errors in copies of `replay_0414` (list in `plant/SELFTEST.txt`) and my checker caught **34 of 34**:

- 21 ledger and feed values, each 1e-6, 0.01, 0.1 or 1 unit off, plus one flipped yes/no, one moved date and one deleted row
- 8 changes to page code (rounding, line position, axis scaling, wrong field shown)
- 5 feed values that still pass the page's strict check, so the planted value is what the page shows

## Definitional notes (documented choices, not counted as disagreements)

- **Listed choices I relied on.** From the brief's list: (a), (b), (c), (d), (e), (g), (h), (j), (l), (m), (n), (p), (q), (r), (t), (u), (w), (y), (ab), (ac), (ad), (ae), (af), (ah).
  - I confirmed (n) (lead trader "unavailable"), (r) (the quiet card's "about N times a year") and (ah) (the closed-through date) on the page.
- **Exact thresholds.** "Rose 10%", "fell 25.3%", "fell 30%" and the ladder levels were tested on exact decimal prices. Percent medians were taken on full-precision floats and rounded half away from zero on the float. Every rounded figure matched, so no tie went the other way.
- **Ties in days.** The day of the 60-day high or deepest dip is the first day it occurs. Where several days share it, I took the first; this matched every row.
- **Volatility for "beat a normal move".**
  - It is based on rows, so the two ETH days missing in May 2016 are skipped.
  - In replays before 2022, the "2016-21 median" uses only the data up to the replay date. This is what the pipeline knew then, and I matched it. It is not shown on the member page.
- **Order treated as layout, compared as sets.** The order of live buttons, of top-grade forming buttons, of live rows in Previous signals, and of rows sharing a date in Past signals. The same goes for which same-date ledger row fills the last of the five "Edge lost or closed" places. Forming cards below the top grade were checked in the documented order: by rose-10% odds.
- **must_close_above.** It is solved exactly on Wilder's recursion. No forming card in any state had a threshold within 1e-6 of a cent boundary.

## Doc sentences that contradict the code

None found. (Unrelated note: during this run `/home/claude/ctzb-data` had uncommitted edits by another party, to the page, refresh/stack/extras and the specs. I audited only the frozen states and their own code, and replays ran from the frozen `current`.)

Files are in `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit25n/`:

- `all_checks.csv`: group A in full; group B as every disagreement plus one count row per replay and check family. Every group-B row is in `B/<replay>/checks.csv.gz` and `page_checks.csv.gz`.
- `disagreements.csv`, `progress.log`, `plan.csv`, `coverage.txt`
- `code/`: `mine.py`, `build.py`, `check_state.py`, `page_check.py`, `driver.py`, `plant.py`, `aggregate.py`
