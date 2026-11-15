# Audit 36c: damage audit of the ETHKROS member site and pipeline

Independent. I read none of the earlier audits, `analysis/audit*` or `docs/AUDIT_LOG.md`, and wrote all the code myself (`bin/`). I edited, committed and pushed nothing in the repo. All work ran on copies of the two frozen states.

**Page copy:** every page case used the frozen state's `docs/artifacts/member-site/index.html` (md5 3d75ceb9…). That file is byte-identical to the page at commits ee91da1 through 2d856f7. The repo HEAD is now 9c177ca, whose page differs only in wording; I did not audit that version. (The first page batch read the page from the live repo while 9c177ca was landing, so one or two of its cases may have run on 9c177ca's page. Every case flagged in that batch was rerun on the frozen copy.) The pipeline cases use each state's own code.

Entry quality only: every figure here is a computed signal, not a fill or a return.

## Top line

**Disagreements (damage that can happen in real life and got through): 0 of 1954 cases.** 479 cases were at the page level and 1475 at the pipeline level.
Hardening (forged files, not counted): 71 cases; 14 were accepted (see the Hardening section).
Negative controls: 2 deliberately wrong expectations were both flagged, so the judge does catch failures.

### Page level (Playwright, http://site.test/, clock at generated_at + 6 min unless the case sets it)

| Family | General rule meant to catch it (page) | Cases tried | Got through |
|---|---|---|---|
| 1 MISSING | `get()` returns null on a non-OK response or an exception. No feed means "Data unavailable"; no ledger means "Past signals unavailable"; no chart file means "Chart data unavailable" | 98 | 0 |
| 2 MALFORMED | Feed: `feedProblems` (FEED_SCHEMA + crossCheck). Ledger: `parseCSV` dropped/cut, `ledgerRowOk`, duplicates, count and share against grade_odds. Charts: `barsOk`, `stepsOk`, last close = price_now, entry close. Trades: `tradesProblems` | 206 | 0 |
| 3 WRONG CONTENT | The chart file's `chart` name, its steps, last close against `price_now` and entry bar against `entry_close`. The ledger's count and share against the feed. The example's entry close against `example_card` | 64 | 0 |
| 4 PARTIAL RUN | `cards_withheld` reads "Setups held back"; the ledger is shown only with a usable feed; extras are used only when whole | 3 | 0 |
| 5 TIMING | `staleNote()` (over 5 h, or a daily close has passed), re-checked every minute. `chartTok` blocks a late file. The trades 5-minute future rule | 38 | 0 |
| 6 DELIVERY | The same checks as family 2 on a file cut short, empty, an HTML error page (200 or 500), gzip bytes, very late (8 to 9 s), or the wrong content type | 70 | 0 |

### Pipeline level (real steps run in daily.yml order on copies; CTZB_NOW and CTZB_STEP_OUTCOMES set from exit codes)

