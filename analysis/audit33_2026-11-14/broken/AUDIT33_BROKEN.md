# Audit 33c: damage audit of the ETHKROS member site and pipeline

Independent run, 14 Nov 2026. All code is my own: `ph.py`, `judge.py`, `page_cases*.py` (page), `pipe.py`, `runclock.py`, `pipe_cases*.py`, `alert_seq.py`, `derive.py`, `replays.sh` (pipeline), `fuzz_verdict.py`. I edited, committed and pushed nothing in the repo. Every case is in `all_checks.csv` (1,607 rows) and every disagreement is in `disagreements.csv`. I decided the expected result for each case before running it.

This work measures entry quality only. Nothing here is a strategy return or a track record, and the dashboard signals are computed, never fills.

## Top line

**Real-life disagreements: 1 case, seen in 2 states.** A lead-trader file that lists the same fill twice shows it as two trades. Nothing else got through. That covers every damaged feed, ledger, chart file and input, every partial run and every clock state.

### Page level (Playwright, both states)

| Family | General rule meant to catch it | Cases tried | Got through |
|---|---|---|---|
| 1 MISSING | `get()` returns null on any non-OK or failed fetch. No feed reads "Data unavailable", and each other file reads its own "unavailable" | 61 | 0 |
| 2 MALFORMED | The strict check (`FEED_SCHEMA` + `crossCheck`). Ledger: cell count, cut line, `ledgerRowOk`, no repeats, matches `grade_odds`. Charts: Worker `csvToBars` + `barsOk`/`stepsOk`. Lead-trader file: schema `trades` | 276 | 0 |
| 3 WRONG CONTENT | Chart file: its name, its steps, its last close equal to `price_now`, its entry close, ending by `generated_at`. Ledger counts against `grade_odds`. Example: entry date and close | 45 | 0 |
| 4 PARTIAL RUN | The same rules across files from different runs; held and fail-closed feeds | 9 | **1 (2 states)** |
| 5 TIMING | `staleNote` (5 h and the daily close), checked again every minute. Days counted from the feed's own date | 30 | 0 |
| 6 DELIVERY | Loading states. `chartTok` (a slow file that arrives after the member picked another setup is not drawn). Cut, empty or HTML bodies fail the rules above | 48 | 0 |
| Hand-forged (not counted) | `crossCheck` | 59 | 0 |

### Pipeline level (copies of both states, steps run in the workflow's order with its gating)

| Family | General rule meant to catch it | Cases tried | Got through |
|---|---|---|---|
| 1 MISSING | `check_fresh`, `history_problems`, the seal ("is missing"), `check_log` and the second copy | 25 | 0 |
| 2 MALFORMED | `fetch.history_problems` (in `check_candles` and in `stack_live` with `lag=True`), `_file_problem`, `_series_problems` | 645 | 0 |
| 3 WRONG CONTENT | Bucket equality, ETH/BTC price ratio, market-column names, first day, intraday end bar, the 11 Nov run's files | 62 | 0 |
| 4 PARTIAL RUN | The seal (`seal.check` / `seal.problems`, `age_problem`), `CTZB_STEP_OUTCOMES` gating, alert log (`check_log`, `carried_alerts`). Includes 25 alert-log sequences | 336 | 0 |
| 5 TIMING | `check_fresh`, stack's "today's bar", `age_problem`, strict check `scored_as_of` = day of `generated_at` | 9 (+6 boundary replays) | 0 |
| 6 DELIVERY | Previous feed unreadable or an HTML page, and `check_log` | 1 (+ all page F6) | 0 |

I also compared verdicts: 2,000 single-field mutations of both real feeds, judged by the page's `__feedProblems` and by `feedcheck.problems`. They disagreed on none.

### Disagreements by kind (real-life only)

| | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 1 (2 states) | 0 |
| (ii) raw placeholder, script error, blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

