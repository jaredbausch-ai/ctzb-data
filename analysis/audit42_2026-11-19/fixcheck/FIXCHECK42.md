# Fix check, audit round 42 (stray carriage return), commit 158f075

Entry quality only: these checks cover input-file integrity for the signal pipeline. Nothing here is a strategy return or track record.

**Verdict: right.** The rule catches every carriage-return damage I tried, in every file tested, and no legitimate file fails. Four sentences need rewording: 2 stale, 2 loose. None is wrong, and none reads as a trade.

## 1. Rule level
I applied 16 damage cases to 9 files (ETH_1D, BTC_2D, ETH_8D, BTC_4H, ETH_12H, ETH_funding, BTC_lsratio, ETH_oi, BTC_pcr) and ran `fetch.history_problems` with and without `lag=True` (today 2026-11-19); per-case results are in `item1_history.csv`. The rule is `b"\r" in raw.replace(b"\r\n", b"")`. For the cases it does not catch, I ran the real chain on a full copy of the repo with CTZB_NOW=2026-11-19T04:14:00Z: check_fresh, check_candles (report mode, Kraken blocked), refresh, grade_live, extras_live, stack_live. Each case was applied to all 21 files at once (candles only for "every row"), then every `datasets/` file was diffed against a clean baseline run.

| Case | Caught? | If not: changes anything? |
|---|---|---|
| CR CR LF, one middle row / last row / every row | yes, 27/27 (stray CR) | - |
| CR CR CR LF, one row | yes, 9/9 | - |
| bare CR line end, one row | yes, 9/9 | - |
| CR inside a cell, middle / last row | yes, 18/18 | - |
| LF CR (next line starts with CR) | yes, 9/9 | - |
| CR at the very end (last line ends CR, no LF) | yes, 9/9 (cut short) | - |
| lone CR after the last LF | yes, 9/9 (cut short) | - |
| UTF-8 BOM | yes, 9/9 (header; series: unreadable date) | - |
| trailing space, every row | series 4/4 (blank cells become " "); candles 0/5 | no: chain all ok; every figure file identical |
| mixed LF and CRLF lines | no, 0/9 (by design) | no: chain all ok; every figure file identical |
| trailing space, last row | no, 0/9 | no: identical |
| trailing tab, last row / middle row | no, 0/18 | no: identical |

In the damaged runs only `manifest.json` changed: the input-file hashes, plus `candle_check.json`, which also differs between two clean baselines. These uncaught cases would be committed, but the parsers (`float()`, csv) read them identically, so no scored figure changes. None of them is a stray CR. Note: my first "CR in a cell, last row" put the CR before an LF and so made a single CRLF line in an LF file (the mixed case). Redone with the CR mid-cell: caught.

## 2. Legitimate files
- The committed data/ at 158f075 passes (`history_problems` returns [] with and without lag; baseline chain: every step ok). It holds 17 CRLF files and 4 LF files (the 4H and 12H files).
- Last 30 commits touching data/ (63e482a to c9ed6c4): all 21 history-check files at each commit pass `_file_problem`, and full `history_problems` (today = the commit's UTC date) returns [] for all 30. No data CSV of any kind in those commits holds a stray CR or mixed line ends. 0 failures (`item2_commits.csv`).

## 3. Changed sentences
- FEED_SPEC.md l.427-428: matches the code. DAMAGE_LIST.md family 2: matches the code.
- fetch.py l.208-209 comment, kind 3. "passed the check on the 4H and 12H files" understates it. With the old fetch.py (c9ed6c4), CR CR LF and a bare CR in a middle row passed `history_problems` on all 21 files (`old_code_check.txt`). CR CR LF in a middle row of ETH_1D, ETH_2D and ETH_funding also passed check_fresh and check_candles, so those files could have been committed too.
- tests/test_input_files.py l.14 header, kind 3: same understatement ("CR CR LF passed on the 4H and 12H files").
- fetch.py l.201-203, `_file_problem` docstring (unchanged), kind 2: it still lists only "a whole line ... and no blank line".
- fetch.py l.328, `history_problems` docstring (unchanged), kind 2: "Every file ends with a whole line and holds no blank line (_file_problem)" omits the new rule.

Suggested sentences are in findings.csv.

## 4. Tests (clone at 158f075)
test_input_files 159/159, test_check_candles 95/95, test_series_cells 62/62, all exit 0.

## Counts by kind
Kind 1 (wrong): 0. Kind 2 (stale): 2. Kind 3 (loose or incomplete): 2. Kind 4 (reads as a trade): 0.
