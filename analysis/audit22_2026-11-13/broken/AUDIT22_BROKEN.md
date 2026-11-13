# Audit 22c: broken, damaged, missing and inconsistent files (page and pipeline)

Code audited: the two frozen states (HEAD 58fd6c6). Every expectation was written into the case before it ran. Entry quality only: these are computed signals, not fills. There is no exit in the data, so nothing here is a return or a track record.

## Top line

A "state" is one case run on one state folder. Counts are states; distinct cases are in brackets.

| Level | States tried | (i) wrong or unsupported figure | (ii) placeholder, script error, blank | (iii) damaged input scored or published | (iv) wording misstates state | (v) reads as return, trade or record | Total disagreements |
|---|---|---|---|---|---|---|---|
| Page | 399 (202 cases) | 106 (56) | 14 (7) | 0 | 10 (5) | 0 | **130 (68)** |
| Pipeline | 240 (240 cases) | 0 | 0 | 28 (28) | 7 (7) | 0 | **35 (35)** |
| **All** | **639** | 106 | 14 | 28 | 17 | 0 | **165 (103)** |

The repo's own tests pass (test_seal 18/18, test_feed_damage 31/31 at RENDER_LIMIT=40 REJECT_LIMIT=10). Almost every disagreement is a damage they do not try: values that are each well-typed but contradict each other or another file.

## Every disagreement

Grouped where cases share one cause. "Both" means replay_0414 and current. Every row is in disagreements.csv.

