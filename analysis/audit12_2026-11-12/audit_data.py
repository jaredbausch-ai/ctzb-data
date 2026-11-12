"""Compare one state's ledger, feed and datasets with my own computation.
python3 audit_data.py <state_name> <state_dir> <pkl>"""
import sys, os, csv, json, pickle, re, datetime as dt, statistics as st, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import chk as K

SN, root, pkl = sys.argv[1:4]
P = pickle.load(open(pkl, 'rb'))
sig = P['sig']; today = P['today']; now = P['now']
M = L.Market(root, now)
feed = json.load(open(os.path.join(root, 'feed', 'ctzb_feed.json')))
ledger = list(csv.DictReader(open(os.path.join(root, 'datasets', 'ledger.csv'))))
rh = L.rh
EXD = dt.date(2024, 9, 22)
MINE = {}           # (chart, d0) -> signal
for (a, tf), lst in sig.items():
    for x in lst:
        if x['closed']:
            MINE[(x['ch'], str(x['d0']))] = x
members = {k: x for k, x in MINE.items() if x['member']}
LED = {(r['chart'], r['entry']): r for r in ledger}
c = lambda loc, lab, shown, yours, cause='': K.check(SN, loc, lab, shown, yours, cause)
yn = lambda b: 'yes' if b else 'no'

# ------------------------------------------------------------------ 1. ledger membership
for k in sorted(set(members) | set(LED)):
    c('ledger membership', f'{k[0]} {k[1]}', 'in ledger' if k in LED else 'absent', 'in ledger' if k in members else 'absent',
      'membership rule')
c('ledger', 'row count', len(ledger), len(members), 'membership')

# grade per member, from the ledger (grades are out of scope)
G = {k: LED[k]['grade'] for k in LED}
for k, x in members.items():
    x['grade'] = G.get(k); x['lenses'] = LED[k]['lenses'] if k in LED else None

# ------------------------------------------------------------------ 2. grade odds (whole sample)
def grade_stats(rows):
    n = len(rows)
    if not n:
        return None
    return dict(n=n, reach10=rh(100 * sum(x['m']['r10'] for x in rows) / n), surv10=rh(100 * sum(x['m']['surv10'] for x in rows) / n),
                reach20=rh(100 * sum(x['m']['r20'] for x in rows) / n), t30=rh(100 * sum(x['m']['t30'] for x in rows) / n),
                medDip=rh(st.median(x['m']['dd'] for x in rows), 1),
                sample=f"{min(x['d0'] for x in rows)} to {max(x['d0'] for x in rows)}")
GS = {}
for a in ('ETH', 'BTC'):
    for g in ('A+', 'A', 'B', 'C'):
        GS[(a, g)] = grade_stats([x for x in members.values() if x['a'] == a and x['grade'] == g])
ethm = [x for x in members.values() if x['a'] == 'ETH']
GS[('ETH', 'diamond or prime dot')] = grade_stats([x for x in ethm if x['prime'] or x['dis']])
GS[('ETH', 'no diamond or prime dot')] = grade_stats([x for x in ethm if not (x['prime'] or x['dis'])])
for go in feed['grade_odds']:
    key = (go['asset'], go['grade'])
    loc = f'grade_odds {go["asset"]} {go["grade"]}'
    if 'HTF' in go['grade']:
        continue   # (h) lens logic, out of scope
    s = GS.get(key)
    if s is None:
        c(loc, 'row exists', 'present', 'no signals', 'grade_odds'); continue
    c(loc, 'past_trades', go['past_trades'], s['n'], 'grade_odds count')
    c(loc, 'past_signals', go.get('past_signals'), s['n'], 'grade_odds count')
    c(loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], s['reach10'], 'grade_odds')
    c(loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], s['surv10'], 'grade_odds')
    c(loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], s['reach20'], 'grade_odds')
    c(loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], s['medDip'], 'grade_odds')
    c(loc, 'sample', go['sample'], s['sample'], 'grade_odds sample range')
    c(loc, 'label', go['label'][:40], 'Computed signal, not a fill. No trade wa', 'label')

