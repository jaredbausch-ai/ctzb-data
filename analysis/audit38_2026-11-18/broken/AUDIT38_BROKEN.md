# Audit 38c: breaking the member site and its pipeline with damaged files

Independent run on copies of the two frozen states (`a38/current`, `a38/replay_1111`), plus two replays made for
this audit (2025-12-31 23:44 and 2026-01-01 00:14) and the committed 17 Nov 20:14 feed (from git history) for
cases around midnight. All harness code is my own (`bin/`). Nothing in `/home/claude/ctzb-data` was changed.
Row-level detail is in `all_checks.csv` (712 rows) and `disagreements.csv`.

This work checks the site and the pipeline only. The feed measures entry quality only. It has no exits, so
nothing here is a strategy return or a track record.

## Top line

**Real-life damage: 685 states tried. 2 disagree, and both come from one cause:** on a page left open, the
stale warning blames the pipeline. Class (iv), wording. No wrong figure was shown. No raw placeholder, script
error or blank area appeared. No damaged input was scored or published. Nothing read as a return or a trade.

| Family | Page: tried / got through | Pipeline: tried / got through |
|---|---|---|
| 1 MISSING | 34 / 0 | 15 / 0 |
| 2 MALFORMED (incl. 10 damaged lead-trader files) | 84 / 0 | 110 / 0 |
| 3 WRONG CONTENT | 48 / 0 | 24 / 0 |
| 4 PARTIAL RUN | 3 / 0 | 214 / 0 |
| 5 TIMING | 37 / **2** | 21 / 0 |
| 6 DELIVERY | 72 / 0 | 10 / 0 |
| Undamaged states and valid lead-trader shapes | 12 / 0 | 1 / 0 |
| **Total (counted)** | **290 / 2** | **395 / 0** |

Outside the count: 25 hardening cases (all held) and 2 states with the viewer's clock behind the feed, which is
a known and accepted case.

| Class | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording misstates the state | 2 (one cause, states cur and r1111) | 0 |
| (v) reads as a return, a trade or a track record | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| page | cur | Page loaded 6 min after the feed, then left open 6 h (TIMING) | Now card, Chart, Past signals and How to read: "This data is 6 hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does." | A stale warning that does not say the pipeline missed a run. In this case the pipeline ran on schedule; the open page never fetched again, so the member only needs to reload. | `docs/artifacts/member-site/index.html:626` (`staleNote`) treats every age over 5 h as a missed run. The page fetches its files once (`boot`, :1268-1269), and the minute timer (:1295-1301) only updates the age. The 00:00 note at :628 has the same flaw: "It updates shortly after each close" is not true on an open page until it is reloaded. |
| page | r1111 | Same | Same | Same | Same |

I counted this because a page left open is real-life TIMING damage. Guarantee (7) only asks for a warning, and
the warning does appear. The disagreement is that its text gives the wrong reason.

## What failed safe, by family

The stated rule is from the code. "Stop" means the job stopped at the candle checks and the previous feed stayed
up. "Held" means `cards_withheld` with the stated steps failed. "Fail-closed" means `feed_error` was set.

| Family | Rule meant to catch it | Page result | Pipeline result |
|---|---|---|---|
| 1 MISSING | Page: `get()` returns null on any non-OK status or network error, which reads as down, ledger unavailable, chart unavailable or trades unavailable. Pipeline: `history_problems` ("is missing"), `feed_live` required files, seal "missing", `check_log` | 14 "Data unavailable" (feed 404/500/502/503/aborted, all files 404). 20 kept the feed and marked only the lost file unavailable | 8 stop, 3 held, 1 fail-closed (alert log and its copy both gone). 3 restored the alert log or carried alerts by design (log gone, copy gone, previous feed gone) |
| 2 MALFORMED | Page: `FEED_SCHEMA` + `crossCheck`; `parseCSV` dropped/cut + `ledgerRowOk`; `barsOk`/`stepsOk`; the Worker's `csvToBars`. Pipeline: `_row_problems`, `_file_problem`, exact header, series checks, seal | 74/74 correct, including a ledger with a BOM (the browser strips it, figures correct) and CRLF→CRCRLF (unavailable) | 89 stop, 7 held, 1 fail-closed. 8 published, equal to the undamaged run (CRLF, cell spaces, exponent form); 5 alert-log repairs |
| 3 WRONG | Page: chart name, last close equals `price_now` and entry bar equals `entry_close` to the half cent, ledger equals `grade_odds`. Pipeline: 2D-8D equal the 1D bucketed, ETH/BTC ratio, market columns, 4H/12H step and 25% close test, seal sha | 12 chart swaps across assets and timeframes, each chart path given the other asset's JSON, ledger, charts and feed from the other run, every path given another file's content: all unavailable or down | 14 stop, 8 held, 2 alert-log cases (no `alert_id` repeated) |
| 4 PARTIAL | `CTZB_STEP_OUTCOMES` gating, the seal (order, twice, sha, 2 h age), `fail_closed` | Held and fail-closed feeds read "Setups held back"; a held feed with last-good ledger/charts reads unavailable | 95 held, 110 fail-closed. Published: extras killed (extras withheld, chart files deleted), feed_live run twice (same feed, no new alerts), runs that died between feed and log (next run rebuilt or restored the log; each alert logged once with its first `emitted_at`) |
| 5 TIMING | `check_fresh` (today's 1D bar, current 4H), the stack's today check, strict `scored_as_of` = generated day, seal age; page 5 h and 00:00 notes | 35/37 correct: 5 h 01 vs 4 h 59, 3 days, 2 years, a feed 5 min ahead, 1 January, 00:00 crossing (incl. left open), slow feed / ledger / chart / example / trades / all files (loading text, never "unavailable" while loading) | 8 stop, 6 held, 4 fail-closed (a step or feed_live crossing 00:00, feed 2 h 05 after refresh, clock stepped back). 23:59:59 run and the two year-end replays published clean; open-signal day counts and best/worst equal my recomputation from 1D candles (35/35) |
| 6 DELIVERY | Page: `r.ok`, JSON parse, last line must end in `\n`, Worker cut check | 32 down (feed cut at 0-99.9%, minus 2 bytes, HTML 200/502, empty, `null`, `{}`, doubled, trailing byte, UTF-16, NULs); 40 others unavailable for that file only | 8 stop (cut candle and series files), 2 alert-log repairs |

Two results are safe but worth knowing.
- When the non-gating extras step is reported as `skipped`, the whole feed fails closed (`p-extras-skipped`).
  Only `failure` is exempt from the seal (`feed_live.py`, `extras_failed`). This matches FEED_SPEC.
- A BTC_2D file with CRLF line ends passes `check_candles`, but `engine.load` cannot read it, so the run is held
  (`c-BTC_2D-crlf`). The same damage on ETH_1D makes `check_fresh` crash (traceback), so the job stops.

## Hardening (not counted)

These 25 hand-forged feeds have fields that are each valid but contradict each other. The page handled all 25
correctly. Rejected as down: a card attached to another live signal; `grade_odds` count +1, alone and with its
miss and path counts moved; `open_signals`, `grade_odds` or `cards` taken from the 11 Nov run; a quiet feed that
is not withheld but has no market filter. Accepted and correct: cards and live-signal lists reversed; duplicate
keys; shares written as `7.0e1`; from-entry exact share 69.999999 (reads "Below the 70% bar") and exactly 70;
prices at cents and near 10^9; a card with 0 past signals ("No odds yet"); a quiet market with the example
switched on, switched off when stale, and switched off on a page left open; one `odds_fade` list emptied. Also
accepted correctly: a 200,000-character sample; RTL, emoji and zero-width text; deeply nested junk; HTML/script
markup in every text field (escaped, never executed); an example card's `entry_close` +0.01 (its chart reads
unavailable).

