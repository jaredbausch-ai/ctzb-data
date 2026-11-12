"""Check 5: every card in feed['cards'] recomputed from my candle measures over the like-for-like sample."""
import csv, json, math, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C

OUT = os.path.dirname(os.path.abspath(__file__))
R = list(csv.DictReader(open(os.path.join(OUT, 'ledger_recomputed.csv'))))
for r in R:
    for k in ('up', 'dd', 'ret', 'ddpk', 'e'): r[k] = float(r[k])
    r['surv10'] = r['surv10'] == 'True'
    for k in ('highs', 'lows'): r[k] = json.loads(r[k])
    for k in ('t10', 't20'): r[k] = None if r[k] == '' else int(r[k])
    for k in ('dpk', 'ddday'): r[k] = int(r[k])
F = json.load(open(os.path.join(C.REPO, 'feed', 'ctzb_feed.json')))
WORDS = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}

# my own volatility ratio (stated: 365-day daily vol at entry / 2016-21 median)
def volmap(a):
    b, _ = C.daily(a)
    c = [x['c'] for x in b]
    lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
    v = {}
    for i in range(365, len(c)):
        w = lr[i - 364:i + 1]; mu = sum(w) / len(w)
        v[b[i]['d']] = math.sqrt(sum((x - mu) ** 2 for x in w) / len(w))
    med = C.median([x for d, x in v.items() if d.year <= 2021])
    return v, med
VM = {a: volmap(a) for a in ('ETH', 'BTC')}

def ladder(G, th, same_day='rise_first'):
    hit = ok = liq = 0
    for r in G:
        e = r['e']; H, L = r['highs'], r['lows']
        for j in range(60):
            rose = H[j] >= e * 1.10; fell = L[j] <= e * (1 - th / 100)
            if rose and (not fell or same_day == 'rise_first'): break
            if fell:
                hit += 1
                for k in range(j, 60):
                    if L[k] <= e * (1 + C.LIQ / 100): liq += 1; break
                    if H[k] >= e * 1.10: ok += 1; break
                break
    return hit, ok, liq

res = []
def cmp(where, field, shown, mine, tol=0):
    ok = (shown is None and mine is None) or (shown is not None and mine is not None and abs(float(shown) - float(mine)) <= tol + 1e-9)
    res.append(dict(check='5', where=where, field=field, shown=shown, mine=mine, ok=ok))

