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
