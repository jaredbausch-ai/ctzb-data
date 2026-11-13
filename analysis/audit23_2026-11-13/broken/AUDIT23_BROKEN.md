# Audit 23c: broken, damaged, missing, stale and slow files, and failed runs

Scope: the member page and the pipeline, on copies of the two frozen states (`a23/replay_0414`, `a23/current`) plus real pipeline outputs I produced from them (a held run, a fail-closed run, a run with extras killed, and replays at 2025-12-31 23:58, 2026-01-01 00:13 and 2024-02-29 04:14). I wrote down what a correct result looks like before running each case. All code is my own: `ph.py`, `pagebat.py`, `run_pages.py`, `cases_extra.py`, `race.py`, `stale_open.py` (page), and `pipe.py`, `pbat.py`, `run_candles.py`, `run_derivs.py`, `run_between.py`, `run_misc.py`, `run_alerts.py`, `gen_states.py` (pipeline). Nothing in the repo was edited.

Entry quality only. These are computed signals, not fills, and the data has no exit.

**The repo changed while I worked.** Commits 3c45354, 404d32a and cf223d9 (HEAD cf223d9) landed during the audit and address most of what is below. The counts are against the frozen states' code. A short re-test on HEAD is at the end.

## Top line (real-life damage only; hardening is not counted)

| Level | States tried | Disagreements | (i) wrong or unsupported figure | (ii) placeholder, script error or blank | (iii) damaged input scored or published | (iv) wording misstates the state | (v) reads as a return, trade or record |
|---|---|---|---|---|---|---|---|
| Page | 135 | 12 | 6 | 2 (1 of them also in i) | 0 | 5 | 0 |
| Pipeline | 990 | 18 | 0 | 0 | 18 | 0 | 0 |

