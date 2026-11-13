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

**Changed** (commits a6ec91a and this round's):
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
