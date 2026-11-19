# Fix check 41: c12db83 (the worked example's card shows no lead-trader line)

**Verdict: right.** The example card shows no lead-trader line in any view or file state. Current setups keep the line and it reads correctly. Nothing else on the page changed. Both suites pass. Findings: kind 1: 0, kind 2: 1, kind 3: 4, kind 4: 1 (on a live setup's card, which this fix left as it was on purpose).
Entry quality only: the page shows computed signals, never fills, exits or returns.

Method: `probe.py` loads the page as it was before the fix (c12db83~1) and after it, in Playwright with the test's stand-in routes. It covers two feeds: the current feed and a quiet market where the page opens on the example. It covers eight lead-trader files: ETH open long, ETH open short, BTC open long, ETH closed, empty, missing (404), invalid and slow (held, then released). In each state it records the card the page opens on, the example via the switch and via the picker's Example button, the Chart tab (alert and "What happened"), Record, How to read, the print media view, a 390 px phone view, the example while the file is still loading, the switch turned off, and every picker entry with its Chart tab. That is 280 views per version. The raw output is in probe_out.json.

## 1. Example card never shows a lead-trader position: PASS
- After the fix, no example view in any of the 16 feed and file states contains `Lead trader:`. That covers the Now card, the switch on and off, the picker button, the Chart tab, the print view, the phone view and the quiet market that opens on the example. It holds while the slow file loads and after it arrives.
- Before the fix, the example card read `Lead trader: in · long` / `in · short` / `out` / `not in` / `unavailable` / `loading`, depending on the file. The Chart tab never carried the line, before or after.
- The page has no separate snapshot or print layout. There is no `@media print`, so the print view is the same text as the screen.

## 2. Current setups unchanged and correct: PASS
- Live BTC-2D-2026-09-21 card and forming ETH-2D-2026-11-20 / ETH-3D-2026-11-23 cards, after the fix:

| File | Live BTC 2D | Forming ETH 2D / 3D |
|---|---|---|
| ETH long | not in | in · long |
| ETH short | not in | in · short |
| BTC long | in · long | not in |
| ETH closed | not in | out |
| empty / missing / invalid | not in / unavailable / unavailable | same |
| slow: while loading, then arrived | loading, then not in | loading, then in · long |

- Before against after: of the 280 views compared in each version, the only lines that differ are the removed `Lead trader: …` lines on the example card. Every Chart, Record and How to read view and every current-setup card is identical, with no file or with one. Neither version raised a page error.

## 3. Other text that could read as the lead trader having taken a past signal
- Live setup card (index.html:780). With a BTC position open (stand-in: opened 10 Nov 2026), the card reads `Confirmed 21 Sept 2026 · entry close $86,594.94 · day 58 of 60 …` and then `Lead trader: in · long`. The signal confirmed 7 weeks before his fill, and the line can read as him having taken it. This is finding F1, kind 4.
- Lead panel on the Now tab, beside the example: `Real trades, posted automatically when they fill (once his feed is live)`; `ETH long · open / 10 Nov 2026 / Price $2,050.50 / 3.0x / 25.0% of acct`; on a close `Move +2.4% / Account +1.8%`; `…sometimes before an alert, sometimes after, sometimes not at all.` The entries are dated and the panel is not tied to the example, so it does not read as taking the 2024 signal.
- Chart tab note, the example's too: `The lead trader's real entries and exits are listed on the Now tab; they are not drawn on this chart.` (or `…posted no trades yet…` / `…feed is unavailable…` / `Loading the lead trader's feed…`). It is not tied to the signal.
- Record: `EVERY TOP-GRADE SIGNAL WHOSE 60 DAYS HAVE CLOSED · COMPUTED, NEVER TRADED` and `Computed signals, not trades. … entry quality, not a return or a track record.` It does not mention the lead trader.
- How to read (index.html:301): `Lead trader — Whether the lead trader is in, out or not in ("unavailable" if his feed can't be read). His real trades never change the odds.` It does not say that only current setups carry the line. This is finding F2, kind 3.

## 4. Changed doc sentences against the page
- FEED_SPEC.md:549-550, kind 3 (F3). `it reads "not in" when he has posted entries but none on that asset`: it also reads "not in" when the file holds no trades. `A current setup's card has a lead-trader line`: a card shown as "Card unavailable" or "No odds yet" has none, because the page returns early at index.html:712-717.
- CARD_SPEC.md:74-75, kind 3 (F4). `(from the lead trader's own posted trades, newest first)`: the state is his newest event on that card's asset, which the sentence does not say. The labels and the example exclusion are right.
- SITE_CHANGES.md:39 (row 6r), kind 3 (F5). `with a position open it read "Lead trader: in · long"`: the position had to be on ETH, and a short read "in · short". The other states read out / not in / unavailable / loading. `Current setups' cards keep it` is right.
- SITE_CHANGES.md:39, kind 2 (F6). The commit column says `(this commit)`, and so does row 6q (line 38), which was f65b5c1. Name c12db83.
- None of the changed sentences reads as a trade, a return or a track record.

## 5. Tests in the clone
- `tests/test_page_states.py`: 65/65. `tests/test_page_timing.py`: 24/24.
- The new test (test_page_states.py:207-211) checks only the ETH-long file and the switch. Of the views this probe covers, it misses the picker's Example button, the quiet page that opens on the example, and the out / not in / unavailable / loading states.

## Findings (suggested changes; details in findings.csv)
- F1, kind 4, index.html:780. On a live setup (already confirmed), show when his position started so it can't read as this signal: `Lead trader: in · long since 10 Nov 2026 (his own trade)`. Or show the line only on forming setups.
- F2, kind 3, index.html:301. `On a live or forming setup's card (the worked example has none): whether the lead trader is in, out or not in on that asset ("loading" while his feed loads, "unavailable" if it can't be read). His real trades never change the odds.`
- F3, kind 3, FEED_SPEC.md:549. `A live or forming setup's card that shows figures has a lead-trader line (the worked example, a past signal, has none); it reads "not in" when his file holds no event on that asset, including when it holds none at all.`
- F4, kind 3, CARD_SPEC.md:75. `… / unavailable" (his newest posted event on that card's asset: "in" after an open, add or reduce, "out" after a close, "not in" with none).`
- F5, kind 3, SITE_CHANGES.md:39. `…with an ETH position open it read "Lead trader: in · long" (or "in · short"), as if he had taken that past signal; with none it read out / not in / unavailable.`
- F6, kind 2, SITE_CHANGES.md:38-39. Commit column: 6q `f65b5c1`, 6r `c12db83`.
