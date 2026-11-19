# Audit 46c: damaged, missing and tampered files

Independent auditor. I tested the code frozen at 0185de1, using copies of the two frozen states (`current`, 19 Nov 2026, and `replay_1111`). I did not edit, commit or push anything in the repo. All harness code is my own and is in this folder (`ph.py`, `prun.py`, `pcases.py`, `pipe.py`, `piperun.py`, `pipecases.py`, `pipe_special.py`, `alertseq.py`, `extra_pipe.py`). The details of every case are in `all_checks.csv` (813 rows) and `disagreements.csv`.

This work covers entry quality only. These files hold computed signals, not fills, so nothing tested here is a strategy return or a track record.

## Top line

**Real-life damage: 2 distinct disagreements (3 rows), both at the pipeline level and both with no figure changed. Page level: 0.**
Hardening (not counted): 1. Two-fault (recorded, not counted): 1.

| Level | Cases tried (real-life) | Got through |
|---|---|---|
| Page (2 states, Playwright) | 550 | 0 |
| Pipeline (both states; most cases on `current`) | 156 | 2 distinct (3 rows) |
| Hardening (hand-forged), page | 106 | 1 (the same rule on both states) |

### Per family (real-life cases; page + pipeline)

| Family | Rule meant to catch it (from the code) | Page tried / through | Pipeline tried / through |
|---|---|---|---|
| 1 Missing | Page: `get()` returns null, then each area reads "unavailable", "held" or "Loading". Pipeline: the candle checks, the seal (`seal.problems`: missing), `feed_live` required files, `check_log` | 46 / 0 | 11 / 0 |
| 2 Malformed | Page: the strict check (`feedProblems`), `parseCSV` (`dropped` and `cut`), `ledgerRowOk`, `barsOk` and `stepsOk`, the Worker's `csvToBars`. Pipeline: `fetch.history_problems` (header, rows, grid, order, blank lines, stray CR, bucketing) | 176 / 0 | 52 / 0 |
| 3 Wrong content | Page: the chart name, the last close against `price_now`, the entry close, the ledger counts against `grade_odds`. Pipeline: the bucketing check, the ETH/BTC ratio, the 4H/12H step, market columns, the seal | 86 / 0 | 14 / 2 |
| 4 Partial run | Seal (steps in order, files unchanged, ran once), `CTZB_STEP_OUTCOMES`, fail-closed on any `feed_live` exception, extras files deleted when extras did not succeed | 4 / 0 | 20 / 0 |
| 5 Timing | Page: `staleNote` (5 h, and the 00:00 UTC close, re-checked every minute), auto-example off when stale. Pipeline: `check_fresh`, stack "today's bar", seal age (2 h), strict check `scored_as_of` == generated day | 50 / 0 | 7 / 0 |
| 6 Delivery | Page: `r.ok`, JSON parse, the CSV "last line has no line end" rule, the Worker's refusal of a cut file, `chartTok` for late files | 88 / 0 | 36 / 1 |
| HTTP-failure combinations (40 seeded random mixes per state) | All of the above together | 80 / 0 | – |
| Alert log (held, fail-closed, killed x2, reverted feed, two runs at once, log deleted, duplicated or cut, previous feed lost) | `check_log`, the second copy, `carried_alerts`, `alerts_held` | – | 16 / 0 |
| Baseline and valid shapes | – | 20 / 0 | – |

### Disagreements by kind (real-life only)

| | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error, blank area | 0 | 0 |
| (iii) damaged input scored, or published, without being withheld | 0 | 2 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, a trade or a track record | 0 | 0 |

## Every disagreement (real-life)

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| pipeline | current | `data/ETH_12H.csv` and `data/BTC_12H.csv` both lost their last bar. Equivalent: both put back to an earlier run's copies, ending 12 h earlier. Logged as 2 rows. | Every check passes and the run publishes clean. The two short files go to the commit step (`git add data/`). No figure changes: nothing scores 12H. | The job stops at the candle checks | `fetch.py` 559-563 checks only that the two 12H files end on the **same bar** and on the **day** of the last daily bar. `.github/scripts/check_fresh.py` 32-33 checks only that the 4H bar is current; nothing checks that the 12H bar is current. One bar missing in one file is caught. The same bar missing in both is not. |
| pipeline | current | `datasets/candle_check.json` replaced between `check_candles` and `refresh` by an earlier run's copy (`checked_at` 11 Nov, `structural_ok` true) | Clean feed published. Its `candle_check` block (`checked_at`, `kraken`) is the earlier run's, so the health monitor reads a stale second-exchange status as this run's. | Held, or a fail-closed feed | `feed_live.py` 468 reads only `structural_ok`. Nothing ties `checked_at` to this run's seal (`started_at`). The seal starts at refresh, after the file is written. Real life is uncertain: in a real runner nothing writes this file between those two steps. It needs a hand or partial re-run, so I counted it, as instructed for doubtful cases. |

## Hardening (not counted)

| Level | State | Forged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| page | both | Ledger plus a matching feed: one top-grade row whose 60th day (entry + 60) is the scored day, so the bar is still open. The feed counts are raised by one to match. | The ledger is accepted and the row is listed | "Past signals unavailable" (FEED_SPEC: "a signal's 60 days had not closed by `scored_as_of`") | `index.html` 1334 uses `entry + 60 d > closedBy`. Day 60 has closed only when `entry + 60 < scored_as_of`, so the test should be `>=`. This is off by one day. In real life it is masked: the pipeline lists only closed rows, and a ledger from a later run fails the count check. |

