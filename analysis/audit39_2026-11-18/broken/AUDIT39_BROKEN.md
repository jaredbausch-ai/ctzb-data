# Audit 39 (c): breaking the member site and its pipeline with damaged files

Independent damage audit, 18 Nov 2026. I wrote all the code in this folder myself. States: `a39/current` (data to 18 Nov, built 15:16Z) and `a39/replay_1111`, both copied. I also made four replays with the state's own `tests/replay_at.sh`: 1 Jan 2026 04:14, 1 Jan 2026 00:13, 31 Dec 2025 23:59:59 and 29 Feb 2024. Nothing in the repo was edited.

Scope reminder: this work measures **entry quality only**. Nothing here is a strategy return or a track record. Every figure on the page is a computed signal, not a fill.

## Top line

**One case got through (counted): partial-run family, pipeline, alert log. I'm not sure it can happen in real life (reason below). There were 0 counted cases at page level and 0 hardening cases got through.**

### Cases tried / got through, per family

| Family | Page: tried | Page: got through | Pipeline: tried | Pipeline: got through |
|---|---|---|---|---|
| 1 Missing | 21 | 0 | 107 | 0 |
| 2 Malformed | 85 | 0 | 565 | 0 |
| 3 Wrong content | 32 | 0 | 74 | 0 |
| 4 Partial run | 12 | 0 | 77 | **1** |
| 5 Timing | 31 | 0 | 9 | 0 |
| 6 Delivery | 55 (+5 slow-file scenarios) | 0 | 3 | 0 |
| Hardening (not counted) | 61 | 0 | – | – |

Other runs: 2 undamaged page baselines, 2 repeated-run alert sequences and 3 two-runs-at-once interleavings, all fine. Total: 1,134 rows in `all_checks.csv`.

### States tried and disagreements (real-life damage only)

| Level | States tried | (i) wrong or unsupported figure | (ii) placeholder, script error or blank area | (iii) damaged input scored or published | (iv) wording misstates the state | (v) reads as a return, trade or record |
|---|---|---|---|---|---|---|
| Page | 296 (current 202, 1111 85, replays 12; slow-file scenarios included) | 0 | 0 | 0 | 0 | 0 |
| Pipeline | 838 (823 single runs, 12 seven-day alert sequences, 3 two-run interleavings) | 0 | 0 | 1 (an alert emitted twice) | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| pipeline | daily runs 12→18 Nov 2026, starting from replay_1111 with its log trimmed to 11 Nov, data cut daily from current | 15 Nov run: `feed_live.py` writes the feed (6 new forming alerts) and the second copy, then dies before writing `feed/alert_log.csv`. Before the 16 Nov run, `feed/ctzb_feed.json` alone is the 14 Nov run's copy. | The 16 Nov feed re-emits all 6 alert_ids (BTC/ETH 1D-2026-11-17, 2D-2026-11-20 and 3D-2026-11-23, forming) with emitted_at 2026-11-16T04:14Z. The 15 Nov feed had already sent them at 2026-11-15T04:14Z, and the log records the later time. | Fail closed, or rebuild the log from the second copy (which holds the 6 rows). No alert_id emitted twice. | `feed_live.py:228-229`: `check_log` returns as soon as the log matches the previous feed's `alert_log` record, without reading `feed/alert_log_backup.csv`, even though the copy records more than the log. `pending_alerts` (`:313-329`) then treats the 6 as new and `:494-498` emits them again with a new emitted_at. |

**Whether it is real life (unsure, so counted):** it needs two faults in a row. First, the feed step is killed between writing the copy and writing the log. Second, only the feed file is reverted to the previous run's copy ("some files from this run and some from the last"). The variant where the copy is reverted too (v11: feed, copy and log all at the previous run's state) is the documented "rollback of feed/" exception and is not counted, because no file shows that the 15 Nov run happened. In v10 the copy does show it.

## What failed safe, by family

