# Audit 36: documentation against code (frozen at 2d856f7)

Entry quality only. Everything checked here describes computed signals and their 60-day records. There are no fills, no exits and no strategy return.

## Top line

- **Documents read:** 7 in scope (member page words, FEED_SPEC, CARD_SPEC, README.md, member-site README, cloudflare README, CONTEXT current-rule sections). Outside scope: 4 BRIEFs, PRETRADE (pipeline statements only), SITE_CHANGES (Pending and Requested rows), the CONTEXT dated notes, the docstrings and comments in the 16 listed modules plus `.github/scripts/*.py` and `daily.yml`, and the headers of all 29 test files.
- **Statements checked:** about 960. About 680 are in scope (page about 115, FEED_SPEC about 240, CARD_SPEC about 75, README about 45, member-site README about 18, cloudflare README about 45, CONTEXT current rules about 140). About 280 are outside scope.
- **COUNTED findings (in scope): 10.** Kind 1 (wrong figure): 1. Kind 2 (stale): 1. Kind 3 (loose or incomplete): 7. Kind 4 (reads as a return or track record): 1.
- **Outside scope (not counted): 7.** Kind 2: 1. Kind 3: 6.

Method: I rebuilt the feed in a copy (`refresh`, `grade_live`, `extras_live`, `stack_live` and `verify_cards` all passed; regression PASS on 919; feed 6 cards, 36 prints, 21 open signals). I walked every key in the rebuilt feed against the spec, and every spec field against `feed_live.py`. I compared the `FEED_SCHEMA` block with both the FEED_SPEC "Strict" column and `feedcheck.py`. I read the page's render code against each label. I ran all six `.mjs` suites (21/26/36/21/26/45, all matching the README counts) and `tests/test_gate_off.sh` (PASS, 10 forming prints, regime off). I rebuilt both generated Workers and got no diff. I checked the BRIEFs' pinned byte counts against git, and I recomputed the quoted counts listed under item 7.

