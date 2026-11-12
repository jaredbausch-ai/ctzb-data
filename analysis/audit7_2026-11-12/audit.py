import datetime as dt, json, os, re, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import *  # noqa
from checker import Checker, norm, OUT

CK = Checker()
YN = lambda b: 'yes' if b else 'no'


def lens_set(txt):
    return set(x for x in txt.split(' + ') if x and x != '-')


# ------------------------------------------------------------------ 1. ledger
def check_ledger(S):
    L = S.csv('ledger.csv'); st_ = S.name
    theirs = {(r['chart'], r['entry']): r for r in L}
    mine = S.ledkey
    for k in sorted(set(theirs) | set(mine)):
        CK.add(st_, f'ledger {k[0]} {k[1]}', 'membership', 'present' if k in theirs else 'absent',
               'present' if k in mine else 'absent', 'membership')
    # grade record from my rows with the ledger's grades (given)
    G = {}
    for k, s in mine.items():
        if k in theirs:
            s['grade'] = theirs[k]['grade']; s['lenses'] = lens_set(theirs[k]['lenses'])
            G.setdefault((s['a'], s['grade']), []).append(s)
    grec = {}
    for key, g in G.items():
        n = len(g)
        grec[key] = (rnd(100 * sum(x['m']['r20'] for x in g) / n), rnd(100 * sum(x['m']['t30'] for x in g) / n),
                     rnd(st.median(x['m']['dd'] for x in g), 1))
    # odds on the day, from the same membership (rows whose 60 days finished before this entry)
    hist = sorted(mine.values(), key=lambda s: s['d0'])
    for k in sorted(set(theirs) & set(mine)):
        r, s = theirs[k], mine[k]; m = s['m']; loc = f'ledger {k[0]} {k[1]}'
        e = s['entry']
        chk = [('asset', r['asset'], s['a']), ('low', r['low'], str(s['tdate'])), ('entryPrice', r['entryPrice'], rnd(e, 2)),
               ('tags', r['tags'], tags_text(s)),
               ('reached20', r['reached20'], YN(m['r20'])), ('touched30', r['touched30'], YN(m['t30'])),
               ('bestMove', r['bestMove'], rnd(m['up'], 6)), ('maxDrawdown', r['maxDrawdown'], rnd(m['dd'], 6)),
               ('dipBeforeHigh', r['dipBeforeHigh'], rnd(m['ddpk'], 6)), ('return60d', r['return60d'], rnd(m['ret'], 6)),
               ('daysToHigh', r['daysToHigh'], m['dpk']), ('year', r['year'], s['d0'].year),
               ('reached10', r['reached10'], YN(m['r10'])), ('reached15', r['reached15'], YN(m['r15'])),
               ('surv10', r['surv10'], YN(m['r10'] and not m['fell25'])),
               ('scaled20', r['scaled20'], (lambda v: '' if v is None else YN(v))(S.vol[s['a']].scaled20(s['d0'], m['up']))),
               ('gradeReach20', r['gradeReach20'], grec[(s['a'], r['grade'])][0]),
               ('gradeTouched30', r['gradeTouched30'], grec[(s['a'], r['grade'])][1]),
               ('gradeMedDrawdown', r['gradeMedDrawdown'], grec[(s['a'], r['grade'])][2])]
        prior = [h for h in hist if h['a'] == s['a'] and h['d0'] + dt.timedelta(days=61) <= s['d0'] and 'grade' in h]
        Gp = [h for h in prior if h['grade'] == r['grade']]
        if len(Gp) < 10 or not prior:
            dv = ['', '', '', '', len(Gp), '', '']
        else:
            def rate(fn):
                base = sum(fn(h) for h in prior) / len(prior)
                return rnd(100 * (sum(fn(h) for h in Gp) + 5 * base) / (len(Gp) + 5))
            dv = [rate(lambda h: h['m']['r10']), rate(lambda h: h['m']['r20']), rate(lambda h: h['m']['up'] >= 30),
                  rate(lambda h: h['m']['t30']), len(Gp), rate(lambda h: h['m']['r10'] and not h['m']['fell25']),
                  rate(lambda h: bool(S.vol[h['a']].scaled20(h['d0'], h['m']['up'])))]
        for nm, v in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10', 'dayScaled20'), dv):
            chk.append((nm, r[nm], v))
        for lab, sh, yo in chk:
            CK.add(st_, loc, lab, sh, yo, 'value')
    return grec