| Level | State | What was damaged (cases) | Shown | Expected | Cause (file:line) |
|---|---|---|---|---|---|
| page | both | Card shares contradict each other or their count: never-fell share above rose-10% share; +20% above +10%; 50% from n=3; whole % vs exact % (90 vs 41.2, 95 vs 37.5); ladder counts rising; deepest dip positive, high negative (F01-F06, F31) | Card drawn with those figures. F31 also logs console errors (negative SVG rect height) | Data unavailable | index.html:406-448 crossCheck (and feedcheck.py cross) has no rule for these relations |
| page | both | Counts that do not add up across sections: if_it_misses or past_paths signals differ from grade_odds; example card 75 vs cloud and misses 140; example 100% rose with 20 misses; grade_odds 0 signals with shares; median dip +12 (F07-F09, F23, F30, F32) | Contradicting counts on card, cloud and Past signals | Data unavailable | same, index.html:406-448 |
| page | both | Example card is another signal (BTC 1D 2023) under the "ETH 2D, Sep 2024" label; example card entry close differs from the example file (F10, F11) | Example card shown; chart priced from the file, card from the feed | Example unavailable | index.html:556-562 never checks example_card.signal_id; 801 and 1103-1105 never compare entry_close |
| page | both | Open signal contradicts itself or the clock: day 5 on a 53-day-old entry; "Rose 10%" at best +0.8%; best below worst; lost at -5% with worst -1%; C-grade card on an A+ signal; entry close ≠ card entry close; day-10 figure on day 5 (F12-F17, F26) | Live card and Previous signals list those figures | Data unavailable | index.html:436-441 checks only id, date order and card chart/date |
| page | replay | Forming card's low in 2019; confirms in 2027; open_signals from another run (F19-F21) | Forming / live cards shown | Data unavailable | index.html:418, 434, 439: only order, no bound |
| page | both | scored_as_of 2023-01-01 on a 2026 feed (F18) | Footer "closed through 31 Dec 2022" beside today's cards | Data unavailable | index.html:432 checks only "not after" |
| page | both | grade_odds shares contradict the ledger (rose 10% 50% vs 89/104 rows); BTC A+ grade_odds row gone and ledger BTC cut to 20 (F22, F24) | Past signals: 137 or 124 signals with contradicting summary | Ledger or feed unavailable | index.html:1112-1116 compares row COUNTS only, and only for assets present in grade_odds |
| page | both | Ledger row contradicts itself: rose 10% "yes" at +5%; "no" at +35%; +20% "yes" at +12%; deepest drop +3%; day 60 above best (L01-L04, L27) | Row shown in Past signals and Previous signals | Past signals unavailable | index.html:463-466 checks each cell alone |
| page | both | Ledger row dated 2027-01-05, or 10 days before the feed: its 60 days cannot have closed (L05, L06) | Listed under "every top-grade signal whose 60 days have closed" | Past signals unavailable | index.html:463-466: no date bound against the feed |
| page | both | Feed 404 plus a ledger from an older run, 3 top-grade rows short (L30) | "134 signals · 18 missed" | Past signals unavailable | index.html:1113: count check skipped when the feed is down |
| page | both | Trades listed oldest first (T07) | Lead trader "in · long" after his close | out, or unavailable | index.html:686-690 takes row 0 as latest; 455 checks shape only |
| page | both | Trade dated 2027; reduce after a close; size -10% of account; 250% of account at 1x (T08, T10, T11, T20) | Rows shown, marker "in" | Lead trader unavailable | index.html:455 schema only; size_pct typed "num" (375) |
| page | both | Chart file of another asset (ETH bars as BTC 2D), another timeframe (1D as 2D), every other bar gone, a 1970 bar first, prices /1e7 (C01, C02, C05 current, C16, C19) | Chart drawn | Chart data unavailable | index.html:458-459 barsOk: no asset, timeframe or spacing check; cd.chart never read |
| page | replay | ETH 1D chart file holds BTC 1D or ETH 2D bars, forming ETH 1D card (C21, C22) | Chart drawn | Chart data unavailable | same |
| page | both | Chart file from an older run (15 bars short) or a later run (5 bars past the feed) for the live setup (C03, C13) | Drawn, no "latest bar" label | Unavailable or labelled | index.html:908-910 labels only forming setups |
| page | both | Entry close disagrees with the chart's entry bar: bar close 60000 vs 86594.94; feed entry 0.01; feed entry 1e9 (C14, B09, B10) | Levels drawn far from the candles | Chart data unavailable | index.html:806-816 finds the entry bar by date only |
| page | both | Example file: entry_close 2710 vs card 2580.92; entry_index 19; BTC bars (E01, E04, E05) | Example chart drawn | Chart data unavailable | index.html:1103-1104 exOk |
| page | both | Example file: 8-day steps after entry, still reaching day 60 (E02) | **Script error** on What happened: "Cannot read properties of undefined (reading 'c')" | Chart data unavailable | index.html:1103-1104; 990 reads ex.bars[E + 30] |
| page | both | Example file: entry_close missing (E03) | NaN in SVG attributes, console errors | Chart data unavailable | index.html:1103-1104; 850-851 |
| page | both | Ledger, trades or example file 8 s slow while the feed has arrived (S-ledger, S-trades, S-example) | Card area blank, header "Market filter …", for 8 s | Card from the feed, the slow part loading | index.html:1090-1091 Promise.all waits for all four files |
| page | both | Share 85.00000000000001; typical high 1e21 (U07, U08) | "85.00000000000001%", "+1e+21%" | 85%; a rounded figure | index.html:337 pc() does not round; 323 toFixed prints exponent form |
| page | both | Feed 3 years old (K03) | Stale warning on Now only | Warning on Chart and Past signals too | index.html:510-513 staleNote is drawn in the Now card only |
| page | both | Held feed, feed 404, fail-closed feed (W01-W03) | Example switch: "Live and forming setups are unaffected"; Chart tab: "The example's chart data couldn't be loaded" | Held back / data unavailable | index.html:582-585 and 796-799 ignore feedHealth() |
| page | both | Quiet feed with no example_card (W04) | Main card "Example unavailable" | "No setup right now" | index.html:1118 turns the example on for any quiet feed |
| pipeline | current | All ETH candle files replaced by BTC's, with the baseline missing (P-C19b). Without the damaged baseline, only the regression guard caught it (P-C19) | Published as ETH, with 7 or more new ETH "confirmed" alerts | Stop | fetch.py:177 checks only "not later than" the first day; no level or cross-file check while Kraken is unreachable |
| pipeline | current | 2019 1D open -150, 0 or "nan"; volume -5000; high below open and close; old 4H row all zeros; ETH_4H holding 12H bars; ETH_12H cut, gapped or empty (P-C10-13, C20, C24, C24b, C25, C25e, C26, C27) | Published; no figure changed | Stop (structural damage) | check_candles.py:30, 57-66: values checked on the last 90 days and 540 4H bars only; fetch.py:150-161: 4H/12H checked for order only |
| pipeline | current | Funding: last 60 days cut; last 40 days "nan"; last 10 days -100 (P-D04, D07, D11) | Published; open cards regraded (e.g. before-2022 n 10→13, 90%→62%) | Stop or withheld | fetch.py:164-169 checks order only; analysis/grade3.py:65 and pcrtest.py:99-100 take any float |
| pipeline | current | tests/baseline/ledger.json deleted (P-B04) | Passes, writes a new baseline, publishes | Withheld | tests/regression.py:78 re-baselines when the file is missing |
| pipeline | current | Alert log deleted (A01) | Seeded; the pending alert is never sent | Withheld, or the alert sent | feed_live.py:259-267 |
| pipeline | current | Alert log: last row cut; older copy; emptied file (A04, A05, A04e) | Re-sends 1, 3, and 17 or more alerts already sent | Withheld; nothing sent twice | feed_live.py:111-129 trusts the log; 259 seeds only a missing file |
| pipeline | current | feed_live dies after the log write: feed path unwritable, or killed mid-write (A07, A08) | Alert logged as sent; no readable feed carries it (A08 leaves half a JSON) | Not lost | feed_live.py:410-414: log written before the feed; feed written non-atomically |
| pipeline | current | grades.csv (n 104→111) or missstats.csv tampered between steps; run held (P-H01, H02) | Held feed still carries them; Past signals summary shows "ETH 111 signals" | Nothing from the flagged file | feed_live.py:227-238 checks the seal only when all steps passed; 323-333 and 347-372 build anyway |
| pipeline | current | ledger.csv tampered (+250%) with a fail-closed feed (P-X03-page) | Past signals shows the +250% row | Unavailable | mirror serves datasets/ledger.csv; index.html:1113 skips the check when grade_odds is empty |
| pipeline | current | ETH candles lose their last day between stack and cards (P-X02) | Published | Withheld | seal.py covers datasets/ only, not data/ |
| pipeline | current | candle_check.json set to structural_ok false before refresh (S-candlecheck-false) | Cards published beside structural_ok false | Withheld | refresh.py:734 seals whatever it finds |
| pipeline | current | grades.csv and manifest.json rewritten together (S-manifest-forged) | Published, ETH n 111 | Withheld | seal.py:32-34, 101-106: unkeyed hashes next to the files |
| pipeline | current | Refresh died; outcome reported as missing, skipped, cancelled or "Failure" (O03 ×4) | Held feed says Bearish, scored 2026-11-12 (last run's) | Market filter unavailable | feed_live.py:241 clears status only on exactly "failure" |
| pipeline | current | Text a BOM only; Arabic-Indic digits in an entry date or a trade time (V- ×3) | feedcheck accepts, page rejects ("Data unavailable" on a feed published as good) | Same verdict | feedcheck.py:30-34 uses Python strip and Unicode \d; the page uses JS trim and ASCII \d |

## What failed safe, by family

All of these show the correct figure or the stated unavailable or held text, with no script error and no placeholder.

| Level | Family | Failed safe / tried |
|---|---|---|
| page | HTTP failures (404, 500, empty, cut, HTML error page, aborted, wrong file) on feed, ledger, trades and example | 60 / 60 |
| page | Every 2-4 file combination failing, all charts 404 | 24 / 24 |
| page | Ledger (CRLF, BOM, reversed, cut, duplicate, renamed column, quoted cells, boundaries) | 44 / 60 |
| page | Lead trader (valid long, short, add, reduce, close, 600 rows, one asset, optional fields; damaged shapes; dollar fields never shown) | 34 / 44 |
| page | Chart and example files (structure: repeated bar, 9 bars, high below close, text, object, cut, HTML, 500, spike) | 39 / 66 |
| page | Unusual JSON (duplicate keys, exponent forms, markup in every text field, 5 MB padding, unicode, deep nesting, NaN, escapes) | 20 / 24 |
| page | Boundaries, clock (future, stale edges, 29 Feb, 1 Jan, midnight) | 32 / 38 |
| page | Inconsistent feeds that are rejected or accepted correctly (F25, F27-F29) | 8 / 61 |
| pipeline | Seal: datasets damaged between steps (delete, empty, header, cut, column, duplicate, altered, older copy), stack_status, invalid candle_check | 123 / 125 |
| pipeline | Candle files: duplicates, swaps, holes, start or end cut, columns, text, blank, header row, timeframe swap, last bar, BOM, CRLF | 20 / 32 |
| pipeline | Funding: deleted, reordered, duplicated, columns renamed, text, BTC's file, header only, emptied | 9 / 12 |
| pipeline | Order, SIGKILL in stack and grade, clock ±1 day, 00:00:00, 23:59:59, two runs at once, replay controls | 15 / 15 |
| pipeline | grade.json damaged; baseline damaged together with real drift; page file missing, emptied or loosened | 12 / 13 |
| pipeline | Step outcomes (absent, false success, "; " separators, extras false failure) | 4 / 8 |
| pipeline | Alert log (control, header damage, duplicated rows, held run keeps the alert for the next run) | 4 / 10 |
| pipeline | Candles changed between steps; held feeds | 2 / 6 |
| pipeline | Page and feedcheck verdicts on unusual Unicode and number values | 16 / 19 |

## Repo tests (part C)

- `tests/test_seal.py`: 18/18 pass.
- `tests/test_feed_damage.py` (RENDER_LIMIT=40 REJECT_LIMIT=10): 31/31 pass. Page and feedcheck agree on 9,220 single-field damages.

What they do not cover:
- Cross-field and cross-file contradictions (rows F, L, T, C and E above).
- The example file's entry, spacing and identity.
- Chart files from another asset, timeframe or run.
- Slow files.
- Wording on the Chart tab and example switch when the feed is held or down.
- Unicode whitespace and digits (the V rows).
- Alert-log damage and a kill between the log write and the feed write.
- What a held feed still publishes.
- Funding values, and old candle values.
- A missing baseline.

The damage test's replay labelled "a state with forming cards" builds 0 forming cards, so no forming card is rendered under damage.

## Could not test

- The Kraken cross-check. There is no network; Kraken was passed in as unreachable, which the pipeline treats as "not a failure".
- The live Workers: the mirror, ctzb-site and the trades relay. The harness serves the files directly.
- GitHub step outcomes and the concurrency group. These were simulated from exit codes; two runs at once were run in one folder.
- check_fresh.py and check_candles.py read the real clock, so they were run with the clock patched to each run's time.
- Layout at phone width, and fonts, which were aborted.

The repo working tree gained uncommitted edits to `index.html` and `feedcheck.py` at about 13:13 UTC during the audit (an odds_fade rule, edge_status handling). They are not in the states and were not audited.

## Files

The case code and run logs are in the same folder: harness.py, page_cases.py, run_page.py, pipe.py, pipe_cases.py, run_pipe.py, pipe_extra.py, heldcheck.py, diverge.py and merge.py.

- all_checks.csv: 639 rows.
- disagreements.csv: 165 rows.
- progress.log.
