# Audit 12: ETHKROS member site, independent recomputation (12 Nov 2026)

**Top line: 55,941 comparisons (REPLAY 28,240, CURRENT 27,701). Figure disagreements: 0 rows, 0 distinct figures.
Docs-vs-code disagreements, counted separately: 5.**

Entry quality only. There is no exit in the data, so nothing here is a strategy return or a track record. Every
signal is a computed signal; none was traded.

## Method

All code is my own and lives in this folder: `lib.py` (candle load with the 0.5-of-body flash-print clamp, Wilder RSI,
stochastic K, pivots, bucket close dates, 60-day measures, ladder, volatility ratio), `build.py`, `audit_data.py`,
`forming_scan.py`, `integrity.py`, `page_extract.py` and `page_compare.py`. From the pipeline I imported
`regimes.py` only, for the gate. I read no earlier audit folder, `docs/AUDIT_LOG.md` or other scratchpad folders.
The membership rule, the samples, the walk-forward tier and every figure were rebuilt from the raw
`data/{ETH,BTC}_{1D..8D}.csv` and `data/derivs/*_funding_daily.csv`. Grades and lenses were taken from each ledger row,
and a card's lenses from its `confirmations` text.
The page was rendered with Playwright/Chromium exactly as briefed: `site.test`, routed files, fonts aborted, trades 404,
clock = `generated_at` + 6 min. For every picker button and the example, I captured the full card, the Chart tab
(SVG elements and their coordinates, both toggles on the example), the Past signals tab (all, ETH, BTC), the
Previous signals column, How to read, the banner and the footer, then compared each against my own values.

Raw-data checks first. Every 2D/3D/5D/8D bar equals its daily bars under the calendar-year bucket rule. The only
exception is ETH's first week, where the 21-22 May 2016 daily bars are missing; that has no effect on any signal.
The clamp fires exactly twice per chart: BTC 2017-04-15 (low 0.06) and ETH 2017-06-21 (low 0.10), as CONTEXT says.
Every confirmation-bar close equals the daily close on the entry date. The candles datasets equal the raw last 70 bars.
The example chart's 52 bars equal raw ETH 2D, and its entry bar closes on 2024-09-22.

## Declared check list (declared before results)

1. Every ledger row: membership, low, entryPrice, tags, year, the yes/no measures, the four 6-place measures,
   daysToHigh, the grade-odds columns, and all seven odds-on-the-day columns (dayScaled20 leaves out signals with no
   year of volatility).
2. `grade_odds`: every field of the A+/A/B/C rows per asset and of the two ETH marker rows.
3. `if_it_misses` (every asset and grade) and `example_if_it_misses`: every field. Medians are also recomputed at
   full precision to catch a 6-place rounding flip.
4. `odds_fade`: the walk-forward tier rebuilt by refresh.py's original rule on each chart's own bars, then the bands,
   n, the +10/+20 after-day-10 shares and their `*_within60d` aliases, and each edge mark against 70% on the exact share.
5. Every card (4 REPLAY forming cards, the example card and all 23 `open_signals[].card` per state). Each check covers
   every field: from_entry, the ladder (shown and exact), low_day, low_date, confirms_on, bars_to_confirm,
   must_close_above (solved analytically from Wilder RSI), price_now/entry_close, the rounded and exact medians, a
   double-rounding guard, the eras, the timing, the sample rule plus every count in the sample text, and the edge.
   I also scanned all 10 charts independently for forming lows: 4 in REPLAY (ETH/BTC 1D and 2D), 0 in CURRENT.
6. `open_signals`: the list (ETH and BTC, 1D-5D) and its order, ids, entry dates and closes, tags, days_elapsed,
   day 10/30/60 on closed daily bars, best/worst so far, edge_level_pct and edge_status.
7. `past_paths` (ETH, BTC) and `example_past_paths`: n and all 61 days × 3 quantiles.
8. The page as listed above. That includes prices, day counts, every vertical line's bar (Entry/Today, Confirms,
   High ~day N, Day 60), the level-line y positions, the axis scaling (at the alert, the example uses only bars to the
   entry), the price-grid labels, the x-axis dates, the candle wicks, the ladder zones and their colours, the shaded
   zones, the cloud median and band polygons, the example's "What happened" labels, side box and path, the record rows
   and summaries, the previous-signals badges, the banner, the footer and the lead panel.
9. Labels against meaning: every label read against what its number measures.
10. Entry quality only: every page string searched for trade/return/profit/win/target/track-record wording.

## Results by check (all passed)

| # | Check | REPLAY | CURRENT |
|---|---|---|---|
| 1 | Ledger (919 rows, membership both ways, 27 columns) | 24,814 | 24,814 |
| 2 | grade_odds | 80 | 80 |
| 3 | if_it_misses + example_if_it_misses | 86 | 86 |
| 4 | odds_fade (tier: 13 chart/tag pairs; pool 168 signals) | 60 | 60 |
| 5 | Cards (forming, example, 23 open-signal cards) | 1,515 | 1,299 |
| 6 | open_signals (23 per state) | 278 | 278 |
| 7 | past_paths + example_past_paths | 556 | 556 |
| 8 | Page (6 / 2 picker selections, chart, record, previous, header, footer) | 848 | 525 |
| – | Feed top level (regime, scored_as_of) | 3 | 3 |
| 9 | Labels against meaning (manual) | no mismatch | no mismatch |
| 10 | Entry-quality wording (manual + search) | no mismatch | no mismatch |

