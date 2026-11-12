# Member site (item 18), review build 11 Nov 2026

Published for review at claude.ai/artifact/VButMskEvrwYEcxW3Ap7cm with a snapshot of the
feed (11 Nov 18:24 UTC) and `datasets/ledger.csv`. The page reads everything by relative
path, so the deployed version serves the same file and proxies:

| Path the page reads | Live source |
|---|---|
| `data/ctzb_feed.json` | `ctzb-feed` mirror: `feed/ctzb_feed.json` |
| `data/ledger.csv` | `ctzb-feed` mirror: `datasets/ledger.csv` |
| `data/trades.json` | `ctzb-trades`: `/trades.json` (404 until MODE=live; the page shows an empty state) |
| `data/candles/<ASSET>_<TF>.json` | `ctzb-feed` mirror: `datasets/candles_<asset>_<tf>.csv`, as JSON (ETH/BTC, 1D/2D/3D/5D/8D) |
| `data/example_ETH-2D-2024-09-22.json` | this folder (the example's chart bars, embedded in the worker) |

Deployed as the `ctzb-site` Worker (`cloudflare/ctzb-site-worker.js`, built by `cloudflare/build_site.py`;
deploy history in `docs/SITE_CHANGES.md`). Every number on the page comes from those files; nothing is typed in.
