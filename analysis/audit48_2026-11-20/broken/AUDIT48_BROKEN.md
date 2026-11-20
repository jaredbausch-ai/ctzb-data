# Audit round 48 (auditor c): damage attack on the ETHKROS member site and pipeline

**Code:** frozen at 4d4069d. **States:** `a48/current` (20 Nov 2026) and `a48/replay_1111` (11 Nov 2026). Every case was run on copies; the repo was not touched.
**Independence:** I wrote all the code myself. I did not read the earlier audit folders or AUDIT_LOG.md.
**Scope:** this attacks the damage rules only. Like everything in the project it covers entry quality only; nothing here is a strategy return or a track record.

## Top line

**Real-life disagreements: 0, at both the page level and the pipeline level.** 821 checks in total: 783 counted cases, plus 38 forged hardening cases that are not counted.

| Family | Page: tried / got through | Pipeline: tried / got through |
|---|---|---|
| 1 Missing | 38 / 0 | 69 / 0 |
| 2 Malformed | 126 / 0 | 129 / 0 |
| 3 Wrong content | 108 / 0 | 41 / 0 |
| 4 Partial run | 16 / 0 | 61 / 0 |
| 5 Timing | 34 / 0 | 20 / 0 |
| 6 Delivery | 92 / 0 | 21 / 0 |
| Controls (valid but unusual files, undamaged runs) | 28 / 0 | n/a |
| **Total** | **442 / 0** | **341 / 0** |

States tried: the page on `current` (285 cases) and `replay_1111` (195), 19 of each state's cases forged, and the pipeline on `current` (252) and `replay_1111` (89).

Disagreements by kind, page and pipeline alike:

| Kind | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

None. `disagreements.csv` has a header only.

These rows did not match my expectation at first. I checked each one and none is a disagreement. All are recorded in `all_checks.csv` with the cause:

| Level / state | Case | What happened | Why it is not a disagreement |
|---|---|---|---|
| page / both | Viewer exactly 5 h after the feed | Stale warning shown | The Playwright clock keeps running after it is set, so the feed was 5 h plus about 1 s old when read. "Older than 5 hours" is the right verdict. |
| page / both | Markup in every text field | `${x}` appeared in the card text | The case itself put that text in the `sample` field. The page shows it escaped, exactly as the file holds it. No script ran (`window.__pwn` was never set). |
| pipeline / replay_1111 | ETH funding last row lost | Published | Replay artefact. The replay's `series_through.json` is dated 20 Nov, after the replay day, so it is skipped by design (FEED_SPEC). On `current` the same damage is held. |
| pipeline / replay_1111 | Clock at 23:59:59 | Published, figures equal to the undamaged run | Replay artefact. The replay keeps 11 Nov's 4H bars up to 20:00, so this was a valid, fresh run. |
| pipeline / replay_1111 | Ledger replaced by "the other run's" before stack or feed (2 cases) | Published | My mistake: the path pointed at the state's own file, so nothing was changed. |

My own harness also had two construction errors, both fixed and re-run before counting:
- The ledger and candle CSVs are written with CRLF line ends. My first "CRLF" variants were therefore CR CR LF. The page rightly refused them, and that variant is now a case of its own.
- The container restarted mid-batch (about 03:46 UTC). Batch 1 was resumed from 230 of 237 cases. I checked the results file for half-written lines and re-ran only the missing cases and the CSV cases whose construction had changed.

## The rule that guards each family, and what failed safe

