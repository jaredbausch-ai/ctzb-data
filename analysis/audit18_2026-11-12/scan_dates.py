"""Scan past dates with my own code to pick replay dates: gate state, forming lows, open signals, quiet days."""
import sys, datetime as dt, json, csv
import core as K
root = '../a18/current'
gate = K.get_gate(root)
day = {a: K.Candles(f'{root}/data/{a}_1D.csv') for a in K.ASSETS}
led = list(csv.DictReader(open(f'{root}/datasets/ledger.csv')))
full = {}
today = dt.date(2026, 11, 13)
for a in K.ASSETS:
    for tf in K.TFS:
        c = K.Candles(f'{root}/data/{a}_{tf}.csv')
        s, _, _ = K.troughs(c, int(tf[:-1]), gate, today)
        full[(a, tf)] = [x for x in s if x['gate'] and x['closed']]
def build(a, tfd, upto):
    dd = day[a]; n = dd.pos[upto] + 1
    if tfd == 1: return dd.date[:n], dd.c[:n]
    dates, closes = [], []
    key = None
    for i in range(n):
        d = dd.date[i]; k = (d.year, (d - dt.date(d.year, 1, 1)).days // tfd)
        if k != key: dates.append(d); closes.append(dd.c[i]); key = k
        else: closes[-1] = dd.c[i]
    return dates, closes
def forming(a, tfd, D):
    dates, c = build(a, tfd, D); ct = K.wilder_rsi(c); n = len(c)
    for back in (1, 2, 3):
        ti = n - 1 - back
        if ti - 3 < 0 or ct[ti] is None: continue
        if any(ct[j] is None or ct[j] <= ct[ti] for j in range(ti - 3, ti)): continue
        if any(ct[j] < ct[ti] for j in range(ti + 1, n)): continue
        return dates[ti], 3 - back
    return None
out = []
D = dt.date(2020, 7, 1)
while D <= dt.date(2026, 11, 11):
    f = {}
    for a in K.ASSETS:
        for tf in K.TFS:
            r = forming(a, int(tf[:-1]), D)
            if r: f[f'{a} {tf}'] = (str(r[0]), r[1], gate(r[0]))
    opens = [f"{k[0]} {k[1]} {s['d0']}" for k, lst in full.items() for s in lst if 0 <= (D - s['d0']).days <= 60]
    og = [x for x in opens if ' 8D ' not in x]
    out.append(dict(date=str(D), gate=gate(D), forming=f, n_open=len(opens), n_open_graded=len(og),
                    cards=[k for k, v in f.items() if v[2] and not k.endswith('8D')]))
    D += dt.timedelta(days=1)
json.dump(out, open('scan.json', 'w'))
quiet = [o['date'] for o in out if not o['forming'] and not o['n_open']]
print('quiet days (nothing forming on any chart, no signal inside 60 days):', len(quiet), quiet[:6], '...', quiet[-6:])
print('quiet with gate on:', [o['date'] for o in out if not o['forming'] and not o['n_open'] and o['gate']][:10])
print('gate on, no card and no graded open signal:', [o['date'] for o in out if o['gate'] and not o['cards'] and not o['n_open_graded']][:10])
goff = [o for o in out if not o['gate']]
print('gate-off days:', len(goff), 'with forming lows:', sum(1 for o in goff if o['forming']), 'with a gate-ON-trough forming low under gate off:', [o['date'] for o in goff if o['cards']][:12])
print('gate on days with a gate-off-trough forming low:', [o['date'] for o in out if o['gate'] and any(not v[2] for v in o['forming'].values())][:12])
flips = [(out[i]['date'], out[i]['gate']) for i in range(1, len(out)) if out[i]['gate'] != out[i - 1]['gate']]
print('gate flips:', flips)
print('A+ signals:', [(r['chart'], r['entry']) for r in led if r['grade'] == 'A+'][-40:])
print('forming on 8D with gate on:', [o['date'] for o in out if any(k.endswith('8D') and v[2] for k, v in o['forming'].items())][:8])