The other 104 hand-forged cases were all refused ("Data unavailable") or, where valid, drawn with the file's own values. They covered: cross-field contradictions, duplicates, wrong card attached, lists reversed, sections from another run, example mismatches, markup in every text field (none ran as script), 200 kB text, 500-deep nesting, and boundaries (0 and 100, 70 against 69.999999, day 0 and 60, rise 100000, dip -100, 29 Feb).

## Two-fault (recorded, not counted)

- **Fault 1:** `tests/baseline/ledger.json` replaced by a valid empty baseline (`{"rows": {}}`). The regression guard then prints "PASS 0 baselined signals unchanged, 923 new" and the run is clean. **Fault 2:** a lens or grade bug changes a past signal, and nothing stops it. A deleted or cut baseline fails, as designed. An emptied one does not (`tests/regression.py` has no minimum row count).

## Notes: correct figures, but not exactly the stated rule

- **Ledger rule (3).** The brief says "no signal appears twice". The page checks duplicates, and row shape, only among top-grade rows. A duplicated non-top-grade row, or a header line repeated mid-file, is accepted. The figures shown stay correct, because those rows are never shown and never counted. FEED_SPEC says "a top-grade signal appears twice", which is what the code does.
- **Example file.** A bar added after day 60 is accepted, though the README says "nothing after its 60-day window". Figures are unaffected: the side panel and the cloud use only bars E+1..E+30.
- **Runner clock behind the candles.** At 2026-11-19T00:00Z with candles through 19:15, `check_fresh` passes and the run publishes. The feed then reads as 19 h old, which is the safe direction. This is only possible with a clock wrong by hours.

## What failed safe, by family (all real-life cases not listed above)

- **Page (550).**
  - Missing, cut, empty, HTML-page, UTF-16, NUL-padded, gzip and doubled feeds all read "Data unavailable" and "Feed unavailable": no figure, no quiet wording, no chart.
  - Held and fail-closed feeds read "Setups held back" on every tab.
  - Ledger damage (cut mid-row or at a row end, a row lost or duplicated, a column lost, blank or text cells, stray CR, wrong file) reads "Past signals unavailable". Line ends converted to LF, BOM and reversed rows are shown correctly.
  - All 37 kinds of chart-file damage on each drawn chart read "Chart data unavailable for …": 404/502, cut JSON or CSV, a lost or duplicated row, swapped rows, the other asset, every other timeframe, the other run, blank/zero/negative/text cells, BOM, a stray CR.
  - Slow files show "Loading", then the right figures.
  - Every timing case got the right note: 4 h 59 min, 5 h 01 min, 3 days, 2 years, feed ahead of the viewer, after 00:00, open 6 h or 3 days. In a quiet market the example was switched off once the data went stale.
  - Lead-trader shapes: long/short, open/add/reduce/close, 1000 trades, one asset, no ids. The line read `in · long/short`, `out` or `not in` correctly, and no dollar or contract field was shown. Damaged lead-trader files read "unavailable".
- **Pipeline (153 cases that failed safe or were correctly accepted).**
  - 75 candle and series damages stop at `check_candles` or `check_fresh`. Lost funding, long/short or put-call rows, a cut `series_through.json` and an older funding copy are held by stack.
  - Every dataset changed, deleted, cut, emptied, replaced by an older copy or added between steps fails the seal: held or fail-closed.
  - Grade, extras, stack and refresh killed mid-step: held. Extras killed: clean, with the extras withheld and its chart files deleted.
  - Steps out of order, run twice, cards never run, a second refresh, two runs in one folder: all held or fail-closed.
  - `feed_live` run alone 3 h later: fail-closed. Run again 10 min later: same figures.
  - Bad or missing `CTZB_STEP_OUTCOMES` (garbage, a step missing, `cancelled`): held.
  - The member page file missing: fail-closed (`FileNotFoundError`).
  - Clocks a day ahead or behind, refresh at 23:59:59 with later steps after 00:00, a feed written at 00:00:01: held or fail-closed. A whole run at 23:59:59 publishes figures equal to the clean run.
  - Alert log: no alert lost or emitted twice in any of the 16 sequences.

## Repo's own tests (part C)

| Test | Result | Not covered |
|---|---|---|
| `tests/test_feed_damage.py` (RENDER_LIMIT=40 REJECT_LIMIT=10) | 33/33 pass (9499 damaged feeds; page and pipeline agree) | Mostly single-field damage. Not covered: the ledger's 60th-day boundary (hardening above), junk rows that are not top grade, multi-file run mixes, HTTP-status combinations |
| `tests/test_seal.py` | 29/29 pass | `candle_check.json` written before the seal starts (disagreement 2) |
| `tests/test_page_timing.py` | 24/24 pass | A chart file that is slow and arrives late, then is drawn (I tested this: it passes) |
| None of the repo's tests | – | 12H currency (disagreement 1); an empty regression baseline (two-fault) |

## What I could not test

- **Live services.** I had no network, so I could not test the Kraken cross-check (it reported "unavailable", which never fails a run by design), the live Workers, the mirror's 15-minute pull, or GitHub push/rebase. The site Worker's `csvToBars` is emulated in my harness. Mixed-run files from the mirror were simulated by serving files from the other state.
- **The deployed page.** The live site runs an older build (656d67c3, per `docs/SITE_CHANGES.md` "Pending"). I tested the page in the frozen repo, not the deployed one.
- **Year-end chart files.** Neither state has a selectable chart whose file crosses 1 January with a short bar (the 5D files cross it on whole 5-day bars), and I did not build a year-end replay. `test_year_end.py` covers the pipeline side.
- **Concurrency on separate runners.** Two runs on separate runners (git-level) were not reproducible. Two runs in one folder were.
