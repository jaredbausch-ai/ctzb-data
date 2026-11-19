# Audit status and procedure

Read this first, before starting or resuming any audit round. The chat that runs the audits forgets; this file and
the files it points to do not. Update the "Where we are" section at the end of every round.

## Where we are (18 Nov 2026, 15:20 ET)

- **Clean rounds in a row: 0 of 2.** The site (`ctzb-site`, still on deploy 656d67c3) is redeployed only after two
  clean rounds in a row.
- **Round 38** (damage and docs only, code af13e4c): damage 1 (left-open page wording, fixed in 590706c), docs 1
  (fixed in 53ec2a7), so not clean.
- **Round 39** (damage and docs only, code 465e385): damage 1 (alert log, family 4, fixed with a test), docs 0, so
  not clean.
- **Round 40** (damage and docs only, code 5e52cba): damage 0, docs 1 (kind 1, README max-safe sentence, fixed in
  452cbd6; plus a borderline kind 4 Jared has not ruled on), so not clean. The first damage part at zero since 36.
- **Round 41** (damage and docs only, code 01f3976): damage 0, docs 0. **Clean.**
- **Round 42** (damage and docs only, code 8d944e4): damage 1 (CR CR LF line ends, family 2, fixed with a test), docs 0.
- Counted per round: docs 24 (34), 21 (35), 10 (36; 3 on the new rule), 1 (37), 1 (38), 0 (39), 1 (40), 0 (41), 0 (42); damage 1 (35),
  0 (36), 1 (37), 1 (38), 1 (39), 0 (40), 0 (41), 1 (42); numbers 1 (35), 0 (36), 0 (37).

## The plan from round 41 (Jared, 18 Nov 15:35 ET)

- **Segmented.** Numbers already has two clean rounds in a row (36, 37) and is not re-run for now. Rounds run the
  damage and docs parts only until **both** have two clean rounds in a row. Then the full system (all three parts) is
  run again.
- **Docs: done** (clean in rounds 41 and 42). **Damage: 0 of 2** (41 clean, 42 not). Rounds 43 and 44 are left in
  the cap; damage needs both clean.
- **Fewer new sentences.** During this segment only counted causes are changed: damage causes, and docs findings of
  kind 1, 2 or 4, each with the smallest change. Loose wording (kind 3) and outside-scope findings are recorded in
  `docs/audit/loose_wording.md` and corrected together at the end, because every rewrite is new text for the next
  round (round 40's counted docs finding was a sentence written in round 39 to fix a loose one).
- **Every change checked before the next round.** Each changed sentence and each code fix gets an independent check
  (the fix check) before the round that follows it starts, not found during it.
- **Decisions (Jared, 18 Nov 15:46 ET).** The priorities are stale or incorrect data and liability (anything that reads
  as a trade, a return or a track record).
  - **Cap: at most 4 more rounds (41 to 44).** If damage and docs do not have two clean rounds in a row by then, stop:
    Jared gets a short list of what is open and decides whether to launch with it.
  - **Two-fault damage cases** (two separate, independent faults in a row) are recorded and fixed, not counted.
  - **Borderline docs findings** (the auditor calls them borderline) count only if they are in the member page's own
    words and show a wrong or stale figure or read to a member as a trade, a return or a track record; otherwise they
    are fixed, not counted.
  - The damage and docs briefs say this.

## What "clean" means (Jared, 13 Nov 2026)

A round is clean when all three parts come back at zero counted findings:

| Part | Counts | Does not count |
|---|---|---|
| Numbers | any figure or label on the page or in the feed that disagrees with a recomputation from the raw candles | — |
| Damage | a real-life damage case that gets through its family's rule (`DAMAGE_LIST.md`, six frozen families) | hand-forged contradictions ("hardening"); a new case outside the families (added to the list, not counted) |
| Docs | in the member page's words, FEED_SPEC, CARD_SPEC, README.md, the member-site README, `cloudflare/README.md` and CONTEXT's current-rule sections, a sentence that is a wrong figure or label (kind 1), stale (kind 2), or reads as a trade, a return or a track record (kind 4) | loose or incomplete wording (kind 3), fixed anyway (Jared, 15 Nov 09:31 ET: "as long as the wording is pretty close"); everything outside those documents (docstrings, comments, test headers, BRIEFs, PRETRADE, SITE_CHANGES): reported "outside scope", fixed anyway |

## Procedure for one round

1. **Freeze.** Note the HEAD commit. Build the states: `bash tests/build_audit_states.sh <dir>` (a replay of 12 Nov
   04:14 UTC and today's data) and `bash tests/replay_at.sh 2026-11-11 <dir>/replay_1111 2026-11-11T04:14:00Z`.
2. **Brief.** `python3 docs/audit/make_prompts.py --round N --parts damage,docs --scratchpad <dir> --today ...
   --built ... --forming ...` writes the prompts from the briefs in `docs/audit/briefs/`, with the frozen commit
   taken from HEAD, and refuses when the repo has uncommitted changes or a prompt keeps any placeholder, another
   commit or another round's number (round 40's docs prompt, edited by hand, kept round 39's commit, so the docs
   were checked against the older code and the difference had to be checked separately).
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
