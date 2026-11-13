"""Check every displayed figure on the member page (harvested by pagerun.py) against my own values."""
import csv, json, os, sys, re, datetime as dt
from decimal import Decimal as D, ROUND_HALF_UP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mycalc import *
from checkdata import Checks, check_state

MINUS = '−'
MON = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
L_, R_, T_, B_ = 20, 960, 24, 480


def dlong(d):
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    return f'{d.day} {MON[d.month]} {d.year}'


def pct(v, d=1):
    if v is None:
        return 'n/a'
    r = rnd(v, d)
    if r == 0:
        return f'{0:.{d}f}%'
    s = f'{abs(r):.{d}f}%'
    return ('+' + s) if r > 0 else (MINUS + s)


def pc(v):
    return 'n/a' if v is None else f'{v}%'


def money(v):
    return 'n/a' if v is None else '$' + f'{rnd(v, 2):,.2f}'


def pxat(entry, p):
    if entry is None or p is None:
        return None
    e = D(str(rnd(entry, 2)))
    return float((e * (1 + D(str(rnd(p, 6))) / 100)).quantize(D('0.01'), rounding=ROUND_HALF_UP))


def lines(t):
    return [x.strip() for x in (t or '').split('\n') if x.strip()]


class Page:
    def __init__(self, K, S, sdir, feed, H, extra):
        self.K, self.S, self.sdir, self.feed, self.H, self.x = K, S, sdir, feed, H, extra

    def c(self, loc, label, shown, yours, cause='page'):
        return self.K.c('page ' + loc, label, shown, yours, cause)

    def has(self, loc, label, text, want, cause='page'):
        ok = want in (text or '')
        self.K.rows.append(dict(state=self.K.state, location='page ' + loc, label=label, shown=(text or '')[:300].replace('\n', ' / '),
                                yours=want, ok='yes' if ok else 'NO', cause='' if ok else cause))
        return ok


def my_misses(S, a, grade, example=False):
    if example:
        G = [s for s in S.led if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= EX_D0]
    else:
        G = [s for s in S.led if s['a'] == a and s['grade'] == grade]
    return S.misses(G) if G else None


