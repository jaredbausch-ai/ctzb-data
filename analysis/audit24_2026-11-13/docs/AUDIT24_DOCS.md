# Audit #24, docs against code

**Top line:** I read 6 documents in scope (FEED_SPEC, CARD_SPEC, the member page's own words with the FEED_SCHEMA comment, README.md, the member-site README, cloudflare/README.md), plus the current-rule sections of CONTEXT.md. I checked about 490 statements (an estimate). There are **15 findings: (1) wrong: 1 · (2) stale: 1 · (3) loose/incomplete: 13 · (4) reads as a return/trade/track record: 0.**

Scope follows the owner's change of 13 Nov 12:56 ET. Findings in other files are listed at the end and not counted. Everything here measures entry quality only: these are computed signals, not fills, and the data has no exit.

How this was checked. I copied the repo to `audit24d/repo` and ran refresh, grade_live, extras_live, stack_live, verify_cards, regression (PASS, 919 + 2 new) and feed_live. The rebuilt feed is identical to the committed one apart from the timestamps. I listed every field path in it and matched each path against FEED_SPEC. I read all the scoring code in full, the page script, the site/scheduler workers and daily.yml. I ran all six Worker test suites (21/26/21/41/24/36, every count matches cloudflare/README). I replayed 2026-06-11 to check the gate-off claim: 10 forming lows, all "regime off", 0 cards, filter Bearish. I recomputed the gate transitions (off 2025-12-05, on 2026-09-02), the pool sizes, the first ETH signals (ETH 3D 2020-03-21 C, first A+ 2020-04-18), the example file (51 bars, 12 Aug to 20 Nov 2024), keep.json (12), the troughs rows (996), the fire drills (58/58 at 16:38Z) and the rounding importers.

## Findings (counted)

| # | File:line | Kind | Quoted (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 1 | FEED_SPEC.md:44 | 1 | `next_buy_date`: close date of the bar on which the next forming ETH tier low would confirm | refresh.py:345 labels a low "Needs fresh data" when conf <= today. ds_status (714) uses only "Upcoming" rows. So a tier low whose confirmation bar closes **today** (need 0) is skipped, and the field shows a later one or "none ahead". | "...the next forming ETH tier low would confirm, counting only bars that close after today (a tier low confirming at today's close is not shown); \"none ahead\" when there is none." |
| 2 | FEED_SPEC.md:44 | 3 | `trades_a_year` ... per year; `next_buy_date` ... a computed date | Both are status.csv text: "17 on average" (or "—"), and "none ahead" (refresh.py:714-715, feed_live.py:367-368). | "`trades_a_year`: text \"N on average\" ... \"—\" when none. `next_buy_date`: a date, or the text \"none ahead\"." |
| 3 | FEED_SPEC.md:38 | 3 | WINMIN tier: closed above entry on the chart's last bar within 60 days | fw() (refresh.py:105-125, called at 247) ends the window 60 days after the confirmation bar's **open** date, on the chart's own bars. It is not the daily 60-day window from the entry date. | "...within 60 days of the confirmation bar's open date, on the chart's own bars..." |
| 4 | FEED_SPEC.md:116 | 3 | odds_fade: "ETH walk-forward tier signals only" | `_daily_windows` (refresh.py:547-573) applies the tier as fixed on 1 Jan of the **current** year to every signal from 2016, so the sample is in-sample. | "ETH signals on the chart/tag pairs of the tier as fixed on 1 January of the current year (`tier_fixed_on`), applied to every signal from 2016, every chart: in-sample." |
| 5 | FEED_SPEC.md:366 | 3 | each scoring step (refresh, grade, extras, stack, cards) checks as it starts | refresh.py:740 only calls `seal.start`. `seal.check` runs in grade/extras/stack/cards. | "...each later scoring step (grade, extras, stack, cards) checks as it starts..." |
| 6 | FEED_SPEC.md:69 (+116-117) | 3 | field tables | These feed fields are not described anywhere: `if_it_falls_first[].fell_pct`, `odds_fade.early_dip[].band`, `odds_fade.day10[].check`, `odds_fade.label`, `past_paths[].grade`, `example_past_paths.grade` (feed_live.py:247, 437, 444, 448, 455, 472). | Add one line each (wording in findings.csv). |
| 7 | FEED_SPEC.md:348 | 3 | schema covers "every feed field the page reads" | index.html:626 reads the rounded `typical_*_pct` fields as `??` fallbacks. They are not in FEED_SCHEMA. The fallbacks are unreachable in practice. | Say so, or drop the fallbacks. |
| 8 | CARD_SPEC.md:71 | 3 | "Where the odds fade · ETH tier signals" (`odds_fade.early_dip` bands) | The fallback ladder (index.html:763-764) also shows the two day-10 rows. | "...`early_dip` bands and the `day10` green/red rows..." |
| 9 | index.html:766 | 3 | "...share that rose 10% after day 10 (days 11 to 60), by the deepest dip in the first 10 days" | The same ladder has rows grouped by the day-10 close. | "...by the deepest dip in the first 10 days and by the day-10 close (green or red)." |
| 10 | CARD_SPEC.md:98 | 2 | e.g. "95 misses of all 312 BTC same-grade signals" | The current feed has BTC C at 95 misses of **313**. | "...95 misses of all 313..." (and mark it as an example) |
| 11 | CARD_SPEC.md:81 | 3 | Edge gone below: two states defined | The page has a third state, "Holds at every level" (index.html:705, 1112). | Add "\"Holds at every level\" when no row is below the bar." |
| 12 | index.html:716 | 3 | "Rose 10%. It rose 10% before falling to its edge level (−X%)." | `rose10` means +10% came before the edge level was reached (stack_live.py:466-468). It says nothing about a later fall, but the sentence reads as if the price then fell to that level. | "It rose 10% before ever reaching its edge level (−X%)." |
| 13 | README.md:93 | 3 | "win" means the chart closed above the entry within 60 days | win = the **last** close of the window above entry (refresh.py:254, fw), with the window counted from the confirmation bar's open date. It is not any close above entry. | "\"win\" means the chart's last close in the 60 days after the confirmation bar opened was above the entry." |
| 14 | member-site/README.md:18 | 3 | "A file that fails reads 'unavailable'; nothing is patched" | The site Worker's csvToBars (site_worker_template.js:130-131) silently drops candle rows that are not numbers before the page checks them. A dropped last row on a live setup's file goes undetected. | State it, or make csvToBars refuse the file. |
| 15 | member-site/README.md:7-13 | 3 | path table | `data/candles/*.json` in that folder is an 11 Nov snapshot (7e85860) that is never served or embedded, and the README doesn't say so. | Add one line saying so, or delete the files. |

Ready-to-paste wording for every row is in findings.csv.

## Documents with zero findings
- cloudflare/README.md: crons, the 26 dispatches/day, grace periods (75 min, 26 h), the three /health routes and all six test counts match.
- CONTEXT.md, current-rule sections: the project rules, the setup and entry, the regime gate, the confirmation-lag note, the Audit corrections paragraph, "The strict check", and the feed and member-site paragraphs. I verified the gate dates, fire drills 58/58 and the rounding importers.
- The member page's How to read, banners, footer, Record tab and FEED_SCHEMA comment. All 15 type definitions in the comment match the PRIM functions and feedcheck.py.

## Could not check
- Live Cloudflare state: deploy ids, KV, Access policies, the Telegram sends, and the backup sizes. I also could not check GitHub run history or the byte count of BRIEF_site's pinned commit.
- I did not run the browser tests (test_feed_damage, test_page_states, test_page_timing, fire_drills E), so "about 35 ways each" was not counted.
- CONTEXT figures from dated research were not recomputed, by design.

## Outside scope (not counted)
- refresh.py:345: the "Needs fresh data" rule is the cause of finding 1. A need-0 low used to get the same label before audit #23.
- extras_live.py:23-25 and analysis/carddesign.py:27: "ETH walk-forward tier signals" has the same looseness as finding 4.
- check_candles.py docstring (l.12-16) and daily.yml comment (l.95-98) list only funding among the series. They leave out the long/short, OI and BTC put/call series and the 4H/12H existence/timeframe/asset checks (fetch.py:226-254, 320-326).
- seal.py docstring (l.184) lists refresh among the steps that check: the same issue as finding 5.
- grade_live.py docstring (l.38) and PRETRADE "Running it" list only formingGrade/formingLenses. live.csv also gets formingHtfDiv, formingMarker, closeNow and closeDate.
- PRETRADE "Costs" table gives the confirmation lag as 3/6/9/15/24 days. That is bar-open to bar-open, and it has no note like CONTEXT's audit #20 (3/7/11/19/31 from low_date to the confirmation close).
- cloudflare/BRIEF_site.md 3.1-3.2 is stale. The footer no longer says "Data through" (it is now "Daily candles closed through <day before scored_as_of>"), and the tab is "Past signals", not "Record".
- CONTEXT "Whole stack" paragraph (l.1455): "At 3.3x with no reserve that share is A+ 14%, A 25%, B 27%, C 36%". dipdist.csv now gives 15/18/24/29% at -25.3%.
- CONTEXT "Dashboard freshness" (l.1469): "= files/index.html in the artifact DB (v35)". The dashboard has been served by ctzb-dashboard since 10 Nov, and there is no superseded note.
- Checked and true: test_gate_off.sh "ten lows forming" (the replay gives 10), regression "missing baseline fails", the node suite counts, and the replay/no-today-bar headers.
