"""Extra probes: dayScaled20 with undefined scaled20 excluded; misses on exact prices vs 6-place values."""
import sys, os, datetime as dt
from fractions import Fraction as Fr
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3]]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
src = open(os.path.join(HERE, 'audit_state.py')).read().split('# ---------------------------------------------------------------- feed')[0]
exec(compile(src, 'audit_state_head', 'exec'))
changed = []; none_rows = 0
for k, r in LKEY.items():
    s = MYLED[k]
    prior = [h for h in HIST if h['a'] == s['a'] and h['d0'] + dt.timedelta(days=60) <= s['d0']]
    G = [h for h in prior if h.get('grade') == s['grade']]
    if len(G) < 10: continue
    sc = lambda h: scaled(h['a'], h['d0'], h['m']['up'])
    P2 = [h for h in prior if sc(h) is not None]; G2 = [h for h in G if sc(h) is not None]
    if len(P2) == len(prior): continue
    none_rows += 1
    if not G2 or not P2: alt = ''
    else:
        base = Fr(sum(1 for h in P2 if sc(h)), len(P2))
        alt = fr_round((sum(1 for h in G2 if sc(h)) + 5 * base) / (len(G2) + 5) * 100)
    if str(alt) != str(r['dayScaled20']): changed.append((k, r['dayScaled20'], str(alt)))
print(LABEL, 'ledger rows whose day-odds pool contains signals with no scaled20 value:', none_rows, '; dayScaled20 would change on', len(changed))
print(changed[:5])
# misses: 6-place vs exact
for a in ASSETS:
    for g in ('A+', 'A', 'B', 'C'):
        m = [s for s in MYLED.values() if s['a'] == a and s.get('grade') == g and not s['m']['r10']]
        ex = (sum(s['m']['up'] > 0 for s in m), sum(s['m']['up'] >= 5 for s in m))
        r6 = (sum(L.r6(s['m']['up']) > 0 for s in m), sum(L.r6(s['m']['up']) >= 5 for s in m))
        if ex != r6: print('misses differ', a, g, ex, r6)
# any signal whose up/dd sits within 1e-6 of a threshold (6-place storage could flip a count)
near = [(s['chart'], str(s['d0']), str(s['m']['up']), str(s['m']['dd'])) for s in MYLED.values()
        if any(abs(s['m']['up'] - t) < Dec('0.000001') for t in (0, 5, 10, 20, 30)) or any(abs(s['m']['dd'] - t) < Dec('0.000001') for t in (Dec('-25.3'), -30))]
print('near-threshold measures:', near)
