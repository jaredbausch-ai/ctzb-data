"""Checks 2 (grade_odds), 3 (if_it_misses), 6 (past_paths) from my recomputed rows."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C

OUT = os.path.dirname(os.path.abspath(__file__))
R = list(csv.DictReader(open(os.path.join(OUT, 'ledger_recomputed.csv'))))
for r in R:
    for k in ('up', 'dd', 'ret', 'ddpk', 'e'): r[k] = float(r[k])
    r['surv10'] = r['surv10'] == 'True'
    r['closes'] = json.loads(r['closes'])
L = {(x['chart'], x['entry']): x for x in csv.DictReader(open(os.path.join(C.REPO, 'datasets', 'ledger.csv')))}
F = json.load(open(os.path.join(C.REPO, 'feed', 'ctzb_feed.json')))
res = []

def cmp(where, field, shown, mine, tol=0):
    ok = shown is not None and mine is not None and abs(float(shown) - float(mine)) <= tol + 1e-9
    res.append(dict(check=where.split(':')[0], where=where, field=field, shown=shown, mine=mine, ok=ok))

pct = lambda G, f: C.r_half(100 * sum(1 for r in G if f(r)) / len(G)) if G else None
# ---- 2: grade_odds
for g in F['grade_odds']:
    a, gr = g['asset'], g['grade']
    if gr in ('A+', 'A', 'B', 'C'):
        G = [r for r in R if r['asset'] == a and r['grade'] == gr]
    elif gr in ('diamond or prime dot', 'no diamond or prime dot'):
        mk = lambda r: any(t in L[(r['chart'], r['entry'])]['tags'] for t in ('diamond', 'prime dot'))
        G = [r for r in R if r['asset'] == a and (mk(r) if gr.startswith('diamond') else not mk(r))]
    else:
        continue  # HTF divergence: lens logic, out of scope
    w = f'2: grade_odds {a} {gr}'
    cmp(w, 'past_trades', g['past_trades'], len(G))
    cmp(w, 'rose10_never_fell25_within60d_pct', g['rose10_never_fell25_within60d_pct'], pct(G, lambda r: r['surv10']))
    cmp(w, 'rose20_within60d_pct', g['rose20_within60d_pct'], pct(G, lambda r: r['up'] >= 20))
    cmp(w, 'median_deepest_dip_pct', g['median_deepest_dip_pct'], round(C.median([r['dd'] for r in G]), 1), 0.05)
    cmp(w, 'rose10_within60d_pct (FEED_SPEC says present)', g.get('rose10_within60d_pct'), pct(G, lambda r: r['up'] >= 10))
    cmp(w, 'sample', None if g['sample'] is None else 0, 0)
    res[-1]['shown'] = g['sample']; res[-1]['mine'] = f"{min(r['entry'] for r in G)} to {max(r['entry'] for r in G)}" if gr in ('A+','A','B','C') else res[-1]['shown']
    res[-1]['ok'] = res[-1]['shown'] == res[-1]['mine'] or gr not in ('A+','A','B','C')

# ---- 3: if_it_misses (miss = did NOT rise 10% within 60 days)
for m in F['if_it_misses']:
    a, gr = m['asset'], m['grade']
    G = [r for r in R if r['asset'] == a and r['grade'] == gr]
    M = [r for r in G if r['up'] < 10]
    M20 = [r for r in G if r['up'] < 20]
    w = f'3: if_it_misses {a} {gr}'
    for fld, mine, mine20, tol in [('signals', len(G), len(G), 0), ('misses', len(M), len(M20), 0),
                                   ('up_first', sum(r['up'] > 0 for r in M), sum(r['up'] > 0 for r in M20), 0),
                                   ('median_peak_pct', round(C.median([r['up'] for r in M]), 1), round(C.median([r['up'] for r in M20]), 1), 0.05),
                                   ('median_worst_drop_pct', round(C.median([r['dd'] for r in M]), 1), round(C.median([r['dd'] for r in M20]), 1), 0.05),
                                   ('median_day60_pct', round(C.median([r['ret'] for r in M]), 1), round(C.median([r['ret'] for r in M20]), 1), 0.05),
                                   ('mean_peak_pct', round(sum(r['up'] for r in M) / len(M), 1), round(sum(r['up'] for r in M20) / len(M20), 1), 0.05),
                                   ('peaked_5_or_more', sum(r['up'] >= 5 for r in M), sum(r['up'] >= 5 for r in M20), 0),
                                   ('peaked_10_or_more', sum(r['up'] >= 10 for r in M), sum(r['up'] >= 10 for r in M20), 0)]:
        cmp(w, fld, m[fld], mine, tol)
        res[-1]['mine_if_miss_is_+20'] = mine20
    res.append(dict(check='3', where=w, field='miss_rule (FEED_SPEC says present)', shown=m.get('miss_rule'), mine='did not rise 10% within 60 days', ok=m.get('miss_rule') is not None))

# ---- 6: past_paths
for p in F['past_paths']:
    a = p['asset']
    G = [r for r in R if r['asset'] == a and r['grade'] == 'A+']
    w = f'6: past_paths {a}'
    cmp(w, 'signals', p['signals'], len(G))
    paths = [[0.0] + [(c / r['e'] - 1) * 100 for c in r['closes']] for r in G]
    bad = 0
    for d in p['days']:
        k = d['day']
        vals = [x[k] for x in paths]
        for fld, f in (('q25_pct', .25), ('median_pct', .5), ('q75_pct', .75)):
            mine = round(C.quant(vals, f), 1)
            if abs(d[fld] - mine) > 0.1 + 1e-9:
                bad += 1
                res.append(dict(check='6', where=w, field=f'day {k} {fld}', shown=d[fld], mine=mine, ok=False))
    res.append(dict(check='6', where=w, field=f'{len(p["days"])*3} day-quantiles', shown='', mine=f'{bad} off by >0.1', ok=bad == 0))

with open(os.path.join(OUT, 'check236.json'), 'w') as f: json.dump(res, f, default=str, indent=0)
for x in res:
    if not x['ok']: print(x)
print(sum(x['ok'] for x in res), 'ok of', len(res))
