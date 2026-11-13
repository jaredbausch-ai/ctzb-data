# Member-site audit log

Jared, 12 Nov 2026: keep running independent audits until two runs in a row come back with
zero issues, and document every change. This file is that record, one round per section:
what the audit found, what was changed, the commits, and what was deliberately left alone.

**How each audit runs.** A separate agent that did not build the site and may not read any
earlier audit recomputes every figure from the raw candles with its own code, then reads the
page in a real browser and checks every number shown. It audits two frozen states:

- **REPLAY:** the data committed by the 12 Nov 04:14 UTC pipeline run (commit 4aa1208), rebuilt
  with the current code and the clock set to that moment (`CTZB_NOW`). It has four forming
  setups, so the cards can be checked whatever the market is doing today.
- **CURRENT:** today's data and clock.

An "issue" is any figure that disagrees with the raw data under the repo's stated definitions,
or a label that says something the number doesn't measure. Definitional choices the repo makes
on purpose are reported as notes, not issues (listed at the end).

Everything here measures entry quality only: no exit is in the data, so none of it is a strategy
return or a track record, and no signal was traded.

---

## Round 1 — 11 Nov, 22:35 ET (first auditor)

**Found:** 16,612 figures checked, 144 disagreed.
- 118: the live feed had been written before the +10% switch (misses, odds fade, edge marks and the
  Record still measured on +20%). Fixed by the next pipeline run (04:14 UTC).
- 5: page bugs — the example's high/low day counted the 2-day bar's close day; a missing example
  file left the previous setup on screen.
- 21: wrong "diamond" tags from floating-point residue (3 signals, plus 3 odds-fade counts they
  fed), a mislabelled grade date range (7), and rounding (8).
- Plus label and meaning problems ("Previous alerts" for signals never sent; "4x"; "18 to 22 a
  year"; the all-signals fade's real sample and window).

**Changed:** label fixes (commit 9b9fa72); recount and re-audit of the audit, every row's status
in `analysis/audit_2026-11-12/reaudit/original_144_status.csv` (c3b6bb2).

**Mistake of mine, corrected:** I first reported 18 remaining; the true count was 21 (my hand count
of the scraper's false alarms was off). Every count since comes from code.

## Round 2 — 12 Nov, 10:00 ET (corrections, then the first auditor's checks re-run)

**Changed** (commit 70313e5):
- One rounding rule everywhere, half away from zero on the exact value (`rounding.py`); Python's
  built-in round() rounds 62.5 to 62.
- The ledger stores its measures to 6 places, so counts and medians use true values.
- `engine.EPS`: a stochastic change under 1e-9 is no change (removed the 3 false diamonds). Side
  effect: "ETH 2D filled diamond" drops below 70% in the older walk-forward tier, which doesn't
  drive alerts.
- A signal is scored only once its 60th day has closed (two 13 Sep signals had been scored on a
  14-minute-old bar).
- The grade date range is the grade's own.
- `clock.py` / `CTZB_NOW` so tests and audits can replay a past run exactly.
- Regression baseline re-approved after checking every drift by code: precision only, plus the 3
  tags.

**Re-run of the first auditor's scripts:** 16,216 checked, 1 disagreement (an example price built
from an unrounded median).

## Round 3 — 12 Nov, 10:25 ET (audit #3, a new independent agent)

**Found:** 41,834 comparisons across both states; 87 real issues (132 rows). Report:
`analysis/audit3_2026-11-12/AUDIT3.md`.

**Changed** (commit 57a8c34):
- **A live top-grade setup was missing.** Open signals came from an ETH-only file, so BTC 2D
  (confirmed 21 Sep 2026, A+) never showed as live. Open signals now come from `open.csv` (ETH and
  BTC), are dated by the confirmation close (one id per signal), and use closed daily candles.
- Live setups and the worked example get their own cards (own sample, ladder and edge), never the
  pooled table (CONTEXT: "the player, not the league"). The example is built only from signals
  whose 60th day had closed by 22 Sep 2024 (no hindsight).
- Prices come from the exact percentage, rounded once to the cent (cards carry `*_exact_pct`).
- The all-signals odds fade is measured on daily candles from the entry close, with the outcome
  counted after day 10. Past-path quantiles are taken on exact values.
- Chart: "At the alert" no longer shows the outcome; a forming setup's day lines count from the
  confirmation, not today; the 2-day "Confirms" line was one bar late.
- Labels: 25.3% (not 25%); "signals" (not "trades"); "all N" (not "the last N"); "Past signals"
  tab (not "Record"); "0 to −2%"; "Typical price on day 60"; the fade ladder caption says "before
  ever falling 25.3%".
- `verify_cards.py` is exact (tolerance 0), applies the flash-print rule, and also checks the live
  and example cards. Feed spec and CONTEXT updated.

## Round 4 — 12 Nov, 10:45 ET (audit #4, a new independent agent)

**Found:** 55,983 comparisons; the **feed and ledger matched exactly** (51,447 comparisons, zero
disagreements). 23 issues: 17 on the page, 6 where docs and code disagreed. Report:
`analysis/audit4_2026-11-12/AUDIT4.md`.

**Changed** (commits 94d90a0, 7342597):
- **Walk-forward tier lookahead.** `refresh.py` said the tier for a year uses "only data available
  by then", but it counted signals dated before 1 January whose 60-day outcomes ended after it.
  Now only outcomes closed before 1 January count. This moves the all-signals odds fade (e.g. red on
  day 10: 62% of 58 → 63% of 64) and the walk-forward table. Neither is shown on a card.
- **Live chart on 2-day+ charts** was anchored to today, because it looked for a bar opening on the
  entry date. It now uses the bar that closes on it, and says so if the chart data doesn't reach back.
- The actual **day the low printed** (`low_day`) is shown, not the 2-day bar's open date ("Low 9 Nov"
  was really 10 Nov).
- "Best setup forming today" only on the best one; banner says alerts are top grade only and
  below-grade forming setups are shown for context; "No open top-grade setup with its edge intact";
  the example subtitle says its odds use only signals known by then; the live side panel no longer
  says prices use today's close; the live chart subtitle says zones come from the setup's own card.
- "If it misses" now reads "median best (price within the 60 days)", which is what it measures; it
  used to say "peak before they failed".
- A value that rounds to zero shows no sign ("0.0%", not "−0.0%").
- Docs: CARD_SPEC and FEED_SPEC now say the big number is "rose 10%" (surv10 is the line under it),
  the ladder is "before falling 25.3%", open signals come from `open.csv`, and the new `low_day`.
- `tests/build_audit_states.sh` builds both audit states from the current repo, so every round
  audits exactly what's committed.

## Round 5 — 12 Nov, 11:15 ET (audit #5, a new independent agent)

