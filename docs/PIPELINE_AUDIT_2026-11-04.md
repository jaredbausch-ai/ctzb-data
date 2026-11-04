# Pipeline audit, 4 Nov 2026

Jared, 4 Nov: "audit all of our back end ... our data flow needs to be repushed
immediately on failures. Unless there is a succession of failures, then ... a cooldown
... retried for 15 or 30 minutes."

## What the run history showed (every run since 16 Oct, every candle commit since 22 Oct)

| Measure | Result |
|---|---|
| Gaps between candle commits longer than 4h45m | 35 of 53 (typical 7-10 hours; worst 19.3h, 31 Oct-1 Nov) |
| Candle job: scheduled ticks honoured, 2-4 Nov | 2-3 of 6 a day, some hours late |
| Watchdog: scheduled ticks honoured, 4 Nov | 3 of 19 |
| Put/call job: biggest gaps between commits | 13.0h, 9.9h, 9.5h |
| Candle runs that failed | 1 (1 Nov, the registry.json push block) |
| Watchdog alerts raised | 3 (1 Nov 19h stale, 3 Nov 9h, 4 Nov 6h); each re-ran the job |

## Defects found

| # | Defect | Effect | Fix |
|---|---|---|---|
| 1 | One GitHub cron tick per 4-hour candle; GitHub honours roughly 1 in 3 | The 4-hour cadence never held | Ticks at :13 and :43 every hour plus 00:07, behind a gate job that skips in seconds when the candle is in and the last run passed |
| 2 | Watchdog on the same best-effort clock, hourly, 6-hour threshold | Fired 3 of 19 times on 4 Nov; alerted only after 6h | Four off-peak ticks an hour, 4h45m threshold, covers put/call too |
| 3 | No automatic re-run of a failed run | A failure waited for the next tick that GitHub honoured, or for the watchdog | Re-run 1 minute after the 1st and 2nd failure in a row, 15 minutes after the 3rd-5th, then every 30 minutes until it succeeds; alert issue from the 3rd; closes on success (.github/scripts/retry_after_failure.sh) |
| 4 | Coinbase Premium and stablecoin/ETF fetches ran before the commit without continue-on-error | An outage at either source blocked the candle commit | Neither can block the candles; any failure turns the run red after the commit and triggers the re-run |
| 5 | Grade, feed and derivatives steps were continue-on-error with nothing checking them | Silent failures, green run | Run turns red after the commit if any of them failed, which triggers the re-run |
| 6 | No check that fetched candles were current | A fetch that "succeeded" with stale bars would commit as fresh | check_fresh.py: today's 1D bar and the current 4H bar must be there, or the run fails and re-runs |
| 7 | Put/call push loop had no --autostash and no failure exit (the bug fixed in the candle job on 1 Nov) | A blocked push was silent | Same fix; plus the same re-run with cooldown |
| 8 | Dashboard refresh (Claude scheduled task) at :37, 30 minutes after a :07 tick | Uploaded the previous candle whenever the tick was late | Moved to :52; flags "CANDLE DATA DELAYED" when the data is over 5 hours old |
| 9 | Health check thresholds 9h (candles) and 30h (dashboard) | Too loose to catch a missed candle | 5h and 6h, and it now counts every gap over 5h in the last 24h |

## Tested live

Forced failure (workflow_dispatch test_failure): run failed 19:29:25 UTC, re-ran itself
at 19:30:33, succeeded 19:33:37, alert closing job ran. Cooldown arithmetic checked for
streaks 1, 2, 3, 6 and 9.

## What still depends on things outside our control

- Every trigger is still GitHub's best-effort scheduler. More ticks make a missed candle
  unlikely, not impossible. The permanent fix is an outside scheduler (a Cloudflare Worker
  cron calling the dispatch API) on the ETHKROS Cloudflare account.
- The dashboard upload is a Claude scheduled task: it depends on Claude usage. The
  Cloudflare backend reading feed/ctzb_feed.json directly removes that.
