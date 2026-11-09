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

### What we would have to buy to run this against the E-cross strategy

Nothing below is a test design. It is what the data would cost to have the
inputs consistently, for whenever we sit down and define the test.

**The blocker.** Every free source lags. Coin Metrics community data ran to
2026-05-23 when fetched on 8 Nov — five and a half months behind. Their
community API (`community-api.coinmetrics.io`) is current and free but is not
on this session's egress allowlist, so it cannot be reached from the container
either. For a backtest the lag does not matter. For scoring a live signal it
is fatal, and that is the use we would want.

**Metrics the question needs**

| Metric | Why | Free source | Lag |
|---|---|---|---|
| Percent supply in profit | the original claim | none | — |
| MVRV, BTC + ETH | closest free relative | Coin Metrics `CapMVRVCur` | 5.5 mo |
| Realized price / realized cap | the denominator; lets MVRV be recomputed from spot | Coin Metrics | 5.5 mo |
| Exchange netflow, exchange supply | who is selling, and the controlled-selling question | Coin Metrics `FlowInExNtv` / `FlowOutExNtv` / `SplyExNtv` | 5.5 mo |
| Spot CVD by venue | the only thing that directly measures spot buying vs selling | none | — |

**Paywalls, verify before buying — checked 8 Nov 2026, prices move**

- *Glassnode.* Studio Advanced is $99/mo, or $49/mo billed annually, but it
  carries API Light only: 14 days of history, daily resolution, 50 calls a day.
  That is unusable for a backtest. Full API access starts at Studio
  Professional, **$999/mo**. Glassnode's pricing page does not name
  supply-in-profit or MVRV by tier; confirm with them before paying.
- *CryptoQuant.* On-chain data requires Professional or above. Professional is
  roughly $109/mo ($99 annual) but caps historical lookback at **1 year**.
  Full history needs **Premium, about $799/mo**. The source listing these
  prices contradicts itself on monthly vs annual, so confirm on their own page.
  Metric paths: `market-indicator/mvrv`, `exchange-flows/netflow`, and
  `network-indicator/pnl-supply` for the supply-in-profit analogue.
- *Coin Metrics.* Community tier free and no key, via the GitHub CSV dump;
  current data needs their paid API, price not published.
- *Kaiko / Amberdata.* The route to trade-level spot CVD. Enterprise pricing,
  contact sales. Almost certainly not worth it for this.

**The cheap option worth weighing first.** Coin Metrics community data is free,
has full history for both assets, and already covers MVRV, realized cap and
exchange flows. It is enough to run the historical work against the signal set.
It is only the live-scoring use that needs a paid feed, and that decision can
wait until the backtest says whether there is anything there.

**Already established, so the test does not have to rediscover it**
- Past long ETH 5D red streaks all ended with MVRV between 0.86 and 0.94, six
  of seven. Working from the May realized price, the current streak implies
  roughly 1.26 down to 1.03 — an ordinary MVRV move inside an unusually gentle
  price move. See `RESULTS_MVRV.txt`.
- Exchange supply change across those streaks had no consistent sign.

---

## 2. Pipeline hardening — before the feed goes live

Added 9 Nov 2026. These are build tasks, not tests; they carry no parameters to
define. Context in the project notes, not here.

**Already done 4 Nov** (see `docs/PIPELINE_AUDIT_2026-11-04.md`): automatic
re-run with cooldown, stale-candle check, cron-free heartbeat, watchdog judged
against the candle close.

### Blocking the repo going private
- **Read-only pipeline.** One job, two outputs, both on the Cloudflare backend.
  (a) A read-only source for real fills, relayed near-real-time as a separate
  stream, labelled as real trades, never merged into the computed-signal odds,
  and carrying no dollar amounts. Needs its own exchange key: the 24 Oct one is
  IP-allowlisted elsewhere. (b) A read-only surface that keeps
  `feed/ctzb_feed.json` reaching the member site once this repo is private.
  The 4-hourly Action is too slow for (a) and its scheduler is unreliable.
  Going private also moves the heartbeat off Actions (private repos bill
  Actions minutes).

### The seven hardening items
- **(a) Bad exchange data.** Cross-check every candle against a second source;
  fail the run on a mismatch.
- **(b) No typed-in numbers.** Every figure anyone sees comes from code, never
  entered by hand.
- ~~**(c) Grade and lens regression test.**~~ **BUILT 9 Nov 2026.**
  `tests/regression.py`, wired into `daily.yml` after the card cross-check.
  Compares every signal in `datasets/ledger.csv` against
  `tests/baseline/ledger.json`, keyed by (asset, chart, entry). Grade, lenses,
  tags and entry price are frozen from confirmation; the 60-day outcome is only
  checked once the window has closed; cohort aggregates are skipped. An intended
  change is re-baselined with `--approve` and committed, so it shows up in the
  diff. Verified by fault injection (flipped outcome, changed grade, deleted
  signal all fail; 919 signals pass clean).
- **(d) Alert safety.** Duplicate-alert guard, and withhold the alert if any
  check in the run failed.
- **(e) Backups.** An off-GitHub copy of the data and the feed.
- **(f) Dashboard upload off Claude usage** — moves to Cloudflare.
- **(g) Dry run.** Several clean weeks before anyone outside sees it.

---

## 3. Outstanding from earlier sessions
- Explain or drop the 160D gradient anomaly in the 0.20–0.30 cell.
- Walk-forward the 160D projection the way the CT/Signal distance was done.
- Re-score projection and confluence interaction against LIQ30, not win rate.
- Volatility-as-risk-filter: per-year split, placebo, and whether it survives
  alongside the funding filter.
- Two broken fetchers: Binance 451 (Coinbase Premium), Farside ETF flows.
- Scanner v9 unverified in TradingView.
- `cycday` mislabel on the 2026-07-13 ETH weekly signal.

---

## Data status update — 8 Nov 2026

`community-api.coinmetrics.io` is now reachable. `fetch_coinmetrics.py` pulls
full history, current to yesterday, free and keyless, into
`data/onchain/{BTC,ETH}_cm_daily.csv`. The GitHub CSV dump and its 5.5-month
lag are no longer the constraint, and nothing needs buying for the historical
work.

Available on the community tier: `PriceUSD`, `CapMrktCurUSD`, `CapMVRVCur`,
`AdrActCnt`, `SplyCur`, `SplyExNtv`, `FlowInExNtv`, `FlowOutExNtv`.
`CapRealUSD` returns 403, but realised cap = `CapMrktCurUSD / CapMVRVCur`.

Percent supply in profit is still Glassnode/CryptoQuant only; see the paywall
table above if it is ever wanted specifically.
