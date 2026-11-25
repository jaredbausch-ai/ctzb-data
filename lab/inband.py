"""Signals fired BETWEEN the band and the turn: while the 5D ROC+ is outside its lower band.
DECLARED 25 Nov 2026, before running. Statistics lab (stats-lab branch).

JARED (25 Nov): "what you should be testing is the signals that are happening between the
band and the turns." band = the first closed 5D bar with ROC+ below its lower band; turn =
the first closed 5D bar back inside after that (lab/pine/ctzb_backdrop.pine v5 markers).

THE READ (the asset's own 5D chart; ROC+ Percent, 9 bars, 10th percentile of 250 bars)
  OUT   at the signal's entry (the confirmation close), the last 5D bar CLOSED by that day
        closed outside the band. That is exactly "on or after a band marker and before the
        next turn marker". Known at entry.
  For comparison, the earlier read B60 (a break in the last 60 days, lab/rocband.py) is
  re-reported on the same rows.

POPULATIONS (both declared)
  P1  GATED: datasets/ledger.csv, every regime-gated graded signal, 1D 2D 3D 5D. The standard.
  P2  UNGATED: every CTZB signal on ETH/BTC 1D 2D 3D 5D whatever the regime gate said
      (engine.signals with no gate), so the bear-market stretches count. Measured the same
      way (tagstats.measure, 60 days from the confirmation close).
  ETH is the question; BTC is run the same way. ETH and BTC are ONE sample (date-anchored).

MEASURES (the card's): surv10 = rose 10% and never fell 25.3% in 60 days (win);
  fell 25.3% (risk); rose 10%, rose 20% reported.

RULES (lab/rocband.py, on surv10): 1 lift >= +5 in BOTH periods (to 2021 / 2022 on), fell
  25.3% not more than 3 worse, n >= 15 per side per period; 2 ahead on >= 2/3 of charts (n>=5)
  and >= 2/3 of years (n>=3); 3 beats the 95th pct of 200 within-year shuffles; 4 (P1 only:
  P2 has no lens fields) no collapse inside either half of any live lens or bucket A.
  Also listed: every excursion (band to turn) with the signals inside it.

ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I lab/inband.py -> lab/RESULTS_inband.txt
"""
import sys, os, csv, random, bisect, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'analysis')); sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E
from measures import LIQ
from tagstats import bucket_end, measure
import rocband as RB
from backdrop import rules as _rules_print  # same four rules, same print format
import backdrop as BD

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)
BD.P = P  # route the shared rule printer into this file's results

random.seed(20261125)
SPLIT, LAST = RB.SPLIT, RB.LAST
TFS = ('1D', '2D', '3D', '5D')


def rate(g, k): return 100 * sum(x[k] for x in g) / len(g) if g else None
def f_(v): return '  -' if v is None else f'{v:3.0f}'


def excursions(a):
    ends, b, roc, low = RB.breaks(f'data/{a}_5D.csv')
    E5 = [bucket_end(b['date'], k) for k in range(len(b['date']))]
    closed = [(E5[k], roc[k] < low[k]) for k in range(len(E5)) if E5[k] is not None and low[k] is not None]
    ex = []; cur = None
    for e, out in closed:
        if out and cur is None: cur = [e, None]
        elif not out and cur is not None: cur[1] = e; ex.append(tuple(cur)); cur = None
    if cur is not None: ex.append((cur[0], None))
    days = [e for e, _ in closed]; state = [o for _, o in closed]

    def out_at(d0):
        j = bisect.bisect_right(days, d0)
        return j > 0 and state[j - 1]

    def b60(d0):
        j = bisect.bisect_right(ends, d0)
        return j > 0 and (d0 - ends[j - 1]).days <= 60
    return ex, out_at, b60


