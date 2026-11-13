"""Compare what the member page shows (page.py dump) with the auditor's own values.
Entry quality only: computed signals, not fills; no exit in the data."""
import os, csv, json, re, datetime as dt
from mine import rnd, px_at, floor_cent, next_cal_open, udate, read_csv, TFS, GRADED, EX_D0
MIN = '−'
MON = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']


def f1(v, d=1):
    if v is None:
        return 'n/a'
    r = rnd(v, d)
    if r == 0:
        return f'{0:.{d}f}'
    return f'{r:.{d}f}'.replace('-', MIN)


def pct(v, d=1):
    if v is None:
        return 'n/a'
    return ('+' if rnd(v, d) > 0 else '') + f1(v, d) + '%'


def pc(v):
    return 'n/a' if v is None else f'{v}%'


def money(v):
    return 'n/a' if v is None else '$' + f'{rnd(v, 2):,.2f}'


def dl(d):
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    return f'{d.day} {MON[d.month]} {d.year}'


def d2(d):
    return f'{d.day:02d} {MON[d.month]}'


def ts(d):
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())


def edge_text(edge):
    return 'Below the 70% bar from entry' if edge == 0 else 'Holds at every level' if edge is None else f'{pct(edge, 0)} before it rises 10%'


def run(ck, sdir, dump, S, X, feed):
    today = S.today
    fr = dump['frame']
    gen = feed['generated_at']; hhmm = gen[11:16]
    on = bool(S.gate(today))
    ck.cmp('page header', 'market filter', fr['filter'], f"Market filter: {'on' if on else 'off'}")
    ck.cmp('page banner', 'scored', fr['rvAsof'], f'{dl(today)} (feed {hhmm} UTC)')
    ck.cmp('page footer', 'feed state', fr['feedState'], f'Daily candles closed through {dl(today - dt.timedelta(days=1))} · updated {hhmm} UTC · checks passed')
    ck.cmp('page', 'script errors', len(dump['errors']), 0)
    ck.cmp('page How to read', 'posting bar', fr['howBar'], '70% bar')
    ck.cmp('page lead trader', 'panel', fr['lead'], "The lead trader's feed is unavailable right now. His real entries and exits appear here the moment they fill.")
    # ---------------- picker
    A_open = [o for o in feed['open_signals'] if o['grade'] == 'A+']
    rows = {r['label']: r for r in fr['picker']}
    live = rows.get('LIVE', {}).get('buttons', [])
    ck.cmp('page picker Live', 'buttons', [b['sel'] for b in live], [o['signal_id'] for o in A_open])
    for b in live:
        it = X.items.get(b['sel'])
        if not it:
            continue
        exp = f"{it['extra']['chart']}\nDay {it['days']}\nbest {pct(it['best'])} · worst {pct(it['worst'])}"
        ck.cmp(f"page picker {b['sel']}", 'button', b['text'], exp, 'figure')
    form = [b for b in rows.get('FORMING', {}).get('buttons', []) if b['sel'] != 'example']
    cards = feed['cards']
    top = [c for c in cards if c['grade'] == 'A+']
    order = top + sorted([c for c in cards if c not in top], key=lambda c: -(c['rose10_within60d_pct'] if c['rose10_within60d_pct'] is not None else -1))
    ck.cmp('page picker Forming', 'buttons', [b['sel'] for b in form], [c['signal_id'] for c in order])
    for b in form:
        it = X.items.get(b['sel'])
        if not it:
            continue
        f = it['fig']
        exp = f"{it['extra']['chart'] if 'chart' in it['extra'] else it['asset'] + ' ' + it['tf']}\n{pc(f['rose10_within60d_pct'])}\nrose 10% in 60 days · n {f['past_trades']} · {'top grade' if it['grade'] == 'A+' else 'not top grade'} · confirms {dl(it['extra']['confirms_on'])}"
        ck.cmp(f"page picker {b['sel']}", 'button', b['text'], exp, 'figure')
    if not live:
        ck.cmp('page picker Live', 'empty text', rows.get('LIVE', {}).get('none'), 'No live top-grade setups right now.')
    if not form:
        ck.cmp('page picker Forming', 'empty text', rows.get('FORMING', {}).get('none'), 'Nothing forming today.')
    # ---------------- previous signals
    led = [r for r in read_csv(os.path.join(sdir, 'datasets', 'ledger.csv')) if r['grade'] == 'A+']
    mine_led = {(f"{s['a']} {s['tf']}", str(s['d0'])): s for s in X.rows}
    intact = [o for o in A_open if X.items.get(o['signal_id'], {}).get('status') in ('intact', 'rose10')]
    lost = [o for o in A_open if X.items.get(o['signal_id'], {}).get('status') == 'lost']
    pi = [x for x in fr['prevIntact'] if 'mini' in x['cls']]
    ck.cmp('page Previous signals', 'on-track group', [x['name'] for x in pi], [o['chart'] for o in intact])
    for x, o in zip(pi, intact):
        it = X.items[o['signal_id']]
        ck.cmp(f"page Previous {o['signal_id']}", 'line', x['sub'], f"Day {it['days']} of 60 · best {pct(it['best'])} · worst {pct(it['worst'])}", 'figure')
        ck.cmp(f"page Previous {o['signal_id']}", 'badge', x['badge'], 'Rose 10%' if it['status'] == 'rose10' else 'On track', 'wording')
    if not intact:
        ck.cmp('page Previous signals', 'on-track empty text', fr['prevIntact'][0]['text'] if fr['prevIntact'] else None, 'No open top-grade setup on track or up 10%.')
    pcl = fr['prevClosed']
    fad = [x for x in pcl if 'fading' in x['cls']]
    ck.cmp('page Previous signals', 'edge-lost group', [x['name'] for x in fad], [o['chart'] for o in lost])
    for x, o in zip(fad, lost):
        it = X.items[o['signal_id']]
        ck.cmp(f"page Previous {o['signal_id']}", 'line', x['sub'], f"Day {it['days']} of 60 · best {pct(it['best'])} · worst {pct(it['worst'])}", 'figure')
        ck.cmp(f"page Previous {o['signal_id']}", 'badge', x['badge'], 'Edge lost', 'wording')
    closed = [x for x in pcl if 'closed' in x['cls']]
    recent = sorted(led, key=lambda r: r['entry'], reverse=True)[:5]
    ck.cmp('page Previous signals', 'closed group count', len(closed), len(recent))
    for x, r in zip(closed, recent):
        s = mine_led.get((r['chart'], r['entry']))
        if s is None:
            continue
        m = s['m']
        ck.cmp(f"page Previous {r['chart']} {r['entry']}", 'chart', x['name'], r['chart'])
        ck.cmp(f"page Previous {r['chart']} {r['entry']}", 'line', x['sub'], f"{dl(s['d0'])} · best {pct(rnd(m['up'], 6))} · worst {pct(rnd(m['dd'], 6))}", 'figure')
        ck.cmp(f"page Previous {r['chart']} {r['entry']}", 'badge', x['badge'], 'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed', 'wording')
    # ---------------- each selectable item: card and chart
    for item in dump['items']:
        sel = item['sel']
        it = X.items.get(sel)
        if it is None and sel == 'example' and today < dt.date(2024, 11, 22):
            ck.cmp('page card example', 'state before 22 Nov 2024', item['card']['state'], 'Example unavailable')
            ck.cmp('page chart example', 'blank before 22 Nov 2024', any(e.get('text') == 'Chart data unavailable' for e in item['chart_alert']['svg']), True)
            continue
        if it is None:
            ck.note(f'page card {sel}', 'auditor has this item', 'shown', 'no expectation', False, 'unexpected item'); continue
        card_page(ck, sel, item['card'], it, X, feed, order)
        chart_page(ck, sel, item['chart_alert'], it, X, S, feed, sdir, happened=False)
        if 'chart_happened' in item:
            chart_page(ck, sel, item['chart_happened'], it, X, S, feed, sdir, happened=True)
    # ---------------- record tab
    rec = dump['record']
    ck.cmp('page Past signals', 'heading', rec['all']['head'], 'Every top-grade signal whose 60 days have closed · computed, never traded'.upper() if rec['all']['head'] and rec['all']['head'].isupper() else 'Every top-grade signal whose 60 days have closed · computed, never traded')
    for a in ('all', 'ETH', 'BTC'):
        R = rec[a]
        mine_rows = [s for s in X.rows if s['grade'] == 'A+' and (a == 'all' or s['a'] == a)]
        ck.cmp(f'page Past signals {a}', 'count line', R['count'], f"{len(mine_rows)} signals · {sum(1 for s in mine_rows if not s['m']['r10'])} missed +10%", 'figure')
        ck.cmp(f'page Past signals {a}', 'rows', len(R['rows']), len(mine_rows))
        for cells in R['rows']:
            key = None
            for s in mine_rows:
                if dl(s['d0']) == cells[0] and f"{s['a']} {s['tf']}" == cells[1]:
                    key = s; break
            if key is None:
                ck.note(f'page Past signals {a}', f'row {cells[0]} {cells[1]}', 'shown', 'not a top-grade signal of mine', False, 'extra row'); continue
            m = key['m']
            exp = [dl(key['d0']), f"{key['a']} {key['tf']}", money(rnd(key['c0'], 2)), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
                   pct(rnd(m['up'], 6)), pct(rnd(m['dd'], 6)), pct(rnd(m['ret'], 6)), str(m['dpk'])]
            names = ['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day']
            for nm, sh, ex in zip(names, cells, exp):
                ck.cmp(f"page Past signals {a} {key['a']} {key['tf']} {key['d0']}", nm, sh, ex, 'figure')
        for b in R['sum']:
            asset = b['head'].split('\n')[0].split()[0]
            g = X.grade_record(asset, 'A+')
            mi = X.misses([s for s in X.rows if s['a'] == asset and s['grade'] == 'A+'])
            ck.cmp(f'page Past signals {a} summary {asset}', 'head', re.sub(r'\s+', ' ', b['head']), f"{asset} {g['n']} signals")
            want = [['Rose 10% in 60 days', pc(g['reach10'])], ['Reached +20% in 60 days', pc(g['reach20'])],
                    ['Rose 10%, never fell 25.3%', pc(g['surv10'])], ['Median deepest dip', pct(g['medDip'])], ['Misses: median best price', pct(mi['median_peak_pct'])]]
            ck.cmp(f'page Past signals {a} summary {asset}', 'tiles', b['kv'], want, 'figure')
    # ---------------- quiet card
    if 'quiet_card' in dump:
        q = dump['quiet_card']
        ck.cmp('page quiet card', 'state', q['state'], 'No setup right now')
        y1 = int(feed['generated_at'][:4]) - 1
        n = sum(1 for s in X.rows if s['grade'] == 'A+' and 2020 <= s['d0'].year <= y1)
        per = rnd(n / (y1 - 2020 + 1))
        if on:
            exp = f'The market filter is on. Nothing at the top grade is forming or confirmed today. Top-grade setups come about {per} times a year (2020 to {y1} average; bear years, when the market filter is off, are included).'
        else:
            exp = 'The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.'
        ck.cmp('page quiet card', 'text', exp in (q['empty'] or ''), True, 'figure')
        if not (exp in (q['empty'] or '')):
            ck.rows[-1]['shown'] = q['empty']; ck.rows[-1]['yours'] = exp


