# Backlog — declared tests not yet run

Candidates are declared here BEFORE they are run, per `docs/PRETRADE.md`
methodology guards. Moving an item out of this file means it has been run and
filed in Tier 1, "Failed — do not re-test", or "Theory-craft".

---

## 1. On-chain holder profitability vs CTZB signal quality

Queued 8 Nov 2026. Preliminary single-cut work is in `analysis/mvrv.py` /
`RESULTS_MVRV.txt`; this entry is the extensive version against the signal set,
which has NOT been run.

### Why it is queued
Standalone MVRV quintiles separate forward returns cleanly and monotonically
(2019+: Q1 +18.6% at 60d / 72% up, Q5 −2.0% / 45%, baseline +5.9% / 57%). That
is a stronger standalone result than most things tested here. It has never been
tested as a CTZB lens.

### Data
Coin Metrics community data, free, no key, BTC daily from 2010:
```
git clone --depth 1 --filter=blob:none --sparse https://github.com/coinmetrics/data
cd data && git sparse-checkout set --no-cone --skip-checks csv/btc.csv
```
`CapMVRVCur`, `PriceUSD`, plus `FlowInExNtv` / `FlowOutExNtv` / `SplyExNtv` for
candidate 3. ETH equivalent at `csv/eth.csv` — CONFIRM MVRV is populated there
before relying on it. Community data lags roughly 5 months.

### Candidate lenses — declared now, full list, nothing added after seeing results
1. MVRV at entry in its bottom quintile (BTC-derived, applied to both assets).
2. MVRV at entry below 1.28 — the fixed Q1 ceiling from the 2019+ cut.
3. MVRV falling over the 30 days into the trough vs rising.
4. MVRV z-score against its own trailing 365-day mean, bottom tercile.
5. Net exchange flow (`FlowInExNtv` − `FlowOutExNtv`) negative over the 14 days
   into the trough — coins leaving exchanges.
6. Exchange supply (`SplyExNtv`) at a trailing 365-day low at entry.

### Required outputs — report all, not just win rate
- Win rate AND the failure metrics: LIQ30, LIQ20, EARLY, median drawdown.
- Split by chart. Split by year. ETH and BTC are ONE sample here, because MVRV
  is BTC-derived and date-anchored — do not count them as independent.
- Collinearity against the existing Tier 1 lenses, especially the regime gate
  and the funding lens. MVRV is slow-moving and may simply restate the gate.
- Placebo: re-score with the MVRV series date-shuffled, 40 draws.

### Known traps
- MVRV is slow-moving, so signals cluster heavily. Decluster and expect the
  effective n to be far below the row count.
- The horizon split is the main finding so far and must survive: current-bucket
  Q2 UNDERPERFORMS baseline at 60 days (+3.7% vs +5.9%) while strongly
  outperforming at 365 (+130.0% vs +57.1%). A lens that only works at 365 days
  is not usable against entries that are judged on a 60-day window.
- MVRV is not percent supply in profit. At the Nov 2022 low, supply-in-profit
  read 57.7% with MVRV 0.78; today supply-in-profit reads 58.3% with MVRV 1.41.
  The two disagree about whether now resembles that bottom. Do not treat a
  result on one as a result on the other.

---

## 2. Outstanding from earlier sessions
- Explain or drop the 160D gradient anomaly in the 0.20–0.30 cell.
- Walk-forward the 160D projection the way the CT/Signal distance was done.
- Re-score projection and confluence interaction against LIQ30, not win rate.
- Volatility-as-risk-filter: per-year split, placebo, and whether it survives
  alongside the funding filter.
- Two broken fetchers: Binance 451 (Coinbase Premium), Farside ETF flows.
- Scanner v9 unverified in TradingView.
- `cycday` mislabel on the 2026-07-13 ETH weekly signal.
