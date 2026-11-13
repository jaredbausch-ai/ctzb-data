"""My own computation of everything in the feed that a member sees (cards, open signals, prints, odds fade,
paths, top-level). Grade and lenses are taken as given (ledger rows, card/open-signal fields)."""
import datetime as dt, math, statistics as st, csv, os, json
import a16lib as L
import funding as F

PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
gp = lambda g: 'the top grade' if g == 'A+' else 'the same grade'
SPLIT = dt.date(2022, 1, 1)


def pool(S, known_by=None):
    """ledger rows joined to my signals + measures. known_by: only signals with d0+60 <= that date."""
    out = []
    for r in S.ledger:
        s = S.by.get((r['chart'], r['entry']))
        if s is None or s['m'] is None:
            continue
        if known_by is not None and s['d0'] + dt.timedelta(days=60) > known_by:
            continue
        x = dict(s); x['grade'] = r['grade']; x['lens'] = frozenset(k for k in r['lenses'].split(' + ') if k and k != '-')
        ra = S.vol[s['asset']].ratio(s['d0']); x['sc'] = None if ra is None else s['m']['up'] >= 20 * ra
        out.append(x)
    return out


def pick_sample(P, asset, tf, grade, lens, example=False):
    chart = f'{asset} {tf}'
    ex = [x for x in P if x['chart'] == chart and x['lens'] == lens]
    sg = [x for x in P if x['chart'] == chart and x['grade'] == grade]
    ag = [x for x in P if x['asset'] == asset and x['grade'] == grade]
    if not example:
        if len(ex) >= 15: return ex, f'all {len(ex)} past {asset} {tf} signals with exactly the same confirmations', 1
        if len(sg) >= 15: return sg, f'all {len(sg)} past {asset} {tf} signals of {gp(grade)} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', 2
        return ag, f'all {len(ag)} past signals of {gp(grade)} across all {asset} charts ({asset} {tf} alone has only {len(sg)}, too few to use)', 3
    if len(ex) >= 15: return ex, f'all {len(ex)} {asset} {tf} signals with exactly the same confirmations whose 60 days had closed by then', 1
    if len(sg) >= 15: return sg, f'all {len(sg)} {asset} {tf} signals of {gp(grade)} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', 2
    return ag, f'all {len(ag)} signals of {gp(grade)} across all {asset} charts whose 60 days had closed by then ({asset} {tf} alone had only {len(sg)}, too few to use)', 3


def pctr(k, n):
    return L.rhaz(100 * k / n) if n else None


