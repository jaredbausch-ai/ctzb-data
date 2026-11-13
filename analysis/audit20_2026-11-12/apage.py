"""Audit #20 -- render the member page with Playwright and compare every displayed number with MY model (check 8)."""
import json, csv, os, re, math, datetime as dt
from fractions import Fraction as Fr
from decimal import Decimal as Dc
from playwright.sync_api import sync_playwright
import alib as A
from alib import rha, fstr, to_fr, D

MINUS = "−"
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
L_, R_, T_, B_ = 20, 960, 24, 480


def fmt(v, d=1):
    v = to_fr(v)
    if v is None: return 'n/a'
    r = rha(v, d)
    return fstr(Fr(0), d) if r == 0 else fstr(r, d).replace('-', MINUS)


def pct(v, d=1, sign=True):
    v = to_fr(v)
    if v is None: return 'n/a'
    return ('+' if sign and rha(v, d) > 0 else '') + fmt(v, d) + '%'


def pc(v):
    return 'n/a' if v is None or v == '' else f'{v}%'


def money(v):
    v = to_fr(v)
    if v is None: return 'n/a'
    r = rha(v, 2); s = fstr(abs(r), 2); i, f = s.split('.')
    return '$' + ('-' if r < 0 else '') + f'{int(i):,}.{f}'


def date_long(iso):
    if not iso: return ''
    d = D.fromisoformat(str(iso)[:10]); return f'{d.day} {MON[d.month - 1]} {d.year}'


def px_at(entry, p):
    entry, p = to_fr(entry), to_fr(p)
    if entry is None or p is None: return None
    return rha(rha(entry, 2) * (1 + p / 100), 2)


def norm(s):
    if s is None: return ''
    return re.sub(r'\s+', ' ', re.sub(r'\bSept\b', 'Sep', str(s).replace(chr(160), ' '))).strip()


def low(s):
    return norm(s).lower()


JS_NOW = r"""() => {
  const T = (e) => e ? e.innerText : null, q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const card = q('#card');
  return {
    rv: T(q('#review span')), filter: T(q('#filterText')), foot: T(q('#feedState')), howBar: q('#howBar') ? q('#howBar').textContent : null,
    preview: q('#previewSwitch').checked,
    picker: qa('#picker .pick').map((b) => ({ sel: b.dataset.sel, pressed: b.getAttribute('aria-pressed'), cls: b.className, text: b.innerText })),
    pnone: qa('#picker .pnone').map(T),
    card: {
      where: T(q('.where', card)), state: T(q('.card-head .state', card)), smalls: qa('.card-head .small', card).map(T),
      big: T(q('.odds .big', card)), bigStyle: q('.odds .big', card) ? q('.odds .big', card).getAttribute('style') : null,
      odds: qa('.odds > div', card).map(T), kv: qa('.stats .kv', card).map((k) => [T(k.children[0]), T(k.children[1])]),
      pool: T(q('.stats > .fine', card)), marker: T(q('.marker', card)),
      tiles: qa('.tile', card).map((t) => [T(q('.t', t)), T(q('.v', t))]), lbl: qa('.box .lbl', card).map(T),
      ladder: qa('#ladder .bar').map((b) => [T(b.children[0]), T(b.children[2]), b.querySelector('.f').style.width, b.querySelector('.f').className]),
      ladderFine: T(q('#ladder .fine')), eras: qa('#eras .bar').map((b) => [T(b.children[0]), T(b.children[2])]),
      foot: T(q('.card-foot .fine', card)), emptyBig: T(q('.empty-card .big', card)), emptySmalls: qa('.empty-card .small', card).map(T), stale: T(q('.stale-note', card)),
      frameC: q('#cardFrame').style.getPropertyValue('--c'),
    },
    prevIntact: qa('#prevIntact .mini').map((m) => [T(q('.name', m)), T(q('.sub', m)), T(q('.badge', m))]), prevIntactNone: T(q('#prevIntact .none')),
    prevClosed: qa('#prevClosed .mini').map((m) => [T(q('.name', m)), T(q('.sub', m)), T(q('.badge', m)), m.className]), prevClosedNone: T(q('#prevClosed .none')),
    lead: T(q('#leadBody')), body: document.body.innerText,
  };
}"""

