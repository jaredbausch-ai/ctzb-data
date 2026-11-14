# Fix check 31 (independent)

Fixes checked: 81c85cc ("Audit #31 fixes") and f00b6e8 (AUDIT_LOG Round 31), against round-30 code (eedde8c). Nothing in
the repo was edited. Work copies: `fixcheck31/new` (HEAD), `fixcheck31/old` (HEAD tests, eedde8c `index.html` and
`feedcheck.py`). Entry quality only: these are computed signals, not fills, and nothing here is a return.

| Finding | Verdict | Evidence | Smallest change if not fixed |
|---|---|---|---|
| D1 (page, family 6: lead-trader file late, Chart tab) | fixed | `index.html:1152`, `:1159-1162` (`chartLeadText` reads `S.loading.trades` on every draw), `:1281` (updates `#chLead` in place on arrival). `test_page_timing` 19/19 on HEAD, 17/19 on old (2 of the 3 new cases fail before). Own cases `d1_cases.py` + `d1_extra.py`: 20/20 on HEAD, 9/18 on old | none |
| D2 (pipeline + page, family 5: run spanning 00:00 UTC) | fixed | `index.html:460`, `feedcheck.py:131-132`. `feed_live.py:603-605` raises, and `fail_closed()` publishes the withheld feed. `test_midnight` 5/5 on HEAD, 2/5 on old. Own cases `d2_cases.py`: 26/26 on HEAD, 24/30 on old | none (optional: add a forming-only case to `test_midnight`; the rule catches it, but no repo test does) |

## Family-level cases tried (own)

| Family 6 (D1) case | HEAD | old |
|---|---|---|
| Now tab while loading, then valid, then Chart tab | pass | pass |
| Switching Now/Chart/Now/Chart while loading, file arrives on Chart | pass | fail |
| Setup switched on Chart while loading (chart files instant; chart files 2.5 s late) | pass | fail |
| Slow, then fails the check (trade in the future; bad price) or 404, opened on Chart and on Now | pass (6/6) | 3/6 |
| Ledger, lead, example and chart files all late, member walks the tabs (ends on Now / Chart / Record) | pass (3/3) | Chart fails |
| Lead file arrives before the feed, member on Chart (valid; 404) | pass | n/a |

Area by area, no tab says "unavailable" while a file loads. When a file arrives, every area that reads it is redrawn on the tab
already open: the feed through `show()`; the ledger and the example through `redraw()`, which redraws an open Chart or
Record tab; the lead-trader file through `renderLead`/`renderCard` and `#chLead`; a chart file through `renderChart` and its token.

| Family 5 (D2) case: scored ~23:59:35, feed at 23:59:55 / 00:00:05 | HEAD | old |
|---|---|---|
| Quiet, filter on | clean / fail-closed | clean / **clean** |
| Quiet, filter off | clean / fail-closed | clean / **clean** |
| Forming cards only, confirming D+2 | clean / fail-closed | clean / **clean** |
| Forming card confirming on D | clean / fail-closed | clean / fail-closed |
| Open signals (repo state) | clean / fail-closed | clean / fail-closed |
| 31 Dec 2025 to 1 Jan 2026, quiet | clean / fail-closed | clean / **clean** |
| Held run (stack failed), quiet and forming | held / held | held / held |
| Alerts: seed; clean D 22:00 adds Y; spanning run adds Z; clean D+1 00:13 | Y sent once; nothing sent and log untouched on the failed run (Y in `alerts_held`); Z sent once at 00:13; no duplicate in log | Z sent from the spanning run |

- **Page vs `feedcheck.py`.** 12 `scored_as_of`/`generated_at` variants (`agree.py`), and they agree on all 12. The
  D2 feed on the HEAD page at 00:03 reads "Data unavailable". The pipeline no longer publishes such a feed.
- **Committed feeds.** `history_check.py` covered all 137 commits of `feed/ctzb_feed.json`; 120 are not withheld.
  - None has `scored_as_of` before `generated_at`'s day.
  - None fails HEAD `feedcheck.py` but passes the old one.
  - 98 older feeds already failed earlier strict rules. They are schema v1 to v6, the newest from 12 Nov 21:05, mostly a missing `checks.all_passed`. Every feed since then passes.

## Nothing else moved

| Test (HEAD copy) | Result |
|---|---|
| numbers_check.py | 13 dates unchanged |
| test_seal / test_feed_alerts / test_page_states | 29/29, 65/65, 52/52 |
| test_midnight / test_page_timing | 5/5, 19/19 |
| test_feed_damage (RENDER_LIMIT=40, REJECT_LIMIT=10) | 31/31; page and pipeline agree on 9,507 damaged feeds |

## Changed sentences that fail 4 to 7 (details and code evidence in failing_sentences.csv)

1. **FEED_SPEC.md:455-456** (rule 6). It reads "...is not published as clean: audit #31". That is history in a spec. The rule it states is true (`index.html:457,460`; `feedcheck.py:129,131`). Fix: drop ": audit #31".
2. **tests/test_midnight.py:6-7** (rule 5). It says a quiet market is "the state that got through". Forming-only feeds whose cards confirm after the scored day got through too: old code published one clean at 00:00:05 (`d2_cases.py`). HEAD catches it at `index.html:460`.
3. **AUDIT_LOG.md:1159-1160** (rule 5). "published clean in a quiet market" leaves out forming-only markets.
4. **AUDIT_LOG.md:1166** (rule 5, loose). "Every new failing case fails on the round-30 code" overstates. The new page-timing 404 case and 2 of the midnight cases are controls, and they pass on both versions. The counts quoted are right.

These pass:
- **FEED_SPEC.md:522-523**, the lead-trader note: `index.html:1159-1162`, `:1281`.
- **DAMAGE_LIST** families 5 and 6:
  - Rule text: `index.html:460`, `feedcheck.py:131`, `index.html:1281` and `redraw()`.
  - The test lists name `test_midnight` and `test_page_timing`. Both exist and cover the rule.
  - The "32 from round 31" count matches the 32 rows added.
- **Comments in `index.html:458-459`, `:1156-1158` and `feedcheck.py:130`.**
- **`test_page_timing` docstring item 6.**
- **Wording rules:** no breach was found.

Seen, not counted (it predates this round's change): with a valid lead-trader file that has no trades, the Chart note
says his entries "are listed on the Now tab", while the Now tab reads "No trades posted yet" (`index.html:1161`).
