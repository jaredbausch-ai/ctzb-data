# Member site — pending changes

The running list of changes to the member site (`ctzb-site`) that are built and committed
but NOT yet live. Batch them, then deploy once with a single Chrome paste.

**On deploy:** move everything under "Pending" into a new entry at the top of "Deployed",
with the Cloudflare version id, the commit it was built from and the date, then leave
"Pending" empty for the next round. `cloudflare/BRIEF_site.md` is re-pinned to that commit
at the same time.

Live right now: version **656d67c3** (11 Nov 2026).

## Pending

| # | Change | Commit | Requested |
|---|---|---|---|
| 1 | Audit label fixes: "Previous alerts" renamed "Previous signals" (none were ever sent as alerts); the 25% line explained as 25.3%, where 3.3x with 5% maintenance liquidates (was "4x"); example and open cards say "from all N top-grade signals" (pooled), not "like this one"; "Dip before the high, from entry"; "about 22 a year (2020 to 2025 average)" replaces the hand-typed 18 to 22; red-on-day-10 shown as "% still rose 10%"; the ETH tier fade labelled as what it is (ETH walk-forward tier, +10% counted day 10 to 60); example odds noted as using the full history; example 2-day bars give the high/low as a two-day span; a missing example chart no longer leaves the previous setup's panel up. | 9b9fa72 | 12 Nov (audit) |
| 2 | Example and open-signal cards round their medians once, half away from zero, before building prices (example typical high $3,481.66 at +34.9%, was $3,482.81). | 5f24063 | 12 Nov (re-audit) |
| 3 | Audit #3: live BTC and ETH setups shown (was ETH only); live setups and the example get their own cards (own sample, ladder, edge); prices from exact percentages (supersedes 2); "At the alert" hides the outcome; forming-setup day lines from the confirmation; 25.3% labels; "signals" not "trades"; "Past signals" tab; dip band "0 to −2%"; "Typical price on day 60"; all-signals fade relabelled (after day 10). | 57a8c34 | 12 Nov (audit #3) |
| 4 | Audits #4–#5: walk-forward tier lookahead fixed; live chart anchored to the entry bar; real low day; banner and "no open top-grade setup" wording; ladder checks the low first; from-entry row on the same measure; chart day lines placed by date across New Year; alert view scaled by known prices only; `price_now` vs `entry_close`; At-the-alert toggle hidden on live/forming charts. | 94d90a0, 7342597, 31c2165 | 12 Nov (audits) |
| 5 | Audits #6–#7: example cloud without hindsight; own-ladder badges; miss tiles name their sample; "Typical change by day 60"; "updates each close"; "went above entry"; "Typical worst drop"; picker shows "rose 10% in 60 days · n"; +20% / −30% tiles say "within 60 days · n"; Past signals title "whose 60 days have closed"; lead trader "unavailable" when his feed can't be read. | 37bcab3, e6d8e48 | 12 Nov (audits) |
| 6 | Audits #8–#9: 70% edge tested on exact shares (ladder colours, chart zones); miss counts always shown ("5 of 5", "95 misses of all 312"); "every figure covers the 60 days after entry"; in-sample label on the general fade; every forming card says it can still vanish; How to read: confirmed alerts are final, forming heads-ups can vanish; Previous-signals badges from the feed's `edge_status`; example misses from the feed; "about N a year" counted from the ledger; no built-in example fallback. | 1dd9514, bf2d4b6 | 12 Nov (audits) |
| 6b | Audits #10–#14: the card names its sample under the big number; no grade letters ("the top grade" / "the same grade"); lead-trader chart note when his feed is unavailable; 70% bar read from the feed (no typed fallback); "+10% level"; example miss tiles "of the 75 … known by then"; live card says Edge lost / On track and "as of the entry close, not from today" (edge-lost card dimmed); chart ladder bands show n with a caption; chart side box restates the sample. | bb32a0a, f870d65, 0a5822d, c7755bd | 12 Nov (audits) |
| 6c | Audits #15–#16: year-end confirmation dates; quiet card prints the per-year count; tier year from the feed; live chart finds a short year-end entry bar; "n/a" (not "n/a%"); "must close above" rounded down; "Rose 10%" status on live cards; exact-decimal prices; "If it misses" row names its pool; feed down / held back / ledger missing / chart file missing read as unavailable. | 6bb13bc, a6ec91a, 92fa64e | 12 Nov (audits) |
| 6d | Audit #17: fail-closed feed reads "Market filter: unavailable"; a chart that can't be drawn clears the previous setup's title, side box and cloud; chart note no longer claims lead-trader markers; chart labels drawn above the candles. | 3dddb15, 9d2d52b | 12 Nov (audit) |
| 7 | **Dashboard worker (Jared's Telegram alerts), separate paste:** forming alert reads "Rose 10% within 60 days: X% of N past signals (Y% without ever falling 25.3%)" (was "never fell 25% … past trades"). `cloudflare/ctzb-dashboard-worker.js` rebuilt. | bf2d4b6 | 12 Nov (audit #9) |

## Requested, not built yet

| # | Change | Requested |
|---|---|---|
| R1 | Previous signals column ("Edge intact" and "Edge lost or closed"): clicking a past signal's mini card opens its full card in the middle panel, the same card a member sees for a live setup. | 12 Nov (Jared) |
| R2 | Chart tab, right-hand column: show the card for the setup being charted (Jared saw it blank on the live site for the live BTC 2D setup). **Cause of the blank column:** the live version (656d67c3) crashes on the Chart tab when the feed carries a live setup it wasn't built for ("Reduce of empty array" — it also blanks "Where the past signals went" and draws the entry on today instead of 21 Sep). The pending build already fixes the crash and fills the column with a short summary of the card (big number, typical high, +10% level, +20%, typical drop, edge) plus the live day-count box. **Still to build:** put the full card there (ladder, eras, timing, if-it-misses), the same card as on the Now tab. | 12 Nov (Jared) |

## Deployed

### 656d67c3 — 11 Nov 2026 (built from 9a013e3)
- Page scales to fit the screen on desktop widths: up to 1.3x on tall screens (never narrower than a 1300px layout), down to 0.85x on short ones; very short screens scroll. Phones unchanged. (16709dd)
- +10% switch finished: "If it misses" counts signals that did not rise 10%; Previous alerts badges read Rose 10% / Reached +20% / Missed; Record gets a Rose 10% column and counts +10% misses; the all-signals fade bars and chart bands use +10%; the example card's eras show "rose 10%, never fell 25%". (c085adf)
- "Below the 70% posting bar" wording replaced with "not top grade" (picker, card, chart view); the Record's grade summary leads with "Rose 10% in 60 days". (6b639b1)
- Chart view: "The next 60 days, as the odds draw them" moved out of the chart (it sat on the +10% line) into the subtitle. (9a013e3)

### ffab70e3 — 11 Nov 2026 (built from dc52155)
- Fire-drill fixes: "Data unavailable" when the feed can't be reached, "Setups held back" when a check failed, a warning when the feed is over 5 hours old; the example card never stands in for an outage.
- Odds described as "statistics based on past signal history and data"; "hypothetical" removed; "Past results don't guarantee future results."
- Small text 1–2px larger; Previous alerts header kept on one line.

### c5536cc1 — 11 Nov 2026
- First deploy behind Cloudflare Access: Live / Forming setup picker, best forming setup shown when there is no top-grade one.
