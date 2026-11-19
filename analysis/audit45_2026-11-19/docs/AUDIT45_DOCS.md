# Audit 45, docs part: doc sentences vs code at a0dc979

The repo copy is at `audit45d/repo`, checked out at commit a0dc979. I rebuilt the feed in that copy: refresh → grade_live → extras_live → stack_live → verify_cards → regression (PASS: 919 baselined signals unchanged, 4 new) → feed_live with every step reported as success. The rebuilt feed passes `feedcheck.py`. I also ran `tests/replay_at.sh 2026-11-12` and all six Worker test suites. Nothing was edited in `/home/claude/ctzb-data`.

This audit covers entry quality only. Every figure involved is a computed signal's 60-day record. There are no fills, no exits and no strategy return.

## Top line

- **Documents read:** 13, plus the docstrings and comments of 20 code and workflow files and the headers of 31 test files.
  - The 7 in scope: member page `index.html`, FEED_SPEC, CARD_SPEC, README.md, member-site/README.md, cloudflare/README.md, and CONTEXT.md's current-rule sections. I also scanned CONTEXT's dated sections for unflagged statements that present something as current.
  - The other 6 documents, outside scope: the 4 cloudflare/BRIEF_*.md files, PRETRADE and SITE_CHANGES.
  - Code and workflow files (outside scope): the 16 listed Python files, the 3 .github/scripts files and daily.yml.
  - Test files (outside scope): all 31 tests/*.py, *.sh and *.mjs headers.
- **Statements checked:** about 850. This is my count of sentences, table cells and comments that state a behaviour, figure, threshold, window, rounding rule, field meaning, file content or count.
- **COUNTED findings (in scope, kinds 1, 2 and 4): 0.**
  - Kind 1 (wrong): 0
  - Kind 2 (stale): 0
  - Kind 4 (reads as a return, trade or track record): 0
  - Kind 3 (loose, reported but not counted): 3, all in the member page's own words
- **Outside scope (not counted): 9.**
  - Kind 1: 3, all in test comments or labels
  - Kind 3: 4
  - Kind 4: 2, both borderline docstrings

## Every finding

The full quotes, code references and paste-ready sentences are in `findings.csv`.

### In scope (kind 3, not counted)

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 1 | member-site/index.html:299 | 3 | "Edge gone: The first fall at which this setup's odds drop below our posting bar." | The edge is 0 when the from-entry exact share is already under the bar, and the card then reads "Below the 70% bar from entry". When no rung is under the bar it reads "Holds at every level" (index.html:595-596, 755). In today's feed, 19 of 21 live signals have edge_level_pct 0. | "Edge gone: The first fall at which this setup's odds drop below our 70% bar. "Below the 70% bar from entry" means its odds were under the bar before any fall; "Holds at every level" means no fall measured takes them under it." |
| 2 | member-site/index.html:217 | 3 | "Real trades, posted automatically when they fill" | The relay polls once a minute (ctzb-trades-worker.js:31, cron `* * * * *`). The page's own empty-state lines (838, 842) say "within about a minute of each fill". | "Real trades, posted automatically within about a minute of each fill (once his feed is live)" |
| 3 | member-site/index.html:220 | 3 | "sometimes before an alert, sometimes after" | No member alert exists. The banner (194) says member alerts aren't switched on, and alerts go only to the operator's Telegram. | "...sometimes before a signal confirms, sometimes after, sometimes not at all." |

### Outside scope (not counted)

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 4 | tests/numbers_check.py:40 | 1 | "2026-11-12 … REPLAY state: four forming setups, live BTC 2D" | `replay_at.sh 2026-11-12`, rerun in the copy, gives 0 forming rows in prints.csv and an empty cards.csv. The baseline file agrees. The four forming setups exist only in commit 4aa1208's data, which build_audit_states.sh and fire_drills.py use. | "# replay of 12 Nov 2026: no forming setup, 23 live signals incl. the BTC 2D top-grade one (the four forming setups are only in commit 4aa1208's data)" |
| 5 | tests/test_feed_damage.py:226 | 1 | check label "(a state with forming cards)" | This is the same replay as #4: the feed has `cards` [] and no forming card. | "replay of 12 Nov 2026 built (a state with live signals, no forming card)" |
| 6 | tests/numbers_check.py:29 | 1 | "2020-09-15 # early quiet day" | The baseline for this date has 3 forming cards and 3 live top-grade signals (ETH 2D 22 Jul, ETH 3D 25 Jul, ETH 1D 31 Jul 2020). The page is not quiet on that date. | "# early history: forming cards and live top-grade signals" |
| 7 | tests/numbers_check.py:39 | 3 | "2026-09-07 # filter on, nothing live or forming" | BTC 1D and ETH 1D 2026-09-05 are live at grade C. The quiet card shows only because the page lists top-grade live signals only. | "# filter on, nothing forming and no top-grade signal live: the quiet card" |
| 8 | .github/workflows/daily.yml:168 | 3 | "cards AND alerts are withheld if any of these failed" | The list includes extras, but feed_live.py:78 GATING_STEPS has only refresh, grade, stack, cards and regress. An extras failure withholds the extras fields only. | "# … withheld if refresh, grade, stack, cards or regress failed; an extras failure withholds only the member-card extras." |
| 9 | refresh.py:609 | 4 (borderline: a docstring, not member-facing) | "holdcheck.csv - is the position green at the day-10 check?" | It compares computed signals' day-10 daily close with the entry close. There is no position. | "is the signal green (day-10 daily close at or above the entry close) at the day-10 check? Computed signals, no fills." |
| 10 | analysis/tagstats.py:19-20 | 4 (borderline: a docstring) | "whether each signal was ever in profit within 90 days" | It counts signals whose 90-day high rose above the entry close (lines 155-165). | "whether each signal's high ever went above its entry close within 90 days … even if it ended below it" |
| 11 | analysis/tagstats.py:14 | 3 | "ddpk worst low BEFORE the H-day high" | `pre` includes the high's own day (lines 55 and 63). CARD_SPEC states it correctly. | "worst low from the day after entry up to and including the day of the H-day high" |
| 12 | extras_live.py:31 | 3 | "Fails (exit 1) rather than write a half result" | Candle files are written one at a time and the script exits on the first bad one, so the files already written stay (lines 124-135). feed_live.py then deletes them. | "Fails (exit 1) rather than write a usable half result … (candle files written before the bad one stay until feed_live.py deletes every extras file of a failed step)." |

## Documents with zero findings

**In scope:**
- docs/FEED_SPEC.md. Every table row and rule matches. All 298 leaf paths in the rebuilt feed are described.
- docs/CARD_SPEC.md. The smallest rule-3 pool is 33 (BTC A+), the first graded ETH signal is ETH 3D 21 Mar 2020 grade C, and the first ETH A+ is 18 Apr 2020: all three confirmed.
- README.md. Confirmed: 13 datasets, 11 candidate tags, keep.json's 12 setups, about 14 requests per asset, and the maxsafe formula.
- docs/artifacts/member-site/README.md. The example file has 51 bars, 12 Aug 2024 to the 20-21 Nov bar. The seven phrases are all on the page.
- cloudflare/README.md. The test counts 21/26/21/45/26/36 were rerun and all pass. Also confirmed: 26 dispatches a day, 75 min and 26 h monitor thresholds, the 200 MB backup cap, and the 10-minute test limit.
- CONTEXT.md current-rule sections. Confirmed: 996 troughs on 6 charts, 13 markets per asset, 176 cells (83 + 49 + 44), 58/58 drills, 13 replay dates, gate on since 2026-09-02, and the BTC 3D confirmer tags.

**Outside scope:**
- cloudflare/BRIEF_dashboard, BRIEF_monitor, BRIEF_site and BRIEF_trades. The pinned byte counts match at their commits: 64,484, 65,188, 16,881, 87,466 and 21,762.
- docs/PRETRADE.md (pipeline statements only).
- docs/SITE_CHANGES.md. Every Pending row, read with its superseded notes, is on the page. R1 to R3 are not built.
- The docstrings and comments of grade_live, stack_live, verify_cards, feed_live, feedcheck, seal, engine, measures, rounding, clock, fetch, regimes, carddesign, check_candles, check_fresh and retry_after_failure.sh.
- Every test header except numbers_check.py and test_feed_damage.py.

## What I could not check, and why

- **Cron schedules and deployment state.** Several Worker facts live in Cloudflare configuration or deployment, not in the repo code: the mirror's `*/15` cron, the dashboard's `5,20,35,50` cron, the deployed version ids, "not yet deployed", the Access policies and the repo being public. Each Worker's code comment agrees with its README.
- **Page behaviour that needs a browser.** I did not run the Playwright suites or the fire drills. The page's words were checked against its code, and the numbers and broken-file behaviour are checked separately.
- **CONTEXT research records, noted but not flagged.** These are research results, which the brief says not to flag:
  - Line 394 gives the gate as on "to 5 Dec 2025, then from 3 Sep 2026", but `rsi_regime` gives on through 4 Dec 2025 and on from 2 Sep 2026.
  - Line 404 says "from 26 Jan" for 2023; the gate is on from 25 Jan.
