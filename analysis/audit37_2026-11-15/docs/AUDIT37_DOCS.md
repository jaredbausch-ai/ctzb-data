# Audit round 37, docs part (frozen code 44e7a74)

Entry quality only: everything checked here describes computed signals and their 60-day records. There are no
fills, no exits and no strategy return in the data.

## Top line

| | |
|---|---|
| Documents read | 31 (the 7 counted documents; 4 BRIEF files, PRETRADE, SITE_CHANGES; 16 Python modules, daily.yml and 3 .github scripts; the headers of all 31 test files) |
| Statements checked | about 1,050 (FEED_SPEC ~240, CARD_SPEC ~75, member page words ~160, the three READMEs ~110, CONTEXT current-rule sections ~130, outside-scope files ~335) |
| **Counted findings (in scope)** | **8**: kind 1 wrong: 1; kind 2 stale: 0; kind 3 loose: 7; kind 4 reads as a return / trade / track record: 0 |
| **In-scope kinds 1, 2 and 4 together** | **1** (the round is not clean on the docs part) |
| Outside scope (not counted) | 8: kind 1: 2; kind 2: 1; kind 3: 5; kind 4: 0 |

The feed was rebuilt in the copy with the brief's command chain; it matched the committed feed except for the
time stamps (generated_at, the two stack_status lines). The two generated Workers rebuild byte-identical from their
sources. All six Worker test suites pass with the counts cloudflare/README.md quotes (21, 26, 21, 45, 26, 36).

## Counted findings (in scope)

| # | File | Line | Kind | Quoted (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| 1 | docs/FEED_SPEC.md | 228 (rule at 52-53) | 1 | "`confirmed` (date), `closes` (confirmed + 10 days)" for confluence windows, under "Every signal is dated by its confirmation bar's close date ... exceptions are named where they occur" | stack_live.py 733-737 dates a DIVH window by analysis/htfdiv.py 39-63 `divergences()`, which returns `dates[conf]`: the OPEN date of the bar that confirms the divergence (it can be today's still-open bar). Feed now: ETH 2D DIVH "confirmed 2026-11-07" (that bar closes 2026-11-08), closes 2026-11-17 = close + 9. Signal windows use the close date (stack_live.py 726) | "`confirmed` (date: for a signal, its confirmation close date; for a DIVH window, the open date of the bar that confirms the divergence, which can be the bar still open today), `closes` (that date + 10 days)" |
| 2 | docs/FEED_SPEC.md | 3-4 | 3 | "carries every computed signal, card and card figure the member page and the alert sender use" | The page also reads past computed signals from datasets/ledger.csv (Past signals tab, the five closed signals under Previous signals, the per-year count; index.html 857-885, 1307-1325) | "carries every card and card figure the member page and the alert sender use, and every live, forming and recent signal; the page's past-signal record comes from `datasets/ledger.csv` beside it" |
| 3 | docs/FEED_SPEC.md | 59-60 | 3 | "`rounding.rnd` rounds ... once, from the unrounded value" | if_it_misses / example_if_it_misses medians and mean (carddesign.py 62-75) are taken from the ledger's 6-place measures (grade_live.py 239-240), then rounded to 1 place | "... once, from the unrounded value (for `if_it_misses` and `example_if_it_misses`, from the ledger's 6-place measures) ..." |
| 4 | docs/FEED_SPEC.md | 516-517 | 3 | "Ledger. Unavailable ... when ... a signal appears twice" | index.html 1310-1314: the duplicate test runs on top-grade rows only | "... a top-grade signal appears twice ..." |
| 5 | docs/CARD_SPEC.md | 6-7, 71-75 | 3 | "A card may not show a number that is not defined here ... Also on the member page: ..." | Two Chart-tab blocks are defined nowhere: "Where the past signals went" (past_paths / example_past_paths: median and middle half per day, "Day 60: median, middle half", n; index.html 1103-1133) and the example's "What this one did" (reached +10/+20%, best price and days, deepest drop and days, day-10 check, price on day 60; 1146-1157) | Add both to "Also on the member page" (full text in findings.csv) |
| 6 | cloudflare/README.md | 49 | 3 | "a feed the mirror misses loses nothing while the mirror pulls at least once a day" | feed_live.py 283-310, FEED_SPEC 314-315: true short of a hold of more than 7 days followed by an unreadable previous feed | add "(short of a hold of more than 7 days followed by an unreadable feed; docs/FEED_SPEC.md, Alerts)" |
| 7 | README.md | 67-68 | 3 | "13 of the datasets behind the dashboard (ETH Setup Standard) and the member feed" | Of the 13, the dashboard reads status, live, forward; the feed status, forward and (through extras_live) earlydip, holdcheck. setups, tier, walkforward, years, confluence, invalidation, levels and buy are read by neither | "turns the candles into 13 datasets; the dashboard reads status, live and forward of them, and the member feed status and forward plus earlydip and holdcheck (through extras_live.py)" |
| 8 | CONTEXT.md | 1477 | 3 | "At 3.3x with no reserve that share is A+ 14%, A 25%, B 27%, C 36%." | dipdist.csv at -25.3%: ETH 14/25/27/36 (matches); BTC 15/14/23/27. The asset is not named | "that share is, for ETH, A+ 14%, A 25%, B 27%, C 36% (BTC: A+ 15%, A 14%, B 23%, C 27%)" |