| Family | General rule meant to catch it (pipeline) | Cases tried | Got through |
|---|---|---|---|
| 1 MISSING | `fetch.history_problems` (check_candles, then again in stack_live). The run seal (a missing file). feed_live's `gone` list, `check_log` and its second copy | 183 | 0 |
| 2 MALFORMED | `_file_problem`, `_row_problems`, `_series_problems` and the 2D-8D bucket check. The seal for datasets/. The strict check before publishing | 937 | 0 |
| 3 WRONG CONTENT | The ETH/BTC close ratio, the 25% intraday asset test, the timeframe step test, the bucket check, the market-column test for series. The seal (an older copy) | 195 | 0 |
| 4 PARTIAL RUN | The seal (steps in order, each once, no file changed). Gating outcomes. Extras files deleted when extras did not succeed. Alert log record and copy | 145 | 0 |
| 5 TIMING | check_fresh (today's bar and the current 4H bar). stack_live's own today-bar check. Seal age of 2 h or less and not in the future. The strict check (scored_as_of is generated_at's day) | 15 | 0 |

### Disagreements by kind (real-life damage only)

| Kind | Page | Pipeline |
|---|---|---|
| (i) wrong or unsupported figure shown | 0 | 0 |
| (ii) raw placeholder, script error or blank area | 0 | 0 |
| (iii) damaged input scored or published without being withheld | 0 | 0 |
| (iv) wording that misstates the state | 0 | 0 |
| (v) reads as a return, trade or track record | 0 | 0 |

## Every disagreement

None among the counted cases. `disagreements.csv` holds only the 14 hardening rows below.

## Hardening (not counted): forged feeds the page and the pipeline accept

Each one below is valid field by field but contradicts itself. Each was published or rendered as a normal feed on both states unless a state is named. None comes from a real writer.

| Forged contradiction | Accepted | Why (no rule covers it) |
|---|---|---|
| A card's typical high (median best) is under +10% while its +10% share is above 50% | both states | crossCheck has no rule linking the median best to the +10% share |
| fell30 is 80% while the typical deepest dip is shallower than −30% | both | No rule linking the median dip to the −30% share |
| Both eras are at 100% never-fell-25.3% while the card's own share is lower | both | Eras are checked against the count only, not against the card's share |
| A forming card confirms in 2028 with bars_to_confirm 2 | both | Only "not before today" is checked; no upper bound from timeframe × bars |
| `checks.failed_steps` names a step while `all_passed` is true | both | failed_steps is not read or checked |
| A live signal's `card.price_now` is 10% off the forming cards' `price_now` for the same asset | both | Prices across sections are not compared (the chart check then refuses that chart) |
| Cards from another run inside this feed | replay_1111 only (current: rejected because they confirm before today) | Nothing ties cards to open signals of the same asset |
| Pipeline: the replay_1111 feed put back as the previous feed | current | The feed was built at an 11 Nov clock on the 15 Nov log, so it is not a feed that can really exist. check_log read it as a run that died before writing the log and appended its 24 alerts to the log (no duplicates, nothing re-emitted). Three genuinely older published feeds from git history (three commits) failed safe |

The other 57 forged page cases were rejected ("Data unavailable") or rendered correctly. These included a card attached to the wrong live signal, duplicate ids, eras that do not add up, rose20 above rose10, rising ladder counts, a low after the confirmation, scored_as_of in the future, days_elapsed off by one, edge status contradicting prices, past paths and odds-fade rows reversed, and the example cloud on another sample. Unusual but valid JSON also passed with the file's own values shown: duplicate keys (last wins), exponent forms, a 20,000-character unicode sample, 400-deep nesting and ±1e308 in unknown fields, and markup or script in every text field (escaped; nothing ran). Boundary values passed too: every share 0 or 100, a ladder share of exactly 70 ("Holds at every level") and 69.999999 shown as 70 (edge marked "−5% before it rises 10%"), price_now 0.01 and 999,999,999.99 (chart refused), a live signal on day 0, and a low dated 1 January.

## What failed safe, by family

**Page (479).** A correct page here means the right figure, or the stated "unavailable" or "held back" text.

| Family | Data unavailable | Setups held back | Past signals unavailable | Chart unavailable | Lead trader unavailable | Stale or close note | Right figures shown |
|---|---|---|---|---|---|---|---|
| MISSING | 27 | 0 | 17 | 52 | 2 | 0 | 0 |
| MALFORMED | 4 | 0 | 20 | 122 | 18 | 0 | 42 |
| WRONG CONTENT | 4 | 0 | 8 | 50 | 2 | 0 | 0 |
| PARTIAL RUN | 0 | 2 | 0 | 1 | 0 | 0 | 0 |
| TIMING | 0 | 0 | 0 | 12 | 2 | 9 | 15 |
| DELIVERY | 20 | 0 | 12 | 20 | 6 | 0 | 12 |

Every page case was also checked for: no pageerror or console error, no NaN, undefined, null, [object, Infinity, ${, n/a% or $- anywhere (chart and cloud SVG text included), no blank card, side box, record count, lead box or filter, and no return or trade wording. Each page case clicked every picker button on Now and Chart, the example switch twice, and both chart-mode buttons on the example.

**Pipeline (1475).**

| Family | Stopped before scoring (feed untouched) | Held feed | Fail-closed feed | Published, equal to the clean run |
|---|---|---|---|---|
| MISSING | 25 | 58 | 93 | 7 (log or copy restored; files not read) |
| MALFORMED | 483 | 126 | 213 | 115 (CRLF, extra or reordered columns, exponents, spaces: same numbers served) |
| WRONG CONTENT | 75 | 76 | 40 | 4 |
| PARTIAL RUN | 0 | 65 | 61 | 19 (whole-chain rerun, feed retry, a "killed" step that finished first, extras withheld only) |
| TIMING | 3 | 0 | 4 | 8 (00:00:00, +2 h, five year-end, leap-day and 23:59:59 replays, feed_live 1 h 59 after the seal) |

Some pipeline cases went beyond the brief's list. A clean replay sequence across a held run, a fail-closed run and a run that died between the feed and the log (with 6 new forming alerts) lost no alert and emitted none twice. A withheld run never changed the alert log. Two runs at once in one folder (5 interleavings) always ended withheld or fail-closed. Scoring at 23:59:30 with the feed written at 00:00:30 failed closed.

Observations that are fail-safe but over-strict (not disagreements):
- CRLF line ends in a 2D-8D candle file withhold the run: it passes the history check, then refresh fails.
- An uppercase `SUCCESS` in the outcomes withholds the run.
- A ledger with a BOM reads "unavailable".
- The 2D-8D cases with a cell padded with spaces publish the same numbers, but the served CSV keeps the spaces.

## C. The repo's own tests (run on a copy of the frozen current state)

| Test | Result | What it does not cover (covered here) |
|---|---|---|
| `tests/test_seal.py` | 29/29 pass | Steps out of order, repeated or interleaved; two runs at once; outcomes that are wrong, missing or uppercase |
| `tests/test_page_timing.py` | 20/20 pass | A viewer clock in the future or years later; a page open across the daily close then 6 h more |
| `tests/test_feed_damage.py` (RENDER_LIMIT=40, REJECT_LIMIT=10; 14.5 min) | 33/33 pass | Single-field feed mutations only. Not covered there: HTTP failures and their combinations; cut, empty or HTML delivery; files from another run, asset or timeframe; cross-section forgeries; ledger damage beyond cells, cuts and duplicates; CSV damage converted by the Worker |

## What I could not test, and why

- The live Cloudflare Workers, mirror sync order, Access gate and real HTTP caching. There is no network or credentials here, so the site Worker's `csvToBars` was ported to Python and the routes were served locally.
- The Kraken cross-check (no network). It was stubbed as unreachable, which the script treats as "not a failure".
- `check_fresh.py` reads the real clock, so its rule was re-implemented on CTZB_NOW for replays.
- Commit/push behaviour (`git pull --rebase` with two runners), GitHub step outcomes and timeouts. Kills were simulated with process kills, and four of the six landed after the step had already finished (refresh, extras, cards, regress). Kills that landed mid-step (grade, stack) and "failed but reported success" were tested separately.
- A real exchange returning altered but self-consistent values. This is out of scope per (5).

## Files

- `all_checks.csv`: 2025 rows (1954 counted plus 71 hardening).
- `disagreements.csv`: the 14 hardening rows; 0 counted.
- `progress.log`
- Code in `bin/` (`pagelib.py`, `page_cases.py`, `page_hard.py`, `page_extra.py`, `judge.py`, `pipe.py`, `pipe_cases.py`, `pipe_more.py`, `alert_cases.py`, `main_pipe.py`, `assemble.py`)
- Run logs `*.log`
- Raw rows: `page_*.json`, `pipe_rows.jsonl`

Re-judged rows (harness expectation errors, each explained in its row's cause):
- 10-bar chart and trades-header judging
- Extras reported failed or skipped (fail-safe by design)
- Closed note at 00:05 after a 23:59:59 feed (correct)
- No example card in a 29 Feb 2024 feed (correct)
- Literal `${x}` from the injection case
- Alert-log checks compared against the pre-damage file
