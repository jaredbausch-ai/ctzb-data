# Audit 31c: damage audit of the ETHKROS member page and pipeline

Independent auditor, 14 Nov 2026. Own harness only (Playwright page level, copied-repo pipeline level). Nothing in
`/home/claude/ctzb-data` was edited. The site measures entry quality only: there is no exit in the data, so nothing here
is a strategy return or a track record. Details: `all_checks.csv` (775 rows), `disagreements.csv`.

## Top line

**2 disagreements (real-life damage). Both are wording that misstates the state (iv). No wrong figure, no placeholder
or script error, no damaged input scored, nothing that reads as a return.**

| Level | Family | Cases tried | Got through |
|---|---|---|---|
| page | 1 Missing | 31 | 0 |
| page | 2 Malformed | 118 | 0 |
| page | 3 Wrong content | 23 | 0 |
| page | 4 Partial run | 6 | 0 |
| page | 5 Timing | 30 | 0 (D2 shows on the page, counted under pipeline) |
| page | 6 Delivery | 56 | **3 cases, one defect (D1)** |
| pipeline | 1 Missing | 53 | 0 |
| pipeline | 2 Malformed | 289 | 0 |
| pipeline | 3 Wrong content | 48 | 0 |
| pipeline | 4 Partial run | 62 (incl. 14 alert-log sequences) | 0 |
| pipeline | 5 Timing | 34 | **1 (D2)** |
| pipeline | 6 Delivery | n/a (browser-side) | n/a |

States tried. Page: replay_0414, current, the pipeline's own held, fail-closed and extras-failed feeds, and replays
for 12 Nov 22:14 (viewer after midnight), 31 Dec 2025 22:14 (viewer on 1 Jan), 1 Jan 2026, 29 Feb 2024, an A+ signal
on day 1 and on day 60, a quiet market with the filter off (clean and held). Pipeline: replay_0414 (clock 04:44) and
current (clock 13:43), each with an undamaged baseline run, plus the quiet 15 Jun 2022 replay for the midnight case.

| Category | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure | 0 | 0 |
| (ii) placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 1 (D1) | 1 (D2) |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

| # | Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|---|
| D1 | page | replay_0414, current | Lead-trader file 3.5 to 6 s late, member on the Chart tab | Chart side panel: "The lead trader's feed is unavailable right now". It says this while the file is still loading, and still says it after a valid file arrives, even though the Now tab already shows "in · long". It only changes when the member leaves and re-opens the Chart tab. | "Loading" while the file loads (family 6 rule: never "unavailable" during loading). After a valid file arrives: "listed on the Now tab". | `index.html:1149` (renderChartSide tests `S.trades` only, with no `S.loading.trades` branch); `index.html:1267-1270` (`pTrades.then` redraws the lead panel and the card, but not an open Chart tab) |
| D2 | pipeline + page | quiet market (15 Jun 2022 replay, filter off) | A run that finishes scoring before 00:00 UTC and starts `feed_live.py` after it (steps 23:59:40, feed 00:00:05) | Clean feed: `generated_at` is 00:00:05, `scored_as_of` is the previous day. At 00:03 the page shows no "daily close has passed" note and reads "updated 00:00 UTC · checks passed". The same data written at 23:59:55 does show the note. | The close note (the data is from before the close), or the feed held back | `index.html:608-609` (staleNote judges the close from `generated_at`, not from the data's day); `feed_live.py:431` (stamps its own start time); `index.html:457` and `feedcheck.py:129` (reject `scored_as_of` after the feed's day but not before it). When open signals exist, the `days_elapsed` cross-check fails the run closed, so only quiet or forming-only feeds get through. |

D2 is real-life but rare. It needs the last scoring step to finish within seconds of midnight, which a retry run
started around 23:58 can do. The window lasts until the 00:13 run, about 13 minutes.

## Hardening (not counted)

28 hand-forged feeds. Every field in them is valid but the fields contradict each other. The page rejected 3. It
accepted 25, and in every accepted one the figures shown equal the file's own values, with no script error and no
injected markup run. The accepted contradictions:

- a card at 100% rose-10% whose median best move is +4%
- 100% touched -30% with a median deepest dip of -1%
- `sample` "from 50 past signals" on a card of 5: the check is only that the text contains "5"
- both eras at 0% while the overall never-fell share is 90%
- a past-path day 0 that is not 0%
- the falls-5%-first ladder row at 100%, above the from-entry share
- live day-10/day-30 figures out of time order
- `low_day` after the feed's date
- a forming card that confirms in 2027
- `must_close_above` at half the current price
- the example card's entry close differing from the example file (the example chart is refused)
- a miss whose median peak is +55%, or whose worst drop is 0 with day 60 at +99%
- day-10 green at 10% and red at 95%
- `scored_as_of` two days before `generated_at` while live signals are present
- `price_now` 1 cent off its chart (the chart is refused)

Text and number edge cases also rendered as the file's values: duplicate keys (the last one wins, the same in the page
and `feedcheck.py`), deeply nested junk, exponent forms, HTML/script/`${}` in `sample` (shown as escaped text),
4,000-character unicode, shares of 0 and 100, and prices of $0.01 and $999,999,999.99.

## The rule per family, and what failed safe

1. **Missing.**
   - Rule, pipeline: `check_fresh`, then `fetch.history_problems` ("is missing"), then seal "is missing", then `feed_live` (required files).
   - Rule, page: `get()` returns null, so the page reads "Data unavailable" or the file's own "unavailable".
   - Failed safe, page: 31/31. 9 read "Data unavailable"; 22 showed the feed with only the lost file reading "unavailable".
   - Failed safe, pipeline: 53/53 (26 stopped before scoring, 14 held, 6 fail-closed, 7 alert-log restores).
