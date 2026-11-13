# Audit #20 — ETHKROS member site against the raw candles (13 Nov 2026)

Independent recomputation, my own code only (`alib.py`, `adata.py`, `apage.py`, `apagecheck.py`, `csynth.py`, `psynth.py`
in this folder; `regimes.py` imported for the gate, nothing else). Prices are exact rationals built from the CSV text,
thresholds are tested exactly, rounding is half away from zero on the exact value. Nothing in the repo was edited.
Entry quality only: every figure checked here is a computed signal's 60-day record. None is a fill, a strategy return or a
track record, and none can be, because the data has no exit.

## Top line

| Group | States | Comparisons | Disagreement rows | Distinct figures |
|---|---|---|---|---|
| (A) the two frozen states | 2 | 60,174 | 0 | 0 |
| (B) replays of real dates, Sep 2020 on (`tests/replay_at.sh`, no tampering) | 110 | 2,357,666 | 2 | 1 (a replay artifact, not a site figure) |
| (C) deliberately broken or synthetic states: targeted assertions | 150 | 711 | 29 | 13 (9 causes) |
| (C) tampered candles the pipeline still published, re-audited in full | 5 | 138,427 | 0 | 0 |
| Docs vs code: figure / threshold / window / rounding | | | 1 | (rounding wording; no instance found) |
| Docs vs code: loose or stale sentence | | | 11 | |

Checker sensitivity: 20 hand edits planted in a copy of the replay state (feed, ledger, one chart file) were all caught,
20 of 20 at the data level and again on the page (68 page rows). Those rows are not counted above.

## What was checked (declared before results)

1. Every ledger row: entryPrice, low, tags, every forward measure, the odds-on-the-day columns (dayScaled20 leaving out
   signals with no year of volatility), membership.
2. `grade_odds`, every field (the two HTF-divergence rows are out of scope).
3. `if_it_misses` and `example_if_it_misses`, every field.
4. `odds_fade`: tier re-selected by refresh.py's rule, pool rebuilt on daily candles, every field, aliases,
   `tier_fixed_on`, each edge mark on the exact share against 70%.
