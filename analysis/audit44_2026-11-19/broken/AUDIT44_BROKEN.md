# Audit 44c: damaged, missing, inconsistent and tampered files

Code frozen at 056aaaf (states `a44/replay_1111` and `a44/current`). Independent harness, all code in this folder. Nothing in the repo was edited.
Everything here measures entry quality only. The feed holds computed signals, not fills, and nothing in it is a strategy return or a track record.

## Top line

**Counted disagreements (real-life damage): 1.** It is on the pipeline side and shows in both states: one fault, type (iii). The page had none.
Hardening (not counted): 7 of 16 hand-forged feeds were accepted. Two-fault (recorded, not counted): 1.

| Family | Rule meant to catch it | Page: tried / got through | Pipeline: tried / got through |
|---|---|---|---|
| 1 MISSING | `get()` returns null on any non-OK or network error, so the area reads unavailable; check_candles/stack `history_problems` report missing files; seal "missing"; feed_live requires its files; check_log needs a record | 40 / 0 | 139 / 0 |
| 2 MALFORMED | Strict check (FEED_SCHEMA + crossCheck); parseCSV `dropped`/`cut`; `barsOk`/`stepsOk`; Worker `csvToBars`; `history_problems` (header, cells, grid, order, whole lines, CR); series range rules | 142 / 0 | 1856 / **1** |
| 3 WRONG CONTENT | Chart `price_now`/`entry_close` to the half cent plus `stepsOk`; ledger rows must match `grade_odds`; example entry close; ETH/BTC ratio; resample equality; seal hashes | 46 / 0 | 38 / 0 |
| 4 PARTIAL RUN | Seal (order, once, unchanged files); CTZB_STEP_OUTCOMES gating; stack_status FAILED; extras files deleted when extras did not succeed | 8 / 0 | 184 / 0 |
| 5 TIMING | `staleNote` (5 h, 00:00 UTC close, page left open); auto-example off when stale; seal age ≤ 2 h and not in the future; stack "today's bar"; `scored_as_of` = generated day | 22 / 0 | 14 / 0 |
| 6 DELIVERY | As 1 and 2, plus the `chartTok` check that only the latest chart request draws, and every area shows "Loading" until its file arrives | 86 / 0 | n/a |
| Lead-trader file (valid shapes and damaged) | `tradesProblems` (schema, newest first, ≤ 5 min ahead, no repeats) | 48 / 0 | n/a |

Pipeline MALFORMED includes 1,536 input damages per state put through the two input gates: 964 were caught, and the 572 not caught were run whole in 14 grouped runs per state. These rows count in all_checks.csv: 2,642 in total. Another 27 rows looked like disagreements but were harness or expectation errors. Each is explained in `fixups.json`, and the `cause` column says so.

### States tried and disagreements (real-life damage only)

| Level | States | Cases | (i) wrong figure | (ii) placeholder / script error / blank | (iii) damaged input scored or published | (iv) misstated state | (v) reads as a return or record |
|---|---|---|---|---|---|---|---|
| Page | replay_1111, current | 392 counted | 0 | 0 | 0 | 0 | 0 |
| Pipeline | replay_1111, current | 278 whole-run + 1,956 input | 0 | 0 | **1** (seen in both states) | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| pipeline | current and replay_1111 | `data/derivs/ETH_funding_daily.csv` lost its last whole row (the file cut at a row boundary, so it ends on the day before the run) | Clean feed, scored. The ETH forming cards changed: ETH 1D 11-21 went from sample 27 / no confirmations to 17 / "funding at or above its 90-day median"; ETH 2D 11-20 from 15 / exact match to 27 / same-grade pool, with every figure different; ETH 3D lost its FUND confirmation. Both states behave the same way. | Held, or the same figures as the whole file | `fetch.py:238` `MAX_LAG_DAYS["funding"] = 1` and `fetch.py:420` accept a series one day behind. `stack_live.py:231-236` `funding_at` then reads the last known day as today's. This loss cannot be told apart from the normal 0-1 day lag the spec allows (FEED_SPEC "Inputs checked before scoring"; `tests/test_cut_files.py` docstring). It is counted because a file cut short is real-life damage and the cards change. The BTC funding, long/short, OI and put/call files with their last row lost published identical figures. |

## Hardening (not counted): hand-forged feeds, every field valid, the fields contradicting each other

