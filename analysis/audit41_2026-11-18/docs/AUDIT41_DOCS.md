# Audit 41, docs pass (frozen code 01f3976)

Entry quality only: everything checked here describes computed signals and their 60-day records. There are no fills, no exits and no strategy return. No document or page sentence was found that reads as a trade taken, a return or a track record.

## Top line

| | |
|---|---|
| Documents read | 21: the 7 in-scope documents (member page words + FEED_SCHEMA comments, FEED_SPEC, CARD_SPEC, README.md, member-site README, cloudflare/README, CONTEXT current-rule sections plus a scan of its dated record), 4 cloudflare BRIEFs, PRETRADE (pipeline statements), SITE_CHANGES (Pending + Requested rows), and the docstrings, comments and test headers on the brief's list (feed_live, stack_live, refresh, grade_live, verify_cards, extras_live, feedcheck, seal, engine, measures, rounding, clock, fetch, regimes, tagstats, carddesign, .github/scripts/*, daily.yml, tests/*.py, *.sh, *.mjs) |
| Statements checked | about 760 (in scope about 590, outside scope about 170) |
| **COUNTED findings (in scope, kinds 1, 2, 4)** | **0**: kind 1: 0 · kind 2: 0 · kind 4: 0 |
| In scope, borderline (fixed, not counted) | 1 (kind 1, CONTEXT open-items note) |
| In scope, kind 3 (reported, not counted) | 8 |
| Outside scope (not counted) | 2 (1 kind 1, 1 kind 3) |

How this was checked: a copy was made at 01f3976 and the whole pipeline was rebuilt there (refresh, grade_live, extras_live, stack_live, verify_cards, regression, feed_live with every step reported as success). Every key in the rebuilt feed (327 paths) was compared with FEED_SPEC, and every FEED_SPEC field was found in the feed or in code. The page's strict check was compared with FEED_SPEC "The strict check" rule by rule. The six Worker test suites were rerun and all counts quoted in cloudflare/README match: 21, 26, 21, 45, 26, 36. The gate-off replay was rerun and passes with 10 forming lows, which is the figure test_gate_off.sh quotes. test_seal (29/29), test_feed_extras (28/28), test_feed_alerts (89/89) and test_midnight (7/7) pass. Both generated Workers were rebuilt and diffed. Recomputed counts that match: schema 6 and the two tests that assert it; 176 confluence cells (83 + 49 + 44); 996 trough rows on 6 charts; 13 perp markets per asset; 12 keep.json setups; 11 tags; 13 refresh datasets; 13 replay dates; 58/58 fire drills; 51 example bars from 12 Aug through 20–21 Nov 2024; the smallest rule-3 pool (33); the first graded ETH signal (ETH 3D, 21 Mar 2020, C); the first ETH A+ (18 Apr 2020); "95 misses of all 313"; the lags 3/7/11/19/31; the regime turning on on 2026-09-02; the 4H gaps (28 Feb 2017, 10 Aug 2018, 25 Oct 2025); the ETH/BTC close ratio range (0.77–14.96%); and the funding range (−0.49 to 0.30).

## Every finding

