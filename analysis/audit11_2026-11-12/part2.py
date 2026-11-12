# Audit 11 part 2 (exec'd from audit_data.py): cards, open signals.
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
RPLAIN = {v: k for k, v in PLAIN.items()}
lens_set = lambda s: frozenset() if s in ('-', '', None) else frozenset(s.split(' + '))
card_lens = lambda txt: frozenset() if txt == 'none' else frozenset(RPLAIN.get(x, '?' + x) for x in txt.split('; '))
ALL = scored              # every signal with a closed 60-day window (all charts)
SPLIT = D(2022, 1, 1)
MINE['cards'] = {}


def ladder(G):
    """from-entry row and the 5/10/15/20 rows; low checked before high within a day."""
    res = {}
    n = ok = lq = 0
    for r in G:
        e = r['entry']; n += 1
        for k, b in S.window(r['a'], r['d0']):
            if b[3] <= e * (1 - LIQ): lq += 1; break
            if b[2] >= e * 1.10: ok += 1; break
    res[0] = dict(n=n, ok=ok, liq=lq)
    for th in (5, 10, 15, 20):
        hit = ok = lq = 0
        for r in G:
            e = r['entry']; w = S.window(r['a'], r['d0'])
            for j, (k, b) in enumerate(w):
                if b[3] <= e * (1 - th / 100):
                    hit += 1
                    for k2, b2 in w[j:]:
                        if b2[3] <= e * (1 - LIQ): lq += 1; break
                        if b2[2] >= e * 1.10: ok += 1; break
                    break
                if b[2] >= e * 1.10: break
        res[th] = dict(n=hit, ok=ok, liq=lq)
    for v in res.values():
        v['okx'] = 100 * v['ok'] / v['n'] if v['n'] else None
        v['okr'] = rh(v['okx']) if v['n'] else None
        v['liqr'] = rh(100 * v['liq'] / v['n']) if v['n'] else None
    return res


def edge_of(lad):
    if lad[0]['okx'] is not None and rh(lad[0]['okx'], 6) < 70:
        return 0
    for th in (5, 10, 15, 20):
        if lad[th]['okx'] is not None and rh(lad[th]['okx'], 6) < 70:
            return -th
    return None


def card_stats(G):
    n = len(G)
    pct = lambda k: rh(100 * k / n)
    sc = [r for r in G if S.vol_ratio(r['a'], r['d0']) is not None]
    sc_ok = [r['m']['up'] >= 20 * S.vol_ratio(r['a'], r['d0']) for r in sc]
    old = [r for r in G if r['d0'] < SPLIT]; new = [r for r in G if r['d0'] >= SPLIT]
    sv = lambda X: rh(100 * sum(r['m']['surv10'] for r in X) / len(X)) if X else None
    up = median([r['m']['up'] for r in G]); dp = median([r['m']['ddpk'] for r in G]); dd = median([r['m']['dd'] for r in G])
    t10 = [x for x in (S.days_to(r['a'], r['d0'], r['entry'], 10) for r in G) if x is not None]
    t20 = [x for x in (S.days_to(r['a'], r['d0'], r['entry'], 20) for r in G) if x is not None]
    lad = ladder(G)
    return dict(n=n, surv10=pct(sum(r['m']['surv10'] for r in G)), scaled20=rh(100 * sum(sc_ok) / len(sc_ok)) if sc else None,
                reach20=pct(sum(r['m']['r20'] for r in G)), reach10=pct(sum(r['m']['r10'] for r in G)),
                best=rh(up, 1), dip=rh(dp, 1), deep=rh(dd, 1), bestx=rh(up, 6), dipx=rh(dp, 6), deepx=rh(dd, 6),
                touched30=pct(sum(r['m']['t30'] for r in G)), nOld=len(old), sOld=sv(old), nNew=len(new), sNew=sv(new),
                t10=rh(median(t10)) if t10 else None, t20=rh(median(t20)) if t20 else None,
                tHigh=rh(median([r['m']['dpk'] for r in G])), tLow=rh(median([r['m']['ddday'] for r in G])), lad=lad, edge=edge_of(lad))


def sample_for(c, pool, chart_label_fn):
    """Re-derive the like-for-like sample from the card's own grade and confirmations (taken as given) and the ledger."""
    a, tf, g = c['asset'], c['timeframe'], c['grade']
    want = card_lens(c['confirmations'])
    same_chart = [r for r in pool if r['ch'] == f'{a} {tf}']
    ex = [r for r in same_chart if lens_set(r['lenses']) == want]
    sg = [r for r in same_chart if r['grade'] == g]
    ag = [r for r in pool if r['a'] == a and r['grade'] == g]
    if len(ex) >= 15: return ex, 'ex', len(ex), len(sg)
    if len(sg) >= 15: return sg, 'sg', len(ex), len(sg)
    return ag, 'ag', len(ex), len(sg)