# ------------------------------------------------------------------ 1b. ledger rows, every column
hist = sorted([x for x in members.values()], key=lambda x: x['d0'])
def day_odds(a, g, d0):
    prior = [h for h in hist if h['a'] == a and h['d0'] + dt.timedelta(days=60) <= d0]
    Gp = [h for h in prior if h['grade'] == g]
    if len(Gp) < 10 or not prior:
        return dict(dayReach10='', dayReach20='', dayReach30='', dayTouched30='', dayN=len(Gp), daySurv10='', dayScaled20='')
    def rate(fn, ok=lambda h: True):
        Pp = [h for h in prior if ok(h)]; Gk = [h for h in Gp if ok(h)]
        if not Pp or not Gk:
            return ''
        base = sum(fn(h) for h in Pp) / len(Pp)
        return rh(100 * (sum(fn(h) for h in Gk) + 5 * base) / (len(Gk) + 5))
    return dict(dayReach10=rate(lambda h: h['m']['r10']), dayReach20=rate(lambda h: h['m']['r20']), dayReach30=rate(lambda h: h['m']['r30']),
                dayTouched30=rate(lambda h: h['m']['t30']), dayN=len(Gp), daySurv10=rate(lambda h: h['m']['surv10']),
                dayScaled20=rate(lambda h: bool(h['sc']), ok=lambda h: h['sc'] is not None))
for k, r in LED.items():
    x = members.get(k)
    if x is None:
        continue
    m = x['m']; loc = f'ledger {k[0]} {k[1]}'
    c(loc, 'low', r['low'], str(x['tdate']), 'trough date')
    c(loc, 'entryPrice', float(r['entryPrice']), rh(x['entry'], 2), 'entry price')
    c(loc, 'tags', r['tags'], M.tags(x), 'tags')
    c(loc, 'asset', r['asset'], x['a'])
    c(loc, 'year', int(r['year']), x['d0'].year)
    for col, v in (('reached20', yn(m['r20'])), ('touched30', yn(m['t30'])), ('reached10', yn(m['r10'])), ('reached15', yn(m['r15'])),
                   ('surv10', yn(m['surv10'])), ('scaled20', '' if x['sc'] is None else yn(x['sc']))):
        c(loc, col, r[col], v, 'yes/no measure')
    for col, v in (('bestMove', m['up']), ('maxDrawdown', m['dd']), ('dipBeforeHigh', m['ddpk']), ('return60d', m['ret'])):
        c(loc, col, float(r[col]), rh(v, 6), '6-place measure')
    c(loc, 'daysToHigh', int(r['daysToHigh']), m['dpk'], 'day of high')
    gs = GS[(x['a'], x['grade'])]
    c(loc, 'gradeReach20', r['gradeReach20'], gs['reach20'], 'grade odds column')
    c(loc, 'gradeTouched30', r['gradeTouched30'], gs['t30'], 'grade odds column')
    c(loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], gs['medDip'], 'grade odds column')
    for col, v in day_odds(x['a'], x['grade'], x['d0']).items():
        c(loc, col, r[col], v, 'odds on the day')
    # consistency of the two +10% readings (percentage vs price)
    if (m['up'] >= 10) != m['r10'] or (m['up'] >= 20) != m['r20']:
        c(loc, 'float edge up>=10 vs high>=1.1e', yn(m['up'] >= 10), yn(m['r10']), 'float boundary')

# ------------------------------------------------------------------ 3. if it misses
def misses(rows):
    ms = [x for x in rows if not x['m']['r10']]
    best = [x['m']['up'] for x in ms]
    best6 = [rh(v, 6) for v in best]
    o = dict(signals=len(rows), misses=len(ms), up_first=sum(b > 0 for b in best), peaked_5_or_more=sum(b >= 5 for b in best),
             peaked_10_or_more=sum(b >= 10 for b in best))
    if ms:
        o.update(median_peak_pct=rh(st.median(best6), 1), mean_peak_pct=rh(st.mean(best6), 1),
                 median_worst_drop_pct=rh(st.median(rh(x['m']['dd'], 6) for x in ms), 1),
                 median_day60_pct=rh(st.median(rh(x['m']['ret'], 6) for x in ms), 1))
        # full-precision variants (flag if the 6-place stored value changes the shown rounding)
        o['_fp'] = dict(median_peak_pct=rh(st.median(best), 1), mean_peak_pct=rh(st.mean(best), 1),
                        median_worst_drop_pct=rh(st.median(x['m']['dd'] for x in ms), 1), median_day60_pct=rh(st.median(x['m']['ret'] for x in ms), 1))
    return o
