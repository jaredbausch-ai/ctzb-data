# Fix check 34, docs part: commit 07339b1 against the frozen code (4388653)

Entry quality only: everything checked describes computed signals and their 60-day records. There are no fills or exits, and no strategy return.

**Checks that apply to the whole commit.** All of them pass. Every changed line in a .py, .js or .html file is a comment, docstring, label or visible text, and the `FEED_SCHEMA` block did not change. `numbers_check.py` reports "numbers unchanged: 13 dates, every dataset, feed and page figure identical". Both Workers rebuild to identical bytes (sha256 OK). `test_page_states` passed 56/56, `test_site_worker` 26/26 and `test_dashboard_gate` 26/26. No test asserts the new page texts, so I rendered them separately (scripts/render_new.py). The live card line, the line under the big number, the chart side box, How to read L290/L300 and the quiet card with the filter on all render. The quiet card's "unavailable" variant cannot be reached: the strict check rejects a clean feed with no `market_regime`. No changed sentence breaks the wording rules or adds history to a spec.

| # | Verdict | Evidence | Smallest further change |
|---|---|---|---|
| 1 | fixed | refresh.py L159-163 (provisional tags), L336-339; filled/hollow/diamond+dot are diamond types (L131-136) | — |
| 2 | **wrong** | New FEED_SPEC:110 says "a run with no log fails closed unless it is seeding". A deleted log is restored from the second copy or rebuilt from the last feed (feed_live.py check_log L234-251), as FEED_SPEC:330 itself says ("deleted"). tests/test_feed_alerts.py L183-187 checks "alert log deleted, its copy whole -> restored exactly" | "...a run that finds no log restores or rebuilds it as below, and fails closed when it cannot; null on a held seeding run with no log, and..." |
| 3 | fixed | feed_live.py L427-450, L573-574, L632-634, L642-646, L770-772 | — |
| 4 | fixed | feedcheck.py L133-135; index.html L461, L516-517 | — |
| 5 | fixed | index.html staleBars L632-638; staleNote is in the held/down, quiet and normal branches; none in L702-706 or L722-726 | — |
| 6 | fixed | index.html L548; feedcheck.py L238/L241 | — |
| 7 | fixed | stack_live.py L554-556, L567-571; tagstats.measure L44-52 (only windows that have closed) | — |
| 8 | fixed | ctzb-scheduler-worker.js GRACE.withheld L149, L294-296 | — |
| 9 | fixed | CARD_SPEC L4, L129; no other "trade card" or "per-trade" in CARD_SPEC | — |
| 10 | fixed | index.html L755, L760, L1157; no "as of the entry close" left in scope | — |
| 11 | fixed | stack_live.py L554-556; the sample is printed under the big number (index.html L762) | — |
| 12 | fixed | extras_live.py L95-101 (asset+grade pool); the row names the pool (index.html L741) | — |
| 13 | fixed | index.html L640-644, L728-733; rendered | — |
| 14 | fixed | index.html L387-391 | — |
| 15 | fixed | FEED_SPEC headings L441, L476; no "Audit #21/#22 corrections" left in the repo | — |
| 16 | fixed | index.html L548 | — |
| 17 | fixed | index.html L628, L835, L880 | — |
| 18 | **incomplete** | The dashboard row now lists its password, but the ctzb-site row (README:12) still says "none". It holds `SITE_PASSWORD` in password mode (site_worker_template.js L24, L109-114). The ctzb-trades row (README:11) also omits `COINBASE_KEY_NAME` and `DRY_VIEW_PASSWORD` (ctzb-trades-worker.js L30-31) | Site: "`SITE_PASSWORD` in password mode; reads the mirror..." Trades: add "`COINBASE_KEY_NAME`; `DRY_VIEW_PASSWORD` for /dry" |
| 19 | fixed | ctzb-scheduler-worker.js L36, L252-256 | — |
| 20 | fixed | At 43f1547 (1 Nov 2026), datasets/walkforward.csv read 90/66, 47/77, 12/75. Note: the table at README:162 dates the same figures 16 October | (optional) use one date for both |
| 21 | fixed | troughs.py L28, L110-114; tagstats.dead L67-76 | — |
| 22 | fixed | refresh.py L250-252, L430-431; the dashboard reads none of these files | — |
| 23 | **incomplete** | "13 of" is right. The new clause "grade_live, extras_live, stack_live and verify_cards write or change the rest" is wrong: verify_cards writes no CSV (it only appends to stack_status.txt, L168-172), and ledger_odds.csv is written by analysis/model.py L201, which is run by hand and is not in daily.yml | "...; grade_live, extras_live and stack_live write or change the rest, except ledger_odds.csv (analysis/model.py, run by hand)" |
| 24 | fixed | CONTEXT L1376, L1383 | — |
| O1 | fixed | ctzb-scheduler L207, dashboard template L190-193, site Worker read the feed through the mirror | — |
| O2 | incomplete | `n` is fixed, but feedcheck.py:8 still says "date (YYYY-MM-DD), ts (ISO time, UTC)" while claiming the page's comment says the same. The page's comment now says real dates in 2000-2099 (feedcheck L41-47) | "date a real calendar date YYYY-MM-DD in 2000-2099, ts ISO time in 2000-2099 ending Z" |
| O3 | incomplete | The new "4H/12H files have no missing bar" is loose: a gap that is the exchange's own (OWN_GAPS), or shared with the other asset, passes (fetch.py L319-321, L461) | "...no missing bar beyond the exchange's own gaps" |
| O4 | incomplete | The forward.csv and live.csv lists are right (grade_live L289-290, L329-330). The ledger description (L21-24) is unchanged and still omits reached10/15, surv10, scaled20 and the day-odds columns (L265-267). New loose text: "closeNow and closeDate: the grade a forming low would carry" (they are the latest daily close and its date, L329) | Fix the ledger list; split the colon: "...formingMarker (the grade...), plus closeNow / closeDate (latest daily close and its date)" |
| O5 | fixed | stack_live.py L790; daily.yml L199 | — |
| O6 | incomplete | L8, L843 and L846-847 are fixed; the CSS comment at index.html:139 still says "/* Previous alerts */" | "/* Previous signals */" |
| O7 | fixed | test_page_timing.py L139, L147-190 | — |
| O8 | fixed | test_seal.py L95-158 | — |
| O9 | incomplete | L196 is fixed, but L195 still has "(17 trades; ... 73 trades)" for signal counts, and PRETRADE:283 "Per-trade fitted odds" (the same test as #24) | "17 signals ... 73 signals"; "Per-signal fitted odds" |
| O10 | fixed | SITE_CHANGES row 6i | — |
| O11 | fixed | SITE_CHANGES row 6 superseded mark | — |
| O12 | fixed | SITE_CHANGES R3 L42; index.html L607, L642 | — |
| O13 | incomplete | The listed labels are fixed. The dashboard card still says "N past trades" (eth-setup-standard.html L316), "(N trades)" (L330), "under 15 trades" (L337), "past trades" (L104), "trades like this" (L107) and "counted from the buy" (L325, L326). The new CONTEXT:1612 bracket says it now says "signals" for trades and "the entry close" for buy | Relabel those 7; or narrow the bracket to the labels changed |

**Totals.** Counted: 21 fixed, 2 incomplete (#18, #23), 1 wrong (#2), 0 not done. Outside scope: 7 fixed, 6 incomplete (O2, O3, O4, O6, O9, O13), 0 wrong, 0 not done.

## Failing sentences after the commit (also in failing_sentences.csv)

Counted scope (4):
- FEED_SPEC:110, finding #2: shown above.
- CONTEXT:216, finding #23: shown above.
- cloudflare/README:11-12, finding #18: shown above.
- **New, docs/artifacts/member-site/README.md:5-6:** "what has changed since is listed as Pending in docs/SITE_CHANGES.md". Not true after 07339b1. The quiet card's new text (index.html L733) and How to read L290/L300 are in no Pending row. Only row 6b's bracket records the live-card wording. Smallest change: add a Pending row 6l for the 14 Nov docs-audit page texts.

Outside scope (7):
- CONTEXT:1612 (new bracket), O13: false, see above.
- grade_live.py:38-40 (new text), O4: loose, see above.
- .github/scripts/check_candles.py:17 (new text), O3: loose, see above.
- feedcheck.py:8, O2: missed repeat, see above.
- feedcheck.py:231 and index.html:545 comment: missed repeats of #6/#16. Both say a trade is "in the future" when it is after the viewer's clock. The code allows up to 5 minutes ahead (feedcheck L238, index L548).
- index.html:139, O6: missed repeat, see above.
- PRETRADE:195 and :283, O9 and #24: missed repeats, see above.

Not counted: SITE_CHANGES row 7b's commit cell reads "14 Nov docs audit" instead of a commit id.
