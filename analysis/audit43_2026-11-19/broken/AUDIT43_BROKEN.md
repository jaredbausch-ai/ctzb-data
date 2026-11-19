# Audit 43c: trying to break the ETHKROS member site and pipeline

Independent audit of the frozen states `a43/replay_1111` (clock 2026-11-11T04:14Z) and `a43/current` (19 Nov, 6 forming setups), code at 723244a. I wrote all the code myself (`code/`). Nothing in the repo was edited. The work used copies only.
I also built two more states with `tests/replay_at.sh` for the midnight and 1 January cases: `mid_1118` (2026-11-18 23:59:59) and `ye_1231` (2025-12-31 23:59:59).
This measures entry quality only. Every feed figure is a computed signal, not a fill. Nothing here is a strategy return or a track record.

## Top line

**Real-life damage: 0 disagreements from 3,760 counted cases (page 656, pipeline 3,104).** I also tried 52 hardening cases: 15 kinds of forged contradiction got through (14 on the page, each on both states, and 1 in the pipeline). Those are listed below and not counted. No two-fault case came up.

| Family | Page: tried / got through | Pipeline: tried / got through |
|---|---|---|
| 1 MISSING | 30 / 0 | 116 / 0 |
| 2 MALFORMED | 316 / 0 | 1,942 / 0 |
| 3 WRONG CONTENT | 108 / 0 | 603 / 0 |
| 4 PARTIAL RUN | (pipeline only) | 343 / 0 |
| 5 TIMING | 18 / 0 | 100 / 0 |
| 6 DELIVERY | 184 / 0 | (page only) |
| By design (spec), not counted | – | 18 / 0 |
| Hardening (forged), not counted | 50 / 28 (14 kinds × 2 states) | 2 / 2 (1 kind × 2 states) |

States tried: page level on current (387 cases) and replay_1111 (319). Pipeline level on current (2,349), replay_1111 (747), mid_1118 (14) and ye_1231 (14). The page counts are cases. Each case renders all four tabs, clicks every picker button, the example switch and both chart modes, and makes 30 to 45 captures.

| Disagreement type | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | – |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, a trade or a track record | 0 | 0 |

## Every disagreement (real-life damage)

None. `disagreements.csv` holds only the hardening rows, one per case, each marked `hardening`.

## Hardening (not counted): forged files, every field valid, fields contradicting each other

The page accepted each of these 14 forged feeds on both states (`FEED_SCHEMA` and `crossCheck` have no rule for them), and so would `feedcheck.py`:

