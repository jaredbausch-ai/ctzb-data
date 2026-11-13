# Audit 25c: broken, damaged, missing, stale or slow files, and failed runs

13 Nov 2026. Independent auditor. Scope: page level and pipeline level. Nothing in the repo was edited. All work ran on copies of the two frozen states (`a25/replay_0414`, `a25/current`) and on replays built with `tests/replay_at.sh` from a copy of the repo. These are computed signals, not fills. There is no exit in the data, so nothing here is a return or a track record.

Details are in `all_checks.csv` (every state: level, state, what was damaged, expected, shown, ok, category, real, cause) and `disagreements.csv`. The code is in `tools/`, and the raw logs are `*.log` and `*.jsonl`.

## Top line (real-life damage only)

| Level | States tried | (i) wrong / unsupported figure | (ii) placeholder, script error, blank | (iii) damaged input scored or published, not withheld | (iv) wording misstates the state | (v) reads as return / trade / record | Disagreements |
|---|---|---|---|---|---|---|---|
| Page | 295 | 0 | 0 | 0 | 2 | 0 | **2** |
| Pipeline | 604 | 0 | 0 | 3 | 0 | 0 | **3** |
| **Total** | **899** | 0 | 0 | 3 | 2 | 0 | **5** (2 causes) |

Hardening (hand-forged, not counted): 21 tried. 4 were accepted although their fields contradict each other (see the last section).

## Every disagreement

| # | Level | State | What was damaged | Shown | Expected | Cause (file:line) |
|---|---|---|---|---|---|---|
| 1 | page (iv) | replay 2026-04-10 (quiet market, filter off) | The page is left open while the pipeline stops refreshing. The feed passes 5 h old (viewer clock +5h01, no reload). | The worked example card ("ETH · 2D chart · example · Confirmed setup", 87%) stays on the Now card, with the 5-hour stale note inside it. A fresh load in the same state shows "No setup right now" and no example. | The example never stands in for an outage. Once the feed is stale, show the quiet or stale card, as a fresh load does. | `index.html:1257` turns the example on (`S.preview = true`) only when the feed is not stale, and does it once. The once-a-minute re-render at `index.html:1221` redraws on the stale transition but never clears that automatic preview. |
| 2 | page (iv) | replay 2026-07-17 (quiet market) | Same as #1 | Same as #1 | Same as #1 | Same as #1 |
| 3 | pipeline (iii) | replay 2022-08-15 (quiet, filter off) | `feed_live.py` run again alone the next day with `CTZB_STEP_OUTCOMES` unset (a hand or repeated run, no rescoring). Unsure this is real: it needs a hand run, which the workflow never does, but `feed_live.py:287-289` documents hand runs as supported. | Published, not withheld. `scored_as_of` 2022-08-15, `generated_at` 2022-08-16T04:14Z. The page shows "No setup right now" and "Market filter: off" with no stale warning. Only the footer hints at it ("closed through 14 Aug"). | Withheld, or a page warning that the data is a day old | `seal.py:82-106`: the seal checks step order and file hashes but carries no run identity, so the last run's intact seal passes again. `feedcheck.py:129` and `index.html:450` only reject `scored_as_of` after `generated_at`, never before it. Staleness is read from `generated_at` alone (`index.html:587`). With live or forming signals the `days_elapsed` / `confirms_on` rules catch it (2023-09-01 was held). A quiet feed has nothing for those rules to catch. |
| 4 | pipeline (iii) | replay 2026-04-10 | Same as #3 | Same as #3, and the auto example is shown as well | Same as #3 | Same as #3 |
| 5 | pipeline (iii) | replay 2026-07-17 | Same as #3 | Same as #3 | Same as #3 | Same as #3 |

## What failed safe, by family