MISS = {}
for a in ('ETH', 'BTC'):
    for g in ('A+', 'A', 'B', 'C'):
        MISS[(a, g)] = misses([x for x in members.values() if x['a'] == a and x['grade'] == g])
seen = set()
for mi in feed['if_it_misses']:
    key = (mi['asset'], mi['grade']); seen.add(key); o = MISS[key]; loc = f'if_it_misses {key[0]} {key[1]}'
    for f in ('signals', 'misses', 'up_first', 'peaked_5_or_more', 'peaked_10_or_more', 'median_peak_pct', 'mean_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
        c(loc, f, mi[f], o.get(f), 'misses')
    for f, v in o.get('_fp', {}).items():
        if v != o[f]:
            c(loc, f + ' (full precision)', mi[f], v, '6-place vs full precision')
    c(loc, 'miss_rule', mi['miss_rule'], 'did not rise 10% within 60 days')
for key in MISS:
    if key not in seen and MISS[key]['signals']:
        c('if_it_misses', f'{key} present', 'absent', 'present', 'missing row')
exs = [x for x in members.values() if x['a'] == 'ETH' and x['grade'] == 'A+' and x['d0'] + dt.timedelta(days=60) <= EXD]
eo = misses(exs); emi = feed['example_if_it_misses']
for f in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
    c('example_if_it_misses', f, emi[f], eo.get(f), 'example misses')
for f, v in eo.get('_fp', {}).items():
    if f in emi and v != eo[f]:
        c('example_if_it_misses', f + ' (full precision)', emi[f], v, '6-place vs full precision')

# ------------------------------------------------------------------ 7. past paths
def paths(rows):
    out = []
    for x in rows:
        a = x['a']; P_ = M.pos[a]; dd = M.day[a]
        p = [0.0]
        for k in range(1, 61):
            i = P_.get(x['d0'] + dt.timedelta(days=k))
            if i is None:
                break
            p.append((dd['close'][i] / x['entry'] - 1) * 100)
        if len(p) == 61:
            out.append(p)
    return out
def cmp_paths(loc, pp, rows):
    ps = paths(rows)
    c(loc, 'signals', pp['signals'], len(ps), 'path count')
    c(loc, 'days count', len(pp['days']), 61)
    for d in pp['days']:
        k = d['day']
        for f, qq in (('q25_pct', .25), ('median_pct', .5), ('q75_pct', .75)):
            c(loc, f'day {k} {f}', d[f], rh(L.q([p[k] for p in ps], qq), 1), 'path quantile')
for pp in feed['past_paths']:
    cmp_paths(f'past_paths {pp["asset"]}', pp, [x for x in members.values() if x['a'] == pp['asset'] and x['grade'] == 'A+'])
cmp_paths('example_past_paths', feed['example_past_paths'], exs)
c('past_paths', 'assets', ','.join(p['asset'] for p in feed['past_paths']), 'ETH,BTC')

# ------------------------------------------------------------------ 4. odds fade
TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
def zser(ct):
    out, z = [], None
    for v in ct:
        if v is None:
            out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v)); out.append(z)
    return out
pool = []; fadesig = []
for tf in (1, 2, 3, 5, 8):
    b = M.chart('ETH', tf); Cc, Dd, n = b['close'], b['date'], len(b['close'])
    allt, ct, Kk = M.troughs('ETH', tf, gated=True)
    zm = zser(ct)
    for s in allt:
        tg = {s['bk'], 'any trough'}
        if s['dis']: tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
        if s['prime']: tg.add('prime dot')
        if s['dis'] and s['prime']: tg.add('diamond+dot')
        if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: tg.add('zone-exit B')
        s['tg'] = tg
        ei = s['ei']
        if ei >= n:
            continue
        end = Dd[ei] + dt.timedelta(days=60)
        if Dd[-1] >= end:
            w = [j for j in range(ei + 1, n) if Dd[j] <= end]
            if w:
                pool.append(dict(chart=f'ETH {tf}D', tf=tf, tags=tg, d=Dd[ei], win=Cc[w[-1]] / Cc[ei] - 1 > 0))
        fadesig.append(s)
def select_tier(upto):
    keep = []
    for tf in (1, 2, 3, 5, 8):
        for t in TAGS:
            sub = [r for r in pool if r['tf'] == tf and t in r['tags'] and r['d'] + dt.timedelta(days=tf - 1 + 60) < upto]
            if len(sub) >= 8 and 100 * sum(r['win'] for r in sub) / len(sub) >= 70:
                keep.append((f'ETH {tf}D', t))
    return keep
