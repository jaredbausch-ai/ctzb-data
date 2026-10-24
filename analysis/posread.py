"""Positioning read for a signal: funding, long/short ratio, open interest.

Part of the standard statistics report (CONTEXT.md, Standing instructions).
A CAUTION read, not a filter: tested 23 Oct 2026 (analysis/derivtest.py), only
"funding below its 90-day median at entry" pointed the same way in both periods
(56% vs 71%, then 39% vs 46% reach +20% in 60d). Nothing here met the standard.

  python3 -I analysis/posread.py                    # ETH and BTC, last complete day
  python3 -I analysis/posread.py --asset ETH --date 2026-10-20
"""
import sys, os, argparse, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from derivtest import series, back


def read(a, d=None):
    f = series(f'data/derivs/{a}_funding_daily.csv', 'funding_mean')
    ls = series(f'data/derivs/{a}_lsratio_daily.csv', 'ls_ratio_mean')
    oi = series(f'data/derivs/{a}_oi_daily.csv', 'oi_usd_total')
    if d is None:
        d = max(f) - dt.timedelta(days=1)          # newest day is still forming
    med = statistics.median(back(f, d - dt.timedelta(days=1), 90))
    w7, w7b = np.mean(back(f, d, 7)), np.mean(back(f, d - dt.timedelta(days=14), 7))
    o14 = (oi[d] / oi[d - dt.timedelta(days=14)] - 1) * 100 if d in oi and (d - dt.timedelta(days=14)) in oi else None
    l14 = ls.get(d - dt.timedelta(days=14))
    below = f[d] < med
    print(f'{a} {d}')
    print(f'  funding {f[d]:.4f}% vs 90-day median {med:.4f}% -> {"BELOW (caution flag)" if below else "at or above"}')
    print(f'  funding 7-day mean {w7:.4f}% vs two weeks earlier {w7b:.4f}% -> {"falling" if w7 < w7b else "rising"}')
    print(f'  long/short ratio {ls[d]:.2f}' + (f' (two weeks earlier {l14:.2f})' if l14 else ''))
    if o14 is not None:
        print(f'  open interest {oi[d]/1e9:.1f}B USD, {o14:+.1f}% over 14 days')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--asset'); ap.add_argument('--date')
    a = ap.parse_args()
    for asset in ([a.asset] if a.asset else ['ETH', 'BTC']):
        read(asset, dt.date.fromisoformat(a.date) if a.date else None)
