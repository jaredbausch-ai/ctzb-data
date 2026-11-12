# Audit: ETHKROS member-site figures vs raw candles

*Independent audit, run 12 Nov 2026 03:35 UTC by a separate agent that did not build the site, against feed generated 2026-11-12 00:14Z and repo HEAD fb0e4ec. Scripts and every comparison are in this folder. Entry quality only.*

**Verdict: 16,612 figures checked, 144 disagree.** Almost all of the disagreements come from one cause: the committed `feed/ctzb_feed.json` (written 2026-11-12 00:14Z) predates the "+10% switch" commit (c085adf). So the misses, odds-fade and Record figures on the page still use +20% while their labels say +10%. The ledger itself matches the candles exactly.

This work measures entry quality only. There is no exit in the data, so nothing here is a strategy return or a track record. Every figure is a computed signal, not a fill.

## Checks declared before running

| # | Check | Recomputed from |
|---|---|---|
| 1 | All 921 ledger rows: entryPrice = close of the chart bar whose period ends on `entry`; that bar is ti+3 of a gated CT pivot low dated `low`; bucket and diamond/prime tags; reached10/15/20, touched30, surv10, bestMove, maxDrawdown, dipBeforeHigh, return60d, daysToHigh | raw `data/*_{TF}.csv`; daily candles d0+1..d0+60 |
| 2 | `grade_odds` by asset and grade (plus the diamond/prime marker rows; HTF-divergence rows are lens logic, skipped) | my row measures |
| 3 | `if_it_misses`, with miss = did not rise 10% in 60 days | my row measures |
| 4 | `odds_fade` early_dip / day10 rows and their edge marks at 70% on +10%. I rebuilt the signal set from candles | own signal detection |
| 5 | Each of the 4 cards: sample per FEED_SPEC/CARD_SPEC rule, every tile, the fade ladder, era split, timing, price_now, low_date, confirms_on, must_close_above | my row measures, own RSI |
| 6 | `past_paths`: q25, median and q75 for days 0–60, per asset, A+ | daily closes |
| 7 | Page served in Playwright: 4 forming cards, the example card, chart side panels and labels, the cloud, the Record tab (All, ETH, BTC), and Previous alerts | all of the above |
| 8 | Whether each label measures what it says | — |

Scripts, dumps and every comparison are in this folder. The full list of 144 disagreements is in `all_disagreements.csv`. Page comparisons are in `page_checks.csv`.

## Disagreements

### Shown on the page (check 7): 39

| Where on the page | Shown | Mine | Likely cause |
|---|---|---|---|
| BTC 1D and BTC 2D cards: "If it misses: up first" | 174 of 175 · median peak +8.8% | 94 of 95 · +4.0% | The feed's `if_it_misses` still uses the +20% miss rule |
| BTC 1D and BTC 2D cards: Worst drop, misses / Price on day 60, misses | −22.2% / −8.0% | −26.7% / −10.7% | same |
| ETH 1D and ETH 2D cards: "If it misses: up first" | Every time · +8.9% | Every time · +5.5% (37 of 37) | same |
| ETH 1D and ETH 2D cards: Worst drop, misses / Price on day 60, misses | −30.6% / −14.2% | −35.5% / −20.9% | same |
| ETH 2D card: By era, Before 2022 (n 8) | 62% | 63% (5/8 = 62.5) | Python `round()` rounds half to even |
| Record summary ETH / BTC: "Rose 10% in 60 days" | n/a% | 86% / 85% | The feed's `grade_odds` has no `rose10_within60d_pct`, although FEED_SPEC says it does |
| Record summary ETH / BTC: "Misses: median peak first" | +7.1% / +6.4% | +4.8% / +6.2% | Uses the +20% miss rule |
| Example card: Typical high | +35.0% | +34.9% | Median taken over the ledger's 0.1-rounded bestMove |
| Example card: Edge gone below | −10% in the first 10 days · $2,322.83 | −20% · $2,064.74 | Edge marks are still on +20%. On +10% the "−10% to −20%" band is 78% (intact) |
| Example card: If it misses: up first | Every time · +7.1% | Every time · +4.8% (15 of 15) | +20% miss rule |
| Example card: Red on day 10 | 47% odds | 67% | The feed row has no rose10, so the page falls back to the +20% share |
| Example card: Worst drop, misses | −19.7% | −25.7% | +20% miss rule |
| Example card: odds-fade ladder "share that rose 10%": Dip < −2 / −2 to −5 / −5 to −10 / −10 to −20 / Green day 10 / Red day 10 | 87 / 89 / 71 / 56 / 92 / 47 | 90 / 93 / 91 / 78 / 97 / 67 | These are the +20% shares under a +10% label. "Dip past −20%" is 44 on both measures |
| Example chart: Typical high price | $3,482.95 | $3,481.66 | 35.0% vs 34.9% |
| Example chart: Edge gone line | $2,322.83 (−10%) | $2,064.74 (−20%) | Stale edge marks |
| Example chart: early-dip band labels (0/−5, −5/−10, −10/−20) | 89 / 71 / 56 | 93 / 91 / 78 | +20% shares |
| Example chart: "Day 10 · red here" | 47% | 67% | +20% share |
| Example chart: "This one" high day and low day (marker and side panel, 4 figures) | day 52 / day 12 | day 51 / day 11 | The page counts 2D bars and reports the day the bar closes, not the day of the high or low |
| Example chart with the spec routing (example JSON 404) | Side panel, title and cloud show the ETH 1D card | Example | `renderChart` returns early and leaves the previous setup's figures on screen |

