# Audit 47c: damage audit of the ETHKROS member site and pipeline

Code frozen at 78d8276 (read from the frozen states, never the live repo). States: `replay_1111` (clock 2026-11-11T04:20Z) and
`current` (clock 2026-11-20T00:40Z, chain run from refresh.py so the seal is new). All work on copies; nothing in the repo
or the states was edited. All code is my own (`code/`); raw results in `w/*.jsonl`; every case in `all_checks.csv`.

## Top line

1,312 cases: 440 page, 872 pipeline (incl. 21 alert-log sequences and 17 follow-up cases). **1 counted disagreement**,
and it is a limit the family-1 rule already names as outside its claim (below). 0 hardening cases got through. 0 two-fault cases.

### Page level (Playwright, every tab, every picker button, the example switch and both chart modes)

| Family | Cases tried | Got through |
|---|---|---|
| 1 Missing | 17 | 0 |
| 2 Malformed | 101 | 0 |
| 3 Wrong content | 87 | 0 |
| 4 Partial run | 12 | 0 |
| 5 Timing | 24 | 0 |
| 6 Delivery | 131 | 0 |
| Hardening (not counted) | 66 | 0 |
| Not counted (viewer clock wrong, known) | 2 | 0 |

### Pipeline level (the daily.yml chain run in order, CTZB_NOW set, CTZB_STEP_OUTCOMES from each step's exit code)

| Family | Cases tried | Got through |
|---|---|---|
| 1 Missing | 189 | 0 |
| 2 Malformed | 494 | 0 |
| 3 Wrong content | 32 | 0 |
| 4 Partial run | 126 | 1 |
| 5 Timing | 13 | 0 |
| 6 Delivery | (page level) | — |
| Not counted (no-op damage or replay artifact, see below) | 18 | — |

### Disagreements by kind (real-life damage only)

| Kind | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 1 (alert re-emitted) |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

| Level | State | What was damaged | Shown | Expected | Cause |
|---|---|---|---|---|---|
| pipeline | current (earlier state P: two forming alerts pending) | After a clean run emitted the two alerts, all of `feed/` (ctzb_feed.json, alert_log.csv, alert_log_backup.csv) put back to the run before (one fault: a rollback of the folder, e.g. the last pipeline commit reverted) | The next clean run re-emits `BTC-1D-2026-11-22:forming` and `ETH-1D-2026-11-22:forming` with a new `emitted_at` (00:50 instead of 00:40) and logs them again | Each alert emitted once | `feed_live.check_log` (feed_live.py 203-288) has nothing newer than the three files to compare with: the log matches its record, so `pending_alerts` (344) treats both as new. DAMAGE_LIST family 1 states this exact case as outside the rule ("short of ... a rollback of feed/"). The Telegram sender dedupes by `alert_id`, so no member message is sent twice; the feed's own record shows two emissions. Counted because it can happen in real life and the rule has the gap; the owner may rule it accepted. |

## Two-fault (recorded, not counted)

None needed. The nearest case, the alert log and its second copy both lost in one fault (feed/ files lost), fails closed
and stays held until the copy is put back (documented); nothing is lost or emitted twice.

## Hardening (not counted)

66 hand-forged feeds (33 per state): shares above the share they are part of, eras or ladder counts that do not add up,
low after confirmation, ids that do not match, a card twice, a live signal carrying another signal's card, `days_elapsed`
off by one, "rose10" with a 3% best, a withheld feed carrying cards, `scored_as_of` after `generated_at`, miss counts that do
not nest or disagree with `grade_odds`, crossed quartiles, odds-fade rows reversed or marked against their share, another
example id, `grade_odds` duplicated, an example card whose entry close differs from the example file, `price_now` 1 cent
off its chart file, exponent forms, HTML/script in every text field, a 200,000-character sample, RTL unicode, 300-deep
nested junk and 1e308 in unread fields, the 70% bar at exactly 70 and at 69.999999, shares 0 and 100, day 0, quiet markets
(filter on and off), a card with 0 past signals. Every contradiction was refused ("Data unavailable") or, where valid,
shown with the file's own values; no markup was injected, no script error, no placeholder.

## Not counted (and why)

| Cases | Why |
|---|---|
| 4 replay series cases (`ser-1111-*-last row deleted`) | Replay only: `data/*/series_through.json` is dated 2026-11-20, after the replay day, so `fetch.rows_lost_problems` skips it by design and a lost last row (inside the 1-day lag) is scored. On 11 Nov the ETH funding case changed the ETH 1D card (before-2022 count 7 → 6). The same damage on `current` is held. In production the record is never after the run's day. Worth knowing for any test built on replays. |
| 10 no-op damages | The other run's `cards_example.csv` and `pastpaths.csv` are byte-identical; `keep.json` is unused in walkforward mode; candle and funding files are already CRLF (my "CRLF" damage changed nothing; redone as LF and as a real mid-run change: held); a ×1.0 "change" (redone ×1.01: held); feed_live finished before my 0.35 s kill; replay 12H files hold future bars. |
| 1 put/call row with copied values on 19 Nov | Not in the future (put/call ends 18 Nov): an invented but self-consistent value, outside the pipeline's claim. |
| 2 page cases | Viewer clock a day behind the feed (known and accepted). |

