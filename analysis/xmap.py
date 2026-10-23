"""Full cross-asset agreement map: every BTC chart into every ETH chart, and back.

DECLARED BEFORE RUNNING (23 Oct 2026). Generalises analysis/xconf.py, which
tested only BTC 3D -> ETH 1D/2D because that was the question asked. All 32
cells are reported, failures included.

  cells      leader in {BTC,ETH} {1D,2D,3D,5D}  ->  follower in the other
             asset's {1D,2D,3D,5D}. 16 cells each direction.
  trade      every regime-gated follower signal (gate R.rsi_regime(BTC_2D,
             8,13,60,41)), entry = confirmation close, timed at the day that
             bar closes; outcomes on the follower asset's daily candles.
  condition  a gated leader signal had already confirmed 0-10 days before the
             follower entry (backward only). W = 5 as robustness.
  outcome    reach +20% within 60 days (as PRETRADE.md)
  PROMISING  a cell needs ALL of:
             (1) with - without >= +10 points at W=10
             (2) n with >= 30
             (3) ahead in at least 2/3 of years that have >= 3 signals on
                 each side
             (4) positive inside BOTH strata of the follower's own-asset
                 agreement (other charts of the same asset 1D/2D/3D/5D/8D
                 confirmed within 10 days: 0-1 vs 2+)
             (5) still >= +5 points at W=5
  caution    32 cells: a few will pass by luck. ETH and BTC share a calendar,
             so this is date-anchored and the per-year split is the real test.
             Cells sharing a follower overlap heavily.

Entry quality only: no exit, no strategy return. Signals computed, never fills.

Run from the repo root:  python3 -I analysis/xmap.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from xconf import confirmed
from tagstats import measure

TFS = ['1D', '2D', '3D', '5D']
REF = ['1D', '2D', '3D', '5D', '8D']


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    conf = {(a, tf): confirmed(f'{a}_{tf}', gate) for a in ('ETH', 'BTC') for tf in REF}
    dates = {k: [d for d, _ in v] for k, v in conf.items()}
    days = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
    pos = {a: {d: i for i, d in enumerate(days[a]['date'])} for a in days}
    print(f'{"leader -> follower":<20}{"with":>6}{"without":>9}{"diff":>6}{"n with":>8}{"years":>7}'
          f'{"own 0-1":>9}{"own 2+":>8}{"W=5":>6}  verdict')
    passed = []
    for lead, fol in (('BTC', 'ETH'), ('ETH', 'BTC')):
        last = days[fol]['date'][-2]
        for ftf in TFS:
            base = []
            for d0, s in conf[(fol, ftf)]:
                if d0 > last:
                    continue
                m = measure(days[fol], pos[fol], d0, s['entry'], 60)
                if not m:
                    continue
                own = sum(1 for t in REF if t != ftf and any(0 <= (d0 - x).days <= 10 for x in dates[(fol, t)]))
                base.append(dict(d=d0, y=d0.year, hit=m['up'] >= 20, own=own))
            for ltf in TFS:
                L = dates[(lead, ltf)]
                for r in base:
                    r['w10'] = any(0 <= (r['d'] - x).days <= 10 for x in L)
                    r['w5'] = any(0 <= (r['d'] - x).days <= 5 for x in L)
                rt = lambda sel: 100 * np.mean([r['hit'] for r in sel]) if sel else float('nan')
                w = [r for r in base if r['w10']]; wo = [r for r in base if not r['w10']]
                diff = rt(w) - rt(wo)
                ya = yt = 0
                for y in sorted({r['y'] for r in base}):
                    a = [r for r in w if r['y'] == y]; b = [r for r in wo if r['y'] == y]
                    if len(a) >= 3 and len(b) >= 3:
                        yt += 1; ya += rt(a) > rt(b)
                s01 = rt([r for r in w if r['own'] <= 1]) - rt([r for r in wo if r['own'] <= 1])
                s2 = rt([r for r in w if r['own'] >= 2]) - rt([r for r in wo if r['own'] >= 2])
                d5 = rt([r for r in base if r['w5']]) - rt([r for r in base if not r['w5']])
                ok = [diff >= 10, len(w) >= 30, yt > 0 and ya >= 2 * yt / 3, s01 > 0 and s2 > 0, d5 >= 5]
                verdict = 'PROMISING' if all(ok) else 'fails ' + ','.join(str(i + 1) for i, x in enumerate(ok) if not x)
                if all(ok):
                    passed.append(f'{lead} {ltf} -> {fol} {ftf}')
                f = lambda x: '  n/a' if np.isnan(x) else f'{x:+5.0f}'
                print(f'{lead+" "+ltf+" -> "+fol+" "+ftf:<20}{rt(w):>5.0f}%{rt(wo):>8.0f}%{diff:>+6.0f}{len(w):>8}'
                      f'{f"{ya}/{yt}":>7}{f(s01):>9}{f(s2):>8}{f(d5):>6}  {verdict}')
        print()
    print('PROMISING cells: ' + (', '.join(passed) if passed else 'none'))


if __name__ == '__main__':
    main()
