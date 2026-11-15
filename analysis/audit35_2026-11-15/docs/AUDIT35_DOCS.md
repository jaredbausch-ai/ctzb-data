# Audit #35, docs against code (one pass), code frozen at 5d36e46

Entry quality only. Everything checked here describes computed signals and their 60-day records; there are no fills,
no exits and no strategy return, and nothing below is one.

## Top line

- **Documents read:** 7 counted (docs/FEED_SPEC.md, docs/CARD_SPEC.md, README.md, docs/artifacts/member-site/README.md,
  cloudflare/README.md, CONTEXT.md current-rule sections, the member page's words), and outside the count: the four
  cloudflare/BRIEF_*.md, docs/PRETRADE.md (code statements), docs/SITE_CHANGES.md (Pending and Requested), the
  docstrings and comments of the 20 files in item 5, and the headers of all 30 tests/*.py, *.sh, *.mjs files. Also
  read as code: every file those documents describe, plus docs/artifacts/eth-setup-standard.html (the console card)
  and .github/workflows/watchdog.yml.
- **Statements checked:** about 1,040 (FEED_SPEC ~260, CARD_SPEC ~75, README ~50, member README ~20,
  cloudflare README ~55, CONTEXT current rules ~110, member page ~150, SITE_CHANGES ~90, PRETRADE ~12, BRIEFs ~25,
  docstrings/comments ~150, test headers ~45).
- **COUNTED findings (in scope): 21.** Kind 1 (wrong figure/threshold/window/meaning): 3. Kind 2 (stale): 3.
  Kind 3 (loose or incomplete): 15. Kind 4 (reads as a return/trade/track record): 0.
- **Outside scope (not counted): 12.** Kind 1: 1. Kind 3: 11.
- One root cause carries 9 of the 21: **CARD_SPEC (and CONTEXT) describe the 11 Nov +10% switch and the
  member-card wording as if they applied to "the console's card now"; the dashboard console card
  (docs/artifacts/eth-setup-standard.html) still leads with surv10, labels it "never fell 25%", shows grade letters and
  has its own forming/foot wording.** Either the console card or CARD_SPEC has to change; the suggested sentences below
  fix the doc, and each row says where the console would change instead.

Verification done in a copy (scratchpad/audit35d/repo): full rebuild (refresh .. verify_cards, regression PASS 919
baselined + 2 new, feed 6 cards / 36 prints / 21 open signals) and a field-by-field diff of the feed against FEED_SPEC
(every field in the feed is described; every field the spec names exists; rounding of every float in the feed
matches the stated rule; no -0.0); generated Workers rebuilt byte-identical; the six Worker suites rerun (21, 26, 21,
45, 26, 36: every count in cloudflare/README matches); 16 Python/shell tests rerun on an untouched copy (repo_t;
results in tests_run.log): 15 pass with the counts their headers imply (test_cut_files 495 cuts on 21 files,
test_gate_off 10 forming prints all regime off as its header says). test_page_states.py fails 1 of 56 on the
committed state: "... and under half a cent off: the same price, drawn". The render shows ETH 1D forming, not the
picked live BTC 2D (LIVE_TOP), so the pick at line 115/129 does not hold when forming cards are present, despite the
comment at line 113; the 4-cent case passes only because the shifted file is refused for the forming chart too.
That is a test defect, not a doc sentence, so it is not counted.

## Every finding

Counted (in scope). Full text in findings.csv.

| # | File | Line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| 1 | CARD_SPEC.md | 42 | 2 | "Big number (since 11 Nov 2026): Rose 10% within 60 days ... `reach10`" | Console card (which line 4 says this spec covers) sets its big number to surv10 (eth-setup-standard.html:320), labelled "Rose 10% and never fell 25%" (:99); reach10 is not on it | "Big number on the member card (since 11 Nov 2026): Rose 10% within 60 days of the entry close (`reach10`). The dashboard console card still leads with surv10 and does not show reach10." |
| 2 | CARD_SPEC.md | 43 | 1 | "Line under it: did it without ever falling 25.3%" | Console has no line under it; its caption says "A 25% fall is what wipes out a position at 3.3x" (:99); measure is -25.3 (measures.LIQ) | "Line under the big number (member card): did it without ever falling 25.3% ... The console shows this share as its big number and captions it 'A 25% fall'; the measure is 25.3%." |
| 3 | CARD_SPEC.md | 50 | 1 | era label "Rose 10% and never fell 25.3%" | Console era tiles: "Rose 10% and never fell 25% within 60 days" (:330) | "...surv10 ('rose 10% and never fell 25.3%') split by entry date ... (the console tile still says 25%)" |
| 4 | CARD_SPEC.md | 51 | 1 | "rose 10% BEFORE falling 25.3% ... fell 25.3% BEFORE rising 10%" | Console column heads: "Still rose 10%, never fell 25%" / "Went on to fall 25%" (:106); code counts 25.3% and "before" (stack_live.py:433-437) | "...(the console's heads say 'never fell 25%' / 'fall 25%'; the code counts 25.3% and 'before')" |
| 5 | CARD_SPEC.md | 97-98 | 3 | "no grade letters: ... a card says 'the top grade' or 'the same grade'" | Console card shows "<chart> · <grade>" buttons and "<chart> · <grade> forming" (:314, :317) | "...and on the member card no grade letters ... The dashboard console card shows the grade letter." |
| 6 | CARD_SPEC.md | 107-109 | 3 | "The card always ends by saying ... entry quality only. The dashboard console uses the sentence above" | Console foot (:347-348): past signals, not real trades, past results don't promise; no "entry quality only" | "The dashboard console's foot says these are past signals, not real trades, but not that this is entry quality only." |
| 7 | CARD_SPEC.md | 110-111 | 3 | "A forming low is labelled 'Setup forming' with 'It can still vanish...'" | True on the member card (index.html:742,753-754); console reads "<chart> · <grade> forming" and "Provisional until it confirms." (:317-319) | "On the member card a forming low is labelled 'Setup forming' ...; the console card reads '<chart> · <grade> forming' and 'Provisional until it confirms.'" |
| 8 | CARD_SPEC.md | 73-74 | 3 | "Lead trader: in / out / not in / unavailable" | leadState also gives "loading" and "in · long" / "in · short" (index.html:810-820) | "Lead trader: loading / in · long / in · short / out / not in / unavailable" |
| 9 | CONTEXT.md | 1401-1403 | 2 | "[superseded 11 Nov 2026: the big number is 'rose 10% within 60 days'...]" | The 28 Oct console card this paragraph is about still shows surv10 as the big number, "never fell 25%" (:99, :320) | "[superseded 11 Nov 2026 on the member card and in the feed ...; the dashboard console card still leads with surv10, labelled 'never fell 25%']" |
| 10 | CONTEXT.md | 1480 | 2 | "Source docs/artifacts/eth-setup-standard.html = files/index.html in the artifact DB (v35)." | build_dashboard.py: identical to v38 on 10 Nov; served by ctzb-dashboard since; edited 14 Nov (SITE_CHANGES 7b) | "Source docs/artifacts/eth-setup-standard.html, served by the ctzb-dashboard Worker; it matched the artifact's files/index.html v38 on 10 Nov 2026 and has changed since." |
| 11 | CONTEXT.md | 1472-1474 | 3 | "...the BTC 3D confirmer's own tags (diamond, prime, bucket) with this chart's record after that kind of confirmer" | liveread has only documented grokpack cells (stack_live.py:613-621); for ETH 1D/2D after BTC 3D the confirming tags covered are any and B (diamond for ETH 1D A only); none for a prime-dot or A confirmer | "...and every documented confluence cell that is on (BTC 3D confirmer cells exist for 'any', B and, for ETH 1D A, diamond; none for a prime-dot or A-bucket confirmer)." |
| 12 | FEED_SPEC.md | 16-18 | 3 | "The ctzb-dashboard Worker reads `alerts` from the mirror" | It also reads cards[], prints[], open_signals[] to word each message (alertText) | "...reads `alerts` (and, to word each message, the matching card, print or live signal)..." |
| 13 | FEED_SPEC.md | 24-26 | 3 | "a backup at 43 minutes that the workflow's gate skips when the first run landed the candle" | daily.yml gate also runs it when the last completed run failed or timed out | "...that the workflow's gate skips when the candle is already in and the last completed run passed." |
| 14 | FEED_SPEC.md | 41-44 | 3 | "Its own work is: the time stamp, ..., the aliases, the label and note texts, ..." | Also builds every signal_id and alert_id (sid), the prints' `provisional` flag, the candle_check summary and the odds_fade.sample tier date (feed_live.py:100,493,522,564,586) | "Its own work is: the time stamp, the schema version, the posting bar constant, the signal and alert ids, the aliases, the provisional flag, the label and note texts, the candle_check summary, which alerts are new, ..." |
| 15 | FEED_SPEC.md | 333-334 | 3 | "(a withheld run commits its own feed, which has no record, and no copy)" | A held ("withheld") feed carries alert_log and writes the copy (feed_live.py:637-646; spec 358); the run meant is the fail-closed one | "(a fail-closed run commits its own feed, whose alert_log is then null, and writes no copy)" |
| 16 | README.md | 38-39 | 3 | "a backup at :43 that skips when the candle is already in" | Same gate rule as #13 | "...a backup at :43 that skips when the candle is already in and the last run passed." |
| 17 | cloudflare/README.md | 26 | 3 | "plus `monthly/ctzb-data-YYYY-MM` on the 1st" | Key is `monthly/ctzb-data-YYYY-MM.tar.gz` (ctzb-feed-worker.js backup) | "plus `monthly/ctzb-data-YYYY-MM.tar.gz` on the 1st" |
| 18 | cloudflare/README.md | 60-61 | 3 | "Never dollar amounts, contract counts or balances: every stored record passes an allow-list." | Only events pass the allow-list; the private KV `state` stores contract counts and average prices (trades-worker.js:131,158,246,318) | "...in what it posts or shows on /dry: every trade event passes an allow-list (its private state keeps contract counts to track positions)." |
| 19 | member index.html | 220 | 3 | "Entry, exit, leverage and size as a share of the account; never dollar amounts." | Each trade shows "Price $X", and on reduce/close "Move" and "Account" (:835-840) | "Each trade shows the action, the fill price, leverage and size as a share of the account, and on a reduce or close the move from his average entry and the result as a share of the account; never position sizes or balances in dollars." |
| 20 | member index.html | 653, 733 | 3 | "Nothing forming today." / "Nothing is forming today and no top-grade signal is within its 60 days." | Shown when there is no forming CARD; lows on 8D, with the gate off at the trough or with an empty sample form without one (stack_live.py:565) and are in prints[] | "No setup is forming that gets a card today, and no top-grade signal is within its 60 days." |
| 21 | member index.html (text from stack_live.py:557, 761) | 762, 980, 1157 | 3 | "from all 75 signals of the top grade across all ETH charts whose 60 days had closed by then" | Rule-3 pools are the graded charts only, 1D-5D (stack_live.py:550-552, 757-758); 8D is not in them | "...signals of the top grade across the ETH 1D, 2D, 3D and 5D charts..." (change the two f-strings in stack_live.py) |

Outside scope (not counted).

| # | File | Line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| O1 | analysis/tagstats.py | 5-7 | 3 | "entry = close of the confirmation bar ..., dated by the confirmation bar" | Per-signal tables print `edate`, the confirmation bar's OPEN date, as "entry date" (:169-180) | "...Paths are measured from the day that bar closes; the per-signal tables print the confirmation bar's open date as 'entry date'." |
| O2 | seal.py | 5-6 | 3 | "feed_live.py checks the seal before it builds the feed" | Only when the checks pass (feed_live.py:427-450) | "When the run's checks pass, feed_live.py checks the seal..." |
| O3 | feed_live.py | 17-19 | 3 | "it stamps the time, the schema version, the posting bar constant and the aliases, and words the labels" | Also alerts, log record and copy, held/fail-closed, extras deletion | List as in finding 14 |
| O4 | feed_live.py; tests/test_seal.py | 196, 426, 631; header 7 | 3 | "...which publishes the withheld feed" | An exception publishes the fail-closed feed | "...which publishes the fail-closed feed" |
| O5 | tests/replay_at.sh | 4-5 | 3 | "Used by tests/test_year_end.py and by audits" | Also numbers_check.py, test_feed_damage.py, test_gate_off.sh, test_no_today_bar.sh, test_per_year.py | List them |
| O6 | docs/SITE_CHANGES.md | 17 (Pending 1) | 1 | "+10% counted day 10 to 60" | Page and data count days 11 to 60 (index.html:805; refresh.py ds_earlydip) | "...+10% counted after day 10, days 11 to 60" |
| O7 | docs/PRETRADE.md | 437-441 | 3 | "adds grade / lenses to forward.csv and formingGrade / formingLenses to live.csv" | Also htfDiv, marker; formingHtfDiv, formingMarker, closeNow, closeDate | Name all of them |
| O8 | docs/PRETRADE.md | 332 | 3 | "...the bucket and the BTC 3D confirmer's tags" | As finding 11 | As finding 11 |
| O9 | extras_live.py | 7-11 | 3 | missstats column list | Also peaked_5_or_more, peaked_10_or_more | Add them |
| O10 | analysis/carddesign.py | 7-12 | 3 | "Per asset and grade (A+, A, B, C since 11 Nov 2026...)" | main() reports A+ only; extras_live makes the per-grade rows | "misses() works per asset and grade; extras_live.py calls it for A+, A, B, C; this script reports A+" |
| O11 | .github/scripts/retry_after_failure.sh | 12-13 | 3 | "opened ... and commented on at the 3rd failure and every 6th after" | At the 3rd the issue is opened (comment only if one is open), then comments at 9, 15, ... | "...opened (or commented on, if open) at the 3rd failure, and commented on every 6th failure after" |
| O12 | cloudflare/BRIEF_trades.md | 154-156 | 3 | "A record shows time, asset, long or short, ..., price, leverage and size" | Events also carry instrument, reduced_pct, move_pct, account_pct, held_days | Name them |

## Documents with zero findings

Counted: docs/artifacts/member-site/README.md. Outside: cloudflare/BRIEF_dashboard.md, BRIEF_monitor.md, BRIEF_site.md
(it describes the build it pins, 9a013e3, which is what is deployed); docs/SITE_CHANGES.md Requested rows R1-R3 (none
built); docstrings/comments of refresh.py, grade_live.py, stack_live.py, verify_cards.py, feedcheck.py, engine.py,
measures.py, rounding.py, clock.py, fetch.py, regimes.py, .github/scripts/check_candles.py, check_fresh.py,
.github/workflows/daily.yml; every tests/*.py, *.sh and *.mjs header except replay_at.sh and test_seal.py (O4, O5).

Checked and agreeing, for the record: FEED_SPEC's strict-check list item for item against feedcheck.py and the page's
crossCheck; the 60-day window, the low-before-high ladder, 0.747 and 1.10 levels, the 70% bar on exact shares,
rounding.rnd, round-down of must_close_above, the 1 January bar restart, "known by then" (entry + 60 <= date) in
stack_live, extras_live, grade_live and verify_cards; the regime gate read on the trough bar's open date (engine,
stack_live, prints); the seal's files, order and 2-hour age; the input checks (first days, own gaps 28 Feb 2017 and
25 Oct 2025 verified in the 4H files, lags, 0.1-50% ETH/BTC band); all SITE_CHANGES Pending rows 1-7b against the page
and the dashboard page (except O6); recomputed figures: 13 refresh datasets, 176 confluence cells (83+49+44), 26
dispatches a day, 996 troughs on 6 charts, 12 keep.json setups, 11 candidate tags, 51 example bars (12 Aug - 20 Nov
2024), example sample 75, first graded ETH signal ETH 3D 21 Mar 2020 C, first ETH A+ 18 Apr 2020, smallest rule-3
pool 33 (BTC A+), 95 misses of 313 BTC C, dipdist shares at 3.3x A+ 14 / A 25 / B 27 / C 36 % (ETH), 13 numbers_check
dates, gate on 2026-09-02, fire_drills_result 58/58, the 21 files test_cut_files covers.

## Could not check

- Anything only true outside the repo: deployed Worker versions (656d67c3, 8704c084, 7f50beb7, 40a4475b), the cron
  strings configured in Cloudflare (ctzb-feed */15, ctzb-dashboard 5,20,35,50 are stated only in comments/briefs),
  Access policies, R2 lifecycle, Telegram delivery, the claude.ai artifact URLs and versions, GitHub run history
  ("133 committed runs", "32 of 32 ticks", the 31 Oct stall).
- External measurements: the TradingView bucketing match (297 signals, 68 OHLC values), Kraken gap statistics,
  Coinbase contract size and leverage limits.
- tests/fire_drills.py, tests/test_feed_damage.py and tests/numbers_check.py were not rerun (long, browser-bound
  replays); their headers were read against their code. CONTEXT's 58/58 matches tests/fire_drills_result.json.
- Research results in CONTEXT/PRETRADE/README (dated figures) were not re-derived, per the brief.
