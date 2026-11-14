# Audit 26, docs against code (independent reviewer)

**Top line:** I read 7 counted documents and checked about 580 statements in them. I found **13 counted findings**: (1) wrong: **1**, (2) stale: **0**, (3) loose or incomplete: **7**, (4) reads as a return, trade or track record: **5**. Outside the counted scope I checked about 200 more statements and noted 11 findings, which are not counted. Every result here is about entry quality only: the data has no exits, so nothing in it is a fill, a strategy return or a track record.

## How it was checked

I worked on a copy of the repo at `audit26d/repo`. In that copy I rebuilt the pipeline from refresh through grade, extras, stack, cards, the regression check and the feed. The run was clean: the feed passed the strict check, 22 cards matched the ledger, and the regression check reported 919 baselined signals unchanged.

- I listed every key in the rebuilt `feed/ctzb_feed.json` (266 paths) and found each one described somewhere in FEED_SPEC.
- I re-ran all 6 Worker test suites. Each count matched cloudflare/README: 21, 26, 21, 41, 25 and 36.
- I rebuilt both generated Workers. Both are in sync with their sources.
- I replayed the gate-off test. It shows 10 forming lows, as its header says.
- I checked commit 4aa1208. It has 4 forming setups, as `build_audit_states.sh` says.
- I recomputed every figure the counted documents quote that can be recomputed:
  - grade pools, with the smallest rule-3 pool at 33
  - first ETH graded signal (21 Mar 2020) and first ETH top-grade signal (18 Apr 2020)
  - 996 trough rows over 6 charts, 176 confluence cells, 12 setups in keep.json, 13 datasets, 11 tags
  - the 51 example bars, the 3/7/11/19/31-day lags, regime on since 2026-09-02, and 58/58 fire drills
  - the ETH dipdist liquidation shares 14/25/27/36%

## Counted findings