def check_page(K, S, sdir, harvest, extra):
    feed = json.load(open(os.path.join(sdir, 'feed', 'ctzb_feed.json')))
    H = harvest
    P = Page(K, S, sdir, feed, H, extra)
    today = S.today
    gen = feed['generated_at']
    I = H['initial']
    P.c('header', 'page errors', len(H['errors']), 0, 'script error')
    P.c('header', 'market filter', I['filter'], 'Market filter: ' + ('on' if S.gate(today) else 'off'))
    P.c('header', 'review banner date', I['rvAsof'], f'{dlong(today)} (feed {gen[11:16]} UTC)')
    P.c('footer', 'closed through / updated / checks', I['feedState'],
        f'Daily candles closed through {dlong(today - ONE_DAY)} · updated {gen[11:16]} UTC · checks passed')
    P.has('header', 'review banner says alerts off', I['review'], "Member alerts aren't switched on yet")
    P.c('read', 'posting bar', H['read']['howBar'], '70% bar')
    P.c('now', 'lead trader panel', I['lead'], "The lead trader's feed is unavailable right now. His real entries and exits appear here the moment they fill.")
    # ------------------------------------------------ which setups the picker offers
    myopenA = {sid: s for sid, s in extra['myopen'].items() if feed_grade_open(feed, sid) == 'A+'}
    fcards = {c['signal_id']: c for c in feed['cards']}
    pick = [x['sel'] for x in I['picker']]
    want = sorted(myopenA) + sorted(extra['myform']) + ['example']
    P.c('picker', 'buttons offered', ' '.join(sorted(pick)), ' '.join(sorted(want)), 'picker membership')
    # status of every open top-grade signal (mine)
    status = {}
    cards_mine = {}
    for sid, s in myopenA.items():
        o = next(o for o in feed['open_signals'] if o['signal_id'] == sid)
        if not o.get('card'):
            continue
        cc = card_for(S, o['card'], 'open', s)
        cards_mine[sid] = cc
        win = S.day[s['a']].closed_window(s['d0'], today)
        lvl = cc.get('edge'); E = s['E']
        st = 'lost' if lvl == 0 else 'intact'
        if lvl != 0:
            for b in win:
                if lvl is not None and b['L'] <= E * (1 + D(lvl) / 100): st = 'lost'; break
                if b['H'] >= E * D('1.10'): st = 'rose10'; break
        status[sid] = dict(st=st, lvl=lvl, days=(today - s['d0']).days, win=win,
                           best=disp((max(b['H'] for b in win) / E - 1) * 100, 1) if win else None,
                           worst=disp((min(b['L'] for b in win) / E - 1) * 100, 1) if win else None,
                           d10=next((disp((b['C'] / E - 1) * 100, 1) for k, b in enumerate(win) if k + 1 == 10), None))
    for b in I['picker']:
        sel = b['sel']; t = lines(b['text'])
        if sel in status:
            s = myopenA[sel]; st = status[sel]
            P.c(f'picker {sel}', 'live button', ' | '.join(t), f"{s['ch']} | Day {st['days']} | best {pct(st['best'])} · worst {pct(st['worst'])}")
        elif sel in extra['myform']:
            f = extra['myform'][sel]; fc = fcards.get(sel)
            if fc is None:
                continue
            cc = card_for(S, fc, 'forming', f=f); cards_mine[sel] = cc
            P.c(f'picker {sel}', 'forming button', ' | '.join(t),
                f"{f['a']} {f['tf']} | {pc(cc.get('reach10'))} | rose 10% in 60 days · n {cc['n']} · {'top grade' if fc['grade'] == 'A+' else 'not top grade'} · confirms {dlong(f['d0'])}")
    pt = I['pickerText'] or ''
    if not myopenA:
        P.has('picker', 'no live top-grade text', pt, 'No live top-grade setups right now.')
    if not extra['myform']:
        P.has('picker', 'nothing forming text', pt, 'Nothing forming today.')
    if 'times a year' in (I['card'] or ''):
        y1 = int(gen[:4]) - 1
        n = sum(1 for s in S.led if s['grade'] == 'A+' and 2020 <= s['d0'].year <= y1)
        P.has('quiet card', 'about N times a year', I['card'], f'Top-grade setups come about {rnd(n / (y1 - 2019), 0)} times a year (2020 to {y1} average;')
    if not myopenA and not extra['myform']:
        if feed.get('example_card') and extra['exs'] is not None:
            P.c('quiet card', 'example stands in for a quiet market', I['preview'], True)
        else:
            want = 'The market filter is on. Nothing at the top grade is forming or confirmed today.' if S.gate(today) else 'The market filter is off, so the system is quiet.'
            P.has('quiet card', 'quiet text', I['card'], want)
    # ------------------------------------------------ previous signals column
    ledA = sorted([s for s in S.led if s['grade'] == 'A+'], key=lambda s: str(s['d0']), reverse=True)
    exp_int = [f"{myopenA[sid]['ch']} | Day {status[sid]['days']} of 60 · best {pct(status[sid]['best'])} · worst {pct(status[sid]['worst'])} | {'Rose 10%' if status[sid]['st'] == 'rose10' else 'On track'}"
               for sid in sorted(myopenA) if status[sid]['st'] != 'lost']
    got_int = [' | '.join(lines(x)) for x in I['prevIntact']]
    if not exp_int:
        exp_int = ['No open top-grade setup on track or up 10%.']
    P.c('previous signals', 'first group (on track or rose 10%)', ' || '.join(sorted(got_int)), ' || '.join(sorted(exp_int)))
    exp_lost = sorted(f"{myopenA[sid]['ch']} | Day {status[sid]['days']} of 60 · best {pct(status[sid]['best'])} · worst {pct(status[sid]['worst'])} | Edge lost"
                      for sid in myopenA if status[sid]['st'] == 'lost')
    got_closed = [' | '.join(lines(x)) for x in I['prevClosed']]
    got_lost = sorted(x for x in got_closed if x.endswith('Edge lost'))
    P.c('previous signals', 'second group: edge lost', ' || '.join(got_lost), ' || '.join(exp_lost))
    got_recent = [x for x in got_closed if not x.endswith('Edge lost')]
    cut = str(ledA[4]['d0']) if len(ledA) >= 5 else None
    cand = {f"{s['ch']} | {dlong(s['d0'])} · best {pct(r6(s['m']['up']))} · worst {pct(r6(s['m']['dd']))} | {'Reached +20%' if s['m']['r20'] else 'Rose 10%' if s['m']['r10'] else 'Missed'}"
            for s in ledA if cut is None or str(s['d0']) >= cut}
    P.c('previous signals', 'second group: 5 most recent closed', len(got_recent), min(5, len(ledA)))
    for x in got_recent:
        P.c('previous signals', 'recent closed signal', x, x if x in cand else 'one of the 5 latest top-grade signals (mine): ' + ' ; '.join(sorted(cand))[:400])
    # ------------------------------------------------ each selection: card, chart
    for st in H['states']:
        sel = st['sel']
        if sel == 'example':
            xc = feed['example_card']; s = extra['exs']
            if xc is None or s is None:
                P.has('example', 'example unavailable', st['now']['card'], 'Example unavailable'); continue
            cc = card_for(S, xc, 'example', s); kind = 'example'; a, tf = 'ETH', '2D'; grade = 'A+'
            entry = s['e']; mi = my_misses(S, 'ETH', 'A+', example=True)
        elif sel in status:
            s = myopenA[sel]; cc = cards_mine[sel]; kind = 'open'; a, tf = s['a'], s['tf']
            o = next(o for o in feed['open_signals'] if o['signal_id'] == sel); grade = o['grade']
            entry = s['e']; mi = my_misses(S, a, grade)
        elif sel in extra['myform'] and sel in fcards:
            f = extra['myform'][sel]; cc = cards_mine[sel]; kind = 'forming'; a, tf = f['a'], f['tf']; grade = fcards[sel]['grade']
            entry = f['price']; mi = my_misses(S, a, grade)
        else:
            continue
        check_card_view(P, S, sel, kind, st, cc, a, tf, grade, entry, mi, status.get(sel), extra, feed)
    # ------------------------------------------------ past signals tab
    for asset in ('all', 'ETH', 'BTC'):
        R = H['record'][asset]
        rows_m = [s for s in ledA if asset == 'all' or s['a'] == asset]
        P.c(f'past signals {asset}', 'count line', R['recCount'], f"{len(rows_m)} signals · {sum(not s['m']['r10'] for s in rows_m)} missed +10%")
        exp_sum = []
        for a in ASSETS:
            if asset != 'all' and a != asset:
                continue
            g = S.grades[(a, 'A+')]
            if not g['n']:
                continue
            mi = my_misses(S, a, 'A+')
            t = [a, f"{g['n']} signals", 'Rose 10% in 60 days', pc(g['reach10']), 'Reached +20% in 60 days', pc(g['reach20']),
                 'Rose 10%, never fell 25.3%', pc(g['surv10']), 'Median deepest dip', pct(g['medDip'])]
            if mi:
                t += ['Misses: median best price', pct(mi['median_peak'])]
            exp_sum.append(' | '.join(t))
        P.c(f'past signals {asset}', 'summary boxes', ' || '.join(' | '.join(lines(x)) for x in R['recSum']), ' || '.join(exp_sum))
        got = R['recRows']
        P.c(f'past signals {asset}', 'rows', len(got), len(rows_m))
        exp = {}
        for s in rows_m:
            m = s['m']
            exp[(dlong(s['d0']), s['ch'])] = [dlong(s['d0']), s['ch'], money(s['e']), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
                                              pct(r6(m['up'])), pct(r6(m['dd'])), pct(r6(m['ret'])), str(m['dpk'])]
        prev = None
        for row in got:
            k = (row[0], row[1])
            P.c(f'past signals {asset} {k[1]} {k[0]}', 'row', ' | '.join(row), ' | '.join(exp.get(k, ['(not one of my top-grade signals)'])))
            d = dt.datetime.strptime(row[0].replace('Sept', 'Sep'), '%d %b %Y').date()
            if prev is not None and d > prev:
                P.c(f'past signals {asset}', 'newest first', str(d), f'on or before {prev}')
            prev = d


