# executed inside checks.py (shares its namespace): items 4-7
# ------------------------------------------------------------------ 4. odds_fade
def zser(ct):
    out, z = [], None
    for v in ct:
        if v is None:
            out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        out.append(z)
    return out

def tags_of(s, zm):
    t = [s['bk'], 'any trough']
    if s['dis']:
        t += ['diamond', 'filled' if s['strong'] else 'hollow']
    if s['prime']:
        t.append('prime dot')
    if s['dis'] and s['prime']:
        t.append('diamond+dot')
    z = zm[s['ti']]
    if s['bk'] == 'B' and s['ct'] < 60 and z is not None and z >= 50:
        t.append('zone-exit B')
    return t

TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
rows_all = []
for tf in ('1D', '2D', '3D', '5D', '8D'):
    V = SIG[('ETH', tf)]; bars = V['bars']; zm = zser(V['ct']); D = [b['date'] for b in bars]
    for s in V['sig']:
        if not s['gated']:
            continue
        s['tg'] = tags_of(s, zm)
        ei = s['ei']; e = bars[ei]['c']; end = D[ei] + dt.timedelta(days=60)
        if D[-1] < end:
            continue
        js = [j for j in range(ei + 1, len(bars)) if D[j] <= end]
        if not js:
            continue
        rows_all.append(dict(chart=f'ETH {tf}', tf=tf, tags=set(s['tg']), d=D[ei], win=bars[js[-1]]['c'] > e))
UPTO = dt.date(TODAY.year, 1, 1)
keep = []
for tf in ('1D', '2D', '3D', '5D', '8D'):
    for t in TAGS:
        sub = [r for r in rows_all if r['tf'] == tf and t in r['tags'] and r['d'] + dt.timedelta(days=TFD[tf] - 1 + 60) < UPTO]
        if len(sub) >= 8 and 100 * sum(r['win'] for r in sub) / len(sub) >= 70:
            keep.append((tf, t))
early, d10g = [], {'green on day 10': [], 'red on day 10': []}
for tf in ('1D', '2D', '3D', '5D', '8D'):
    for s in SIG[('ETH', tf)]['sig']:
        if not s['gated'] or not s['closed'] or not any(k[0] == tf and k[1] in s['tg'] for k in keep):
            continue
        dd = daily['ETH']
        if s['d0'] not in dd.pos or not dd.complete(s['d0']):
            continue
        e = dd.b[dd.pos[s['d0']]]['c']
        w = dd.window(s['d0'])
        dip_lo = min(b['l'] for k, b in w if k <= 10)
        hi_after = max(b['h'] for k, b in w if k > 10)
        early.append(dict(dip=(dip_lo / e - 1) * 100, r10=hi_after >= e * 1.10, r20=hi_after >= e * 1.20))
        c10 = [b['c'] for k, b in w if k == 10]
        if c10:
            d10g['green on day 10' if c10[0] >= e else 'red on day 10'].append(dict(r10=hi_after >= e * 1.10, r20=hi_after >= e * 1.20))
BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
my_ed = []
for hi, lo, lab in BANDS:
    g = [p for p in early if lo < p['dip'] <= hi]
    if len(g) >= 5:
        my_ed.append(dict(band=lab, n=len(g), x10=100 * sum(p['r10'] for p in g) / len(g), x20=100 * sum(p['r20'] for p in g) / len(g)))
my_d10 = [dict(band=lab, n=len(g), x10=100 * sum(p['r10'] for p in g) / len(g), x20=100 * sum(p['r20'] for p in g) / len(g))
          for lab, g in d10g.items() if len(g) >= 5]
