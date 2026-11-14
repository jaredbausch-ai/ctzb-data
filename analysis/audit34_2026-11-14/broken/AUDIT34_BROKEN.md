# Audit 34c: damage audit of the ETHKROS member page and pipeline (14 Nov 2026)

Independent run, with my own code only (`code/`). I read no earlier audit material. I edited nothing in the repo and
committed nothing. Everything was run on copies of the two frozen states: `replay_1111`, with 4 forming setups, and
`current`, with none. I also replayed three real dates on copies to test timing: 1 Jan 2026 00:20, 31 Dec 2025 23:50
and 29 Feb 2024. Before attacking anything, I re-ran both states' clean chains: each reproduced its frozen feed
exactly, apart from the time stamps. Each expected result was written into the case files (`code/pcases*.py`,
`code/gcases*.py`) before the case ran.

This audit measures how the system handles damaged files. It produces no strategy return or track record. Every
signal in it is a computed signal, not a fill.

## Top line

**Real-life damage: 0 disagreements** (627 checks, 7 of them no-ops excluded). **Hardening (not counted): 9 forged
feeds got through.**

### Page level (Playwright, every tab, every setup button, the example switch, both chart modes)

| Family | Rule meant to catch it | Cases tried | Got through |
|---|---|---|---|
| 1 Missing (404/500/502/503, network error, every file and combinations) | `get()` returns null on any non-OK answer or throw; each area has its own "unavailable" state (index.html:365, 616-618) | 37 | 0 |
| 2 Malformed (cut, empty, HTML, wrong type, encodings, cells, rows, columns) | Strict check `feedProblems` (FEED_SCHEMA + `crossCheck`); ledger `parseCSV` dropped/cut + `ledgerRowOk`; Worker `csvToBars` + `barsOk`/`stepsOk`; `tradesProblems` | 109 | 0 |
| 3 Wrong content (another asset, timeframe or run; a file served under another name) | Chart: `cd.chart`, last close = `price_now` to the half cent, last bar not after `generated_at`, entry bar = `entry_close`; ledger: top-grade count and +10% share = `grade_odds`; example: entry date, 60 days, entry close = card's | 36 | 0 |
| 4 Partial run (held feed, fail-closed feed, extras withheld, ledger cut by a dead run) | `cards_withheld` → nothing shown ("Setups held back"); ledger needs a usable feed | 8 | 0 |
| 5 Timing (viewer clock ±, 4h59/5h01, two years later, midnight, 1 Jan, 29 Feb, left open 6 h / 3 days, quiet market) | `staleNote()` re-checked every minute; the auto-example turns off when the data goes stale | 25 | 0 |
| 6 Delivery (cut at 6 points, empty, HTML 200, files arriving in any order, slow feed on each tab, never arriving) | The feed is processed before any other file's handler (`await pFeed`, index.html:1267); latest-request token for charts | 57 | 0 |
| Entry quality (dollar size or contract count in lead-trader rows) | The page shows only `price`, `leverage`, `size_pct`, `move_pct`, `account_pct` | 1 | 0 |

### Pipeline level (the steps run in daily.yml order, outcomes taken from exit codes, feed_live run last)