keep = select_tier(dt.date(today.year, 1, 1))
tierfile = list(csv.reader(open(os.path.join(root, 'datasets', 'oddsfade.csv'))))
fpool = []
for s in fadesig:
    if not any(s['ch'] == k0 and k1 in s['tg'] for k0, k1 in keep):
        continue
    if not s['closed']:
        continue
    ks, ok = M.window('ETH', s['d0'])
    if not ok:
        continue
    dd = M.day['ETH']; e = dd['close'][M.pos['ETH'][s['d0']]]
    days = [(k, (dd['date'][k] - s['d0']).days) for k in ks]
    lo10 = min(dd['low'][k] for k, d in days if d <= 10); hi_after = max(dd['high'][k] for k, d in days if d > 10)
    k10 = [k for k, d in days if d == 10]
    fpool.append(dict(dip=(lo10 / e - 1) * 100, r10=hi_after >= e * 1.10, r20=hi_after >= e * 1.20,
                      green=None if not k10 else dd['close'][k10[0]] >= e, s=s))
BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
myfade = {'early_dip': [], 'day10': []}
for hi, lo, lab in BANDS:
    g = [p for p in fpool if lo < p['dip'] <= hi]
    if len(g) >= 5:
        x10 = 100 * sum(p['r10'] for p in g) / len(g)
        myfade['early_dip'].append(dict(band=lab, n=len(g), r10=rh(x10), r20=rh(100 * sum(p['r20'] for p in g) / len(g)), x10=x10, edge='intact' if x10 >= 70 else 'gone'))
for lab, f in (('green on day 10', True), ('red on day 10', False)):
    g = [p for p in fpool if p['green'] is f]
    if len(g) >= 5:
        x10 = 100 * sum(p['r10'] for p in g) / len(g)
        myfade['day10'].append(dict(band=lab, n=len(g), r10=rh(x10), r20=rh(100 * sum(p['r20'] for p in g) / len(g)), x10=x10, edge='intact' if x10 >= 70 else 'gone'))
