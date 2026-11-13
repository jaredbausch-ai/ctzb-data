**Audit #25 (docs against code): 7 in-scope documents read, about 640 statements checked, 24 findings: (1) wrong 2, (2) stale 7, (3) loose or incomplete 15, (4) reads as a return / trade / track record 0. Five more outside scope, not counted.**

Scope (owner, 13 Nov 12:56 ET): the member page's own words, docs/FEED_SPEC.md, docs/CARD_SPEC.md, README.md, docs/artifacts/member-site/README.md, cloudflare/README.md, and the CONTEXT.md sections that state current rules. Repo state: commit a44c348. Everything was checked read-only. The feed was rebuilt in a copy (refresh, grade_live, extras_live, stack_live, verify_cards, regression, feed_live), and it matches the committed feed field for field, timestamps aside. Details for every row are in findings.csv.

Entry quality only. Everything here describes computed signals' 60-day records. There are no fills, no exits and no strategy return.

## Every finding (in scope, counted)

| # | File | Line | Kind | Quoted sentence (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| F1 | FEED_SPEC | 21-22, 95 | 3 | cards_withheld when stack_status.txt "has a FAILED line" or a gating step failed; checks.passed = "no FAILED line" | feed_live.py:196-200 `ok = bool(lines) and not failed`. A missing or empty stack_status.txt also withholds the cards and sets checks.passed false | "...whenever `stack_status.txt` is missing, empty or has a FAILED line, or any gating step ... did not report success." |
| F2 | FEED_SPEC | 22-24 | 3 | "A broken run seal, a missing dataset, a damaged alert log or a feed that fails the strict check publishes the fail-closed feed" | feed_live.py:301-302 also fails closed when step outcomes are set and candle_check.json does not say `structural_ok` true. This is stated only at line 446 | "A broken run seal, a missing dataset, a candle check that did not pass (when step outcomes are set), a damaged alert log or a feed that fails the strict check publishes the fail-closed feed instead (feed_live exits 1)." |
| F3 | FEED_SPEC | 44 | 3 | trades_a_year: "'—' when there are none" | refresh.py:391-405, 715: "—" appears when the tier has fewer than 4 scored signals (tier.csv gets no row). With none at all, refresh.py stops at line 383 and the feed is held | "...'—' when the tier has fewer than 4 scored signals (with none, refresh.py stops and the feed is held)." |
| F4 | FEED_SPEC | 57 | 3 | must_close_above: "Confirms at the close if price closes above this" | stack_live.py:377-390: exact only when the confirmation bar is the bar now open. When it is the next bar, it is an estimate that assumes today's bar closes at the latest price. Empty when two bars away. Rounded down to the cent | "The confirmation-bar close above which the low confirms (rounded down to the cent): exact when the confirmation bar is the bar now open, an estimate when it is the next bar, empty when further off (CARD_SPEC)." |
| F5 | FEED_SPEC | 72 | 1 | active_confluences: "Every confluence cell active for this setup today" | stack_live.py:613-625: the confirming signal must fall 0-10 days before `confirms_on`, not before today. A window open today that closes before the confirmation date is left out | "Every confluence cell that will be active when this setup confirms (its confirming signal 0-10 days before `confirms_on`), weak ones included: ..." |
| F6 | FEED_SPEC | 134-138 | 2 | Fail-closed feed: "a feed with every list empty" | feed_live.py:536-550: since audit #24 it carries `alert_log_carry`, which can be non-empty. It also lacks `alerts_seeded`, `signals_a_year`, `odds_fade.tier_fixed_on` and `odds_fade.edge_measured_on`, which every other feed has | "...every signal, card and figure list empty (`alert_log_carry` may hold alerts the last feed sent that the log lacks) ... It has no `alerts_seeded`, `signals_a_year`, `odds_fade.tier_fixed_on` or `odds_fade.edge_measured_on`." |
| F7 | FEED_SPEC | 244-245 | 2 | "How to read says a confirmed alert is final while a forming heads-up can vanish" | index.html:287 now reads "A confirmed setup is final and can't vanish. A forming setup can: it is shown before the confirming close." | "...How to read says a confirmed setup is final while a forming setup can vanish." |
| F8 | FEED_SPEC | 312-313 | 2 | "with no edge_status its badge reads 'Status unavailable'" | edge_status is required by FEED_SCHEMA (index.html:377). A feed without it is rejected whole ("Data unavailable"). The words "Status unavailable" are no longer on the page (index.html:822-827) | "[superseded 13 Nov audit #21: a live signal with no or an unknown edge_status fails the strict check; the page reads 'Data unavailable'.]" |
| F9 | FEED_SPEC | 326-330 | 2 | withheld cards "ignored even if present"; a non-number price prints "n/a"; an unknown edge_status reads "Status unavailable"; an unknown market_regime reads "Market filter: unavailable" | Since audit #21 each of these fails the strict check (index.html:446, schema `px`, `=lost\|rose10\|intact`, `=Bullish\|Bearish`) and the whole feed is dropped: header "Feed unavailable" (851), card "Data unavailable". Only a missing market_regime reads "Market filter: unavailable" | "[superseded 13 Nov audit #21: each now fails the strict check and the page drops the whole feed; only a missing market_regime reads 'Market filter: unavailable'.]" |
| F10 | FEED_SPEC | 439 | 2 | "the page now says so (banner and How to read)" | Only the review banner says it (index.html:194). How to read (285-303) has no sentence about alerts | "...member alerts are not switched on, and the page's review banner says so; the alert promises are gone." |
| C1 | CARD_SPEC | 56 | 1 | Active confluences: "Every confluence cell active for this setup today" | Same as F5: counted against `confirms_on`, not today | "Every confluence cell active on the date this setup would confirm (its confirming signal 0-10 days before that date), weak ones included, ..." |
| C2 | CARD_SPEC | 79-80 | 2 | Feed field `typical_biggest_rise_pct` / `typical_deepest_dip_pct` / `typical_dip_before_rise_pct` "(+ their *_exact_pct)" | index.html:626 reads only the three `*_exact_pct` fields and rounds them once (FEED_SPEC 486-487, audit #24) | Feed field: "`typical_biggest_rise_exact_pct` / `typical_deepest_dip_exact_pct` (rounded once for display)" and "`typical_dip_before_rise_exact_pct` (rounded once)". |
| C3 | CARD_SPEC | 118-121 | 3 | verify_cards "recomputes every figure on the card" | verify_cards.py:106-155 re-derives only the figures computed from the sample. The kill close (a card number, line 52), latest price, entry close, dates and confluences are not re-derived (FEED_SPEC 226 says so) | "...recomputes every figure computed from the card's sample: n, the big number, ... The card's dates and prices (low day, confirms, must close above, latest price, entry close) and its confluences are not re-derived there." |
| R1 | README | 76-77 | 3 | "`--today YYYY-MM-DD` overrides it for testing" | refresh.py applies --today to main() only. _daily_windows (553-555), ds_forward (659-661) and status "Updated (UTC)" (717) read clock.now_utc(), so earlydip, holdcheck and forward still use the real date | "The date comes from the clock (`CTZB_NOW` replays a past run whole); `--today` overrides only the tier anchor, status and buy / walk-forward dates, not earlydip, holdcheck or forward." |
| R2 | README | 49-51 | 3 | "every scoring step drops it ... so it shows only as forming" | refresh.py:357-374 writes the engine's last signal, which can sit on the open bar, into live.csv as lastPrint / lastEntry / daysSince | "...every scoring step drops it until that bar has closed; live.csv's lastPrint can still name it, but no figure counts it." |
| M1 | member-site README | 3-5 | 3 | "the live site is the `ctzb-site` Worker built from it" | The deployed Worker is 656d67c3, built from 9a013e3 (SITE_CHANGES "Deployed"). Pending rows 1-6j are in this file but not live | "The current page is this file. The live site runs the `ctzb-site` Worker last deployed from an earlier build (656d67c3, from 9a013e3); later changes are listed as Pending in docs/SITE_CHANGES.md." |
| P1 | member page | 194 | 3 | "when they are, they will cover top-grade setups only" | Undecided: SITE_CHANGES R3 lists "top grade only" as still to decide (on hold). The pipeline's alerts today cover every grade (feed_live.py:326-328) | "Member alerts aren't switched on yet; which setups they will cover is still to be decided." |
| P2 | member page | 230 | 3 | Previous signals: "updates each close" | The page loads its files once (boot, 1199-1260). Left open, it never refetches; it only shows the stale warning after 5 hours | "as of the latest data · reload for each 4-hour update" |
| P3 | member page | 624 | 3 | "confirms <date> if it closes above $X" | With bars_to_confirm 1 the price is an estimate that assumes today's bar closes at the latest price (stack_live.py:377-390; CARD_SPEC 52). The page states it flatly | When bars_to_confirm is 1: "confirms <date> if it closes above about $X (an estimate until today's bar closes)". |
| X1 | CONTEXT | 160-162 | 2 | "The dashboard still uses the symmetric one and is inflated accordingly." | The dashboard reads status, live, grades, forward, dipdist, cards, liveread, prints and windows (README 84-85), and none of them carries the symmetric count. tier, confluence and buy.csv still use `abs(days) <= 10` (refresh.py:250, 341, 466), but nothing reads them. The AGREE lens and the windows count backward only (stack_live.py:167, 273, 715-721) | "refresh.py's tier.csv, confluence.csv and buy.csv still use the symmetric count; nothing on the dashboard, the feed or the member site reads them (the AGREE lens and the confluence windows count only prints 0-10 days before)." |
| X2 | CONTEXT | 115-116 | 3 | "Every row's date field is the confirmation bar's close date" | live.csv `lastEntry` (refresh.py:364, `edate`) is the confirmation bar's OPEN date: ETH 3D shows 2026-09-22 for the signal that confirms 2026-09-24. refresh.py's tier dating also uses the open date (FEED_SPEC 340-342) | "Every date field in the ledger, cards, prints, open signals and forward record is the confirmation bar's close date ...; refresh.py's live.csv `lastEntry` and its tier statistics still use the open date." |
| X3 | CONTEXT | 1393 (vs 220) | 3 | "The v16/v10 scripts keep the asterisk ETH grade." | No v16 indicator or v10 scanner exists in pine/ or docs/reference/. Line 220 and pine/README.md name v15 and scanner v9 as live, and say pine/ holds every Pine source | Commit v16 / v10 to pine/ and update line 220, or write "The live scripts (indicator v15, scanner v9) keep the asterisk ETH grade." |
| X4 | CONTEXT | 1463-1465 | 3 | liveread gives "each lens on vs off this chart" | stack_live.py:586-591 writes one record per lens, for its current state only (`rec(on if v else off)`), never both | "...each lens's state (ON / off) with this chart's record in that same state, ..." |
| X5 | CONTEXT | 1486 | 3 | lists "the cells that are ON right now (liveread rows 'Confluence cell ... ON')" | stack_live.py:526, 610-617 reads these at the subject's date: a forming low's confirmation date, or an open signal's ENTRY date. For a live signal they are the cells that were on at its entry | "...lists only the cells that are ON (liveread rows 'Confluence cell ... ON': for a forming low at its confirmation date, for an open signal at its entry), ALL of them ..." |

