# Audit 34, docs part: doc versus code at 4388653

Entry quality only. Everything checked here describes computed signals and their 60-day records. There are no fills, no exits and no strategy return.

## Top line

| | |
|---|---|
| Documents read | 13 docs (member page, FEED_SPEC, CARD_SPEC, README, member-site README, cloudflare README, CONTEXT, BRIEF_dashboard/monitor/site/trades, PRETRADE, SITE_CHANGES), plus the docstrings and comments of the 22 code files and workflow in brief item 5, and the headers of all 31 tests/*.py, *.sh and *.mjs files |
| Statements checked | about 780 (FEED_SPEC ~230, CARD_SPEC ~70, member page ~120, three READMEs ~75, CONTEXT current-rule sections ~120, outside scope ~165) |
| **Counted findings (in scope)** | **24**: kind 1 (wrong) 4 · kind 2 (stale) 2 · kind 3 (loose or incomplete) 16 · kind 4 (reads as a trade) 2 |
| Outside-scope findings (not counted) | 13 |

The feed was rebuilt in a copy using the command in the brief (all steps passed: 0 cards, 30 prints, 21 open signals, 14 windows). Every field in that feed is described in FEED_SPEC, and every field FEED_SPEC names is in the feed or in the code that writes it. Every "Strict" column in FEED_SPEC matches `FEED_SCHEMA` exactly.

## Counted findings

Kinds: 1 = wrong · 2 = stale · 3 = loose or incomplete · 4 = reads as a return, a trade or a track record. Each suggested sentence is written out in full in findings.csv.

| # | File:line | Kind | Doc says (short) | Code does | Suggested |
|---|---|---|---|---|---|
| 1 | FEED_SPEC:99 | 3 | next_buy_date: a forming low "that carries a walk-forward tier tag" | `refresh.provisional` (L146-168) gives a forming low only its bucket, any trough, zone-exit B and prime dot. Diamond, filled, hollow and diamond+dot tier pairs never match. ETH 1D's only tier pair today is "hollow" | "...whose bucket, any-trough, zone-exit B or prime-dot tag is a tier pair (diamond tags are not read until it confirms)" |
| 2 | FEED_SPEC:109 | 3 | alert_log "null when there is no log" | When a run is not seeding and finds no log, `check_log` raises (L215-225) and the fail-closed feed carries the last record. Null occurs only on a held seeding run | "a run with no log fails closed unless seeding; null on a held seeding run with no log, and..." |
| 3 | FEED_SPEC:41 | 3 | "Its own work is: ..." (list) | Also writes `alert_log_backup.csv` (L642-646), deletes the extras files (L573), and runs the candle, seal and strict checks (L427-450, L632) | Add "the second copy, the held/fail-closed checks, deleting the extras files" |
| 4 | FEED_SPEC:461 | 3 | "no signal id ... appears twice" | Ids are checked within `cards` and within `open_signals`, each list on its own (feedcheck L133-135, page L461). Prints and alerts are not checked | "no signal id appears twice within cards or within open_signals" |
| 5 | FEED_SPEC:485 | 3 | stale warning "on every tab" | `staleBars` covers Chart, Past signals and How to read. On the Now card, the "No odds yet"/"Card unavailable" (L702) and "Example unavailable" (L722) branches show no note | "...on the Chart, Past signals and How to read tabs and on the Now card (not on a No odds yet / Card unavailable / Example unavailable card)" |
| 6 | FEED_SPEC:525 | 3 | lead-trader file "none in the future" | Accepted up to 5 minutes ahead of the viewer's clock (page L548, feedcheck L238) | "none more than 5 minutes ahead of the viewer's clock" |
| 7 | CARD_SPEC:63 | 1 | "A live setup's card is the card as issued at its entry close." | Open cards are rebuilt every run from `rows` measured up to today (stack_live L567-571), so the sample includes signals whose 60 days closed after the entry. Only the example card is limited to signals known by its date (L746) | "rebuilt every run ... sample of every past signal whose 60 days have closed by the run's date; each figure measured from each past signal's entry close" |
| 8 | CARD_SPEC:124 | 3 | "...and the health monitor messages Jared" | The monitor has a 75-minute grace for held-back cards (scheduler `GRACE.withheld`, L149) | "...messages Jared if they are still held back 75 minutes later" |
| 9 | CARD_SPEC:4 (and :129) | 4 | "every word on a **trade** card"; "per-trade fitted models" | Renamed "signal card" on 13 Nov (CONTEXT L1398). None was traded | "signal card"; "per-signal fitted models" |
| 10 | page:755 (also :760, :1156) | 3 | "The odds below are as of the entry close, not from today." | Same cause as #7: the sample is rebuilt each run. Only the measuring point is fixed at the entry | "measured from the entry close, not from today's price" |
| 11 | page:290 | 3 | odds "from past signals with the same profile" | The sample falls back to the same grade on this chart, then the same grade across the asset (stack_live L554-556) | "...like this one: the same confirmations when there are enough, otherwise the same grade, as the card says" |
| 12 | page:300 | 3 | If it misses: "Of the past signals that did not rise 10%..." | The pool is every signal of this asset and grade, not the card's sample (feed_live L575-583, page L738-741) | "Of all past signals of this asset and grade that did not rise 10%..." |
| 13 | page:733 | 3 | quiet card "Nothing at the top grade is forming or confirmed today." | Shown only when nothing of any grade is forming and no top-grade signal is within its 60 days (L640-644, L728) | "Nothing is forming today and no top-grade signal is within its 60 days." |
| 14 | page:380 (FEED_SCHEMA comment) | 1 | "n whole number >= 0", "date YYYY-MM-DD", "ts ISO time" | `n` must be under 1e6 (L391). `date` and `ts` must be real calendar dates in 2000-2099 (L387-388; same in feedcheck) | "n a whole number from 0 to under a million; date a real date YYYY-MM-DD in 2000-2099; ts ... in 2000-2099" |
| 15 | member README:19 | 2 | FEED_SPEC "Audit #21 corrections" and "Audit #22 corrections" "list every rule" | Those sections are gone (moved to docs/history). The rules are in "The strict check" and "What the member page does..." | Point to those two sections |
| 16 | member README:19 | 3 | lead-trader file: "nothing in the future" | 5-minute allowance (page L548) | "nothing more than 5 minutes ahead of the viewer's clock" |
| 17 | member README:17 | 3 | "What the page types is ..." (list) | The page also types the 5-minute allowance (L548), 6 latest trades (L835), 5 latest past signals (L879) and the 00:00 UTC close (L628) | Add these to the list |
| 18 | cloudflare README:10 | 1 | ctzb-dashboard holds "none" | It holds the secret `TELEGRAM_BOT_TOKEN` (and `DASHBOARD_PASSWORD` in password mode) (template L21-26). The README's own paragraph lists it | "`TELEGRAM_BOT_TOKEN` (`DASHBOARD_PASSWORD` in password mode)" |
| 19 | cloudflare README:9 | 3 | ctzb-scheduler holds `GITHUB_DISPATCH_TOKEN` | v3 also holds `TELEGRAM_BOT_TOKEN` (scheduler L36) | Add it |
| 20 | README:147 | 2 | "reads 90 signals at 66% ... 77% at 3+ ... 75% at 4+" (undated) | walkforward.csv now reads 94 at 66%, 48 at 79% and 13 at 77% | Date it: "on 16 October 2026 ... read ..." |
| 21 | CONTEXT:151 | 1 | `dead` counts a −30% "before the trough gives back 5%" | troughs.py L28 and L111-114: −30% from entry **without first gaining +5%** from entry | "...before price has gained 5% from entry" |
| 22 | CONTEXT:162 | 3 | "tier.csv, confluence.csv and buy.csv still use the symmetric count" | walkforward.csv's 3+/4+ agreeing rows also use it (refresh L250-252, L430-431) | Add walkforward.csv |
| 23 | CONTEXT:216 | 3 | refresh.py "builds `datasets/*.csv`" | It writes 13 of the 39 datasets. Four other steps write or change the rest | "builds 13 of the datasets/*.csv (status ... forward)" |
| 24 | CONTEXT:1375 (and :1382) | 4 | "**Every trade its own odds**"; "per-trade fitted odds" | model.py fits computed signals. None was traded | "Every signal its own odds"; "per-signal fitted odds" |

## Outside scope (not counted)

| # | File:line | Kind | Doc says (short) | Code does |
|---|---|---|---|---|
| O1 | feed_live.py:6 | 2 | the Cloudflare backend will read it "once the ETHKROS Cloudflare account exists" | The account exists, and four Workers read the feed |
| O2 | feedcheck.py:7 | 1 | "n a whole number 0 or more" | Must be under 1e6 (L51) |
| O3 | check_candles.py:16 | 2 | "the funding series is whole and current" | No lag check is made here (only stack_live, lag=True). The list also omits the long/short, OI and put/call series and the 4H/12H gap checks |
| O4 | grade_live.py:34 (and :21) | 3 | forward.csv adds grade/lenses; live.csv adds formingGrade/formingLenses | The step also adds htfDiv and marker to forward.csv, and formingHtfDiv, formingMarker, closeNow and closeDate to live.csv. The ledger column list is short |
| O5 | stack_live.py:19 | 3 | "Writes datasets/: ..." | It also rewrites analysis/registry.json (L788) |
| O6 | page comments :8, :843, :847 | 2 | "previous alerts" panel; per-year average runs "to last year" | The panel is "Previous signals". The average ends at the last full year whose signals have all closed |
| O7 | tests/test_page_timing.py:3 | 3 | header lists cases 1, 1b, 2, 3, 4, 6 | The body also runs 4b, 4c, 4d and 5 |
| O8 | tests/test_seal.py:4 | 3 | header sentence cut and run together | (cases listed in the next lines) |
| O9 | PRETRADE:196 | 4 | "past graded **trades** ... next to a live **trade**" | stack_live pools computed signals |
| O10 | SITE_CHANGES:30 (6i) | 3 | "stale warning on every tab" | Same gap as #5 |
| O11 | SITE_CHANGES:22 (6) | 2 | "confirmed alerts are final, forming heads-ups can vanish" | Reworded by 6j (a forming setup is "shown"), with no superseded mark |
| O12 | CONTEXT:535 (research section) | 2 | "members are sent A+ only" | No member alerts. The page shows forming setups of every grade. The bracket note does not cover this |
| O13 | eth-setup-standard.html:103 (+ CONTEXT :1602, :1610) | 4 | "Past trades", "Trades that got there", "buy price", "within 60 days of buying" | The dashboard card shows computed signals. CONTEXT's dated notes repeat these words |

## Documents with zero findings

- **In scope:** none. Every counted document has at least one finding.
- **Outside scope:** BRIEF_dashboard.md, BRIEF_monitor.md, BRIEF_site.md and BRIEF_trades.md (setup briefs pinned to the commits they deploy; they agree with those builds by design); refresh.py, engine.py, measures.py, rounding.py, clock.py, regimes.py, seal.py, fetch.py, verify_cards.py, extras_live.py, analysis/tagstats.py, analysis/carddesign.py, check_fresh.py, retry_after_failure.sh, daily.yml; and the test headers not listed above.

## Counts and figures recomputed (all agree unless listed above)

| Figure | Where | Result |
|---|---|---|
| Node test counts 21, 26, 21, 45, 26, 36 | cloudflare README | Ran all six suites: 21/21, 26/26, 21/21, 45/45, 26/26, 36/36 |
| 58/58 fire drills; 13 replay dates; six damage families | CONTEXT | fire_drills_result.json 58/58; numbers_check DATES has 13 entries; DAMAGE_LIST has six families |
| 13 refresh datasets; 11 candidate tags; keep.json 12 setups; walk-forward tier 13 setups | README | Agree |
| 138+88+47+24 = 297 signals | README, fetch.py | Agree |
| troughs.json 996 rows, 6 charts; 176 confluence cells; 12 PRETRADE headings | CONTEXT | Agree |
| 13 perp markets per asset, 7 exchanges; 26 dispatches a day | CONTEXT, cloudflare README | Agree |
| Smallest rule-3 pool 33; first graded ETH signal ETH 3D 2020-03-21 (C); first ETH A+ 2020-04-18 | CARD_SPEC | Agree |
| Example: 51 bars from 12 Aug 2024 to the bar of 20-21 Nov; sample 75 | member README, SITE_CHANGES 6b | Agree |
| Confirmation lags 3/7/11/19/31 days; ETH 3D 13 Sep to 24 Sep | CONTEXT | Agree |
| At 3.3x, share of dips reaching liquidation: A+ 14, A 25, B 27, C 36 | CONTEXT | Agree for ETH (dipdist.csv). The doc does not say ETH |
| schema_version asserted in two tests | FEED_SPEC | Agree (test_feed_alerts, test_feed_extras) |
| Walk-forward 90 at 66%, 77% / 75% | README | **Disagrees** (finding #20) |

## What I could not check, and why

- **Cron triggers** (mirror `*/15`, dashboard `5,20,35,50`, trades `* * * * *`, scheduler `13,25,35,43`). These are set in the Cloudflare dashboard, not in the repo. Only the code comments and the scheduler's job table could be compared.
- **Deployed versions and the live site.** 656d67c3, the Access policies, Joe's artifact, the R2 backup state and whether the repository is public are outside the repo.
- **The Playwright tests** (test_feed_damage, test_page_timing, test_page_states, numbers_check, test_per_year) were not run, so the page behaviour their headers claim was checked against the page source only. fire_drills.py was not re-run; its committed result file was used.
- **Pinned BRIEF byte counts.** They describe the old commits they pin and were not rebuilt.
- **progress.log** got its per-document lines appended together at the end of the pass, not one at a time as each document finished.
