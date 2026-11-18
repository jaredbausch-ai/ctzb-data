# Audit round 38: docs against code (frozen at af13e4c)

Entry quality only. Everything checked here describes computed signals and their 60-day records. There are no fills, no exits and no strategy return.

## Top line

| | |
|---|---|
| Documents read | 23 (7 in scope, 16 outside scope; listed below) |
| Statements checked | about 1,040 (about 700 in scope, about 340 outside) |
| In-scope findings, kind 1 (wrong figure, threshold, window, rounding or field meaning) | 0 |
| In-scope findings, kind 2 (stale) | 1 |
| In-scope findings, kind 3 (loose or incomplete) | 4 |
| In-scope findings, kind 4 (reads as a return, a trade or a track record) | 0 |
| **In-scope kinds 1 + 2 + 4 (these decide whether the round is clean)** | **1** |
| Outside scope (not counted) | 4 (kind 3: 3, kind 4: 1) |

**Verdict:** the round is not clean. One in-scope finding counts: CONTEXT.md line 1477, a liquidation share that has moved since it was written.

The repo was copied to `audit38d/repo` at af13e4c. The feed was rebuilt in a second copy, `audit38d/run`, using the brief's command sequence. Every step passed: regression 919 unchanged and 4 new, 26 cards matched the ledger, and the feed has 4 cards, 21 open signals and 10 windows. The rebuilt feed's field list was compared with FEED_SPEC: every field in the feed is described, and every field the spec names exists. Rebuilding `ctzb-site-worker.js` and `ctzb-dashboard-worker.js` from their sources gives byte-identical files.

## Every finding

### In scope (counted)