### Feed and datasets (checks 1–5): 105

| Field | Shown | Mine | Likely cause |
|---|---|---|---|
| `if_it_misses`, all 8 asset×grade groups (72 fields) | e.g. ETH A+ misses 26, peak +7.1, worst −19.7, day60 −12.2 | 15, +4.8, −25.7, −14.4 | Under the +20% rule all 8 groups reproduce my numbers within rounding (4 fields are off by 0.1 or by one count). `miss_rule` field is absent. Per group: `all_disagreements.csv` |
| `grade_odds` rose10_within60d_pct (8 grades + 2 marker rows) | absent | ETH A+ 86, A 74, B 69, C 67; BTC A+ 85, A 74, B 75, C 70 | Feed predates the switch |
| `grade_odds[].sample` (7 rows) | "2020-03-21 to 2026-09-13" for every ETH grade | e.g. ETH A+ 2020-04-18 to 2025-12-04 | The field holds the asset-wide date range, not the grade's own |
| `odds_fade` rose10 field (7 rows) | absent | 90 / 93 / 91 / 78 / 44 / 97 / 67 | Feed predates the switch |
| `odds_fade` early_dip "−10% to −20%" edge | gone | intact (78%) | Edge marked on +20% |
| `odds_fade` "shallower than −2%" n / rose20; green on day 10 n | 30 / 87; 93 | 29 / 86; 92 | ETH 2D 2023-03-15 enters only through a floating-point "diamond" (see definitions) |
| Ledger tags (3 rows: ETH 2D 2023-03-15, ETH 1D 2023-08-21, BTC 2D 2020-03-18) | "filled diamond" | no diamond | K is 0.0 at both troughs. The engine's running-sum SMA leaves ~1e-15 residue, which reads as a K change |
| Card ETH 2D before_2022; card BTC 1D typical_day_first_rose20 | 62; 22 | 63 (62.5); 23 (22.5) | Half-to-even rounding |

At HEAD, `missstats.csv` and `oddsfade.csv` (the +10% versions, not yet in the feed) agree with me except for four items. BTC B up_first is 33 vs 34, BTC B median peak 4.6 vs 4.5, and BTC C peaked_5 is 40 vs 39: those are counts and medians taken on 0.1-rounded bestMove. The fourth is the same 30 vs 29 n from the floating-point diamond.

## Checked and passed

| # | Figures | Pass | Notes |
|---|---|---|---|
| 1 | 921 rows × 16 | 14,733 | entryPrice 921/921; ti+3 pivot, low date, gate 921/921; all 9,210 measures exact or within 0.1pp; only the 3 tag rows fail |
| 2 | 60 | 43 | past_trades, surv10, rose20 and median dip agree in all 10 checked rows |
| 3 | 80 | 8 | Only `signals` agrees |
| 4 | 28 | 17 | My rebuilt walk-forward tier is the same 12 chart+tag cells, n 150 vs 151 |
| 5 | 137 | 135 | All 4 samples rebuild exactly (17 / 27 / 37 / 15). Ladder, timing, price_now, kill close, low and confirm dates all agree |
| 6 | 368 | 368 | 17 of 366 quantiles differ by exactly 0.1: carddesign rounds paths to 2 dp before taking quantiles |
| 7 | 1,203 | 1,164 | All 137 Record rows × 7 cells, 5 Previous alerts, the picker, every forming-card headline/tile/ladder/era, chart prices (price_now × (1+pct)), low markers, cloud figures, market filter |

