"""Audit #10: recompute every feed / ledger figure for one frozen state, from raw candles, with own code.

  python3 audit_state.py <state_dir> <label> <now_iso>

Writes checks_<label>.csv (location,label,shown,yours,ok,cause) and mine_<label>.json (values the page check uses).
"""
import csv, json, os, sys, datetime as dt, math, statistics
from decimal import Decimal as Dec
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib as L

STATE, LABEL, NOW = sys.argv[1], sys.argv[2], sys.argv[3]
now = dt.datetime.fromisoformat(NOW.replace('Z', '+00:00'))
TODAY = now.date()
sys.path.insert(0, STATE)
import regimes as RG          # gate only
GATE = RG.rsi_regime(os.path.join(STATE, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)

CHECKS = []


def norm(v):
    if v is None or v == '': return None
    if isinstance(v, bool): return v
    if isinstance(v, (int, float, Dec)):
        return Dec(str(v)) if not isinstance(v, Dec) else v
    s = str(v)
    try:
        return Dec(s)
    except Exception:
        return s


def chk(loc, label, shown, yours, cause=''):
    a, b = norm(shown), norm(yours)
    if isinstance(a, Dec) and isinstance(b, Dec): ok = a == b
    else: ok = a == b
    CHECKS.append(dict(state=LABEL, location=loc, label=label, shown='' if shown is None else shown,
                       yours='' if yours is None else (str(yours) if not isinstance(yours, bool) else yours), ok=ok, cause='' if ok else cause))
    return ok


def fr_round(fr, nd=0):
    """half away from zero on an exact Fraction"""
    return L.rhalf(Dec(fr.numerator) / Dec(fr.denominator), nd)


def pctr(k, n, nd=0):
    return fr_round(Fr(100 * k, n), nd)


# ---------------------------------------------------------------- data
ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D'); GRADED = ('1D', '2D', '3D', '5D')
DAILY, RAWD, BARS, CLAMPS = {}, {}, {}, []
for a in ASSETS:
    raw, _ = L.load(os.path.join(STATE, 'data', f'{a}_1D.csv'), clamp=False); RAWD[a] = raw
    d, cl = L.load(os.path.join(STATE, 'data', f'{a}_1D.csv')); CLAMPS += [(a, '1D') + x for x in cl]
    DAILY[a] = L.Daily(d, TODAY)
    chk(f'data {a} 1D', 'last daily bar is today (open)', str(d[-1]['date']), str(TODAY), 'data not current')
    for tf in TFS:
        if tf == '1D': BARS[(a, tf)] = d; continue
        rb, _ = L.load(os.path.join(STATE, 'data', f'{a}_{tf}.csv'), clamp=False)
        mine = L.rebucket(raw, int(tf[:-1]))
        bad = sum(1 for x, y in zip(rb, mine) if (x['date'], x['o'], x['h'], x['l'], x['c']) != (y['date'], y['o'], y['h'], y['l'], y['c'])) + abs(len(rb) - len(mine))
        chk(f'data {a} {tf}', 'bars equal 1D re-bucketed by calendar year', bad, 0, 'chart bars differ from bucketed daily bars')
        b, cl = L.load(os.path.join(STATE, 'data', f'{a}_{tf}.csv')); CLAMPS += [(a, tf) + x for x in cl]
        BARS[(a, tf)] = b

# ---------------------------------------------------------------- signals
SIG = {}       # (a, tf) -> list of signal dicts (gated, conf bar closed or not)
PIV = {}
for a in ASSETS:
    for tf in TFS:
        b = BARS[(a, tf)]; tfd = int(tf[:-1])
        pv, ct, K = L.pivots(b); PIV[(a, tf)] = (pv, ct, K)
        out = []
        for p in pv:
            if p['ei'] >= len(b): continue
            tdate = b[p['ti']]['date']
            if not GATE(tdate): continue
            cb = b[p['ei']]
            d0 = L.bucket_span(cb['date'], tfd)[1] if tfd > 1 else cb['date']
            closed = d0 < TODAY
            s = dict(p, a=a, tf=tf, chart=f'{a} {tf}', tdate=tdate, d0=d0, entry=cb['c'], closed=closed, tags=L.tagstr(p),
                     tlow=b[p['ti']]['l'])
            if closed:
                dd = DAILY[a]
                if d0 not in dd.pos or dd.b[dd.pos[d0]]['c'] != cb['c']:
                    chk(f'signal {a} {tf} {d0}', 'confirmation close equals the daily close on the entry date', str(cb['c']),
                        str(dd.b[dd.pos[d0]]['c']) if d0 in dd.pos else 'missing', 'chart close != daily close')
                s['m'] = dd.measure(d0, cb['c'])
            out.append(s)
        SIG[(a, tf)] = out

# ---------------------------------------------------------------- vol ratio (scaled20)
VOL = {}
for a in ASSETS:
    bs = RAWD[a]; c = [float(x['c']) for x in bs]
    lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
    v = {bs[i]['date']: statistics.pstdev(lr[i - 364:i + 1]) for i in range(365, len(c))}
    med = statistics.median(x for k, x in v.items() if k.year <= 2021)
    VOL[a] = (v, med)


def scaled(a, d0, up):
    v, med = VOL[a]
    if d0 not in v: return None
    return float(up) >= 20 * (v[d0] / med)


# ---------------------------------------------------------------- funding membership (ETH)
def fund_tables(a):
    p = os.path.join(STATE, 'data', 'derivs', f'{a}_funding_daily.csv')
    any_, mean_ = {}, {}
    for r in csv.DictReader(open(p)):
        d = dt.date.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): any_[d] = float(v)
        if r.get('funding_mean') not in ('', None): mean_[d] = float(r['funding_mean'])
    return any_, mean_


