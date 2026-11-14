# Audit 32c: damage audit of the ETHKROS member site and pipeline

Independent damage audit, 14 Nov 2026, repo at 4178753 (code identical in both frozen states). All code is my own
(`code/`). Nothing in the repo was edited. Scope: entry quality only. These are computed signals. There is no exit in
the data, so nothing here is a return, a fill or a track record.

## Top line

**Real-life damage: 2 distinct disagreements (6 rows in `disagreements.csv`). Hardening: 1 distinct (2 rows).**
2,375 checks in all (2,296 counted, 79 hardening). Both counted disagreements are low impact: no wrong figure reaches a member.

### Page level (Playwright; both states; every tab, every picker button, the example switch and both chart modes)

| Family | Cases tried | Got through |
|---|---|---|
| 1 MISSING | 62 | 0 |
| 2 MALFORMED (incl. unusual valid JSON) | 291 | 4 (1 distinct: ledger `dipBeforeHigh` blank) |
| 3 WRONG CONTENT | 58 | 0 |
| 4 PARTIAL RUN (page view of 39 pipeline outcomes) | 39 | 0 |
| 5 TIMING (clocks, slow files, page left open, midnight, 1 Jan, 29 Feb) | 44 | 0 |
| 6 DELIVERY | 24 | 0 |
| Hardening (hand-forged) | 77 | 0 |

### Pipeline level (steps run in daily.yml order, CTZB_NOW set, CTZB_STEP_OUTCOMES from exit codes)

| Family | Cases tried | Got through |
|---|---|---|
| 1 MISSING | 64 | 0 |
| 2 MALFORMED | 507 | 0 |
| 3 WRONG CONTENT | 53 | 0 |
| 4 PARTIAL RUN | 1,126 | 2 (1 distinct: alert re-emitted after three files lost) |
| 5 TIMING | 28 | 0 |
| 6 DELIVERY | n/a (page side) | – |
| Hardening | 2 | 2 (1 distinct) |

### Disagreements by kind (real-life only)

| Kind | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error, blank area | 0 | 0 |
| (iii) damaged input used, scored or published without being withheld | 1 (4 rows) | 1 (2 rows) |
| (iv) wording misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| page | current, replay_1111 | `ledger.csv`: one top-grade row's `dipBeforeHigh` cell blank (`''`), and separately a single space (`' '`). Cell count is unchanged. | Past signals used and shown: "137 signals · 20 missed +10%", all rows. The figures shown are right, because that column is never displayed. | "Past signals unavailable" (rule 3: every top-grade row well formed) | `docs/artifacts/member-site/index.html:551-557` `ledgerRowOk`: `dipBeforeHigh` is only compared through unary `+` (`+''` and `+' '` are 0). It is never checked with `numText`, unlike `bestMove`, `maxDrawdown` and `return60d`. Text (`'x1'`) is refused. |
| pipeline | current, replay_1111 | `feed/alert_log.csv` cut by 2 rows, **and** the previous `feed/ctzb_feed.json` lost, **and** `feed/alert_log_backup.csv` lost, all before the feed step | Clean feed published. The two "vanished" alerts whose log rows were lost are emitted again with a new `emitted_at` and logged again. | Fails closed, or no alert emitted twice | `feed_live.py:184-196` `check_log`: with no readable previous feed and no second copy there is no record, so the log on disk is accepted as it is. `pending_alerts` (`feed_live.py:282-298`) then treats the lost events as new. Counted because it is three file losses, each real-life on its own; needing all three at once makes it unlikely. The alert_id is unchanged, so a sender that de-duplicates by alert_id would not send it twice. |

Hardening (not counted): with `datasets/candle_check.json` replaced by the other run's copy between `check_candles` and
`refresh`, the feed publishes clean, but its `candle_check.kraken` status comes from that other run ("ok" where this run had
"unavailable"). No member-facing figure changes. It is not counted because within one job no other process writes between
those two steps.

The other 77 hand-forged page feeds did not get through: every contradiction a stated rule covers read "Data unavailable".
Six have no rule and were accepted, each showing its own field as given. Recorded only:
- a live signal with `edge_status` "lost" and no `edge_level_pct` reads "edge level (n/a)";
- a forming card with `bars_to_confirm` 1 that confirms days later;
- two cards on one chart;
- `market_regime` Bearish beside a live top-grade signal;
- posting bar 0 or 100;
- a card `price_now` far from its chart. The chart refuses to draw it.

## What failed safe, by family (counted cases)