| Family | Rule attacked | Result |
|---|---|---|
| 1 Missing | Page: any file that doesn't arrive reads unavailable. Pipeline: check_fresh / `history_problems`, the seal, `feed_live`'s required files, alert-log copy | Feed 404/500/503 or network error read "Data unavailable / Feed unavailable" with no figure. Ledger, example, each chart file and the lead trader read unavailable while everything else stayed correct. All 14 candle files and the 7 daily series deleted or emptied stopped the job at the candle check. A dataset deleted at any step boundary was held or failed closed. Losing the log, the copy or the feed (one at a time, or feed + log cut) recovered correctly. Losing both log and copy, or feed and copy, failed closed. |
| 2 Malformed | Strict check, ledger/chart/example/lead-trader checks, worker `csvToBars`, `history_problems` | Tried: 41 damage kinds × 8 candle files (11 kinds on the other 6), 20 kinds × 3 series files (7 on 4 more), and 8 kinds × 4-7 datasets at each of 6 step boundaries. Every one stopped, held or failed closed, or (for no-op encodings: CRLF, leading space, quoted cells, float times on 4H/12H, an unread market column dropped) published figures byte-equal to the clean reference. On the page: a feed cut at 0-99.9% of its length, UTF-16, NUL-padded, `null`/`{}`/`[]` all read "Data unavailable". Ledger rows cut, blank, duplicated or missing a column, a NUL-padded ledger and an HTML page read "Past signals unavailable". All 22 candle-CSV damages × 2 charts were refused or drew identical bars. |
| 3 Wrong content | Chart name, steps, last close = `price_now`, entry close; ledger counts; example vs card; seal hashes | Another asset's or timeframe's chart file under a name (8 pairs), another run's charts, ledger or feed, an older or newer run's ledger, the feed served as ledger or trades, the ETH 2D file as the example: all refused or unavailable. Other assets' or timeframes' candle and series files and older runs' datasets between steps: stopped, held or failed closed. |
| 4 Partial run | Seal (order, repeats, hashes, age), strict outcomes, extras clean-up, alert carry | 7 orderings, 7 kills, 14 outcome strings, 3 two-runs-at-once interleavings and 11 alert sequences: all held or failed closed, or clean with the extras withheld when extras failed. In the alert sequences, held, fail-closed and repeated runs lost or duplicated no alert, apart from the v10 case above. Real held, fail-closed, extras-failed and typo-outcome feeds read "Setups held back" (or chart unavailable) on both states. |
| 5 Timing | Stale note, close note, scored_as_of = feed day, seal age, today's bar | Viewer at 4.9h / 5.1h / 26h / 72h / 400 days, 3 min and 1 day in the future, after 00:00, page open 5h, 3 days and across the close: right note each time. Pipeline: clock a day ahead or behind stopped the job. Feed after midnight, a 3h-old or future seal, and stack after midnight all held or failed closed. Runs at 00:00:00 and 23:59:59 were clean and correct. Replays at the year end and 29 Feb read correctly. |
| 6 Delivery | Strict checks, cut-short CSVs, Loading states, tokened chart loads | Slow feed, ledger, example, charts and lead trader, and every file held back: "Loading" on every tab, never blank or unavailable, then the right figures. A slow chart file that arrived after the member switched setups was not drawn. HTML error pages, empty bodies and truncated files read unavailable. |
| Hardening (not counted) | Cross-field rules | Script/HTML in every text field (escaped, no execution), 50k-character unicode, exponent forms, 1e308, duplicate keys, 5,000-deep junk, prices 0.01 and 999,999,999.99, edge 69.999999 vs 70, 29 Feb 2024 / 2023, a card on the wrong signal, a duplicated grade row, misses vs odds, eras not adding up, days_elapsed off by one, rose10 with best 9.9%, quiet market fresh / old / open 5h (the example goes off), 11 malformed lead-trader shapes: all handled. Dollar size, contracts and balance fields in a trade are never shown. No page text reads as a return, a trade taken or a track record. |

The repo's own tests (on a copy of current) all pass:
- `test_seal.py`: 29/29
- `test_page_timing.py`: 24/24
- `test_feed_damage.py` with RENDER_LIMIT=40 REJECT_LIMIT=10: 33/33

Gaps:
- None of them runs more than one pipeline run in a row, so none covers the alert log across a killed feed step plus a reverted feed (the case above).
- `test_feed_damage` damages single feed fields. It does not test HTTP-level delivery (UTF-16, NUL padding, two feeds in one file), wrong-run combinations (feed vs charts vs ledger) or the replay boundaries.

## Not counted, with reason

These are in `all_checks.csv`.

| Case | Why not counted |
|---|---|
| Feed replaced by the 1111 state's feed: the log accepted 2 "vanished" rows | Replay artefact. The 1111 log holds rows from 18 Nov, so its record equals today's log plus its own alerts. A real older feed's log is a prefix of today's and fails closed (o:log_older, alert v9). |
| BTC put/call file with an unread column dropped, or 1e9 in an unread cell | No figure changed. `fetch_pcr` writes fixed columns whole. |
| Outcome string with a duplicate key (`stack=failure` then `stack=success`) | The workflow string has each key once, and the stack really succeeded. |
| CRLF or float times in the 1D-8D files: scoring crashed, so held rather than published | Failed safe. |

## Could not test

- The Kraken cross-check (no network; it ran as "unavailable").
- `fetch.py`, `fetch_derivs.py` and `fetch_pcr.py` against a live exchange: I tested only their output files.
- The real Cloudflare Workers (mirror, site, trades relay). I replicated `csvToBars` in Python.
- Git commit and push races between runs.
- The 9 BTC 8D middle-row damages (the file is shorter than my row index). The same damages ran on 7 other candle files.
- The full-size `test_feed_damage.py`: I ran only the quick setting.

Files in this folder:
- `all_checks.csv` (every check)
- `disagreements.csv`
- `progress.log`
- `alert_v*.json` (sequence detail)
- `results_*.jsonl`
- the harness: `pipe.py`, `pipecases.py`, `pagehar.py`, `pagecases*.py`, `judge.py`, `alertseq.py`, `tworuns.py`, `clockshim.py`
