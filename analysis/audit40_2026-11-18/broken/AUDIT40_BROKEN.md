# Audit 40c: damage audit of the ETHKROS member page and pipeline

Run on 18 Nov 2026 by an independent auditor, on copies of the two frozen states (`a40/current`, `a40/replay_1111`) and on six states I replayed myself (31 Dec 2025 23:50, 1 Jan 2026 00:20, 29 Feb 2024, 1 Jan 2025, 6 Jan 2025). I wrote all the code (`page_harness.py`, `page_cases1-4.py`, `pipe_harness.py`, `pipe_cases.py`, `pipe_batch_a/c/d.py`, `alert_seq*.py`). I edited nothing in the repo.

This work measures how the site and pipeline handle damage. The data has no exits, so nothing here is a strategy return or a track record. Every signal is a computed signal, never a fill.

## Top line

**Result: 1,137 checks, 0 disagreements (real-life damage that got through).** The only flags were my own oracle or harness mistakes; each one is triaged in `all_checks.csv`.

| Family | Page: tried / got through | Pipeline: tried / got through |
|---|---|---|
| 1 Missing | 41 / 0 | 63 / 0 |
| 2 Malformed | 113 / 0 | 553 / 0 |
| 3 Wrong content | 40 / 0 | 27 / 0 |
| 4 Partial run | 4 / 0 | 92 / 0 (3 are alert-log sequences) |
| 5 Timing | 49 / 0 | 18 / 0 |
| 6 Delivery | 65 / 0 | 1 / 0 |
| Lead-trader file shapes | 22 / 0 | – |
| Unusual valid JSON / boundary values | 22 / 0 | – |
| Baselines | 5 | 1 |
| Hardening (not counted) | 18 forged feeds (21 rows marked hardening) | – |

States tried:

- **Page level:** 379 served states.
- **Pipeline level:** 755 runs. 224 stopped at the fetch checks, 389 failed closed and 37 were held. 98 published a clean feed whose figures equal the undamaged run. 4 were runs with extras failed, which publish the cards with extras withheld, as designed. 3 were alert-log sequences.

Disagreements (real-life damage only):

| | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

None. `disagreements.csv` has the header only.

## The general rule per family, and what failed safe

