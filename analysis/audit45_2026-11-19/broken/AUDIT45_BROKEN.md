# Audit 45c: broken-state audit of the ETHKROS member site and pipeline (code a0dc979)

Independent auditor. I wrote all the code myself (in `bin/`), worked on copies and changed nothing in the repo. States: `replay_1111` (11 Nov 2026 04:14Z, 4 forming setups) and `current` (19 Nov 2026, 6 forming setups; I ran each pipeline case from a new seal at 14:30Z). Entry quality only: every figure checked here is a computed signal's entry quality. None is a fill, a strategy return or a track record.

## Top line

**0 disagreements** (real-life damage). That covers 1,095 counted cases: 467 on the page and 628 in the pipeline. The pipeline figure is 305 full runs, 4 midnight and 1 January replays, and 319 input-file damages that the pipeline's own input checks stopped, which I ran in-process. I tried 337 input damages in all; the 18 that passed every check were run in full. Nothing landed in any of the categories (i)–(v). Six hardening cases got through and three two-fault cases were recorded; neither group is counted.

| Family | General rule meant to catch it (from the code) | Page: tried / got through | Pipeline: tried / got through |
|---|---|---|---|
| 1 Missing | Page: `get()` returns null on any non-2xx status or network error. A null feed reads "Data unavailable"; a missing ledger, chart, example or lead-trader file reads "unavailable". Pipeline: `history_problems` reports a file as "missing"; the seal reports a file as missing or appeared; `feed_live` needs its required files plus the alert-log record or the second copy | 64 / 0 | 14 / 0 |
| 2 Malformed | Page: the strict check (`FEED_SCHEMA` plus `crossCheck`); `parseCSV` rejects a row with the wrong cell count or a missing line end; `ledgerRowOk` and a duplicate check on the ledger; the Worker's `csvToBars`, then `barsOk` and `stepsOk`; `tradesProblems`. Pipeline: `fetch.history_problems` (whole lines, exact header, every row and cell, the series rules) and the `check_candles` structural checks | 202 / 0 | 309 / 0 |
| 3 Wrong content | Page: the chart file must name the right chart, end no later than `generated_at`, and close at `price_now` and at the entry close to the half cent; the ledger must match `grade_odds` per asset; the example's entry date and close must match the card. Pipeline: 2D–8D files must equal the 1D bars resampled; the ETH/BTC close ratio; 4H/12H within 25%, on the grid and on 99% steps; market columns; a series' first day, lag and `series_through.json` | 52 / 0 | 34 / 0 |
| 4 Partial run | The seal (steps in order, each finished and run once, files unchanged, started at most 2 h before and not in the future); `CTZB_STEP_OUTCOMES` withholds on anything but `success`; any `feed_live` exception writes the fail-closed feed; extras files are deleted when extras did not succeed; the alert-log record and its second copy | 10 / 0 | 253 / 0 |
| 5 Timing | Pipeline: `check_fresh` (today's daily bar and the current 4H bar); stack's today's-bar check; the seal's age; the strict check's `scored_as_of` must be `generated_at`'s day. Page: `staleNote` (older than 5 h, daily close passed, page left open, re-checked each minute); a chart may not end after `generated_at`; the automatic example is switched off when the data is stale | 48 / 0 | 18 / 0 |
| 6 Delivery | The same page rules as 1 and 2 (a cut or HTML body means no file), the Worker's refusal of a cut CSV, `chartTok` so a late chart file is not drawn, and "Loading" states everywhere | 91 / 0 | n/a (browser side) |

**States tried and disagreements (real-life damage only)**

| Level | Cases | (i) wrong or unsupported figure | (ii) placeholder, script error or blank area | (iii) damaged input scored or published | (iv) wording misstates the state | (v) reads as a return, trade or track record |
|---|---|---|---|---|---|---|
| Page (both states, every tab, every picker button, the example switch, both chart modes) | 467 | 0 | 0 | 0 | 0 | 0 |
| Pipeline (steps run in `daily.yml` order, outcomes taken from exit codes, `feed_live` last) | 628 | 0 | 0 | 0 | 0 | 0 |

**Every disagreement:** none. `disagreements.csv` has a header only.

`all_checks.csv` has one row per case: 1,170 rows. That is the 1,095 counted cases, 43 hardening, 3 two-fault, 4 out-of-scope value edits, 2 not reachable, 1 hand run, and 22 "void" rows. A void row is a harness run that did not exercise its case (a step finished before its kill timer; a clock check stopped the job first). Each was re-run correctly and the void row is kept for the record. I also reviewed by hand every case my judge flagged; the verdicts are in `review.json`. Every flag was one of three things: a harness judging error (CSS upper-case "LATEST"; 6.5e1 compared as "65.0"; text from hidden tabs), a fail-safe reading where my expectation allowed either reading, or an older run's file that was byte-identical to this run's.

## Hardening (not counted): hand-forged feeds the strict check accepts

The strict check rejected 19 of the 43 forged feeds. Among them: swapped live cards, eras that do not add up, a sample text with the wrong count, a ladder whose counts rise, a low after its confirmation, days off by one, `rose10` with best under 10%, intact past its edge, duplicate ids, a ledger count mismatch, `grade_odds` from another run, quartiles out of order, an edge mark disagreeing with its share, withheld-with-cards, and a missing regime. The ones below got through:

| # | Forged contradiction | What the page shows | Gap (file and line) |
|---|---|---|---|
| H1 | Live A+ card's exact from-entry share set to 69.999999 (line under 65; every other share consistent) | The card says "Edge gone below: Below the 70% bar from entry" and the chart says "below the bar already". The same card's status line says "It fell to its edge level (−5%)" | No rule ties `open_signals[].edge_level_pct` or `edge_status` to its own card's ladder (`index.html` crossCheck, 464–484) |
| H2 | Live card: headline 12%, line under 10%, eras left at 80% (n 20) and 69% (n 13) | Shows 12% and 10% over eras that average about 76% | Era shares are not tied to the card's own line-under share (count-weighted); only era counts are checked (423–424) |
| H3 | Forming card with `bars_to_confirm` 0 and `must_close_above` = 3 × `price_now` | "confirms 20 Nov 2026 if it closes above $5,408…" | `must_close_above` is not checked against `price_now` |
| H4 | C-grade card relabelled A+, sample text unchanged | Ranked first as the top-grade setup, with a C card's sample | Grade and sample wording are not cross-checked |
| H5 | Forming card with its low 2 months before it confirms | Accepted, drawn as a forming setup | The `low_date`→`confirms_on` span is not bounded |
| H6 | An unread field holding a `NaN` token | Page: JSON.parse fails, so "Data unavailable". `feedcheck.problems` passes it, and `feed_live` writes `json.dumps` with `allow_nan` on | The page and the pipeline disagree on what valid JSON is. Not reachable from damage: every number that reaches such a field is checked finite upstream (extras_live, the input checks) |

Markup in every text field was shown escaped and never run; duplicate keys, exponent forms, 400-digit integers, unicode, a 200k-character sample and 3,000-deep nesting all rendered cleanly.

## Two-fault (recorded, not counted)

| Faults | Result |
|---|---|
| ETH funding lost its last row AND `data/derivs/series_through.json` records 18 Nov | Published clean, scored on the shorter file. This is the documented limit (`fetch.rows_lost_problems`) |
| Alert log lost its last row AND its second copy cut short | Clean. The log was rebuilt exactly from the previous feed's alerts and nothing was re-emitted (recovered) |
| BTC put/call lost 2 rows AND `data/options/series_through.json` deleted | Held (caught by the 2-day lag) |

## What failed safe, by family (counted cases)

- **1 Missing.** Page: every 404, 500, 503 and network abort, file by file and in combination (all files down, all but the feed down, every chart file 404), read "Data unavailable", "Past signals unavailable", "Chart data unavailable", "Example unavailable" or "Lead trader … unavailable" (68 readings). Pipeline: missing config, baseline, page, PRETRADE or seal files were held or failed closed. Every alert-log loss (log or copy deleted or emptied, previous feed lost) was restored with nothing re-emitted. Log and copy both lost failed closed.
- **2 Malformed.** Pipeline: 337 input damages across 8 candle files (1D, 2D, 3D, 5D, 8D, 4H, 12H) and 5 daily series. The damages were duplicated, swapped or deleted rows (first, middle, last), dropped, renamed or extra columns, text, blank, NaN, inf, zero and negative cells, cut lines, BOM, trailing blank lines, CR CR LF, a header row mid-file, another asset's or timeframe's file, an older run's copy, emptied files, future rows and date formats. 319 stopped at `check_fresh` (24), `check_candles` (273) or the stack check (22, held). The 18 that passed every check were: 13 line-end toggles (LF↔CRLF), which published feeds identical to an undamaged run; `series_through.json` deleted, also identical; and 4 in-range value edits, which are out of scope. Page: the strict check, the ledger and chart rules and the Worker's conversion refused every cut, blank, duplicated, reordered or text-filled file, and every one with a cell or column missing (157 readings). CRLF, BOM, an extra column, a later-run example file and shuffled rows were accepted, and their figures equalled the file's.
- **3 Wrong content.** Page: another run's feed, ledger or chart, another asset's or timeframe's bars (named or renamed), the example served as a chart and a chart served as the example, and the feed served as the ledger or as trades. All were refused or drawn as unavailable (50); another run's ledger with an identical top-grade set was accepted with correct figures. Pipeline: another asset's or timeframe's file and older copies were all stopped or held.
- **4 Partial run.** 198 between-step damages to 18 dataset files (deleted, emptied, header only, cut, a row duplicated, a figure altered, an older copy; each made just after the step that writes the file, and again before `feed_live`), plus 4 to the seal manifest itself. Across the family, 149 runs were held, 83 failed closed and 23 were clean. Every clean one was correct: byte-identical older copies; `candle_check.json` changed before the seal starts (not reachable); step-outcome strings that mean success; repeated or reordered runs whose final run is whole; and the kill cases below. Steps killed part-way (refresh, grade, stack and cards at 30–95% of their run) were held. A killed extras step still published cards with extras withheld and its files deleted, as designed. A killed `feed_live` left the last clean feed and a log the next run accepts. Skipped steps, steps out of order, repeated steps and two interleaved runs were held or failed closed, or were byte-identical to a clean run. In the alert sequence (held, fail-closed, clean, clean), pending alerts were emitted exactly once and carried in their window, with none lost or duplicated. A run killed between the feed and its copy, or between the copy and the log, was rebuilt cleanly by the next run.
- **5 Timing.** Clock a day ahead or behind, and a run before today's candle exists: the job stopped. Scoring at 23:59:59 was clean. When the feed, stack, cards or grade crossed midnight, the run failed closed or was held. `feed_live` 1 h 59 min after refresh published; at 2 h 01 min and before the seal it failed closed. Replays of 1 Jan 00:20, 31 Dec 23:50, 29 Feb 00:00:00 and 1 Mar 23:59:59 were all clean and passed. Page: 4 h 59 min showed no note; 5 h 01, 3 days and 400 days showed the stale note on every tab. A page left open 5 h, 18 h or 3 days updated by itself. 23:50 → 00:05 showed the close note. A quiet market's example stood in only when fresh and clean, and went off when left open.
- **6 Delivery.** A feed cut at any point, an HTML error page, null, {} or [], trailing garbage, two copies joined, or a 503 arriving after 5 s read "Data unavailable". A slow feed, ledger, chart, example or lead-trader file read "Loading" in every area and on every tab, never "unavailable" or quiet. A chart file arriving after the member picked another setup was not drawn. A feed request that hangs reads "Loading the latest data…" with no timeout of its own (until the browser gives up): never quiet, never a figure.

## What I could not test, and why

- Real fetches from Coinbase and Kraken (no network): the Kraken cross-check only ran its "unavailable" path. I emulated `check_fresh` and `check_candles` under a clock shim because they read the wall clock.
- The real Cloudflare Workers (mirror timing, Access redirects) and GitHub concurrency, commit and push. I emulated the site Worker's routes and its CSV-to-JSON conversion; two runs at once were interleaved in one folder.
- Kills at an exact byte inside a write: kills are timing-based (30–95% of each step's measured run). `feed_live` runs in about 0.07 s, so its kills land before or around the write.
- Midnight and 1 January on the frozen states need candles consistent with the clock, so I ran them as replays, and as runs whose candle checks were done at 14:30.
- `trades.json` is 404 in the harness (accepted). I routed my own valid and damaged lead-trader files instead.

## C. The repo's own tests (run on copies)

| Test | Result |
|---|---|
| `RENDER_LIMIT=40 REJECT_LIMIT=10 tests/test_feed_damage.py current replay_1111` | 32/32 passed (12,577 and 12,566 damaged feeds: page and `feedcheck` agree) |
| `tests/test_seal.py` | 29/29 passed |
| `tests/test_page_timing.py` | 24/24 passed |

These tests do not cover:
- HTTP status failures per file and in combination.
- Hung requests.
- CSV damage passed through the Worker's conversion (blank lines become zero bars; CR CR LF).
- Files from another run, asset or timeframe beyond older chart files.
- Feeds produced by real held, fail-closed and extras-failed runs (they forge a held feed).
- Example-file damage beyond its loading state.
- Killed, skipped, repeated, out-of-order or interleaved steps.
- Clocks across midnight inside a run.
- The alert log through a held → fail-closed → clean sequence.
- Cross-field forgeries H1–H5 (the damage test changes one field at a time).
