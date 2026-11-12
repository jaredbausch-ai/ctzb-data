"""Checks 5 and 6: every card (forming, example, open) and every open signal."""
import datetime as dt
from fractions import Fraction as Fr
import core as K
from rec import chk

WORDS = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
SPLIT = dt.date(2022, 1, 1)


def lens_set(txt):
    if txt in ('none', '-', ''):
        return set()
    if ';' in txt or txt in WORDS:
        return {WORDS[x.strip()] for x in txt.split(';')}
    return {x.strip() for x in txt.split('+')}


def sample_for(card, pairs, known_by=None):
    """The card's past signals, by the rule its own sample line states; grades/lenses as given in the ledger."""
    P = [(r, s) for r, s in pairs if known_by is None or s['d0'] + dt.timedelta(days=60) <= known_by]
    smp = card['sample']; ch = card['chart']; a = card['asset']; g = card['grade']
    if 'exactly the same confirmations' in smp and ' graded ' not in smp and 'grade ' not in smp.split('signals')[0]:
        L = lens_set(card['confirmations'])
        G = [(r, s) for r, s in P if r['chart'] == ch and lens_set(r['lenses']) == L]
        rule = 'exact'
    elif f'{ch} signals graded' in smp:
        G = [(r, s) for r, s in P if r['chart'] == ch and r['grade'] == g]; rule = 'chart+grade'
    else:
        G = [(r, s) for r, s in P if r['asset'] == a and r['grade'] == g]; rule = 'asset+grade'
    return G, rule


def card_figures(G, root):
    ms = [s['m'] for _, s in G]; n = len(G)
    old = [s for _, s in G if s['d0'] < SPLIT]; new = [s for _, s in G if s['d0'] >= SPLIT]
    sc = [s['scaled20'] for _, s in G if s['scaled20'] is not None]
    med = lambda k: K.median([m[k] for m in ms])
    t10 = [m['d10'] for m in ms if m['d10'] is not None]; t20 = [m['d20'] for m in ms if m['d20'] is not None]
    return dict(n=n, surv10=K.share(sum(m['surv10'] for m in ms), n), scaled20=K.share(sum(sc), len(sc)) if sc else None,
                reach20=K.share(sum(m['r20'] for m in ms), n), reach10=K.share(sum(m['r10'] for m in ms), n),
                best=med('up'), dip_before=med('ddpk'), deepest=med('dd'), touched30=K.share(sum(m['t30'] for m in ms), n),
                nOld=len(old), sOld=K.share(sum(s['m']['surv10'] for s in old), len(old)) if old else None,
                nNew=len(new), sNew=K.share(sum(s['m']['surv10'] for s in new), len(new)) if new else None,
                lad=K.ladder([s for _, s in G], True), lad_hf=K.ladder([s for _, s in G], False),
                d10=K.rhaz(K.median(t10)) if t10 else None, d20=K.rhaz(K.median(t20)) if t20 else None,
                dHigh=K.rhaz(K.median([m['dpk'] for m in ms])), dLow=K.rhaz(K.median([m['ddday'] for m in ms])))


