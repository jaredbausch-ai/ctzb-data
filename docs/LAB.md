# Statistics lab — branch `stats-lab`

Set up 25 Nov 2026 at Jared's request: a place to keep improving the entry
statistics without touching the live product.

## Why this branch cannot reach the product

Everything live reads `main` and nothing else:

| Part of the product | Reads | Where that is set |
|---|---|---|
| Candle / scoring Action (`daily.yml`) | `main` | `cloudflare/ctzb-scheduler-worker.js`, `REF = 'main'` |
| Feed and dataset mirror (`ctzb-feed`) | `main` | `cloudflare/ctzb-feed-worker.js`, `BRANCH = 'main'` |
| Dashboard, member site, alerts | the mirror above | — |
| `pcr.yml` push trigger | `main` only | `branches: [main]` |
| `basis.yml` push trigger | `test/basis` only | `branches: [test/basis]` |

No workflow runs on a push to `stats-lab`, so nothing committed here can
change a card, a grade, the feed, the dashboard or an alert.

## Rules for working here

1. **Commit only to `stats-lab`.** Never push to `main` from a lab session.
   Check with `git branch --show-current` before every commit.
2. **The repo's rules still apply in full.** `CONTEXT.md` and
   `docs/PRETRADE.md` are the record: entry at `ei = ti + 3`, the mechanical
   gate `R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)` (never `engine.BULL`),
   the do-not-re-test list, and the six methodology guards — declare the
   candidates first, split by chart, split by year, check collinearity, treat
   ETH and BTC as one sample for anything date-anchored. Entry quality only;
   no result here is a strategy return.
3. **Do not edit the live scripts in place** (`refresh.py`, `grade_live.py`,
   `extras_live.py`, `stack_live.py`, `feed_live.py`, `verify_cards.py`,
   `engine.py`, `regimes.py`, `troughs.py`, `measures.py`). Import them. New
   work goes in `lab/` — one generator per test, its output beside it as
   `lab/RESULTS_<name>.txt`, declared candidate list at the top of the script.
4. **Keep the lab's data current** by merging `main` in before a run
   (`git fetch --depth=50 origin main && git merge origin/main`). The Action
   commits candles to `main` every 4 hours; the lab does not get them otherwise.
5. **Log every test** in the table below, pass or fail.

## Promoting a result to the product

Only when Jared says so. A finding moves to `main` as its own commit with:
the generator and its RESULTS file, the PRETRADE entry, and — if it lands
under Tier 1, Promising or In-trade reads — its `REGISTRY` entry and
`DOC_MAP` line in `stack_live.py` plus the regenerated
`analysis/registry.json` in the same commit, or the next pipeline run fails.

## Test log

| Date | Test | Generator | Declared | Result |
|---|---|---|---|---|
| 25 Nov 2026 | ROC+ lower band (ETH/BTC 5D, and own chart) broken in the 30/60 days before a signal | `lab/rocband.py` | yes, before running | **All 6 fail.** ETH 5D 60-day (Jared's read): +20% 70% vs 54%, touched -30% 9% vs 23% (n=67/294), passes charts, years, shuffle and lens overlap, but fails rule 1 on sample (12 signals to 2021); the 67 come from 5 break episodes (Nov-Dec 2025: 0 of 5); 37 of 67 overlap the 5D-turn-under-40 watch item (9.5 by chance). BTC: no effect (49% vs 51%). Own-chart band: no effect on either asset. Watch item at most, not a lens. Entry quality only |
| 25 Nov 2026 | ROC+ lower band, addendum on the card measure (rose 10% and never fell 25.3%) | `lab/rocband10.py` | yes, before running | **All 6 fail.** ETH 5D 60-day: 75% vs 62%, fell 25.3% 12% vs 30% (n=67/294); 2022 on 69% vs 58%, fell 15% vs 29%; charts 3/4, years 4/4, shuffle +13.1 vs p95 +5.7, no lens overlap; fails rule 1 on sample only (12 signals to 2021). BTC: 61% vs 64%, no effect. Misses still went above entry first (ETH on: 10 of 10, median best +7.2%). Entry quality only |
