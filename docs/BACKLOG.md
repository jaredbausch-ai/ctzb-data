# Backlog — things to sit down and define

Nothing here is a declared test. Parameters are Jared's to set. An item leaves
this file only once he has defined what to measure and it has been run.

---

## 1. On-chain holder profitability (MVRV / percent supply in profit)

Noted 8 Nov 2026. To discuss and define before anything is run against signals.

### What prompted it
A post claiming 58.3% of BTC supply in profit marks a historic accumulation
zone. Percent supply in profit itself needs a paid Glassnode or CryptoQuant
key. MVRV is the closest free relative.

### Data source, confirmed working
Coin Metrics community data — free, no key, BTC daily from 2010:
```
git clone --depth 1 --filter=blob:none --sparse https://github.com/coinmetrics/data
cd data && git sparse-checkout set --no-cone --skip-checks csv/btc.csv
```
Carries `CapMVRVCur`, `PriceUSD`, and exchange flow columns (`FlowInExNtv`,
`FlowOutExNtv`, `SplyExNtv`). ETH file at `csv/eth.csv`, not yet checked.
Community data lags roughly 5 months; it ended 2026-05-24 when fetched.

### What one standalone cut showed
`analysis/mvrv.py` / `RESULTS_MVRV.txt`. Quintiled MVRV against forward
returns, 2019+: bottom quintile +18.6% at 60d and 72% up, top quintile −2.0%
and 45%, baseline +5.9% and 57%. Monotone and clean. Never tested as a CTZB
lens.

### Two things to settle before designing anything
- The horizon split. The current bucket underperforms baseline at 60 days
  (+3.7% vs +5.9%) and strongly outperforms at 365 (+130.0% vs +57.1%). Whether
  that is usable depends on what window the test judges entries on.
- MVRV is not percent supply in profit. Nov 2022 read 57.7% supply in profit
  with MVRV 0.78; now reads 58.3% with MVRV 1.41. They disagree about whether
  today resembles that bottom.

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