def feed_grade_open(feed, sid):
    o = next((o for o in feed['open_signals'] if o['signal_id'] == sid), None)
    return o['grade'] if o else None


def card_for(S, c, kind, s=None, f=None):
    lens_txt = c['confirmations']
    lens = frozenset() if lens_txt in ('none', '-', '') else frozenset(UNPLAIN.get(x, x) for x in lens_txt.split('; '))
    return S.card(c['asset'], c['timeframe'], c['grade'], lens, known=EX_D0 if kind == 'example' else None, example=kind == 'example')


def edge_text(cc):
    e = cc.get('edge')
    if e == 0:
        return 'Below the 70% bar from entry'
    if e is not None:
        return f'{pct(e, 0)} before it rises 10%'
    return 'Holds at every level'


def check_card_view(P, S, sel, kind, st, cc, a, tf, grade, entry, mi, stat, extra, feed):
    now = st['now']; loc = f'card {sel}'
    L = lines(now['card'])
    top = grade == 'A+'
    P.c(loc, 'where', L[0].upper() if L else '', f"{a} · {tf} CHART" + (' · EXAMPLE' if kind == 'example' else ''))
    P.c(loc, 'state', L[1] if len(L) > 1 else '', {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind])
    if kind == 'forming':
        f = extra['myform'][sel]
        want = f"Low {dlong(f['low_day'])} · confirms {dlong(f['d0'])}" + (f" if it closes above {money(f['kill']['cent'])}" if f['kill'] else '')
    elif kind == 'open':
        s = extra['myopen'][sel]
        want = f"Confirmed {dlong(s['d0'])} · entry close {money(s['e'])} · day {stat['days']} of 60 · best so far {pct(stat['best'])} · worst {pct(stat['worst'])}"
    else:
        want = f"Example: confirmed {dlong(EX_D0)} · entry close {money(entry)}"
    P.c(loc, 'line', L[2] if len(L) > 2 else '', want)
    if kind == 'open':
        lvl = stat['lvl']
        if stat['st'] == 'lost':
            t = 'Edge lost. ' + ('Its odds were below the bar from the entry.' if lvl == 0 else f'It fell to its edge level ({pct(lvl, 0)}) before rising 10%.')
        elif stat['st'] == 'rose10':
            t = 'Rose 10%. ' + ('It has risen 10% from the entry close.' if lvl is None else f'It rose 10% before falling to its edge level ({pct(lvl, 0)}).')
        else:
            t = 'On track. ' + ('It has neither risen 10% nor lost its edge; its odds hold at every fall measured.' if lvl is None else f'It has not fallen to its edge level ({pct(lvl, 0)}) or risen 10% yet.')
        P.c(loc, 'status line', L[3] if len(L) > 3 else '', t + ' The odds below are as of the entry close, not from today.')
    if not cc['n']:
        P.has(loc, 'no odds yet', now['card'], 'No odds yet'); return
    txt = now['card']
    P.has(loc, 'big number', txt, f"\n{pc(cc['reach10'])}\nrose 10% within 60 days" + (' · at the entry close, not from today' if kind == 'open' else ''))
    P.has(loc, 'line under it', txt, f"{pc(cc['surv10'])} did it without ever falling 25.3%")
    P.has(loc, 'sample line', txt, f"from {cc['sample']} · every figure covers the 60 days after entry")
    if mi is None:
        mt = 'n/a'
    else:
        mt = 'none missed' if not mi['misses'] else f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak'])}"
    pool_name = 'top-grade' if (grade == 'A+' or kind == 'example') else 'same-grade'
    kv = [' | '.join(lines(x)) for x in now['kvs']]
    P.c(loc, 'key figures', ' || '.join(kv), ' || '.join([f"Typical high | {pct(cc['bestX'])}", f"Typical drop from entry | {pct(cc['maxX'])}",
                                                         f"Edge gone below | {edge_text(cc)}", f"If it misses: went above entry | {mt}"]))
    if mi:
        P.has(loc, 'misses pool', txt, f"{'of the' if kind == 'example' else 'of all'} {mi['signals']} {a} {pool_name} signals{' known by then' if kind == 'example' else ''}")
    P.has(loc, 'lead trader', txt, 'Lead trader: unavailable')
    pool_t = f" · {mi['misses']} misses of {'the' if kind == 'example' else 'all'} {mi['signals']} {a} {pool_name} signals{' known by then' if kind == 'example' else ''}" if mi else ''
    tiles = [('Dip before the high, from entry', pct(cc['dipX'])), ('High lands around', f"Day {cc['dHigh']}"),
             (f"Reached +20% within 60 days · n {cc['n']}", pc(cc['reach20'])), (f"Touched {MINUS}30% within 60 days · n {cc['n']}", pc(cc['touched30'])),
             ('Typical high', pct(cc['bestX'])), ('Deepest dip lands around', f"Day {cc['dLow']}"),
             ('Typical worst drop, misses' + pool_t, pct(mi['worst']) if mi else 'n/a'),
             ('Typical change by day 60, misses' + pool_t, pct(mi['d60']) if mi else 'n/a')]
    got = [(x['t'], x['v']) for x in now['tiles']]
    for (gt, gv), (wt, wv) in zip(got, tiles):
        P.c(loc, f'tile "{wt}"', f'{gt} = {gv}', f'{wt} = {wv}')
    P.c(loc, 'tile count', len(got), len(tiles))
    lad = [('From entry', cc['fe']['ok'], cc['fe']['okx'], cc['n'])] + [(f"Falls {r['fell']}% first", r['ok'], r['okx'], r['n']) for r in cc['lad']]
    for gl, (t, v, x, n) in zip(now['ladder'], lad):
        P.c(loc, f'ladder "{t}"', ' | '.join(lines(gl['text'])) + (' [gone]' if gl['gone'] else ''),
            f"{t} n {n} | {pc(v)}" + (' [gone]' if (x is not None and x < 70) else ''))
    P.c(loc, 'ladder rows', len(now['ladder']), 5)
    eras = [f"Before 2022 n {cc['nOld']} | {pc(cc['sOld'])}", f"Since 2022 n {cc['nNew']} | {pc(cc['sNew'])}"]
    P.c(loc, 'eras', ' || '.join(' | '.join(lines(x)) for x in now['eras']), ' || '.join(eras))
    P.has(loc, 'foot: entry quality only', txt, 'Entry quality only: no exit, not a trade or a track record.')
    # ------------------------------------------------ the chart
    ch = st['chart']; locc = f'chart {sel}'
    e2 = rnd(entry, 2)
    if kind == 'forming':
        f = extra['myform'][sel]
        P.c(locc, 'title', ch['chTitle'].upper(), f"{a} · {tf} · {'SETUP FORMING' if top else 'FORMING, NOT TOP GRADE'}")
        P.has(locc, 'subtitle', ch['chSub'], f"Low {dlong(f['low_day'])} · confirms {dlong(f['d0'])} · price levels drawn from today's price ({money(entry)})")
    elif kind == 'open':
        s = extra['myopen'][sel]
        P.c(locc, 'title', ch['chTitle'].upper(), f"{a} · {tf} · LIVE SETUP, DAY {stat['days']} OF 60")
        P.has(locc, 'subtitle', ch['chSub'], f"Confirmed {dlong(s['d0'])} · entry close {money(s['e'])}. Zones use this setup's own card ({cc['sample']}).")
    else:
        P.c(locc, 'title', ch['chTitle'].upper(), 'ETH · 2-DAY · EXAMPLE: PAST CONFIRMED SETUP')
        P.has(locc, 'subtitle', ch['chSub'], f"Confirmed {dlong(EX_D0)} · entry close {money(entry)}")
    side = [' | '.join(lines(x)) for x in ch['sideKV']]
    eg = cc.get('edge')
    egt = 'below the bar already' if eg == 0 else ('holds at every level' if eg is None else f"{money(pxat(e2, eg))} ({pct(eg, 0)})")
    want = [f"Typical high | {pct(cc['bestX'])} · {money(pxat(e2, cc['bestX']))}", f"+10% level | {money(pxat(e2, 10))}",
            f"Reached +20% within 60 days | {pc(cc['reach20'])}", f"Typical drop | {pct(cc['maxX'])} · {money(pxat(e2, cc['maxX']))}",
            f"Edge gone below | {egt}"]
    if kind == 'open':
        want += [f"Best so far | {pct(stat['best'])}", f"Worst so far | {pct(stat['worst'])}", f"Day 10 | {'not yet' if stat['d10'] is None else pct(stat['d10'])}"]
    P.c(locc, 'side box', ' || '.join(side), ' || '.join(want))
    P.has(locc, 'side big number', ch['side'], f"{pc(cc['reach10'])}\nrose 10% within 60 days, from {cc['n']} past signals; {pc(cc['surv10'])} without ever falling 25.3%")
    P.has(locc, 'side sample', ch['side'], f"from {cc['sample']}")
    texts = [t['text'] for t in ch['chartTexts']]
    lv = dict(high=pxat(e2, cc['bestX']), t20=pxat(e2, 10), drop=pxat(e2, cc['maxX']))
    for w in (f"Typical high {pct(cc['bestX'])}", f"+10% · {pc(cc['reach10'])} of past signals got here", f"Typical drop {pct(cc['maxX'])}",
              money(lv['high']), money(lv['t20']), money(e2), money(lv['drop']), 'Day 60', f"High usually ~day {cc['dHigh']}"):
        P.c(locc, f'label "{w}"', w if w in texts else 'missing', w)
    bands = [(cc['fe']['ok'], cc['n'])] + [(r['ok'], r['n']) for r in cc['lad'][:3]]
    got_b = [t for t in texts if re.match(r'^(\d+% · n \d+|n/a)$', t)]
    P.c(locc, 'ladder band labels', ' | '.join(got_b), ' | '.join('n/a' if v is None else f'{v}% · n {n}' for v, n in bands))
    if eg not in (None, 0):
        w = f"Edge gone below {money(pxat(e2, eg))} ({pct(eg, 0)}, before +10%)"
        P.c(locc, 'edge label', w if w in texts else ' | '.join(t for t in texts if t.startswith('Edge')) or 'missing', w)
    else:
        P.c(locc, 'edge label', ' | '.join(t for t in texts if t.startswith('Edge')) or 'none', 'none')
    if kind == 'forming':
        f = extra['myform'][sel]
        c_ = S.ch[(a, tf)]; tb = c_.bars[f['ti']]
        w = f"Low {dlong(f['low_day'])} · {money(raw_bar(P.sdir, a, tf, tb['t'])['l'])}"
        P.c(locc, 'low marker label', w if w in texts else ' | '.join(t for t in texts if t.startswith('Low ')) or 'missing', w)
        if True:
            w = f"Confirms {dlong(f['d0'])} · entry, day 0"
            got = [t for t in texts if t.startswith('Confirms')]
            P.c(locc, 'confirms label', ' | '.join(got) or 'none', w if f['need'] > 0 else 'none')
    chart_geometry(P, S, sel, kind, ch, st.get('happened'), cc, a, tf, entry, extra, feed)
    # cloud
    if kind == 'example':
        G = [s for s in S.led if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= EX_D0]
        P.c(locc, 'cloud subtitle', ch['cloudSub'], f"ETH top-grade signals whose 60 days had closed by {dlong(EX_D0)}, n {len(G)}")
    else:
        G = [s for s in S.led if s['a'] == a and s['grade'] == 'A+']
        P.c(locc, 'cloud subtitle', ch['cloudSub'], f"Every past {a} top-grade signal, n {len(G)}")
    PP = S.paths(G)
    d60 = PP['days'][60]
    P.has(locc, 'cloud day 60', ch['cloudNote'], f"Day 60: median {pct(d60['med'])}, middle half {pct(d60['q25'])} to {pct(d60['q75'])}.")
    med_line = next((p for p in ch['cloudPoly'] if p['tag'].lower() == 'polyline'), None)
    if med_line:
        pts = [tuple(map(float, x.split(','))) for x in med_line['points'].split()]
        Yc = lambda v: 230 - (max(-40, min(100, v)) - -40) / 140 * (230 - 12)
        bad = [d['day'] for d, (x, y) in zip(PP['days'], pts) if abs(y - Yc(d['med'])) > 1e-6 or abs(x - (20 + 940 * d['day'] / 60)) > 1e-6]
        P.c(locc, 'cloud median path, 61 points (y vs my medians)', 'all match' if not bad and len(pts) == 61 else f'{len(pts)} points; off on days {bad[:10]}', 'all match')
    band = next((p for p in ch['cloudPoly'] if p['tag'].lower() == 'polygon'), None)
    if band:
        pts = [tuple(map(float, x.split(','))) for x in band['points'].split()]
        Yc = lambda v: 230 - (max(-40, min(100, v)) - -40) / 140 * (230 - 12)
        want_pts = [Yc(d['q75']) for d in PP['days']] + [Yc(d['q25']) for d in reversed(PP['days'])]
        bad = sum(abs(y - w) > 1e-6 for (x, y), w in zip(pts, want_pts))
        P.c(locc, 'cloud middle-half band (122 points vs my quartiles)', 'all match' if not bad and len(pts) == 122 else f'{bad} off', 'all match')
    if kind == 'example' and st.get('happened'):
        example_happened(P, S, st['happened'], entry, extra)
        hp = [p for p in st['happened']['cloudPoly'] if p['tag'].lower() == 'polyline']
        if len(hp) >= 2:
            pts = [tuple(map(float, x.split(','))) for x in hp[1]['points'].split()]
            exs = extra['exs']; w_ = exs['m']['w']; E_ = exs['E']
            Yc = lambda v: 230 - (max(-40, min(100, v)) - -40) / 140 * (230 - 12)
            want = [(20.0, Yc(0))] + [(20 + 940 * (2 * k) / 60, Yc(float((w_[2 * k - 1]['C'] / E_ - 1) * 100))) for k in range(1, 31)]
            bad = sum(abs(x - wx) > 1e-6 or abs(y - wy) > 1e-6 for (x, y), (wx, wy) in zip(pts, want))
            P.c('chart example What happened', "this signal's path on the cloud (31 points vs my daily closes)", 'all match' if not bad and len(pts) == 31 else f'{bad} off of {len(pts)}', 'all match')
        else:
            P.c('chart example What happened', "this signal's path on the cloud", 'missing', 'drawn')


