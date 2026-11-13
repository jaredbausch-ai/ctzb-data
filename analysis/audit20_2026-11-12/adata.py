"""Audit #20 -- build my own model of everything the feed / ledger carry, and compare (checks 1-7)."""
import csv, json, os, sys, datetime as dt
from fractions import Fraction as Fr
from decimal import Decimal as Dc
import alib as A
from alib import rha, fstr, to_fr, med, quant, share, D

DAYS = lambda n: dt.timedelta(days=n)


class Checks:
    def __init__(self, state): self.state = state; self.rows = []
    def add(self, loc, label, shown, mine, cause=''):
        ok = same(shown, mine)
        self.rows.append([self.state, loc, label, show(shown), show(mine), 'ok' if ok else 'DIFF', '' if ok else cause])
        return ok
    def n(self): return len(self.rows)
    def bad(self): return [r for r in self.rows if r[5] != 'ok']


def show(v):
    if isinstance(v, Fr): return fstr(v, 6).rstrip('0').rstrip('.') if v.denominator != 1 else str(v.numerator)
    if v is None: return ''
    if isinstance(v, (dt.date,)): return str(v)
    return str(v)


def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool): return a == b
    fa, fb = to_fr(a), to_fr(b)
    if fa is not None and fb is not None: return fa == fb
    sa = '' if a is None else str(a).strip(); sb = '' if b is None else str(b).strip()
    return sa == sb


def yn(b): return 'yes' if b else 'no'


def funding(root, a):
    f1, f2 = {}, {}
    p = os.path.join(root, 'data', 'derivs', f'{a}_funding_daily.csv')
    if not os.path.exists(p): return f1, f2
    for r in csv.DictReader(open(p)):
        d = D.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): f1[d] = float(v)
        v = r.get('funding_mean')
        if v not in ('', None): f2[d] = float(v)
    return f1, f2


