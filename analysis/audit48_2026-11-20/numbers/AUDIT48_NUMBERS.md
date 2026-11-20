# Audit 48 (numbers): member-site figures against raw prices

**Scope:** independent recomputation, at code commit 4d4069d, from raw candles. My own code is in `code/`. It imports only `regimes.rsi_regime` (the gate). I did not read any earlier audit folder or `docs/AUDIT_LOG.md`, and I did not edit, commit or push anything in the repo.

**Entry quality only.** These are computed signals, not fills, and nothing here is a strategy return or a track record.

## Top line

| Group | States | Comparisons (rows) | Disagreements (rows) | Distinct figures disagreeing | Wrong figure | Wording |
|---|---|---|---|---|---|---|
| (A) frozen states | replay_0414, current | 56,405 (54,132 feed/ledger/chart-file + 2,273 page) | **0** | 0 | 0 | 0 |
| (B) real-date replays | 327 via `tests/replay_at.sh`, plus 4 envelope runs | 6,080,823 (5,786,018 data + 294,765 page + 40 envelope) | **0** | 0 | 0 | 0 |

## Every disagreement

None. `disagreements.csv` has only its header.

The replay run hit one false alarm, and the cause was in my checker. On 2021-03-14 with the clock at 23:59, the page clock was set to generated_at + 6 min, which falls after 00:00 UTC. The page then correctly showed its "daily close has passed" note, and my checker had expected no note. I fixed the checker, re-ran that replay, and it passed. The container restart at about 03:46 UTC killed the replay run. All 78 completed rows were whole, and the one replay in progress (2021-12-14) was re-run.

## Checks passed, by number (declared before the results)

| # | Check | A: comparisons (both states) | B: in every replay |
|---|---|---|---|
| 1 | Every ledger row: membership and order, entryPrice, low, tags, the 3 grade-odds columns, every forward measure (6 dp), yes/no columns, scaled20, every odds-on-the-day column (dayScaled20 leaves out signals with no year of volatility), dayN | 47,896 | yes |
| 2 | grade_odds: every field (the HTF rows are left out, note h) | 162 | yes |
| 3 | if_it_misses and example_if_it_misses: every field | 158 | yes |
| 4 | odds_fade: the walk-forward tier rebuilt on chart bars; bands, n, both shares and aliases, the edge on the exact share, tier_fixed_on, edge_measured_on; also next_buy_date and trades/signals_a_year | 114 | yes |
| 5 | Cards (forming, open, example): every field, the ladder (shown and exact shares, went_on_to_fall25), low_day, confirms_on (1 Jan restart), must_close_above (closed-form inverse RSI, rounded down), medians, eras, timing, sample text and n. Also that cards exist only on graded charts with the gate on and a non-empty sample, and that every live signal has a card | 3,466 | yes |
| 6 | open_signals (ids and order, days, day10/30/60 on closed bars, best/worst, edge level and status); prints (last 3 + forming, regime note, exact-CT/K tags); top-level fields | 1,200 | yes |
| 7 | past_paths and example_past_paths: n and every quartile for days 0-60 | 1,106 | yes |
| 7b | Chart files: the served files match the raw last 70 bars, and the example file is checked bar by bar, including its entry bar, entry close and the bar that holds day 60 | 30 | yes |
| 8 | Page (Playwright): every picker button, every card (Live, Forming, example), the Chart tab "At the alert" and "What happened" (level and edge lines, price tags, axis labels, candle wicks by slot, Entry/Today/Confirms/Day 60/high-day lines by date, ladder bands with n and colour, "What this one did", the cloud's points), Past signals (all/ETH/BTC: every row and the summaries), Previous signals, How to read, banner, footer | 2,273 | yes |
| 9 | Labels vs meaning: each label is checked against my own figure for what it says. I also read each label against its definition and found no mismatch | in 5 and 8 | yes |
| 10 | Entry quality only: a scan of the page for return/profit/result/track record/trade words. Every hit is a negation or describes the lead trader's own trades (note o) | 9 sentences reviewed | yes |

## Coverage of group B (327 replays, 2020-09 to 2026-11; one replay can count under several kinds)

| Kind | Replays |
|---|---|
| Within a forming low's reach of each of the 6 filter flips (F-3 to F+19) | 138 |
| First/last day of each episode and the days either side | 24 |
| Year-ends, 26 Dec to 4 Jan, 2020/21 through 2025/26 | 60 |
| Market filter off (feed reads Bearish) | 130 (40 picked at random off-days) |
| With a top-grade forming card | 60 (40 candidates declared) |
| Nothing live or forming on any chart | 11 |
| Quiet card checked, including perYear text and "filter off" text | 87 |
| 60th day in progress / the day after it closes (20 signals) | 20 / 20 |
| Just after a confirmation | 9 |
| Other clock times (00:00:30, 03:59, 08:43, 12:00, 16:13, 23:59) | 12 |
| With an example card (on or after 2024-11-22) / without one | 105 / 222 |
| With a live top-grade setup shown | 179 |
| Envelope: candles end on day D, clock on D+1. All 4 failed closed: stack failed, cards withheld, empty lists, page shows "Setups held back" | 4 |

## Definitional notes (not counted as disagreements)

Every item (a) to (al) in the brief applies as stated, and I found no place where the repo contradicts its own stated choice. In particular:

- (a, ad) The gate is read on the trough bar's open date, and the header shows today's filter.
- (b, c) The flash clamp and the low-before-high rule are applied in my code too.
- (d) must_close_above for need 1 assumes the open bar closes at the current price.
- (e) The day count is the day in progress.
- (g, i) The odds-fade tier uses refresh.py's original rule on chart bars as of 1 January and is in-sample.
- (j) "Known by then" means entry + 60 on or before the date.
- (m) Live cards are measured from each past signal's own entry close.
- (r) perYear: I derived the last complete year independently, and it matched in every quiet replay, leap years included.
- (u) The replay day's bar is kept whole.
- (ab) The example's chart file is static, so I check it only in states dated 2024-11-22 or later.

Threshold booleans (+10%, +15%, +20%, −30%, −25.3%) were tested in exact decimal on the CSV prices and compared with the pipeline's float route. No boundary case occurred in any state (no notes logged). No rounding tie between a feed rounded field and the page's toFixed of the 6-dp stored value occurred either.

## Self-test of the checker

I planted 27 errors in a copy of the current state, and the checker caught all 27, each at its own field (`out/plant_results.csv`). The planted errors included:

- feed card big number +1, an exact median off by 1e-6, an exact ladder share off by 1e-6, must_close_above +1 cent, low_day moved a day
- live best +0.1, day-10 change −0.1, edge level changed
- grade_odds, misses and cloud values +0.1, odds-fade +1, a print price +1 cent, signals a year, sample wording, an era share +1
- ledger bestMove +1e-6, an odds-on-the-day value +1, tags, a top-grade daysToHigh −1, an entry price +1 cent
- one chart-file bar high +1
- page code: the +20% tile showing the +10% share, the live day count +1, the +10% chart line drawn at +10.5%

The self-test found one weakness. The page check placed candles from the served chart file rather than raw data. I fixed it, and group A was re-run. The 327 replays had already run with the old version, but each of them also compared the served chart files with raw candles (check 7b), so that gap was covered there.

## Files

- `all_checks.csv`: group A and the envelope runs, every row.
- Group B rows, one gzipped file per replay with the same columns: `out/replays/*.csv.gz`.
- `out/replay_summary.csv`, `replays_planned.csv`: the declared list.
- `disagreements.csv`, `progress.log`.

Doc sentences contradicting the code: none found.