| Family | Rule attacked (code) | Failed safe |
|---|---|---|
| 1 Missing | **Page:** `get()` returns null on a non-OK status or a network error. That gives "Data unavailable" / "Feed unavailable", `ledgerOk` false or a blank chart with its message. **Pipeline:** `history_problems` names missing files; `feed_live` raises when a datasets file is gone; the seal flags "is missing"; `check_log` fails closed with no record. | **Page:** 404, 500, 503, dropped connection, 200-empty and HTML-200 on every file; all files at once; every chart file at once. **Pipeline:** every candle, series and datasets file deleted; manifest, page file, `grade.json`, regression baseline, PRETRADE, `grokpack.json` and `keep.json` lost; alert log, backup and previous feed lost alone and in pairs. All stopped, held or failed closed. A missing backup alone was rewritten. |
| 2 Malformed | **Page:** `FEED_SCHEMA` + `crossCheck`; `parseCSV` (dropped/cut) + `ledgerRowOk`; the worker's `csvToBars` + `barsOk`/`stepsOk`. **Pipeline:** `_file_problem`, the exact header, `_row_problems`, `_cells_problem`, and the seal hashes. | 23 kinds of row/cell/encoding damage on 6 candle files (incl. 4H/12H) and 4 series; 9 kinds on all 40 datasets files between cards and feed; 28 kinds on chart CSVs through the worker conversion; 24 kinds on the ledger. |
| 3 Wrong content | **Page:** the chart file must name its chart, close at `price_now` / `entry_close` to the half cent and end by `generated_at`. The ledger must match `grade_odds` per asset. The example must match its date and entry close. **Pipeline:** 2D-8D files must equal the daily candles bucketed; the ETH/BTC close ratio; intraday last close within 25%; market columns; the seal and lag checks. | Another asset's or timeframe's file under the name; files swapped in pairs; the other run's feed, ledger or charts (every combination); feed, ledger, example and charts served under each other's names. Every one read unavailable or stopped the run. |
| 4 Partial run | The seal (order, repeats, changed / appeared / missing files, age); `CTZB_STEP_OUTCOMES` gating; `fail_closed`; the alert-log record and backup. | Each scoring step killed part-way; steps repeated, skipped or out of order; two interleaved runs (both held); 9 kinds of wrong outcomes env; extras failed / cancelled (cards publish, extras withheld, extras files deleted); 10 manifest damages; alert-log damage and held/clean sequences. No alert was lost or re-stamped. 3 real new events were emitted once after a hold, the same as a direct clean run. |
| 5 Timing | **Pipeline:** `check_fresh`; stack's today's-bar check; seal age 2 h; the strict check (`scored_as_of` = `generated_at`'s day). **Page:** `staleNote`; the `chartTok` race guard; the loading states. | **Pipeline:** steps split across midnight; feed_live at 00:00:30 after scoring at 23:59:59; clocks a day ahead or behind; replays at year end, 1 Jan and 29 Feb. **Page:** viewer at 4h59 / 5h / 3 years / a day behind; page left open 6 h and 3 days; across midnight and 1 Jan; quiet market fresh, stale and left open (the example goes off); slow feed, ledger, trades, example and every file; slow-chart races (3). |
| 6 Delivery | **Page:** `r.json()` failure; `out.cut`; the worker's line-end check; the example checks. | Feed cut at 8 points; ledger cut at 5 points and at line ends; chart JSON cut; UTF-16; NUL bytes; HTML error pages with status 200. |

**Hardening (not counted).** 18 forged feeds, of which 12 were rejected or handled as I expected. Accepted as designed:

- Eras shifted by one so they still add up.
- Rows in reverse order.
- A posting bar of 100.

Accepted, with these observations:

- `checks.failed_steps` naming a step in a clean feed is accepted. The page does not read it.
- A forged clean feed whose example card's entry close is a cent off the example file is accepted. Only the example chart refuses it.

Lead-trader files (12 valid shapes, 16 damaged): extra `size_usd` / `contracts` fields are never shown, and every damaged shape read "unavailable".

**Not counted, noted.** The figures are right in all of these:

- A ledger with an extra header row, or with a column dropped, added or reordered, is shown when the top-grade rows are untouched.
- Unread columns of the series files can be dropped, renamed, or hold a negative or zero value without stopping the run.
- A runner clock 19 h behind on the same date publishes the true figures, with an early `generated_at`.
- A hold followed by a clean run carries alerts older than 24 h. This is by design; the sender dedups.

## Repo tests (part C)

| Test | Result |
|---|---|
| `tests/test_feed_damage.py` (quick pass: RENDER_LIMIT=40, REJECT_LIMIT=10) | 33/33 pass |
| `tests/test_seal.py` | 29/29 pass |
| `tests/test_page_timing.py` | 24/24 pass |

What `test_feed_damage.py` does not cover:

- **Delivery of the feed:** HTTP status, cut, encoding, slow files.
- **Combinations across files:** the feed from one run with the ledger or charts from another; every chart file wrong at once, checked on every selection.
- **Worker-converted CSV damage:** blank cells read as 0, BOM, hex.
- **The example file beyond a few edits**, year-end and leap-day states, and multi-field forgeries.
- **The pipeline.** The two other tests cover the seal and loading states, but not candle or series damage before `check_candles`, wrong `CTZB_STEP_OUTCOMES`, killed or interleaved runs, or alert logs carried through a hold with real new events.

## What I could not test, and why

- **`fetch.py` and the exchanges:** no network, so no Coinbase outage, hourly fallback or stale page. `check_fresh` and `check_candles` ran on the files, with the clock pinned and Kraken unreachable.
- **The Cloudflare Workers:** mirror timing, `ctzb-dashboard`'s send-once rule and Access. I emulated the site worker's CSV-to-JSON conversion in Python and served mixed-run files to stand in for a mirror caught mid-commit.
- **GitHub itself:** the concurrency group, step-timeout kill semantics (simulated with a process kill) and the commit step's `pull --rebase` and push.
- **Browsers:** Chromium only, delays up to 4 s, no real network throttling.
- **Full render pass of the repo damage test:** run with the quick limits (40 render / 10 reject), as the brief allows.

**Files:** `all_checks.csv` (1,137 rows: level, state, family, what was damaged, expected, shown, ok, hardening, cause, with the triage of each flag), `disagreements.csv` (empty), `progress.log`.
