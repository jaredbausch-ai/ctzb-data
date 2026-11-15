# Audit 35c: damage audit of the ETHKROS member site and its pipeline

Independent, 15 Nov 2026 (machine clock). Nothing in the repo was edited. All work on copies, own code only
(`pipe.py`, `page.py`, `p*.py` in this folder). Every case's expected result was written into the case before it ran.
This audit measures whether damaged files and runs fail safe. It says nothing about returns: the site shows entry
quality only, computed signals, never fills.

## Top line

**1 counted disagreement (page level, real-life damage). 0 at pipeline level.** 1,532 real-life cases, 28 hardening.

Page level (Playwright, every tab, every picker button, example switch, both chart modes):

| Family | Rule that guards it (from the code) | Tried | Got through |
|---|---|---|---|
| 1 Missing | any file that does not arrive reads "unavailable" (feed: "Data unavailable") | 12 | 0 |
| 2 Malformed | strict checks: FEED_SCHEMA + crossCheck, ledgerRowOk/cell count/cut, barsOk/stepsOk, example check, tradesProblems | 50 | 0 |
| 3 Wrong content | each file must agree with the feed (chart name, last close = price_now, entry close, ledger counts/shares) | 29 | 0 |
| 4 Partial run | feeds of real failed runs (held, fail-closed, extras withheld) shown as the run left them | 4 | **1** |
| 5 Timing | stale (5 h) and daily-close notes on the viewer's clock; yearly counts from full years | 13 | 0 |
| 6 Delivery | cut / empty / HTML / slow files: "Loading" until arrival, then the file's own state | 57 | 0 |
| (none) | valid shapes and real states (lead-trader files, 8 states walked whole) | 13 | 0 |