def low_day(a, tf, tdate):
    end = bucket_end(tdate, tf)
    cand = [(S.day[a][S.dpos[a][tdate + TD(days=i)]][3], tdate + TD(days=i)) for i in range((end - tdate).days + 1) if tdate + TD(days=i) in S.dpos[a]]
    return str(min(cand)[1])


def check_card(loc, c, G, kind, ex_n, sg_n, rule, meta):
    st_ = card_stats(G)
    MINE['cards'][c['signal_id'] + ('|ex' if kind == 'example' else '')] = dict(st_, lad={k: dict(v) for k, v in st_['lad'].items()}, meta=meta)
    a, tf, g = c['asset'], c['timeframe'], c['grade']
    n = st_['n']
    # sample text
    if kind == 'example':
        txt = {'ex': f'all {n} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then',
               'sg': f'all {n} {a} {tf} signals graded {g} whose 60 days had closed by then (' + ('none' if not ex_n else f'only {ex_n}') + ' had exactly the same confirmations, too few to use)',
               'ag': f'all {n} grade {g} signals across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {sg_n}, too few to use)'}[rule]
    else:
        txt = {'ex': f'all {n} past {a} {tf} signals with exactly the same confirmations',
               'sg': f'all {n} past {a} {tf} signals graded {g} (' + ('none' if not ex_n else f'only {ex_n}') + ' had exactly the same confirmations, too few to use)',
               'ag': f'all {n} past grade {g} signals across all {a} charts ({a} {tf} alone has only {sg_n}, too few to use)'}[rule]
    chk(loc, 'sample', c['sample'], txt, 'sample text/rule')
    chk(loc, 'past_trades', c['past_trades'], n); chk(loc, 'past_signals', c.get('past_signals'), n)
    chk(loc, 'rose10_within60d_pct (big number)', c['rose10_within60d_pct'], st_['reach10'])
    chk(loc, 'rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], st_['surv10'])
    chk(loc, 'beat_normal_move_pct', c['beat_normal_move_pct'], st_['scaled20'])
    chk(loc, 'rose20_within60d_pct', c['rose20_within60d_pct'], st_['reach20'])
    chk(loc, 'fell30_within60d_pct', c['fell30_within60d_pct'], st_['touched30'])
    chk(loc, 'typical_biggest_rise_pct', c['typical_biggest_rise_pct'], st_['best'])
    chk(loc, 'typical_dip_before_rise_pct', c['typical_dip_before_rise_pct'], st_['dip'])
    chk(loc, 'typical_deepest_dip_pct', c['typical_deepest_dip_pct'], st_['deep'])
    chk(loc, 'typical_biggest_rise_exact_pct', c['typical_biggest_rise_exact_pct'], st_['bestx'])
    chk(loc, 'typical_dip_before_rise_exact_pct', c['typical_dip_before_rise_exact_pct'], st_['dipx'])
    chk(loc, 'typical_deepest_dip_exact_pct', c['typical_deepest_dip_exact_pct'], st_['deepx'])
    # display of the exact medians (page rounds the 6-place value once) must equal the rounded field
    for f_, x_ in (('typical_biggest_rise_pct', 'typical_biggest_rise_exact_pct'), ('typical_dip_before_rise_pct', 'typical_dip_before_rise_exact_pct'),
                   ('typical_deepest_dip_pct', 'typical_deepest_dip_exact_pct')):
        chk(loc, f'{f_} == round1({x_})', c[f_], rh(c[x_], 1), 'rounded field differs from the 6-place value rounded once')
    chk(loc, 'before_2022.past_trades', c['before_2022']['past_trades'], st_['nOld'])
    chk(loc, 'before_2022.rose10_never_fell25', c['before_2022']['rose10_never_fell25_within60d_pct'], st_['sOld'])
    chk(loc, 'since_2022.past_trades', c['since_2022']['past_trades'], st_['nNew'])
    chk(loc, 'since_2022.rose10_never_fell25', c['since_2022']['rose10_never_fell25_within60d_pct'], st_['sNew'])
    chk(loc, 'typical_day_first_rose10', c['typical_day_first_rose10'], st_['t10'])
    chk(loc, 'typical_day_first_rose20', c['typical_day_first_rose20'], st_['t20'])
    chk(loc, 'typical_day_of_60d_high', c['typical_day_of_60d_high'], st_['tHigh'])
    chk(loc, 'typical_day_of_deepest_dip', c['typical_day_of_deepest_dip'], st_['tLow'])
    fe, L0 = c['from_entry'], st_['lad'][0]
    chk(loc, 'from_entry.past_trades', fe['past_trades'], L0['n'])
    chk(loc, 'from_entry.still_rose10_pct', fe['still_rose10_pct'], L0['okr'])
    chk(loc, 'from_entry.went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], L0['liqr'])
    chk(loc, 'from_entry.still_rose10_exact_pct', fe['still_rose10_exact_pct'], rh(L0['okx'], 6))
    for row in c['if_it_falls_first']:
        th = row['fell_pct']; Lr = st_['lad'][th]
        chk(loc, f'falls {th}% first: past_trades', row['past_trades'], Lr['n'])
        chk(loc, f'falls {th}% first: still_rose10_pct', row['still_rose10_pct'], Lr['okr'])
        chk(loc, f'falls {th}% first: went_on_to_fall25_pct', row['went_on_to_fall25_pct'], Lr['liqr'])
        chk(loc, f'falls {th}% first: still_rose10_exact_pct', row['still_rose10_exact_pct'], None if Lr['okx'] is None else rh(Lr['okx'], 6))
    chk(loc, 'ladder rows', ','.join(str(r['fell_pct']) for r in c['if_it_falls_first']), '5,10,15,20')
    for k_, v in meta.items():
        chk(loc, k_, c.get(k_), v)
    chk(loc, 'label', c['label'], feed['label'])
    return st_


# ---------------- forming setups (all charts)
def forming(a, tf):
    b = S.bars[(a, tf)]; C = [x[4] for x in b]; ct = rsi(C); n = len(b)
    for back in (1, 2, 3):
        ti = n - 1 - back
        v = ct[ti]
        if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)): continue
        if any(ct[j] <= v for j in range(ti + 1, n)):
            if any(ct[j] < v for j in range(ti + 1, n)): continue
            print('TIE while forming', a, tf, ti)
        need = 3 - back
        op = b[-1][0]
        for _ in range(need): op = next_open(op, tf)
        conf_close = bucket_end(op, tf)
        kill = None
        if back >= 2:
            base = C[:-1] if back == 3 else C[:]
            au, ad = rsi_state(base)
            r_ = v / (100 - v); prev = base[-1]
            ch = 13 * (r_ * ad - au)
            if ch < 0: ch = 13 * ad - 13 * au / r_
            kill = prev + ch
            assert abs(rsi(base + [kill])[-1] - v) < 1e-6
        return dict(ti=ti, tdate=b[ti][0], need=need, confirms=conf_close, kill=kill, price=C[-1])
    return None


