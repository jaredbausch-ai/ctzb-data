# Audit 27c: broken states (independent)

Date 14 Nov 2026 (UTC). States: `a27/replay_0414` (12 Nov 04:14 run) and `a27/current` (14 Nov, re-run at clock 2026-11-14T00:40Z, which reproduces the frozen feed figure for figure), plus real pipeline outputs built from them (held, fail-closed, extras killed, a run at 23:13, replays at 2025-12-03, 2025-12-09, 2026-01-01). All code is my own (`work/`); nothing in the repo was edited. Every row is in `all_checks.csv` (768 rows); the failures are in `disagreements.csv` (24 rows, 18 counted).

This audit measures how the system behaves under damage. The data has no exits, so nothing here is a strategy return or a track record. Every signal is a computed signal, not a fill.

## Top line

**Real-life disagreements: 18 rows from 4 causes.** 2 are on the page, both TIMING. 16 are in the pipeline, all from damaged or stale funding data that gets scored. Hand-forged contradictions that got through (hardening, not counted): 6.

### Page level (Playwright, own harness; 227 states, including 51 hardening)

| Family | General rule (from the code) | Tried | Got through |
|---|---|---|---|
| MISSING | `get()` returns null on any non-OK status or a parse failure. No feed means "Data unavailable". The ledger needs a body. A chart file or the example must pass `barsOk`/`stepsOk` | 34 | 0 |
| MALFORMED | Strict check (FEED_SCHEMA + crossCheck); `parseCSV` dropped rows, `ledgerRowOk`, duplicates and the per-asset count/share against grade_odds; `barsOk`, `stepsOk`, last close equal to `price_now`; Worker `csvToBars` refuses rows that are not numbers | 68 | 0 |
| WRONG CONTENT | The chart file must name its chart, end no later than `generated_at` and close at the card's price (and the entry bar at `entry_close`). The ledger must match grade_odds per asset. The example must match the card's entry close | 23 | 0 |
| PARTIAL RUN | `cards_withheld` reads as "Setups held back"; a held feed has no cards; the ledger cannot be checked without grade_odds | 6 | 0 |
| TIMING | Stale note after 5 h, re-checked each minute; auto example off when stale; "Loading" until each file arrives | 22 | **2** |
| DELIVERY | As MISSING/MALFORMED: a cut, empty or HTML body fails to parse or fails its check | 23 | 0 |

Disagreement types (page): (i) wrong or unsupported figure **1**, (ii) placeholder, script error or blank area **0**, (iii) damaged input shown **0**, (iv) wording that misstates the state **1**, (v) reads as a return, trade or track record **0**.

### Pipeline level (steps run in daily.yml order on copies; outcomes from exit codes; feed_live last; 542 runs + 19 alert sequences)

| Family | General rule (from the code) | Tried | Got through |
|---|---|---|---|
| MISSING | Missing input: check_candles / `history_problems` stops the job; a missing dataset or config fails a step or the seal | 8 | 0 |
| MALFORMED | `fetch.history_problems` (every candle row, grid, order, first day, gaps, 2D-8D = daily bucketed, asset ratio; series day-by-day, range, freshness), run in check_candles and again in stack_live | 318 | **16** |
| WRONG CONTENT | Asset ratio check, 4H/12H step and asset checks, bucketing check, derivatives market columns | 23 | 0 |
| PARTIAL RUN | Run seal (`seal.py`: order, once only, sha of every dataset and input, age ≤ 2 h); CTZB_STEP_OUTCOMES gating; fail-closed on any feed_live error; alert-log sha chain with carry | 176 + 19 seq. | 0 |
| TIMING | Last daily bar must be today (check_fresh, stack_live); seal age; strict check `days_elapsed` against `generated_at` | 16 | 0 |

Disagreement types (pipeline): (iii) damaged input scored or published without being withheld **16**. 5 of these change a published card figure, which also counts as (i). There are 0 of types (ii), (iv) and (v).

## Every disagreement (grouped by cause; each row is in disagreements.csv)

