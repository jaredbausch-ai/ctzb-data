# Fix check 46 (d516e32 vs 0185de1)

Entry quality only: computed signals, never trades or fills, and no strategy return or track record.
Read only: worked in a clone of d516e32; nothing in /home/claude/ctzb-data was edited.

| Item | Verdict |
|---|---|
| 1 Code (check_fresh 12H) | **Incomplete**: rule right, fire-drill harness not updated |
| 2 Words (57 sentences, 21 files) | 6 loose; no wrong figure, nothing reads as a trade; page diff is wording only |
| 3 Build | Right: rebuild byte-identical, rows 6q-6u all in it |
| 4 test_page_states | 65/65 |

## 1. check_fresh.py
- **Rule.** `b12 = floor(now/43200)*43200`; fails when `h12 < b12`, as for 4H.
- **Fault cases**, fake clock on the committed files of each real 19 Nov run at 00:14, 04:14, 08:14, 12:14, 16:14 and 20:14 UTC:
  committed files pass at all six; both 12H files, or BTC 12H alone, one bar short fail at all six; committed data passes at the real time (23:57 UTC).
- **New 12H bar at 00:14 and 12:14?** Yes.
  - `hourly()` reads from the open of the last stored 12H bar to now, and `resample_intraday` puts the 00:00 (or 12:00) hourly candle in the new 12H bucket, as it does for 4H.
  - Git history: across 170 commits of data/ETH_12H.csv, 12H is current on every commit where 4H is current, including 28 in the 00 slot and 26 in the 12 slot.
  - The only 2 commits with a stale 12H bar (1 Nov, 4 Nov) have a stale 4H bar too.
- **Copies from an earlier run** fail only when that run was in an earlier 12H window.
  Same-window copies pass (00:14's at 04:14 or 08:14; 12:14's at 16:14 or 20:14): only the last bar's open time is read, and nothing compares the 12H last close with the 4H or 1D last close (equal on every committed run).
- **Tests:**
  - `tests/test_fetch_today.py`: 6/6, at 23:57 and again after midnight.
  - `tests/fire_drills.py` at 19 Nov 23:58: 58/58.
  - `tests/fire_drills.py` at 20 Nov 00:03: **54/58**.
    - `A control: current candles pass the freshness check` FAILS: `make_current()` (fire_drills.py:94) extends 1D and 4H but not 12H.
    - The same fixture passes under the 0185de1 check_fresh; under d516e32 it gives `STALE CANDLES: ETH_12H last bar 2026-11-19 12:00 UTC, expected 00:00 UTC`.
    - So the A control fails whenever the drill runs after the next 12H boundary following the data commit. The 4H-behind, 1D-behind and empty-4H drills now also fail on 12H, so they no longer isolate their own fault.
    - The other 3 FAILs come from crossing midnight (make_current extends 1D but not 2D-8D), not from this change.
  - No other `tests/*.py` or `*.sh` runs check_fresh.
- **Docstring** (check_fresh.py lines 7-11) still lists only the 1D and 4H rules.

## 2. Words
- **Page diff.** docs/artifacts/member-site/index.html: 10 lines changed, all wording, at lines 217, 220, 296, 299-301, 620, 757, 1163 and 1216:
  the lead-trader panel subtitle and note; How to read (Typical high, Edge gone, If it misses, Lead trader); one comment; missTxt's shown text; the Best move and Misses labels. No logic changed; FEED_SCHEMA did not change.
- **Checked against code:**
  - How to read: `leadState`, `edgeTxt`, the line-780 example exclusion, the `kind` values, the Chart tab's "below the bar already".
  - "median best move": `median_peak_pct` is the median of the ledger's `bestMove` over misses.
  - FEED_SPEC: a card `label` with no strict rule is right; `mean_peak_pct` exists at 1 decimal; open_signals "1 to 60" (0 never appears in 150 feeds); a missing alert log is restored (`lb=b""`); chart rule line 966.
  - daily.yml GATING_STEPS; feed_live fail-closed causes; extras file deletion; grade_live keyed on `(ch, d0)`; fetch_derivs START and series dates.
  - Volume is 0 on every 4H/12H row; refresh buy rows use tier stats; engine `_declamp`; BRIEF pins checked against git.
  - numbers_check comments against their baselines: 2020-09-15 has 3 forming and 3 A+ live; 2026-09-07 has none; 2026-11-12 has 0 cards and 23 open, including BTC 2D A+.
- **Findings** (also in findings.csv):
  - **kind 2** `.github/scripts/check_fresh.py:7-11`: the docstring leaves out 12H. Add "- data/{ETH,BTC}_12H.csv: the last bar must be the current 12-hour bar (19 Nov 2026 audit round 46)."
  - **kind 3** `.github/scripts/check_fresh.py:41`: "expected 00:00 UTC" has no date. Print `%Y-%m-%d %H:%M`.
  - **kind 3** `.github/scripts/check_fresh.py:23-24` and `tests/test_fetch_today.py:47`: "the short files were committed". No commit in git history has this; it was the damage run. Use "so a run would have committed them (round 46 damage run)".
  - **kind 3** `fetch.py:213-214` and `tests/test_input_files.py:14-15`: "the 4H and 12H files with it were committed". No commit of those files ever held a stray CR. Use "so a run would have committed the 4H and 12H files with it (round 42 damage run)".
  - **kind 3** `docs/SITE_CHANGES.md:39` (row 6r): "with none it read out / not in / unavailable" leaves out "loading". Use "with none it read out / not in, and loading / unavailable while his feed loaded or could not be read".
  - **kind 3** `docs/artifacts/member-site/README.md:17`: the bar lengths leave out "1W 7", which TF_DAYS types (index.html:343). Add ", 1W 7".
- **Code findings:**
  - `tests/fire_drills.py:94-108`: add `(f"{a}_12H.csv", 43200)` to make_current and its docstring.
  - Optional: require each 12H file's last close to equal its 4H file's last close, which catches same-window copies.

## 3. Build
- Rebuilt with `build_site.py`: byte-identical to the committed worker (142,188 bytes, sha256 a1b7468e...fa20); its page is index.html exactly.
- The worker diff since 0185de1 is the PAGE line only.
- All Pending rows present, old wording gone: 6q "several separate confirmations"; 6r no Lead trader line on the example; 6s the five "move" labels; 6t the Edge gone sentence, the "known by its date" pool, Lead trader scope and "loading"; 6u the subtitle and the note.

## 4. tests/test_page_states.py
- 65/65 passed. Output in test_page_states.txt.

**Counts:** kind 1: 0, kind 2: 1, kind 3: 7, kind 4: 0. Code: 2 (1 harness break, 1 optional).