of = feed['odds_fade']
c('odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70)
c('odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)')
c('odds_fade', 'tier pairs (mine)', '', '; '.join(f'{a} {b}' for a, b in keep), 'info only') if False else None
for kind, key in (('early_dip', 'band'), ('day10', 'check')):
    c('odds_fade', f'{kind} rows', len(of[kind]), len(myfade[kind]), 'odds fade rows')
    for fr, mr in zip(of[kind], myfade[kind]):
        loc = f'odds_fade {kind} {fr[key]}'
        c(loc, key, fr[key], mr['band'])
        c(loc, 'past_trades', fr['past_trades'], mr['n'], 'odds fade n')
        c(loc, 'past_signals', fr.get('past_signals'), mr['n'], 'odds fade n')
        for f in ('rose10_after_day10_pct', 'rose10_within60d_pct'):
            c(loc, f, fr[f], mr['r10'], 'odds fade share')
        for f in ('rose20_after_day10_pct', 'rose20_within60d_pct'):
            c(loc, f, fr[f], mr['r20'], 'odds fade share')
        c(loc, 'edge (exact share vs 70)', fr['edge'], mr['edge'], 'edge mark')
FADE_INFO = dict(keep=keep, n=len(fpool))

# ------------------------------------------------------------------ 5. cards
PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
lensset = lambda txt: frozenset() if txt in ('none', '-', '') else frozenset(PLAIN.get(t, t) for t in txt.split('; ')) if ';' in txt or txt in PLAIN else frozenset(txt.split(' + '))
def ledlens(x):
    return frozenset() if x['lenses'] in ('-', '') else frozenset(x['lenses'].split(' + '))
gof = lambda n: 'C' if n <= 1 else 'B' if n == 2 else 'A' if n == 3 else 'A+'

def sample_for(a, tf, grade, have, known):
    Cr = [x for x in known if x['a'] == a and x['tf'] == tf]
    ex = [x for x in Cr if ledlens(x) == have]
    sg = [x for x in Cr if x['grade'] == grade]
    ag = [x for x in known if x['a'] == a and x['grade'] == grade]
    if len(ex) >= 15: return 'exact', ex, len(ex), len(sg)
    if len(sg) >= 15: return 'chart', sg, len(ex), len(sg)
    return 'asset', ag, len(ex), len(sg)

def card_figs(G):
    n = len(G); f = {}
    pct = lambda k: rh(100 * k / n) if n else None
    f['n'] = n
    f['surv10'] = pct(sum(x['m']['surv10'] for x in G))
    sc = [x['sc'] for x in G if x['sc'] is not None]
    f['scaled20'] = rh(100 * sum(sc) / len(sc)) if sc else None
    f['reach20'] = pct(sum(x['m']['r20'] for x in G)); f['reach10'] = pct(sum(x['m']['r10'] for x in G))
    f['t30'] = pct(sum(x['m']['t30'] for x in G))
    for k, mk in (('best', 'up'), ('dip', 'ddpk'), ('deep', 'dd')):
        v = st.median(x['m'][mk] for x in G)
        f[k] = rh(v, 1); f[k + 'X'] = rh(v, 6); f[k + 'raw'] = v
    old = [x for x in G if x['d0'] < L.SPLIT]; new = [x for x in G if x['d0'] >= L.SPLIT]
    f['nOld'], f['nNew'] = len(old), len(new)
    f['sOld'] = rh(100 * sum(x['m']['surv10'] for x in old) / len(old)) if old else None
    f['sNew'] = rh(100 * sum(x['m']['surv10'] for x in new) / len(new)) if new else None
    ok = sum(x['m']['fe'] == 'ok' for x in G); lq = sum(x['m']['fe'] == 'liq' for x in G)
    f['fe'] = (pct(ok), pct(lq), rh(100 * ok / n, 6) if n else None, 100 * ok / n if n else None)
    f['lad'] = {}
    for th in (5, 10, 15, 20):
        hit = [x for x in G if x['m']['lad'][th] is not None]
        h = len(hit); okk = sum(x['m']['lad'][th] == 'ok' for x in hit); lq = sum(x['m']['lad'][th] == 'liq' for x in hit)
        f['lad'][th] = (h, rh(100 * okk / h) if h else None, rh(100 * lq / h) if h else None, rh(100 * okk / h, 6) if h else None, 100 * okk / h if h else None)
    t10 = [x['m']['d10'] for x in G if x['m']['d10'] is not None]; t20 = [x['m']['d20'] for x in G if x['m']['d20'] is not None]
    f['d10'] = rh(st.median(t10)) if t10 else None; f['d20'] = rh(st.median(t20)) if t20 else None
    f['dHigh'] = rh(st.median(x['m']['dpk'] for x in G)); f['dLow'] = rh(st.median(x['m']['ddday'] for x in G))
    # edge on exact shares
    if f['fe'][3] is not None and f['fe'][3] < 70:
        f['edge'] = 0
    else:
        f['edge'] = next((-th for th in (5, 10, 15, 20) if f['lad'][th][4] is not None and f['lad'][th][4] < 70), None)
    return f

def low_day(a, tf, tdate):
    b = M.chart(a, tf)
    cd = L.bar_close_date(tf, tdate)
    days = [tdate + dt.timedelta(days=i) for i in range((cd - tdate).days + 1)]
    cand = [(M.day[a]['low'][M.pos[a][d]], d) for d in days if d in M.pos[a]]
    return str(min(cand)[1])

CARDS = {}   # loc -> (feed card, my figs, my sample info)
def cmp_card(loc, cd, a, tf, grade, have, known, extra):
    rule, G, nex, nsg = sample_for(a, tf, grade, have, known)
    f = card_figs(G)
    CARDS[loc] = (cd, f, rule, nex, nsg)
    for k, v in extra.items():
        c(loc, k, cd.get(k), v, 'card date/price')
    c(loc, 'past_trades', cd['past_trades'], f['n'], 'card sample')
    c(loc, 'past_signals', cd.get('past_signals'), f['n'], 'card sample')
    # sample text: the numbers and the rule it states
    txt = cd['sample']; nums = [int(x) for x in re.findall(r'\b(\d+)\b', re.sub(r'\b(1D|2D|3D|5D|8D)\b|60 days', '', txt))]
    if rule == 'exact':
        exp = 'exactly the same confirmations' in txt and 'too few' not in txt
        expn = [f['n']]
    elif rule == 'chart':
        exp = ('of the top grade' if grade == 'A+' else 'of the same grade') in txt and 'across all' not in txt
        expn = [f['n']] + ([nex] if nex else [])
    else:
        exp = 'across all' in txt
        expn = [f['n'], nsg]
    c(loc, 'sample rule', txt, f'rule={rule}, n={f["n"]}, exact-confirmations n={nex}, same-chart-same-grade n={nsg}',
      'sample text vs rule', ) if not (exp and nums == expn) else c(loc, 'sample rule', txt, txt)
    c(loc, 'rose10_within60d_pct', cd['rose10_within60d_pct'], f['reach10'], 'card share')
    c(loc, 'rose10_never_fell25_within60d_pct', cd['rose10_never_fell25_within60d_pct'], f['surv10'], 'card share')
    c(loc, 'beat_normal_move_pct', cd['beat_normal_move_pct'], f['scaled20'], 'card share')
    c(loc, 'rose20_within60d_pct', cd['rose20_within60d_pct'], f['reach20'], 'card share')
    c(loc, 'fell30_within60d_pct', cd['fell30_within60d_pct'], f['t30'], 'card share')
    for fld, k in (('typical_biggest_rise', 'best'), ('typical_dip_before_rise', 'dip'), ('typical_deepest_dip', 'deep')):
        c(loc, fld + '_pct', cd[fld + '_pct'], f[k], 'card median')
        c(loc, fld + '_exact_pct', cd[fld + '_exact_pct'], f[k + 'X'], 'card exact median')
        if rh(f[k + 'X'], 1) != f[k]:
            c(loc, fld + ' 6-place re-rounded', rh(f[k + 'X'], 1), f[k], 'double rounding')
    c(loc, 'before_2022.past_trades', cd['before_2022']['past_trades'], f['nOld'], 'era')
    c(loc, 'before_2022.rose10_never_fell25', cd['before_2022']['rose10_never_fell25_within60d_pct'], f['sOld'], 'era')
    c(loc, 'since_2022.past_trades', cd['since_2022']['past_trades'], f['nNew'], 'era')
    c(loc, 'since_2022.rose10_never_fell25', cd['since_2022']['rose10_never_fell25_within60d_pct'], f['sNew'], 'era')
    c(loc, 'typical_day_first_rose10', cd['typical_day_first_rose10'], f['d10'], 'timing')
    c(loc, 'typical_day_first_rose20', cd['typical_day_first_rose20'], f['d20'], 'timing')
    c(loc, 'typical_day_of_60d_high', cd['typical_day_of_60d_high'], f['dHigh'], 'timing')
    c(loc, 'typical_day_of_deepest_dip', cd['typical_day_of_deepest_dip'], f['dLow'], 'timing')
    fe = cd['from_entry']
    c(loc, 'from_entry.past_trades', fe['past_trades'], f['n'], 'ladder')
    c(loc, 'from_entry.still_rose10_pct', fe['still_rose10_pct'], f['fe'][0], 'ladder')
    c(loc, 'from_entry.went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], f['fe'][1], 'ladder')
    c(loc, 'from_entry.still_rose10_exact_pct', fe['still_rose10_exact_pct'], f['fe'][2], 'ladder')
    for r in cd['if_it_falls_first']:
        th = r['fell_pct']; h, okp, lqp, x6, _ = f['lad'][th]
        c(loc, f'falls {th}% first: past_trades', r['past_trades'], h, 'ladder')
        c(loc, f'falls {th}% first: still_rose10_pct', r['still_rose10_pct'], okp, 'ladder')
        c(loc, f'falls {th}% first: went_on_to_fall25_pct', r['went_on_to_fall25_pct'], lqp, 'ladder')
        c(loc, f'falls {th}% first: still_rose10_exact_pct', r['still_rose10_exact_pct'], x6, 'ladder')
    c(loc, 'label', cd['label'], feed['label'])
    return f

known_now = list(members.values())
LIVE = []
for o in feed['open_signals']:
    a, tfs = o['chart'].split(); tf = int(tfs[:-1])
    x = MINE.get((o['chart'], o['entry_date']))
    if o.get('card') is None or x is None:
        continue
    cd = o['card']
    extra = dict(signal_id=f'{a}-{tfs}-{x["d0"]}', chart=o['chart'], asset=a, timeframe=tfs, low_date=str(x['tdate']), low_day=low_day(a, tf, x['tdate']),
                 confirms_on=str(x['d0']), bars_to_confirm=None, must_close_above=None, price_now=rh(M.day[a]['close'][-1], 2),
                 entry_close=rh(x['entry'], 2))
    f = cmp_card(f'open card {o["signal_id"]}', cd, a, tf, cd['grade'], lensset(cd['confirmations']), known_now, extra)
    LIVE.append((o, x, f))
# example card
exm = members.get(('ETH 2D', str(EXD)))
xc = feed['example_card']
if exm and xc:
    known = [x for x in members.values() if x['d0'] + dt.timedelta(days=60) <= EXD]
    extra = dict(signal_id='ETH-2D-2024-09-22', chart='ETH 2D', asset='ETH', timeframe='2D', low_date=str(exm['tdate']), low_day=low_day('ETH', 2, exm['tdate']),
                 confirms_on=str(EXD), bars_to_confirm=None, must_close_above=None, price_now=None, entry_close=rh(exm['entry'], 2), example=True)
    c('example_card', 'grade (ledger row)', xc['grade'], exm['grade'], 'example grade vs ledger')
    c('example_card', 'confirmations (ledger row lenses)', ','.join(sorted(lensset(xc['confirmations']))), ','.join(sorted(ledlens(exm))), 'example lenses vs ledger')
    EXF = cmp_card('example_card', xc, 'ETH', 2, xc['grade'], lensset(xc['confirmations']), known, extra)
# forming cards
def forming(a, tf):
    b = M.chart(a, tf); Cc = b['close']; n = len(Cc); ct = L.rsi(Cc)
    for back in (1, 2, 3):
        ti = n - 1 - back; v = ct[ti]
        if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)):
            continue
        if any(ct[j] <= v for j in range(ti + 1, n)):
            continue
        return ti, back, ct
    return None