def card_page(ck, sel, c, it, X, feed, order):
    f = it['fig']; kind = it['kind']; ex = it['extra']; a = it['asset']; grade = it['grade']
    loc = f'page card {sel}'
    tfx = it['tf']
    ck.cmp(loc, 'where', (c['where'] or '').upper(), (f'{a} · {tfx} chart' + (' · example' if kind == 'example' else '')).upper())
    ck.cmp(loc, 'state', c['state'], {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind])
    sm = c['smalls']
    if kind == 'forming':
        line = f"Low {dl(ex['low_day'])} · confirms {dl(ex['confirms_on'])}" + (f" if it closes above {money(ex['must_close_above'])}" if ex['must_close_above'] else '')
        ck.cmp(loc, 'line', sm[0] if sm else None, line, 'figure')
        if grade != 'A+':
            best = order[0]['signal_id'] == sel if order else False
            exp2 = ('Best setup forming today.' if best else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms."
        else:
            exp2 = 'Not confirmed yet. It can still vanish before it confirms.'
        ck.cmp(loc, 'status line', sm[1] if len(sm) > 1 else None, exp2, 'wording')
    elif kind == 'open':
        line = f"Confirmed {dl(ex['confirms_on'])} · entry close {money(ex['entry_close'])} · day {it['days']} of 60 · best so far {pct(it['best'])} · worst {pct(it['worst'])}"
        ck.cmp(loc, 'line', sm[0] if sm else None, line, 'figure')
        st_, e = it['status'], it['edge']
        if st_ == 'lost':
            t = 'Edge lost. ' + ('Its odds were below the bar from the entry.' if e == 0 else f'It fell to its edge level ({pct(e, 0)}) before rising 10%.')
        elif st_ == 'rose10':
            t = 'Rose 10%. ' + ('It has risen 10% from the entry close.' if e is None else f'It rose 10% before falling to its edge level ({pct(e, 0)}).')
        else:
            t = 'On track. ' + ('It has neither risen 10% nor lost its edge; its odds hold at every fall measured.' if e is None else f'It has not fallen to its edge level ({pct(e, 0)}) or risen 10% yet.')
        t += ' The odds below are as of the entry close, not from today.'
        ck.cmp(loc, 'status line', sm[1] if len(sm) > 1 else None, t, 'wording')
        ck.cmp(loc, 'big number dimmed when edge lost', (c['bigStyle'] or '').find('0.5') >= 0, st_ == 'lost')
        ck.cmp(loc, 'frame colour', c['frame'], 'var(--fade)' if st_ == 'lost' else 'var(--live)')
    else:
        ck.cmp(loc, 'line', sm[0] if sm else None, f"Example: confirmed {dl(EX_D0)} · entry close {money(ex['entry_close'])}", 'figure')
    if kind == 'forming':
        ck.cmp(loc, 'frame colour', c['frame'], 'var(--live)' if grade == 'A+' else 'var(--fade)')
    o = c['odds']
    ck.cmp(loc, 'big number (rose 10%)', c['big'], pc(f['rose10_within60d_pct']), 'figure')
    ck.cmp(loc, 'big number label', o[1] if len(o) > 1 else None, 'rose 10% within 60 days' + (' · at the entry close, not from today' if kind == 'open' else ''), 'wording')
    ck.cmp(loc, 'surv10 line', o[2] if len(o) > 2 else None, f"{pc(f['rose10_never_fell25_within60d_pct'])} did it without ever falling 25.3%", 'figure')
    ck.cmp(loc, 'sample line', o[3] if len(o) > 3 else None, f"from {ex['sample']} · every figure covers the 60 days after entry", 'figure')
    if kind == 'example':
        mi = X.misses(it['known_ap']) if 'known_ap' in it else None
    known = [s for s in X.rows if s['a'] == a and s['grade'] == grade] if kind != 'example' else \
        [s for s in X.rows if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= EX_D0]
    mi = X.misses(known)
    misstxt = 'none missed' if not mi['misses'] else f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}"
    gw = 'top-grade' if grade == 'A+' else 'same-grade'
    stats = dict(c['stats'])
    ck.cmp(loc, 'Typical high', stats.get('Typical high'), pct(f['typical_biggest_rise_shown']), 'figure')
    ck.cmp(loc, 'Typical drop from entry', stats.get('Typical drop from entry'), pct(f['typical_deepest_dip_shown']), 'figure')
    ck.cmp(loc, 'Edge gone below', stats.get('Edge gone below'), edge_text(f['_edge']), 'figure')
    ck.cmp(loc, 'If it misses: went above entry', stats.get('If it misses: went above entry'), misstxt, 'figure')
    ck.cmp(loc, 'misses pool', c['pool'], (f"of the {mi['signals']} {a} {gw} signals known by then" if kind == 'example' else f"of all {mi['signals']} {a} {gw} signals"), 'figure')
    ck.cmp(loc, 'lead trader', c['marker'], 'Lead trader: unavailable')
    mt = f"{mi['misses']} misses of {'the' if kind == 'example' else 'all'} {mi['signals']} {a} {gw} signals" + (' known by then' if kind == 'example' else '')
    want_tiles = [['Dip before the high, from entry', pct(f['typical_dip_before_rise_shown'])],
                  ['High lands around', f"Day {f['typical_day_of_60d_high']}"],
                  [f"Reached +20% within 60 days · n {f['past_trades']}", pc(f['rose20_within60d_pct'])],
                  [f"Touched {MIN}30% within 60 days · n {f['past_trades']}", pc(f['fell30_within60d_pct'])],
                  ['Typical high', pct(f['typical_biggest_rise_shown'])],
                  ['Deepest dip lands around', f"Day {f['typical_day_of_deepest_dip']}"],
                  [f'Typical worst drop, misses · {mt}', pct(mi['median_worst_drop_pct'])],
                  [f'Typical change by day 60, misses · {mt}', pct(mi['median_day60_pct'])]]
    for i, (w, sh) in enumerate(zip(want_tiles, c['tiles'])):
        ck.cmp(loc, f'tile {i + 1} label', sh[0], w[0], 'wording' if i in (0, 1, 4, 5) else 'figure')
        ck.cmp(loc, f'tile {i + 1} ({w[0][:30]})', sh[1], w[1], 'figure')
    ck.cmp(loc, 'tiles count', len(c['tiles']), 8)
    lad = c['ladder']
    want = [(f"From entry n {f['past_trades']}", pc(f['from_entry']['still_rose10_pct']), f['from_entry']['still_rose10_exact_pct'] < 70)]
    for r in f['if_it_falls_first']:
        want.append((f"Falls {r['fell_pct']}% first n {r['past_trades']}", pc(r['still_rose10_pct']), r['still_rose10_exact_pct'] is not None and r['still_rose10_exact_pct'] < 70))
    ck.cmp(loc, 'ladder rows', len(lad), len(want))
    for sh, (lab, v, gone) in zip(lad, want):
        ck.cmp(loc, f'ladder {lab} label', sh['label'], lab, 'figure')
        ck.cmp(loc, f'ladder {lab} share', sh['val'], v, 'figure')
        ck.cmp(loc, f'ladder {lab} below the bar (exact share)', sh['gone'], gone, 'figure')
    ck.cmp(loc, 'ladder title', (c['ladderTitle'] or '').upper(), 'WHERE THE ODDS FADE · THIS SETUP')
    eras = c['eras']
    we = [(f"Before 2022 n {f['before_2022']['past_trades']}", pc(f['before_2022']['rose10_never_fell25_within60d_pct'])),
          (f"Since 2022 n {f['since_2022']['past_trades']}", pc(f['since_2022']['rose10_never_fell25_within60d_pct']))]
    for sh, (lab, v) in zip(eras, we):
        ck.cmp(loc, f'era {lab[:11]} label', sh['label'], lab, 'figure')
        ck.cmp(loc, f'era {lab[:11]} share', sh['val'], v, 'figure')
    ck.cmp(loc, 'eras note', c['erasNote'], 'Share that rose 10% and never fell 25.3%.')
    ck.cmp(loc, 'card foot says entry quality only', 'Entry quality only: no exit, not a trade or a track record.' in (c['foot'] or ''), True, 'wording')


