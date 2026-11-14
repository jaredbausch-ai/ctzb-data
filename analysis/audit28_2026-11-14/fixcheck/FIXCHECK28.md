# Fix check, round 28 (commits 929b713, a489cef; base 551f753)

Independent check. The repo was not edited. All probes ran on copies in this folder. The scripts are in `code/` and
the results are in `alert_probe*.json`, `page_probe.json` and the screenshots `p1_*.png`. This work checks entry
quality only. The data has no exits, so nothing here is a return or a track record.

| Finding | Verdict | Evidence | Smallest change that would fix it |
|---|---|---|---|
| 1-2 Partial run: an alert lost to a red run's 1-minute retry | **incomplete** | Reported case fixed. `test_feed_alerts` fails on the old code (3 FAIL, then KeyError `alerts_held`) and passes 45/45 on the new. My cases that pass: a red run plus 57 retries over 26 h (mirror sees nothing until 25 h 30) gives one send, then the alert drops; held 30 h plus a fail-closed run gives one send; a run that died before the log while carrying a logged alert gives a rebuilt log with no duplicate, with or without a fail-closed run between, and also when it died twice in a row. Still lost: (a) **a fail-closed run while the alert log is unreadable** (header renamed, or NUL bytes). `held_alerts` hits KeyError, catches it and writes `alerts_held: []` (feed_live.py:597-605, :207). After the log is restored, the next clean feed carries nothing (alert_probe.json S3). (b) **A damaged previous feed.** When the previous feed is cut, `prev_feed` is None (:385-389) and `check_log` accepts the log because there is no record, so the window resets 1 minute after emission (S5a). A previous feed with a non-list `alerts_held` makes one run fail closed with `[]`, and the alert is gone (S5b). | Build the carry from the log as well as the previous feed: in `carried_alerts`, also carry every non-seeded log row whose `emitted_at` is under `ALERT_HOLD_HOURS` old, whether or not the previous feed lists it. In `held_alerts`, fall back to `prev_carry(prev)` when the log cannot be read. Add S3 and S5a to `test_feed_alerts`. |
| 3-4 Delivery: Chart and Past signals read "unavailable" while the feed loads | fixed | `test_page_timing` 1b fails on the old code (4 FAIL) and passes 15/15 on the new. My cases: slow feed and slow ledger together on every tab, all "Loading" (the ledger is still "Loading past signals…" after the feed lands). A slow feed that then fails the strict check (cut at 60%, or a wrong-typed field) reads "Data unavailable" or "Feed unavailable." everywhere, with no "Loading" left behind. Clicks while loading (Example button, example switch on and off, BTC filter, tabs) keep "Loading", then resolve to the member's choice. No page errors. | none |
| 5-6 Delivery: picker and Previous signals blank while the feed loads | **incomplete** | Picker ("Loading…" ×2) and Previous signals ("Loading…", "Loading past signals…") are fixed and tested. The family rule (DAMAGE_LIST row 6: "every area that reads a file says Loading … never blank") still fails on the Chart tab. The **"Where the past signals went"** panel (feed `past_paths`, index.html:254-258) shows only its heading while the feed loads, and while a chart file loads, because `blankChart` empties `#cloudSub`, `#cloudSvg` and `#cloudNote` (index.html:905). See `p1_chart_loading.png`. | In `blankChart`, give the panel a line, such as `#cloudNote` set to "Loading…" when the chart message is a loading one, or hide `.cloudbox`. Add `cloudNote` to test 1b's areas. |

**Nothing else moved.** `numbers_check` passes (13 dates unchanged). `alerts_held` was added to the run bookkeeping it
skips, in the same commit, and it holds no figure. Also passed on the current repo: test_seal 23/23, test_page_states
48/48, test_dashboard_alerts 21/21, test_health_monitor 36/36, fire_drills 58/58.

