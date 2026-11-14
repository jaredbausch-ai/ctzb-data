# Fix check, round 33 (commits 9d85d36, 5fefeb1, 3e4c8ca after 698cf42)

Independent check. I edited, committed and pushed nothing in the repo; all work was done on clones in this folder.
This work checks the page's file checks only. It measures entry quality only, never a return or a track record.

| Finding | Verdict | Evidence | Smallest change that would fix it |
|---|---|---|---|
| T1, page family 4: one lead-trader event listed twice was shown as two trades | **incomplete** | `test_page_states` 54/56 on the 698cf42 page, 56/56 now (the two repeat cases). 41 cases of my own (`cases.json`): repeats with the same id (adjacent, far apart, three times, one field different, key order changed) and exact copies with no id (2050.5 vs 2050.50, 3 vs 3.0, 2.5e1) are refused. Ids that are numbers, objects, `true` or `""` are refused by the schema. Two events with different ids, or with no id and one field different, are shown. **Still shown twice:** the same event with `id` on one copy only (either order); `id` null on one copy and missing on the other; equal object or list fields (=== never matches); the same instant written as `12:00:00Z` vs `12:00:00.000Z` with no id | In `sameEvent` (index.html:530) and `_same_event` (feedcheck.py:257): when both copies have a string id, compare ids. Otherwise compare every field except `id`, with null treated as missing, values compared as key-sorted JSON text, and `time` compared with `Date.parse`. Add the with/without-id and null/missing cases to `test_page_states` |
| T1, `feedcheck.trades_problems` mirrors the page | fixed (one contrived exception) | 47 cases (41 + 6 relay-built lists): same verdict on 46. Differs only when an extra, non-schema field holds whole numbers above 2^53 (`9007199254740993` vs `...992`): the page refuses and feedcheck shows. No test fails before the fix and passes after it for feedcheck; `test_feed_damage` only compares the two verdicts (its "last item doubled" case) | `_js_eq`: compare numbers as `float(a) == float(b)`, with overflow read as infinity |
| T1, no legitimate relay output refused | fixed | `node tests/test_trades_relay.mjs` 41/41. Every event list it leaves in KV passes both checks. My simulation (`sim_relay.mjs`, S6) covers open, add, reduce, close, a flip (`e4:close` + `e4:open` in one second) and a reconcile tick, and its output passes. The relay always writes a non-empty string id (`${entry_id}:${action}`, worker l.224-247), so the new `id?: str` schema entry refuses none of its output | none |
| T1, real-life route (relay) | the page rule alone is not enough | `appendEvents` (worker l.319-326) filters against the list it read and writes that list back, so one update applied twice cannot store an id twice. That held in simulation: stale state plus stale events (S1), stale state plus fresh events (S2) and two ticks at once (S3) each stored one event. The repeat the relay can emit in real life comes under **two different ids**. Case S4: a fill of one order appears in Coinbase's list after a later fill of the same order, and that tick reads stale state. Result: `e2:open` 3001 and `e1:open` 3000 for one 100-contract order. The page shows both, by design | In the relay: key the posted event on `order_id` (store the order ids already posted and never post a second `open` for one order), plus a relay test for S4 |
| Site Worker rebuilt from the page | fixed | `python3 cloudflare/build_site.py` on a clone gives a byte-identical `cloudflare/ctzb-site-worker.js`; `node tests/test_site_worker.mjs` 26/26 | none |
| Nothing else moved | fixed | `python3 tests/numbers_check.py`: 13 dates unchanged. `test_feed_damage` (quick pass): 31/31 now; 29/31 at 9d85d36 | none |

Not from this round, not counted: when a fill of an open order appears late with an earlier time and state is fresh
(S5), the relay prepends an `add` older than the `open`, and the file is refused as "not newest first".

## Changed sentences that fail (detail and suggested wording in `failing_sentences.csv`)

1. **docs/FEED_SPEC.md 524-527** (5, incomplete): "...no event repeating an earlier one (the same `id`, or every field
   the same...)". The code shows two events for the cases listed in row T1. Code: `index.html:530-531`, which needs a
   string id, or the same key count and `===` on every key.
2. **docs/audit/DAMAGE_LIST.md 17** (4): "as a relay update applied twice would". Code: `ctzb-trades-worker.js:319-326`
   cannot store one id twice (S1-S3). The relay's real repeat (S4, two ids) is not refused. Also has the gap in item 1.
   The rows guarding family 4 and the `test_page_states` entry hold: the two repeat tests fail before the fix and
   pass after it.
3. **docs/AUDIT_LOG.md 1272** (4): "The cause, fixed at its family's rule". Not at the family level (row T1).
4. **docs/AUDIT_LOG.md 1285-1286** (4): "it failed 29 of 31 until then". At 9d85d36 the damage test **passed** 29 of
   31. The 2 failures were "every ... field the page reads is in the schema -- trades.trades[].id", one per state
   (`feeddamage_mid.log` l.12, 28).
5. **docs/artifacts/member-site/README.md 19** (5): "no event listed twice". Has the gap in item 1.
6. **feedcheck.py 248-249, 242-243** (4): "JavaScript ===" and "compared as the page compares them". Untrue for whole
   numbers above 2^53 (`feedcheck.py:254`).
7. **index.html 539-540** comment (5): has the gap in item 1.

Sentences that hold:
- Every other Round 33 claim: 54/56 on the old page; 36 cases added to `damage_list.csv` (1 real-life, 35 hardening);
  the Worker not rebuilt since 92176c5 (round 29); relay 41/41; site Worker 26/26; numbers unchanged.
- The DAMAGE_LIST count "36 from round 33".
- The comments in `test_page_states.py` (l.17, 175, 181).
- Wording rules: every changed sentence calls the lead trader's own fills "trades", which is allowed. None reads as
  a return.

FEED_SPEC sentences that fail: 1 (of 1 changed).
