# Audit 30 (c): damage to the ETHKROS member site and its pipeline

Independent damage audit, 14 Nov 2026. States: `a30/replay_0414` (12 Nov 04:14 UTC, forming setups) and
`a30/current` (14 Nov, no forming setup), plus 14 real replays made with `tests/replay_at.sh` from a copy (1 Jan
2021/2025/2026, 31 Dec 2020/2025 at 23:59:59, 29 Feb 2024, a Bearish quiet day, A+ forming days, 00:00:00) and three
real held / fail-closed feeds made by the pipeline. Nothing in the repo was edited. All code is in `tools/`; every
case is in `all_checks.csv`, the counted ones in `disagreements.csv`.
Entry quality only: these are computed signals, not fills, with no exit. Nothing here is a return or a track record.

## Top line

**4 disagreements, 2 causes. Both are on the pipeline side. The page level had none.**

| Family (rule) | Page: tried / got through | Pipeline: tried / got through |
|---|---|---|
| 1 Missing | 40 / 0 | 285 / 0 |
| 2 Malformed | 98 / 0 | 1,567 / **4** |
| 3 Wrong content | 27 / 0 | 105 / 0 |
| 4 Partial run | 3 / 0 | 183 / 0 |
| 5 Timing | 42 / 0 | 31 / 0 |
| 6 Delivery | 92 / 0 | 12 / 0 |
| Boundary and unusual-but-valid values (not damage) | 16 / 0 | n/a |
| Hardening (forged contradictions, **not counted**) | 22 / 11 accepted | n/a |

The page level covered 19 states and 340 renders. The pipeline level covered 2 states and the sequence from the
replay state to the current state, with 2,184 runs on 111 damaged files or conditions.

| Kind of disagreement (real-life damage only) | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 3 (chart bars drawn from a file altered between steps; 1 shown on the page, 2 on charts the page does not draw today) |
| (ii) placeholder, script error, blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 4 (the 3 above, plus 1 series column lost) |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| pipeline + page | replay | `datasets/candles_btc_1d.csv`: one middle bar's high raised 25% between the grade and extras steps (repro) | extras refused the seal (`extras=failure`); the feed was published with cards (`cards_withheld` false); the altered file stayed in `datasets/`; the page drew the BTC 1D chart for BTC-1D-2026-11-13 including the altered bar, with no "unavailable" | the run fails closed (6a), or the chart reads "Chart data unavailable" | see A |
| pipeline | replay | `datasets/candles_eth_5d.csv`: a figure altered after grade | the same: published, the altered file stays | fails closed | A |
| pipeline | current | `datasets/candles_eth_5d.csv`: a figure altered after grade | the same (ETH 5D is drawn only for an A+ live setup, and none is live today) | fails closed | A |
| pipeline | current | `data/derivs/BTC_funding_daily.csv`: the whole `funding_oi_weighted` column removed | passes every input check and is scored (the FUND read falls back to `funding_mean` on every day); the figures happened to equal the clean run's | the run stops at the candle check, or the cards are held | B |

**A. The run seal does not cover chart files once extras has refused it.** `extras_live.py:76` checks the seal before it
clears its outputs (`:79-83`). So when a file in `EXTRAS_FILES` changes between grade and extras, extras exits and
leaves that file in place. After that, `seal.py:139` (in stack and cards) and `feed_live.py:414-416` leave
`EXTRAS_FILES` out of the check because extras failed. The cards still publish. The member page reads the
`candles_*.csv` chart files whatever `extras_withheld` says. Its only cross-check is that the last bar's close matches
`price_now` / `entry_close`. A file deleted, cut, emptied, reordered or from an older run fails that check (the page
says "unavailable"). A middle bar that is altered passes it. Guarantee (6a) holds for every other datasets file in
every case I tried.

The same path leaves the previous run's chart files beside a fresh feed whenever extras stops at its seal check. The
last-close check catches that unless the price has not moved, for example on the 1-minute retry of a failed run.

Real life: this needs the leftover chart file to change between grade and extras by accident, the premise of (6a). It is
counted.

**B.** `fetch.py:369` reads `funding_oi_weighted` only "where filled" (`r.get`). A file that has lost the whole column
therefore passes, and `analysis/pcrtest.py:99` (`funding_below`) silently switches to `funding_mean`. This is
structural damage (a wrong column), not a value. Real life: it happens if the source or `fetch_derivs.py` stops
writing that column. Today it changed no figure.

## What failed safe, by family (the rule, and what was thrown at it)

1. **Missing.** Pipeline (285 cases): every candle file, series, dataset, the seal, the alert log, its second copy,
   the previous feed, the grade rules, the regression baseline and the page file were deleted or emptied. Each one
   stopped the job, held the cards, failed closed, or restored the alert log exactly. Page (40): the feed, ledger,
   charts, example and trades files were tested as 404, 500, 503 and network abort. Each reads "Data unavailable" /
   "Past signals unavailable" / "Chart data unavailable" / "unavailable". None read as quiet.
2. **Malformed.** All 50 kinds on all 14 candle files: rows duplicated, swapped, reversed or deleted at the start,
   middle or end; a column lost or renamed; text, NaN, inf, blank, negative or zero cells; cut mid-line or after a
   comma; BOM; a trailing or middle blank line; an extra header row or cell; time in ms, ISO or off-grid; an
   appended revised bar. On the daily files every one of these stopped at `check_candles` or `check_fresh`. The 4H
   and 12H files are read by no scoring step. The rest: 30 kinds on the 7 daily series (1 got through, B above);
   10 kinds on every datasets file between steps (740 + 197 + 168 runs); the page's ledger in 15 malformed forms; and
   chart files in 15 forms. All the rest failed safe.
