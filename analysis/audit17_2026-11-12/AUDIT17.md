# AUDIT 17: ETHKROS member site, every number recomputed from the raw candles

Independent auditor, own code only (`code/`), 13 Nov 2026. Nothing in the repo was read from an earlier audit, edited, committed or pushed.
Scope reminder: this measures **entry quality only**. The data has no exit, so nothing here is a strategy return or a track record, and every signal is computed, never a fill.

## Top line

| | Comparisons | Disagreement rows | Distinct figures |
|---|---|---|---|
| REPLAY (12 Nov 2026 04:14 UTC) | 30,457 | 0 | 0 |
| CURRENT (13 Nov 2026 00:47 UTC) | 29,558 | 0 | 0 |
| **The two frozen states** | **60,015** | **0** | **0** |
| Other states: 173 replayed dates (163 built and audited, 10 pipeline failures) | 3,744,594 | 253 + 3 failed runs | **2 defects** |
| Other states: 30 synthetic page states | 508 | 26 | **5 defects** |
| Docs vs code | | | **3** |

Every member-facing number in both frozen states agrees with my own computation, to the last stored decimal and the last cent.
The checker is sensitive: 5 planted errors (1e-6 on a ledger figure, 0.00002 on an exact median, +1 on a ladder n, 0.1 on best/worst and on a path median) were all caught, 20 rows, including a 2-cent move of a chart price.

## Checks declared before the results

