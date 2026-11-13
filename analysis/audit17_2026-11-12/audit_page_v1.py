"""Audit 17, check 8: the member page, rendered with Playwright, every text node and the chart geometry
compared with values recomputed from the raw candles (audit_feed.Model).

usage: audit_page.py <state root> <now ISO> <state name> <out csv>
"""
import csv, datetime as dt, json, os, re, sys
from decimal import Decimal
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
from core import rnd
import audit_feed as AF
from playwright.sync_api import sync_playwright

MINUS = '−'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']


def dec(x, d):
    return format(Decimal(x.numerator) / Decimal(x.denominator), f',.{d}f')


def fx(v, d=1):
    if v is None: return 'n/a'
    r = rnd(v, d)
    if r == 0: return dec(F(0), d)
    return (MINUS if r < 0 else '') + dec(abs(r), d).replace(',', '')


def pct(v, d=1, sign=True):
    if v is None: return 'n/a'
    return ('+' if sign and rnd(v, d) > 0 else '') + fx(v, d) + '%'


def money(v):
    return 'n/a' if v is None else '$' + dec(rnd(v, 2), 2)


def date_long(d):
    if isinstance(d, str): d = dt.date.fromisoformat(d)
    return f'{d.day} {MON[d.month - 1]} {d.year}'


def date_axis(d):
    return f'{d.day:02d} {MON[d.month - 1]}'


def px_at(entry, p):
    """entry (to the cent) x (1 + p/100), exact, to the cent, half away from zero."""
    return None if entry is None or p is None else rnd(rnd(entry, 2) * (1 + F(p) / 100), 2)


def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()


JS_TEXT = """(sel) => { const root = document.querySelector(sel); if (!root) return null; const out = [];
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { let p = n.parentElement, hid = false; while (p && p !== root.parentElement) { if (p.hidden) hid = true; p = p.parentElement; }
    const t = n.textContent.replace(/\\s+/g, ' ').trim(); if (t && !hid) out.push(t); } return out; }"""
JS_SVG = """(sel) => Array.from(document.querySelector(sel).children).map((e) => { const a = {}; for (const x of e.attributes) if (x.name !== 'style') a[x.name] = x.value;
  return { tag: e.tagName, a, fill: e.style.getPropertyValue('fill') || a.fill || '', stroke: a.stroke || e.style.getPropertyValue('stroke') || '', text: e.textContent }; })"""
JS_BARS = """(sel) => Array.from(document.querySelectorAll(sel + ' .bar')).map((e) => ({ gone: e.querySelector('.f').classList.contains('gone'), width: e.querySelector('.f').style.width }))"""


