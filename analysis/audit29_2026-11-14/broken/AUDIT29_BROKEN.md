# Audit 29c: breaking the ETHKROS member site and pipeline with damaged files

Independent damage audit, 14 Nov 2026. I wrote all the code myself. The only things I copied were the two frozen states, and the repo was not changed. This audit measures whether damage is caught. It produces no strategy return and no track record: the data has no exits, so it measures entry quality only. Details are in `all_checks.csv` (1,106 rows) and `disagreements.csv`.

## Top line

**5 distinct real-life disagreements (25 rows), 1 on the page and 4 in the pipeline. All are category (iii): damaged input used without being withheld. None of them shows a wrong printed figure, a placeholder or script error, wording that misstates the state, or anything that reads as a return. There is 1 hardening case, which is not counted.**

### Page level (Playwright; 383 states, each walked through every tab, picker button, the example switch and both chart modes)

| Family | Rule meant to catch it (index.html) | Tried | Got through |
|---|---|---|---|
| 1 MISSING | `get()` returns null when not ok; no feed: "Data unavailable"; ledger, chart, example and trades each say unavailable | 40 | 0 |
| 2 MALFORMED | `feedProblems` (schema plus crossCheck), `tradesProblems`, `parseCSV` plus `ledgerRowOk` plus the count/share match, `barsOk`/`stepsOk` | 209 | 0 |
| 3 WRONG CONTENT | chart file names the chart, ends no later than `generated_at`, last close is `price_now` (1e-6), entry bar is `entry_close`; ledger matches `grade_odds` | 27 | 0 |
| 5 TIMING | `staleNote` (more than 5 h, or the daily close has passed), checked every minute; auto example off when stale; `chartTok` | 19 | 0 |
| 6 DELIVERY | the same rules as 1 to 3, applied to files that are cut, empty, HTML, slow, or passed through the Worker's `csvToBars` | 73 | **1** |
| (Hardening) | crossCheck | 15 | 1 (not counted) |

### Pipeline level (each step run as daily.yml runs it, with CTZB_NOW and CTZB_STEP_OUTCOMES set from exit codes; 723 runs)

| Family | Rule meant to catch it | Tried | Got through |
|---|---|---|---|
| 1 MISSING | `history_problems` (missing file, lag); feed_live requires its files; seal "is missing"; `check_log` | 136 | **1** |
| 2 MALFORMED | `history_problems` (`_row_problems`, `_cut_short`, `_series_problems`, `_cells_problem`); seal sha | 284 | **4 rows (2 findings)** |
| 3 WRONG CONTENT | asset and timeframe tests, 2D-8D equal to the daily candles bucketed; seal sha; lag | 96 | **1 row (same finding as TIMING)** |
| 4 PARTIAL RUN | seal: order, "already ran", files changed, appeared or missing; `CTZB_STEP_OUTCOMES`; atomic writes | 155 | 0 |
| 5 TIMING | stack_live "today's bar is missing"; `seal.age_problem` (2 h, future); feedcheck day rules | 52 | **18 rows (1 finding)** |

### States tried and disagreements, by kind (real-life damage only)

| | States | (i) wrong figure | (ii) placeholder, error or blank | (iii) damaged input used | (iv) wording misstates state | (v) reads as return or trade |
|---|---|---|---|---|---|---|
| Page | 383 | 0 | 0 | 1 | 0 | 0 |
| Pipeline | 723 | 0 | 0 | 4 (24 rows) | 0 | 0 |

## Every disagreement

| # | Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|---|
| D1 | page | r0414 | `candles_btc_2d.csv` cut one character short in its last cell (73736.44 became 73736.4), so the Worker's `csvToBars` accepts it | Chart drawn for BTC 2D (live 21 Sep signal and forming 16 Nov card). Last candle is 4 cents low; no printed figure uses it | "Chart data unavailable" (rule 4: the file must close at the card's price) | `index.html` l.939 (and l.946): the match uses a relative tolerance of 1e-6, about 7 cents at BTC prices, so dropping the cents digit passes. ETH files are caught (0.002 tolerance) |
| D2 | pipeline | cur, r0414 | `ETH_4H.csv`: 199 consecutive recent bars (33 days) deleted, last bar kept | Run clean, feed published (figures equal the clean run) | Job stops: a gap is structural damage | `fetch.py` l.304: a 4H/12H file passes when 99% of steps are one bar, and a 33-day hole is one off-step pair. `check_candles.structural` checks only prices on the last 540 4H bars. No scoring step reads 4H, so no figure changes |
| D3 | pipeline | cur, r0414 | A row dated tomorrow (or two days ahead) appended to the funding, long/short, open-interest or BTC put/call series. Same for a newer run's funding copy | Run clean, published (figures unchanged in all 18 rows) | Held back: a series row after the run's day is a damaged or wrong file | `fetch.py` `_series_problems` (lag test l.259) and the funding block (l.337) test only "no more than N days **behind** today". Nothing rejects a day **after** today. Real life: a source dating a row ahead, or a series newer than the clock |
| D4 | pipeline | cur, r0414 | A blank line inside `ETH_funding_daily.csv` | Run clean, published (figures unchanged) | Stop or held: a blank row is a damaged file | `history_problems` and `_series_problems` read with `csv.DictReader`, which skips blank lines. A blank line in a **candle** file also passes `check_candles`, but `engine.load` then crashes in refresh and the run is held (safe) |
| D5 | pipeline | replays 12 to 13 Nov | Feed file lost, and the alert log lost its last row, between two runs | Next clean run accepted the log and re-emitted `ETH-2D-2026-11-16:vanished` as new (emitted_at 20:14 changed to 04:14 the next day) | Fail closed, or rebuild without emitting the alert again | `feed_live.py` `check_log` l.169-174: with no readable previous feed, an existing log is accepted as it is (FEED_SPEC documents this). It needs two files damaged at once. The sender's alert_id dedupe would stop a second message |

**Hardening (not counted):** a hand-forged held feed that still carries `grade_odds` and `market_regime` shows the Past-signals table and "Market filter: on" while the card reads "Setups held back". This happens because the ledger check (`index.html` l.1276-1281) and `renderHeader` do not look at `cards_withheld`. feed_live never writes such a feed (a held feed empties both). The other 14 forged feeds were rejected or shown consistently: swapped cards, count +1, an example 1 cent off its file, sections from another run, reordered lists, ladder and era contradictions, and so on.

## What failed safe

- **Page (381 of 383; the other 2 are D1 and the hardening case):**
  - Every 404, 500, abort, empty, HTML or truncated feed read "Data unavailable" / "Feed unavailable". In those cases the ledger read "Past signals unavailable" and the example read "Data unavailable".
  - Cut, duplicated, renamed or other-run ledgers read "Past signals unavailable". LF line ends, a BOM and reversed rows showed the identical record.
  - Every chart file was handled: 404, 500, HTML, cut, empty, other asset, other timeframe, other run, last bar dropped, 9 bars, duplicate, gap, swap, zero, negative, h<c, string t, null c, a bar in the future, no "chart" key, and 25 CSV forms through the Worker. Each read "Chart data unavailable" with the card untouched, or was drawn identically when harmless (exponent numbers, extra columns, reordered columns, LF).
  - Example file damage read "couldn't be loaded".
  - All 12 damaged lead-trader shapes read "unavailable". Valid shapes showed their own values. Fields like `size_usd`, `contracts` and `notional` never appeared.
  - Clocks at +4 h 59 m, +5 h 01 m, +3 days, +3 years, 10 minutes and 1 day in the future, the next day at 00:01, and a page left open 6 h or 3 days all showed the right note on every tab, and the auto example went off.
  - A slow chart file did not overwrite a newer selection.
  - Markup in every text field was escaped (no script ran). NaN and 1e308 were rejected.
  - Boundaries showed the file's own values: 0, 100, exactly 70 versus 69.999999 on the edge bar, $0.01, $999,999,999.99, 1e9 rejected, day 0 and day 60, 2026-02-29 rejected, 2028-02-29 and 2027-01-01 shown, a card with 0 past signals.
