# WGMI liquidity export

`BTC_2D_wgmi_tv.csv`, 38 columns, Coinbase BTCUSD, ends 2026-09-12. Rescued
22 Oct 2026 from session uploads.

Carries `Raw YoY Liquidity Growth %`, `DIRECTION (level-dominant)`,
`TIMING (impulse - turns, NOT direction)` and `DIRECTION unshifted (for
export)`, plus divergence pivots and anchors.

**This does not make the green-star tag rebuildable.** `CONTEXT.md` explains
why: the M2 series behind these columns is revised after publication, so the
values in this file are what the indicator shows *today* for past dates, not
what it showed on those dates. Using them to score historical signals produces
an upper bound, not an estimate. That was the original finding and this file
does not change it.

Kept because the WGMI Pine source in `pine/` is useless without an example of
what it emits.
