# Audit 46: docs against code (commit 0185de1)

Entry quality only: every figure here is about computed signals and their 60-day records. There are no fills, no exits and no strategy return.

## Top line

- **Documents read:** 13 doc files (FEED_SPEC, CARD_SPEC, member page, README.md, member-site README, cloudflare README, CONTEXT, 4 cloudflare BRIEFs, PRETRADE, SITE_CHANGES). Also the docstrings and comments of 20 code files and the headers of 30 test files.
- **Statements checked:** about 1,010 (estimate):

| Source | Statements |
|---|---|
| FEED_SPEC | ~240 |
| CARD_SPEC | ~75 |
| Member page words | ~160 |
| CONTEXT current-rule sections | ~95 |
| Three READMEs | ~150 |
| BRIEFs | ~35 |
| PRETRADE | ~10 |
| SITE_CHANGES | ~75 |
| Docstrings and comments | ~130 |
| Test headers | ~40 |

- **COUNTED findings (in scope, kinds 1, 2, 4): 0.**

| Kind | Count |
|---|---|
| 1 (wrong) | 0 |
| 2 (stale) | 0 |
| 4 (reads as a trade, return or track record) | 0 |
| Borderline | 0 |

- **In scope, kind 3 (loose; reported, not counted): 6.**
- **Outside scope (not counted): 5.** Two are kind 2 (one of them borderline) and three are kind 3.

The most important item is not counted, but it needs action before the next site deploy. The committed `cloudflare/ctzb-site-worker.js` is not what `build_site.py` builds from the current page. Rebuilding it changes three places:

- the How-to-read sentence (SITE_CHANGES 6q);
- the "Lead trader" line on the worked example's card (SITE_CHANGES 6r, the liability fix: it read "Lead trader: in · long" beside a past computed signal);
- one code comment.

`BRIEF_site.md` deploys by pasting that committed file, so a deploy now would ship without 6q and 6r. Fix: run `python cloudflare/build_site.py` and commit the result. `build_dashboard.py` reproduces the committed dashboard Worker exactly, so the dashboard Worker is current.

## Method

- **Working copy.** I cloned the repo at 0185de1 into this output folder and worked only there. In the copy I ran `refresh`, `grade_live`, `extras_live`, `stack_live` and `verify_cards`, then `tests/regression.py` (PASS: 919 unchanged, 4 new), then `feed_live.py` with every step reported as success. The feed had 6 cards, 36 prints, 21 open signals and 10 windows, and it passed the strict check.
- **Fields.** I listed every field path in that feed and compared it with every FEED_SPEC table and its strict column. I also compared the FEED_SPEC strict column with `FEED_SCHEMA` key by key.
- **Worker tests.** All six Worker test suites were run, and the counts quoted in `cloudflare/README` all match: 21, 26, 21, 36, 45, 26.
- **Recomputed figures.** All of these match:

| Figure | Where quoted | Recomputed |
|---|---|---|
| Smallest rule-3 pool | CARD_SPEC | 33 |
| First graded ETH signal | CARD_SPEC | ETH 3D 2020-03-21, grade C |
| First ETH top grade | CARD_SPEC | 2020-04-18 |
| troughs.json | CONTEXT | 996 rows, 6 charts |
| Confluence cells | CONTEXT | 176 |
| keep.json setups | README | 12 |
| refresh.py datasets | README, CONTEXT | 13 |
| Signals matching TradingView | README, fetch.py | 297 = 138 + 88 + 47 + 24 |
| Worked example's chart file | member README, FEED_SPEC | 51 bars, 12 Aug through 20-21 Nov 2024 |
| Exchange outages in 4H files | FEED_SPEC | 28 Feb 2017 and 25 Oct 2025 |
| Low-to-confirmation days | CONTEXT | 3/7/11/19/31 |
| numbers_check replay dates | CONTEXT | 13 |
| DAMAGE_LIST families | CONTEXT | 6 |
| Tests asserting schema 6 | FEED_SPEC | 2 |
| Regime on since | CONTEXT | 2026-09-02 |
| fire_drills_result.json | CONTEXT | 58/58 |
| BTC 3D confirmer cells | CONTEXT | any, B, diamond |

## Every finding

Details and paste-ready sentences are in `findings.csv`.

