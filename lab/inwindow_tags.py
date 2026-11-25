"""Inside the ROC+ band windows: A + filled diamond against the OTHER signals in the same windows.
DECLARED 25 Nov 2026, before running. Statistics lab (stats-lab branch).

JARED (25 Nov): compare the A + filled diamond to "any other signals that are happening in
those ranges" -- not to every signal.

POPULATION: datasets/ledger.csv (regime-gated, graded; the tags live only there), ETH, every
chart 1D 2D 3D 5D, entry inside a band window: B60 = a closed ETH 5D bar with ROC+ below its
lower band in the 60 days before entry (lab/rocband.py). Also split by where in the window:
OUT (ROC still outside the band at entry, between band and turn) and AFTER (back inside).
GROUPS: AFD = bucket A + filled diamond (with or without prime dot); OTHER = every other signal
in the same windows. Reported for all ETH charts and for ETH 2D alone.
OUTCOMES (60 days from the confirmation close): change at day 60, best move, worst drop,
rose 10%, fell 25.3%, rose 10% and never fell 25.3%. Medians and rates.
No pass/fail: the AFD group is a handful of signals; this is a description, not a lens test.
ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I lab/inwindow_tags.py -> lab/RESULTS_inwindow_tags.txt
"""
import sys, os, csv, statistics as S, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, 'analysis'), ROOT]; os.chdir(ROOT)
from measures import LIQ
import inband as IB

L = []
def P(s): L.append(s); print(s)


def summ(g):
    if not g: return '0'
    med = lambda k: S.median(r[k] for r in g)
    pc = lambda f: round(100 * sum(f(r) for r in g) / len(g))
    return (f'{len(g)} | day60 {med("ret"):+.1f}% | best {med("up"):+.1f}% | worst {med("dd"):+.1f}% | '
            f'rose10 {pc(lambda r: r["up"] >= 10)}% | fell25.3 {pc(lambda r: r["dd"] <= LIQ)}% | surv10 {pc(lambda r: r["surv"])}%')


def main():
    ex, out_at, b60 = IB.excursions('ETH')
    rows = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        if x['asset'] != 'ETH' or not x['return60d']: continue
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > IB.LAST or not b60(d0): continue
        rows.append(dict(ch=x['chart'], d0=d0, tags=x['tags'], afd=x['tags'].startswith('A + filled diamond'),
                         where='OUT' if out_at(d0) else 'AFTER', ret=float(x['return60d']), up=float(x['bestMove']),
                         dd=float(x['maxDrawdown']), surv=x['surv10'] == 'yes'))
    P('INSIDE THE ETH 5D ROC+ BAND WINDOWS: A + filled diamond vs the other signals there (lab/inwindow_tags.py)')
    P('group | n | day60 | best | worst | rose10 | fell25.3 | surv10   (medians / rates)')
    for nm, sel in (('ALL ETH charts', lambda r: True), ('ETH 2D only', lambda r: r['ch'] == 'ETH 2D')):
        for w in ('ALL', 'OUT', 'AFTER'):
            g = [r for r in rows if sel(r) and (w == 'ALL' or r['where'] == w)]
            P(f'{nm}, {w:<5} A+filled diamond | ' + summ([r for r in g if r['afd']]))
            P(f'{nm}, {w:<5} other signals    | ' + summ([r for r in g if not r['afd']]))
    P('')
    P('Every A + filled diamond inside a window:')
    for r in sorted((r for r in rows if r['afd']), key=lambda r: r['d0']):
        P(f"{r['d0']} {r['ch']} {r['tags']} [{r['where']}] day60 {r['ret']:+.1f}% best {r['up']:+.1f}% worst {r['dd']:+.1f}% surv10 {'yes' if r['surv'] else 'no'}")
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_inwindow_tags.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
