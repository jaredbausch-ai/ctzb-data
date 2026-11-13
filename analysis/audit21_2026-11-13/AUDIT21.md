# Audit 21: ETHKROS member site, independent check (13 Nov 2026)

Everything here measures **entry quality only**. The site's signals are computed signals, not fills; no trade was taken and there is
no exit in the data, so nothing below is a strategy return or a track record. All figures were recomputed from the raw candles with
my own code (own indicator, pivots, tags, windows, rounding, page reader); only `regimes.py` was imported, for the gate. Nothing in the
repo was edited. Earlier audits and the audit log were not read.

## Top line

| Group | States | Comparisons | Disagreement rows | Distinct | A wrong figure among them |
|---|---|---|---|---|---|
| (A) the two frozen states | 2 | 61,125 | 0 | 0 | 0 |
| (B) replays of real dates, Sep 2020 on | 188 | 4,136,858 | 39 | 2 | 0 (both are wording) |
| (C) deliberately broken or synthetic states | 133 | 484 | 21 | 11 | 4 (duplicated row, reversed rows, stale filter reading, footer date) |
| Docs vs code: figure / threshold / window / rounding | about 70 statements read, 13 figures recomputed | | 1 | 1 | 0 on the member page |
| Docs vs code: loose or stale sentence | | | 2 | 2 | |

In the two frozen states and in 188 replays of real dates, no number on the feed, the ledger or the page differed from mine.
The checker itself was tested by planting errors (39 in the feed and ledger, 26 in the feed, ledger and chart files behind the page): all were caught.

## What was checked (declared before the results)

1 ledger rows; 2 grade_odds; 3 if_it_misses and the example's; 4 odds_fade; 5 every card (forming, example, live); 6 open signals,
prints, top-level fields; 7 past paths and the example's; 8 the page with Playwright (every picker button, the example, Chart tab at
the alert and what happened, Past signals for all / ETH / BTC, Previous signals, How to read, banner, footer); 9 labels vs meaning;
10 entry quality only. Group B ran all ten on each replay; group C checked what the docs say a broken state must show.

## Every disagreement

