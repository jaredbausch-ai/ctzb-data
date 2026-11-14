# Fix check, audit round 29 (damage part)

Independent check of commits 1e331d8 and 637dd67 (after e6f3855) against `analysis/audit29_2026-11-14/broken/`.
The repo was not edited; all runs were on copies in this folder (`after` = HEAD, `before` = HEAD with fetch.py,
feed_live.py, index.html and both site-Worker files from e6f3855). This checks whether damage is caught. It measures
entry quality only and produces no return or track record. Probe scripts: `probe/`.

| Finding | Verdict | Evidence | Smallest change if not fixed |
|---|---|---|---|
| D1 Delivery: BTC chart cut one digit, drawn | fixed | index.html l.345, 945, 952 (`sameCents`); site_worker_template.js l.127 (rebuilt worker identical). test_page_states 49/52 before, 52/52 after; test_site_worker 25/26 before, 26/26 after. My cases: Worker refuses a candle CSV cut by 1, 2 or 3 bytes (BTC and ETH) or padded with a partial row; cut at a line end, or a repeated row, is then refused by the page. Page: ETH live +0.01 not drawn, -0.004 drawn; BTC 2D live entry bar +0.01 not drawn; forming ETH 2D +0.01 not drawn, +0.0049 drawn. Example file: entry close must match exactly (l.1296-1298) | - |
| D2 Malformed: 199 ETH 4H bars deleted | incomplete | Caught: 1 bar from the middle of each 4H/12H file, 30 BTC 12H bars, 2 separate BTC 4H bars, overlapping but different deletions. Passes as it should: the same bars missing from both files (an exchange outage), ETH 4H 2 bars ahead of BTC (a later run), the committed data at today's clock, 14 Nov and 15 Nov. **Gets through:** ETH_4H first 10 bars deleted; ETH_12H last 20 bars deleted (check_fresh checks only the 4H end, and only on the real clock); ETH_4H missing exactly the 3 bars of BTC's own 10 Aug 2018 gap, and BTC_4H missing ETH's own May 2016 gap bars. The rule accepts the other file's gap even when it is only that file's own gap (fetch.py l.436-444). Nothing scores 4H/12H, so no figure moves | fetch.py l.440: do not accept a gap from the other file when it is in that file's own OWN_GAPS. Also require each 4H/12H file to start at a fixed first bar, and to end on the same bar as the other asset's file |
| D3 Timing: series row after today | fixed | fetch.py l.282-284, 375-376; test_input_files 2/56 before, 56/56 after. 70 cases of mine (7 series, 1 and 3 days ahead, clock at 23:59:59 and just after midnight, candle check and stack check) all caught, and a row dated the clock's own day passes. In 149 commits of the 7 series, none ran past its commit's UTC day. Replays only: a series whose first day is after the run's day is skipped whole, so rows after the run's day get through if that series was left uncut (2021-03-15 replay with ETH_oi uncut: candle check and stack check both clean) | (optional) fetch.py l.344 and 349: skip only when the file has no data rows |
| D4 Malformed: blank line in funding | fixed | fetch.py l.196-206. 105 cases of mine (21 files x 5 forms: CRLF blank after the header, blank first line, tab-only, blank second-to-last, commas only): all caught; the old code let 42 through. The scoring steps read no data file that the history check does not read. The old code also had this: a blank first line in a funding file raises AttributeError (fetch.py l.181) instead of reporting a problem. The step still exits non-zero | - |
| D5 Missing: lost feed + cut log re-emitted | incomplete (one case now worse than before) | Fixed: feed lost with the log cut, cut mid-row, emptied, deleted or holding a repeated row; a run killed between feed and copy, or copy and log, with or without the feed lost; a held run in between; an older copy holds the run until it is put right. No alert was sent twice in any of these (sender model: `deliver()` in test_feed_alerts, which skips `alerts_withheld` and sends each alert_id once, as ctzb-dashboard-worker.js l.197-207 does). **Gets through:** (a) feed lost (never pulled) and the copy damaged in a way that keeps every alert_id (one row's emitted_at altered, or a row repeated), with the log whole: the good log is overwritten from the copy. The altered alert falls outside the 7-day carry and **is never delivered**; old code delivered it. Cause: when the copy is the record, `sha(bk) == want` is always true and only alert_ids are compared (feed_live.py l.211-222). (b) feed lost, copy deleted and log cut: the cut log is accepted and the alert is re-emitted (FEED_SPEC documents this). (c) a run killed between feed and copy, then the feed lost: the alert is re-emitted with a new emitted_at. In (b) and (c) the sender still sends it once | feed_live.py l.214-220: when the copy is the record, restore only when the copy repeats no alert_id and every log row (the whole row) is in the copy; otherwise fail closed. I tried this on a copy: test_feed_alerts 62/62, and case (a) is held back |
| Hardening: held feed shows record and filter | incomplete | Filter and record count are fixed (index.html l.596, 1282). Still read from a held feed: index.html l.1163, where `recSum` uses `S.feed.grade_odds` without checking `cards_withheld`. The Past signals tab shows "Past signals unavailable right now" next to "ETH · 104 signals · Rose 10% in 60 days 86% · ...". The test checks only the count line (test_page_states l.203) | l.1163: add `!S.feed.cards_withheld &&`, and extend the test to the summary boxes |
| Numbers baseline re-approval | fixed (claim holds) | numbers_check on HEAD: 13 dates unchanged. Old code with the new replay cut reproduces the new baseline exactly for the 8 dates from 2023-12-31. The 5 earlier dates need the first-day skip, and old code with only that skip added reproduces them too. So the moved figures come from the cut alone. Live pipeline: the new code adds checks and one bookkeeping file. The 14 Nov 08:14 UTC live feed was built by the new code; its `alert_log` matches the log, and the copy is byte-identical to the log | - |

Also run on HEAD: test_series_cells 40/40, test_check_candles 95/95, test_dashboard_alerts 21/21, fire_drills 58/58.

## Changed sentences that fail (details in failing_sentences.csv)

FEED_SPEC: 5 sentences fail. Other files: 6.

1. **FEED_SPEC l.109** (#4): "null ... on a held-back feed with no last record and a second copy". Only the fail-closed
   feed nulls it (feed_live.py l.698-699). A held feed (a failed step) writes the record "as usual" (l.604-605): a
   held run with the feed lost wrote `{rows: 62}`.
2. **FEED_SPEC l.322** (#5): "Every run also keeps `feed/alert_log_backup.csv`". A fail-closed run (l.679-) and a run
   with no log (l.609, `final_log is not None`) do not write it.
3. **FEED_SPEC l.325-326** (#5): "Anything else fails closed, including a log holding an alert the copy lacks ... (the
   copy is then the damaged file)". A damaged copy that keeps every alert_id replaces a whole log (D5 (a)).
4. **FEED_SPEC l.404** (#5): "with no bar missing". Bars missing at the start or end of a 4H/12H file are not checked,
   and a gap that matches the other asset's own gap passes (fetch.py l.436-444).
5. **FEED_SPEC l.412-413** (#4/#5): "a series is not read on a day before its first day". stack_live.py still reads
   the file (l.177-179). Only the check skips it (fetch.py l.344, 349), and with it the "no row after today" rule.
6. **AUDIT_LOG l.1031** (#4): "The page now reads neither from a held feed". `recSum` still shows grade_odds (index.html
   l.1163).
7. **AUDIT_LOG l.1009**, **DAMAGE_LIST l.15** (family 2) and the **fetch.py docstring l.314-315** (#5): "no bar missing
   from a 4H or 12H file". This is incomplete, as in item 4.
8. **DAMAGE_LIST l.14** (family 1) (#5): "restored from its second copy when that drops nothing it holds, and fails
   closed otherwise". With the feed lost and the copy missing, a cut log is accepted (l.192-197). A damaged copy can
   replace a good log (D5 (a)).
9. **feed_live.py docstring l.176-177** (#4): "send its lost alert again". The old behaviour re-emitted the alert, but
   the sender's alert_id dedupe stopped a second message (audit D5).

The other changed sentences check out against the code: cloudflare/README, member-site README, FEED_SPEC page and
ledger rules (l.488, 492, 496, 500-501), the FEED_SPEC Order bullet and fail-closed `alert_log` sentence,
DAMAGE_LIST families 5 and 6 and their tests, the replay_at.sh and numbers_check.py comments, the site Worker
template comment, the page's new comments, the OWN_GAPS comment against the committed gaps, and the damage-list
count (44 added rows, 3,100 total). No history notes were added to FEED_SPEC, and every changed sentence follows
the wording rules.
