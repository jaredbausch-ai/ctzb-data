# Audit 47, docs part: every doc sentence against the code at 78d8276

Entry quality only. Everything checked here describes computed signals and their 60-day records; there are no fills,
no exits and no strategy return in the data.

## Top line

| | |
|---|---|
| Documents read | 21 (in scope: member page, FEED_SPEC, CARD_SPEC, README, member-site README, cloudflare README, CONTEXT current-rule sections; outside scope: 4 BRIEF files, PRETRADE pipeline statements, SITE_CHANGES Pending and Requested rows, docstrings and comments of the 18 listed code files, daily.yml, 33 test headers) |
| Statements checked | about 770 (FEED_SPEC ~230, member page ~120, CARD_SPEC ~70, CONTEXT current rules ~90, the three READMEs ~110, outside scope ~150) |
| COUNTED findings (in scope, kinds 1, 2, 4) | **0** (kind 1: 0, kind 2: 0, kind 4: 0; no borderline) |
| In scope, kind 3 (reported, not counted) | 4 |
| Outside scope (not counted) | 4 (one kind 1, three kind 3) |

Copy: `/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit47d/repo` at 78d8276. Feed rebuilt
there as the brief says (refresh, grade, extras, stack, cards all passed; regression "919 baselined signals unchanged,
4 new"; feed: 4 cards, 34 prints, 21 open signals, 10 windows, not withheld). Every field in the rebuilt feed (337
paths) is described in FEED_SPEC, and every field FEED_SPEC names exists with the stated meaning.

## Every finding

Full rows (code file and line, suggested sentence) are in `findings.csv` in this folder.

| # | File:line | Kind | Quoted (short) | What the code does | Suggested sentence (short) |
|---|---|---|---|---|---|
| 1 | docs/FEED_SPEC.md:391-392 | 3, in scope | fail-closed feed has "every list except `alert_log_carry` and `alerts_held` empty" | feed_live.py:766-768 `checks.failed_steps` is `["feed"]`, a non-empty list (stated just before in the same sentence) | "every other list empty except `alert_log_carry` and `alerts_held`" |
| 2 | docs/FEED_SPEC.md:262 | 3, in scope | "With no misses the medians are null." | carddesign.py:74-83 also leaves `mean_peak_pct` blank, so it is null too | "With no misses the medians and `mean_peak_pct` are null." |
| 3 | docs/CARD_SPEC.md:72-74 | 3, in scope | "Red on day 10, rose 10% after" and "Where the odds fade · ETH tier signals" are on the member page, "shown only when a card has no ladder" | index.html:586-597 `setupFade` is null only with no ladder rows or no bar; the strict check requires 4 rungs and `posting_bar_pct`, and n 0 cards return early (712), so no drawn card lacks a ladder: these two never show | say they are in the page's code but never shown with a feed that passes the strict check |
| 4 | docs/artifacts/member-site/README.md:17 | 3, in scope | the list of what the page types (given as complete) | index.html also types the 1-minute re-check of the data's age (1307-1313) and the cloud's gridlines +50%, +20%, 0%, -20% (1125-1127) | add both to the list |
| 5 | docs/artifacts/eth-setup-standard.html:224 | 1, outside scope | "Each card is rebuilt from the signal ledger and must match, or the old card stays up." | stack_live.py:786 writes `cards.csv` before verify_cards.py runs; verify_cards.py:170-172 only appends FAILED and exits 1; daily.yml:198-216 commits `datasets/` regardless; the console reads `/data/datasets/cards.csv` (dashboard_shim.js:61) and never reads `stack_status.txt`. After a failed cross-check the console shows the new, unverified card | "Every card is re-derived from the signal ledger each run. If it does not match, the run is marked failed and the member feed holds cards and alerts back; this console still shows the latest card." |
| 6 | cloudflare/dashboard_worker_template.js:154 (and the built worker) | 3, outside scope | Telegram forming alert: `Low ${card.low_date}, confirms ...` | `low_date` is the trough bar's open date (feed_live.py:377); on 2D+ the low printed on `low_day`, which the member card prints | use `card.low_day || card.low_date` |
| 7 | refresh.py:193-201 | 3, outside scope | `_declean` docstring: a low far under the body "is pulled back to the body" | 208-211 also pulls a high above twice the body back | "A low under half the bar's body, or a high above twice it, ..." |
| 8 | stack_live.py:8-11 | 3, outside scope | check_coverage() fails on an unmapped heading or an unevaluated id | 144-150 also fails when a DOC_MAP id is not in REGISTRY | add "a mapped id is not in REGISTRY" |