## Counted findings (in scope)

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 1 | README.md:33 | 1 | "pages the daily history back to 2016 (about a dozen requests)" | `fetch.py` L32-48 pages back 300 days at a time for each product until it gets an empty page. For 2026-11-15 that is 14 requests for ETH and 14 for BTC, 28 a run. | "Every run pages the daily history back to 2016 (about 14 requests per asset, 28 in all);" |
| 2 | docs/FEED_SPEC.md:42 | 3 | "`alert_log`, `alert_log_carry` and `alerts_held` are schema 6 fields that came without a bump" | `odds_fade.tier_fixed_on` (`feed_live.py` L591) was added in 6bb13bc (12 Nov, 17:07 ET). That is after the bump to 6 in c7755bd (16:03 ET), and no new bump followed. A diff of key names from c7755bd to HEAD shows exactly these four. | "`odds_fade.tier_fixed_on`, `alert_log`, `alert_log_carry` and `alerts_held` are schema 6 fields that came without a bump." |
| 3 | docs/FEED_SPEC.md:281 | 3 | "`example_if_it_misses` has `signals`, `misses`, ... `note`" | `feed_live.py` L617-622 also writes `label`, `asset` and `grade`, and all three are in the rebuilt feed. | "`example_if_it_misses` has `label`, `asset` ("ETH"), `grade` ("A+"), `signals`, `misses`, `up_first`, `median_peak_pct`, `median_worst_drop_pct`, `median_day60_pct`, `miss_rule`, `note`." |
| 4 | docs/CARD_SPEC.md:87-88 | 3 | If-it-misses row and miss tiles → "`if_it_misses[]`" | On the worked example the page reads `example_if_it_misses` instead (`index.html` L738). | Feed field: "`if_it_misses[]` (`up_first`, `median_peak_pct`); on the worked example `example_if_it_misses` (signals whose 60 days had closed by 22 Sep 2024)". Add the same to row 88. |
| 5 | member page index.html:303 (also 310, 792, 1175) | 4 | "Past results don't guarantee future results." | Nothing on the page is a result. The figures are 60-day entry-quality statistics of computed signals, and FEED_SPEC L4-6 says so. "Past results" reads as a performance record. (The wording was deployed on purpose in ffab70e3, so this may be Jared's call.) | "How past signals behaved doesn't guarantee how future signals will behave." |
| 6 | member page index.html:235 | 3 | "See every past signal, misses included" | The tab lists only top-grade rows: L1310 keeps grade A+, and the heading at L266 says "Every top-grade signal whose 60 days have closed". | "See every past top-grade signal, misses included" |
| 7 | CONTEXT.md:89-92 | 3 | "the only exceptions are single instances caused by irregular bar gaps in the data" | 2D+ bars restart on 1 January (`fetch.resample`), so every year's last bar can be short. A confirmation that crosses the year-end comes sooner. For example, a 3D trough bar opening 21 Dec confirms on 31 Dec, 10 days after the low instead of 11. This happens every year, not once. | "... 24 on 8D, bar open to bar open, except across 1 January: 2D+ bars restart there, so a year's last bar can be short and a confirmation that crosses the year-end comes sooner." |
| 8 | CONTEXT.md:245 | 2 | Live artifacts: "ETH Setup Standard (Joe's) ... Update via `ArtifactData` with `if_version` pinned" | The live dashboard is now the ctzb-dashboard Worker, built from `eth-setup-standard.html` (`dashboard_worker_template.js` L1-11). CONTEXT L1482-1484 says the page matched that artifact's v38 on 10 Nov and has changed since. | "Joe has this link. Frozen at files/index.html v38 (10 Nov 2026); the live dashboard is the ctzb-dashboard Worker, built from docs/artifacts/eth-setup-standard.html by cloudflare/build_dashboard.py." |
| 9 | CONTEXT.md:1414 | 3 | "`feed_live.py` writes `feed/ctzb_feed.json` every Action run" | Two kinds of run write no feed. A gate-skipped tick never runs the job (`daily.yml` L57-67). A run whose fetch, freshness or candle check fails stops before `feed_live.py` (L85-105). FEED_SPEC L29 states this. | "... on every Action run that gets past the fetch, freshness and candle checks, repackaging this run's datasets (cards withheld if a check failed)." |
| 10 | CONTEXT.md:1423 | 3 | "Still not built: the Grok ping; repo private." | FEED_SPEC L560-565 lists four items. The two missing here are keyed views per audience (ctzb-site serves one view) and a member alert channel (alerts go only to the operator's Telegram). | "Still not built: keyed views per audience, a member alert channel, the Grok ping; the repo going private." |

## Outside scope (not counted)

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| O1 | feed_live.py:10-11 | 3 | "(the additions alert_log and alert_log_carry, 13 Nov 2026, and alerts_held, 14 Nov, were made at 6 without a bump)" | `odds_fade.tier_fixed_on` (12 Nov, 6bb13bc) is also missing from this list. | "(the additions odds_fade.tier_fixed_on, 12 Nov 2026, alert_log and alert_log_carry, 13 Nov, and alerts_held, 14 Nov, were made at 6 without a bump)" |
| O2 | stack_live.py:9-10 | 3 | "fails the run if a PRETRADE heading is not mapped ..., or a registry id is not evaluated" | L138-147 checks only the Tier 1, Promising and In-trade headings. An unevaluated id fails the run only when there is at least one subject. | "... if a PRETRADE heading under Tier 1, Promising or In-trade reads is not mapped to a registry id, or, when there is at least one subject, a registry id is not evaluated." |
| O3 | extras_live.py:21 | 3 | "the read-only mirror, which serves datasets/*.csv only" | The mirror also serves `feed/ctzb_feed.json`, `keep.json`, `odds.json` and `troughs.json` (`ctzb-feed-worker.js` L45-53). What it does not serve is `data/`. | "... which serves datasets/*.csv but nothing in data/." |
| O4 | extras_live.py:36 | 3 | "the ledger is always read from the repo's datasets/ledger.csv; only the outputs follow --datasets" | `earlydip.csv` and `holdcheck.csv` are also read from the repo's `datasets/` (`carddesign.py` L50-52, L139-147). The seal check follows `--datasets`. | "(the ledger, earlydip.csv and holdcheck.csv are always read from the repo's datasets/; the outputs and the seal follow --datasets)" |
| O5 | docs/SITE_CHANGES.md:13 (Pending) | 3 | Pending rows 1-7b | Two built changes are not listed. ee91da1 changed the page: the strict check now refuses example extras without the example card, and the cloud note is set when past paths are missing. 2d856f7 changed the console: "No chart has a low forming with a card right now." | Add a row 6o for ee91da1, and add the 2d856f7 console wording to row 7b. Exact text is in findings.csv. |
| O6 | docs/SITE_CHANGES.md:35 | 3 | 6n: "the picker and quiet card say 'No setup with a card forming today'" · Commit "(this round)" | The quiet card reads "No setup with a card **is** forming today" (L733). The commit is cf6b4ec. | "... the picker says 'No setup with a card forming today' and the quiet card 'No setup with a card is forming today' ... \| cf6b4ec" |
| O7 | CONTEXT.md:1612 (dated 4 Nov note) | 2 | "The dashboard upload is a Claude scheduled task and does depend on Claude usage" | Since 10 Nov the ctzb-dashboard Worker serves the dashboard from the mirror. The supersede note at L1620 covers only the scheduler. | Prefix: "[superseded 10 Nov 2026: the ctzb-dashboard Worker serves the dashboard from the mirror; no Claude scheduled task uploads it]" |

## Documents with zero findings

- **In scope:** `docs/artifacts/member-site/README.md` and `cloudflare/README.md`. In both, every Worker route, binding, cron, threshold and test count matched the code (test counts 21/26/21/45/26/36 confirmed by running the suites).
- **In-scope documents that had findings:** every other statement in them checked out. That includes every FEED_SPEC table and correction section against `feed_live.py`, `stack_live.py`, `extras_live.py`, `refresh.py`, `feedcheck.py`, `seal.py` and the rebuilt feed. Every field in the feed is described, and every field the spec names exists. The "Strict" column matches `FEED_SCHEMA` key for key. Every CARD_SPEC label and its console wording matched. Every How-to-read line and every card, chart, picker, footer and banner label on the page matched what it shows.
- **Outside scope:** `cloudflare/BRIEF_dashboard.md`, `BRIEF_monitor.md`, `BRIEF_site.md` and `BRIEF_trades.md`. Pinned byte counts and first lines match git (87,466; 65,188; 16,881; 21,762; ~63 KB). Note that BRIEF_site describes the pinned 9a013e3 build, as SITE_CHANGES intends.
- **Outside scope:** the pipeline statements in `docs/PRETRADE.md`, and the SITE_CHANGES Requested rows R1-R3 (none of them is built).
- **Outside scope:** the docstrings and comments in `refresh.py`, `grade_live.py`, `verify_cards.py`, `feedcheck.py`, `seal.py`, `engine.py`, `measures.py`, `rounding.py`, `clock.py`, `fetch.py`, `regimes.py`, `analysis/tagstats.py`, `analysis/carddesign.py`, `check_candles.py`, `check_fresh.py` and `daily.yml`.
- **Outside scope:** every test header. Spot checks: `regression.py`; `replay_at.sh`, whose list of users matches a grep; the `numbers_check.py` date count (13); `test_gate_off.sh`, run and PASS with 10 lows forming; `test_per_year.py` logic; and `test_feed_extras.py`'s posting-bar check.

Recomputed and confirmed:
- `refresh.py` writes 13 datasets; `keep.json` holds 12 setups; there are 11 candidate tags.
- `troughs.json` has 996 rows across 6 charts; there are 176 confluence cells (83+49+44).
- The smallest rule-3 pool is 33 (BTC A+).
- The first graded ETH signal is ETH 3D, 2020-03-21, grade C. The first ETH A+ is 2020-04-18.
- The dip shares at 3.3x are 14/25/27/36%.
- The regime has been on since 2026-09-02.
- The BTC 3D confirmer cells are any/B, plus diamond for ETH 1D A only.
- There are 13 perp markets per asset; the scheduler makes 26 dispatches a day.
- The example file has 51 bars, 12 Aug to 20 Nov 2024. The fire drills show 58/58, matching the result file. DAMAGE_LIST has six families, as CONTEXT says.

## Not checked, and why

- **Cloudflare deployment state:** deployed version ids, Access policies, the R2 lifecycle rule, the KV contents and live `/health`. These are not in the repo.
- **External services:** live Kraken and Coinbase responses (no network use, by brief).
- **Tests not re-run:** `tests/fire_drills.py`, `test_feed_damage.py`, `test_page_*.py` and `numbers_check.py` were not run again, because they take too long. Their headers were read against their code only.
- **Historical figures:** the dated README tables and the CONTEXT research records, which the brief excludes.
- **Handed on, not counted:** an empty CSV cell parses as 0 in the site Worker's `csvToBars`, so "refuses ... any row [that] is not numbers" (member-site README L19, FEED_SPEC L524) is loose for blank cells. The page's `barsOk` still refuses that chart. This is broken-file behaviour, so I pass it to that check rather than count it.
