# Audit 22: documentation against code

**I read 60 documents (13 docs and pages, 20 pipeline code files, 22 test files and 5 worker headers) and checked about 1,050 statements (an estimate). I found 57 findings: (1) 8 wrong figure, threshold, window, rounding or field meaning; (2) 14 stale; (3) 29 loose or incomplete; (4) 6 that read as a return, a trade or a track record.**

The audit ran against repo HEAD 58fd6c6 ("candles through 2026-11-13"). Nothing in /home/claude/ctzb-data was edited. All runs used a copy at `audit22d/repo`. In that copy I rebuilt the feed with the brief's command sequence, and it matched the committed feed except for timestamps. Full rows with code references and ready-to-paste sentences are in `findings.csv`. The scope is entry quality only: these are computed signals, there are no fills, and the data has no exits.

## The ones that matter most

1. **D1: member alerts.** The page says alerts go out "for top-grade setups only", "it isn't top grade, so no alert goes out for it", "You'll get a push alert the moment one confirms", and "Only the ones where the most line up reach members". The code does something different:
   - `feed_live.py` 251-276 writes forming and confirmed alerts for every grade, for every confirmed print on all 10 charts (8D included).
   - The only sender, `ctzb-dashboard-worker.js` notify(), passes every one of them to a single Telegram chat, Jared's.
   - No member alert channel exists in the repo.
   - On 11 Nov the log shows a forming alert for a grade C card (ETH 1D 2026-11-13).
2. **D2: `checks.passed`.** FEED_SPEC says it is "the stack check alone". In fact it also covers the card cross-check, because `verify_cards.py` appends to `stack_status.txt`.
3. **D3: who writes `liveread.csv`.** CONTEXT says `grade_live.py`. It is `stack_live.py`.
4. **D4: lens lists in the `grade_live.py` docstring.** BTCX is listed as an ETH lens and left out of the BTC lenses. The actual sets are ETH = GAP, HIGH, AGREE, BTC3, FUND, FCOOL and BTC = GAP, UP8, BTCX, FASTCT.
5. **D5: an unused parameter.** The `fetch.history_problems` docstring says `upto` skips the first-day rule, but the parameter is never read.
6. **D14: two different 70% bars.** FEED_SPEC equates the card's 70% edge bar with refresh `WINMIN`. WINMIN selects the ETH tier on a different measure: the chart's last close within 60 days is above entry. As a result, `trades_a_year` counts ETH tier signals only. Nothing says so.
7. **D15: `must_close_above` with one bar to go.** When the low needs one more bar, this price assumes today's still-open bar closes at the latest price, and that bar must also hold CT above the trough. The price is an estimate. CARD_SPEC and FEED_SPEC present it as exact.
8. **D16, D17: overstated coverage of the checks.**
   - "verify_cards re-derives every figure on a card": it does not re-derive dates, prices or confluence rows. CONTEXT 1404-1406 already says so.
   - "the schema covers every feed field the page reads": the page's general odds-fade fallback reads `odds_fade.posting_bar_pct`, `tier_fixed_on`, `early_dip[].rose10_*` and `day10[].edge`. FEED_SCHEMA does not type those fields. A passing feed never reaches that branch.
   - The list of cross-field rules leaves out 6 rules that `feedcheck.py` enforces.
   - The ledger check also has a count-match rule that isn't listed.

## Every finding

Kinds: 1 = wrong, 2 = stale, 3 = loose or incomplete, 4 = reads as a return, a trade or a track record. The code references and the full suggested sentences are in `findings.csv`.

