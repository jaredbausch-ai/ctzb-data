# Loose wording cleanup, 19 Nov 2026

Input: docs/audit/loose_wording.md (68 rows). Working tree only: nothing committed, pushed or branched. Off-limits paths not touched.

| # | Round | File | Done | New sentence (a few words) |
|---|---|---|---|---|
| 1 | 40 | docs/FEED_SPEC.md | changed | "put back to an earlier run's (most often the run before's, because ...)" |
| 2 | 40 | docs/FEED_SPEC.md | changed | "When the log on disk is missing, the copy or a beginning of it" |
| 3 | 40 | feed_live.py | changed | comment: "an earlier run's ...; when the log is missing, is the copy, or is a beginning of it" |
| 4 | 40 | README.md | changed | "for each forming low that matches a tier setup, the date it would confirm" |
| 5 | 40 | .github/workflows/daily.yml | changed | "from this run's ledger, early-dip and day-10 tables and candles" |
| 6 | 41 | member-site/index.html | changed | Typical high: "The median best move within 60 days: how far above the entry close the highest price went, as a percentage." (SITE_CHANGES 6s) |
| 7 | 41 | member-site/index.html | changed | Edge gone: explains "from entry" (Chart tab "below the bar already") and "Holds at every level" (6t) |
| 8 | 41 | member-site/index.html | changed | If it misses: "the median best move ..., as a percentage above the entry close" (6s) |
| 9 | 41 | member-site/index.html | changed | "Misses: median best move"; card row also "median best move" (6s) |
| 10 | 41 | docs/CARD_SPEC.md | changed | "the median best move (% above the entry close) of all those misses" |
| 11 | 41 | docs/FEED_SPEC.md | changed | "median and mean moves and changes 1 decimal" |
| 12 | 41 | README.md | changed | 4H/12H "volume column is always 0 (the hourly volume is not kept)" |
| 13 | 41 | member-site/README.md | left | worker build lags the page (rebuilt separately) |
| 14 | 41 | CONTEXT.md | changed | "[done: the 1D-8D files carry volume; the 4H/12H files carry history with a volume column of 0 ...]" |
| 15 | 41 | fetch.py | changed | hourly(): "Returns {unix_ts: (o,h,l,c)}: the hourly volume is not kept ..." |
| 16 | 41 | member-site/index.html (comment) | changed | "00:00 UTC, when the daily bar, and any 2D-5D bar ending that day, closes" |
| 17 | 41 | member-site/index.html | changed | Lead trader: "On a live or forming setup's card (the worked example has none) ... on that asset ("loading" ...)" (6t) |
| 18 | 41 | docs/FEED_SPEC.md | changed | "A live or forming setup's card that shows figures has a lead-trader line ...; "not in" when his file holds no event on that asset, including none at all" |
| 19 | 41 | docs/CARD_SPEC.md | changed | "(his newest posted event on that card's asset: "in" after an open, add or reduce, "out" after a close, "not in" with none)" |
| 20 | 41 | docs/SITE_CHANGES.md | changed | 6r: "with an ETH position open ... (or "in · short") ...; with none it read out / not in / unavailable" |
| 21 | 42 | docs/FEED_SPEC.md | changed | "has a last bar that opened no later than `generated_at`" |
| 22 | 42 | docs/FEED_SPEC.md | changed | added: live file not reaching its entry bar reads "This chart's data doesn't reach back to the entry" |
| 23 | 42 | member-site/index.html | changed | same as row 6 (handled once) |
| 24 | 42 | member-site/index.html | changed | same as row 8 (handled once) |
| 25 | 42 | member-site/index.html | changed | same as row 9 (handled once) |
| 26 | 42 | member-site/index.html | changed | "What this one did": "Best move" (was "Best price"); CARD_SPEC "best move and deepest drop" (6s) |
| 27 | 42 | docs/CARD_SPEC.md | changed | same as row 10 (handled once) |
| 28 | 42 | member-site/index.html | changed | "posted automatically within about a minute of each fill" (6u) |
| 29 | 42 | member-site/README.md | changed | "damages every field the page reads (every field in the schema) in each of its listed ways" |
| 30 | 42 | cloudflare/BRIEF_site.md | left | pin to the old site-worker build (re-pinned at next deploy) |
| 31 | 42 | cloudflare/BRIEF_site.md | left | describes the pinned old build's page ("Data through"), which is what it shows |
| 32 | 42 | cloudflare/BRIEF_site.md | left | describes the pinned old build's page ("Record" tab), which is what it shows |
| 33 | 42 | cloudflare/BRIEF_monitor.md | changed | added "(This brief's pins are its own deploy's builds; the dashboard Worker has changed since: SITE_CHANGES rows 7 and 7b.)" |
| 34 | 42 | cloudflare/BRIEF_dashboard.md | changed | added "(This pin is the first deploy's build; later builds are in BRIEF_monitor.md and SITE_CHANGES.)" |
| 35 | 42 | cloudflare/BRIEF_trades.md | changed | added "(This pin is the 11 Nov 2026 deploy's build; the 14 Nov build in cloudflare/README.md is not deployed yet.)" |
| 36 | 42 | docs/SITE_CHANGES.md | left | 6q/6r vs unbuilt ctzb-site-worker.js (rebuilt separately) |
| 37 | 42 | engine.py | changed | load(): "Read a candle file (fetch.py's data/*.csv or a TradingView export), clamping flash prints." |
| 38 | 42 | grade_live.py | changed | "(matched by chart and entry date, the confirmation close)" |
| 39 | 42 | feed_live.py | changed | "a failed candle check, a missing card file, a broken or old seal, a damaged alert log, a failed strict check or any crash publishes the fail-closed feed" |
| 40 | 42 fix | fetch.py | changed | "passed the check on every file it reads; the 4H and 12H files with it were committed" |
| 41 | 42 fix | tests/test_input_files.py | changed | "CR CR LF passed the history check on every file; the 4H and 12H files with it were committed" (also the matching line-59 comment) |
| 42 | 42 fix | fetch.py | changed | _file_problem: "holds no blank line and holds no carriage return other than as part of a CRLF line end" |
| 43 | 42 fix | fetch.py | changed | history_problems: "holds no carriage return outside a CRLF line end (_file_problem)" |
| 44 | 45 | member-site/index.html | changed | same as row 7 (handled once) |
| 45 | 45 | member-site/index.html | changed | same as row 28 (handled once) |
| 46 | 45 | member-site/index.html | changed | "sometimes before a signal confirms" (6u) |
| 47 | 45 | tests/numbers_check.py | changed | 2026-11-12: "no forming setup, 23 live signals incl. the BTC 2D top-grade one" (commit 4aa1208 note left out: not checked) |
| 48 | 45 | tests/test_feed_damage.py | changed | "(a state with live signals, no forming card)" |
| 49 | 45 | tests/numbers_check.py | changed | 2020-09-15: "early history: forming cards and live top-grade signals" |
| 50 | 45 | tests/numbers_check.py | changed | 2026-09-07: "nothing forming and no top-grade signal live" |
| 51 | 45 | .github/workflows/daily.yml | changed | "if refresh, grade, stack, cards or regress failed this run; an extras failure withholds only the member-card extras" |
| 52 | 45 | refresh.py | changed | holdcheck: "is the signal green at the day-10 check? Computed signals, no fills." |
| 53 | 45 | analysis/tagstats.py | left | analysis/ is off-limits for this pass |
| 54 | 45 | analysis/tagstats.py | left | analysis/ is off-limits for this pass |
| 55 | 45 | extras_live.py | changed | "rather than write a usable half result ... (candle files written before the bad one stay until feed_live.py deletes ...)" |
| 56 | 45 obs | member-site/index.html | left | behaviour, not wording (live setup chart has no trough marker) |
| 57 | 45 | docs/FEED_SPEC.md | changed | open_signals: "1 to 60 days before today" (the last bar has no close date, so 0 cannot occur) |
| 58 | 46 | cloudflare/README.md | left | worker rebuild note (rebuilt separately) |
| 59 | 46 | docs/FEED_SPEC.md | changed | cards table: added "| `label` | | The computed-signal label |" |
| 60 | 46 | member-site/index.html | changed | same as row 7 (handled once) |
| 61 | 46 | member-site/index.html | changed | If it misses: "(on the worked example, those known by its date)" (6t) |
| 62 | 46 | member-site/README.md | changed | typed figures: "and each chart's bar length (1D 1 day, 2D 2, 3D 3, 5D 5, 8D 8)" |
| 63 | 46 | CONTEXT.md | changed | derivs: "daily (a backfill asks from 2019; each series starts where Coinalyze's does, dates below)" |
| 64 | 46 | docs/SITE_CHANGES.md | left | 6q/6r vs unbuilt ctzb-site-worker.js (rebuilt separately) |
| 65 | 46 | cloudflare/BRIEF_site.md | left | describes the pinned old build's page |
| 66 | 46 | fetch.py | changed | history_problems lag=True: adds "every scored series ends no earlier than the date its fetch recorded (series_through.json, rows_lost_problems)"; CR wording as row 43 |
| 67 | 46 | .github/scripts/check_candles.py | changed | "every file ending with a whole line, with no blank line and no stray carriage return" |
| 68 | 46 | engine.py | changed | same as row 37 (handled once) |

Counts (68 rows): changed 57 (8 of them repeat an earlier row and were handled once), already fixed 0, not true 0, left 11 (5 about the old site-worker build or its pin, 3 BRIEF_site page descriptions tied to that pinned build, 2 in off-limits analysis/, 1 observation: behaviour, not wording).

"median best price" / "Best price" renamed on the page (How to read, card's If-it-misses row, Past signals summary, "What this one did"), in CARD_SPEC and in SITE_CHANGES. No test asserted on the old wording, so no test was changed for it.

SITE_CHANGES Pending rows added: 6s (best move wording), 6t (How to read: Edge gone, If it misses pool, Lead trader), 6u (lead-trader panel subtitle and note).

Observation rows: "left: behaviour, not wording" (row 56). Only one row in the input is marked observation.

## Tests

| Check | Result |
|---|---|
| python3 tests/test_page_states.py | 65/65 passed, exit 0 |
| ast.parse on every changed .py (10 files) | all parse |
| node --check on the member page's script (extracted) | passes; no .js file changed |
| daily.yml loads as YAML | passes |