## Outside scope (not counted)

| # | File | Line | Kind | Quoted (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| O1 | cloudflare/BRIEF_trades.md | 152 | 1 | "Every minute it reads new futures fills, positions and the futures balance" | Fills every minute; positions and balance only when fills arrive, on an adjusted fill, or every 15 minutes (ctzb-trades-worker.js 354-356; same in the pinned 08e06ab) | "Every minute it reads new futures fills; it reads positions and the futures balance when fills arrive and otherwise every 15 minutes" |
| O2 | docs/SITE_CHANGES.md | 33 (Pending 6l) | 1 | "off the card's price by half a cent or more is not drawn" | sameCents passes a gap of exactly 0.005 (index.html 345, 965) | "off ... by more than half a cent is not drawn" |
| O3 | CONTEXT.md | 1622 (dated, 4 Nov) | 2 | "the candle job ticks at :13 and :43 every hour plus 00:07 ...; the watchdog ... alerts at 4h45m" | No GitHub cron; the scheduler Worker dispatches daily.yml at :13/:43 after each 4-hour close and the watchdog 95 min after each close. The section's [superseded] note covers only the dashboard upload; the correction is in the next section | prefix "[superseded 10 Nov 2026: ...]" (findings.csv) |
| O4 | refresh.py | 6-7 docstring | 3 | "the dataset CSVs the ETH Setup Standard dashboard and the feed read (tier, buy, ...)" | Neither reads tier.csv or buy.csv | list what each reader takes (findings.csv) |
| O5 | stack_live.py | 20-30 docstring | 3 | "windows.csv ... which print opened it"; Writes list | DIVH windows are opened by a divergence; stack_status.txt is written too and not listed | "the print or divergence that opened it"; add stack_status.txt |
| O6 | feed_live.py | 13 docstring | 3 | "every record carries the computed-signal label" | confluence_windows rows carry none (543-547) | "every card, print, live signal, grade row, alert and extras block carries ..." |
| O7 | tests/test_page_states.py | 1-2 header | 3 | placeholder list | BAD (line 20) also matches "[object" | add "[object" |
| O8 | grade_live.py | 243-245 comment | 3 | "whose 60 days had finished before this entry" | `entry + 60 <= this entry` (253): same day counts | "whose 60th day had closed by this entry's close" |

## Documents with zero findings

Counted: docs/artifacts/member-site/index.html (every label, heading, badge, banner, footer, How-to-read sentence
and the FEED_SCHEMA comment), docs/artifacts/member-site/README.md.
Outside scope: cloudflare/BRIEF_site.md, BRIEF_dashboard.md, BRIEF_monitor.md (each checked against its pinned
commit: byte counts and first lines match), docs/PRETRADE.md (pipeline statements; 12 headings covered as the stack
step reports), SITE_CHANGES "Requested, not built yet" (R1-R3 really not built) and every other Pending row,
engine.py, measures.py, rounding.py, clock.py, fetch.py, regimes.py, seal.py, feedcheck.py, verify_cards.py,
extras_live.py, analysis/tagstats.py, analysis/carddesign.py, .github/scripts/check_candles.py, check_fresh.py,
retry_after_failure.sh, .github/workflows/daily.yml, and every test header except test_page_states.py.

Recomputed and matching: 13 refresh datasets; 996 troughs on 6 charts; 12 keep.json setups; 11 candidate tags;
176 confluence cells (83 + 49 + 44); smallest rule-3 pool 33; first graded ETH signal ETH 3D 2020-03-21 C, first
ETH A+ 2020-04-18; 51 example bars from 12 Aug 2024; 13 numbers_check dates; 13 funding markets; schema-6 fields
added without a bump (exactly the four FEED_SPEC names); shared 4H gaps 28 Feb 2017 and 25 Oct 2025; regime on
since 2026-09-02; dipdist shares (ETH); rounding imported by exactly the five modules CONTEXT names.

## Could not check, and why

- Cloudflare-side settings not in the repo: cron triggers, R2 lifecycle, deployed version ids, Access policies.
- Pine scripts' behaviour (CONTEXT: indicator v15 and scanner v9 "keep the asterisk ETH grade"; scanner compiling).
- Historical one-off figures (TradingView bar and signal matches, the restore drill, "133 committed runs").
- (Checked, not a gap: tests/fire_drills.py rerun in the copy gave 58/58 in 196 s, matching CONTEXT's "58/58" and
  the header's "about 3 minutes".)
- docs/audit/* (DAMAGE_LIST "six families") was not opened: it is audit process, not code.
- One question, not a finding: CARD_SPEC 52 says five mechanical exits lost to holding and CONTEXT 26 counts four
  plus the 50-line cross, while PRETRADE's two-stage row (9 Nov) calls itself the sixth. Which count is meant?