The pipeline count includes 35 no-op states where the damage left the file byte-identical (for example an older run's copy that matched). All 35 published the same figures and are not disagreements.

## Every disagreement (counted)

Rows with the same cause are grouped. `disagreements.csv` has one line per state.

| # | Level | State(s) | What was damaged | Shown | Expected | Cause (file:line) |
|---|---|---|---|---|---|---|
| P1 | page | replay_0414 | Feed slow to arrive (held open) | Header "Market filter …", an empty card area, empty picker and panels, no loading or unavailable text, until the request ends | A loading or "unavailable" state | index.html:1190-1201: `boot()` awaits the feed before drawing anything, and `get()` (361-364) has no timeout. The static HTML has an empty `#card` |
| P2 | page | replay_0414 | Chart file slow (BTC_1D held) | Chart tab keeps the previously drawn setup's chart, title and side figures ("BTC · 2D · live setup, day 52") while BTC 1D is selected. On a fresh load straight onto #chart the chart is blank | A loading state for the selected setup | index.html:884-899: nothing is cleared before `await candlesFor(c.chart)` |
| P3 | page | replay_0414 | Chart file arrives after the member has moved on (BTC_1D late, ETH 2D selected) | The chart switches to BTC 1D, with "Low 10 Nov 2026 · $72,643.48", while ETH 2D is selected | ETH 2D's chart | index.html:885/899: `c = selected()` is read before the await and drawn after it with no re-check |
| P4 | page | replay_0414 ×4 | Chart file of the other asset served under the name (ETH_1D←BTC, ETH_2D←BTC, BTC_1D←ETH, BTC_2D←ETH) | Accepted. For example, an ETH 1D forming chart drawn with BTC candles, labelled "Low 10 Nov 2026 · $72,643.48" (ETH's low that day was $2,003.24) | "Chart data unavailable" | index.html:901-903 checks the name, structure, steps and end time only. site_worker_template.js `handle()` labels the bars with the requested name, and for a forming setup nothing ties the prices to the asset |
| P5 | page | replay_0414 | Example chart file slow, example switch on, Chart tab | "The example's chart data couldn't be loaded." while it is still loading | Loading (README: "Loading…" meanwhile) | index.html:889-892: `S.example` is null during loading and is treated as failed |
| P6 | page | current ×2, replay_0414 ×2 | Page left open (#now, #record) while the feed ages 6 hours, then a tab switch | No "hours old" warning at any point | The 5-hour warning | index.html:590-602: `staleNote`/`staleBars` run only on a render (`renderHeader` at boot, 1201). There is no timer and no re-fetch |
| D1 | pipeline | current ×4 | 4H/12H file of the other asset (ETH_4H, BTC_4H, ETH_12H) or of the other intraday timeframe (ETH_4H←ETH_12H) | Passes check_fresh and check_candles. Run green, file committed | Run stopped (brief: a swapped file must not get through) | fetch.py `history_problems`: 4H/12H get row and grid checks only, and the ETH/BTC ratio is checked on daily closes only. No scoring step reads 4H/12H (traced), so no member figure changes |
| D2 | pipeline | current ×5 | `data/derivs/{ETH,BTC}_lsratio_daily.csv` emptied or last 30 rows lost, or ETH/BTC swapped | Published. Feed unchanged, `datasets/liveread.csv` (read by the operator dashboard) changed | Stopped or withheld | stack_live.py:177 `series(...)` reads it unchecked. It is not in `history_problems` and not in the seal (seal.py `_files` covers `*_funding_daily.csv` only) |
| D3 | pipeline | current ×5 | `data/derivs/{ETH,BTC}_oi_daily.csv`, same damages | Same as D2 | Stopped or withheld | stack_live.py:178, same gap |
| D4 | pipeline | current ×3 | `data/options/BTC_pcr_daily.csv` deleted, emptied, or last 30 rows lost | Same as D2 (K1 read) | Stopped or withheld | analysis/pcrtest.py:66-73 `load_pcr` returns {} for a missing file. Unchecked, unsealed |
| D5 | pipeline | current | `BTC_funding_daily.csv` with its first 100 rows lost | Published, liveread.csv changed | Stopped | `history_problems` checks funding for gaps and recency but not its first day. ETH's equivalent was caught only by the regression guard, because FUND is an ETH lens |

**Not counted, with the reason:**
- `CTZB_STEP_OUTCOMES` missing while the regression step failed publishes cards. This is the documented hand-run rule (FEED_SPEC Audit #21).
- An older `candle_check.json` republishes stale Kraken statuses. This cannot happen in a real run: check_candles rewrites the file and a failure stops the run first.

## What failed safe, by family (frozen states)

| Family | States | Result |
|---|---|---|
| Candle files 1D–8D, 4H, 12H (dup, swap, delete first/mid/last, cut start, column lost or renamed, text, blank, negative, zero, NaN, inf, truncated last line, CRLF/LF, BOM, blank tail/mid, extra header, header only, emptied, deleted, other asset, other timeframe, time shifted) | 247 | 176 stopped at check_fresh/check_candles, 10 withheld, 1 fail-closed, 34 published identical (format-only damage or unused columns), 22 4H/12H gaps passed by design, 4 = D1 |
| Funding, L/S, OI, put/call files | 74 | 26 stopped, 16 withheld (regression or stack crash), 18 identical, 14 = D2–D5 |
| `datasets/*` deleted, emptied, cut, header-only, last row lost, row duplicated, figure altered, or an older run's copy, before each of grade, extras, stack, cards, regress and feed | 607 | 354 fail-closed, 210 withheld, 8 extras-only withheld (cards published, by design), 35 no-op. Every change was caught by the seal |
| Alert log (deleted, emptied, header-only, cut, duplicated row, reordered, mid-row cut, older copy), previous feed lost or cut, repeat run, held-then-clean, died between feed and log, two runs at once | 18 | No alert lost or sent twice in any state. Damaged logs fail closed and stay held until reseeded. The run after a died-before-log run rebuilds the log |
| Outcomes env (typo, case, `;`, missing step, skipped, cancelled), steps out of order, twice, missing, killed mid-step, clocks ±1 day, 00:00:00, 23:59:59, grade/grokpack/baseline/page/PRETRADE damaged, feed folder lost | 44 | All withheld, fail-closed or stopped, except 6 correct publishes (all steps passed) and the 2 not counted above |
| Page: every file 404/500/502 HTML/200 HTML/empty/truncated/last bytes cut/other file's content; slow ledger, trades, example; stale, future and midnight clocks; feed/ledger/chart/example from other runs; chart CSV damage via the worker parser; ledger cuts, doubles, shuffles, CRLF, BOM; 14 lead-trader shapes; real held, fail-closed, extras-withheld, year-end, new-year and leap-day feeds | 135 | 123 correct: the right figure, or the stated "unavailable"/"held back" text, with no script error, raw placeholder or blank, and nothing reading as a return. A held or down feed never reads as quiet, the example never stands in for an outage, and no lead-trader row shows a dollar size or contract count |

## Hardening (not counted)

| State | Hand-forged damage | Shown | Note |
|---|---|---|---|
| replay_0414 | Feed with `odds_fade` missing, or null. Both are allowed by the schema (`odds_fade?`), and feedcheck.py accepts both | Script error "Cannot read properties of undefined (reading 'early_dip')". The page stays blank: header "Market filter …", no card, no picker | index.html:1197 on the frozen page. HEAD:1205 adds the null guard |

The other 23 forged cases behaved correctly: markup in every text field (escaped, no script ran), 20k-character or unicode text, duplicate keys, exponent numbers, nested junk, prices of 0.01 and 999999999, a share of exactly 70 or 69.999999, shares of 0 and 100, day 0 and day 60, a live signal with another signal's card, eras that don't add up, +20% above +10%, counts one more than the ledger, a status that contradicts its prices, sections from another run, cards reversed, an example entry off its file, an odds-fade mark against its share, and 29 Feb ids. Contradictions read "Data unavailable" or "Past signals unavailable", and accepted files show their own values.

## C. The repo's own tests

- `tests/test_seal.py`: passes, 18/18.
- `tests/test_feed_damage.py` (RENDER_LIMIT=40, REJECT_LIMIT=10):
  - First run: 30/31. The failure was mine: I set TMPDIR inside the repo copy, so the replay tarred itself. The test then carried on with a replay that had not built and still reported its checks as passing.
  - Second run, clean: 30/31, with one real failure: "feed.odds_fade missing → Cannot read properties of undefined". This is the hardening row above.
  - It renders a random 40 of about 510 accepted kinds, so a quick pass can miss that case. My first run did.
- What it does not cover: slow files and late arrivals (P1–P3, P5), a file of the other asset under a chart name (P4), a page left open (P6), any pipeline input other than the feed, ledger, trades and chart files (D1–D5), the alert log, and run order.

## Re-test on HEAD cf223d9 (not in the counts)

Same harness, HEAD page and code, frozen data. 23 page states and 11 pipeline states.

- **Fixed on HEAD:** P1, P3, P4, D1, D4, D5, and D2/D3 for emptied or cut files.
- **Still present on HEAD:**
  - P2: while a chart file loads, the Chart tab still shows the previous setup's chart and title. After a fresh load on #now it shows the static title "ETH · 2-day · past confirmed setup" over a blank chart.
  - P5 and P6 (×4) are unchanged.
  - ETH/BTC swapped `lsratio` and `oi` files still pass and change liveread.csv. The new checks don't tell the assets apart.

## Could not test

- The live Kraken cross-check: there is no network, so check_candles ran with Kraken "unreachable".
- The real Cloudflare Workers, the mirror, Access, and cache behaviour. The worker's CSV-to-JSON step was emulated exactly from `site_worker_template.js`.
- GitHub concurrency groups, retries and pushes. Two runs at once were tested in one folder only.
- fetch.py against the exchange: damage was applied to the files it would have written.
- Viewer devices other than desktop Chromium at 1440×900.
- A real 31 Dec short bar on a selected forming 2D–5D setup: the year-end replays had no forming cards.