FA, FM = fund_tables('ETH')


def eth_member(d0):
    if d0 not in FA: return False
    back = [FA.get(d0 - dt.timedelta(days=k)) for k in range(1, 91)]
    if sum(x is not None for x in back) < 60: return False
    w7 = [d0 - dt.timedelta(days=k) for k in range(7)]; w7b = [d0 - dt.timedelta(days=14 + k) for k in range(7)]
    return sum(x in FM for x in w7) >= 5 and sum(x in FM for x in w7b) >= 5


# ---------------------------------------------------------------- ledger
LED = list(csv.DictReader(open(os.path.join(STATE, 'datasets', 'ledger.csv'))))
LKEY = {(r['chart'], r['entry']): r for r in LED}
MYLED = {}
for (a, tf), lst in SIG.items():
    if tf not in GRADED: continue
    for s in lst:
        if not s['closed'] or not s.get('m'): continue
        if a == 'ETH' and not eth_member(s['d0']): continue
        MYLED[(s['chart'], str(s['d0']))] = s
for k in sorted(set(LKEY) | set(MYLED), key=lambda x: (x[1], x[0])):
    chk(f'ledger {k[0]} {k[1]}', 'membership (in ledger)', k in LKEY, k in MYLED, 'membership')

# my grade records (ledger membership, grade as given)
GR = {}
def grade_rec(rows):
    n = len(rows)
    if not n: return None
    dd = L.median([s['m']['dd'] for s in rows])
    return dict(n=n, r10=pctr(sum(s['m']['r10'] for s in rows), n), s10=pctr(sum(s['m']['surv10'] for s in rows), n),
                r20=pctr(sum(s['m']['r20'] for s in rows), n), t30=pctr(sum(s['m']['t30'] for s in rows), n),
                med=L.rhalf(dd, 1), sample=f"{min(s['d0'] for s in rows)} to {max(s['d0'] for s in rows)}")

for k, r in LKEY.items():
    if k in MYLED: MYLED[k]['grade'] = r['grade']; MYLED[k]['lenses'] = r['lenses']
for a in ASSETS:
    for g in ('A+', 'A', 'B', 'C'):
        GR[(a, g)] = grade_rec([s for s in MYLED.values() if s['a'] == a and s.get('grade') == g])

# day odds
HIST = sorted(MYLED.values(), key=lambda s: s['d0'])
def day_odds(s):
    prior = [h for h in HIST if h['a'] == s['a'] and h['d0'] + dt.timedelta(days=60) <= s['d0']]
    G = [h for h in prior if h.get('grade') == s['grade']]
    if len(G) < 10 or not prior: return dict(dayReach10='', dayReach20='', dayReach30='', dayTouched30='', dayN=len(G), daySurv10='', dayScaled20='')
    def rate(fn):
        base = Fr(sum(1 for h in prior if fn(h)), len(prior))
        return fr_round((sum(1 for h in G if fn(h)) + 5 * base) / (len(G) + 5) * 100)
    return dict(dayReach10=rate(lambda h: h['m']['r10']), dayReach20=rate(lambda h: h['m']['r20']), dayReach30=rate(lambda h: h['m']['r30']),
                dayTouched30=rate(lambda h: h['m']['t30']), dayN=len(G), daySurv10=rate(lambda h: h['m']['surv10']),
                dayScaled20=rate_sc(prior, G))


def rate_sc(prior, G):
    # beat a normal move: a signal with no 365-day volatility at entry has no "normal move", so it is left
    # out (as the card's beat_normal_move_pct does), not counted as a miss
    sc = lambda h: scaled(h['a'], h['d0'], h['m']['up'])
    P2 = [h for h in prior if sc(h) is not None]; G2 = [h for h in G if sc(h) is not None]
    if not P2 or not G2: return ''
    base = Fr(sum(1 for h in P2 if sc(h)), len(P2))
    return fr_round((sum(1 for h in G2 if sc(h)) + 5 * base) / (len(G2) + 5) * 100)

yn = lambda b: 'yes' if b else 'no'
for k, r in LKEY.items():
    s = MYLED.get(k)
    if not s: continue
    m = s['m']; loc = f'ledger {k[0]} {k[1]}'
    chk(loc, 'asset', r['asset'], s['a'])
    chk(loc, 'low (trough bar open date)', r['low'], str(s['tdate']))
    chk(loc, 'entryPrice', r['entryPrice'], L.rhalf(s['entry'], 2))
    chk(loc, 'tags', r['tags'], s['tags'], 'tag')
    chk(loc, 'reached20', r['reached20'], yn(m['r20']))
    chk(loc, 'touched30', r['touched30'], yn(m['t30']))
    chk(loc, 'bestMove', r['bestMove'], L.r6(m['up']))
    chk(loc, 'maxDrawdown', r['maxDrawdown'], L.r6(m['dd']))
    chk(loc, 'dipBeforeHigh', r['dipBeforeHigh'], L.r6(m['ddpk']))
    chk(loc, 'return60d', r['return60d'], L.r6(m['ret']))
    chk(loc, 'daysToHigh', r['daysToHigh'], m['dpk'])
    chk(loc, 'year', r['year'], s['d0'].year)
    chk(loc, 'reached10', r['reached10'], yn(m['r10']))
    chk(loc, 'reached15', r['reached15'], yn(m['r15']))
    chk(loc, 'surv10', r['surv10'], yn(m['surv10']))
    sc = scaled(s['a'], s['d0'], m['up'])
    chk(loc, 'scaled20', r['scaled20'], '' if sc is None else yn(sc))
    gr = GR.get((s['a'], s['grade']))
    chk(loc, 'gradeReach20', r['gradeReach20'], gr['r20'] if gr else '')
    chk(loc, 'gradeTouched30', r['gradeTouched30'], gr['t30'] if gr else '')
    chk(loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], gr['med'] if gr else '')
    od = day_odds(s)
    for c in ('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10'):
        chk(loc, c, r[c], od[c])
    chk(loc, 'dayScaled20', r['dayScaled20'], od['dayScaled20'] if r['dayN'] != '' and int(r['dayN']) >= 10 and od['dayReach10'] != '' else '',
        'undefined "normal move" (no 365-day volatility, BTC before 2017) counted as a miss; the card leaves such signals out')
    if m['gaps']:
        chk(loc, 'daily bars in the 60-day window', 60 - m['gaps'], 60, 'gap in daily data')

