# Fix check, audit round 27 (commit 3674a05 against 90ed06f)

Independent check, 14 Nov 2026 UTC. Nothing in the repo was edited. Copies: `head/` (3674a05) and `old/` (90ed06f's
fetch.py, index.html and site Worker checked out). Probes: `probe_pipeline.py` and `probe_page.py`, both in this folder. This is a check of the
damage fixes only. The data has no exits, so nothing here is a return, a strategy result or a track record. Every
signal is a computed signal, not a fill.

| Finding | Verdict | Evidence | Smallest change to fix |
|---|---|---|---|
| #1 funding_oi_weighted not range-checked (15 runs) | fixed | fetch.py:203-215 (`_cells_problem`), :317-327; test_series_cells 32/32 on 3674a05, fails on 90ed06f (ETH funding cells 6/96, oi_weighted 3.0 and -1.5 pass). My own cases, all caught on 3674a05 and all passed by 90ed06f: oi_weighted "Infinity", -1e5 mid-history, pcr_prem inf (an unread column), lsratio n_markets "twelve", oi market column 1e400. A padded " 0.001 " passes (same value the scorer reads) | none |
| #2 funding 3 days behind changed the ETH 1D card | **wrong** (side effect) | The rule is at family level: fetch.py:200, :256, :329. My cases: funding and OI 2 days behind and put/call 3 days behind are caught, and 1 day behind passes. 90ed06f passes all of them. But the lag is enforced in check_candles (daily.yml:105, no continue-on-error), which runs before the candle commit and before "Fetch derivatives positioning" (daily.yml:193). One UTC day with no successful derivatives fetch (Coinalyze down, or the key refused, fetch_derivs.py:61) makes every later run stop before the only step that could catch up. Candles stop committing and the feed goes stale until someone steps in. Shown: derivatives cut by 2 days, check_candles exits 1 on 3674a05 and 0 on 90ed06f. Before the fix this took more than 3 days | Apply the lag rule in stack_live only, so a stale series withholds the cards (stack=failure, which the audit expected) while the candle commit and fetch_derivs still run. For example, add a `max_lag=None` switch to `history_problems` and use it from check_candles |
| #2 (gap in the family) | incomplete | Put/call lag is measured on the row date. Blanking `pcr_amt` on the last 3 rows passes on both versions (fetch.py:243-251, blank_ok), and the scorer skips blanks (analysis/pcrtest.py:71). Effect on figures not measured | In fetch.py, allow a blank `pcr_amt` only where `call_amt` is 0. All 63 real blanks (2016-17) have `call_amt` 0 |
| #3 23:13 feed read at 00:05, no note | fixed | index.html:595-602, :604-610, :1239-1245; test_page_timing 11/11 (4d fails on 90ed06f, 10/11). My cases, all caught on 3674a05 and missed on 90ed06f: feed at 23:59:30 seen at 00:00:40; the note on Chart, Past signals and How to read; a page opened at 23:58 on a 20:13 feed shows the note by 00:01 with no reload. Also correct: 5 h later the hours-old note replaces it, and a 00:14 feed read at 03:00 shows no note | none |
| #4 per-year count on 1 January | fixed | index.html:824-834, exact against tagstats.py:47-52 (a signal is listed once bar d0+60 has closed, so all of year Y is listed from Jan 1 Y+1 + 60 days). test_per_year passes on 3674a05 and fails on 90ed06f ("2020 to 2025"). My cases (scored date, last year averaged): 2026-03-01 → 2024; 2026-03-02 → 2025; 2028-02-29 → 2026 and 2028-03-01 → 2027 (leap year); 2027-01-01 → 2025. All right on 3674a05; 90ed06f fails 3 of the 5 | none |

**Nothing else moved:** on 3674a05, `numbers_check` shows every figure unchanged on all 13 dates. Also passing:
test_cut_files 496/496, test_check_candles 95/95, test_seal 23/23, test_page_timing 11/11, test_per_year,
test_series_cells 32/32. The site Worker's PAGE matches index.html verbatim.

**Lag claim checked:** across the 133 committed runs in git (1 to 14 Nov), the derivatives were 0 days behind 119
times and 1 day behind 14 times; put/call was 1 day behind 118 times and 2 days behind 15 times. Nothing was further
behind, so the limits are right. The "79 runs from 25 Oct" count cannot be reproduced: git holds no run before 1 Nov.

## Changed sentences that fail (details and suggested text in failing_sentences.csv)

FEED_SPEC: 3 sentences fail.
1. **FEED_SPEC.md:387-388** "The scoring steps read the last known day as today's, so a series further behind would change
   the forming cards" (4/5). This is true of funding only: stack_live.py:225-229 (funding_at) and :232-240 (fcool_at).
   Long/short reads d or d-1 only (:262). Put/call reads the last Sunday's 7-day value (:242-245). OI is read only in
   the positioning line (:631-633). The same sentence is in fetch.py:196-197 and AUDIT_LOG Round 27.
2. **FEED_SPEC.md:385-386** "`funding_oi_weighted`, read first, and `funding_mean`, its fallback, between -1 and 1 where
   filled" (5). `funding_mean` is also read directly by the FCOOL lens (analysis/grade3.py:60-66, stack_live.py:176,
   grade_live.py:130). It must also be filled on every row: a blank fails (fetch.py:316). The same error is in the
   fetch.py:268-270 docstring.
3. **FEED_SPEC.md:442-443** "Both are re-checked every minute on the viewer's clock and are the only texts that depend
   on it" (4/5). The lead-trader check rejects a trade more than 5 minutes after the viewer's clock (index.html:526).
   When both conditions hold, only the hours-old note shows (index.html:598 returns before :600), which the sentence
   leaves out. The comment at index.html:594 makes the same claim. The unchanged comment at index.html:1238 ("the only
   text") now contradicts it.
4. **fetch.py:273** "(79 runs from 25 Oct to 14 Nov 2026: never more)" and **AUDIT_LOG.md:895** "measured over the last
   79 runs" (4). The count cannot be reproduced; git shows 133 committed runs from 1 to 14 Nov.
5. **fetch.py:197-199** "at the next run's scoring the derivatives end at most 1 day behind" (5). This holds only after
   a successful derivatives fetch on the previous day. Otherwise the run stops at check_candles (see #2).
6. **AUDIT_LOG.md:883 vs :893** The table counts the stale-funding run as Pipeline Malformed 318/16 and Timing 16/0,
   but the causes list calls it "Timing (1 run)" (4).
7. **DAMAGE_LIST.md:18** (Timing row) "each derivatives series" leaves out put/call, which `MAX_LAG_DAYS` covers. "yearly
   counts use only full years" is also what the old code did; the rule is "full years whose signals have all had their
   60 days close" (index.html:827-830) (5).

The member page's new words are true. The daily-close note matches index.html:600, and the Worker runs at :13 after
each close (ctzb-scheduler-worker.js:12). The per-year line matches index.html:833. No changed sentence breaks the
wording rules or puts history in a spec. CONTEXT.md is not changed by the commit.
