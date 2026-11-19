# Audit 42, docs part: documentation against the code at 8d944e4

Copy checked out at `8d944e4`, in `audit42d/repo`. I rebuilt the pipeline in the copy with refresh, grade_live, extras_live, stack_live, verify_cards, regression and feed_live. Every step passed. The regression step reported 919 baselined signals unchanged and 4 new. The feed it wrote has 2 cards, 32 prints, 21 open signals and 10 windows. I did not read docs/AUDIT_LOG.md or any audit folder.

Entry quality only: every figure here belongs to computed signals and their 60-day records. There are no fills, no exits and no strategy return.

## Top line

| | |
|---|---|
| Documents read | 7 in scope (the member page, FEED_SPEC, CARD_SPEC, README, the member-site README, the cloudflare README, CONTEXT's current-rule sections), plus 4 BRIEFs, PRETRADE, SITE_CHANGES (Pending and Requested rows), the docstrings and comments of the 18 code files on the brief's list, daily.yml, and 33 test headers |
| Statements checked | about 1,000 (my estimate: FEED_SPEC ~230, member page ~110, CARD_SPEC ~70, CONTEXT current rules ~90, the three READMEs ~110, SITE_CHANGES ~120, BRIEFs ~30, PRETRADE ~15, docstrings and comments ~170, test headers ~60) |
| **COUNTED findings in scope (kinds 1, 2, 4)** | **0** |
| In scope, not counted | 1 kind 1 marked borderline (in FEED_SPEC, not the page's own words); 8 kind 3 |
| Outside scope (not counted) | 7 kind 2, 3 kind 3 |
| Kind 4 (reads as a return, a trade or a track record) | 0 anywhere |

## Every finding

Each suggested sentence is ready to paste. Full text is in `findings.csv`.

### In scope

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 1 | FEED_SPEC.md:535 | 1, borderline (FEED_SPEC is not the member page's own words, and the intended meaning can be recovered, so it is not counted) | a chart file "ends no later than `generated_at`" | index.html:966 refuses a file only when its last bar *opened* after generated_at. The last bar is normally today's open bar, which ends after generated_at | "whose last bar opened no later than `generated_at`" |
| 2 | FEED_SPEC.md:533 | 3 | the list of conditions for drawing a chart file | index.html:980-981 also refuses a live signal's file that does not reach back to its entry bar, with the message "This chart's data doesn't reach back to the entry" | Add: "A live signal's file that does not reach back to its entry bar reads \"This chart's data doesn't reach back to the entry\"." |
| 3 | index.html:296 | 3 | "Typical high: The median best price within 60 days, from the entry close." | The card shows `typical_biggest_rise_exact_pct`, a % move (L775, L789) | "The median best move within 60 days: how far above the entry close the highest price got." |
| 4 | index.html:300 | 3 | "...the median best price of all those misses within the 60 days" | The row shows `median_peak_pct`, a % move (L757) | "...and the median best move above entry of all those misses within the 60 days (the row names the pool)." |
| 5 | index.html:1216 | 3 | "Misses: median best price" | The value is `pct(median_peak_pct)` | "Misses: median best move" |
| 6 | index.html:1163 | 3 | "Best price" (What this one did) | The value is a % from the entry close plus its days | "Best move" |
| 7 | index.html:217 | 3 | "Real trades, posted automatically when they fill" | The relay runs every minute, and the panel itself says "within about a minute of each fill" (L838, L842) | "Real trades, posted automatically within about a minute of each fill (once his feed is live)" |
| 8 | CARD_SPEC.md:87 | 3 | "the median best price of all those misses" | `median_peak_pct` is the median of the misses' bestMove, a % (carddesign.misses) | "...and the median best move above entry (in %) of all those misses" |
| 9 | member-site/README.md:19 | 3 | "test_feed_damage.py damages every field in every way" | The test damages every schema field (the fields the page reads) in each of a fixed list of ways | "...damages every field the page reads (every field in the schema) in each of its listed ways, and checks exactly that." |

Rows 3 to 6 and 8 are one family: a label says "best price" where the number is a % move from the entry close. None of these shows a wrong figure, and none reads as a trade or a return, so none counts.

### Outside scope (not counted)

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 10 | BRIEF_site.md:28-31 | 2 | pinned to 9a013e3, "87,466 bytes" | The current site worker is 141,614 bytes (last built at 465e385) | "Pinned to the 11 Nov 2026 deploy (656d67c3). Re-pin to the build commit and size recorded in docs/SITE_CHANGES.md at the next deploy." |
| 11 | BRIEF_site.md:87-88 | 2 | "\"Data through\" today's date at the bottom right" | The footer reads "Daily candles closed through <scored_as_of − 1> · updated HH:MM UTC · checks passed" (index.html:914) | "\"Daily candles closed through\" yesterday's date at the bottom right" |
| 12 | BRIEF_site.md:90 | 2 | "Click Chart, Record and How to read a card. Record lists about 137 rows." | The tab is "Past signals" (index.html:205). The count of 137 top-grade rows still holds | "Click Chart, Past signals and How to read a card. Past signals lists about 137 rows." |
| 13 | BRIEF_monitor.md:122-138 | 2 | pinned to 0cdf3df: dashboard 65,188 bytes, scheduler 16,881 bytes | The dashboard file is now 65,453 bytes (SITE_CHANGES rows 7/7b pending). The scheduler is 17,008 bytes, with comment-only changes | Add: "(pinned to the 12 Nov 2026 deploy; the dashboard worker has changed since, see docs/SITE_CHANGES.md rows 7 and 7b)" |
| 14 | BRIEF_dashboard.md:62-65 | 2 | pinned to e43c0f8, "About 63 KB" | 65,453 bytes now | Add: "(pinned to the 10 Nov 2026 first deploy; later builds are listed in docs/SITE_CHANGES.md)" |
| 15 | BRIEF_trades.md:243-246 | 2 | pinned to 08e06ab, "21,762 bytes" | 23,387 bytes now (the 14 Nov build, not deployed, per cloudflare/README.md:72) | Add: "(pinned to the 11 Nov 2026 deploy; the 14 Nov build in cloudflare/README.md is not deployed yet)" |
| 16 | SITE_CHANGES.md:57-58 | 2 | rows 6q and 6r listed as "built and committed but NOT yet live" | Both are in index.html, but cloudflare/ctzb-site-worker.js was last rebuilt at 465e385. A fresh build_site.py run differs from the committed worker in exactly 3 page lines: 6q's sentence, 6r's example lead-trader line and one comment. Deploying the committed worker would ship neither change | Run `python3 cloudflare/build_site.py` and commit the result, or add to 6q/6r: "(index.html only; cloudflare/ctzb-site-worker.js not rebuilt yet)" |
| 17 | engine.py:73 | 3 | "Read a TradingView export." | `load()` reads the pipeline's own Coinbase data/*.csv files too | "Read a candle CSV (the pipeline's data/*.csv or a TradingView export). Returns dict of lists." |
| 18 | grade_live.py:36-37 | 3 | forward.csv rows "matched by chart and entry bar" | Rows are matched by chart and the confirmation close date (L277-291) | "(matched by chart and entry date, the confirmation close)" |
| 19 | feed_live.py:14-17 | 3 | "a broken seal, a damaged alert log or a failed strict check publishes the fail-closed feed" | The fail-closed feed is also published when the candle check did not pass structurally (with CTZB_STEP_OUTCOMES set), when a card file is missing after a clean run, when the seal is old, and on any crash (L468-483, L796) | "a failed candle check, a missing card file, a broken or old seal, a damaged alert log, a failed strict check or any crash publishes the fail-closed feed" |

## The site worker build is out of date

This is not a doc sentence, but it bears on finding 16 and on FEED_SPEC:549-550. That FEED_SPEC sentence says the worked example has no lead-trader line. It is true of index.html but not of the committed `cloudflare/ctzb-site-worker.js`, which is the file a deploy pastes. The dashboard worker rebuilds byte-identical; the site worker does not. Rebuilding and committing the site worker closes finding 16 and needs no doc change.

## Documents with zero findings

- README.md. Its counts recompute: 13 datasets, 11 candidate tags, keep.json's 12 setups, about 14 requests per asset. So do the schedule, `--today`, the dashboard's 9 datasets and the maxsafe formula.
- cloudflare/README.md. Every Worker statement matches its JS. The test counts reproduce: 21, 26, 21, 45, 26 and 36, all passing. The scheduler makes 26 dispatches a day, and the backup runs at 01:00 UTC with a 200 MB cap.
- CONTEXT.md, current-rule sections ("The setup", "Regime gate", "Traps", "Where things live", "Standing instructions", "Open items"). Its figures recompute: lags of 3/7/11/19/31 days, 996 trough rows on 6 charts, 176 confluence cells, 13 replay dates, 58/58 fire drills, and the regime on since 2026-09-02. Its dated notes all carry their superseded marks.
- docs/PRETRADE.md (statements about the pipeline). The coverage section boundaries, the run order and the BTC 3D confirmer cells (any, B, and diamond for ETH 1D A) all match.
- The Pending and Requested rows of SITE_CHANGES. Every Pending row is on disk in index.html (finding 16 is only about the build), and R1, R2 and R3 are not built.
- Docstrings and comments in refresh, stack_live, verify_cards, extras_live, feedcheck, seal, measures, rounding, clock, fetch, regimes, analysis/tagstats.py, analysis/carddesign.py, .github/scripts/*.py and retry_after_failure.sh, and daily.yml.
- Every tests/*.py, *.sh and *.mjs header. The counts each quotes match: 13 dates, 10 lows forming on 2026-06-11, the 2024 year limit for 15 Jan 2026, and the users of replay_at.

FEED_SPEC was checked against the rebuilt feed. Every top-level, card, open, print, window, grade, extras, checks and alert field it names exists with the stated meaning, and every field in the feed is described. The Strict column matches FEED_SCHEMA row by row. The schema-6 additions (alert_log, alert_log_carry, alerts_held, tier_fixed_on) match a diff against c7755bd.

## What I could not check, and why

- The deployed Workers and their crons (dashboard 5,20,35,50; trades every minute). I have no Cloudflare access, so I checked these only against the repo's JS and briefs.
- The research figures in README (the TradingView match table and the 16 Oct figures) and in CONTEXT's dated research record. These are records of past runs, not current rules.
- Running the browser tests (test_feed_damage, test_page_states, test_page_timing, test_per_year, numbers_check). The numbers and the broken-file behaviour are checked separately, so I read these headers against the code instead.
- I ran the non-browser Python tests in the background; results are in `pytests.log`. All 11 passed:

| Test | Result |
|---|---|
| test_check_candles | 95/95 |
| test_cut_files | 495/495 cut files caught across 21 files |
| test_feed_alerts | 89/89 |
| test_feed_extras | 28/28 |
| test_fetch_today | 4/4 |
| test_input_files | 117/117 |
| test_midnight | 7/7 |
| test_seal | 29/29 |
| test_series_cells | 62/62 |
| test_year_end | 8/8 |
| test_action_env | 1/1 |