def card_figs(S, G):
    """every sample figure on a card, from my measures"""
    n = len(G); o = {}
    surv = lambda x: x['m']['up'] >= 10 and x['m']['dd'] > -25.3
    o['past_trades'] = n
    o['rose10_never_fell25_within60d_pct'] = pctr(sum(surv(x) for x in G), n)
    sc = [x['sc'] for x in G if x['sc'] is not None]
    o['beat_normal_move_pct'] = pctr(sum(sc), len(sc))
    o['rose20_within60d_pct'] = pctr(sum(x['m']['up'] >= 20 for x in G), n)
    o['rose10_within60d_pct'] = pctr(sum(x['m']['up'] >= 10 for x in G), n)
    for f, k in (('typical_biggest_rise', 'up'), ('typical_dip_before_rise', 'ddpk'), ('typical_deepest_dip', 'dd')):
        med = st.median(x['m'][k] for x in G) if n else None
        o[f + '_pct'] = L.rhaz(med, 1) if n else None
        o[f + '_exact_pct'] = L.rhaz(med, 6) if n else None
        o[f + '_full'] = med
    o['fell30_within60d_pct'] = pctr(sum(x['m']['dd'] <= -30 for x in G), n)
    old = [x for x in G if x['d0'] < SPLIT]; new = [x for x in G if x['d0'] >= SPLIT]
    o['before_2022'] = dict(past_trades=len(old), rose10_never_fell25_within60d_pct=pctr(sum(surv(x) for x in old), len(old)))
    o['since_2022'] = dict(past_trades=len(new), rose10_never_fell25_within60d_pct=pctr(sum(surv(x) for x in new), len(new)))
    fe = [L.from_entry_outcome(S.day[x['asset']], x['d0'], x['entry']) for x in G]
    o['from_entry'] = dict(past_trades=n, still_rose10_pct=pctr(fe.count('ok'), n), went_on_to_fall25_pct=pctr(fe.count('liq'), n),
                           still_rose10_exact_pct=L.rhaz(100 * fe.count('ok') / n, 6) if n else None,
                           _full=100 * fe.count('ok') / n if n else None)
    o['if_it_falls_first'] = []
    for th in (5, 10, 15, 20):
        lo = [L.ladder_outcome(S.day[x['asset']], x['d0'], x['entry'], th) for x in G]
        hit = sum(v is not None for v in lo)
        o['if_it_falls_first'].append(dict(fell_pct=th, past_trades=hit, still_rose10_pct=pctr(lo.count('ok'), hit),
                                           went_on_to_fall25_pct=pctr(lo.count('liq'), hit),
                                           still_rose10_exact_pct=L.rhaz(100 * lo.count('ok') / hit, 6) if hit else None,
                                           _full=100 * lo.count('ok') / hit if hit else None))
    medr = lambda xs: L.rhaz(st.median(xs)) if xs else None
    t10 = [v for v in (L.first_day_reach(S.day[x['asset']], x['d0'], x['entry'], 10) for x in G) if v is not None]
    t20 = [v for v in (L.first_day_reach(S.day[x['asset']], x['d0'], x['entry'], 20) for x in G) if v is not None]
    o['typical_day_first_rose10'] = medr(t10); o['typical_day_first_rose20'] = medr(t20)
    o['typical_day_of_60d_high'] = medr([x['m']['dpk'] for x in G]); o['typical_day_of_deepest_dip'] = medr([x['m']['ddday'] for x in G])
    # the edge: first ladder level whose exact (full precision) share is below 70
    if o['from_entry']['_full'] is not None and o['from_entry']['_full'] < 70: o['_edge'] = 0
    else:
        o['_edge'] = next((-r['fell_pct'] for r in o['if_it_falls_first'] if r['_full'] is not None and r['_full'] < 70), None)
    return o


def low_day(S, asset, tf, tdate):
    c = S.ch[(asset, tf)]; i = c.b.pos[tdate]
    nxt = c.b.d[i + 1] if i + 1 < c.b.n else L.next_open(tdate, c.step)
    day = S.day[asset]
    cand = [(day.l[day.pos[tdate + dt.timedelta(days=k)]], tdate + dt.timedelta(days=k)) for k in range((nxt - tdate).days) if tdate + dt.timedelta(days=k) in day.pos]
    return min(cand)[1] if cand else tdate


def forming(S, asset, tf):
    """the pivot low still waiting on right-hand bars: ti within the last 3 bars before the open one"""
    c = S.ch[(asset, tf)]; ct, k, n = c.ct, c.k, c.b.n
    for back in (1, 2, 3):
        ti = n - 1 - back
        if ti < 3 or ct[ti] is None or any(ct[j] is None for j in range(ti - 3, ti)): continue
        if not all(ct[j] > ct[ti] for j in range(ti - 3, ti)): continue
        if any(ct[j] < ct[ti] for j in range(ti + 1, n)): continue
        need = 3 - back
        co = c.b.d[-1]
        for _ in range(need): co = L.next_open(co, c.step)
        conf_close = L.next_open(co, c.step) - L.ONE
        prevs = [p for p in c.piv if p < ti]
        v, kk = ct[ti], k[ti]
        dis = False
        if prevs and kk is not None:
            dct, dk = v - ct[prevs[-1]], kk - k[prevs[-1]]
            dis = (dct > L.EPS and dk < -L.EPS) or (dct < -L.EPS and dk > L.EPS)
        strong = dis and v < 50; prime = kk is not None and 20 <= kk < 50
        # must close above: the conf-bar close at which CT(conf bar) equals CT(trough); only if conf bar is the open bar or the next
        kill = None
        if need in (0, 1):
            base = c.b.c[:-1] if need == 0 else c.b.c[:]
            lo, hi = c.b.c[-1] * 0.5, c.b.c[-1] * 1.5
            f = lambda x: L.wilder_rsi(base[-400:] + [x])[-1] if False else None
            # exact: Wilder state up to the bar before the confirmation bar
            gains = [max(base[i] - base[i - 1], 0.0) for i in range(1, len(base))]; losses = [max(base[i - 1] - base[i], 0.0) for i in range(1, len(base))]
            ag = sum(gains[:14]) / 14; al = sum(losses[:14]) / 14
            for i in range(14, len(gains)):
                ag = (ag * 13 + gains[i]) / 14; al = (al * 13 + losses[i]) / 14
            p = base[-1]
            def rsi_at(x):
                g2 = (ag * 13 + max(x - p, 0.0)) / 14; l2 = (al * 13 + max(p - x, 0.0)) / 14
                return 100.0 if l2 == 0 else 100.0 - 100.0 / (1.0 + g2 / l2)
            for _ in range(200):
                mid = (lo + hi) / 2
                if rsi_at(mid) <= v: lo = mid
                else: hi = mid
            kill = lo
        return dict(asset=asset, tf=tf, chart=c.name, ti=ti, tdate=c.b.d[ti], need=need, confirms=conf_close, price=c.b.c[-1],
                    bk=L.bucket(v), dis=dis, strong=strong, prime=prime, tags=L.tagstr(L.bucket(v), dis, strong, prime), kill=kill,
                    gate_on=S.gate(c.b.d[ti]), low_day=low_day(S, asset, tf, c.b.d[ti]))
    return None


