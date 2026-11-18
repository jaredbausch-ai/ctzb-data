# Fix check 40: 5e52cba..452cbd6 (read-only copy at fixcheck40/repo)

Entry quality only: an alert is a computed signal, not a fill, an exit or a strategy return.

## 1. Code: feed_live.py check_log / record_prefix. Verdict: RIGHT

At the rule level: a copy counts as ahead only when it is intact (its end line checks), its hash differs from the record, a proper whole-row beginning of it hashes to the record, and the log on disk (or nothing, if the log is missing) is a beginning of it. A copy is only written after a feed that records the same bytes, so a copy ahead always holds rows that a published feed recorded. The check depends only on (record, copy, log), not on how the restoring run ends, so a restore followed by a fail-closed run is accepted again on the next run. Tests: `tests/test_feed_alerts.py` 89/89, `tests/fire_drills.py` 58/58. Own harness: `fixcheck40/cases.py` and `cases2.py`, which run feed_live.py on a copy of datasets/ with CTZB_NOW and reseal, followed by 3 clean runs. Output is in `cases.out`, `cases_out.json` and `cases2_out.json`.

| Case | Result | Alert lost / re-stamped / twice? | Locks up? |
|---|---|---|---|
| (a) feed+copy written, died before log, feed alone put back (sender saw / missed the later feed) | log restored from copy; restored alerts carried with their first emitted_at | none / none / none | no |
| (b) as (a), restoring run fails closed on the strict check, then clean | fail-closed feed keeps old record; next run sees copy ahead again, accepts | none | no |
| (b2) as (a), two fail-closed runs, then held, then clean | as (b) | none | no |
| (b3) as (b) with a new card pending in the failing run | new alert emitted once on the next clean run | none | no |
| (c) feed and log put back, copy not (also after a fully clean run) | restored from copy | none | no |
| (d) copy alone put back to an older run's | copy behind: log matches record, copy rewritten at end of run | none | no |
| (d2) (d), then a run dies after copy and its feed is put back | restored | none | no |
| (e) copy ahead, a row the record also holds altered, copy re-sealed by hand | not "ahead" (record not a beginning): log accepted, later feed's alert re-emitted | re-stamped (same alert_id, so a dedup sender does not send twice) | no |
| (e') copy ahead, its extra row altered and re-sealed | restored as written: the altered alert_id replaces the real one | the real alert_id is never logged or sent (forged copy) | no |
| (e'') copy ahead, a byte altered without re-sealing | copy reads as lost: log accepted, alert re-emitted | re-stamped | no |
| (e''') copy same length as log, one row altered, re-sealed | log accepted, copy rewritten | none | no |
| (f) copy ahead, log cut by whole rows / cut mid-row / emptied | restored from copy | none | no |
| (g) copy ahead, log missing | restored from copy | none | no |
| (h) copy two runs ahead (feed+log two back; feed two back, log one back; feed one back, log two back) | restored | none | no |
| (h4) feed two back, copy one back, log current | copy behind the log, log not the record: fails closed, as it did before the change | none | yes, until put right by hand (damage, not a legitimate state) |
| (h5) feed alone put back after a clean run | copy == log, record a beginning: accepted (failed closed before the change) | none | no |
| (i) two clean runs; held then clean; fail-closed (strict, or open.csv gone) then clean; killed before copy; after copy; after log; killed after copy, then fail-closed, then held; killed before copy, then fail-closed; held run writes copy | all pass, no unexpected fail-closed | none | no |

Notes:
- The (e) rows need the copy to be damaged as well as the feed put back; the end line catches damage that is not hand re-sealed. The alert_id stays the same, so it is not sent twice. Optional hardening: fail closed when the copy is longer than the log but does not begin with it.
- A restored row from the later feed is carried only within ALERT_HOLD_HOURS (24 h) of its emitted_at, because the old feed's chain does not hold it. If no sender pulled the later feed and the put-back is found more than 24 h later, the alert is logged but never sent. This was checked on `carried_alerts` directly. End-to-end replay is blocked because the strict check ties the feed to the data's day.

## 2. Sentence findings (kinds: 1 wrong figure/label, 2 stale, 3 loose/incomplete, 4 reads as a trade/return/record)

1. **Kind 3, docs/FEED_SPEC.md:333-334.** The text says the copy is ahead when the feed "was then put back to the run before's". Cases (h) show the same restore when the feed (and log) is put back two or more runs. Suggested: "...was then put back to an earlier run's (most often the run before's, because that run died between the copy and the log)."
2. **Kind 3, docs/FEED_SPEC.md:334-335.** The text reads "When the log on disk is the copy or a beginning of it, the log is restored". The code (`lb = ... if have else b""`) also restores when the log is missing, as in case (g). Suggested: "When the log on disk is missing, the copy, or a beginning of it, the log is restored from the copy..."
3. **Kind 3, feed_live.py:239-242 (comment).** The comment says "this happens only when ... put back to the run before's" and "(when the log on disk is the copy or a beginning of it)". The same two gaps apply: any earlier run's feed, and a missing log is also restored. Suggested: "...this happens only when a later run wrote the copy and the feed (or the feed and log) was then put back to an earlier run's... the log is restored from the copy (when the log is missing, is the copy, or is a beginning of it)..."
4. **Kind 3, README.md:76-77.** "when each forming low would confirm (`buy.csv`'s `buyDate`...)" is too broad. refresh.py `ds_buy` lists a forming low only if one of its tags is a walk-forward tier setup with at least 4 scored signals (`if not best: continue`). Rows whose date has passed read "Needs fresh data". Suggested: "...and, for each forming low that matches a tier setup, the date it would confirm (`buy.csv`'s `buyDate`: a computed date, not a planned buy)."
5. **Kind 3, .github/workflows/daily.yml:126.** "from this run's ledger and candles" leaves out a source. The odds-fade marks come from refresh's `earlydip.csv` and `holdcheck.csv` (extras_live.py through carddesign.fade), not from the ledger or the candles. Suggested: "...the odds-fade marks and the chart candle files, from this run's ledger, early-dip and day-10 tables and candles."

Checked with no finding:
- README.md maxsafe sentence: the formula and "ETH grade" match eth-setup-standard.html:245-247, and no pipeline step writes maxsafe.
- cloudflare/README.md: the scheduler header says v3, 11 Nov, and `/health` returns `version: 3`.
- PRETRADE.md:342,356 and grade_live.py:8: GAP is `ct - signal > 5`, which matches "more than 5 points above its Signal line".
- seal.py:31-32: `check()` ignores extras files when extras did not finish, and `remove_extras_files` covers every file in EXTRAS_FILES.
- daily.yml:127-128: extras failing does not withhold cards or alerts; files are deleted on a published feed and on a fail-closed feed; the page shows "Chart data unavailable".
- member-site README additions: each item and all seven phrases appear in index.html.
- index.html:289: forming setups are graded, and A+ needs 4 or more lenses.
- SITE_CHANGES 6q: old and new wording match the diff, and FUND and FCOOL both read funding.
- No changed sentence reads as a trade, a return or a track record.

Counts: kind 1: 0, kind 2: 0, kind 3: 5, kind 4: 0.