def check_card(st, loc, c, f, extra_cause=''):
    cz = extra_cause
    chk(st, loc, 'past_trades (n)', c['past_trades'], f['n'], 'sample size' + cz)
    chk(st, loc, 'sample line states n', 'yes' if f' {c["past_trades"]} ' in f' {c["sample"]} ' else 'no', 'yes', 'sample text')
    chk(st, loc, 'rose10_within60d_pct', c['rose10_within60d_pct'], f['reach10'], 'share' + cz)
    chk(st, loc, 'rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], f['surv10'], 'share' + cz)
    chk(st, loc, 'beat_normal_move_pct', c['beat_normal_move_pct'], f['scaled20'], 'share' + cz)
    chk(st, loc, 'rose20_within60d_pct', c['rose20_within60d_pct'], f['reach20'], 'share' + cz)
    chk(st, loc, 'fell30_within60d_pct', c['fell30_within60d_pct'], f['touched30'], 'share' + cz)
    for key, k in (('typical_biggest_rise', 'best'), ('typical_dip_before_rise', 'dip_before'), ('typical_deepest_dip', 'deepest')):
        chk(st, loc, f'{key}_pct', c[f'{key}_pct'], K.rhaz(f[k], 1), 'median' + cz)
        chk(st, loc, f'{key}_exact_pct', c[f'{key}_exact_pct'], K.rhaz(f[k], 6), 'median (6 places)' + cz)
    chk(st, loc, 'before_2022.past_trades', c['before_2022']['past_trades'], f['nOld'], 'era' + cz)
    chk(st, loc, 'before_2022.rose10_never_fell25', c['before_2022']['rose10_never_fell25_within60d_pct'], f['sOld'], 'era' + cz)
    chk(st, loc, 'since_2022.past_trades', c['since_2022']['past_trades'], f['nNew'], 'era' + cz)
    chk(st, loc, 'since_2022.rose10_never_fell25', c['since_2022']['rose10_never_fell25_within60d_pct'], f['sNew'], 'era' + cz)
    chk(st, loc, 'eras add up to n', c['before_2022']['past_trades'] + c['since_2022']['past_trades'], c['past_trades'], 'era sum')
    for i, row in enumerate(c['if_it_falls_first']):
        L = f['lad'][i]; Lh = f['lad_hf'][i]
        why = 'ladder' + cz
        if (L['n'], L['ok'], L['liq']) != (Lh['n'], Lh['ok'], Lh['liq']) and (row['past_trades'], row['still_rose10_pct'], row['went_on_to_fall25_pct']) == (Lh['n'], Lh['ok'], Lh['liq']):
            why = 'first-fall step checks the HIGH before the LOW within a daily bar (stated choice (c): low first)'
        chk(st, loc, f'falls {row["fell_pct"]}% first: past_trades', row['past_trades'], L['n'], why)
        chk(st, loc, f'falls {row["fell_pct"]}% first: still_rose10_pct', row['still_rose10_pct'], L['ok'], why)
        chk(st, loc, f'falls {row["fell_pct"]}% first: went_on_to_fall25_pct', row['went_on_to_fall25_pct'], L['liq'], why)
    for key, k in (('typical_day_first_rose10', 'd10'), ('typical_day_first_rose20', 'd20'), ('typical_day_of_60d_high', 'dHigh'), ('typical_day_of_deepest_dip', 'dLow')):
        if key in c:
            chk(st, loc, key, c[key], f[k], 'timing median' + cz)
    chk(st, loc, 'label', c['label'], 'Computed signal, not a fill. No trade was taken. Entry quality only: the data has no exits, so this is not a strategy return or a track record.', 'label')


def provisional(b, ct, K_):
    """Forming low: the latest of the last three closed-or-open bars that is a pivot so far (3 strictly higher bars
    to its left, every bar since at or above it), with fewer than 3 bars after it."""
    n = b.n
    for back in (1, 2, 3):
        ti = n - 1 - back
        v = ct[ti]
        if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)):
            continue
        if any(ct[j] < v for j in range(ti + 1, n)):
            continue
        return ti, 3 - back
    return None


def kill_close(b, ti, need):
    """Close of the confirmation bar at which CT would equal the trough CT; it must close above this.
    Solved exactly from the Wilder averages (current open bar assumed to close at the current price)."""
    c = list(b.Cf)
    if need == 0:
        base = c[:-1]
    elif need == 1:
        base = c
    else:
        return None
    ct = K.rsi(c, 14)
    target = ct[ti]
    ags, als = K.rsi_state(base, 14)
    ag, al, p = ags[-1], als[-1], base[-1]
    # RSI(X) = target  <=>  ag'/al' = target/(100-target)
    R = target / (100 - target)
    # try X >= p: ag' = (13ag + X-p)/14, al' = 13al/14
    x_up = p + R * 13 * al - 13 * ag
    if x_up >= p:
        return x_up
    # X < p: ag' = 13ag/14, al' = (13al + p - X)/14 -> 13ag = R(13al + p - X)
    return p + 13 * al - 13 * ag / R