- **Pipeline (699 of 723):**
  - Candle damage: 162 runs stopped at check_candles. These covered duplicate, swap, delete, cut, text, blank, zero, negative, NaN, inf, BOM, extra header, renamed or missing columns, other asset, other timeframe, HTML, ms times and future rows.
  - Between-step damage: every `datasets/` file, `stack_status.txt`, `candle_check.json`, `manifest.json`, `analysis/grade.json`, the regression baseline and a missing or cut page was held or fail-closed.
  - Every killed step (72 runs killed after their 1st, 3rd or 8th write or rename) was held. A killed extras step withheld extras with cards equal to the clean run, and its chart files went missing rather than stale. A killed feed step left the previous feed in place.
  - Order: steps run twice, out of order, without refresh, two runs interleaved, and runs crossing midnight before stack, cards or the feed were all held or fail-closed.
  - Clocks a day ahead or behind were held. A feed 2 h 01 m late, or before refresh, failed closed.
  - Outcome strings that were garbage, capitalised, missing regress, cancelled, or a duplicate key were held.
  - All datasets deleted, or replaced by the other run's copies, before a run: rebuilt identically.
  - Alerts: 13 sequences (held, fail-closed, log write failed, log cut, LF, feed deleted or truncated, repeated run, held across 24 h) logged each alert exactly once, and a clean feed carried each one. A duplicated or deleted log row failed closed. Note: it stays fail-closed until someone repairs it, while the page says "usually within the hour".
  - Replays at 2025-12-31 20:14 and 23:59:59, 2026-01-01 00:00 and 00:20, 2024-02-29, 2024-03-01 00:13, 2024-12-31 23:59:59, 2025-01-01, 2026-11-13 23:59:59 and 2023-12-31 all passed the strict check. Pages rendered clean, with every year-end chart drawn and the "daily close passed" note when viewed after midnight.
  - Not counted:
    - With `CTZB_STEP_OUTCOMES` missing or empty, a run is judged on `stack_status.txt` alone, as FEED_SPEC documents.
    - A negative value in `pcr_prem`, a column no step reads, is a value only.
    - A newer run's funding file moved one card through today's completed-day value, which is a source value. Its extra rows changed nothing.

## Part C: the repo's own tests

All three were run from a copy of `current`.

| Test | Result |
|---|---|
| `test_feed_damage.py` (RENDER_LIMIT=40, REJECT_LIMIT=10) | 31/31 PASS, 12 m 44 s |
| `test_seal.py` | 23/23 PASS |
| `test_page_timing.py` | 16/16 PASS |

What these tests miss:
- **No forming card under damage.** The damage test's replay of 12 Nov, which its PASS line calls "a state with forming cards", prints "0 forming cards". `replay_at.sh` keeps the 12 Nov daily bar whole and does not cut `data/derivs` or `data/options`, so the replay's series run to 14 Nov. Its other state (today) has no forming card either, so no forming card is ever rendered under damage.
- **Single feed fields only.** It damages single feed fields but not delivery forms: cut mid-number, HTML at 200, BOM, concatenated feeds, slow files, or the Worker's CSV conversion, where D1 lives.
- **Cross-file runs only partly covered.** Feed, chart and ledger from different runs are covered only by the timing test's one "older run" chart.
- **No input files.** Series rows after today (D3), blank series lines (D4) and 4H gaps (D2) are not tested anywhere.
- **No lost feed with a cut log.** That combination (D5) is not in `test_feed_alerts.py`.

## What I could not test

- The Kraken cross-check (no network; stubbed as unreachable, as a real outage is) and `check_fresh.py` (real clock only; stack_live's today-bar check was tested instead).
- The live Cloudflare mirror, Worker routing and Access. Only the Worker's own `csvToBars` was run, through node.
- The dashboard sender's dedupe (alerts were judged from the feeds).
- git commit, rebase and push, and two genuinely concurrent GitHub runs (simulated as interleaved steps in one folder).
- fetch.py and fetch_derivs network behaviour. Their whole-or-nothing writes were assumed and the damage applied to the files.
- Viewport sizes other than 1440x900.
- The trades relay is 404 in this harness, so trades files were supplied directly.