| Family | Page: how it failed safe | Pipeline: outcome |
|---|---|---|
| 1 MISSING | 16 "Data unavailable", 10 "Past signals unavailable", 13 chart unavailable, 23 correct figures (e.g. trades 404/500 reads "unavailable") | 64 stop at the candle check |
| 2 MALFORMED | 59 "Data unavailable", 66 "Past signals unavailable", 88 chart or example unavailable, 74 correct figures (BOM, CRLF, minified, reordered or extra columns, unusual JSON) | 433 stop, 11 held, 63 clean and equal to the clean run (CRLF, LF, BOM, extra or reordered columns, trailing newline, put/call or funding blanks within the allowed lag) |
| 3 WRONG CONTENT | 51 "Data unavailable", 4 "Past signals unavailable", 53 chart unavailable (other asset, timeframe or run; example file under a chart name), 27 correct (feed from the other run shows its own figures, with a stale warning when old) | 51 stop, 2 equal |
| 4 PARTIAL RUN | page view of every distinct pipeline outcome: held and fail-closed feeds read "Setups held back", "Market filter: unavailable", past signals unavailable | 755 fail-closed, 183 held, 10 extras withheld (cards equal, extras files deleted), 4 stop, 172 equal (78 of them no-op damage, verified byte for byte by `code/noop.py`) |
| 5 TIMING | 42 correct (stale note at 5h01 and not at 4h59, hour count kept current while left open, daily-close note after 00:00 UTC, example switched off when stale, 1 Jan / 29 Feb per-year count correct), 2 chart unavailable (newer-run file) | 10 stop, 7 fail-closed (scoring 23:59:50 / feed 00:00:20, feed 2h01 late, clock stepped back), 4 held, 7 equal |
| 6 DELIVERY | 6 "Data unavailable" (HTML error page, gzip bytes, 502), 8 "Past signals unavailable" (HTML page, cut at a line end), 4 chart unavailable, 6 correct | n/a |

Alert log: no held, fail-closed or stopped run changed the alert log or consumed an alert. These pipeline flows ran
clean and delivered every alert once:
- held, then a clean run;
- fail-closed, then a clean run;
- stopped at the candle check, then a clean run;
- feed killed after publishing, then the next run;
- two clean runs back to back;
- the feed step run twice.

Two runs interleaved in one checkout failed closed or were held, in all three orders tried.


## Repo's own tests (stage C)

| Test | Result |
|---|---|
| `RENDER_LIMIT=40 REJECT_LIMIT=10 python3 tests/test_feed_damage.py` | 31/31 passed (12m48s) |
| `python3 tests/test_seal.py` | 29/29 passed |
| `python3 tests/test_page_timing.py` | 20/20 passed |

What these tests do not cover, and this audit did:
- They damage the ledger with 11 fixed cases and the chart files with 10. None blanks a column the page validates only
  through `+`, which is how the `dipBeforeHigh` gap got through.
- None of them runs the pipeline steps end to end on damaged candle, derivatives or put/call inputs. None does it
  between steps, or with killed, repeated, reordered or interleaved steps.
- The alert-log tests do not lose the log rows, the previous feed and the second copy together.
- They never pair a feed with a ledger or chart file from another run, or with a chart file of another asset or timeframe.

## Could not test

- **Live Cloudflare path.** I did not test the `ctzb-feed` mirror's 15-minute per-file pull or the `ctzb-site` Worker.
  Mixed-run files were simulated at the page instead. The Worker's CSV-to-JSON step (`csvToBars`) was reviewed by
  reading the code only.
- **Kraken cross-check.** There is no network here, so the check reports "unavailable" and never fails.
- **fetch.py.** I could not test fetch.py, which writes the files whole or not at all. Its outputs were damaged directly instead.
- **The 1 January and 29 February pipeline runs.** These need candles that do not exist yet. The page was tested on
  those dates with a quiet-market feed.
- **Rolling back the whole `feed/` folder** (a snapshot restore). It ran, but neither state emits a new alert at its own
  clock, so it could not show a re-emission. By the same logic as the counted case, it would emit again.
- **The setup-alert sender's de-duplication by alert_id**, which lives in the dashboard Worker.
- **The lead-trader relay.** It returns 404 in this harness. Synthetic valid and damaged files were served instead.

## Notes on method

- The "current" state runs at CTZB_NOW 2026-11-14T15:30Z, because its last 4H bar is 12:00. The replay runs at
  2026-11-11T04:30Z.
- check_fresh, check_candles and regression read the wall clock, so they run under a clock shim (`code/fakeclock.py`).
- Regression is forced to pass on the replay state, as `tests/replay_at.sh` does.
- Expectations were coded before each run (`code/page_cases.py`, `code/pipe_cases.py`, `code/flows.py`,
  `code/page_hard.py`, `code/page_timing.py`).
- Harness false positives were fixed and re-run (BOM clock, cloud text read as the main chart). They are recorded
  in `override.json`.
- Files: `all_checks.csv` (every check), `disagreements.csv`, `progress.log`, and the raw `*.jsonl` logs.
