# Audit 19 — ETHKROS member site against the raw candles

Independent audit, 13 Nov 2026. All figures recomputed with my own code (`lib.py`, `audit_data.py`,
`page_check.py`) from `data/*.csv`; only `regimes.py` was imported, for the gate. No earlier audit, its
folder or `docs/AUDIT_LOG.md` was read. Nothing in the repo was edited.

Entry quality only: every signal checked is a computed signal, never a fill. There is no exit in the data,
so nothing here is a strategy return or a track record.

## Top line

| Scope | Comparisons | Disagreements |
|---|---|---|
| Two frozen states (REPLAY 12 Nov 04:14 UTC, CURRENT 13 Nov 03:03 UTC) | 61,795 (REPLAY 31,372; CURRENT 30,423) | **0 rows, 0 distinct figures** |
| 60 pipeline replays, Sep 2020 to Nov 2026 (counted separately) | 1,392,325 | 0; no replay failed a pipeline step |
| Envelope test: clock a day ahead of the candles | 7 | 0 (fails closed) |
| Synthetic page states, 51 scenarios (counted separately) | 186 | **6 rows = 4 distinct defects**, none reachable from a clean run |
| Docs vs code | — | 0 on any figure or definition; 5 stale or loose statements |

Checker sensitivity: 28 single-figure changes were injected into the feed, ledger or chart files; 27 were
flagged. The 28th (+0.06 on a best move of 10.953917) changes no displayed digit.

## What was checked (declared before the results)

1. Every ledger row: entryPrice, tags, forward measures, odds-on-the-day columns (dayScaled20 included), membership.
2. Feed `grade_odds`, every field.
3. Feed `if_it_misses` and `example_if_it_misses`, every field.
4. Feed `odds_fade`, recomputed from the docs: tier, every share, aliases, `tier_fixed_on`, each edge mark on the exact share.
5. Every card: REPLAY `cards`, `example_card`, every `open_signals[].card`; and that forming cards exist only on 1D-5D, gate on at the trough, non-empty sample.
6. Feed `open_signals`, `prints`, top-level fields.
7. Feed `past_paths` and `example_past_paths`.
8. The page in Chromium: every picker button, the example, Chart tab (both views), Past signals (all / ETH / BTC), Previous signals, How to read, banner, footer.
9. Labels against meaning.
10. Entry quality only: nothing reads as a return, a trade taken or a track record.

## Disagreements, frozen states

None.

## Defects in other states (not in either frozen state)

| State | Where | Shown | Mine | Cause |
|---|---|---|---|---|
| Synthetic: a live signal's `card` missing from the feed (BTC 2D, feed says edge lost) | Now card, status line | "On track. It has neither risen 10% nor lost its edge; its odds hold at every fall measured." | "Edge lost" | Without `o.card` the page builds the card itself (`cardFromOpen` fallback) and drops `edge_status`. Previous signals still lists the same signal as "Edge lost" |
| Same state | "Edge gone below", ladder, day-10 tile | "−20% in the first 10 days · $69,275.95"; ladder "ETH tier signals"; "Red on day 10, rose 10% after 63%" | none (no card) | The fallback puts the pooled ETH early-dip table on a BTC signal. Reachable only if `cards_open.csv` is missing while `open.csv` exists (`feed_live.py` then sets every card to null without withholding) |
| Synthetic: chart file one daily bar behind the feed | Chart, "Today" line | on the 11 Nov candle | 12 Nov | The page takes the last bar served as today's. Follows from note (x): a chart file is accepted with 10+ numeric bars and no date check. Confirms and Day 60 lines stay right (placed by date) |
| Synthetic: lead-trader feed with trades in the other asset only | Card marker | "Lead trader: out" | "not in" | `leadState()`; How to read promises "in, out or not in" |
| Synthetic: prices under about $5 | Chart price axis | "$0" on every gridline | distinct labels | Axis labels are whole dollars. Not reachable for BTC or ETH |

Rows 1 and 2 are one distinct defect (the fallback), counted as 3 rows in `disagreements.csv`.

## Docs vs code (counted separately)