**Limits of the window (not counted):**
- If the mirror pulls nothing for more than 24 h, an alert can leave the feed unsent (S1b).
- A seeding run carries nothing.
- Probes past midnight used a copy with `feedcheck.problems` stubbed. The frozen data fails the strict check
  (`days_elapsed`) after 00:00, so without the stub every later run fails closed. In that state the alert was correctly
  kept in `alerts_held`.

**Hardening (pre-existing trust, now wider):** suppose a previous feed is forged and its `alert_log.sha256` equals the
hash of the log plus a forged row. Then `check_log` appends that row as "died before the log" (feed_live.py:175-181),
and `carried_alerts` now re-publishes it in genuine feeds for 24 h. It was sent (S5c). Before the fix it was logged
but not re-sent.

## Changed sentences that fail checks 4-7 (full list with suggested wording: `failing_sentences.csv`)

**FEED_SPEC: 5 sentences fail.**
- :97 `alerts_held[]` "On a held feed, the alerts it would have carried". It is also on fail-closed feeds. It keeps every alert the last feed carried, whatever its age (`keep_all`, feed_live.py:219, :409), not the alerts a clean feed would have carried. It is empty when the log cannot be read (:604-605).
- :301-303 "An emitted alert is carried in `alerts` for at least 24 hours…". The carry comes only from the previous feed (`prev_carry`, :195-200). A cut or forged previous feed, or a fail-closed feed written with an unreadable log, ends it early (S3, S5a, S5b).
- :303-305 "a feed replaced sooner … is never read; the window means some feed it reads carries every alert". "Never" should be "may never". The guarantee needs the mirror to pull within the window, and it fails in the same cases as above.
- :309-310 "Alerts already emitted are kept in `alerts_held` (held and fail-closed feeds alike) … however long the run was held". This is false for a fail-closed run with an unreadable alert log (:597-605).
- :361 fail-closed "`alerts_held` (the alerts the last feed was carrying)". Only the ones the log records, or the last feed's unlogged alerts, are kept, and the list is empty if the log cannot be read.
- Unchanged but now incomplete: :41-43 "Its own work is: … which alerts are new". It also chooses which alerts are carried (`carried_alerts`).

**Elsewhere:**
- `cloudflare/ctzb-dashboard-worker.js:206`: the comment was changed only in the **built** file. `dashboard_worker_template.js:206` still says "The feed shows an alert for ~4 hours", which is now false. Rebuilding (`build_dashboard.py`, verified on a copy) reverts the fix.
- `feed_live.py:22`: "alerts lists the events of the last day". It lists alerts in their delivery window, which can run past a day and through any hold, and the list is empty on held feeds.
- `feed_live.py:63-67`: "they keep the alerts in `alerts_held`". This has the same exception, the unreadable log.
- `feed_live.py:204-205`: "so a damaged feed cannot add one". A feed whose `alert_log` hash matches the log plus its alerts can add one (S5c).
- `cloudflare/README.md:49`: "an alert stays in the feed at least 24 hours, so a feed the mirror never pulled loses nothing". This is loose in the same way as FEED_SPEC :301-305.
- `DAMAGE_LIST` row 4: "so no run, retry or hold can replace it before the sender reads it". This fails for S3, S5a and S5b. The tests it names (test_seal, test_feed_alerts, fire_drills) do exist and cover the window.
- `DAMAGE_LIST` row 6: "every area that reads a file says Loading … never blank". The cloud panel is blank. The tests it names (test_feed_damage, test_page_timing) are correct.
- `index.html:366` (comment): "each area that reads it says Loading, never … nothing". The cloud panel is blank.
- `AUDIT_LOG` :943, :949: the same two claims as rows 4 and 6.
- `AUDIT_LOG` :963: "its own fixed clock, which ends 04:30 UTC". The test's clock ends at 03:50Z (test_health_monitor.mjs comment), and `/health` goes stale 40 min later (ctzb-scheduler-worker.js:344).

There is no history wording in the FEED_SPEC changes, and no signal/trade or return wording problem in any changed sentence.
