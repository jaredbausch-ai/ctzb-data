"""Check 5: every field of the 4 REPLAY cards. Samples re-derived from the ledger (grades and lenses as given),
figures from my own candle measurements."""
import pickle, json, statistics as st
from mine import *
from checks import rec, num_eq, dump, ROWS

state = 'REPLAY'; root = STATES[state]; now = NOWS[state]
U = pickle.load(open(f'{S}/audit3/universe_{state}.pkl', 'rb'))
L = pickle.load(open(f'{S}/audit3/ledger_{state}.pkl', 'rb'))
led = list(csv.DictReader(open(f'{root}/datasets/ledger.csv')))
feed = json.load(open(f'{root}/feed/ctzb_feed.json'))
PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
CL = 'documented flash-print clamp (BTC 2017-04-15 $0.06 low)'
lset = lambda s: frozenset() if s in ('-', '', 'none') else frozenset(x.strip() for x in s.split('+'))
day = {a: Daily(U['day'][a]) for a in U['day']}
vr = {a: vol_ratio_fn(root, a) for a in ('ETH', 'BTC')}


def ladder(G, key='m', literal=False):
    res = []
    for th in (5, 10, 15, 20):
        hit = ok = liq = amb = 0
        for s in G:
            a = s['a']; e = s['entry']
            w = [day[a].b[day[a].pos[s['d0'] + dt.timedelta(days=k)]] for k in range(1, 61)]
            if key == 'mc':
                w = [dict(b, l=max(b['l'], min(b['o'], b['c'])) if b['l'] < 0.5 * min(b['o'], b['c']) else b['l']) for b in w]
            first = None
            for j, b in enumerate(w):
                if b['h'] >= e * 1.10:
                    if b['l'] <= e * (1 - th / 100): amb += 1
                    break
                if b['l'] <= e * (1 - th / 100): first = j; break
            if first is None: continue
            hit += 1
            if literal:
                rose = any(b['h'] >= e * 1.10 for b in w[first:]); fell = any(b['l'] <= e * (1 - LIQ_FRAC) for b in w)
                ok += rose and not fell; liq += any(b['l'] <= e * (1 - LIQ_FRAC) for b in w[first:])
            else:
                for b in w[first:]:
                    if b['l'] <= e * (1 - LIQ_FRAC): liq += 1; break
                    if b['h'] >= e * 1.10: ok += 1; break
        res.append(dict(fell=th, n=hit, ok=100 * ok / hit if hit else None, liq=100 * liq / hit if hit else None, amb=amb))
    return res


def kill_close(bars, ti):
    c = [b['c'] for b in bars]
    ct = my_rsi(c); target = ct[ti]
    lo, hi = c[-1] * 0.5, c[-1] * 1.5
    for _ in range(200):
        mid = (lo + hi) / 2
        if my_rsi(c + [mid])[-1] <= target: lo = mid
        else: hi = mid
    return lo


