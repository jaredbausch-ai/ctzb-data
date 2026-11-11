# Member site — pending changes

The running list of changes to the member site (`ctzb-site`) that are built and committed
but NOT yet live. Batch them, then deploy once with a single Chrome paste.

**On deploy:** move everything under "Pending" into a new entry at the top of "Deployed",
with the Cloudflare version id, the commit it was built from and the date, then leave
"Pending" empty for the next round. `cloudflare/BRIEF_site.md` is re-pinned to that commit
at the same time.

Live right now: version **ffab70e3** (11 Nov 2026), confirmed by Jared.

## Pending

| # | Change | Commit | Requested |
|---|---|---|---|
| 1 | Page scales to fit the screen on desktop widths: up to 1.3x on tall screens (never narrower than a 1300px layout), down to 0.85x on short ones; very short screens scroll. Phones unchanged. | 16709dd | 11 Nov |

## Deployed

### ffab70e3 — 11 Nov 2026 (built from dc52155)
- Fire-drill fixes: "Data unavailable" when the feed can't be reached, "Setups held back" when a check failed, a warning when the feed is over 5 hours old; the example card never stands in for an outage.
- Odds described as "statistics based on past signal history and data"; "hypothetical" removed; "Past results don't guarantee future results."
- Small text 1–2px larger; Previous alerts header kept on one line.

### c5536cc1 — 11 Nov 2026
- First deploy behind Cloudflare Access: Live / Forming setup picker, best forming setup shown when there is no top-grade one.