def check(st, C):
    feed, pairs, W = C['feed'], C['pairs'], C['W']
    root, now = W['root'], W['now']
    today = now.date()
    mine = {(f"{s['a']} {s['tf']}", str(s['d0'])): s for lst in W['sig'].values() for s in lst}
    day = {a: K.Daily(root, a) for a in ('ETH', 'BTC')}

    # ---------------- forming cards (REPLAY has four)
    forming_mine = {}
    for (a, tf), b in W['bars'].items():
        ct = W['ct'][(a, tf)]
        p = provisional(b, ct, None)
        if p:
            ti, need = p
            conf_i = ti + 3
            # confirmation bar's last day: bars run every tf days from the last open
            nd = int(tf.rstrip('D'))
            conf_open = b.D[-1] + dt.timedelta(days=nd * (conf_i - (b.n - 1)))
            d0 = conf_open + dt.timedelta(days=nd - 1)
            forming_mine[f'{a} {tf}'] = dict(ti=ti, need=need, d0=d0, trough=b.D[ti], b=b, ct=ct)
    shown = {c['chart']: c for c in feed['cards']}
    for ch in sorted(set(forming_mine) | set(shown)):
        chk(st, 'feed.cards', f'forming card present for {ch}', 'present' if ch in shown else 'absent', 'present' if ch in forming_mine else 'absent', 'forming set')
    for c in feed['cards']:
        ch = c['chart']; a = c['asset']; loc = f'feed.cards[{c["signal_id"]}]'
        fm = forming_mine.get(ch)
        if fm:
            b = fm['b']
            chk(st, loc, 'low_date (trough bar open)', c['low_date'], str(fm['trough']), 'trough date')
            dd = day[a]; t1 = b.end_date(fm['ti']); cand = []
            d = fm['trough']
            while d <= t1:
                x = dd.bar(d)
                if x: cand.append((x[1], d))
                d += K.ONE_DAY
            chk(st, loc, 'low_day (lowest daily low in the trough bar)', c['low_day'], str(min(cand)[1]), 'low day')
            chk(st, loc, 'confirms_on', c['confirms_on'], str(fm['d0']), 'confirmation date')
            chk(st, loc, 'signal_id', c['signal_id'], f"{ch.replace(' ', '-')}-{fm['d0']}", 'id')
            chk(st, loc, 'bars_to_confirm', c['bars_to_confirm'], fm['need'], 'bars to confirm')
            kc = kill_close(b, fm['ti'], fm['need'])
            chk(st, loc, 'must_close_above', c['must_close_above'], None if kc is None else K.rhaz(Fr(kc), 2), 'kill close')
            chk(st, loc, 'price_now (latest price, chart bar)', c['price_now'], K.rhaz(b.C[-1], 2), 'price now')
            chk(st, loc, 'price_now = latest daily price', c['price_now'], K.rhaz(day[a].b.C[-1], 2), 'price now vs daily')
        G, rule = sample_for(c, pairs)
        fg = card_figures(G, root); check_card(st, loc, c, fg)
        C.setdefault('cardfig', {})[c['signal_id']] = dict(fig=fg, kind='forming', fm=fm, kill=(kill_close(fm['b'], fm['ti'], fm['need']) if fm else None),
                                                          low_day=str(min(cand)[1]) if fm else None, price_now=fm['b'].C[-1] if fm else None, card=c)
        for x in c['active_confluences']:
            chk(st, loc, f'confluence {x["after"]} window_closes = confirmed + 10 days', x['window_closes'],
                str(dt.date.fromisoformat(x['after_confirmed']) + dt.timedelta(days=10)), 'window')
            ca, ctf = x['after'].split()[:2]
            chk(st, loc, f'confluence {x["after"]} after_confirmed is a real {ca} {ctf} signal date', 'yes',
                'yes' if (f'{ca} {ctf}', x['after_confirmed']) in mine else 'no', 'confluence date')

    # ---------------- example card
    xc = feed.get('example_card')
    if xc:
        loc = 'feed.example_card'
        kb = dt.date(2024, 9, 22)
        s = mine.get(('ETH 2D', '2024-09-22'))
        chk(st, loc, 'is a real ETH 2D signal confirmed 2024-09-22', 'yes', 'yes' if s and s['confirmed'] else 'no', 'example signal')
        chk(st, loc, 'entry_close', xc['entry_close'], K.rhaz(s['entry'], 2), 'entry')
        chk(st, loc, 'price_now (= entry at the alert)', xc['price_now'], K.rhaz(s['entry'], 2), 'entry')
        chk(st, loc, 'low_date', xc['low_date'], str(s['trough']), 'trough')
        chk(st, loc, 'low_day', xc['low_day'], str(s['low_day']), 'low day')
        chk(st, loc, 'confirms_on', xc['confirms_on'], '2024-09-22', 'date')
        chk(st, loc, 'grade (ledger)', xc['grade'], next(r['grade'] for r, s2 in pairs if s2 is s), 'grade')
        G, rule = sample_for(xc, pairs, known_by=kb)
        chk(st, loc, 'sample uses only signals whose 60th day closed by 2024-09-22', 'yes',
            'yes' if all(s2['d0'] + dt.timedelta(days=60) <= kb for _, s2 in G) else 'no', 'hindsight')
        fg = card_figures(G, root); check_card(st, loc, xc, fg)
        C.setdefault('cardfig', {})['example'] = dict(fig=fg, kind='example', s=s, card=xc)

    # ---------------- open signals and their cards
    opens = []
    for (a, tf), lst in W['sig'].items():
        for s in lst:
            if s['confirmed'] and 0 <= (today - s['d0']).days <= 60:
                opens.append(s)
    shown = {o['signal_id']: o for o in feed['open_signals']}
    ids = {f"{s['a']}-{s['tf']}-{s['d0']}": s for s in opens}
    for sid in sorted(set(ids) | set(shown)):
        exp = 'present' if sid in ids else 'absent'
        cause = 'open set'
        if sid in ids and sid not in shown and ids[sid]['tf'] == '8D':
            cause = '8D open signal not listed (FEED_SPEC: open signals cover 1D/2D/3D/5D)'
        chk(st, 'feed.open_signals', f'{sid} listed', 'present' if sid in shown else 'absent', exp, cause)
    led_by = {(r['chart'], r['entry']): r for r, _ in pairs}
    for o in feed['open_signals']:
        s = ids.get(o['signal_id'])
        loc = f'feed.open_signals[{o["signal_id"]}]'
        if not s:
            continue
        a = s['a']; dd = day[a]
        chk(st, loc, 'chart', o['chart'], f"{a} {s['tf']}", 'chart')
        chk(st, loc, 'entry_date (confirmation close)', o['entry_date'], str(s['d0']), 'date')
        chk(st, loc, 'entry_close', o['entry_close'], K.rhaz(s['entry'], 2), 'entry')
        chk(st, loc, 'tags', o['tags'], s['tags'], 'tags')
        chk(st, loc, 'days_elapsed (day in progress)', o['days_elapsed'], (today - s['d0']).days, 'day count')
        w = dd.window(s['d0'], now)
        for N in (10, 30, 60):
            x = next((y for y in w if y[0] == N), None)
            chk(st, loc, f'day{N}_pct (closed daily bar only)', o[f'day{N}_pct'], None if x is None else K.rhaz((x[3] / s['entry'] - 1) * 100, 1), f'day {N}')
        chk(st, loc, 'best_so_far_pct', o['best_so_far_pct'], K.rhaz((max(y[1] for y in w) / s['entry'] - 1) * 100, 1) if w else None, 'best so far')
        chk(st, loc, 'worst_so_far_pct', o['worst_so_far_pct'], K.rhaz((min(y[2] for y in w) / s['entry'] - 1) * 100, 1) if w else None, 'worst so far')
        chk(st, loc, 'label', o['label'], feed['label'], 'label')
        c = o['card']
        if not c:
            chk(st, loc, 'has its own card', 'no', 'yes', 'card missing'); continue
        cl = loc + '.card'
        chk(st, cl, 'signal_id', c['signal_id'], o['signal_id'], 'id')
        chk(st, cl, 'low_date (trough bar open)', c['low_date'], str(s['trough']), 'trough')
        chk(st, cl, 'low_day', c['low_day'], str(s['low_day']), 'low day')
        chk(st, cl, 'confirms_on', c['confirms_on'], str(s['d0']), 'date')
        chk(st, cl, 'grade = open signal grade', c['grade'], o['grade'], 'grade')
        chk(st, cl, 'confirmations = open signal lenses', str(sorted(lens_set(c['confirmations']))), str(sorted(lens_set(o['confirmations']))), 'lenses')
        chk(st, cl, 'price_now (field says price now)', c['price_now'], K.rhaz(dd.b.C[-1], 2),
            'open card price_now holds the ENTRY close, not the price now (feed only; page does not show it)')
        G, rule = sample_for(c, pairs)
        fg = card_figures(G, root); check_card(st, cl, c, fg)
        C.setdefault('cardfig', {})[o['signal_id']] = dict(fig=fg, kind='open', s=s, card=c, o=o, w=w)
