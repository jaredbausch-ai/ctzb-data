# Audit 40 — documentation against code (frozen at 465e385)

Reviewer: independent, docs only. Code and page read from a fresh clone checked out at 465e385, at
`audit40d/repo/`. The pipeline was rebuilt there exactly as the brief says (refresh → grade_live → extras_live →
stack_live → verify_cards → regression → feed_live with all steps "success"). Every step passed, and
`feedcheck.py` accepts the feed. I also built a held feed (grade=failure) and a fail-closed feed (cards.csv
removed) and compared both with FEED_SPEC field by field. Nothing in `/home/claude/ctzb-data` was edited.

Entry quality only: everything here is about computed signals' 60-day records. There are no fills, no exits
and no strategy return.

## Top line

- **Documents read:** 7 in scope (the member page, FEED_SPEC, CARD_SPEC, README.md, member-site README,
  cloudflare README, CONTEXT.md's current-rule sections). Outside scope: 4 BRIEF files, PRETRADE (pipeline
  statements), SITE_CHANGES (Pending and Requested rows), docstrings and comments in 22 code files, and the
  headers of 30 test files.
- **Statements checked:** about 950 (about 560 in scope, about 390 outside).
- **Counted findings (in scope): 4.** By kind: (1) wrong figure, threshold, window, rounding or meaning: **0**;
  (2) stale: **0**; (3) loose or incomplete: **3**; (4) reads as a return, trade or track record: **1**.
- **Kinds 1 + 2 + 4 in scope: 1.** It is README.md:76, "the next buy dates". I call it kind 4, but it is
  borderline (see the note under the table).
- **Outside scope (not counted): 4.** Kind 2: 2 (seal.py, daily.yml). Kind 3: 2 (the "5+" GAP wording in
  grade_live.py and PRETRADE).

## Every finding

Full quotes, the code each one disagrees with, and replacement sentences ready to paste are in `findings.csv`.

### Counted (in scope)

| # | File:line | Kind | Quoted sentence (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 1 | README.md:76 | 4 | "prints a summary of the regime, what is forming on each chart, and the next buy dates." | refresh.py:813-818 prints buy.csv's `buyDate`, the date a forming low would confirm (refresh.py:327-333). Nothing is bought. FEED_SPEC.md:106 calls the same date "a computed date, not a planned buy". | "...and when each forming low would confirm (buy.csv's `buyDate`: a computed date, not a planned buy)." |
| 2 | docs/artifacts/member-site/index.html:289 | 3 | "Every confirmed setup is checked against several independent confirmations." | The grade is a count of lenses (grade_live.py:62-104; stack_live.py:523-538). ETH's FUND and FCOOL both read the same funding series (pcrtest.py:94-105, grade3.py:60-66), and PRETRADE.md:345-347 says "both are funding". Forming setups are graded too. | "Every setup is checked against several separate confirmations. Only the ones where the most line up reach the top grade." |
| 3 | docs/artifacts/member-site/README.md:17 | 3 | "...and two phrases of plain description (...)" (the list of what the page types) | The page also types "within about a minute of each fill" (index.html:838, 842, added in round 38), "each 4-hour update" (index.html:230) and "a few days before the low itself" (index.html:288). None of the three is in the list. | Add "each 4-hour update" and make it four phrases: "...'within about a minute of each fill' for how soon the lead trader's trades post once his feed is live, 'a few days' for how far a 2D-5D low can sit after its bar opened". |
| 4 | cloudflare/README.md:27 | 3 | "**ctzb-scheduler** (v2, 10 Nov 2026) — KV binding `SCHED`..." | The code is v3, 11 Nov 2026 (ctzb-scheduler-worker.js:2), and `/health` returns `"version": 3` (line 351). The v3 health monitor is described later in the same file. | "**ctzb-scheduler** (v2 10 Nov 2026; v3, with the health monitor below, 11 Nov; `/health` reports version 3) — ..." |

Note on #1: "buy date" is the name of the field. I counted it as kind 4 because it reads as a planned trade,
and FEED_SPEC already qualifies the same field with "not a planned buy". If you read kind 4 as covering only a
trade *taken*, re-file it as kind 3, and this round has **0** counted findings of kinds 1, 2 and 4.

### Outside scope (not counted)

| # | File:line | Kind | Quoted sentence (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| O1 | seal.py:30-31 | 2 | "...and feed_live.py withholds just the extras fields." | Since audit #30, feed_live.py:575-576 and 772-776 delete every extras file whenever extras is not "success". That includes all ten `candles_<asset>_<tf>.csv` (seal.py:32-33), so the page's charts also read "Chart data unavailable". | "...feed_live.py withholds the extras fields and deletes every extras file, the chart candle files included." |
| O2 | .github/workflows/daily.yml:126-127 | 2 | "Never blocks anything; if it fails, the feed withholds just these fields." | Same as O1. The comment's list of outputs also leaves out the chart candle files (extras_live.py:123-135). | "...the miss stat, the past-signal paths, the odds-fade marks and the chart candle files... if it fails, the feed withholds these fields and feed_live.py deletes this step's files." |
| O3 | grade_live.py:8 | 3 | "GAP (CT > Signal by 5+)" | The test is `gap > 5`, strictly (grade_live.py:87, stack_live.py:311). That matches PRETRADE's Tier 1 #1 heading, "more than 5 points". The same "5+" wording is in stack_live.py:73 (the REGISTRY label printed into liveread.csv). | "GAP (CT more than 5 points above its Signal line)" |
| O4 | docs/PRETRADE.md:342, 356 | 3 | "CT > Signal by 5+" (the ETH and BTC lens lists) | Same as O3. | "CT more than 5 points above its Signal line" |

