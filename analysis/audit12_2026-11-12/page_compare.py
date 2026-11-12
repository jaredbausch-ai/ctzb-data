"""Compare everything the page displays with my own values. python3 page_compare.py <SN> <state_dir> <pkl>"""
import sys, os, json, pickle, re, csv, math, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import chk as K

SN, root, pkl = sys.argv[1:4]
PG = json.load(open(f'page_{SN}.json'))
MY = pickle.load(open(f'{SN}_mine.pkl', 'rb'))
P = pickle.load(open(pkl, 'rb'))
sig = P['sig']; today = P['today']; now = P['now']
M = L.Market(root, now)
feed = json.load(open(os.path.join(root, 'feed', 'ctzb_feed.json')))
rh = L.rh
MINUS = '−'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
def dlong(d):
    d = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d)[:10])
    return f'{d.day} {MON[d.month - 1]} {d.year}'
def fmt(v, d=1):
    if v is None: return 'n/a'
    r = rh(v, d) if d else rh(v)
    if r == 0: return f'{0:.{d}f}'
    s = f'{abs(r):.{d}f}'
    return (MINUS if r < 0 else '') + s
def pct(v, d=1, sign=True):
    if v is None: return 'n/a'
    r = rh(v, d) if d else rh(v)
    return ('+' if sign and r > 0 else '') + fmt(v, d) + '%'
def money(v):
    if v is None: return 'n/a'
    r = rh(v, 2)
    return '$' + f'{r:,.2f}'
c = lambda loc, lab, shown, yours, cause='': K.check(SN, loc, lab, shown, yours, cause)
def has(loc, lab, text, piece, cause='text'):
    return K.check(SN, loc, lab, piece if piece in text else f'(not found) {text[:300]}', piece, cause)

MINE = {}
for (a, tf), lst in sig.items():
    for x in lst:
        if x['closed']:
            MINE[(x['ch'], str(x['d0']))] = x
members = MY['members']
for k, v in members.items():
    MINE[k]['grade'] = v['grade']
APLUS = sorted([(k, MINE[k]) for k in members if members[k]['grade'] == 'A+'], key=lambda kv: str(kv[1]['d0']), reverse=True)
CARDS = MY['CARDS']; MISS = MY['MISS']; GS = MY['GS']

# my open signals with progress
def progress(x):
    a = x['a']; dd = M.day[a]; e = x['entry']; i0 = M.pos[a][x['d0']]
    win = [k for k in range(i0 + 1, len(dd['date'])) if dd['date'][k] < today and (dd['date'][k] - x['d0']).days <= 60]
    mk = lambda m: next((rh((dd['close'][k] / e - 1) * 100, 1) for k in win if (dd['date'][k] - x['d0']).days == m), None)
    return dict(days=(today - x['d0']).days, best=(max(dd['high'][k] for k in win) / e - 1) * 100 if win else None,
                worst=(min(dd['low'][k] for k in win) / e - 1) * 100 if win else None, d10=mk(10), win=win)
OPEN = []
for ch, d in MY['open']:
    x = MINE[(ch, d)]
    o = next(o for o in feed['open_signals'] if o['chart'] == ch and o['entry_date'] == d)
    OPEN.append((x, progress(x), o))
OPENA = [(x, p, o) for x, p, o in OPEN if o['grade'] == 'A+']
init = PG['initial']

# ------------------------------------------------ header, banner, footer, lead
gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
c('page header', 'market filter pill', init['pill'], f'Market filter: {"on" if M.gate(today) else "off"}', 'gate today')
last_closed = max(d for d in M.day['ETH']['date'] if d < today)
last_closed_b = max(d for d in M.day['BTC']['date'] if d < today)
has('page banner', 'scored date', init['review'], f'scored {dlong(today)} (feed {gen:%H:%M} UTC)')
has('page footer', 'daily candles closed through', init['feedState'], f'Daily candles closed through {dlong(min(last_closed, last_closed_b))}', 'last closed daily bar')
has('page footer', 'updated / checks', init['feedState'], f'updated {gen:%H:%M} UTC · checks passed')
c('page lead panel', 'text', init['lead'], "The lead trader's feed is unavailable right now. His real entries and exits appear here the moment they fill.", '(n)')

# ------------------------------------------------ picker
pk = init['picker']
live_btns = [b for b in pk if b['cls'].startswith('pick top') and any(b['sel'] == o['signal_id'] for _, _, o in OPENA)]
c('page picker', 'live buttons (ids)', ' '.join(b['sel'] for b in live_btns), ' '.join(f"{x['a']}-{x['tf']}D-{x['d0']}" for x, p, o in OPENA), 'open A+ list')
for x, p, o in OPENA:
    sid = f"{x['a']}-{x['tf']}D-{x['d0']}"
    b = next((b for b in pk if b['sel'] == sid), None)
    if b:
        c('page picker ' + sid, 'button text', b['text'].replace('\n', ' '), f"{x['ch']} Day {p['days']} best {pct(p['best'])} · worst {pct(p['worst'])}", 'picker')
