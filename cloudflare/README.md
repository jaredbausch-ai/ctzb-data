# Cloudflare Workers

Source for the two Workers on the ETHKROS Cloudflare account. This folder is the
record; the dashboard editor is where they are deployed.

| Worker | File | Token it holds | Public |
|---|---|---|---|
| `ctzb-feed` | `ctzb-feed-worker.js` | `GITHUB_TOKEN` — Contents: read-only | yes — read-only mirror of the repo |
| `ctzb-scheduler` | `ctzb-scheduler-worker.js` | `GITHUB_DISPATCH_TOKEN` — Actions: read+write | no data route; `/health` only |
| `ctzb-dashboard` | `ctzb-dashboard-worker.js` (**generated** — see below) | none; reads the mirror over a Service Binding | **no** — every path behind a gate that fails closed |

They are separate on purpose. The public mirror must never hold a credential that
can trigger CI.

Neither file contains a secret. Both tokens live in Cloudflare's secret store and
are read from `env` at runtime.

**ctzb-feed** — KV binding `FEED`, cron `*/15 * * * *`. Serves `feed/ctzb_feed.json`,
`datasets/*.csv`, `keep.json`, `odds.json`, `troughs.json` byte-for-byte, so a
consumer of the public repo switches by changing only its base URL.

Backups (item 17e): optional R2 binding `BACKUPS` -> bucket `ctzb-backups` (private).
Once a day at 01:00 UTC the cron stores the exact current commit as
`daily/ctzb-data-YYYY-MM-DD.tar.gz` (tagged with its sha), plus `monthly/ctzb-data-YYYY-MM`
on the 1st. Write-once. An R2 lifecycle rule expires `daily/` after 90 days; `monthly/`
is kept. ~8.8 MB each. `/health` reports the last backup. To restore: download the object
from the R2 dashboard and `tar -xzf` it. Tests: `node tests/test_mirror_backup.mjs` (21).

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
each `alert_id` once, recorded in KV `NOTIFY`. A failed send is not recorded and retries
on the next tick. `POST /alerts/test` (gated, once per 10 minutes) checks the path.
Bindings: `NOTIFY` (KV), secret `TELEGRAM_BOT_TOKEN`, var `TELEGRAM_CHAT_ID`.

Tests: `node tests/test_dashboard_gate.mjs` (26), `node tests/test_dashboard_alerts.mjs` (18).
