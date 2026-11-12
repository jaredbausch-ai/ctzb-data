"""Check 7 (page), 8 (labels vs meaning) and 9 (entry quality only). Every displayed number vs my value."""
import pickle, json, statistics as st, re
import numpy as np
from mine import *
from checks import rec, dump, ROWS

MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
dl = lambda d: f'{d.day} {MON[d.month - 1]} {d.year}'
M = '\u2212'


def fmt(v, d=1):
    q = Decimal(1) if d == 0 else Decimal(1).scaleb(-d)
    x = Decimal(abs(float(v))).quantize(q, rounding=ROUND_HALF_UP)
    s = f'{x:.{d}f}'
    return (M if v < 0 else '') + s


def pct(v, d=1, sign=True):
    return ('+' if sign and v > 0 else '') + fmt(v, d) + '%'


def money(v):
    x = Decimal(float(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return '$' + f'{x:,.2f}'


def share(xs):
    return rhaz(100 * sum(xs) / len(xs)) if xs else None


def lines(t):
    return [x.strip() for x in t.split('\n') if x.strip()]


def after(L, label, k=1):
    i = L.index(label)
    return L[i + k]


def chk(state, where, label, shown, mine, cause='differs', check='7'):
    rec(state, check, where, label, shown, mine, shown == mine, cause)


part1 = list(csv.DictReader(open(f'{S}/audit3/part1.csv')))
part5 = list(csv.DictReader(open(f'{S}/audit3/part5.csv')))
fadep = pickle.load(open(f'{S}/audit3/fade.pkl', 'rb'))


def my5(card, label):
    r = [x for x in part5 if x['location'] == f'card {card}' and x['label'] == label]
    return r[0]['yours']


def my5f(card, fell, label):
    r = [x for x in part5 if x['location'] == f'card {card} falls {fell}% first' and x['label'] == label]
    return r[0]['yours']


for state in ('REPLAY', 'CURRENT'):
    root = STATES[state]; now = NOWS[state]
    P = json.load(open(f'{S}/audit3/page_{state}.json'))
    feed = json.load(open(f'{root}/feed/ctzb_feed.json'))
    U = pickle.load(open(f'{S}/audit3/universe_{state}.pkl', 'rb'))
    Lg = pickle.load(open(f'{S}/audit3/ledger_{state}.pkl', 'rb'))
    led = list(csv.DictReader(open(f'{root}/datasets/ledger.csv')))
    aplus = [r for r in led if r['grade'] == 'A+']
    mine = {(r['chart'], r['entry']): Lg['mine_led'][(r['chart'], r['entry'])] for r in led}
    gate = gate_fn(root)
    # ---------- header / footer
    on = gate(now.date())
    chk(state, 'header', 'Market filter', 'on' if 'Market filter: on' in P['initial']['header'] else 'off', 'on' if on else 'off')
    chk(state, 'footer', 'Data through', re.search(r'Data through (.*?) ·', P['initial']['foot']).group(1), dl(max(b['d'] for b in U['day']['ETH'])))
    chk(state, 'review bar', 'feed time', re.search(r'feed (\d\d:\d\d) UTC', P['initial']['review']).group(1), feed['generated_at'][11:16])
    rec(state, '7', 'card', 'stale warning shown', P['initial']['stale'], False, P['initial']['stale'] is False, 'stale warning')

    # ---------- my A+ figures per asset
    def grp(a, g='A+'):
        return [mine[(r['chart'], r['entry'])] for r in led if r['asset'] == a and r['grade'] == g]
    def misses(a, g):
        G = grp(a, g); Mi = [s for s in G if not s['m']['r10']]; best = [s['m']['up'] for s in Mi]
        return dict(signals=len(G), misses=len(Mi), up_first=sum(b > 0 for b in best), med=st.median(best),
                    worst=st.median(s['m']['dd'] for s in Mi), d60=st.median(s['m']['ret'] for s in Mi))
    # ---------- Previous signals column
    rec_ = sorted(aplus, key=lambda r: r['entry'], reverse=True)[:5]  # JS sort is stable on equal dates
    L = lines(P['initial']['prevClosed'])
    for i, r in enumerate(rec_):
        s = mine[(r['chart'], r['entry'])]; m = s['m']
        where = f"Previous signals row {i + 1}"
        chk(state, where, 'chart', L[3 * i], r['chart'])
        chk(state, where, 'date · best · worst', L[3 * i + 1], f"{dl(s['d0'])} · best {pct(m['up'])} · worst {pct(m['dd'])}")
        chk(state, where, 'badge', L[3 * i + 2], 'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed')
    # ---------- Record tab
    for a in ('all', 'ETH', 'BTC'):
        X = P[f'record:{a}']
        rows = sorted([r for r in aplus if a == 'all' or r['asset'] == a], key=lambda r: r['entry'], reverse=True)
        n_miss = sum(1 for r in rows if not mine[(r['chart'], r['entry'])]['m']['r10'])
        chk(state, f'Record {a}', 'count line', X['recCount'], f'{len(rows)} signals · {n_miss} missed +10%')
        chk(state, f'Record {a}', 'rows', len(X['recRows']), len(rows))
        for shown, r in zip(X['recRows'], rows):
            s = mine[(r['chart'], r['entry'])]; m = s['m']
            exp = [dl(s['d0']), s['chart'], money(s['entry']), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
                   pct(m['up']), pct(m['dd']), pct(m['ret']), str(m['dpk'])]
            labs = ['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day']
            for lab, sh, ex in zip(labs, shown, exp):
                ok = sh == ex; cause = 'differs'
                if not ok and s.get('mc'):
                    mc = s['mc']; alt = {'Deepest drop': pct(mc['dd']), 'Rose 10%': 'Yes' if mc['r10'] else 'No'}
                    if alt.get(lab) == sh: cause = 'documented flash-print clamp (BTC 2017-04-15 $0.06 low)'
                if not ok and cause == 'differs':
                    # double rounding through the 6-place ledger value?
                    lk = {'Best': 'bestMove', 'Deepest drop': 'maxDrawdown', 'Day 60': 'return60d'}.get(lab)
                    if lk and pct(float(r[lk])) == sh: cause = 'page rounds the 6-place ledger value (double rounding)'
                rec(state, '7', f"Record {a} {r['chart']} {r['entry']}", lab, sh, ex, ok, cause)
        # summary boxes
        for asset in (('ETH', 'BTC') if a == 'all' else (a,)):
            G = grp(asset); n = len(G); mi = misses(asset, 'A+')
            box = [b for b in X['recSum'].split('\n\n')] if False else None
            T = lines(X['recSum'])
            i = T.index(asset)
            seg = T[i:i + 12]
            exp = {'signals': f'{n} signals', 'Rose 10% in 60 days': f"{share([s['m']['r10'] for s in G])}%",
                   'Reached +20% in 60 days': f"{share([s['m']['r20'] for s in G])}%",
                   'Rose 10%, never fell 25%': f"{share([s['m']['surv10'] for s in G])}%",
                   'Median deepest dip': pct(st.median(s['m']['dd'] for s in G)),
                   'Misses: median peak first': pct(mi['med'])}
            chk(state, f'Record {a} summary {asset}', 'signals', seg[1], exp['signals'])
            for lab in list(exp)[1:]:
                chk(state, f'Record {a} summary {asset}', lab, after(seg, lab), exp[lab])
    # ---------- example card (Now) and its chart
    ex = P['now:example']['card']; E_ = lines(ex)
    G = grp('ETH'); n = len(G); mi = misses('ETH', 'A+')
    exs = [s for s in U['sig'][('ETH', '2D')] if s['gated'] and str(s['d0']) == '2024-09-22']
    s_ex = exs[0] if exs else None
    lr = [r for r in led if r['chart'] == 'ETH 2D' and r['entry'] == '2024-09-22']
    rec(state, '7', 'example card', 'signal is a ledger A+ ETH 2D signal confirmed 2024-09-22', lr[0]['grade'] if lr else 'absent', 'A+', bool(lr) and lr[0]['grade'] == 'A+', 'example not A+')
    chk(state, 'example card', 'line', after(E_, 'Confirmed setup'), f"Example: confirmed {dl(s_ex['d0'])} · entry close {money(s_ex['entry'])}")
    reach10 = share([s['m']['r10'] for s in G]); surv = share([s['m']['surv10'] for s in G])
    chk(state, 'example card', 'big number (rose 10%)', E_[E_.index('rose 10% within 60 days') - 1], f'{reach10}%')
    chk(state, 'example card', 'did it without ever falling 25%', after(E_, 'rose 10% within 60 days'), f'{surv}% did it without ever falling 25%')
    chk(state, 'example card', 'sample size', after(E_, 'rose 10% within 60 days', 2), f'from all {n} ETH top-grade signals')
    hi = st.median(s['m']['up'] for s in G); dd = st.median(s['m']['dd'] for s in G); dbh = st.median(s['m']['ddpk'] for s in G)
    hd = st.median(s['m']['dpk'] for s in G); d60 = st.median(s['m']['ret'] for s in G)
    chk(state, 'example card', 'Typical high', after(E_, 'Typical high'), pct(hi))
    chk(state, 'example card', 'Typical drop from entry', after(E_, 'Typical drop from entry'), pct(dd))
    # edge: pooled early-dip table, first band below 70% (mine: stated measurement == repo for +10% early-dip)
    early = fadep[state]['variants'][('D',)][0]
    gone = next(b for b in early if rhaz(b['r10']) < 70)
    dip = -20 if gone['band'] == 'worse than -20%' else None
    chk(state, 'example card', 'Edge gone below', after(E_, 'Edge gone below'), f"{pct(dip, 0)} in the first 10 days · {money(s_ex['entry'] * (1 + dip / 100))}")
    chk(state, 'example card', 'If it misses: up first', after(E_, 'If it misses: up first'),
        ('Every time' if mi['up_first'] == mi['misses'] else f"{mi['up_first']} of {mi['misses']}") + f" · median peak {pct(mi['med'])}")
    chk(state, 'example card', 'Dip before the high, from entry', after(E_, 'Dip before the high, from entry'), pct(dbh))
    chk(state, 'example card', 'High lands around', after(E_, 'High lands around'), f'Day {hd:g}')
    if hd != int(hd):
        rec(state, '7', 'example card', 'High lands around (unrounded median shown)', after(E_, 'High lands around'), f'Day {rhaz(hd)}', False, 'median of whole days shown unrounded')
    chk(state, 'example card', 'Reached +20%', after(E_, 'Reached +20%'), f"{share([s['m']['r20'] for s in G])}%")
    chk(state, 'example card', 'Touched −30%', after(E_, 'Touched ' + M + '30%'), f"{share([s['m']['t30'] for s in G])}%")
    d10 = fadep[state]['variants'][('D',)][1]
    red = [x for x in d10 if x['check'] == 'red on day 10'][0]
    chk(state, 'example card', 'Red on day 10 (still rose 10%, day 10 to day 60)', after(E_, 'Red on day 10'), f"{rhaz(red['r10'])}% still rose 10%",
        'the 67% counts highs from day 1; after a red day 10 the share that rose 10% from day 10 on is 64%', check='7')
    chk(state, 'example card', 'Worst drop, misses', after(E_, 'Worst drop, misses'), pct(mi['worst']))
    chk(state, 'example card', 'Price on day 60 (median of all ETH A+)', after(E_, 'Price on day 60'), pct(d60))
    # pooled ladder
    lad_lab = {'shallower than -2%': f'Dip < {M}2%', '-2% to -5%': f'Dip {M}2% to {M}5%', '-5% to -10%': f'Dip {M}5% to {M}10%',
               '-10% to -20%': f'Dip {M}10% to {M}20%', 'worse than -20%': f'Dip past {M}20%'}
    for b in early:
        chk(state, 'example card odds-fade ladder', lad_lab[b['band']], after(E_, lad_lab[b['band']]), f"{rhaz(b['r10'])}%")
    for x in d10:
        lab = x['check'].replace(' on day 10', ' day 10').capitalize()
        chk(state, 'example card odds-fade ladder', lab, after(E_, lab), f"{rhaz(x['r10'])}%",
            'day-10 rows count +10% from day 1 to day 60, the box says day 10 to day 60')
    for era, f in (('Before 2022', lambda s: s['d0'].year < 2022), ('Since 2022', lambda s: s['d0'].year >= 2022)):
        X = [s for s in G if f(s)]
        chk(state, 'example card eras', era, E_[E_.index(f'{era} n {len(X)}') + 1] if f'{era} n {len(X)}' in E_ else 'n differs', f"{share([s['m']['surv10'] for s in X])}%")
    # example chart (both modes)
    e0 = s_ex['entry']
    for mode in ('chart-alert:example', 'chart-happened:example'):
        X = P[mode]; T = X['chartSvg']; SD = lines(X['side'])
        exp_tags = [money(e0 * (1 + float(fmt(hi)[0:].replace(M, '-')) / 100)), money(e0 * 1.1), money(e0), money(e0 * (1 + float(fmt(dd).replace(M, '-')) / 100))]
        exp_tags_true = [money(e0 * (1 + hi / 100)), money(e0 * 1.1), money(e0), money(e0 * (1 + dd / 100))]
        for lab, ex_r, ex_t in zip(('typical high price', '+10% price', 'entry price', 'typical drop price'), exp_tags, exp_tags_true):
            ok = ex_t in T
            rec(state, '7', f'{mode} price tags', lab, ex_r if ex_r in T else 'absent', ex_t, ok,
                'price derived from the rounded 1-place percentage (rounded twice)')
        chk(state, mode, 'Typical high label', f'Typical high {pct(hi)}' if f'Typical high {pct(hi)}' in T else 'absent', f'Typical high {pct(hi)}')
        chk(state, mode, '+10% label', f'+10% · {reach10}% of past signals got here' if f'+10% · {reach10}% of past signals got here' in T else 'absent', f'+10% · {reach10}% of past signals got here')
        chk(state, mode, 'edge label', [t for t in T if t.startswith('Edge gone')][0], f"Edge gone below {money(e0 * 0.8)} ({pct(-20, 0)})")
        chk(state, mode, 'day-10 label', [t for t in T if t.startswith('Day 10')][0], f"Day 10 · red here: {rhaz(red['r10'])}% still rose 10%",
            'the 67% counts highs from day 1, not after day 10')
        chk(state, mode, 'high-day label', [t for t in T if t.startswith('High usually')][0], f'High usually ~day {rhaz(hd)}')
        bandv = [max(rhaz(early[0]['r10']), rhaz(early[1]['r10'])), rhaz(early[2]['r10']), rhaz(early[3]['r10'])]
        chk(state, mode, 'early-dip band labels', [t for t in T if re.fullmatch(r'\d+%', t)], [f'{v}%' for v in bandv])
        # this signal's own path (daily): best / worst within 60 days and their 2D-bar day ranges
        m = s_ex['m']
        hiT = [t for t in T if t.startswith('This one')]
        w = window(Daily(U['day']['ETH']), s_ex['d0'], e0, now)
        kb = max(range(60), key=lambda k: w[k]['h']); kl = min(range(60), key=lambda k: w[k]['l'])
        rng = lambda k: f'days {k + 1 - (k % 2)}–{k + 1 - (k % 2) + 1}'
        exp_hi = f"This one: {money(w[kb]['h'])} · {pct(m['up'])} · {rng(kb)}"
        exp_lo = f"This one: {money(w[kl]['l'])} · {pct(m['dd'])} · {rng(kl)}"
        chk(state, mode, 'this one: best', hiT[0] if hiT else 'absent', exp_hi)
        chk(state, mode, 'this one: deepest', hiT[1] if len(hiT) > 1 else 'absent', exp_lo)
        if mode == 'chart-alert:example':
            rec(state, '8', mode, '"At the alert" shows only what was known at the alert', 'outcome markers drawn: ' + ' | '.join(hiT), 'no outcome markers',
                not hiT, 'the "At the alert" view draws this signal\'s 60-day best and deepest points, which a member could not have had at the alert; the side box says "This is all a member had at the alert"')
        chk(state, mode, 'side: big number', SD[SD.index('ETH 2D · example') + 1], f'{reach10}%')
        chk(state, mode, 'side: line', SD[SD.index('ETH 2D · example') + 2], f'rose 10% within 60 days, from {n} past signals; {surv}% without ever falling 25%')
        ok_ = after(SD, 'Typical high') == f'{pct(hi)} · {money(e0 * (1 + hi / 100))}'
        rec(state, '7', mode, 'side: Typical high', after(SD, 'Typical high'), f'{pct(hi)} · {money(e0 * (1 + hi / 100))}', ok_, 'price derived from the rounded 1-place percentage (rounded twice)')
        chk(state, mode, 'side: +10% target', after(SD, '+10% target'), money(e0 * 1.1))
        chk(state, mode, 'side: Reached +20%', after(SD, 'Reached +20%'), f"{share([s['m']['r20'] for s in G])}%")
        ok_ = after(SD, 'Typical drop') == f'{pct(dd)} · {money(e0 * (1 + dd / 100))}'
        rec(state, '7', mode, 'side: Typical drop', after(SD, 'Typical drop'), f'{pct(dd)} · {money(e0 * (1 + dd / 100))}', ok_, 'price derived from the rounded 1-place percentage (rounded twice)')
        chk(state, mode, 'side: Edge gone below', after(SD, 'Edge gone below'), f"{money(e0 * 0.8)} ({pct(-20, 0)})")
        if mode == 'chart-happened:example':
            d10c = [b for b in w if (b['d'] - s_ex['d0']).days == 10][0]['c']
            chk(state, mode, 'what this one did: reached', after(SD, 'Reached +10% / +20%'), f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}")
            chk(state, mode, 'what this one did: best', after(SD, 'Best price'), f"{pct(m['up'])}, {rng(kb)}")
            chk(state, mode, 'what this one did: deepest', after(SD, 'Deepest drop'), f"{pct(m['dd'])}, {rng(kl)}")
            chk(state, mode, 'what this one did: day 10', after(SD, 'Day 10 check'), f"{'Red' if d10c < e0 else 'Green'}, {pct((d10c / e0 - 1) * 100)}")
            chk(state, mode, 'what this one did: day 60', after(SD, 'Price on day 60'), pct(m['ret']))
        # cloud
        pp = np.array([[ (U['day']['ETH'][Daily(U['day']['ETH']).pos[s['d0'] + dt.timedelta(days=k)]]['c'] / s['entry'] - 1) * 100 for k in range(1, 61)] for s in G])
        chk(state, mode, 'cloud n', X['cloudSub'], f'Every past ETH top-grade signal, n {len(G)}')
        q = [np.percentile(pp[:, 59], v) for v in (50, 25, 75)]
        chk(state, mode, 'cloud day-60 figures', re.search(r'Day 60: (.*?)\. Daily', X['cloudNote']).group(1),
            f'median {pct(q[0])}, middle half {pct(q[1])} to {pct(q[2])}', 'path values rounded to 2 places before the quantile (double rounding)')
    # example JSON bars vs raw candles
    exj = json.load(open(f'{root}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
    raw2 = {b['t']: b for b in U['charts'][('ETH', '2D')]['bars']}
    bad = [b['t'] for b in exj['bars'] if b['t'] not in raw2 or any(abs(b[k] - raw2[b['t']][k]) > 1e-9 for k in 'ohlc')]
    rec(state, '7', 'example JSON', 'bars equal raw ETH 2D candles', f"{len(exj['bars'])} bars, {len(bad)} differ", '0 differ', not bad, 'bar differs')
    eb = exj['bars'][exj['entry_index']]
    rec(state, '7', 'example JSON', 'entry bar is the confirmation bar', utcd(eb['t']), s_ex['cdate'], utcd(eb['t']) == s_ex['cdate'], 'entry bar differs')
    rec(state, '7', 'example JSON', 'entry_close', exj['entry_close'], s_ex['entry'], abs(exj['entry_close'] - s_ex['entry']) < 1e-9, 'differs')
    # switch-off empty card claim: about 22 top-grade setups a year, 2020-2025 average
    if 'now:switch-off' in P and 'times a year' in P['now:switch-off']['card']:
        yrs = [s['d0'].year for s in (grp('ETH') + grp('BTC')) if 2020 <= s['d0'].year <= 2025]
        v = len(yrs) / 6
        sh = re.search(r'about (\d+) times a year', P['now:switch-off']['card']).group(1)
        rec(state, '7', 'empty card', 'top-grade setups a year, 2020-2025 average (hard-coded)', sh, round(v, 2), int(sh) == rhaz(v), 'hard-coded figure differs from the ledger')
    # ---------- forming cards (REPLAY)
    for c in feed['cards']:
        cid = c['signal_id']; key = f'now:{cid}'
        if key not in P: continue
        T = lines(P[key]['card']); a = c['asset']
        y = lambda lab: float(my5(cid, lab))
        reach10 = rhaz(y('rose10_within60d_pct')); surv = rhaz(y('rose10_never_fell25_within60d_pct')); n = int(float(my5(cid, 'past_trades')))
        hi = y('typical_biggest_rise_pct'); dd = y('typical_deepest_dip_pct'); dbh = y('typical_dip_before_rise_pct')
        pick = lines(P[key]['picker']); i = pick.index(c['chart'])
        chk(state, f'picker {cid}', 'odds', pick[i + 1], f'{reach10}%')
        chk(state, f'picker {cid}', 'grade/date', pick[i + 2], f"not top grade · confirms {dl(dt.date.fromisoformat(my5(cid, 'confirms_on (last day of the confirmation bar)')))}")
        lowd = dt.date.fromisoformat(my5(cid, 'low_date')); cd_ = dt.date.fromisoformat(my5(cid, 'confirms_on (last day of the confirmation bar)'))
        kc = my5(cid, 'must_close_above')
        chk(state, f'card {cid}', 'line', after(T, 'Setup forming'), f'Low {dl(lowd)} · confirms {dl(cd_)}' + (f' if it closes above {money(float(kc))}' if kc not in ('', 'None') else ''))
        chk(state, f'card {cid}', 'big number', T[T.index('rose 10% within 60 days') - 1], f'{reach10}%')
        chk(state, f'card {cid}', 'surv line', after(T, 'rose 10% within 60 days'), f'{surv}% did it without ever falling 25%')
        chk(state, f'card {cid}', 'n line', after(T, 'rose 10% within 60 days', 2), f'from {n} past signals like this one')
        chk(state, f'card {cid}', 'Typical high', after(T, 'Typical high'), pct(hi))
        chk(state, f'card {cid}', 'Typical drop from entry', after(T, 'Typical drop from entry'), pct(dd))
        rows = [(f, rhaz(float(my5f(cid, f, 'still_rose10_pct'))) if my5f(cid, f, 'still_rose10_pct') not in ('', 'None') else None, int(my5f(cid, f, 'past_trades'))) for f in (5, 10, 15, 20)]
        if reach10 < 70: edge = 'Below the 70% bar from entry'
        else:
            g_ = next((r for r in rows if r[1] is not None and r[1] < 70), None)
            edge = f'{pct(-g_[0], 0)} before it rises 10%' if g_ else 'Holds at every level'
        chk(state, f'card {cid}', 'Edge gone below', after(T, 'Edge gone below'), edge)
        mi = misses(a, c['grade'])
        chk(state, f'card {cid}', 'If it misses: up first', after(T, 'If it misses: up first'),
            ('Every time' if mi['up_first'] == mi['misses'] else f"{mi['up_first']} of {mi['misses']}") + f" · median peak {pct(mi['med'])}")
        chk(state, f'card {cid}', 'misses pool', after(T, 'If it misses: up first', 2), f"all {mi['signals']} {a} signals of this grade")
        chk(state, f'card {cid}', 'Dip before the high, from entry', after(T, 'Dip before the high, from entry'), pct(dbh))
        chk(state, f'card {cid}', 'High lands around', after(T, 'High lands around'), f"Day {rhaz(y('typical_day_of_60d_high'))}")
        chk(state, f'card {cid}', 'Reached +20%', after(T, 'Reached +20%'), f"{rhaz(y('rose20_within60d_pct'))}%")
        chk(state, f'card {cid}', 'Touched −30%', after(T, 'Touched ' + M + '30%'), f"{rhaz(y('fell30_within60d_pct'))}%",
            'documented flash-print clamp' if a == 'BTC' else 'differs')
        chk(state, f'card {cid}', 'Deepest dip lands around', after(T, 'Deepest dip lands around'), f"Day {rhaz(y('typical_day_of_deepest_dip'))}")
        chk(state, f'card {cid}', 'Worst drop, misses', after(T, 'Worst drop, misses'), pct(mi['worst']))
        chk(state, f'card {cid}', 'Price on day 60, misses', after(T, 'Price on day 60, misses'), pct(mi['d60']))
        chk(state, f'card {cid}', 'ladder From entry', after(T, f'From entry n {n}') if f'From entry n {n}' in T else 'n differs', f'{reach10}%')
        for f_, v, k in rows:
            lab = f'Falls {f_}% first n {k}'
            chk(state, f'card {cid}', f'ladder falls {f_}%', after(T, lab) if lab in T else 'n differs', 'n/a' if v is None else f'{v}%')
        for era in ('before_2022', 'since_2022'):
            k = int(my5(cid, f'{era}.past_trades')); v = rhaz(float(my5(cid, f'{era}.rose10_never_fell25_within60d_pct')))
            lab = ('Before 2022' if era == 'before_2022' else 'Since 2022') + f' n {k}'
            chk(state, f'card {cid}', f'era {era}', after(T, lab) if lab in T else 'n differs', f'{v}%')
        # chart
        X = P[f'chart-alert:{cid}']; CT = X['chartSvg']; SD = lines(X['side'])
        bars = U['charts'][(a, c['timeframe'])]['bars']; e0 = bars[-1]['c']
        chk(state, f'chart {cid}', 'subtitle', X['chSub'].split('. The real')[0],
            f"Low {dl(lowd)} · confirms {dl(cd_)} · zones drawn from today's price ({money(e0)})")
        lowbar = [b for b in bars if b['d'] == lowd][0]
        chk(state, f'chart {cid}', 'low marker', [t for t in CT if t.startswith('Low ')][0], f"Low {dl(lowd)} · {money(lowbar['l'])}")
        for lab, ex_t in (('typical high price', money(e0 * (1 + hi / 100))), ('+10% price', money(e0 * 1.1)), ('today price', money(e0)), ('typical drop price', money(e0 * (1 + dd / 100)))):
            ex_r = money(e0 * (1 + float(fmt(hi if 'high' in lab else dd).replace(M, '-')) / 100)) if 'typical' in lab else ex_t
            rec(state, '7', f'chart {cid} price tags', lab, ex_r if ex_r in CT else 'absent', ex_t, ex_t in CT, 'price derived from the rounded 1-place percentage (rounded twice)')
        chk(state, f'chart {cid}', '+10% label', [t for t in CT if t.startswith('+10% ·')][0], f'+10% · {reach10}% of past signals got here')
        chk(state, f'chart {cid}', 'high-day label', [t for t in CT if t.startswith('High usually')][0], f"High usually ~day {rhaz(y('typical_day_of_60d_high'))}")
        chk(state, f'chart {cid}', 'confirms label', [t for t in CT if t.startswith('Confirms')][0], f'Confirms {dl(cd_)}')
        chk(state, f'chart {cid}', 'ladder band labels', [t for t in CT if re.fullmatch(r'\d+%|n/a', t)], [f'{reach10}%'] + [('n/a' if r[1] is None else f'{r[1]}%') for r in rows[:3]])
        ed = [t for t in CT if t.startswith('Edge gone')]
        if reach10 >= 70:
            g_ = next((r for r in rows if r[1] is not None and r[1] < 70), None)
            chk(state, f'chart {cid}', 'edge label', ed[0] if ed else 'absent', f"Edge gone below {money(e0 * (1 - g_[0] / 100))} ({pct(-g_[0], 0)}, before +10%)")
            chk(state, f'chart {cid}', 'side: Edge gone below', after(SD, 'Edge gone below'), f"{money(e0 * (1 - g_[0] / 100))} ({pct(-g_[0], 0)})")
        else:
            chk(state, f'chart {cid}', 'side: Edge gone below', after(SD, 'Edge gone below'), 'below the bar already')
        chk(state, f'chart {cid}', 'side: big number', SD[2], f'{reach10}%')
        chk(state, f'chart {cid}', 'side: line', SD[3], f'rose 10% within 60 days, from {n} past signals; {surv}% without ever falling 25%')
        chk(state, f'chart {cid}', 'side: sample', SD[1], f"{c['chart']} · from {my5(cid, 'sample text')}")
        rec(state, '7', f'chart {cid}', 'side: Typical high', after(SD, 'Typical high'), f'{pct(hi)} · {money(e0 * (1 + hi / 100))}',
            after(SD, 'Typical high') == f'{pct(hi)} · {money(e0 * (1 + hi / 100))}', 'price derived from the rounded 1-place percentage (rounded twice)')
        chk(state, f'chart {cid}', 'side: +10% target', after(SD, '+10% target'), money(e0 * 1.1))
        chk(state, f'chart {cid}', 'side: Reached +20%', after(SD, 'Reached +20%'), f"{rhaz(y('rose20_within60d_pct'))}%")
        rec(state, '7', f'chart {cid}', 'side: Typical drop', after(SD, 'Typical drop'), f'{pct(dd)} · {money(e0 * (1 + dd / 100))}',
            after(SD, 'Typical drop') == f'{pct(dd)} · {money(e0 * (1 + dd / 100))}', 'price derived from the rounded 1-place percentage (rounded twice)')
        Pp = [s for s in grp(a)]
        pp = np.array([[(U['day'][a][Daily(U['day'][a]).pos[s['d0'] + dt.timedelta(days=k)]]['c'] / s['entry'] - 1) * 100 for k in range(1, 61)] for s in Pp])
        q = [np.percentile(pp[:, 59], v) for v in (50, 25, 75)]
        chk(state, f'chart {cid}', 'cloud n', X['cloudSub'], f'Every past {a} top-grade signal, n {len(Pp)}')
        chk(state, f'chart {cid}', 'cloud day-60 figures', re.search(r'Day 60: (.*?)\. Daily', X['cloudNote']).group(1),
            f'median {pct(q[0])}, middle half {pct(q[1])} to {pct(q[2])}', 'path values rounded to 2 places before the quantile (double rounding)')
    # ---------- How to read: the liquidation arithmetic
    rd = P['read']['read']
    v = 100 * (1 / 3.3 - 0.05)
    rec(state, '7', 'How to read', '25.3% = 3.3x with 5% maintenance', '25.3%' if '25.3% below the entry close' in rd else 'absent', f'{v:.2f}%', abs(v - 25.3) < 0.05, 'arithmetic')
    rec(state, '7', 'How to read', '70% bar = WINMIN / posting bar', '70%' if 'our 70% bar' in rd else 'absent', feed['odds_fade']['posting_bar_pct'], feed['odds_fade']['posting_bar_pct'] == 70, '')
    pickle.dump(None, open('/dev/null', 'wb'))
dump('part7.csv')
bad = [r for r in ROWS if r['ok'] == 'no']
print(len(ROWS), 'checks', len(bad), 'bad')
for r in bad: print(r)
