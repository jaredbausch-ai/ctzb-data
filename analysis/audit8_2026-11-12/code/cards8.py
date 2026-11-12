import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from sigs import *

PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
SPLIT = dt.date(2022, 1, 1)


def ledger_with_grades(st):
    L = my_ledger(st)
    for r in csv.DictReader(open(STATES[st] + '/datasets/ledger.csv')):
        k = (r['chart'], r['entry'])
        L[k]['grade'] = r['grade']
        L[k]['lensset'] = frozenset(x for x in r['lenses'].split(' + ') if x != '-')
    return L


def choose(L, chart, a, tf, g, lenses, known_by=None):
    rows = [x for x in L.values() if known_by is None or x['d0'] + dt.timedelta(days=60) <= known_by]
    ex = [x for x in rows if x['chart'] == chart and x['lensset'] == lenses]
    sg = [x for x in rows if x['chart'] == chart and x['grade'] == g]
    ag = [x for x in rows if x['asset'] == a and x['grade'] == g]
    if known_by is None:
        if len(ex) >= 15: return f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex
        if len(sg) >= 15: return f'all {len(sg)} past {a} {tf} signals graded {g} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
        return f'all {len(ag)} past grade {g} signals across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag
    if len(ex) >= 15: return f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', ex
    if len(sg) >= 15: return f'all {len(sg)} {a} {tf} signals graded {g} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
    return f'all {len(ag)} grade {g} signals across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', ag


def figures(st, G):
    n = len(G); M = [x['m'] for x in G]
    P = lambda f: pct(sum(bool(f(m)) for m in M), n)
    sc = []
    for x in G:
        vr = volratio(st, x['asset'], x['d0'])
        if vr is not None: sc.append(float(x['m']['up']) >= 20 * vr)
    old = [x for x in G if x['d0'] < SPLIT]; new = [x for x in G if x['d0'] >= SPLIT]
    sv = lambda X: pct(sum(x['m']['surv10'] for x in X), len(X)) if X else None
    mu, mp, md = med([m['up'] for m in M]), med([m['ddpk'] for m in M]), med([m['dd'] for m in M])
    out = dict(past_trades=n, past_signals=n, rose10_never_fell25_within60d_pct=P(lambda m: m['surv10']),
               beat_normal_move_pct=pct(sum(sc), len(sc)) if sc else None, rose20_within60d_pct=P(lambda m: m['r20']),
               rose10_within60d_pct=P(lambda m: m['r10']), typical_biggest_rise_pct=rhaz(mu, 1), typical_dip_before_rise_pct=rhaz(mp, 1),
               typical_deepest_dip_pct=rhaz(md, 1), typical_biggest_rise_exact_pct=rhaz(mu, 6), typical_dip_before_rise_exact_pct=rhaz(mp, 6),
               typical_deepest_dip_exact_pct=rhaz(md, 6), fell30_within60d_pct=P(lambda m: m['t30']))
    out['before_2022.past_trades'] = len(old); out['before_2022.past_signals'] = len(old); out['before_2022.rose10_never_fell25_within60d_pct'] = sv(old)
    out['since_2022.past_trades'] = len(new); out['since_2022.past_signals'] = len(new); out['since_2022.rose10_never_fell25_within60d_pct'] = sv(new)
    t10 = [m['d10'] for m in M if m['d10'] is not None]; t20 = [m['d20'] for m in M if m['d20'] is not None]
    out['typical_day_first_rose10'] = rhaz(med(t10)) if t10 else None
    out['typical_day_first_rose20'] = rhaz(med(t20)) if t20 else None
    out['typical_day_of_60d_high'] = rhaz(med([m['dpk'] for m in M]))
    out['typical_day_of_deepest_dip'] = rhaz(med([m['ddday'] for m in M]))
    out['from_entry.past_trades'] = n; out['from_entry.past_signals'] = n
    out['from_entry.still_rose10_pct'] = P(lambda m: m['l0'] == 'ok'); out['from_entry.went_on_to_fall25_pct'] = P(lambda m: m['l0'] == 'liq')
    for i, th in enumerate((5, 10, 15, 20)):
        hits = [m['lad'][th] for m in M if m['lad'][th] is not None]
        h = len(hits)
        out[f'if_it_falls_first[{i}].fell_pct'] = th
        out[f'if_it_falls_first[{i}].past_trades'] = h; out[f'if_it_falls_first[{i}].past_signals'] = h
        out[f'if_it_falls_first[{i}].still_rose10_pct'] = pct(sum(x[1] == 'ok' for x in hits), h) if h else None
        out[f'if_it_falls_first[{i}].went_on_to_fall25_pct'] = pct(sum(x[1] == 'liq' for x in hits), h) if h else None
    out['_exact'] = (mu, mp, md)
    return out


def flat(c):
    o = {}
    for k, v in c.items():
        if isinstance(v, dict):
            for k2, v2 in v.items(): o[f'{k}.{k2}'] = v2
        elif k == 'if_it_falls_first':
            for i, r in enumerate(v):
                for k2, v2 in r.items(): o[f'{k}[{i}].{k2}'] = v2
        else:
            o[k] = v
    return o


def low_day(st, a, tf, tdate):
    b, pos, _ = daily(st, a)
    end = bar_last_day(tdate, tf)
    days = [tdate + dt.timedelta(days=i) for i in range((end - tdate).days + 1)]
    cand = [(b[pos[d]]['l'], d) for d in days if d in pos]
    return str(min(cand)[1])


def provisional(st, a, tf):
    v = all_signals(st)[(a, tf)]; ct = v['ct']; bars = v['bars']; n = len(bars)
    for back in (1, 2, 3):
        ti = n - 1 - back
        x = ct[ti]
        if x is None: continue
        if not all(ct[j] is not None and ct[j] > x for j in range(ti - 3, ti)): continue
        if not all(ct[j] > x for j in range(ti + 1, n)): continue
        return dict(ti=ti, need=3 - back, tdate=bars[ti]['d'], ct=x)
    return None


def conf_close_day(bars, ti, tf, k=3):
    """close day of bar ti+k, following the calendar rule for bars that don't exist yet."""
    d = bars[ti]['d']
    for _ in range(k):
        d = bar_last_day(d, tf) + dt.timedelta(days=1)
    return bar_last_day(d, tf)


def kill_close(st, a, tf, p):
    v = all_signals(st)[(a, tf)]; bars = v['bars']; n = len(bars)
    C = [b['cf'] for b in bars]
    if p['need'] == 0: base = C[:-1]
    elif p['need'] == 1: base = C
    else: return None
    lo, hi = C[-1] * 0.2, C[-1] * 3.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if rsi(base + [mid])[-1] <= p['ct']: lo = mid
        else: hi = mid
    return lo