| Family | Rule meant to catch it | Cases tried | Got through |
|---|---|---|---|
| 1 Missing (grade.json, grokpack, PRETRADE, baseline, page file, candle_check.json, series files) | A step crashes and its outcome withholds; feed_live requires `candle_check.structural_ok`; feedcheck reads the schema from the page | 7 | 0 |
| 2 Malformed (every candle file 1D-8D, 4H, 12H: 21 kinds of damage; 13 kinds on 5 series files; encodings; LF/CRLF; duplicated column) | `fetch.history_problems` in check_candles and stack_live; check_fresh | 91 | 0 |
| 3 Wrong content (another asset's or timeframe's file under the name; an older run's file; another run's candle_check) | `history_problems` checks for: ETH/BTC ratio, 2D-8D = daily bucketed, 4H/12H step and asset, market columns, lag | 19 | 0 |
| 4 Partial run (18 datasets × 8 kinds of damage between steps; datasets damaged before refresh; manifest; out of order, skipped, twice; outcomes missing, empty, mistyped, cancelled; steps killed; two runs at once) and alert-log sequences (23) | Run seal (`seal.check`/`problems`/`age_problem`); `CTZB_STEP_OUTCOMES` gating; `check_log` + second copy | 160 | 0 |
| 5 Timing (clock a day ahead or behind, 00:00:00, 23:59:59, midnight between any two steps, feed_live 3 h later, clock stepped back, 4H bar not in; 3 real replays) | check_fresh (today's 1D bar, current 4H bar); stack's "today's bar" check; seal age ≤ 2 h and not in the future; strict check `scored_as_of` = `generated_at` day | 11 + 3 replays | 0 |

### States tried and disagreements (real-life damage only)

| | Page | Pipeline |
|---|---|---|
| Checks run | 273 counted (+59 hardening) | 295 (+ 3 replays) |
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, a trade or a track record | 0 | 0 |

## Every disagreement

None counted. `disagreements.csv` holds only the 9 hardening rows, each marked `counted = no (hardening)`.

## Hardening (not counted): forged feeds the page accepted

Each is a feed hand-forged so that every field is valid but the fields contradict each other. All 9 pass FEED_SCHEMA
and `crossCheck` (index.html:418-518), and the page shows the file's own values. Fifteen other forgeries were refused
as they should be: the live card belongs to another chart, rose20 above rose10, eras or ladder counts do not add up,
`low_day` after `confirms_on`, duplicate ids, `days_elapsed` off by one, `if_it_misses` or `grade_odds` counts off,
`scored_as_of` before the feed's day, a live card's entry close or grade differs, and the odds-fade bar at 50 against
70.

| Forged | What the page shows | Rule that would catch it |
|---|---|---|
| `fell30_within60d_pct` 100 while the median deepest dip is −2% | Both figures on one card | Deepest-dip median must be ≤ −30 when more than half fell 30%, and the reverse |
| 90% rose 10% while the median best move is +2% | Both | Median best move ≥ 10 when more than half rose 10% |
| `typical_day_of_60d_high` 0 with a +50% median rise | "High lands around Day 0" | Day of high ≥ 1 when the rise is above 0 |
| `market_regime` Bearish while forming cards are present | "Market filter: off" plus forming cards | Cards need the gate on (FEED_SPEC Cards) |
| Not withheld while `checks.failed_steps` lists grade (and `checks.passed` false, `all_passed` true) | A clean page | `failed_steps` empty and `passed` true when not withheld |
| Past-paths day-0 median 12% (q25 10, q75 14) | Cloud starting at +12% | Day 0 must be 0/0/0 |
| Forming card `bars_to_confirm` 0 that confirms 5 days later | "confirms 16 Nov" | `bars_to_confirm` 0 ⇒ `confirms_on` is the open bar's close |
| Example card low dates moved, id unchanged | Nothing visible: the example's dates are typed | Example `low_date`/`low_day` fixed |

Lead-trader forgeries (17: future time, order, duplicates, bad words, ranges) all read "unavailable". Unusual valid
JSON (11: duplicate keys, exponents, 84.0, nesting 5,000 deep, 1e308, markup in every text field, 20,000-character
unicode) was shown as the file's values. Markup was escaped and never ran. Boundary values behaved correctly: exactly
70.0 holds, 69.999999 shows as 70 but is below the bar, 100/0 shares, $0.01, $999,999,999.99, day 0.

## Gaps that let damage through without anything wrong being shown (not counted, listed for the owner)

1. **Ledger rule (3) is narrower than written.** A duplicated non-top-grade row, or a header row repeated mid-file, is
   accepted. The duplicate check covers only top-grade rows (index.html:1308). The page shows only top-grade rows, so
   what it displays stays correct.
2. **The regression guard passes an emptied baseline.** `tests/baseline/ledger.json` with its `rows` emptied leads
   to "0 baselined, PASS" and a clean publish. Deleting the file, cutting it, or emptying it to `{}` holds the run as
   it should. The figures still follow from the inputs.
3. **An older copy of `feed/ctzb_feed.json` locks the pipeline closed.** If the previous feed is replaced by an
   older one while the alert log and its copy are intact, every later run fails closed (`check_log`, feed_live.py
   about line 255). Nothing recovers on its own, but the held page still says held runs return "usually within the
   hour". The failure is safe, but it needs a hand repair.
4. **The mirror never drops deleted files.** `cloudflare/ctzb-feed-worker.js` `serve()` returns the KV copy of any
   `datasets/*.csv` even after the repo deleted it. So when extras fails, the chart CSVs that feed_live deletes stay
   served at their last clean version. The page's own `price_now` / `generated_at` check refuses them (the cross-run
   chart cases all read unavailable), so the guarantee rests on that check, not on the deletion FEED_SPEC describes.