## Documents with zero findings

- **In scope:** docs/FEED_SPEC.md and docs/CARD_SPEC.md. Every field and every strict-check rule was checked
  against the code. Every field in the rebuilt feed is described. The held and fail-closed feeds match their
  lists exactly. The aliases, rounding, windows, seal, alert-log and input-check rules all hold.
- **In scope:** CONTEXT.md's current-rule sections (lines 1-257, 1302-1631). The dated notes that state
  something no longer true all carry a superseded or correction note.
- **Outside scope:**
  - cloudflare/BRIEF_dashboard.md, BRIEF_monitor.md, BRIEF_site.md and BRIEF_trades.md. Each one's pinned
    commit, byte counts and quoted lines match what it pins.
  - docs/SITE_CHANGES.md. Every Pending row is on the page as built, or is marked superseded. R1, R2 and R3 are
    not built.
  - Docstrings and comments in refresh.py, stack_live.py (apart from the REGISTRY label in O3),
    verify_cards.py, extras_live.py, feed_live.py, feedcheck.py, engine.py, measures.py, rounding.py, clock.py,
    fetch.py, regimes.py, analysis/tagstats.py and analysis/carddesign.py.
  - .github/scripts/check_candles.py, check_fresh.py and retry_after_failure.sh.
  - Every tests/*.py, *.sh and *.mjs header.

## Figures recomputed and found right

These are not findings.

- schema_version is 6, and two tests assert it.
- The fields added without a schema bump (tier_fixed_on, alert_log, alert_log_carry, alerts_held) are the full
  list, checked by diffing against c7755bd.
- refresh.py writes 13 datasets. There are 11 candidate tags, and keep.json holds 12 setups.
- troughs.json has 996 rows.
- There are 176 confluence cells (83 + 49 + 44 v4 rows), 12 PRETRADE headings and 36 registry ids.
- The smallest rule-3 pool is 33 (BTC A+). The first graded ETH signal is ETH 3D, 21 Mar 2020, grade C, and
  the first ETH A+ is 18 Apr 2020.
- The CARD_SPEC example "95 misses of all 313 BTC same-grade signals" matches today's feed.
- The example file has 51 bars, 12 Aug to 20-21 Nov 2024, with day 60 on 21 Nov 2024.
- The regime has been on since 2026-09-02, and the gate turned off on 2022-01-27.
- The shared 4H gaps are 28 Feb 2017 and 25 Oct 2025. BTC's own 4H gap is 10 Aug 2018.
- Low date to confirmation date is 3, 7, 11, 19 and 31 days.
- The scheduler makes about 26 dispatches a day. There are five Workers.
- Fire drills: 58/58, with group B being 6 step crashes plus 5 faults. numbers_check uses 13 replay dates.
- test_gate_off's "ten lows were forming" is confirmed by a replay (10 forming prints, all with the gate off).
- The Worker test counts 26, 21, 36, 21, 26 and 45 were re-run and pass.

## Not checked, and why

- **Cloudflare dashboard settings that are not in the repo:** the cron triggers (`*/15`, `5,20,35,50`,
  `* * * * *`), the R2 lifecycle rule (90 days), the deployed version ids, and the Access policies. The code
  comments agree with these, but the settings themselves cannot be seen from the repo.
- **External facts:** Coinalyze and Deribit history depth, and Coinbase perp contract size.
- **Runtime claims:** "about 3 minutes" for a run or the fire drills, and "about 10 MB" for a backup.
- **Tests that were not run:** tests/test_feed_damage.py and numbers_check.py (playwright, run time). The first
  test loop ran out of time on test_feed_damage, so their headers were checked by reading only. These Python
  tests were run and pass:
  - test_action_env 1/1
  - test_check_candles 95/95
  - test_cut_files 495/495
  - test_feed_alerts 83/83
  - test_feed_extras 28/28
  - test_fetch_today 4/4
  - test_input_files 117/117
  - test_midnight 7/7
  - test_seal 29/29
  - regression: pass
  - test_gate_off: pass

  These finished after the report was handed back, and all pass:
  - test_series_cells 62/62
  - test_year_end 8/8
  - test_page_states 64/64
  - test_page_timing 24/24
  - test_per_year: pass
- **Research results** in CONTEXT and PRETRADE (dated findings) were not re-tested, as the brief says.
  docs/AUDIT_LOG.md and analysis/audit* were not read.