| # | Level | State | What was damaged | Shown | Expected | Cause (file, line) |
|---|---|---|---|---|---|---|
| 1 | pipeline | current | `data/derivs/{ETH,BTC}_funding_daily.csv`, column `funding_oi_weighted`: one cell set to inf / 1e300 / nan (mid-history; 5 runs) or today's cell set to 3.0 / -3.0 / inf / nan / 1e300 (10 runs) | Feed published clean every time. With ETH's last cell at 3.0, inf, nan or 1e300, the ETH 1D forming card changes (confirmations, sample, odds). The other runs scored the bad value with no visible change | Job stops ("a funding value is not a number between -1 and 1"), which is what the same values in `funding_mean` get | `fetch.py` l.289/297 range-checks only `funding_mean`. The scorer reads `funding_oi_weighted` first (`analysis/pcrtest.py` `funding_below` l.99: `r.get('funding_oi_weighted') or r.get('funding_mean')`). Text in that column crashes grade and the feed is held, so only numeric bad values get through |
| 2 | pipeline | current | ETH funding file missing its last 3 days (derivatives source down 2 days, or file cut at a line end) | Published clean. ETH 1D card changes: confirmations "none" -> "funding at or above its 90-day median", n 27 -> 17, rose 10% 67% -> 65%, typical drop -9.3% -> -17.7%. Nothing says the funding read is 3 days old | Withheld, or the card without a funding read | `stack_live.py` `funding_at` l.225-229 uses the last known funding day as today's. `fetch.py` l.299 accepts a series up to 3 days old (documented tolerance). With 1 or 2 days missing the card is unchanged. BTC with 3 days missing is unchanged |
| 3 | page | 23:13 run (12 Nov), viewer 00:05 on 13 Nov | Clock: the feed is 52 min old, but the 1D confirmation bar closed at 00:00 | BTC 1D / ETH 1D cards read "confirms 13 Nov 2026 if it closes above about $X (an estimate until the current bar closes)". No stale note. If the 00:13 run fails, this stays up to 5 h | Wording that does not say the bar is still open after it has closed (for example "result pending the next update") | `index.html` `cardFromFeed` l.624 words from the feed alone. The viewer clock is used only for the 5-hour note (l.586-594) |
| 4 | page | replay 2026-01-01 00:13 (quiet + filter on forced so the text renders; the count uses the real ledger) | Clock: 1 January | "Top-grade setups come about 21 times a year (2020 to 2025 average)". All 2020-2025 top-grade signals are 130; 130 / 6 = 22. Same until about 1 Mar | 22, or a statement that names the incomplete year | `index.html` `perYearText` l.816-821 counts ledger rows. The ledger lists a signal only after its 60th day closes, so late-2025 signals are missing in Jan-Feb |

Not sure #3 and #4 count as damage. They are real-life timing states (runs around midnight and 1 January), so they are in the counted section as the brief asks.

## What failed safe, by family (counts of OK rows)

- **Page.** MISSING 34: 10 "Data unavailable", 18 chart "unavailable", 4 "Past signals unavailable", 2 other. MALFORMED 66 (plus 2 harness slips, below): 13 down, 18 ledger unavailable, 18 chart unavailable, 9 same page (CRLF, columns reordered or extra, rows shuffled), 10 other. WRONG CONTENT 23: 13 chart unavailable (feed vs chart file from another run or asset in both directions, files under another asset's or timeframe's name), held or fail-closed feed paired with clean files reads held, the ledger served at the feed path reads down. PARTIAL 6: held and fail-closed feeds read "Setups held back", with the stale note when old; the extras-killed run shows its cards, and its missing chart files read unavailable. TIMING 20: 4 h 59 min clean, 5 h 01 min and 3 days stale on every tab, left open 5 h and 2 days (hour count advances), slow feed "Loading" then drawn, hang + 504 goes Loading then down, quiet market auto example turns off when stale, year-end, live and forming top-grade replays draw every chart. DELIVERY 23: empty, HTML 200, connection dropped mid-body and wrong content-type for feed, ledger, two chart files and example, plus 3 combinations. No script error, placeholder or blank area in any state. No injected markup ran.
- **Pipeline.** 218 candle and series damages stopped at check_candles. 41 held and 4 fail-closed from damage after the check. 26 benign ones (CRLF, trailing blank line, reordered columns) published the same figures. Datasets changed between steps (102 runs over 6 gaps: deleted, emptied, header only, cut, column lost, row duplicated, figure altered, older copy) were all held or fail-closed. Steps killed mid-run (16 effective kills), out of order, repeated, skipped, interleaved runs, feed_live run 3 h later and seals from the future were all held or fail-closed. Clocks a day ahead or behind, or before today's candle, stopped or held; 00:00:00 published equal figures; a run straddling midnight failed closed. 19 alert-log sequences (held, fail-closed, failed log write followed by every combination, log deleted / emptied / duplicated / cut / CRLF, previous feed deleted / cut / older) never sent an alert twice, never sent one while withheld, never lost one.
- **Got through but harmless, not counted** (listed in the CSV): a 12H file cut at its end or replaced by an older copy (12H is not scored and has no freshness rule). Funding one or two days behind (equal figures). A sign flip of a valid funding value (a value, not structure). A blank `funding_oi_weighted` or put/call cell (legitimate blank). An older dataset copy that was byte-identical. A hand run (or wrong CTZB_STEP_OUTCOMES) with regress failing publishes, as FEED_SPEC "Held feed" documents. The figures follow from the inputs.