if __name__ == '__main__':
    pass


# ------------------------------------------------------------------ 2. grade_odds
def check_grade_odds(S, F):
    st_ = S.name
    eth = [s for s in S.led if s['a'] == 'ETH']
    groups = {}
    for a in ('ETH', 'BTC'):
        for g in ('A+', 'A', 'B', 'C'):
            groups[(a, g)] = [s for s in S.led if s['a'] == a and s.get('grade') == g]
    groups[('ETH', 'diamond or prime dot')] = [s for s in eth if s['prime'] or s['dis']]
    groups[('ETH', 'no diamond or prime dot')] = [s for s in eth if not (s['prime'] or s['dis'])]
    seen = set()
    for go in F['grade_odds']:
        key = (go['asset'], go['grade']); loc = f"grade_odds {go['asset']} {go['grade']}"
        seen.add(key)
        if key not in groups:
            CK.add(st_, loc, 'out of scope (HTF divergence lens)', '', '', ok=True); continue
        G = groups[key]; n = len(G)
        CK.add(st_, loc, 'label', go['label'], LABEL, 'label')
        CK.add(st_, loc, 'past_trades', go['past_trades'], n, 'value')
        CK.add(st_, loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], pctr(sum(s['m']['r10'] for s in G), n), 'value')
        CK.add(st_, loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'],
               pctr(sum(s['m']['r10'] and not s['m']['fell25'] for s in G), n), 'value')
        CK.add(st_, loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], pctr(sum(s['m']['r20'] for s in G), n), 'value')
        CK.add(st_, loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], medr([s['m']['dd'] for s in G], 1), 'value')
        CK.add(st_, loc, 'sample', go['sample'], f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}", 'value')
    for key in groups:
        if key not in seen:
            CK.add(st_, f'grade_odds {key[0]} {key[1]}', 'row present', 'absent', 'present', 'membership')


LABEL = ("Computed signal, not a fill. No trade was taken. Entry quality only: "
         "the data has no exits, so this is not a strategy return or a track record.")


# ------------------------------------------------------------------ 3. if_it_misses
def misses_of(G):
    ms = [s for s in G if not s['m']['r10']]
    b = [s['m']['up'] for s in ms]
    above_first = 0
    for s in ms:   # stricter reading of "up first": above entry before ever being below it (low first in a day)
        e = s['entry']
        for h, l in zip(s['m']['H'], s['m']['L']):
            if l < e: break
            if h > e: above_first += 1; break
    return dict(signals=len(G), misses=len(ms), up_first=sum(x > 0 for x in b),
                median_peak_pct=medr(b, 1), mean_peak_pct=rnd(st.mean(b), 1) if b else '',
                peaked_5_or_more=sum(x >= 5 for x in b), peaked_10_or_more=sum(x >= 10 for x in b),
                median_worst_drop_pct=medr([s['m']['dd'] for s in ms], 1),
                median_day60_pct=medr([s['m']['ret'] for s in ms], 1), _above_before_below=above_first)


def check_misses(S, F):
    st_ = S.name
    have = {(m['asset'], m['grade']): m for m in F['if_it_misses']}
    for a in ('ETH', 'BTC'):
        for g in ('A+', 'A', 'B', 'C'):
            G = [s for s in S.led if s['a'] == a and s.get('grade') == g]
            loc = f'if_it_misses {a} {g}'
            if (a, g) not in have:
                CK.add(st_, loc, 'row present', 'absent', 'present' if G else 'absent', 'membership'); continue
            sh = have[(a, g)]; mi = misses_of(G)
            for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'mean_peak_pct', 'peaked_5_or_more',
                      'peaked_10_or_more', 'median_worst_drop_pct', 'median_day60_pct'):
                CK.add(st_, loc, k, sh[k], mi[k], 'value')
            CK.add(st_, loc, 'miss_rule', sh['miss_rule'], 'did not rise 10% within 60 days', 'label')
            S.__dict__.setdefault('miss_alt', {})[(a, g)] = mi


