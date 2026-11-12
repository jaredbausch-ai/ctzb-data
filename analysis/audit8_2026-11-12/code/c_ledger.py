import sys
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from sigs import *
import chk

for st in ('REPLAY', 'CURRENT'):
    L = my_ledger(st)
    led = list(csv.DictReader(open(STATES[st] + '/datasets/ledger.csv')))
    chk.add(st, 'ledger.csv', 'row count', len(led), len(L))
    keys = [(r['chart'], r['entry']) for r in led]
    chk.add(st, 'ledger.csv', 'membership (same set of chart+entry)', 'set', 'set', ok=set(keys) == set(L), cause='membership')
    chk.add(st, 'ledger.csv', 'no duplicate rows', len(set(keys)), len(keys))
    # grade-level figures from my measures and the ledger's grades
    grade = {(r['chart'], r['entry']): r['grade'] for r in led}
    for r in led:
        k = (r['chart'], r['entry']); s = L[k]; m = s['m']; loc = f"ledger {k[0]} {k[1]}"
        exp = {'asset': s['asset'], 'low': str(s['tdate']), 'entryPrice': rhaz(s['entry'], 2), 'tags': tags(s),
               'reached20': m['r20'], 'touched30': m['t30'], 'bestMove': rhaz(m['up'], 6), 'maxDrawdown': rhaz(m['dd'], 6),
               'dipBeforeHigh': rhaz(m['ddpk'], 6), 'return60d': rhaz(m['ret'], 6), 'daysToHigh': m['dpk'], 'year': s['d0'].year,
               'reached10': m['r10'], 'reached15': m['r15'], 'surv10': m['surv10']}
        vr = volratio(st, s['asset'], s['d0'])
        exp['scaled20'] = '' if vr is None else (float(m['up']) >= 20 * vr)
        for f_, v in exp.items():
            yv = v if not isinstance(v, bool) else ('yes' if v else 'no')
            chk.add(st, loc, f_, r[f_], yv, cause='forward measure' if f_ not in ('tags', 'low') else 'tag/date')
        s['grade'] = r['grade']
    # grade odds columns
    for a in ('ETH', 'BTC'):
        for g in ('A+', 'A', 'B', 'C'):
            G = [L[k] for k in L if L[k]['asset'] == a and grade[k] == g]
            n = len(G)
            gr = pct(sum(x['m']['r20'] for x in G), n); gt = pct(sum(x['m']['t30'] for x in G), n)
            gm = rhaz(med([x['m']['dd'] for x in G]), 1)
            for r in led:
                if r['asset'] == a and r['grade'] == g:
                    loc = f"ledger {r['chart']} {r['entry']}"
                    chk.add(st, loc, 'gradeReach20', r['gradeReach20'], gr, 'grade odds')
                    chk.add(st, loc, 'gradeTouched30', r['gradeTouched30'], gt, 'grade odds')
                    chk.add(st, loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], gm, 'grade odds')
    # odds on the day
    for r in led:
        k = (r['chart'], r['entry']); s = L[k]; d0 = s['d0']; a = s['asset']
        prior = [L[x] for x in L if L[x]['asset'] == a and L[x]['d0'] + dt.timedelta(days=61) <= d0]
        G = [x for x in prior if x['grade'] == r['grade']]
        loc = f"ledger {k[0]} {k[1]}"
        def sc(x):
            vr = volratio(st, x['asset'], x['d0'])
            return vr is not None and float(x['m']['up']) >= 20 * vr
        fns = {'dayReach10': lambda x: x['m']['r10'], 'dayReach20': lambda x: x['m']['r20'],
               'dayReach30': lambda x: x['m']['up'] >= 30, 'dayTouched30': lambda x: x['m']['dd'] <= -30,
               'daySurv10': lambda x: x['m']['surv10'], 'dayScaled20': sc}
        chk.add(st, loc, 'dayN', r['dayN'], len(G), 'odds on the day')
        for f_, fn in fns.items():
            if len(G) < 10 or not prior:
                y = ''
            else:
                base = F(sum(bool(fn(x)) for x in prior), len(prior))
                y = rhaz(100 * (sum(bool(fn(x)) for x in G) + 5 * base) / (len(G) + 5))
            chk.add(st, loc, f_, r[f_], y, 'odds on the day')
chk.dump('_ledger.csv')
bad = [c for c in chk.CHECKS if c['ok'] == 'no']
print(len(chk.CHECKS), 'checks', len(bad), 'bad')
for c in bad[:40]: print(c)