## Hardening (not counted): forged contradictions the strict check accepts

| Case | Shown |
|---|---|
| Ladder row share no count can give (n 8, 37%) | accepted, shown "37% · n 8" |
| Era share no count can give (n 22, 51%) | accepted |
| `scored_as_of` 3 days before `generated_at` | accepted; no stale note (stale is judged on `generated_at` only) |
| Forming card confirming on 2030-01-01 | accepted |
| Past path whose day-0 median is +5% | accepted (cloud starts at +5%) |
| Ledger top-grade row moved to another chart, counts unchanged | accepted, row shown under the wrong chart |

These were rejected or handled correctly: shares above their parent, eras that do not add up, a card of another chart, duplicate ids, low after confirmation, reversed ladder, two cards of one asset with different prices, example paths of another sample, misses vs grade_odds, live signal states that contradict best/worst/edge, 30 Feb, duplicate keys (last wins on both sides), exponent numbers, a 200k-character sample, unicode, markup in every text field (shown as text), 0 / 100 / 0.01 / 999,999,999.99 values, a sample of 0 ("No odds yet"), and the 70 / 69.999999 edge on the ladder. Lead-trader files: 3 valid shapes (a long open with optional fields absent; a short open/add/reduce/close cycle on ETH only; 400 trades) plus 9 damaged ones and 6 broken deliveries were all correct ("unavailable" when damaged). No dollar size or contract count is shown even when the file carries one.

Harness slips, re-done or explained in the CSV: the chart CSVs already end lines with CRLF, so my "CRLF" and "cut the last digit" chart cases tested other things (re-done: a cut close reads unavailable). Two edge forgeries broke another rule (re-done as H-edge2: pass). Three expectation slips were also correct page behaviour.

## Repo's own tests (part C)

| Test | Result |
|---|---|
| `tests/test_seal.py` | 23/23 pass (29 s) |
| `tests/test_page_timing.py` | 10/10 pass (18 s) |
| `RENDER_LIMIT=40 REJECT_LIMIT=10 tests/test_feed_damage.py` | 31/31 pass (13 min) |

What they do not cover, and this audit did:
- HTTP status, empty, HTML and dropped-connection bodies for the feed and ledger.
- Files from different runs mixed on the page (feed vs ledger vs chart vs example; held or fail-closed feed with clean files).
- Pipeline input damage beyond the seal: candle rows, columns and encodings, the derivatives and put/call series.
- The scored `funding_oi_weighted` column (cause #1) and stale funding (cause #2).
- Killed and interleaved steps.
- Alert-log failure sequences.
- Viewer clock against bar close (cause #3) and the 1 January per-year count (cause #4).

## Could not test

- The Kraken cross-check: there is no network, so it reads "unavailable", as designed.
- The real site and mirror Workers. `csvToBars` was emulated in Python. Mirror sync across two commits and GitHub push/rebase races were represented only by mixing files at the page.
- check_fresh on the real clock: it was emulated on the pinned clock.
- Killing feed_live between its feed write and its log write: a failed log write was used instead.
- The Access gate, the live trades relay (404 here) and the viewer device clock (accepted).
- The full-size test_feed_damage run: only the quick pass was run.