| Where | Statement | Code |
|---|---|---|
| `refresh.py` docstring | reads ETH charts and BTC_2D, "writes the ten dataset CSVs" | also reads both assets' 1D candles; writes 13 files |
| `stack_live.py` docstring | lists three outputs | also writes `open.csv`, `cards.csv`, `cards_open.csv`, `cards_example.csv` |
| FEED_SPEC, `low_date` | "can be a day earlier" than `low_day` | up to 2 days on 3D, 4 days on 5D |
| member-site README | "nothing is typed in" | the page types its definitions (10%, 25.3%, 3.3x / 5%, 60 days, the 2020 start year, the example's date); FEED_SPEC and the page comment state this correctly |
| Page, How to read | "Signals only fire while our market filter says the broader trend is on your side" | the gate is read on the trough date (note a): replays of 9 Feb 2022, 5 Dec 2025 and 14 Dec 2025 show forming cards, and day-1 live top-grade cards, under "Market filter: off" |

No doc disagrees with the code on a figure, a threshold, a window or a rounding rule.

## Checks passed, by number

| # | Check | REPLAY | CURRENT |
|---|---|---|---|
| — | Data integrity (multi-day bars = daily candles bucketed within the year; last bar is today's) | 10 | 10 |
| 1 | Ledger rows (919 / 921 rows, 27 fields each; membership both ways) | 24,815 | 24,869 |
| 2 | `grade_odds` (10 rows; the two HTF-divergence rows are out of scope) | 70 | 70 |
| 3 | `if_it_misses`, `example_if_it_misses` | 86 | 86 |
| 4 | `odds_fade` (my tier: 13 chart/tag pairs; 7 rows; edge on exact share) | 54 | 54 |
| 5 | Cards (4 forming + example + 23 live / example + 21 live) | 1,763 | 1,387 |
| 6 | `open_signals`, `prints`, top-level | 512 | 462 |
| 7 | `past_paths`, `example_past_paths` (61 days x 3 quantiles each) | 557 | 557 |
| 8 | Page | 3,505 | 2,928 |
| | Total | 31,372 | 30,423 |

Page (REPLAY / CURRENT): files served 14 / 14; banner, header, footer, How to read, lead panel 5 / 5; picker
14 / 6; Previous signals 32 / 32; Now cards 450 / 150; Chart tab 484 / 215; Past signals 2,505 / 2,505;
script errors 1 / 1.

Chart tab, per card: Entry (or Today) line on the bar that closes on the entry date (holds today); Confirms
line on the confirmation bar; Day 60 on the bar holding that calendar day; level lines, zones and price tags
(exact decimal arithmetic); ladder bands with share, n and colour on the exact share; every candle; both
axes; the cloud at my quantiles for all 61 days. Example: "At the alert" is scaled and drawn only from bars
up to the entry and shows no outcome; "What happened" agrees with the daily candles.

9. Labels: every figure in both frozen states measures what its words say. Each sample names its rule and n;
   ladder rows, eras and miss tiles carry their own n and pool; the live card says "as of the entry close".
10. Entry quality only: no member text presents a return, a win rate, a trade taken or a track record; no
    grade letter or internal name appears. Card, chart side box and Past signals end with the entry-quality line.

## Replays (states in neither frozen state)

60 runs through `tests/replay_at.sh` on a copy, each followed by the full data and page checks.

| Kind of state | Runs |
|---|---|
| Market filter off | 22 |
| First / last day of a filter episode (Jun and Aug 2021, Jan 2022, Jan 2023, Dec 2025, Sep 2026) | 12 |
| Year-ends (31 Dec and 1 Jan of 2020-21, 2023-24, 2024-25, 2025-26) | 9 |
| A top-grade forming low | 18 |
| Nothing live at top grade and nothing forming (quiet card); of these, no open signal on any chart | 13; 10 |
| A top-grade signal on day 60; on day 1 (no closed bar yet, best / worst "n/a") | 9; 7 |
| Forming cards under "Market filter: off" | 6 |
| Other clock times (00:02, 00:14, 23:50 UTC) | 4 |

Across them: 140 forming cards (61 with the confirmation bar open today), live top-grade edge statuses
lost 50, rose10 144, intact 39. All 100 "must close above" prices equal my threshold floored to the cent; for
the 92 tested directly (2 in REPLAY, 90 in replays) a close at the shown price does not confirm and a close
one cent above does.

Envelope: replaying 11 Nov with the clock at 12 Nov 00:05 UTC fails in `stack_live.py` ("today's bar is
missing"), the feed is withheld with no cards, open signals or example, and the page reads "Setups held back".

Synthetic states that passed: feed down, held, fail-closed, stale (4h59, 5h01, 6h30, 49h), quiet with the
filter on and off, top-grade forming card, every edge status, day 60, day 1, extras withheld, ledger and
chart and example files missing / empty / cut short / malformed, example card missing, an asset/grade with
no misses, an empty sample, lead-trader trades, 0% / 100% / exactly 70.0 / 69.999999 shares, an era with no
signals, a price over $1,000,000.

## Definitional notes (not counted)

Notes (a) to (x) of the brief were all met and none is contradicted by the repo's own stated choice:
(a) gate on the trough date; (b) clamp; (c) low before high; (d) "must close above" one bar out; (e) day in
progress; (f) `peaked_10_or_more`; (g) (i) odds-fade tier, in-sample; (h) lens rows out of scope; (j) "known
by then"; (k) field names; (l) the page opens on the best forming card ahead of a live setup; (m) live card
as issued; (n) (o) lead trader; (p) (s) medians; (q) liveread; (r) signals a year; (t) "n/a" before a closed
bar; (u) replay bar; (v) labels over candles; (w) sample rule; (x) file acceptance.

Remarks, not counted:

- In the fail-closed envelope state the ledger, grade odds and Past signals tab are still published. The
  brief excludes testing what that state shows; noted only.
- The example button reads "Sep 2024" where dates elsewhere print "Sept"; ETH daily candles have one gap,
  21-22 May 2016, before any graded ETH signal. Neither touches a figure.

## Method

- Thresholds are tested with exact rational arithmetic on the candle prices; shares and medians are rounded
  half away from zero on the exact value. The pipeline's floating-point results agree everywhere.
- The page was served through Playwright as specified; expected text was built from my values, not the feed's.
- My first replay batch was mis-launched; its outputs remain in `replays/` because a safety check declined
  the removal. `replays2/` is the batch reported here. The repo copies used for replays are deleted.

## Files

In `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit19/`: `all_checks.csv`
(frozen, synthetic, envelope: 61,988 rows), `all_checks_replays.csv.gz` (1,392,325 rows),
`disagreements.csv` (6 rows, all synthetic), `progress.log`, and the scripts.
