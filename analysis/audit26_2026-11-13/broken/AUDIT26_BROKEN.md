# Audit #26, broken states (independent)

Code tested: the frozen states `a26/replay_0414` and `a26/current` (copies only; the repo was not edited). Repo HEAD moved to
b6eb046 during the audit (docs and comments only); results are for the frozen-state code. Entry quality only: everything here is
computed signals, not fills, not a return or a track record.

## Top line (real-life damage only)

| Level | States tried | (i) wrong or unsupported figure | (ii) placeholder, script error, blank | (iii) damaged input scored or published | (iv) wording misstates state | (v) reads as return, trade, record | Disagreements |
|---|---|---|---|---|---|---|---|
| Page | 192 | 6 | 0 | 0 | 0 | 0 | **6** |
| Pipeline | 1,156 | 10 | 0 | 24 | 0 | 0 | **34** |
| **Total** | **1,348** | **16** | **0** | **24** | **0** | **0** | **40** |

These 40 come from **2 root causes**. Not counted: 48 hand-forged feeds (hardening, all handled correctly) and 55 pipeline
cases where damage reached a file or column that no scoring step reads (listed below).

## Every disagreement (grouped by cause; one line per case in disagreements.csv)

| # | Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|---|
| P1 | page | replay, current (6 cases) | Page left open while the pipeline is down: loaded 4.9 h or 6 h after the feed, then left open 1 to 24 h | The stale note keeps the age it had when the data first went stale. At 28.9 h it still reads "This data is 5 hours old", on every tab | The real age, for example "28 hours old" | `index.html` ~l.1221-1226: the 60 s timer redraws only when staleness changes (`if (now !== wasStale)`), so the `Math.floor(age)` text in `staleNote()` is never updated. `test_page_timing.py` checks only that the words "hours old" appear |
| B1 | pipeline | replay (16), current (16) | A 2D, 3D, 5D or 8D candle file cut short exactly after a row's last comma, so the volume cell is blank. Tested on ETH_2D, BTC_3D, ETH_5D and BTC_8D with 0, 1, 3 and 30 bars lost | Passes check_fresh, check_candles and stack_live. The feed is **published**, not withheld. 10 of the 32 cases publish different figures; the other 22 are scored with the same output | The run stops at check_candles ("bars differ from the daily candles") | `fetch.py` l.153 reads a blank volume as 0, so the row passes. Then l.316-319, the 2D-8D bucket check, does `float(volume)`, hits ValueError and does `continue  # already reported above`. Nothing was reported, so the whole file skips the check that would see the missing bars |
| B1a | pipeline | replay (ETH_2D, 1 or 3 bars lost) | as B1 | The ETH 2D forming card is dropped (4 cards become 3) and a **false `ETH-2D-2026-11-16:vanished` alert** is emitted and logged | withheld | as B1 |
| B1b | pipeline | replay and current (30 bars lost on 2D/3D/5D, 8D) | as B1 | Live signals go 23→21 (replay) or 21→19 (current). **False "confirmed" alerts** are emitted for re-dated past signals (for example `ETH-2D-2025-10-17:confirmed` and `ETH-2D-2025-11-10:confirmed` on current). The regression guard ran on current and passed, because the lost bars are recent | withheld | as B1. tests/regression.py only checks rows that are already in its baseline |
| B2 | pipeline | replay, current | A 2D-8D file with one blank volume cell and nothing else wrong | Scored and published (output identical) | Rejected: a blank cell is structural damage | as B1 |

Real life: fetch.py writes each file whole or not at all, so fetch cannot make this cut. Any later cut-short file (a storage or
checkout fault) that happens to end right after a comma takes this path. A cut anywhere else in the line is caught (tested). The
daily file is protected only because check_candles' own `load()` reads its volume with `float()`. stack_live's
`history_problems` call alone would also let a daily file through.

## What failed safe (by family; full rows in all_checks.csv)