## Wording vs meaning (check 8)

| Label | What the number actually is |
|---|---|
| "did it without ever falling 25%" / "the dip that would wipe out a 4x position" (Read tab) | The threshold is −25.3% over the whole 60-day window, not just before the +10% touch. CARD_SPEC defines −25.3% as 3.3x with 5% maintenance, not 4x. 4 rows fell 25.0–25.3% and still count as "never fell 25%". Bounding the test at the +10% touch would change 57 rows |
| "Where the odds fade · all kept signals" / "Every kept signal, all grades: share that rose 10% within 60 days" | ETH only. It is a walk-forward tier: chart+tag cells with 8+ signals and a 60-day close above entry at 70%+, including 8D, from 2016. 68 of the 151 are not in the graded ledger. It is measured on each chart's own bars from the confirmation bar's open date, and in the early-dip table "rose 10%" counts only highs from day 10 to day 60. On daily candles from the entry close, rose10 is 81 (not 78) and 50 (not 44) for the two deepest bands |
| Example: "a past computed signal, shown as a member would have seen it" | The card's 104 signals, 86% and 80% include signals after 22 Sep 2024 and the example's own outcome. The ledger's no-hindsight "odds on the day" for that row are n 75, rose10 86%, surv10 79% |
| "from 104 past signals like this one" (example card) | All ETH A+ signals pooled, the grade_odds figure, which FEED_SPEC says never to show as a setup's number. Same for an open A+ card (`cardFromOpen`); none was live today, so that path was not rendered |
| "Previous alerts" / "Edge lost or closed" | The 5 most recent ledger A+ computed signals, with outcome badges. No alert was sent for any of them; the alert log starts 10 Nov 2026 and there are no members. This reads as a record of issued alerts |
| "Red on day 10 · 47% odds" | The +20% share. It does not say what the odds are of |
| "Dip before the high" tile | Lowest low before the 60-day high vs the buy price. CONTEXT (4 Nov) requires the tile to name its reference point; it does not |
| "the last 17 ETH 1D trades…" (sample line) | Every such trade, not a recent subset |
| "Price on day 60" (example card) | Median day-60 change over all ETH A+ signals, not this signal's (that one is +30.2%) |
| "Top-grade setups come about 18 to 22 times a year" (empty-card text, not shown today) | Typed by hand. grades.csv perYear gives ETH 14.9 + BTC 3.0 = 17.9 |

Nothing on the page presents a dollar return or a filled trade. The Record and card footers say "not a trade or a track record".

## Definitional discrepancies (CONTEXT / specs vs code)

| Item | Finding |
|---|---|
| Regime gate | `engine.signals` applies `rsi_regime(...)` on the trough-bar date. CONTEXT does not say which date to use. 29 graded-chart signals would flip if the gate were read on the confirmation date |
| Forward window | grade_live / tagstats use daily candles d0+1..d0+60, where d0 is the last day of the confirmation bar. That matches CONTEXT. refresh.py's earlydip and holdcheck (the odds-fade source) instead count from the confirmation bar's open date on chart bars |
| Incomplete last candle | ETH 1D and BTC 1D 2026-09-13 (both grade C) are scored as complete. Their day 60 is the 2026-11-12 daily bar, which was 14 minutes old when the feed was written, so return60d, high and low come from an unfinished bar |
| Diamond test | `(dCt>0 and dK<0)` fires on floating-point residue when K is 0 at both troughs. It adds 3 diamonds and 1 odds-fade signal, and changes the ETH "diamond or prime dot" grade_odds row (137 vs 135, median dip −10.9 vs −11.0) |
| Rounding | `round()` is half-to-even (2 card figures). Medians and counts are taken on 0.1-rounded ledger values (example typical high; 3 missstats figures). Quantiles are taken on 2-dp paths |
| FEED_SPEC | The Schema 5 table still defines misses on +20% while the +10% section says +10%. It claims `grade_odds` rose10 and `odds_fade` rose10 / `edge_measured_on` / `miss_rule`, none of which are in the committed feed |
| Flash-print clamp | 10 BTC rows from Feb–Mar 2017 depend on it (raw drawdown −100%). For BTC 3D 2017-02-23 the clamped dip of −25.0% decides surv10. Consistent with CONTEXT; recorded only |

These are the exact deviations between the code and CONTEXT that I found. I did not assess grade and lens logic or the ETH funding filter (203 gated ETH 1D–5D signals with complete windows are absent from the ledger: 196 from before 2020, 7 after).