| # | File | Line | Kind | Quoted (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| 1 | member page | 296 | 3 | "Typical high: The median best price within 60 days, from the entry close." | The tile shows `typical_biggest_rise_exact_pct`, a % move (index.html 775); CARD_SPEC 82 calls it the median best move | `<dt>Typical high</dt><dd>The median best move within 60 days: how far above the entry close the highest price went, as a percentage.</dd>` |
| 2 | member page | 299 | 3 | "Edge gone: The first fall at which this setup's odds drop below our 70% bar." | Leaves out two cases: the card reads "Below the 70% bar from entry" when the from-entry share is already under the bar, and "Holds at every level" when no row is (index.html 595, 755) | `…drop below our 70% bar; "below the bar from entry" when even the first row is under it, and "holds at every level" when no row is.` |
| 3 | member page | 300 | 3 | "…the median best price of all those misses…" | The value is `median_peak_pct`, the median `bestMove` in % (carddesign.py 73-78), shown as "median best +5.3%" | `…and the median best move of all those misses within the 60 days, as a percentage above the entry close (the row names the pool).` |
| 4 | member page | 1216 | 3 | "Misses: median best price" | Shows `pct(mi.median_peak_pct)`, a % | `Misses: median best move` |
| 5 | CARD_SPEC | 87 | 3 | "…and the median best price of all those misses" | Same as #3 | `…how many had a best price above entry, and the median best move (% above the entry close) of all those misses` |
| 6 | FEED_SPEC | 63 | 3 | "Shares are whole numbers; median moves and changes 1 decimal; …" | `if_it_misses[].mean_peak_pct` is a mean, also rounded to 1 decimal (carddesign.py 79), and the list leaves it out | `Shares are whole numbers; median and mean moves and changes 1 decimal; …` |
| 7 | README.md | 10 | 3 | "Columns are time,open,high,low,close,volume … ETH_4H, ETH_12H and the BTC equivalents are rebuilt from Coinbase's hourly candles." | `fetch.hourly` keeps only (o,h,l,c) (fetch.py 64), so `resample_intraday` has no volume to sum (fetch.py 88). Every 4H and 12H row has volume 0: 22,996, 23,845, 7,669 and 7,950 rows, with none non-zero | `… rebuilt from Coinbase's hourly candles; their volume column is always 0 (the hourly volume is not kept).` |
| 8 | member-site README (also cloudflare/README 12) | 16 | 3 | "Deployed as the ctzb-site Worker (cloudflare/ctzb-site-worker.js, built by cloudflare/build_site.py …)" | Running `build_site.py` at 01f3976 changes the committed `ctzb-site-worker.js`. The committed build still has "Every confirmed setup is checked against several independent confirmations" and lacks Pending row 6q | Rebuild and commit `ctzb-site-worker.js`, or add: `rebuild it before each deploy; the committed build can lag the page.` |
| 9 | CONTEXT.md | 1372 | 1, borderline | "[done: data/*.csv carry volume and 4H/12H history] … brings down volume" | 4H/12H volume is all zeros (see #7). Borderline because it is an open-items note rather than a current-rule section, and it shows no member figure, so it does not count | `[done: the 1D-8D files carry volume; the 4H/12H files carry history with a volume column of 0, since fetch.py keeps no hourly volume]` |

### Outside scope (not counted)

| # | File | Line | Kind | Quoted | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| 10 | fetch.py docstring | 47 | 1 | "Returns {unix_ts: (o,h,l,c,v)}." | Stores `(op, hi, lo, cl)` with no volume (line 64) | `Returns {unix_ts: (o,h,l,c)}: the hourly volume is not kept, so the 4H/12H files carry volume 0.` |
| 11 | member page JS comment | 620 | 3 | "a daily close (00:00 UTC, when every graded chart's bar closes)" | Only the 1D bar closes at every 00:00 UTC; 2D, 3D and 5D bars close every 2, 3 or 5 days, restarting on 1 January (`fetch.resample`) | `a daily close (00:00 UTC, when the daily bar, and any 2D-5D bar ending that day, closes)` |

Full text, code references and paste-ready sentences: `findings.csv` in this folder.

## Documents with zero findings

- docs/FEED_SPEC.md: no kind 1, 2 or 4. Every field, table, corrections section, alert rule, seal rule, input check and strict-check rule matches the code and the rebuilt feed. Its only finding is #6, kind 3.
- docs/CARD_SPEC.md: no kind 1, 2 or 4. Its only finding is #5, kind 3.
- cloudflare/README.md: no own finding; it shares #8.
- cloudflare/BRIEF_dashboard.md, BRIEF_monitor.md, BRIEF_site.md (pinned to the deployed 9a013e3 build, consistent with it), BRIEF_trades.md
- docs/PRETRADE.md (pipeline and code statements)
- docs/SITE_CHANGES.md: the page on disk does what every Pending row (1 to 6q, 7, 7b) says, and R1, R2 and R3 are not built.
- CONTEXT.md current-rule sections: The setup, Confirmation lag and its correction, Regime gate, Traps, Where things live, the Standing instructions paragraphs on the card, feed, Workers, strict check, whole stack, and 4 Nov notes with their superseded markers.
- Docstrings, comments and headers in refresh, grade_live, stack_live, verify_cards, extras_live, feed_live, feedcheck, seal, engine, measures, rounding, clock, regimes, analysis/tagstats, analysis/carddesign, .github/scripts/*, daily.yml, and every tests/*.py, *.sh and *.mjs header

## Could not check, and why

- I did not run the browser suites (test_feed_damage, test_page_states, test_page_timing, test_per_year, numbers_check), fire_drills.py or test_year_end. They take a long time and need playwright. I checked their headers against the code they drive by reading.
- test_cut_files, test_input_files, test_series_cells, test_check_candles and test_fetch_today were still running when this report was written. Their headers were checked by reading.
- Deployed Workers and live URLs: these docs are checked against the repo source only. The live Cloudflare versions (656d67c3 and others) cannot be reached from here.
- The rebuild fetched fresh candles to 18 Nov 2026, so live figures in the feed differ from the committed feed. That has no effect on any doc statement checked here.
