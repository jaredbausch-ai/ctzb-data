# Audit headline numbers (as of 19 Nov 2026, 16:50 ET; after round 46)

Counted from the archived reports in `analysis/audit*/`. Entry quality only: everything audited is computed signals
and the pipeline and site that publish them. None of it is a fill, a trade record or a strategy return.

| What | Figure | Source |
|---|---|---|
| Audit rounds run | 46 (since 12 Nov 2026) | `docs/AUDIT_LOG.md` |
| Numbers: all four clean numbers rounds (36, 37, 45, 46) | 25,580,388 comparisons over 1,464 real-date replays, 0 disagreements | the three below plus round 46: 53,320 + 7,904,894 (`AUDIT46_NUMBERS.md`) |
| Damage: checks run, rounds 22 to 46 | 33,877 | the 33,064 below plus round 46's 813 |
| Docs: statements checked, 14 rounds | about 11,760 | the 10,750 below plus round 46's about 1,010 |
| Round 46 | numbers 0, docs 0, damage 2 (no figure changed; one fixed, one open) | `analysis/audit46_2026-11-19/` |
| Full clean rounds (numbers, damage and docs together, 0 counted findings in each) | 1 (round 45) | `analysis/audit45_2026-11-19/` |
| Numbers: published figures compared with an independent recomputation from the raw candles, in the three clean numbers rounds (36, 37, 45) | 17,622,174 comparisons, 0 disagreements | round 36: 5,749,424; round 37: 4,952,132; round 45: 53,299 + 6,867,319 (`AUDIT36/37/45_NUMBERS.md`) |
| Numbers: real-date replays in those rounds | 998 (328 + 270 + 400), from 1 Sep 2020 to 14 Nov 2026 | same |
| Numbers: the round 45 checker's self-test (errors planted on purpose) | 44/44 data and 15/15 page plants caught | `AUDIT45_NUMBERS.md` |
| Damage: checks run (page and pipeline), rounds 22 to 45 | 33,064 | rows of `broken/all_checks.csv(.gz)` in 23 archived rounds |
| Damage: real-life cases in round 45 | 1,095, 0 got through | `AUDIT45_BROKEN.md` |
| Docs: statements checked against the code, in the 13 rounds that counted them | about 10,750 | the docs reports (each an estimate by its auditor) |
| Docs: statements in round 45 | about 850, 0 counted findings; all 298 feed fields matched to the spec | `AUDIT45_DOCS.md` |
| Automated test cases run after every change | 445 | the suite (`docs/audit/STATUS.md`) |
