# Audit #26, numbers part: summary written from the auditor's own logs

The auditor's run was stopped by a container restart before it wrote its report (13 Nov 2026, about 23:50 UTC).
Its completed work, from progress.log and runner.log in this folder:

| Scope | Comparisons | Disagreements |
|---|---|---|
| Both frozen states (data and rendered page) | 59,236 (29,224 current, 30,012 replay 04:14) | 0 |
| 293 replays of real dates | 5,698,860 | 72 rows on one date (2021-06-25), one cause |

The cause: the BTC volatility median used by "beat a normal move" (scaled20) included today's open daily bar when
the replay date fell in 2016-21, which flipped BTC 2D 2018-06-19 and moved two open-signal cards (65% to 71%).
Today's runs are unaffected (the open bar is in 2026, outside the median's years). Fixed in measures.py.

Not finished: the auditor's re-run of its first 34 replays and 14 quiet dates with its final checker (replays
before #22 had run without its extended chart checks). From round 27 the full numbers audit runs only in the two
final clean runs; tests/numbers_check.py covers every change in between.
