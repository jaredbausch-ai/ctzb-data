# Audit 24c: broken, damaged, missing, stale or slow files and failed runs

13 Nov 2026, independent. Scope: the ETHKROS member page and the scoring pipeline under real-life damage. Entry quality only: everything here is a computed signal, never a fill, and there is no exit in the data. Nothing in the repo was edited. Details: `all_checks.csv` (every state), `disagreements.csv`.

**The code changed while this ran.** Commit 628160c (18:04 UTC) changed the site worker, the page and refresh.py. Commit 8483047 (18:26 UTC) fixed page finding D1 below; I reported that finding in progress.log at 18:13. The pipeline runs used the code in the frozen state folders. That code matches the repo except one line of refresh.py (the next_buy_date status). Page runs before 18:26 used the earlier page. Every page family was then run again on 8483047 (see the last section).

## Top line (real-life damage only)

| Level | States tried | States in disagreement | Root causes | (i) wrong or unsupported figure | (ii) placeholder, script error, blank | (iii) damaged input scored or published | (iv) wording misstates the state | (v) reads as a return, trade or record |
|---|---|---|---|---|---|---|---|---|
| Page | 281 (+ 22 hardening) | 7 | 1, **fixed during the audit (8483047)** | 7 | 0 | 0 | 0 | 0 |
| Pipeline | 462 | 12 | 4, all open | 0 | 0 | 11 | 1 | 0 |

On the current page (8483047), every page family was run again: 280 real-life states plus the end-to-end case, 0 disagreements. The 22 hardening feeds: 0 problems. Rows are in all_checks.csv, marked `@page 8483047`.

## Every disagreement

| # | Level | States | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|---|
| D1 | Page | 7: BTC 2D chart file missing its last bar or last 3 bars (both states); the other run's BTC 2D file (current state); every chart file from 12 Nov 04:14 under the current feed; the D2 run below | The chart file for the live top-grade setup (BTC 2D, 21 Sep): cut short, or from another run | The chart is drawn as "live setup, day 52 of 60" from the stale or short file (for example, last 2D close 73,927.63 where this run's data has 73,736.44), with no notice | "Chart data unavailable for BTC 2D", which is what forming setups already got | index.html:913 (audited version) compared the file's last close with `c.price_now`. A live signal has no top-level `price_now` (its card does), so only the entry bar was checked (line 920). **Fixed in 8483047. Re-test: 8/8 states and the end-to-end case now read unavailable.** No test was added for it |
| D2 | Pipeline | 1 (end to end) | Extras step fails before it writes (killed) | The feed is published with cards and `extras_withheld: true`, but `datasets/candles_*.csv` are still the previous run's files and are committed and mirrored beside this run's feed | Chart files withheld with the extras fields, or rebuilt this run | extras_live.py:112-125 writes the chart files only near its end. feed_live.py:421-423 withholds the extras *fields* only. Since 8483047 the page refuses these files, so members see "Chart data unavailable" on every chart until a clean extras step |
| D3 | Pipeline | 4: ETH long/short, BTC open interest and BTC put/call cut inside the last line; ETH funding cut so the last day reads `0.00` | A derivatives or options series cut short inside its last row | check_candles and stack_live pass. The run publishes clean and scores the cut value (ls_ratio shortened, funding_mean 0.00, put/call blank) | Run fails closed | fetch.py:178-212 (`_series_problems`) and 255-279 (funding) check only the date and the one value column, never that a row has all its cells. fetch_derivs.py:127 writes in place, not atomically, and the commit step runs after it. In this state no published figure changed |
| D4 | Pipeline | 6: 2D, 3D, 5D and 8D files without the volume column (ETH 2D/3D/5D/8D, BTC 2D); today's ETH 1D bar stamped 01:00 | A wrong column, or a row off the daily grid | Passes every check, scored, published clean | Run fails closed | fetch.py:141-167 (`_row_problems`) reads a missing volume as 0 and does not check daily rows against midnight. Not sure this can happen in real life (fetch.py always writes both); counted because the brief asks for every wrong-column case that gets through. No figure changed: no scoring step reads 2D-8D volume |
| D5 | Pipeline | 1 sequence (4 alerts pending): a clean run killed between the feed write and the log write → a run whose feed step crashes → clean runs | A killed run, then a failed run | The first feed publishes the 4 alerts (none lost or sent twice). After that, **every run fails closed**: "the alert log is not the one the last published feed left (40 rows on disk, 44 expected)". The page holds setups back with no end, while it tells members they "return on the next clean run, usually within the hour" | The next clean run recovers, as it does when the crash is left out (tested: it rebuilds the log) | feed_live.py:512-529: `fail_closed()` carries the last feed's `alert_log` record forward but publishes `alerts: []`. `check_log()` (feed_live.py:166) can only rebuild from the previous feed's own alerts. Only a hand run with CTZB_SEED_ALERT_LOG=1 recovers |

