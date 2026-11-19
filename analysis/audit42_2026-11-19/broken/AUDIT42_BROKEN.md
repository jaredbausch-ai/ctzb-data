# Audit 42c: damaged, missing, inconsistent and tampered files (code frozen at 8d944e4)

I wrote all the code independently, in `code/`. Raw results are in `w/*.jsonl`, and every check is in `all_checks.csv` (868 rows). I did not read, import or copy anything from earlier audits.

## Top line

**One real-life disagreement: 0 at page level, 1 at pipeline level.** A candle file whose line ends are CR CR LF passes the candle check. Where that file is a scored one, the run fails safe one step later. A 12H or 4H file is not scored, so the run publishes clean and commits the damaged file. No figure a member reads changes.

| Family | Rule meant to catch it | Cases tried (page + pipeline) | Got through |
|---|---|---|---|
| 1 Missing | Page: `get()` returns null on a non-OK, thrown or unparseable response, so that area reads "unavailable". Pipeline: `history_problems` "is missing"; `feed_live` requires its five card files after a clean run; the seal flags any file that went missing | 36 + 16 = 52 | 0 |
| 2 Malformed | Page: `parseCSV` dropped/cut, the strict check, `barsOk`/`stepsOk`, the Worker's `csvToBars`. Pipeline: `fetch.history_problems` (`_file_problem`, exact header, `_row_problems`) and `check_candles.structural` | 211 + 20 direct = 231 (page cut/blank/dup cases are counted under Delivery) | **1** (CR CR LF line ends) |
| 3 Wrong content | Page: chart name, last close = `price_now`, entry close, ledger matched to `grade_odds`, example entry close. Pipeline: ETH/BTC close ratio, 2D-8D = daily bucketed, 4H/12H step and 25% check, market columns | 48 + 22 = 70 | 0 |
| 4 Partial run | `seal.py` (order, repeats, file hashes, 2 h age); `CTZB_STEP_OUTCOMES` gating; `feed_live` requires `candle_check.structural_ok`; alert-log record plus second copy | 20 + 125 + 23 alert sequences = 168 | 0 (1 explained, 2 two-fault) |
| 5 Timing | `check_fresh` (today's daily bar, current 4H bar); stack_live requires today's bar; seal age; strict check (`scored_as_of` = the day of `generated_at`); page `staleNote` | 31 + 22 = 53 | 0 |
| 6 Delivery | Page: JSON parse to null, `parseCSV` cut, Worker refuses a cut CSV, chart token for slow files, loading states | 172 | 0 |

| Level | States tried | (i) wrong figure | (ii) placeholder / script error / blank | (iii) damaged input scored or published | (iv) state misworded | (v) reads as return / trade |
|---|---|---|---|---|---|---|
| Page | 14 real states (replay 11 Nov, current 19 Nov, replays 12 Nov, 18 Nov 22:13, 31 Dec 2025 20:13, 1 Jan 2026 00:13, 29 Feb 2024, a quiet 15 Apr 2026, 30 Dec 2024, 3 Jan 2025, 1 Feb 2025, a real held feed and a real fail-closed feed); 321 cases | 0 | 0 | 0 | 0 | 0 |
| Pipeline | Copies of replay_1111 at 20:30Z, plus 12 Nov data for alert sequences; 387 runs + 23 sequences + 20 direct checks | 0 | 0 | **1** | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| pipeline | copy of replay_1111, clock 2026-11-11T20:30Z | `BTC_12H.csv` with every line ending CR CR LF, as when a CRLF file goes through a CRLF conversion again. Checked directly too: the same holds for every candle file, whole or with one such row | `check_candles` and `history_problems` pass it. The run publishes a clean feed and the damaged 12H file is committed. 4H with one such row mid-file also passes. 1D, 2D and 3D fail safe later: `check_fresh` raises IndexError, so the job stops; `engine.load` raises IndexError, so refresh, grade and stack fail and the feed is held | Candle check fails: a lone CR is a blank line to every universal-newline reader | `fetch.py:207-208` `_file_problem` splits on LF only and strips CR from each piece, so a piece holding only CR is never seen as blank. `engine.py:74` and `check_fresh.py:28` then read that piece as an empty row |

## Not counted

- **Explained.** Putting the whole `feed/` folder back to the run before's (feed, log and copy all reverted) makes the next run emit 4 alerts again. In real life that state means one of two things. The commit never landed (push failed), so the mirror never read those alerts and re-emitting them is right. Or someone with write access undid a landed commit, which is out of scope. In both cases the sender's alert_id memory still stops a second send.
- **Two-fault, recorded.** (a) The log and its copy both deleted: fail-closed, nothing lost or repeated. (b) The feed lost and the log cut: the log is restored from the copy and no alert repeats. Both behave as the spec says.
- **Documented behaviour.** With `CTZB_STEP_OUTCOMES` unset or empty (a hand run) and a failed regression step, the run publishes clean. FEED_SPEC "Held feed" says a hand run is judged on `stack_status.txt` alone.
- **My expectations that were wrong; the results are correct.** These pipeline rows are all marked ok in all_checks.csv:
  - Cells in exponent form, quoted cells, spaces in cells, and a time written as a float on 4H/12H: format only, same values. For the exponent case the chart CSV bytes differ because extras copies cell text, but the values are equal.
  - "Two runs interleaved": the second refresh restarts the seal, so it is one whole run.
  - Spaces around "=" in `CTZB_STEP_OUTCOMES`: every step really did succeed.
  - P0229 at 00:00:30: the 5-hour note correctly takes precedence over the daily-close note.

## Hardening (not counted)

108 forged or unusual cases on two states, all as expected. The page's verdict and `feedcheck.py`'s verdict agree on every one.

- **Contradicting feeds (62, all rejected, "Data unavailable"):**
  - shares nested wrong
  - eras or ladder counts that do not add up
  - ids that do not match
  - `low_day` after `confirms_on`
  - the sample text naming another size
  - duplicate cards or signals
  - a card attached to the wrong signal
  - `days_elapsed` off by one
  - `edge_status` contradicting best or worst
  - day-10 present too early
  - grade_odds, if_it_misses and past_paths disagreeing with each other
  - another card used as the example
  - withheld but carrying cards
  - `scored_as_of` before or after its day
  - odds_fade out of order, mismarked or undated
- **Accepted-but-unusual feeds (shown with the file's own values):**
  - lists reversed
  - a big price
  - HTML and script markup in every text field: escaped, nothing executed
  - a 20 kB sample
  - RTL, emoji and zero-width text
  - deeply nested junk
  - duplicate JSON keys
  - exactly 70 / 69.999999 on the edge bar
  - days 0 and 60
  - feed 3 minutes and 1 day ahead of the viewer
  - price 0.01: the chart reads unavailable
- **Lead-trader files (18):**
  - valid long and short, open/add/reduce/close, 40 BTC-only trades, empty, ids absent, 4 minutes ahead: shown correctly, with the right "in · long", "out" or "not in" on each card
  - damaged ones (30 minutes ahead, oldest first, the same fill twice by id, without id, or with a different time format, unknown asset, price or leverage 0, no action, not a list): all "unavailable"
  - a row carrying `usd_size` and `contracts`: accepted, and neither is shown

## What failed safe, by family

| Family | Page (outcome) | Pipeline (outcome) |
|---|---|---|
| Missing | 36: feed 404/500/abort reads "Data unavailable" with no quiet wording; ledger, trades and example "unavailable"; each chart file and all chart files "Chart data unavailable" | 16: 12 job stopped (candle check), 3 held (missing grade.json, grokpack.json or regression baseline), 1 fail-closed (member page missing, so feedcheck has no schema) |
| Malformed | (under Delivery) | 210: 182 stopped, 10 held, 1 fail-closed, 17 harmless format-only (same values). Covers rows duplicated, swapped, deleted at start/middle/end; columns dropped, renamed or swapped; text, blank, negative, zero, nan; cut lines; BOM; trailing blank; second header; extra comma; future bar; all derivs and put/call series |
| Wrong content | 48: feed URL serving the ledger, a chart, the example or a trades file reads down; ledger of another run "unavailable"; 12 cross-asset and cross-timeframe chart swaps and neighbouring-run chart files "unavailable"; a shifted example "unavailable" | 22: 21 stopped (asset and timeframe swaps, yesterday's files), 1 held (OI saved as long/short) |
| Partial run | 20: feed of run N with ledger and/or charts of N±1 (11/12 Nov, 18/19 Nov, 31 Dec/1 Jan) gives charts "unavailable" and the ledger only when its top-grade rows match; real held and fail-closed feeds read "Setups held back" everywhere | 125: 70 held, 43 fail-closed, 12 correct clean (the seal catches every datasets/ change between every pair of steps; killed, repeated and out-of-order steps; manifest lost, cut or old; stray file; outcomes misreported). 23 alert sequences: no alert lost or emitted twice; held and fail-closed runs log and send nothing |
| Timing | 31: 4h59 fresh, 5h01/26h/30d stale on every tab; page left open 5h or 3 days asks for a reload; midnight and 1 January notes; year-end 2D/3D/5D charts with short bars have Entry and Day 60 lines placed correctly (checked against my own date arithmetic) | 22: a clock a day ahead or behind stops the job; a run crossing midnight is held or fail-closed; a seal that is 2h05 old or started in the future is fail-closed; derivs 2 days behind or put/call 4 days behind is held |
| Delivery | 172: feed cut at 0-99.9%, HTML 200, null, {}, doubled, all "Data unavailable"; BOM and CRLF accepted unchanged; ledger cut mid-line, doubled or HTML "unavailable"; chart CSV cut, blank-lined, row-duplicated, swapped or lost "unavailable"; slow feed, ledger, example, trades and chart (with a switch mid-load) say Loading, then draw the right setup | n/a |

## Part C: the repo's own tests (run on a copy of `current`)

- `tests/test_seal.py`: 29/29 passed.
- `tests/test_page_timing.py`: 24/24 passed.
- `RENDER_LIMIT=40 REJECT_LIMIT=10 tests/test_feed_damage.py`: 33/33 passed in 14 minutes.

What they do not cover:

- None of them runs `check_fresh` or `check_candles` (`replay_at.sh` skips both and reports regression as success without running it).
- No line-end damage other than LF blank lines, CRLF and a cut last line, which is why CR CR LF slipped.
- No feed, ledger or chart files from neighbouring runs served together, which is how the mirror actually fetches them (`ctzb-feed-worker.js` reads each path at `ref=main`, and keeps serving a file deleted from the repo).
- No multi-day charts across 1 January.
- No alert-log damage combined with a run that really emits new alerts.
- No `CTZB_STEP_OUTCOMES` formatting variants.

## Could not test

- **Kraken cross-check in enforce mode:** no network here, so it always read "unavailable".
- **`fetch.py` itself:** network.
- **The deployed Workers:** the live site is an older build, 656d67c3. I ported only `csvToBars` from the frozen template; the mirror's KV behaviour I read from code only.
- **Real GitHub push races and concurrency:** simulated in one folder only.
- **Browsers other than Chromium.**
- **Feeds and replays before 2020:** out of scope.