def build(root, now, state):
    W = A.World(root, now); C = Checks(state); today = W.today
    feed = json.load(open(os.path.join(root, 'feed', 'ctzb_feed.json')))
    led = list(csv.DictReader(open(os.path.join(root, 'datasets', 'ledger.csv'))))
    M = dict(today=str(today))

    # ------------------------------------------------------------ 1. ledger
    graded = [s for a in A.ASSETS for tf in A.GRADED for s in W.sig[(a, tf)] if s['m']]
    f1, f2 = funding(root, 'ETH')
    def eth_ok(s):
        d0 = s['d0']
        k1 = d0 in f1 and sum(1 for k in range(1, 91) if d0 - DAYS(k) in f1) >= 60
        k2 = sum(1 for k in range(7) if d0 - DAYS(k) in f2) >= 5 and sum(1 for k in range(7) if d0 - DAYS(14 + k) in f2) >= 5
        return k1 and k2
    mine = {(s['chart'], str(s['d0'])): s for s in graded if s['a'] == 'BTC' or eth_ok(s)}
    theirs = {(r['chart'], r['entry']): r for r in led}
    C.add('ledger', 'row count', len(led), len(mine), 'ledger membership')
    C.add('ledger', 'duplicate keys', len(led) - len(theirs), 0, 'duplicate ledger rows')
    for k in sorted(set(mine) - set(theirs)): C.add(f'ledger {k[0]} {k[1]}', 'membership (mine, not in ledger)', 'absent', 'present', 'signal missing from the ledger')
    for k in sorted(set(theirs) - set(mine)): C.add(f'ledger {k[0]} {k[1]}', 'membership (in ledger, not mine)', 'present', 'absent', 'ledger row I cannot derive')
    L = []      # joined: my signal + given grade / lenses
    for k, r in theirs.items():
        s = mine.get(k)
        if s is None: continue
        s = dict(s); s['grade'] = r['grade']; s['lens'] = frozenset(x for x in r['lenses'].split(' + ') if x and x != '-'); s['row'] = r
        s['sc'] = W.scaled20(s)
        m = s['m']; s['x6'] = {k_: rha(m[k_], 6) for k_ in ('up', 'dd', 'ddpk', 'ret')}
        L.append(s)
    L.sort(key=lambda s: (s['d0'], s['tf']))
    # grade stats (grades.csv / grade_odds)
    GS = {}
    for a in A.ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            G = [s for s in L if s['a'] == a and s['grade'] == g]; n = len(G)
            if not n: GS[(a, g)] = dict(n=0); continue
            GS[(a, g)] = dict(n=n, reach10=share(sum(s['m']['r10'] for s in G), n), surv10=share(sum(s['m']['surv'] for s in G), n),
                              reach20=share(sum(s['m']['r20'] for s in G), n), t30=share(sum(s['m']['t30'] for s in G), n),
                              medDip=rha(med([s['m']['dd'] for s in G]), 1), sample=f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}")
    for lab, sel in (('diamond or prime dot', lambda s: s['prime'] or s['dis']), ('no diamond or prime dot', lambda s: not (s['prime'] or s['dis']))):
        G = [s for s in L if s['a'] == 'ETH' and sel(s)]; n = len(G)
        if n: GS[('ETH', lab)] = dict(n=n, reach10=share(sum(s['m']['r10'] for s in G), n), surv10=share(sum(s['m']['surv'] for s in G), n),
                                      reach20=share(sum(s['m']['r20'] for s in G), n), t30=share(sum(s['m']['t30'] for s in G), n),
                                      medDip=rha(med([s['m']['dd'] for s in G]), 1), sample=f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}")
    # odds on the day
    def day_odds(s):
        prior = [h for h in L if h['a'] == s['a'] and h['d0'] + DAYS(60) <= s['d0']]
        G = [h for h in prior if h['grade'] == s['grade']]
        if len(G) < 10 or not prior: return ['', '', '', '', len(G), '', '']
        def rate(fn, ok=lambda h: True):
            P = [h for h in prior if ok(h)]; Gk = [h for h in G if ok(h)]
            if not P or not Gk: return ''
            base = Fr(sum(1 for h in P if fn(h)), len(P))
            return rha(100 * (sum(1 for h in Gk if fn(h)) + 5 * base) / (len(Gk) + 5))
        return [rate(lambda h: h['m']['r10']), rate(lambda h: h['m']['r20']), rate(lambda h: h['m']['r30']), rate(lambda h: h['m']['t30']), len(G),
                rate(lambda h: h['m']['surv']), rate(lambda h: bool(h['sc']), ok=lambda h: h['sc'] is not None)]
    for s in L:
        r = s['row']; m = s['m']; loc = f"ledger {s['chart']} {s['d0']}"; gs = GS.get((s['a'], s['grade']), {})
        do = day_odds(s)
        exp = dict(asset=s['a'], low=str(s['tdate']), entryPrice=rha(s['entry'], 2), tags=A.tagstr(s),
                   gradeReach20=gs.get('reach20'), gradeTouched30=gs.get('t30'), gradeMedDrawdown=gs.get('medDip'),
                   reached20=yn(m['r20']), touched30=yn(m['t30']), bestMove=s['x6']['up'], maxDrawdown=s['x6']['dd'], dipBeforeHigh=s['x6']['ddpk'],
                   return60d=s['x6']['ret'], daysToHigh=m['dpk'], year=s['d0'].year, reached10=yn(m['r10']), reached15=yn(m['r15']),
                   surv10=yn(m['surv']), scaled20='' if s['sc'] is None else yn(s['sc']),
                   dayReach10=do[0], dayReach20=do[1], dayReach30=do[2], dayTouched30=do[3], dayN=do[4], daySurv10=do[5], dayScaled20=do[6])
        for k_, v in exp.items(): C.add(loc, k_, r.get(k_), v, 'ledger figure')
    M['ledger'] = [dict(asset=s['a'], chart=s['chart'], entry=str(s['d0']), entryPrice=fstr(rha(s['entry'], 2), 2), grade=s['grade'],
                        reached10=yn(s['m']['r10']), reached20=yn(s['m']['r20']), bestMove=fstr(s['x6']['up'], 6), maxDrawdown=fstr(s['x6']['dd'], 6),
                        return60d=fstr(s['x6']['ret'], 6), daysToHigh=s['m']['dpk']) for s in L]

    # ------------------------------------------------------------ 2. grade_odds
    M['grade_odds'] = []
    for g in feed.get('grade_odds', []):
        key = (g['asset'], g['grade']); loc = f"grade_odds {g['asset']} {g['grade']}"
        if 'HTF divergence' in g['grade']:
            M['grade_odds'].append(dict(g, _given=True)); continue      # lens logic, out of scope (note h)
        gs = GS.get(key)
        if gs is None: C.add(loc, 'row exists', 'present', 'absent', 'grade_odds row I cannot derive'); continue
        if gs['n'] == 0:
            C.add(loc, 'past_trades', g['past_trades'], 0, 'grade_odds'); M['grade_odds'].append(dict(asset=g['asset'], grade=g['grade'], past_trades=0)); continue
        exp = dict(past_trades=gs['n'], past_signals=gs['n'], rose10_within60d_pct=gs['reach10'], rose10_never_fell25_within60d_pct=gs['surv10'],
                   rose20_within60d_pct=gs['reach20'], median_deepest_dip_pct=gs['medDip'], sample=gs['sample'])
        for k_, v in exp.items(): C.add(loc, k_, g.get(k_), v, 'grade_odds')
        M['grade_odds'].append(dict(asset=g['asset'], grade=g['grade'], **{k_: (show(v) if isinstance(v, Fr) else v) for k_, v in exp.items()}))
    have = {(g['asset'], g['grade']) for g in feed.get('grade_odds', [])}
    for key, gs in GS.items():
        if key not in have and not feed.get('cards_withheld') and feed.get('grade_odds'): C.add(f'grade_odds {key[0]} {key[1]}', 'row exists', 'absent', 'present', 'grade_odds row missing')

    # ------------------------------------------------------------ 3. if_it_misses
    def misses(G):
        m_ = [s for s in G if not s['m']['r10']]; best = [s['x6']['up'] for s in m_]
        md = lambda xs: rha(med(xs), 1) if xs else None
        return dict(signals=len(G), misses=len(m_), up_first=sum(1 for b in best if b > 0), median_peak_pct=md(best),
                    mean_peak_pct=rha(sum(best) / len(best), 1) if best else None, peaked_5_or_more=sum(1 for b in best if b >= 5),
                    peaked_10_or_more=sum(1 for b in best if b >= 10), median_worst_drop_pct=md([s['x6']['dd'] for s in m_]),
                    median_day60_pct=md([s['x6']['ret'] for s in m_]))
    M['if_it_misses'] = []
    fm = {(x['asset'], x['grade']): x for x in feed.get('if_it_misses', [])}
    aplus_assets = [a for a in A.ASSETS if any(s['a'] == a and s['grade'] == 'A+' for s in L)]
    for a in aplus_assets:
        for g in ('A+', 'A', 'B', 'C'):
            G = [s for s in L if s['a'] == a and s['grade'] == g]
            if not G: continue
            mm = misses(G); M['if_it_misses'].append(dict(asset=a, grade=g, **{k_: (show(v) if isinstance(v, Fr) else v) for k_, v in mm.items()}))
            x = fm.get((a, g))
            if x is None:
                if not feed.get('extras_withheld'): C.add(f'if_it_misses {a} {g}', 'row exists', 'absent', 'present', 'if_it_misses row missing')
                continue
            for k_, v in mm.items(): C.add(f'if_it_misses {a} {g}', k_, x.get(k_), v, 'if_it_misses')
            C.add(f'if_it_misses {a} {g}', 'miss_rule', x.get('miss_rule'), 'did not rise 10% within 60 days', 'label')
    for key in fm:
        if not any(s['a'] == key[0] and s['grade'] == key[1] for s in L): C.add(f'if_it_misses {key[0]} {key[1]}', 'row exists', 'present', 'absent', 'if_it_misses row I cannot derive')
    known = [s for s in L if s['d0'] + DAYS(60) <= A.EX_DATE]
    exk = [s for s in known if s['a'] == 'ETH' and s['grade'] == 'A+']
    xm = feed.get('example_if_it_misses')
    M['example_if_it_misses'] = None
    if exk:
        mm = misses(exk); M['example_if_it_misses'] = {k_: (show(v) if isinstance(v, Fr) else v) for k_, v in mm.items()}
        if xm is None:
            if not feed.get('extras_withheld'): C.add('example_if_it_misses', 'exists', 'absent', 'present', 'example misses missing')
        else:
            for k_ in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'): C.add('example_if_it_misses', k_, xm.get(k_), mm[k_], 'example_if_it_misses')
    elif xm is not None: C.add('example_if_it_misses', 'exists', 'present', 'absent', 'example misses with no known signals')

    # ------------------------------------------------------------ 4. odds_fade (and trades_a_year)
    TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
    trow = []; sigtags = {}
    for tf in A.TFS:
        ch = W.ch[('ETH', tf)]; ct = W.ct[('ETH', tf)]
        zm = []; z = None
        for v in ct:
            if v is None: zm.append(None); continue
            z = None if v >= 60 else (v if z is None else min(z, v)); zm.append(z)
        for s in W.sig[('ETH', tf)]:
            tg = {s['bk'], 'any trough'}
            if s['dis']: tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
            if s['prime']: tg.add('prime dot')
            if s['dis'] and s['prime']: tg.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: tg.add('zone-exit B')
            sigtags[(tf, s['ei'])] = tg
            end = s['edate'] + DAYS(60)
            if ch.date[-1] < end: continue
            js = [j for j in range(s['ei'] + 1, ch.n) if ch.date[j] <= end]
            if not js: continue
            trow.append(dict(tf=tf, tags=tg, d=s['edate'], win=ch.c[js[-1]] > s['entry'], ei=s['ei']))
    anchor = D(today.year, 1, 1)
    keep = []
    for tf in A.TFS:
        for t in TAGS:
            sub = [r for r in trow if r['tf'] == tf and t in r['tags'] and r['d'] + DAYS(int(tf[:-1]) - 1 + 60) < anchor]
            if len(sub) >= 8 and Fr(100 * sum(r['win'] for r in sub), len(sub)) >= 70: keep.append((tf, t))
    M['tier'] = [f'ETH {tf} {t}' for tf, t in keep]
    intier = lambda tf, tg: any(k[0] == tf and k[1] in tg for k in keep)
    T = {(r['tf'], r['d']) for r in trow if intier(r['tf'], r['tags'])}
    tay = None
    if len(T) >= 4:
        data_end = max(W.ch[('ETH', tf)].date[-1] for tf in A.TFS); sc_to = data_end - DAYS(60)
        span = max(Fr(1, 4), Fr((sc_to - min(d for _, d in T)).days * 100, 36525))
        tay = f'{rha(Fr(len(T)) / span)} on average'
    M['trades_a_year'] = tay if tay else '—'
    pool = []
    dy = W.day['ETH']
    for tf in A.TFS:
        for s in W.sig[('ETH', tf)]:
            if not intier(tf, sigtags[(tf, s['ei'])]) or s['d0'] is None or s['d0'] not in dy.pos: continue
            if s['d0'] + DAYS(60) >= today or (s['d0'] + DAYS(60)) not in dy.pos: continue
            ks = W.window('ETH', s['d0'])
            if not ks or (dy.date[ks[-1]] - s['d0']).days != 60: continue
            e = dy.c[dy.pos[s['d0']]]; dn = lambda k: (dy.date[k] - s['d0']).days
            lo10 = min(dy.l[k] for k in ks if dn(k) <= 10); hi_after = max(dy.h[k] for k in ks if dn(k) > 10)
            k10 = [k for k in ks if dn(k) == 10]
            pool.append(dict(dip=(lo10 / e - 1) * 100, r10=hi_after * 100 >= e * 110, r20=hi_after * 100 >= e * 120,
                             green=(dy.c[k10[0]] >= e) if k10 else None))
    bands = [('shallower than -2%', lambda d: d > -2), ('-2% to -5%', lambda d: -5 < d <= -2), ('-5% to -10%', lambda d: -10 < d <= -5),
             ('-10% to -20%', lambda d: -20 < d <= -10), ('worse than -20%', lambda d: d <= -20)]
    def frow(g):
        n = len(g); x = Fr(100 * sum(p['r10'] for p in g), n)
        return dict(past_trades=n, past_signals=n, rose10_after_day10_pct=rha(x), rose20_after_day10_pct=share(sum(p['r20'] for p in g), n),
                    rose10_within60d_pct=rha(x), rose20_within60d_pct=share(sum(p['r20'] for p in g), n), edge='intact' if x >= BARF else 'gone')
    BARF = Fr(A.BAR)
    my_early = [dict(band=lab, **frow([p for p in pool if fn(p['dip'])])) for lab, fn in bands if len([p for p in pool if fn(p['dip'])]) >= 5]
    my_d10 = [dict(check=lab, **frow(g)) for lab, g in (('green on day 10', [p for p in pool if p['green'] is True]), ('red on day 10', [p for p in pool if p['green'] is False])) if len(g) >= 5]
    of = feed.get('odds_fade') or {}
    M['odds_fade'] = dict(posting_bar_pct=A.BAR, tier_fixed_on=str(anchor), early_dip=[{k: (show(v) if isinstance(v, Fr) else v) for k, v in r.items()} for r in my_early],
                          day10=[{k: (show(v) if isinstance(v, Fr) else v) for k, v in r.items()} for r in my_d10])
    if not feed.get('extras_withheld') and feed.get('schema_version') and not feed.get('feed_error'):
        C.add('odds_fade', 'posting_bar_pct', of.get('posting_bar_pct'), A.BAR, 'odds_fade')
        C.add('odds_fade', 'tier_fixed_on', of.get('tier_fixed_on'), str(anchor), 'odds_fade')
        C.add('odds_fade', 'sample names the tier date', f"{anchor.day} {anchor:%b %Y}" in (of.get('sample') or ''), True, 'odds_fade sample text')
        C.add('odds_fade', 'edge_measured_on', of.get('edge_measured_on'), 'rose 10% after day 10 (days 11 to 60)', 'label')
        for name, key, minerows in (('early_dip', 'band', my_early), ('day10', 'check', my_d10)):
            tr = {r[key]: r for r in of.get(name, [])}
            C.add(f'odds_fade {name}', 'rows', ' | '.join(tr), ' | '.join(r[key] for r in minerows), 'odds_fade rows')
            for r in minerows:
                x = tr.get(r[key])
                if x is None: continue
                for k_, v in r.items():
                    if k_ != key: C.add(f'odds_fade {name} {r[key]}', k_, x.get(k_), v, 'odds_fade')
    # top level
    C.add('feed top', 'schema_version', feed.get('schema_version'), 6, 'top level')
    C.add('feed top', 'posting_bar_pct', feed.get('posting_bar_pct'), A.BAR, 'top level')
    if not feed.get('feed_error'):
        C.add('feed top', 'trades_a_year', feed.get('trades_a_year'), M['trades_a_year'], 'trades_a_year')
        C.add('feed top', 'signals_a_year', feed.get('signals_a_year'), M['trades_a_year'], 'trades_a_year alias')
        C.add('feed top', 'market_regime', feed.get('market_regime'), 'Bullish' if W.gate(today) else 'Bearish', 'market_regime')
        C.add('feed top', 'scored_as_of', feed.get('scored_as_of'), str(today), 'scored_as_of')
    M['market_regime'] = 'Bullish' if W.gate(today) else 'Bearish'

    # ------------------------------------------------------------ 5. cards
    def figs(G):
        n = len(G)
        if not n: return None
        sc = [s['sc'] for s in G if s['sc'] is not None]
        old = [s for s in G if s['d0'] < A.SPLIT]; new = [s for s in G if s['d0'] >= A.SPLIT]
        sv = lambda X: share(sum(s['m']['surv'] for s in X), len(X))
        ok0, liq0, _ = W.from_entry(G); lad = []
        for th in (5, 10, 15, 20):
            h, o, l = W.ladder(G, th)
            lad.append(dict(fell_pct=th, past_trades=h, past_signals=h, still_rose10_pct=share(o, h), went_on_to_fall25_pct=share(l, h),
                            still_rose10_exact_pct=share(o, h, 6), _x=Fr(100 * o, h) if h else None))
        t10 = [x for x in (W.days_to(s, 10) for s in G) if x is not None]; t20 = [x for x in (W.days_to(s, 20) for s in G) if x is not None]
        mi = lambda xs: rha(med([Fr(x) for x in xs])) if xs else None
        mu, mp, md_ = med([s['m']['up'] for s in G]), med([s['m']['ddpk'] for s in G]), med([s['m']['dd'] for s in G])
        x0 = Fr(100 * ok0, n)
        edge = 0 if x0 < BARF else next((-r['fell_pct'] for r in lad if r['_x'] is not None and r['_x'] < BARF), None)
        return dict(past_trades=n, past_signals=n, rose10_never_fell25_within60d_pct=sv(G), beat_normal_move_pct=share(sum(sc), len(sc)),
                    rose20_within60d_pct=share(sum(s['m']['r20'] for s in G), n), rose10_within60d_pct=share(sum(s['m']['r10'] for s in G), n),
                    typical_biggest_rise_pct=rha(mu, 1), typical_dip_before_rise_pct=rha(mp, 1), typical_deepest_dip_pct=rha(md_, 1),
                    typical_biggest_rise_exact_pct=rha(mu, 6), typical_dip_before_rise_exact_pct=rha(mp, 6), typical_deepest_dip_exact_pct=rha(md_, 6),
                    fell30_within60d_pct=share(sum(s['m']['t30'] for s in G), n),
                    before_2022=dict(past_trades=len(old), past_signals=len(old), rose10_never_fell25_within60d_pct=sv(old)),
                    since_2022=dict(past_trades=len(new), past_signals=len(new), rose10_never_fell25_within60d_pct=sv(new)),
                    typical_day_first_rose10=mi(t10), typical_day_first_rose20=mi(t20), typical_day_of_60d_high=mi([s['m']['dpk'] for s in G]),
                    typical_day_of_deepest_dip=mi([s['m']['ddday'] for s in G]),
                    from_entry=dict(past_trades=n, past_signals=n, still_rose10_pct=share(ok0, n), went_on_to_fall25_pct=share(liq0, n), still_rose10_exact_pct=rha(x0, 6)),
                    if_it_falls_first=lad, _edge=edge)

    def sample(univ, a, tf, grade, lens, example=False):
        gp = 'the top grade' if grade == 'A+' else 'the same grade'
        Cf = [s for s in univ if s['a'] == a and s['tf'] == tf]
        ex = [s for s in Cf if s['lens'] == lens]; sg = [s for s in Cf if s['grade'] == grade]
        ag = [s for s in univ if s['a'] == a and s['grade'] == grade]
        if not example:
            if len(ex) >= 15: return f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex
            if len(sg) >= 15: return f'all {len(sg)} past {a} {tf} signals of {gp} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
            return f'all {len(ag)} past signals of {gp} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag
        if len(ex) >= 15: return f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', ex
        if len(sg) >= 15: return f'all {len(sg)} {a} {tf} signals of {gp} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
        return f'all {len(ag)} signals of {gp} across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', ag

    def lens_of(conf_text):
        if conf_text in (None, '', 'none'): return frozenset()
        return frozenset(A.RPLAIN.get(x.strip(), '?' + x.strip()) for x in conf_text.split(';'))

    def cmp_card(loc, fc, mc):
        for k_, v in mc.items():
            if k_.startswith('_'): continue
            if isinstance(v, dict):
                for k2, v2 in v.items(): C.add(loc, f'{k_}.{k2}', (fc.get(k_) or {}).get(k2), v2, 'card figure')
            elif isinstance(v, list):
                fl = fc.get(k_) or []
                C.add(loc, f'{k_} rows', len(fl), len(v), 'card ladder')
                for i, r in enumerate(v):
                    for k2, v2 in r.items():
                        if not k2.startswith('_'): C.add(loc, f'{k_}[{r["fell_pct"]}].{k2}', fl[i].get(k2) if i < len(fl) else None, v2, 'card ladder')
            else: C.add(loc, k_, fc.get(k_), v, 'card figure')
        C.add(loc, 'past_signals alias', fc.get('past_signals'), fc.get('past_trades'), 'alias')
        # the three rounded medians must equal the exact (6-place) ones rounded once
        for k_ in ('typical_biggest_rise', 'typical_dip_before_rise', 'typical_deepest_dip'):
            if mc.get(k_ + '_exact_pct') is not None: C.add(loc, f'{k_}_pct = exact rounded once', fc.get(k_ + '_pct'), rha(mc[k_ + '_exact_pct'], 1), 'double rounding')

    def jsonable(mc):
        def f(v):
            if isinstance(v, Fr): return show(v)
            if isinstance(v, dict): return {k: f(x) for k, x in v.items() if not k.startswith('_x')}
            if isinstance(v, list): return [f(x) for x in v]
            if isinstance(v, dt.date): return str(v)
            return v
        return f(mc)

    withheld = bool(feed.get('cards_withheld'))
    # forming lows on every chart
    forming = [f for a in A.ASSETS for tf in A.TFS for f in [W.forming(a, tf)] if f]
    fcards = {c['signal_id']: c for c in feed.get('cards', [])}
    M['cards'] = []; M['forming'] = []
    for f in forming:
        sid = f"{f['a']}-{f['tf']}-{f['d0']}"; loc = f'card forming {sid}'
        gate_on = W.gate(f['tdate']); fc = fcards.get(sid)
        M['forming'].append(dict(sid=sid, chart=f['chart'], tdate=str(f['tdate']), d0=str(f['d0']), need=f['need'], gate=gate_on, tags=A.tagstr(f)))
        eligible = f['tf'] in A.GRADED and gate_on
        if not eligible:
            C.add(loc, 'card exists (8D or gate off at the low: none)', 'present' if fc else 'absent', 'absent', 'forming card on an ungraded chart or with the gate off')
            continue
        if fc is None:
            if not withheld:
                # legitimate only if its sample is empty (note w). The provisional grade is lens logic: read it from liveread.csv
                g_ = None
                try:
                    for r_ in csv.DictReader(open(os.path.join(root, 'datasets', 'liveread.csv'))):
                        if r_['subject'].startswith(f"{f['a']} {f['tf']} forming") and r_['subject'].endswith(f"confirms {f['d0']}") and r_['read'].startswith('Grade '):
                            g_ = r_['read'].split(':')[0].replace('Grade ', '').strip()
                except Exception: pass
                pool_ = [s for s in L if s['a'] == f['a'] and s['grade'] == g_] if g_ else [s for s in L if s['a'] == f['a']]
                C.add(loc, f'card exists (grade {g_}, rule-3 pool {len(pool_)})', 'absent', 'present' if pool_ else 'absent', 'forming card missing')
            continue
        grade = fc['grade']; lens = lens_of(fc.get('confirmations'))
        basis, G = sample(L, f['a'], f['tf'], grade, lens)
        mc = dict(signal_id=sid, chart=f['chart'], asset=f['a'], timeframe=f['tf'], low_date=str(f['tdate']), low_day=str(W.low_day(f['a'], f['tf'], f['tdate'])),
                  confirms_on=str(f['d0']), bars_to_confirm=f['need'], must_close_above=f['kill'], price_now=rha(f['price'], 2), entry_close=None, sample=basis)
        fg = figs(G)
        if fg is None:
            C.add(loc, 'card exists (empty sample: none)', 'present', 'absent', 'card with an empty sample'); continue
        mc.update(fg); cmp_card(loc, fc, mc)
        if f['kill'] is not None and fc.get('must_close_above') is not None:
            ch = W.ch[(f['a'], f['tf'])]; base = ch.cf[:-1] if f['need'] == 0 else ch.cf; x = float(fc['must_close_above'])
            C.add(loc, 'close AT must_close_above does not confirm', A.rsi14(base + [x])[-1] <= f['ctv'], True, 'must_close_above')
            C.add(loc, 'close 1 cent above confirms', A.rsi14(base + [round(x + 0.01, 2)])[-1] > f['ctv'], True, 'must_close_above')
        j = jsonable(mc); j['grade'] = grade; j['confirmations'] = fc.get('confirmations'); M['cards'].append(j)
    for sid in fcards:
        if sid not in {m['sid'] for m in M['forming']}: C.add(f'card forming {sid}', 'card exists', 'present', 'absent', 'card for a low I do not find forming')

    # example card
    xc = feed.get('example_card'); M['example_card'] = None
    exs = next((s for s in L if s['a'] == 'ETH' and s['tf'] == '2D' and s['d0'] == A.EX_DATE), None)
    if exs is not None:
        basis, G = sample(known, 'ETH', '2D', exs['grade'], exs['lens'], example=True)
        mc = dict(signal_id='ETH-2D-2024-09-22', chart='ETH 2D', asset='ETH', timeframe='2D', low_date=str(exs['tdate']), low_day=str(W.low_day('ETH', '2D', exs['tdate'])),
                  confirms_on='2024-09-22', bars_to_confirm=None, must_close_above=None, price_now=None, entry_close=rha(exs['entry'], 2), sample=basis)
        fg = figs(G)
        if fg: mc.update(fg)
        if xc is None:
            if not withheld: C.add('card example', 'exists', 'absent', 'present', 'example card missing')
        else:
            cmp_card('card example', xc, mc)
            C.add('card example', 'grade = ledger grade', xc.get('grade'), exs['grade'], 'example grade')
            C.add('card example', 'confirmations = ledger lenses', '|'.join(sorted(lens_of(xc.get('confirmations')))), '|'.join(sorted(exs['lens'])), 'example lenses')
            C.add('card example', 'example flag', xc.get('example'), True, 'example flag')
        j = jsonable(mc); j['grade'] = exs['grade']; M['example_card'] = j
    elif xc is not None: C.add('card example', 'exists', 'present', 'absent', 'example card before its 60 days closed')

    # ------------------------------------------------------------ 6. open signals
    fo = {o['signal_id']: o for o in feed.get('open_signals', [])}
    M['open_signals'] = []
    myopen = [s for a in A.ASSETS for tf in A.GRADED for s in W.sig[(a, tf)] if s['d0'] is not None and 0 <= (today - s['d0']).days <= 60]
    myopen.sort(key=lambda s: (str(s['d0']), s['chart']))
    if not withheld:
        C.add('open_signals', 'ids', ' '.join(o['signal_id'] for o in feed.get('open_signals', [])), ' '.join(f"{s['a']}-{s['tf']}-{s['d0']}" for s in myopen), 'open signal list')
    for s in myopen:
        sid = f"{s['a']}-{s['tf']}-{s['d0']}"; loc = f'open {sid}'; o = fo.get(sid)
        if o is None: continue
        dyy = W.day[s['a']]; e = s['entry']; ks = W.window(s['a'], s['d0']) or []
        mark = lambda m_: next((rha((dyy.c[k] / e - 1) * 100, 1) for k in ks if (dyy.date[k] - s['d0']).days == m_), None)
        best = rha((max(dyy.h[k] for k in ks) / e - 1) * 100, 1) if ks else None
        worst = rha((min(dyy.l[k] for k in ks) / e - 1) * 100, 1) if ks else None
        grade = o['grade']; lens = frozenset(x for x in (o.get('confirmations') or '').split(' + ') if x and x != '-')
        basis, G = sample(L, s['a'], s['tf'], grade, lens); fg = figs(G)
        mo = dict(signal_id=sid, chart=s['chart'], entry_date=str(s['d0']), entry_close=rha(e, 2), tags=A.tagstr(s), days_elapsed=(today - s['d0']).days,
                  day10_pct=mark(10), day30_pct=mark(30), day60_pct=mark(60), best_so_far_pct=best, worst_so_far_pct=worst)
        lvl = fg['_edge'] if fg else None       # an empty sample has no ladder, so no edge level (FEED_SPEC audit #9: "else empty")
        if lvl == 0: st = 'lost'
        else:
            st = 'intact'
            for k in ks:
                if lvl is not None and dyy.l[k] * 100 <= e * (100 + lvl): st = 'lost'; break
                if dyy.h[k] * 100 >= e * 110: st = 'rose10'; break
        mo['edge_level_pct'] = lvl; mo['edge_status'] = st
        for k_, v in mo.items(): C.add(loc, k_, o.get(k_), v, 'open signal')
        fc = o.get('card')
        if fc is None: C.add(loc, 'card exists', 'absent', 'present', 'live signal without a card')
        mc = dict(signal_id=sid, chart=s['chart'], asset=s['a'], timeframe=s['tf'], low_date=str(s['tdate']), low_day=str(W.low_day(s['a'], s['tf'], s['tdate'])),
                  confirms_on=str(s['d0']), bars_to_confirm=None, must_close_above=None, price_now=rha(dyy.c[-1], 2), entry_close=rha(e, 2), sample=basis)
        if fg: mc.update(fg)
        else: mc.update(past_trades=0, past_signals=0, rose10_within60d_pct=None, rose10_never_fell25_within60d_pct=None, typical_biggest_rise_exact_pct=None)
        if fc is not None:
            cmp_card(loc + ' card', fc, mc)
            C.add(loc + ' card', 'grade = open signal grade', fc.get('grade'), grade, 'card grade')
            C.add(loc + ' card', 'confirmations = open signal lenses', '|'.join(sorted(lens_of(fc.get('confirmations')))), '|'.join(sorted(lens)), 'card lenses')
        jm = jsonable(mo); jm['grade'] = grade; jc = jsonable(mc); jc['grade'] = grade; jm['card'] = jc; jc['_empty'] = not fg
        M['open_signals'].append(jm)
    # prints
    myprints = []
    for a in A.ASSETS:
        for tf in A.TFS:
            conf = [s for s in W.sig[(a, tf)] if s['d0'] is not None]
            for s in conf[-3:]: myprints.append((f'{a} {tf}', 'confirmed', str(s['tdate']), str(s['d0']), rha(s['entry'], 2), A.tagstr(s), 'regime on' if W.gate(s['tdate']) else 'regime off'))
            f = next((x for x in forming if x['a'] == a and x['tf'] == tf), None)
            if f: myprints.append((f'{a} {tf}', 'forming', str(f['tdate']), str(f['d0']), rha(f['price'], 2), A.tagstr(f),
                                   ('regime on' if W.gate(f['tdate']) else 'regime off') + f"; {f['need']} bar(s) to confirm"))
    fp = feed.get('prints', [])
    if not feed.get('feed_error'):
        C.add('prints', 'count', len(fp), len(myprints), 'prints list')
        fpk = {(p['chart'], p['state'], p['confirms_on']): p for p in fp}
        for ch_, st_, td, d0_, en, tg, note in myprints:
            p = fpk.get((ch_, st_, d0_)); loc = f'print {ch_} {st_} {d0_}'
            if p is None: C.add(loc, 'exists', 'absent', 'present', 'print missing'); continue
            C.add(loc, 'low_date', p.get('low_date'), td, 'print'); C.add(loc, 'entry_close', p.get('entry_close'), en, 'print')
            C.add(loc, 'tags', p.get('tags'), tg, 'print tags'); C.add(loc, 'note', p.get('note'), note, 'print note')
            C.add(loc, 'provisional', p.get('provisional'), st_ != 'confirmed', 'print'); C.add(loc, 'signal_id', p.get('signal_id'), f"{ch_.replace(' ', '-')}-{d0_}", 'print id')

    # ------------------------------------------------------------ 7. past paths
    def paths(G, a):
        dyy = W.day[a]; P = []
        for s in G:
            p = [Fr(0)]
            for k in range(1, 61):
                i = dyy.pos.get(s['d0'] + DAYS(k))
                if i is None: p = None; break
                p.append((dyy.c[i] / s['entry'] - 1) * 100)
            if p: P.append(p)
        if not P: return None
        return dict(signals=len(P), days=[dict(day=d_, q25_pct=rha(quant([p[d_] for p in P], Fr(1, 4)), 1), median_pct=rha(quant([p[d_] for p in P], Fr(1, 2)), 1),
                                              q75_pct=rha(quant([p[d_] for p in P], Fr(3, 4)), 1)) for d_ in range(61)])
    def cmp_paths(loc, fpth, mp):
        C.add(loc, 'signals', fpth.get('signals'), mp['signals'], 'past paths n')
        fd = {x['day']: x for x in fpth.get('days', [])}
        C.add(loc, 'days', len(fd), 61, 'past paths days')
        for r in mp['days']:
            for k_ in ('q25_pct', 'median_pct', 'q75_pct'): C.add(loc, f"day {r['day']} {k_}", (fd.get(r['day']) or {}).get(k_), r[k_], 'past paths')
    M['past_paths'] = []
    fpp = {p['asset']: p for p in feed.get('past_paths', [])}
    for a in aplus_assets:
        mp = paths([s for s in L if s['a'] == a and s['grade'] == 'A+'], a)
        if not mp: continue
        M['past_paths'].append(dict(asset=a, **jsonable(mp)))
        C.add(f'past_paths {a}', 'n = top-grade ledger signals', mp['signals'], len([s for s in L if s['a'] == a and s['grade'] == 'A+']), 'path skipped')
        if a in fpp: cmp_paths(f'past_paths {a}', fpp[a], mp)
        elif not feed.get('extras_withheld'): C.add(f'past_paths {a}', 'exists', 'absent', 'present', 'past_paths missing')
    M['example_past_paths'] = None
    xp = feed.get('example_past_paths')
    if exk:
        mp = paths(exk, 'ETH'); M['example_past_paths'] = jsonable(mp)
        if xp is not None: cmp_paths('example_past_paths', xp, mp)
        elif not feed.get('extras_withheld'): C.add('example_past_paths', 'exists', 'absent', 'present', 'example paths missing')
    elif xp is not None: C.add('example_past_paths', 'exists', 'present', 'absent', 'example paths with no known signals')
    M['clamped'] = [(a + tf, str(c[0]), c[1]) for (a, tf), ch in W.ch.items() for c in ch.clamped]
    M['generated_at'] = feed.get('generated_at')
    return C, M, W, feed