pct = lambda G, f: C.r_half(100 * sum(1 for r in G if f(r)) / len(G)) if G else None
for c in F['cards']:
    a, tf, ch = c['asset'], c['timeframe'], c['chart']
    lens = set() if c['confirmations'] == 'none' else {WORDS[x] for x in c['confirmations'].split('; ')}
    s = c['sample']
    if 'exactly the same confirmations' in s and ' graded ' not in s:
        G = [r for r in R if r['chart'] == ch and set(x for x in r['lenses'].split(' + ') if x != '-') == lens]
        rule = 'exact lenses'
    elif f'{ch} trades graded' in s:
        G = [r for r in R if r['chart'] == ch and r['grade'] == c['grade']]
        rule = 'chart+grade'
        ex = [r for r in R if r['chart'] == ch and set(x for x in r['lenses'].split(' + ') if x != '-') == lens]
        res.append(dict(check='5', where=f'5: card {c["signal_id"]}', field='sample text: exact-lens count', shown=s, mine=f'{len(ex)} exact-lens rows', ok=f'only {len(ex)} had' in s))
    else:
        G = [r for r in R if r['asset'] == a and r['grade'] == c['grade']]; rule = 'asset+grade'
    w = f'5: card {c["signal_id"]} ({rule})'
    cmp(w, 'past_trades', c['past_trades'], len(G))
    cmp(w, 'rose10_within60d_pct', c['rose10_within60d_pct'], pct(G, lambda r: r['up'] >= 10))
    cmp(w, 'rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], pct(G, lambda r: r['surv10']))
    cmp(w, 'rose20_within60d_pct', c['rose20_within60d_pct'], pct(G, lambda r: r['up'] >= 20))
    cmp(w, 'fell30_within60d_pct', c['fell30_within60d_pct'], pct(G, lambda r: r['dd'] <= -30))
    cmp(w, 'typical_biggest_rise_pct', c['typical_biggest_rise_pct'], round(C.median([r['up'] for r in G]), 1), 0.05)
    cmp(w, 'typical_deepest_dip_pct', c['typical_deepest_dip_pct'], round(C.median([r['dd'] for r in G]), 1), 0.05)
    cmp(w, 'typical_dip_before_rise_pct', c['typical_dip_before_rise_pct'], round(C.median([r['ddpk'] for r in G]), 1), 0.05)
    sc = []
    for r in G:
        v = VM[a][0].get(dt.date.fromisoformat(r['entry']))
        if v is not None: sc.append(r['up'] >= 20 * v / VM[a][1])
    cmp(w, 'beat_normal_move_pct', c['beat_normal_move_pct'], C.r_half(100 * sum(sc) / len(sc)) if sc else None)
    old = [r for r in G if r['entry'] < '2022-01-01']; new = [r for r in G if r['entry'] >= '2022-01-01']
    cmp(w, 'before_2022.past_trades', c['before_2022']['past_trades'], len(old))
    cmp(w, 'before_2022.surv10', c['before_2022']['rose10_never_fell25_within60d_pct'], pct(old, lambda r: r['surv10']))
    cmp(w, 'since_2022.past_trades', c['since_2022']['past_trades'], len(new))
    cmp(w, 'since_2022.surv10', c['since_2022']['rose10_never_fell25_within60d_pct'], pct(new, lambda r: r['surv10']))
    md = lambda xs: C.r_half(C.median(xs)) if xs else None
    cmp(w, 'typical_day_first_rose10', c['typical_day_first_rose10'], md([r['t10'] for r in G if r['t10'] is not None]))
    cmp(w, 'typical_day_first_rose20', c['typical_day_first_rose20'], md([r['t20'] for r in G if r['t20'] is not None]))
    cmp(w, 'typical_day_of_60d_high', c['typical_day_of_60d_high'], md([r['dpk'] for r in G]))
    cmp(w, 'typical_day_of_deepest_dip', c['typical_day_of_deepest_dip'], md([r['ddday'] for r in G]))
    for row in c['if_it_falls_first']:
        th = row['fell_pct']
        hit, ok, liq = ladder(G, th)
        h2, o2, l2 = ladder(G, th, 'fall_first')
        cmp(w, f'falls {th}% first: past_trades', row['past_trades'], hit)
        cmp(w, f'falls {th}% first: still_rose10_pct', row['still_rose10_pct'], C.r_half(100 * ok / hit) if hit else None)
        cmp(w, f'falls {th}% first: went_on_to_fall25_pct', row['went_on_to_fall25_pct'], C.r_half(100 * liq / hit) if hit else None)
        if (h2, o2, l2) != (hit, ok, liq):
            res.append(dict(check='5', where=w, field=f'falls {th}% first: same-day ambiguity', shown=f'{hit}/{ok}/{liq}', mine=f'fall-first reading {h2}/{o2}/{l2}', ok=True, note='same-day high>=+10 and low<=-th'))
    # tile prices from candles: price_now, low_date, confirms_on, must_close_above
    bars = C.load(a, tf)
    cmp(w, 'price_now', c['price_now'], round(bars[-1]['c'], 2), 0.005)
    clo = [x['c'] for x in bars]; ct = C.wilder_rsi(clo)
    ti = next((i for i in range(len(bars)) if str(bars[i]['d']) == c['low_date']), None)
    okpiv = ti is not None and all(ct[j] > ct[ti] for j in range(ti - 3, ti)) and all(ct[j] > ct[ti] for j in range(ti + 1, len(bars)))
    res.append(dict(check='5', where=w, field='low_date is a provisional CT pivot low', shown=c['low_date'], mine=okpiv, ok=okpiv))
    need = ti + 3 - (len(bars) - 1)
    cmp(w, 'bars_to_confirm', c['bars_to_confirm'], need)
    conf_end = bars[ti]['d'] + dt.timedelta(days=4 * C.TFD[tf] - 1)
    res.append(dict(check='5', where=w, field='confirms_on', shown=c['confirms_on'], mine=str(conf_end), ok=c['confirms_on'] == str(conf_end)))
    if len(bars) - 1 == ti + 2:
        lo, hi = clo[-1] * 0.5, clo[-1] * 1.5
        for _ in range(80):
            mid = (lo + hi) / 2
            if C.wilder_rsi(clo + [mid])[-1] <= ct[ti]: lo = mid
            else: hi = mid
        cmp(w, 'must_close_above', c['must_close_above'], round(lo, 2), 0.011)
    else:
        cmp(w, 'must_close_above', c['must_close_above'], None)
    res.append(dict(check='5', where=w, field='_sample', shown=s, mine=[(r['chart'], r['entry']) for r in G], ok=True))

json.dump(res, open(os.path.join(OUT, 'check5.json'), 'w'), default=str, indent=0)
for x in res:
    if not x['ok'] or 'ambiguity' in x['field']: print(x)
print(sum(x['ok'] for x in res if x['field'] != '_sample'), 'ok of', sum(1 for x in res if x['field'] != '_sample'))