cards = feed['cards']
for c in cards:
    a, tf = c['asset'], c['timeframe']; loc = f"card {c['signal_id']}"
    bars = U['charts'][(a, tf)]['bars']; ct = U['charts'][(a, tf)]['ct']
    n = len(bars)
    # forming low: pivot with 3 strictly higher bars on the left and every bar since strictly higher
    form = None
    for back in (1, 2):
        ti = n - 1 - back
        if all(ct[j] > ct[ti] for j in range(ti - 3, ti)) and all(ct[j] > ct[ti] for j in range(ti + 1, n)):
            form = ti; break
    rec(state, '5', loc, 'low_date', c['low_date'], str(bars[form]['d']) if form else None, form is not None and c['low_date'] == str(bars[form]['d']), 'trough differs')
    tfd = int(tf[:-1]); need = form + 3 - (n - 1)
    conf_open = bars[-1]['d'] + dt.timedelta(days=tfd * need)
    conf_close = conf_open + dt.timedelta(days=tfd - 1)
    rec(state, '5', loc, 'confirms_on (last day of the confirmation bar)', c['confirms_on'], str(conf_close), c['confirms_on'] == str(conf_close), 'confirmation date differs')
    rec(state, '5', loc, 'bars_to_confirm', c['bars_to_confirm'], need, c['bars_to_confirm'] == need, 'differs')
    rec(state, '5', loc, 'signal_id', c['signal_id'], f'{a}-{tf}-{conf_close}', c['signal_id'] == f'{a}-{tf}-{conf_close}', 'id differs')
    rec(state, '5', loc, 'price_now', c['price_now'], bars[-1]['c'], num_eq(c['price_now'], bars[-1]['c'], 2), 'price differs')
    if need == 1:
        k = kill_close(bars, form)
        rec(state, '5', loc, 'must_close_above', c['must_close_above'], round(k, 4), num_eq(c['must_close_above'], k, 2), 'kill close differs')
    else:
        rec(state, '5', loc, 'must_close_above', c['must_close_above'], None, c['must_close_above'] is None, 'should be blank 2+ bars out')
    # sample
    have = lset(' + '.join(PLAIN[x.strip()] for x in c['confirmations'].split(';') if x.strip() != 'none') if c['confirmations'] != 'none' else '-')
    g = c['grade']
    chart_rows = [r for r in led if r['chart'] == c['chart']]
    ex = [r for r in chart_rows if lset(r['lenses']) == have]
    sg = [r for r in chart_rows if r['grade'] == g]
    ag = [r for r in led if r['asset'] == a and r['grade'] == g]
    if len(ex) >= 15: G_, basis = ex, f'the last {len(ex)} {a} {tf} trades with exactly the same confirmations'
    elif len(sg) >= 15: G_, basis = sg, f'the last {len(sg)} {a} {tf} trades graded {g} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)'
    else: G_, basis = ag, f'the last {len(ag)} grade {g} trades across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)'
    G = [L['mine_led'][(r['chart'], r['entry'])] for r in G_]
    rec(state, '5', loc, 'sample text', c['sample'], basis, c['sample'] == basis, 'sample rule differs')
    rec(state, '5', loc, 'past_trades', c['past_trades'], len(G), c['past_trades'] == len(G), 'sample size differs')
    N = len(G)
    def pct2(lab, fn, shown):
        v = 100 * sum(fn(s['m']) for s in G) / N; v2 = 100 * sum(fn(s['mc']) for s in G) / N
        ok = num_eq(shown, v, 0)
        rec(state, '5', loc, lab, shown, v, ok, CL if (not ok and num_eq(shown, v2, 0)) else f'{lab} differs')
    pct2('rose10_never_fell25_within60d_pct', lambda m: m['surv10'], c['rose10_never_fell25_within60d_pct'])
    pct2('rose20_within60d_pct', lambda m: m['r20'], c['rose20_within60d_pct'])
    pct2('rose10_within60d_pct', lambda m: m['r10'], c['rose10_within60d_pct'])
    pct2('fell30_within60d_pct', lambda m: m['t30'], c['fell30_within60d_pct'])
    sc = [s['m']['up'] >= 20 * vr[a](s['d0']) for s in G if vr[a](s['d0']) is not None]
    v = 100 * sum(sc) / len(sc)
    rec(state, '5', loc, 'beat_normal_move_pct', c['beat_normal_move_pct'], v, num_eq(c['beat_normal_move_pct'], v, 0), 'differs')
    for lab, kk in (('typical_biggest_rise_pct', 'up'), ('typical_dip_before_rise_pct', 'ddpk'), ('typical_deepest_dip_pct', 'dd')):
        v = st.median(s['m'][kk] for s in G); v2 = st.median(s['mc'][kk] for s in G); ok = num_eq(c[lab], v, 1)
        rec(state, '5', loc, lab, c[lab], v, ok, CL if (not ok and num_eq(c[lab], v2, 1)) else f'{lab} differs')
    for era, f in (('before_2022', lambda s: s['d0'] < dt.date(2022, 1, 1)), ('since_2022', lambda s: s['d0'] >= dt.date(2022, 1, 1))):
        X = [s for s in G if f(s)]
        rec(state, '5', loc, f'{era}.past_trades', c[era]['past_trades'], len(X), c[era]['past_trades'] == len(X), 'era count differs')
        v = 100 * sum(s['m']['surv10'] for s in X) / len(X); v2 = 100 * sum(s['mc']['surv10'] for s in X) / len(X)
        ok = num_eq(c[era]['rose10_never_fell25_within60d_pct'], v, 0)
        rec(state, '5', loc, f'{era}.rose10_never_fell25_within60d_pct', c[era]['rose10_never_fell25_within60d_pct'], v, ok,
            CL if (not ok and num_eq(c[era]['rose10_never_fell25_within60d_pct'], v2, 0)) else 'era share differs')
    t10 = [s['m']['d10'] for s in G if s['m']['d10'] is not None]; t20 = [s['m']['d20'] for s in G if s['m']['d20'] is not None]
    for lab, xs in (('typical_day_first_rose10', t10), ('typical_day_first_rose20', t20),
                    ('typical_day_of_60d_high', [s['m']['dpk'] for s in G]), ('typical_day_of_deepest_dip', [s['m']['ddday'] for s in G])):
        v = st.median(xs); v2 = st.median([s['mc']['ddday'] for s in G]) if lab == 'typical_day_of_deepest_dip' else None
        ok = num_eq(c[lab], v, 0)
        rec(state, '5', loc, lab, c[lab], v, ok, CL if (not ok and v2 is not None and num_eq(c[lab], v2, 0)) else f'{lab} differs')
    lad = ladder(G); ladc = ladder(G, 'mc'); lit = ladder(G, literal=True)
    for fr, mr, mc, ml in zip(c['if_it_falls_first'], lad, ladc, lit):
        l2 = f"{loc} falls {fr['fell_pct']}% first"
        rec(state, '5', l2, 'past_trades', fr['past_trades'], mr['n'], fr['past_trades'] == mr['n'], CL if fr['past_trades'] == mc['n'] else 'count differs')
        for lab, kk in (('still_rose10_pct', 'ok'), ('went_on_to_fall25_pct', 'liq')):
            ok = num_eq(fr[lab], mr[kk], 0)
            rec(state, '5', l2, lab, fr[lab], mr[kk], ok, CL if (not ok and num_eq(fr[lab], mc[kk], 0)) else f'{lab} differs')
        if not num_eq(fr['still_rose10_pct'], ml['ok'], 0):
            rec(state, '5', l2, 'still_rose10_pct (CARD_SPEC literal: rose 10% after the fall AND never fell 25.3% in the 60 days)',
                fr['still_rose10_pct'], ml['ok'], False, 'ladder counts +10% reached before -25.3%, even if -25.3% comes later')
        if mr['amb']:
            rec(state, '5', l2, 'same-day ambiguity', '', mr['amb'], True, '')
    # confluences
    for x in c['active_confluences']:
        ca, ctf = x['after'].split()[:2]; ctag = x['after'].split()[2]
        csig = [s for s in U['sig'][(ca, ctf)] if s['gated'] and s['d0'] is not None]
        tagok = (lambda s: True) if ctag == 'any' else (lambda s: s['bk'] == ctag)
        conf = [s for s in csig if 0 <= (conf_close - s['d0']).days <= 10 and tagok(s)]
        l2 = f"{loc} confluence after {x['after']}"
        rec(state, '5', l2, 'after_confirmed', x['after_confirmed'], str(conf[-1]['d0']) if conf else None, bool(conf) and x['after_confirmed'] == str(conf[-1]['d0']), 'differs')
        wc = str(conf[-1]['d0'] + dt.timedelta(days=10)) if conf else None
        rec(state, '5', l2, 'window_closes', x['window_closes'], wc, x['window_closes'] == wc, 'differs')
        hist = [s for s in U['sig'][(a, tf)] if s['gated'] and s.get('m') and any(0 <= (s['d0'] - y['d0']).days <= 10 and tagok(y) for y in csig)]
        rec(state, '5', l2, 'past_trades', x['past_trades'], len(hist), x['past_trades'] == len(hist), 'differs')
        for lab, fn in (('rose20_within60d_pct', lambda m: m['r20']), ('rose10_within60d_pct', lambda m: m['r10']), ('fell30_within60d_pct', lambda m: m['t30'])):
            v = 100 * sum(fn(s['m']) for s in hist) / len(hist); v2 = 100 * sum(fn(s['mc']) for s in hist) / len(hist)
            ok = num_eq(x[lab], v, 0)
            rec(state, '5', l2, lab, x[lab], v, ok, CL if (not ok and num_eq(x[lab], v2, 0)) else 'differs')
    pickle.dump(None, open('/dev/null', 'wb'))
dump('part5.csv')
for r in ROWS:
    if r['ok'] == 'no' or 'ambiguity' in r['label']: print(r)
print(len(ROWS))