## What failed safe, by family

| Family | Page | Pipeline |
|---|---|---|
| 1 Missing | 14 "Data unavailable"; 6 "Past signals unavailable"; 17 file-level "unavailable" (example, charts, lead trader) | 4 held, 2 fail-closed, 1 unaffected (keep.json is not an input) |
| 2 Malformed | 21 ledger unavailable; the rest are chart, example or lead-trader "unavailable", or the file's own values for benign encodings | 66 job stopped at check_fresh/check_candles, 7 held, 2 fail-closed, 16 scored identically (LF/CRLF, spaces, exponents, reordered columns) |
| 3 Wrong content | 4 "Data unavailable", 2 ledger unavailable, the rest chart unavailable | 14 stopped, 3 held (series lag), 2 same (identical inputs) |
| 4 Partial run | 6 "Setups held back", 2 ledger unavailable | 46 held, 42 fail-closed, 54 same where a step rewrites the file (damage before refresh, extras' own files, order changes), 2 extras withheld; alert log: 23 sequences, no alert lost or sent twice; log/copy loss restores or fails closed |
| 5 Timing | 25 correct stale or "closed" notes; the example never stands in once stale | 4 stopped, 4 fail-closed, 1 held, 2 clean at 23:59:59 and within the lag; 3 replays (1 Jan, 31 Dec, 29 Feb) clean |
| 6 Delivery | 24 "Data unavailable" for cut, empty or HTML feeds; 12 file-level unavailable; 19 correct with any arrival order; "Loading" while the feed never arrives | n/a |

## Repo tests (part C)

| Test | Result | Not covered |
|---|---|---|
| `tests/test_seal.py` | 29/29 pass (84 s) | Input files damaged before the candle check, alert-log sequences, outcomes strings |
| `tests/test_page_timing.py` | 20/20 pass (35 s) | Arrival orders other than its own; ledger or feed last with the member on Record or Chart (I covered these) |
| `tests/test_feed_damage.py` (RENDER_LIMIT=40, REJECT_LIMIT=10) | 33/33 pass (13.7 min) | Both its states have **0 forming cards**, so forming-card fields and charts are damaged only through the schema; no files mixed across runs or assets (feed, ledger, chart, example); no HTTP status codes or bodies cut mid-stream; none of the forged contradictions above; no 1 Jan / 29 Feb states |

## What I could not test, and why

- **fetch.py against the exchanges, the Kraken cross-check and the "today's bar from hourly" path.** There is no
  network for these here: Kraken was forced to "unavailable", and the job starts at check_fresh.
- **The Workers themselves.** I emulated the site Worker's `csvToBars` in Python, mirror timing between files, and
  git push/rebase races. Mirror behaviour was read from code only (gap 4).
- **The member page HTML arriving cut short.** It is embedded in the Worker as one response. It would be a broken
  page, not something the page can handle.
- **A browser timeout on a hung feed request.** The page reads "Loading" for as long as the request hangs.
- **Out of scope:** a viewer's wrong device clock, candle values altered but self-consistent, and rewrites by someone
  with repo write access.

Details: `all_checks.csv` (627 rows: level, family, state, what was damaged, expected, shown, ok, counted, cause) and
`disagreements.csv`. Raw results are in `w/*.jsonl` and code in `code/`.