JS_CHART = r"""() => {
  const T = (e) => e ? e.innerText : null, q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const el = (e) => { const o = { tag: e.tagName, text: e.tagName === 'text' ? e.textContent : undefined };
    for (const a of e.attributes) if (a.name !== 'style') o[a.name] = a.value;
    for (const p of ['stroke', 'fill']) { const v = e.style.getPropertyValue(p); if (v && !(e.tagName === 'text' && p === 'stroke')) o[p] = v; }
    return o; };
  return {
    title: T(q('#chTitle')), sub: T(q('#chSub')), toggleHidden: q('.toggle').hidden, alertPressed: q('#bAlert').getAttribute('aria-pressed'),
    svg: qa('#chartSvg > *').map(el), cloud: qa('#cloudSvg > *').map(el), cloudSub: T(q('#cloudSub')), cloudNote: T(q('#cloudNote')),
    side: qa('#chartSide > *').map((b) => ({ cls: b.className, title: T(q('.sec-title', b)), kv: qa('.kv', b).map((k) => [T(k.children[0]), T(k.children[1])]),
      smalls: qa('.small', b).filter((x) => !x.closest('.kv')).map(T), big: T(q('.num:not(.kv)', b)), fines: qa('.fine', b).map(T), text: T(b) })),
  };
}"""

JS_REC = r"""() => {
  const T = (e) => e ? e.innerText : null, q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  return { count: T(q('#recCount')), head: T(q('#view-record .sec-title')),
    sum: qa('#recSum .sidebox').map((b) => qa('.kv', b).map((k) => [T(k.children[0]), T(k.children[1])])),
    rows: qa('#recBody tr').map((r) => qa('td', r).map(T)) };
}"""


