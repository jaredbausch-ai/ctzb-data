"""Should funding count once or twice in the ETH grade? DECLARED 28 Oct 2026 20:20 ET.
FUND (funding at or above its 90-day median) and FCOOL (7-day mean funding at or above
its level 14 days earlier) both passed the lens rules as separate reads, but both are
funding. Three versions of the ETH grade, same other lenses (GAP HIGH AGREE BTC3), same
cut points (C 0-1, B 2, A 3, A+ 4+), same sample (2020 on, funding data present):
  V0  as live: FUND and FCOOL each count (funding can add 2)
  V1  funding counts once if EITHER is on
  V2  funding counts once only if BOTH are on
Reported per grade: n, +20% in 60d, touched -30%, median drawdown from entry (largest
dip in 60d), by period. Rule for preferring a version (set before running): the grade
must stay ordered (A+ >= A >= B >= C on +20% and A+ <= A <= B <= C on touched -30%) in
both periods; among versions that stay ordered, prefer the one with the larger A+ minus
C gap on +20% summed over both periods. Entry quality only, computed signals, not fills.
  python3 -I analysis/grade5.py -> analysis/RESULTS_grade5.txt
"""
import sys, os, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import grokpack as GP, pcrtest as PT
from grade3 import funding_series
L = []; P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)
rows, allsig = GP.build(); fb = PT.funding_below(); f = funding_series('ETH')
b3 = [x['d0'] for x in allsig[('BTC', '3D')]]
G0 = []
for r in rows:
    if r['a'] != 'ETH' or r['tf'] not in ('1D', '2D', '3D', '5D'): continue
    d0 = r['d0']; v = fb.get(('ETH', d0))
    w7 = [f[d0 - dt.timedelta(days=k)] for k in range(7) if d0 - dt.timedelta(days=k) in f]
    w7b = [f[d0 - dt.timedelta(days=14 + k)] for k in range(7) if d0 - dt.timedelta(days=14 + k) in f]
    if v is None or len(w7) < 5 or len(w7b) < 5: continue
    r['FUND'] = not v; r['FCOOL'] = sum(w7) / len(w7) >= sum(w7b) / len(w7b)
    r['base'] = sum([r['gap'] is not None and r['gap'] > 5, bool(r['higher']), r['agree'] >= 2,
                     r['tf'] in ('1D', '2D') and any(0 <= (d0 - d).days <= 10 for d in b3)])
    G0.append(r)
V = {'V0 funding counts twice': lambda r: r['base'] + r['FUND'] + r['FCOOL'],
     'V1 once if either': lambda r: r['base'] + (r['FUND'] or r['FCOOL']),
     'V2 once if both': lambda r: r['base'] + (r['FUND'] and r['FCOOL'])}
gr = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'
P('FUNDING ONCE OR TWICE IN THE ETH GRADE -- declared 28 Oct 2026, run', dt.date.today(), f'| {len(G0)} ETH signals 2020 on | entry quality only\n')
score = {}
for name, fn in V.items():
    P(name)
    ok = True; gap = 0
    for pl, sel in (('all', lambda r: True), ('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
        line = []; wins = []; t30s = []
        for g in ('A+', 'A', 'B', 'C'):
            G = [r for r in G0 if sel(r) and gr(fn(r)) == g]; n = len(G)
            if not n: line.append(f'{g} n=0'); wins.append(None); t30s.append(None); continue
            w = 100 * sum(r['win'] for r in G) / n; t = 100 * sum(r['t30'] for r in G) / n
            wins.append(w); t30s.append(t)
            line.append(f'{g} n={n:3} +20% {w:3.0f}% -30% {t:3.0f}% dd {st.median(r["m"]["dd"] for r in G):+5.1f}%')
        P(f'  {pl:8} ' + ' | '.join(line))
        if pl != 'all':
            ww = [x for x in wins if x is not None]; tt = [x for x in t30s if x is not None]
            if ww != sorted(ww, reverse=True) or tt != sorted(tt): ok = False
            if wins[0] is not None and wins[3] is not None: gap += wins[0] - wins[3]
    score[name] = (ok, gap)
    P(f'  ordered in both periods: {"yes" if ok else "NO"} | A+ minus C on +20%, summed over periods: {gap:+.0f}\n')
best = max((k for k in score if score[k][0]), key=lambda k: score[k][1], default=None)
P('PREFERRED by the declared rule:', best or 'none stays ordered')
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_grade5.txt'), 'w').write('\n'.join(L) + '\n')
