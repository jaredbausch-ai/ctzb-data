# Top grade at 70%: walk-forward check (27 Nov 2026)

Declared before running: `analysis/topgrade.py` (candidates T1 to T4 and the pass rule are in its header).
Each test signal is judged by the card it would have had on its confirmation date, built only from signals
whose 60 days had closed by then. Outcome: rose 10% before ever falling 25.3% within 60 days of entry.

**Entry quality only.** Computed signals, not fills. The data has no exits, so this is not a strategy return or a track record.

Test signals: 756 (ETH and BTC, 1D to 5D, confirmed 2019-01-01 to 2026-09-26, 60 days closed).

## All candidates, pooled

| Rule | Top grade: signals | Rose 10% before falling 25.3% | Reached +10% | Fell 25.3% first | Not top grade: signals | Rose 10% before falling 25.3% | Gap (points) |
|---|---|---|---|---|---|---|---|
| T1 from-entry share ≥ 70% | 536 | 70% | 72% | 16% | 220 | 64% | +6 |
| T2 T1 with 15+ in the sample | 469 | 67% | 68% | 18% | 287 | 71% | -4 |
| T3 headline share ≥ 70% | 623 | 69% | 71% | 18% | 133 | 66% | +3 |
| T4 grade A+ (today) | 127 | 83% | 83% | 10% | 629 | 66% | +17 |

## T1 from-entry share ≥ 70%: split

| Split | Top grade: signals | Rose 10% before falling 25.3% | Not top grade: signals | Rose 10% before falling 25.3% |
|---|---|---|---|---|
| Asset BTC | 248 | 71% | 164 | 62% |
| Asset ETH | 288 | 69% | 56 | 70% |
| Chart BTC 1D | 112 | 76% | 91 | 65% |
| Chart BTC 2D | 73 | 64% | 33 | 61% |
| Chart BTC 3D | 48 | 73% | 18 | 61% |
| Chart BTC 5D | 15 | 67% | 22 | 55% |
| Chart ETH 1D | 151 | 70% | 22 | 73% |
| Chart ETH 2D | 70 | 64% | 17 | 65% |
| Chart ETH 3D | 43 | 72% | 11 | 55% |
| Chart ETH 5D | 24 | 75% | 6 | 100% |
| Year 2019 | 22 | 86% | 23 | 65% |
| Year 2020 | 85 | 93% | 22 | 68% |
| Year 2021 | 113 | 66% | 18 | 61% |
| Year 2022 | 13 | 38% | 3 | 33% |
| Year 2023 | 108 | 69% | 35 | 86% |
| Year 2024 | 129 | 71% | 36 | 64% |
| Year 2025 | 64 | 50% | 74 | 58% |
| Year 2026 | 2 | 0% | 9 | 33% |

## T2 T1 with 15+ in the sample: split

| Split | Top grade: signals | Rose 10% before falling 25.3% | Not top grade: signals | Rose 10% before falling 25.3% |
|---|---|---|---|---|
| Asset BTC | 236 | 70% | 176 | 64% |
| Asset ETH | 233 | 64% | 111 | 81% |
| Chart BTC 1D | 103 | 75% | 100 | 67% |
| Chart BTC 2D | 70 | 63% | 36 | 64% |
| Chart BTC 3D | 48 | 73% | 18 | 61% |
| Chart BTC 5D | 15 | 67% | 22 | 55% |
| Chart ETH 1D | 120 | 62% | 53 | 87% |
| Chart ETH 2D | 53 | 58% | 34 | 74% |
| Chart ETH 3D | 37 | 68% | 17 | 71% |
| Chart ETH 5D | 23 | 74% | 7 | 100% |
| Year 2019 | 19 | 84% | 26 | 69% |
| Year 2020 | 40 | 88% | 67 | 88% |
| Year 2021 | 94 | 64% | 37 | 70% |
| Year 2022 | 13 | 38% | 3 | 33% |
| Year 2023 | 108 | 69% | 35 | 86% |
| Year 2024 | 129 | 71% | 36 | 64% |
| Year 2025 | 64 | 50% | 74 | 58% |
| Year 2026 | 2 | 0% | 9 | 33% |

## Pass rule

- **T1: fails.** (a) 70% ≥ 70%: True; (b) gap +6 ≥ 10: False; (c) both assets: False; (d) beats in 5 of 7 years with 5+: True
- **T2: fails.** (a) 67% ≥ 70%: False; (b) gap -4 ≥ 10: False; (c) both assets: False; (d) beats in 3 of 7 years with 5+: False
- Overlap: 127 of the 536 T1 top-grade signals are also A+; 127 test signals are A+ in all.

## Check of the card rebuild

The same sample rule, run on today's data, reproduces all 20 live cards in the feed of 27 Nov 2026 exactly: grade,
sample size and from-entry share (to 6 decimals). So each test signal's card above is the one stack_live.py would
have built on its confirmation date.

## Reading (27 Nov 2026)

T1, the pick, fails its declared pass rule: top grade beats not-top-grade by 6 points pooled (rule: 10) and not on
ETH (69% vs 70%). Most test signals' cards clear 70% (536 of 756), so the label would not separate much. T4, grade A+,
separates by 17 points (83% vs 66%). Caveat on T4: the grade's lens lists were chosen on the full history (see
analysis/model.py, addendum), so its 83% carries some hindsight; the T1 cards use the same lens sets to pick their
samples. Top grade therefore stays A+. Entry quality only.