# ------------------------------------------------------------------ 7. past paths
def path_of(S, s):
    day = S.day[s['a']]; e = s['entry']; p = [0.0]
    for k in range(1, 61):
        i = day.pos.get(s['d0'] + dt.timedelta(days=k))
        if i is None: return None
        p.append((day.C[i] / e - 1) * 100)
    return p


def check_paths(S, sh, G, loc):
    st_ = S.name
    P = [p for p in (path_of(S, s) for s in G) if p is not None]
    CK.add(st_, loc, 'signals', sh['signals'], len(P), 'value')
    CK.add(st_, loc, 'grade', sh['grade'], 'A+', 'label')
    days = {d['day']: d for d in sh['days']}
    CK.add(st_, loc, 'days listed', len(days), 61, 'value')
    for d in range(61):
        x = days.get(d, {})
        for f, q in (('q25_pct', .25), ('median_pct', .5), ('q75_pct', .75)):
            CK.add(st_, loc, f'day {d} {f}', x.get(f), rnd(q_lin([p[d] for p in P], q), 1), 'value')
    return P


def check_all_paths(S, F):
    for pp in F['past_paths']:
        G = [s for s in S.led if s['a'] == pp['asset'] and s.get('grade') == 'A+']
        check_paths(S, pp, G, f"past_paths {pp['asset']}")
    CK.add(S.name, 'past_paths', 'assets', ','.join(p['asset'] for p in F['past_paths']), 'ETH,BTC', 'membership')
    lim = dt.date(2024, 9, 22)
    G = [s for s in S.led if s['a'] == 'ETH' and s.get('grade') == 'A+' and s['d0'] + dt.timedelta(days=60) <= lim]
    check_paths(S, F['example_past_paths'], G, 'example_past_paths')


# ------------------------------------------------------------------ 4. odds_fade
TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]


def chart_tags(ch, s):
    # zone-exit B: bucket B and CT's running minimum since it was last at or above 60 is still >= 50
    z = None
    for v in ch.ct[:s['ti'] + 1]:
        if v is None: continue
        z = None if v >= 60 else (v if z is None else min(z, v))
    t = {s['bk'], 'any trough'}
    if s['dis']: t |= {'diamond', 'filled' if s['strong'] else 'hollow'}
    if s['prime']: t.add('prime dot')
    if s['dis'] and s['prime']: t.add('diamond+dot')
    if s['bk'] == 'B' and s['ct'] < 60 and z is not None and z >= 50: t.add('zone-exit B')
    return t


def all_gated(S, a, tf):
    """every gated pivot on the chart, confirmed or not (refresh.py scores the tier on these)"""
    ch = S.ch[(a, tf)]; out = []; prev = None
    for ti in troughs(ch):
        v, k = ch.ct[ti], ch.K[ti]
        dis = prev is not None and (((v - prev[0]) > EPS and (k - prev[1]) < -EPS) or ((v - prev[0]) < -EPS and (k - prev[1]) > EPS))
        prev = (v, k)
        if not S.gate(ch.D[ti]) or ti + 3 >= len(ch.C): continue
        s = dict(ti=ti, ei=ti + 3, ct=v, k=k, dis=dis, strong=dis and v < 50, prime=20 <= k < 50,
                 bk='A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D')
        s['tags'] = chart_tags(ch, s)
        out.append(s)
    return out


def tier(S, upto):
    keep = set()
    for tf in TFS:
        ch = S.ch[('ETH', tf)]; tfd = int(tf[0])
        rows = []
        for s in all_gated(S, 'ETH', tf):
            i = s['ei']; end = ch.D[i] + dt.timedelta(days=60)
            if ch.D[-1] < end: continue
            js = [j for j in range(i + 1, len(ch.D)) if ch.D[j] <= end]
            if not js: continue
            win = ch.C[js[-1]] > ch.C[i]
            if ch.D[i] + dt.timedelta(days=tfd - 1 + 60) < upto:
                rows.append((s['tags'], win))
        for t in TAGS:
            sub = [w for tg, w in rows if t in tg]
            if len(sub) >= 8 and 100 * sum(sub) / len(sub) >= 70: keep.add((tf, t))
    return keep


