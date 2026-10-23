# pine/

Every Pine source in the project's history, rescued 22 Oct 2026 from a working
directory that was never committed. Before this, the repo held only
`ctzb_scanner_v8/v9` under `docs/reference/` — **the indicator itself was not
in version control at all.**

## The indicator

`ct_zone_bounce_v15.pine` is current — 751 lines, `//@version=6`. This is what
paints the chart: CT RSI, the Signal line, buckets, diamonds, prime dots, the
odds table and the confluence block.

Lineage, oldest to newest: `ct_rsi_zone_bounce_eth2d` → `_v2` → `_v2_fixed` →
`v3_compact` / `v3_BTC` → `v4` … `v15`. The `v31` / `v32` files are an older
numbering, not newer than v15. `_v8base.pine` is the base v8 was cut from.
`ct_zone_bounce_LT.pine` is the long-timeframe variant.

Note the header comment inside `v15` still reads "CT ZONE BOUNCE v14" — the
file is v15, the banner was not updated.

## The scanner

`ctzb_scanner_v9.pine` is current and is the same file as
`docs/reference/ctzb_scanner_v9.pine`. Seven columns; adds STEP, renames EDGE
to ODDS, adds the per-chart CONF lift. **Still not confirmed compiling** — the
first paste failed on "Undeclared identifier o1" and the confluence block was
moved above the alert block to fix it, but it has not been pasted back in
since. Verify before relying on it.

`ctzb_scanner.pine` (unnumbered) and `v6`, `v7`, `v8` are the earlier chain.

## The forecast cone

`ctzb_forecast_cone.pine` (22 Oct 2026, v1) draws the adopted volatility-scaled
forecast range (`analysis/volrange.py`) on the price pane: a cone 14/30/60/90
days forward, the band each bar was forecast to land in (offset onto the bar
it was for), and a table with today's levels and the indicator's own live
track record. One script for 1D, 2D and 3D charts; it detects the timeframe and
always computes on daily bars underneath, so the numbers are the same on every
chart. It carries the mechanical regime gate (BTC 2D CT RSI control zone)
inside itself; it does not read any other indicator.

`analysis/cone_mirror.py` is a bar-for-bar Python replica. Its printout is what
the table should show (track record within a few tenths; n a day or two higher
as the chart moves on). **Not yet confirmed compiling** — paste and check.

## Other sources

| file | what it is |
|---|---|
| `wgmi_dir_v3_1_ORIGINAL.pine`, `wgmi_dir_v3_2.pine`, `wgmi_dir_v4.pine` | The WGMI liquidity indicator. The green-star tag was diamond + WGMI timing below zero. `CONTEXT.md` explains why that tag **cannot be rebuilt** — the M2 data it reads is revised after publication, so the figures were never knowable on the day. Kept as source, not as something to restore |
| `btc_cycle_clock.pine` | Cycle-day clock |
| `eth_logreg_v2.pine` | Log-regression bands. Belongs to the separate ETH-Indicators project |
| `their_v11.pine` | A v11 from someone else, kept for diffing |
| `reverse_engineered_from_image.pine` | An early reconstruction from a screenshot |

## Warning

`engine.py` is the Python reimplementation of this indicator and the two must
agree. If a Pine file changes in a way that moves a signal, `engine.py` has to
move with it, and `troughs.json` and `odds.json` need regenerating. The
definitions in `CONTEXT.md` are the contract between them.