| # | File : line | Kind | Quoted (short) | What the code does | Suggested sentence (ready to paste) |
|---|---|---|---|---|---|
| 1 | docs/FEED_SPEC.md:15-17 (also :33, and :406/:419) | 1 wrong | "schema_version goes up by one whenever a field is added … from 6 on, one step per addition again" | `feed_live.py:60` still sets `SCHEMA_VERSION = 6`, but top-level `alert_log` was added on 13 Nov (#22, b6aac76, `:493`) and `alert_log_carry` on 13 Nov (#24, 311da2e, `:553`), and neither raised the version. #22 lists `alert_log` under "Fields not described above" although it was new in that round. | "Fields are only ever added, never renamed or removed. `schema_version` is 6: the 11-12 Nov 2026 additions were batched into schema 6 (12 Nov 2026), and two fields added on 13 Nov 2026 were also added at schema 6 without a bump: top-level `alert_log` (audit #22) and `alert_log_carry` (fail-closed feed only, audit #24)." (Or raise SCHEMA_VERSION and keep the rule.) |
| 2 | docs/FEED_SPEC.md:95 | 3 loose | "`all_passed`: no FAILED line and no failed gating step. `checks.passed` … no FAILED line" | `feed_live.py:196-200,290`: a stack_status.txt that is missing or empty also makes both false. Line 42 of the spec says this. | "`all_passed`: stack_status.txt exists, is not empty and has no FAILED line, and no gating step failed. `checks.passed` keeps its old meaning: stack_status.txt exists, is not empty and has no FAILED line, i.e. the stack check and the card cross-check (verify_cards.py appends to that file)." |
| 3 | docs/FEED_SPEC.md:267 | 3 loose | "its 'on for N days' age stays as of the entry date" | `stack_live.py:605`: for a forming low, the age is measured as of today. | "…(its "on for N days" age stays as of the entry date, or today for a forming low)." |
| 4 | docs/CARD_SPEC.md:81 | 3 loose | "\"below the bar from entry\" when even the from-entry row is" | The page prints "Below the {bar}% bar from entry" on the Now card (`index.html:705`) and "below the bar already" on the Chart tab (`:1114`). | "…; "Below the 70% bar from entry" (Chart tab: "below the bar already") when even the from-entry row is; "Holds at every level" when no row is below the bar" |
| 5 | docs/artifacts/member-site/index.html:298 (same wording at :759 and :1116) | 3 loose | "after it first falls 5%, 10%, 15% or 20%, the share of its past signals that still rose 10%…" | `stack_live.py:420-436` (and `verify_cards.py:76-90`): a row counts only the signals that fell X% **before** rising 10%. A signal that rose 10% first is left out of the row (`:435`). The share is of those signals, not of all past signals. CARD_SPEC:83 states it correctly. | "This setup's own record: of its past signals that fell 5%, 10%, 15% or 20% before rising 10%, the share that then still rose 10% before ever falling 25.3%. The first row, from entry, is the same measure with no fall first. The number of signals is shown on every row." (Wording for :759 and :1116 is in findings.csv.) |
| 6 | README.md:49-51 | 3 loose | "live.csv's `lastPrint` can still name it, but no figure counts it" | `refresh.py:243` builds `dates` from every engine signal, including the one on the open bar. `:341-342` counts it in buy.csv's `agree`. `:361-370` describes it in live.csv's lastEntry, lastTag and daysSince. | "live.csv's `lastPrint`, `lastEntry`, `lastTag` and `daysSince` can still describe it, and buy.csv's agreement count can count it (nothing on the dashboard, the feed or the member site reads that count); no scored figure counts it." |
| 7 | CONTEXT.md:1416 | 3 loose | "`ctzb-feed` (read-only mirror …, works once the repo is private)" | `ctzb-feed-worker.js:1-12`: the mirror serves the repo now (it is public today) and is built to keep working after the repo is made private. | "`ctzb-feed` (read-only mirror of the feed and datasets; live now, and built to keep working once the repo is private)" |
| 8 | CONTEXT.md:1421 | 3 loose | "GitHub email from the watchdog (candles/put-call stale, any step failing 3 runs running, …)" | The watchdog alerts on stale data (`watchdog.yml:98-118`) and on Worker /health (`watchdog.yml:120-178`). The issue for 3 failures in a row is opened by each workflow's retry job (`retry_after_failure.sh:35-46`), not by the watchdog. | "GitHub email from the watchdog (candles or put/call stale, and the Workers' /health as the monitor's backup and dead-man) and from each workflow's own retry job (any run failing 3 times in a row)." |
| 9 | CONTEXT.md:1385-1389, 1398, 1470 | 4 trade | "for the ETH 1D trade … the trade's odds" / "**Trade card**" / "not the number for the trade" | These are computed signals: the CONSOLE RECORD in stack_live, and LABEL at `feed_live.py:66`. | "…for the ETH 1D signal … the signal's odds" / "**Signal card** (called the trade card until 13 Nov 2026)" / "not the number for the signal." |
| 10 | CONTEXT.md:1488 | 4 trade | "each with trades / +20% / -30%" | Counts of past computed signals (`stack_live.py:617`). | "each with its past signals / +20% / -30%." |
| 11 | CONTEXT.md:1495-1497 | 4 trade | "61% on 18 trades … Under 15 trades, say so" | liveread [tag, exact] rows count signals (`stack_live.py:600-602`). | "…61% on 18 past signals, the chart's ordinary rate. … Under 15 signals, say so and give the parent figure beside it, labelled." |
| 12 | CONTEXT.md:1499-1501 | 4 trade | "Odds beside a live trade … next to an open trade reads as that trade's chance" | Open signals are computed signals (open.csv). None was traded. | "Odds beside a live signal are FROM TODAY, never from entry (set 31 Oct 2026). A from-entry figure next to an open signal reads as that signal's chance, …" |
| 13 | CONTEXT.md:1583-1585 | 4 trade | "before the trade's high … the worst individual trades … 60d return" | `tagstats`/`xconf` print computed signals. The day-60 figure is the day-60 close against the entry close (`measure.ret`), not a return on a position. | "lead with the drawdown from entry before the signal's 60-day high (median), then a table of the worst individual signals with columns Chart \| Entry \| Price \| Worst \| On day \| 60d high \| Day-60 change." |

## Documents with zero counted findings

- docs/artifacts/member-site/README.md
- cloudflare/README.md
- The FEED_SCHEMA comments in the member page (its type list matches feedcheck.py and the schema block)

In FEED_SPEC, all of these matched the code and the rebuilt feed:
- Top-level table: posting bar, WINMIN tier rule, next_buy_date, trades_a_year
- The Card fields table
- Schema 4 and Schema 5, the candle_check section, the fail-closed field list, the +10% switch
- Audit #3 to #25 corrections (except rows 2-3 above)

In CARD_SPEC, these matched: the sample rules, the number table, the member table (except row 81), the wording rules and the airtight checks.

In the member page, these matched: every label against the field it shows, the banner, footer, picker, quiet, held and down cards, the Chart tab captions, and the Past signals tab.

In CONTEXT, these sections had no findings: confirmation lag, the setup, regime gate, traps, where things live, open items, and every dated note checked for its superseded marker.

## Outside scope (not counted)

Full rows are in findings.csv, marked "outside scope".

- **feed_live.py:10-11 (1 wrong):** states the same schema-bump rule as finding 1.
- **seal.py:3-4 (3):** says refresh "checks" the seal; in fact refresh starts a new one.
- **check_candles.py:15-18 (3):** the list of whole-history checks leaves out:
  - the 4H/12H presence, timeframe and asset checks
  - the long/short, open-interest and put/call series
- **grade_live.py:34-41 (3):** forward.csv and live.csv each gain more columns than the docstring lists.
- **fetch.py:4 (3):** "Coinbase serves only 1D natively", but the same file pulls 1H candles.
- **extras_live.py:31-33 (3):** "rather than write a half result", but candle files are written one by one before a bad one stops the step.
- **watchdog.yml:6-11 (2):** the 4 Nov heartbeat and "four times an hour" text has no superseded marker.
- **SITE_CHANGES (2):**
  - Pending row 5, "updates each close": superseded by 6k with no note.
  - Pending row 6, "confirmed alerts are final, forming heads-ups can vanish": superseded by 6j with no note.
  - Every other Pending row matches the page on disk.
  - R1, R2 and R3 are indeed not built (no click-through on mini cards, the Chart side box is a summary, no member alert channel).
- **refresh.py:806-808 and the dataset headers (4):** the console says "M of those won", and tier, years and walkforward CSVs use a `trades` column.
- **ctzb-trades /health (noticed, 3):**
  - `ok` needs `last_ok_at` to be under 10 minutes old.
  - In a quiet stretch `last_ok_at` is written only every 15 minutes, so `ok` can read false between check-ins.
  - BRIEF_trades:121-122 expects `"ok": true`. The monitor and the watchdog use 20 minutes.

**Checked with zero findings:**
- PRETRADE statements about code
- BRIEF_site, BRIEF_monitor and BRIEF_dashboard behaviour
- engine, measures, rounding, clock, regimes, tagstats, carddesign, verify_cards, stack_live, feedcheck
- daily.yml, check_fresh, retry_after_failure
- every tests/*.py, *.sh and *.mjs header (counts re-run where quoted)

## Could not check, and why

- **Whether the GitHub repo is public or private** ("Until then this file is public"). I made no outside request about the repo: the container token is invalid, and private details are not to be sent to outside services.
- **Cloudflare deploy ids, live versions, pinned BRIEF commits as deployed, Access, Telegram and R2 behaviour** (656d67c3, 8704c084, 7f50beb7, v35). These live outside the repo.
- **The TradingView verification table and the 68/68 OHLC match in README.** The exports were not re-run.
- **The "1-11 Sep 2020" no-past-signals card window in FEED_SPEC #22.** I checked it by reasoning from the first ETH grade-A signal (2020-07-13, closed 2020-09-11), not by a replay.
- **Historical figures stated with their dates.** These are records, not current rules: 38 of 271 days, 73 ledger rows, 56/56, 480 files and 9,902,744 bytes.