| id | file:line | kind | quoted (short) | what the code does (where) | suggested sentence (short) |
|---|---|---|---|---|---|
| D1 | member-site/index.html:194,289,604,624,979 | 1 | "Alerts go out for top-grade setups only" / "no alert goes out for it" / "push alert" | Every grade alerted; the only sender is Jared's Telegram (feed_live 251-276; dashboard-worker 161-196) | Member alerts not built; the pipeline flags every grade to the operator's Telegram |
| D2 | FEED_SPEC.md:92 | 1 | "`checks.passed` ... the stack check alone" | Stack and card cross-check (feed_live 130-134; verify_cards 166-170) | "...no FAILED line: the stack check and the card cross-check" |
| D3 | CONTEXT.md:1454 | 1 | "liveread.csv (written by grade_live.py" | stack_live.py 765 | "(written by stack_live.py ...)" |
| D4 | grade_live.py:7-13 | 1 | "ETH lenses: ... BTCX ... BTC lenses: GAP, UP8, FASTCT" | BTC has BTCX (grade2.json; 58-76) | ETH: GAP HIGH AGREE BTC3 FUND FCOOL; BTC: GAP UP8 BTCX FASTCT |
| D5 | fetch.py:145-146 | 1 | "`upto` ... ignores the first-day rule" | Never read (140-204) | Drop it, or honour it |
| D6 | CONTEXT.md:143-144 | 1 | "both return the clamp list" | `_declean` returns a count (refresh 213); both also clamp highs | "...`_declean` prints it and returns the count" |
| D7 | cloudflare/README.md:53 | 1 | "test_dashboard_alerts.mjs (18)" | 21/21 on 13 Nov | "(21)" |
| D8 | README.md:10 | 1 | "Columns are time,open,high,low,close" | Plus volume; also 4H/12H (fetch 225-228) | "...close,volume..." |
| D9 | FEED_SPEC.md:19-21 | 3 | "cards empty ... whenever stack_status.txt has a FAILED line" | Also any gating step; seal or strict-check failure gives the fail-closed feed (feed_live 223-238) | Name every trigger |
| D10 | feed_live.py:13-15 | 3 | same, in the docstring | same | same |
| D11 | FEED_SPEC.md:92 | 3 | "`checks.steps` ... each gating step (refresh, grade, stack, cards, regress)" | Includes extras (daily.yml 165) | Every step passed in; extras doesn't gate |
| D12 | FEED_SPEC.md:111 | 3 | "extras_withheld ... True when the extras step failed" | Also when a file is missing; the example_* fields go null (feed_live 347-401) | Add both |
| D13 | FEED_SPEC.md:32-69 | 3 | Field tables | About 30 feed fields named nowhere; a forming print's `entry_close` is the latest price (stack_live 374) | Add tables for prints, open_signals, windows, grade_odds |
| D14 | FEED_SPEC.md:35,113,336-338 | 3 | "posting_bar_pct (= refresh WINMIN)"; trades_a_year definition | WINMIN uses the last chart close within 60d above entry, ETH only (refresh 105-125, 264-276) | Say it's the same number on a different measure; ETH only |
| D15 | CARD_SPEC.md:52 (+FEED_SPEC 54) | 3 | "Confirms ... if [asset] closes above X" | With 1 bar to go it assumes today closes at the latest price (stack_live 380-390) | Say it's an estimate until today closes |
| D16 | FEED_SPEC.md:223 (+CARD_SPEC 113-115) | 3 | "re-derives every figure on a card" | Not dates, prices or confluences (verify_cards 119-153) | Every figure computed from the sample |
| D17 | FEED_SPEC.md:344-357; test_feed_damage.py:14; member-site/README.md:18 | 3 | "covering every feed field the page reads"; rules list | Unreachable fallbacks read untyped odds_fade fields; 6 more cross rules; ledger count rule | Remove the fallbacks or type them; complete the lists |
| D18 | CARD_SPEC.md:118; FEED_SPEC.md:21; CONTEXT.md:1442-1443 | 3 | "The dashboard refresh reports it" / "refresh task ... notifies" | ctzb-dashboard Worker reads live and sends Telegram alerts; the monitor reports holds | Name the Worker and the monitor |
| D19 | CARD_SPEC.md:68-86 | 3 | "Each label below is defined here" | Live card shows best/worst so far, day count, day 10; "closes above $X"; lead trader marker (index 534, 550, 642, 972-976) | Add rows |
| D20 | CARD_SPEC.md:86 | 3 | "+10% level = Entry close x 1.10" | Forming card uses the latest price (index 811, 1000) | Add the stand-in |
| D21 | CARD_SPEC.md:108-112 | 3 | "any share is outside 0-100" | Only 7 shares checked, not the ladder (stack_live 772-773) | Name them |
| D22 | CARD_SPEC.md:56 | 3 | Confluence rows: "past trades, rose 20%, fell 30%" | Also rose 10%, confirmer and date (stack_live 623-625) | Add |
| D23 | CONTEXT.md:113-116 | 3 | "Every row's date field is that confirmation date" | The confirmation bar's CLOSE date; low/low_date/low_day also carried | Say close date; name the low fields |
| D24 | CONTEXT.md:1437 | 3 | "prints.csv (every print and forming low)" | Last 3 per chart plus forming (stack_live 332, 374) | Same |
| D25 | CONTEXT.md:1417 | 3 | "Setup in BRIEF_trades.md" after schema 5; deploy date | Misplaced; SITE_CHANGES dates the 656d67c3 deploy 11 Nov | Move it; use one date |
| D26 | stack_live.py:20-21 | 3 | liveread record "(n, +20%, ...)" | Also +10%, +30%, best move (158-164, 765) | Add |
| D27 | extras_live.py:31-32 | 3 | "Fails ... an asset with no usable path" | An asset with no A+ signals is skipped; also fails on empty fade or bad candles | List them |
| D28 | engine.py:105-111,139 | 3 | "We clamp a low only..." / "Return confirmed signals" | Also clamps highs; can return a signal on the open bar | Say both |
| D29 | README.md:49-51 | 3 | "an unfinished final bar can never produce a signal" | The engine does; bucket_end drops it downstream; ds_live reads sg[-1] | Reword |
| D30 | README.md:72-84 | 3 | Lists 10 refresh datasets; grade_live writes grades + columns | Also earlydip, holdcheck, forward; ledger, dipdist; grade6; later steps unmentioned | Complete |
| D31 | tests/regression.py:17-18 | 3 | "SETTLED the 60-day outcome ... once entry + 60" | Also the 7 day-odds columns; >60 days, local date | Reword |
| D32 | daily.yml:95-97,113-114,160-161 | 3 | Structural list; grade outputs; "withheld if stack or card check failed" | history_problems; ledger and dipdist; any gating step | Complete |
| D33 | check_candles.py:8-13 | 3 | STRUCTURAL list | Also whole-history checks (148-153) | Add |
| D34 | member-site/index.html:217,220 | 3 | "Real trades, posted when they fill" / "Every trade is posted live" | Trades relay in dry run; /trades.json is 404 | "...once his feed goes live" |
| D35 | member-site/index.html:233 | 3 | "Edge lost or closed" | Also holds "Status unavailable" signals (741-752) | "Edge lost, status unavailable, or closed" |
| D36 | member-site/README.md:15 | 3 | What the page types | Also +20%, -30%, day 10, cloud range, 10-bar minimum | Complete |
| D37 | FEED_SPEC.md:77-78; ctzb-feed-worker.js:4-6 | 3 | "public ... until private" vs "the private GitHub repo" | They disagree; visibility not checked | Align |
| D38 | FEED_SPEC.md:41,67 | 4 | next_buy_date / trades_a_year "As on the dashboard"; "trades that got there" | Computed ETH tier signals; no fills | Say "computed signal ... not a planned buy"; "signals" |
| D39 | CARD_SPEC.md:1,15,28,36-37,45-54 | 4 | "Trade card", "past trades", "buy price", "buying" | Computed signals only | "Card", "past signals", "entry close" |
| D40 | verify_cards.py:1 (+daily.yml 140-142) | 4 | "every trade card ... trade ledger" | Signal ledger | "every card ... signal ledger" |
| D41 | refresh.py:57-62,392-396,404,637-645,709 | 4 | "traded blind", "live out-of-sample record", "traded set", "70%+ trades", "Trades a year" | Computed signals; the dashboard and feed show these words | "scored blind", "forward signal record", "signals" |
| D42 | stack_live.py:602,706 | 4 | liveread text "under 15 trades", "past ... trades" | Shown on the dashboard; past signals | "signals" |
| D43 | README.md:90-156 | 4 | "traded tier", "Tier trades 150", "Tier win rate 75%" | Computed; win = last chart close within 60d; no entry-quality caveat anywhere | Add the entry-quality sentence; "signals" |
| D44 | README.md:4,36-39 | 2 | "Runs itself once a day" / "01:20 UTC daily" | Every 4h at :13, ctzb-scheduler | Every 4 hours |
| D45 | README.md:86 | 2 | "fetch_pcr.py runs hourly" | Every 3 h at :25 (scheduler) | Every 3 hours |
| D46 | cloudflare/README.md:3,17-18 | 2 | "two Workers" / "Both tokens" | Five Workers, many secrets | Five; every secret |
| D47 | cloudflare/README.md:72-74 | 2 | 404 "shows as an empty state" | Page says "unavailable" (index 697-699) | "unavailable" |
| D48 | ctzb-scheduler-worker.js:9-10,19 | 2 | "Ticks that match nothing ... write nothing"; "26 a day" | Monitor writes every tick (315, 370) | Add the monitor's writes |
| D49 | grade_live.py:24-26 | 2 | worstTenthMedian "the dashboard sizes against" | Sizes on medDip (eth-setup-standard 279-285) | Not used for sizing |
| D50 | CONTEXT.md:1142 | 2 | "sizes against the WORST-CASE MEDIAN" | medDip since 28 Oct; no superseded note | Add a note |
| D51 | CONTEXT.md:1328-1338 | 2 | "Joe's console ... It does not refresh" | Rebuilt 28 Oct; served live by ctzb-dashboard | Mark closed |
| D52 | CONTEXT.md:1362-1368 | 2 | "Until that runs, data/*.csv has no volume column" | Volume and 4H/12H present | Mark done |
| D53 | CONTEXT.md:846 | 2 | "ODDS BY DISTANCE (... ledger bestMove >= ...)" | From today's state (stack_live 674-709) | Reword |
| D54 | CONTEXT.md:1598 | 2 | "Three layers now: ... heartbeat.yml" | No heartbeat.yml; retired 10 Nov | Add a superseded note |
| D55 | CONTEXT.md:1417 | 2 | "56/56 pass" | fire_drills_result.json: 58/58 | "58/58" |
| D56 | PRETRADE.md:338-339,437-442 | 2 | "Applied daily"; grade_live outputs; "'Conviction grade' section reads those three files" | Every 4 h; ledger and dipdist too; no such section now | Reword |
| D57 | SITE_CHANGES.md:17,19 (Pending) | 2 | Row 1 "from all N top-grade signals", "about 22 a year (2020 to 2025)", "full history", "day 10 to 60"; row 3 "Typical price on day 60" | Later rows replaced these; the page does otherwise (index 634, 654, 677, 726-731, 803) | Mark superseded |

