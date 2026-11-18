# Audit 41c: damaged, missing, inconsistent and tampered files (code frozen at 01f3976)

Independent auditor; own harness (`page.py`, `pcases.py`, `prun.py`, `pipe.py`, `qcases.py`, `qrun.py`, `midnight.py` in this folder). No earlier audit folder, AUDIT_LOG or other scratch folder was read. Nothing in the repo was edited. Every expectation was written into the case before it ran.

This work checks file handling only. The site measures entry quality, not a strategy return or a track record: the data has no exits.

## Top line

**Real-life disagreements: 0 at page level, 0 at pipeline level.** 675 real-life cases ran (page 368, pipeline 307). None showed a wrong figure, a placeholder, a script error, a blank area, a damaged input scored, wording that misstates the state, or anything that reads as a return. A further 12 "second guard" pipeline cases, 24 hardening cases and 19 valid lead-trader-file cases ran outside the count.

| Family | Page: cases tried | Page: got through | Pipeline: cases tried | Pipeline: got through |
|---|---|---|---|---|
| 1 Missing | 48 | 0 | 37 | 0 |
| 2 Malformed | 73 | 0 | 88 | 0 |
| 3 Wrong content | 31 | 0 | 14 | 0 |
| 4 Partial run | 4 | 0 | 149 | 0 |
| 5 Timing | 57 | 0 | 19 | 0 |
| 6 Delivery | 148 | 0 | n/a (page side) | n/a |
| Clean baselines | 7 | 0 | 2 (one per state) | 0 |

