"""Audit 11: compare every number the page showed (page_dump.py) with my own values.
  python3 page_check.py <name> <state_root> <now ISO>"""
import csv, datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *          # noqa
import checks as K

NAME, ROOT, NOW = sys.argv[1], sys.argv[2], sys.argv[3]
now = dt.datetime.fromisoformat(NOW.replace('Z', '+00:00'))
S = State(ROOT, now)
OUT = K.OUT
P = json.load(open(os.path.join(OUT, f'_{NAME}_page.json')))
M = json.load(open(os.path.join(OUT, f'_{NAME}_mine.json')))
feed = json.load(open(os.path.join(ROOT, 'feed/ctzb_feed.json')))
ledger = list(csv.DictReader(open(os.path.join(ROOT, 'datasets/ledger.csv'))))
chk = lambda *a, **k: K.chk(NAME, *a, **k)

MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
dl = lambda d: (lambda x: f'{x.day} {MON[x.month - 1]} {x.year}')(D.fromisoformat(str(d)))
MINUS = '−'


def num(v, d=1):
    r = rh(v, d) if d else rh(v)
    if r == 0:
        return f'{0:.{d}f}'
    s = f'{abs(r):.{d}f}'
    return (MINUS if r < 0 else '') + s


def pct(v, d=1):
    if v is None:
        return 'n/a'
    r = rh(v, d) if d else rh(v)
    return ('+' if r > 0 else '') + num(v, d) + '%'


