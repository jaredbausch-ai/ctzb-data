# Audit #10 — ETHKROS member site vs raw price data (independent)

Entry quality only. Every figure audited here is a computed signal measured over the 60 days after its
confirmation close. There is no exit in the data, so nothing here is a strategy return, a fill or a track record.

## Top line

| | |
|---|---|
| Comparisons made | **60,863** (REPLAY 30,722; CURRENT 30,141) |
| Disagreements | **998 rows = 499 distinct figures**, one cause: ledger `dayScaled20` (the same 499 BTC rows in both states) |
| Member-visible disagreements (page, feed cards, open signals, misses, paths, odds fade, grade odds) | **0** |
| Docs-vs-code disagreements (counted separately) | **5** |

All code is my own (`lib.py`, `audit_state.py`, `page_audit.py`, `extra_checks.py`). The only repo import is `regimes.py`, for the gate.
Prices are read as exact decimals from the CSV text, so every threshold test (+10%, +20%, −25.3%, −30%, falls 5/10/15/20% first) is exact.

## What was checked (declared before running)

1. Every ledger row (919 per state): membership, low, entryPrice, tags, every forward measure (6-place values), yes/no flags, grade-record columns, odds-on-the-day columns.
2. `grade_odds`: every field of the 8 grade rows and the 2 diamond-or-prime-dot rows. The 2 HTF-divergence rows are skipped (lens logic).
3. `if_it_misses` (8 rows) and `example_if_it_misses`, every field.
4. `odds_fade`: the walk-forward tier rebuilt from each ETH chart's own bars (13 chart/tag pairs). The early-dip and day-10 rows were rebuilt on daily candles: n, the after-day-10 shares and their aliases, and each edge mark tested against 70% on the exact share.
5. Every card: the 4 REPLAY forming cards, `example_card` and all 23 `open_signals[].card` in each state. Every field was checked, including the sample text and n, from_entry, the ladder (shown and exact), edge level, low_day, price_now/entry_close, kill close, exact and rounded medians, eras and timing.
6. `open_signals`: the set (23 per state) and every field, including the edge level and status.
7. `past_paths` (ETH, BTC) and `example_past_paths`: all 61 days, every quantile.
8. The page in Playwright, with the routes as specified and the clock set to generated_at + 6 min. Covered: every picker button, the example card, the Chart tab ("At the alert" and "What happened"), the cloud and side panel, the Past signals tab (all, ETH, BTC), Previous signals, How to read, banner and footer. Lines, zones, circles, axis labels and axis scaling were checked against my dates and prices.
9. Labels vs meaning. 10. Entry quality only.

Also: the chart bars (2D to 8D) re-bucketed from 1D, the served candle files (last 70 bars), and the example chart JSON against the raw ETH 2D bars.

## Disagreements

| State | Where | Shown | Mine | Cause |
|---|---|---|---|---|
| REPLAY, CURRENT | ledger `dayScaled20`, 16 BTC rows (BTC 1D 2016-09-25 … 2017-02-28) | 0 | blank | Undefined "normal move" counted as a miss (see below) |
| REPLAY, CURRENT | ledger `dayScaled20`, 483 BTC rows (e.g. BTC 1D 2017-03-13; BTC 3D 2020-07-25; BTC 1D 2026-09-05) | 3; 45; 51 | 100; 61; 57 | Same; understated by 3 to 97 points |

Cause: "beat a normal move" needs 365 days of daily volatility at entry. BTC signals before 2017 have none.
- grade_live's odds-on-the-day counts those signals as misses (`bool(None)` is False).
- The card's own `beat_normal_move_pct`, in stack_live and verify_cards, leaves them out.

So the repo uses two definitions of one measure. With the card's rule, every BTC row that shows a value changes (499 of 562 BTC rows; ETH is unaffected).

The column is in `datasets/ledger.csv` but is not shown on the page. The full list is in `disagreements.csv`.

## Docs vs code (5, counted separately)