# ---------------------------------------------------------------- feed
FEED = json.load(open(os.path.join(STATE, 'feed', 'ctzb_feed.json')))
ALIAS_OK = []
def aliases(o, path):
    if isinstance(o, dict):
        if 'past_trades' in o: chk(path, 'past_signals == past_trades', o.get('past_signals'), o['past_trades'], 'alias')
        if 'trades_a_year' in o: chk(path, 'signals_a_year == trades_a_year', o.get('signals_a_year'), o['trades_a_year'], 'alias')
        for k, v in o.items(): aliases(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o): aliases(v, f'{path}[{i}]')
aliases(FEED, 'feed')
LABELTXT = 'Computed signal, not a fill. No trade was taken. Entry quality only: the data has no exits, so this is not a strategy return or a track record.'
for nm, lst in (('cards', FEED['cards']), ('prints', FEED['prints']), ('open_signals', FEED['open_signals']), ('open_signals.card', [o['card'] for o in FEED['open_signals']]),
                ('grade_odds', FEED['grade_odds']), ('if_it_misses', FEED['if_it_misses']), ('past_paths', FEED['past_paths']),
                ('example_card', [FEED['example_card']]), ('example_if_it_misses', [FEED['example_if_it_misses']]), ('example_past_paths', [FEED['example_past_paths']]), ('odds_fade', [FEED['odds_fade']])):
    chk(f'feed {nm}', 'every record carries the computed-signal label', sum(1 for x in lst if x.get('label') == LABELTXT), len(lst), 'label missing')

# grade_odds
for g in FEED['grade_odds']:
    loc = f"feed grade_odds {g['asset']} {g['grade']}"
    if g['grade'] in ('A+', 'A', 'B', 'C'):
        gr = GR[(g['asset'], g['grade'])]
    elif g['grade'] in ('diamond or prime dot', 'no diamond or prime dot'):
        want = g['grade'] == 'diamond or prime dot'
        gr = grade_rec([s for s in MYLED.values() if s['a'] == 'ETH' and bool(s['prime'] or s['dis']) == want])
    else:
        continue   # HTF divergence rows: lens logic, out of scope
    chk(loc, 'past_trades', g['past_trades'], gr['n'])
    chk(loc, 'rose10_within60d_pct', g['rose10_within60d_pct'], gr['r10'])
    chk(loc, 'rose10_never_fell25_within60d_pct', g['rose10_never_fell25_within60d_pct'], gr['s10'])
    chk(loc, 'rose20_within60d_pct', g['rose20_within60d_pct'], gr['r20'])
    chk(loc, 'median_deepest_dip_pct', g['median_deepest_dip_pct'], gr['med'])
    chk(loc, 'sample', g['sample'], gr['sample'])


# if it misses (from 6-place stored values)
def miss_stats(rows):
    m = [s for s in rows if not s['m']['r10']]
    best = [L.r6(s['m']['up']) for s in m]
    out = dict(signals=len(rows), misses=len(m), up_first=sum(b > 0 for b in best))
    if m:
        out.update(median_peak_pct=L.rhalf(L.median(best), 1), mean_peak_pct=L.rhalf(sum(best) / len(best), 1),
                   peaked_5_or_more=sum(b >= 5 for b in best), peaked_10_or_more=sum(b >= 10 for b in best),
                   median_worst_drop_pct=L.rhalf(L.median([L.r6(s['m']['dd']) for s in m]), 1),
                   median_day60_pct=L.rhalf(L.median([L.r6(s['m']['ret']) for s in m]), 1))
    return out

MISS = {}
for x in FEED['if_it_misses']:
    rows = [s for s in MYLED.values() if s['a'] == x['asset'] and s.get('grade') == x['grade']]
    ms = miss_stats(rows); MISS[(x['asset'], x['grade'])] = ms
    for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'mean_peak_pct', 'peaked_5_or_more', 'peaked_10_or_more', 'median_worst_drop_pct', 'median_day60_pct'):
        chk(f"feed if_it_misses {x['asset']} {x['grade']}", k, x.get(k), ms.get(k))
    chk(f"feed if_it_misses {x['asset']} {x['grade']}", 'miss_rule', x['miss_rule'], 'did not rise 10% within 60 days')
have = {(x['asset'], x['grade']) for x in FEED['if_it_misses']}
for a in ASSETS:
    for g in ('A+', 'A', 'B', 'C'):
        if GR[(a, g)] and (a, g) not in have: chk('feed if_it_misses', f'row {a} {g} present', 'missing', 'present', 'missing row')
EXD = dt.date(2024, 9, 22)
ex_rows = [s for s in MYLED.values() if s['a'] == 'ETH' and s.get('grade') == 'A+' and s['d0'] + dt.timedelta(days=60) <= EXD]
EXMISS = miss_stats(ex_rows)
x = FEED['example_if_it_misses']
for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
    chk('feed example_if_it_misses', k, x.get(k), EXMISS.get(k))
for k in ('mean_peak_pct', 'peaked_5_or_more', 'peaked_10_or_more'):
    if k in x: chk('feed example_if_it_misses', k, x.get(k), EXMISS.get(k))