2. **Malformed.**
   - Rule, pipeline: `history_problems` (`_file_problem`, `_row_problems`, `_series_problems`, bucketing).
   - Rule, page: FEED_SCHEMA plus crossCheck; parseCSV (dropped and cut rows); `ledgerRowOk`; `barsOk`/`stepsOk`; the Worker's `csvToBars`.
   - Failed safe, page: 118/118.
   - Failed safe, pipeline: 289/289. 226 stopped. 27 held. 6 fail-closed. 30 clean with content equal to the undamaged run: line-end changes, a reordered column, a series one day behind, and per-market or `pcr_prem` columns the scorer never reads (columns the source adds and drops itself).
3. **Wrong content.**
   - Rule, pipeline: the asset ratio, the 4H/12H step test, 2D-8D bucketing, seal hashes and the alert-log hash.
   - Rule, page: chart label, last bar no later than the feed, last close equal to `price_now`/`entry_close` to the half cent; ledger counts and +10% share against `grade_odds`; example entry close.
   - Failed safe, page: 23/23. Feeds and other files swapped between the 12 and 14 Nov runs, another asset's or timeframe's chart under the name, and files served under the wrong path.
   - Failed safe, pipeline: 48/48 (23 stopped, 15 held, 10 fail-closed).
4. **Partial run.**
   - Rule: the seal (order, repeat, hashes, 2-hour age), strict `CTZB_STEP_OUTCOMES`, extras clearing its files first, then the feed, its copy and the log written in that order.
   - Failed safe, pipeline: 62/62. That covers 9 steps killed, 5 skipped, 3 out of order, 4 repeated, 8 outcome strings, two interleaved runs, and 14 alert-log sequences (held, fail-closed, died between feed and log, log cut/duplicated/garbled/older/lost, feed lost or older). No alert was lost or emitted twice, and nothing was sent on a held run.
   - Failed safe, page: 6/6 read "Setups held back".
5. **Timing.**
   - Rule, pipeline: `check_fresh` (today's 1D bar and the current 4H bar), stack's today-bar and lag checks, seal age.
   - Rule, page: the 5-hour note and the daily-close note, re-checked every minute; per-year counts from full years only.
   - Failed safe, pipeline: 33/34. Clocks a day or 4 hours off stopped or held. 00:00:00 held. 23:59:59 was clean and equal to the undamaged run. A run spanning midnight with live signals failed closed. The seal at 2 h 01 or in the future failed closed.
   - Failed safe, page: 30/30. That covers the 4 h 59 / 5 h 01 / 3-day / 3-year clocks, feeds 3 minutes and 1 day ahead (accepted, as specified), a page left open 5 and 7 hours (hour count kept current on every tab), midnight, 1 Jan, 29 Feb, day 1, day 60, and a stale quiet market (no automatic example).
6. **Delivery.**
   - Rule: the strict checks; CSVs and candle files without a final newline refused; `sameCents`; loading states; the chart request token.
   - Failed safe, page: 53/56. Feeds cut at 2-99.9%, empty, HTML 200, UTF-16, gzip, doubled, null or a NUL run; ledgers and chart JSON cut, empty or HTML; slow feed, ledger, example and chart files; and a member switching setups while a chart file is slow.
   - The 3 that got through are D1.

## Not counted, by stated design

- A hand run with no `CTZB_STEP_OUTCOMES` publishes clean when only the regression guard failed. FEED_SPEC says a hand run is judged on `stack_status.txt` alone.
- These fail closed when they did not need to (safe, not a disagreement):
  - extras reported "skipped", or killed in a hand run, withholds the whole feed instead of just the extras;
  - a ledger with a non-top-grade row repeated, or its header row repeated, is shown, and correctly so (only top-grade rows are read).
- A last feed replaced by an older run's copy keeps every later run fail-closed until someone fixes it by hand. This is safe, but the page's "usually within the hour" no longer holds.

## Repo's own tests (part C)

| Test | Result |
|---|---|
| `test_seal.py` | 29/29 pass |
| `test_page_timing.py` | 16/16 pass |
| `test_feed_damage.py` (RENDER_LIMIT=40, REJECT_LIMIT=10) | 31/31 pass; page and pipeline agree on 9,507 and 9,499 damaged feeds and on 695 lead-trader files |

What they do not cover:

- **D1.** No test makes the lead-trader file slow, and none checks the Chart tab after it arrives.
- **D2.** No test runs scoring and `feed_live` on opposite sides of midnight.
- **Forming cards.** `test_feed_damage`'s "replay of 12 Nov 2026 (a state with forming cards)" has 0 forming cards: the replay keeps the day's bar whole. So forming-card rendering and the chart's `price_now` check are not exercised by that test under damage.
- **Ledger and chart damage.** Only 11 ledger damages and 10 chart-file damages are tried. Wrong-run, wrong-asset and wrong-timeframe files and Worker conversion details are not.

## What I could not test

- **Network.** Coinbase, Kraken (stubbed both agreeing and 1% off), the Cloudflare Workers (`csvToBars` emulated in Python) and the mirror's 15-minute pulls.
- **GitHub.** Concurrency groups and push races (two runs were only interleaved in one folder) and the CDN caching of raw files.
- **Browsers.** Chromium at 1400 px only; no other browsers or phone widths.
- **Lead-trader relay.** The live relay; it is 404 in this harness, so valid trade files were served by hand.
- **Old dates.** Replays before Sept 2020 (out of scope).