def check_fade(S, F):
    st_ = S.name; of = F['odds_fade']
    keep = tier(S, dt.date(S.today.year, 1, 1))
    S.keep = keep
    day = S.day['ETH']; pool = []
    for tf in TFS:
        ch = S.ch[('ETH', tf)]
        for s in all_gated(S, 'ETH', tf):
            if not any((tf, t) in keep for t in s['tags']): continue
            d0 = bucket_last_day(ch.D[s['ei']], int(tf[0]))
            if d0 + dt.timedelta(days=60) >= S.today or d0 not in day.pos: continue
            ks = window(day, d0)
            if ks is None: continue
            e = day.C[day.pos[d0]]
            dip = (min(day.L[k] for k in ks[:10]) / e - 1) * 100
            run_hi = max(day.H[k] for k in ks[10:])
            c10 = day.C[ks[9]]
            pool.append(dict(dip=dip, r10=run_hi >= e * 1.10, r20=run_hi >= e * 1.20, green=c10 >= e))
    S.fade_pool = pool
    bands = [("shallower than -2%", -2, 100), ("-2% to -5%", -5, -2), ("-5% to -10%", -10, -5), ("-10% to -20%", -20, -10), ("worse than -20%", -100, -20)]
    mine = []
    for lab, lo, hi in bands:
        g = [p for p in pool if lo < p['dip'] <= hi]
        if len(g) >= 5: mine.append((lab, g))
    CK.add(st_, 'odds_fade', 'early_dip rows', len(of['early_dip']), len(mine), 'membership')
    for (lab, g), r in zip(mine, of['early_dip']):
        loc = f'odds_fade early_dip {lab}'
        r10 = pctr(sum(p['r10'] for p in g), len(g)); r20 = pctr(sum(p['r20'] for p in g), len(g))
        CK.add(st_, loc, 'band', r['band'], lab, 'label')
        CK.add(st_, loc, 'past_trades', r['past_trades'], len(g), 'value')
        for k in ('rose10_after_day10_pct', 'rose10_within60d_pct'): CK.add(st_, loc, k, r[k], r10, 'value')
        for k in ('rose20_after_day10_pct', 'rose20_within60d_pct'): CK.add(st_, loc, k, r[k], r20, 'value')
        CK.add(st_, loc, 'edge', r['edge'], 'intact' if r10 >= 70 else 'gone', 'value')
    grp = [('green on day 10', [p for p in pool if p['green']]), ('red on day 10', [p for p in pool if not p['green']])]
    grp = [x for x in grp if len(x[1]) >= 5]
    CK.add(st_, 'odds_fade', 'day10 rows', len(of['day10']), len(grp), 'membership')
    for (lab, g), r in zip(grp, of['day10']):
        loc = f'odds_fade day10 {lab}'
        r10 = pctr(sum(p['r10'] for p in g), len(g)); r20 = pctr(sum(p['r20'] for p in g), len(g))
        CK.add(st_, loc, 'check', r['check'], lab, 'label')
        CK.add(st_, loc, 'past_trades', r['past_trades'], len(g), 'value')
        for k in ('rose10_after_day10_pct', 'rose10_within60d_pct'): CK.add(st_, loc, k, r[k], r10, 'value')
        for k in ('rose20_after_day10_pct', 'rose20_within60d_pct'): CK.add(st_, loc, k, r[k], r20, 'value')
        CK.add(st_, loc, 'edge', r['edge'], 'intact' if r10 >= 70 else 'gone', 'value')
    CK.add(st_, 'odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70, 'value')
    CK.add(st_, 'odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)', 'label')
    CK.add(st_, 'odds_fade', 'label', of['label'], LABEL, 'label')


# ------------------------------------------------------------------ 5/6. cards and open signals
PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
GOF = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'


def card_lenses(txt):
    return set() if txt == 'none' else {PLAIN[x] for x in txt.split('; ')}


def sample_for(S, a, tf, grade, lenses, known_by=None):
    L = [s for s in S.led if known_by is None or s['d0'] + dt.timedelta(days=60) <= known_by]
    ex = [s for s in L if s['chart'] == f'{a} {tf}' and s['lenses'] == lenses]
    sg = [s for s in L if s['chart'] == f'{a} {tf}' and s['grade'] == grade]
    ag = [s for s in L if s['a'] == a and s['grade'] == grade]
    tail = ' whose 60 days had closed by then' if known_by else ''
    past = '' if known_by else 'past '
    if len(ex) >= 15:
        return f'all {len(ex)} {past}{a} {tf} signals with exactly the same confirmations{tail}', ex
    if len(sg) >= 15:
        return (f'all {len(sg)} {past}{a} {tf} signals graded {grade}{tail} (' + ('none' if not ex else f'only {len(ex)}')
                + ' had exactly the same confirmations, too few to use)'), sg
    alone = 'had' if known_by else 'has'
    return f'all {len(ag)} {past}grade {grade} signals across all {a} charts{tail} ({a} {tf} alone {alone} only {len(sg)}, too few to use)', ag


def low_day(S, a, tf, tdate):
    tfd = int(tf[0]); last = bucket_last_day(tdate, tfd); day = S.day[a]
    cand = [(day.L[day.pos[d]], d) for d in (tdate + dt.timedelta(days=i) for i in range((last - tdate).days + 1)) if d in day.pos]
    return str(min(cand)[1])


def compare_card(S, loc, c, exp, G):
    st_ = S.name
    f = card_figs([dict(a=s['a'], d0=s['d0'], entry=s['entry'], m=s['m']) for s in G], S.vol)
    E = dict(exp)
    E.update({'past_trades': f['n'], 'rose10_within60d_pct': f['reach10'], 'rose10_never_fell25_within60d_pct': f['surv10'],
              'rose20_within60d_pct': f['reach20'], 'beat_normal_move_pct': f['scaled20'], 'fell30_within60d_pct': f['touched30'],
              'typical_biggest_rise_pct': f['bestMove'], 'typical_dip_before_rise_pct': f['dipBeforeHigh'], 'typical_deepest_dip_pct': f['maxDip60'],
              'typical_biggest_rise_exact_pct': rnd(f['bestMoveExact'], 6) if G else '', 'typical_dip_before_rise_exact_pct': rnd(f['dipBeforeHighExact'], 6) if G else '',
              'typical_deepest_dip_exact_pct': rnd(f['maxDip60Exact'], 6) if G else '',
              'typical_day_first_rose10': f['daysTo10'], 'typical_day_first_rose20': f['daysTo20'],
              'typical_day_of_60d_high': f['daysToHigh'], 'typical_day_of_deepest_dip': f['daysToLow'], 'label': LABEL})
    for k, v in E.items():
        CK.add(st_, loc, k, c.get(k), v, 'value')
    for nm, key in (('before_2022', 'Old'), ('since_2022', 'New')):
        CK.add(st_, loc, f'{nm}.past_trades', c[nm]['past_trades'], f['n' + key], 'value')
        CK.add(st_, loc, f'{nm}.rose10_never_fell25_within60d_pct', c[nm]['rose10_never_fell25_within60d_pct'], f['surv10' + key], 'value')
    CK.add(st_, loc, 'from_entry.past_trades', c['from_entry']['past_trades'], f['n'], 'value')
    CK.add(st_, loc, 'from_entry.still_rose10_pct', c['from_entry']['still_rose10_pct'], f['l0ok'], 'value')
    CK.add(st_, loc, 'from_entry.went_on_to_fall25_pct', c['from_entry']['went_on_to_fall25_pct'], f['l0liq'], 'value')
    rows = {r['fell_pct']: r for r in c['if_it_falls_first']}
    CK.add(st_, loc, 'if_it_falls_first rows', ','.join(str(x) for x in rows), '5,10,15,20', 'membership')
    for th in (5, 10, 15, 20):
        r = rows.get(th, {})
        CK.add(st_, loc, f'falls {th}% first: past_trades', r.get('past_trades'), f[f'l{th}n'], 'value')
        CK.add(st_, loc, f'falls {th}% first: still_rose10_pct', r.get('still_rose10_pct'), f[f'l{th}ok'], 'value')
        CK.add(st_, loc, f'falls {th}% first: went_on_to_fall25_pct', r.get('went_on_to_fall25_pct'), f[f'l{th}liq'], 'value')
    # displayed medians must equal the exact ones rounded once
    for a_, b_ in (('typical_biggest_rise_pct', 'typical_biggest_rise_exact_pct'), ('typical_dip_before_rise_pct', 'typical_dip_before_rise_exact_pct'),
                   ('typical_deepest_dip_pct', 'typical_deepest_dip_exact_pct')):
        if c.get(b_) not in (None, ''):
            CK.add(st_, loc, f'{a_} = round({b_})', c[a_], rnd(c[b_], 1), 'value')
    for x in c.get('active_confluences', []):
        ca, ctf = x['after'].split()[:2]
        ok = any(str(s['d0']) == x['after_confirmed'] for s in S.sig[(ca, ctf)])
        CK.add(st_, loc, f"confluence after {x['after']} confirmed", x['after_confirmed'], x['after_confirmed'] if ok else 'no such signal', 'value')
        CK.add(st_, loc, f"confluence after {x['after']} window_closes", x['window_closes'],
               str(dt.date.fromisoformat(x['after_confirmed']) + dt.timedelta(days=10)), 'value')
        d_conf = dt.date.fromisoformat(exp['confirms_on'])
        CK.add(st_, loc, f"confluence after {x['after']} within 0-10 days before confirmation",
               (d_conf - dt.date.fromisoformat(x['after_confirmed'])).days, (d_conf - dt.date.fromisoformat(x['after_confirmed'])).days, 'value',
               ok=0 <= (d_conf - dt.date.fromisoformat(x['after_confirmed'])).days <= 10)
    return f


def forming_lows(S):
    """my own forming (provisional) lows: a CT pivot waiting on its right-hand bars"""
    out = []
    for (a, tf), ch in S.ch.items():
        ct = ch.ct; n = len(ct)
        for back in (1, 2, 3):
            ti = n - 1 - back; v = ct[ti]
            if v is None or ti < 3: continue
            if not all(ct[j] is not None and ct[j] > v for j in range(ti - 3, ti)): continue
            if any(ct[j] < v for j in range(ti + 1, n)): continue
            need = 3 - back
            tfd = int(tf[0]); d = ch.D[-1]
            for _ in range(need):
                d = bucket_last_day(d, tfd) + dt.timedelta(days=1)
            conf = bucket_last_day(d, tfd)
            kill = None
            if need <= 1:
                base = ch.C[:-1] if need == 0 else ch.C[:]
                lo, hi = ch.C[-1] * 0.3, ch.C[-1] * 3
                for _ in range(200):
                    mid = (lo + hi) / 2
                    if rsi(base + [mid])[-1] <= v: lo = mid
                    else: hi = mid
                kill = (lo + hi) / 2
            out.append(dict(a=a, tf=tf, ti=ti, tdate=ch.D[ti], need=need, conf=conf, kill=kill, ct=v))
            break
    return out


def check_cards(S, F):
    st_ = S.name; day = {a: S.day[a] for a in ('ETH', 'BTC')}
    last_close = {a: day[a].C[-1] for a in day}
    # forming
    fl = {f"{x['a']}-{x['tf']}-{x['conf']}": x for x in forming_lows(S)}
    cards = {c['signal_id']: c for c in F['cards']}
    for sid in sorted(set(fl) | set(cards)):
        CK.add(st_, f'cards {sid}', 'membership', 'present' if sid in cards else 'absent', 'present' if sid in fl else 'absent', 'membership')
    for sid in sorted(set(fl) & set(cards)):
        x, c = fl[sid], cards[sid]; a, tf = x['a'], x['tf']; lz = card_lenses(c['confirmations'])
        basis, G = sample_for(S, a, tf, c['grade'], lz)
        exp = dict(signal_id=sid, chart=f'{a} {tf}', asset=a, timeframe=tf, low_date=str(x['tdate']), low_day=low_day(S, a, tf, x['tdate']),
                   confirms_on=str(x['conf']), bars_to_confirm=x['need'], must_close_above=rnd(x['kill'], 2) if x['kill'] else None,
                   price_now=rnd(last_close[a], 2), entry_close=None, sample=basis)
        CK.add(st_, f'cards {sid}', 'grade vs lens count (consistency)', c['grade'], GOF(len(lz)), 'value')
        S.__dict__.setdefault('mycards', {})[sid] = dict(exp, kind='forming', grade=c['grade'], figs=compare_card(S, f'cards {sid}', c, exp, G))
        S.__dict__.setdefault('kill', {})[sid] = x['kill']
    # open signals
    opens = []
    for (a, tf), lst in S.sig.items():
        if tf not in GRADED: continue
        for s in lst:
            if 0 <= (S.today - s['d0']).days <= 60: opens.append(s)
    have = {o['signal_id']: o for o in F['open_signals']}
    mine = {f"{s['a']}-{s['tf']}-{s['d0']}": s for s in opens}
    for sid in sorted(set(have) | set(mine)):
        CK.add(st_, f'open_signals {sid}', 'membership', 'present' if sid in have else 'absent', 'present' if sid in mine else 'absent', 'membership')
    order = [o['signal_id'] for o in F['open_signals']]
    CK.add(st_, 'open_signals', 'order (by entry date, chart)', ','.join(order),
           ','.join(sorted(mine, key=lambda k: (str(mine[k]['d0']), mine[k]['chart']))), 'value')
    for sid in sorted(set(have) & set(mine)):
        o, s = have[sid], mine[sid]; a = s['a']; dd = day[a]; e = s['entry']; loc = f'open_signals {sid}'
        closed = [i for i in (dd.pos.get(s['d0'] + dt.timedelta(days=k)) for k in range(1, 61)) if i is not None and dd.D[i] < S.today]
        mark = lambda m: next((rnd((dd.C[i] / e - 1) * 100, 1) for i in closed if (dd.D[i] - s['d0']).days == m), None)
        exp = dict(chart=s['chart'], entry_date=str(s['d0']), entry_close=rnd(e, 2), tags=tags_text(s), days_elapsed=(S.today - s['d0']).days,
                   day10_pct=mark(10), day30_pct=mark(30), day60_pct=mark(60),
                   best_so_far_pct=rnd((max(dd.H[i] for i in closed) / e - 1) * 100, 1) if closed else None,
                   worst_so_far_pct=rnd((min(dd.L[i] for i in closed) / e - 1) * 100, 1) if closed else None, label=LABEL)
        for k, v in exp.items():
            CK.add(st_, loc, k, o.get(k), v, 'value')
        c = o['card']
        if not c:
            CK.add(st_, loc, 'card', 'missing', 'present', 'membership'); continue
        lz = card_lenses(c['confirmations'])
        CK.add(st_, loc, 'grade = card grade', o['grade'], c['grade'], 'value')
        CK.add(st_, loc, 'confirmations = card lenses', ' + '.join(sorted(lens_set(o['confirmations']))), ' + '.join(sorted(lz)), 'value')
        basis, G = sample_for(S, a, s['tf'], c['grade'], lz)
        cexp = dict(signal_id=sid, chart=s['chart'], asset=a, timeframe=s['tf'], low_date=str(s['tdate']), low_day=low_day(S, a, s['tf'], s['tdate']),
                    confirms_on=str(s['d0']), bars_to_confirm=None, must_close_above=None, price_now=rnd(last_close[a], 2), entry_close=rnd(e, 2), sample=basis)
        S.__dict__.setdefault('mycards', {})[sid] = dict(cexp, kind='open', grade=c['grade'], figs=compare_card(S, f'open card {sid}', c, cexp, G), open=exp)
    # example
    xc = F['example_card']; s = S.ledkey.get(('ETH 2D', '2024-09-22'))
    lz = card_lenses(xc['confirmations'])
    basis, G = sample_for(S, 'ETH', '2D', xc['grade'], lz, known_by=dt.date(2024, 9, 22))
    xexp = dict(signal_id='ETH-2D-2024-09-22', chart='ETH 2D', asset='ETH', timeframe='2D', low_date=str(s['tdate']), low_day=low_day(S, 'ETH', '2D', s['tdate']),
                confirms_on='2024-09-22', bars_to_confirm=None, must_close_above=None, price_now=None, entry_close=rnd(s['entry'], 2), sample=basis, example=True)
    CK.add(st_, 'example_card', 'grade = ledger grade', xc['grade'], s['grade'], 'value')
    CK.add(st_, 'example_card', 'confirmations = ledger lenses', ' + '.join(sorted(lz)), ' + '.join(sorted(s['lenses'])), 'value')
    S.__dict__.setdefault('mycards', {})['example'] = dict(xexp, kind='example', grade=xc['grade'], figs=compare_card(S, 'example_card', xc, xexp, G))
    S.example_G = G