form_ids = [lo.split(' ', 2)[2] for lo in CARDS if lo.startswith('forming card')]
c('page picker', 'forming buttons (set)', ' '.join(sorted(b['sel'] for b in pk if b['sel'] in form_ids or b['cls'].startswith('pick below'))), ' '.join(sorted(form_ids)), 'forming list')
for sid in form_ids:
    f, rule, nex, nsg = CARDS['forming card ' + sid]
    cd = next(cc for cc in feed['cards'] if cc['signal_id'] == sid)
    b = next((b for b in pk if b['sel'] == sid), None)
    if b:
        conf = sid.split('-', 2)[2]
        c('page picker ' + sid, 'button text', b['text'].replace('\n', ' '),
          f"{cd['chart']} {f['reach10']}% rose 10% in 60 days · n {f['n']} · {'top grade' if cd['grade'] == 'A+' else 'not top grade'} · confirms {dlong(conf)}", 'picker')
if not form_ids:
    has('page picker', 'forming empty', init['pickerText'], 'Nothing forming today.')

# ------------------------------------------------ previous signals column
intact = [(x, p, o) for x, p, o in OPENA if o['edge_status'] != 'lost']
lost = [(x, p, o) for x, p, o in OPENA if o['edge_status'] == 'lost']
# my own edge status for A+ opens
def my_status(x, p):
    f = CARDS[f"open card {x['a']}-{x['tf']}D-{x['d0']}"][0]
    lvl = f['edge']
    if lvl == 0: return 'lost'
    if lvl is None: return 'intact'
    dd = M.day[x['a']]; e = x['entry']
    for k in p['win']:
        if dd['low'][k] <= e * (1 + lvl / 100): return 'lost'
        if dd['high'][k] >= e * 1.10: return 'intact'
    return 'intact'
myint = [(x, p) for x, p, o in OPENA if my_status(x, p) == 'intact']; mylost = [(x, p) for x, p, o in OPENA if my_status(x, p) == 'lost']
exp_int = [f"{x['ch']}\nDay {p['days']} of 60 · best {pct(p['best'])} · worst {pct(p['worst'])}\nOn track" for x, p in myint] or ['No open top-grade setup with its edge intact.']
c('page previous', 'edge intact list', ' || '.join(d['text'] for d in init['prevIntact']), ' || '.join(exp_int), 'previous column')
exp_closed = [f"{x['ch']}\nDay {p['days']} of 60 · best {pct(p['best'])} · worst {pct(p['worst'])}\nEdge lost" for x, p in mylost]
for k, x in APLUS[:5]:
    m = x['m']
    badge = 'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed'
    exp_closed.append(f"{x['ch']}\n{dlong(x['d0'])} · best {pct(m['up'])} · worst {pct(m['dd'])}\n{badge}")
shown_closed = [d['text'] for d in init['prevClosed']]
for i, e_ in enumerate(exp_closed):
    c('page previous', f'edge lost or closed #{i + 1}', shown_closed[i] if i < len(shown_closed) else '', e_, 'previous column')
c('page previous', 'edge lost or closed count', len(shown_closed), len(exp_closed))
# double-rounding check on ledger 6-place values used by the page
for k, x in APLUS:
    m = x['m']
    for lab, v in (('bestMove', m['up']), ('maxDrawdown', m['dd']), ('return60d', m['ret'])):
        if rh(rh(v, 6), 1) != rh(v, 1):
            c(f'page ledger value {k}', lab + ' shown from 6-place value', rh(rh(v, 6), 1), rh(v, 1), 'double rounding')

# ------------------------------------------------ cards
def exp_card(sel):
    """Return (loc key in CARDS, my figs, feed card, kind, entry, extra)"""
    if sel == 'example':
        return 'example_card', 'example'
    if any(sel == f"{x['a']}-{x['tf']}D-{x['d0']}" for x, p, o in OPENA):
        return 'open card ' + sel, 'open'
    return 'forming card ' + sel, 'forming'

def ladder_exp(f, n):
    rows = [('From entry', n, f['fe'][0], f['fe'][3])] + [(f'Falls {th}% first', f['lad'][th][0], f['lad'][th][1], f['lad'][th][4]) for th in (5, 10, 15, 20)]
    return rows