Finding 5 is not in either scope list (the console page is not named in the brief); it is reported because it is a
wrong statement about pipeline behaviour on a page Jared and Joe read. CARD_SPEC's own sentence on this (line 138, "the
feed then withholds cards and alerts") is correct.

Considered and not flagged:
- The member page's lead-trader panel ("Real trades, ... the move from his average entry and the result as a share of
  the account") describes his real Coinbase trades, a separate, clearly labelled stream in dry run; it does not present
  a computed signal as a trade, so it is not a kind 4 finding.
- FEED_SPEC "open_signals ... confirmation close is 1 to 60 days before today": the code takes 0 to 60
  (stack_live.py:399), but a confirmed signal's close date is always at least one day before today (its confirmation
  bar has closed and today's bar is open), so 1 to 60 is what the feed can hold.
- The ledger check's "60 days had not closed by `scored_as_of`" (page allows entry + 60 = `scored_as_of`) matches the
  known-by-then rule (entry + 60 on or before the date).

## Documents with zero findings

- In scope: the member page's own words (`docs/artifacts/member-site/index.html`: every How-to-read sentence, label,
  heading, badge, banner, footer, and the FEED_SCHEMA comment, checked in the code and in a headless render of the
  rebuilt feed), `README.md`, `cloudflare/README.md` (every worker claim; test counts 21, 26, 21, 45, 26, 36 all
  re-run and matching), CONTEXT.md current-rule sections (setup, gate, traps, where things live, standing
  instructions, the dated notes all carry their superseded markers).
- Outside scope: `cloudflare/BRIEF_site.md`, `BRIEF_monitor.md`, `BRIEF_dashboard.md`, `BRIEF_trades.md` (each is
  pinned to its own deploy's build and says so), `docs/PRETRADE.md` pipeline statements, `docs/SITE_CHANGES.md`
  (every Pending row is in the page on disk, superseded parts are marked; R1, R2 and R3 are not built), docstrings
  and comments of grade_live.py, verify_cards.py, extras_live.py, feed_live.py, feedcheck.py, seal.py, engine.py,
  measures.py, rounding.py, clock.py, fetch.py, regimes.py, analysis/tagstats.py, analysis/carddesign.py,
  .github/scripts/*, daily.yml, and every tests/*.py, *.sh and *.mjs header.

Figures recomputed and matching: 51 example bars (12 Aug to 20-21 Nov 2024); smallest rule-3 pool 33; first ETH graded
signal ETH 3D 2020-03-21 grade C, first ETH top grade 2020-04-18; 176 confluence cells; 13 numbers-check dates; fire
drills 58/58; troughs.json 996 rows, 6 charts; keep.json 12 setups; 11 candidate tags; 13 refresh datasets; 13 funding
markets; ten forming lows in the 2026-06-11 gate-off replay (re-run: PASS); four forming setups at 4aa1208; schema 6 asserted by
two tests; shared 4H gaps 28 Feb 2017 and 25 Oct 2025; gate off 2025-12-05 to 2026-09-01; 4H/12H volume 0 on every row;
replay_at.sh users exactly the six named; ledger 923 rows (ETH A+ 104, BTC A+ 33).

## Could not check, and why

- Cloudflare-side configuration (cron triggers on ctzb-feed and ctzb-dashboard, the R2 lifecycle rule, Access
  policies, deployed version ids, the repository being public): not in the code.
- CONTEXT's audit-count statement ("audits #22 and #23, 100 findings fixed") rests on docs/AUDIT_LOG.md, which the
  brief forbids reading.
- fetch.py's "133 committed runs of 1 to 14 Nov 2026" and dated restore-drill and backup sizes: historical, not
  recomputed.
- Browser tests (test_feed_damage, test_page_timing, numbers_check) were not re-run; their headers were checked against
  their code.

Other observation (code, not a doc finding): ctzb-trades `/health` sets `ok` only when `last_ok_at` is under 10 minutes
old (ctzb-trades-worker.js:419), but the relay stores `last_ok_at` only on a change or every 15 minutes (373-388), so in
a quiet stretch `/health` reads `ok: false` for about 5 of every 15 minutes. The health monitor and the watchdog use 20
minutes and are unaffected.
