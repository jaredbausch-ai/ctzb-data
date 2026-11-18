# Audit 40e: delta sentences at 5e52cba (diff 465e385..5e52cba)

Read-only copy at 5e52cba; sims `sim_copy_ahead.py`, `sim_e.py`. Entry quality only: no fill, exit or strategy return.
## 1. docs/FEED_SPEC.md:331-334 (copy ahead of the log). Right for the case it names; 3 findings (kind 3)

Code: check_log's match branch (feed_live.py:228-245) restores the log from the copy when the copy is longer and starts
with the log's bytes, and fails closed if its rows repeat an alert_id or cannot be decoded. Write order is feed (659),
copy (662-664), log (667-669), as the sentence and the Order bullet (FEED_SPEC:348) say.

| case | result |
|---|---|
| A: feed + copy written, died before log; feed alone put back | clean; log restored; alert keeps first emitted_at |
| B: copy alone put back to an older run's | clean; log unchanged; copy rewritten |
| C: feed AND log put back, copy not (run had finished) | log restored; not re-emitted |
| D: case A, then the restoring run fails closed (strict check) | log restored (41 rows), fail-closed record still 40; next 2 clean runs fail closed: "41 rows on disk, 40 expected" |
| E: copy ahead with an undecodable row, no repeat | fails closed; log untouched |

- F1 (332-333) "ahead of both only when a later run died between the copy and the log and its feed was then put back":
  "only" is too strong; case C (or a later copy restored) reaches the same state, handled the same way.
  Suggested: "the copy is written before the log, so it is ahead of both when a later run wrote it and the feed (or
  the feed and the log) was then put back to the run before's, most often because that run died between the two."
- F2 (334) "a copy ahead of the log that repeats an `alert_id` fails closed": also fails closed when its rows cannot
  be decoded (feed_live.py:236-242; case E). "Otherwise" in the next sentence now reads off the fail-closed clause.
  Suggested: "...that repeats an `alert_id` or cannot be read as rows fails closed. When the log does not match the
  record, it appends the previous feed's..."
- F3 (333-334) "The log is then restored from the copy, so the later feed's alerts are not emitted again": the
  restore is written at the run's start (check_log, called at feed_live.py:485), before its checks. If that run then
  fails closed, its feed keeps the older record (feed_live.py:766) and every later run fails closed (case D); the
  section does not say so. (The rebuild and the other restore write a log equal to the record, so they are safe.)
  Suggested, appended: "The restored log is written when the run starts; if that run then fails closed, its feed
  keeps the older record, and later runs fail closed until the log or the feed is put back by hand."

## 2. README.md:88 (datasets the dashboard reads; maxsafe). 1 finding (kind 1)

The nine files match the shim (cloudflare/dashboard_shim.js:15) and the page (eth-setup-standard.html:386, 400,
411-414); all exist in datasets/; no pipeline script writes maxsafe. But maxsafe is computed in the page:
`dash.calc("maxsafe", {inputs: ["grades"]})` (eth-setup-standard.html:245-247), run by the shim after loading
(dashboard_shim.js:66-72, also in the built ctzb-dashboard-worker.js). Today's column: A+ 6.29x, A 5.00x, B 4.93x,
C 4.67x. "so its max-safe column stays empty" is wrong.
- F4 Suggested: "...`prints` and `windows`; its max-safe column (`maxsafe`) is worked out in the page from `grades`
  (1 / (|medDip|/100 + 0.05) for each ETH grade), so no pipeline step writes it."

## 3. docs/artifacts/member-site/README.md:17 (what the page types). Every listed item right; list incomplete, 2 findings (kind 3)

Present as listed: +10% (index.html:1065), +20%/-30% tiles (787-788), day 10 (815, 1165), 25.3% (295), ladder (425),
cloud range (1123), fallback zones (1049), 2-day example bars (955), 2020 (873), example date/id (519, 1345), 10 bars
(965, 1342), 5 hours (612), 00:00 UTC (637), 5 minutes (548), six trades (845), five signals (890), four phrases
(288/743, 727, 838/842, 288).
- F5 Typed, not listed: the 2022 era split ("Before 2022"/"Since 2022", 675, 796-797); "every signal from 2016"
  (815); the 1 January restart of 2D+ bars, short last bar on 31 December, used by the chart-file check and day lines
  (557-560, 859-866); "reload for each 4-hour update" (230). Suggested addition: "the era split at 2022, 2016 as the
  first year of the odds-fade table, the 1 January restart of 2D+ bars (a year's last bar can be short), the 4-hour
  update named under Previous signals".
- F6 "four phrases of plain description": seven. Missing "a few candle closes" (287), "several independent
  confirmations" (289), "shortly after each close" (638). Suggested: "seven phrases of plain description (the four
  above, plus "a few candle closes" for how long a setup holds before it confirms, "several independent
  confirmations" for what a setup is checked against, "shortly after each close" for when the data updates)".

Count: kind 1: 1 (F4); kind 2: 0; kind 3: 5 (F1, F2, F3, F5, F6); kind 4: 0.