# ---------------------------------------------------------------- past paths
def paths(rows):
    P = []
    for s in rows:
        dd = DAILY[s['a']]; p = [Dec(0)]
        for k in range(1, 61):
            d = s['d0'] + dt.timedelta(days=k)
            if d not in dd.pos or d >= TODAY: break
            p.append((dd.b[dd.pos[d]]['c'] / s['entry'] - 1) * 100)
        if len(p) == 61: P.append(p)
    days = [dict(day=k, q25_pct=L.rhalf(L.quant([p[k] for p in P], 0.25), 1), median_pct=L.rhalf(L.quant([p[k] for p in P], 0.5), 1),
                 q75_pct=L.rhalf(L.quant([p[k] for p in P], 0.75), 1)) for k in range(61)] if P else []
    return len(P), days

PATHS = {}
for pp in FEED['past_paths']:
    n, days = paths([s for s in MYLED.values() if s['a'] == pp['asset'] and s.get('grade') == 'A+'])
    PATHS[pp['asset']] = (n, days)
    loc = f"feed past_paths {pp['asset']}"
    chk(loc, 'signals', pp['signals'], n)
    chk(loc, 'day rows', len(pp['days']), len(days))
    for x, y in zip(pp['days'], days):
        for k in ('q25_pct', 'median_pct', 'q75_pct'):
            chk(loc, f"day {x['day']} {k}", x[k], y[k])
n, days = paths(ex_rows); PATHS['example'] = (n, days)
pe = FEED['example_past_paths']
chk('feed example_past_paths', 'signals', pe['signals'], n)
for x, y in zip(pe['days'], days):
    for k in ('q25_pct', 'median_pct', 'q75_pct'):
        chk('feed example_past_paths', f"day {x['day']} {k}", x[k], y[k])

# ---------------------------------------------------------------- odds fade (ETH tier)
def zser(ct):
    out, z = [], None
    for v in ct:
        if v is None: out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v)); out.append(z)
    return out

TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
TIERROWS = []; FADESIG = []
for tf in TFS:
    b = BARS[('ETH', tf)]; pv, ct, K = PIV[('ETH', tf)]; zm = zser(ct); tfd = int(tf[:-1])
    for p in pv:
        if p['ei'] >= len(b) or not GATE(b[p['ti']]['date']): continue
        tg = {p['bk'], 'any trough'}
        if p['dis']: tg |= {'diamond', 'filled' if p['strong'] else 'hollow'}
        if p['prime']: tg.add('prime dot')
        if p['dis'] and p['prime']: tg.add('diamond+dot')
        if p['bk'] == 'B' and p['ct'] < 60 and zm[p['ti']] is not None and zm[p['ti']] >= 50: tg.add('zone-exit B')
        i = p['ei']; Dd = b[i]['date']; end = Dd + dt.timedelta(days=60)
        rec = dict(chart=f'ETH {tf}', tags=tg, d=Dd, p=p, tfd=tfd)
        if b[-1]['date'] >= end:
            js = [j for j in range(i + 1, len(b)) if b[j]['date'] <= end]
            if js:
                rec['win'] = b[js[-1]]['c'] > b[i]['c']
                TIERROWS.append(rec)
        FADESIG.append(rec)
UPTO = dt.date(2026, 1, 1)
KEEP = []
for tf in TFS:
    for t in TAGS:
        sub = [r for r in TIERROWS if r['chart'] == f'ETH {tf}' and t in r['tags'] and r['d'] + dt.timedelta(days=r['tfd'] - 1 + 60) < UPTO]
        if len(sub) >= 8 and Fr(sum(r['win'] for r in sub), len(sub)) >= Fr(7, 10):
            KEEP.append((f'ETH {tf}', t))
pool_e, pool_h = [], []
dd = DAILY['ETH']
for r in FADESIG:
    if not any(r['chart'] == k[0] and k[1] in r['tags'] for k in KEEP): continue
    tfd = r['tfd']; d0 = L.bucket_span(r['d'], tfd)[1] if tfd > 1 else r['d']
    if d0 not in dd.pos: continue
    e = dd.b[dd.pos[d0]]['c']
    w = [x for x in dd.b[dd.pos[d0] + 1:] if (x['date'] - d0).days <= 60]
    if not w or (w[-1]['date'] - d0).days < 60 or w[-1]['date'] >= TODAY: continue
    first = [x for x in w if (x['date'] - d0).days <= 10]; after = [x for x in w if (x['date'] - d0).days > 10]
    lo = min(x['l'] for x in first); hi = max(x['h'] for x in after)
    pool_e.append(dict(dip=(lo / e - 1) * 100, r10=hi >= e * Dec('1.1'), r20=hi >= e * Dec('1.2')))
    d10 = [x for x in w if (x['date'] - d0).days == 10]
    if d10: pool_h.append(dict(green=d10[0]['c'] >= e, r10=hi >= e * Dec('1.1'), r20=hi >= e * Dec('1.2')))
BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
MYFADE = {'early_dip': [], 'day10': []}
for hi_, lo_, lab in BANDS:
    g = [p for p in pool_e if Dec(lo_) < p['dip'] <= Dec(hi_)]
    if len(g) < 5: continue
    MYFADE['early_dip'].append(dict(band=lab, n=len(g), r10=pctr(sum(p['r10'] for p in g), len(g)), r20=pctr(sum(p['r20'] for p in g), len(g)),
                                    x10=Fr(100 * sum(p['r10'] for p in g), len(g))))
