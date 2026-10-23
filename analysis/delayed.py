"""Delayed entry: wait N days after the CTZB confirmation and buy only if it held up.

DECLARED BEFORE RUNNING (23 Oct 2026). analysis/sweep.py found day-5/day-10
state sorts winners from losers, measured from the ORIGINAL entry. Jared wants
to use it as an entry rule, which buys at a later, different price. This
measures it the way it would actually be traded.

  signals    regime-gated signals, ETH 1D/2D/3D/5D and BTC 1D/2D/3D/5D, as sweep.py
  rules      A    buy the confirmation close (today's practice)
             G5   buy the day-5 close, only if it is at or above the confirmation close
             G10  the same at day 10
             S5   buy the day-5 close unless the trade is down 10%+ or has broken
                  the trough bar's low by then (a softer filter)
             S10  the same at day 10
             8D   buy the confirmation close only if the asset's 8D CT is rising
             8D+G5  both
  measured   FROM EACH RULE'S OWN ENTRY PRICE, next 60 days, daily candles:
             reach +20%, median 60d return, median drawdown from entry,
             touched -20%; plus how many signals it takes and the price it pays
             versus the confirmation close
  periods    2016-2021 and 2022 onward reported separately
  read       a rule helps only if, in BOTH periods, reach +20% is higher and the
             -20% touch rate lower than rule A, and it keeps at least 40% of signals

Entry quality only: no exit, no strategy return. Signals computed, never fills.

Run from the repo root:  python3 -I analysis/delayed.py
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end, measure
from sweep import closed_index

CHARTS = ['ETH_1D', 'ETH_2D', 'ETH_3D', 'ETH_5D', 'BTC_1D', 'BTC_2D', 'BTC_3D', 'BTC_5D']
SPLIT = dt.date(2022, 1, 1)


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    rules = ['A', 'G5', 'G10', 'S5', 'S10', '8D', '8D+G5']
    res = {(r, p): [] for r in rules for p in ('D', 'H')}
    for ch in CHARTS:
        a = ch.split('_')[0]
        day = E.load(f'data/{a}_1D.csv'); P = {d: i for i, d in enumerate(day['date'])}
        last = day['date'][-2]
        b8 = E.load(f'data/{a}_8D.csv'); ct8 = E.rsi(b8['close'], 14)
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        for s in sig:
            d0 = bucket_end(b['date'], s['ei'])
            if d0 is None or d0 not in P or d0 + dt.timedelta(days=70) > last:
                continue
            per = 'D' if d0 < SPLIT else 'H'
            e0 = s['entry']; tl = b['low'][s['ti']]
            k8 = closed_index(b8['date'], d0)
            up8 = k8 >= 1 and ct8[k8] is not None and ct8[k8 - 1] is not None and ct8[k8] > ct8[k8 - 1]

            def at(n):
                dn = d0 + dt.timedelta(days=n); j = P.get(dn)
                if j is None:
                    return None
                lows = [day['low'][P[d0 + dt.timedelta(days=k)]] for k in range(1, n + 1) if (d0 + dt.timedelta(days=k)) in P]
                return dn, day['close'][j], min(lows)

            def take(rule, dn, px):
                m = measure(day, P, dn, px, 60)
                if m:
                    res[(rule, per)].append(dict(m=m, paid=(px / e0 - 1) * 100))
            take('A', d0, e0)
            if up8:
                take('8D', d0, e0)
            for n in (5, 10):
                x = at(n)
                if not x:
                    continue
                dn, c, lo = x
                if c >= e0:
                    take(f'G{n}', dn, c)
                    if n == 5 and up8:
                        take('8D+G5', dn, c)
                if not (lo <= e0 * 0.9 or lo < tl):
                    take(f'S{n}', dn, c)
    for per, lab in (('D', '2016-2021'), ('H', '2022 onward')):
        nA = len(res[('A', per)])
        print(f'==================== {lab}  (rule A takes {nA} signals)')
        print(f'  {"rule":<7}{"taken":>7}{"of A":>6}{"price paid vs confirm":>23}{"reach +20%":>12}{"med 60d ret":>13}'
              f'{"med DD":>8}{"touched -20%":>14}')
        for r in rules:
            x = res[(r, per)]
            if not x:
                continue
            g = lambda k: np.array([v['m'][k] for v in x])
            print(f'  {r:<7}{len(x):>7}{100*len(x)/nA:>5.0f}%{np.median([v["paid"] for v in x]):>+22.1f}%'
                  f'{100*np.mean(g("up") >= 20):>11.0f}%{np.median(g("ret")):>+12.1f}%{np.median(g("dd")):>+7.1f}%'
                  f'{100*np.mean(g("dd") <= -20):>13.0f}%')
        print()
    print('READ (declared): helps only if higher reach +20% AND lower -20% touch than A in BOTH periods, keeping >= 40%')
    for r in rules[1:]:
        ok = True
        for per in ('D', 'H'):
            A = res[('A', per)]; X = res[(r, per)]
            if not X:
                ok = False; continue
            hA = np.mean([v['m']['up'] >= 20 for v in A]); hX = np.mean([v['m']['up'] >= 20 for v in X])
            dA = np.mean([v['m']['dd'] <= -20 for v in A]); dX = np.mean([v['m']['dd'] <= -20 for v in X])
            ok = ok and hX > hA and dX < dA and len(X) >= 0.4 * len(A)
        print(f'  {r:<7} {"HELPS" if ok else "does not pass"}')


if __name__ == '__main__':
    main()