## Documents with zero findings

- **Cloudflare briefs.** `BRIEF_dashboard.md`, `BRIEF_monitor.md`, `BRIEF_site.md`, `BRIEF_trades.md`. Each describes its commit-pinned file, and the pinned byte sizes match the git objects: 87,466, 65,188, 16,881 and 21,762.
- **Code files.** `clock.py`, `rounding.py`, `measures.py`, `regimes.py`, `seal.py`, `feedcheck.py`, `analysis/tagstats.py`, `analysis/carddesign.py`, `.github/scripts/check_fresh.py`, `.github/scripts/retry_after_failure.sh`.
- **Test headers.** `fire_drills.py`, `reseal.py`, `test_action_env.py`, `test_check_candles.py`, `test_feed_alerts.py`, `test_feed_extras.py`, `test_fetch_today.py`, `test_page_states.py`, `test_seal.py`, `test_year_end.py`, `build_audit_states.sh` ("four forming setups" at 4aa1208 confirmed), `replay_at.sh`, `test_gate_off.sh` ("ten lows" confirmed: 10 forming prints, all regime off), `test_no_today_bar.sh` (ran: PASS), and all six `.mjs` suites.
- **Test runs in the copy.** `test_check_candles` 29/29, `test_feed_alerts` 23/23, `test_feed_extras` 28/28, `test_seal` 18/18, `test_fetch_today` 4/4, `test_action_env` 1/1, `test_page_states` 44/44. For `test_feed_damage` (limited render run) every line printed while I watched passed; I did not confirm its final exit.
- **Figures recomputed and found right:**
  - CARD_SPEC: smallest rule-3 pool 33; first graded ETH signal 2020-03-21; first ETH A+ 2020-04-18.
  - Page: "about 22 a year" (130 A+ from 2020 to 2025).
  - Gate dates 2025-12-04, 2025-12-05 and 2026-09-02.
  - The 2021-08-19 to 2022-01-25 episode note.
  - `troughs.json`: 996 rows. `keep.json`: 12 setups.
  - README's "13 datasets".
  - The worked example file: 51 bars, ending on the bar that holds day 60.
  - dipdist shares A+ 14, A 25, B 27, C 36 (ETH at -25.3%).
  - grade_odds sample "2020-04-18 to 2025-12-04".
  - test_feed_damage's "about 35 ways".
  - The fail-closed feed passes `feedcheck` (it does).

## What I could not check, and why

- **Deployed state and private services.** I couldn't confirm the live Cloudflare deploys and versions (656d67c3 and others), the actual cron settings in Cloudflare, the Telegram recipients, whether the Claude "dashboard refresh" scheduled task is retired, or whether the repo is public or private. These are outside the repo, and I sent no outside requests.
- **Test runs.** I did not re-run `tests/fire_drills.py`; D55 is taken from its committed result file. I did not re-run `tests/test_year_end.py`.
- **Research records in CONTEXT and PRETRADE.** Dated research results were not re-checked, by the brief's rule. Dated sections were flagged only where they say "now" and carry no superseded note: D50 to D54.
- **Out of scope.** The dashboard page (`docs/artifacts/eth-setup-standard.html`) was used only as evidence. Along the way I noticed that it reads a `maxsafe` dataset no step writes. I note this here only; numbers and broken files belong to the other auditors.
