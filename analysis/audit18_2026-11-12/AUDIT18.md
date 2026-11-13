# Audit 18: ETHKROS member site against the raw candles

Independent audit, 13 Nov 2026. Own code throughout (`core.py`, `stage_data.py`, `page_expect.py`, `run_page.py`);
only `regimes.py` was imported, for the gate, and the gate was also rebuilt and compared. No earlier audit, no
`docs/AUDIT_LOG.md`, no other scratch folder was read. Nothing in the repo was edited, committed or pushed.

Everything the site shows measures **entry quality only**. There is no exit in the data, so none of it is a
strategy return or a track record, and every signal is computed: none was taken.

## Top line

| Scope | Comparisons | Disagreement rows | Distinct figures / defects |
|---|---|---|---|
| **Two frozen states** (REPLAY 04:14 and CURRENT) | **58,409** | **0** | **0** |
| Other states: 98 replayed dates | 2,152,774 | 20 | 1 defect (one replay, 2020-08-15) |
| Other states: synthetic page states | 15,947 | 8 | 3 defects |
| Other states: frozen pages under 4 browser settings | 25,484 | 0 | 0 |
| Docs vs code | | | 2 |

## What was checked (declared before the results)

1. Every ledger row: entry price, tags, every forward measure, the grade columns, the odds-on-the-day columns (dayScaled20 included), membership both ways.
2. Feed `grade_odds`, every field (the two HTF-divergence rows excepted: lens logic).
3. Feed `if_it_misses` and `example_if_it_misses`, every field.
4. Feed `odds_fade`, recomputed from my own tier: every field, the after-day-10 fields and their aliases, `tier_fixed_on`, each edge mark on the exact share.
5. Every card (forming cards, `example_card`, every `open_signals[].card`): every field, sample text and n, ladder shown and exact, low day, confirmation date by the bar rule, must-close-above, prices, medians, eras, timing, edge; cards only on 1D-5D with the gate on at the trough.
6. Feed `open_signals` (ids, dates, days, day 10/30/60, best/worst, edge level and status), `prints`, and the top-level fields.
7. Feed `past_paths` and `example_past_paths`.
8. The page under Playwright: every picker button, the example, the Chart tab (both views, line / zone / band positions, axis scale), Past signals (all, ETH, BTC), Previous signals, How to read, banner, footer.
9. Labels against meaning.
10. Entry quality only.

## Disagreements in the two frozen states

None. Every one of the 58,409 figures compared equals my value, to the last digit shown.

## Defects found in other states (not in either frozen state)

| State | Where | Shown | Mine / expected | Cause |
|---|---|---|---|---|
| Replay 2020-08-15 | Feed card ETH 3D, forming, and its page card, picker, chart | Sample "all 0 past signals of the same grade across all ETH charts"; page prints "n/a%" (big number, line under it, +20% and −30% tiles, picker), "+10% · null% of past signals got here", "High usually ~day null", "Edge gone below: Holds at every level" | No card on an empty sample, or plain "n/a" throughout | A forming card is issued when the fallback sample is empty. ETH grade A had no closed signal before 12 Sep 2020. Cannot recur on today's data: the smallest fallback pool is 33. 20 rows, one cause |
| Synthetic: ledger arrives short | Past signals tab, Previous signals | Header only: "0 signals · 0 missed +10%". Cut part-way: "105 signals · 15 missed +10%", 105 rows, no warning | "unavailable", or a warning: the summary boxes on the same tab say 104 + 33 = 137 | The page treats any ledger it can parse as the whole record. A missing or empty file does read "unavailable" |
| Synthetic: candle file with no bars | Chart tab | Live setup: script error; the chart, title and side box of the setup charted before stay on screen. Forming setup: 42 chart elements with NaN coordinates | "Chart data unavailable" | `bars[E].c` is read before the empty-file case is handled. A missing file, and files of 1 or 10 bars, are handled without error |
| Synthetic: example chart file stops before day 60 | Chart tab, "What happened" | Script error; side box not updated; with 30 bars the chart draws "This one: $2,729.39 · +5.8% · days 5–6" | No outcome from a partial window (true best +33.6%, days 51–52) | The outcome is taken from whatever bars the file holds. A missing file reads "Chart data unavailable" |

## Docs vs code