for sel, d in PG['selections'].items():
    key, kind = exp_card(sel)
    f, rule, nex, nsg = CARDS[key]
    card = d['card']; loc = f'page card {sel}'
    if kind == 'example':
        fc = feed['example_card']; x = MINE[('ETH 2D', '2024-09-22')]; asset, tfs = 'ETH', '2D'; grade = 'A+'
        mi = MY['EXMISS']
    elif kind == 'open':
        fc = next(o for o in feed['open_signals'] if o['signal_id'] == sel)['card']; x = MINE[(fc['chart'], fc['confirms_on'])]
        asset, tfs = fc['asset'], fc['timeframe']; grade = next(o for o in feed['open_signals'] if o['signal_id'] == sel)['grade']
        mi = MISS[(asset, grade)]
    else:
        fc = next(cc for cc in feed['cards'] if cc['signal_id'] == sel); x = None
        asset, tfs = fc['asset'], fc['timeframe']; grade = fc['grade']; mi = MISS[(asset, grade)]
    c(loc, 'where', card['where'], f"{asset} · {tfs} chart{' · example' if kind == 'example' else ''}".upper(), 'card head')
    c(loc, 'state', card['state'], {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind], 'card head')
    if kind == 'open':
        p = progress(x)
        c(loc, 'line', card['head'][2], f"Confirmed {dlong(x['d0'])} · entry close {money(x['entry'])} · day {p['days']} of 60 · best so far {pct(p['best'])} · worst {pct(p['worst'])}", 'card line')
    elif kind == 'example':
        c(loc, 'line', card['head'][2], f"Example: confirmed {dlong('2024-09-22')} · entry close {money(x['entry'])}", 'card line')
    else:
        # my forming low day and kill close (verified in audit_data against the feed)
        mca = fc['must_close_above']
        c(loc, 'line', card['head'][2], f"Low {dlong(fc['low_day'])} · confirms {dlong(fc['confirms_on'])}" + (f" if it closes above {money(mca)}" if mca else ''), 'card line')
    c(loc, 'big number', card['big'], f"{f['reach10']}%", 'big number')
    c(loc, 'under big number', card['odds'][2], f"{f['surv10']}% did it without ever falling 25.3%", 'surv10')
    c(loc, 'sample line', card['odds'][3], f"from {fc['sample']} · every figure covers the 60 days after entry", 'sample line')
    kv = {k[0]: k[1] for k in card['kv']}
    c(loc, 'Typical high', kv.get('Typical high'), pct(f['bestraw']), 'median rounding')
    c(loc, 'Typical drop from entry', kv.get('Typical drop from entry'), pct(f['deepraw']), 'median rounding')
    edge = f['edge']
    c(loc, 'Edge gone below', kv.get('Edge gone below'), 'Below the 70% bar from entry' if edge == 0 else f'{pct(edge, 0)} before it rises 10%' if edge is not None else 'Holds at every level', 'edge')
    c(loc, 'If it misses', kv.get('If it misses: went above entry'), f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}", 'misses')
    c(loc, 'lead marker', card['marker'], 'Lead trader: unavailable', '(n)')
    below = kind == 'forming' and grade != 'A+'
    if below:
        c(loc, 'pool line', card['statsAll'][-1] if card['statsAll'] else '', f"all {mi['signals']} {asset} signals of this grade", 'misses pool')
    tl = {t[0]: t[1] for t in card['tiles']}
    gw = 'top-grade' if grade == 'A+' else 'same-grade'
    mt = f" · {mi['misses']} misses of all {mi['signals']} {asset} {gw} signals"
    exp_tiles = {'Dip before the high, from entry': pct(f['dipraw']), 'High lands around': f"Day {f['dHigh']}",
                 f"Reached +20% within 60 days · n {f['n']}": f"{f['reach20']}%", f"Touched {MINUS}30% within 60 days · n {f['n']}": f"{f['t30']}%",
                 'Typical high': pct(f['bestraw']), 'Deepest dip lands around': f"Day {f['dLow']}",
                 'Typical worst drop, misses' + mt: pct(mi['median_worst_drop_pct']), 'Typical change by day 60, misses' + mt: pct(mi['median_day60_pct'])}
    for k_, v_ in exp_tiles.items():
        c(loc, 'tile ' + k_, tl.get(k_, '(tile missing)'), v_, 'tile')
    c(loc, 'tile count', len(card['tiles']), len(exp_tiles))
    lad = card['ladder']
    for i, (lab, n_, v_, x_) in enumerate(ladder_exp(f, f['n'])):
        s_ = lad[i] if i < len(lad) else ['', '', '', '']
        c(loc, f'ladder {lab}', s_[0], f'{lab} n {n_}', 'ladder')
        c(loc, f'ladder {lab} value', s_[3], 'n/a' if v_ is None else f'{v_}%', 'ladder')
        c(loc, f'ladder {lab} gone', 'gone' in s_[2], x_ is not None and x_ < 70, 'ladder edge colour (exact share vs 70)')
        c(loc, f'ladder {lab} bar width', s_[1], f'{v_ if v_ is not None else 0}%', 'ladder bar')
    c(loc, 'ladder box label', card['boxLbls'][0], 'WHERE THE ODDS FADE · THIS SETUP')
    er = card['eras']
    c(loc, 'era before 2022', ' '.join(er[0]), f"Before 2022 n {f['nOld']} {f['sOld'] if f['sOld'] is not None else 0}% {f['sOld'] if f['sOld'] is not None else 'n/a'}%", 'era')
    c(loc, 'era since 2022', ' '.join(er[1]), f"Since 2022 n {f['nNew']} {f['sNew'] if f['sNew'] is not None else 0}% {f['sNew'] if f['sNew'] is not None else 'n/a'}%", 'era')
    if kind == 'forming':
        note = card['head'][3] if len(card['head']) > 3 else ''
        best = max((cc for cc in feed['cards']), key=lambda cc: (CARDS['forming card ' + cc['signal_id']][0]['reach10']))
        if below:
            exp_note = ('Best setup forming today.' if sel == best['signal_id'] else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms."
        else:
            exp_note = 'Not confirmed yet. It can still vanish before it confirms.'
        c(loc, 'forming note', note, exp_note, 'forming note')
    # ---------------- chart (At the alert)
    ch = d['chart_alert']; info = ch['info']; svg = ch['svg']; locc = f'page chart {sel}'
    a = asset; tf = int(tfs[:-1])
    if kind == 'example':
        ex = json.load(open(os.path.join(root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
        bars = ex['bars']; E = ex['entry_index']; entry = x['entry']; tEntry = dt.date(2024, 9, 22)
        b2 = M.chart('ETH', 2); idx = {t: i for i, t in enumerate(b2['t'])}
        for j, b in enumerate(bars):
            i = idx.get(b['t'])
            if i is None:
                c('example chart data', f'bar {j}', 'present', 'absent in raw ETH 2D'); continue
            c('example chart data', f'bar {j} {L.todate(b["t"])} ohlc', (b['o'], b['h'], b['l'], b['c']), (b2['open'][i], b2['high'][i], b2['low'][i], b2['close'][i]), 'example bars vs raw')
        c('example chart data', 'entry bar closes on 2024-09-22', str(L.bar_close_date(2, L.todate(bars[E]['t']))), '2024-09-22', 'entry index')
        c('example chart data', 'entry_close', ex['entry_close'], rh(entry, 2), 'example entry')
        opens = [b['t'] for b in bars]
        A_ = E
    else:
        cdl = list(csv.DictReader(open(os.path.join(root, f'datasets/candles_{a.lower()}_{tfs.lower()}.csv'))))
        bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in cdl]
        raw = M.chart(a, tf); rawu = L.load(os.path.join(root, 'data', f'{a}_{tfs}.csv'), clamp=False)
        c(f'candles dataset {a} {tfs}', 'last 70 bars equal raw data', [(b['t'], b['o'], b['h'], b['l'], b['c']) for b in bars] == [(rawu['t'][i], rawu['open'][i], rawu['high'][i], rawu['low'][i], rawu['close'][i]) for i in range(len(rawu['t']) - 70, len(rawu['t']))], True, 'candles dataset')
        if kind == 'open':
            tEntry = x['d0']; entry = x['entry']
            E = next(i for i, b in enumerate(bars) if L.bar_close_date(tf, L.todate(b['t'])) == tEntry)
            A_ = E
        else:
            E = len(bars) - 1; entry = M.day[a]['close'][-1]; tEntry = dt.date.fromisoformat(fc['confirms_on'])
        opens = [b['t'] for b in bars]
        # extend with future bucket opens (my own rule)
        while opens[-1] <= int(dt.datetime(tEntry.year, tEntry.month, tEntry.day, tzinfo=dt.timezone.utc).timestamp()) + 61 * 86400:
            od = L.todate(opens[-1]); nx = L.bar_close_date(tf, od) + dt.timedelta(days=1)
            opens.append(int(dt.datetime(nx.year, nx.month, nx.day, tzinfo=dt.timezone.utc).timestamp()))
    tE = int(dt.datetime(tEntry.year, tEntry.month, tEntry.day, tzinfo=dt.timezone.utc).timestamp())
    def slot_of_day(k):
        day = tEntry + dt.timedelta(days=k)
        for i, t in enumerate(opens):
            od = L.todate(t); cd_ = L.bar_close_date(tf, od)
            if od <= day <= cd_:
                return i
        return len(opens) - 1
    if kind == 'forming':
        A_ = slot_of_day(0)
    nS = len(opens); sl = 940 / nS; X = lambda i: 20 + sl * i + sl / 2
    hi_p = entry * (1 + f['bestX'] / 100); drop_p = entry * (1 + f['deepX'] / 100)
    edge_p = entry * (1 + edge / 100) if edge else None
    shown = bars[:E + 1] if kind == 'example' else bars
    lo = min(min(b['l'] for b in shown), drop_p, entry * 0.8) * 0.95; hi = max(max(b['h'] for b in shown), hi_p) * 1.07
    Y = lambda p_: 480 - (p_ - lo) / (hi - lo) * 456
    texts = [e for e in svg if e['tag'] == 'text']
    lines = [e for e in svg if e['tag'] == 'line']
    def vline_x(label_start):
        t = next((e for e in texts if e['text'].startswith(label_start)), None)
        return None if t is None else float(t['attrs']['x']) - 6, t
    def near(v, w, tol=1e-6): return v is not None and w is not None and abs(v - w) < tol
    xs, t_ = vline_x('Entry' if kind != 'forming' else 'Today')
    c(locc, 'Entry/Today line x (bar)', None if xs is None else rh((xs - 20) / sl - 0.5, 6), float(E), 'vline position')
    if kind != 'forming':
        c(locc, 'entry bar closes on entry date', str(L.bar_close_date(tf, L.todate(opens[E]))), str(tEntry), 'entry bar')
    xs, t_ = vline_x('Day 60')
    c(locc, 'Day 60 line x (slot)', None if xs is None else rh((xs - 20) / sl - 0.5, 6), float(min(nS - 1, slot_of_day(60))), 'vline position')
    xs, t_ = vline_x('High usually ~day')
    c(locc, 'High line label', t_['text'] if t_ else None, f"High usually ~day {f['dHigh']}", 'label')
    c(locc, 'High line x (slot)', None if xs is None else rh((xs - 20) / sl - 0.5, 6), float(slot_of_day(f['dHigh'])), 'vline position')
    if kind == 'forming':
        xs, t_ = vline_x('Confirms')
        c(locc, 'Confirms line label', t_['text'] if t_ else None, f"Confirms {dlong(tEntry)} · entry, day 0", 'label')
        c(locc, 'Confirms line x (slot)', None if xs is None else rh((xs - 20) / sl - 0.5, 6), float(A_), 'vline position')
    # horizontal levels: price tags and labels
    tags = [e['text'] for e in texts if e['attrs'].get('fill') == '#07060F']
    c(locc, 'price tags', ' '.join(sorted(tags)), ' '.join(sorted([money(hi_p), money(entry * 1.1), money(entry), money(drop_p)])), 'price tags')
    lab = lambda s: next((e for e in texts if e['text'].startswith(s)), None)
    t1 = lab('Typical high'); c(locc, 'typical high label', t1['text'] if t1 else None, f"Typical high {pct(f['bestraw'])}", 'label')
    t2 = lab('+10% ·'); c(locc, '+10% label', t2['text'] if t2 else None, f"+10% · {f['reach10']}% of past signals got here", 'label')
    t3 = lab('Typical drop'); c(locc, 'typical drop label', t3['text'] if t3 else None, f"Typical drop {pct(f['deepraw'])}", 'label')
    t4 = lab('Edge gone below')
    c(locc, 'edge label', t4['text'] if t4 else None, f"Edge gone below {money(edge_p)} ({pct(edge, 0)}, before +10%)" if edge_p else None, 'label')
    # y positions of the level lines (drawn from xE to x60)
    hl = [e for e in lines if e['attrs'].get('y1') == e['attrs'].get('y2') and float(e['attrs']['x1']) > 20.0001]
    ys = sorted(float(e['attrs']['y1']) for e in hl)
    exp_ys = sorted([Y(hi_p), Y(entry * 1.1), Y(entry), Y(drop_p)] + ([Y(edge_p)] if edge_p else []))
    c(locc, 'level line y positions', ' '.join(f'{v:.4f}' for v in ys), ' '.join(f'{v:.4f}' for v in exp_ys), 'level lines / axis scaling')
    # ladder zones on the chart
    zl = [e['text'] for e in texts if e['attrs'].get('font-weight') == '700' and e['attrs'].get('text-anchor') == 'middle' and e['attrs'].get('fill') != '#07060F' and e['text'].endswith('%') or e['text'] == 'n/a']
    vals = [f['fe'][0]] + [f['lad'][th][1] for th in (5, 10, 15)]
    c(locc, 'ladder zone labels', ' '.join(zl), ' '.join('n/a' if v is None else f'{v}%' for v in vals), 'chart zones')
    zr = [e for e in svg if e['tag'] == 'rect' and e['attrs'].get('opacity') == '0.24']
    cols = [('high' if 'high' in (e['style'] or '') else 'drop' if 'drop' in (e['style'] or '') else 'closed') for e in zr]
    xv = [f['fe'][3]] + [f['lad'][th][4] for th in (5, 10, 15)]
    c(locc, 'ladder zone colours', ' '.join(cols), ' '.join('closed' if v is None else 'high' if v >= 70 else 'drop' for v in xv), 'zone colour (exact share)')
    # candles drawn
    nc = len([e for e in svg if e['tag'] == 'rect' and e['attrs'].get('opacity') is None and e['attrs'].get('rx') is None and e['attrs'].get('width') not in ('1100',)])
    c(locc, 'candles drawn', nc, E + 1 if kind == 'example' else len(bars), 'candles shown at the alert')
    # geometry: x-axis date labels, grid label y, candle wicks, ladder zone y-bands, shaded zones
    xl = [e for e in texts if e['attrs'].get('y') == '502']
    okx = all(L.todate(opens[rh((float(e['attrs']['x']) - 20) / sl - 0.5)]).strftime('%d ') + MON[L.todate(opens[rh((float(e['attrs']['x']) - 20) / sl - 0.5)]).month - 1] == e['text'] for e in xl)
    c(locc, f'x-axis date labels ({len(xl)}) match slot dates', okx, True, 'x axis')
    gl = [e for e in texts if e['attrs'].get('x') == '968']
    okg = all(abs(float(e['attrs']['y']) - 5 - Y(float(e['text'].replace('$', '').replace(',', '')))) < 1e-6 for e in gl)
    c(locc, f'price grid labels ({len(gl)}) at their prices', okg, True, 'y axis')
    wicks = [e for e in svg if e['tag'] == 'line' and e['attrs'].get('stroke-width') == '1.5' and e['attrs'].get('y1') != '24']
    drawn = bars[:E + 1] if kind == 'example' else bars
    okw = len(wicks) == len(drawn) and all(abs(float(w['attrs']['x1']) - X(i)) < 1e-6 and abs(float(w['attrs']['y1']) - Y(b['h'])) < 1e-6 and abs(float(w['attrs']['y2']) - Y(b['l'])) < 1e-6 for i, (w, b) in enumerate(zip(wicks, drawn)))
    c(locc, f'candle wicks ({len(wicks)}) at bar highs/lows', okw, True, 'candles')
    xE = X(A_)
    steps = [(0, -5), (-5, -10), (-10, -15), (-15, -20)]
    okz = len(zr) == 4 and all(abs(float(z['attrs']['x']) - xE) < 1e-6 and abs(float(z['attrs']['y']) - Y(entry * (1 + a1 / 100))) < 1e-6 and
                               abs(float(z['attrs']['y']) + float(z['attrs']['height']) - min(480, Y(entry * (1 + b1 / 100)))) < 1e-6 for z, (a1, b1) in zip(zr, steps))
    c(locc, 'ladder zones span entry→-5→-10→-15→-20% from the entry bar', okz, True, 'zones')
    sh = [e for e in svg if e['tag'] == 'rect' and e['attrs'].get('opacity') in ('0.07', '0.1')]
    x60 = X(min(nS - 1, slot_of_day(60)))
    oks = len(sh) == 2 and abs(float(sh[0]['attrs']['y']) - Y(hi_p)) < 1e-6 and abs(float(sh[0]['attrs']['height']) - (Y(entry) - Y(hi_p))) < 1e-6 \
        and abs(float(sh[1]['attrs']['y']) - Y(entry)) < 1e-6 and abs(float(sh[1]['attrs']['height']) - (Y(drop_p) - Y(entry))) < 1e-6 \
        and all(abs(float(s_['attrs']['x']) - xE) < 1e-6 and abs(float(s_['attrs']['width']) - (x60 - xE)) < 1e-6 for s_ in sh)
    c(locc, 'shaded zones: entry bar to day 60, typical high / typical drop', oks, True, 'zones')
    if kind == 'forming':
        lw = lab('Low ')
        tb = next((b for b in bars if L.todate(b['t']) == dt.date.fromisoformat(fc['low_date'])), None)
        myl = min(M.day[a]['low'][M.pos[a][dt.date.fromisoformat(fc['low_date']) + dt.timedelta(days=k)]] for k in range(tf) if dt.date.fromisoformat(fc['low_date']) + dt.timedelta(days=k) in M.pos[a])
        c(locc, 'low marker label', lw['text'] if lw else None, f"Low {dlong(fc['low_day'])} · {money(myl)}", 'low marker')
    if kind == 'example':
        c(locc, 'toggle shown', ch['info']['toggleHidden'], False)
        c(locc, 'no outcome at the alert', any(e['text'].startswith('This one') for e in texts), False, 'outcome hidden')
    # side box
    side = info['sideBoxes'][0]
    exp_side = [f"{f['reach10']}%", f"rose 10% within 60 days, from {f['n']} past signals; {f['surv10']}% without ever falling 25.3%",
                f"Typical high\n{pct(f['bestraw'])} · {money(hi_p)}", f"+10% target\n{money(entry * 1.1)}", f"Reached +20% within 60 days\n{f['reach20']}%",
                f"Typical drop\n{pct(f['deepraw'])} · {money(drop_p)}",
                "Edge gone below\n" + ('below the bar already' if edge == 0 else 'holds at every level' if edge is None else f"{money(edge_p)} ({pct(edge, 0)})")]
    for e_ in exp_side:
        has(locc, 'side: ' + e_.split('\n')[0][:30], side, e_, 'chart side')
    if kind == 'open':
        p = progress(x); s2 = info['sideBoxes'][1]
        for e_ in (f"LIVE: DAY {p['days']} OF 60", f"Best so far\n{pct(p['best'])}", f"Worst so far\n{pct(p['worst'])}", f"Day 10\n{'not yet' if p['d10'] is None else pct(p['d10'])}"):
            has(locc, 'live box: ' + e_.split('\n')[0], s2, e_, 'live box')
        c(locc, 'title', info['title'], f"{a} · {tfs} · LIVE SETUP, DAY {p['days']} OF 60", 'title')
        has(locc, 'subtitle', info['sub'], f"Confirmed {dlong(x['d0'])} · entry close {money(entry)}.")
    if kind == 'forming':
        has(locc, 'subtitle', info['sub'], f"Low {dlong(fc['low_day'])} · confirms {dlong(fc['confirms_on'])} · price levels drawn from today's price ({money(entry)})")
    # cloud
    pp = feed['example_past_paths'] if kind == 'example' else next(p_ for p_ in feed['past_paths'] if p_['asset'] == a)
    exs = [MINE[k] for k in members if members[k]['grade'] == 'A+' and MINE[k]['a'] == a and (kind != 'example' or MINE[k]['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22))]
    paths = []
    for s_ in exs:
        pth = [0.0]
        for k_ in range(1, 61):
            i_ = M.pos[a].get(s_['d0'] + dt.timedelta(days=k_))
            if i_ is None: break
            pth.append((M.day[a]['close'][i_] / s_['entry'] - 1) * 100)
        if len(pth) == 61: paths.append(pth)
    q = lambda k_, f_: rh(L.q([p_[k_] for p_ in paths], f_), 1)
    c(locc, 'cloud subtitle', info['cloudSub'], (f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {len(paths)}" if kind == 'example' else f"Every past {a} top-grade signal, n {len(paths)}"), 'cloud n')
    has(locc, 'cloud day 60 note', info['cloudNote'], f"Day 60: median {pct(q(60, .5))}, middle half {pct(q(60, .25))} to {pct(q(60, .75))}.", 'cloud note')
    if grade != 'A+':
        has(locc, 'cloud caveat', info['cloudNote'], "Top-grade signals only; the selected setup isn't top grade.")
    poly = next((e for e in ch['cloud'] if e['tag'] == 'polyline'), None)
    if poly:
        pts = [tuple(map(float, s_.split(','))) for s_ in poly['attrs']['points'].split()]
        Yc = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
        okp = all(abs(pt[0] - (20 + 940 * k_ / 60)) < 1e-6 and abs(pt[1] - Yc(q(k_, .5))) < 1e-6 for k_, pt in enumerate(pts)) and len(pts) == 61
        c(locc, 'cloud median polyline (61 points)', okp, True, 'cloud median path')
        pg_ = next((e for e in ch['cloud'] if e['tag'] == 'polygon'), None)
        pts = [tuple(map(float, s_.split(','))) for s_ in pg_['attrs']['points'].split()]
        exp = [(20 + 940 * k_ / 60, Yc(q(k_, .75))) for k_ in range(61)] + [(20 + 940 * k_ / 60, Yc(q(k_, .25))) for k_ in range(60, -1, -1)]
        c(locc, 'cloud middle-half band (122 points)', len(pts) == 122 and all(abs(a_[0] - b_[0]) < 1e-6 and abs(a_[1] - b_[1]) < 1e-6 for a_, b_ in zip(pts, exp)), True, 'cloud band')
    # ---------------- example: what happened
    if kind == 'example' and 'chart_happened' in d:
        hp = d['chart_happened']; t2s = [e for e in hp['svg'] if e['tag'] == 'text']
        dd = M.day['ETH']; i0 = M.pos['ETH'][dt.date(2024, 9, 22)]
        ks = [i0 + k_ for k_ in range(1, 61)]
        hs = [dd['high'][k_] for k_ in ks]; ls_ = [dd['low'][k_] for k_ in ks]
        jh = hs.index(max(hs)) + 1; jl = ls_.index(min(ls_)) + 1
        rng = lambda j: f'days {j - 1 if j % 2 == 0 else j}–{j if j % 2 == 0 else j + 1}'   # 2D bar holding day j (days 1-2, 3-4, ...)
        this = [e['text'] for e in t2s if e['text'].startswith('This one')]
        c('page chart example (what happened)', 'best label', next((t for t in this if '+' in t.split('·')[1]), None), f"This one: {money(max(hs))} · {pct((max(hs) / entry - 1) * 100)} · {rng(jh)}", 'what happened')
        c('page chart example (what happened)', 'deepest label', next((t for t in this if MINUS in t.split('·')[1]), None), f"This one: {money(min(ls_))} · {pct((min(ls_) / entry - 1) * 100)} · {rng(jl)}", 'what happened')
        sb = hp['info']['sideBoxes'][1]
        r10 = max(hs) >= entry * 1.1; r20 = max(hs) >= entry * 1.2
        cl10 = dd['close'][i0 + 10]; cl60 = dd['close'][i0 + 60]
        for e_ in (f"Reached +10% / +20%\n{'Yes' if r10 else 'No'} / {'Yes' if r20 else 'No'}", f"Best price\n{pct((max(hs) / entry - 1) * 100)}, {rng(jh)}",
                   f"Deepest drop\n{pct((min(ls_) / entry - 1) * 100)}, {rng(jl)}", f"Day 10 check\n{'Red' if cl10 < entry else 'Green'}, {pct((cl10 / entry - 1) * 100)}",
                   f"Price on day 60\n{pct((cl60 / entry - 1) * 100)}"):
            has('page chart example (what happened)', 'side: ' + e_.split('\n')[0], sb, e_, 'what happened side')
        # candles: all bars drawn in What happened
        ncs = len([e for e in hp['svg'] if e['tag'] == 'rect' and e['attrs'].get('opacity') is None and e['attrs'].get('rx') is None and e['attrs'].get('width') != '1100'])
        c('page chart example (what happened)', 'candles drawn', ncs, len(bars))
        # cloud "this signal" line: 2D closes vs daily closes at days 2..60
        pl = [e for e in hp['cloud'] if e['tag'] == 'polyline']
        if len(pl) == 2:
            pts = [tuple(map(float, s_.split(','))) for s_ in pl[1]['attrs']['points'].split()]
            Yc = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
            exp = [(0, 0.0)] + [(k_, (dd['close'][i0 + k_] / entry - 1) * 100) for k_ in range(2, 61, 2)]
            okp = len(pts) == len(exp) and all(abs(pt[0] - (20 + 940 * k_ / 60)) < 1e-6 and abs(pt[1] - Yc(v)) < 1e-6 for pt, (k_, v) in zip(pts, exp))
            c('page chart example (what happened)', 'this-signal path (31 points, daily closes days 0-60 even)', okp, True, 'cloud this signal')
        # y scaling uses all bars in What happened
# ------------------------------------------------ record tab
for a in ('all', 'ETH', 'BTC'):
    rec = PG['record'][a]; loc = f'page past signals {a}'
    rows = [x for k, x in APLUS if a == 'all' or x['a'] == a]
    c(loc, 'count line', rec['count'], f"{len(rows)} signals · {sum(not x['m']['r10'] for x in rows)} missed +10%", 'record count')
    c(loc, 'rows', len(rec['rows']), len(rows))
    shown = {(r[0], r[1]): r for r in rec['rows']}
    dates = [r[0] for r in rec['rows']]
    for x in rows:
        r = shown.get((dlong(x['d0']), x['ch']))
        m = x['m']
        exp = [dlong(x['d0']), x['ch'], money(x['entry']), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No', pct(m['up']), pct(m['dd']), pct(m['ret']), str(m['dpk'])]
        c(loc, f"row {x['ch']} {x['d0']}", ' | '.join(r) if r else '(missing)', ' | '.join(exp), 'record row')
    order = [dt.datetime.strptime(d_.replace('Sept', 'Sep'), '%d %b %Y').date() for d_ in dates]
    c(loc, 'sorted newest first', order == sorted(order, reverse=True), True)
    for g in (['ETH', 'BTC'] if a == 'all' else [a]):
        s = GS[(g, 'A+')]; mi = MISS[(g, 'A+')]
        txt = next((t for t in rec['sum'] if t.startswith(g)), '')
        exp = f"{g}\n{s['n']} signals\nRose 10% in 60 days\n{s['reach10']}%\nReached +20% in 60 days\n{s['reach20']}%\nRose 10%, never fell 25.3%\n{s['surv10']}%\nMedian deepest dip\n{pct(s['medDip'])}\nMisses: median best price\n{pct(mi['median_peak_pct'])}"
        c(loc, f'summary {g}', txt, exp, 'record summary')
    c(loc, 'header', ' | '.join(rec['head']), 'Confirmed | Chart | Entry close | Rose 10% | Reached +20% | Best | Deepest drop | Day 60 | High on day')
K.save(f'checks_page_{SN}.csv')
bad = [r for r in K.ROWS if r['ok'] != 'yes']
print(SN, 'page checks', len(K.ROWS), 'disagreements', len(bad))
for r in bad[:100]:
    print(' ', r['location'], '|', r['label'], '| shown', r['shown'][:200], '| mine', r['yours'][:200], '|', r['cause'])
