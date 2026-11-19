# Fix check 44: rows lost from a scored series (8000198)

Read-only. Everything was run in a clone at 8000198. Each case below is the real chain (check_fresh, check_candles, refresh, grade_live, extras_live, stack_live, verify_cards, regression, feed_live), run at CTZB_NOW=2026-11-19T12:14Z on a copy of data/ that includes the records. "Changed" means the stack outputs or the feed's cards differ from an undamaged run. Raw rows: work/results.tsv. This measures entry quality only: the cards are computed signals, not fills, returns or a track record.

**Verdict: incomplete.** When only the series file is damaged and the record is intact, the rule catches it, and it holds no legitimate run. When the record itself is damaged, the check switches off without any message. Four of those record cases scored a cut ETH funding file, and the ETH cards changed.

## 1. Rule level: caught when the record is intact, missed when the record is damaged
| Case (on every scored series unless named) | Caught? | If not: figures changed? / legit run held? |
|---|---|---|
| Last 1, 2 or 5 rows lost (7 series x 3) | yes, all 21: stack fails, cards withheld | - |
| A middle row lost (7) | yes (check_candles and stack) | - |
| Replaced by an older commit that ends earlier (4d91925 derivs, 146dc5f pcr) (7) | yes | - |
| Replaced by an older same-day commit (056aaaf: same end date, older values) (6 derivs) | no | none changed this run; this is family 3 (an older run's copy), not this rule |
| File and record put back together (record = file end) (7) | no | ETH funding: cards changed; ETH/BTC oi: liveread changed; the other 4 unchanged. This looks the same as legitimate case L1 |
| Record emptied, cut mid-byte, non-date, null (derivs and options) | yes ("not readable") | - |
| Record cut to 3 lines (options: that is the whole file, so nothing is lost) | yes, the cut row is caught | - |
| **ETH funding last row lost + record file deleted** | **no** | **cards.csv, liveread, feed cards changed** |
| **... + its record key missing** | **no** | **cards changed** |
| **... + record edited later (2026-11-20, 2027-01-01), live clock** | **no** | **cards changed** |
| ... + record edited earlier (2026-11-10) | no | cards changed (cannot be caught without a second copy) |
| BTC pcr last row lost + record deleted / key missing / later / earlier | no | none changed this run (pcr read blank either way) |
| Record key for an unscored file (ETH_other.csv, ETH_pcr_daily.csv, dated 2027) | ignored | no hold |
| BTC pcr last pcr_amt blanked, row kept (blank allowed) | no | none changed |
| Record edited to 19 Nov on oi ending 18 Nov (record damage) | yes (holds; correct) | - |

None of the cases where the record was intact got through with changed figures. The 4 rows in bold are damage to the record itself. They are in scope for family 1 ("a file lost"), and in each one a cut ETH funding file was scored and the ETH cards changed.

## 2. Legitimate states: all pass
| State | Result |
|---|---|
| replay_at.sh at 11-17, 11-18 and 11-19, each 4h run 00:14 to 12:14 (16 runs; derivs record 19 Nov is later than the replay day for 11-17 and 11-18) | 16/16 ok, cards published |
| Real committed states 19 Nov 00:14, 04:14, 08:14 (candles from that run, derivs and feed from the run before, options from before, records as the fetch writes them) | stack, cards and feed ok (check_fresh fails only because it uses the real clock) |
| Derivs fetch not yet written today (all 6 end 18 Nov, through fetch_derivs.write) | ok |
| Open interest a day behind funding; pcr 2 days behind (fetch_pcr.save) | ok, ok |
| Full backfill (all 6 rewritten through fetch_derivs.write) | ok: the record follows the new file end |
| Fetch killed after the file was written but before its record (derivs, pcr) | ok: the record is behind the file, never ahead of it |
| build_audit_states.sh (replay_0414 from 4aa1208 with no record; current) | both ok |

Workflow: daily.yml commits `data/` after fetch_derivs, so the files and the record go into one commit. pcr.yml writes the record after each save and commits `data/options/` as a whole. Neither workflow writes the other's folder, so a rebase in the push race cannot pair a file with a record from another run. A kill can only leave the record behind the file, which is the safe direction. A corrupt record is rewritten by the next fetch.

## 3. Sentences (findings.csv)
| # | Where | Kind | Finding | Suggested change |
|---|---|---|---|---|
| 1 | fetch.py:341 | 1 wrong | "no record ... (no fetch has written since the record began)": since the seed, a missing record means it was lost | say it means the record was lost (or the data predates 19 Nov) and that rows lost with it are not seen |
| 2 | fetch.py:340 | 3 loose | "a replay of an earlier day reads a later record and skips it": a live run skips it too | say a live run skips it too |
| 3 | fetch.py:309 | 3 loose | "only ever add rows ... every series file they wrote": a backfill rebuilds from the source; only scored series are recorded | see findings.csv |
| 4 | FEED_SPEC.md:452 | 3 loose | "only add rows" (same as 3) | see findings.csv |
| 5 | FEED_SPEC.md:454 | 3 loose | names the replay as the only reason for the skip; leaves out a missing key; does not say record damage goes undetected | see findings.csv |
| 6 | DAMAGE_LIST.md:14 (family 1) | 3 loose | "a scored series ending before that record fails the stack step", with no exceptions given; test_series_cells is not in the Tests column | name the cases it does not catch |
| - | test_series_cells.py section 5 header | - | accurate | - |

No sentence reads as a trade, return or track record (kind 4: 0).

Suggested code change (optional): in rows_lost_problems, fail when the record is missing or a scored series has no key in it, since both folders have a committed record now and audit copies of old data can be seeded from file ends. Skip a later-dated record only when CTZB_NOW is set, or have replay_at.sh cap each record at <date> and fail any record dated after today. An earlier-dated record, or a file and record rolled back together, can only be caught with a second copy (as the alert log has).

## 4. Tests in the clone
test_series_cells 106/106; test_input_files 159/159; test_check_candles 95/95; fire_drills 58/58. The clone's tree is still clean afterwards.

Counts by kind: 1 wrong 1, 2 stale 0, 3 loose 5, 4 trade/return 0.