| Forged contradiction | What the page showed |
|---|---|
| A card's `sample` says "117 past signals" when `past_trades` is 17 | Card drawn. `crossCheck` only tests `sample.includes(String(n))`, and "117" contains "17" (index.html l.430) |
| `fell30_within60d_pct` 0 with a median deepest dip of −45% | Both figures shown |
| Two forming cards on the same chart (ETH 1D) | Both listed in the picker |
| A forming low dated on its confirmation day (after the feed's date) | Card drawn |
| `bars_to_confirm` 0 when confirmation is days away | Shown as "confirms … if it closes above $X" with no "estimate" wording |
| One card's `price_now` 40× the other same-asset cards' | Card and levels drawn from it (its chart file is refused on price) |
| `past_paths` day 0 median +5% | Cloud drawn from it |
| `example_card` graded C | Shown as the example, styled as top grade |
| `odds_fade.tier_fixed_on` 2099-01-01 | Accepted |
| `checks.failed_steps` ["stack"] in a clean feed | Footer "checks passed" (the page reads `cards_withheld`) |
| `alerts_withheld` true in a clean feed | Accepted |
| A live signal marked `lost` with `edge_level_pct` null | Card text reads "It fell to its edge level (n/a) before rising 10%" (index.html l.765) |
| A live card's `price_now` 3× its entry while best so far is small | Accepted |
| A live card's sample text naming two sample sizes | Accepted |

The page refused two forged cases correctly: a live signal also listed as a forming card, and `odds_fade.posting_bar_pct` 60 against the top-level 70.
The 9 unusual-JSON cases were all handled correctly on both states: duplicate keys, exponent integers, unicode escapes, 20,000-character text, HTML and script markup in every free-text field (escaped, never run), 300-deep nesting, huge numbers in unknown fields, and 1e400 (refused).
Pipeline (1): `CTZB_STEP_OUTCOMES` with a key given twice (`grade=failure,…,grade=success`) published as clean, because the last value wins. This is not real: GitHub writes each step outcome once.

## Two-fault cases (recorded, not counted)

None came up.

## By design per the spec (recorded, not counted)

- **A daily series 1 day behind is accepted** (`MAX_LAG_DAYS`). When the last row of `ETH_funding_daily.csv` is lost, or its `funding_oi_weighted` is 0, the ETH cards publish with different figures. The figures follow from the file as it is: the FUND read takes the last known day as today's (FEED_SPEC, "Inputs checked before scoring"). The other series 1 day behind gave figures equal to the clean run.
- **A hand run with no `CTZB_STEP_OUTCOMES` is judged on `stack_status.txt` alone.** With the regression baseline missing it publishes clean. The workflow always sets the variable.
- **`extras=cancelled` or `extras=skipped` publish the cards with the extras withheld.** The seal still requires extras unless the outcome is "failure".
- **Damage to unread columns publishes figures equal to the clean run.** These are the per-market columns of the funding, long/short and open-interest files, and `pcr_prem`. `pcr_amt` blank or 0 is allowed by the spec.

## What failed safe, by family (counted cases)

| Family | Page | Pipeline |
|---|---|---|
| MISSING | 4 feed down: "Data unavailable" with "Feed unavailable" in the header and no example standing in. 26 part refused: ledger, chart, example or lead-trader file reads unavailable | 84 stopped at the gate, 12 held, 10 fail-closed. 10 published equal to the clean run (alert log, copy or previous feed lost: restored from the second copy, no alert lost or sent twice) |
| MALFORMED | 26 feed down. 176 part refused. 114 used, figures equal the file (CRLF, BOM, minified feed, rows shuffled, lower-grade row damage, quoted cells) | 1,446 stopped at the gate (`history_problems` and `structural`). 248 held, 123 fail-closed. 124 published equal: format-only changes (CRLF, exponent, quoted or space-padded numbers), unread columns, extras files rewritten |
| WRONG CONTENT | 108 refused: another run's or asset's or timeframe's chart file, a moved example file, another run's feed or ledger | 94 stopped, 264 held, 143 fail-closed. 99 equal: the extras step rewrites its own files, or the copy was byte-identical |
| PARTIAL RUN | – | 204 held, 98 fail-closed. 41 equal (a step re-run that rescored the same inputs, feed_live run twice, a killed fast step that had already finished) |
| TIMING | 18: stale and daily-close notes correct (4h59m none; 5h01m "has not refreshed"; open 6 h "page has been open"; 23:58 open over the close; 00:30; 3 years old; feed in the future) | 27 stopped (candles not today, clock a day off). 32 held, 16 fail-closed (refresh before midnight and later steps after it; feed_live after midnight; seal 2h01m old or from the future). 25 equal |
| DELIVERY | 59 feed down (404, 500, 502 with a valid body, reset, empty, cut at 7 points, HTML 200, gzip, UTF-16, junk). 103 part refused, 22 used. Slow feed, ledger, trades, example and chart files read "Loading", then the right figures | – |

Alert log: no withheld run changed the log, and none emitted an `alert_id` twice. The held and fail-closed feeds kept the last feed's 2 alerts in `alerts_held`. Both read "Setups held back" and "Market filter: unavailable" on the page.

## Repo tests (part C)

| Test | Result |
|---|---|
| `test_feed_damage.py` (RENDER_LIMIT=40, REJECT_LIMIT=10) | 33/33 passed, 851 s |
| `test_seal.py` | 29/29 passed |
| `test_page_timing.py` | 24/24 passed |

`test_feed_damage.py` covers single-field damage to the feed and the lead-trader file, plus some ledger and chart-file damage, on one file at a time. It does not cover:
- a file from another run beside this run's files;
- HTTP status and body combinations across files;
- slow chart files;
- the viewer's clock;
- forged cross-field contradictions like the 14 above;
- anything in the pipeline.

## What I could not test, and why

- **The Kraken cross-check.** There is no network here; it was passed as unreachable, which never fails a run.
- **The real clock in `check_fresh.py` and `check_candles.py`.** Both read the machine clock, so I re-implemented the freshness rule on the run's clock and called `check_candles.main(today=…)`.
- **GitHub itself:** the concurrency group, the commit and rebase-push, and the retry job. Two runs at once were emulated in one folder, where the interleavings were held or failed closed.
- **The Workers:** the mirror's per-file KV pulls and the Access gate. I emulated only the site Worker's `csvToBars` and its fixed paths. The trades relay is 404, as in the harness.
- **Damage between steps on replay_1111.** It was run on current only (1,068 cases), for time.
- **A 1 January page boundary.** There is no clean Dec-31 feed. The pipeline did cross 1 January (ye_1231).
- **The full-size `test_feed_damage.py`** (quick mode only).
- **Harness caveats, all fixed and re-run:** my gate first ignored `check_candles`' return code; cases started mid-run first reported earlier steps as skipped; one alert check had a false positive when two runs used the same clock. The case list is fixed in `code/piperun.py` and `code/pagerun.py`. The triage reasons are in `code/collect.py` and the `cause` column.
