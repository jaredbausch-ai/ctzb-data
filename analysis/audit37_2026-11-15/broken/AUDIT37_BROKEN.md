# Audit 37c: damage audit of the ETHKROS member page and pipeline

This audit was independent: I wrote all the harness code myself and ran everything on copies of the two frozen states. Nothing in the repo was edited. These results measure entry quality only. None of them is a strategy return, a fill or a track record.

Details are in `all_checks.csv` (1,687 rows) and `disagreements.csv` (17 rows: 13 counted, 4 hardening) in this folder. The harness scripts are here too.

## Top line

**Counted disagreements: 13 check rows, from 2 causes, all at the pipeline level. The page level has none.**

| Level | Checks run (counted) | Disagreements | Hardening tried / got through |
|---|---|---|---|
| Page (Playwright, every tab, every picker button, the example switch and both chart modes) | 207 | 0 | 25 / 4 |
| Pipeline (the daily.yml chain run step by step, each step's outcome taken from its exit code, feed_live last) | 1,455 | 13 (2 causes) | n/a |

### Per family: cases tried / got through

| Family | General rule meant to catch it | Page | Pipeline |
|---|---|---|---|
| 1 MISSING | Page: `get()` returns null on a non-OK response or a throw, so the area reads "Data unavailable" or "unavailable". Pipeline: history_problems "is missing", the required files in feed_live, the "missing" check in seal, check_log | 37 / 0 | 168 / **1** (D2) |
| 2 MALFORMED | Page: FEED_SCHEMA with shapeCheck and crossCheck, parseCSV `dropped`/`cut`, barsOk/stepsOk, and the Worker's csvToBars. Pipeline: `fetch._file_problem`, `_row_problems`, `history_problems`, and seal hashes | 22 / 0 | 955 / **12** (D1) |
| 3 WRONG CONTENT | Page: chart name, price_now and entry_close must match to the half cent; ledger rows must match grade_odds counts; example entry close must match. Pipeline: ETH/BTC close ratio, market columns, 2D–8D equal to the daily bucketed, the 4H/12H 25% check, and the seal | 30 / 0 | 128 / 0 |
| 4 PARTIAL RUN | The seal (step order, finished steps, file hashes), gating on CTZB_STEP_OUTCOMES, and the alert-log record plus its copy | 15 / 0 | 188 / 0 |
| 5 TIMING | check_fresh (today's 1D bar and the current 4H bar); stack_live's "today" check; seal age of 2 hours or less; scored_as_of must be generated_at's day. Page: 5-hour and daily-close notes | 18 / 0 | 16 / 0 |
| 6 DELIVERY | Page: `get()` plus JSON parse, the strict check, the cut-file rule and the Worker's csvToBars (emulated) | 85 / 0 | (no pipeline-side delivery; files arriving cut short are under MALFORMED) |

**States tried:**
- `current` (15 Nov, 6 forming setups) and `replay_1111` (11 Nov, 4 forming setups).
- A setup built from replay_1111's feed and log rolled back to the 11 Nov 04:14 run, plus the 15 Nov candles, so that alerts would be pending.
- Replays made with the frozen code's own `tests/replay_at.sh`: 2026-01-01 00:05, 2025-12-31 23:55 and 2024-02-29 04:14. All three ran clean and rendered with no error, placeholder or blank area.

**Disagreements by kind (real-life damage only):**

| Kind | Page | Pipeline |
|---|---|---|
| (i) a wrong or unsupported figure shown | 0 | 5 rows (D1 on 1D, 2D and 3D files; D2): a clean feed with changed cards |
| (ii) a raw placeholder, script error or blank area | 0 | 0 |
| (iii) a damaged input scored or published without being withheld | 0 | 13 rows: all of D1 and D2. The 5 rows in (i) are among them |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement (counted)

| # | Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|---|
| D1a | pipeline | current | data/ETH_1D.csv gains a second column named `close` (the real close). The first `close` is changed on the last 3 rows only, still within each row's high and low | Clean feed. The ETH-1D-2026-11-17 forming card is gone, and the ETH open signals' card price_now reads 1709.49 instead of 1827.98 | Job stops at check_candles | `fetch.py` reads the rows with csv.DictReader (`_row_problems`; `history_problems` at fetch.py:335). There the **last** column of a repeated name wins. `engine.load` (engine.py:79–90) scores the **first** numeric column of that name |
| D1b | pipeline | current | data/BTC_3D.csv, same damage | Clean feed; cards and prints changed | Job stops | Same as D1a |
| D1c | pipeline | replay_1111 | data/ETH_1D.csv, same damage | Clean feed; cards, open_signals and prints changed | Job stops | Same as D1a |
| D1d | pipeline | replay_1111 | data/BTC_2D.csv, same damage | Clean feed; cards and prints changed | Job stops | Same as D1a |
| D1e–l | pipeline | both | A repeated `close` column, first or last copy bad, in BTC_4H (current) and in ETH_4H, ETH_12H and BTC_12H (replay_1111): 8 rows | Passes every check and is committed. Figures are unchanged, because 4H/12H are not scored | Job stops | Same as D1a. The 25% asset check reads the last `close` |
| D2 | pipeline | replay_1111 | data/derivs/ETH_funding_daily.csv loses its last row (today, 2026-11-11), cut at a line end | Clean feed. ETH 1D's confirmations change from "funding at or above its 90-day median" to "none" (n 17 becomes 27, +10% share 65 becomes 67). ETH 2D changes too (n 27 becomes 15). Every figure on both cards changes | Withheld, or figures that do not depend on whether today's partial funding row exists | `fetch.MAX_LAG_DAYS` funding=1 (fetch.py:229) accepts a series one day behind, and the FUND read then takes yesterday's value. The same damage on `current` changed nothing; the other series (L/S, OI, put/call) changed nothing in either state |

Whether these can happen in real life:
- **D1:** fetch.py writes a fixed header, so a repeated column needs a writer change, a merge or a hand edit. I counted it anyway, under guarantee (5) ("wrong columns … that gets through") and the rule for unsure cases. A whole bad first `close` column (`dup_close_col_first_bad`) on 1D–8D was caught only by the regression guard (the feed was held: `regress`). Bad values confined to recent, unsettled rows get past that guard.
- **D2:** this is a fetch that did not write today's partial row, or a file cut at a line end. The spec counts a one-day lag as normal, so the history check cannot tell this apart from the lag. Is a funding series that ends yesterday meant to be scored as current? If yes, D2 is accepted behaviour; it is still listed because the cards depend on it.

## Hardening (not counted): hand-forged feeds that the page accepted

Each was valid field by field but contradicted itself. They were accepted and rendered with no error:

1. `sample` reads "all 127 ETH 1D signals" while `past_trades` is 27. `sample.includes(String(n))` matches the substring (index.html crossCheck, `card()`).
2. Two forming cards for the same chart (ETH 1D, confirming on the 17th and the 18th).
3. A forming card that confirms on 2099-01-01. Only "not before today" is checked.
4. A forming card whose `low_date`/`low_day` is after the feed's date. Only low_date ≤ low_day ≤ confirms_on is checked.

Note: forming cards tied on the +10% share keep the feed's order, so the feed order decides which one reads "Best setup forming today".

21 other forged or boundary cases were rejected ("Data unavailable") or shown exactly as in the file: impossible share for its n, card from another signal, figures out of order, quartiles, misses, grade_odds against past_paths, price extremes ($999,999,999.99 shown exactly), day 0/60, exact 70 against 69.999999. Markup in every text field shows as text: I re-checked that no element was injected and no handler ran.

## What failed safe, by family (counted checks)

| Family | Page | Pipeline | How |
|---|---|---|---|
| MISSING | 37 | 167 | Page: 404/500/502/503/abort on the feed, ledger, example, trades and chart files each read the right "unavailable" or "Feed unavailable", and the rest of the page was unchanged. Pipeline: deleted datasets between steps were refused by the seal or failed closed; deleted log, feed or copy were restored, or failed closed |
| MALFORMED | 22 | 943 | Bad trade shapes read "unavailable". Candle files: duplicated, reordered or deleted rows; text, blank, NaN, inf, zero or negative cells; cuts, BOM, NUL, UTF-16, blank lines, extra headers and off-grid times all stopped the job. CRLF/LF, mixed line ends, quotes, whitespace, extra columns and exponent forms published identical figures. time-as-float in multi-day files ended in a hold |
| WRONG | 30 | 128 | Another asset's, another timeframe's or another run's chart files read "Chart data unavailable". Ledger ±1 top-grade row, or a duplicate, read "Past signals unavailable". A changed example entry close read unavailable, including when the example file arrived before a slow feed. Pipeline: asset or timeframe swaps and other-run candle or series files stopped or were held; altered datasets failed closed |
| PARTIAL | 15 | 188 | Held and fail-closed feeds read "Setups held back", with no example standing in. Outcomes unset, empty, typo, cancelled or missing; kills of each step (with and without outcomes); stack/cards killed but reported success; out of order, skipped, twice, or two runs in one folder: all withheld, or clean with figures identical to an uninterrupted run. Alert log: held, fail-closed, died between feed/copy/log, deleted, emptied, cut, duplicated or CRLF logs, lost or cut previous feed, cut copy: no alert lost or logged twice, and pending alerts went out once on the next clean run. An altered row, or a log and copy both gone, failed closed |
| TIMING | 18 | 16 | Stale warnings appeared at 5 h 01 m, after 4 years, and on a page left open 6 h, on all four tabs. The daily-close note appeared; a quiet feed's example went off when stale. Pipeline: clock ±1 day and 23:59:59 stopped at check_fresh. Midnight between scoring and feed, cards after midnight, feed 2 h 01 m late, and the clock stepping back all failed closed. Stack after midnight, and a run before today's candle, were held. 00:00:00 and 23:59:59 (checks skipped) published identical figures |
| DELIVERY | 85 | – | Feed: cut at 0–99.9%, HTML 200, null/[]/{}, UTF-16, concatenated, trailing junk, gzip bytes, random bytes, or the wrong file all read "Data unavailable". A BOM'd, minified, re-keyed, exponent-form or unicode-escaped feed gave the same page. A slow feed or ledger gave the same page, because the ledger and example handlers wait for the feed. Ledger, example, chart and trades files that were cut, HTML or empty read unavailable |

## Repo tests (part C), on a copy of `current`

| Test | Result |
|---|---|
| tests/test_seal.py | 29/29 pass |
| tests/test_page_timing.py | 20/20 pass |
| tests/test_feed_damage.py (RENDER_LIMIT=40 REJECT_LIMIT=10, this state plus its own 2026-11-12 replay) | 33/33 pass |

What they do not cover:
- Repeated column names in candle files (D1).
- A series' last row lost within the allowed lag (D2).
- Cross-run mixes of feed, ledger, chart and example files at the page.
- Step-order permutations beyond "twice" and "out of order".
- Kills with no CTZB_STEP_OUTCOMES.
- Midnight falling between individual steps.
- Year-end or leap-day page renders.
- Hand-forged cross-field contradictions such as the 4 hardening cases above.

## What I could not test

- **The Kraken cross-check:** there is no network. check_candles ran with Kraken treated as unreachable, which is the "not a failure" path.
- **fetch.py itself:** it needs the network. I injected damage after the fetch.
- **The live Cloudflare Worker and the mirror's pull timing:** I emulated the Worker's csvToBars in Python and served files through Playwright routes.
- **Git commit and push:** I emulated a lost push by reverting files.
- **The GitHub concurrency group:** I tested two runs at once only in one folder.
- **Other browsers:** Chromium only.
- **test_feed_damage at full size:** I ran only the quick pass.
- **Partial HTTP bodies:** truncated bodies stood in for real slow chunked transfers. A request that never completes was not tested (the slowest case was 2.5 s).