| Level | State | Damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| page | replay 11 Nov, current | Lead-trader file holding one fill twice (the same `id`, time, price and size) | The Lead trader panel lists "ETH long · open" twice, as two trades | The fill once, or "unavailable" | `index.html` `tradesProblems` (~l.530-538) checks shape, newest-first order and future times only. The schema's `trades` item has no `id`, so a repeated event passes. Real life: the relay `cloudflare/ctzb-trades-worker.js` `appendEvents` (~l.318-326) removes repeats only against a KV read. KV is eventually consistent (up to ~60 s) and the cron runs every minute, so a tick that reads stale state and stale events posts the same fill again. That is my reading of the code; I could not reproduce it here. |

**Not counted (design, one line):** a hand run of `feed_live.py` with no `CTZB_STEP_OUTCOMES` publishes clean even though `tests/regression.py` failed. `feed_live.py` l.423 handles it that way and FEED_SPEC documents it ("judged on stack_status.txt alone"). The workflow always sets the variable, so this needs a person running the step by hand.

## Hardening (not counted)

I tried 59 hand-forged feeds with every field valid but contradictory, plus boundary values. None got through.
- **Contradictions:** a live signal's `edge_status` against its best/worst/edge level; `days_elapsed` off by one; a card from another signal or with another entry close; a day-30 figure before day 30; ids against chart and date; day figures outside best/worst; shares above their parent share; duplicate grade rows; misses above signals; `grade_odds` counts against misses and paths; past paths reversed or quartiles out of order; odds-fade bands out of order or marks against their share; `cards_withheld` against `checks.all_passed`; `scored_as_of` after `generated_at` or a day before it; the example's sample, entry close and paths; `grade_odds` swapped in from the other run; ladder order and counts; eras; dates out of order; confirms before today; never-fell share above the +10% share; dip ordering; rounded share against exact share.
- **Each one:** the feed was rejected ("Data unavailable"), or the affected chart said unavailable.
- **Boundaries handled correctly:** 69.999999 shows as 70% but is read as below the bar; `price_now` 0.01 makes the chart refuse; a typical high on day 0 shows "Day 0".

## What failed safe, by family

- **F1 Missing (86):**
  - Feed 404/500/502/503 or a network error reads "Data unavailable", header "Feed unavailable". Nothing reads as quiet.
  - A missing ledger, example or chart file reads its own "unavailable". Every combination I tried read the same way.
  - A deleted input stops the job at `check_fresh` or `check_candles`.
  - An alert log deleted, or a log and its copy both deleted, is restored from the copy or held. No alert was lost or sent twice.
- **F2 Malformed (921):**
  - Feeds cut at 9 points, empty, `null`/`{}`/`[]`, trailing junk, doubled, UTF-16 or holding NUL bytes are rejected.
  - BOM, CRLF, minified, exponent and escaped-unicode forms are accepted and render exactly like the clean page.
  - A ledger cut mid-line or at a top-grade row, with a header only, HTML, duplicated rows, lost columns, bad cells, run-together rows, a stray quote or a CR-only cut reads unavailable. Converted line ends, a BOM or shuffled rows render the same figures.
  - Chart files with 20 kinds of row/cell/column damage are refused. Damage made at the JSON level (cut, empty, HTML, 9 bars, text prices, no name) is refused too.
  - On every candle file, 1D-8D, 4H and 12H, 23 kinds of structural damage stop the job at `check_candles`/`check_fresh`.
  - Damage to the columns the scorer reads in funding, long/short, open interest and put/call (blank, text, zero, negative, out of range, dropped, swapped, last rows lost) fails closed, at `check_candles` or as a held feed. The last case is the 2-day lag rule.
  - The damage that "passed" touched only columns no step reads, or was a valid value or the normal 1-day lag. Output was byte-equal to the clean run (overrides recorded in `all_checks.csv`).