### In scope (kind 3, not counted)

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 1 | cloudflare/README.md:12, 75-77 | 3 | "`ctzb-site-worker.js` (**generated** by `build_site.py`)… Built, not written" | At 0185de1 the committed file is a build of an older page. Rebuilding changes index.html L289 (How to read) and L780 (no Lead trader line on the example), plus one comment. | "The committed `ctzb-site-worker.js` must be rebuilt (`python cloudflare/build_site.py`) and committed after every page change; before a deploy, check that rebuilding leaves it unchanged." Then rebuild it. |
| 2 | docs/FEED_SPEC.md:149-177 | 3 | Cards table lists every card field but `label` | `feed_live.card()` L372 writes `label` on every card. The prints and open_signals tables point to "As on a card" for `label`. | Add the row "\| `label` \| \| The computed-signal label (Rules) \|" |
| 3 | member page index.html:299 | 3 | "Edge gone: The first fall at which this setup's odds drop below our posting bar." | `setupFade` L594-596 and `stack_live.edge_status` L467-468: when the from-entry share is already below 70% the edge is gone with no fall. The card then reads "Below the 70% bar from entry". Today 18 of the 21 open signals (all grades) have `edge_level_pct` 0. | "…drop below our posting bar, or "from entry" when they are below it with no fall at all." |
| 4 | member page index.html:300 | 3 | "If it misses: Of all past signals of this asset and grade…" | On the worked example the pool is only the ETH top-grade signals known by 22 Sep 2024 (L748, L751, "known by then"). | "Of all past signals of this asset and grade (on the worked example, those known by its date) that did not rise 10%…" |
| 5 | docs/artifacts/member-site/README.md:15 | 3 | typed-figures list: "…the example's 2-day bars…" | index.html L343 types every chart's bar length (`TF_DAYS` 1/2/3/5/8/7) for chart steps, day lines and the live entry bar. | "…the example's 2-day bars and each chart's bar length (1D 1 day, 2D 2, 3D 3, 5D 5, 8D 8)…" |
| 6 | CONTEXT.md:227 | 3 | "…from Coinalyze, daily, 2019 on." | 2019-01-01 is only where a backfill asks from. The series start 2020-01-21 (funding), 2020-05-31 (long/short) and 2022-09-13 (open interest), and `fetch.history_problems` enforces those dates. | "…daily (a backfill asks from 2019; the series start where Coinalyze's do: funding 2020-01-21, long/short 2020-05-31, open interest 2022-09-13)…" |

### Outside scope (not counted)

| # | File:line | Kind | Quote (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|
| 7 | docs/SITE_CHANGES.md:38-39 (Pending 6q, 6r) | 2 | Pending = "built and committed but NOT yet live… one Chrome paste" | The page on disk has both changes. The committed Worker file that the paste deploys has neither (see #1). | Rebuild and commit `ctzb-site-worker.js`; then the rows are true as written. |
| 8 | cloudflare/BRIEF_site.md:88, 90 | 2, borderline | "'Data through' today's date… Click Chart, Record… Record lists about 137 rows." | The footer reads "Daily candles closed through <yesterday>" (L913-914). The tab is "Past signals" (L205). Borderline because this is a dated 11 Nov brief, but SITE_CHANGES says it is re-pinned and reused for each deploy. | "…"Daily candles closed through" yesterday's date… Click Chart, Past signals and How to read a card." |
| 9 | fetch.py:388-393 | 3 | history_problems docstring: lag=True item and "ends with a whole line and holds no blank line" | `_file_problem` also fails a stray CR (round 42). With `lag=True` it also runs `rows_lost_problems`, the series_through.json check (round 44). | Add "no carriage return outside a CRLF line end", and add the series_through.json rule to the lag=True item. |
| 10 | .github/scripts/check_candles.py:13-19 | 3 | "whole history (fetch.history_problems): … every row … well formed" | The summary omits the whole-file rule: a cut last line, a blank line or a stray CR all fail. | Add "every file ending with a whole line, with no blank line and no stray carriage return". |
| 11 | engine.py:73 | 3 | "Read a TradingView export." | Every pipeline caller passes fetch.py's Coinbase `data/*.csv`. `load()` reads both formats and clamps flash prints. | "Read a candle file (fetch.py's data/*.csv or a TradingView export), clamping flash prints." |

## Documents with zero findings

- **Docs:** docs/CARD_SPEC.md; README.md; docs/PRETRADE.md (pipeline statements); cloudflare/BRIEF_dashboard.md, BRIEF_monitor.md and BRIEF_trades.md (worker behaviour).
- **SITE_CHANGES "Requested, not built yet":** R1, R2 and R3 are really not built.
- **SITE_CHANGES "Pending":** the page on disk does every row, as amended by the later rows. The only exception is #7, and it concerns the Worker build, not the page.
- **Docstrings and comments:** refresh.py, grade_live.py, stack_live.py, verify_cards.py, extras_live.py, feed_live.py, feedcheck.py, seal.py, measures.py, rounding.py, clock.py, regimes.py, analysis/tagstats.py, analysis/carddesign.py, .github/scripts/check_fresh.py, .github/scripts/retry_after_failure.sh and .github/workflows/daily.yml.
- **Test headers:** every header in tests/*.py, tests/*.sh and tests/*.mjs. The quoted counts I could run match.

## Could not check, and why

- **Cron triggers.** ctzb-feed `*/15`, ctzb-dashboard `5,20,35,50` and ctzb-trades `* * * * *` are set in the Cloudflare dashboard, not in code. Only the code comments state them.
- **Deployment facts.** Version ids, the Access team, "live since" times and the R2 lifecycle rule are not visible from the repo.
- **Dated history and research results.** I checked these only for undated current claims, as the brief says.
- **fire_drills.** I did not re-run it: it needs a browser and takes several minutes. The 58/58 in CONTEXT matches `tests/fire_drills_result.json` (12 Nov), but `fire_drills.py` itself changed on 14 Nov.
- **Browser tests.** The playwright tests (page states, timing, damage) and the live member site were not run.
- **Excluded by the brief.** The numbers and the broken-file behaviour. Of docs/audit/ I read only the headings of DAMAGE_LIST.md, to count its families. I did not read AUDIT_LOG.md or any analysis/audit* folder.