| Group | State | Where | Shown | Mine | Cause |
|---|---|---|---|---|---|
| B | Replays 9, 10, 13 Jun 2021 (BTC 3D, confirms 17 Jun); 28, 29 Jan, 1, 5 Feb 2022 (ETH 3D, confirms 5 Feb); 12, 14 Dec 2025 (BTC 3D, confirms 14 Dec). 9 rows, 3 setups, none top grade | Forming card "Low 8 Jun 2021" / "27 Jan 2022" / "5 Dec 2025", with How to read: "A signal only counts if our market filter said the broader trend was on your side on the day its low printed" | A card, although the filter was off on the day shown as the low | Filter on only at the trough bar's open date, two days earlier | Wording. The gate is read on `low_date` (bar open); the page calls `low_day` the day the low printed. The same three are ledger rows (grades B, C, C) |
| B | 30 live top-grade setups in 18 replays, e.g. 19 Apr 2024, ETH 3D of 3 Mar 2024, day 47 | Previous signals, group heading | "Edge intact" (badge "Rose 10%"), worst so far -18.3% against an edge level of -15% | It fell to its edge level after rising 10% | Wording. Status `rose10` is grouped under "Edge intact". The card's own sentence ("rose 10% before falling to its edge level") is right |
| C | Feed with a null entry in `cards` or `grade_odds`, a card ladder that is not a list, a `past_paths` entry without `days` (4 rows) | Now / Chart tab | Card area blank, header stuck on "Market filter ..." (script error) | "Data unavailable", or the entry skipped | The page validates the feed object and `generated_at` only, not list entries |
| C | Regime neither Bullish nor Bearish, nothing live or forming | Quiet card | "The market filter is off, so the system is quiet" under a header reading "Market filter: unavailable" | No "off" claim | Quiet card tests for "bull" only; FEED_SPEC says unknown reads unavailable, never off |
| C | `edge_status` missing or unknown (5 variants) | Previous signals | Listed under "Edge intact" with badge "Status unavailable" | Not under "Edge intact" | Unknown status falls into the intact list |
| C | Live signal without `days_elapsed` | Card line, picker | "day null of 60", "Day null" | "n/a" | No guard on a missing day count |
| C | `cards_withheld` true but `checks.all_passed` true | Footer | "checks passed" beside "Setups held back" | "FAILED, cards held back" | Footer reads a different field from the card |
| C | Live lead-trader feed, leverage and size not numbers | Lead trader panel | "n/ax", "n/a% of acct" | "n/a" | Unit appended to "n/a" |
| C | `BTC_1D.csv` with its last row duplicated | Pipeline and page (3 rows) | Every step passes, feed not withheld, a BTC 1D "Setup forming" card that the true candles do not have | Fail closed | `history_problems` and `check_candles.py` read rows into a table keyed by date, so a repeated row is invisible; the engine reads the rows as a list |
| C | `BTC_1D.csv` with rows in reverse order | Pipeline and page (2 rows) | Every step passes, feed not withheld, BTC rescored on reversed candles; the live top-grade BTC 2D setup is gone and the page opens on the example | Fail closed | Same |
| C | `open.csv` lost after every check passed, before the feed step | Page | Feed not withheld, no live signals: the page reads as a quiet market | Held back or unavailable | `feed_live.py` treats a missing `open.csv` as an empty list |
| C | Refresh fails (ETH_3D.csv missing) on 7 Dec 2025, last good run 4 Dec, filter turned off in between | Header | "Market filter: on" in a feed stamped 7 Dec ("Setups held back") | Off, or unavailable | The withheld feed repeats `market_regime` from the last good `status.csv` |
| C | Same state | Footer | "Daily candles closed through 6 Dec 2025" beside "scored 4 Dec 2025" | 3 Dec 2025 (the data scored) | Footer date is the feed timestamp minus a day, not read from the data |
| Docs (window) | CARD_SPEC ladder row; FEED_SPEC `went_on_to_fall25_pct` | What the "fell 25.3%" share counts | Docs: "the share that went on to fall 25.3%" | Code: only those that fell 25.3% before rising 10%. Example card, falls 5% first: 12% in the feed; read as "at any time in the 60 days" it would be 19% | Wording of a feed figure's window. Not shown on the member page |
| Docs (loose) | FEED_SPEC `prints[]` | Which lows are listed | Docs: "the last 3 confirmed lows per chart"; gate-off lows "still appear in prints[]" | Code: the last 3 gate-on signals; a low that confirms with the filter off drops out. Replay 24 Jun 2026: ETH 1D prints end at 4 Dec 2025 though 23 ETH 1D lows confirmed after it | Loose sentence |
| Docs (loose) | member-site README | What the page types | Docs: only the +10% level, 25.3%, 60 days, 2020, the example's date | Page also types the ladder steps (5, 10, 15, 20%), the 5-hour staleness limit, "sometimes for a year" and "usually within the hour" | Incomplete list |

## Checks passed, by number

| # | Check | A comparisons | A disagreements | B comparisons | B disagreements |
|---|---|---|---|---|---|
| 1 | Ledger rows (entry price, tags, forward measures, odds-on-the-day, membership) | 47,846 | 0 | 3,043,708 | 0 |
| 2 | grade_odds | 204 | 0 | 19,176 | 0 |
| 3 | if_it_misses and example_if_it_misses | 230 | 0 | 21,581 | 0 |
| 4 | odds_fade (tier rebuilt with my own engine) | 126 | 0 | 11,428 | 0 |
| 5 | Cards: forming, example, every live signal's card | 3,374 | 0 | 267,848 | 9 wording |
| 6 | open_signals, prints, top-level fields | 1,368 | 0 | 120,306 | 0 |
| 7 | past_paths and example_past_paths | 1,494 | 0 | 140,436 | 0 |
| 8 | Page: every displayed number, line and zone position | 5,919 | 0 | 432,977 | 0 |
| 9 | Labels vs meaning (label text and what it is attached to) | 530 | 0 | 74,608 | 30 wording |
| 10 | Entry quality only (no strategy return, trade taken or track record) | 34 | 0 | 4,602 | 0 |

A by state: replay_0414 31,095 (page 3,554); current 30,030 (page 2,929).
Group B also holds 188 run checks (the pipeline ran clean and the feed was not withheld on every replayed date).

## Group B coverage (188 replays, 2020-09-01 to 2026-11-13, real candles, no file tampering)

| Kind of state | Replays |
|---|---|
| Market filter off | 50 (22 of them with a forming card or a live top-grade setup) |
| First and last day of each filter episode (6 flips, both sides) | 12 |
| Year-end dates (26 Dec to 4 Jan), including lows whose confirmation crosses 1 January | 36 |
| A top-grade forming low | 46 |
| No card and no live top-grade setup (quiet card) | 44 |
| Nothing live or forming on any chart | 14 |
| A signal on its 60th day (the day after was replayed too) | 32 |
| A live signal with no closed daily bar yet (day after confirmation) | 43 |
| Clock other than 04:14 UTC (00:00:00 to 23:59:59) | 19 |
| Before 22 Nov 2024 (no worked example) | 109 |