- **F3 Wrong content (107):**
  - Another asset's or timeframe's candles, the other run's chart files, ledger or feed under each name: the job stops at `check_candles`/`check_fresh`, or the page refuses the chart (close against `price_now`, steps, end time, name).
  - The feed from 11 Nov served beside today's files shows "86 hours old" on every tab, and its charts are refused.
- **F4 Partial run (345):**
  - Any changed, deleted, cut or stray dataset between steps fails at the next seal check (that step fails, so the feed is held) or in `feed_live` (fail-closed).
  - Steps skipped, out of order or run twice also fail closed; a refresh started mid-run and seal tampering likewise.
  - The 5 gating steps reported as failure, skipped, cancelled, empty, "Success", missing or garbage are held. Extras reported failed or skipped withholds the extras and deletes the chart files.
  - Alert log: a held run, a fail-closed run, a run killed between the feed and the copy or between the copy and the log, a log cut, emptied, duplicated, reordered or from a newer run, an unreadable previous feed, and two runs interleaved in one folder. In all of them no alert was lost, none was emitted twice, and a withheld run left the log alone.
  - A real held feed, a real fail-closed feed and a real extras-withheld feed render correctly.
- **F5 Timing (54):**
  - Clock a day ahead or behind: the job stops. 00:00:30 with no new bar: held.
  - Scoring at 23:58 with the feed at 00:01: fail-closed. Feed 2 h 01 after its seal, or before it: fail-closed.
  - Feed written at 23:59:59 or 00:00:00 is consistent.
  - Viewer clock at -5 min, -1 day, +4 h 59, +5 h 01, +3 days, +2 years and 31 Dec 23:59:59; page left open 5.2 h and then 30 h (the note appears and its hours keep counting).
  - Boundary replays on 12 Nov (day 60), 1 Jan 00:20, 31 Dec 23:50, 29 Feb 2024, 1 Mar 2024 and 10 Nov all published clean. Their pages chart every setup, and each shows the daily-close note after 00:00.
- **F6 Delivery (49):**
  - Feed, ledger, every file 30 s late, and the feed arriving 6 h late (stale on arrival): "Loading" while waiting, then the clean page.
  - A slow chart file arriving after the member picked another setup or the example is not drawn.
  - The lead-trader file as HTML, cut, empty or 500 reads unavailable.

## Repo's own tests (stage C, on a copy of the repo)

| Test | Result | Not covered (that this audit added) |
|---|---|---|
| `tests/test_feed_damage.py` (RENDER_LIMIT=40 REJECT_LIMIT=10) | 31/31 pass | It turns CSV into chart JSON with Python `float`, not the Worker's `csvToBars` (blank → 0, JS whitespace trim, hex). It does no cross-file runs (feed from one run with a ledger or charts from another), no damage to the candle CSVs before the Worker, no line-end variants, no repeated lead-trader events, and no clocks or slow files |
| `tests/test_seal.py` | 29/29 pass | Wrong `CTZB_STEP_OUTCOMES` values ("Success", empty, missing key, garbage). Steps skipped, repeated or interleaved. Inputs in `data/` changed between each pair of steps. Clocks at the seal's 2 h edge or before it |
| `tests/test_page_timing.py` | 20/20 pass | Every file slow at once, and the feed arriving after the 5 h line |

## Could not test, and why

- **Live HTTP behaviour of the Workers:** no network. Cloudflare-specific failures (partial bodies mid-stream, CDN-served stale objects, KV staleness) were modelled as bodies served by my router, not observed.
- **Kraken cross-check:** no network, so it ran as "unreachable" (never fails, by design). Coinbase fetch and `fetch.py`'s writes were not run; inputs were damaged after a "fetch".
- **Real git concurrency** (two workflow runs racing to push): only simulated as two runs interleaved in one folder.
- **The relay's KV race** behind the one disagreement: argued from the code, not reproduced.
- **The full-size `test_feed_damage.py`** was not run, only the quick pass. Out of scope by the brief: viewer device clocks, replays before Sep 2020, and value-only changes to candles or to published fields.
