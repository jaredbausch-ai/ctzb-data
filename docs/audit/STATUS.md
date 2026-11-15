# Audit status and procedure

Read this first, before starting or resuming any audit round. The chat that runs the audits forgets; this file and
the files it points to do not. Update the "Where we are" section at the end of every round.

## Where we are (15 Nov 2026, 09:25 ET)

- **Clean rounds in a row: 0 of 2.** The site (`ctzb-site`, still on deploy 656d67c3) is redeployed only after two
  clean rounds in a row.
- **Round 36** (code frozen at 2d856f7): numbers part 0 disagreements; docs part 10 counted, all corrected in 9c177ca,
  so round 36 is not clean; damage part still running.
- **Next:** when round 36's damage part reports, fix any counted cause, run a fix check, then start round 37 on the
  new frozen code.
- Findings per round, docs passes: 24 (round 34), 21 (round 35), 10 (round 36). Damage: 1 (35); numbers: 1 (35), 0 (36).

## What "clean" means (Jared, 13 Nov 2026)

A round is clean when all three parts come back at zero counted findings:

| Part | Counts | Does not count |
|---|---|---|
| Numbers | any figure or label on the page or in the feed that disagrees with a recomputation from the raw candles | — |
| Damage | a real-life damage case that gets through its family's rule (`DAMAGE_LIST.md`, six frozen families) | hand-forged contradictions ("hardening"); a new case outside the families (added to the list, not counted) |
| Docs | a sentence that disagrees with the frozen code in: the member page's words, FEED_SPEC, CARD_SPEC, README.md, the member-site README, `cloudflare/README.md`, CONTEXT's current-rule sections | everything else (docstrings, comments, test headers, BRIEFs, PRETRADE, SITE_CHANGES): reported "outside scope", fixed anyway |

## Procedure for one round

1. **Freeze.** Note the HEAD commit. Build the states: `bash tests/build_audit_states.sh <dir>` (a replay of 12 Nov
   04:14 UTC and today's data) and `bash tests/replay_at.sh 2026-11-11 <dir>/replay_1111 2026-11-11T04:14:00Z`.
2. **Brief.** Copy the three briefs in `docs/audit/briefs/` (numbers, damage, docs), fill in the round number,
   the state folder, the frozen commit and today's state (forming setups, build time).
3. **Run.** Three independent agents at once (opus, background), each told to read only its brief. They must not
   read earlier audit reports or AUDIT_LOG: independence is the point. The machine has 2 cores; the briefs say so.
4. **Fix.** For each counted cause: fix it at its family's rule (not just the case), add a test that fails on the
   old code, run the suite (below), commit and push. Correct every docs finding, counted or not.
5. **Fix check.** An independent agent checks the fixes and the corrected sentences (`FIX_CHECK_BRIEF.md`;
   `briefs/fixcheck_example.txt`). Correct what it finds.
6. **Record.** Archive each report to `analysis/audit<round>_<date>/` (numbers, broken, docs, fixcheck); append the
   round's damage cases to `damage_list.csv`; write the round in `AUDIT_LOG.md`; update "Where we are" above.
7. **Next round** on the new frozen code. Two clean rounds in a row ends the loop.

The suite (after every change): `tests/numbers_check.py` (must say numbers unchanged; if a change moves the
baseline, prove with a field-by-field diff that only the intended wording or field moved, then `--approve`),
`test_midnight`, `test_seal`, `test_feed_extras`, `test_feed_alerts`, `test_page_states`, `fire_drills`,
`test_year_end`, `test_gate_off.sh`, `test_no_today_bar.sh`, `test_page_timing`, `test_per_year`, the six Worker
`.mjs` suites, and `test_feed_damage` (quick pass: `RENDER_LIMIT=40 REJECT_LIMIT=10`).

## Where everything is

| What | Where |
|---|---|
| Every round, its findings, fixes and re-checks | `docs/AUDIT_LOG.md` |
| The six damage families, each family's rule and tests | `docs/audit/DAMAGE_LIST.md` |
| Every damage case ever tried that got through, or was hardening | `docs/audit/damage_list.csv` |
| The audit briefs | `docs/audit/briefs/` |
| The fix-check brief | `docs/audit/FIX_CHECK_BRIEF.md` |
| Each round's reports | `analysis/audit<round>_<date>/` |
| Page changes waiting for the deploy | `docs/SITE_CHANGES.md`, Pending |
| The rules the audits check against | `docs/FEED_SPEC.md`, `docs/CARD_SPEC.md`, `CONTEXT.md` |

## Parked (do not raise)

Member alerts (R3); the deploy until two clean rounds; the three earlier open decisions; R1/R2 site requests;
making the repo private; data licences; CFTC Q16-18; customer service backend; the relay going live (Noah's
sign-off, then Jared's switch).