1. Every ledger row: entry price, tags, forward measures, odds-on-the-day columns (dayScaled20 included), membership.
2. Feed `grade_odds`, every field (the two HTF-divergence rows are out of scope).
3. `if_it_misses` and `example_if_it_misses`, every field.
4. `odds_fade`, recomputed from refresh.py's documented tier rule: every field, aliases, `tier_fixed_on`, each edge mark on the exact share.
5. Every card (forming, example, every open signal's card), every field; forming cards only on graded charts with the gate on at the trough.
6. `open_signals`, `prints`, top-level fields.
7. `past_paths` and `example_past_paths`.
8. The page in Playwright: every text node of every view, every picker button, both chart modes, chart geometry.
9. Labels against meaning.
10. Entry quality only.

Plus a stage 0 on the candle files themselves (multi-day bars rebuilt from the daily file, 4H against 1D, the page's candle files, the example's chart file).

## Disagreements

### The two frozen states

None.

### Other states (counted separately)

| # | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| R1 | Replays 2026-02-16, 2026-03-15, 2026-07-24: a quiet market, no low forming on any of the 10 charts and no signal in the last 60 days | `stack_live.py`, then feed and page | "COVERAGE FAILURE", stack_status FAILED, feed withheld. Page: "Setups held back · A data check failed on the latest run", footer "checks FAILED, cards held back" | Run passes. Page: "No setup right now · Waiting for the next one · The market filter is off…" | `check_coverage()` treats "no subject to evaluate" as "registry id never evaluated". By my scan, 38 of the 271 days of the last filter-off stretch (5 Dec 2025 to 1 Sep 2026) had no subject |
| R2 | 11 of 13 runs replayed at 00:05 UTC before the new day's candle exists (e.g. 23 Sep 2024, 22 Sep 2026, 3 Nov 2026) | Feed `cards`, `prints`, `open_signals`; page picker and card | A low whose confirmation bar closed at 00:00 is still "Setup forming … confirms 22 Sept 2024 if it closes above $2,143.78 … Not confirmed yet. It can still vanish" (top grade; that bar had closed at $2,580.92). It is missing from open signals and confirmed prints. Other forming lows' `bars_to_confirm` is one too many (feed only) | A confirmed signal, live on day 1 | The pipeline takes the last candle in the file as today's open bar. Audit #16 fixed the day counts for this run, not the confirmation state. It corrects itself on the next run with the new candle. 253 rows |
| S1 | Fail-closed feed (a real one, built by making feed_live.py crash) | Header pill | "Market filter: off" | unavailable | That feed has no `market_regime`; the page reads missing as off |
| S2 | Same feed | Banner | "scored  (feed 04:14 UTC)", date blank | unavailable | No `scored_as_of` in that feed |
| S3 | Example's chart file missing, after any other chart was opened | Chart tab, cloud | The previous setup's cloud stays: "Every past BTC top-grade signal, n 33 … Day 60: median +32.7%, middle half −3.4% to +54.5%" under "Chart data unavailable" | Cleared | The example branch of `renderChart` clears the chart and side box, not the cloud |
| S4 | A chart file too short to reach the entry (BTC 2D cut to 20 bars) | Chart tab title, subtitle, cloud | The previous setup's: "ETH · 1D · forming, not top grade", "Low 10 Nov 2026 · confirms…", ETH cloud | "BTC · 2D · live setup, day 52 of 60" | That branch returns before the title is set. Cannot happen with intact 70-bar files |
| S5 | Lead trader's feed live with a BTC trade open (synthetic trades.json) | Chart tab note | "The lead trader's real entries and exits show on the chart as markers. None on this one." No marker is drawn | A marker, or no such claim | The note is fixed text. Matters only once his feed is switched to live |

Not counted: 7 early-history replays cannot run (2018-12-10 `refresh.py` ZeroDivisionError; 2019-12-30 to 2020-01-03 and 2020-06-07 `extras_live.py` IndexError). They predate the first known ETH top-grade signal and the ledger never shrinks, so they are not reachable going forward.

The other 150 replays, run at 04:14 UTC, had 0 disagreements across 375 forming cards and 524 live top-grade cards. They include 43 dates with the market filter off, 30 year-end dates (30 Dec to 3 Jan, 2020 to 2026), 39 with a top-grade forming low (0, 1 and 2 bars to confirm), 35 with nothing live or forming, 12 with a top-grade signal on its 60th day (and the days after it left), all three edge statuses, and both gate flips of 2025-26.

## Docs vs code (3)

| # | Doc | Says | Code does |
|---|---|---|---|
| D1 | FEED_SPEC, "Fail-closed feed" | "Readers need no special case: it is a withheld feed" | The member page does need one (S1, S2) |
| D2 | FEED_SPEC, "Audit #16 corrections"; SITE_CHANGES 6c | A missing chart file reads as unavailable, not as the previous setup's figures | True for a live or forming chart; not for the example's chart file (S3) |
| D3 | CARD_SPEC, "The member site's card"; CONTEXT 31 Oct note | A live card "says 'Edge lost' or 'On track'" | The page has a third status, "Rose 10%", documented only in FEED_SPEC audit #16. CARD_SPEC says a card may not show a word it does not define |

Related to R2: CARD_SPEC says the "closes above" line shows when the confirmation bar is the bar now open or the next one; in the midnight run it shows for a bar that has closed.

## Checks passed, by number

| # | Check | REPLAY | CURRENT | Disagreements |
|---|---|---|---|---|
| 0 | Candle files, page candle files, example chart file, gate history | 55 | 55 | 0 |
| 1 | Ledger (919 / 921 rows, 26 figures each, plus membership) | 23,896 | 23,948 | 0 |
| 2 | `grade_odds` (10 of 12 rows) | 71 | 71 | 0 |
| 3 | `if_it_misses` (8 rows) and the example's | 97 | 97 | 0 |
| 4 | `odds_fade` (13 tier pairs, 168 signals, 7 rows) | 62 | 62 | 0 |
| 5 | Cards (4 forming + example + 23 open / example + 21 open) | 1,752 | 1,368 | 0 |
| 6 | Open signals, prints (34 / 30), top level | 546 | 492 | 0 |
| 7 | Past paths, ETH, BTC and the example (61 days x 3) | 555 | 555 | 0 |
| 8 | Page: every text node on Now, Chart and Past signals, chart geometry | 3,422 | 2,909 | 0 |
| 9 | Labels vs meaning: 201 / 167 distinct sentences matched word for word against the definition and my number; How to read checked against the definitions | within 8 | within 8 | 0 |
| 10 | Entry quality only: label on all 109 / 97 feed records; "return" and "track record" appear only in disclaimers; "trade" only for the lead trader's own trades or in disclaimers | 1 | 1 | 0 |

Check 8 also confirmed on the charts: Entry and Confirms sit on the bar that closes on that date, Day 60 on the bar containing that calendar day, "At the alert" is scaled and drawn only from what was known, every ladder band carries its share and n and its colour follows the exact share, every price is the exact cent. The page text is identical in UTC+14, UTC−11 and a German-locale browser.

## Remarks that are not disagreements

- The feed carries `-0.0` at `example_past_paths` day 31 `q25_pct` in both states. It is numerically zero and never displayed.
- Legibility: on the live BTC 2D chart the first ladder band label ("82% · n 33"), "Edge gone below $82,265.19" and "Typical drop −6.5%" are partly overdrawn by candles; on the ETH 2D forming chart the "$3,000" axis label sits under "High usually ~day 44". The same figures are clear in the side box.
- The cloud's axis prints "-20%" and "-40%" with a plain hyphen where the rest of the page uses "−".
- ETH daily candles have one gap, 21 and 22 May 2016, before any signal.
- No decimal tie occurred anywhere: the page's binary `toFixed` and exact decimal half-away rounding gave the same text in every state.

## Definitional notes

Known choices, accepted as stated; the repo contradicts none of them.

- (a) The gate is read on the trough date. Seen in replays both ways: a forming card under "Market filter: off" (8 dates) and a gate-off low with no card under "on" (6 dates).
- (b) The flash-print clamp: one bar per asset, ETH 2017-06-21 and BTC 2017-04-15.
- (c) Low before high within a day.
- (d) "Must close above" one bar from confirming assumes today's bar closes at the current price.
- (e) "Day N of 60" is the day in progress.
- (f) `peaked_10_or_more` is 0 by construction.
- (g) The odds-fade tier is refresh.py's rule on each chart's own bars, fixed on 1 January.
- (h) Confluence counts and the two HTF-divergence rows are lens logic, out of scope.
- (i) The pooled odds fade is in-sample, as labelled.
- (j) "Known by then" is entry + 60 days on or before the date.
- (k) Compatibility field names (`past_trades`, `trades_a_year`, `*_within60d_pct`, `*fell25*`, `grade`).
- (l) Which card the page opens on. REPLAY opens on the below-grade forming BTC 1D, not the live top-grade BTC 2D.
- (m) An open signal's card uses every signal closed by now. 3 of 23 open cards in REPLAY and 5 of 21 in CURRENT include a signal that closed after their entry; none of those is shown on the page, and the one live card shown (BTC 2D) equals its card as issued.
- (n) The trades feed is 404 in the harness, so lead-trader panels read "unavailable".
- (o) The "Review build" banner and the lead-trader panel text.
- (p) "If it misses" median best is over all the misses.
- (q) The liveread "Regime gate" row.
- (r) "About N times a year" averages full years from 2020; 22 now, from 130 top-grade signals in 2020 to 2025.
- (s) The typical drop is a median.
- (t) A live setup with no closed daily bar shows best / worst "n/a".
- (u) replay_at.sh keeps the replay date's bar whole. My harness gives a byte-identical feed for the same date.

Mine: grades and lenses are taken as given from the ledger, the cards and `open_signals`. 203 ETH signals before 21 Mar 2020 are outside the ledger (no funding history). In a midnight run I do not assert a forming low on the last closed bar, because there is no price yet to hold it.

## Files

Folder: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit17/`

- `all_checks.csv`: 60,523 rows, the two frozen states and the synthetic states in full.
- `disagreements.csv`: 287 rows, every disagreement, replays, failed runs and docs items included.
- `replay_summary.csv`: comparisons and disagreements per replay. Per-replay rows are in `out/rp/*.csv.gz` and `out/rp2/*.csv.gz`.
- `code/`: `core.py` (candles, indicators, measures), `audit_feed.py` (checks 1 to 7, 10), `audit_page.py` (8, 9), `data_checks.py`, `audit_states.py`, `audit_tz.py`, `audit_trades.py`, `scan_quiet.py`, `replay_any.sh`, `run_replays*.sh`, `assemble.py`.
- The replay copies are deleted. To rerun replays, copy the `current` state without `analysis/audit*` and `docs/AUDIT_LOG.md` to `audit17/base`.