class Site:
    def __init__(self, root, feed_obj=None, ledger='__file__', candles=True, example=True, clock=None, feed_status=200):
        self.root = root
        self.page_html = open(os.path.join(root, 'docs/artifacts/member-site/index.html'), encoding='utf-8').read()
        self.doc = '<!doctype html><html><head><meta charset=utf-8></head><body>' + self.page_html + '</body></html>'
        self.feed_bytes = open(os.path.join(root, 'feed/ctzb_feed.json'), 'rb').read() if feed_obj is None else json.dumps(feed_obj).encode()
        self.feed_status = feed_status
        self.ledger = open(os.path.join(root, 'datasets/ledger.csv')).read() if ledger == '__file__' else ledger
        self.candles = candles; self.example = example
        self.clock = clock
        self.errors = []; self.requests = []

    def candle_json(self, a, tf):
        p = os.path.join(self.root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        if not os.path.exists(p): return None
        rows = list(csv.DictReader(open(p)))
        return '{"chart":"%s %s","bars":[%s]}' % (a, tf, ','.join('{"t":%s,"o":%s,"h":%s,"l":%s,"c":%s}' % (r['time'], r['open'], r['high'], r['low'], r['close']) for r in rows))

    def handler(self, route):
        u = route.request.url; self.requests.append(u)
        if u == 'http://site.test/' or u.startswith('http://site.test/#'):
            return route.fulfill(body=self.doc, content_type='text/html; charset=utf-8')
        if u.endswith('data/ctzb_feed.json'):
            return route.fulfill(status=self.feed_status, body=self.feed_bytes if self.feed_status == 200 else b'x', content_type='application/json')
        if u.endswith('data/ledger.csv'):
            return route.fulfill(body=self.ledger, content_type='text/csv') if self.ledger is not None else route.fulfill(status=404, body='x')
        m = re.search(r'data/candles/(ETH|BTC)_(1D|2D|3D|5D|8D)\.json$', u)
        if m:
            ok = self.candles if isinstance(self.candles, bool) else (f'{m.group(1)} {m.group(2)}' in self.candles)
            c = self.candle_json(m.group(1), m.group(2)) if ok else None
            return route.fulfill(body=c, content_type='application/json') if c else route.fulfill(status=404, body='x')
        if u.endswith('data/example_ETH-2D-2024-09-22.json'):
            if not self.example: return route.fulfill(status=404, body='x')
            return route.fulfill(body=open(os.path.join(self.root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')).read(), content_type='application/json')
        if 'font' in u: return route.abort()
        return route.fulfill(status=404, body='x')

    def open(self, pw, view='now'):
        self.browser = pw.chromium.launch()
        self.pg = self.browser.new_page(viewport={'width': 1440, 'height': 900})
        self.pg.on('pageerror', lambda e: self.errors.append(str(e)))
        self.pg.on('console', lambda m: self.errors.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        self.pg.route('**/*', self.handler)
        if self.clock is not None:
            self.pg.clock.install(time=self.clock)
        self.pg.goto('http://site.test/#' + view); self.pg.wait_for_timeout(700)
        return self.pg

    def texts(self, sel): return self.pg.evaluate(JS_TEXT, sel)
    def svg(self, sel): return self.pg.evaluate(JS_SVG, sel)
    def close(self): self.browser.close()


# ---------------------------------------------------------------- my view models
def vm_common(st, basis, asset, tf, grade):
    return dict(asset=asset, tf=tf, chart=f'{asset} {tf}', grade=grade, top=grade == 'A+', n=st['n'], sample=basis, reach10=st['reach10'], surv10=st['surv10'],
                reach20=st['reach20'], touched30=st['touched30'], high=st['best_exact'], drop=st['dip_exact'], dipb=st['dipb_exact'],
                highDay=st['thigh'], lowDay=st['tlow'], eras=[('Before 2022', st['nOld'], st['survOld']), ('Since 2022', st['nNew'], st['survNew'])],
                l0=st['l0'], lad=st['lad'], edge=st['edge'])


def models(M):
    feed = M.feed; out = {}
    for c in feed['cards']:
        x = M.cards.get(c['signal_id'])
        if not x: continue
        f = x['f']; v = vm_common(x['st'], x['basis'], f['a'], f['tf'], c['grade'])
        kill = C.floor_cent(F(repr(f['kill_exact']))) if f['kill_exact'] is not None else None
        v.update(kind='forming', sid=c['signal_id'], low_day=M.S.low_day(f['a'], f['tf'], f['tdate']), low_date=f['tdate'], confirms=f['d0'], kill=kill,
                 entry=rnd(f['price'], 2), need=f['need'])
        out[c['signal_id']] = v
    for o in feed['open_signals']:
        x = M.open.get(o['signal_id'])
        if not x: continue
        s = x['s']; v = vm_common(x['st'], x['basis'], s['a'], s['tf'], o['grade'])
        v.update(kind='open', sid=o['signal_id'], entry=rnd(s['entry'], 2), entry_date=s['d0'], days=(M.S.today - s['d0']).days, best=x['best'], worst=x['worst'],
                 status=x['status'], lvl=x['lvl'], d10=x['d10'], low_date=s['tdate'])
        out[o['signal_id']] = v
    if M.example:
        x = M.example; s = x['s']; v = vm_common(x['st'], x['basis'], 'ETH', '2D', s['grade'])
        v.update(kind='example', sid='example', entry=rnd(s['entry'], 2), entry_date=s['d0'], top=True)
        out['example'] = v
    return out


def miss_for(M, v):
    return M.miss.get('example') if v['kind'] == 'example' else M.miss.get((v['asset'], v['grade']))


def edge_text(v, bar=70):
    return f'Below the {bar}% bar from entry' if v['edge'] == 0 else (f"{pct(F(v['edge']), 0)} before it rises 10%" if v['edge'] is not None else 'Holds at every level')


def card_line(v):
    if v['kind'] == 'forming':
        return f"Low {date_long(v['low_day'])} · confirms {date_long(v['confirms'])}" + (f" if it closes above {money(v['kill'])}" if v['kill'] else '')
    if v['kind'] == 'open':
        return f"Confirmed {date_long(v['entry_date'])} · entry close {money(v['entry'])} · day {v['days']} of 60 · best so far {pct(v['best'])} · worst {pct(v['worst'])}"
    return f"Example: confirmed {date_long('2024-09-22')} · entry close {money(v['entry'])}"


def pool_words(v, mi):
    return f"{'the' if v['kind'] == 'example' else 'all'} {mi['signals']} {v['asset']} {'top-grade' if v['grade'] == 'A+' else 'same-grade'} signals{' known by then' if v['kind'] == 'example' else ''}"


def card_texts(M, v, best_sid):
    mi = miss_for(M, v); t = []
    t.append(f"{v['asset']} · {v['tf']} chart" + (' · example' if v['kind'] == 'example' else ''))
    t.append({'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[v['kind']])
    t.append(card_line(v))
    if v['kind'] == 'forming' and not v['top']:
        t.append(('Best setup forming today.' if best_sid == v['sid'] else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
    elif v['kind'] == 'forming':
        t.append('Not confirmed yet. It can still vanish before it confirms.')
    elif v['kind'] == 'open':
        lost = v['status'] == 'lost'
        t.append('Edge lost.' if lost else 'Rose 10%.' if v['status'] == 'rose10' else 'On track.')
        if lost:
            s = 'Its odds were below the bar from the entry.' if v['lvl'] == 0 else f"It fell to its edge level ({pct(F(v['lvl']), 0)}) before rising 10%."
        elif v['status'] == 'rose10':
            s = 'It has risen 10% from the entry close.' if v['lvl'] is None else f"It rose 10% before falling to its edge level ({pct(F(v['lvl']), 0)})."
        else:
            s = 'It has neither risen 10% nor lost its edge; its odds hold at every fall measured.' if v['lvl'] is None else f"It has not fallen to its edge level ({pct(F(v['lvl']), 0)}) or risen 10% yet."
        t.append(s + ' The odds below are as of the entry close, not from today.')
    t.append(f"{v['reach10']}%")
    t.append('rose 10% within 60 days' + (' · at the entry close, not from today' if v['kind'] == 'open' else ''))
    t.append(f"{v['surv10']}% did it without ever falling 25.3%")
    t.append(f"from {v['sample']} · every figure covers the 60 days after entry")
    t += ['Typical high', pct(v['high']), 'Typical drop from entry', pct(v['drop']), 'Edge gone below', edge_text(v), 'If it misses: went above entry']
    t.append('n/a' if not mi else 'none missed' if not mi['misses'] else f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak'])}")
    if mi and mi['signals']: t.append('of ' + pool_words(v, mi))
    t.append('Lead trader: unavailable')
    t.append('The detail')
    t += ['Dip before the high, from entry', pct(v['dipb']), 'High lands around', f"Day {v['highDay']}",
          f"Reached +20% within 60 days · n {v['n']}", f"{v['reach20']}%", f"Touched {MINUS}30% within 60 days · n {v['n']}", f"{v['touched30']}%",
          'Typical high', pct(v['high']), 'Deepest dip lands around', f"Day {v['lowDay']}"]
    tail = f" · {mi['misses']} misses of {pool_words(v, mi)}" if mi and mi['signals'] else ''
    t += ['Typical worst drop, misses' + tail, pct(mi['median_worst']) if mi else 'n/a', 'Typical change by day 60, misses' + tail, pct(mi['median_d60']) if mi else 'n/a']
    t.append('Where the odds fade · this setup')
    t += ['From entry', f"n {v['n']}", f"{v['l0'][1]}%"]
    for th, hit, okp, liqp, ex in v['lad']:
        t += [f'Falls {th}% first', f'n {hit}', f'{okp}%' if okp is not None else 'n/a']
    t.append("Share of this setup's past signals that, after first falling that far, still rose 10% before ever falling 25.3%. Below 70% the edge is gone. Small samples: read the n.")
    t.append('By era')
    for lab, n, sv in v['eras']:
        t += [lab, f'n {n}', f'{sv}%' if sv is not None else 'n/a']
    t += ['Share that rose 10% and never fell 25.3%.', 'Open on the chart →',
          "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record. Past results don't guarantee future results."]
    return t


def ladder_bars(v):
    out = [dict(gone=v['l0'][3] is not None and v['l0'][3] < 70, width=f"{v['l0'][1]}%")]
    for th, hit, okp, liqp, ex in v['lad']:
        out.append(dict(gone=ex is not None and ex < 70, width=f"{okp if okp is not None else 0}%"))
    return out


def cmp_list(L, loc, label, got, exp):
    """One comparison per text node; a length mismatch is reported once, then aligned pairwise."""
    if got is None: got = []
    if len(got) != len(exp):
        L.chk(loc, f'{label}: number of text items', len(got), len(exp), 'page text differs in structure')
    for i in range(max(len(got), len(exp))):
        g = got[i] if i < len(got) else None; e = exp[i] if i < len(exp) else None
        L.rows.append([L.state, loc, f'{label} [{i}]', '' if g is None else g, '' if e is None else e, 'ok' if g == e else 'DISAGREE', '' if g == e else 'page text'])


def near(a, b, tol=0.02):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


# ---------------------------------------------------------------- the chart
def chart_check(L, loc, site, M, v, mode='alert'):
    S = M.S; a, tf = v['asset'], v['tf']
    svg = site.svg('#chartSvg')
    lines = [e for e in svg if e['tag'] == 'line']; texts = [e for e in svg if e['tag'] == 'text']; rects = [e for e in svg if e['tag'] == 'rect']
    raw = C.Chart(os.path.join(M.root, 'data', f'{a}_{tf}.csv'), clamp=False)
    if v['kind'] == 'example':
        ex = json.load(open(os.path.join(M.root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
        i0 = raw.pos[C.utc_date(ex['bars'][0]['t'])]; idx = list(range(i0, i0 + len(ex['bars'])))
    else:
        idx = list(range(raw.n - 70, raw.n))
    opens = [raw.d[i] for i in idx]
    d0 = v['confirms'] if v['kind'] == 'forming' else v['entry_date']
    if v['kind'] != 'example':
        while opens[-1] <= d0 + dt.timedelta(days=61): opens.append(C.next_open(opens[-1], tf))
    nS = len(opens); Lx, Rx, T, B = 20.0, 960.0, 24.0, 480.0
    slot = (Rx - Lx) / nS; X = lambda i: Lx + slot * i + slot / 2
    slot_of = lambda day: max(i for i, o in enumerate(opens) if o <= day) if day >= opens[0] else 0
    E = len(idx) - 1 if v['kind'] == 'forming' else next(i for i, k in enumerate(idx) if C.next_open(raw.d[k], tf) - dt.timedelta(days=1) == d0)
    Aslot = slot_of(d0) if v['kind'] == 'forming' else E
    entry = v['entry']
    lv = dict(high=px_at(entry, v['high']), t10=px_at(entry, 10), drop=px_at(entry, v['drop']), edge=px_at(entry, v['edge']) if v['edge'] else None)
    happened = mode == 'happened'
    shown = idx[:E + 1] if (v['kind'] == 'example' and not happened) else idx
    lo = float(min(min(raw.l[k] for k in shown), lv['drop'], entry * F(8, 10))) * 0.95
    hi = float(max(max(raw.h[k] for k in shown), lv['high'])) * 1.07
    Y = lambda p: B - (float(p) - lo) / (hi - lo) * (B - T)
    k = lambda label, shown_, mine, cause='chart geometry': L.chk(loc, label, shown_, mine, cause)
    # candles: one wick line per drawn bar, at its slot, spanning its high and low
    wick = [e for e in lines if e['a'].get('stroke-width') == '1.5' and e['a']['x1'] == e['a']['x2'] and float(e['a']['y1']) != T]
    drawn = idx if v['kind'] != 'example' or happened else idx[:E + 1]
    k('candles drawn (count; "At the alert" stops at the entry bar)', len(wick), len(drawn))
    badc = [str(raw.d[kk]) for e, (i, kk) in zip(wick, enumerate(drawn)) if not (near(e['a']['x1'], X(i)) and near(e['a']['y1'], Y(raw.h[kk])) and near(e['a']['y2'], Y(raw.l[kk])))]
    k('every candle sits on its own date slot with its own high and low (price axis scaled from what is shown)', ' '.join(badc[:4]), '')
    # vertical lines by label
    vl = {}
    for i, e in enumerate(svg):
        if e['tag'] == 'text' and i and svg[i - 1]['tag'] == 'line' and svg[i - 1]['a']['x1'] == svg[i - 1]['a']['x2'] and float(svg[i - 1]['a']['y1']) == T and float(svg[i - 1]['a']['y2']) == B:
            vl[e['text']] = float(svg[i - 1]['a']['x1'])
    exp_v = {}
    exp_v['Today' if v['kind'] == 'forming' else 'Entry'] = X(E)
    exp_v[f"High usually ~day {v['highDay']}"] = X(slot_of(d0 + dt.timedelta(days=int(v['highDay']))))
    exp_v['Day 60'] = X(min(nS - 1, slot_of(d0 + dt.timedelta(days=60))))
    if v['kind'] == 'forming' and Aslot > E:
        exp_v[f"Confirms {date_long(v['confirms'])} · entry, day 0"] = X(Aslot)
    k('vertical lines (labels)', ' | '.join(sorted(vl)), ' | '.join(sorted(exp_v)), 'chart labels')
    for lab, x in exp_v.items():
        k(f'line "{lab}" sits on the bar containing that date', round(vl.get(lab, -1), 2), round(x, 2))
    # the bar under each line really contains the date (my bar rule)
    ent_bar = opens[E if v['kind'] != 'forming' else Aslot]
    k('entry / confirmation bar closes on the entry date', str(C.next_open(ent_bar, tf) - dt.timedelta(days=1)), str(d0))
    d60 = opens[min(nS - 1, slot_of(d0 + dt.timedelta(days=60)))]
    k('Day 60 bar contains entry + 60 days', d60 <= d0 + dt.timedelta(days=60) < C.next_open(d60, tf), True)
    # horizontal levels (x from the entry slot to day 60)
    xE, x60 = X(Aslot), X(min(nS - 1, slot_of(d0 + dt.timedelta(days=60))))
    hl = [e for e in lines if e['a'].get('stroke-width') == '2' and near(e['a']['x1'], xE) and near(e['a']['x2'], x60)]
    k('level lines: typical high, +10%, entry, typical drop (y positions)', ' '.join(f"{float(e['a']['y1']):.2f}" for e in hl),
      ' '.join(f'{Y(p):.2f}' for p in (lv['high'], lv['t10'], entry, lv['drop'])))
    # zones
    z = [e for e in rects if e['a'].get('opacity') in ('0.07', '0.1')]
    k('high zone (entry slot to day 60, entry to typical high)', ' '.join(f"{float(z[0]['a'][q]):.2f}" for q in ('x', 'y', 'width', 'height')) if len(z) > 0 else '',
      f'{xE:.2f} {Y(lv["high"]):.2f} {x60 - xE:.2f} {Y(entry) - Y(lv["high"]):.2f}')
    k('drop zone (entry slot to day 60, entry to typical drop)', ' '.join(f"{float(z[1]['a'][q]):.2f}" for q in ('x', 'y', 'width', 'height')) if len(z) > 1 else '',
      f'{xE:.2f} {Y(entry):.2f} {x60 - xE:.2f} {Y(lv["drop"]) - Y(entry):.2f}')
    # price tags
    tags = [e['text'] for e in texts if e['a'].get('fill') == '#07060F']
    exp_tags = [money(p) for p in sorted((lv['high'], lv['t10'], entry, lv['drop']), reverse=True)]
    k('price tags (typical high, +10% level, entry, typical drop)', ' '.join(tags), ' '.join(exp_tags), 'chart prices')
    # ladder bands
    bands = [e for e in rects if e['a'].get('opacity') == '0.24']
    steps = [(0, -5, v['l0'][1], v['l0'][3], v['n'])] + [(-th, -(v['lad'][i + 1][0] if i + 1 < len(v['lad']) else th + 5), okp, ex, hit) for i, (th, hit, okp, liqp, ex) in enumerate(v['lad'][:3])]
    k('ladder bands drawn', len(bands), len(steps))
    btxt = [e['text'] for e in texts if re.fullmatch(r'(\d+% · n \d+|n/a)', e['text'])]
    k('ladder band labels (share · n)', ' | '.join(btxt), ' | '.join('n/a' if s[2] is None else f'{s[2]}% · n {s[4]}' for s in steps), 'chart ladder')
    for e, s in zip(bands, steps):
        y1 = Y(entry * (1 + F(s[0], 100))); y2 = min(B, Y(entry * (1 + F(s[1], 100))))
        col = 'var(--closed)' if s[2] is None else 'var(--high)' if s[3] >= 70 else 'var(--drop)'
        k(f'ladder band {s[0]}% to {s[1]}%: position and colour (exact share vs 70)', f"{float(e['a']['x']):.2f} {float(e['a']['y']):.2f} {float(e['a']['height']):.2f} {e['fill']}", f'{xE:.2f} {y1:.2f} {y2 - y1:.2f} {col}')
    # edge line
    el = [e for e in lines if e['a'].get('stroke-width') == '2.5']
    k('edge line drawn only when the edge is a fall level', len(el), 1 if lv['edge'] else 0)
    if lv['edge'] and el:
        k('edge line y (entry x (1 + edge))', round(float(el[0]['a']['y1']), 2), round(Y(lv['edge']), 2))
        et = [e['text'] for e in texts if e['text'].startswith('Edge gone below')]
        k('edge label', et[0] if et else '', f"Edge gone below {money(lv['edge'])} ({pct(F(v['edge']), 0)}, before +10%)", 'chart prices')
    # level labels
    lab = [e['text'] for e in texts if e['text'].startswith(('Typical high', '+10% ·', 'Typical drop'))]
    k('level labels', ' | '.join(lab), ' | '.join([f"Typical high {pct(v['high'])}", f"+10% · {v['reach10']}% of past signals got here", f"Typical drop {pct(v['drop'])}"]), 'chart labels')
    # the low marker (forming / live) or the outcome (What happened)
    lowt = [e['text'] for e in texts if e['text'].startswith('Low ')]
    if v['kind'] in ('forming', 'open'):
        ti = raw.pos.get(v['low_date']); in_view = ti is not None and ti in idx
        want = f"Low {date_long(v['low_day'])} · {money(raw.l[ti])}" if in_view and v['kind'] == 'forming' else ''
        k('low marker label (the day the low printed, its price)', lowt[0] if lowt else '', want, 'chart labels')
        circ = [e for e in svg if e['tag'] == 'circle']
        if in_view and circ and v['kind'] == 'forming':
            k('low marker sits on the trough bar at its low', f"{float(circ[0]['a']['cx']):.2f} {float(circ[0]['a']['cy']):.2f}", f'{X(idx.index(ti)):.2f} {Y(raw.l[ti]):.2f}')
    this = [e['text'] for e in texts if e['text'].startswith('This one:')]
    if v['kind'] == 'example' and happened:
        s = M.example['s']; m = s['m']; d = S.day['ETH']
        mh = max(d.h[kk] for _, kk in m['w']); ml = min(d.l[kk] for _, kk in m['w'])
        def span(day):
            bo = C.bar_open_of(d0 + dt.timedelta(days=day), tf); a1 = (bo - d0).days; b1 = min(60, (C.next_open(bo, tf) - d0).days - 1)
            return f'days {a1}–{b1}' if b1 > a1 else f'day {a1}'
        want = [f"This one: {money(mh)} · {pct(m['up'])} · {span(m['dpk'])}", f"This one: {money(ml)} · {pct(m['dd'])} · {span(m['ddday'])}"]
        k('outcome labels (60-day high and low of this signal, from daily candles)', ' | '.join(this), ' | '.join(want), 'chart outcome')
    else:
        k('no outcome label at the alert', len(this), 0)
    # axis: grid labels are whole dollars at their own y; date labels are the slot dates
    grid = [e for e in texts if re.fullmatch(r'\$[\d,]+', e['text']) and e['a'].get('fill') != '#07060F']
    badg = [e['text'] for e in grid if not near(float(e['a']['y']) - 5, Y(F(e['text'][1:].replace(',', ''))), 0.6 * (B - T) / (hi - lo) + 0.02)]
    k('price-axis labels sit at their own price', ' '.join(badg), '')
    every = max(1, int(nS / 8 + 0.5))
    dl = [e['text'] for e in texts if e['a'].get('y') == str(int(B + 22)) or e['a'].get('y') == '502']
    k('date-axis labels (slot open dates)', ' '.join(dl), ' '.join(date_axis(opens[i]) for i in range(0, nS, every)), 'chart dates')
    return dict(entry=entry, lv=lv, E=E, opens=opens, idx=idx, raw=raw)


def cloud_check(L, loc, site, M, v, mode='alert'):
    key = 'example' if v['kind'] == 'example' else v['asset']
    pp = M.pp.get(key)
    svg = site.svg('#cloudSvg')
    X = lambda d: 20 + 940 * d / 60; Y = lambda p: 230 - (max(-40.0, min(100.0, float(p))) + 40) / 140 * 218
    pl = [e for e in svg if e['tag'] == 'polyline']
    pts = lambda s: [tuple(float(q) for q in p.split(',')) for p in s.split()]
    if pp is None:
        L.chk(loc, 'cloud: past paths present', 'drawn' if pl else 'none', 'none'); return
    got = pts(pl[0]['a']['points']) if pl else []
    bad = [d['day'] for d, g in zip(pp['days'], got) if not (near(g[0], X(d['day'])) and near(g[1], Y(d['median'])))]
    L.chk(loc, 'cloud: median path (61 points at my medians)', f'{len(got)} points, off: {bad[:5]}', '61 points, off: []', 'cloud')
    pg = [e for e in svg if e['tag'] == 'polygon']
    gp = pts(pg[0]['a']['points']) if pg else []
    expb = [(X(d['day']), Y(d['q75'])) for d in pp['days']] + [(X(d['day']), Y(d['q25'])) for d in reversed(pp['days'])]
    badb = [i for i, (g, e) in enumerate(zip(gp, expb)) if not (near(g[0], e[0]) and near(g[1], e[1]))]
    L.chk(loc, 'cloud: middle-half band (my quartiles)', f'{len(gp)} points, off: {badb[:5]}', '122 points, off: []', 'cloud')
    sub = site.texts('#cloudSub'); note = site.texts('#cloudNote')
    L.chk(loc, 'cloud caption (sample and n)', ' '.join(sub or []), f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {pp['n']}" if key == 'example' else f"Every past {v['asset']} top-grade signal, n {pp['n']}", 'cloud')
    last = pp['days'][-1]
    exp = ['━', 'median path', '█', 'middle half of outcomes' + ('' if mode == 'happened' else f". Day 60: median {pct(last['median'])}, middle half {pct(last['q25'])} to {pct(last['q75'])}. Daily closes.")]
    if mode == 'happened':
        exp += ['━', f"this signal. Day 60: median {pct(last['median'])}, middle half {pct(last['q25'])} to {pct(last['q75'])}. Daily closes."]
    if v['kind'] != 'example' and v['grade'] != 'A+':
        exp.append("Top-grade signals only; the selected setup isn't top grade.")
    cmp_list(L, loc, 'cloud note', note, exp)
    if mode == 'happened' and v['kind'] == 'example':
        s = M.example['s']; d = M.S.day['ETH']
        mine = [(X(0), Y(0))] + [(X(n), Y((d.c[kk] / s['entry'] - 1) * 100)) for n, kk in s['m']['w'] if n % 2 == 0]
        g2 = pts(pl[1]['a']['points']) if len(pl) > 1 else []
        badp = [i for i, (g, e) in enumerate(zip(g2, mine)) if not (near(g[0], e[0]) and near(g[1], e[1]))]
        L.chk(loc, "cloud: this signal's path (daily closes on days 2, 4 .. 60 vs entry)", f'{len(g2)} points, off: {badp[:5]}', '31 points, off: []', 'cloud')


def side_texts(M, v, mode='alert'):
    mi = None; t = ['What the card says']
    t.append(v['chart'] + (' · example' if v['kind'] == 'example' else '') + f" · from {v['sample']}" + (' · odds as of the entry close, not from today' if v['kind'] == 'open' else ''))
    t.append(f"{v['reach10']}%")
    t.append(f"rose 10% within 60 days, from {v['n']} past signals; {v['surv10']}% without ever falling 25.3%")
    e = v['entry']
    t += ['Typical high', f"{pct(v['high'])} · {money(px_at(e, v['high']))}", '+10% level', money(px_at(e, 10)), 'Reached +20% within 60 days', f"{v['reach20']}%",
          'Typical drop', f"{pct(v['drop'])} · {money(px_at(e, v['drop']))}", 'Edge gone below',
          'below the bar already' if v['edge'] == 0 else 'holds at every level' if v['edge'] is None else f"{money(px_at(e, v['edge']))} ({pct(F(v['edge']), 0)})"]
    if v['kind'] == 'forming':
        t.append("Prices use the latest price (today's bar is still open) as a stand-in for the entry.")
    t.append("Bands beside the entry: this setup's own ladder. From entry, then after first falling 5%, 10% and 15%: the share of its past signals that still rose 10% before ever falling 25.3%, with the number of signals.")
    if v['kind'] == 'open':
        t += [f"Live: day {v['days']} of 60", 'Best so far', pct(v['best']), 'Worst so far', pct(v['worst']), 'Day 10', 'not yet' if v['d10'] is None else pct(v['d10'])]
    elif v['kind'] == 'forming':
        t.append(f"Still forming. It confirms only if it holds through {date_long(v['confirms'])}, and it can vanish before then." + ('' if v['top'] else " It isn't top grade, so no alert goes out for it."))
    elif mode == 'happened':
        s = M.example['s']; m = s['m']; d = M.S.day['ETH']; en = s['entry']
        span = lambda day: f'days {day - 1 if day % 2 == 0 else day}–{day if day % 2 == 0 else day + 1}'
        c10 = next(d.c[kk] for n, kk in m['w'] if n == 10)
        t += ['What this one did', 'Reached +10% / +20%', f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}", 'Best price', f"{pct(m['up'])}, {span(m['dpk'])}",
              'Deepest drop', f"{pct(m['dd'])}, {span(m['ddday'])}", 'Day 10 check', f"{'Red' if c10 < en else 'Green'}, {pct((c10 / en - 1) * 100)}", 'Price on day 60', pct(m['ret'])]
    else:
        t += ['This is all a member had at the alert: the zones, the +10% level and the timing. Press', 'What happened', 'to see the real path.']
    t += ["The lead trader's feed is unavailable right now, so his entries and exits can't be shown.",
          "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record. Past results don't guarantee future results."]
    return t


def run(root, now, name, out):
    M, L = AF.run(root, now, name)
    n_feed = len(L.rows)
    V = models(M); feed = M.feed; S = M.S
    gen = dt.datetime.fromisoformat(str(feed['generated_at']).replace('Z', '+00:00'))
    site = Site(root, clock=gen + dt.timedelta(minutes=6))
    top_open = [o['signal_id'] for o in feed['open_signals'] if o['grade'] == 'A+']
    forming_sorted = [c['signal_id'] for c in sorted(feed['cards'], key=lambda c: -(c['rose10_within60d_pct'] if c['rose10_within60d_pct'] is not None else -1))]
    live_cards = [c['signal_id'] for c in feed['cards'] if c['grade'] == 'A+']
    forming_btns = live_cards + [x for x in forming_sorted if x not in live_cards]
    best_sid = (live_cards + forming_sorted + [None])[0]
    with sync_playwright() as pw:
        pg = site.open(pw, 'now')
        # ---------- banner, header, footer
        cmp_list(L, 'page banner', 'review banner', site.texts('#review'),
                 ['Review build.', 'Real pipeline data, scored', f"{date_long(S.today)} (feed {gen:%H:%M} UTC)",
                  ". Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run.", 'Show the example card'])
        cmp_list(L, 'page header', 'market filter', site.texts('#filterPill'), [f"Market filter: {'on' if S.gate(S.today) else 'off'}"])
        d1 = S.day['ETH']; last_closed = d1.d[-1] if d1.d[-1] < S.today else d1.d[-2]
        cmp_list(L, 'page footer', 'feed state (last closed daily candle from the data file)', site.texts('#feedState'),
                 [f'Daily candles closed through {date_long(last_closed)} · updated {gen:%H:%M} UTC · checks passed'])
        # ---------- picker
        exp = ['Live']
        if top_open:
            for sid in top_open:
                v = V[sid]; exp += [v['chart'], f"Day {v['days']}", f"best {pct(v['best'])} · worst {pct(v['worst'])}"]
        else: exp.append('No live top-grade setups right now.')
        exp.append('Forming')
        if forming_btns:
            for sid in forming_btns:
                v = V[sid]; exp += [v['chart'], f"{v['reach10']}%", f"rose 10% in 60 days · n {v['n']} · {'top grade' if v['top'] else 'not top grade'} · confirms {date_long(v['confirms'])}"]
        else: exp.append('Nothing forming today.')
        exp.append('Example: ETH 2D, Sep 2024')
        cmp_list(L, 'page picker', 'picker', site.texts('#picker'), exp)
        # ---------- previous signals column
        exp = ['Previous signals', 'updates each close', 'Edge intact']
        intact = [sid for sid in top_open if V[sid]['status'] != 'lost']; fading = [sid for sid in top_open if V[sid]['status'] == 'lost']
        if intact:
            for sid in intact:
                v = V[sid]; exp += [v['chart'], f"Day {v['days']} of 60 · best {pct(v['best'])} · worst {pct(v['worst'])}", 'Rose 10%' if v['status'] == 'rose10' else 'On track']
        else: exp.append('No open top-grade setup with its edge intact.')
        exp.append('Edge lost or closed')
        for sid in fading:
            v = V[sid]; exp += [v['chart'], f"Day {v['days']} of 60 · best {pct(v['best'])} · worst {pct(v['worst'])}", 'Edge lost']
        aplus = sorted([s for s in M.G if s['grade'] == 'A+'], key=lambda s: str(s['d0']), reverse=True)
        # the page sorts by entry date only (stable), ledger order within a date
        order = {(r['chart'], r['entry']): i for i, r in enumerate(M.led)}
        aplus = sorted([s for s in M.G if s['grade'] == 'A+'], key=lambda s: order[(s['chart'], str(s['d0']))])
        aplus = sorted(aplus, key=lambda s: str(s['d0']), reverse=True)
        for s in aplus[:5]:
            m = s['m']
            exp += [s['chart'], f"{date_long(s['d0'])} · best {pct(rnd(m['up'], 6))} · worst {pct(rnd(m['dd'], 6))}", 'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed']
        exp.append('See every past signal, misses included')
        cmp_list(L, 'page previous signals', 'previous signals column', site.texts('section.prev'), exp)
        # ---------- every picker button: the card, then the chart
        sels = [(sid, sid) for sid in top_open + forming_btns] + [('example', 'example')]
        for sid, key in sels:
            if key not in V: continue
            v = V[key]; loc = f'page card {sid}'
            pg.goto('http://site.test/#now'); pg.wait_for_timeout(150)
            pg.click(f'#picker [data-sel="{sid}"]'); pg.wait_for_timeout(250)
            cmp_list(L, loc, 'card', site.texts('#card'), card_texts(M, v, best_sid))
            L.chk(loc, 'ladder bars: width and the below-70% colour (exact share)', json.dumps(pg.evaluate(JS_BARS, '#ladder')), json.dumps(ladder_bars(v)), 'ladder colour')
            L.chk(loc, 'era bars: width', json.dumps([b['width'] for b in pg.evaluate(JS_BARS, '#eras')]), json.dumps([f"{sv if sv is not None else 0}%" for _, _, sv in v['eras']]))
            col = pg.evaluate("() => document.querySelector('#cardFrame').style.getPropertyValue('--c')")
            L.chk(loc, 'card frame colour (live unless below grade or edge lost)', col, 'var(--fade)' if (v['kind'] == 'forming' and not v['top']) or (v['kind'] == 'open' and v['status'] == 'lost') else 'var(--live)')
            # chart
            pg.click('#tab-chart'); pg.wait_for_timeout(450)
            loc = f'page chart {sid}'
            if v['kind'] == 'open':
                ttl = f"{v['chart'].replace(' ', ' · ')} · live setup, day {v['days']} of 60"
                sub = f"Confirmed {date_long(v['entry_date'])} · entry close {money(v['entry'])}. Zones use this setup's own card ({v['sample']})."
            elif v['kind'] == 'forming':
                ttl = f"{v['asset']} · {v['tf']} · {'setup forming' if v['top'] else 'forming, not top grade'}"
                sub = f"Low {date_long(v['low_day'])} · confirms {date_long(v['confirms'])} · price levels drawn from today's price ({money(v['entry'])}), since the entry price is the confirmation close; days count from the confirmation."
            else:
                ttl = 'ETH · 2-day · example: past confirmed setup'
                sub = f"Confirmed {date_long('2024-09-22')} · entry close {money(v['entry'])} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them."
            cmp_list(L, loc, 'chart title', site.texts('#chTitle'), [ttl])
            cmp_list(L, loc, 'chart subtitle', site.texts('#chSub'), [sub + ' The shaded zones are the next 60 days, as the odds draw them.'])
            L.chk(loc, 'At the alert / What happened toggle shown only for the example', pg.evaluate("() => document.querySelector('.toggle').hidden"), v['kind'] != 'example')
            chart_check(L, loc, site, M, v, 'alert')
            cloud_check(L, loc, site, M, v, 'alert')
            cmp_list(L, loc, 'chart side box', site.texts('#chartSide'), side_texts(M, v, 'alert'))
            if v['kind'] == 'example':
                pg.click('#bHap'); pg.wait_for_timeout(450)
                loc = 'page chart example (What happened)'
                cmp_list(L, loc, 'chart subtitle', site.texts('#chSub'), [sub])
                chart_check(L, loc, site, M, v, 'happened')
                cloud_check(L, loc, site, M, v, 'happened')
                cmp_list(L, loc, 'chart side box', site.texts('#chartSide'), side_texts(M, v, 'happened'))
                pg.click('#bAlert'); pg.wait_for_timeout(200)
        # ---------- Past signals
        pg.click('#tab-record'); pg.wait_for_timeout(300)
        for flt in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{flt}"]'); pg.wait_for_timeout(250)
            loc = f'page past signals ({flt})'
            rows = [s for s in aplus if flt == 'all' or s['a'] == flt]
            cmp_list(L, loc, 'count line', site.texts('#recCount'), [f"{len(rows)} signals · {sum(1 for s in rows if not s['m']['r10'])} missed +10%"])
            exp = []
            for a in C.ASSETS:
                if flt not in ('all', a): continue
                gs = M.gstat.get((a, 'A+'))
                if not gs: continue
                mi = M.miss.get((a, 'A+'))
                exp += [a, f"{gs['n']} signals", 'Rose 10% in 60 days', f"{gs['r10']}%", 'Reached +20% in 60 days', f"{gs['r20']}%", 'Rose 10%, never fell 25.3%', f"{gs['surv']}%",
                        'Median deepest dip', pct(gs['mdd'])]
                if mi: exp += ['Misses: median best price', pct(mi['median_peak'])]
            cmp_list(L, loc, 'summary boxes', site.texts('#recSum'), exp)
            exp = []
            for s in rows:
                m = s['m']
                exp += [date_long(s['d0']), s['chart'], money(s['entry']), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No', pct(rnd(m['up'], 6)), pct(rnd(m['dd'], 6)), pct(rnd(m['ret'], 6)), str(m['dpk'])]
            cmp_list(L, loc, 'table', site.texts('#recBody'), exp)
        cmp_list(L, 'page past signals', 'heading and footnote', site.texts('#view-record .rec-head .sec-title') + site.texts('#view-record p.fine'),
                 ['Every top-grade signal whose 60 days have closed · computed, never traded',
                  'Computed signals, not trades. Each row is a signal at its confirmation close, measured over the next 60 days. There is no exit in the data, so this is entry quality, not a return or a track record.'])
        # ---------- How to read
        pg.click('#tab-read'); pg.wait_for_timeout(250)
        L.chk('page how to read', 'posting bar', ' '.join(site.texts('#howBar')), '70% bar')
        txt = ' '.join(site.texts('#view-read'))
        nums = sorted(set(re.findall(r'\d+(?:\.\d+)?x?%?', txt)))
        L.chk('page how to read', 'every number in the text (10% rise, 60 days, 25.3%, 3.3x, 5% margin, falls of 5/10/15/20%, 70% bar)', ' '.join(nums), ' '.join(sorted(set(['10%', '60', '25.3%', '3.3x', '5%', '15%', '20%', '70%']))))
        L.chk('page', 'no page error or console error', ' | '.join(site.errors[:3]), '')
        site.close()
    with open(out, 'w', newline='') as f:
        csv.writer(f).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + L.rows)
    bad = L.bad()
    print(f'{name}: {len(L.rows)} comparisons ({n_feed} data, {len(L.rows) - n_feed} page), {len(bad)} disagreements')
    for r in bad[:80]:
        print('  ', r[1], '|', r[2], '|', repr(r[3])[:150], '|', repr(r[4])[:150])
    return M, L


if __name__ == '__main__':
    root, now, name, out = sys.argv[1:5]
    run(root, dt.datetime.fromisoformat(now.replace('Z', '+00:00')), name, out)
