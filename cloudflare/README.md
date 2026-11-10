# Cloudflare Workers

Source for the two Workers on the ETHKROS Cloudflare account. This folder is the
record; the dashboard editor is where they are deployed.

| Worker | File | Token it holds | Public |
|---|---|---|---|
| `ctzb-feed` | `ctzb-feed-worker.js` | `GITHUB_TOKEN` — Contents: read-only | yes — read-only mirror of the repo |
| `ctzb-scheduler` | `ctzb-scheduler-worker.js` | `GITHUB_DISPATCH_TOKEN` — Actions: read+write | no data route; `/health` only |

They are separate on purpose. The public mirror must never hold a credential that
can trigger CI.

Neither file contains a secret. Both tokens live in Cloudflare's secret store and
are read from `env` at runtime.

**ctzb-feed** — KV binding `FEED`, cron `*/15 * * * *`. Serves `feed/ctzb_feed.json`,
`datasets/*.csv`, `keep.json`, `odds.json`, `troughs.json` byte-for-byte, so a
consumer of the public repo switches by changing only its base URL.

**ctzb-scheduler** (v2, 10 Nov 2026) — KV binding `SCHED`, ONE cron trigger
`13,25,35,43 * * * *`. The code decides what each tick dispatches: `daily.yml`
(with `scheduled=true`) at :13 and :43 after each 4-hour close, `watchdog.yml`
95 minutes after each close, `pcr.yml` every 3 hours. About 26 dispatches a day.