| Level | Family | States | Result |
|---|---|---|---|
| Page | Feed: 404, 500, 502, empty, cut mid-file, cut by 3 bytes, HTML error page, another file's body, slow 6 s | 37 | "Data unavailable" and "Feed unavailable" everywhere. Picker, previous signals and chart tab all say unavailable. Ledger not shown. No example stand-in. A slow feed draws correctly when it lands. |
| Page | Ledger: same HTTP set; top-grade row duplicated, lost, cut, blanked; column lost; header only; BOM; CR CR LF; LF-only; from the other run | 46 | "Past signals unavailable". When the damage hit only non-top-grade rows, or the file was LF-only, the top-grade record shown equals the file's (137 rows, 20 missed). |
| Page | Chart files: HTTP set, plus CSV through the Worker conversion. Covers rows duplicated, swapped or deleted (start, middle, end), close column lost, text, blank, negative, zero, cut last line, CRLF, BOM, trailing blank line, extra header, other asset, other timeframe, 8D file, previous 4-hour run (last close +0.3%), files from the other run. Run on BTC 2D (live), BTC 1D, ETH 1D, ETH 2D (forming). | 142 | Every damaged file reads "Chart data unavailable" (or "doesn't reach / don't match"). Harmless forms draw correctly. |
| Page | Example chart file: HTTP set, one bar short of day 60, first bar lost (with and without index fix), duplicate bar, ETH 2D chart served instead | 16 | Unavailable, except the index-fixed file, which draws correctly. The card still comes from the feed. |
| Page | Lead-trader file: HTTP set; empty; long or short; open, add, reduce, close; 40 trades; one asset only; optional fields absent; not newest first; future; text price; unknown action; wrong key; bare list; extra `size_usd` and `contracts` fields | 23 | Valid files show the file's prices and leverage, and the card marker reads in, out or not in correctly. Damaged files read "unavailable". No dollar size or contract count is ever shown. |
| Page | Wrong file under a name (ledger as feed, feed as ledger, feed as trades, chart as example, example as feed); feed or charts from the other run | 10 | Unavailable or not drawn, as expected |
| Page | Viewer clock 4h59, 5h01, 30 h, 2 years after the feed | 8 | Stale note on Now, Chart, Past signals and How to read from 5 h. None at 4h59. |
| Page | Real pipeline outputs: held run, fail-closed run, extras killed or failed, quiet-market 404, 500, held and 6 h old; year end 23:58, 1 Jan 04:14, 1 Jan 00:13, 29 Feb 2024, 1 Mar 2025, 23:59:59 viewed after midnight | 14 | "Setups held back" / "Data unavailable" with no quiet wording. Extras withheld means charts unavailable and cards shown. Year-end, leap-day and midnight replays render clean, with correct figures. |
| Page | Every state above | 295 | No pageerror, no console error (other than aborted fonts and 404s), no raw placeholder (NaN, undefined, null, [object, Infinity, ${, n/a%, $-) in text or SVG, no blank card or chart |
| Pipeline | Candle files, 7 timeframes × 2 assets × 21 damages (rows, columns, cells, cuts, CRLF, BOM, blank line, extra header, other asset or timeframe, emptied, header only) | 294 | 261 stopped at check_candles or check_fresh: feed and log untouched. 17 harmless or unscored damages published identical figures: 4H/12H gaps, a cut below 1e-9 relative, 12H not scored. 16 (CR CR LF, or a blank line, in 2D-8D) passed check_candles and then crashed refresh, so the run was held (safe, but late). |
| Pipeline | Derivatives and put/call series: deleted, emptied, duplicated, missing or swapped rows, text, cut, first row lost, 1 day and 4 days stale, other asset, CRLF | 76 | 55 stopped at check_candles. 19 identical output: 1 day stale is within the stated 3-day tolerance, CRLF, or the cut hit an unscored per-market column. 2 held late: text in `funding_oi_weighted`, which history_problems does not validate, crashed a later step. |
| Pipeline | `datasets/*` between steps (deleted, emptied, header only, cut, duplicated, digit altered, older run's copy) before grade, extras, stack, cards, regress and feed | 171 | Withheld through the seal, or fail-closed. Damage to extras-only files withheld just the extras fields. The 10 "older copies" that published were byte-identical to this run's. |
| Pipeline | Alert log (deleted, emptied, last row lost, row duplicated, cut mid-row, older copy, LF-only); previous feed lost or cut; outage gap then clean, repeat, held, kill after feed write followed by clean, crash, two crashes or held | 24 | Each pending alert was emitted once and logged once. Held runs consumed nothing. A damaged log fails closed and stays held. An LF-only log is rebuilt byte-identical. |
| Pipeline | Order and outcomes: stack before extras, cards before stack, grade twice, refresh re-run mid-way, cards never ran, extras or regress skipped, outcomes typo, cancelled, regress missing, unset or empty | 16 | Held, except the documented hand run. With outcomes unset, a failed regression step does not withhold, but the figures published equalled the correct run. |
| Pipeline | Killed steps: refresh, grade, extras, stack, cards half way; feed_live before writing | 6 | Held (extras: just the extras withheld). With feed_live killed, the previous feed was left whole and the run went red. |
| Pipeline | Clock a day ahead or behind, 00:00:00 next day, 23:59:59 on stale 4H data, 00:00:00 on the last day | 5 | STOP (check_fresh), or identical output |
| Pipeline | grade.json deleted, cut or emptied; baseline deleted, emptied or cut; page missing; stack_status, candle_check (missing or failed) and manifest (missing or from another run) damaged; all of `datasets/` from another run | 12 | Held or fail-closed. A page cut to a third still holds the schema block, so output was identical. |

## Repo's own tests (C)

`tests/test_seal.py` passed 18/18, `tests/test_page_timing.py` 8/8, and `RENDER_LIMIT=40 REJECT_LIMIT=10 tests/test_feed_damage.py` 31/31. All ran on a copy.

They do not cover:
- **No forming cards in the damage test's replay.** It says it uses "a state with forming cards", but its replay of 12 Nov is built from today's candles, so the 12 Nov bar is whole. The log prints "0 forming cards, 23 live signals", so forming-card rendering under damage is not exercised there.
- **No page left open in a quiet market** with the example auto-shown (#1).
- **No re-run of feed_live alone later** (#3).
- **No pipeline-level damage that passes check_candles and then crashes a scoring step** (the 18 late-held runs).
- **Single-file damage only.** Mixed runs (feed with ledger or charts from another run) are covered only by the timing test's older-chart case.
- **Hand-forged contradictions** are only checked for page and pipeline agreement, not for whether accepting them is right.

## What I could not test, and why

- **Network calls.** Kraken cross-check, `fetch.py`, the third-party fetches: there is no network. Kraken counts as unreachable, which check_candles skips by design.
- **Clock in the gate steps.** `check_fresh.py` and `check_candles.py` read the real clock. They ran under a wrapper that sets `time.time`/`datetime.now` to `CTZB_NOW`.
- **The Cloudflare Worker.** Its `csvToBars` was reimplemented in Python to build chart responses. Its gate, headers and Service Bindings were not run.
- **Git behaviour.** git push/rebase races, two runners at once (the `candles` concurrency group serialises them), the scheduler and watchdog, and git autocrlf on checkout. A pure CRLF-to-LF change of the alert log was simulated and is harmless.
- **A feed request that never answers.** Only a 6 s delay was served. By reading the code, a hang leaves "Loading the latest data…" until the browser gives up.
- **Viewer devices.** Mobile widths, real devices, and a wrong viewer clock (accepted per the brief).

## Hardening (hand-forged; not counted)

| Forged file | Result |
|---|---|
| Card `sample` text says "all 33" while `past_trades` is 3 (eras, ladder and from-entry scaled to match) | Accepted: the card shows "n 3" beside "from all 33 past ETH 1D signals". `index.html:423` and `feedcheck.py:118` test only that the digits occur in the text. |
| `feed_live.py` re-run a day later with outcomes all "success" (3 quiet dates) | Published yesterday's scoring as today's. Needs outcomes that claim steps ran when they did not. Same cause as #3. |
| 16 others, rejected or shown correctly: edge_status rose10 at best 9.96; example `entry_close` 1 cent off the chart file; grade_odds count off by one; open card from another signal; reversed odds_fade rows; past_paths assets swapped; up_first > misses; price 10^9-1 and 0.01; share 70 vs exact 69.999999; HTML/script in every text field; unicode and 5000-char text; deep junk field; 6.5e1 exponent; duplicate keys (both orders); reordered card list | Rejected as "Data unavailable", or shown with the file's own values and no script error. Markup is escaped. |
