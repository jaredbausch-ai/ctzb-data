# Fix check, audit round 26 (independent)

Checked: b6eb046, 42cdc9c, 3bc0f0f and the FEED_SPEC rewrite (now committed as ac49945, same text as the working tree I
read). Pre-fix runs used a copy with single files checked out at b6eb046. Repo not edited. Everything here is entry
quality only: computed signals, never fills, no return or track record.

Tests run: test_cut_files 496/496 (pre-fix fetch.py 468/496); test_page_timing 10/10 (pre-fix page 9/10);
test_seal 23/23; test_check_candles 95/95; numbers_check FAILS on HEAD (row N0); site Worker rebuilt in a copy: in sync.

## Findings

| Id | Verdict | Evidence | Smallest change if not fixed |
|---|---|---|---|
| D1 schema_version | fixed | FEED_SPEC:35-37 matches feed_live.py:60, :359, :539; alert_log no longer filed as old | (new wording fails 4: see sentence 2) |
| D2 checks.passed / all_passed | fixed | FEED_SPEC:272, 276, 311 match feed_live.py:196-200, 289-290 | |
| D3 regime age, forming low | fixed | FEED_SPEC:183 matches stack_live.py:605 | |
| D4 CARD_SPEC:81 | fixed | index.html:705 "Below the {bar}% bar from entry", :1114 "below the bar already" | |
| D5 page odds-fade text | fixed | index.html:298, 759, 1116 match stack_live.py:420-436 | old wording survives only in code comments index.html:558, 976 |
| D6 README:49-51 | fixed | refresh.py:243, 341-342, 361-370 | |
| D7 CONTEXT:1416 | fixed | ctzb-feed-worker.js:1-12 | |
| D8 CONTEXT:1421 | fixed | watchdog.yml:98-178; retry_after_failure.sh:35-46 | |
| D9, D10, D11, D13 trade wording | fixed | CONTEXT:1385-1389, 1398, 1470, 1488, 1495-1497, 1583-1585 | |
| D12 "live trade" odds rule | incomplete | Same standing rule at CONTEXT.md:847: "From-entry odds next to a live trade read as that trade's chance ... past graded trades" | "live signal", "that signal's chance", "past graded signals" |
| P1 stale hour count | fixed, tested | index.html:1221-1232; test_page_timing 4c fails on b6eb046 page (every tab "5"), passes now | |
| B1, B1a, B1b, B2 cut / blank volume | fixed, tested | fetch.py:153-155 (blank volume fails), :185-193 `_cut_short`, :315-340 (no silent skip); test_cut_files 28 cuts pass pre-fix, 0 now. My probe: 2D/3D/5D/8D cut after a comma with 0/1/3/30 rows lost, and one blank volume mid-file on 1D/2D/8D/4H/12H: all caught | |
| N1 scaled20 open bar | fixed, tested | measures.py:30; numbers_check --dates 2021-06-25 with pre-fix measures.py adds ledger.csv, grades.csv, cards_open.csv changes; none with the fix | |
| N0 numbers_check ("nothing else moved") | wrong | Fails on HEAD: 52 items over all 13 dates. All in candle_check.json, manifest.json, alert_log.csv and the feed's alerts (2 `:vanished` alerts per date for ETH/BTC-1D-2026-11-16). The replay copies live repo state uncut (feed/alert_log.csv, datasets/candle_check.json, data/derivs, data/options; replay_at.sh:10-16). The baseline in 42cdc9c predates its own parent c1573d9 (baseline checked_at 21:56, 42cdc9c^ has 00:14), so it never passed on its commit, and it will break on every 4-hour run. No dataset figure or page number moved. | replay_at.sh: cut data/derivs and data/options to the date, start from a fixed alert-log/feed fixture (or seed), regenerate or drop candle_check.json; then re-approve |
| Outside scope (11, not counted) | 4 fixed | feed_live.py:10-11, seal.py:3, fetch.py:4, SITE_CHANGES row 5. Commit message says 5 | Untouched: SITE_CHANGES row 6, check_candles.py:15-18, grade_live.py:34-41, extras_live.py:31-33, watchdog.yml:6-11, refresh.py console "won" / `trades` column, BRIEF_trades /health |

## FEED_SPEC rewrite: 12 sentences fail (full rows in failing_sentences.csv)

No history wording (no "Audit #N", "now", "used to"), and the wording rules hold throughout. Failures:

1. :23-24 (5) Only the scheduler is named. Re-runs after a failure, the watchdog's re-dispatch and manual runs skip the gate and also write a feed (daily.yml:51-56).
2. :35-37 (4) "Nothing computes or checks it". Two tests assert it is 6 (test_feed_extras.py:79, test_feed_alerts.py:72).
3. :43 (4) "times ... ending in Z". `candle_check.checked_at` is "2026-11-14T00:14:01+00:00" (check_candles.py:129), and the spec does not name it as an exception.
4. :50-52 (5) "medians ... 1 decimal". The four `typical_day_*` medians are whole days (stack_live.py:474).
5. :78 and its rows (5) Blank Strict cells on fields the strict check reads: `checks` (all_passed bool), the extras row, `from_entry`. The `typical_*_pct` rows show rise?/dip?, but only the `_exact_pct` field is checked (index.html:377 schema).
6. :116-119 (5) Grade, confirmations and the sample wording are not re-derived either. verify_cards takes them from the card (verify_cards.py:110-118).
7. :338-341 (4) "every list empty". `alert_log_carry` is a list and can be non-empty (feed_live.py:553).
8. :366-368 (5) check_candles also stops the job on its own recent-window checks: a missing day, bad prices or zero volume on the last 90 closed daily bars, bad 4H prices, an unreadable file (check_candles.py:48-72, 140-148). A zero-volume closed day passes "volume not negative" but stops the job.
9. :381 (5) The freshness check also requires the current 4H bar (check_fresh.py:24-36).
10. :382-383 (4) "The fetchers write each file whole". Only fetch.py, fetch_derivs.py and fetch_pcr.py do; fetch_flows.py, fetch_onchain.py and fetch_basis.py write in place.
11. :391-394 (4/5) `n` must also be under a million (feedcheck.py:51). Most lists have only a minimum length (`"cards": ["@card", 0]`; feedcheck.py:76).
12. :395-411 (5) Three enforced cross-field rules are missing:
    - from-entry share between the never-fell and +10% shares (feedcheck.py:110-111)
    - ladder shares adding to at most 101 (:116)
    - grade_odds figures vs count, and the shares nesting (:176-180; index.html:490-492)

**Old-file check:** both rows coverage.csv marks obsolete are obsolete. The old file marks both superseded itself
(history :316, :332), and the page has no "Status unavailable" (`edge_status` is required, index.html:377). Two true
statements were lost:
- old :7-8, that the feed is the one agreed in the plan with Joe (`docs/joe/...` files)
- old :119, that `past_paths` and `example_past_paths` draw the Chart tab's past-signal cloud (index.html:1056, 1075); the new page section never says what the page does with them
