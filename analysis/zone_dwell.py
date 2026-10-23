"""How long BTC's CT RSI stays in each zone during bull phases (22 Oct 2026).

Definitions, declared before running:
  chart     BTC 2D (data/BTC_2D.csv), the chart the regime gate runs on.
            CT = rsi(close, 14) on completed bars.
  zones     bullish control zone  CT >= 60
            bearish zone          CT <= 40
            neutral               40 < CT < 60
            (the indicator's zone lines; the gate's exit uses < 41)
  visit     a maximal run of consecutive bars closing in one zone. Entry = the
            first bar closing in it, exit = the first bar closing outside it.
            Days = exit bar's date - entry bar's date (calendar days, so the
            1-day bars TradingView makes on 31 Dec are counted correctly).
  bull      the mechanical gate R.rsi_regime(BTC_2D, 8, 13, 60, 41) state.
            A visit belongs to a bull phase if the gate is on for any bar of
            it; it is measured over its whole length, entry to exit, even
            where that starts before the gate turned on (the run that turns
            the gate on) or runs past the gate turning off.
  excluded  the visit still in progress on the last completed bar.
Also reported: the same for bear phases (gate off), for comparison, and each
bull episode's visits so one cycle cannot carry the average unseen.

Run from the repo root:  python3 -I analysis/zone_dwell.py
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R


def zone(v):
    return 'bull' if v >= 60 else 'bear' if v <= 40 else 'neutral'


def main():
    b = E.load('data/BTC_2D.csv')
    D = b['date'][:-1]; C = b['close'][:-1]          # drop the forming bar
    ct = E.rsi(C, 14)
    st, days = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41, ret_series=True)
    on = [st[d] for d in D]
    # episodes
    eps = []
    for i, d in enumerate(D):
        if on[i] and (i == 0 or not on[i - 1]):
            eps.append([d, None])
        if not on[i] and i and on[i - 1]:
            eps[-1][1] = D[i - 1]
    # visits
    visits = []
    i = next(k for k, v in enumerate(ct) if v is not None)
    while i < len(D):
        z = zone(ct[i]); j = i
        while j + 1 < len(D) and zone(ct[j + 1]) == z:
            j += 1
        if j + 1 < len(D):                            # completed: bar j+1 closed outside
            visits.append(dict(z=z, a=D[i], exit=D[j + 1], days=(D[j + 1] - D[i]).days,
                               bull=any(on[i:j + 1]), bear=not all(on[i:j + 1])))
        i = j + 1

    def table(sel, label):
        print(f'{label}')
        print(f'  {"zone":<9}{"visits":>7}{"avg days":>10}{"median":>8}{"min":>6}{"max":>6}{"share of days":>15}')
        tot = sum(v['days'] for v in sel)
        for z in ('bull', 'neutral', 'bear'):
            x = [v['days'] for v in sel if v['z'] == z]
            if not x:
                print(f'  {z:<9}{0:>7}'); continue
            print(f'  {z:<9}{len(x):>7}{np.mean(x):>10.1f}{np.median(x):>8.0f}{min(x):>6}{max(x):>6}'
                  f'{100*sum(x)/tot:>14.0f}%')

    print(f'BTC 2D, {D[0]} .. {D[-1]} (last completed bar)')
    print('Gate-on episodes: ' + ', '.join(f'{a} -> {b or "ongoing"}' for a, b in eps))
    print()
    table([v for v in visits if v['bull']], 'BULL PHASES (gate on at any bar of the visit)')
    print()
    table([v for v in visits if v['bear'] and not v['bull']], 'BEAR PHASES (gate off throughout), for comparison')
    print()
    print('BY BULL EPISODE: visits / avg days')
    for a, e in eps:
        end = e or D[-1]
        sel = [v for v in visits if v['bull'] and v['exit'] > a and v['a'] <= end]
        cells = []
        for z in ('bull', 'neutral', 'bear'):
            x = [v['days'] for v in sel if v['z'] == z]
            cells.append(f'{z} {len(x)} / {np.mean(x):.1f}d' if x else f'{z} 0')
        print(f'  {a} -> {e or "ongoing"}:  ' + '   '.join(cells))


if __name__ == '__main__':
    main()
