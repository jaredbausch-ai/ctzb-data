# Audit 15: ETHKROS member site against the raw candles (12 Nov 2026)

Independent audit. All code is mine (this folder); only `regimes.rsi_regime` was imported, for the gate.
Nothing in the repo or in the two frozen state folders was edited. Entry quality only: these are computed
signals with no exit in the data, so nothing here is a strategy return or a track record.

## Top line

- **The two frozen states: 67,174 comparisons, 0 disagreements** (REPLAY 34,083; CURRENT 33,091).
- **States that occur in neither: 5 distinct defects, 411 rows.** 1,695,953 comparisons on 55 other replayed
  dates (406 rows, 3 defects), 30,976 on the repo's gate-off replay (0), 47 on synthetic page states (5 rows).
- **Docs-vs-code disagreements: 6** (counted separately, listed below).
- Auditor self-test: 200 numbers changed in a copy of the feed and ledger, 200 flagged.

## Declared list of checks (both states where they apply)

1. Every ledger row: membership, entry price, tags, forward measures, grade columns, odds-on-the-day columns.
2. Feed `grade_odds`, every field. 3. Feed `if_it_misses` and `example_if_it_misses`, every field.
4. Feed `odds_fade`, recomputed from the documented rule (tier, groups, shares, aliases, edge marks on the exact share).
5. Every card: forming, example, every open signal's card; every field; forming cards only on 1D-5D with the gate on.
6. Feed `open_signals`, `prints`, top-level fields (plus `next_buy_date` and confluence-window dates).
7. Feed `past_paths` and `example_past_paths`.
8. The page in Playwright: every picker button, the example, Chart tab (both views), Past signals (all/ETH/BTC),
   Previous signals, How to read, banner, footer; every text, line, zone, band and marker position.
9. Labels against meaning. 10. Entry quality only.

## Every disagreement

| State | Where | Shown | Mine | Cause |
|---|---|---|---|---|
| Replays 27, 29, 30, 31 Dec 2023 (filter on) | Forming cards: `confirms_on`, `signal_id`, picker, card line, chart subtitle and side box, Confirms / Day 60 / typical-high-day lines, zones, bands | ETH 2D "confirms 1 Jan 2024"; ETH 3D 4 Jan; BTC 2D 5 Jan; BTC 3D 7 Jan | 31 Dec 2023; 3 Jan; 4 Jan; 6 Jan (three of the four later confirmed, and the ledger dates them 31 Dec, 4 Jan and 6 Jan) | `stack_live.py:307-308` dates a forming low with a fixed bar step; 2D+ bars restart on 1 January, so a year's last bar is short |
| Replay 31 Dec 2024 | Same, BTC 5D forming card | confirms 14 Jan 2025 | 10 Jan 2025 | Same |
| Replays 28, 30, 31 Dec 2025 (filter off) | `prints[]` forming lows only | 2D 1 Jan 2026; BTC 3D 7 Jan; 8D 11 Jan | 31 Dec 2025; 6 Jan; 8 Jan | Same |
| Replays 7, 8, 9, 15 Sep 2026; both frozen feeds with nothing live or forming | Quiet card, example switched off, filter on | "Top-grade setups come about ${perYear()} times a year (2020 to 2025 average)." | "... about 22 times a year ..." | `index.html:485`: the placeholder sits inside a plain string, so it prints raw |
| 38 replay dates outside 2026 | `odds_fade.sample` | "tier as fixed on 1 Jan 2026" | 1 Jan of the replayed year | `feed_live.py:333` types the year; `refresh.py:746` uses the current year |
| Replay 1 Jan 2024, ETH 2D of 31 Dec 2023 shown as live top grade (page test) | Chart tab | "This chart's data doesn't reach back to the entry" | Entry line on the 31 Dec bar | `index.html:671` finds the entry bar as open + (bar length - 1) days; the 31 Dec bar is one day long |
| Both frozen feeds, one era emptied (page test) | By era row | "n/a%" | "n/a" | `index.html:558` appends % (cosmetic) |

Rows: 364 year-end (8 dates), 4 + 2 placeholder, 38 tier year, 1 entry bar, 2 "n/a%". Details: `disagreements.csv`, `replays.csv`.

What these mean for the live product:

- **Year-end confirmation date.** 2026 is not a leap year, so the 2D bar of 31 Dec 2026 is one day long and the
  3D bar of 30-31 Dec is two. A 2D or 3D low forming in the last days of December 2026 will show a
  confirmation date one day late, and its `signal_id` will change when it confirms. By `feed_live.pending_alerts`
  the forming id would then be reported "vanished" and the confirmed one as new (read from the code, not replayed).
- **`${perYear()}`.** The filter was on with nothing live or forming on 7, 8, 9 and 15 Sep 2026. The page opens on
  the example on such a day; switching the example off shows the raw placeholder.
- **Tier year.** Correct today. Wrong from 1 Jan 2027, also in `analysis/carddesign.py:146` and `index.html:556`.

## Docs vs code (6)

1. `CARD_SPEC.md:11` says one card per forming low on every chart, 1D to 8D. Code (`stack_live.py:520`) and
   CARD_SPEC's own member-site section: graded charts 1D-5D, gate on at the trough date.
2. FEED_SPEC schema 4 says a `signal_id` is the same at every stage of a signal's life, and audit #5 says bars
   restart on 1 January. `stack_live.py:307-308` breaks both across a year-end (first rows of the table).
3. FEED_SPEC audit #9 says "about N times a year" is counted from the ledger. `index.html:594` counts it;
   `index.html:485` never prints it.