5. Every card (forming, example, every open signal's): every field, from-entry row, ladder (shown and exact), low_day,
   confirms_on by the bar rule, must_close_above (and that a close at it does not confirm and one cent above does),
   price_now / entry_close, medians (1 and 6 places), eras, timing, sample text and n, edge; which lows get a card.
6. `open_signals` (ids, dates, days, day 10/30/60, best/worst, edge level and status), `prints`, top-level fields.
7. `past_paths` and `example_past_paths`.
8. The page in Chromium: every picker button, the example, Chart tab (both views; every candle, line, zone, band, axis
   and date label by position), Past signals (all / ETH / BTC), Previous signals, How to read, banner, footer.
9. Labels against meaning. 10. Entry quality only.

## Every disagreement

| Group | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| B | replay 2024-11-22 (04:14 and 00:01) | Example chart file vs raw ETH 2D | 1 bar differs | 0 | Replay artifact. The example chart file is a static asset that `replay_at.sh` does not cut; its last bar (22-23 Nov 2024, after day 60) holds 23 Nov data. No card figure is affected |
| C | feed with `cards_withheld` true but cards left in | Now card | cards shown | held back | Hand-edited feed. The page trusts the list, not the flag; feed_live always empties the list |
| C | no posting bar anywhere and `odds_fade` empty | Chart tab | JavaScript error, chart blank | unavailable | Hand-edited feed |
| C | `price_now` a string | Chart subtitle, price tag | `$NaN` | n/a | Made-up price |
| C | no typical day of the high | Chart label | "High usually ~day null" | n/a | Hand-edited feed |
| C | unknown `edge_status` | Card status, Previous signals badge | "On track" | "Status unavailable" | Hand-edited feed; stack_live writes only lost / rose10 / intact |
| C | unknown `market_regime` text | Header | "Market filter: off" | "unavailable" | Hand-edited feed; only empty or missing reads unavailable |
| C | `generated_at` missing, null or not a date; feed a JSON list (4 states) | Whole Now tab | JavaScript error, card area blank | "Data unavailable" | Damaged feed; the header throws before the card renders |
| C | lead-trader trade with empty fields | Card | "Lead trader: in · null" | no placeholder | Live lead-trader feed, malformed row |
| C | `BTC_1D.csv` cut to 40 bars; `ETH_2D.csv` cut to its first half (2 states) | Feed and page | every step passed; cards and alerts published | held back | Candle file cut short. In a real run fetch.py rewrites every candle file and check_candles.py checks the last 90 daily bars; the scoring steps do not notice on their own |

No disagreement was found on any figure a working pipeline publishes.

## Checks passed, by number

| # | Check | (A) comparisons | (A) diffs | (B) comparisons | (B) diffs |
|---|---|---|---|---|---|
| — | Raw candles: 2D-8D bars = my bucketing of the daily bars; chart files = last 70 raw bars | 64 | 0 | (rebuilt by the replay) | |
| 1 | Ledger rows | 47,844 | 0 | 1,770,040 | 0 |
| 2 | grade_odds | 140 | 0 | 7,694 | 0 |
| 3 | if_it_misses, example_if_it_misses | 172 | 0 | 9,450 | 0 |
| 4 | odds_fade | 110 | 0 | 5,861 | 0 |
| 5 | Cards (forming, example, open) | 3,548 | 0 | 176,845 | 0 |
| 6 | open_signals, prints, top level | 972 | 0 | 51,527 | 0 |
| 7 | past_paths, example_past_paths | 1,114 | 0 | 61,270 | 0 |
| 8 | Page | 6,180 | 0 | 272,826 | 2 (the artifact above) |
| 9 | Labels vs meaning (read by eye on both frozen states, every tab) | — | 0 | — | |
| 10 | Entry-quality wording present; nothing reads as a return or a trade taken | 30 | 0 | 2,153 | 0 |

Frozen states: replay 30,544 comparisons, current 29,630 (each includes 32 raw-candle checks). Both show the live top-grade
BTC 2D of 21 Sep 2026 as "Edge lost" (fell to its −5% edge level before rising 10%), on my figures as well.

Group B coverage (110 replay states; list in `replays.txt`, `replays2.txt`, results in `replays.log`):

| Kind of state | Replays |
|---|---|
| Market filter off | 23 |
| First or last day of a filter episode (Jun and Aug 2021, Jan 2022, Jan 2023, Dec 2025, Sep 2026) | 12 |
| Year-ends, 30 Dec to 2 Jan (2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26), and the 2024 leap day | 19 |
| A top-grade forming card | 35 |
| Nothing live or forming on any of the 10 charts | 11 |
| Quiet card shown (no top-grade setup to select; the "times a year" figure checked) | 23 |
| A signal's day 60 in progress, and the day after it closes | 9 |
| Day after a confirmation (live setup with no closed bar yet: best / worst "n/a") | 10 |
| Confirmation bar is today's open bar | 68 |
| Clock other than 04:14 (00:00:30, 00:01, 00:02, 00:03, 08:43, 12:30, 16:13, 20:13, 23:58) | 10 |
| Before 22 Nov 2024, so no worked example ("Example unavailable") | 67 |
| Live top-grade signals seen, by status | lost 77, rose 10% 248, on track 99 |
| Forming lows correctly without a card (8D, gate off at the low, or empty sample) | 56 states |

Group C, what failed safe (all as expected): feed 404 / malformed / empty / an HTML error page; held feed; fail-closed
feed; stale feed (5 h 30, 30 h; not at 4 h 54); ledger missing, header only, cut short, cut mid-row, garbage, one row
dropped or duplicated; chart file missing, 9 bars, non-numeric, null, not JSON, not reaching the entry, two days old
("Latest bar · date", not "Today"); example file missing, cut short, malformed; example card null; extras withheld; a
made-up asset (forming and live); live card missing; status missing; exact 69.999999 against a shown 70; exactly 70.
Pipeline level: clock on D+1, D+2, D+30 and D−1 against candles ending D (five cases, all "today's bar is missing",
cards, open signals and alerts withheld); a daily or chart file missing, empty, header only, stale by one or two bars,
with a garbage row, with text in a price, with a negative price; funding file missing; cards.csv, cards_open.csv,
cards_example.csv hand-edited (including by 0.00001) or a live card deleted before the card check; a ledger figure edited
after grading; a FAILED line in stack_status.txt; each gating step reported failed; feed_live crashing (fail-closed feed,
"Market filter: unavailable"); extras missing (extras withheld, cards still out). A live lead-trader feed lists each
trade with price, leverage and share of account, never a dollar size or contract count, and the card reads in / out / not in.

Five tampered-candle states were published by the pipeline with every step green (a deleted mid day on two base dates, ETH close
halved, a made-up 0.01 flash low, a zero 2D close). I re-audited each in full on the same tampered candles: 0 disagreements, so
what was published was self-consistent. Whether such candles are stopped is fetch.py's and check_candles.py's job.

## Docs vs code

| Kind | Where | What |
|---|---|---|
| Rounding rule | FEED_SPEC "Audit corrections" and audit #8, CONTEXT (1); rounding.py | The docs say half away from zero on the exact (6-place) value. rounding.py and the page's toFixed round the float's binary value (its docstring: 2.675 gives 2.67). A stored value ending exactly in 5 at the display digit could print one unit low. I round the decimal and found no instance in 2.4 million comparisons |
| Stale (window) | CONTEXT "Confirmation lag" | "3, 6, 9, 15, 24 days" is bar open to bar open. The date fields are now trough bar open and confirmation close, so low_date to confirms_on is 3, 7, 11, 19, 31 days (e.g. ETH 3D 13 Sep to 24 Sep 2026) |
| Stale | CONTEXT, regime blind-spot note | "episode 2021-08-19 to 2022-01-25": the gate's last on day is 26 Jan 2022 (off from the 27 Jan bar) |
| Stale | engine.py docstring | "mirrors ct_zone_bounce_v8.pine"; CONTEXT names v15 as the live indicator |
| Stale | grade_live.py docstring | Lists five ETH and two BTC lenses; the code also counts FCOOL, BTCX and FASTCT (lens logic itself is out of scope) |
| Stale | refresh.py docstring; README | Names a "buydates" dataset (it writes buy.csv); README says ten datasets (it writes 13) |
| Stale (figure in a comment) | measures.py docstring | "A+ (79%) from C (58%)"; today ETH 80 / 54, BTC 76 / 60. Not member-facing |
| Loose | FEED_SPEC audit #9 | "counted from the ledger (2020-2025)"; the page counts 2020 to last year, so it rolls in January |
| Loose | CARD_SPEC, "Beat a normal move" | Does not say signals with no year of volatility are left out of the denominator (the code and a grade_live comment do). Not on the member page |
| Gap | CARD_SPEC / FEED_SPEC | Odds-on-the-day columns (weight 5 toward the base rate, 10 prior signals minimum), `trades_a_year`, and the quartile interpolation of past_paths are defined only in code or README |
| Stale | member-site README | Header still describes the 11 Nov review snapshot |
| Loose | CARD_SPEC wording rules | "The card always ends with: these are past signals, not real trades..."; the member card's foot says the same thing in other words |

## Definitional notes (not counted)

Known choices (a) to (y) in the brief were applied as given; the repo did not contradict any of its own stated choices.
Those that mattered in practice: (a) gate read on the trough date, header shows today's filter (quiet card and live cards
under either header were seen in replays); (d) must_close_above one bar ahead assumes today's bar closes at the current
price; (e) "day N of 60" is the day in progress; (j) known-by-then is entry + 60 on or before the date; (m) a live card is
the card as issued, labelled "as of the entry close, not from today"; (n) lead trader "unavailable" in this harness; (t)
best / worst "n/a" before the first closed bar; (u) the replay keeps the date's own bar whole; (w) rule 3 at any size, no
card on an empty sample; (x) the page's acceptance tests for ledger and chart files.

Mine, where the docs are silent and I took the rule from the code:
- A forming low is a CT pivot 1 to 3 bars behind the open bar that no later bar has undercut.
- ETH ledger membership needs funding on the entry day, 60 of the prior 90 days, and 5 of 7 days in both cooling windows.
- Fade bands are (lower, upper], and a band or day-10 row needs 5 signals.
- Quartiles use linear interpolation.
- Day of the high and of the low take the first occurrence; the dip before the high includes the high day's low.
- An open signal with an empty sample (early history) carries no edge level, so its status can only be rose10 or intact;
  the page shows "No odds yet" for it.
- Chrome prints "Sept" for September in dates; I treated "Sept" and "Sep" as the same.

## Files

`all_checks.csv` (group, state, location, label, shown, yours, ok, cause): groups A and C in full; for group B one summary
row per replay plus its disagreements, the full rows being in `replays/checks_<state>.csv.gz`. `disagreements.csv`: all 31
rows. `frozen/`, `replays/`, `synthetic/`: per-state check files and summaries. `progress.log`: stage notes.