**Found:** 61,226 comparisons. Every ledger row, grade_odds, if_it_misses, past_paths, the odds fade,
all 23 open signals per state, every card median/share/era/timing, every Past-signals row and every
chart price matched. 47 issues from 9 causes. Report: `analysis/audit5_2026-11-12/AUDIT5.md`.

**Changed** (commit 31c2165):
- **Ladder order within a day.** The first step checked the day's high before its low, contradicting
  the cautious rule the second step used. Both now check the low first (example "falls 5% first":
  41 · 76% → 43 · 77%).
- **Ladder "From entry" row** counted any +10%, while the rows under it count +10% before a 25.3%
  fall. Cards now carry `from_entry` on the same measure (BTC 2D forming: 67% → 60%); the big number
  is unchanged.
- **Chart day lines are placed by date.** 2D+ bars restart on 1 January, so counting 30 two-day bars
  put Day 60 one bar early across New Year. Future bars now follow that rule, and Day 10, the
  high-day and Day 60 sit on the bars containing those calendar days.
- The example's **"At the alert"** view is scaled only by prices known at the alert.
- **Live cards' `price_now`** held the entry close. Cards now carry `price_now` (latest price) and
  `entry_close` separately.
- `low_day` is searched within the trough bar's real span (a year's last bar can be short).
- Open signals are limited to the graded charts (1D–5D; 8D isn't graded).
- Every timestamp a step writes uses the replay clock, so replays are exact.
- Wording: "the latest price (today's bar is still open)" rather than "today's close"; the footer
  says "daily candles closed through 11 Nov · updated HH:MM UTC" rather than "Data through 12 Nov";
  How to read now says "before ever falling 25.3%" and explains the from-entry row.
- The At-the-alert/What-happened toggle was showing on live and forming charts (a CSS rule beat
  `hidden`); fixed.

## Round 6 — 12 Nov, 11:45 ET (audit #6, a new independent agent)

**Found:** 56,371 comparisons. Feed and ledger matched exactly again. 25 disagreement rows from 6
causes on the page and feed labels, plus 8 places where the docs and code disagreed. Report:
`analysis/audit6_2026-11-12/AUDIT6.md`.

**Changed** (commit 37bcab3):
- **The example's "where past signals went" cloud used hindsight.** It drew every ETH top-grade
  signal up to today (n 104). It now draws only those whose 60th day had closed by 22 Sep 2024
  (n 75), the same rule as the example's card. New file `pastpaths_example.csv`, new feed field
  `example_past_paths`; the subtitle names the sample.
- **"Edge lost" / "On track" on Previous signals** was judged by the pooled ETH table, even for a
  BTC setup. It now uses the setup's own ladder, as How to read says. (The BTC 2D 21 Sep badge is
  unchanged: Edge lost.)
- **Odds-fade field names** said "within 60 days" but count days 11–60. New fields
  `rose10_after_day10_pct` / `rose20_after_day10_pct`; the old names stay as aliases with the same
  values (fields are never renamed); `edge_measured_on` says "days 11 to 60". The page reads the new
  ones.
- **Miss tiles** now say their sample ("· all N ETH C signals"), since it is the whole grade, not the
  card's chart.
