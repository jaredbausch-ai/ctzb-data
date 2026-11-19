# Audit headline numbers (as of 18 Nov 2026, 22:00 ET; round 42 damage still running)

Counted from the archived reports in `analysis/audit*/`. Entry quality only: everything audited is computed signals
and the pipeline and site that publish them. None of it is a fill, a trade record or a strategy return.

| What | Figure | Source |
|---|---|---|
| Audit rounds run | 42 (since 12 Nov 2026) | `docs/AUDIT_LOG.md` |
| Numbers: figures compared with an independent recomputation from the raw candles, in the two clean rounds (36, 37) | 10,701,556 comparisons, 0 disagreements | round 36: 53,892 + 5,695,532; round 37: 56,479 + 4,895,609 + 44 (`AUDIT36_NUMBERS.md`, `AUDIT37_NUMBERS.md`) |
| Numbers: real dates replayed in those two rounds | 598 (328 + 270), from 1 Sep 2020 to 14 Nov 2026 | same |
| Damage: checks run (page and pipeline), rounds 22 to 41 | 24,212 | rows of `broken/all_checks.csv(.gz)` in 19 archived rounds |
| Damage: real-life damage cases in round 41 (clean) | 675, 0 got through | `AUDIT41_BROKEN.md` |
| Docs: statements checked against the code, in the 12 rounds that counted them | about 9,900 | the docs reports (each an estimate by its auditor) |
| Docs: statements in the two clean rounds (41, 42) | about 1,760, 0 counted findings | `AUDIT41_DOCS.md`, `AUDIT42_DOCS.md` |
| Automated test cases run after every change | 445 | the suite (`docs/audit/STATUS.md`) |
