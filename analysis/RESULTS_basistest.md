# Basis-built funding vs the real thing (analysis/basistest.py, run 2026-10-29)

Basis days: 2491, 2020-01-01 to 2026-10-27.

## 1. Day by day: share of days the basis version agrees with the official one

| Year | days | P1 FUND | P1 FCOOL | P2 FUND | P2 FCOOL |
|---|---|---|---|---|---|
| 2020 | 286 | 77% | 80% | 79% | 81% |
| 2021 | 365 | 89% | 87% | 81% | 82% |
| 2022 | 365 | 79% | 75% | 65% | 65% |
| 2023 | 365 | 78% | 65% | 68% | 65% |
| 2024 | 366 | 83% | 84% | 81% | 82% |
| 2025 | 365 | 83% | 78% | 67% | 72% |
| 2026 | 300 | 77% | 82% | 64% | 74% |
| all | 2412 | 81% | 79% | 72% | 74% |

## 2. On every graded ETH 1D-5D signal (356 with official funding)

| Version | signals | FUND agrees | FCOOL agrees | GRADE LETTER agrees |
|---|---|---|---|---|
| P1 daily mean | 356 | 80% | 76% | 74% |
| P2 daily close | 356 | 74% | 76% | 71% |

Grade letter agreement by chart and by year:

| Split | P1 daily mean (n) | P2 daily close (n) |
|---|---|---|
| ETH 1D | 83% (178) | 74% (178) |
| ETH 2D | 66% (89) | 69% (89) |
| ETH 3D | 64% (56) | 66% (56) |
| ETH 5D | 64% (33) | 67% (33) |
| 2020 | 75% (59) | 73% (59) |
| 2021 | 83% (65) | 75% (65) |
| 2022 | 88% (8) | 88% (8) |
| 2023 | 62% (73) | 52% (73) |
| 2024 | 77% (86) | 87% (86) |
| 2025 | 72% (65) | 62% (65) |

## Verdict against the declared bar (95%+ overall, no year with 10+ signals below 90%)

- P1 daily mean: 74% overall, worst year 62% -> FAIL
- P2 daily close: 71% overall, worst year 52% -> FAIL

Entry quality only: computed signals, never fills.