def main():
    P('SIGNALS BETWEEN THE BAND AND THE TURN -- declared 25 Nov 2026 (lab/inband.py)')
    X = {a: excursions(a) for a in ('ETH', 'BTC')}

    # P1 gated
    p1 = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > LAST or not x['reached20']: continue
        a = x['asset']
        p1.append(dict(a=a, ch=x['chart'], d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1,
                       win=x['surv10'] == 'yes', r10=x['reached10'] == 'yes', r20=x['reached20'] == 'yes',
                       t=float(x['maxDrawdown']) <= LIQ, bkA=x['tags'][:1] == 'A',
                       lens=set(t.strip() for t in x['lenses'].split('+')),
                       OUT=X[a][1](d0), B60=X[a][2](d0)))
    # P2 ungated
    p2 = []
    for a in ('ETH', 'BTC'):
        day = E.load(f'data/{a}_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}
        for tf in TFS:
            sig, b = E.signals(f'data/{a}_{tf}.csv', regime=lambda d: True)
            for s in sig:
                d0 = bucket_end(b['date'], s['ei'])
                if d0 is None or d0 > LAST or d0 not in pos: continue
                m = measure(day, pos, d0, s['entry'], 60)
                if m is None: continue
                p2.append(dict(a=a, ch=f'{a} {tf}', d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1,
                               win=m['up'] >= 10 and m['dd'] > LIQ, r10=m['up'] >= 10, r20=m['up'] >= 20,
                               t=m['dd'] <= LIQ, bkA=s['bk'] == 'A', lens=set(),
                               OUT=X[a][1](d0), B60=X[a][2](d0)))

    for nm, rows in (('P1 GATED (ledger)', p1), ('P2 UNGATED (every signal, gate ignored)', p2)):
        P('')
        P(f'== {nm} ==')
        P('SUMMARY  read asset | n on/off | surv10 on/off | rose10 on/off | rose20 on/off | fell25.3 on/off')
        for a in ('ETH', 'BTC'):
            for c in ('OUT', 'B60'):
                g = [r for r in rows if r['a'] == a]; on = [r for r in g if r[c]]; off = [r for r in g if not r[c]]
                P(f'{c:<4} {a} | {len(on)}/{len(off)} | {f_(rate(on,"win"))}/{f_(rate(off,"win"))} | {f_(rate(on,"r10"))}/{f_(rate(off,"r10"))} | '
                  f'{f_(rate(on,"r20"))}/{f_(rate(off,"r20"))} | {f_(rate(on,"t"))}/{f_(rate(off,"t"))}')
        P('RULES on OUT  name asset | to 2021: n on/off win on/off fell on/off | 2022 on: same | charts years | shuffle | overlap | verdict')
        for a in ('ETH', 'BTC'):
            g = [r for r in rows if r['a'] == a]
            if rows is p2:
                for r in g: r['lens'] = set(); r['bkA'] = False  # rule 4 not applicable to P2
            _rules_print(g, 'OUT', 'OUT')
        P('BY CHART (OUT)  chart | n on/off | surv10 on/off | fell25.3 on/off')
        for chn in sorted({r['ch'] for r in rows}):
            g = [r for r in rows if r['ch'] == chn]; on = [r for r in g if r['OUT']]; off = [r for r in g if not r['OUT']]
            P(f'{chn} | {len(on)}/{len(off)} | ' + (f'{f_(rate(on,"win"))}/{f_(rate(off,"win"))} | {f_(rate(on,"t"))}/{f_(rate(off,"t"))}' if on and off else '-'))
        P('BY YEAR (OUT)  asset year | n on/off | surv10 on/off | fell25.3 on/off')
        for a in ('ETH', 'BTC'):
            for y in sorted({r['yr'] for r in rows if r['a'] == a}):
                g = [r for r in rows if r['a'] == a and r['yr'] == y]; on = [r for r in g if r['OUT']]; off = [r for r in g if not r['OUT']]
                if on: P(f'{a} {y} | {len(on)}/{len(off)} | {f_(rate(on,"win"))}/{f_(rate(off,"win"))} | {f_(rate(on,"t"))}/{f_(rate(off,"t"))}')
        P('EXCURSIONS (band close .. turn close)  asset | signals inside: n, surv10, rose10, fell25.3')
        for a in ('ETH', 'BTC'):
            for s0, e0 in X[a][0]:
                g = [r for r in rows if r['a'] == a and r['d0'] >= s0 and (e0 is None or r['d0'] < e0)]
                if g: P(f'{a} {s0}..{e0 or "open"} | {len(g)}, {rate(g,"win"):.0f}%, {rate(g,"r10"):.0f}%, {rate(g,"t"):.0f}%')
    P('')
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_inband.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
