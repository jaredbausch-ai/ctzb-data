"""How far past signals went, by tag: a likelihood ladder, NOT a take-profit rule.
25 Nov 2026 (Jared asked for "a range system, percentage of likelihood" per tag). Descriptive.
Exits are discretionary and settled (CONTEXT; PRETRADE: six mechanical exit rules, all lost to
holding). This only says how often signals with a tag reached each level within 60 days.
Population: datasets/ledger.csv, regime-gated graded signals with a full 60 days.
  python3 -I lab/reachladder.py -> lab/RESULTS_reachladder.txt
"""
import sys, os, csv, statistics as S, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); os.chdir(ROOT)
LEVELS = (10, 15, 20, 30, 50)
L = []
def P(s): L.append(s); print(s)
rows = [x for x in csv.DictReader(open('datasets/ledger.csv')) if x['bestMove'] and x['reached20']
        and dt.date.fromisoformat(x['entry']) <= dt.date(2026, 9, 25)]
def tag(t):
    b = t[:1]; fd = 'filled diamond' in t; hd = 'hollow diamond' in t
    return b + (' + filled diamond' if fd else ' + hollow diamond' if hd else '')
P('REACH LADDER by tag: share of signals whose best price in 60 days reached each level (lab/reachladder.py)')
P('asset tag | n | ' + ' | '.join(f'+{l}%' for l in LEVELS) + ' | median best | median worst drop')
for a in ('ETH', 'BTC'):
    groups = {}
    for x in rows:
        if x['asset'] == a: groups.setdefault(tag(x['tags']), []).append(x)
    for t in sorted(groups):
        g = groups[t]; up = [float(x['bestMove']) for x in g]; dd = [float(x['maxDrawdown']) for x in g]
        P(f'{a} {t} | {len(g)} | ' + ' | '.join(f'{round(100*sum(u >= l for u in up)/len(g))}%' for l in LEVELS) +
          f' | {S.median(up):+.1f}% | {S.median(dd):+.1f}%')
P('Entry quality only. No exit in the data; a level reached is not a profit taken. Computed signals, never fills.')
open(os.path.join(HERE, 'RESULTS_reachladder.txt'), 'w').write('\n'.join(L) + '\n')