Live top-grade setups seen: 655 (rose 10% 415, on track 136, edge lost 104). No replay failed.

## Group C: what failed closed as documented

Feed down, not JSON, a list, null, no or bad `generated_at` (11 states): "Data unavailable", no figure, the example does not stand in.
Held (3 variants): "Setups held back"; the fail-closed feed also reads "Market filter: unavailable". Stale: warning from 301 minutes, none at 295.
Ledger missing, empty, cut short, cut inside a top-grade row, a row without a date: "Past signals unavailable". Chart file missing, 9 bars,
text or null price, not reaching the entry: unavailable, nothing left over; an old last bar is labelled by date. Example file broken: unavailable.
Non-numeric prices print "n/a". Markup in feed text is escaped. Pipeline: clock a day ahead of or behind the candles, candle files missing,
empty, cut at the start, a day missing, last days missing, a bar 1 cent off, text or blank price, a cut row, funding file missing, ledger
deleted or cut, a card figure altered, `cards_open.csv` or `stack_status.txt` deleted, a column lost: all withheld. Candle check (offline,
second exchange replaced by the true closes): a made-up close 1 day or 20 days back, a zero low, a high under its close all fail the run.

## Docs vs code: figures recomputed and found right

38 of 271 quiet filter-off days (FEED_SPEC #17); smallest rule-3 pool 33; example chart file 51 bars ending on the day-60 bar; first graded
ETH signal 21 Mar 2020 and first top grade 18 Apr 2020; grade sample "2020-04-18 to 2025-12-04"; low-to-confirmation 3, 7, 11, 19, 31
days and ETH 3D 13 to 24 Sep 2026; gate last on 26 Jan 2022; 25.3% = 1/3.3 less 5%; flash prints clamped on two daily bars
(ETH 21 Jun 2017, BTC 15 Apr 2017); no decimal rounding tie that the binary float decides differently; tier and "17 on average".

## Definitional notes (known choices, not counted)

(a) gate read on the trough date, header shows today; (b) flash-print clamp; (c) low before high within a day; (d) "must close above"
one bar out assumes today's bar closes at the current price; (e) "day N of 60" is the day in progress; (f) `peaked_10_or_more` is 0 by
construction; (g) odds-fade tier by refresh.py's rule on each chart's own bars as of 1 January; (h) confluence counts and the two ETH
HTF-divergence rows are lens logic; (i) pooled odds fade is in-sample, as labelled; (j) "known by then" = entry + 60 days on or before the
date; (k) compatibility field names; (l) which card opens first is layout; (m) a live card is the card as issued at the entry close, from
every signal closed by now; (n) lead-trader feed is 404 in this harness; (o) review banner and lead-trader text describe the review
period and the live product; (p) "if it misses" median over all misses; (q) liveread "Regime gate" row; (r) "about N times a year"
averages 2020 to last year; (s) typical drop is a median; (t) no closed bar yet shows "n/a"; (u) replay keeps the date's own bar whole;
(v) labels are drawn over candles; (w) sample = first of three rules giving 15, rule 3 at any size; (x) the page accepts a ledger on its
top-grade count per asset (a copied row or an edited value passes, confirmed), chart files with 10 numeric bars, the example file reaching
day 60; (y) the page types definitions; (z) feed validation at load; (aa) candle values are taken as given: a made-up close 45 days
back, a made-up high yesterday and a made-up price today all pass the candle check, as the docs allow; (ab) the example chart file is static.

## Limits

No network: the live second-exchange call, the fetch step, the Cloudflare workers, the login and the alert sender were not run. Grades
and lenses were taken as given. Files: `all_checks.csv` holds groups A and C in full; group B's rows are in `checks_B/*.csv.gz` (same
columns, one file per replay) with a line per replay in `replays.csv`; `disagreements.csv` holds every disagreement row of all groups.
Two checks were added while the replays ran (no unexplained text on a chart; filter on at the day shown as the low): they cover group A
and the replays run after that point, which include every replayed date within a forming low's reach of a filter flip.
Code is in this folder (`core.py` engine, `datacheck.py`, `pagecheck.py`, `pagerun.py`, `batchB.py`, `synthC.py`, `synthC_pipe.py`, `synth_stale.py`,
`synth_cc.py`, `finalize.py`); the replay source copy was deleted to keep the folder small (recreate with `cp -r ../a21/current src_current`).
