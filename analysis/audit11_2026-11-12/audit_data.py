"""Audit 11, data side: ledger, grade_odds, misses, odds_fade, cards, open signals, past paths.
  python3 audit_data.py <state_name> <state_root> <now ISO>"""
import csv, datetime as dt, json, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *          # noqa
import checks as K

NAME, ROOT, NOW = sys.argv[1], sys.argv[2], sys.argv[3]
now = dt.datetime.fromisoformat(NOW.replace('Z', '+00:00'))
S = State(ROOT, now)
chk = lambda *a, **k: K.chk(NAME, *a, **k)
feed = json.load(open(os.path.join(ROOT, 'feed', 'ctzb_feed.json')))
ledger = list(csv.DictReader(open(os.path.join(ROOT, 'datasets', 'ledger.csv'))))
MINE = {}          # exported for the page audit

# ------------------------------------------------------------------ raw-data sanity
bad = S.bucket_check()
chk('data/*.csv', '2D+ bars = 1D bucketed within calendar year (fetch.py rule)', len(bad), 0, 'stored multi-day bars differ from the bucket rule')
for k, v in S.clamps.items():
    if v:
        print('clamp', k, v)

# ------------------------------------------------------------------ 1. ledger
scored = S.scored()
mine_led = {}
for r in scored:
    if r['tf'] not in GRADED:
        continue
    if r['a'] == 'ETH' and not S.eth_member(r['d0']):
        continue
    mine_led[(r['ch'], str(r['d0']))] = r
theirs = {(x['chart'], x['entry']): x for x in ledger}
chk('ledger', 'membership: row count', len(theirs), len(mine_led), 'ledger membership')
for k in sorted(set(mine_led) - set(theirs)):
    chk('ledger', f'membership {k}', 'absent', 'present', 'signal missing from ledger')
for k in sorted(set(theirs) - set(mine_led)):
    chk('ledger', f'membership {k}', 'present', 'absent', 'ledger row not a qualifying signal')
yn = lambda b: 'yes' if b else 'no'
for k in sorted(set(mine_led) & set(theirs)):
    r, x = mine_led[k], theirs[k]; m = r['m']
    loc = f'ledger {k[0]} {k[1]}'
    chk(loc, 'asset', x['asset'], r['a'])
    chk(loc, 'low (trough bar open date)', x['low'], str(r['tdate']))
    chk(loc, 'entryPrice', x['entryPrice'], rh(r['entry'], 2))
    dclose = S.day[r['a']][S.dpos[r['a']][r['d0']]][4]
    chk(loc, 'entry close = daily close on entry date', r['entry'], dclose, 'chart close differs from daily close')
    chk(loc, 'tags', x['tags'], S.tags(r))
    chk(loc, 'year', x['year'], r['d0'].year)
    chk(loc, 'reached20', x['reached20'], yn(m['r20']))
    chk(loc, 'reached15', x['reached15'], yn(m['r15']))
    chk(loc, 'reached10', x['reached10'], yn(m['r10']))
    chk(loc, 'touched30', x['touched30'], yn(m['t30']))
    chk(loc, 'surv10', x['surv10'], yn(m['surv10']))
    vr = S.vol_ratio(r['a'], r['d0'])
    r['sc'] = None if vr is None else m['up'] >= 20 * vr
    chk(loc, 'scaled20', x['scaled20'], '' if r['sc'] is None else yn(r['sc']))
    for col, key in (('bestMove', 'up'), ('maxDrawdown', 'dd'), ('dipBeforeHigh', 'ddpk'), ('return60d', 'ret')):
        chk(loc, col, x[col], rh(m[key], 6))
    chk(loc, 'daysToHigh', x['daysToHigh'], m['dpk'])
    r['grade'] = x['grade']; r['lenses'] = x['lenses']

L = [mine_led[k] for k in sorted(mine_led, key=lambda k: (mine_led[k]['d0'], mine_led[k]['tf'])) if k in theirs]

# grade whole-sample record (grades.csv -> ledger grade columns and feed grade_odds)
def grec(G):
    n = len(G)
    return dict(n=n, reach20=rh(100 * sum(g['m']['r20'] for g in G) / n), touched30=rh(100 * sum(g['m']['t30'] for g in G) / n),
                medDip=rh(median([rh(g['m']['dd'], 6) for g in G]), 1), medDipFull=rh(median([g['m']['dd'] for g in G]), 1),
                reach10=rh(100 * sum(g['m']['r10'] for g in G) / n), surv10=rh(100 * sum(g['m']['surv10'] for g in G) / n),
                sample=f"{min(g['d0'] for g in G)} to {max(g['d0'] for g in G)}")
