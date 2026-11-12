"""Ledger columns beyond the forward measures: the grade's whole-sample record and the 'odds on the day'."""
import pickle, sys, json, os, csv, statistics as st, datetime as dt
sys.path.insert(0, '.')
from core import *
rows_out = []
for NAME in ('replay_0414', 'current'):
    L = pickle.load(open(f'led_{NAME}.pkl', 'rb')); LG, groups = L['LG'], L['groups']
    LED = {(r['chart'], r['entry']): r for r in csv.DictReader(open(f'../a9/{NAME}/datasets/ledger.csv'))}
    bad = 0; n = 0
    for s in LG:
        r = LED[(s['chart'], str(s['d0']))]; G = groups[(s['a'], s['grade'])]; k = len(G)
        exp = dict(gradeReach20=rha(100 * sum(x['m']['r20'] for x in G) / k), gradeTouched30=rha(100 * sum(x['m']['t30'] for x in G) / k),
                   gradeMedDrawdown=rha(st.median([r6(x['m']['dd']) for x in G]), 1))
        prior = [x for x in LG if x['a'] == s['a'] and x['d0'] + dt.timedelta(days=61) <= s['d0']]
        Gp = [x for x in prior if x['grade'] == s['grade']]
        if len(Gp) < 10 or not prior:
            exp.update(dayReach10='', dayReach20='', dayReach30='', dayTouched30='', dayN=len(Gp), daySurv10='', dayScaled20='')
        else:
            def rate(f):
                base = sum(f(x) for x in prior) / len(prior)
                return rha(100 * (sum(f(x) for x in Gp) + 5 * base) / (len(Gp) + 5))
            exp.update(dayReach10=rate(lambda x: x['m']['up'] >= 10), dayReach20=rate(lambda x: x['m']['up'] >= 20), dayReach30=rate(lambda x: x['m']['up'] >= 30),
                       dayTouched30=rate(lambda x: x['m']['dd'] <= -30), dayN=len(Gp), daySurv10=rate(lambda x: x['m']['surv10']),
                       dayScaled20=rate(lambda x: bool(x['sc20'])))
        for kk, v in exp.items():
            n += 1
            ok = str(r[kk]) == str(v) or (r[kk] != '' and v != '' and float(r[kk]) == float(v))
            rows_out.append(dict(state=NAME, location=f"ledger {s['chart']} {s['d0']}", label=kk, shown=r[kk], yours=v, ok=ok, cause='' if ok else 'ledger extra column'))
            if not ok:
                bad += 1
                if bad < 15: print(NAME, s['chart'], s['d0'], kk, r[kk], v)
    print(NAME, n, 'checks', bad, 'disagree')
with open('ledgerextra.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(rows_out)