Spot values, for orientation (both states agree):

| Figure | Value |
|---|---|
| Ledger members | 919 (ETH from ETH 3D 2020-03-21, first ETH top grade 2020-04-18) |
| BTC 2D live (confirmed 2026-09-21), day 52 | best +0.8%, worst −16.1%, day 10 −2.0%; edge level −5%, status lost |
| Its card | 85% rose 10% (n 33); 76% without falling 25.3%; from entry 82%, falls 5% first 60% (n 15) |
| Example card (ETH 2D 2024-09-22) | 87% (n 75); edge −10%; what happened: best +33.6% on days 51–52, deepest −10.5% on days 11–12 |
| odds_fade "red on day 10" | 63% rose 10% after day 10 (n 64), edge gone; 165 of its 168 signals closed before 1 Jan 2026 (in-sample, as labelled) |

## Disagreements

**Figures: none.** Every displayed or fed number equals my value to the last displayed digit. That covers the 6-place
exact values and the SVG coordinates to 1e-6. No 6-place re-rounding changed a shown figure.

**Docs vs code (separate count, 5):**

| Where | Docs say | Code does |
|---|---|---|
| CONTEXT.md:223 | Refresh runs at 01:20, 05:20, 09:20, 13:20, 17:20, 21:20 UTC | ctzb-scheduler dispatches daily.yml at :13 (and :43, gated) after 00/04/08/12/16/20 UTC; the replayed run is 04:14 |
| FEED_SPEC.md:4 | "every 4 hours, first run 7 minutes after the 00:00 UTC close" | Same scheduler: :13 after each 4-hour close |
| CARD_SPEC.md:3-7, 34-51 | "The single definition of every number and every word on a trade card … client screens" | The member card uses other words (Typical high; Dip before the high, from entry, not the 4 Nov wording "Typical lowest point vs the buy price…"; Typical drop from entry; Touched −30%; no corner n). It also shows figures CARD_SPEC never defines: the from-entry row, Edge gone below and the five If-it-misses figures (defined only in FEED_SPEC and CONTEXT) |
| FEED_SPEC.md:230 | "The page types no figures" | How to read types "our 70% bar" in the HTML (index.html:299), while the card reads `posting_bar_pct` |
| CONTEXT.md:526 | Members are sent A+ only, "and the card says 'Confirmed setup'" | A live top-grade card says "Live setup"; only the worked example says "Confirmed setup" |

Observations, not counted (labels are accurate; wording is the owner's call):
- The chart side box labels entry × 1.10 "+10% target", and the example says "the zones, the target and the timing".
  The number is the +10% measurement level; "target" is trade-plan wording.
- The lead panel's static text says "Every trade is posted live", while the banner says the lead trader's feed is in
  dry run. In this harness the panel correctly shows "unavailable" (n).

## Definitional notes (choices taken as stated, not counted)

(a) The regime gate is read on the trough bar's date. (b) The flash-print clamp (0.5 of body) applies to all candles.
(c) Within a daily bar the low is taken before the high (ladder, from-entry, edge status; dip-before-high includes the
high day's low). (d) "Must close above" assumes today's open bar closes at the current price. My analytic RSI solve
matches all to the cent: ETH 1D $2,047.21, BTC 1D $73,533.06. The 2D cards need two bars, so no level is shown.
(e) days_elapsed / "day N of 60" is the day in progress (today − entry date). (f) peaked_10_or_more is 0 by
construction. (g) The odds_fade tier is chosen by refresh.py's original rule on each chart's bars. Its groupings and
outcomes use daily candles; the tier as of 1 Jan 2026 is ETH 1D hollow; ETH 2D diamond, hollow, prime dot; ETH 3D
prime dot; ETH 5D any, A, B, diamond, prime dot, zone-exit B; ETH 8D any, C. (h) Confluence cells and the two ETH
HTF-divergence grade_odds rows are not checked. (i) The pooled odds_fade is in-sample, as labelled. (j) "Known by then"
means entry + 60 ≤ date (example card, its cloud and misses, odds-on-the-day). (k) Kept feed field names are not
member labels. (l) Opening card: REPLAY opens on BTC 1D forming (highest +10% share), not the live top-grade BTC 2D.
(m) An open signal's card uses every signal whose 60 days have closed. (n) Trades 404, so the lead panels say
"unavailable".
Also relied on: the forward window is days 1-60 on daily bars, valid only once the day-60 bar has closed. ETH ledger
membership needs funding data with a 90-day median from ≥ 60 days plus the FCOOL 7-day windows; in practice the FCOOL
windows exclude nothing. The volatility ratio is the population stdev of 365 daily log returns ending at entry, over
its median for dates through 2021. Path quantiles use linear interpolation. Ties take the earliest day (high, low,
low_day).

## Files

- Report: this file.
- `all_checks.csv`: every comparison (state, location, label, shown, yours, ok, cause), 55,941 rows.
- `disagreements.csv`: the 5 docs-vs-code rows; no figure rows.
- Per-part outputs: `checks_data_{replay,current}.csv`, `checks_page_{replay,current}.csv`, `page_{replay,current}.json`
  (everything the page displayed).