def open_list(S):
    """gated confirmed signals on graded charts whose 60th day's daily bar has not closed yet"""
    out = []
    for s in S.sigs:
        if s['tf'] not in L.TFS_G or s['d0'] is None: continue
        if s['d0'] < S.today and s['d0'] + dt.timedelta(days=60) >= S.today:
            out.append(s)
    return sorted(out, key=lambda s: (str(s['d0']), s['chart']))


def open_progress(S, s):
    day = S.day[s['asset']]; e = s['entry']; d0 = s['d0']
    ks = [k for k in range(day.pos[d0] + 1, day.n) if day.d[k] < S.today and (day.d[k] - d0).days <= 60]
    def mark(m):
        dd = d0 + dt.timedelta(days=m)
        return L.rhaz((day.c[day.pos[dd]] / e - 1) * 100, 1) if dd in day.pos and dd < S.today else None
    return dict(days_elapsed=(S.today - d0).days, day10_pct=mark(10), day30_pct=mark(30), day60_pct=mark(60) if False else None,
                best_so_far_pct=L.rhaz((max(day.h[k] for k in ks) / e - 1) * 100, 1) if ks else None,
                worst_so_far_pct=L.rhaz((min(day.l[k] for k in ks) / e - 1) * 100, 1) if ks else None, ks=ks)


def edge_status(S, s, edge, ks):
    if edge == 0: return 'lost'
    if edge is None: return 'intact'
    day = S.day[s['asset']]; e = s['entry']
    for k in ks:
        if day.l[k] <= e * (1 + edge / 100): return 'lost'
        if day.h[k] >= e * 1.10: return 'intact'
    return 'intact'


# ---------------------------------------------------------------- odds fade (refresh.py's tier rule, my code)
def eth_tier(S, year):
    """chart/tag pairs with 8+ signals whose 60-day outcome (on the chart's own bars) had closed before 1 Jan `year`
    and 70%+ of them closing higher at the end of 60 days."""
    upto = dt.date(year, 1, 1); keep = []; rows = []
    for tf in L.TFS_ALL:
        c = S.ch[('ETH', tf)]; b = c.b
        # running min of CT since it was last at or above 60
        z = []; cur = None
        for v in c.ct:
            if v is None: z.append(None); continue
            cur = None if v >= 60 else (v if cur is None else min(cur, v)); z.append(cur)
        for s in c.sig:
            ei = s['ei']; end = b.d[ei] + dt.timedelta(days=60)
            tg = {s['bk'], 'any trough'}
            if s['dis']: tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
            if s['prime']: tg.add('prime dot')
            if s['dis'] and s['prime']: tg.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and z[s['ti']] is not None and z[s['ti']] >= 50: tg.add('zone-exit B')
            s['tier_tags'] = tg
            win = None
            if b.d[-1] >= end:
                js = [j for j in range(ei + 1, b.n) if b.d[j] <= end]
                if js: win = b.c[js[-1]] / b.c[ei] - 1 > 0
            rows.append(dict(chart=c.name, tf=tf, tags=tg, d=b.d[ei], win=win, s=s))
    for tf in L.TFS_ALL:
        for t in ("any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"):
            sub = [r for r in rows if r['tf'] == tf and t in r['tags'] and r['win'] is not None
                   and r['d'] + dt.timedelta(days=int(tf[:-1]) - 1 + 60) < upto]
            if len(sub) >= 8 and 100 * sum(r['win'] for r in sub) / len(sub) >= 70:
                keep.append((f'ETH {tf}', t))
    return keep, rows