| # | File | Line | Kind | Quoted sentence (short) | What the code does | Suggested sentence (ready to paste) |
|---|---|---|---|---|---|---|
| 1 | docs/FEED_SPEC.md | 421-422 | 3 | "every candle file ... present, with a volume column and every row exactly the header's cells" | `fetch.history_problems` fails a candle file whose header is not exactly `time,open,high,low,close,volume`: a repeated, extra, missing or reordered column (fetch.py:142, 340-344; round 37 fix 63adca9). The spec mentions only a volume column. | "- every candle file (1D to 8D, 4H, 12H) present, with a header that is exactly `time,open,high,low,close,volume` (no extra, missing, repeated or reordered column) and every row exactly the header's cells; every cell readable; prices finite and above zero; high and low bracketing open and close; volume not negative; times on the bar grid (daily and multi-day bars at midnight UTC) and strictly ascending;" |
| 2 | CONTEXT.md | 1477 | 2 | "At 3.3x with no reserve that share is, for ETH, A+ 14%, A 25%, B 27%, C 36% ..." | The console liquidates at −25.30% (3.3x, 5% maintenance, no reserve; eth-setup-standard.html:267). It counts dips at or below that level in `datasets/dipdist.csv` (line 286). ETH A is now 16 of 62, which rounds to **26%**. The other seven figures still match. | "At 3.3x with no reserve that share is, for ETH, A+ 14%, A 26%, B 27%, C 36% (BTC: A+ 15%, A 14%, B 23%, C 27%) as of 18 Nov 2026; the shares move as signals close (datasets/dipdist.csv)." |
| 3 | CONTEXT.md | 1466-1469 | 3 | "check_coverage() fails the run ... if a PRETRADE heading ... is not mapped in DOC_MAP or a registry id is not evaluated." | It also fails when a DOC_MAP id is missing from REGISTRY. The "not evaluated" rule applies only when there is at least one subject, so a quiet market passes (stack_live.py:144-156, line 149). | "`check_coverage()` fails the run (red Action + `datasets/stack_status.txt` FAILED) if a PRETRADE heading in Tier 1 / Promising / In-trade is not mapped in DOC_MAP, a mapped id is not in REGISTRY, or, when there is at least one forming low or open signal to evaluate, a registry id is not evaluated." |
| 4 | docs/artifacts/member-site/index.html | 1156 | 3 | "Price on day 60" (the worked example's "What this one did" box) | The value is the percentage change of the day-60 close from the entry close (`pct((bars[E+30].c / entry_close - 1) x 100)`), not a price. The card tile for the same measure was already renamed "Typical change by day 60" (SITE_CHANGES row 5), and CARD_SPEC:74 calls it "day-60 close vs entry". | Change the row label to "Change by day 60". The value stays the same. |
| 5 | docs/artifacts/member-site/index.html | 828, 832 | 3 | "His real entries and exits appear here the moment they fill." (two places) | The relay reads fills once a minute and publishes nothing until MODE=live (ctzb-trades-worker.js, cron `* * * * *`). The page fetches `data/trades.json` once at load (index.html:1268) and never polls, so a fill appears only after the next relay tick and a reload. | "His real entries and exits are posted here automatically, within about a minute of each fill, once his feed is live (reload to see the latest)." |

### Outside scope (reported, not counted)

| # | File | Line | Kind | Quoted sentence (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| O1 | tests/test_action_env.py | 1-5 | 3 | "after refresh.py (and fetch / check steps) have run. Run those steps here with numpy blocked" | `STEPS = [refresh.py]` only (line 12). The fetch and check scripts are never run with numpy blocked. | "... after refresh.py (and the fetch / check steps) have run. Run refresh.py here with numpy blocked, so a numpy import in it fails locally too" |
| O2 | verify_cards.py | 8-9 | 3 | "fails the run if any differs, exactly: ... the rounded and exact medians" | The three `*Exact` medians are allowed a tolerance of 1e-6 (line 152). The comment at lines 149-151 says so; the docstring does not. | "fails the run if any figure differs: exactly for n, the big number, surv10, scaled20, +20%, -30%, the rounded medians, the eras, the timing and the ladder rows, and to one unit in the 6th place (the ledger's precision) for the three exact medians" |
| O3 | .github/scripts/check_candles.py | 13-15 | 3 | "whole history (fetch.history_problems): every row of every candle file well formed (...)" | The list leaves out the round-37 rule that the header must be exactly `time,open,high,low,close,volume` (fetch.py:340-344). | "- whole history (fetch.history_problems): every candle file's header exactly time,open,high,low,close,volume and every row well formed (...)" |
| O4 | CONTEXT.md | 1626 (dated 4 Nov note) | 4 | "the median lowest low between the buy and the day of the 60-day high, as a percentage of the BUY PRICE" | The measure (tagstats.py:55,63, ddpk) is taken from the entry close of a computed signal; nothing was bought. The 14 Nov bracket fixed the dashboard's wording but not this note's own sentences. | "It is the median lowest low between the entry close and the day of the 60-day high, as a percentage of the ENTRY CLOSE (...). Relabelled "Typical lowest point vs the entry close, before it made its 60-day high" (14 Nov 2026; on 4 Nov it read "the buy price")" |

All nine rows, with the code references in full, are in `findings.csv`.

## Documents with zero findings

**In scope:** docs/CARD_SPEC.md, README.md, docs/artifacts/member-site/README.md, cloudflare/README.md.

The member page's FEED_SCHEMA block and its comment, the strict-check rules, "How to read", the banners, badges, headings and footer all match the code. FEED_SPEC has no finding apart from #1. Every Strict-column type was compared with the page's FEED_SCHEMA, and every cross-field rule with feedcheck.py and the page's crossCheck.

**Outside scope:** cloudflare/BRIEF_dashboard.md, BRIEF_monitor.md, BRIEF_site.md and BRIEF_trades.md (the byte counts of every pinned file were checked at their pinned commits); docs/PRETRADE.md (pipeline statements only); docs/SITE_CHANGES.md (every Pending row is built on the page or Worker on disk, and R1, R2 and R3 are not built).

The docstrings and comments of these files have zero findings: refresh.py, grade_live.py, stack_live.py, extras_live.py, feed_live.py, feedcheck.py, seal.py, engine.py, measures.py, rounding.py, clock.py, fetch.py, regimes.py, analysis/tagstats.py, analysis/carddesign.py, check_fresh.py, retry_after_failure.sh and daily.yml.

Every test header other than test_action_env.py has zero findings.

## Counts recomputed (all match unless listed above)

- Fixed counts and constants:
  - 13 refresh datasets; 11 candidate tags; 12 setups in keep.json.
  - 176 confluence cells (83 + 49 + 44); 12 DOC_MAP headings.
  - Smallest rule-3 pool is 33 (BTC A+).
  - About 14 Coinbase requests per asset.
  - 26 scheduler dispatches a day (12 + 6 + 8).
- Dates and data:
  - First graded ETH signal: ETH 3D, 2020-03-21, grade C. First ETH A+: 2020-04-18.
  - troughs.json has 996 rows on 6 charts.
  - The regime gate turned on 2026-09-02 and is still on.
  - The ETH 3D signal with low 13 Sep confirmed on 24 Sep 2026.
  - Series start dates: 2020-01-21, 2020-05-31, 2022-09-13 and 2016-11-01.
  - Shared 4H outages are 28 Feb 2017 and 25 Oct 2025. One-asset gaps match OWN_GAPS.
  - The example file has 51 bars, 12 Aug to 20 Nov 2024.
- Tests:
  - Node suites: 21, 26, 21, 45, 26 and 36 checks, all passing.
  - fire_drills_result.json records 58/58. numbers_check has 13 replay dates.
  - The gate-off replay of 2026-06-11 has 10 forming lows. The 4aa1208 fixture has 4 forming setups.
- Pinned brief files: 16,881 / 65,188 / 87,466 / 21,762 bytes.
- dipdist shares: 15 of 16 match; ETH A is finding #2.

## Could not check, and why

- **Live Cloudflare state.** Deployed version ids, "LIVE since" times, KV contents, Access policies, and the dashboard and trades cron settings are configured in Cloudflare, not in the repo. Only the briefs and the code were compared.
- **External research figures.** TradingView match counts, Kraken gap history, the Coinalyze market list, the restore-drill byte counts and the GitHub cron history are dated records, not recomputable here.
- **Browser tests not run.** I did not run the playwright suites (test_feed_damage, test_page_states, test_page_timing, numbers_check, test_per_year) or the full fire drills. Their headers were checked against their code, not against a run.
- **Run-time claims not timed.** "About 3 minutes" for a run or for the fire drills was not measured.