The same root shows up three times: "active today" (F5, C1, X5). The code anchors a confluence to the subject's confirmation or entry date. One wording change in stack_live's terms ("at confirmation" / "at entry") fixes all three.

## Documents with zero findings

- cloudflare/README.md. Every Worker's routes, gates, tokens, health checks, monitor thresholds (75 min, 26 h, 6 h reminders), backup keys, the 200 MB cap and about 26 dispatches a day match cloudflare/*.js. All six quoted test counts reproduce: 21, 26, 21, 41, 25 and 36, all passing. The generated ctzb-site and ctzb-dashboard Workers rebuild byte-identical from their sources.

Checked and correct, among others:
- FEED_SPEC: every field present in the rebuilt feed is described, and every described field exists.
- CARD_SPEC: the facts on line 24 (smallest rule-3 pool 33) and line 31 (first graded ETH signal is ETH 3D, 21 Mar 2020, C; first ETH A+ 18 Apr 2020).
- README: 13 datasets, eleven tags, twelve keep.json setups and the dashboard's nine datasets.
- member README: the example file holds 51 bars, 12 Aug to 20-21 Nov 2024.
- CONTEXT:
  - 996 trough rows on 6 charts
  - derivatives start dates 2020-01-21, 2020-05-31 and 2022-09-13
  - dipdist shares 14 / 25 / 27 / 36 (ETH, 3.3x)
  - fire drills 58/58
  - 176 confluence cells
  - regime on since 2026-09-02
  - deploy 656d67c3
  - confirmation lags of 3, 7, 11, 19 and 31 days