| Family | Rule attacked | Failed safe (outcomes) |
|---|---|---|
| 1 Missing | Page: any file that does not arrive reads "unavailable". Pipeline: `check_fresh`, `history_problems`, `rows_lost_problems`, the seal, missing datasets fail closed, and the alert-log record plus its second copy. | Page 38/38: feed 404/500/502/503/403 reads "Data unavailable"; ledger, chart, example and trades files read "unavailable". Pipeline: 21 stopped at check_candles, 3 at check_fresh, 20 held, 12 fail-closed. 6 harmless cases published figures equal to the undamaged run (for example `series_through.json` lost alone, or datasets/ emptied before refresh). |
| 2 Malformed | Page: `FEED_SCHEMA` with `crossCheck`, `parseCSV` (cut, cell count), `ledgerRowOk`, `barsOk`/`stepsOk`, and the worker's `csvToBars`. Pipeline: `history_problems` (header, cells, grid, whole lines, CR) and the seal. | Page 102 refused as expected. 24 valid variants (CRLF and LF, reordered or extra columns, BOM, rows reversed) shown with the file's own values. Pipeline: 75 stopped at check_candles, 18 held, 9 fail-closed. 24 harmless encodings (CRLF and LF swapped, spaces, quotes, exponent form, `.0` times on 4H/12H) published figures identical to the undamaged run. |
| 3 Wrong content | Page: the chart file must name its chart, be on its own steps, end no later than the feed and close at `price_now` / `entry_close` to the half cent; the ledger must match `grade_odds`; the example file must match the example card. Pipeline: asset, timeframe and bucketing checks, and seal hashes. | Page 104 refused: every other chart's file under each name, the other run's copy, an extra bar, feed and charts from different runs, a newer ledger. A ledger from the other run with identical top-grade rows was accepted and showed correct rows. Pipeline: 13 stopped, 14 held, 10 fail-closed. |
| 4 Partial run | Seal step order, "already ran" and file hashes; `CTZB_STEP_OUTCOMES` read strictly; extras clear their own files; the feed is written first, then the copy, then the log. | Each scoring step killed (SIGKILL) leads to held. Extras killed or cancelled leads to a clean feed with extras withheld and no extras file left. Steps swapped, run twice, or refresh re-run lead to held or fail-closed. Outcomes that say success while a step died lead to fail-closed. Two full runs at once on one checkout (4 staggers) lead to held. 12 alert-log scenarios: no alert lost, none emitted twice, and withheld runs log nothing. |
| 5 Timing | Freshness gates, the stack's today-bar check, seal age (2 h, not in the future), `scored_as_of` equal to the generated day; page stale/close notes on the viewer's clock. | Clock a day ahead or behind leads to stopped or held. A run straddling midnight leads to held or fail-closed. Feed 2h01m after refresh, or before it, leads to fail-closed. At 00:00:00 the figures equal the undamaged run. Page: 5h01m, 3 days, 2 years, midnight, and a page left open 6 h or across midnight all show the right note. A quiet feed that goes stale drops the example. |
| 6 Delivery | Strict checks; a CSV with no final line end is cut and refused; "Loading" until a file arrives; a stale chart request is not drawn. | Truncated, empty, HTML-page, UTF-16, gzip and doubled feeds read "Data unavailable". A hung feed or ledger stays on "Loading", never "unavailable" or "quiet". Slow feed, ledger, trades and chart files fill in when they arrive. |

## Hardening (not counted): hand-forged feeds where every field is valid but the fields contradict each other

19 forged per state. 14 are rejected by the strict check. These 5 are accepted and shown as written on both states, because the strict check has no rule for them:
- A card's `sample` text names a different count that contains the true count's digits (for example "all 115" with n = 15). The check is `sample.includes(String(past_trades))`.
- `rose10_within60d_pct` is 100 while the median best move is 3%.
- An ETH forming card's `price_now` differs from the ETH live card's `price_now` in the same feed. Only that card's chart is refused.
- `if_it_misses.up_first` is 0 while `median_peak_pct` is above 0.
- Both eras are at 100% while the card's never-fell-25.3% share is 0.

## Two-fault cases (recorded, not counted)

None found. One documented single-fault behaviour, consistent with FEED_SPEC:

**The feed step killed by SIGKILL or a timeout leaves the previous feed in place.** No fail-closed feed is written, because the `except` block never runs. The workflow then commits the new datasets beside the old feed. The old feed carries its honest `generated_at` and gets the stale warning after 5 h. Its chart files from the new run are refused for price mismatch: "feed other run, charts this run" reads "Chart data unavailable" on every chart.

## What I could not test, and why

- `fetch.py` and the Kraken cross-check, live. There is no network here; Kraken was stubbed as unreachable, which the code treats as not failing.
- The Cloudflare Workers and the mirror. I emulated the site worker's `csvToBars` and status mapping in Python rather than running it.
- The GitHub Actions concurrency group, the gate, and git push or rebase between runs.
- The relay that produces the live lead-trader file. Only file shapes were tested; `trades.json` is 404 in this harness.
- The 1 January rollover. Neither frozen state has a scored day near a year end; the repo's `test_year_end.py` covers this.
- Viewer device clocks that are wrong. This is listed as known and accepted.

## C. The repo's own tests (run on a copy of `current`)

| Test | Result |
|---|---|
| `tests/test_seal.py` | 29/29 passed |
| `tests/test_page_timing.py` | 24/24 passed |
| `tests/test_feed_damage.py` with `RENDER_LIMIT=40 REJECT_LIMIT=10` | 33/33 passed |

What the repo's tests do not cover, and this audit added:
- Chart files swapped across every asset and timeframe.
- Feed, ledger and charts mixed across runs.
- Live alert-log faults across runs: killed between feed, copy and log; a held or fail-closed run in between; two feed steps at once.
- Two full runs at once.
- Input encodings that must score identically.
- Clocks straddling midnight per step.
- Strict-check gaps for cross-section contradictions. Their forged feeds damage one field at a time, so they never test those.

Files are in `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit48c/`:
- `all_checks.csv`: 821 rows.
- `disagreements.csv`: empty.
- Code: `harness.py`, `pagecases*.py`, `check.py`, `pipe/*.py`.
- Raw results: `res_*.csv`, `pipe/res_*.jsonl`.
- `progress.log`.
