# Member site (item 18)

`index.html` is the member page. It was first published for review on 11 Nov 2026 (claude.ai/artifact/VButMskEvrwYEcxW3Ap7cm,
with a feed snapshot); that review copy is not kept up to date. The current page is this file, and the live
site is the `ctzb-site` Worker built from it. The page reads everything by relative path:

| Path the page reads | Live source |
|---|---|
| `data/ctzb_feed.json` | `ctzb-feed` mirror: `feed/ctzb_feed.json` |
| `data/ledger.csv` | `ctzb-feed` mirror: `datasets/ledger.csv` |
| `data/trades.json` | `ctzb-trades`: `/trades.json` (404 until MODE=live; the page then says the lead trader's feed is unavailable) |
| `data/candles/<ASSET>_<TF>.json` | `ctzb-feed` mirror: `datasets/candles_<asset>_<tf>.csv`, as JSON (ETH/BTC, 1D/2D/3D/5D/8D) |
| `data/example_ETH-2D-2024-09-22.json` | this folder (the example's chart bars, embedded in the worker): 51 ETH 2D bars, 12 Aug 2024 through the bar that holds day 60 (20-21 Nov 2024). Nothing after its 60-day window (13 Nov 2026 audit #20: it carried one later bar) |

Deployed as the `ctzb-site` Worker (`cloudflare/ctzb-site-worker.js`, built by `cloudflare/build_site.py`;
deploy history in `docs/SITE_CHANGES.md`). Every figure on the page comes from those files. What the page types is definitions, not figures: the +10% level, the 25.3% line (3.3x with 5% maintenance), the 60-day window, 2020 as the first year of the per-year average, and the worked example's date.