## Lead-trader file

All 8 valid shapes render as their own values: long/short, open/add/reduce/close, 500 trades, ETH only, optional
fields absent, empty, `move_pct` without `account_pct`. The card line reads "in · long", "not in" or "out". A
file carrying `size_usd`, `contracts` and `qty` shows none of them. All 10 damaged files read "unavailable":
future time, wrong order, duplicate, unknown asset, price as text, price 0, no action, `+00:00` time,
leverage 0, `trades` as an object.

## The repo's own tests (part C)

| Test | Result | What it does not cover |
|---|---|---|
| `tests/test_feed_damage.py`, `RENDER_LIMIT=40 REJECT_LIMIT=10`, both states | 32/32 pass (14 min) | Damages one feed field at a time, plus 11 ledgers and 10 chart files per state. Not covered: HTTP status, HTML or empty bodies, cut bytes; damage at the CSV the Worker converts (blank or space cell read as 0, hex, BOM, CRLF); files from different runs served together; slow files; markup in text fields; lead-trader shapes beyond schema damage |
| `tests/test_seal.py` | 29/29 pass | Steps killed part-way, skipped, run twice or out of order (beyond the cases it names); a step clock crossing 00:00; two runs in one folder; extras `skipped` |
| `tests/test_page_timing.py` | 20/20 pass | Checks that the stale note appears, not what it says (the disagreement above) |

## What I could not test, and why

- **Kraken cross-check.** No network, so every run took the "unavailable, skipped" path. I never exercised the
  0.5% enforce threshold.
- **The real Workers.** Both the site and mirror Workers are emulated: `csvToBars` was re-implemented in Python
  with JS number rules. Cloudflare caching and the mirror's 15-minute pull timing were not run.
- **Real GitHub runs.** "Two runs at once" was simulated in one folder (B's refresh between A's grade and extras,
  result: held). The concurrency group and the commit, rebase and push race were not run. Neither was
  `fetch.py`'s own network failure: damage was applied to its outputs.
- **The Telegram sender's `alert_id` de-duplication.** Not run. Cases where the spec relies on it were checked
  only for no repeated `alert_id` in the log: previous feed lost (7 days carried), and feed, log and copy swapped
  for another run's consistent set.
- **The 4-hour freshness check late at night.** The state's 4H files end at 08:00, so the 23:59 and 00:00
  crossing runs left `check_fresh` out. All other steps ran as in daily.yml.
- **A real evening state.** The 00:00 page note was tested with the 17 Nov 20:14 committed feed beside today's
  ledger and charts, not with a matching evening state.
- **The live lead-trader relay.** It returns 404 in this harness, so trade files were served synthetically.

## Files

- `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit38c/all_checks.csv`: every
  state (level, state, case, family, counted, damaged, expected, shown, ok, cause).
- `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit38c/disagreements.csv`: the 2
  rows, with class.
- `page_checks.csv` and `pipe_checks.csv` (the two halves), `progress.log`, `bin/` (harness), and `work/`
  (repo-test outputs and run logs) are in the same folder.
- Harness slips found and corrected before counting, recorded in `pipe_checks.csv`:
  - The first page batch was re-run after a clock-unit error.
  - 11 pipeline "alter" cases that changed no byte were removed and replaced with real one-digit and
    regime-flip edits (all held).
  - 7 alert-log rows were reclassified with their reasons.