**States tried:** replay_1111, current, plus seven states I built myself:
- a real run at 00:00:30 UTC on 19 Nov, the day after current (today's bar from the first hourly candle);
- replays of 2026-03-15 (a quiet market, filter off), 2025-12-31, 2026-01-01 and 2024-02-29;
- an extras-failed run and a stack-failed (held) run.

| Category | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, a trade or a track record | 0 | 0 |

## Every disagreement (real-life damage)

None. `disagreements.csv` lists only the valid-file observation below, which is not counted. `all_checks.csv` has all 730 checks.

## Noted, not counted

1. **Valid lead-trader file, no damage (category v, not counted).** When the lead-trader file shows an open ETH position, the worked-example card reads "Lead trader: in · long". That card is the 22 Sep 2024 signal, and the line can be read as saying he took that 2024 signal. The page shows it on the Now card and keeps it on every later snapshot while the example is up, on both states.
   - Cause: `docs/artifacts/member-site/index.html:780` puts `leadState(m)` on every card kind, and `leadState` (820-830) never checks `m.kind === "example"`.
   - It needs a valid file and no damage, so it is outside the owner's count. It is recorded because guarantee (9) says nothing may read as a trade.
2. **The previous run's chart file served beside a run at 00:00:30.** I built that run's new bar flat at the last close, so the older file closes at `price_now` to the cent. The page draws it labelled "Latest bar · 17/18 Nov 2026", which is what FEED_SPEC says it should do. No figure on it is wrong.
   - I expected "unavailable" before running and changed that after review. Exact-cent equality needs a flat first trade after the close.
3. **Corrected expectations, recorded as ok.** These were my own mistakes in setting up cases, not page or pipeline faults:
   - The 1D-8D candle files and `ledger.csv` are already CRLF. My first "CRLF" case wrote `\r\r\n`; it failed safe, and I re-ran it as an LF conversion.
   - A no-op "figure" edit, and an "older copy" that was byte-identical, were re-run or skipped.
   - The kill timings were too long for `refresh` and `extras` and were re-run shorter.
   - The 3 s chart wait was too short for the harness and was re-run longer.
   - In the replay state, alert flags came from re-running on the frozen run's own clock (same `emitted_at`). The log holds each alert once.

## Hardening (not counted): hand-forged feeds, each field valid and the fields contradicting each other

Rejected ("Data unavailable"), both states:
- an open signal carrying another signal's card;
- one signal listed both as forming and as live;
- `cards_withheld` true with cards present.

Accepted and shown (the strict check has no rule for these):
- two ETH forming cards with different `price_now` (one chart then reads unavailable);
- `example_card.entry_close` different from the example file (the card shows the feed's entry close, and the example chart reads unavailable);
- a past-paths day 0 that is not 0%;
- a forming card confirming 2099-01-01 (shown "confirms 1 Jan 2099");
- `posting_bar_pct` 0 (every edge "holds");
- a feed dated a day ahead with a matching `scored_as_of` (no stale note);
- `grade_odds` ETH A+ +20% share set to 0 while the ledger shows hits (the ledger check compares count and the +10% share only).

## Two-fault (recorded, not counted)

None recorded. No single fault I constructed needed a second one to get through.

## What failed safe, by family

| Family | Rule meant to catch it | Page outcome (cases) | Pipeline outcome (cases) |
|---|---|---|---|
| 1 Missing | Page: `get()` (index.html 365-368) returns null on any non-OK status or throw, and every area has an "unavailable" text. Pipeline: `fetch.history_problems` "is missing", the seal's "is missing", `check_log`, `fail_closed`. | Data unavailable / Past signals unavailable / chart unavailable / lead file unavailable: 48 | 37: stopped 4, held 15, fail-closed 14, published with figures equal to the undamaged run 4 (deleted alert log or previous feed, restored from the second copy, no alert sent twice) |
| 2 Malformed | Page: FEED_SCHEMA and crossCheck (384-529), parseCSV dropped/cut and ledgerRowOk (346-364, 561-573), barsOk/stepsOk (559-562), tradesProblems (542-554), worker csvToBars. Pipeline: `history_problems` (exact header, `_row_problems`, `_file_problem`, `_series_problems`). | 73, all unavailable or correct figures | 88: stopped at the candle check 63, held 10, fail-closed 1, published with figures equal to the undamaged run 14 (line ends toggled, columns reordered, a cut or duplicated alert log restored from the copy, put/call within its 2-day lag) |
| 3 Wrong content | Page: chart name, last close equal to `price_now` / `entry_close`, last bar not after `generated_at` (965-983); ledger against `grade_odds` (1330-1336); example against its card (1342-1346). Pipeline: ETH/BTC close ratio, 2D-8D equal to the daily bars bucketed, 4H/12H step and 25% test, derivatives market columns, series first day. | 31 | 14, all stopped at the candle check |
| 4 Partial run | `seal.py` (`problems` / `check` / `age_problem`); `CTZB_STEP_OUTCOMES` (feed_live 456); `stack_status`; `candle_check` `structural_ok` (468); `fail_closed`. | held and fail-closed feeds read "Setups held back", filter unavailable, no ledger: 4 | 149: held 95, fail-closed 42, published equal 12 (correct or whitespace-padded outcome strings, a hand run, the feed step run twice, extras failure with the extras withheld) |
| 5 Timing | `check_fresh`; stack_live today check (219-222); seal 2 h limit and future start; crossCheck `scored_as_of` equal to the feed's day; page `staleNote` (623-640). | 5 h / 3 days / 2 years / left open / past midnight / clock behind: 57, notes correct | 19: stopped 9 (day ahead / day behind / 00:00:00 before the candle), held 2 and fail-closed 6 (midnight inside a run, feed step 3 h late or before the seal start), published equal 2 (23:59:59) |
| 6 Delivery | Page: `get()` and JSON parse, parseCSV `cut`, worker csvToBars, chartTok, loading states. | 404/500/502/524/abort/empty/HTML page/cut at 6 points/NUL/UTF-16/doubled/slow 3-8 s: 148 | n/a |

Second guard (outside the count): with damage placed after the candle check, `stack_live.py`'s own `history_problems` and lag check held all 12 cases.

## Repo tests (C)

All three pass on a copy of `current`:

| Test | Result |
|---|---|
| `tests/test_seal.py` | 29/29 |
| `tests/test_page_timing.py` | 24/24 |
| `tests/test_feed_damage.py` with RENDER_LIMIT=40 REJECT_LIMIT=10 | 33/33: 9,499 damaged feeds per state agree page against pipeline; 761 lead-trader files; 11 ledgers; 10 chart files |

They do not cover:
- HTTP-level delivery (5xx, HTML error pages, aborts, files cut part-way);
- a full chain on damaged candle or series files (the damage test is page-only, and the seal test damages datasets);
- step outcome strings, steps out of order, killed steps, a clock crossing midnight inside a run;
- file sets mixed across runs (feed, ledger and chart files);
- the wording for valid lead-trader shapes (finding 1 above);
- quick mode renders only 40 of 492 accepted kinds and 10 rejected feeds.

## Could not test

- Kraken cross-check (no network; it ran as "unavailable") and real exchange fetches (`fetch.py`).
- The real Cloudflare mirror and site Worker: I emulated csvToBars from the template only.
- The git commit, `pull --rebase` and push steps, the retry and watchdog jobs, and truly concurrent runs on separate runners (the `concurrency` group serialises them).
- The live trades relay; browser caching beyond `no-store`.
- `regression.py` on the replay state: the ledger is shorter by construction, so the replay used `regress=success` as `tests/replay_at.sh` does.

Files in this folder:
- `all_checks.csv`, `disagreements.csv`, `progress.log`
- `res_*.jsonl` (raw results per case)
- `feeds/` (sample held and fail-closed feeds)