All 16 were on the current state. **Rejected ("Data unavailable"): 4**: odds_fade bar 60 against the top-level 70; grade_odds count +1 (the miss counts no longer match); a lost live signal marked intact; past_paths n from another run.
**Shown as the file says, and consistent: 5**: from-entry exact 69.999999 shown as 70 (the edge is decided on the exact share); every share 100; day 0 and 60; low_day = confirms_on; price_now 0.01 (that chart reads unavailable).
**Accepted although the fields contradict each other: 7.**

| Forged contradiction | What the page shows | Why no rule catches it |
|---|---|---|
| A forming card and a live signal share one signal_id (both dated today) | Both listed, the same setup twice | Duplicate ids are checked within `cards` and within `open_signals`, not across the two (index.html, crossCheck) |
| `bars_to_confirm` 1 on a card confirming 4 days later | "if it closes above about $X (an estimate until the current bar closes)" | No rule ties bars_to_confirm to confirms_on and the feed date |
| `must_close_above` 10 × `price_now` | That price as the confirmation level | No rule ties the two |
| Two ETH cards with different `price_now` (ETH 1D raised 20%) | The card shows the forged price; its chart reads unavailable (close no longer matches); the other ETH charts draw | No rule across cards |
| `sample` says "127 past signals" while past_trades = 27 | "from all 127 past ETH 2D signals" beside "n 27" | `c.sample.includes(String(c.past_trades))` matches "27" inside "127" (index.html:430) |
| Example card graded C | Shown as the worked top-grade example | The example's grade is not checked; `cardExample` sets `top: true` |
| `market_regime` Bearish with forming cards present | "Market filter: off" above forming setups | No rule ties regime to the cards (a card's gate is read at its trough, so this can be legitimate) |

## Two-fault (recorded, not counted)

| Faults | Result |
|---|---|
| (1) `tests/regression.py` fails (baseline deleted) **and** (2) CTZB_STEP_OUTCOMES says `regress=success` | Published clean. Regression is the only gating step that leaves nothing the seal or stack_status records, so feed_live can only take the reported outcome. Either fault alone is safe: with regress reported `failure` the feed is held. A CTZB_STEP_OUTCOMES that is set but empty is read as a hand run (documented); that is the same exposure. |

## What failed safe, by family (counts are cases that read unavailable, held back, fail-closed or job-stopped, or that showed the right figures)

- **MISSING (page 40, pipeline 139):** feed 404/500/502/abort, then "Data unavailable", header "Feed unavailable", ledger unavailable, Chart tab "Data unavailable". Ledger, chart and example 404/502/abort each read unavailable in their own area only. Pipeline: every candle, series and dataset file deleted (stopped or held); the page file deleted, or its schema markers cut (fail-closed); baseline JSON deleted (held); candle_check.json lost (fail-closed); alert log deleted or emptied (restored from the copy, clean, nothing re-emitted); previous feed lost (clean); feed and copy both lost (fail-closed, as documented).
- **MALFORMED (page 142, pipeline 1,856):** the feed cut at 10%, 50%, −2 bytes; doubled; UTF-16; NUL bytes; HTML; a ledger file or a lead-trader file served as the feed (all down). A feed that is still valid JSON (CRLF, BOM, minified, extra whitespace, exponent forms, a duplicate key, 3,000-deep junk, markup or RTL characters in samples, 40k-character sample) showed exactly its own figures, with markup shown as text. Ledger: a row cut, rows dropped at a row boundary, an A+ row dropped or duplicated, a column lost, an extra cell, a blank cell, CR CR LF, a trailing blank line (all unavailable). A header repeated in the middle, rows reversed, a non-top-grade row lost, a BOM: right rows. Chart files: reversed, a bar lost or duplicated, 9 bars, zero price, high below close, string numbers, ms times, a future bar (all unavailable). Inputs: every damage to rows, order, gaps, duplicates, truncation, columns, text/blank/negative/zero/NaN cells, CR, BOM, blank lines, extra headers, grid, ms times, on all 14 candle files and 7 series, was caught. What got past the gates published identical figures, with these exceptions: time written `N.0` was held; the ETH funding last row is the finding above. The gates also let these through with no effect on the feed: CRLF, spaces after commas, exponent closes, every unread per-market column set −5, a dropped last column, a renamed unread column, a blank `pcr_amt` (mid or last), and lost last rows of the other six series.
- **WRONG CONTENT (page 46, pipeline 38):** another asset's or timeframe's chart under a chart's name (relabelled, as the Worker stamps it), another run's chart files, an example with an off entry close, entry index or bars (all unavailable). Another run's ledger: its top-grade rows are identical, so right figures. Another run's feed: stale note, its charts unavailable. Pipeline: other-run copies of datasets between steps (seal: held or fail-closed); another run's alert log, previous feed or copy (restored or fail-closed, no alert lost or re-dated).
- **PARTIAL RUN (page 8, pipeline 184):** held and fail-closed feeds read "Setups held back", "Market filter: unavailable" and ledger unavailable, never a quiet market. An extras failure kept the cards and read unavailable on the charts and the cloud. Pipeline: every dataset deleted, emptied, header-only, cut, missing its last row, duplicated, missing a column, altered or swapped for an older copy after each step (held or fail-closed); steps out of order, repeated, skipped or killed mid-write; two runs interleaved (held or fail-closed); a killed extras (cards publish, extras withheld, no extras file left). Wrong or garbled outcomes (semicolons, capitals, cancelled): held. Alert sequence: a held run, then a fail-closed run, then clean runs. Nothing was logged until the clean run, which emitted exactly the direct run's 4 alerts once; the next run carried them. No duplicates, nothing re-dated.
- **TIMING (page 22, pipeline 14):** 4h59 shows no note and 5h01 shows the stale note; 3 days and 3 years; feed 5 min ahead; page left open across 5 h ("this page has been open") and across 00:00 UTC; a quiet market where the example stands in only while fresh and goes off when stale. Pipeline: clock a day ahead or behind (held); feed after midnight (fail-closed); stack after midnight (held); seal 1h59 (clean), 2h01 or 1 min in the future (fail-closed).
- **DELIVERY (page 86):** a slow feed, ledger, example or lead-trader file reads "Loading", then the right file. A slow chart file picked away from never draws over the newer pick.

## Could not test, and why

- check_candles' Kraken comparison and check_fresh against a live exchange: no network. Kraken was stubbed as unreachable, and check_fresh's own `time.time()` was not used; stack's "today's bar" covers the same ground.
- Workers: the mirror's 15-minute pull and partial mirror states were simulated only as file mixes served to the page. The Telegram sender and the health monitor were not run.
- 1 January and 29 February: not run, for lack of time. A replay at 2026-01-01 or 2024-02-29 from `a44/current` is possible with tests/replay_at.sh. The 70-bar chart files of both states hold no 1 January bar, so the page's year-end rule (`stepsOk`, `barNextOpen`) was not exercised. The midnight logic was tested on 19/20 Nov (page and pipeline).
- A run truly killed by a signal: simulated as the step's files half-written with its seal record missing.

## C. The repo's own tests (run on a copy of `a44/current`)

| Test | Result |
|---|---|
| `tests/test_seal.py` | 29/29 pass |
| `tests/test_page_timing.py` | 24/24 pass |
| `RENDER_LIMIT=40 REJECT_LIMIT=10 tests/test_feed_damage.py` | 33/33 pass (9,499 damaged feeds, verdicts agree) |

Gaps these tests do not cover:
- Damage to the derivative series that keeps a file whole but one day shorter, and its effect on the cards (the finding above).
- Contradictions across lists: a duplicate id between `cards` and `open_signals`, or a sample digit inside a larger number.
- Extras reported `skipped` when the step did run: this was tested here and handled. Extras that never ran fails the feed closed (`order-extras-skipped`), which is safe but stricter than the extras-only withholding the spec describes for "failure".
- The regression step's outcome as the only evidence for it (two-fault above).

## Notes on this audit

- A harness bug (an empty step list re-ran the whole chain) voided the first whole-run pass. All 136 + 136 whole-run cases were run again after the fix. Every row in the CSVs comes from the second pass.
- Files: `all_checks.csv` (2,642 rows; fixups applied), `disagreements.csv` (each row with its section), `progress.log`. The harness is `ph.py`, `judge.py`, `batch1-3.py`, `batch2b.py`, `inputs.py`, `triage.py`, `pipe.py`, `pipe_cases.py`, `alertseq.py` and `twofault.py`.