| Family | Cases | Result |
|---|---|---|
| Candle files 1D-8D: 42 damages each on ETH/BTC 1D, ETH 2D; 17 on the rest; other-asset and other-timeframe swaps | 720 | Stopped at check_fresh or check_candles, or (trailing blank line on 2D-8D) held back by a later step. CRLF and columns reordered with their header passed, and the feed was identical |
| Funding, long/short, OI, put/call series: 14-15 damages each | 130 | Stopped, or harmless (CRLF, trailing blank line) with an identical feed |
| datasets/*.csv between every pair of steps (deleted, emptied, header only, cut, column lost, row doubled, figure altered, older run's copy, a stray file) | 157 | Next step refused (seal) and the feed was withheld. Two "older copies" were byte-identical (no damage) |
| Inputs changed between steps (ETH_1D, BTC_2D, funding) | 6 | Seal broke, so the feed was withheld |
| Step outcomes (failure, missing, "Success", skipped, cancelled, blank, unset) | 20 | Withheld as specified. extras=failure withholds only the extras fields |
| Steps out of order, run twice, skipped; whole chain repeated | 14 | Withheld, or (repeat) the same clean feed |
| Steps killed part-way (refresh, grade, stack, cards, extras) | 10 | Withheld. A killed extras step withholds only the extras fields |
| Clocks: a day ahead or behind; 00:00:00; 23:59:59; a run crossing midnight; feed_live alone 3 h later | 12 | Withheld or fail-closed. The midnight-edge runs equal the 04:14 run field for field |
| grade.json and the page file deleted, emptied or cut; regression baseline deleted, emptied or cut; candle_check.json missing or false | 19 | Withheld or fail-closed. When the page is cut in half the schema block survives, so the feed was correct |
| Alert log: deleted, emptied, header only, row lost, row doubled, cut mid-row, older copy, CRLF; previous feed deleted or cut | 20 | Fail-closed. CRLF is rebuilt to the recorded bytes, so nothing is lost or re-sent. A lost or cut previous feed with the log intact publishes clean |
| Alert sequences: withheld, crashed, killed between feed and log, repeated, feed lost, push lost | 10 | Every new event was emitted by exactly one published feed and logged once (after a lost push, the next run sends it once) |
| Two runs at once in one folder (both orders) | 2 | The finished run publishes clean; the broken one withholds; no alert sent twice |
| Page: feed 404, 500, empty, cut at 1-99.9%, HTML or login page, wrong file, null, string, BOM; feed, ledger or trades slow | 40 | "Data unavailable" / "Feed unavailable", or "Loading the latest data…" while the feed is slow |
| Page: stale 5h01m, 3 days, 2 years; 4h59m; viewer 3 min behind; held and fail-closed feeds | 18 | Correct warning, or none when the feed is fresh. Held reads "Setups held back"; the example is never switched on |
| Page: chart files (404, 500, cut, HTML, empty, bars cut, doubled, swapped, slow, other run, other asset, other timeframe) | 28 | "Chart data unavailable", or drawn correctly |
| Page: ledger (HTTP failures, cut, HTML, wrong file, CRLF, BOM, reordered, duplicates, extra column, other run, feed of an earlier run); baseline | 37 | "Past signals unavailable", or the correct count |
| Page: lead-trader file in 13 shapes and 8 damages; example file in 6 damages | 38 | Correct "in · long" / "not in" / "out", or "unavailable". No dollar size or contract count is shown even when present in the file |
| Page: real replays (2025-12-31 23:58 viewed across New Year, 2024-02-29, 2026-01-01 00:00, a quiet bear day, 2026-09-21 23:59:59, 2020-12-31) and 16 feeds the pipeline really published | 25 | Figures equal the feed; footer dates follow `scored_as_of`; no placeholders |

Across every page state: no script error, no raw placeholder (including chart text), no blank card area, and no wording that
reads as a return, a trade or a track record. Markup in every free-text field never executed.

## Hardening (not counted): 48 hand-forged feeds

Contradictions: a share above its parent, eras not adding up, a card on the wrong signal, dates out of order, duplicate signals,
reversed paths or bands, miss counts or grade counts off by one, a status against its prices, `days_elapsed` off by one, and
scored-after-generated. All 16 forms × 2 states read "Data unavailable".

Unusual but valid input was accepted, with figures equal to the file's own values: exponent forms, duplicate keys, deeply nested
junk, 6 kB of unicode, script markup, and a price of 0.01. Two forged "exact 70 / 69.999999" edge cases broke the card's own
nesting rule and were correctly rejected, so the bar edge itself was not reached by forging.

## Not counted, listed for completeness

- **4H and 12H files.** Rows deleted at the start or middle, the last 1-3 rows lost on 12H, and blank volume pass the check
  (36 cases). No scoring step reads 4H or 12H; gaps are allowed by design; 4H is current-checked by check_fresh, 12H is not.
- **Blank or text cells in unread series columns** (`funding_oi_weighted`, per-market columns, put/call `trades`/`pcr_prem`; 18
  cases). The checked column is the only one any step reads; the output was identical.
- **Feed file lost and log rolled back together** re-sends alerts. That needs a manual rollback by someone with write access.
- **A slow feed.** The picker row stays empty while the card says "Loading the latest data…" (judged not a blank card area).

## Could not test

- check_candles' second-exchange comparison: there is no network, so Kraken was stubbed as "unavailable".
- GitHub Actions itself (timeouts, the commit and push step, the concurrency group): steps were run by hand in the workflow order.
- The site Worker's CSV-to-JSON conversion and Cloudflare caching: files were served directly. The live trades relay returns 404 here.
- check_fresh and check_candles read the real clock; they were run with the state's clock patched in.

## Part C: the repo's own tests

| Test | Result | What it does not cover |
|---|---|---|
| `test_feed_damage.py` (RENDER_LIMIT=40, REJECT_LIMIT=10, both states) | 30/30 pass | The pipeline side of candle damage (B1); the stale note's hour count; real HTTP shapes such as cut-off JSON or an HTML page with status 200 |
| `test_seal.py` | 23/23 pass | Inputs that pass the candle check while damaged (B1) |
| `test_page_timing.py` (both states) | 9/9 pass each | Checks that "hours old" appears, not that the number is right (P1) |

Files: `all_checks.csv` (1,451 rows), `disagreements.csv` (40 rows), `progress.log`; per-stage detail in `*.jsonl`.