GR = {}
for a in ASSETS:
    for g in ('A+', 'A', 'B', 'C'):
        G = [r for r in L if r['a'] == a and r['grade'] == g]
        if G: GR[(a, g)] = grec(G)
for r in L:
    o = GR[(r['a'], r['grade'])]
    loc = f"ledger {r['ch']} {r['d0']}"
    x = theirs[(r['ch'], str(r['d0']))]
    chk(loc, 'gradeReach20', x['gradeReach20'], o['reach20'])
    chk(loc, 'gradeTouched30', x['gradeTouched30'], o['touched30'])
    chk(loc, 'gradeMedDrawdown', x['gradeMedDrawdown'], o['medDipFull'])

# odds on the day
for r in L:
    a, g, d0 = r['a'], r['grade'], r['d0']
    prior = [h for h in L if h['a'] == a and h['d0'] + TD(days=60) <= d0]
    G = [h for h in prior if h['grade'] == g]
    if len(G) < 10 or not prior:
        v = ['', '', '', '', len(G), '', '']
    else:
        def rate(fn, ok=lambda h: True):
            P = [h for h in prior if ok(h)]; Gk = [h for h in G if ok(h)]
            if not P or not Gk: return ''
            base = sum(fn(h) for h in P) / len(P)
            return rh(100 * (sum(fn(h) for h in Gk) + 5 * base) / (len(Gk) + 5))
        v = [rate(lambda h: h['m']['r10']), rate(lambda h: h['m']['r20']), rate(lambda h: h['m']['mh'] >= h['entry'] * 1.3),
             rate(lambda h: h['m']['t30']), len(G), rate(lambda h: h['m']['surv10']),
             rate(lambda h: bool(h['sc']), ok=lambda h: h['sc'] is not None)]
    x = theirs[(r['ch'], str(d0))]
    for col, val in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10', 'dayScaled20'), v):
        chk(f"ledger {r['ch']} {d0}", col, x[col], val)

# ------------------------------------------------------------------ 2. grade_odds
tag_rows = {'diamond or prime dot': lambda r: r['prime'] or r['dis'], 'no diamond or prime dot': lambda r: not (r['prime'] or r['dis'])}
for go in feed['grade_odds']:
    a, g = go['asset'], go['grade']
    loc = f'feed grade_odds {a} {g}'
    if g in ('HTF divergence', 'no HTF divergence'):
        continue                      # lens logic, out of scope (h)
    if g in tag_rows:
        G = [r for r in L if r['a'] == a and tag_rows[g](r)]
        o = grec(G)
    else:
        o = GR.get((a, g))
    if o is None:
        chk(loc, 'row exists', 'present', 'absent', 'no such group'); continue
    chk(loc, 'past_trades', go['past_trades'], o['n'])
    chk(loc, 'past_signals', go.get('past_signals'), o['n'])
    chk(loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], o['reach10'])
    chk(loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], o['surv10'])
    chk(loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], o['reach20'])
    chk(loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], o['medDip'], 'median of full-precision dips vs 6-place values' if o['medDip'] == o['medDipFull'] else 'median rounding')
    chk(loc, 'sample', go['sample'], o['sample'])
    chk(loc, 'label', go['label'], feed['label'])
MINE['grade'] = {f'{a}|{g}': v for (a, g), v in GR.items()}

# ------------------------------------------------------------------ 3. if_it_misses
def misses(G):
    m = [r for r in G if not r['m']['r10']]
    best = [rh(r['m']['up'], 6) for r in m]
    return dict(signals=len(G), misses=len(m), up_first=sum(r['m']['mh'] > r['entry'] for r in m),
                median_peak_pct=rh(median(best), 1) if m else None, mean_peak_pct=rh(sum(best) / len(best), 1) if m else None,
                peaked_5_or_more=sum(r['m']['mh'] >= r['entry'] * 1.05 for r in m),
                peaked_10_or_more=sum(r['m']['r10'] for r in m),
                median_worst_drop_pct=rh(median([rh(r['m']['dd'], 6) for r in m]), 1) if m else None,
                median_day60_pct=rh(median([rh(r['m']['ret'], 6) for r in m]), 1) if m else None)
