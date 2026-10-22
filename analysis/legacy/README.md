# analysis/legacy/

The 9–16 Oct generation, rescued 22 Oct 2026 from an uncommitted working
directory and from `/tmp`. Superseded by the current `odds.py` / `troughs.py`
pipeline but kept because the published PDFs and HTML pages were built from
these and nothing else reproduces them.

| file | what it is |
|---|---|
| `mkodds.py`, `mkodds4.py` | Built `docs/artifacts/odds_v3.html` / `odds_v4.html` and the matching PDFs in `docs/reference/` |
| `odds4.py`, `odds4.json` | The v4 odds aggregation |
| `conf.json` | Confluence scoring output. **Built with the symmetric window**, which peeks forward — see the trap in `CONTEXT.md`. Figures from it are inflated |
| `solo.json`, `oos.json` | Lone-signal and out-of-sample splits |
| `best_rsi.json` | The RSI-length search result |
| `pinecheck.py` | Diffs a Pine file against the Python engine |
| `alts.py` | The altcoin sweep — ADA, BNB, XRP exports |
| `ctzb_trade_log.csv`, `trades47.csv`, `ctzb_cycle_trades_eth2d.csv` | Trade logs. **Computed signals, never fills.** No position in them was ever taken |

Do not quote a figure from here without checking it against the current
pipeline first. The regime gate and the backward-only confluence window both
changed after these were generated.