def kill(Cc, ti, ct, need):
    if need == 0:
        base = Cc[:-1]
    elif need == 1:
        base = Cc[:]
    else:
        return None
    # Wilder state after base
    n = 14; g = l = 0.0
    for i in range(1, n + 1):
        ch = base[i] - base[i - 1]; g += max(ch, 0); l += max(-ch, 0)
    ag, al = g / n, l / n
    for i in range(n + 1, len(base)):
        ch = base[i] - base[i - 1]
        ag = (ag * (n - 1) + max(ch, 0)) / n; al = (al * (n - 1) + max(-ch, 0)) / n
    T = ct[ti]; last = base[-1]; r = T / (100 - T)
    # case down: mid <= last
    ag1 = ag * 13 / 14; al1 = ag1 / r; mid = last - (14 * al1 - 13 * al)
    if mid <= last:
        return mid
    al1 = al * 13 / 14; ag1 = al1 * r; return last + 14 * ag1 - 13 * ag
FORM = []
for cd in feed['cards']:
    a, tfs = cd['chart'].split(); tf = int(tfs[:-1])
    fr = forming(a, tf)
    if fr is None:
        c(f'forming card {cd["signal_id"]}', 'forming low exists', 'yes', 'no', 'forming detection'); continue
    ti, back, ct = fr; b = M.chart(a, tf); need = 3 - back
    # confirmation bar: need bars after the open bar
    od = b['date'][-1]
    for _ in range(need):
        od = L.bar_close_date(tf, od) + dt.timedelta(days=1)
    conf = L.bar_close_date(tf, od)
    k = kill(b['close'], ti, ct, need)
    extra = dict(signal_id=f'{a}-{tfs}-{conf}', chart=cd['chart'], asset=a, timeframe=tfs, low_date=str(b['date'][ti]),
                 low_day=low_day(a, tf, b['date'][ti]), confirms_on=str(conf), bars_to_confirm=need,
                 must_close_above=rh(k, 2) if k is not None else None, price_now=rh(M.day[a]['close'][-1], 2), entry_close=None)
    f = cmp_card(f'forming card {cd["signal_id"]}', cd, a, tf, cd['grade'], lensset(cd['confirmations']), known_now, extra)
    FORM.append((cd, f, k))
