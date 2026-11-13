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
deploy history in `docs/SITE_CHANGES.md`). Every figure on the page comes from those files. What the page types is definitions and fixed wording, not figures: the +10% level, the +20% and -30% tile levels, the day-10 check, the 25.3% line (3.3x with 5% maintenance), the 60-day window, the ladder's steps (5, 10, 15, 20%), the cloud's +100% / -40% range, the odds-fade band and check names, the fallback chart's zones (0 to -5, -5 to -10, -10 to -20%), the example's 2-day bars, the strict check's rounding tolerances, 2020 as the first year of the per-year average, the worked example's date and id, the 10-bar minimum for a chart file, the 5-hour limit after which the data is called out of date (the pipeline runs every 4 hours), and two phrases of plain description ("sometimes for a year" for how long the filter can stay off, "usually within the hour" for when a held run retries).

The page uses a file only if it passes a strict check (13 Nov 2026): the feed against the schema inside the page (`FEED_SCHEMA`, with its cross-field rules; `feedcheck.py` reads the same block and `feed_live.py` will not publish a feed that fails it), the lead-trader file against the same schema's `trades` part (newest first, nothing in the future), the ledger row by row and against the feed's counts, and each chart file bar by bar and against the setup it is drawn for (docs/FEED_SPEC.md "Audit #21 corrections" and "Audit #22 corrections" list every rule). A file that fails reads "unavailable"; nothing is patched or guessed. `tests/test_feed_damage.py` damages every field in every way and checks exactly that.
