# Fix check 35 (clean run #1): commits cf6b4ec, ee91da1, 732549e after 5d36e46

Independent check on copies (`repo/` = HEAD 732549e, a 5d36e46 copy, removed after use). Nothing in the repo was edited. Entry quality only:
the site shows computed signals, never fills, and nothing here is a return or a track record.
Runs: test_page_states 64/64 (on HEAD); the same test with 5d36e46's index.html, feedcheck.py and feed_live.py 62/64, and the 2
failures are the two new checks; test_page_timing 20/20; numbers_check exit 0 (13 dates); test_site_worker 26/26;
test_dashboard_gate 26/26; test_feed_damage (RENDER 40 / REJECT 10) 33/33. Both Workers rebuild byte-identical.
Own harness `tools/loadcheck.py`: 12 states, 132 page sessions, 1,656 checks, 864 of them after a picker or example pick.
118 replays through `tests/replay_at.sh` (`tools/sweep.sh`).

| Id | Verdict | Evidence | Smallest change if not fixed |
|---|---|---|---|
| N1 example extras with no example card | fixed | feed_live.py:616,624 write them only with `example_card`; feedcheck.py:197-198 and index.html:515 apply the same rule (null when there is no card). 118 replays, 2020-09-03 to 2026-11-13 every 23 days, every day 14-30 Nov 2024, and clocks 21 Nov 00:13 / 23:59 and 22 Nov 00:00:30: the extras are there exactly when the card is (77 without, 41 with; switches on 22 Nov), every feed passes feedcheck, none fail closed. Real feed_live runs (held, fail-closed, extras withheld) on 3 dates also pass. The page and feedcheck refuse a feed carrying them with no card (the test fails on 5d36e46) | - |
| B1 stale "Loading" under the cloud | fixed | index.html:1107-1111 sets #cloudSub/#cloudNote before returning. Harness on 5d36e46 (extras withheld): "Loading <chart>" under the cloud on every pick. On HEAD: 0 of 1,656 checks still say "Loading" after the files arrived or failed. States: as built, clean, forming only, live only, no example, quiet with the filter on, quiet with it off, held, fail-closed, extras withheld (with example, without example, quiet). Every tab; first/last live and forming buttons and the example (alert and What happened) on the Chart tab; the example switch. Each file (feed, ledger, trades, example, candles) late; all late; others 404 / abort / empty / HTML, at once or after 2.5 s; feed 404 / empty / late+abort. No page errors | (test_page_states checks one pick per state; the harness's per-button loop would make the repo test cover the family) |
| D1-D7 CARD_SPEC console rows | fixed | CARD_SPEC:43-52, 99, 109-113 against eth-setup-standard.html:99, 106, 314, 317-320, 330, 347-348 and stack_live.py:433-437 | - |
| D8 lead-trader states | fixed | CARD_SPEC:75; index.html:810-820 (direction is required by the schema, so a plain "in" never shows) | - |
| D9-D11 CONTEXT | fixed | CONTEXT:1402-1404; :1482-1484 with build_dashboard.py:4; :1474-1476 with stack_live.py:516-519, 613-621 and grokpack layer4/4_small BTC 3D cells (any, B, and diamond for ETH 1D A only) | - |
| D12 dashboard reads alerts | incomplete | FEED_SPEC:16-17 is right (dashboard_worker_template.js:146-149), but cloudflare/README:47-49 still says it reads the feed's `alerts` only | fix cloudflare/README:48 (csv) |
| D13 / D16 the :43 gate | incomplete | FEED_SPEC:26-27 and README:39 are right (daily.yml:57-62), but CONTEXT:230-232 (Where things live) still says it skips "when the :13 run already landed the candle" | fix CONTEXT:231 (csv) |
| D14 feed_live's own work | fixed | FEED_SPEC:43-47 against feed_live.py:100, 493, 522, 564-568, 588 (ee91da1 then added a step the list leaves out: see the failing sentences) | - |
| D15 fail-closed record | fixed | FEED_SPEC:338; fail_closed carries prev_log_record (feed_live.py:664-670, 749), which is null when the previous feed has no record; it writes no copy | - |
| D17 monthly key | fixed | ctzb-feed-worker.js:261 | - |
| D18 trades relay, no counts | wrong | cloudflare/README:60-62 says there are no contract counts in what /dry shows. /dry returns `review_notes` (ctzb-trades-worker.js:439), and every reconcile note reads "tracked N contracts, Coinbase shows M" (:316). CONTEXT:1420-1422 still says "percentages only, never dollar amounts or contract counts", but each posted trade has its fill price and leverage | csv rows 1 and 3 |
| D19 lead-trader panel | fixed | index.html:220 against :835-840 (the fill price is a dollar price; no sizes or balances in dollars) | - |
| D20 "No setup with a card" | fixed | index.html:653, 733; stack_live.py:557-565 | - |
| D21 sample wording | incomplete | stack_live.py:557, 761 are right and the baseline moved only that wording (below); CONTEXT:1388-1389 (Standing instructions) still says "the same grade across the asset's charts" | fix CONTEXT:1389 (csv) |
| O1-O3, O5-O12 | fixed | tagstats.py:169-180; feed_live.py:428-451; replay_at.sh users (7 tests grep'd); SITE_CHANGES:17 with index.html:805; grade_live.py:292, 332; MISS_FIELDS extras_live.py:52; carddesign.py:154; retry_after_failure.sh:35-45; EVENT_FIELDS ctzb-trades-worker.js:51-52 | - |
| O4 "withheld" for fail-closed | incomplete | lines 197 and 427 corrected; feed_live.py:633-634 still "crash, which publishes the withheld feed" (also :731, 764, 776, 778 and test_seal.py:168) | "...publishes the fail-closed feed" |
| Baseline re-approval cf6b4ec | only what it says | Against 5d36e46: every changed dataset/feed text is the exact "across all <asset> charts" to "across the <asset> 1D, 2D, 3D and 5D charts" swap; page numbers changed only by inserting 1, 2, 3, 5 at each sample line; nothing else on any of the 13 dates | - |
| Baseline re-approval ee91da1 | only what it says | Against cf6b4ec: only `example_if_it_misses` and `example_past_paths` (object to null) in feed/ctzb_feed.json, on the 7 dates before 22 Nov 2024; the 6 later dates are identical | - |
| Workers | identical | build_site.py 139,781 bytes and build_dashboard.py 65,347 bytes; git status clean after both | - |

## Changed or nearby sentences that fail (full text in failing_sentences.csv)

Counted scope (7: 2 new, 1 wrong correction, 4 repeats left uncorrected):
1. cloudflare/README.md:60-62 (wrong; this is D18's correction). "...or shows on /dry" is false: /dry shows the contract counts in its review notes
   (ctzb-trades-worker.js:316, 135-137, 439).
2. CONTEXT.md:230-232. The :43 tick also runs when the last completed run failed or timed out (daily.yml:59-60).
3. CONTEXT.md:1420-1422. "percentages only, never dollar amounts or contract counts": the fill price and leverage are posted
   (EVENT_FIELDS :51-52; index.html:838), and the private state and /dry hold contract counts.
4. CONTEXT.md:1388-1389. The last-resort pool is the 1D, 2D, 3D and 5D charts only (stack_live.py:549-551).
5. cloudflare/README.md:47-49. To word each alert it also reads the card, print or live signal (dashboard_worker_template.js:146-149).
6. docs/CARD_SPEC.md:117-121 (new section, loose). Its list of differences leaves two out. The console states its sample rule in its foot
   (html:347-348), not under the big number as CARD_SPEC:27-28 and :105 require of a card. With no card it reads "Nothing forming /
   No chart has a low forming right now." (html:311), the claim D20 corrected on the member page.
7. docs/FEED_SPEC.md:43-47 (new looseness from ee91da1). feed_live's own work now includes leaving the example's extras out when
   there is no example card (feed_live.py:616, 624). The list does not name it.

Outside scope (6): feed_live.py:633-634 and 731/764/776/778, test_seal.py:168 ("withheld" for fail-closed); stack_live.py:554
liveread label "Grade {g}, all {a} charts" and comment :545 (same as D21); daily.yml:8-9 comment (same as D13); eth-setup-standard.html:311
(same as D20, console); CONTEXT.md:538 "no grade letter is shown anywhere" (the console shows them, html:314/317);
BRIEF_trades.md:155-157 (the reduced share is set only on a reduce, ctzb-trades-worker.js:238).

No history words in the changed spec sentences (the "still"/"now" in CONTEXT:1403-1404 are in a dated note). Wording rules are
held throughout: signals, not trades; the only trades named are the lead trader's own. Not checkable here: whether the console
(SITE_CHANGES 7b) and the member page are deployed with these words.