Pipeline level (the workflow's steps in order on copies, outcomes from exit codes, feed_live last):

| Family | Rule | Tried | Got through |
|---|---|---|---|
| 1 Missing | check_fresh / history_problems stop the job; seal; feed_live fails closed; alert log restored from its copy or fails closed | 243 | 0 |
| 2 Malformed | fetch.history_problems (check_candles, stack_live); seal for datasets | 816 | 0 |
| 3 Wrong content | asset/timeframe/bucket checks; seal hashes; alert-log hash | 199 | 0 |
| 4 Partial run | seal (order, once, unchanged), strict outcomes, extras clears first, alert carry/hold | 81 | 0 |
| 5 Timing | today's bar + current 4H bar; stack's own today check; seal age 2 h / not in future; scored_as_of = feed's day | 15 | 0 |

States tried (11): `a35/current` (cur), `a35/replay_1111` (r1111), r1111 advanced day by day with real candles to
14-15 Nov (alert log), and six built with the repo's own `tests/replay_at.sh` from a copy of cur: 15 Mar 2026
(quiet, filter off), 15 Jun 2022 (bear), 1 Jan 2026 00:20, 31 Dec 2025 23:50, 29 Feb 2024, 24 Sep 2024 (the example
signal itself live), plus three feeds written by real feed_live runs on cur: held (stack failed), fail-closed (seal
broken), extras withheld (extras failed).

Disagreements (real-life only), by kind:

| Kind | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | **1** | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| page | cur, feed written by a real feed_live run with `extras=failure` (published: cards on, `extras_withheld` true, `past_paths` empty) | the extras step failed (Family 4); member opens each setup on the Chart tab | the past-signals box draws "Past paths unavailable in this feed", but the note under it reads "Loading BTC 2D…" on the BTC 2D live setup, "Loading ETH 3D…" on the BTC 2D forming setup (another chart's name), "Loading BTC 1D…" on the example; it never clears | the cloud and its note say the paths are unavailable (Family 6 rule: every area says its own state, never "Loading" after arrival) | `docs/artifacts/member-site/index.html` line 1107, `renderCloud`: `if (!pp) { svgEl(...); return; }` returns before setting `#cloudNote` and `#cloudSub`, so they keep what `blankChart` wrote while the chart file loaded (line 930) or the previous setup's text. Reached on every run where extras fails, which the workflow treats as non-gating. The repo's `test_page_states.py` "extras withheld" state checks placeholders only, not stale "Loading" |

## Hardening (not counted)

| Case | Result | Where |
|---|---|---|
| `past_trades` written as `27.0` (float form of a whole number) | page accepts (`String(27)` is in the sample text); feedcheck.py rejects (`str(27.0)` = "27.0"): verdicts differ. feed_live's `num()` never writes that form | index.html line 430 vs feedcheck.py line 118 |
| both ETH_12H and BTC_12H lose their last bar at a run after 12:00 UTC | passes history_problems (both end on the same bar, on the last daily bar's day); check_fresh and check_candles' structural() look at 1D/4H only. Not counted: fetch.py builds 4H and 12H from one hourly fetch, so a stale 12H beside a current 4H cannot come from the pipeline's writers; 12H is not scored (no figure changes). Both 4H files cut the same way are stopped by check_fresh | fetch.py lines 474-481 |
| `tests/baseline/ledger.json` replaced by `{"rows": {}}` | the regression guard passes ("0 baselined signals unchanged"); figures equal this run's, but any past-row drift would pass. Needs `--approve` on an empty ledger or a hand edit | tests/regression.py, main |
| 26 others: markup in every printed text field, 200 KB sample, unicode/RTL/NUL, exponent forms, 1e308 and deep junk in unknown fields, shares above parents, eras not adding up, a card on the wrong live signal, duplicate ids, days_elapsed off, lists reversed, grade_odds or example card from another run, feed a day in the future, scored_as_of before generated_at, the 5% ladder row at exactly 70 and 69.999999 (edge read correct both ways), shares 0/100, price 0.01 and 999,999,999.99, day 0/60, bar 60/100 | all rejected cleanly or rendered with the file's own values, no script error, no placeholder, no markup executed; page verdict = feedcheck.py's except the row above | page_results.jsonl |

## What failed safe

Page (178 real-life cases): feed 404/500/503/abort/empty/HTML/null/array/UTF-16/gzip/trailing garbage/two feeds
concatenated/cut at 6 points/ledger, chart, example, trades, alert-log or manifest served as the feed: "Data
unavailable", header "Feed unavailable", Past signals unavailable, Chart "Data unavailable", example never standing in.
Feed with a BOM: read correctly. Feed and chart files from different runs (both directions), chart of another asset or
timeframe (relabelled or not), older-run charts cut by 1/2/5 bars, 14 bar-level damages on a forming and on the live
chart: "Chart data unavailable" (a file missing only its oldest bars is drawn correctly). Example file 404/HTML/cut/
empty/candles/short of day 60/entry close or index off/bar repeated: example chart unavailable, card from the feed.
Ledger 404/500/HTML/empty/header only/cut mid-row/lines lost holding top-grade rows/row repeated or lost/two copies/
UTF-16/column lost: "Past signals unavailable"; CRLF, BOM, reordered, repeated header, below-grade lines lost: whole and
correct. Lead-trader files: 7 valid shapes shown (no dollar size, no contracts), 10 damaged read "unavailable". Viewer
clock +5 h, +3 days, +1 year, 10 min behind, across 00:00 UTC: notes correct. Real held and fail-closed feeds: "Setups
held back" on every tab, never quiet, with the stale note after 6 h. Slow feed/ledger/example/trades (3 s) while on
Chart, Past signals or How to read: "Loading", then the file's state.

Pipeline (1,354 real-life cases): stopped before scoring 615, held 213, fail-closed 355, published with figures equal to
the clean run 140 (cosmetic: CRLF/LF, extra column, labelled column order, space in a cell; a damaged chart file before
extras, which extras rewrites; unused config files lost), alert sequences 31.
- Inputs (734): every candle file 1D-8D, 4H, 12H and every funding/long-short/OI/put-call series, 37-40 damages each
  (rows repeated/swapped/lost at start/middle/end, column lost or renamed, text/blank/negative/zero/nan/inf cells, cut
  mid-cell/after a comma/at the line end, BOM, blank lines, extra header, ms timestamps, off-grid time, another asset's
  or timeframe's file, an older run's copy, a row dated after today). Older-run or lagging series: held by stack_live.
- Datasets between steps (486): every datasets/ file deleted, emptied, header only, cut, column lost, row repeated,
  figure altered, older run's copy, before feed_live (336) and before grade/extras/stack/cards/regress (150).
- Config and reference files (38): analysis/grade*.json, grokpack.json, keep/odds/troughs.json, PRETRADE.md, the page
  (feedcheck's schema), the regression baseline: lost/emptied/cut.
- Runs (63): steps skipped, run twice, out of order, killed by SIGKILL at 26 points, two runs interleaved, a second
  refresh mid-run, outcomes missing/cancelled/miscased/garbage/extras skipped or failed, clocks a day ahead/behind,
  00:00:00, steps across midnight, feed_live 2 h 1 min after the seal, before it, the next day, stack an hour late.
- Alert log (31 sequences on real days, 6 new events on 15 Nov): log deleted/emptied/header only/cut/lines lost/row
  repeated/CRLF/reordered/older copy, before and after new events; second copy deleted or older; previous feed lost,
  cut or older; held, two held, fail-closed and 1-minute-retry runs; the same run twice; feed written but log not.
  No alert emitted twice, none lost; log and copy both lost, or a rolled-back feed beside a newer log, fail closed
  and keep the alerts in `alerts_held`.

## Repo's own tests (part C), on a fresh copy of the repo

| Test | Result |
|---|---|
| tests/test_seal.py | 29/29 pass |
| tests/test_page_timing.py | 20/20 pass |
| tests/test_feed_damage.py, RENDER_LIMIT=40 REJECT_LIMIT=10 | 33/33 pass (9,499 damaged feeds on the 12 Nov replay: page and feedcheck agree) |

Not covered by them: a feed from a real failed extras step walked through every Chart-tab setup, and any check for
"Loading" text left after a file arrived (the disagreement above); verdicts on float-form integers (`27.0`); mixed-run
files beyond older chart files (feed/ledger from different runs, a held run's chart files beside the last clean feed);
pipeline-level damage at all (test_feed_damage is page-only; test_seal covers the seal, not candle inputs, outcomes,
clocks or the alert log); 12H currency.

## Not tested, and why

- fetch.py, fetch_derivs.py, fetch_pcr.py and Kraken itself: no network. Exchange damage was applied to data/ after
  the fetch; check_candles ran in enforce mode with Kraken unreachable (recorded "unavailable", as designed).
- check_fresh.py and check_candles.py use the real clock; they were run under a fixed clock (`fakeclock.py`, patches
  `time.time`, `datetime.now`, `date.today`).
- The Cloudflare Workers in their runtime. Read their code instead: the mirror syncs file by file and never deletes a
  KV entry, so after extras fails it keeps serving the last run's chart files; modelled on the page (rejected on price).
- The commit/push step and git history rollbacks; disk full (fail_closed itself failing).
- A filter-on quiet market from a real replay (dates tried were filter-off); repo test_page_states covers a forged one.
- Trades relay in live mode (404 in this harness, as instructed).

Files: all_checks.csv (1,560 rows), disagreements.csv (1 row), progress.log, harness scripts. Harness expectation
errors were reviewed by hand and re-marked with their reason: 18 in overrides.json (no-op damage, kills that landed
after the step finished, designed behaviour such as zero volume on a 4H bar) and 103 by fixjsonl.py (my check wrongly
flagged the extras step's own sealed files beside held feeds when extras had succeeded). None of them is a defect.
