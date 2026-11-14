# Fix check, audit round 30 (commit 74a3428; AUDIT_LOG d1e4e52)

Independent check, 14 Nov 2026. Nothing in the repo was edited; all runs were on copies. Entry quality only: the
pipeline publishes computed signals, not fills, and nothing here is a return or a track record.

| Finding | Verdict | Evidence | Smallest change that would fix it |
|---|---|---|---|
| A. Chart/extras file changed between grade and extras was served with the cards | **incomplete** | Fixed between grade and extras: extras_live.py:80-85 deletes, seal.py:141 ignores for the extras step. My cases A1-A5 (missstats altered, ETH 8D deleted, oddsfade cut mid-line, BTC 5D swapped for an older copy, both example files emptied) are all written again, identical to a clean run, and the run publishes clean. A non-extras seal problem still stops extras (A6 stray file, A8 data/BTC_1D.csv cut: extras and stack refuse, no extras file left). After a successful extras, a changed chart file is still caught (A9 before stack, A11 after cards) and so is a deleted oddsfade (A10). Extras run twice: the second refuses, and the run is held (A12). **Still gets through:** if extras fails part-way after its first write (a kill, a timeout, any exception after :132), this run's chart files stay (A13: 10 left; A15: 6 left). seal.py:141 and feed_live.py:415-416 then ignore EXTRAS_FILES. A14: extras killed at missstats.csv, then a candles_btc_1d.csv middle bar's high raised 25% before stack. Result: stack and cards pass, the feed is published (cards_withheld false, extras_withheld true), and the altered bar is still in datasets/, which the site worker serves (site_worker_template.js:161). A16: extras dies before writing, and the last run's candles_btc_1d.csv is put back before stack. It is published beside the feed. | In feed_live.py, when extras did not succeed, remove every seal.EXTRAS_FILES file from datasets/ before writing the feed, so the page reads "Chart data unavailable". Or make the later checks treat any extras file present after a failed extras as damage. Add a test_seal case: extras killed after its chart files, then a bar altered before stack. |
| A, test | fixed | tests/test_seal.py: 27/27 on HEAD; 24/27 with c8fe698's extras_live.py, seal.py and fetch.py (the 3 new cases fail) | covers grade→extras only, not the A14 path |
| B. funding_oi_weighted lost and still scored | **fixed** | fetch.py:385-402. 42 own cases (21 per asset): emptied, removed, renamed, blank on one day, on 2022-09-13, on 181 days, from 2022-09-13 on, on the last day while OI has it, filled on 2022-09-12, filled 2020-2022, set to 0, emptied with the OI file deleted, cut to its header, cut mid-line, last 300 days cut, OI column renamed, OI's last total blanked. Each fails at the candle check, except two (blank on days the OI file was cut back to by the same amount, 2 or 300 days), which fail at the stack step through the OI lag rule, so the cards are held. On c8fe698, 22 of these 42 pass both checks. Passes as it should: the real committed data (lag on and off); live with OI one day behind (last day blank or filled). Replays: 2021-06-01, 2022-09-12, 2022-09-13, 2022-09-14 and 2026-11-13 are all "ok". Last 80 committed versions of both funding files: no blank from 2022-09-13 on. | - |
| B, test | fixed | tests/test_series_cells.py: 62/62 on HEAD; 42/62 on c8fe698 (20 new cases fail, the live case passes on both) | - |
| Nothing else moved | fixed | numbers_check: 13 dates unchanged. test_input_files 61/61, test_check_candles 95/95, test_feed_extras 28/28. | - |

Not a round-30 finding, seen in passing: an OI file of non-UTF-8 bytes makes history_problems raise
UnicodeDecodeError (fetch.py:257, `_series_problems`, code from before this fix). The step stops, so this fails safe.

## Changed sentences that fail (detail in failing_sentences.csv)

FEED_SPEC: 2 sentences changed, **1 fails**. Docstrings and comments in fetch.py, extras_live.py and the two test
files: all true. DAMAGE_LIST's test claims are true: test_seal covers family 2's new extras clause and family 4's
"before its own seal check", and test_series_cells covers the funding clause.

1. **FEED_SPEC.md:386-387** "...when it fails (its seal check included) none of them is left". False (rule 4) when
   extras fails part-way: extras_live.py:132 writes each chart file inside the loop, before :135-149 write the rest.
   A stop after the first write leaves those files (A13, A15). The sentence is also incomplete (rule 5): oddsfade.csv
   comes from earlydip.csv and holdcheck.csv (extras_live.py:114), not from "ledger and candles".
2. **DAMAGE_LIST.md:15** (family 2) "...so a damaged one is never served". False: A14 and A16. The steps after a
   failed extras ignore these files (seal.py:141, feed_live.py:415-416).
3. **seal.py:139-140** "(feed_live.py withholds them)". feed_live.py:541-590 withholds only the missstats, oddsfade
   and pastpaths fields. The 10 chart files stay in datasets/ and are served (site_worker_template.js:161).
4. **AUDIT_LOG.md:1097-1099** "when it fails, none of its files is left". Same problem as 1.
5. **AUDIT_LOG.md:1104** "the one day open interest has not yet reached may be blank". At the candle check, any
   number of days that the OI file lacks may be blank (fetch.py:398 tests only the days in oi_days). Only the stack
   step's OI lag rule (MAX_LAG_DAYS oi = 1) limits it to one day.
6. **AUDIT_LOG.md:1109** "series cells 42 of 58 then". On c8fe698 the run gives 42/62 (20 new cases fail).

No changed sentence breaks rule 6 (history in a spec) or rule 7 (wording).