| # | Docs say | Code does |
|---|---|---|
| 1 | CARD_SPEC: the sample is "chosen by the first rule that gives 15 or more" | `stack_live.py` uses rule 3 whatever its size. Replays of 2020 give n = 0, 5 and 7. No effect today (smallest pool 33; the example's is 75) |
| 2 | SITE_CHANGES 6c: the page prints "n/a" (not "n/a%"); `tests/test_page_states.py` fails on "n/a%" | The ladder and era rows do. The big number, the line under it, the +20% / −30% tiles, the picker and the chart side still print "n/a%" for a card with no sample |

## Checks passed, by number

| # | Check | REPLAY | CURRENT |
|---|---|---|---|
| – | Raw candles (order, multi-day bars rebuilt from daily, today's bar, gate rebuilt, no gap inside a scored window) | 32 | 32 |
| 1 | Ledger (919 / 921 rows) | 22,980 | 23,030 |
| 2 | `grade_odds` | 72 | 72 |
| 3 | `if_it_misses`, `example_if_it_misses` | 88 | 88 |
| 4 | `odds_fade` | 62 | 62 |
| 5 | Cards (4 forming + example + 23 live / example + 21 live) | 1,871 | 1,473 |
| 6 | Open signals, prints, top level | 558 | 502 |
| 7 | Past paths | 558 | 558 |
| 8 | Page | 3,463 | 2,908 |
| | Total | 29,684 | 28,725 |

Page detail (REPLAY / CURRENT): Now cards 457 / 174, Chart 481 / 209, Past signals 2,508 / 2,508, files and How to read 17 / 17.

9. Labels: every label template on the four tabs was read against the definition of the number beside it. None found that says something other than what is measured.
10. Entry quality: the page text was scanned for trade, win, profit, return, fill, position, track record. The 12 sentences found are disclaimers ("not a trade or a track record") or the lead-trader panel (note o).

## Other states, coverage

| Replay coverage (98 dates, mid-2020 to 11 Nov 2026) | Replays |
|---|---|
| Market filter on / off | 65 / 33 |
| A top-grade forming low | 29 |
| Confirmation bar is today's open bar | 41 |
| The day after a confirmation (best / worst n/a) | 32 |
| A signal on its 60th day (and the day after, when it leaves) | 21 |
| Quiet card (no card, no live top-grade setup) | 28 |
| Nothing live or forming on any chart | 7 |
| Year-end and New Year (2020 to 2026) | 12 |
| Forming card under a filter-off header (note a) | 7 |
| Gate-off forming low under a filter-on header (no card) | 3 |
| An asset/grade with no misses | 11 |
| Top-grade live setups by status: rose 10% / on track / edge lost | 132 / 76 / 63 |

Each replay ran `tests/replay_at.sh` on my copy of the current state, then my whole audit (checks 1 to 8). Two used other
clock times on the same day (00:01, 23:59). 30 dates were random. Per-date results: `replays_summary.csv`.

Envelope: clock on 12 Nov 00:05 with candles ending 11 Nov fails closed (stack status FAILED "today's bar is
missing"; cards, open signals and the example withheld; the page says "Setups held back").

Synthetic page states, all rendered and compared: feed down; held back (the real failed run above); fail-closed
feed; feed 299 / 301 / 419 / 1,770 minutes old; stale and quiet; no setup with the filter on and off; a top-grade
forming card; live cards at seven edge level / status / best-worst combinations (near-zero and exact-70 shares included);
no misses; extras withheld; ledger missing and short; chart files missing and short; example file missing and
short; a lead-trader feed with trades and with none; half-way and near-zero figures. Browser settings: UTC+14 with
a German locale, US Pacific, a 390 px phone, a 2560 px screen.

My own harness was tested: 11 changes to the feed the page reads produced 95 page disagreements, and one daily low
changed by 3% in my inputs produced 48 data disagreements.

## Definitional notes (not counted)

The known choices (a) to (w) all hold as stated; the repo does not contradict any of them. Seen directly:
(a) a forming card under "Market filter: off" in 7 replays; (b) one clamp per chart, BTC 15 Apr 2017 and ETH
21 Jun 2017; (c) low before high in every ladder and edge walk; (d) must-close-above one bar early; (e) day in
progress; (f) `peaked_10_or_more` is 0 in every row; (g) and (i) my tier (13 chart/tag pairs), built by refresh.py's rule, reproduces
the fade and the per-year figure; (j) entry + 60 on or before the date; (l) REPLAY opens on the best forming
card although a top-grade setup is live; (m) every live card's sample holds only closed signals; (n) and (o) lead-trader
panels read "unavailable"; (p), (r), (s) as labelled; (t) "n/a" on day 1; (u) and (v) replays were run from 15 Aug 2020 on. (h), (k), (q), (w) were not checked, as scoped.

Further notes from this audit:

- Rounding is applied to the stored figure's binary value (rounding.py says so; the page's toFixed does the same). My
  expected values round the exact decimal. They agreed everywhere, so no stored figure sat on an exact half.
- Quartiles of the past paths use linear interpolation between order statistics; the docs do not name the method.
- ETH daily candles have no bars for 21 and 22 May 2016 (the exchange printed none). No scored 60-day window touches them.
- Dates render "Sept" (the browser's en-GB short month) while one typed label says "Example: ETH 2D, Sep 2024". Not a figure.
- An independent count reproduces FEED_SPEC's "38 of the 271 filter-off days" with nothing live or forming.
- Grades and lenses were taken as given. Confluence cells, `confluence_windows`, `alerts` and `candle_check` were not checked.

## Files (all in this folder)

| File | Holds |
|---|---|
| `all_checks.csv` | 99,840 rows: both frozen states, the synthetic states, the browser-setting runs |
| `all_checks_replays.csv.gz` | 2,152,774 rows: every comparison in the 98 replays |
| `disagreements.csv` | The 28 rows above |
| `replays_summary.csv`, `synth_notes.json`, `dumps/` | Per-replay results; what the page showed in the defect states; page text of both frozen states |
| `progress.log` | Stage notes with running counts |
| `core.py`, `stage_data.py`, `page_lib.py`, `page_expect.py`, `run_page.py`, `replay_run.py`, `synth.py`, `env_variants.py`, `scan_dates.py`, `mutate_test.py` | The audit code. `replay_run.py` and `synth.py` need a copy of a state folder at `rep/src`; the replay copies were deleted |