myforming = {}
for a in ASSETS:
    for tf in TFS:
        f = forming(a, tf)
        if f: myforming[f'{a}-{tf}-{f["confirms"]}'] = (a, tf, f)
chk('feed cards', 'forming cards: ids', ','.join(sorted(c['signal_id'] for c in feed['cards'])), ','.join(sorted(myforming)), 'forming set differs')
for c in feed['cards']:
    loc = f"feed cards {c['signal_id']}"
    if c['signal_id'] not in myforming:
        continue
    a, tf, f = myforming[c['signal_id']]
    G, rule, exn, sgn = sample_for(c, L, None)
    meta = {'chart': f'{a} {tf}', 'asset': a, 'timeframe': tf, 'low_date': str(f['tdate']), 'low_day': low_day(a, tf, f['tdate']),
            'confirms_on': str(f['confirms']), 'bars_to_confirm': f['need'], 'must_close_above': rh(f['kill'], 2) if f['kill'] is not None else None,
            'price_now': rh(f['price'], 2), 'entry_close': None}
    check_card(loc, c, G, 'forming', exn, sgn, rule, meta)
    MINE['cards'][c['signal_id']]['kill_exact'] = f['kill']

# ---------------- example card
xc = feed['example_card']
exsig = next(r for r in L if r['ch'] == 'ETH 2D' and r['d0'] == EXD)
known = [r for r in L if r['d0'] + TD(days=60) <= EXD]
G, rule, exn, sgn = sample_for(xc, known, None)
meta = {'chart': 'ETH 2D', 'asset': 'ETH', 'timeframe': '2D', 'low_date': str(exsig['tdate']), 'low_day': low_day('ETH', '2D', exsig['tdate']),
        'confirms_on': str(EXD), 'bars_to_confirm': None, 'must_close_above': None, 'price_now': None, 'entry_close': rh(exsig['entry'], 2),
        'grade': theirs[('ETH 2D', str(EXD))]['grade'], 'example': True, 'signal_id': 'ETH-2D-2024-09-22'}
