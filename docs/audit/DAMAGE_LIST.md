# The frozen damage list

Jared, 13 Nov 2026, 20:23 ET: the damage list is frozen. This file defines it and how the damage part of an audit is
counted from round 27 on.

**Why.** The specific ways files and runs can break are effectively unlimited (about 60 files, dozens of ways to
break each, at any point in a run), so a fresh auditor always finds a case nobody tried. The kinds of damage are few.
Each kind has one general rule in the code meant to catch every case of that kind; the audit tests those rules.

## The six families, the rule that guards each, and the tests

| Family | What it covers | The general rule | Tests |
|---|---|---|---|
| 1. Missing | A source down, a file lost or emptied, any HTTP failure | Pipeline: a missing input stops the job before scoring (`check_fresh`, `fetch.history_problems`); a dataset lost between steps breaks the run seal; `feed_live.py` fails closed when a dataset or the alert log is missing. Page: any file that does not arrive reads "unavailable" (feed: "Data unavailable") | test_check_candles, test_seal, test_feed_alerts, fire_drills, test_page_states |
| 2. Malformed | Rows or cells cut, blank, duplicated, reordered or of the wrong type; a file cut at any point; columns missing or extra | Every scoring input goes through `fetch.history_problems` (every row, every cell of every column, the columns the scorer reads in range, a whole last line); every file the page reads goes through its strict check (`FEED_SCHEMA`, and the ledger, chart, example and lead-trader checks), which `feedcheck.py` applies to the feed before publishing | test_check_candles, test_cut_files, test_series_cells, test_feed_damage, test_page_states |
| 3. Wrong content | A well-formed file holding the wrong thing: another asset or timeframe, an older run's copy, another run's chart or ledger | Inputs: asset and timeframe checks and the 2D-8D bucketing check (`fetch.history_problems`). Between steps: the run seal's hashes. The alert log: its hash against the last feed. Page: each file must agree with the feed (chart names its chart and ends no later than the feed; the ledger matches the feed's counts; the example file matches the example card) | test_check_candles, test_seal, test_feed_alerts, test_page_states |
| 4. Partial run | A step killed, skipped, repeated or out of order; files from two runs; two runs at once | The run seal (steps in order, files unchanged, one run); step outcomes read strictly (`CTZB_STEP_OUTCOMES`); the extras step clears its outputs first; the feed is written whole before the log; every clean feed carries, from the alert log itself, every alert of the last 24 hours, and an older one until a clean feed carrying it has stood an hour; held and fail-closed feeds keep them for the next clean feed; when the previous feed cannot be read, every alert of the last 7 days is carried. So no run, retry, hold or damaged feed can take an alert away before a mirror that pulls at least once a day sees it (short of a hold of more than 7 days followed by an unreadable feed) | test_seal, test_feed_alerts, fire_drills |
| 5. Timing | Clocks ahead or behind; midnight UTC and 1 January; a run before today's candle exists; a page left open | Freshness: today's daily bar and the current 4H bar must exist; stack_live.py fails without today's bar, and when a derivatives or put/call series' read column ends further behind than its normal lag (`fetch.MAX_LAG_DAYS`), which holds the cards back without stopping the job; the seal is refused more than 2 hours old or in the future. Page: every text that depends on the viewer's clock is judged on it: the stale note after 5 hours (hour count kept current) and the daily-close note once 00:00 UTC has passed since the data was written; yearly counts use only full years whose signals have all had their 60 days close | test_fetch_today, test_no_today_bar, test_seal, test_year_end, test_series_cells, test_page_timing, test_per_year |
| 6. Delivery | A file reaching the member's browser cut short, empty, as an HTML error page, or late | The page's strict checks reject anything not well formed; every file starts "loading", and every area that reads a file says "Loading" until it arrives, on every tab (never blank, never "unavailable"); while the chart cannot be drawn, its side panel and the past-signals cloud say the chart's own state; a file that arrives after the member moved on is not drawn | test_feed_damage, test_page_timing |

## The list

`docs/audit/damage_list.csv`: every distinct case the damage auditors tried in rounds 21 to 26, 3,056 in all (2,953
real-life, 103 hand-forged), each with its level (page or pipeline), its family, the round it was first tried and the
expected result. The family column was assigned by keyword from each case's description; 204 cases did not match a
keyword and are marked UNSORTED (they are still on the list).

## How the damage part is counted (from round 27)

- **Clean on damage:** every family's rule holds. Each audit attacks every family with cases of its own invention and
  reports, per family, the cases tried and any that got through.
- **A case that gets through counts against the run**, whether or not it is on the list: getting through means the
  family's rule is broken or has a gap. It is fixed at the rule (not just for the case), a test for the family is added
  or extended, and the case is added to the list.
- **A case that fits none of the six families** is fixed and added to the list (with a new family if needed), but does
  not count against that run.
- **Hand-forged contradictions** (every field valid, the fields contradicting each other) stay hardening: fixed where
  cheap, never counted (Jared, 13 Nov 10:23 ET).

What freezing changes in practice: the target is six rules, not an open list of cases, and every fix is made to the
rule, so the cases a new auditor invents are caught by rules that already exist. It does not excuse a case that gets
through a rule.
