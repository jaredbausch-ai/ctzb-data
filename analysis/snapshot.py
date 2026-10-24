"""Market snapshot from everything in the repo: price, volatility, regime, every
open signal since the gate turned on and how it is behaving, forming troughs,
confluence windows, higher-timeframe direction, positioning.

Read-only and descriptive. Numbers carry their tested meaning from PRETRADE.md;
nothing here is a forecast or a trade. Run from the repo root:
  python3 -I analysis/snapshot.py
"""
import sys, os, math, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end
from sweep import closed_index
import twoweek as T

CH = ['1D', '2D', '3D', '5D']


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    gd = T.gate_daily()
    for a in ('ETH', 'BTC'):
        day = E.load(f'data/{a}_1D.csv'); D, C, H, L = day['date'], day['close'], day['high'], day['low']
        i = len(C) - 1
        lr = np.diff(np.log(C))
        v30 = np.std(lr[-30:]); hist = [np.std(lr[k - 30:k]) for k in range(30, len(lr))]
        pct = 100 * np.mean([h <= v30 for h in hist])
        sma200 = np.mean(C[-200:]); hi365 = max(C[-365:]); lo365 = min(C[-365:])
        print(f'================ {a}  {D[i]} close {C[i]:,.2f} (newest bar may still be forming)')
        print(f'  change: 7d {100*(C[i]/C[i-7]-1):+.1f}%  30d {100*(C[i]/C[i-30]-1):+.1f}%  90d {100*(C[i]/C[i-90]-1):+.1f}%')
        print(f'  vs 200d avg {100*(C[i]/sma200-1):+.1f}%   vs 1y high {100*(C[i]/hi365-1):+.1f}%   vs 1y low {100*(C[i]/lo365-1):+.1f}%')
        print(f'  30d volatility {100*v30:.2f}%/day = {pct:.0f}th percentile of history; typical 60d move ~{100*v30*math.sqrt(60):.0f}%')
        b8 = E.load(f'data/{a}_8D.csv'); ct8 = E.rsi(b8['close'], 14)
        k8 = closed_index(b8['date'], D[i] if True else None)
        print(f'  8D CT last closed bar {b8["date"][k8]}: {ct8[k8]:.1f} vs {ct8[k8-1]:.1f} -> {"RISING" if ct8[k8] > ct8[k8-1] else "falling"}'
              f'   forming 8D bar now {ct8[-1]:.1f}')
        # open signals since gate on
        on = max(d for d in D if gd(d) and not gd(d - dt.timedelta(days=1)) and d <= D[i])
        print(f'  signals since the gate turned on ({on}):')
        P = {d: k for k, d in enumerate(D)}
        for tf in CH:
            sig, b = E.signals(f'data/{a}_{tf}.csv', regime=gate)
            ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
            for x in sig:
                d0 = bucket_end(b['date'], x['ei'])
                if d0 is None or d0 < on:
                    continue
                e0 = x['entry']; j0 = P.get(d0)
                if j0 is None:
                    continue
                age = (D[i] - d0).days
                after = range(j0 + 1, i + 1)
                worst = min((L[k] for k in after), default=e0); best = max((H[k] for k in after), default=e0)
                def at(n):
                    k = P.get(d0 + dt.timedelta(days=n)); return None if k is None or k > i else C[k]
                c5, c10 = at(5), at(10)
                low10 = min((L[k] for k in after if (D[k] - d0).days <= 10), default=e0)
                tl = b['low'][x['ti']]
                k8e = closed_index(b8['date'], d0)
                up8 = ct8[k8e] > ct8[k8e - 1]
                gap = ct[x['ei']] - em[x['ei']]
                tags = (['hollow dmd' if not x['strong'] else 'filled dmd'] if x['dis'] else []) + (['prime'] if x['prime'] else [])
                s5 = '-' if c5 is None else ('green' if c5 >= e0 else 'red')
                s10 = '-' if c10 is None else ('green' if c10 >= e0 else 'red')
                warn = []
                if low10 <= e0 * 0.9: warn.append('down 10%+ by day 10')
                if low10 < tl: warn.append('broke trough low')
                print(f'    {tf} {d0} {x["bk"]} {",".join(tags) or "plain":<16} entry {e0:,.2f} day {age:>2}  now {100*(C[i]/e0-1):+6.1f}%  '
                      f'worst {100*(worst/e0-1):+6.1f}%  best {100*(best/e0-1):+6.1f}%  day5 {s5:<5} day10 {s10:<5} '
                      f'gap {gap:+5.1f} 8D {"up" if up8 else "dn"}' + (f'  !! {"; ".join(warn)}' if warn else ''))
        fm = T.forming(a)
        print('  forming troughs: ' + ('; '.join(f'{tf} low {d} CT {v:.1f} needs {n} more bar(s)' for tf, d, v, k, n in fm) if fm else 'none'))
    b2 = E.load('data/BTC_2D.csv'); ct2 = E.rsi(b2['close'], 14)
    run = 0
    for v in reversed(ct2[:-1]):
        if v is not None and v < 41: run += 1
        else: break
    print(f'\nREGIME: gate {"ON" if gd(E.load("data/BTC_1D.csv")["date"][-1]) else "OFF"}; BTC 2D CT {ct2[-2]:.1f} (last closed), '
          f'{run} consecutive closed bars below 41 (13 turn it off)')


if __name__ == '__main__':
    main()
