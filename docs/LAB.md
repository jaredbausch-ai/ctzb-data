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
| | | | | |
