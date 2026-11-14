# Audit 28c: damage audit of the ETHKROS member page and pipeline

Independent. Nothing in the repo was edited. Every run used copies of the two frozen states (`replay_0414`, clock
2026-11-12T04:14Z, and `current`, candles to 14 Nov, clock 2026-11-14T03:12:30Z). Details are in `all_checks.csv`
(1,105 rows) and `disagreements.csv`. Code is in `code/`. This work checks entry-quality figures only. The data has
no exits, so nothing here is a strategy return or a track record.

## Top line

**3 causes, shown in 6 disagreement rows (real-life damage only):** 2 at pipeline level and 4 at page level
(2 causes × 2 states). There were no wrong figures, no script errors, no raw placeholders, nothing read as a
return, trade or track record, and no damaged input scored and published without being withheld.

| Family | Rule (from the code) | Page cases tried / got through | Pipeline cases tried / got through |
|---|---|---|---|
| 1 Missing | page: any file that does not arrive reads "unavailable"; pipeline: `check_fresh`, `fetch.history_problems`, the seal, feed_live's required files and alert-log check | 64 / 0 | 129 / 0 |
| 2 Malformed | page: `FEED_SCHEMA` + `crossCheck`, ledger/chart/example/trades checks; pipeline: `history_problems` (every row and cell), the strict check before publishing | 157 / 0 | 304 / 0 |
| 3 Wrong content | page: chart names its chart, ends no later than the feed, closes at `price_now`; ledger matches `grade_odds`; example matches the card; pipeline: asset/timeframe/bucketing checks, seal hashes, alert-log hash | 36 / 0 | 80 / 0 |
| 4 Partial run | seal (order, files unchanged, one run), strict `CTZB_STEP_OUTCOMES`, extras clears its outputs, feed before log | 10 / 0 | 114 / **2** |
| 5 Timing | freshness (today's 1D bar, current 4H bar), stack's today check and lag rule, seal age 2 h; page: 5-hour and daily-close notes on the viewer's clock, per-year count on full years | 34 / 0 | 19 + 8 calendar replays / 0 |
| 6 Delivery | page strict checks; a slow file shows "Loading"; a late file is not drawn | 90 / **4** | 8 / 0 |

**States tried:** 443 page states (245 `current`, 198 `replay_0414`; every tab, every picker button, the example switch
and both chart modes on each, with pageerror/console capture and a placeholder scan of all text, SVG text included),
640 pipeline runs (344 input, 300 between-step, unsealed-config, outcome, kill, order, concurrency and clock cases),
10 alert-log sequences (2 to 3 runs each), and 8 calendar-boundary replays (2021-01-01, 2024-02-29, 2024-03-01,
2025-01-01, 2025-12-31, 2026-01-01, 2026-03-01, 2026-03-02), each rendered on the page as well.

| Level | (i) wrong/unsupported figure | (ii) placeholder, script error, blank area | (iii) damaged input scored or published unwithheld | (iv) wording misstates the state | (v) reads as return/trade/record |
|---|---|---|---|---|---|
| Page | 0 | 2 | 0 | 2 | 0 |
| Pipeline | 0 | 0 | 2 | 0 | 0 |

## Every disagreement

| # | Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|---|
| 1 | pipeline | current + pending alerts | extras step fails (non-gating), so the run goes red and the automatic re-run comes 1 min later | run 1 published 6 alerts and logged them; the re-run published `alerts: []` over them 5 min later | an alert is never lost to a red run | `feed_live.py:349-371` carries an alert in exactly one generation. `retry_after_failure.sh:6` re-runs after 1 minute. The mirror pulls every 15 min (`cloudflare/README.md:20`) and `ctzb-dashboard-worker.js:199` sends only the current feed's `alerts`. A :13 run commits after the :15 pull and its retry commits before the :30 pull, so the sender never sees run 1's generation, while the log marks those alerts sent |
| 2 | pipeline | current + pending alerts | a fetch after the feed fails (flows/onchain/derivs outage), so the run goes red and is re-run | same: 6 alerts replaced by `[]` | same | same; `daily.yml`'s "Fail the run" step counts the third-party fetches |
| 3, 4 | page | current, replay_0414 | feed file slow (still loading); member opens Chart or Past signals | Chart: "Data unavailable" and "Can't reach the data right now." Past signals: "Past signals unavailable right now". Header: "Loading…" (screenshot `shot_slowfeed_chart.png`) | "Loading" | `index.html:590` `feedHealth()` returns "down" whenever `S.feed` is null, before arrival too. `renderChart` (:905-908) and `renderRecord` (:1140) test `S.loading`, which is set only at :1225 after the feed arrives. `test_page_timing.py` checks only the Now card |
| 5, 6 | page | current, replay_0414 | feed file slow | setup picker and Previous signals panel empty (headings only, no "Loading") on every tab until the feed arrives | "Loading" in each area | `index.html:1227`: `renderPicker`/`renderPrev` first run after `await get(feed)` (:1217) |

## What failed safe, by family

- **1 Missing.**
  - Page: feed 404, 500, 503 HTML, abort, empty or HTML-200 in both states, every other file alone, all files, and all but the feed. The result was always "Data unavailable" / "Past signals unavailable" / "Chart data unavailable" / lead "unavailable", with the other files' figures still correct.
  - Pipeline: any candle, funding, long/short, OI or put/call file deleted, emptied or header-only stopped at `check_candles` or `check_fresh` (75). Any dataset, `stack_status.txt`, `candle_check.json`, `manifest.json` or alert log lost between steps gave a held or fail-closed feed (41). A lost `analysis/grade.json`, `grade2.json`, `grokpack.json`, `PRETRADE.md`, `tests/baseline/ledger.json` or page file gave a held feed. Losing `troughs.json`, `odds.json` or `keep.json` changed no figure.
- **2 Malformed.**
  - Pipeline: 8 candle files × 34 damages (duplicated, swapped, deleted rows; dropped or renamed columns; text, blank, negative, zero, nan or inf cells; cut lines; extra header; off-grid time). Every damage that touches a scored file stopped the job. CRLF stayed byte-for-byte harmless. A BOM stopped the job. A trailing blank line on 2D/3D/5D/8D passes `check_candles` but crashes `engine.load`, so the feed was held: safe but over-strict.
  - Pipeline: every dataset at feed time × 8 damages gave a fail-closed feed (128).
  - Page: feed cut at 0.05% to 99.9%, missing its last 2 bytes, UTF-16, gzip bytes, NaN token, doubled, spliced from two runs or NUL-padded: all "Data unavailable". BOM-prefixed, whitespace-padded and compact feeds rendered correctly. Ledger, chart, example and lead-trader files with 25, 16, 9 and 20 kinds of damage each read "unavailable" or showed correct figures.
- **3 Wrong content.**
  - Pipeline: another asset's or timeframe's file, or an older run's copy, stopped the job (candles) or broke the seal (datasets). An older run's funding or ratio series tripped the lag rule (held).
  - Page: chart files from the other run or asset, 2D bars under a 1D name, a different last close, or one bar newer than the feed all read "Chart data unavailable". An example file 1 cent off, BTC bars, shifted or cut read "unavailable". A ledger with swapped assets, one top-grade row short, or one extra unclosed row read "unavailable". The other run's identical ledger was accepted correctly.
- **4 Partial run.**
  - Kills: refresh, grade (×2), extras, stack (×2) and cards killed mid-run. Extras is non-gating, so only the extras fields were withheld and its chart files went missing; every gating kill held the feed.
  - Order: grade/stack/cards/refresh skipped; stack before extras; cards before stack; extras after cards; grade before refresh. Each step repeated; a second refresh after each step; two runs interleaved in one checkout; new candles landing mid-run. All held or correct.
  - Outcome strings: wrong case, typo, semicolons, missing key, empty value, `extras=cancelled` or `skipped`. All withheld (safe).
  - Alert sequences, all correct with no alert lost or emitted twice: held→clean, fail-closed→clean, died-before-log→clean, died-before-log→fail-closed→clean, died-before-log→held→clean, and two fail-closed runs→clean.
- **5 Timing.**
  - Clock a day ahead or behind, 4 h behind, 23:59:59 with the freshness check, 04:00:30 before the new 4H bar, a fetch-and-refresh split across midnight, a run before today's bar exists, a seal from the future, and feed_live re-run 2 h 01 min later: all held or stopped.
  - 00:00:00, 23:59:59 (scoring only), and feed_live re-run after 30 min or 1 h 59 min all published correct figures.
  - Page: 4 h 59 min vs 5 h 1 min, 3 days, 2 years, feed in the future, left open 5 h then 7 h (hour count follows), quiet feed left open (auto example turns off), across 00:00 UTC (daily-close note), 1 January, and the per-year sentence at scored 2027-03-01/02 and 2028-02-29/03-01: all correct.
- **6 Delivery.**
  - Slow ledger, trades, example and chart files read "Loading". A late chart file is not drawn over the setup picked meanwhile. Markup in every free-text field was shown as text and never run.

## Hardening (not counted)

- 25 hand-forged contradictory feeds. The rules rejected 18 (+20 above +10%, eras, id/date, wrong card, duplicates, misses vs grades, path order, withheld flag, rose10 with best 5, scored after generated, early day-10, example id, odds mark, entry close, ladder counts, low after confirm, quartiles), and the lost/edge-level forgery was rejected too.
- Accepted with no rule:
  - A `sample` text naming a larger number that contains the count ("all 1N5 signals" passes `includes`).
  - `bars_to_confirm` 2 with a `must_close_above` price, worded as an exact "if it closes above $X".
  - A live card's `price_now` that matches no chart (the chart then reads unavailable).
  - `market_regime` Bearish with forming cards.
  - Card and live-signal order (sorted by the page).
- Pipeline: a valid but empty `tests/baseline/ledger.json` (`{"n":0,"rows":{}}`) silently turns off the regression guard. Published figures were still correct.
- 11 unusual-but-valid boundary values were all shown as the file's own values: 0 and 100%, day 0 and 60, price 0.01 and 999,999,999.99, confirmation on 1 Jan or 29 Feb 2028, rise 99,999%, dip −100%. 29 Feb 2027 was rejected as not a date.

## Not counted, by the stated exclusions

- 4H/12H rows deleted mid-file (the exchange has gaps) and a stale 12H file. Neither is scored, shown or under the freshness rule, and the figures were unchanged.
- A blank put/call day: valid, since it means no trades that day.
- An older run's dataset copies that are byte-identical to this run's (15 files never change between the two states). These are no-ops.
- Restoring `feed/` (feed plus log) from an older snapshot would re-emit alerts. That is a rewrite of a file together with its alert-log record, which is outside the claim.

## Repo's own tests (on a copy)

`test_seal.py` 23/23 passed. `test_page_timing.py` 11/11 passed. `test_feed_damage.py` with `RENDER_LIMIT=40 REJECT_LIMIT=10` passed 31/31, on this repo and a replay of 12 Nov.

What they do not cover:
- The Chart and Past-signals tabs (and the empty picker and Previous-signals panels) while the feed is slow. The timing test checks only the Now card.
- Alert delivery across a red run and its 1-minute retry. The tests check the log, not what the sender can see.
- Damage to inputs between steps, killed or reordered steps, and concurrent runs with real candle changes. These are partly in `test_seal.py` (23 fixed cases), not systematically.
- The quick pass renders only 40 accepted kinds and 10 rejected kinds per state.

## Could not test

- The live Workers (mirror timing, the dashboard's KV dedup, the site Worker's CSV conversion). I reproduced the conversion from `site_worker_template.js` and took the timing from the README and the workflow.
- The Kraken cross-check, which has no network here (recorded as "unavailable", as designed).
- The real GitHub runner (the `timeout`, commit and push steps).
- A real browser network stack for partial TCP delivery: I used whole bodies cut at chosen points instead.
- The trades relay, which is 404 in this harness. I served the lead-trader shapes myself.
