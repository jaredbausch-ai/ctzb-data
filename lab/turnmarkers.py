"""What price did after each ROC+ band -> turn marker pair (ETH 5D), measured from the TURN close.
Descriptive, 25 Nov 2026, from Jared's chart of the markers (not a declared test).
For each completed excursion since 2019: band close, turn close (first 5D bar back inside the
band), then from the turn close: lowest low / highest high within 90 days, day-90 change, and
the lowest low within 180 days. Daily candles. Entry quality only; computed, never fills.
  python3 -I lab/turnmarkers.py -> lab/RESULTS_turnmarkers.txt
"""
import sys, os, datetime as dt, statistics as S
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, 'analysis'), ROOT]; os.chdir(ROOT)
import engine as E, inband as IB

L = []
def P(s): L.append(s); print(s)

def main(a='ETH'):
    ex = IB.excursions(a)[0]
    d = E.load(f'data/{a}_1D.csv'); pos = {x: i for i, x in enumerate(d['date'])}
    P(f'{a} 5D ROC+ band -> turn, measured from the turn close (lab/turnmarkers.py)')
    P('band | turn | turn close | 90d lowest | 90d highest | day 90 | 180d lowest low')
    rows = []
    for s0, e0 in ex:
        if s0 < dt.date(2019, 1, 1) or e0 is None: continue
        c = d['close'][pos[e0]]
        w90 = [k for k in range(pos[e0] + 1, len(d['date'])) if (d['date'][k] - e0).days <= 90]
        w180 = [k for k in range(pos[e0] + 1, len(d['date'])) if (d['date'][k] - e0).days <= 180]
        lo = 100 * (min(d['low'][k] for k in w90) / c - 1); hi = 100 * (max(d['high'][k] for k in w90) / c - 1)
        r90 = 100 * (d['close'][w90[-1]] / c - 1) if (d['date'][w90[-1]] - e0).days >= 90 else None
        l180 = min(d['low'][k] for k in w180)
        rows.append((lo, hi, r90))
        P(f'{s0} | {e0} | {c:,.0f} | {lo:+.1f}% | {hi:+.1f}% | ' + ('-' if r90 is None else f'{r90:+.1f}%') + f' | {l180:,.0f} ({100*(l180/c-1):+.1f}%)')
    P(f'n={len(rows)}  median 90d highest {S.median(r[1] for r in rows):+.1f}%  median 90d lowest {S.median(r[0] for r in rows):+.1f}%  '
      f'median day 90 {S.median(r[2] for r in rows if r[2] is not None):+.1f}%  up at day 90 {sum(r[2] > 0 for r in rows if r[2] is not None)}/{sum(r[2] is not None for r in rows)}  '
      f'fell 25.3%+ within 90d {sum(r[0] <= -25.3 for r in rows)}/{len(rows)}')
    P('Entry quality only. No exit in the data. Computed, never fills.')
    open(os.path.join(HERE, 'RESULTS_turnmarkers.txt'), 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    main()
