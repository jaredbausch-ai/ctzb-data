# Member site (item 18), review build 11 Nov 2026

Published for review at claude.ai/artifact/VButMskEvrwYEcxW3Ap7cm with a snapshot of the
feed (11 Nov 18:24 UTC) and `datasets/ledger.csv`. The page reads everything by relative
path, so the deployed version serves the same file and proxies:

| Path the page reads | Live source |
|---|---|
| `data/ctzb_feed.json` | `ctzb-feed` mirror: `feed/ctzb_feed.json` |
| `data/ledger.csv` | `ctzb-feed` mirror: `datasets/ledger.csv` |
| `data/trades.json` | `ctzb-trades`: `/trades.json` (404 until MODE=live; the page shows an empty state) |
| `data/example_ETH-2D-2024-09-22.json` | this folder (the chart view's example until a candles route exists) |

Not deployed yet. Every number on the page comes from those files; nothing is typed in.