def odds_fade(S):
    keep, rows = eth_tier(S, S.today.year)
    day = S.day['ETH']; pool = []
    for r in rows:
        s = r['s']
        if not any(k[0] == r['chart'] and k[1] in r['tags'] for k in keep): continue
        d0 = s['d0']
        if d0 is None or d0 not in day.pos: continue
        end = d0 + dt.timedelta(days=60)
        if end not in day.pos or end >= S.today: continue
        e = day.c[day.pos[d0]]
        w = [(k, (day.d[k] - d0).days) for k in range(day.pos[d0] + 1, day.pos[end] + 1)]
        first = [k for k, nd in w if nd <= 10]; after = [k for k, nd in w if nd > 10]
        lo10 = min(day.l[k] for k in first); hi_after = max(day.h[k] for k in after)
        k10 = [k for k, nd in w if nd == 10]
        pool.append(dict(dip=(lo10 / e - 1) * 100, r10=hi_after >= e * 1.10, r20=hi_after >= e * 1.20,
                         r10p=(hi_after / e - 1) * 100 >= 10, r20p=(hi_after / e - 1) * 100 >= 20,
                         green=None if not k10 else day.c[k10[0]] >= e, e=e, d0=d0, chart=r['chart']))
    bands = [("shallower than -2%", 100, -2), ("-2% to -5%", -2, -5), ("-5% to -10%", -5, -10), ("-10% to -20%", -10, -20), ("worse than -20%", -20, -100)]
    early = []
    for lab, hi, lo in bands:
        g = [p for p in pool if lo < p['dip'] <= hi]
        if len(g) < 5: continue
        x = 100 * sum(p['r10'] for p in g) / len(g)
        early.append(dict(band=lab, past_trades=len(g), rose10=L.rhaz(x), rose20=L.rhaz(100 * sum(p['r20'] for p in g) / len(g)), exact=x,
                          edge='intact' if x >= 70 else 'gone', pctdiff=sum(p['r10'] != p['r10p'] or p['r20'] != p['r20p'] for p in g)))
    d10 = []
    for lab, want in (("green on day 10", True), ("red on day 10", False)):
        g = [p for p in pool if p['green'] is want]
        if len(g) < 5: continue
        x = 100 * sum(p['r10'] for p in g) / len(g)
        d10.append(dict(check=lab, past_trades=len(g), rose10=L.rhaz(x), rose20=L.rhaz(100 * sum(p['r20'] for p in g) / len(g)), exact=x,
                        edge='intact' if x >= 70 else 'gone'))
    return keep, rows, pool, early, d10


def trades_a_year(S, keep, rows):
    T = {}
    for r in sorted((r for r in rows if r['win'] is not None and any(k[0] == r['chart'] and k[1] in r['tags'] for k in keep)), key=lambda r: r['d']):
        T.setdefault((r['chart'], r['d']), r)
    data_end = max(S.ch[('ETH', tf)].b.d[-1] for tf in L.TFS_ALL)
    span = max(0.25, ((data_end - dt.timedelta(days=60)) - min(r['d'] for r in T.values())).days / 365.25)
    return len(T) / span, len(T)


def paths(S, G):
    """per day 0..60 the quartiles of close/entry-1 over signals with 60 consecutive daily closes"""
    P = []
    for x in G:
        day = S.day[x['asset']]; p = [0.0]
        for k in range(1, 61):
            d = x['d0'] + dt.timedelta(days=k)
            if d not in day.pos: break
            p.append((day.c[day.pos[d]] / x['entry'] - 1) * 100)
        if len(p) == 61: P.append(p)
    return len(P), [dict(day=k, q25_pct=L.rhaz(L.quant([p[k] for p in P], 0.25), 1), median_pct=L.rhaz(L.quant([p[k] for p in P], 0.5), 1),
                         q75_pct=L.rhaz(L.quant([p[k] for p in P], 0.75), 1)) for k in range(61)] if P else []