def money(v):
    r = Decimal(float(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return '$' + f'{r:,.2f}'


# ---------------- my per-signal measures (rebuilt here from raw candles)
sig_by_id = {}
for a in ASSETS:
    for tf in TFS:
        for s in S.sig[(a, tf)]:
            sig_by_id[f"{a}-{tf}-{s['d0']}"] = s
led_ap = []
for x in ledger:
    if x['grade'] != 'A+':
        continue
    s = sig_by_id[f"{x['chart'].replace(' ', '-')}-{x['entry']}"]
    m = S.measure(s['a'], s['d0'], s['entry'])
    led_ap.append(dict(s=s, m=m, chart=x['chart'], entry=x['entry'], a=s['a']))
cards = M['cards']
today = D.fromisoformat(M['today'])

# ---------------- header, banner, footer
i0 = P['initial']
chk('page header', 'market filter', i0['filter'], 'Market filter: on' if M['regime_today'] else 'Market filter: off')
gen = feed['generated_at']
chk('page header', 'scored as of (review banner)', i0['rvAsof'], f"{dl(today)} (feed {gen[11:16]} UTC)", 'scored date')
closed_through = max(b[0] for b in S.day['ETH'] if b[0] < today)
chk('page footer', 'daily candles closed through / updated / checks', i0['feedState'],
    f"Daily candles closed through {dl(closed_through)} · updated {gen[11:16]} UTC · checks passed")
chk('page footer', 'disclaimer: entry quality, not advice', 'entry quality only' in i0['footer'], True)

# ---------------- picker
open_ap = [o for o in feed['open_signals'] if o['grade'] == 'A+']
live_btns = [b for b in i0['picker'] if b['cls'].startswith('pick top') and b['sel'] in {o['signal_id'] for o in open_ap}]
chk('page picker', 'live buttons (open top-grade signals)', ','.join(b['sel'] for b in live_btns), ','.join(o['signal_id'] for o in open_ap))
for b in live_btns:
    c = cards[b['sel']]
    exp = f"{b['sel'][:3]} {b['sel'][4:6]}\nDay {c['days']}\nbest {pct(c['sofar_best'])} · worst {pct(c['sofar_worst'])}"
    chk(f"page picker {b['sel']}", 'button text (day, best, worst so far)', b['text'], exp)
form_btns = [b for b in i0['picker'] if b['sel'] not in {o['signal_id'] for o in open_ap} and b['sel'] != 'example']
chk('page picker', 'forming buttons', ','.join(sorted(b['sel'] for b in form_btns)), ','.join(sorted(M['forming'])))
for b in form_btns:
    c = cards[b['sel']]; fc = next(x for x in feed['cards'] if x['signal_id'] == b['sel'])
    exp = (f"{fc['chart']}\n{c['reach10']}%\nrose 10% in 60 days · n {c['n']} · {'top grade' if fc['grade'] == 'A+' else 'not top grade'}"
           f" · confirms {dl(M['forming'][b['sel']]['confirms'])}")
    chk(f"page picker {b['sel']}", 'button text (rose 10%, n, grade, confirms)', b['text'], exp)
if not form_btns:
    chk('page picker', 'forming row empty text', ' | '.join(i0['pnone']), 'Nothing forming today.')


# ---------------- the card
def expect_card(sel, kind):
    """kind: forming / open / example."""
    key = sel + ('|ex' if kind == 'example' else '')
    c = cards[key]
    if kind == 'example':
        fc = feed['example_card']; asset, tf, grade = 'ETH', '2D', fc['grade']; entry = M['ex_entry']
        mi = M['ex_misses']
    elif kind == 'open':
        o = next(x for x in feed['open_signals'] if x['signal_id'] == sel); fc = o['card']
        asset, tf, grade = o['chart'].split()[0], o['chart'].split()[1], o['grade']; entry = c['entry']
        mi = M['misses'][f'{asset}|{grade}']
    else:
        fc = next(x for x in feed['cards'] if x['signal_id'] == sel); asset, tf, grade = fc['asset'], fc['timeframe'], fc['grade']
        entry = M['forming'][sel]['price']; mi = M['misses'][f'{asset}|{grade}']
    return c, fc, asset, tf, grade, entry, mi


def edge_text(c):
    e = c['edge']
    return 'Below the 70% bar from entry' if e == 0 else (f'{pct(e, 0)} before it rises 10%' if e is not None else 'Holds at every level')


def check_card_dom(loc, cd, sel, kind):
    c, fc, asset, tf, grade, entry, mi = expect_card(sel, kind)
    chk(loc, 'where', cd['where'], f"{asset} · {tf} CHART" + (' · EXAMPLE' if kind == 'example' else ''))
    chk(loc, 'state', cd['state'], {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind])
    if kind == 'forming':
        f = M['forming'][sel]
        exp = f"Low {dl(c['meta']['low_day'])} · confirms {dl(f['confirms'])}" + (f" if it closes above {money(rh(f['kill'], 2))}" if f['kill'] is not None else '')
        chk(loc, 'head line (low day, confirms, must close above)', cd['head'][0], exp)
        note = cd['head'][1] if len(cd['head']) > 1 else ''
        if grade != 'A+':
            best = max((cards[x]['reach10'] for x in M['forming']), default=None)
            lab = 'Best setup forming today.' if note.startswith('Best') else 'Setup forming.'
            if lab.startswith('Best'):
                chk(loc, '"Best setup forming today" is the highest rose-10% forming card', c['reach10'], best, 'label: "best" card is not the highest')
            chk(loc, 'forming note', note, f"{lab} It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
        else:
            chk(loc, 'forming note', note, 'Not confirmed yet. It can still vanish before it confirms.')
    elif kind == 'open':
        exp = (f"Confirmed {dl(c['entry_date'])} · entry close {money(rh(entry, 2))} · day {c['days']} of 60 · best so far {pct(c['sofar_best'])} · worst {pct(c['sofar_worst'])}")
        chk(loc, 'head line (entry date, entry close, day, best, worst)', cd['head'][0], exp)
    else:
        chk(loc, 'head line', cd['head'][0], f"Example: confirmed {dl('2024-09-22')} · entry close {money(rh(entry, 2))}")
    chk(loc, 'big number: rose 10% within 60 days', cd['big'], f"{c['reach10']}%")
    chk(loc, 'line under: did it without ever falling 25.3%', cd['odds'][2], f"{c['surv10']}% did it without ever falling 25.3%")
    chk(loc, 'sample line (text and n)', cd['odds'][3], f"from {fc['sample']} · every figure covers the 60 days after entry")
    chk(loc, 'sample text states my n', f" {c['n']} " in f" {fc['sample']} ", True)
    st = dict(cd['stats'])
    chk(loc, 'Typical high', st.get('Typical high'), pct(c['best']), 'double rounding')
    chk(loc, 'Typical drop from entry', st.get('Typical drop from entry'), pct(c['deep']), 'double rounding')
    chk(loc, 'Edge gone below', st.get('Edge gone below'), edge_text(c))
    chk(loc, 'If it misses: went above entry', st.get('If it misses: went above entry'), f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}")
    if kind == 'forming' and grade != 'A+':
        chk(loc, 'misses pool line', ' '.join(cd['pool']), f"all {mi['signals']} {asset} signals of this grade")
    tiles = dict(cd['tiles'])
    chk(loc, 'tile Dip before the high, from entry', tiles.get('Dip before the high, from entry'), pct(c['dip']))
    chk(loc, 'tile High lands around', tiles.get('High lands around'), f"Day {c['tHigh']}")
    chk(loc, 'tile Reached +20% (with n)', tiles.get(f"Reached +20% within 60 days · n {c['n']}"), f"{c['reach20']}%")
    chk(loc, 'tile Touched -30% (with n)', tiles.get(f"Touched {MINUS}30% within 60 days · n {c['n']}"), f"{c['touched30']}%")
    chk(loc, 'tile Typical high', tiles.get('Typical high'), pct(c['best']))
    chk(loc, 'tile Deepest dip lands around', tiles.get('Deepest dip lands around'), f"Day {c['tLow']}")
    sfx = f" · {mi['misses']} misses of all {mi['signals']} {asset} {grade}"
    chk(loc, 'tile Typical worst drop, misses (with counts)', tiles.get('Typical worst drop, misses' + sfx), pct(mi['median_worst_drop_pct']))
    chk(loc, 'tile Typical change by day 60, misses (with counts)', tiles.get('Typical change by day 60, misses' + sfx), pct(mi['median_day60_pct']))
    chk(loc, 'tile count', len(cd['tiles']), 8)
    lad = c['lad']
    exp_rows = [(f"From entry n {lad['0']['n']}", lad['0'])] + [(f"Falls {t}% first n {lad[str(t)]['n']}", lad[str(t)]) for t in (5, 10, 15, 20)]
    chk(loc, 'ladder title', cd['ladderLbl'], 'WHERE THE ODDS FADE · THIS SETUP')
    for (lab, L_), row in zip(exp_rows, cd['ladder']):
        chk(loc, f'ladder {lab}: label', row['label'], lab)
        chk(loc, f'ladder {lab}: share', row['value'], 'n/a' if L_['okr'] is None else f"{L_['okr']}%")
        chk(loc, f'ladder {lab}: below-70% mark (exact share)', row['gone'], L_['okx'] is not None and rh(L_['okx'], 6) < 70)
    chk(loc, 'ladder rows', len(cd['ladder']), 5)
    eras = [(f"Before 2022 n {c['nOld']}", c['sOld']), (f"Since 2022 n {c['nNew']}", c['sNew'])]
    for (lab, v), row in zip(eras, cd['eras']):
        chk(loc, f'era {lab}', f"{row['label']} = {row['value']}", f"{lab} = {'n/a' if v is None else v}%")
    chk(loc, 'era note (measure named)', ' '.join(cd['erasNote']), 'Share that rose 10% and never fell 25.3%.')
    chk(loc, 'lead trader marker (feed unreadable)', cd['marker'], 'Lead trader: unavailable')
    return c, fc, asset, tf, grade, entry, mi


# ---------------- chart helpers
L_, R_, T_, B_ = 20, 960, 24, 480


def style_of(e, k):
    m = re.search(k + r':\s*([^;]+);', e['a'].get('style', ''))
    return m.group(1).strip() if m else e['a'].get(k)


def chart_check(loc, ch, sel, kind, happened=False):
    c, fc, asset, tf, grade, entry, mi = expect_card(sel, kind)
    if kind == 'example':
        ex = json.load(open(os.path.join(ROOT, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
        bars = ex['bars']; E = ex['entry_index']; ent = ex['entry_close']
    else:
        bars = [{'t': int(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])}
                for r in csv.DictReader(open(os.path.join(ROOT, 'datasets', f'candles_{asset.lower()}_{tf.lower()}.csv')))]
        E = len(bars) - 1
        ent = fc['price_now'] if kind == 'forming' else fc['entry_close']
    bdate = lambda b: dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date()
    opens = [bdate(b) for b in bars]
    if kind == 'open':
        E = next(i for i, d in enumerate(opens) if bucket_end(d, tf) == D.fromisoformat(c['entry_date']))
    # every candle the page has is the raw candle
    raw = {b[0]: b for b in S.raw[(asset, tf)]}
    badc = [str(d) for d, b in zip(opens, bars) if d not in raw or [raw[d][1], raw[d][2], raw[d][3], raw[d][4]] != [b['o'], b['h'], b['l'], b['c']]]
    chk(loc, 'chart candles = raw candles (o,h,l,c)', ','.join(badc), '', 'chart data differs from raw candles')
    svg = ch['svg']
    hl = {style_of(e, 'stroke'): e for e in svg if e['tag'] == 'line' and e['a'].get('stroke-width') in ('2', '2.5')}
    yE, y10 = float(hl['var(--soft)']['a']['y1']), float(hl['var(--text)']['a']['y1'])
    # Y = B - (p - lo)/(hi - lo)*(B - T): two known prices give lo and hi
    k = (yE - y10) / (ent * 1.1 - ent)          # pixels per dollar (positive)
    hi = ent + (yE - T_) / k; lo = ent - (B_ - yE) / k
    Y = lambda p: B_ - (p - lo) * k
    lv_high = ent * (1 + c['bestx'] / 100); lv_drop = ent * (1 + c['deepx'] / 100)
    shown = bars[:E + 1] if (kind == 'example' and not happened) else bars
    exp_lo = min(min(b['l'] for b in shown), lv_drop, ent * 0.8) * 0.95
    exp_hi = max(max(b['h'] for b in shown), lv_high) * 1.07
    chk(loc, 'price axis bottom (scaled on what is shown' + (', known at the alert)' if kind == 'example' and not happened else ')'), round(lo, 4), round(exp_lo, 4), 'axis scaling')
    chk(loc, 'price axis top', round(hi, 4), round(exp_hi, 4), 'axis scaling')
    chk(loc, 'Typical high line at its price', round(float(hl['var(--high)']['a']['y1']), 6), round(Y(lv_high), 6))
    chk(loc, 'Typical drop line at its price', round(float(hl['var(--drop)']['a']['y1']), 6), round(Y(lv_drop), 6))
    texts = [e['text'] for e in svg if e['tag'] == 'text']
    tagtxt = [e['text'] for e in svg if e['tag'] == 'text' and e['a'].get('fill') == '#07060F']
    chk(loc, 'price tags (typical high, +10%, entry, typical drop)', ' | '.join(tagtxt),
        ' | '.join(money(p) for p in (lv_high, ent * 1.1, ent, lv_drop)))
    chk(loc, 'Typical high label', f"Typical high {pct(c['best'])}" in texts, True)
    chk(loc, '+10% label', f"+10% · {c['reach10']}% of past signals got here" in texts, True)
    chk(loc, 'Typical drop label', f"Typical drop {pct(c['deep'])}" in texts, True)
    e_ = c['edge']
    if e_:
        chk(loc, 'edge line label', next((t for t in texts if t.startswith('Edge gone')), None), f"Edge gone below {money(ent * (1 + e_ / 100))} ({pct(e_, 0)}, before +10%)")
        chk(loc, 'edge line at its price', round(float(hl['var(--fade-2)']['a']['y1']), 6), round(Y(ent * (1 + e_ / 100)), 6))
    else:
        chk(loc, 'no edge line', any(t.startswith('Edge gone') for t in texts), False)
    # candles drawn: wick lines
    wicks = [e for e in svg if e['tag'] == 'line' and e['a'].get('stroke-width') == '1.5' and not (e['a']['y1'] == '24' and e['a']['y2'] == '480')]
    nc = len(wicks)
    chk(loc, 'candles drawn', nc, (E + 1) if (kind == 'example' and not happened) else len(bars), 'outcome candles at the alert')
    xs = [float(w['a']['x1']) for w in wicks]
    slot = (xs[1] - xs[0]) if len(xs) > 1 else None
    bad = []
    for j, w in enumerate(wicks):
        b = bars[j]
        if abs(float(w['a']['y1']) - Y(b['h'])) > 1e-6 or abs(float(w['a']['y2']) - Y(b['l'])) > 1e-6:
            bad.append(str(opens[j]))
    chk(loc, 'each candle wick at its high/low', ','.join(bad), '')
    # slots -> dates
    ext = list(opens)
    while len(ext) < 200:
        ext.append(next_open(ext[-1], tf))
    idx = lambda x: round((x - L_) / slot - 0.5)
    slot_of_day = lambda d: max(i for i, o in enumerate(ext) if o <= d)
    entry_day = D.fromisoformat(c['meta']['confirms_on']) if kind != 'example' else D(2024, 9, 22)
    vl = []
    for j, e in enumerate(svg):
        if e['tag'] == 'line' and e['a'].get('y1') == '24' and e['a'].get('y2') == '480':
            vl.append((svg[j + 1]['text'], idx(float(e['a']['x1']))))
    vd = dict(vl)
    if kind == 'forming':
        chk(loc, '"Today" line on the open bar', vd.get('Today'), len(bars) - 1)
        conf_lbl = next((t for t in vd if t.startswith('Confirms')), None)
        chk(loc, 'confirms line label', conf_lbl, f"Confirms {dl(entry_day)} · entry, day 0")
        chk(loc, 'confirms line on the bar closing on the confirmation date', vd.get(conf_lbl), slot_of_day(entry_day))
        chk(loc, 'confirmation bar closes on confirms_on', str(bucket_end(ext[slot_of_day(entry_day)], tf)), str(entry_day))
    else:
        chk(loc, '"Entry" line on the bar closing on the entry date', vd.get('Entry'), E)
        chk(loc, 'entry bar closes on the entry date', str(bucket_end(ext[E], tf)), str(entry_day))
    # price grid labels sit on their grid line and name its price
    badg = []
    for j, e in enumerate(svg):
        if e['tag'] == 'line' and e['a'].get('stroke') == '#1C1736':
            y = float(e['a']['y1']); p = lo + (B_ - y) / k
            nxt = svg[j + 1] if j + 1 < len(svg) else None
            if nxt and nxt['tag'] == 'text' and nxt['text'].startswith('$'):
                if nxt['text'] != '$' + f'{round(p):,}' or abs(float(nxt['a']['y']) - (y + 5)) > 1e-6:
                    badg.append(f"{nxt['text']}@{p:.2f}")
    chk(loc, 'price grid labels match their lines', ','.join(badg), '')
    # date ticks under the axis name the open date of the bar above them
    badt = []
    for e in svg:
        if e['tag'] == 'text' and e['a'].get('y') == str(B_ + 22):
            i = idx(float(e['a']['x'])); d = ext[i]
            if e['text'] != f'{d.day:02d} {MON[d.month - 1]}':
                badt.append(f"{e['text']}->{d}")
    chk(loc, 'date ticks = open date of the bar above', ','.join(badt), '')
    nS = round((R_ - L_) / slot)
    chk(loc, '"Day 60" line on the bar containing day 60', vd.get('Day 60'), min(nS - 1, slot_of_day(entry_day + TD(days=60))))
    hlab = f"High usually ~day {c['tHigh']}"
    chk(loc, 'high-day line label', hlab in vd, True)
    chk(loc, 'high-day line on the bar containing that day', vd.get(hlab), slot_of_day(entry_day + TD(days=c['tHigh'])))
    chk(loc, 'no pooled day-10 line on a card with its own ladder', any(t.startswith('Day 10') for t in vd), False)
    # zones start at the entry/confirmation bar
    zr = [e for e in svg if e['tag'] == 'rect' and e['a'].get('opacity') in ('0.07', '0.1')]
    x0 = L_ + slot * (slot_of_day(entry_day) if kind == 'forming' else E) + slot / 2
    chk(loc, 'shaded zones start at the entry bar', ','.join(f"{float(z['a']['x']):.6f}" for z in zr), ','.join(f'{x0:.6f}' for _ in zr))
    # ladder zones on the chart: from entry, falls 5/10/15 first
    zl = [e['text'] for e in svg if e['tag'] == 'text' and e['a'].get('font-weight') == '700' and e['a'].get('text-anchor') == 'middle' and e['a'].get('fill') != '#07060F']
    lad = c['lad']
    exp_z = [lad['0'], lad['5'], lad['10'], lad['15']]
    chk(loc, 'chart ladder zones (from entry, falls 5/10/15 first)', ' | '.join(zl[:4]), ' | '.join('n/a' if z['okr'] is None else f"{z['okr']}%" for z in exp_z))
    zrects = [e for e in svg if e['tag'] == 'rect' and e['a'].get('opacity') == '0.24']
    cols = [style_of(z, 'fill') for z in zrects]
    chk(loc, 'chart ladder zone colours (70% bar on exact share)', ','.join(cols),
        ','.join('var(--closed)' if z['okr'] is None else 'var(--high)' if rh(z['okx'], 6) >= 70 else 'var(--drop)' for z in exp_z))
    # low marker (forming only)
    if kind == 'forming':
        lowtxt = next((t for t in texts if t.startswith('Low ')), None)
        ld = D.fromisoformat(c['meta']['low_day']); lowb = S.day[asset][S.dpos[asset][ld]]
        chk(loc, 'low marker (day and price)', lowtxt, f"Low {dl(ld)} · {money(lowb[3])}")
    # side box
    sb = ch['sideBoxes'][0]; kv = dict(sb['kv'])
    chk(loc, 'side: big number', f"{c['reach10']}%" in sb['text'].split('\n'), True)
    chk(loc, 'side: n and surv10 line', f"rose 10% within 60 days, from {c['n']} past signals; {c['surv10']}% without ever falling 25.3%" in sb['text'], True)
    chk(loc, 'side: Typical high', kv.get('Typical high'), f"{pct(c['best'])} · {money(ent * (1 + c['bestx'] / 100))}")
    chk(loc, 'side: +10% target', kv.get('+10% target'), money(ent * 1.1))
    chk(loc, 'side: Reached +20%', kv.get('Reached +20% within 60 days'), f"{c['reach20']}%")
    chk(loc, 'side: Typical drop', kv.get('Typical drop'), f"{pct(c['deep'])} · {money(ent * (1 + c['deepx'] / 100))}")
    chk(loc, 'side: Edge gone below', kv.get('Edge gone below'), 'below the bar already' if e_ == 0 else 'holds at every level' if e_ is None else f"{money(ent * (1 + e_ / 100))} ({pct(e_, 0)})")
    if kind == 'open':
        kv2 = dict(ch['sideBoxes'][1]['kv'])
        chk(loc, 'side live box title', ch['sideBoxes'][1]['text'].split('\n')[0], f"LIVE: DAY {c['days']} OF 60")
        chk(loc, 'side: Best so far', kv2.get('Best so far'), pct(c['sofar_best']))
        chk(loc, 'side: Worst so far', kv2.get('Worst so far'), pct(c['sofar_worst']))
        chk(loc, 'side: Day 10', kv2.get('Day 10'), 'not yet' if c['day10'] is None else pct(c['day10']))
        chk(loc, 'title', ch['title'], f"{asset} · {tf} · LIVE SETUP, DAY {c['days']} OF 60")
        chk(loc, 'subtitle', ch['sub'], f"Confirmed {dl(c['entry_date'])} · entry close {money(ent)}. Zones use this setup's own card ({fc['sample']}). The shaded zones are the next 60 days, as the odds draw them.")
    elif kind == 'forming':
        chk(loc, 'title', ch['title'], f"{asset} · {tf} · " + ('SETUP FORMING' if grade == 'A+' else 'FORMING, NOT TOP GRADE'))
        chk(loc, 'subtitle', ch['sub'], f"Low {dl(c['meta']['low_day'])} · confirms {dl(entry_day)} · price levels drawn from today's price ({money(ent)}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them.")
        chk(loc, 'side: still forming note', ch['sideBoxes'][1]['text'], f"Still forming. It confirms only if it holds through {dl(entry_day)}, and it can vanish before then. " + ('' if grade == 'A+' else "It isn't top grade, so no alert goes out for it."), 'text')
    # cloud
    if kind == 'example':
        pth = M['ex_paths']; sub = f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {pth['n']}"
    else:
        pth = M['paths'][asset]; sub = f"Every past {asset} top-grade signal, n {pth['n']}"
    chk(loc, 'cloud subtitle (sample, n)', ch['cloudSub'], sub)
    note = f"Day 60: median {pct(pth['med'][60])}, middle half {pct(pth['q25'][60])} to {pct(pth['q75'][60])}. Daily closes."
    chk(loc, 'cloud day-60 note', note in ch['cloudNote'], True)
    if grade != 'A+':
        chk(loc, 'cloud says it is top-grade only', "Top-grade signals only; the selected setup isn't top grade." in ch['cloudNote'], True)
    poly = [e for e in ch['cloud'] if e['tag'] == 'polyline']
    cy = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * (230 - 12)
    pts = [tuple(map(float, p.split(','))) for p in poly[0]['a']['points'].split()]
    badp = [d for d, (x, y) in enumerate(pts) if abs(y - cy(pth['med'][d])) > 1e-6 or abs(x - (20 + 940 * d / 60)) > 1e-6]
    chk(loc, 'cloud median path points', ','.join(map(str, badp)), '')
    return bars, E, ent, Y, svg, texts


# ---------------- run every view
for sel, v in P['views'].items():
    kind = 'example' if sel == 'example' else 'open' if sel in {o['signal_id'] for o in open_ap} else 'forming'
    sid = 'ETH-2D-2024-09-22' if kind == 'example' else sel
    loc = f'page card {sid}' + (' (example)' if kind == 'example' else '')
    check_card_dom(loc, v['now']['card'], sid, kind)
    chart_check(f'page chart {sid} at the alert', v['chart_alert'], sid, kind)
    if kind == 'example':
        chk('page chart example', 'toggle shown', v['chart_alert']['toggleHidden'], False)
        chk('page chart example', '"At the alert" draws nothing after entry', any(t.startswith('This one') for t in (e['text'] for e in v['chart_alert']['svg'] if e['tag'] == 'text')), False)
        chart_check(f'page chart {sid} at the alert (after toggling back)', v['chart_alert_again'], sid, kind)
        bars, E, ent, Y, svg, texts = chart_check(f'page chart {sid} what happened', v['chart_happened'], sid, kind, happened=True)
        # what this one did, from daily candles
        a = 'ETH'; d0 = D(2024, 9, 22)
        w = S.window(a, d0)
        mh = max(b[2] for k, b in w); kh = next(k for k, b in w if b[2] == mh)
        ml = min(b[3] for k, b in w); kl = next(k for k, b in w if b[3] == ml)
        c10 = next(b[4] for k, b in w if k == 10); c60 = next(b[4] for k, b in w if k == 60)
        e = M['ex_entry']
        chk('page chart example', 'example entry close = raw', ent, rh(e, 2))
        side = dict(v['chart_happened']['sideBoxes'][1]['kv'])
        rng = lambda k: f"days {k - 1 if k % 2 == 0 else k}–{k if k % 2 == 0 else k + 1}"
        chk('page chart example what happened', 'Reached +10% / +20%', side.get('Reached +10% / +20%'), f"{'Yes' if mh >= e * 1.1 else 'No'} / {'Yes' if mh >= e * 1.2 else 'No'}")
        chk('page chart example what happened', 'Best price', side.get('Best price'), f"{pct((mh / e - 1) * 100)}, {rng(kh)}")
        chk('page chart example what happened', 'Deepest drop', side.get('Deepest drop'), f"{pct((ml / e - 1) * 100)}, {rng(kl)}")
        chk('page chart example what happened', 'Day 10 check', side.get('Day 10 check'), f"{'Red' if c10 < e else 'Green'}, {pct((c10 / e - 1) * 100)}")
        chk('page chart example what happened', 'Price on day 60', side.get('Price on day 60'), pct((c60 / e - 1) * 100))
        this = sorted(t for t in texts if t.startswith('This one'))
        exp = sorted([f"This one: {money(mh)} · {pct((mh / e - 1) * 100)} · {rng(kh)}", f"This one: {money(ml)} · {pct((ml / e - 1) * 100)} · {rng(kl)}"])
        chk('page chart example what happened', 'chart circles: best and deepest', ' | '.join(this), ' | '.join(exp))
        poly = [x for x in v['chart_happened']['cloud'] if x['tag'] == 'polyline']
        cy = lambda vv: 230 - (max(-40, min(100, vv)) + 40) / 140 * (230 - 12)
        pts = [tuple(map(float, p.split(','))) for p in poly[1]['a']['points'].split()]
        badp = []
        for x, y in pts[1:]:
            d = round((x - 20) / 940 * 60)
            cl = next(b[4] for k, b in w if k == d)
            if abs(y - cy((cl / e - 1) * 100)) > 1e-6: badp.append(d)
        chk('page chart example what happened', 'cloud "this signal" path = daily closes', ','.join(map(str, badp)), '')
        chk('page chart example what happened', 'cloud "this signal" path reaches day 60', round((pts[-1][0] - 20) / 940 * 60), 60)
    else:
        chk(f'page chart {sid}', 'no toggle on a live/forming chart', v['chart_alert']['toggleHidden'], True)
# the switch shows the example card
check_card_dom('page card ETH-2D-2024-09-22 (example, via switch)', P['switch_on']['card'], 'ETH-2D-2024-09-22', 'example')

# ---------------- previous signals column
open_status = {o['signal_id']: cards[o['signal_id']]['status'] for o in open_ap}
pi = P['initial']['prevIntact']; pc = P['initial']['prevClosed']
intact = [s for s, st in open_status.items() if st == 'intact']
lost = [s for s, st in open_status.items() if st == 'lost']
if not intact:
    chk('page previous signals', 'edge intact group', pi[0]['text'] if pi else '', 'No open top-grade setup with its edge intact.')
else:
    chk('page previous signals', 'edge intact group size', len([x for x in pi if 'mini' in x['cls']]), len(intact))
mini_open = [x for x in pi + pc if 'closed' not in x['cls'] and 'mini' in x['cls']]
for x, sid in zip(mini_open, intact + lost):
    c = cards[sid]
    exp = f"{sid[:3]} {sid[4:6]}\nDay {c['days']} of 60 · best {pct(c['sofar_best'])} · worst {pct(c['sofar_worst'])}\n" + ('On track' if c['status'] == 'intact' else 'Edge lost')
    chk(f'page previous signals {sid}', 'mini (day, best, worst, badge)', x['text'], exp)
recent = sorted(led_ap, key=lambda r: r['entry'], reverse=True)[:5]
closed_minis = [x for x in pc if 'closed' in x['cls']]
chk('page previous signals', 'recent closed count', len(closed_minis), 5)
for x, r in zip(closed_minis, recent):
    m = r['m']
    badge = 'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed'
    exp = f"{r['chart']}\n{dl(r['entry'])} · best {pct(m['up'])} · worst {pct(m['dd'])}\n{badge}"
    chk(f"page previous signals {r['chart']} {r['entry']}", 'mini (date, best, worst, badge)', x['text'], exp)

# ---------------- past signals tab
for a, rec in P['record'].items():
    rows = [r for r in led_ap if a == 'all' or r['a'] == a]
    rows.sort(key=lambda r: r['entry'], reverse=True)
    loc = f'page past signals ({a})'
    chk(loc, 'count line', rec['count'], f"{len(rows)} signals · {sum(not r['m']['r10'] for r in rows)} missed +10%")
    chk(loc, 'row count', len(rec['rows']), len(rows))
    for got, r in zip(rec['rows'], rows):
        m = r['m']
        exp = [dl(r['entry']), r['chart'], money(r['s']['entry']), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
               pct(rh(m['up'], 6)), pct(rh(m['dd'], 6)), pct(rh(m['ret'], 6)), str(m['dpk'])]
        for h, g_, e_ in zip(rec['head'], got, exp):
            chk(f"{loc} {r['chart']} {r['entry']}", h, g_, e_)
            if h in ('Best', 'Deepest drop', 'Day 60'):
                full = {'Best': m['up'], 'Deepest drop': m['dd'], 'Day 60': m['ret']}[h]
                chk(f"{loc} {r['chart']} {r['entry']}", h + ' (full precision vs 6-place)', pct(full), e_, 'double rounding')
    for box in rec['sum']:
        asset = box['head'].split('\n')[0]
        g = M['grade'][f'{asset}|A+']; mi = M['misses'][f'{asset}|A+']
        chk(f'{loc} summary {asset}', 'head (signals)', box['head'], f"{asset}\n{g['n']} signals")
        kv = dict(box['kv'])
        chk(f'{loc} summary {asset}', 'Rose 10% in 60 days', kv.get('Rose 10% in 60 days'), f"{g['reach10']}%")
        chk(f'{loc} summary {asset}', 'Reached +20% in 60 days', kv.get('Reached +20% in 60 days'), f"{g['reach20']}%")
        chk(f'{loc} summary {asset}', 'Rose 10%, never fell 25.3%', kv.get('Rose 10%, never fell 25.3%'), f"{g['surv10']}%")
        chk(f'{loc} summary {asset}', 'Median deepest dip', kv.get('Median deepest dip'), pct(g['medDip']))
        chk(f'{loc} summary {asset}', 'Misses: median best price', kv.get('Misses: median best price'), pct(mi['median_peak_pct']))
    chk(loc, 'summary boxes', ','.join(b['head'].split('\n')[0] for b in rec['sum']), 'ETH,BTC' if a == 'all' else a)

K.dump(f'_{NAME}_page_checks.json')
bad = [r for r in K.ROWS if r['ok'] == 'no']
print(NAME, 'page checks', len(K.ROWS), 'bad', len(bad))
for r in bad:
    print(r)