OF = feed['odds_fade']
chk('odds_fade', 'posting_bar_pct', OF['posting_bar_pct'], 70)
chk('odds_fade', 'edge_measured_on', OF['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)')
for key, mine, shown in (('early_dip', my_ed, OF['early_dip']), ('day10', my_d10, OF['day10'])):
    chk(f'odds_fade {key}', 'row count', len(shown), len(mine), 'rows')
    for mr, sr in zip(mine, shown):
        loc = f"odds_fade {key} {mr['band']}"
        chk(loc, 'band/check label', sr.get('band', sr.get('check')), mr['band'])
        chk(loc, 'past_trades', sr['past_trades'], mr['n']); chk(loc, 'past_signals', sr['past_signals'], mr['n'])
        for f, v in (('rose10_after_day10_pct', mr['x10']), ('rose10_within60d_pct', mr['x10']), ('rose20_after_day10_pct', mr['x20']), ('rose20_within60d_pct', mr['x20'])):
            chk(loc, f, sr[f], rha(v))
        chk(loc, 'edge (exact share vs 70%)', sr['edge'], 'intact' if mr['x10'] >= 70 else 'gone')
OUT.append(dict(state=NAME, location='odds_fade', label='walk-forward tier (info)', shown='', yours='; '.join(f'ETH {a} {b}' for a, b in keep), ok=True, cause=''))

# ------------------------------------------------------------------ 5. cards
PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
def lensset(txt):
    return set() if txt in ('none', '-', '') else {PLAIN.get(x, x) for x in txt.split('; ')}
def ledlens(s):
    return set() if s['lenses'] in ('-', '') else set(s['lenses'].split(' + '))

def low_day(a, tf, tdate):
    bars = SIG[(a, tf)]['bars']; dd = daily[a]
    b = next(x for x in bars if x['date'] == tdate)
    days = [b['date'] + dt.timedelta(days=i) for i in range((b['end'] - b['date']).days + 1)]
    cand = [(dd.b[dd.pos[d]]['l'], d) for d in days if d in dd.pos]
    return min(cand)[1], min(cand)[0]

def kill_close(bars, ti, need):
    c = [b['c'] for b in bars]; n = len(c)
    ct = rsi(c)
    if need == 1:
        base = c[:]
    elif need == 0:
        base = c[:-1]
    else:
        return None
    lo, hi = c[-1] * 0.3, c[-1] * 2.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if rsi(base + [mid])[-1] <= ct[ti]: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def card_expect(card, LGx, a, tf, grade, lenses, example=False):
    ex = [s for s in LGx if s['chart'] == f'{a} {tf}' and ledlens(s) == lenses]
    sg = [s for s in LGx if s['chart'] == f'{a} {tf}' and s['grade'] == grade]
    ag = [s for s in LGx if s['a'] == a and s['grade'] == grade]
    if example:
        if len(ex) >= 15: basis, Gx = f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', ex
        elif len(sg) >= 15: basis, Gx = f'all {len(sg)} {a} {tf} signals graded {grade} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
        else: basis, Gx = f'all {len(ag)} grade {grade} signals across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', ag
    else:
        if len(ex) >= 15: basis, Gx = f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex
        elif len(sg) >= 15: basis, Gx = f'all {len(sg)} past {a} {tf} signals graded {grade} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
        else: basis, Gx = f'all {len(ag)} past grade {grade} signals across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag
    return basis, Gx

MYCARDS = {}
def check_card(c, loc, kind, LGx, entry=None):
    a, tf = c['asset'], c['timeframe']
    basis, Gx = card_expect(c, LGx, a, tf, c['grade'], lensset(c['confirmations']), example=(kind == 'example'))
    n = len(Gx); pc = lambda k: rha(100 * k / n)
    chk(loc, 'sample', c['sample'], basis, 'sample text/rule')
    chk(loc, 'past_trades', c['past_trades'], n, 'sample'); chk(loc, 'past_signals', c['past_signals'], n, 'sample')
    chk(loc, 'rose10_within60d_pct', c['rose10_within60d_pct'], pc(sum(s['m']['r10'] for s in Gx)))
    chk(loc, 'rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], pc(sum(s['m']['surv10'] for s in Gx)))
    chk(loc, 'rose20_within60d_pct', c['rose20_within60d_pct'], pc(sum(s['m']['r20'] for s in Gx)))
    chk(loc, 'fell30_within60d_pct', c['fell30_within60d_pct'], pc(sum(s['m']['t30'] for s in Gx)))
    sc = [s['sc20'] for s in Gx if s['sc20'] is not None]
    chk(loc, 'beat_normal_move_pct', c['beat_normal_move_pct'], rha(100 * sum(sc) / len(sc)) if sc else None)
    for f, key in (('typical_biggest_rise', 'up'), ('typical_dip_before_rise', 'ddpk'), ('typical_deepest_dip', 'dd')):
        full = st.median([s['m'][key] for s in Gx]); six = st.median([r6(s['m'][key]) for s in Gx])
        chk(loc, f + '_pct', c[f + '_pct'], rha(six, 1))
        chk(loc, f + '_exact_pct', c[f + '_exact_pct'], r6(full))
        if abs(r6(six) - r6(full)) > 0:
            OUT.append(dict(state=NAME, location=loc, label=f + '_exact_pct (median of the 6dp ledger values)', shown=c[f + '_exact_pct'], yours=r6(six), ok=abs(c[f + '_exact_pct'] - six) <= 5e-7 + 1e-12, cause='6dp median vs full-precision median'))
        if rha(six, 1) != rha(full, 1):
            OUT.append(dict(state=NAME, location=loc, label=f + '_pct full vs 6dp', shown=rha(full, 1), yours=rha(six, 1), ok=False, cause='precision'))
        if entry:
            MYCARDS.setdefault(loc, {})[f + '_price'] = rha(entry * (1 + full / 100), 2)
    old = [s for s in Gx if s['d0'] < dt.date(2022, 1, 1)]; new = [s for s in Gx if s['d0'] >= dt.date(2022, 1, 1)]
    sv = lambda X: rha(100 * sum(s['m']['surv10'] for s in X) / len(X)) if X else None
    chk(loc, 'before_2022.past_trades', c['before_2022']['past_trades'], len(old)); chk(loc, 'before_2022.past_signals', c['before_2022']['past_signals'], len(old))
    chk(loc, 'before_2022.rose10_never_fell25', c['before_2022']['rose10_never_fell25_within60d_pct'], sv(old))
    chk(loc, 'since_2022.past_trades', c['since_2022']['past_trades'], len(new)); chk(loc, 'since_2022.past_signals', c['since_2022']['past_signals'], len(new))
    chk(loc, 'since_2022.rose10_never_fell25', c['since_2022']['rose10_never_fell25_within60d_pct'], sv(new))
    med = lambda xs: rha(st.median(xs)) if xs else None
    chk(loc, 'typical_day_first_rose10', c['typical_day_first_rose10'], med([s['m']['d10'] for s in Gx if s['m']['d10'] is not None]))
    chk(loc, 'typical_day_first_rose20', c['typical_day_first_rose20'], med([s['m']['d20'] for s in Gx if s['m']['d20'] is not None]))
    chk(loc, 'typical_day_of_60d_high', c['typical_day_of_60d_high'], med([s['m']['dpk'] for s in Gx]))
    chk(loc, 'typical_day_of_deepest_dip', c['typical_day_of_deepest_dip'], med([s['m']['ddday'] for s in Gx]))
    nn, ok, liq = from_entry(Gx)
    fe = c['from_entry']
    chk(loc, 'from_entry.past_trades', fe['past_trades'], nn); chk(loc, 'from_entry.past_signals', fe['past_signals'], nn)
    chk(loc, 'from_entry.still_rose10_pct', fe['still_rose10_pct'], rha(100 * ok / nn))
    chk(loc, 'from_entry.still_rose10_exact_pct', fe['still_rose10_exact_pct'], r6(100 * ok / nn))
    chk(loc, 'from_entry.went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], rha(100 * liq / nn))
    exacts = [100 * ok / nn]
    for row in c['if_it_falls_first']:
        th = row['fell_pct']; hit, ok2, liq2 = ladder_row(Gx, th); l2 = f'ladder falls {th}%'
        chk(loc, l2 + ' past_trades', row['past_trades'], hit); chk(loc, l2 + ' past_signals', row['past_signals'], hit)
        chk(loc, l2 + ' still_rose10_pct', row['still_rose10_pct'], rha(100 * ok2 / hit) if hit else None)
        chk(loc, l2 + ' still_rose10_exact_pct', row['still_rose10_exact_pct'], r6(100 * ok2 / hit) if hit else None)
        chk(loc, l2 + ' went_on_to_fall25_pct', row['went_on_to_fall25_pct'], rha(100 * liq2 / hit) if hit else None)
        exacts.append(100 * ok2 / hit if hit else None)
    chk(loc, 'ladder levels', [r['fell_pct'] for r in c['if_it_falls_first']], [5, 10, 15, 20])
    # edge: first level whose exact share is below 70
    lv = [0, 5, 10, 15, 20]
    edge = next((lv[i] for i, x in enumerate(exacts) if x is not None and x < 70), None)
    MYCARDS.setdefault(loc, {}).update(edge=edge, n=n, G=Gx, exacts=exacts)
    chk(loc, 'active_confluences (forming only; lens logic)', '', '')
    return Gx, edge

# REPLAY forming cards
for c in feed['cards']:
    a, tf = c['asset'], c['timeframe']; loc = f"card {c['signal_id']}"
    V = SIG[(a, tf)]; bars = V['bars']; ct = V['ct']; n = len(bars)
    cand = None
    for back in (1, 2, 3):
        ti = n - 1 - back
        v = ct[ti]
        if all(ct[j] > v for j in range(ti - 3, ti)) and all(ct[j] > v for j in range(ti + 1, n)):
            cand = ti; break
    chk(loc, 'forming trough exists (my pivot rule, current bar at current price)', 'yes', 'yes' if cand is not None else 'no', 'forming')
    if cand is None:
        continue
    need = 3 - ((n - 1) - cand)
    tb = bars[cand]
    # confirmation bar: `need` bars after the open one, by the bucket rule
    d = bars[-1]['end']
    for _ in range(need):
        d = bucket_end(d + dt.timedelta(days=1), tf)
    ld, lp = low_day(a, tf, tb['date'])
    chk(loc, 'signal_id', c['signal_id'], f"{a}-{tf}-{d}")
    chk(loc, 'low_date', c['low_date'], str(tb['date'])); chk(loc, 'low_day', c['low_day'], str(ld))
    chk(loc, 'confirms_on', c['confirms_on'], str(d)); chk(loc, 'bars_to_confirm', c['bars_to_confirm'], need)
    kc = kill_close(bars, cand, need)
    chk(loc, 'must_close_above', c['must_close_above'], None if kc is None else rha(kc, 2), 'kill close')
    chk(loc, 'price_now', c['price_now'], rha(daily[a].b[-1]['c'], 2)); chk(loc, 'entry_close', c['entry_close'], None)
    chk(loc, 'timeframe/chart', c['chart'], f'{a} {tf}')
    MYCARDS.setdefault(loc, {}).update(low_price=tb['l'], kill=kc, entry=daily[a].b[-1]['c'])
    check_card(c, loc, 'forming', LG, entry=c['price_now'])

# example card
xc = feed['example_card']
if xc:
    loc = 'example_card'
    s = next(x for x in SIG[('ETH', '2D')]['sig'] if x['d0'] == dt.date(2024, 9, 22))
    known = [x for x in LG if x['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
    chk(loc, 'signal_id', xc['signal_id'], 'ETH-2D-2024-09-22'); chk(loc, 'example', xc['example'], True)
    chk(loc, 'low_date', xc['low_date'], str(s['tdate'])); chk(loc, 'low_day', xc['low_day'], str(low_day('ETH', '2D', s['tdate'])[0]))
    chk(loc, 'confirms_on', xc['confirms_on'], '2024-09-22'); chk(loc, 'entry_close', xc['entry_close'], rha(s['e'], 2))
    chk(loc, 'price_now', xc['price_now'], None); chk(loc, 'bars_to_confirm', xc['bars_to_confirm'], None); chk(loc, 'must_close_above', xc['must_close_above'], None)
    chk(loc, 'grade (ledger)', xc['grade'], next(x['grade'] for x in LG if x['chart'] == 'ETH 2D' and x['d0'] == dt.date(2024, 9, 22)))
    MYCARDS.setdefault(loc, {}).update(entry=s['e'], tdate=s['tdate'], low_price=s['tlow'])
    check_card(xc, loc, 'example', known, entry=s['e'])

# ------------------------------------------------------------------ 6. open signals
exp_open = []
for (a, tf), V in SIG.items():
    if tf == '8D':
        continue
    for s in V['sig']:
        if s['gated'] and s['closed'] and 0 <= (TODAY - s['d0']).days <= 60:
            exp_open.append(s)
exp_ids = {f"{s['a']}-{s['tf']}-{s['d0']}": s for s in exp_open}
shown_ids = {o['signal_id']: o for o in feed['open_signals']}
for k in sorted(set(exp_ids) | set(shown_ids)):
    chk('open_signals membership', k, 'listed' if k in shown_ids else 'absent', 'listed' if k in exp_ids else 'absent', 'membership')
LEDG = {(r['chart'], r['entry']): r for r in LED}
for k in sorted(set(exp_ids) & set(shown_ids)):
    s, o = exp_ids[k], shown_ids[k]; loc = f'open_signals {k}'; a = s['a']; e = s['e']
    w = daily[a].window(s['d0'])   # closed bars only
    chk(loc, 'chart', o['chart'], s['chart']); chk(loc, 'entry_date', o['entry_date'], str(s['d0']))
    chk(loc, 'entry_close', o['entry_close'], rha(e, 2)); chk(loc, 'tags', o['tags'], tagstr(s))
    chk(loc, 'days_elapsed', o['days_elapsed'], (TODAY - s['d0']).days)
    for N in (10, 30, 60):
        b = [x for kk, x in w if kk == N]
        chk(loc, f'day{N}_pct', o[f'day{N}_pct'], rha((b[0]['c'] / e - 1) * 100, 1) if b else None)
    chk(loc, 'best_so_far_pct', o['best_so_far_pct'], rha((max(x['h'] for _, x in w) / e - 1) * 100, 1) if w else None)
    chk(loc, 'worst_so_far_pct', o['worst_so_far_pct'], rha((min(x['l'] for _, x in w) / e - 1) * 100, 1) if w else None)
    s['open_w'] = w
    if o.get('card'):
        c = o['card']; cl = f'open card {k}'
        chk(cl, 'signal_id', c['signal_id'], k); chk(cl, 'confirms_on', c['confirms_on'], str(s['d0']))
        chk(cl, 'low_date', c['low_date'], str(s['tdate'])); chk(cl, 'low_day', c['low_day'], str(low_day(a, s['tf'], s['tdate'])[0]))
        chk(cl, 'price_now', c['price_now'], rha(daily[a].b[-1]['c'], 2)); chk(cl, 'entry_close', c['entry_close'], rha(e, 2))
        chk(cl, 'bars_to_confirm', c['bars_to_confirm'], None); chk(cl, 'must_close_above', c['must_close_above'], None)
        chk(cl, 'grade = open row grade', c['grade'], o['grade'])
        MYCARDS.setdefault(cl, {}).update(entry=e, low_price=s['tlow'], tdate=s['tdate'], s=s)
        check_card(c, cl, 'open', LG, entry=e)
    else:
        chk(loc, 'card present', 'absent', 'present', 'missing card')

# ------------------------------------------------------------------ 7. past paths
def paths(G):
    P = []
    for s in G:
        dd = daily[s['a']]; p = [0.0]
        for k in range(1, 61):
            i = dd.pos.get(s['d0'] + dt.timedelta(days=k))
            if i is None: break
            p.append((dd.b[i]['c'] / s['e'] - 1) * 100)
        if len(p) == 61: P.append(p)
    return P
def cmp_paths(loc, pp, G):
    P = paths(G)
    chk(loc, 'signals', pp['signals'], len(P)); chk(loc, 'n == signals in the group', len(P), len(G))
    chk(loc, 'day count', len(pp['days']), 61)
    for dday in pp['days']:
        k = dday['day']
        for f, q in (('q25_pct', .25), ('median_pct', .5), ('q75_pct', .75)):
            chk(loc, f'day {k} {f}', dday[f], rha(q7([p[k] for p in P], q), 1))
    return P
for pp in feed['past_paths']:
    cmp_paths(f"past_paths {pp['asset']}", pp, groups[(pp['asset'], 'A+')])
    chk(f"past_paths {pp['asset']}", 'grade', pp['grade'], 'A+')
EXG = [s for s in groups[('ETH', 'A+')] if s['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
if feed['example_past_paths']:
    cmp_paths('example_past_paths', feed['example_past_paths'], EXG)

pickle.dump(dict(MYCARDS={k: {kk: vv for kk, vv in v.items() if kk not in ('G', 's')} for k, v in MYCARDS.items()},
                 exp_open={k: dict(d0=s['d0'], e=s['e'], tdate=s['tdate'], tlow=s['tlow'], tf=s['tf'], a=s['a']) for k, s in exp_ids.items()},
                 my_ed=my_ed, my_d10=my_d10),
            open(os.path.join(HERE, f'mine_{NAME}.pkl'), 'wb'))