- Labels: "Typical change by day 60" (it's a %, not a price); Previous signals header "updates each
  close" (it shows no odds).
- **60-day windows** (ladder, from-entry row, past paths) now count 60 calendar days rather than 60
  daily bars. No figure moved: the daily data has no gaps after May 2016.
- Docs: FEED_SPEC (`cards[]` is forming setups only; `day60_pct` is always empty; odds-fade sample is
  ETH tier, days 11–60), CARD_SPEC (the check is surv10 ≤ rose 10%; ETH's first graded signal is
  18 Apr 2020 under the funding rule), the measures.py docstring, extras_live.py docstring and log
  line (+10%, not +20%), and CONTEXT's +20%-era miss figures marked superseded.

**Re-checked after the changes:** every pipeline step, regression (919 signals unchanged),
verify_cards (24 cards exact), unit tests (feed 15 + 27, candles 15, workers 21/26/36/21/24/41),
fire drills 58/58.

## Round 7 — 12 Nov, 12:20 ET (audit #7, a new independent agent)

**Found:** 60,626 comparisons. **No wrong number anywhere**: every price, percentage, count, date, day
count and chart position matched, in both states. 32 rows from 9 issues, all wording (6) or docs (3).
Report: `analysis/audit7_2026-11-12/AUDIT7.md`.

**Changed** (commit 4ea4528):
- **"If it misses: up first"** read as "above entry before ever being below it", but it counts misses
  whose best price in the 60 days was above entry. Now reads "went above entry"; How to read, FEED_SPEC
  and the code comments say the same. (The figure is unchanged, e.g. 94 of 95.)
- **"Worst drop, misses"** is a median: now "Typical worst drop, misses".
- **Forming picker buttons** showed a bare "84%": now "84% rose 10% in 60 days · n 37".
- **"Reached +20%" and "Touched −30%" tiles** now say "within 60 days · n N"; the chart side panel says
  "Reached +20% within 60 days".
- **Past signals title** now says "Every top-grade signal whose 60 days have closed" (the live BTC 2D
  signal isn't in that table yet, correctly).
- **Feed field names that say "trades"**: every `past_trades` gains a `past_signals` twin and
  `trades_a_year` a `signals_a_year` twin, same values; old names stay.
- **Lead trader with no data** (an auditor note, fixed anyway): if his feed can't be read, the page now
  says "unavailable" instead of "not in" / "No trades posted yet".
- Docs: CARD_SPEC (first graded ETH signal is ETH 3D 21 Mar 2020, grade C; first top grade 18 Apr 2020;
  the eras split surv10, not the big number), CONTEXT ("25.3%", not "25%").

**Re-checked after the changes:** feed tests 15 + 27, site worker 24, fire drills 58/58, page
screenshot with the replay data.

## Round 8 — 12 Nov, 13:10 ET (audit #8, a new independent agent)

**Found:** 59,709 comparisons. **No numeric disagreement in either state** (second round running).
11 rows, 9 items: one label (the odds-fade sample) and the rest docs that didn't match the code.
Report: `analysis/audit8_2026-11-12/AUDIT8.md` (the auditor's caches and page dumps left out).

**Changed** (commit d4f2e4b):
- **Odds-fade sample label.** It said "walk-forward tier, 2016 on", but the tier fixed on 1 Jan 2026 is
  applied to every signal back to 2016, so 167 of 168 are the signals it was chosen on. The feed's
  `sample` and the page's fine print now say so: in-sample, a general explainer. (Not shown on any card
  in either state. The auditor notes that judged year by year the "−10% to −20%" row would read 58%
  "gone" instead of 79% "intact"; I did not change the method — that's a definitional call for Jared.)
- **The 70% edge bar is now tested on the exact share**, never on the whole-percent one shown (a 69.6%
  share displays as 70% and used to count as intact). New exact columns: `reached10Exact` in
  earlydip/holdcheck, `l0okExact`…`l20okExact` on the cards, `still_rose10_exact_pct` in the feed's
  ladder rows. No badge or edge moved in either state.
- **`verify_cards.py` now re-derives every figure on a card**, as the docs claimed: added the big number,
  scaled20, dip-before-high, the three exact medians, both eras, and the from-entry and four ladder rows
  (written out independently from the 1D candles). Tested by planting four wrong values: all four caught.
  The three 6-place exact medians are confirmed to one unit in the 6th place (the ledger's precision).
- **Misses always show their count**: "5 of 5" instead of "Every time", and the miss tiles say "95 misses
  of all 312 BTC C", since their medians rest on the misses only.
- The card says once, under the big number, "every figure covers the 60 days after entry"; How to read
  says "the share" for figures shown as percentages.
- Docs: rounding stated precisely ("exact" = stored to 6 places, displayed figures rounded once from it);
  FEED_SPEC n-rule and forming wording match the page; CARD_SPEC wording rules and the verify_cards
  description; CONTEXT's old big-number line and "still on +20%" marked superseded; carddesign docstring
  (all four grades, exact edge test).

**Re-checked after the changes:** every pipeline step, regression (919 unchanged), verify_cards (24 exact),
feed/candle tests 15 + 27 + 15, worker tests, fire drills 58/58, page screenshot.

## Round 9 — 12 Nov, 13:35 ET (audit #9, a new independent agent)

**Found:** 56,383 comparisons, **0 disagreements between any figure shown and the auditor's own value**
(third round running with no wrong number). Not counted as a clean run: it listed 6 places where docs and
code disagree, one of them a real page gap, plus label notes. All fixed. Report:
`analysis/audit9_2026-11-12/AUDIT9.md`.

**Changed** (commit bf2d4b6):
- **A top-grade forming card had no "can still vanish" warning** (only below-grade ones did), and How to
  read said "by the time you get an alert, the signal is final" although forming heads-ups exist. Every
  forming card now says it can still vanish; How to read says a confirmed alert is final and a forming
  heads-up can vanish.
- **"Edge lost" / "On track" badges** used best/worst rounded to 0.1% and ignored which came first. The
  pipeline now decides it (`edge_status`, `edge_level_pct` on each open signal): on exact prices and closed
  daily bars, whichever came first, the setup's own edge level or +10%. BTC 2D 21 Sep: edge level −5%,
  lost (unchanged). Chart ladder-zone colours use the exact share too.
- **No figures typed into the page**: "about N times a year" is counted from the ledger (still 22); the
  built-in example fallback (2580.92 and hindsight numbers) is gone — without the feed's example card the
  page says "Example unavailable"; the example's "if it misses" figures now come from the feed
  (`example_if_it_misses`, n 75: 10 of 10 went above entry), not computed in the page.
- **One "known by then" rule.** The ledger's odds-on-the-day counted a past signal from entry + 61 days, the
  example from entry + 60 (both bars close at the same instant). Both now use entry + 60. 73 ledger rows'
  odds-on-the-day columns moved; nothing else. Regression baseline re-approved after checking by code that
  only `dayN`, `dayReach10/20/30`, `dayTouched30`, `daySurv10`, `dayScaled20` changed. These columns are
  not on the member page.
- **stack_live's internal card checks** now run on every card (forming, live and example), and CARD_SPEC
  says the ladder counts may stay level but never rise (what the code checks).
- CONTEXT now says exactly what verify_cards re-derives (every figure computed from a card's sample; the
  card's dates and prices are covered by the audits).
- Jared's own dashboard Telegram forming alert said "never fell 25% … past trades": now "Rose 10% within
  60 days: X% of N past signals (Y% without ever falling 25.3%)". Needs its own redeploy (SITE_CHANGES #7).

**Re-checked after the changes:** every pipeline step, regression (re-approved, then 919 unchanged),
verify_cards (24 exact), feed tests 15 + 27, all worker tests including dashboard alerts 21/21, fire drills
58/58, page screenshots (example card, How to read) with no page errors.

## Round 10 — 12 Nov, 14:00 ET (audit #10, a new independent agent)

**Found:** 60,863 comparisons. **Nothing a member sees disagreed** (fourth round running). One real data
disagreement in a ledger column the page never shows, and 5 docs-vs-code items. Not a clean run. Report:
`analysis/audit10_2026-11-12/AUDIT10.md`.

**Changed** (commit 7eaf540):
- **Ledger `dayScaled20` (odds on the day of "beat a normal move")** counted BTC signals from before 2017,
  which have no year of volatility to compare against, as misses; the card's own figure leaves them out.
  Now the same rule as the card. 499 BTC rows moved (16 now blank instead of 0; the rest were understated by
  3–97 points, e.g. BTC 3D 25 Jul 2020: 45 → 61). Every value now equals the auditor's independent figure.
  Regression baseline re-approved after checking by code that only `dayScaled20` changed.
- **The card now says which sample it uses** under the big number (e.g. "from all 33 past grade A+ signals
  across all BTC charts (BTC 2D alone has only 12, too few to use)"), not just "like this one", which could
  hide a broader sample. CARD_SPEC updated to match (no "corner").
- CONTEXT: verify_cards' one tolerance (the 6-place exact medians) stated; the 10-11 Nov member-card paragraph
  marked partly superseded (cards use their own ladder; the figures are in the feed).
- Member-site README: the candle route added; "Not deployed yet" replaced with where it is deployed.
- `extras_live.py` docstring lists `missstats_example.csv`.

**Re-checked after the changes:** every pipeline step, regression (re-approved, then 919 unchanged),
verify_cards (24 exact), feed tests 15 + 27 + 15, worker tests, fire drills 58/58, page screenshot.
## Round 11 — 12 Nov, 14:25 ET (audit #11, a new independent agent)

**Found:** 62,489 comparisons. **No number disagreed anywhere** (fifth round running), ledger included. One
wording item (12 places) and one docs-vs-code item (8 places). Not a clean run. Report:
`analysis/audit11_2026-11-12/AUDIT11.md`.

**Changed** (commit f870d65):
- **Grade letters reached members.** CONTEXT says the grade stays internal, but the sample line said
  "graded C" / "grade A+" and the miss tiles "312 BTC C". They now say "signals of the top grade" / "of the
  same grade" and "312 BTC same-grade signals". verify_cards reads the new wording; CARD_SPEC states the rule.
- **The chart's lead-trader note** said "None on this one" even when his feed couldn't be read; it now says the
  feed is unavailable in that case.

**Re-checked after the changes:** every pipeline step, regression (919 unchanged), verify_cards (24 exact),
feed tests, worker tests, fire drills 58/58, page screenshot.
## Round 12 — 12 Nov, 14:55 ET (audit #12, a new independent agent)

**Found:** 55,941 comparisons. **No figure disagreed** — feed, ledger and rendered page all matched to the last
digit (sixth round running). 5 docs-vs-code items. Not a clean run. Report: `analysis/audit12_2026-11-12/AUDIT12.md`.

**Found by me while fixing this round — the live pipeline was failing.** Every Action run since about 15:30 UTC
failed its refresh step: `refresh.py` imported `analysis/tagstats.py` (added in the round-3 corrections), which
needs numpy, and the Action installs numpy only at the next step. Every local test passed because numpy is
installed here. The feed was withheld all that time, so the live site showed "Setups held back". Fixed in
commit 3c240ec (`bucket_end` defined in refresh.py), pushed at 19:47 UTC, and a fresh run dispatched. New test
`tests/test_action_env.py` runs refresh with numpy blocked: it fails on the old code, passes on the new. It is
now part of every round's checks.

**Changed** (commit 3ba3890):
- CONTEXT and FEED_SPEC give the real schedule: the `ctzb-scheduler` Worker triggers the pipeline at :13 after
  each 4-hour close (backup :43), not 01:20 / 05:20 … or "7 minutes after".
- CARD_SPEC has a new section defining every label on the member site's card (from-entry row, Edge gone below,
  If it misses, the miss tiles, +10% level …) with its feed field, so it is again the single definition.
- How to read's "our 70% bar" now comes from the feed (`odds_fade.posting_bar_pct`), not typed.
- CONTEXT: the card states are "Live setup" / "Setup forming" / "Confirmed setup" (example), no grade letter.
- "+10% target" → "+10% level" (it is a measuring level; there is no exit in the data).

**Re-checked after the changes:** every pipeline step, regression (919 unchanged), verify_cards (24 exact),
feed tests, worker tests, fire drills 58/58, Action-environment test 1/1.
**Pipeline confirmed:** the 20:04 UTC run passed every step (refresh, grade, stack, cards, regression, extras);
the feed is published again with all 23 open signals and their cards.

## Round 13 — 12 Nov, 15:25 ET (audit #13, a new independent agent)

**Found:** 59,181 comparisons. **No number wrong** (seventh round running): ledger, feed, all 51 cards and the
page. One label (4 places) and 4 docs-vs-code items. Not a clean run. Report: `analysis/audit13_2026-11-12/AUDIT13.md`.

**Changed** (commit 0a5822d):
- **Example miss tiles** said "10 misses of all 75 ETH top-grade signals"; 75 is only those known by 22 Sep 2024
  (104 today). Now "10 misses of the 75 ETH top-grade signals known by then".
- **Regime note on `prints[]`** read the gate on the confirmation date, contradicting the documented trough
  date, so three signals the gate let through were labelled "regime off" (ETH 5D and BTC 5D 6 Dec 2025, BTC 3D
  14 Dec 2025). Now read on the trough date, for forming lows too. Feed only; not on the page.
- FEED_SPEC: `prints[]` is the last 3 confirmed per chart plus any forming low (not "every").
- CARD_SPEC: Typical high / drop prices appear on the Chart tab; "If it misses" is the median best of all the
  misses — How to read now says so too.

**Re-checked after the changes:** every pipeline step, regression (919 unchanged), verify_cards (24 exact),
feed tests, worker tests, Action-environment test, fire drills 58/58, page screenshot.
## Round 14 — 12 Nov, 16:05 ET (audit #14, a new independent agent)

**Found:** 61,267 comparisons, **0 numeric disagreements** (eighth round running). 11 docs-vs-code items, two of
them real behaviour problems in states that don't occur today (the auditor replayed a filter-off date to show
them). Not a clean run. Report: `analysis/audit14_2026-11-12/AUDIT14.md`.

**Changed** (commit c7755bd):
- **Forming cards with the market filter off.** Replaying 11 Jun 2026 (filter off), the pipeline produced 10
  forming cards and 10 forming alerts under a header reading "Market filter: off". A filter-off low can never
  confirm as a signal. Forming cards and alerts now exist only when the filter is on at the low's trough date.
  New test `tests/test_gate_off.sh` replays that date: 0 cards, 0 forming alerts (old code: 10 and 10).
- **8D forming cards** got a grade and a sample although 8D isn't graded and the card checker skipped them.
  Cards are now built on graded charts only (1D–5D); the checker fails the run if an 8D card ever appears.
- **Live setup card (Jared's 31 Oct rule: no from-entry figure beside a live trade).** The live BTC 2D card showed
  its from-entry 85% in the live colour on day 52 with its edge lost. The card itself now says "Edge lost" /
  "On track", says the odds are "as of the entry close, not from today", and an edge-lost card is dimmed and not
  drawn in the live colour. No from-today figure was invented; whether members should get one is left to Jared
  (noted in CONTEXT beside the rule).
- **Feed schema 6.** The rule says the version goes up when fields are added; it had stayed at 5 through
  11–12 Nov. New top-level `posting_bar_pct`, so the page has no typed "70" fallback left.
- Forming-low tags (diamond / prime) use exact CT and K with the engine's EPS guard, not 1-decimal values.
- `trades_a_year` rounded once from the unrounded rate. The dashboard's "Regime gate" row reads ON/OFF on the
  trough date (its "on for N days" age is unchanged).
- Chart: ladder bands show n and are captioned; the side box restates the sample for every card.
- FEED_SPEC: the page shows the exact median rounded once (was "show the rounded fields").

**Re-checked after the changes:** every pipeline step, regression (919 unchanged), verify_cards (24 exact), feed
tests 15 + 28 + 15, worker tests, Action-environment test, gate-off replay, fire drills 58/58, page screenshots
(live card, live chart).
**Pipeline on GitHub with the round-14 code:** dispatched run 43306525452 passed every step.

## Round 15 — 12 Nov, 17:15 ET (audit #15, a new independent agent)

**Found:** in the two frozen states, 67,174 comparisons and **0 disagreements** (ninth round running). This
auditor also replayed 55 other dates and built synthetic page states, and there found **5 defects that today's
data doesn't show**, plus 6 docs-vs-code items. Not a clean run. Report: `analysis/audit15_2026-11-12/AUDIT15.md`
(`all_checks.csv` is gzipped).

**Changed** (commit b8269c3):
- **Forming lows across a year-end showed the wrong confirmation date.** 2D+ bars restart on 1 January, but the
  date was built with a fixed bar step (replay 31 Dec 2023: ETH 2D "confirms 1 Jan 2024", really 31 Dec 2023;
  replay 31 Dec 2024: BTC 5D "14 Jan 2025", really 10 Jan). The signal id would also have changed on
  confirmation, reporting the forming one "vanished". It would next have shown in late December 2026. The date
  now follows the bar rule. New test `tests/test_year_end.py` replays both dates (8/8).
- **The quiet card printed a raw placeholder** ("about ${perYear()} times a year") — my slip in round 9. That
  state really occurs (7, 8, 9, 15 Sep 2026: filter on, nothing live or forming). Fixed; the years are no longer
  typed either ("2020 to last full year average; bear years, when the market filter is off, are included").
  New test `tests/test_page_states.py` renders seven states today's data doesn't show (quiet, filter off, extras
  withheld, no example, an empty era, feed down) and fails on any raw placeholder or page error (16/16).
- **"Tier as fixed on 1 Jan 2026" was typed** in the feed, the page and a code comment; it would have been wrong
  from 1 Jan 2027. Now the current year (`odds_fade.tier_fixed_on`).
- **Live chart for a setup confirmed on a year's short last bar** said the chart data didn't reach the entry; the
  entry bar is now found by the bar rule.
- "n/a%" on an era with no signals → "n/a".
- Docs: CARD_SPEC's opening (cards on graded charts with the filter on, not every chart to 8D); README (trades
  feed 404 → "unavailable"); FEED_SPEC "Not built yet" (the Cloudflare backend is built; per-tier views are not).
- `tests/replay_at.sh <date> <dir>` replays any past date on a copy, for tests and audits.

**Re-checked after the changes:** every pipeline step, regression (919 unchanged), verify_cards (24 exact), feed
tests, worker tests, Action-environment test, gate-off replay, year-end replays, page-state test, fire drills
58/58.
**Pipeline on GitHub with the round-15 code:** dispatched run 43316862036 passed every step.

## Round 16 — 12 Nov, 19:40 ET (audit #16, a new independent agent; interrupted by the usage limit and resumed)

**Found:** frozen states 86,425 comparisons: **0 disagreements in today's state, 1 in the replay state** (a "must
close above" price one cent too high for its words). It also replayed 64 other dates (1.9 million comparisons)
and 17 synthetic page renders: 3 causes on other dates, 1 in a "clock ahead of candles" state, 3 page defects in
unavailable states, 7 docs-vs-code items. Not a clean run. Report: `analysis/audit16_2026-11-12/AUDIT16.md`.

**Changed** (commits a6ec91a, 92fa64e):
- **"Confirms if it closes above $X"** was rounded to the nearest cent, so about half the time X was a cent above
  the real threshold and a close exactly at X would also have confirmed. X is now rounded down to the cent.
- **Live card "On track. It has not fallen to its edge level"** was false for a setup that rose 10% first and
  later fell through that level. New status "rose10": the card and the Previous-signals badge say "Rose 10%".
- **Half-cent prices.** −5% of $3,359.90 is exactly $3,191.905; binary multiplication printed $3,191.90. Prices a
  percentage away from the entry now use exact decimal arithmetic (`pxAt`), and `money()` rounds by the one rule.
- **Crash when an asset/grade has signals but no miss** (`carddesign.misses` took a median of nothing; 5 replay
  dates in 2020–21 could not run). Now empty medians, and the card says "none missed".
- **Day counts one short just after midnight UTC**: stack_live took "today" from the last daily candle; now from
  the clock, like the other steps.
- **"If it misses" row** names its pool on every card (top-grade cards named it only in the tiles).
- **Unavailable read as "none"**: with the feed down or held back, the Live row and Previous signals said "No
  live top-grade setups"; with the ledger missing, Past signals said "0 signals"; with a chart file missing, the
  Chart tab kept the previous setup's heading and figures. Each now says unavailable / held back and clears.
- **Test harness**: `tests/replay_at.sh` kept the open 2D–8D bar whole (later days leaked into a replay). It now
  rebuilds those bars from the cut daily candles with fetch.py's own rule; the gate-off test uses it.
- `odds_fade.tier_fixed_on` quotes refresh.py's own anchor (new status.csv row "Tier fixed on") instead of
  feed_live's clock. Docs: CONTEXT (rounding), CARD_SPEC (rounded-down threshold, miss pool), FEED_SPEC.
- `tests/test_page_states.py` grew to 20 checks (feed down, held back, ledger missing, no misses).

**Re-checked after the changes:** every pipeline step, regression (919 unchanged, 2 new: the 13 Sep signals'
60th day closed), verify_cards (22 exact), feed tests 15 + 28 + 15, worker tests, Action-environment test,
gate-off replay, year-end replays 8/8, page states 20/20, a replay of 15 Mar 2021 (used to crash), fire drills
58/58.
**Pipeline on GitHub with the round-16 code:** dispatched run 43339771405 passed every step.

## Round 17 — 12 Nov, 20:55 ET (audit #17, a new independent agent)

**Found: both frozen states clean** — 60,015 comparisons, 0 disagreements (data and rendered page), and the
checker caught 5 of 5 planted errors. Not a clean run: it also replayed 173 other dates (3.7 million comparisons)
and 30 synthetic page states, and found 2 defects on other dates, 5 in page states that only occur when
something is broken, and 3 docs-vs-code items. Report: `analysis/audit17_2026-11-12/AUDIT17.md`.

**Changed** (commits 3dddb15, 9d2d52b):
- **A quiet market failed the run.** With no low forming on any chart and no signal in its 60 days, the stack
  step raised a "coverage failure" (nothing to evaluate a read against), so the feed was withheld and the page
  said "Setups held back" instead of the quiet card. By the auditor's scan that was 38 of the 271 filter-off
  days between 5 Dec 2025 and 1 Sep 2026. The check now needs a subject before it requires every read; a replay
  of 15 Mar 2026 publishes normally.
- **A run just after midnight UTC, before the new day's candle existed**, showed a setup whose confirmation bar
  had already closed as "forming … can still vanish" (and left it out of open signals) until the next run. The
  pipeline assumed the last daily bar is today's open bar, but the freshness check accepted yesterday's bar for
  the first 20 minutes of the day. Now: fetch.py builds today's bar from the hourly candles when the daily
  endpoint is slow; the freshness check no longer accepts yesterday's bar (such a run is retried like any stale
  fetch); and the stack step fails closed if today's bar is missing. (At 00:13 UTC on 13 Nov the exchange already
  had the new daily candle, so this was not live today.)
- **Fail-closed feed**: the header said "Market filter: off" and the scored date was blank; both now read
  "unavailable".
- **A chart that can't be drawn** (example file missing, candle file missing or too short) kept the previous
  setup's title, subtitle or cloud. One exit path now clears everything.
- **Chart note claimed lead-trader markers** that are never drawn. It now says his trades are listed on the Now
  tab.
- Chart labels are drawn above the candles (the auditor's legibility remark; Jared, 11 Nov). No `-0.0` in the feed.
- Docs: FEED_SPEC (fail-closed feed, audit #17 section), CARD_SPEC and CONTEXT (three live-card statuses).
- New tests: `tests/test_no_today_bar.sh` (a run without today's candle withholds cards), `tests/test_fetch_today.py`
  (hourly fallback, stricter freshness check, 4/4), `tests/test_page_states.py` now 21 checks; `tests/replay_at.sh`
  takes a clock and a keep-going flag.

**Re-checked after the changes:** every pipeline step, regression (919 unchanged, 2 new), verify_cards (22
exact), feed tests 15 + 28 + 15, worker tests, Action-environment test, gate-off replay, no-today-bar replay,
year-end replays 8/8, page states 21/21, fetch tests 4/4, replay of 15 Mar 2026, fire drills 58/58, chart
screenshot.
**Pipeline on GitHub with the round-17 code** (new fetch fallback and stricter freshness check): dispatched run
43349219267 passed every step.

## Round 18 — 12 Nov, 22:15 ET (audit #18, a new independent agent)

**Found: both frozen states clean again** — 58,409 comparisons, 0 disagreements; and the same two pages under
four browser settings (time zone, locale, phone, large screen), 25,484 comparisons, 0. It replayed 98 other
dates (2.15 million comparisons): 97 with 0 disagreements, 1 defect in one replay. Synthetic page states: 3
defects, all files arriving cut short. Docs vs code: 2. Not a clean run. Report:
`analysis/audit18_2026-11-12/AUDIT18.md`.

**Changed** (commits 8b07b2f, 994f4e5):
- **A forming card with an empty sample** (replay of 15 Aug 2020: "all 0 past signals") printed "n/a%", "null%"
  and "Holds at every level". Cannot recur on today's data (the smallest pool is 33). Now: no card and no
  forming alert for an empty sample; the page prints "n/a" (never "n/a%") through one helper; and a setup whose
  card has no past signals shows "No odds yet".
- **A ledger that arrives cut short** was listed as the whole record ("105 signals" beside summary boxes saying
  137). The page now accepts the ledger only if it holds exactly the top-grade signals the feed counts, per
  asset; otherwise "Past signals unavailable".
- **A candle file with no bars** threw a script error or drew a chart with broken coordinates; **an example chart
  file that stops before day 60** threw an error and drew a best price from the partial window. Both now read
  as unavailable (a chart file needs at least 10 numeric bars; the example file must reach 60 days past its entry).
- Docs: CARD_SPEC says rule 3 (same grade across the asset's charts) is used whatever its size, and that an
  empty sample gets no card.
- `tests/test_page_states.py` now 25 checks (empty-sample card, cut ledger, short candle files, cut example file).

**Re-checked after the changes:** every pipeline step, regression (919 unchanged, 2 new), verify_cards (22
exact), feed tests 15 + 28 + 15, worker tests, Action-environment test, gate-off and no-today-bar replays,
year-end replays 8/8, page states 25/25, fetch tests 4/4, a replay of 15 Aug 2020 (no empty-sample card), fire
drills 58/58.
**Pipeline on GitHub with the round-18 code:** dispatched run 43356294325 passed every step.

## Round 19 — 12 Nov, 22:50 ET (audit #19, a new independent agent)

**Found: nothing wrong on real data.**

| Scope | Comparisons | Disagreements |
|---|---|---|
| Both frozen states (data and rendered page) | 61,795 | 0 |
| 60 replays of other real dates, Sep 2020 – Nov 2026 | 1,392,325 | 0, and no pipeline step failed |
| Envelope test (clock a day ahead of the candles) | 7 | 0 (fails closed) |
| 51 deliberately broken page states | 186 | 4 defects |
| Docs vs code | — | 0 on any figure, threshold, window or rounding rule; 5 loose statements |

The replays covered 22 filter-off runs, 12 first/last days of a filter episode, 9 year-ends, 18 with a top-grade
forming low, 13 quiet days, 9 with a signal on day 60, 7 on day 1. The checker caught 27 of 28 planted
single-figure errors; the 28th changes no displayed digit. Report: `analysis/audit19_2026-11-12/AUDIT19.md`.

**This is the first audit with zero issues on the two frozen states AND zero on replays of real dates.** It is
not zero on everything: the four defects are in states a working pipeline does not produce, and five doc
sentences were loose. Whether that counts as a clean run is Jared's call (asked 12 Nov, 22:25 ET).

**Changed** (commits 52a5811, 43c3570, 5b74bcd):
- **A live setup whose own card is missing from the feed**: the page built a stand-in card from pooled figures
  (another table's edge on a BTC signal, "On track" for a signal the feed marks edge lost). It now shows "Card
  unavailable" and no figures, and makes no status guess of its own. The pipeline's card check also fails the
  run if any live signal lacks a card, so the feed never carries one.
- **Chart file one bar behind the feed**: the last candle is labelled "Latest bar · date", not "Today".
- **Lead trader with trades only in the other asset**: "not in", not "out".
- **Price axis**: enough decimals at any price level (a sub-$5 asset read "$0" on every gridline; not reachable
  for BTC or ETH).
- Docs: refresh.py and stack_live.py docstrings list what they read and write; FEED_SPEC `low_date` (up to a bar
  length minus a day earlier); README (the page types definitions, not figures); How to read (a signal counts if
  the filter was on the day its low printed; the header shows the filter today).
- `tests/test_page_states.py` now 26 checks.

**Re-checked after the changes:** every pipeline step, regression (919 unchanged, 2 new), verify_cards (22
exact; fails when cards_open.csv is removed), feed tests 15 + 28 + 15, worker tests, Action-environment test,
gate-off and no-today-bar replays, year-end replays 8/8, page states 26/26, fetch tests 4/4, fire drills 58/58.

---

## Round 20 — 13 Nov, 00:40 ET (audit #20, a new independent agent)

**Found: nothing wrong on any figure a working pipeline publishes.**

| Scope | Comparisons | Disagreements |
|---|---|---|
| (A) Both frozen states (data and rendered page) | 60,174 | 0 |
| (B) 110 replays of other real dates, Sep 2020 – Nov 2026 | 2,357,666 | 1 figure: the worked example's chart file carried one candle after day 60 (a static file the replay does not cut; no card figure affected) |
| (C) 150 deliberately broken or synthetic states | 711 | 9 causes |
| (C) 5 tampered-candle states the pipeline published, re-audited in full | 138,427 | 0 (self-consistent) |
| Docs vs code | — | 1 rounding wording (no instance in the data), 11 loose or stale sentences |

The replays covered 23 filter-off runs, 12 first/last days of a filter episode, 19 year-end days and the 2024
leap day, 35 with a top-grade forming card, 11 with nothing live or forming, 23 quiet cards, 9 around a
signal's day 60, 10 the day after a confirmation, 10 at clocks other than 04:14. The checker caught 20 of 20
planted errors. Report: `analysis/audit20_2026-11-12/AUDIT20.md`.

**Changed** (commits 7a52463, f01fbb3):
- **Example chart file**: trimmed to 51 bars, ending with the bar that holds day 60.
- **Candle files cut short passed every step** (BTC daily cut to 40 bars, ETH 2D cut in half): a new
  whole-history check (`fetch.history_problems`) requires each daily file to start on the exchange's first day
  with no missing day after it, and every 2D–8D file to be exactly its daily candles bucketed. The candle check
  fails the run on it, and stack_live.py fails closed on it as well.
- **Member page, damaged or hand-edited feeds** (none of these is produced by the pipeline):
  - feed that is not a JSON object, or has no readable `generated_at`: "Data unavailable" (was a JavaScript
    error and a blank card area);
  - `cards_withheld` true with cards left in: the cards and live signals are ignored;
  - no posting bar and an empty `odds_fade`: the Chart tab says unavailable (was a JavaScript error);
  - a price that is not a number: "n/a" (was "$NaN");
  - no typical day of the high: the label is left off (was "day null");
  - unknown `edge_status`: "Status unavailable" (was "On track");
  - unknown `market_regime`: "Market filter: unavailable" (was "off");
  - lead-trader row with empty fields: no "null" placeholder.
- **Docs**: rounding rule worded exactly (half away from zero on the stored float, as Python and the browser
  both do); CONTEXT confirmation lag (3 / 7 / 11 / 19 / 31 days from low date to confirmation date) and the
  regime episode's last day (26 Jan 2022); engine.py, grade_live.py, refresh.py, measures.py docstrings; README
  (13 datasets); member-site README header; CARD_SPEC ("beat a normal move" denominator, the card's closing
  line); FEED_SPEC now defines the ledger's odds-on-the-day columns, `trades_a_year` and the past-path
  quartiles, and "2020 to last year".
- `tests/test_page_states.py` now 37 checks; `tests/test_check_candles.py` now 23.

**Re-checked after the changes:** every pipeline step, regression (919 unchanged, 2 new), verify_cards, feed
tests 15 + 28, candle check 23/23, Action-environment test, year-end replays 8/8, fetch tests 4/4, page states
37/37, gate-off and no-today-bar replays, a replay of 15 Sep 2020, worker tests 21 / 26 / 36 / 21 / 24 / 41,
fire drills 58/58.

---

## Round 21 — 13 Nov, 03:30 ET (audit #21, a new independent agent; then the audit method changed)

**Jared's definition from here (13 Nov, 01:34 ET):** a clean run is zero of anything, including deliberately
broken states and doc wording. Two clean runs in a row before the site ships. On that definition there have
been no clean runs yet.

**Found:**

| Scope | Comparisons | Disagreement rows | Distinct causes | Wrong figure? |
|---|---|---|---|---|
| (A) Both frozen states | 61,125 | 0 | 0 | — |
| (B) 188 replays of real dates, Sep 2020 – Nov 2026 | 4,136,858 | 39 | 2 | No, both wording |
| (C) 133 deliberately broken states | 484 | 21 | 11 | 4 |
| Docs vs code | about 70 statements | 3 | 3 | No |

The checker caught 65 of 65 planted errors. Report: `analysis/audit21_2026-11-13/AUDIT21.md` (group B's
per-replay check files, 26 MB, are not committed; their totals are in the report).

**Changed** (commits 0cf798f):

*Wording on real dates*
- How to read said a signal counts if the filter was on "the day its low printed". The filter is read on the
  day the bar that made the low opened, which on a 2D, 3D or 5D chart can be a few days earlier (3 setups in
  six years fall in that gap, none top grade). The sentence now says so.
- Previous signals' first group was headed "Edge intact" but also held setups that rose 10% and later fell to
  their edge level. Now headed "On track or rose 10%".

*Broken states with a wrong figure*
- A candle file with a row twice, or rows reversed, passed every check and was scored (the checks key rows by
  date; the engine reads them as a list). `fetch.history_problems` now requires every candle file (1D–8D, 4H,
  12H) and the funding series to run in strictly ascending time.
- A pipeline file lost after the checks passed made the page read as a quiet market. feed_live now fails closed.
- A failed refresh republished the last good run's market filter reading. It is now left empty (header:
  "Market filter: unavailable").
- In that state the footer's candle date came from the clock. It now comes from the data's own date, and is
  left off when there is none.

*The other seven broken-state causes, and the change of method.* Seven of the eleven causes were the page
reacting badly to hand-damaged feeds, as in every round since #16. Instead of patching each one:
- **One strict check.** The page holds one definition of a well-formed feed (`FEED_SCHEMA`: every field's
  type, range, allowed words and list lengths, plus rules across fields). A feed that fails anything is not
  used at all: "Data unavailable". The lead-trader file, the ledger and the chart files get the same treatment.
  `feedcheck.py` reads the same block, and `feed_live.py` will not publish a feed that fails it.
- **The run seal (`seal.py`).** Every scoring step checks, as it starts, that the steps before it finished in
  order and that no file in `datasets/` has changed since; feed_live checks the same before publishing. A file
  deleted, cut, edited or swapped for an older copy between steps, a step that never finished, or steps run
  out of order now fail the run closed. An extras failure part-way still lets the cards publish.
- **Step outcomes read strictly.** A gating step reported as anything but "success" (skipped, cancelled,
  missing) now withholds.
- **`tests/test_feed_damage.py`.** Damages every field the page reads in about 35 ways each. On the two test
  states: 21,436 damaged feeds, page and pipeline gave the same verdict on every one; all 1,834 accepted kinds
  rendered with no script error or placeholder; rejected ones read "Data unavailable"; 1,390 damaged
  lead-trader files, 22 damaged ledgers and 20 damaged chart files read "unavailable". 30/30.
- **Audits from round 22 run as three independent agents at once:** numbers on real data, broken states, docs.

*Docs:* `went_on_to_fall25_pct` defined as falling 25.3% before rising 10%; `prints[]` holds the last 3
signals per chart; the member-site README's list of fixed wording completed; FEED_SPEC "Audit #21
corrections"; CONTEXT "The strict check, and how audits are counted".

*Tests:* page states 44 (was 37), candle check 29 (was 23), alerts 23 (was 15), run seal 18 (new), feed damage
30 (new).

**Re-checked after the changes:** every pipeline step, regression (919 unchanged, 2 new), verify_cards, feed
alerts 23/23, feed extras 28/28, candle check 29/29, run seal 18/18, feed damage 30/30, Action-environment
test, year-end replays 8/8, fetch tests 4/4, page states 44/44, gate-off and no-today-bar replays, worker tests
21 / 26 / 36 / 21 / 24 / 41, fire drills 58/58. All 91 real feeds built from replays (2020 to today) pass the
strict check.

---

## Round 22 — 13 Nov, 08:00–11:00 ET (audit #22: three independent agents at once)

**The new method's first round.** Three agents ran in parallel, each knowing nothing of earlier audits: numbers
on real data, broken files, and docs against code.

**Jared's definition, settled during this round (13 Nov 10:23 ET):** a clean run is zero on real data, zero in
the docs, and zero under damage that can really happen (outages, bad exchange data, partial or killed runs,
lost, cut, stale or duplicated files, wrong clocks, slow files). Hand-forged files whose fields are each valid
but contradict each other are hardening: listed and fixed where cheap, not counted against a run. Two clean
runs in a row before launch. No clean run yet.

**Found:**

| Part | Checked | Findings |
|---|---|---|
| Numbers on real data | 2 frozen states + 302 replayed dates, 6,011,866 comparisons | 1: on 1–11 Sep 2020 a live ETH grade-A card had no past signals yet; the strict check rejected it and the whole feed was held back on good data |
| Broken files | 639 damaged states (399 page, 240 pipeline) | 165 rows, 103 distinct cases: 68 hand-forged contradictions on the page; 35 in the pipeline (real damage) |
| Docs against code | 60 documents, about 1,050 statements | 57 (8 wrong, 14 stale, 29 loose, 6 reading as a trade or track record) |

The most serious docs finding: the page promised members push alerts ("Alerts go out for top-grade setups
only… You'll get a push alert"), but no member alert channel exists; every alert, any grade, goes only to
Jared's private Telegram.

Reports: `analysis/audit22_2026-11-13/` (AUDIT22_NUMBERS.md, AUDIT22_BROKEN.md, AUDIT22_DOCS.md).

**Changed** (commits PENDING_A):

*Real damage that got through, now stopped:*
- Every ETH candle file replaced by BTC's passed the candle checks. ETH's daily close must now be 0.1% to 50%
  of BTC's on every day.
- Old candle rows with a zero, negative or "nan" price, a high below the open and close, damaged 4H/12H files:
  every row of every candle file is now checked for its whole history.
- A funding file cut short, holding "nan" or -100: the funding series must now be whole, in range and current.
- The run seal now covers the candle files and the funding series as well as `datasets/`.
- `candle_check.json` saying the candles failed no longer lets a later step publish.
- A deleted alert log started a new one and lost the pending alert; a cut, emptied or older log re-sent alerts.
  The feed now records the log's exact state and the next run checks it; a new log only on purpose
  (`CTZB_SEED_ALERT_LOG=1`).
- The feed was written after the log and not atomically. Now the feed is written whole first, then the log;
  if a run dies between them, the next run rebuilds the log from the feed's alerts.
- A held feed still carried grade figures, the extras and the old market filter reading; now it carries none.
  A refresh reported as anything but "success" clears the status fields too.
- `tests/regression.py` re-baselined and passed when its baseline was missing; now it fails.
- feedcheck.py and the page disagreed on three unusual-character cases; they now trim and match digits the same way.

*Page:*
- A slow ledger, trade or example file left the card area blank: the card now draws as soon as the feed
  arrives, the rest fill in ("Loading…").
- An example file with 2-day bars thinned out threw a script error; one with no entry close drew NaN. The
  example file must now run on 2-day steps, its entry bar must be 22 Sep 2024, and its entry close the card's.
- With the feed held or down, the example switch and the Chart tab now say so; the stale warning shows on every
  tab; a quiet feed with no example no longer shows "Example unavailable".
- Chart files must name the chart asked for, run on its own steps, end no later than the feed, and close the
  live setup's entry bar at its entry close. The ledger must match the feed's counts and rose-10% share per
  asset, each row must agree with itself, every signal's 60 days must have closed, and it is not shown when the
  feed is down or held. The lead-trader file must be newest first with nothing in the future.
- Hardening (hand-forged contradictions): every number now has a range; cards' shares nest; a live signal's
  day count, closed-day figures, best/worst and status must agree with its dates and edge level; misses, past
  paths and the example must match their samples; odds-fade rows in fixed order with marks matching shares.
- Alerts: the page no longer promises member alerts; it says they aren't switched on yet. Member alerts are on
  the to-do list (SITE_CHANGES R3).

*Numbers:* a live card with no past signals yet is now published with no figures ("No odds yet"), and a band
of the general odds table with no past signals is left out (both early 2020 only). Checked: 51 replayed real
feeds and ledgers, Sep 2020 to today, all accepted by the page with no errors.

*Docs:* all 57 findings corrected (FEED_SPEC "Audit #22 corrections" lists the fields that were undescribed and
every new rule; CARD_SPEC reworded from trades to signals; README, CONTEXT, PRETRADE, worker comments and
docstrings).

*Tests:* alerts 30 (was 23), candle check 57 (was 29), page states 44, damage test extended to the Sep 2020
state, fire drill E now ages the feed by the viewer's clock.

**Re-checked after the changes:** every pipeline step, regression (919 unchanged, 2 new), verify_cards, feed
alerts 30/30, feed extras 28/28, candle check 57/57, run seal 18/18, Action-environment test, year-end replays
8/8, fetch tests 4/4, page states 44/44, gate-off and no-today-bar replays, worker tests 21 / 26 / 36 / 21 / 24 /
41, fire drills 58/58; page and pipeline gave the same verdict on 31,200 damaged feeds across three states
(12 Nov, today, 5 Sep 2020); 51 replayed real feeds and ledgers accepted by the page with no errors.

---

## Deliberately left alone (definitional notes, not issues)

- **Flash-print clamp.** A $0.06 BTC low on 15 Apr 2017 (and ETH's $0.10 GDAX wick on 21 Jun 2017)
  is pulled back to the bar body before anything is measured. Bad prints, documented in CONTEXT.
- **Regime gate date.** The gate is read on the trough date. Reading it on the confirmation date
  would change about 22–29 signals. Jared's call; not changed.
- **Diamond definition.** CT against K versus the previous trough among all troughs, as in
  `engine.py`.
- **Order inside a day.** A daily bar doesn't say whether its high or its low came first; the ladder
  checks the low first (the cautious reading), in every step since round 5.
- **"Must close above"** for a setup one bar from confirming assumes today's open bar closes at the
  current price.
- **"Day N of 60"** is the day in progress.
- **`peaked_10_or_more`** is 0 by construction now that a miss means "did not rise 10%".
- **The all-signals odds fade's tier** is chosen by refresh.py's original rule on each chart's own bars;
  only its groupings and outcomes use daily candles. It is a general explainer and not shown on any
  card.