## Hardening (not counted)

These are 22 hand-forged feeds where every field is valid but the fields contradict each other: shares above the share they belong to, eras that don't add up, a ladder bigger than its sample, a live signal carrying another signal's card, duplicate ids, a low after its confirmation, cards confirming before today, withheld but carrying cards, "lost" without a fall, misses not nested, swapped quartiles, reversed odds-fade rows, an example card that doesn't match the example file, and ledger shares against the feed. Every one was rejected ("Data unavailable" or "Chart data unavailable"). Feeds that were unusual but valid were shown with their own values, with no script error: HTML and script markup in every text field (shown escaped, nothing injected), a 100,000-character sample, −0, a +100,000% rise, a 999,999,999.99 price, and edge shares of exactly 70 and 69.999999. **0 problems** on both page versions.

## What failed safe, by family

| Level | Family | Real-life states | Failed safe (held, unavailable, run stopped) | Correct figures shown | Disagreements |
|---|---|---|---|---|---|
| Page | Feed HTTP (404/500/502/503, empty, HTML, cut, null, wrong file, UTF-16, garbage, two feeds joined, slow) | 44 | 40 | 4 | 0 |
| Page | Published feeds and clocks (held, fail-closed, extras withheld, quiet 2022, viewer +4h59/+5h01/+30h/+3y, feed in the future, midnight, 1 Jan) | 27 | 5 | 22 | 0 |
| Page | Ledger (HTTP failures, cut, rows lost or doubled, BOM, CRLF, column lost or renamed, other run, slow) | 46 | 34 | 12 | 0 |
| Page | Lead-trader file (HTTP failures, every action and shape, 60 trades, one asset, dollar size or contracts present, future, unsorted, bad values) | 42 | 24 | 18 | 0 |
| Page | Chart files (HTTP failures, worker-converted CSV damage, other asset, timeframe or run, slow) | 104 | 79 | 20 | 5 (D1) |
| Page | Example file; files from different runs | 12; 6 | 12; 2 | 0; 2 | 0; 2 (D1) |
| Pipeline | Candle files 1D-8D, 4H, 12H (23 kinds each, before check_candles) | 203 | 184 | 13 | 6 (D4) |
| Pipeline | Funding, long/short, OI and put/call series | 50 | 45 | 1 | 4 (D3) |
| Pipeline | datasets/ between steps, and before the feed (the seal) | 166 | 165 | 1 | 0 |
| Pipeline | Order, kills, outcomes, clocks, repeats, grade.json, baseline, page file, previous feed, alert log, and D2 | 36 | 27 | 8 | 1 (D2) |
| Pipeline | Alert log over sequences of runs | 7 | 4 | 2 | 1 (D5) |

Remarks, not counted:
- CRLF line ends or a trailing blank line in a 1D-5D file make refresh crash. The run withholds, which is stricter than needed but never wrong.
- While a slow feed loads, the Previous signals column is empty under its two headings. The card and header say "Loading".
- Three expectations of mine were wrong about the data, and the page was right. A 2022 feed has no 2024 example card, so the page correctly shows "No setup right now, the market filter is off". The worker's `trim()` strips a BOM, so those charts are the real data. A repeated grade step that refused to run changed nothing.

## What could not be tested

- **Kraken cross-check.** There is no network here, so it was stubbed as unreachable, which the pipeline treats as "not a failure".
- **check_fresh.py.** It reads the wall clock, not CTZB_NOW, so stale 1D/4H by real time could not be replayed. 4H/12H files are not read by any scoring step.
- **GitHub Actions itself.** The concurrency group, the retry job, commit and push, and rebase conflicts were not run. "Two runs at once" was not run either: the concurrency group runs them one at a time, and a race inside one folder is not a real-life state.
- **Cloudflare.** KV consistency and the mirror's one-file-at-a-time sync were emulated by serving files from different runs. The worker's access gate and the live trades relay were not exercised; the trades file is 404, so fixtures were used.
- **Browsers.** Desktop Chromium at 1440x900 only.

## Part C: the repo's own tests

| Test | Result | Not covered (found here) |
|---|---|---|
| tests/test_feed_damage.py (RENDER_LIMIT=40 REJECT_LIMIT=10) | 31/31 pass (14 min) | Only malformed chart files. Not a well-formed file that is cut short or from another run (D1), and still no test for the 8483047 check |
| tests/test_seal.py | 18/18 pass | "Extras failed part-way" checks the extras fields but not the chart files left behind (D2) |
| tests/test_page_timing.py | 7/7 pass | Previous signals column while the feed loads |
| none | | Sequences of runs on the alert log (D5); series cut inside a row (D3); 2D-8D volume column and the daily grid (D4) |