def chart_page(ck, sel, ch, it, X, S, feed, sdir, happened):
    kind = it['kind']; f = it['fig']; ex = it['extra']; a = it['asset']; tf = it['tf']; tfd = int(tf[:-1])
    loc = f"page chart {sel}{' what happened' if happened else ' at the alert'}"
    forming = kind != 'example'
    if kind == 'example':
        exj = json.load(open(os.path.join(sdir, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')))
        bars = exj['bars']; E = exj['entry_index']; entry = exj['entry_close']
        # the example file against the auditor's own ETH 2D bars
        mb = {b['open']: b for b in S.bars[('ETH', '2D')]}
        bad = 0
        for b in bars:
            m = mb.get(udate(b['t']))
            if m is None or (b['o'], b['h'], b['l'], b['c']) != (m['o'], m['rawh'], m['rawl'], m['c']):
                bad += 1
        ck.cmp(loc, 'example chart file bars equal the 2D candles', bad, 0, 'figure')
        ck.cmp(loc, 'example entry bar closes on 2024-09-22', str(next_cal_open(udate(bars[E]['t']), 2) - dt.timedelta(days=1)), '2024-09-22')
        ck.cmp(loc, 'example entry close', entry, ex['entry_close'])
        last_close = next_cal_open(udate(bars[-1]['t']), 2) - dt.timedelta(days=1)
        ck.cmp(loc, 'example file ends with the bar holding day 60', udate(bars[-1]['t']) <= EX_D0 + dt.timedelta(days=60) <= last_close, True)
    else:
        p = os.path.join(sdir, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        bars = [dict(t=int(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
        mb = {b['open']: b for b in S.bars[(a, tf)]}
        bad = sum(1 for b in bars if (lambda m: m is None or (b['o'], b['h'], b['l'], b['c']) != (m['o'], m['rawh'], m['rawl'], m['c']))(mb.get(udate(b['t']))))
        ck.cmp(loc, 'chart candles equal the auditor\'s bars', bad, 0, 'figure')
        ck.cmp(loc, 'chart candles end on today\'s bar', str(udate(bars[-1]['t'])), str(S.bars[(a, tf)][-1]['open']))
        if kind == 'open':
            E = next((i for i, b in enumerate(bars) if next_cal_open(udate(b['t']), tfd) - dt.timedelta(days=1) == dt.date.fromisoformat(ex['confirms_on'])), -1)
            entry = ex['entry_close']
        else:
            E = len(bars) - 1; entry = ex['price_now']
    d_entry = dt.date.fromisoformat(ex['confirms_on'])
    tEntry = ts(d_entry)
    opens = [udate(b['t']) for b in bars]
    if forming:
        while ts(opens[-1]) <= tEntry + 61 * 86400:
            opens.append(next_cal_open(opens[-1], tfd))
    def slot_of(d):
        i = 0
        while i + 1 < len(opens) and opens[i + 1] <= d:
            i += 1
        return i
    dayX = lambda k: slot_of(d_entry + dt.timedelta(days=k))
    A = dayX(0) if kind == 'forming' else E
    nS = len(opens) if forming else len(bars)
    slot = 940 / nS
    X_ = lambda i: 20 + slot * i + slot / 2
    edge = f['_edge']
    lv = dict(high=px_at(entry, f['typical_biggest_rise_exact_pct']), t20=px_at(entry, 10), drop=px_at(entry, f['typical_deepest_dip_exact_pct']),
              edge=px_at(entry, edge) if edge else None)
    shown = bars[:E + 1] if (kind == 'example' and not happened) else bars
    lo = min(min(b['l'] for b in shown), lv['drop'], entry * 0.8) * 0.95
    hi = max(max(b['h'] for b in shown), lv['high']) * 1.07
    Y = lambda p_: 480 - (p_ - lo) / (hi - lo) * 456
    svg = ch['svg']
    texts = [e for e in svg if e['tag'] == 'text']
    tx = [e['text'] for e in texts]
    lines = [e for e in svg if e['tag'] == 'line']
    # titles
    if kind == 'example':
        ck.cmp(loc, 'title', (ch['title'] or '').upper(), 'ETH · 2-DAY · EXAMPLE: PAST CONFIRMED SETUP')
        sub = f"Confirmed {dl(EX_D0)} · entry close {money(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them." + ('' if happened else ' The shaded zones are the next 60 days, as the odds draw them.')
    elif kind == 'open':
        ck.cmp(loc, 'title', (ch['title'] or '').upper(), f"{a} · {tf} · live setup, day {it['days']} of 60".upper(), 'figure')
        sub = f"Confirmed {dl(d_entry)} · entry close {money(entry)}. Zones use this setup's own card ({ex['sample']}). The shaded zones are the next 60 days, as the odds draw them."
    else:
        ck.cmp(loc, 'title', (ch['title'] or '').upper(), f"{a} · {tf} · {'setup forming' if it['grade'] == 'A+' else 'forming, not top grade'}".upper())
        sub = f"Low {dl(ex['low_day'])} · confirms {dl(d_entry)} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them."
    ck.cmp(loc, 'subtitle', ch['sub'], sub, 'figure')
    ck.cmp(loc, 'view toggle hidden', ch['toggleHidden'], forming)
    # price axis: every grid label sits at its own price (scaling at the alert uses only what was known)
    ax = [t for t in texts if t.get('x') == '968' and t['text'].startswith('$')]
    badax = sum(1 for t in ax if abs(float(t['y']) - 5 - Y(float(t['text'][1:].replace(',', '')))) > 0.05)
    ck.cmp(loc, 'price axis labels at their prices', badax, 0, 'figure')
    # horizontal levels: price tags and line heights
    tags = sorted(t['text'] for t in texts if t.get('fill') == '#07060F')
    ck.cmp(loc, 'price tags', tags, sorted([money(lv['high']), money(lv['t20']), money(entry), money(lv['drop'])]), 'figure')
    hl = [e for e in lines if e.get('y1') == e.get('y2') and float(e.get('x1')) == round(float(e.get('x1')), 10) and e.get('stroke-width') in ('2', '2.5')]
    cols = {'var(--high)': 'high', 'var(--text)': 't20', 'var(--soft)': 'entry', 'var(--drop)': 'drop', 'var(--fade-2)': 'edge'}
    for e in hl:
        k = cols.get(e.get('css_stroke'))
        if k is None:
            continue
        p_ = entry if k == 'entry' else lv[k]
        ck.cmp(loc, f'{k} line height (price {p_})', round(float(e['y1']), 6), round(Y(p_), 6), 'figure')
        ck.cmp(loc, f'{k} line starts at the entry slot', round(float(e['x1']), 6), round(X_(A), 6), 'figure')
    for lab in (f"Typical high {pct(f['typical_biggest_rise_shown'])}", f"+10% · {pc(f['rose10_within60d_pct'])} of past signals got here", f"Typical drop {pct(f['typical_deepest_dip_shown'])}"):
        ck.cmp(loc, f'label "{lab[:14]}"', lab in tx, True, 'figure')
    if edge:
        lab = f"Edge gone below {money(lv['edge'])} ({pct(edge, 0)}, before +10%)"
        ck.cmp(loc, 'edge label', lab in tx, True, 'figure')
        if lab not in tx:
            ck.rows[-1]['shown'] = next((t for t in tx if t.startswith('Edge gone')), None); ck.rows[-1]['yours'] = lab
    else:
        ck.cmp(loc, 'no edge line', any(t.startswith('Edge gone') for t in tx), False, 'figure')
    # ladder bands
    want = [f"{pc(f['from_entry']['still_rose10_pct'])} · n {f['past_trades']}"] + \
           [('n/a' if r['still_rose10_pct'] is None else f"{r['still_rose10_pct']}% · n {r['past_trades']}") for r in f['if_it_falls_first'][:3]]
    got = [t for t in tx if re.match(r'^(\d+% · n \d+|n/a)$', t)]
    ck.cmp(loc, 'ladder bands', got, want, 'figure')
    # vertical lines by date
    vl = [e for e in lines if e.get('y1') == '24' and e.get('y2') == '480']
    def vat(label_start):
        t = next((t for t in texts if t['text'].startswith(label_start)), None)
        if t is None:
            return None, None
        x = float(t['x']) - 6
        return x, t['text']
    if kind == 'forming':
        x, lab = vat('Today')
        if x is None:
            x, lab = vat('Latest bar')
        ck.cmp(loc, 'Today line on today\'s bar', None if x is None else round(x, 6), round(X_(len(bars) - 1), 6), 'figure')
        ck.cmp(loc, 'Today label', lab, 'Today')
        x, lab = vat('Confirms')
        if A > E:
            ck.cmp(loc, 'Confirms line on the confirmation bar', None if x is None else round(x, 6), round(X_(A), 6), 'figure')
            ck.cmp(loc, 'Confirms label', lab, f"Confirms {dl(d_entry)} · entry, day 0", 'figure')
    else:
        x, lab = vat('Entry')
        ck.cmp(loc, 'Entry line on the bar closing on the entry date', None if x is None else round(x, 6), round(X_(E), 6), 'figure')
    x, lab = vat('Day 60')
    ck.cmp(loc, 'Day 60 line on the bar holding day 60', None if x is None else round(x, 6), round(X_(min(nS - 1, dayX(60))), 6), 'figure')
    hd = f['typical_day_of_60d_high']
    x, lab = vat('High usually')
    ck.cmp(loc, 'High line on the bar holding that day', None if x is None else round(x, 6), round(X_(dayX(hd)), 6), 'figure')
    ck.cmp(loc, 'High label', lab, f'High usually ~day {hd}', 'figure')
    # date ticks
    every = max(1, rnd(nS / 8))
    ticks = [t for t in texts if t.get('y') == '502']
    want_ticks = [(round(X_(i), 6), d2(opens[min(i, len(opens) - 1)])) for i in range(0, nS, every)]
    ck.cmp(loc, 'date ticks', [(round(float(t['x']), 6), t['text']) for t in ticks], want_ticks, 'figure')
    # candles drawn
    bodies = [e for e in svg if e['tag'] == 'rect' and e.get('css_fill') in ('var(--high)', 'var(--drop)') and 'opacity' not in e and 'rx' not in e and e.get('x') != '0']
    upto = len(bars) if (forming or happened) else E + 1
    ck.cmp(loc, 'candles drawn (none after the alert in At the alert)', len(bodies), upto)
    # the low marker
    if forming and kind == 'forming':
        tb = next((b for b in bars if str(udate(b['t'])) == ex['low_date']), None)
        if tb:
            ck.cmp(loc, 'low marker', any(t == f"Low {dl(ex['low_day'])} · {money(tb['l'])}" for t in tx), True, 'figure')
    if happened:
        win = [b for i, b in enumerate(bars) if i > E and b['t'] < tEntry + 61 * 86400]
        hiB = max(win, key=lambda b: b['h']); loB = min(win, key=lambda b: b['l'])
        for b, p_ in ((hiB, hiB['h']), (loB, loB['l'])):
            i = bars.index(b)
            d0_ = round((b['t'] - tEntry) / 86400)
            nx = bars[i + 1]['t'] if i + 1 < len(bars) else ts(next_cal_open(udate(b['t']), tfd))
            d1_ = min(60, round((nx - tEntry) / 86400) - 1)
            lab = f"This one: {money(p_)} · {pct((p_ / entry - 1) * 100)} · " + (f'days {d0_}–{d1_}' if d1_ > d0_ else f'day {d0_}')
            ck.cmp(loc, f'outcome label {lab[:24]}', lab in tx, True, 'figure')
        # against the auditor's daily data
        s = it['s']; m = s['m']
        ck.cmp(loc, 'best within 60 days = daily high', rnd((hiB['h'] / entry - 1) * 100, 1), rnd(m['up'], 1), 'figure')
        ck.cmp(loc, 'deepest within 60 days = daily low', rnd((loB['l'] / entry - 1) * 100, 1), rnd(m['dd'], 1), 'figure')
    # cloud
    pp = feed.get('example_past_paths') if kind == 'example' else next((x for x in feed.get('past_paths', []) if x['asset'] == a), None)
    mp = X.paths([s for s in X.rows if s['a'] == a and s['grade'] == 'A+' and (kind != 'example' or s['d0'] + dt.timedelta(days=60) <= EX_D0)])
    ck.cmp(loc, 'cloud n', ch['cloudSub'], (f"ETH top-grade signals whose 60 days had closed by {dl(EX_D0)}, n {mp['signals']}" if kind == 'example' else f"Every past {a} top-grade signal, n {mp['signals']}"), 'figure')
    last = mp['days'][60]
    note = f"Day 60: median {pct(last['median_pct'])}, middle half {pct(last['q25_pct'])} to {pct(last['q75_pct'])}."
    ck.cmp(loc, 'cloud day-60 note', note in (ch['cloudNote'] or ''), True, 'figure')
    if note not in (ch['cloudNote'] or ''):
        ck.rows[-1]['shown'] = ch['cloudNote']; ck.rows[-1]['yours'] = note
    if it['grade'] != 'A+' and kind != 'example':
        ck.cmp(loc, 'cloud says top-grade only', "Top-grade signals only; the selected setup isn't top grade." in (ch['cloudNote'] or ''), True, 'wording')
    poly = [e for e in ch['cloud'] if e['tag'] == 'polyline']
    if poly:
        pts = [tuple(map(float, p_.split(','))) for p_ in poly[0]['points'].split()]
        CY = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
        badp = sum(1 for (x, y), d in zip(pts, mp['days']) if abs(y - CY(d['median_pct'])) > 1e-6 or abs(x - (20 + 940 * d['day'] / 60)) > 1e-6)
        ck.cmp(loc, 'cloud median path points', badp, 0, 'figure')
        if happened and kind == 'example' and len(poly) > 1:
            d = S.daily['ETH']
            pts2 = [tuple(map(float, p_.split(','))) for p_ in poly[1]['points'].split()]
            exp2 = [(0, 0.0)] + [(2 * k, (d['c'][d['pos'][EX_D0 + dt.timedelta(days=2 * k)]] / entry - 1) * 100) for k in range(1, 31)]
            bad2 = sum(1 for (x, y), (dd, v) in zip(pts2, exp2) if abs(y - CY(v)) > 1e-6 or abs(x - (20 + 940 * dd / 60)) > 1e-6) + abs(len(pts2) - len(exp2))
            ck.cmp(loc, 'cloud: this signal path = daily closes on days 2..60', bad2, 0, 'figure')
    # side box
    side = ch['side']
    if side:
        kv = dict(side[0]['kv'])
        e_ = f['_edge']
        ck.cmp(loc, 'side big number', f"{pc(f['rose10_within60d_pct'])}" in side[0]['text'].split('\n'), True, 'figure')
        ck.cmp(loc, 'side sample line', f"rose 10% within 60 days, from {f['past_trades']} past signals; {pc(f['rose10_never_fell25_within60d_pct'])} without ever falling 25.3%" in side[0]['text'], True, 'figure')
        ck.cmp(loc, 'side Typical high', kv.get('Typical high'), f"{pct(f['typical_biggest_rise_shown'])} · {money(lv['high'])}", 'figure')
        ck.cmp(loc, 'side +10% level', kv.get('+10% level'), money(lv['t20']), 'figure')
        ck.cmp(loc, 'side Reached +20%', kv.get('Reached +20% within 60 days'), pc(f['rose20_within60d_pct']), 'figure')
        ck.cmp(loc, 'side Typical drop', kv.get('Typical drop'), f"{pct(f['typical_deepest_dip_shown'])} · {money(lv['drop'])}", 'figure')
        ck.cmp(loc, 'side Edge gone below', kv.get('Edge gone below'), 'below the bar already' if e_ == 0 else 'holds at every level' if e_ is None else f"{money(px_at(entry, e_))} ({pct(e_, 0)})", 'figure')
        if kind == 'open':
            kv2 = dict(side[1]['kv'])
            ck.cmp(loc, 'side live: best so far', kv2.get('Best so far'), pct(it['best']), 'figure')
            ck.cmp(loc, 'side live: worst so far', kv2.get('Worst so far'), pct(it['worst']), 'figure')
            ck.cmp(loc, 'side live: day 10', kv2.get('Day 10'), 'not yet' if it['day10'] is None else pct(it['day10']), 'figure')
            ck.cmp(loc, 'side live: day N', side[1]['text'].split('\n')[0].upper(), f"LIVE: DAY {it['days']} OF 60", 'figure')
        if kind == 'example' and happened:
            kv2 = dict(side[1]['kv'])
            s = it['s']; m = s['m']; d = S.daily['ETH']
            c10 = d['c'][d['pos'][EX_D0 + dt.timedelta(days=10)]]; c60 = d['c'][d['pos'][EX_D0 + dt.timedelta(days=60)]]
            ck.cmp(loc, 'what it did: +10% / +20%', kv2.get('Reached +10% / +20%'), f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}", 'figure')
            hiday = m['dpk']; loday = m['ddday']
            rng = lambda dd: (lambda k: f'{2 * k - 1}–{2 * k}')((dd + 1) // 2)
            ck.cmp(loc, 'what it did: best price', kv2.get('Best price'), f"{pct(m['up'])}, days {rng(hiday)}", 'figure')
            ck.cmp(loc, 'what it did: deepest drop', kv2.get('Deepest drop'), f"{pct(m['dd'])}, days {rng(loday)}", 'figure')
            ck.cmp(loc, 'what it did: day 10', kv2.get('Day 10 check'), f"{'Red' if c10 < entry else 'Green'}, {pct((c10 / entry - 1) * 100)}", 'figure')
            ck.cmp(loc, 'what it did: day 60', kv2.get('Price on day 60'), pct((c60 / entry - 1) * 100), 'figure')