for lab, gr_ in (('green on day 10', True), ('red on day 10', False)):
    g = [p for p in pool_h if p['green'] == gr_]
    if len(g) < 5: continue
    MYFADE['day10'].append(dict(band=lab, n=len(g), r10=pctr(sum(p['r10'] for p in g), len(g)), r20=pctr(sum(p['r20'] for p in g), len(g)),
                                x10=Fr(100 * sum(p['r10'] for p in g), len(g))))
of = FEED['odds_fade']
chk('feed odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70)
chk('feed odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)')
for kind, key in (('early_dip', 'band'), ('day10', 'check')):
    chk('feed odds_fade', f'{kind} row count', len(of[kind]), len(MYFADE[kind]))
    for x, y in zip(of[kind], MYFADE[kind]):
        loc = f"feed odds_fade {kind} {y['band']}"
        chk(loc, key, x[key], y['band'])
        chk(loc, 'past_trades', x['past_trades'], y['n'])
        chk(loc, 'rose10_after_day10_pct', x['rose10_after_day10_pct'], y['r10'])
        chk(loc, 'rose20_after_day10_pct', x['rose20_after_day10_pct'], y['r20'])
        chk(loc, 'rose10_within60d_pct (alias)', x['rose10_within60d_pct'], y['r10'])
        chk(loc, 'rose20_within60d_pct (alias)', x['rose20_within60d_pct'], y['r20'])
        chk(loc, 'edge (exact share vs 70)', x['edge'], 'intact' if y['x10'] >= 70 else 'gone')

# ---------------------------------------------------------------- cards
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
RPLAIN = {v: k for k, v in PLAIN.items()}


def lensset(s):
    return frozenset(x for x in s.split(' + ') if x and x != '-')


def sample_for(card, pool, example=False):
    a, tf, g = card['asset'], card['timeframe'], card['grade']
    have = frozenset() if card['confirmations'] == 'none' else frozenset(RPLAIN[x] for x in card['confirmations'].split('; '))
    Cf = [s for s in pool if s['chart'] == f'{a} {tf}']
    ex = [s for s in Cf if lensset(s['lenses']) == have]
    sg = [s for s in Cf if s['grade'] == g]
    ag = [s for s in pool if s['a'] == a and s['grade'] == g]
    tail = ' whose 60 days had closed by then' if example else ''
    if len(ex) >= 15:
        return ex, (f'all {len(ex)} {a} {tf} signals with exactly the same confirmations{tail}' if example else f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations')
    if len(sg) >= 15:
        why = 'none' if not ex else f'only {len(ex)}'
        return sg, (f'all {len(sg)} {a} {tf} signals graded {g}{tail} ({why} had exactly the same confirmations, too few to use)' if example
                    else f'all {len(sg)} past {a} {tf} signals graded {g} ({why} had exactly the same confirmations, too few to use)')
    return ag, (f'all {len(ag)} grade {g} signals across all {a} charts{tail} ({a} {tf} alone had only {len(sg)}, too few to use)' if example
                else f'all {len(ag)} past grade {g} signals across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)')


def card_figures(G):
    n = len(G); M = [s['m'] for s in G]
    f = dict(n=n)
    f['surv10'] = pctr(sum(m['surv10'] for m in M), n)
    sc = [scaled(s['a'], s['d0'], s['m']['up']) for s in G]; sc = [x for x in sc if x is not None]
    f['scaled20'] = pctr(sum(sc), len(sc)) if sc else None
    f['reach20'] = pctr(sum(m['r20'] for m in M), n); f['reach10'] = pctr(sum(m['r10'] for m in M), n)
    f['touched30'] = pctr(sum(m['t30'] for m in M), n)
    for k, src in (('best', 'up'), ('dipb', 'ddpk'), ('deep', 'dd')):
        full = L.median([m[src] for m in M]); f[k + 'X'] = L.r6(full); f[k] = L.rhalf(f[k + 'X'], 1); f[k + 'F'] = L.rhalf(full, 1)
    old = [s for s in G if s['d0'] < dt.date(2022, 1, 1)]; new = [s for s in G if s['d0'] >= dt.date(2022, 1, 1)]
    f['nOld'], f['nNew'] = len(old), len(new)
    f['sOld'] = pctr(sum(s['m']['surv10'] for s in old), len(old)) if old else None
    f['sNew'] = pctr(sum(s['m']['surv10'] for s in new), len(new)) if new else None
    ok = sum(m['fe'] == 'ok' for m in M); lq = sum(m['fe'] == 'liq' for m in M)
    f['l0ok'], f['l0liq'], f['l0x'] = pctr(ok, n), pctr(lq, n), fr_round(Fr(100 * ok, n), 6)
    f['l0xF'] = Fr(100 * ok, n)
    for th in (5, 10, 15, 20):
        hit = [m['lad'][th] for m in M if m['lad'][th] is not None]
        f[f'l{th}n'] = len(hit)
        f[f'l{th}ok'] = pctr(sum(x == 'ok' for x in hit), len(hit)) if hit else None
        f[f'l{th}liq'] = pctr(sum(x == 'liq' for x in hit), len(hit)) if hit else None
        f[f'l{th}x'] = fr_round(Fr(100 * sum(x == 'ok' for x in hit), len(hit)), 6) if hit else None
        f[f'l{th}xF'] = Fr(100 * sum(x == 'ok' for x in hit), len(hit)) if hit else None
    md = lambda xs: L.rhalf(Dec(str(L.median(xs))), 0) if xs else None
    f['t10'] = md([m['d10'] for m in M if m['d10'] is not None]); f['t20'] = md([m['d20'] for m in M if m['d20'] is not None])
    f['tH'] = md([m['dpk'] for m in M]); f['tL'] = md([m['ddday'] for m in M])
    # edge level: 0 if from-entry exact share < 70, else first fall whose exact share < 70, else None
    if f['l0xF'] < 70: f['edge'] = 0
    else: f['edge'] = next((-th for th in (5, 10, 15, 20) if f[f'l{th}xF'] is not None and f[f'l{th}xF'] < 70), None)
    return f


def check_card(loc, c, G, basis, f):
    chk(loc, 'sample', c['sample'], basis, 'sample text / count')
    chk(loc, 'past_trades', c['past_trades'], f['n'])
    chk(loc, 'rose10_within60d_pct', c['rose10_within60d_pct'], f['reach10'])
    chk(loc, 'rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], f['surv10'])
    chk(loc, 'beat_normal_move_pct', c['beat_normal_move_pct'], f['scaled20'])
    chk(loc, 'rose20_within60d_pct', c['rose20_within60d_pct'], f['reach20'])
    chk(loc, 'fell30_within60d_pct', c['fell30_within60d_pct'], f['touched30'])
    for k, kk in (('typical_biggest_rise', 'best'), ('typical_dip_before_rise', 'dipb'), ('typical_deepest_dip', 'deep')):
        chk(loc, f'{k}_exact_pct', c[f'{k}_exact_pct'], f[kk + 'X'])
        chk(loc, f'{k}_pct (from 6-place exact)', c[f'{k}_pct'], f[kk], 'double rounding')
        if f[kk] != f[kk + 'F']: chk(loc, f'{k}_pct full-precision vs 6-place rounding', f[kk + 'F'], f[kk], 'double rounding')
    chk(loc, 'before_2022.past_trades', c['before_2022']['past_trades'], f['nOld'])
    chk(loc, 'before_2022.rose10_never_fell25', c['before_2022']['rose10_never_fell25_within60d_pct'], f['sOld'])
    chk(loc, 'since_2022.past_trades', c['since_2022']['past_trades'], f['nNew'])
    chk(loc, 'since_2022.rose10_never_fell25', c['since_2022']['rose10_never_fell25_within60d_pct'], f['sNew'])
    chk(loc, 'typical_day_first_rose10', c['typical_day_first_rose10'], f['t10'])
    chk(loc, 'typical_day_first_rose20', c['typical_day_first_rose20'], f['t20'])
    chk(loc, 'typical_day_of_60d_high', c['typical_day_of_60d_high'], f['tH'])
    chk(loc, 'typical_day_of_deepest_dip', c['typical_day_of_deepest_dip'], f['tL'])
    fe = c['from_entry']
    chk(loc, 'from_entry.past_trades', fe['past_trades'], f['n'])
    chk(loc, 'from_entry.still_rose10_pct', fe['still_rose10_pct'], f['l0ok'])
    chk(loc, 'from_entry.went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], f['l0liq'])
    chk(loc, 'from_entry.still_rose10_exact_pct', fe['still_rose10_exact_pct'], f['l0x'])
    for r in c['if_it_falls_first']:
        th = r['fell_pct']
        chk(loc, f'falls {th}% first past_trades', r['past_trades'], f[f'l{th}n'])
        chk(loc, f'falls {th}% first still_rose10_pct', r['still_rose10_pct'], f[f'l{th}ok'])
        chk(loc, f'falls {th}% first went_on_to_fall25_pct', r['went_on_to_fall25_pct'], f[f'l{th}liq'])
        chk(loc, f'falls {th}% first still_rose10_exact_pct', r['still_rose10_exact_pct'], f[f'l{th}x'])
    # edge as the page derives it, on the exact shares in the feed
    xs = [fe['still_rose10_exact_pct']] + [r['still_rose10_exact_pct'] for r in c['if_it_falls_first']]
    shown_edge = 0 if xs[0] is not None and xs[0] < 70 else next((-r['fell_pct'] for r in c['if_it_falls_first'] if r['still_rose10_exact_pct'] is not None and r['still_rose10_exact_pct'] < 70), None)
    chk(loc, 'edge level (first exact share < 70%)', shown_edge, f['edge'])


def low_day(a, tf, topen):
    tfd = int(tf[:-1]); st_, en = L.bucket_span(topen, tfd) if tfd > 1 else (topen, topen)
    dd = DAILY[a]; days = [st_ + dt.timedelta(days=i) for i in range((en - st_).days + 1)]
    cand = [(dd.b[dd.pos[d]]['l'], d) for d in days if d in dd.pos]
    return str(min(cand)[1])


POOL = list(MYLED.values())
MINE = {'cards': {}, 'open': {}, 'example': None, 'misses': {f'{k[0]}|{k[1]}': {kk: (str(v) if isinstance(v, Dec) else v) for kk, v in ms.items()} for k, ms in MISS.items()},
        'exmiss': {kk: (str(v) if isinstance(v, Dec) else v) for kk, v in EXMISS.items()}, 'grades': {}, 'paths': {}, 'today': str(TODAY)}
for (a, g), gr in GR.items():
    if gr: MINE['grades'][f'{a}|{g}'] = {k: (str(v) if isinstance(v, Dec) else v) for k, v in gr.items()}
for k, (n, days) in PATHS.items():
    MINE['paths'][k] = dict(n=n, last={kk: str(v) for kk, v in days[-1].items()} if days else None)


def figs_json(f):
    return {k: (str(v) if isinstance(v, (Dec, Fr)) else v) for k, v in f.items()}


# forming cards
def provisional(b):
    cl = [float(x['c']) for x in b]; ct = L.wilder_rsi(cl); K = L.stoch_k(ct); n = len(b)
    for back in (1, 2, 3):
        ti = n - 1 - back
        v = ct[ti]
        if v is None: continue
        if any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)): continue
        if any(ct[j] < v for j in range(ti + 1, n)): continue
        return dict(ti=ti, need=3 - ((n - 1) - ti), ct=v, k=K[ti]), cl, ct
    return None, cl, ct


def kill_close(cl, ct, ti):
    n = len(cl)
    base = cl[:-1] if n - 1 == ti + 3 else cl if n - 1 == ti + 2 else None
    if base is None: return None
    au, ad = L.rsi_state(base); cp = base[-1]; v = ct[ti]; r = v / (100 - v)
    x = cp + r * ad * 13 - au * 13
    if x < cp:
        x = cp - (au * 13 / r - ad * 13)
    return L.rhalf(x, 2)


myforming = {}
for a in ASSETS:
    for tf in TFS:
        b = BARS[(a, tf)]; p, cl, ct = provisional(b)
        if not p: continue
        tfd = int(tf[:-1])
        conf_open = b[-1]['date']
        for _ in range(p['need']):
            conf_open = (L.bucket_span(conf_open, tfd)[1] + dt.timedelta(days=1)) if tfd > 1 else conf_open + dt.timedelta(days=1)
        d0 = L.bucket_span(conf_open, tfd)[1] if tfd > 1 else conf_open
        myforming[f'{a}-{tf}-{d0}'] = dict(lowday=low_day(a, tf, b[p['ti']]['date']), tlow=str(b[p['ti']]['l']), a=a, tf=tf, ti=p['ti'], need=p['need'], d0=d0, tdate=b[p['ti']]['date'],
                                          kill=kill_close(cl, ct, p['ti']), price=L.rhalf(b[-1]['c'], 2), gate=GATE(b[p['ti']]['date']))
feed_forming = {c['signal_id']: c for c in FEED['cards']}
for sid in sorted(set(myforming) | set(feed_forming)):
    chk(f'feed cards {sid}', 'forming card present', sid in feed_forming, sid in myforming, 'forming set')
for sid, c in feed_forming.items():
    loc = f'feed cards {sid}'; mf = myforming.get(sid)
    if mf:
        chk(loc, 'chart', c['chart'], f"{mf['a']} {mf['tf']}"); chk(loc, 'asset', c['asset'], mf['a']); chk(loc, 'timeframe', c['timeframe'], mf['tf'])
        chk(loc, 'low_date (trough bar open)', c['low_date'], str(mf['tdate']))
        chk(loc, 'low_day', c['low_day'], low_day(mf['a'], mf['tf'], mf['tdate']))
        chk(loc, 'confirms_on', c['confirms_on'], str(mf['d0']))
        chk(loc, 'bars_to_confirm', c['bars_to_confirm'], mf['need'])
        chk(loc, 'must_close_above', c['must_close_above'], mf['kill'])
        chk(loc, 'price_now', c['price_now'], mf['price'])
        chk(loc, 'entry_close', c['entry_close'], None)
        chk(loc, 'regime gate on at the forming trough (definitional a)', True, mf['gate'], 'forming card shown with gate off')
    G, basis = sample_for(c, POOL)
    f = card_figures(G)
    check_card(loc, c, G, basis, f)
    MINE['cards'][sid] = figs_json(f)

# example card
xc = FEED['example_card']
known = [s for s in POOL if s['d0'] + dt.timedelta(days=60) <= EXD]
exs = next((s for s in SIG[('ETH', '2D')] if s['d0'] == EXD), None)
loc = 'feed example_card'
chk(loc, 'signal_id', xc['signal_id'], 'ETH-2D-2024-09-22')
chk(loc, 'low_date (trough bar open)', xc['low_date'], str(exs['tdate']))
chk(loc, 'low_day', xc['low_day'], low_day('ETH', '2D', exs['tdate']))
chk(loc, 'confirms_on', xc['confirms_on'], str(exs['d0']))
chk(loc, 'entry_close', xc['entry_close'], L.rhalf(exs['entry'], 2))
chk(loc, 'price_now', xc['price_now'], None)
for k_, v_ in (('chart', 'ETH 2D'), ('asset', 'ETH'), ('timeframe', '2D'), ('bars_to_confirm', None), ('must_close_above', None), ('example', True)):
    chk(loc, k_, xc[k_], v_)
chk(loc, 'grade (ledger)', xc['grade'], LKEY[('ETH 2D', '2024-09-22')]['grade'])
G, basis = sample_for(xc, known, example=True)
chk(loc, 'sample = only signals whose 60th day closed by 2024-09-22', max(s['d0'] for s in G) + dt.timedelta(days=60) <= EXD, True)
f = card_figures(G); check_card(loc, xc, G, basis, f); MINE['example'] = figs_json(f)
MINE['example']['entry'] = str(exs['entry'])

# open signals
myopen = {}
for a in ASSETS:
    for tf in GRADED:
        for s in SIG[(a, tf)]:
            if s['closed'] and 0 <= (TODAY - s['d0']).days <= 60:
                myopen[f"{a}-{tf}-{s['d0']}"] = s
fo = {o['signal_id']: o for o in FEED['open_signals']}
for sid in sorted(set(myopen) | set(fo)):
    chk(f'feed open_signals {sid}', 'present', sid in fo, sid in myopen, 'open set')
for sid, o in fo.items():
    s = myopen.get(sid)
    if not s: continue
    loc = f'feed open_signals {sid}'; a = s['a']; dd = DAILY[a]; e = s['entry']
    w = dd.window(s['d0'], 60)
    chk(loc, 'chart', o['chart'], s['chart']); chk(loc, 'entry_date', o['entry_date'], str(s['d0']))
    chk(loc, 'entry_close', o['entry_close'], L.rhalf(e, 2)); chk(loc, 'tags', o['tags'], s['tags'], 'tag')
    chk(loc, 'days_elapsed', o['days_elapsed'], (TODAY - s['d0']).days)
    mark = lambda k: next((L.rhalf((x['c'] / e - 1) * 100, 1) for x in w if (x['date'] - s['d0']).days == k), None)
    chk(loc, 'day10_pct', o['day10_pct'], mark(10)); chk(loc, 'day30_pct', o['day30_pct'], mark(30)); chk(loc, 'day60_pct', o['day60_pct'], mark(60))
    chk(loc, 'best_so_far_pct', o['best_so_far_pct'], L.rhalf((max(x['h'] for x in w) / e - 1) * 100, 1) if w else None)
    chk(loc, 'worst_so_far_pct', o['worst_so_far_pct'], L.rhalf((min(x['l'] for x in w) / e - 1) * 100, 1) if w else None)
    c = o['card']
    chk(loc + ' card', 'signal_id', c['signal_id'], sid)
    chk(loc + ' card', 'low_date (trough bar open)', c['low_date'], str(s['tdate']))
    chk(loc + ' card', 'low_day', c['low_day'], low_day(a, s['tf'], s['tdate']))
    chk(loc + ' card', 'confirms_on', c['confirms_on'], str(s['d0']))
    chk(loc + ' card', 'price_now', c['price_now'], L.rhalf(dd.b[-1]['c'], 2))
    chk(loc + ' card', 'entry_close', c['entry_close'], L.rhalf(e, 2))
    chk(loc + ' card', 'grade == open signal grade', c['grade'], o['grade'])
    for k_, v_ in (('chart', s['chart']), ('asset', a), ('timeframe', s['tf']), ('bars_to_confirm', None), ('must_close_above', None)):
        chk(loc + ' card', k_, c[k_], v_)
    G, basis = sample_for(c, POOL)
    f = card_figures(G); check_card(loc + ' card', c, G, basis, f)
    lvl = f['edge']
    if lvl == 0: status = 'lost'
    elif lvl is None: status = 'intact'
    else:
        status = 'intact'
        for x in w:
            if x['l'] <= e * (1 + Dec(lvl) / 100): status = 'lost'; break
            if x['h'] >= e * Dec('1.1'): status = 'intact'; break
    chk(loc, 'edge_level_pct', o['edge_level_pct'], lvl); chk(loc, 'edge_status', o['edge_status'], status)
    MINE['open'][sid] = dict(figs_json(f), status=status, days=(TODAY - s['d0']).days,
                             bsf=str(L.rhalf((max(x['h'] for x in w) / e - 1) * 100, 1)) if w else None,
                             wsf=str(L.rhalf((min(x['l'] for x in w) / e - 1) * 100, 1)) if w else None,
                             d10=str(mark(10)) if mark(10) is not None else None, entry=str(e), entry_date=str(s['d0']),
                             price_now=str(dd.b[-1]['c']), grade=o['grade'])

# top level
chk('feed top', 'market_regime (gate today)', FEED['market_regime'], 'Bullish' if GATE(TODAY) else 'Bearish')
chk('feed top', 'scored_as_of', FEED['scored_as_of'], str(TODAY))

MINE['clamps'] = [str(x) for x in CLAMPS]
MINE['keep'] = KEEP
MINE['fade'] = {k: [dict(band=r['band'], n=r['n'], r10=str(r['r10']), r20=str(r['r20']), x10=str(L.r6(Dec(r['x10'].numerator) / r['x10'].denominator))) for r in v] for k, v in MYFADE.items()}
MINE['ledger_aplus'] = {f'{k[0]}|{k[1]}': dict(best=str(L.r6(s['m']['up'])), dd=str(L.r6(s['m']['dd'])), ret=str(L.r6(s['m']['ret'])),
                                              r10=s['m']['r10'], r20=s['m']['r20'], dpk=s['m']['dpk'], entry=str(s['entry']), a=s['a'])
                        for k, s in MYLED.items() if s.get('grade') == 'A+'}
MINE['forming'] = {k: {kk: (str(vv) if not isinstance(vv, (int, bool)) else vv) for kk, vv in v.items()} for k, v in myforming.items()}
MINE['paths_full'] = {k: [{kk: str(vv) for kk, vv in d.items()} for d in days] for k, (n, days) in PATHS.items()}
exm = exs['m']; w = DAILY['ETH'].window(EXD, 60)
hiK = max(range(len(w)), key=lambda i: (w[i]['h'], -i)); loK = min(range(len(w)), key=lambda i: (w[i]['l'], i))
MINE['example_sig'] = dict(entry=str(exs['entry']), r10=exm['r10'], r20=exm['r20'], hi=str(w[hiK]['h']), hiday=(w[hiK]['date'] - EXD).days,
                           lo=str(w[loK]['l']), loday=(w[loK]['date'] - EXD).days, c10=str(next(x['c'] for x in w if (x['date'] - EXD).days == 10)),
                           c60=str(next(x['c'] for x in w if (x['date'] - EXD).days == 60)), tdate=str(exs['tdate']),
                           closes={(x['date'] - EXD).days: str(x['c']) for x in w})
MINE['gate_today'] = GATE(TODAY)
MINE['last_closed_daily'] = str(max(b['date'] for b in DAILY['ETH'].b if b['date'] < TODAY))
MINE['ledger_aplus_order'] = [f"{s['chart']}|{s['d0']}" for s in sorted(MYLED.values(), key=lambda s: (s['d0'], s['tf'])) if s.get('grade') == 'A+']
json.dump(MINE, open(os.path.join(HERE, f'mine_{LABEL}.json'), 'w'), indent=1, default=str)
with open(os.path.join(HERE, f'checks_{LABEL}.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(CHECKS)
bad = [c for c in CHECKS if not c['ok']]
print(f'{LABEL}: {len(CHECKS)} checks, {len(bad)} disagreements; clamps {CLAMPS}; keep {KEEP}')
for c in bad[:80]: print('  ', c)
