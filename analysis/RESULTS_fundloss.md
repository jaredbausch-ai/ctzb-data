# What the ETH grade loses without funding (analysis/fundloss.py, run 2026-10-29 )
Sample: regime-gated ETH 1D/2D/3D/5D signals with a finished 60 days. With funding data (2020 on): 356. Full history (2016 on): 559.
Measure: rose 10% and never fell 25.3% within 60 days (the card headline); rose 20% alongside.

## 1. FULL grade (live), 2020 on

| Grade | n | Rose 10%, never fell 25% | Rose 20% |
|---|---|---|---|
| C | 110 | 53% | 44% |
| B | 81 | 59% | 53% |
| A | 61 | 66% | 62% |
| A+ | 104 | 80% | 75% |
| all | 356 | 64% | 58% |

## 1. PRICE-only grade, same signals (2020 on)

| Grade | n | Rose 10%, never fell 25% | Rose 20% |
|---|---|---|---|
| C | 203 | 57% | 49% |
| B | 75 | 68% | 61% |
| A | 61 | 77% | 75% |
| A+ | 17 | 88% | 88% |
| all | 356 | 64% | 58% |

## 1. PRICE-only grade, full history (2016 on)

| Grade | n | Rose 10%, never fell 25% | Rose 20% |
|---|---|---|---|
| C | 330 | 55% | 55% |
| B | 121 | 62% | 64% |
| A | 83 | 73% | 75% |
| A+ | 25 | 76% | 88% |
| all | 559 | 60% | 61% |

## 2. Same signal, different letter (2020 on)

Same letter 153 of 356 (43%). FULL higher 203, FULL lower 0.

| PRICE grade | FULL C | FULL B | FULL A | FULL A+ |
|---|---|---|---|---|
| C | 110 | 62 | 31 | 0 |
| B | 0 | 19 | 23 | 33 |
| A | 0 | 0 | 7 | 54 |
| A+ | 0 | 0 | 0 | 17 |

## 3. Odds quoted on the day vs what happened (walk-forward, no hindsight)

| Version | Signals quoted | Avg quote | Actual | Brier (lower is better) | AUC (higher is better) |
|---|---|---|---|---|---|
| FULL, 2020 on, all | 304 | 73% | 60% | 0.264 | 0.52 |
| FULL, 2020 on, since 2022 | 232 | 68% | 61% | 0.249 | 0.51 |
| PRICE, same signals, all | 296 | 72% | 59% | 0.274 | 0.47 |
| PRICE, same signals, since 2022 | 223 | 68% | 60% | 0.257 | 0.47 |
| PRICE, 2016 on, all | 511 | 61% | 60% | 0.252 | 0.42 |
| PRICE, 2016 on, since 2022 | 232 | 61% | 61% | 0.237 | 0.49 |

Quoted vs actual by grade, on the signals both versions quoted (2020 on):

| Grade | FULL n | FULL quote | FULL actual | PRICE n | PRICE quote | PRICE actual |
|---|---|---|---|---|---|---|
| C | 98 | 65% | 47% | 169 | 66% | 52% |
| B | 64 | 66% | 55% | 59 | 78% | 59% |
| A | 49 | 71% | 61% | 48 | 78% | 71% |
| A+ | 68 | 84% | 71% | 3 | 93% | 67% |

## 4. Split by chart and by year: Brier on the signals both versions quoted (lower is better)

| Split | n | FULL | PRICE | Better |
|---|---|---|---|---|
| ETH 1D | 136 | 0.287 | 0.282 | PRICE |
| ETH 2D | 68 | 0.314 | 0.317 | FULL |
| ETH 3D | 47 | 0.247 | 0.257 | FULL |
| ETH 5D | 28 | 0.265 | 0.265 | FULL |
| 2021 | 54 | 0.417 | 0.410 | PRICE |
| 2022 | 8 | 0.365 | 0.360 | PRICE |
| 2023 | 71 | 0.241 | 0.246 | FULL |
| 2024 | 79 | 0.237 | 0.235 | PRICE |
| 2025 | 65 | 0.278 | 0.282 | FULL |

FULL better in 5 splits, PRICE better in 4.

Entry quality only: computed signals, never fills; no exit in the data.