4. FEED_SPEC audit #8, `feed_live.py:333`, `carddesign.py:27,146` and `index.html:556` say "1 Jan 2026".
   `refresh.py:746` fixes the tier on 1 Jan of the current year.
5. `member-site/README.md:11` says a 404 on `trades.json` shows an empty state. The page says the lead
   trader's feed "is unavailable right now"; "No trades posted yet" appears only when the file exists and is empty.
6. FEED_SPEC "Not built yet" says the Cloudflare backend waits on the account. CONTEXT says the account,
   mirror, scheduler and member site were built 10-11 Nov.

## Checks passed, by number

| # | Check | REPLAY | CURRENT |
|---|---|---|---|
| 1 | Ledger, 919 rows, 29 comparisons each | 26,652 | 26,652 |
| 2 | `grade_odds` | 86 | 86 |
| 3 | `if_it_misses`, `example_if_it_misses` | 98 | 98 |
| 4 | `odds_fade` (13 tier pairs, 168 signals) | 56 | 56 |
| 5 | Cards (REPLAY 4 forming + example + 23 open; CURRENT example + 23 open) | 1,978 | 1,684 |
| 6 | Open signals, prints, top level, window dates | 640 | 608 |
| 7 | `past_paths`, `example_past_paths` | 563 | 563 |
| 8 | Page, the example's chart file, stale note | 4,008 | 3,342 |
| | Gate re-derived with my own RSI; CONTEXT's gate dates | 2 | 2 |
| | **Total, all agree** | **34,083** | **33,091** |

9. Labels against meaning: every label on every view read against what its number measures. No number is
   mislabelled in either frozen state. 10. Nothing reads as a strategy return, a trade taken or a track record;
   every card, the Past signals tab and the footer say entry quality only.

Also confirmed: raw 2D/3D/5D/8D candles equal the 1D candles bucketed by fetch.py's rule (0 mismatches);
`datasets/candles_*.csv` equal the last 70 raw bars; the example's 52 chart bars equal the raw ETH 2D candles.
Membership: all 919 ledger rows are my signals; the only signals of mine not in it are 203 ETH signals before
21 Mar 2020 (no funding history, per CARD_SPEC).

## Method

- Thresholds and rounding are decided in exact arithmetic from the CSV decimal strings, never in floats.
- My values feed the page check: each rendered text is compared with the string built from my numbers; each line,
  zone and band is read back from its pixel position to a date or a price.
- Other dates: a copy of the current code, candles cut at the date, 2D+ bars rebuilt from the dailies, clock set,
  pipeline run, both audits run (`mkstate.sh`, `runstate.sh`). Funding and other inputs are today's files; they
  only affect grades, taken as given. Dates before the example exists (2023) are checked without the example.
- Page tests marked synthetic alter one field in a copy of the feed to reach wording no real state had.

## Definitional notes (not counted)

As given in the brief, confirmed consistent in the repo: (a) gate read on the trough date; (b) flash-print clamp
(one bar per chart: ETH 21 Jun 2017, BTC 15 Apr 2017); (c) low before high within a day; (d) "must close above"
one bar ahead assumes today's bar closes at the current price; (e) day N is the day in progress;
(f) `peaked_10_or_more` is 0 by construction; (g) the odds-fade tier is chosen on each chart's own bars, a win
being a 60-day close above entry; (h) confluence counts and the two HTF-divergence rows are out of scope (their
counts add up to all 357 graded ETH signals); (i) the pooled odds fade is in-sample; (j) "known by then" is
entry + 60 on or before the date; (k) kept field names; (l) the page opens on the best forming card in REPLAY
(BTC 1D, not top grade) although a top-grade setup is live; (m) a live card is the card as issued at entry;
(n) trades feed 404; (o) review banner and lead-trader text; (p) median best over all misses; (q) liveread gate row.

Mine, where the docs leave a choice and I followed the code:

- `scaled20`: population standard deviation of the 365 daily log returns ending on the entry date, over the
  asset's median of that series for dates to end 2021.
- Day of the 60-day high or low: the first day it printed. Path quartiles: linear interpolation.
- `trades_a_year`: the ETH walk-forward tier's signals, one per chart and date, over the span to 60 days before
  the last bar (16.6, shown as 17). Not on the member page.
- `next_buy_date` reads "none ahead" in REPLAY with four cards forming: it only counts forming ETH lows carrying
  a tier tag, and dates them by the confirmation bar's open. Not on the member page.
- Forming buttons: top-grade first in feed order, then the rest by +10% share.

## Observations (not counted)

- "about 22 times a year (2020 to 2025 average)", once it prints: 130 top-grade signals, ETH and BTC together,
  over six years that include 2022 with the filter off. The years and the divisor are typed in the page.
- How to read says "Size your position and leverage so this dip doesn't hurt you" of the typical (median) drop;
  half of the past signals dipped further.
- Previous signals marks ETH 1D 4 Dec 2025 "Rose 10%" (best +11.0%, worst -31.2%). True as worded: +10% on day 6,
  -25.3% on day 58.

## Files

Folder: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit15/`

- `all_checks.csv`: 98,197 rows (both frozen states, the gate-off replay, the synthetic page tests).
- `disagreements.csv`: 411 rows. `replays.csv`: 55 dates with counts.
- Code: `core.py`, `audit_data.py` (checks 1-7), `page_audit.py` and `harness.py` (check 8), `extra_checks.py`,
  `page_extra.py`, `page_quiet.py`, `page_synth.py`, `page_yearend.py`, `rawcheck.py`, `mutate.py`, `mkstate.sh`,
  `runstate.sh`, `combine.py`. Per-state working files are in `work/`.