check_card('feed example_card', xc, G, 'example', exn, sgn, rule, meta)
chk('feed example_card', 'every sample signal known by 2024-09-22 (entry+60 <= date)', max(str(r['d0'] + TD(days=60)) for r in G) <= str(EXD), True)

# ---------------- open signals
last_px = {a: S.day[a][-1][4] for a in ASSETS}
myopen = {}
for a in ASSETS:
    for tf in GRADED:
        for s in S.sig[(a, tf)]:
            if s['d0'] < S.today and 0 <= (S.today - s['d0']).days <= 60:
                myopen[f"{a}-{tf}-{s['d0']}"] = s
fo = {o['signal_id']: o for o in feed['open_signals']}
chk('feed open_signals', 'ids', ','.join(sorted(fo)), ','.join(sorted(myopen)), 'open-signal set differs')
for sid_ in sorted(set(fo) & set(myopen)):
    o, s = fo[sid_], myopen[sid_]; a = s['a']; e = s['entry']; loc = f'feed open_signals {sid_}'
    chk(loc, 'chart', o['chart'], s['ch'])
    chk(loc, 'entry_date', o['entry_date'], str(s['d0']))
    chk(loc, 'entry_close', o['entry_close'], rh(e, 2))
    chk(loc, 'tags', o['tags'], S.tags(s))
    chk(loc, 'days_elapsed', o['days_elapsed'], (S.today - s['d0']).days)
    w = [(k, b) for k, b in S.window(a, s['d0']) if b[0] < S.today]
    mark = lambda N: next((rh((b[4] / e - 1) * 100, 1) for k, b in w if k == N), None)
    chk(loc, 'day10_pct', o['day10_pct'], mark(10)); chk(loc, 'day30_pct', o['day30_pct'], mark(30)); chk(loc, 'day60_pct', o['day60_pct'], mark(60))
    chk(loc, 'best_so_far_pct', o['best_so_far_pct'], rh((max(b[2] for k, b in w) / e - 1) * 100, 1) if w else None)
    chk(loc, 'worst_so_far_pct', o['worst_so_far_pct'], rh((min(b[3] for k, b in w) / e - 1) * 100, 1) if w else None)
    chk(loc, 'label', o['label'], feed['label'])
    # its card
    c = o['card']
    if c is None:
        chk(loc, 'card present', 'absent', 'present', 'missing card'); continue
    chk(loc, 'card grade = signal grade', c['grade'], o['grade'])
    pool = L
    G, rule, exn, sgn = sample_for(c, pool, None)
    meta = {'chart': s['ch'], 'asset': a, 'timeframe': s['tf'], 'low_date': str(s['tdate']), 'low_day': low_day(a, s['tf'], s['tdate']),
            'confirms_on': str(s['d0']), 'bars_to_confirm': None, 'must_close_above': None, 'price_now': rh(last_px[a], 2),
            'entry_close': rh(e, 2), 'signal_id': sid_}
    st_ = check_card(f'{loc} card', c, G, 'open', exn, sgn, rule, meta)
    # edge level and status (FEED_SPEC audit #9)
    lvl = st_['edge']
    if lvl == 0: status = 'lost'
    elif lvl is None: status = 'intact'
    else:
        status = 'intact'
        for k, b in w:
            if b[3] <= e * (1 + lvl / 100): status = 'lost'; break
            if b[2] >= e * 1.10: break
    chk(loc, 'edge_level_pct', o['edge_level_pct'], lvl)
    chk(loc, 'edge_status', o['edge_status'], status)
    MINE['cards'][sid_].update(status=status, sofar_best=rh((max(b[2] for k, b in w) / e - 1) * 100, 1) if w else None,
                               sofar_worst=rh((min(b[3] for k, b in w) / e - 1) * 100, 1) if w else None, days=(S.today - s['d0']).days,
                               day10=mark(10), entry=e, entry_date=str(s['d0']), tdate=str(s['tdate']))
MINE['today'] = str(S.today)
MINE['last_px'] = last_px
MINE['ex_entry'] = exsig['entry']
MINE['regime_today'] = S.gate(S.today)
MINE['forming'] = {k: dict(v[2], a=v[0], tf=v[1]) for k, v in myforming.items()}