def chart_geometry(P, S, sel, kind, ch, hap, cc, a, tf, entry, extra, feed):
    """x of the day lines by date, y of the levels by the axis built only from what is shown"""
    locc = f'chart {sel}'
    tfd = int(tf[:-1])
    if kind == 'example':
        ex = json.load(open(os.path.join(P.sdir, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')))
        bars = ex['bars']; E = ex['entry_index']
        # the example file against my own 2D candles
        mybars = {b['t']: b for b in S.ch[('ETH', '2D')].bars}
        badb = [b['t'] for b in bars if b['t'] not in mybars or any(abs(b[k] - (raw_bar(P.sdir, 'ETH', '2D', b['t'])[k])) > 1e-9 for k in 'ohlc')]
        P.c('chart example', 'example chart file bars equal the 2D candles', 'all equal' if not badb else f'{len(badb)} differ', 'all equal')
        P.c('chart example', 'entry bar closes 22 Sep 2024', str(next_open(udate(bars[E]['t']), 2) - ONE_DAY), str(EX_D0))
        P.c('chart example', 'entry close', ex['entry_close'], rnd(S.ch[('ETH', '2D')].bars[[b['t'] for b in S.ch[('ETH', '2D')].bars].index(bars[E]['t'])]['c'], 2))
        last = udate(bars[-1]['t']); P.c('chart example', 'file ends with the bar holding day 60', str(bar_start(EX_D0 + dt.timedelta(days=60), 2)), str(last))
        t_entry = EX_D0
        opens = [udate(b['t']) for b in bars]
        nS = len(bars); A = E
    else:
        p = os.path.join(P.sdir, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        bars = [dict(t=int(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
        opens = [udate(b['t']) for b in bars]
        if kind == 'open':
            s = extra['myopen'][sel]; t_entry = s['d0']
            E = opens.index(bar_start(t_entry, tfd)) if tfd > 1 else opens.index(t_entry)
        else:
            f = extra['myform'][sel]; t_entry = f['d0']; E = len(bars) - 1
        while opens[-1] <= t_entry + dt.timedelta(days=61):
            opens.append(next_open(opens[-1], tfd))
        nS = len(opens)
        A = slot_of(opens, t_entry) if kind == 'forming' else E
    slot = (R_ - L_) / nS
    X = lambda i: L_ + slot * i + slot / 2
    lines_ = ch['chartLines']
    vl = [l for l in lines_ if l['x1'] == l['x2'] and l['y1'] == T_ and l['y2'] == B_]
    texts = {t['text']: t for t in ch['chartTexts']}

    def vx(label_start):
        t = next((t for t in ch['chartTexts'] if t['text'].startswith(label_start)), None)
        return None if t is None else t['x'] - 6
    def chk_x(name, label_start, idx, day_desc):
        x = vx(label_start)
        if x is None:
            P.c(locc, f'{name} line', 'missing', f'slot {idx}'); return
        gi = round((x - L_) / slot - 0.5, 6)
        P.c(locc, f'{name} line on the bar holding {day_desc}', f'bar {gi:g} (opens {opens[int(round(gi))] if 0 <= round(gi) < len(opens) else "?"})', f'bar {idx} (opens {opens[idx]})')
    if kind == 'forming':
        chk_x('Today', 'Today', E, 'today')
        if A > E:
            chk_x('Confirms', 'Confirms', A, f'the confirmation day {t_entry}')
    else:
        chk_x('Entry', 'Entry', E, f'the entry day {t_entry}')
    chk_x('Day 60', 'Day 60', min(nS - 1, slot_of(opens, t_entry + dt.timedelta(days=60))), f'day 60 ({t_entry + dt.timedelta(days=60)})')
    if cc.get('dHigh') is not None:
        chk_x('High', 'High usually', slot_of(opens, t_entry + dt.timedelta(days=cc['dHigh'])), f"day {cc['dHigh']}")
    # vertical scale: only what is shown at the alert
    e2 = rnd(entry, 2)
    hi_l, drop = pxat(e2, cc['bestX']), pxat(e2, cc['maxX'])
    shown = bars[:E + 1] if kind == 'example' else bars
    lo = min(min(b['l'] for b in shown), drop, e2 * 0.8) * 0.95
    hi = max(max(b['h'] for b in shown), hi_l) * 1.07
    Y = lambda p: B_ - (p - lo) / (hi - lo) * (B_ - T_)
    hl = [l for l in lines_ if l['y1'] == l['y2'] and l['x1'] != L_]
    for name, p in (('typical high', hi_l), ('+10%', pxat(e2, 10)), ('entry', e2), ('typical drop', drop)):
        ok = any(abs(l['y1'] - Y(p)) < 1e-6 for l in hl)
        P.c(locc, f'{name} line height (axis from {"bars to the entry" if kind == "example" else "the bars shown"})', 'at its price' if ok else 'not at its price', 'at its price')
    # candles drawn at the alert: none after the entry bar on the example
    if kind == 'example':
        nwick = len([l for l in lines_ if l['x1'] == l['x2'] and l['y1'] != T_])
        P.c(locc, 'candles drawn at the alert', nwick, E + 1)
        if hap:
            nw2 = len([l for l in hap['chartLines'] if l['x1'] == l['x2'] and l['y1'] != T_])
            P.c(locc, 'candles drawn in What happened', nw2, len(bars))


_RAW = {}


def raw_bar(sdir, a, tf, t):
    k = (sdir, a, tf)
    if k not in _RAW:
        _RAW[k] = {int(float(r['time'])): dict(o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']))
                   for r in csv.DictReader(open(os.path.join(sdir, 'data', f'{a}_{tf}.csv')))}
    return _RAW[k].get(t, dict(o=None, h=None, l=None, c=None))


def slot_of(opens, d):
    i = 0
    while i + 1 < len(opens) and opens[i + 1] <= d:
        i += 1
    return i


def example_happened(P, S, hap, entry, extra):
    s = extra['exs']; m = s['m']; w = m['w']; E = s['E']
    locc = 'chart example What happened'
    side = [' | '.join(lines(x)) for x in hap['sideKV']][5:]
    kp = max(range(60), key=lambda k: (w[k]['H'], -k)); kl = min(range(60), key=lambda k: (w[k]['L'], k))
    dd = lambda k: f'days {(k // 2) * 2 + 1}–{(k // 2) * 2 + 2}'
    # the 2D bar holding the high (its own high is the daily max)
    want = [f"Reached +10% / +20% | {'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}",
            f"Best price | {pct((w[kp]['H'] / E - 1) * 100)}, {dd(kp)}",
            f"Deepest drop | {pct((w[kl]['L'] / E - 1) * 100)}, {dd(kl)}",
            f"Day 10 check | {'Red' if w[9]['C'] < E else 'Green'}, {pct((w[9]['C'] / E - 1) * 100)}",
            f"Price on day 60 | {pct((w[59]['C'] / E - 1) * 100)}"]
    P.c(locc, 'side box', ' || '.join(side), ' || '.join(want))
    texts = [t['text'] for t in hap['chartTexts'] if t['text'].startswith('This one')]
    want_t = [f"This one: {money(float(w[kp]['H']))} · {pct((w[kp]['H'] / E - 1) * 100)} · {dd(kp)}",
              f"This one: {money(float(w[kl]['L']))} · {pct((w[kl]['L'] / E - 1) * 100)} · {dd(kl)}"]
    P.c(locc, 'markers', ' | '.join(texts), ' | '.join(want_t))


if __name__ == '__main__':
    sdir, now, name, harvest, out = sys.argv[1:6]
    now = dt.datetime.fromisoformat(now.replace('Z', '+00:00'))
    K, S, extra = check_state(sdir, now, name)
    ndata = len(K.rows)
    check_page(K, S, sdir, json.load(open(harvest)), extra)
    with open(out, 'w', newline='') as fh:
        wr = csv.DictWriter(fh, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
        wr.writeheader(); wr.writerows(K.rows)
    bad = [r for r in K.rows if r['ok'] != 'yes']
    print(name, 'data', ndata, 'page', len(K.rows) - ndata, 'disagreements', len(bad))
    for r in bad[:60]:
        print('  ', r['location'], '|', r['label'], '| shown:', r['shown'][:200], '| mine:', r['yours'][:200])