class Site:
    def __init__(self, root, feed='file', ledger='file', example='file', candles='file', trades=None, clock=None, pw=None):
        self.root = root; self.over = dict(feed=feed, ledger=ledger, example=example, candles=candles, trades=trades)
        page = open(os.path.join(root, 'docs/artifacts/member-site/index.html'), encoding='utf-8').read()
        self.doc = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page + '</body></html>'
        self.pw = pw; self.clock = clock; self.errors = []

    def body(self, kind, path):
        o = self.over[kind]
        if o == 'file': return open(path, 'rb').read() if os.path.exists(path) else None
        if callable(o): return o(path)
        return o        # None -> 404, bytes/str -> served

    def candle_json(self, a, tf):
        p = os.path.join(self.root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        if not os.path.exists(p): return None
        return json.dumps({'chart': f'{a} {tf}', 'bars': [{'t': float(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])} for r in csv.DictReader(open(p))]})

    def open(self):
        self.b = self.pw.chromium.launch(); self.pg = self.b.new_page(viewport={'width': 1440, 'height': 900})
        self.pg.on('pageerror', lambda e: self.errors.append(str(e)))
        def h(route):
            u = route.request.url.split('?')[0]
            def serve(bd, ct):
                if bd is None: return route.fulfill(status=404, body='not found')
                return route.fulfill(body=bd, content_type=ct)
            if u == 'http://site.test/': return route.fulfill(body=self.doc, content_type='text/html')
            if 'fonts' in u: return route.abort()
            if u.endswith('/data/ctzb_feed.json'): return serve(self.body('feed', os.path.join(self.root, 'feed/ctzb_feed.json')), 'application/json')
            if u.endswith('/data/ledger.csv'): return serve(self.body('ledger', os.path.join(self.root, 'datasets/ledger.csv')), 'text/csv')
            if u.endswith('/data/trades.json'): return serve(self.over['trades'], 'application/json')
            if '/data/example_ETH-2D-2024-09-22.json' in u: return serve(self.body('example', os.path.join(self.root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')), 'application/json')
            m = re.search(r'/data/candles/(ETH|BTC)_(1D|2D|3D|5D|8D)\.json$', u)
            if m:
                o = self.over['candles']
                bd = self.candle_json(m.group(1), m.group(2)) if o == 'file' else (o(m.group(1), m.group(2)) if callable(o) else o)
                return serve(bd, 'application/json')
            return route.fulfill(status=404, body='not found')
        self.pg.route('**/*', h)
        if self.clock: self.pg.clock.install(time=self.clock)
        self.pg.goto('http://site.test/'); self.pg.wait_for_timeout(700)
        return self

    def now(self): return self.pg.evaluate(JS_NOW)
    def tab(self, v): self.pg.click(f'#tab-{v}'); self.pg.wait_for_timeout(350)
    def pick(self, sel):
        self.pg.evaluate("(s) => { const b = Array.from(document.querySelectorAll('#picker .pick')).find((x) => x.dataset.sel === s); if (b) b.click(); }", sel)
        self.pg.wait_for_timeout(350)
    def chart(self): return self.pg.evaluate(JS_CHART)
    def rec(self, asset):
        self.pg.evaluate("(a) => document.querySelector(`.seg button[data-asset='${a}']`).click()", asset); self.pg.wait_for_timeout(250)
        return self.pg.evaluate(JS_REC)
    def close(self): self.b.close()


# ------------------------------------------------------------------ expectations from MY model
def miss_for(M, asset, grade):
    return next((m for m in M.get('if_it_misses', []) if m['asset'] == asset and m['grade'] == grade), None)


def edge_of(mc):
    fe = to_fr(mc['from_entry']['still_rose10_exact_pct'])
    if fe is not None and fe < A.BAR: return 0
    for r in mc['if_it_falls_first']:
        x = to_fr(r['still_rose10_exact_pct'])
        if x is not None and x < A.BAR: return -r['fell_pct']
    return None


def exp_card(M, kind, mc, mo=None, best_sid=None):
    """What the Now card should read, from my model card mc (and my open signal mo)."""
    top = mc['grade'] == 'A+'; e = {}
    e['where'] = f"{mc['asset']} · {mc['timeframe']} chart" + (' · example' if kind == 'example' else '')
    e['state'] = {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind]
    if kind == 'forming':
        e['line'] = f"Low {date_long(mc['low_day'])} · confirms {date_long(mc['confirms_on'])}" + (f" if it closes above {money(mc['must_close_above'])}" if mc.get('must_close_above') not in (None, '', '0') else '')
        e['note'] = ((('Best setup forming today.' if best_sid == mc['signal_id'] else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.") if not top
                     else 'Not confirmed yet. It can still vanish before it confirms.')
    elif kind == 'open':
        e['line'] = f"Confirmed {date_long(mo['entry_date'])} · entry close {money(mo['entry_close'])} · day {mo['days_elapsed']} of 60 · best so far {pct(mo['best_so_far_pct'])} · worst {pct(mo['worst_so_far_pct'])}"
        st, lv = mo['edge_status'], mo['edge_level_pct']
        if st == 'lost': s = 'Edge lost. ' + ('Its odds were below the bar from the entry.' if lv in (0, '0') else f'It fell to its edge level ({pct(lv, 0)}) before rising 10%.')
        elif st == 'rose10': s = 'Rose 10%. ' + ('It has risen 10% from the entry close.' if lv is None else f'It rose 10% before falling to its edge level ({pct(lv, 0)}).')
        else: s = 'On track. ' + ('It has neither risen 10% nor lost its edge; its odds hold at every fall measured.' if lv is None else f'It has not fallen to its edge level ({pct(lv, 0)}) or risen 10% yet.')
        e['note'] = s + ' The odds below are as of the entry close, not from today.'
    else:
        e['line'] = f"Example: confirmed {date_long('2024-09-22')} · entry close {money(mc['entry_close'])}"; e['note'] = None
    e['big'] = pc(mc['rose10_within60d_pct'])
    e['odds1'] = 'rose 10% within 60 days' + (' · at the entry close, not from today' if kind == 'open' else '')
    e['odds2'] = f"{pc(mc['rose10_never_fell25_within60d_pct'])} did it without ever falling 25.3%"
    e['odds3'] = f"from {mc['sample']} · every figure covers the 60 days after entry"
    edge = edge_of(mc)
    mi = M.get('example_if_it_misses') if kind == 'example' else miss_for(M, mc['asset'], mc['grade'])
    gl = 'top-grade' if top else 'same-grade'
    e['kv'] = [['Typical high', pct(mc['typical_biggest_rise_exact_pct'])], ['Typical drop from entry', pct(mc['typical_deepest_dip_exact_pct'])],
               ['Edge gone below', f'Below the {A.BAR}% bar from entry' if edge == 0 else f'{pct(edge, 0)} before it rises 10%' if edge is not None else 'Holds at every level'],
               ['If it misses: went above entry', 'n/a' if not mi else 'none missed' if not mi['misses'] else f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}"]]
    e['pool'] = None if not (mi and mi['signals']) else (f"of the {mi['signals']} {mc['asset']} {gl} signals known by then" if kind == 'example' else f"of all {mi['signals']} {mc['asset']} {gl} signals")
    n = mc['past_trades']
    mt = '' if not (mi and mi['signals']) else (f" · {mi['misses']} misses of the {mi['signals']} {mc['asset']} {gl} signals known by then" if kind == 'example' else f" · {mi['misses']} misses of all {mi['signals']} {mc['asset']} {gl} signals")
    e['tiles'] = [['Dip before the high, from entry', pct(mc['typical_dip_before_rise_exact_pct'])], ['High lands around', f"Day {mc['typical_day_of_60d_high'] if mc['typical_day_of_60d_high'] is not None else 'n/a'}"],
                  [f'Reached +20% within 60 days · n {n}', pc(mc['rose20_within60d_pct'])], [f'Touched {MINUS}30% within 60 days · n {n}', pc(mc['fell30_within60d_pct'])],
                  ['Typical high', pct(mc['typical_biggest_rise_exact_pct'])], ['Deepest dip lands around', f"Day {mc['typical_day_of_deepest_dip'] if mc['typical_day_of_deepest_dip'] is not None else 'n/a'}"],
                  ['Typical worst drop, misses' + mt, pct(mi['median_worst_drop_pct']) if mi else 'n/a'], ['Typical change by day 60, misses' + mt, pct(mi['median_day60_pct']) if mi else 'n/a']]
    fe = mc['from_entry']
    e['ladder'] = [[f'From entry n {n}', pc(fe['still_rose10_pct']), to_fr(fe['still_rose10_exact_pct']) < A.BAR]] + \
                  [[f"Falls {r['fell_pct']}% first n {r['past_trades']}", pc(r['still_rose10_pct']) if r['still_rose10_pct'] is not None else 'n/a',
                    r['still_rose10_exact_pct'] is not None and to_fr(r['still_rose10_exact_pct']) < A.BAR] for r in mc['if_it_falls_first']]
    e['ladderFine'] = f"Share of this setup's past signals that, after first falling that far, still rose 10% before ever falling 25.3%. Below {A.BAR}% the edge is gone. Small samples: read the n."
    e['eras'] = [[f"{t} n {x['past_trades']}", pc(x['rose10_never_fell25_within60d_pct']) if x['rose10_never_fell25_within60d_pct'] is not None else 'n/a'] for t, x in (('Before 2022', mc['before_2022']), ('Since 2022', mc['since_2022']))]
    e['edge'] = edge
    return e


def cmp_card(C, loc, dom, e):
    c = dom['card']
    C.add(loc, 'card: where', low(c['where']), e['where'].lower(), 'page card')
    C.add(loc, 'card: state', norm(c['state']), e['state'], 'page card')
    sm = [norm(x) for x in c['smalls']]
    C.add(loc, 'card: line', sm[0] if sm else None, norm(e['line']), 'page card line')
    C.add(loc, 'card: status note', sm[1] if len(sm) > 1 else None, norm(e['note']), 'page card note')
    C.add(loc, 'card: big number', norm(c['big']), e['big'], 'page big number')
    od = [norm(x) for x in c['odds']]
    for i, k in ((1, 'odds1'), (2, 'odds2'), (3, 'odds3')): C.add(loc, f'card: line under big number {i}', od[i] if len(od) > i else None, norm(e[k]), 'page card')
    for i, (lab, val) in enumerate(e['kv']):
        got = c['kv'][i] if i < len(c['kv']) else [None, None]
        C.add(loc, f'card: {lab} (label)', norm(got[0]), lab, 'page label'); C.add(loc, f'card: {lab}', norm(got[1]), norm(val), 'page card stat')
    C.add(loc, 'card: miss pool', norm(c['pool']), norm(e['pool']), 'page miss pool')
    C.add(loc, 'card: tile count', len(c['tiles']), len(e['tiles']), 'page tiles')
    for i, (lab, val) in enumerate(e['tiles']):
        got = c['tiles'][i] if i < len(c['tiles']) else [None, None]
        C.add(loc, f'tile {i + 1}: label', norm(got[0]), norm(lab), 'page tile label'); C.add(loc, f'tile {i + 1}: {lab[:38]}', norm(got[1]), norm(val), 'page tile')
    C.add(loc, 'ladder rows', len(c['ladder']), len(e['ladder']), 'page ladder')
    for i, (lab, val, gone) in enumerate(e['ladder']):
        got = c['ladder'][i] if i < len(c['ladder']) else [None, None, None, '']
        C.add(loc, f'ladder {i}: label and n', norm(got[0]), lab, 'page ladder n'); C.add(loc, f'ladder {i}: {lab}', norm(got[1]), val, 'page ladder share')
        C.add(loc, f'ladder {i}: below-bar mark', 'gone' in (got[3] or ''), gone, 'page edge mark (70% on exact share)')
        C.add(loc, f'ladder {i}: bar width', got[2], (val if val != 'n/a' else '0%'), 'page ladder bar width')
    C.add(loc, 'ladder: fine print', norm(c['ladderFine']), e['ladderFine'], 'page ladder text')
    for i, (lab, val) in enumerate(e['eras']):
        got = c['eras'][i] if i < len(c['eras']) else [None, None]
        C.add(loc, f'era {i}: label and n', norm(got[0]), lab, 'page era n'); C.add(loc, f'era {i}: {lab}', norm(got[1]), val, 'page era share')
    C.add(loc, 'card: lead trader', norm(c['marker']), 'Lead trader: unavailable', 'lead trader (404 in this harness)')
    C.add(loc, 'card: foot says entry quality only', 'Entry quality only: no exit, not a trade or a track record' in (c['foot'] or ''), True, 'entry-quality wording')


def bars_of(W, a, tf, n=70):
    ch = W.raw[(a, tf)]
    return ch[-n:]


def load_raw(root):
    raw = {}
    for a in A.ASSETS:
        for tf in A.TFS:
            raw[(a, tf)] = [dict(t=int(float(r['time'])), o=Fr(Dc(r['open'])), h=Fr(Dc(r['high'])), l=Fr(Dc(r['low'])), c=Fr(Dc(r['close']))) for r in csv.DictReader(open(os.path.join(root, 'data', f'{a}_{tf}.csv')))]
    return raw


def ts(d): return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())
def dayof(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).date()


def exp_chart(M, kind, mc, mo, bars, tfd, happened=False, E_idx=None, feed_day=None):
    """Expected geometry and texts of the chart for my model card, from my bars."""
    forming = kind in ('forming', 'open')
    if kind == 'forming': entry_day = mc['confirms_on']; entry = to_fr(mc['price_now']); E = len(bars) - 1
    elif kind == 'open':
        entry_day = mo['entry_date']; entry = to_fr(mo['entry_close'])
        E = next((i for i, b in enumerate(bars) if A.next_open(dayof(b['t']), tfd) - dt.timedelta(days=1) == D.fromisoformat(entry_day)), None)
    else: entry_day = '2024-09-22'; entry = to_fr(mc['entry_close']); E = E_idx
    if E is None: return None
    tE = ts(D.fromisoformat(entry_day)); opens = [b['t'] for b in bars]
    if forming:
        while opens[-1] <= tE + 61 * 86400: opens.append(ts(A.next_open(dayof(opens[-1]), tfd)))
    def slot_of(t):
        i = 0
        while i + 1 < len(opens) and opens[i + 1] <= t: i += 1
        return i
    dayx = lambda k: slot_of(tE + k * 86400)
    Aidx = dayx(0) if kind == 'forming' else E
    n_slots = len(opens) if forming else len(bars); slot = (R_ - L_) / n_slots
    X = lambda i: L_ + slot * i + slot / 2
    hi_p, dr_p = to_fr(mc['typical_biggest_rise_exact_pct']), to_fr(mc['typical_deepest_dip_exact_pct'])
    edge = edge_of(mc)
    lv = dict(high=px_at(entry, hi_p), t20=px_at(entry, 10), drop=px_at(entry, dr_p), edge=px_at(entry, edge) if edge else None)
    shown = bars[:E + 1] if (not forming and not happened) else bars
    lo = float(min(min(b['l'] for b in shown), lv['drop'], entry * Fr(8, 10))) * 0.95
    hi = float(max(max(b['h'] for b in shown), lv['high'])) * 1.07
    Y = lambda p: B_ - (float(p) - lo) / (hi - lo) * (B_ - T_)
    hd = mc['typical_day_of_60d_high']
    out = dict(E=E, A=Aidx, n_slots=n_slots, X=X, Y=Y, lv=lv, entry=entry, xT=X(E), xE=X(Aidx), x60=X(min(n_slots - 1, dayx(60))), xHigh=X(dayx(int(hd))) if hd is not None else None,
               upto=len(bars) if (forming or happened) else E + 1, opens=opens, edge=edge, tE=tE, slot=slot, dayx=dayx)
    last_close_day = A.next_open(dayof(bars[-1]['t']), tfd) - dt.timedelta(days=1)
    t = []
    t.append(f"Typical high {pct(hi_p)}"); t.append(f"+10% · {pc(mc['rose10_within60d_pct'])} of past signals got here"); t.append(f"Typical drop {pct(dr_p)}")
    out['tags'] = sorted([money(lv['high']), money(lv['t20']), money(entry), money(lv['drop'])])
    fe = mc['from_entry']; steps = [(fe['still_rose10_pct'], mc['past_trades'])] + [(r['still_rose10_pct'], r['past_trades']) for r in mc['if_it_falls_first'][:3]]
    out['bands'] = ['n/a' if v is None else f'{v}% · n {nn}' for v, nn in steps]
    xs = [(fe['still_rose10_pct'], fe['still_rose10_exact_pct'])] + [(r['still_rose10_pct'], r['still_rose10_exact_pct']) for r in mc['if_it_falls_first'][:3]]
    out['band_rects'] = [(Y(entry * (1 + Fr(a1, 100))), min(B_, Y(entry * (1 + Fr(b1, 100)))), 'var(--closed)' if v is None else 'var(--high)' if to_fr(x) >= A.BAR else 'var(--drop)')
                         for (a1, b1), (v, x) in zip(((0, -5), (-5, -10), (-10, -15), (-15, -20)), xs)]
    if lv['edge']: t.append(f"Edge gone below {money(lv['edge'])} ({pct(edge, 0)}, before +10%)")
    out['vl'] = {}
    if kind == 'forming': out['vl'][('Today' if (feed_day is None or str(last_close_day) >= feed_day) else f"Latest bar · {date_long(str(dayof(bars[-1]['t'])))}")] = out['xT']
    else: out['vl']['Entry'] = out['xT']
    out['vl'][f'High usually ~day {hd}'] = out['xHigh']; out['vl']['Day 60'] = out['x60']
    if kind == 'forming' and Aidx > E: out['vl'][f"Confirms {date_long(mc['confirms_on'])} · entry, day 0"] = X(Aidx)
    out['texts'] = t
    return out


def cmp_chart(C, loc, dom, ex, bars, kind, mc, low_label=None, happened_labels=None):
    svg = dom['svg']; fl = lambda e, k: float(e[k])
    texts = [e for e in svg if e['tag'] == 'text']; lines = [e for e in svg if e['tag'] == 'line']; rects = [e for e in svg if e['tag'] == 'rect']
    tx = [norm(e['text']) for e in texts]
    for t in ex['texts']: C.add(loc, f'chart text: {t[:28]}', next((x for x in tx if x == norm(t)), None), norm(t), 'chart label')
    tags = sorted(norm(e['text']) for e in texts if e.get('fill') == '#07060F')
    C.add(loc, 'chart price tags', ' | '.join(tags), ' | '.join(ex['tags']), 'chart price tag')
    bands = [norm(e['text']) for e in texts if re.fullmatch(r'(\d+% · n \d+|n/a)', norm(e['text']))]
    C.add(loc, 'chart ladder bands (share · n)', ' | '.join(bands), ' | '.join(ex['bands']), 'chart ladder band')
    # vertical lines by label
    vls = [l for l in lines if l['y1'] == str(T_) and l['y2'] == str(B_) and l['x1'] == l['x2']]
    for lab, x in ex['vl'].items():
        te = next((e for e in texts if norm(e['text']) == norm(lab)), None)
        C.add(loc, f'chart line label: {lab[:30]}', norm(te['text']) if te else None, norm(lab), 'chart line label')
        if te is not None and x is not None:
            lx = fl(te, 'x') - 6
            C.add(loc, f'chart line position: {lab[:30]}', round(lx, 2), round(x, 2), 'chart line on the wrong bar')
            C.add(loc, f'chart line drawn: {lab[:30]}', any(abs(fl(l, 'x1') - x) < 0.01 for l in vls), True, 'chart line missing')
    # horizontal levels
    hl = [l for l in lines if l['y1'] == l['y2'] and l.get('stroke-width') in ('2', '2.5')]
    for nm, p in (('typical high', ex['lv']['high']), ('+10%', ex['lv']['t20']), ('entry', ex['entry']), ('typical drop', ex['lv']['drop']), ('edge', ex['lv']['edge'])):
        if p is None: continue
        y = ex['Y'](p)
        C.add(loc, f'chart level y: {nm}', any(abs(fl(l, 'y1') - y) < 0.02 for l in hl), True, 'chart level misplaced')
    for l in hl[:1]:
        C.add(loc, 'chart levels start at the entry bar', round(fl(l, 'x1'), 2), round(ex['xE'], 2), 'zone start'); C.add(loc, 'chart levels end at day 60', round(fl(l, 'x2'), 2), round(ex['x60'], 2), 'zone end')
    # zones and ladder bands
    zr = [r for r in rects if r.get('opacity') in ('0.07', '0.1')]
    zu = next((r for r in zr if r.get('opacity') == '0.07'), None); zd = next((r for r in zr if r.get('opacity') == '0.1'), None)
    yH, yE, yD = ex['Y'](ex['lv']['high']), ex['Y'](ex['entry']), ex['Y'](ex['lv']['drop'])
    okz = zu is not None and zd is not None and abs(fl(zu, 'x') - ex['xE']) < 0.02 and abs(fl(zu, 'width') - (ex['x60'] - ex['xE'])) < 0.02 and abs(fl(zu, 'y') - yH) < 0.02 and abs(fl(zu, 'height') - (yE - yH)) < 0.02 \
        and abs(fl(zd, 'x') - ex['xE']) < 0.02 and abs(fl(zd, 'y') - yE) < 0.02 and abs(fl(zd, 'height') - (yD - yE)) < 0.02 and abs(fl(zd, 'width') - (ex['x60'] - ex['xE'])) < 0.02
    C.add(loc, 'chart zones: entry bar to day 60, typical high to entry to typical drop', okz, True, 'zone geometry')
    br = [r for r in rects if r.get('opacity') == '0.24']
    badb = sum(1 for i, (y1, y2, col) in enumerate(ex['band_rects']) if i >= len(br) or abs(fl(br[i], 'y') - y1) > 0.02 or abs(fl(br[i], 'height') - (y2 - y1)) > 0.02 or br[i].get('fill') != col or abs(fl(br[i], 'x') - ex['xE']) > 0.02)
    C.add(loc, 'chart ladder bands misplaced or miscoloured (of 4; colour on the exact share vs 70%)', badb + abs(len(br) - 4), 0, 'ladder band geometry / colour')
    circ = [e for e in svg if e['tag'] == 'circle']
    if low_label is not None and ex.get('low_xy'):
        C.add(loc, 'chart low marker on the trough bar at its low', any(abs(fl(c_, 'cx') - ex['low_xy'][0]) < 0.02 and abs(fl(c_, 'cy') - ex['low_xy'][1]) < 0.02 for c_ in circ), True, 'low marker position')
    if ex.get('out_xy'):
        C.add(loc, 'chart outcome markers on the right bars', sum(1 for (x_, y_) in ex['out_xy'] if any(abs(fl(c_, 'cx') - x_) < 0.02 and abs(fl(c_, 'cy') - y_) < 0.02 for c_ in circ)), len(ex['out_xy']), 'outcome marker position')
    # candles
    wk = [l for l in lines if l['x1'] == l['x2'] and not (l['y1'] == str(T_) and l['y2'] == str(B_))]
    C.add(loc, 'chart candles drawn', len(wk), ex['upto'], 'candle count (at the alert: none after the entry)')
    bad = 0
    for i, l in enumerate(wk[:ex['upto']]):
        b = bars[i]
        if abs(fl(l, 'x1') - ex['X'](i)) > 0.02 or abs(fl(l, 'y1') - ex['Y'](b['h'])) > 0.02 or abs(fl(l, 'y2') - ex['Y'](b['l'])) > 0.02: bad += 1
    C.add(loc, 'chart candles misplaced (x by date, y by price scale)', bad, 0, 'candle geometry / axis scaling')
    # grid labels on the same scale
    badg = 0; ng = 0
    for e in texts:
        m = re.fullmatch(r'\$([\d,]+(\.\d+)?)', norm(e['text']))
        if m and e.get('fill') != '#07060F' and e.get('x') == str(R_ + 8):
            ng += 1; p = float(m.group(1).replace(',', ''))
            if abs((fl(e, 'y') - 5) - ex['Y'](p)) > max(0.6, abs(ex['Y'](p) - ex['Y'](p * 1.0005))): badg += 1
    C.add(loc, f'chart axis labels off the price scale (of {ng})', badg, 0, 'axis label')
    # date labels along the bottom
    badd = 0; nd = 0
    for e in texts:
        if e.get('y') == str(B_ + 22):
            nd += 1; i = round((fl(e, 'x') - L_ - ex['slot'] / 2) / ex['slot']); d_ = dayof(ex['opens'][min(i, len(ex['opens']) - 1)])
            if norm(e['text']) != f'{d_.day:02d} {MON[d_.month - 1]}': badd += 1
    C.add(loc, f'chart date labels wrong (of {nd})', badd, 0, 'date axis')
    if low_label is not None:
        got = next((x for x in tx if x.startswith('Low ')), None)
        C.add(loc, 'chart low marker', got, norm(low_label), 'low marker')
    if happened_labels is not None:
        got = sorted(x for x in tx if x.startswith('This one:'))
        C.add(loc, 'chart outcome labels', ' | '.join(got), ' | '.join(sorted(norm(x) for x in happened_labels)), 'outcome label')
    else:
        C.add(loc, 'no outcome label unless "What happened"', any(x.startswith('This one:') for x in tx), False, 'outcome shown at the alert')


def exp_side(M, kind, mc, mo, entry):
    top = mc['grade'] == 'A+'; edge = edge_of(mc)
    small = f"{mc['chart']}" + (' · example' if kind == 'example' else '') + (f" · from {mc['sample']}" if mc.get('sample') else '') + (' · odds as of the entry close, not from today' if kind == 'open' else '')
    kv = [['Typical high', f"{pct(mc['typical_biggest_rise_exact_pct'])} · {money(px_at(entry, mc['typical_biggest_rise_exact_pct']))}"], ['+10% level', money(px_at(entry, 10))],
          ['Reached +20% within 60 days', pc(mc['rose20_within60d_pct'])], ['Typical drop', f"{pct(mc['typical_deepest_dip_exact_pct'])} · {money(px_at(entry, mc['typical_deepest_dip_exact_pct']))}"],
          ['Edge gone below', 'below the bar already' if edge == 0 else 'holds at every level' if edge is None else f'{money(px_at(entry, edge))} ({pct(edge, 0)})']]
    return dict(small=small, big=pc(mc['rose10_within60d_pct']), line=f"rose 10% within 60 days, from {mc['past_trades']} past signals; {pc(mc['rose10_never_fell25_within60d_pct'])} without ever falling 25.3%", kv=kv)


def cmp_side(C, loc, dom, es):
    sb = dom['side'][0] if dom['side'] else dict(kv=[], smalls=[], big=None, text='')
    sm = [norm(x) for x in sb['smalls']]
    C.add(loc, 'side: chart and sample', sm[0] if sm else None, norm(es['small']), 'chart side sample')
    C.add(loc, 'side: big number', norm(sb['big']), es['big'], 'chart side big number')
    C.add(loc, 'side: n and surv line', sm[1] if len(sm) > 1 else None, norm(es['line']), 'chart side line')
    for i, (lab, val) in enumerate(es['kv']):
        got = sb['kv'][i] if i < len(sb['kv']) else [None, None]
        C.add(loc, f'side: {lab} (label)', norm(got[0]), lab, 'chart side label'); C.add(loc, f'side: {lab}', norm(got[1]), norm(val), 'chart side figure / price')
    C.add(loc, 'side: entry quality wording', any('Entry quality only: no exit, not a trade or a track record' in (b['text'] or '') for b in dom['side']), True, 'entry-quality wording')
    C.add(loc, 'side: lead trader note', any("lead trader's feed is unavailable right now" in (b['text'] or '') for b in dom['side']), True, 'lead trader (404)')


def cmp_cloud(C, loc, dom, pp, sub, extra_poly=None):
    cl = dom['cloud']; X = lambda d_: L_ + (R_ - L_) * d_ / 60; Y = lambda v: 230 - (max(-40.0, min(100.0, float(v))) + 40) / 140 * 218
    if pp is None:
        C.add(loc, 'cloud unavailable', any('Past paths unavailable' in (e.get('text') or '') for e in cl), True, 'cloud'); return
    C.add(loc, 'cloud: caption (sample and n)', norm(dom['cloudSub']), norm(sub), 'cloud n')
    last = pp['days'][-1]
    C.add(loc, 'cloud: day 60 note', norm(dom['cloudNote'])[norm(dom['cloudNote']).find('Day 60:'):].split(' Daily closes.')[0],
          f"Day 60: median {pct(last['median_pct'])}, middle half {pct(last['q25_pct'])} to {pct(last['q75_pct'])}.", 'cloud day-60 figures')
    pl = [e for e in cl if e['tag'] == 'polyline']; pg = [e for e in cl if e['tag'] == 'polygon']
    def pts(s): return [tuple(float(z) for z in p.split(',')) for p in s.split()]
    medp = pts(pl[0]['points']) if pl else []
    bad = sum(1 for d_, r in enumerate(pp['days']) if d_ >= len(medp) or abs(medp[d_][0] - X(r['day'])) > 0.01 or abs(medp[d_][1] - Y(to_fr(r['median_pct']))) > 0.01)
    C.add(loc, 'cloud: median path points off (of 61)', bad, 0, 'cloud median path')
    band = pts(pg[0]['points']) if pg else []
    exp = [(X(r['day']), Y(to_fr(r['q75_pct']))) for r in pp['days']] + [(X(r['day']), Y(to_fr(r['q25_pct']))) for r in reversed(pp['days'])]
    bad = sum(1 for i, p in enumerate(exp) if i >= len(band) or abs(band[i][0] - p[0]) > 0.01 or abs(band[i][1] - p[1]) > 0.01)
    C.add(loc, 'cloud: middle-half band points off (of 122)', bad, 0, 'cloud band')
    if extra_poly is not None:
        got = pts(pl[1]['points']) if len(pl) > 1 else []
        exp2 = [(X(d_), Y(v)) for d_, v in extra_poly]
        bad = sum(1 for i, p in enumerate(exp2) if i >= len(got) or abs(got[i][0] - p[0]) > 0.01 or abs(got[i][1] - p[1]) > 0.01)
        C.add(loc, f'cloud: this signal\'s path points off (of {len(exp2)})', bad, 0, 'cloud signal path')
    else: C.add(loc, 'cloud: no signal path unless "What happened"', len(pl), 1, 'outcome shown at the alert')
