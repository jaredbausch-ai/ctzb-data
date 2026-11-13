"""Audit 18: what the member page should show, built from MY values (stage_data ctx['MY']), compared with the DOM dump."""
import csv, datetime as dt, json, math, os
from fractions import Fraction as Fr
import core as K
from core import rnd, D

MINUS = '−'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']


def dec(v):
    """exact decimal value of a stored figure"""
    if isinstance(v, Fr): return v
    if isinstance(v, int): return Fr(v)
    return Fr(str(v))


def num_s(v, d=1):
    r = rnd(dec(v), d)
    if r == 0:
        return f'{0:.{d}f}'
    s = f'{abs(r):.{d}f}' if d else str(abs(int(r)))
    return (MINUS if r < 0 else '') + s


def pct(v, d=1, sign=True):
    if v is None or v == '': return 'n/a'
    r = rnd(dec(v), d)
    return ('+' if sign and r > 0 else '') + num_s(v, d) + '%'


def money(v):
    if v is None: return 'n/a'
    r = rnd(dec(v), 2)
    c = int(round(abs(r) * 100)); s = f'{c // 100:,}.{c % 100:02d}'
    return ('-' if r < 0 else '') + '$' + s


def px_at(entry, p):
    """entry (2-dp price) moved by p percent (6-dp figure), exact arithmetic on cents, half away from zero"""
    if entry is None or p is None: return None
    cents = dec(entry) * 100
    v = cents * (1 + dec(p) / 100)
    return float(Fr(rnd(v, 0), 100))


def date_long(iso):
    if not iso: return ''
    d = dt.date.fromisoformat(str(iso)[:10])
    return f'{d.day} {MON[d.month - 1]} {d.year}'


def ts(d):
    return int((dt.datetime(d.year, d.month, d.day) - dt.datetime(1970, 1, 1)).total_seconds())


class Model:
    """one selectable thing on the page, from my numbers"""

    def __init__(self, MY, kind, o, extra=None):
        self.MY = MY; self.kind = kind; self.o = o; self.x = extra or {}
        self.asset, self.tf, self.chart, self.grade = o['asset'], o['tf'], o['chart'], o['grade']
        self.top = self.grade == 'A+'
        self.n = o['past_trades']
        self.high, self.drop, self.dipb = o['typical_biggest_rise_exact_pct'], o['typical_deepest_dip_exact_pct'], o['typical_dip_before_rise_exact_pct']
        self.lad = o['ladder']
        self.edge = o['edge']
        self.entry = o.get('entry') if kind != 'forming' else None
        self.mi = MY.get('ex_misses') if kind == 'example' else MY['misses'].get((self.asset, self.grade))

    def pool_words(self):
        mi = self.mi
        return f"{'the' if self.kind == 'example' else 'all'} {mi['signals']} {self.asset} {'top-grade' if self.top else 'same-grade'} signals{' known by then' if self.kind == 'example' else ''}"


def bar_next_open_ts(t, tfd):
    d = K.utcdate(t)
    return ts(K.bar_next_open(d, tfd))