3. **Wrong content.** Candle files of the other asset or timeframe, series of the other asset or another series,
   the other state's datasets copied in between steps, the other run's ledger, every chart file from the other run,
   and another run's alert log or previous feed were all caught. The ledger, charts and feed mixed across runs read
   "unavailable" or (when the bytes were identical) correct.
4. **Partial run.** All of these failed safe: each step killed part-way; steps skipped, repeated or out of order;
   refresh skipped or re-run; two runs interleaved in one folder; `feed_live` alone at 1 h 59 min (publishes the same
   figures), 2 h 01 min, 26 h and before the seal (all fail closed); outcomes unset, empty, skipped, cancelled,
   missing, upper-case, garbage or all failing. Alert log: 32 cases, including the feed dying before the second copy
   or the log, and held, fail-closed or stopped runs in between. No alert was lost or emitted twice; 4 vanished
   alerts went out once.
5. **Timing.** The run clock was set a day ahead, a day behind, 4 h ahead and 2 days ahead: each stops at
   `check_fresh`. Midnight passing between the scoring steps and the feed fails closed. A 00:00:00 run publishes the
   same figures as 04:14. On the page: 5 h 01 min, 2 days and 3 years each show the stale note on every tab; a page
   left open 5 h, 7 h and 3 days keeps the note and its hour count current; the note after 00:00 is right; all 14 real
   replays (year ends, 29 Feb, Bearish quiet, A+ forming) drew every chart, matched the record and carried the right
   notes.
6. **Delivery.** These all read "Data unavailable" with no figure: the feed cut at 10 points, an HTML error page (as
   html and as json), the ledger or a chart file served as the feed, the feed twice, trailing garbage, `{}` `[]`
   `null`. A slow feed shows "Loading", then the feed. A BOM, minified JSON, reversed keys, duplicate keys, exponent
   numbers, `\u` escapes, deep junk, `86.0` and huge whitespace each gave exactly the clean page. Markup in every
   free-text field was shown as text and no script ran.

Lead-trader file: 10 valid shapes gave the right "in · long", "in · short", "out" or "not in", with no dollar size or
contract count shown even when the file carried them. 18 damaged shapes read "unavailable".

**Hardening (not counted).** The page and `feedcheck.py` accept a forming card confirming in 2030 with 1 bar to go; a
forming card whose `price_now` is 3x the other cards' for the same asset; a `must_close_above` at 10% of the price;
a dip-before-high that lands after the high; 100% touched -30% while the never-fell-25.3% share equals the +10%
share; a live signal marked `rose10` with best +25% and worst -1% against a card whose price is below entry; and
`scored_as_of` a month before `generated_at`. That last one shows "closed through" a month back, and the ledger is then
refused. Reversed `grade_odds` reorders the ETH/BTC summary boxes, which follow the file order; that is not wrong.
Rejected correctly: a low after the feed's date, a card attached to another signal, a duplicate A+ row, `grade_odds`
not matching the ledger, an example card not matching its file, past paths of +99,999%.

**Outside the families (not counted).** Cutting `docs/PRETRADE.md` in half publishes the same figures, but the stack
coverage check (`stack_live.py:138`) silently checks fewer headings. Limit as documented: with the previous feed, the
second copy and the log all damaged at once, a cut log is accepted, and the vanished alerts for the forming rows it lost
are never emitted.

## Part C: the repo's own tests (on a copy)

| Test | Result |
|---|---|
| `tests/test_seal.py` | 23/23 pass |
| `tests/test_page_timing.py` | 16/16 pass |
| `tests/test_feed_damage.py` (`RENDER_LIMIT=40 REJECT_LIMIT=10`) | 31/31 pass |

These tests do not cover:

- **A:** damage to an `EXTRAS_FILES` file between steps (test_seal only cuts the ledger and appends to grades).
- **B:** a funding column lost.
- **Forming-setup chart checks:** test_feed_damage's own replay has 0 forming cards, so the `price_now` check on
  forming-setup charts is exercised only on the repo state.
- **Runs across files:** feed, ledger and charts from different runs, except "older chart, 3 bars missing".
- **Alert sequences** with the previous feed swapped for another run's.
- **Real held and fail-closed feeds rendered** with that run's own ledger and charts.
- **Real replays** around 1 January and 29 February.

## What I could not test, and why

- **Kraken cross-check and `fetch.py`, `fetch_derivs.py`, `fetch_pcr.py`:** there is no network here. Kraken was
  stubbed as unreachable.
- **The site Worker's CSV-to-JSON conversion, Cloudflare Access, the mirror's 15-minute pull and GitHub's
  concurrency, commit, rebase and push:** the harness serves JSON built from `datasets/` as the brief specifies, and
  runs steps locally with the workflow's gating.
- **A viewer's wrong device clock and replays before September 2020:** accepted and out of scope.
- **The live trades relay:** it is 404 here, and fixtures were used.
- **Most damage on the frozen `current` state:** its seal is from 09:47 UTC, so its runs used a new seal from
  `refresh.py`.