| # | Doc says | Code does |
|---|---|---|
| 1 | CONTEXT (Audit #3 paragraph): "verify_cards is now exact (tolerance 0)" | `verify_cards.py` allows 1e-6 on the three 6-place exact medians. CARD_SPEC #2 documents this; CONTEXT does not. |
| 2 | CONTEXT "Member card redesign (item 18)": the card's edge read is the pooled early-dip read, and "these figures are NOT in the feed yet" | The card's edge comes from the setup's own ladder (stack_live, page `setupFade`). The misses, paths and fade figures are in the feed (schema 5). The bracketed "Superseded" note covers only the miss rule and the numbers. |
| 3 | CARD_SPEC: "The card always says which rule it used … and states the sample size there and in the corner" | The member Now card shows only "from N past signals like this one". The rule text (`sample`) appears only on the Chart tab, and there is no corner n. |
| 4 | `docs/artifacts/member-site/README.md`: route table and "Not deployed yet" | The page also fetches `data/candles/<ASSET>_<TF>.json`, which is not in the table. CONTEXT records the site as deployed (ctzb-site, 12 Nov 2026). |
| 5 | `extras_live.py` docstring lists `pastpaths_example.csv` under the misses and omits `missstats_example.csv` | It writes both files. This is a code comment, not a figure. |

## Checks passed, by area

| Area | REPLAY | CURRENT |
|---|---|---|
| Raw data: 2D–8D bars = 1D re-bucketed by calendar year; data current to today | 10 / 10 | 10 / 10 |
| Ledger rows (membership + every column) | 24,314 / 24,813 | 24,314 / 24,813 |
| grade_odds | 61 / 61 | 61 / 61 |
| if_it_misses + example_if_it_misses | 88 / 88 | 88 / 88 |
| odds_fade (tier, rows, aliases, edge on exact share) | 54 / 54 | 54 / 54 |
| Forming cards + example_card (incl. labels on every record) | 274 / 274 | 58 / 58 |
| open_signals (set + fields + edge level/status) | 301 / 301 | 301 / 301 |
| open_signals[].card (23 cards) | 1,242 / 1,242 | 1,242 / 1,242 |
| past_paths + example_past_paths | 556 / 556 | 556 / 556 |
| `past_signals` / `signals_a_year` aliases, top level | 249 / 249 | 215 / 215 |
| Page (Playwright) | 3,074 / 3,074 | 2,743 / 2,743 |

Page breakdown, both states:

| Page area | Checks |
|---|---|
| Past signals rows and summaries | 5,010 |
| Chart and cloud | 408 |
| Now cards | 312 |
| Chart candle files and example JSON vs raw | 30 |
| Previous signals | 18 |
| How to read | 16 |
| Picker | 13 |
| Banner, header, footer, JS errors | 10 |

Notable confirmations:
- BTC 2D A+ of 21 Sep 2026: live in both states. Day 52 of 60, best +0.8%, worst −16.1%, edge level −5%, lost.
- Forming kill closes match a closed-form RSI solve: ETH 1D $2,047.21 and BTC 1D $73,533.06.
- "At the alert" draws only bars up to the entry (21 candles), with the axis scaled on those bars alone.
- "What happened" marks the 60-day high and low on the right 2D bars: $3,446.98 on days 51–52 and $2,309.17 on days 11–12.

## Labels vs meaning; entry quality only

- **Labels.** Every figure I checked measures what its words say:
  - big number (rose 10%) and the line under it;
  - Typical high and drop;
  - Dip before the high;
  - "High/Deepest dip lands around";
  - +20% and −30% tiles with n;
  - ladder rows with n;
  - eras;
  - misses lines (count and pool);
  - Past signals columns;
  - footer "closed through".
- **Exception (docs-vs-code #3).** "Like this one" can cover a broader sample than the label suggests. Example: "all 33 grade A+ signals across all BTC charts" for the BTC 2D card.
- **Entry quality.** No figure reads as a return, a fill or a track record. Every card, Chart tab and Past signals table carries the "entry quality only / not a trade or a track record" line.
- **Lead-trader panel.** It speaks of real trades. In both states it shows "unavailable", and no trade is displayed.
- **Selection.** In REPLAY the page opens on the best forming card (BTC 1D, grade C, labelled "not top grade") while a live top-grade signal is in the Live row.

## Definitional notes (not counted)

(a)–(k) as given. All were applied, and the repo follows its own stated choice in each:
- **(a)** The gate is read on the trough bar's open date.
- **(b)** The flash-print clamp hits one bar per chart in 2017: ETH 2017-06-21 low $0.10; BTC 2017-04-15 low $0.06.
- **(c)** The low is taken before the high, in the ladder, edge status and dip-before-high (which includes the high's own day).
- **(d)** The kill close assumes today's bar closes at the current price.
- **(e)** Day N = today − entry date.
- **(f)** `peaked_10_or_more` is 0 in all rows.
- **(g)** Tier = 60-day close above entry on chart bars, NMIN 8, 70%, outcome closed before 1 Jan 2026.
- **(h), (i), (k)** As stated.
- **(j)** Entry + 60 ≤ the date in question.

Further choices the docs leave unstated, which I matched:
- Past-path quartiles interpolate linearly between order statistics.
- An even-count median is the mean of the middle two.
- Timing medians round half away from zero.
- Ties for the high or low day take the first day.
- Early-dip bands are (lower, upper], so exactly −2% falls in "−2% to −5%".
- "Green on day 10" includes a close equal to entry.
- ETH membership needs funding at entry, ≥60 of the prior 90 days and ≥5 of 7 days in both 7-day windows.
- Forming cards are not filtered by the gate in code. The gate was on at every forming trough here, so there was no effect.
- 25.3% is applied exactly as worded (low ≤ entry × 0.747). The 3.3x / 5% liquidation reading assumes maintenance on the entry notional.
- The 4H candles were not needed: no member figure depends on them.

Files (all under `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit10/`):
- `all_checks.csv` and `disagreements.csv`;
- per-state `checks_*.csv` and `page_checks_*.csv`;
- `mine_*.json` (my values).
