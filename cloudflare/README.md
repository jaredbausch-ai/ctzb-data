# Cloudflare Workers

Source for the five Workers on the ETHKROS Cloudflare account. This folder is the
record; the dashboard editor is where they are deployed.

| Worker | File | Token it holds | Public |
|---|---|---|---|
| `ctzb-feed` | `ctzb-feed-worker.js` | `GITHUB_TOKEN` — Contents: read-only | yes — read-only mirror of the repo |
| `ctzb-scheduler` | `ctzb-scheduler-worker.js` | `GITHUB_DISPATCH_TOKEN` — Actions: read+write | no data route; `/health` only |
| `ctzb-dashboard` | `ctzb-dashboard-worker.js` (**generated** — see below) | none; reads the mirror over a Service Binding | **no** — every path behind a gate that fails closed |
| `ctzb-trades` | `ctzb-trades-worker.js` | `COINBASE_PRIVATE_KEY` — Coinbase CDP key, **View only** | `/health` only until `MODE=live`; then `/trades.json` |
| `ctzb-site` | `ctzb-site-worker.js` (**generated** by `build_site.py`) | none; reads the mirror and `ctzb-trades` over Service Bindings | **no** — every path behind a gate that fails closed |

They are separate on purpose. The public mirror must never hold a credential that
can trigger CI.

No file contains a secret. Every token, key and password lives in Cloudflare's secret store and is read
from `env` at runtime.

**ctzb-feed** — KV binding `FEED`, cron `*/15 * * * *`. Serves `feed/ctzb_feed.json`,
`datasets/*.csv`, `keep.json`, `odds.json`, `troughs.json` byte-for-byte, so a
consumer of the public repo switches by changing only its base URL.

Backups (item 17e): optional R2 binding `BACKUPS` -> bucket `ctzb-backups` (private).
Once a day at 01:00 UTC the cron stores the exact current commit as
`daily/ctzb-data-YYYY-MM-DD.tar.gz` (tagged with its sha), plus `monthly/ctzb-data-YYYY-MM`
on the 1st. Write-once. An R2 lifecycle rule expires `daily/` after 90 days; `monthly/`
is kept. About 10 MB on 12 Nov 2026 and growing with the repo (cap 200 MB). `/health` reports the last backup. To restore: download the object
from the R2 dashboard and `tar -xzf` it (drilled 12 Nov 2026: byte-identical to its tagged commit, pipeline reruns clean on it). Tests: `node tests/test_mirror_backup.mjs` (21).

**ctzb-scheduler** (v2, 10 Nov 2026) — KV binding `SCHED`, ONE cron trigger
`13,25,35,43 * * * *`. The code decides what each tick dispatches: `daily.yml`
(with `scheduled=true`) at :13 and :43 after each 4-hour close, `watchdog.yml`
95 minutes after each close, `pcr.yml` every 3 hours. About 26 dispatches a day.

**ctzb-dashboard** (10 Nov 2026, item 17f) — the ETH Setup Standard dashboard, moved off
the claude.ai artifact so it no longer needs a Claude scheduled task to upload its data
six times a day. Service Binding `MIRROR` -> `ctzb-feed`. Gate: `GATE_MODE` = `access`
(Cloudflare Access; the Worker also verifies the Access JWT itself: signature, audience,
issuer, expiry) or `password` (HTTP Basic against the secret `DASHBOARD_PASSWORD`).
Unset or unknown, it serves nothing.

`ctzb-dashboard-worker.js` is built, not written: `python cloudflare/build_dashboard.py`
combines `docs/artifacts/eth-setup-standard.html` (the page, unchanged) with
`dashboard_shim.js` (a stand-in for the Dashboard artifact type's `dash` runtime) and
`dashboard_worker_template.js`. Edit those three, never the output.
It also sends Jared's phone alerts through a private Telegram bot: cron `5,20,35,50 * * * *`
(offset from the mirror's 15-minute sync) reads the feed's `alerts` (schema 4) and sends
each `alert_id` once, recorded in KV `NOTIFY` (every clean feed carries each alert for at least 24 hours after it was first emitted, so a feed the mirror misses loses nothing while the mirror pulls at least once a day). A failed send is not recorded and retries
on the next tick. `POST /alerts/test` (gated, once per 10 minutes) checks the path.
Bindings: `NOTIFY` (KV), secret `TELEGRAM_BOT_TOKEN`, var `TELEGRAM_CHAT_ID`.

Tests: `node tests/test_dashboard_gate.mjs` (26), `node tests/test_dashboard_alerts.mjs` (21).

**ctzb-trades** (11 Nov 2026, item 13a) — the lead trader's real trades, relayed from
Coinbase. KV binding `TRADES`, cron `* * * * *`. Reads futures fills, positions and the
futures balance with a **View-only** CDP key (ES256 JWT, one per request), groups the
fills of one order into one trade, and records open / add / reduce / close with price,
leverage and size as % of the account; on reduce / close also the move from average
entry and the result as % of the account. Never dollar amounts, contract counts or
balances: every stored record passes an allow-list. First run takes a baseline (open
positions recorded, not posted). Positions reconciled against Coinbase; mismatches are
corrected and logged, never posted. `MODE` unset or anything but `live` = dry run:
nothing public, gated `/dry` (`DRY_VIEW_PASSWORD`) shows what would post. Going live
needs Noah's sign-off and is Jared's switch. Setup: `BRIEF_trades.md`.
Tests: `node tests/test_trades_relay.mjs` (41).

**ctzb-site** (11 Nov 2026, item 18) — the member site. Built, not written:
`python cloudflare/build_site.py` wraps `docs/artifacts/member-site/index.html` and the
chart example into `site_worker_template.js`. The page reads `data/...` by relative path;
the Worker answers from fixed tables only: the feed and `ledger.csv` from the mirror,
candles from the mirror's `datasets/candles_<asset>_<tf>.csv` (written by `extras_live.py`
each run), trades from `ctzb-trades` (404 until it goes live, which the page shows as "the lead
trader's feed is unavailable"). Bindings `MIRROR` -> ctzb-feed, `TRADES` -> ctzb-trades; gate `GATE_MODE`
`access` (`ACCESS_TEAM_DOMAIN`, `ACCESS_AUD`) or `password` (`SITE_PASSWORD`), unset =
refuse everything. Setup: `BRIEF_site.md`. Tests: `node tests/test_site_worker.mjs` (25).

**Health monitor (11 Nov 2026).** `ctzb-scheduler` v3 also watches everything that can fail
quietly -- its own GitHub dispatches, the mirror's sync, the nightly backup, the feed's age,
cards or extras held back for over 75 minutes, the Kraken cross-check skipped for over a day,
the trades relay, and `ctzb-dashboard`'s alert sender (by a heartbeat in the shared `NOTIFY`
KV) -- and messages Jared on Telegram: PROBLEM once, STILL DOWN every 6 hours, RECOVERED when
it clears. Extra bindings `MIRROR`, `TRADES`, `NOTIFY`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`; setup in `BRIEF_monitor.md`. Backup channel and dead-man: the GitHub
watchdog reads the three public `/health` routes and opens a `pipeline-alert` issue (GitHub
emails) if a Worker is unreachable, the mirror or relay is stale, the monitor stops, or it has
problems it can't deliver. Tests: `node tests/test_health_monitor.mjs` (36).