c('feed', 'forming cards count', len(feed['cards']), len(FORM))

# ------------------------------------------------------------------ 6. open signals
myopen = sorted([x for x in MINE.values() if x['tf'] in (1, 2, 3, 5) and 0 <= (today - x['d0']).days <= 60], key=lambda x: (str(x['d0']), x['ch']))
fo = {(o['chart'], o['entry_date']): o for o in feed['open_signals']}
c('open_signals', 'count', len(feed['open_signals']), len(myopen), 'open list')
c('open_signals', 'ids (order)', ' '.join(o['signal_id'] for o in feed['open_signals']), ' '.join(f"{x['a']}-{x['tf']}D-{x['d0']}" for x in myopen), 'open list')
OPENF = {lo: f for lo, (cd, f, *_) in CARDS.items()}
for x in myopen:
    o = fo.get((x['ch'], str(x['d0'])))
    loc = f'open_signals {x["ch"]} {x["d0"]}'
    if o is None:
        c(loc, 'present', 'absent', 'present', 'open list'); continue
    a = x['a']; dd = M.day[a]; e = x['entry']; i0 = M.pos[a][x['d0']]
    win = [k for k in range(i0 + 1, len(dd['date'])) if dd['date'][k] < today and (dd['date'][k] - x['d0']).days <= 60]
    def mark(m):
        ks = [k for k in win if (dd['date'][k] - x['d0']).days == m]
        return rh((dd['close'][ks[0]] / e - 1) * 100, 1) if ks else None
    c(loc, 'signal_id', o['signal_id'], f"{a}-{x['tf']}D-{x['d0']}")
    c(loc, 'entry_close', o['entry_close'], rh(e, 2), 'entry')
    c(loc, 'tags', o['tags'], M.tags(x), 'tags')
    c(loc, 'days_elapsed', o['days_elapsed'], (today - x['d0']).days, 'days')
    c(loc, 'day10_pct', o['day10_pct'], mark(10), 'day mark')
    c(loc, 'day30_pct', o['day30_pct'], mark(30), 'day mark')
    c(loc, 'day60_pct', o['day60_pct'], mark(60), 'day mark')
    c(loc, 'best_so_far_pct', o['best_so_far_pct'], rh((max(dd['high'][k] for k in win) / e - 1) * 100, 1) if win else None, 'best so far')
    c(loc, 'worst_so_far_pct', o['worst_so_far_pct'], rh((min(dd['low'][k] for k in win) / e - 1) * 100, 1) if win else None, 'worst so far')
    if x['tf'] in (1, 2, 3, 5):
        f = OPENF.get(f'open card {o["signal_id"]}')
        if f is None:
            c(loc, 'card', 'none', 'expected', 'open card'); continue
        lvl = f['edge']
        if lvl == 0:
            status = 'lost'
        elif lvl is None:
            status = 'intact'
        else:
            status = 'intact'
            for k in win:
                if dd['low'][k] <= e * (1 + lvl / 100): status = 'lost'; break
                if dd['high'][k] >= e * 1.10: break
        c(loc, 'edge_level_pct', o['edge_level_pct'], lvl, 'edge level')
        c(loc, 'edge_status', o['edge_status'], status, 'edge status')
    c(loc, 'label', o['label'], feed['label'])