No in-scope sentence reads as a return, a trade taken or a track record.

## Outside scope (not counted)

| # | File | Line | Note |
|---|---|---|---|
| O1 | docs/SITE_CHANGES.md | 30 (6i) | Says How to read states that member alerts aren't on. It doesn't (same as F10). |
| O2 | docs/SITE_CHANGES.md | 28 (6g) | "Status unavailable" and the unknown-filter behaviour were superseded by 6h. The row has no superseded note. |
| O3 | stack_live.py docstring | 13-14 | Says "the record ... with it on and with it off". The code writes one record (line 591). |
| O4 | refresh.py docstring | 6 | Calls the dashboard "ETH Setup Odds". It is ETH Setup Standard. |
| O5 | extras_live.py | 35, 83 | `--datasets` does not move the ledger it reads: carddesign.rows always reads <repo>/datasets/ledger.csv. |

Code observation for the other auditors (not a documentation issue): ctzb-trades `/health` reports `ok` only when `last_ok_at` is under 10 minutes old (ctzb-trades-worker.js:400). But that field is persisted only on a change or every 15 minutes (HEARTBEAT_MIN = 15, lines 366-369), so on a quiet account `ok` reads false about a third of the time. The monitor uses its own 20-minute threshold, and the watchdog checks only for HTTP 200, so no alert fires.

## Could not check, and why

- **Cloudflare dashboard settings.** Cron triggers (`*/15`, `13,25,35,43`, `5,20,35,50`, `* * * * *`), bindings, Access policies, the R2 lifecycle rule and the deployed version ids are set in Cloudflare, not in the repo. Only the code comments and SITE_CHANGES record them.
- **claude.ai artifacts.** The links in CONTEXT "Live artifacts" were not opened.
- **Research records.** CONTEXT "What has been tested and failed" and the dated historical notes (README "Figures as of 16 October 2026", the TradingView match table, the waves ratios) were not re-run. They are research records, outside the counted scope. A grep of that section found no unannotated current-state claim.
- **Browser tests.** tests/test_feed_damage.py and test_page_timing.py need Playwright and Chromium. They were not run; their headers were read. The "about 35 ways" claim matches the 28 values plus 4 list operations in the test.
- **Member alert scope.** Whether member alerts will be top grade only is undecided (SITE_CHANGES R3). P1 flags the page for stating it as settled.
