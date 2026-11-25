"""Same comparison as lab/inwindow_tags.py, with the regime gate PEELED BACK.
DECLARED 25 Nov 2026, before running. Statistics lab (stats-lab branch).
Every ETH CTZB signal on 1D 2D 3D 5D whatever the gate said (engine.signals, no gate), so the
2018 and 2022 bear-market band windows count. Tags straight from the engine: A = bucket A,
filled diamond = s['strong'] (diamond with its low under CT 50), as in analysis/grokpack.py.
Inside the ETH 5D band windows (B60), split OUT (between band and turn) / AFTER (back inside):
A + filled diamond vs the OTHER signals in the same part of the window. Outcomes as before,
60 days from the confirmation close (tagstats.measure). Descriptive, no pass/fail.
ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I lab/inwindow_tags_ungated.py -> lab/RESULTS_inwindow_tags_ungated.txt
"""
import sys, os, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, 'analysis'), ROOT]; os.chdir(ROOT)
import engine as E
from measures import LIQ
from tagstats import bucket_end, measure
import inband as IB
import inwindow_tags as IT

L = []
def P(s): L.append(s); print(s)
IT.P = P


def main():
    ex, out_at, b60 = IB.excursions('ETH')
    day = E.load('data/ETH_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}
    rows = []
    for tf in ('1D', '2D', '3D', '5D'):
        sig, b = E.signals(f'data/ETH_{tf}.csv', regime=lambda d: True)
        for s in sig:
            d0 = bucket_end(b['date'], s['ei'])
            if d0 is None or d0 > IB.LAST or d0 not in pos or not b60(d0): continue
            m = measure(day, pos, d0, s['entry'], 60)
            if m is None: continue
            afd = s['bk'] == 'A' and bool(s['strong'])
            rows.append(dict(ch=f'ETH {tf}', d0=d0, tags='A + filled diamond' if afd else s['bk'], afd=afd,
                             where='OUT' if out_at(d0) else 'AFTER', ret=m['ret'], up=m['up'], dd=m['dd'],
                             surv=m['up'] >= 10 and m['dd'] > LIQ))
    P('GATE PEELED BACK -- inside the ETH 5D ROC+ band windows: A + filled diamond vs the other signals there')
    P('group | n | day60 | best | worst | rose10 | fell25.3 | surv10   (medians / rates)')
    for nm, sel in (('ALL ETH charts', lambda r: True), ('ETH 2D only', lambda r: r['ch'] == 'ETH 2D')):
        for w in ('ALL', 'OUT', 'AFTER'):
            g = [r for r in rows if sel(r) and (w == 'ALL' or r['where'] == w)]
            P(f'{nm}, {w:<5} A+filled diamond | ' + IT.summ([r for r in g if r['afd']]))
            P(f'{nm}, {w:<5} other signals    | ' + IT.summ([r for r in g if not r['afd']]))
    P('')
    P('Every A + filled diamond inside a window:')
    for r in sorted((r for r in rows if r['afd']), key=lambda r: r['d0']):
        P(f"{r['d0']} {r['ch']} [{r['where']}] day60 {r['ret']:+.1f}% best {r['up']:+.1f}% worst {r['dd']:+.1f}% surv10 {'yes' if r['surv'] else 'no'}")
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_inwindow_tags_ungated.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