Expectations I corrected after looking (all fail-safe or correct, none hide a problem): a blank put/call value is allowed
(no-trade day); a second header row in the ledger is ignored and the record shown is whole and correct; a BTC 2D chart file
cut to its last 12 bars is rightly drawn for the forming setup while the live signal reads "doesn't reach back"; my judge
missed CSS upper-casing and a 60-character note cut.

## What failed safe, by family

| Family | Pipeline outcome (counted cases) | Page outcome (counted cases) |
|---|---|---|
| 1 Missing | 61 stopped at the gate, 76 held, 50 fail-closed, 2 clean with correct figures (series record lost alone) | feed "Data unavailable" 2, ledger "Past signals unavailable" 2, chart unavailable 9, example unavailable 4 |
| 2 Malformed | 242 stopped, 108 held, 90 fail-closed, 54 clean with identical figures (CRLF/LF/mixed line ends, spaces, quotes, exponent forms) | chart unavailable 56, ledger unavailable 16, example unavailable 6, lead file unavailable 10, figures equal the file 13 |
| 3 Wrong content | 30 stopped (another asset/timeframe/run under the name), 2 held | feed down 8, chart unavailable 67 (other asset, other timeframe, older run, other state), example unavailable 6, ledger unavailable 4, correct figures 2 |
| 4 Partial run | 30 fail-closed, 56 held, 18 clean and correct (extras failed: cards published, extras withheld; repeated run; hand run); alert sequences: held, fail-closed, died after the feed, died before the log, feed rolled back, log deleted/cut/emptied/doubled/CRLF/older, copy deleted/cut, feed deleted/cut: every pending alert emitted once | held and fail-closed feeds read "Setups held back"; extras-withheld feed shown correctly; repeated lead-trader events refused |
| 5 Timing | clock a day ahead/behind, 23:59:59, 04:05 before the 4H bar: stopped; scoring at 23:59:50 with the feed at 00:00:10: fail-closed; feed_live alone 3 h later or before its seal: fail-closed; 00:00:00 and 23:59:59 on the replay: clean and correct | stale note at 5 h 01 (not at 4 h 59), on a page left open 5 h and 30 h (reload wording), 2 years old, 1 Jan; close note before and after midnight with both wordings; the self-switched example goes off when stale; trade 1 h ahead refused, 4 min ahead allowed |
| 6 Delivery | — | 404/500/503/empty/HTML-200/cut at 1-99.9%/wrong file for every file: unavailable; BOM, CRLF, text/plain, missing final newline, slow files (3-7 s, all at once): correct figures |

## Part C: the repo's own tests (run on a copy of `current`)

| Test | Result |
|---|---|
| `RENDER_LIMIT=40 REJECT_LIMIT=10 tests/test_feed_damage.py` | 33/33 passed (13 min 52 s; 9,499 damaged feeds per state, page and pipeline agree) |
| `tests/test_seal.py` | 29/29 passed |
| `tests/test_page_timing.py` | 24/24 passed |

What they do not cover (my cases above do): files from different runs or assets served together (feed + ledger, feed + chart
files, a BTC example file under the ETH example's name, a chart of another timeframe under a name); HTTP error bodies,
HTML pages served with 200, BOM/CRLF/text-plain deliveries, slow ledger and all files slow at once; candle and series inputs
changed between steps (data/ files) and step outcome strings malformed; steps killed with SIGKILL, run twice or out of order
against the real scripts; two overlapping runs in one folder; a feed written at 23:50 viewed across midnight; quiet-market
example rules when the feed is stale on arrival or the example file is missing; the alert log across a rolled-back feed/.

## What I could not test, and why

- The Kraken cross-check in enforce mode and every exchange call (no network): Kraken always read "unavailable"; fetch.py,
  fetch_derivs.py and fetch_pcr.py were not run, so their whole-or-nothing writes, `today_from_hourly` and the
  `series_through.json` writes were not exercised.
- GitHub and Cloudflare behaviour: the concurrency group, commit/push and rebase conflicts, the retry job, the mirror's
  15-minute pull and the site Worker were emulated (my router serves exactly what the brief describes), not run.
- The live lead-trader relay (404 here); real browser caches and proxies; font loading (aborted).
- Two runs at once on separate runners (only the same-folder overlap: both runs held).