MINE['misses'] = {}
for a in ASSETS:
    for g in ('A+', 'A', 'B', 'C'):
        G = [r for r in L if r['a'] == a and r['grade'] == g]
        mm = misses(G); MINE['misses'][f'{a}|{g}'] = mm
        f = next((x for x in feed['if_it_misses'] if x['asset'] == a and x['grade'] == g), None)
        loc = f'feed if_it_misses {a} {g}'
        if f is None:
            chk(loc, 'row exists', 'absent', 'present', 'missing'); continue
        for k_, v in mm.items():
            chk(loc, k_, f[k_], v)
        chk(loc, 'miss_rule', f['miss_rule'], 'did not rise 10% within 60 days')
EXD = D(2024, 9, 22)
known_ap = [r for r in L if r['a'] == 'ETH' and r['grade'] == 'A+' and r['d0'] + TD(days=60) <= EXD]
mm = misses(known_ap); MINE['ex_misses'] = mm
f = feed['example_if_it_misses']
for k_ in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
    chk('feed example_if_it_misses', k_, f[k_], mm[k_])
chk('feed example_if_it_misses', 'asset/grade', f"{f['asset']} {f['grade']}", 'ETH A+')

# ------------------------------------------------------------------ 4. odds_fade (ETH walk-forward tier as of 1 Jan 2026)
def zone_exit(ct):
    out, z = [], None
    for v in ct:
        if v is None: out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v)); out.append(z)
    return out
TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
pool = []
for tf in TFS:
    b = S.bars[('ETH', tf)]; C = [x[4] for x in b]; H = [x[2] for x in b]; Dd = [x[0] for x in b]
    ct = rsi(C); zm = zone_exit(ct)
    for s in S.sig[('ETH', tf)]:
        t = {s['bk'], 'any trough'}
        if s['dis']: t |= {'diamond', 'filled' if s['strong'] else 'hollow'}
        if s['prime']: t.add('prime dot')
        if s['dis'] and s['prime']: t.add('diamond+dot')
        if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: t.add('zone-exit B')
        s['tg'] = t
        # refresh.py's original rule on the chart's own bars: from the confirmation bar's OPEN date, 60 days, close vs entry
        ei = s['ei']; end = Dd[ei] + TD(days=60)
        if Dd[-1] < end: continue
        j = ei + 1; last = None
        while j < len(Dd) and Dd[j] <= end: last = C[j]; j += 1
        if last is None: continue
        pool.append(dict(tf=tf, d=Dd[ei], win=last > C[ei], tags=t))
upto = D(2026, 1, 1)
keep = []
for tf in TFS:
    for t in TAGS:
        sub = [r for r in pool if r['tf'] == tf and t in r['tags'] and r['d'] + TD(days=int(tf[:-1]) - 1 + 60) < upto]
        if len(sub) >= 8 and 100 * sum(r['win'] for r in sub) / len(sub) >= 70:
            keep.append((tf, t))
print('tier', keep)
MINE['tier'] = keep
win = []
for tf in TFS:
    for s in S.sig[('ETH', tf)]:
        if not any(tf == k[0] and k[1] in s['tg'] for k in keep): continue
        d0 = s['d0']
        if d0 >= S.today or not S.complete('ETH', d0): continue
        e = S.day['ETH'][S.dpos['ETH'][d0]][4]
        w = S.window('ETH', d0)
        win.append((e, w, s))
EARLY_BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
ed = []
for e, w, s in win:
    lo = min(b[3] for k, b in w if k <= 10); hi = max(b[2] for k, b in w if k > 10)
    ed.append(dict(dip=(lo / e - 1) * 100, r10=hi >= e * 1.1, r20=hi >= e * 1.2))
myED = []
for hi, lo, lab in EARLY_BANDS:
    g = [p for p in ed if lo < p['dip'] <= hi]
    if len(g) < 5: continue
    myED.append(dict(band=lab, n=len(g), r10=rh(100 * sum(p['r10'] for p in g) / len(g)), r20=rh(100 * sum(p['r20'] for p in g) / len(g)),
                     x10=100 * sum(p['r10'] for p in g) / len(g)))
hc = {'green on day 10': [], 'red on day 10': []}
for e, w, s in win:
    k10 = [b for k, b in w if k == 10]
    if not k10: continue
    hi = max(b[2] for k, b in w if k > 10)
    hc['green on day 10' if k10[0][4] >= e else 'red on day 10'].append(dict(r10=hi >= e * 1.1, r20=hi >= e * 1.2))