# top level
gate_today = M.gate(today)
c('feed', 'market_regime', feed['market_regime'], 'Bullish' if gate_today else 'Bearish', 'gate today')
c('feed', 'scored_as_of', feed['scored_as_of'], str(today))
pickle.dump(dict(GS=GS, MISS=MISS, EXMISS=eo, CARDS={k: (v[1], v[2], v[3], v[4]) for k, v in CARDS.items()}, myfade=myfade, FADE_INFO=FADE_INFO,
                 open=[(x['ch'], str(x['d0'])) for x in myopen], members={k: dict(m=x['m'], grade=x['grade'], entry=x['entry'], d0=x['d0'], a=x['a']) for k, x in members.items()},
                 FORM=[(cd['signal_id'], k) for cd, f, k in FORM]),
            open(f'{SN}_mine.pkl', 'wb'))
K.save(f'checks_data_{SN}.csv')
bad = [r for r in K.ROWS if r['ok'] != 'yes']
print(SN, 'checks', len(K.ROWS), 'disagreements', len(bad))
for r in bad[:80]:
    print(' ', r['location'], '|', r['label'], '| shown', r['shown'], '| mine', r['yours'], '|', r['cause'])
print('tier', keep, 'fade pool', len(fpool))
import collections
print('fade pool by year', sorted(collections.Counter(p['s']['d0'].year for p in fpool).items()),
      'outcome closed before 2026-01-01:', sum(p['s']['d0'] + dt.timedelta(days=60) < dt.date(2026, 1, 1) for p in fpool), 'of', len(fpool))
