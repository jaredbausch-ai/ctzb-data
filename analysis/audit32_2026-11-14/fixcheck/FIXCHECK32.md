# Fix check, audit round 32

Commits checked: 4436766, 3f84df3, 2626c6a, 643f1cd (4178753..HEAD, not the Action's). Nothing in the repo was edited;
all runs were on copies in this folder. Scope: entry quality only. These are computed signals, not trades or fills;
the data has no exits, so nothing here is a return or a track record.

| Finding | Verdict | Evidence | Smallest change that would fix it |
|---|---|---|---|
| L1: family 2, a top-grade ledger row's `dipBeforeHigh` blank or a space was accepted | fixed | index.html:554 `numText(r.dipBeforeHigh)`. Every column the page reads now passes a text check before any `+`: entryPrice, bestMove, maxDrawdown, dipBeforeHigh and return60d use `numText` (:550), daysToHigh uses `/^\d+$/`, and asset, chart, entry, reached10/20 and grade are compared exactly. `l1_after.csv`: 204 of 204 as expected. That covers 6 numeric columns x 12 values (blank, space, tab, +5, 5., .5, 1e1, NaN, Infinity, 0x10, leading space, trailing space) and 6 text columns x 5 values. Each was tried in a top-grade row (Past signals unavailable) and in a grade-C row (still shown, "137 signals"). Old page: 5 got through, all dipBeforeHigh (blank, space, tab, leading or trailing space). test_page_states: 52/53 on the old page, 53/53 now | none |
| A1: families 4 and 1, the log cut while the feed and the copy were lost, accepted, and lost alerts emitted again | **incomplete** | Fixed when the copy is lost or unreadable. Across 36 combinations (the feed lost, empty or garbage; the copy lost or garbage; the log cut, emptied, header only, whole, deleted or an older copy), each run twice: rc 1 both times and the log is untouched. The withheld feed has `alert_log` null and `alert_log_carry` [], and `alerts_held` is drawn from the log on disk ([forming, vanished] when the log is whole; [forming] when cut or older; [] when it is gone). Putting the copy back: clean in 36/36, the log byte-identical, nothing emitted again. Putting the feed back: clean for whole, cut and older logs. **Gets through: the copy emptied (0 bytes).** feed_live.py:188 takes `b""` as a record of an empty log, and :201/:226 accept or restore it. With the feed lost, empty or garbage, the copy emptied and the log deleted, emptied or header-only, both runs are clean (9/9 combinations). 2 log rows (forming, vanished) are dropped, and all 36 confirmed signals in the log are emitted again with a new `emitted_at` (same `alert_id`). Putting the copy back afterwards does not repair it, because the damaged log is now the record. This is the same on 4178753 (a gap the fix leaves, not one it caused). `a1_after.csv`, `a1_after.log` | In `check_log`, after line 185: `if bk is not None and not bk.startswith(log_bytes([])): bk = None` (a copy without the log's header line is lost). Add that case (feed lost, copy emptied, log deleted, run twice) to test_feed_alerts |
| A1 test | tested | test_feed_alerts: 67/69 on 4178753, 67/69 on 4436766 (the second run was accepted), 69/69 now. Its "nothing re-sent" uses a sender that drops repeated alert_ids, so it would not show a re-emission. The fix rests on rc 1 and the log being untouched | none |

Not moved: numbers_check "13 dates ... identical to the baseline"; test_seal 29/29; fire_drills 58/58; test_page_states
53/53; test_feed_alerts 69/69. Not run: test_feed_damage, build_audit_states.sh.

Legitimate states, none of which fails closed (`a1_after.log`, LEGIT lines):
- two clean runs;
- a held run, then clean;
- a fail-closed run, then clean;
- the feed killed after publishing, before the copy and the log;
- the feed killed after the copy, before the log;
- the feed lost alone;
- the copy lost alone;
- the log cut alone.

`check_log` (HEAD code) accepts the committed `feed/` of all 23 commits from 1e331d8 (the copy's introduction) to HEAD
(`commits_check.md`). The 97 commits from 4aa1208 that come before the alert-log record existed (all earlier than the 49 that pass) now fail closed. The rule
intends that.

Fixture change (tests/fire_drills.py:403-405, tests/build_audit_states.sh:18-20): the 4aa1208 feed has no `alert_log`
key and its tree has no copy (checked). With the old drills file and the new code, the drills score 53/58. The 5 that
fail are the ones that expect a clean run (B control, B extras crash, C held alert out once, C vanished, E control).
Each fails closed at `check_log`. The B crash drills then passed for the wrong reason: the run was withheld by
`check_log`, not by the crash. Giving the fixture its copy (equal to its log) hides no drill check. Nothing in the
drills tested a fixture with no record.

Beyond the brief's list (`a1_after.log`, "extra" rows): with the feed lost and the copy cut or older, while the log is
deleted, emptied or damaged the same way, the run is clean and the `vanished` alert is emitted again (10 of 12). The
files cannot show this, because the rule makes the copy the record. The cause is the mirror of A1's counted case. It is
why the DAMAGE_LIST qualifier must stay (below).

## Changed sentences that fail (details and code in failing_sentences.csv)

FEED_SPEC: 2 of 3 changed sentences fail. DAMAGE_LIST: 2. AUDIT_LOG Round 32: 1. feed_live.py: 3 (comments and
message). test_feed_alerts: 1. The others are true: FEED_SPEC:109; the index.html, test_page_states, fire_drills and
build_audit_states comments; the rest of Round 32 (52/53, 67/69, 53/58 and 56 cases all checked); DAMAGE_LIST's family
2 and 4 rule and test claims. No spec sentence carries history, and no sentence breaks the wording rules.

1. FEED_SPEC.md:330-332 "With no previous record and no copy ... fails closed whether the log is there or not, until
   the feed or the copy is put back from the last commit". There are three problems:
   - An emptied copy is a copy (feed_live.py:188), so a 0-byte copy and a deleted log run clean.
   - Putting the feed back alone does not end the hold when the log is deleted, emptied or header-only. It fails
     closed again at :227 (18/18).
   - "From the last commit" does not work in the pipeline. The feed step has continue-on-error (daily.yml:166), and
     the commit step runs `git add ... feed/` (:199). The last commit therefore holds the withheld feed
     (`alert_log` null, feed_live.py:721) and no copy.
2. FEED_SPEC.md:375-377 "with no copy stays held until the feed or the copy is put back". This has the first two
   problems of item 1.
3. DAMAGE_LIST.md:14 "With both the previous feed and the copy lost, the run fails closed whether the log is whole or
   not." It leaves out the emptied copy, which family 1 itself counts as lost.
4. DAMAGE_LIST.md:14 "No alert is dropped from the log or emitted twice." This is false. With the feed lost, the copy
   emptied and the log deleted, 2 rows are dropped and 36 alerts are emitted again. With the feed lost and the copy
   and log cut alike, `vanished` is emitted again. The old qualifier ("Short of the feed, the copy and the log all
   damaged at once") was removed and is still needed.
5. AUDIT_LOG.md:1214-1216 "Rule now: ... until the feed or the copy is put back from the last commit". This is item
   1's sentence.
6. feed_live.py:192-195 comment: "no readable previous feed and no second copy ... fails closed until the feed or the
   copy is restored". This branch is also reached with a readable withheld feed whose `alert_log` is null, on every
   second run of a hold. Restoring the feed alone does not end the hold when the log is gone.
7. feed_live.py:199-200 message "restore feed/ctzb_feed.json or feed/alert_log_backup.csv from the last commit". This
   is item 1's last-commit problem.
8. feed_live.py:717-719 comment "with no copy either it stays held until the feed or the copy is put back". This is
   item 2.
9. tests/test_feed_alerts.py:237-238 "Now the run is withheld until the feed or the copy is put back". This is item 2.
   The test only puts the copy back.