myHC = []
for lab in ('green on day 10', 'red on day 10'):
    g = hc[lab]
    if len(g) < 5: continue
    myHC.append(dict(check=lab, n=len(g), r10=rh(100 * sum(p['r10'] for p in g) / len(g)), r20=rh(100 * sum(p['r20'] for p in g) / len(g)),
                     x10=100 * sum(p['r10'] for p in g) / len(g)))
of = feed['odds_fade']
chk('feed odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70)
chk('feed odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)')
chk('feed odds_fade', 'early_dip row count', len(of['early_dip']), len(myED))
chk('feed odds_fade', 'day10 row count', len(of['day10']), len(myHC))
for fr, mr in zip(of['early_dip'], myED):
    loc = f"feed odds_fade early_dip {mr['band']}"
    chk(loc, 'band', fr['band'], mr['band'])
    for k_, v in (('past_trades', mr['n']), ('past_signals', mr['n']), ('rose10_after_day10_pct', mr['r10']), ('rose20_after_day10_pct', mr['r20']),
                  ('rose10_within60d_pct', mr['r10']), ('rose20_within60d_pct', mr['r20']), ('edge', 'intact' if mr['x10'] >= 70 else 'gone')):
        chk(loc, k_, fr.get(k_), v)
for fr, mr in zip(of['day10'], myHC):
    loc = f"feed odds_fade day10 {mr['check']}"
    chk(loc, 'check', fr['check'], mr['check'])
    for k_, v in (('past_trades', mr['n']), ('past_signals', mr['n']), ('rose10_after_day10_pct', mr['r10']), ('rose20_after_day10_pct', mr['r20']),
                  ('rose10_within60d_pct', mr['r10']), ('rose20_within60d_pct', mr['r20']), ('edge', 'intact' if mr['x10'] >= 70 else 'gone')):
        chk(loc, k_, fr.get(k_), v)
MINE['fade'] = dict(early=myED, day10=myHC)

# ------------------------------------------------------------------ 7. past paths
def paths(G):
    P = []
    for r in G:
        a, d0, e = r['a'], r['d0'], r['entry']
        p = [0.0]
        for k in range(1, 61):
            i = S.dpos[a].get(d0 + TD(days=k))
            if i is None: break
            p.append((S.day[a][i][4] / e - 1) * 100)
        if len(p) == 61: P.append(p)
    return dict(n=len(P), q25=[rh(lin_q([p[d] for p in P], .25), 1) for d in range(61)], med=[rh(lin_q([p[d] for p in P], .5), 1) for d in range(61)],
                q75=[rh(lin_q([p[d] for p in P], .75), 1) for d in range(61)])
MINE['paths'] = {}
for pp in feed['past_paths']:
    a = pp['asset']
    my = paths([r for r in L if r['a'] == a and r['grade'] == 'A+']); MINE['paths'][a] = my
    loc = f'feed past_paths {a}'
    chk(loc, 'signals', pp['signals'], my['n'])
    chk(loc, 'grade', pp['grade'], 'A+')
    chk(loc, 'days count', len(pp['days']), 61)
    for d in pp['days']:
        k_ = d['day']
        for f_, mk in (('q25_pct', 'q25'), ('median_pct', 'med'), ('q75_pct', 'q75')):
            chk(loc, f'day {k_} {f_}', d[f_], my[mk][k_])
chk('feed past_paths', 'assets', ','.join(p['asset'] for p in feed['past_paths']), 'ETH,BTC')
my = paths(known_ap); MINE['ex_paths'] = my
pp = feed['example_past_paths']
chk('feed example_past_paths', 'signals', pp['signals'], my['n'])
for d in pp['days']:
    for f_, mk in (('q25_pct', 'q25'), ('median_pct', 'med'), ('q75_pct', 'q75')):
        chk('feed example_past_paths', f"day {d['day']} {f_}", d[f_], my[mk][d['day']])

exec(open(os.path.join(K.OUT, 'part2.py')).read())
json.dump(MINE, open(os.path.join(K.OUT, f'_{NAME}_mine.json'), 'w'), default=str)
K.dump(f'_{NAME}_data.json')
bad = [r for r in K.ROWS if r['ok'] == 'no']
print(NAME, 'checks', len(K.ROWS), 'bad', len(bad))
for r in bad[:80]:
    print(r)
