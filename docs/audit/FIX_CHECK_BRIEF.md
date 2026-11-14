# Fix check: brief for the independent agent that checks a round's fixes

Used from round 26 (13 Nov 2026). After each audit round's fixes are made, and before the next full audit, a
separate agent that did not make the fixes checks only what changed. A fix that is itself wrong or incomplete
used to come back as a finding two hours later in the next full audit; this catches it in minutes.

The agent gets: the findings list of the round (the audit reports), the commit range of the fixes
(`git diff <before>..<after>`), and this brief. It may read any file in the repo and run any test.

## What it checks

For every finding:
1. **Fixed at the family level.** The fix covers the whole family the finding belongs to, not only the exact case
   reported. Example: "a candle file cut after a comma passed" is fixed only if every input file, cut at any point,
   now fails (`tests/test_cut_files.py`), not only the file named in the report. If the fix is narrower than the
   family, say which members of the family still get through, and show one.
2. **Tested.** A test in `tests/` fails on the code before the fix and passes after it. Run it on both.
3. **Nothing else moved.** `python3 tests/numbers_check.py` passes, or every change it reports is explained by
   the finding and was approved in the same commit.

For every changed sentence in a document (FEED_SPEC, CARD_SPEC, README, the member-site README,
cloudflare/README, CONTEXT's current-rule sections, and the page's own words):
4. **True against the code.** Cite the file and line that makes it true. A sentence with no code evidence is a
   finding.
5. **Complete.** It does not leave out a case the code handles differently (the "loose" findings of earlier rounds).
6. **No history in a spec.** No "Audit #N", "now", "no longer", "used to", or dated change notes in a spec;
   history belongs in docs/AUDIT_LOG.md.
7. **Wording rules.** Signals, never trades; entry quality only, never a return, strategy result or track record.

## What it reports

One table: finding id, verdict (fixed / incomplete / wrong / untested), evidence (file:line or test name), and for
anything not "fixed", the smallest change that would fix it. Then any changed sentence that fails 4 to 7, with the
code evidence. Under 60 lines. It does not edit the repo.