class PageCheck:
    def __init__(self, C, ctx, root, example_json):
        self.C = C; self.ctx = ctx; self.MY = ctx['MY']; self.root = root; self.ex = example_json
        self.feed = ctx['feed']

    def eq(self, loc, label, shown, mine, cause=''):
        return self.C.add(loc, label, shown, mine, ok=(shown == mine), cause=cause)

    def eqi(self, loc, label, shown, mine, cause=''):
        return self.C.add(loc, label, shown, mine, ok=(shown or '').upper() == (mine or '').upper(), cause=cause)

    def near(self, loc, label, shown, mine, tol=1e-6, cause=''):
        ok = shown is not None and mine is not None and abs(float(shown) - float(mine)) <= tol
        return self.C.add(loc, label, shown, None if mine is None else round(float(mine), 6), ok=ok, cause=cause)

    # ------------------------------------------------------------------ models
    def models(self):
        MY = self.MY; out = {}
        order = [(a, tf) for a in K.ASSETS for tf in K.TFS]
        form = [Model(MY, 'forming', o, o) for k, o in MY['cards'].items() if k.startswith('feed.cards ')]
        form.sort(key=lambda m: order.index((m.asset, m.tf)))
        opens = [Model(MY, 'open', op['card'], op) for op in MY['opens'] if op['grade'] == 'A+']
        ex = next((Model(MY, 'example', o, o) for k, o in MY['cards'].items() if k == 'feed.example_card'), None)
        top = [m for m in form if m.top]
        ranked = sorted(form, key=lambda m: -(m.o['rose10_within60d_pct'] if m.o['rose10_within60d_pct'] is not None else -1))
        best = (top or ranked or [None])[0]
        form_btns = top + [m for m in ranked if m not in top]
        return dict(opens=opens, forming=form_btns, example=ex, best=best)

    # ------------------------------------------------------------------ the card
    def card(self, loc, d, m, best_id=None):
        c = d['card']; o = m.o; e = self.eq
        self.eqi(loc, 'card where', c['where'], f"{m.asset} · {m.tf} chart" + (' · example' if m.kind == 'example' else ''))
        e(loc, 'card state', c['state'], {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[m.kind])
        x = m.x
        if m.kind == 'forming':
            line = f"Low {date_long(x['low_day'])} · confirms {date_long(x['confirms'])}" + (f" if it closes above {money(x['kill'])}" if x.get('kill') else '')
            l2 = ("Not confirmed yet. It can still vanish before it confirms." if m.top else
                  ("Best setup forming today." if best_id == x['signal_id'] else "Setup forming.") + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
        elif m.kind == 'open':
            line = f"Confirmed {date_long(x['entry_date'])} · entry close {money(x['entry'])} · day {x['elapsed']} of 60 · best so far {pct(x['best'])} · worst {pct(x['worst'])}"
            lv = x['edge_level']; st = x['edge_status']
            if st == 'lost':
                l2 = 'Edge lost. ' + ("Its odds were below the bar from the entry." if lv == 0 else f"It fell to its edge level ({pct(lv, 0)}) before rising 10%.")
            elif st == 'rose10':
                l2 = 'Rose 10%. ' + ("It has risen 10% from the entry close." if lv is None else f"It rose 10% before falling to its edge level ({pct(lv, 0)}).")
            else:
                l2 = 'On track. ' + ("It has neither risen 10% nor lost its edge; its odds hold at every fall measured." if lv is None else f"It has not fallen to its edge level ({pct(lv, 0)}) or risen 10% yet.")
            l2 += ' The odds below are as of the entry close, not from today.'
        else:
            line = f"Example: confirmed {date_long('2024-09-22')} · entry close {money(m.entry)}"; l2 = None
        e(loc, 'card line (dates, prices, day count)', c['head'][0] if c['head'] else None, line)
        e(loc, 'card status line', c['head'][1] if len(c['head']) > 1 else None, l2)
        pv = lambda v: 'n/a' if v is None else f'{v}%'
        e(loc, 'big number: rose 10% within 60 days', c['big'], pv(o['rose10_within60d_pct']), cause='empty sample printed as "n/a%"' if m.n == 0 else '')
        e(loc, 'big number caption', c['odds'][1], 'rose 10% within 60 days' + (' · at the entry close, not from today' if m.kind == 'open' else ''))
        e(loc, 'did it without ever falling 25.3%', c['odds'][2], f"{pv(o['rose10_never_fell25_within60d_pct'])} did it without ever falling 25.3%", cause='empty sample printed as "n/a%"' if m.n == 0 else '')
        e(loc, 'sample line (text and n)', c['odds'][3], f"from {o['sample']} · every figure covers the 60 days after entry")
        st = {k[0]: k[1] for k in c['stats']}
        e(loc, 'Typical high', st.get('Typical high'), pct(m.high))
        e(loc, 'Typical drop from entry', st.get('Typical drop from entry'), pct(m.drop))
        # one rounding only: the 1-dp figure from the full-precision median must equal the 6-dp figure rounded once
        e(loc, 'Typical high: 6-place figure rounded once = full-precision median rounded once', pct(m.high), pct(o['typical_biggest_rise_pct']))
        e(loc, 'Typical drop: 6-place figure rounded once = full-precision median rounded once', pct(m.drop), pct(o['typical_deepest_dip_pct']))
        e(loc, 'Dip before high: 6-place figure rounded once = full-precision median rounded once', pct(m.dipb), pct(o['typical_dip_before_rise_pct']))
        edge_txt = 'n/a' if m.n == 0 else 'Below the 70% bar from entry' if m.edge == 0 else f"{pct(m.edge, 0)} before it rises 10%" if m.edge is not None else 'Holds at every level'
        e(loc, 'Edge gone below', st.get('Edge gone below'), edge_txt, cause='empty sample reads as "Holds at every level"' if m.n == 0 else '')
        mi = m.mi
        miss_txt = 'n/a' if not mi else 'none missed' if not mi['misses'] else f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}"
        e(loc, 'If it misses: went above entry', st.get('If it misses: went above entry'), miss_txt)
        e(loc, 'misses pool line', c['pool'], f"of {m.pool_words()}" if mi and mi['signals'] else None)
        e(loc, 'Lead trader marker', c['marker'], 'Lead trader: unavailable')
        tail = f" · {mi['misses']} misses of {m.pool_words()}" if mi and mi['signals'] else ''
        tiles = [("Dip before the high, from entry", pct(m.dipb)), ("High lands around", 'n/a' if o['typical_day_of_60d_high'] is None else f"Day {o['typical_day_of_60d_high']}"),
                 (f"Reached +20% within 60 days · n {m.n}", pv(o['rose20_within60d_pct'])), (f"Touched {MINUS}30% within 60 days · n {m.n}", pv(o['fell30_within60d_pct'])),
                 ("Typical high", pct(m.high)), ("Deepest dip lands around", 'n/a' if o['typical_day_of_deepest_dip'] is None else f"Day {o['typical_day_of_deepest_dip']}"),
                 ("Typical worst drop, misses" + tail, pct(mi['median_worst_drop_pct']) if mi else 'n/a'),
                 ("Typical change by day 60, misses" + tail, pct(mi['median_day60_pct']) if mi else 'n/a')]
        e(loc, 'tile count', len(c['tiles']), len(tiles))
        for got, (t, v) in zip(c['tiles'], tiles):
            e(loc, f'tile label: {t[:40]}', got[0], t); e(loc, f'tile value: {t[:40]}', got[1], v)
        self.eqi(loc, 'ladder heading', c['ladderLbl'][0] if c['ladderLbl'] else None, 'Where the odds fade · this setup')
        rows = []
        for th, hit, okp, lq, ex6, exf in m.lad:
            name = 'From entry' if th is None else f'Falls {th}% first'
            rows.append((f'{name} n {hit}', 'n/a' if okp is None else f'{okp}%', exf is not None and exf < 70, f'{okp if okp is not None else 0}%'))
        e(loc, 'ladder rows', len(c['ladder']), len(rows))
        for got, (t, v, gone, w) in zip(c['ladder'], rows):
            e(loc, f'ladder {t.split(" n ")[0]}: label and n', got['t'], t)
            e(loc, f'ladder {t.split(" n ")[0]}: share shown', got['v'], v)
            e(loc, f'ladder {t.split(" n ")[0]}: below-70 colour (exact share)', got['gone'], gone)
            e(loc, f'ladder {t.split(" n ")[0]}: bar width', got['w'], w)
        e(loc, 'ladder note', c['ladderNote'], "Share of this setup's past signals that, after first falling that far, still rose 10% before ever falling 25.3%. Below 70% the edge is gone. Small samples: read the n.")
        eras = [('Before 2022', o['before_2022']), ('Since 2022', o['since_2022'])]
        e(loc, 'era rows', len(c['eras']), 2)
        for got, (t, (n_, v_)) in zip(c['eras'], eras):
            e(loc, f'era {t}: label and n', got['t'], f'{t} n {n_}'); e(loc, f'era {t}: share', got['v'], 'n/a' if v_ is None else f'{v_}%')
        lost = m.kind == 'open' and x.get('edge_status') == 'lost'
        e(loc, 'frame colour (live / faded)', c['frame'], 'var(--fade)' if (m.kind == 'forming' and not m.top) or lost else 'var(--live)')
        e(loc, 'big number dimmed iff edge lost', c['bigDim'], '0.5' if lost else '')
        e(loc, 'no stale note', c['stale'], None)

    # ------------------------------------------------------------------ picker / prev / header
    def chrome(self, loc, d, M, sel_id):
        e = self.eq; MY = self.MY; feed = self.feed
        live = d['picker'][0]; form = d['picker'][1]
        exp_live = [(m.x['signal_id'], f"{m.chart} Day {m.x['elapsed']} best {pct(m.x['best'])} · worst {pct(m.x['worst'])}") for m in M['opens']]
        e(loc, 'picker Live: buttons', len(live['btns']), len(exp_live))
        for b, (sid, t) in zip(live['btns'], exp_live):
            e(loc, f'picker Live {sid}: id', b['sel'], sid); e(loc, f'picker Live {sid}: text', b['text'], t)
            e(loc, f'picker Live {sid}: pressed', b['pressed'], str(sid == sel_id).lower())
        if not exp_live:
            e(loc, 'picker Live: none text', live['none'], 'No live top-grade setups right now.')
        exp_form = [(m.x['signal_id'], f"{m.chart} {'n/a' if m.o['rose10_within60d_pct'] is None else str(m.o['rose10_within60d_pct']) + '%'} rose 10% in 60 days · n {m.n} · {'top grade' if m.top else 'not top grade'} · confirms {date_long(m.x['confirms'])}",
                     'pick top' if m.top else 'pick below') for m in M['forming']]
        fb = [b for b in form['btns'] if b['sel'] != 'example']
        e(loc, 'picker Forming: buttons', len(fb), len(exp_form))
        for b, (sid, t, cls) in zip(fb, exp_form):
            e(loc, f'picker Forming {sid}: id', b['sel'], sid); e(loc, f'picker Forming {sid}: text', b['text'], t); e(loc, f'picker Forming {sid}: class', b['cls'], cls)
            e(loc, f'picker Forming {sid}: pressed', b['pressed'], str(sid == sel_id).lower())
        if not exp_form:
            e(loc, 'picker Forming: none text', form['none'], 'Nothing forming today.')
        e(loc, 'picker example button', [b['text'] for b in form['btns'] if b['sel'] == 'example'], ['Example: ETH 2D, Sep 2024'])
        # header, banner, footer
        today = MY['today']; gen = feed['generated_at']
        e(loc, 'Market filter pill', d['filter'], 'Market filter: ' + ('on' if self.ctx['gate'](today) else 'off'))
        e(loc, 'pill styled off iff filter off', d['filterOff'], not self.ctx['gate'](today))
        e(loc, 'banner: scored date and feed time', d['review'],
          f"Review build. Real pipeline data, scored {date_long(today)} (feed {gen[11:16]} UTC). Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run. Show the example card")
        last_closed = self.ctx['day']['ETH'].date[-2]
        e(loc, 'footer: candles closed through / updated / checks', d['footer'], f"Daily candles closed through {date_long(last_closed)} · updated {gen[11:16]} UTC · checks passed")
        e(loc, 'footer: last closed daily bar is yesterday (clock)', str(last_closed), str(today - dt.timedelta(days=1)))
        e(loc, 'lead trader panel', d['lead'], "The lead trader's feed is unavailable right now. His real entries and exits appear here the moment they fill.")
        # previous signals
        op = [x for x in MY['opens'] if x['grade'] == 'A+']
        intact = [x for x in op if x['edge_status'] != 'lost']; fading = [x for x in op if x['edge_status'] == 'lost']
        if intact:
            e(loc, 'Edge intact: rows', len(d['prevIntact']), len(intact))
            for g, x in zip(d['prevIntact'], intact):
                e(loc, f"Edge intact {x['signal_id']}: name", g['name'], x['chart'])
                e(loc, f"Edge intact {x['signal_id']}: day/best/worst", g['sub'], f"Day {x['elapsed']} of 60 · best {pct(x['best'])} · worst {pct(x['worst'])}")
                e(loc, f"Edge intact {x['signal_id']}: badge", g['badge'], 'Rose 10%' if x['edge_status'] == 'rose10' else 'On track')
        else:
            e(loc, 'Edge intact: none text', [g['text'] for g in d['prevIntact']], ['No open top-grade setup with its edge intact.'])
        A = [r for r in self.ctx['L'] if r['grade'] == 'A+']
        A = sorted(A, key=lambda r: r['entry'], reverse=True)   # stable: ledger order within a date
        # stable descending sort keeps ledger order among equal dates only if done as below
        A = sorted([r for r in self.ctx['L'] if r['grade'] == 'A+'], key=lambda r: tuple(-ord(ch) for ch in r['entry']))[:5]
        exp = [('mini fading', x['chart'], f"Day {x['elapsed']} of 60 · best {pct(x['best'])} · worst {pct(x['worst'])}", 'Edge lost') for x in fading]
        for r in A:
            m = r['_s']['m']
            exp.append(('mini closed', r['chart'], f"{date_long(r['entry'])} · best {pct(rnd(m['up'], 6))} · worst {pct(rnd(m['dd'], 6))}",
                        'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed'))
        e(loc, 'Edge lost or closed: rows', len(d['prevClosed']), len(exp))
        for g, (cls, nm, sub, badge) in zip(d['prevClosed'], exp):
            e(loc, f'Edge lost or closed {nm} {sub[:11]}: class', g['cls'], cls); e(loc, f'Edge lost or closed {nm} {sub[:11]}: name', g['name'], nm)
            e(loc, f'Edge lost or closed {nm} {sub[:11]}: figures', g['sub'], sub); e(loc, f'Edge lost or closed {nm} {sub[:11]}: badge', g['badge'], badge)
        e(loc, 'How to read: bar', d['howBar'], '70% bar')

    # ------------------------------------------------------------------ record tab
    def record(self, loc, d, asset):
        e = self.eq; r_ = d['record']
        rows = [r for r in self.ctx['L'] if r['grade'] == 'A+' and (asset == 'all' or r['asset'] == asset)]
        rows = sorted(rows, key=lambda r: tuple(-ord(ch) for ch in r['entry']))
        e(loc, 'count line', r_['count'], f"{len(rows)} signals · {sum(1 for r in rows if not r['_s']['m']['r10'])} missed +10%")
        e(loc, 'table rows', len(r_['rows']), len(rows))
        e(loc, 'table head', r_['th'], ['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'])
        for got, r in zip(r_['rows'], rows):
            s = r['_s']; m = s['m']; l2 = f"{loc} row {r['chart']} {r['entry']}"
            exp = [date_long(s['d0']), s['chart'], money(rnd(s['xentry'], 2)), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
                   pct(rnd(m['up'], 6)), pct(rnd(m['dd'], 6)), pct(rnd(m['ret'], 6)), str(m['dpk'])]
            for name, g, x in zip(['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'], got, exp):
                e(l2, name, g, x)
        want = [a for a in K.ASSETS if asset in ('all', a)]
        e(loc, 'summary boxes', len(r_['sum']), len(want))
        for box, a in zip(r_['sum'], want):
            g = self.MY['grade'][(a, 'A+')]; mi = self.MY['misses'].get((a, 'A+'))
            exp = [[a, f"{g['n']} signals"], ['Rose 10% in 60 days', f"{g['reach10']}%"], ['Reached +20% in 60 days', f"{g['reach20']}%"],
                   ['Rose 10%, never fell 25.3%', f"{g['surv10']}%"], ['Median deepest dip', pct(g['medDip'])]]
            if mi: exp.append(['Misses: median best price', pct(mi['median_peak_pct'])])
            e(loc, f'summary {a}: lines', len(box['kv']), len(exp))
            for gk, xk in zip(box['kv'], exp):
                e(loc, f'summary {a}: {xk[0]}', gk, xk)

    # ------------------------------------------------------------------ chart tab
    def chart(self, loc, d, m, happened=False):
        e = self.eq; ch = d['chart']; o = m.o; x = m.x
        if m.n == 0:      # a card with an empty sample: nothing to place; only look for raw placeholders
            tx = [t['text'] for t in ch['svg'] if t['tag'] == 'text'] + [b['text'] for b in ch['side']]
            bad = [t for t in tx if 'null' in t or 'NaN' in t or 'undefined' in t or 'n/a%' in t]
            self.C.add(loc, 'chart of a card with an empty sample: no raw placeholder', '; '.join(b[:60] for b in bad[:4]), '', ok=not bad, cause='empty sample printed as null / n/a%')
            return
        forming = m.kind in ('forming', 'open'); is_open = m.kind == 'open'
        tfd = int(m.tf[:-1])
        if m.kind == 'example':
            bars = self.ex['bars']; E = self.ex['entry_index']; entry = self.ex['entry_close']; entry_day = D(2024, 9, 22)
            title = 'ETH · 2-day · example: past confirmed setup'
            sub = f"Confirmed {date_long('2024-09-22')} · entry close {money(m.entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them."
            e(loc, 'example chart file: entry close = my entry close', entry, m.entry)
        else:
            p = os.path.join(self.root, 'datasets', f'candles_{m.asset.lower()}_{m.tf.lower()}.csv')
            bars = [dict(t=int(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
            if is_open:
                entry_day = dt.date.fromisoformat(x['entry_date']); entry = x['entry']
                E = next(i for i, b in enumerate(bars) if K.bar_close_date(K.utcdate(b['t']), tfd) == entry_day)
                title = f"{m.chart.replace(' ', ' · ')} · live setup, day {x['elapsed']} of 60"
                sub = f"Confirmed {date_long(entry_day)} · entry close {money(entry)}. Zones use this setup's own card ({o['sample']})."
            else:
                entry_day = dt.date.fromisoformat(x['confirms']); entry = x['price_now']; E = len(bars) - 1
                title = f"{m.asset} · {m.tf} · " + ('setup forming' if m.top else 'forming, not top grade')
                sub = (f"Low {date_long(x['low_day'])} · confirms {date_long(x['confirms'])} · price levels drawn from today's price ({money(entry)}), "
                       "since the entry price is the confirmation close; days count from the confirmation.")
        if not happened: sub += ' The shaded zones are the next 60 days, as the odds draw them.'
        self.eqi(loc, 'chart title', ch['title'], title); e(loc, 'chart subtitle', ch['sub'], sub)
        e(loc, 'alert/happened toggle hidden for live and forming', ch['toggleHidden'], forming)
        tE = ts(entry_day)
        opens = [b['t'] for b in bars]
        if forming:
            while opens[-1] <= tE + 61 * 86400: opens.append(bar_next_open_ts(opens[-1], tfd))
        n_slots = len(opens) if forming else len(bars)
        slot = 940 / n_slots; X = lambda i: 20 + slot * i + slot / 2
        slot_of = lambda t: max(i for i in range(len(opens)) if opens[i] <= t) if opens[0] <= t else 0
        day_x = lambda k: slot_of(tE + k * 86400)
        A = day_x(0) if (forming and not is_open) else E
        lv_high, lv_10, lv_drop = px_at(entry, m.high), px_at(entry, 10), px_at(entry, m.drop)
        edge_pct = m.edge if m.edge else None
        lv_edge = px_at(entry, edge_pct) if edge_pct is not None else None
        shown = bars[:E + 1] if (not forming and not happened) else bars
        lo = min(min(b['l'] for b in shown), lv_drop, entry * 0.8) * 0.95; hi = max(max(b['h'] for b in shown), lv_high) * 1.07
        Y = lambda p: 480 - (p - lo) / (hi - lo) * 456
        svg = ch['svg']
        f = lambda v: float(v)
        lines = [s for s in svg if s['tag'] == 'line']; texts = [s for s in svg if s['tag'] == 'text']; rects = [s for s in svg if s['tag'] == 'rect']
        used = set()

        def text_at(label, content, xx=None, yy=None, tol=0.02):
            c = [t for t in texts if t['text'] == content and id(t) not in used]
            if xx is not None: c = [t for t in c if abs(f(t['x']) - xx) <= tol]
            if yy is not None: c = [t for t in c if abs(f(t['y']) - yy) <= tol]
            if c: used.add(id(c[0]))
            near_ = [t['text'] for t in texts if t['text'][:8] == content[:8]]
            self.C.add(loc, label, content if c else (near_[0] if near_ else 'missing'), content, ok=bool(c), cause='chart label text or position')
            return c[0] if c else None

        def vline(label, xx, col=None):
            c = [l for l in lines if l['x1'] == l['x2'] and f(l['y1']) == 24 and f(l['y2']) == 480 and abs(f(l['x1']) - xx) < 0.02]
            self.C.add(loc, label, 'drawn' if c else 'not at this bar', 'drawn', ok=bool(c), cause='vertical line not on the expected bar')

        def hline(label, p, x1, x2):
            c = [l for l in lines if l['y1'] == l['y2'] and abs(f(l['y1']) - Y(p)) < 0.02 and abs(f(l['x1']) - x1) < 0.02 and abs(f(l['x2']) - x2) < 0.02 and l.get('stroke-width') in ('2', '2.5')]
            self.C.add(loc, label, 'drawn' if c else 'not at this price / span', 'drawn', ok=bool(c), cause='level line not at the expected price')

        xT, xE = X(E), X(A); x60 = X(min(n_slots - 1, day_x(60))); x10 = X(day_x(10)); hd = o['typical_day_of_60d_high']; xH = X(day_x(hd))
        # the entry / confirmation bar is the bar that closes on the entry date
        cb = K.bar_close_date(K.utcdate(opens[A]), tfd)
        e(loc, 'entry bar closes on the entry / confirmation date', str(cb), str(entry_day))
        d60 = entry_day + dt.timedelta(days=60); b60 = K.utcdate(opens[min(n_slots - 1, day_x(60))])
        e(loc, 'Day 60 line is on the bar holding calendar day 60', 'yes' if b60 <= d60 <= K.bar_close_date(b60, tfd) else 'no', 'yes')
        vline('Entry / Today line on its bar', xT); text_at('Entry / Today label', 'Today' if (forming and not is_open) else 'Entry', xT + 6, 36)
        vline('Day 60 line', x60); text_at('Day 60 label', 'Day 60', x60 + 6, 54)
        vline('High-day line on the bar holding that day', xH); text_at('High-day label', f'High usually ~day {hd}', xH + 6, 36)
        if forming and not is_open and A > E:
            vline('Confirms line on the confirmation bar', X(A)); text_at('Confirms label', f"Confirms {date_long(x['confirms'])} · entry, day 0", X(A) + 6, 72)
        hline('Typical high line at entry x (1 + typical high)', lv_high, xE, x60)
        hline('+10% line at entry x 1.10', lv_10, xE, x60)
        hline('Entry line at the entry price', entry, xE, x60)
        hline('Typical drop line', lv_drop, xE, x60)
        text_at('Typical high label', f'Typical high {pct(m.high)}')
        text_at('+10% label', f"+10% · {o['rose10_within60d_pct']}% of past signals got here")
        text_at('Typical drop label', f'Typical drop {pct(m.drop)}')
        # price tags
        for nm, p in (('Typical high', lv_high), ('+10%', lv_10), ('entry', entry), ('Typical drop', lv_drop)):
            text_at(f'price tag {nm}', money(p), 1018)
        if lv_edge is not None:
            hline('Edge line at entry x (1 + edge level)', lv_edge, xE, x60)
            text_at('Edge label', f"Edge gone below {money(lv_edge)} ({pct(edge_pct, 0)}, before +10%)")
        else:
            self.C.add(loc, 'no edge line when the edge is at entry or nowhere', len([t for t in texts if t['text'].startswith('Edge gone')]), 0)
        # ladder bands: from entry, then falls 5 / 10 / 15
        steps = [(0, -5, m.lad[0])] + [(-m.lad[k][0], -(m.lad[k + 1][0] if k + 1 < len(m.lad) else m.lad[k][0] + 5), m.lad[k]) for k in (1, 2, 3)]
        xL = X(E + 6 / tfd) if X(E + 6 / tfd) > xE + 88 else xE + 88
        for a1, b1, (th, hit, okp, lq, ex6, exf) in steps:
            y1 = Y(entry * (1 + a1 / 100)); y2 = min(480, Y(entry * (1 + b1 / 100)))
            col = 'var(--closed)' if okp is None else 'var(--high)' if exf >= 70 else 'var(--drop)'
            c = [r for r in rects if abs(f(r['x']) - xE) < 0.02 and abs(f(r['y']) - y1) < 0.02 and abs(f(r['width']) - (xL - xE)) < 0.02 and abs(f(r['height']) - (y2 - y1)) < 0.02]
            nm = 'from entry' if th is None else f'falls {th}%'
            self.C.add(loc, f'ladder band {nm}: position', 'drawn' if c else 'missing', 'drawn', ok=bool(c), cause='ladder band misplaced')
            if c:
                e(loc, f'ladder band {nm}: colour on the exact share', 'fill: ' + col + ';' in c[0].get('style', '') or c[0].get('fill') == col, True)
            text_at(f'ladder band {nm}: share and n', 'n/a' if okp is None else f'{okp}% · n {hit}', (xE + xL) / 2, (y1 + y2) / 2 + 5)
        # zones
        for nm, y1, hgt in (('upside zone', Y(lv_high), Y(entry) - Y(lv_high)), ('downside zone', Y(entry), Y(lv_drop) - Y(entry))):
            c = [r for r in rects if abs(f(r['x']) - xE) < 0.02 and abs(f(r['y']) - y1) < 0.02 and abs(f(r['width']) - (x60 - xE)) < 0.02 and abs(f(r['height']) - hgt) < 0.02]
            self.C.add(loc, f'{nm}: entry to day 60, entry to level', 'drawn' if c else 'missing', 'drawn', ok=bool(c), cause='zone misplaced')
        # candles drawn
        upto = len(bars) if forming or happened else E + 1
        wicks = [l for l in lines if l['x1'] == l['x2'] and not (f(l['y1']) == 24 and f(l['y2']) == 480)]
        e(loc, 'candles drawn (none after the alert in "At the alert")', len(wicks), upto)
        okw = sum(1 for i in range(upto) if any(abs(f(w['x1']) - X(i)) < 0.02 and abs(f(w['y1']) - Y(bars[i]['h'])) < 0.02 and abs(f(w['y2']) - Y(bars[i]['l'])) < 0.02 for w in wicks))
        e(loc, 'every candle wick at its bar and its high/low (axis scale)', okw, upto)
        # the low marker (forming only)
        if m.kind == 'forming':
            li = next((i for i, b in enumerate(bars) if str(K.utcdate(b['t'])) == x['low_date']), None)
            if li is not None:
                text_at('Low marker', f"Low {date_long(x['low_day'])} · {money(bars[li]['l'])}", X(li) - 12, Y(bars[li]['l']) + 5)
                dd = self.ctx['day'][m.asset]
                e(loc, 'Low marker price = the daily low on the low day', bars[li]['l'], dd.l[dd.pos[dt.date.fromisoformat(x['low_day'])]])
        if happened:
            dd = self.ctx['day']['ETH']; s = self.ctx['bykey'][('ETH 2D', '2024-09-22')]; mm = s['m']
            win = [(i, b) for i, b in enumerate(bars) if i > E and b['t'] < tE + 61 * 86400]
            hi_i, hi_b = max(win, key=lambda t: (t[1]['h'], -t[0])); lo_i, lo_b = min(win, key=lambda t: (t[1]['l'], t[0]))
            for nm, (i, b), p, day_ in (('high', (hi_i, hi_b), hi_b['h'], mm['dpk']), ('low', (lo_i, lo_b), lo_b['l'], mm['ddday'])):
                d0 = round((b['t'] - tE) / 86400); nxt = bars[i + 1]['t'] if i + 1 < len(bars) else bar_next_open_ts(b['t'], tfd)
                d1 = min(60, round((nxt - tE) / 86400) - 1)
                my_p = float(max(dd.xh[k] for k in mm['ks'])) if nm == 'high' else float(min(dd.xl[k] for k in mm['ks']))
                my_pct = rnd(mm['up'], 6) if nm == 'high' else rnd(mm['dd'], 6)
                rng = f'days {d0}–{d1}' if d1 > d0 else f'day {d0}'
                text_at(f'This one ({nm}): price, percent, days', f"This one: {money(my_p)} · {pct(my_pct)} · {rng}")
                e(loc, f'This one ({nm}): my day of the {nm} ({day_}) lies in the days shown', 'yes' if d0 <= day_ <= d1 else 'no', 'yes')
        # axis date labels
        every = max(1, math.floor(n_slots / 8 + 0.5))
        for i in range(0, n_slots, every):
            dte = K.utcdate(opens[min(i, len(opens) - 1)])
            text_at(f'date axis slot {i}', f'{dte.day:02d} {MON[dte.month - 1]}', X(i), 502)
        # every remaining text is a price gridline label; check each sits at its price
        left = [t for t in texts if id(t) not in used]
        badg = 0
        for t in left:
            if not t['text'].startswith('$'): badg += 1; continue
            p = float(t['text'][1:].replace(',', ''))
            if abs((f(t['y']) - 5) - Y(p)) > 0.6 * 456 / (hi - lo) + 0.02: badg += 1
        e(loc, f'price axis labels ({len(left)}) each at its price; no other text on the chart', badg, 0)
        # cloud
        key = 'example' if m.kind == 'example' else m.asset
        pp = self.MY['paths'].get(key)
        if pp and pp['days']:
            e(loc, 'cloud heading', ch['cloudSub'], f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {pp['signals']}" if m.kind == 'example' else f"Every past {m.asset} top-grade signal, n {pp['signals']}")
            last = pp['days'][60]
            note = f"━ median path █ middle half of outcomes{' ━ this signal' if happened else ''}. Day 60: median {pct(last[1])}, middle half {pct(last[0])} to {pct(last[2])}. Daily closes."
            if m.kind != 'example' and not m.top: note += " Top-grade signals only; the selected setup isn't top grade."
            e(loc, 'cloud note (day-60 median and middle half)', ch['cloudNote'], note)
            Xc = lambda dd_: 20 + 940 * dd_ / 60; Yc = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
            pl = [s for s in ch['cloud'] if s['tag'] == 'polyline']; pg = [s for s in ch['cloud'] if s['tag'] == 'polygon']
            def pts(s): return [tuple(float(z) for z in p.split(',')) for p in s['points'].split(' ')]
            med = pts(pl[0]) if pl else []
            bad = sum(1 for k in range(61) if k >= len(med) or abs(med[k][0] - Xc(k)) > 1e-6 or abs(med[k][1] - Yc(pp['days'][k][1])) > 1e-6)
            e(loc, 'cloud median path: 61 points at my medians', bad, 0)
            band = pts(pg[0]) if pg else []
            bad = sum(1 for k in range(61) if len(band) != 122 or abs(band[k][1] - Yc(pp['days'][k][2])) > 1e-6 or abs(band[121 - k][1] - Yc(pp['days'][k][0])) > 1e-6)
            e(loc, 'cloud middle half: 122 points at my quartiles', bad, 0)
            if happened:
                # this signal's own path, drawn from the 2D closes: each point must be the daily close on that day
                dd = self.ctx['day']['ETH']; s = self.ctx['bykey'][('ETH 2D', '2024-09-22')]
                own = pts(pl[1]) if len(pl) > 1 else []
                bad = 0
                for k in range(1, 31):
                    j = dd.pos[s['d0'] + dt.timedelta(days=2 * k)]
                    v = float((dd.xc[j] / s['xentry'] - 1) * 100)
                    if k >= len(own) or abs(own[k][0] - Xc(2 * k)) > 1e-6 or abs(own[k][1] - Yc(v)) > 1e-6: bad += 1
                e(loc, "cloud: this signal's path = daily closes on days 2, 4 .. 60", bad, 0)
            else:
                e(loc, 'cloud: no outcome path at the alert', len(pl), 1)
        # side box
        side = ch['side']; s0 = side[0] if side else dict(kv=[], small=[], fine=[], big=None)
        e(loc, 'side: chart and sample', s0['small'][0] if s0['small'] else None,
          f"{m.chart}{' · example' if m.kind == 'example' else ''} · from {o['sample']}{' · odds as of the entry close, not from today' if is_open else ''}")
        e(loc, 'side: big number', s0['big'], f"{o['rose10_within60d_pct']}%")
        e(loc, 'side: n and surv10', s0['small'][1] if len(s0['small']) > 1 else None,
          f"rose 10% within 60 days, from {m.n} past signals; {o['rose10_never_fell25_within60d_pct']}% without ever falling 25.3%")
        kv = {k[0]: k[1] for k in s0['kv']}
        e(loc, 'side: Typical high pct and price', kv.get('Typical high'), f"{pct(m.high)} · {money(lv_high)}")
        e(loc, 'side: +10% level', kv.get('+10% level'), money(lv_10))
        e(loc, 'side: Reached +20%', kv.get('Reached +20% within 60 days'), f"{o['rose20_within60d_pct']}%")
        e(loc, 'side: Typical drop pct and price', kv.get('Typical drop'), f"{pct(m.drop)} · {money(lv_drop)}")
        e(loc, 'side: Edge gone below', kv.get('Edge gone below'), 'below the bar already' if m.edge == 0 else 'holds at every level' if m.edge is None else f"{money(px_at(entry, m.edge))} ({pct(m.edge, 0)})")
        s1 = side[1] if len(side) > 1 else dict(kv=[], text='', title=None)
        if is_open:
            self.eqi(loc, 'side: live day', s1['title'], f"Live: day {x['elapsed']} of 60")
            kv1 = {k[0]: k[1] for k in s1['kv']}
            e(loc, 'side: Best so far', kv1.get('Best so far'), pct(x['best'])); e(loc, 'side: Worst so far', kv1.get('Worst so far'), pct(x['worst']))
            e(loc, 'side: Day 10', kv1.get('Day 10'), 'not yet' if x['d10'] is None else pct(x['d10']))
        elif m.kind == 'forming':
            e(loc, 'side: still forming text', s1['text'], f"Still forming. It confirms only if it holds through {date_long(x['confirms'])}, and it can vanish before then." + ("" if m.top else " It isn't top grade, so no alert goes out for it."))
        elif happened:
            dd = self.ctx['day']['ETH']; s = self.ctx['bykey'][('ETH 2D', '2024-09-22')]; mm = s['m']
            kv1 = {k[0]: k[1] for k in s1['kv']}
            e(loc, 'side: Reached +10% / +20%', kv1.get('Reached +10% / +20%'), f"{'Yes' if mm['r10'] else 'No'} / {'Yes' if mm['r20'] else 'No'}")
            def rng(day_):   # the 2-day bar holding that day
                a = day_ if day_ % 2 else day_ - 1
                return f'days {a}–{a + 1}'
            e(loc, 'side: Best price', kv1.get('Best price'), f"{pct(rnd(mm['up'], 6))}, {rng(mm['dpk'])}")
            e(loc, 'side: Deepest drop', kv1.get('Deepest drop'), f"{pct(rnd(mm['dd'], 6))}, {rng(mm['ddday'])}")
            c10 = dd.xc[dd.pos[s['d0'] + dt.timedelta(days=10)]]; p10 = (c10 / s['xentry'] - 1) * 100
            e(loc, 'side: Day 10 check', kv1.get('Day 10 check'), f"{'Red' if c10 < s['xentry'] else 'Green'}, {pct(rnd(p10, 6))}")
            e(loc, 'side: Price on day 60', kv1.get('Price on day 60'), pct(rnd(mm['ret'], 6)))
        else:
            e(loc, 'side: at the alert text (no outcome)', s1['text'], "This is all a member had at the alert: the zones, the +10% level and the timing. Press What happened to see the real path.")
        e(loc, 'side: lead trader note', side[2]['text'] if len(side) > 2 else None, "The lead trader's feed is unavailable right now, so his entries and exits can't be shown.")
