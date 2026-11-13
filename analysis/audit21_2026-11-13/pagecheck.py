"""Audit 21 -- page checks (item 8): every number the member page shows vs MY values (the model from datacheck)."""
import csv, datetime as dt, json, os, re, sys
from decimal import Decimal
from fractions import Fraction
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C
from core import rnd, D1

MINUS = '−'
MON = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
FOOT = "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record."


def nt(s):
    return None if s is None else re.sub(r'\bSept\b', 'Sep', re.sub(r'\s+', ' ', str(s))).strip()


def fmt(v, d=1):
    if v is None: return 'n/a'
    r = rnd(v, d) if d else rnd(v)
    if r == 0: return f'{0:.{d}f}'
    return f'{r:.{d}f}'.replace('-', MINUS)


def pct(v, d=1, sign=True):
    if v is None: return 'n/a'
    r = rnd(v, d) if d else rnd(v)
    return ('+' if sign and r > 0 else '') + fmt(v, d) + '%'


def pc(v): return 'n/a' if v is None else f'{v}%'


def money(v):
    if v is None: return 'n/a'
    return '$' + f'{rnd(v, 2):,.2f}'


def px_at(entry, p):
    if entry is None or p is None: return None
    cents = round(entry * 100)
    x = Fraction(cents) * (100 + Fraction(Decimal(str(p)))) / 100
    return C.rnd_exact(x, 0) / 100


def date_long(iso):
    if not iso: return ''
    d = dt.date.fromisoformat(str(iso)[:10])
    return f'{d.day} {MON[d.month]} {d.year}'


EXTRACT_NOW = r"""() => {
  const N = (s) => s == null ? null : s.replace(/\s+/g, ' ').trim();
  const T = (s, r = document) => { const e = r.querySelector(s); return e ? N(e.textContent) : null; };
  const A = (s, r = document) => Array.from(r.querySelectorAll(s));
  const card = document.querySelector('#card');
  const bar = (b) => ({ lab: N(b.children[0].textContent), val: N(b.children[2].textContent), gone: !!b.querySelector('.f.gone'), w: b.querySelector('.f') ? b.querySelector('.f').style.width : null });
  const mini = (m) => ({ name: T('.name', m), sub: T('.sub', m), badge: T('.badge', m), cls: m.className });
  return {
    filter: T('#filterText'), filterOff: document.querySelector('#filterPill').classList.contains('off'), review: T('#review'), rv: T('#rvAsof'), feedState: T('#feedState'), foot: T('footer'),
    preview: document.querySelector('#previewSwitch').checked,
    picker: A('#picker .prow').map((r) => ({ label: T('.plabel', r), btns: A('button', r).map((b) => ({ t: N(b.textContent), sel: b.dataset.sel, pressed: b.getAttribute('aria-pressed'), cls: b.className })), none: T('.pnone', r) })),
    card: { text: N(card.innerText), where: T('.where', card), state: T('.state', card), stateAttr: (card.querySelector('.state') || {}).dataset ? card.querySelector('.state').dataset.state || null : null,
      headSmall: A('.card-head .small', card).map((e) => N(e.textContent)), stale: T('.stale-note', card),
      odds: A('.odds > div', card).map((e) => N(e.textContent)), bigStyle: card.querySelector('.odds .big') ? card.querySelector('.odds .big').getAttribute('style') : null,
      stats: A('.stats .kv', card).map((k) => Array.from(k.children).map((s) => N(s.textContent))), pool: A('.stats .fine', card).map((e) => N(e.textContent)),
      marker: T('.marker', card), tiles: A('.tile', card).map((t) => [T('.t', t), T('.v', t)]),
      ladder: A('#ladder .bar', card).map(bar), ladderFine: T('#ladder .fine', card), eras: A('#eras .bar', card).map(bar), lbls: A('.box .lbl', card).map((e) => N(e.textContent)),
      boxFine: A('.box.teal .fine', card).map((e) => N(e.textContent)), foot: T('.card-foot', card), empty: T('.empty-card', card), frame: document.querySelector('#cardFrame').style.getPropertyValue('--c') },
    prevIntact: A('#prevIntact .mini').map(mini), prevIntactNone: T('#prevIntact .none'), prevClosed: A('#prevClosed .mini').map(mini), prevClosedNone: T('#prevClosed .none'),
    lead: T('#leadBody'), howBar: T('#howBar'), read: T('#view-read'), body: N(document.body.innerText) };
}"""

EXTRACT_CHART = r"""() => {
  const N = (s) => s == null ? null : s.replace(/\s+/g, ' ').trim();
  const T = (s, r = document) => { const e = r.querySelector(s); return e ? N(e.textContent) : null; };
  const A = (s, r = document) => Array.from(r.querySelectorAll(s));
  const g = (e, k) => e.getAttribute(k) != null ? e.getAttribute(k) : e.style.getPropertyValue(k);
  const num = (e, k) => +e.getAttribute(k);
  return { title: T('#chTitle'), sub: T('#chSub'), toggleHidden: document.querySelector('.toggle').hidden, alertPressed: document.querySelector('#bAlert').getAttribute('aria-pressed'),
    texts: A('#chartSvg text').map((t) => ({ s: t.textContent, x: num(t, 'x'), y: num(t, 'y'), fill: g(t, 'fill'), anchor: t.getAttribute('text-anchor') })),
    lines: A('#chartSvg line').map((l) => ({ x1: num(l, 'x1'), x2: num(l, 'x2'), y1: num(l, 'y1'), y2: num(l, 'y2'), sw: l.getAttribute('stroke-width'), stroke: g(l, 'stroke'), dash: l.getAttribute('stroke-dasharray') })),
    rects: A('#chartSvg rect').map((r) => ({ x: num(r, 'x'), y: num(r, 'y'), w: num(r, 'width'), h: num(r, 'height'), fill: g(r, 'fill'), op: r.getAttribute('opacity') })),
    circles: A('#chartSvg circle').map((c) => ({ x: num(c, 'cx'), y: num(c, 'cy') })),
    cloudSub: T('#cloudSub'), cloudNote: T('#cloudNote'), cloudTexts: A('#cloudSvg text').map((t) => t.textContent),
    poly: A('#cloudSvg polyline').map((p) => p.getAttribute('points')), polygon: A('#cloudSvg polygon').map((p) => p.getAttribute('points')),
    side: A('#chartSide .sidebox').map((b) => ({ title: T('.sec-title', b), kv: A('.kv', b).map((k) => Array.from(k.children).map((s) => N(s.textContent))), text: N(b.textContent) })),
    sideFine: A('#chartSide > .fine').map((e) => N(e.textContent)) };
}"""

EXTRACT_REC = r"""() => {
  const N = (s) => s == null ? null : s.replace(/\s+/g, ' ').trim();
  const A = (s, r = document) => Array.from(r.querySelectorAll(s));
  return { count: N(document.querySelector('#recCount').textContent), rows: A('#recBody tr').map((tr) => A('td', tr).map((td) => N(td.textContent))),
    sum: A('#recSum .sidebox').map((b) => A('.kv', b).map((k) => Array.from(k.children).map((s) => N(s.textContent)))), head: N(document.querySelector('#view-record .rec-head .sec-title').textContent),
    foot: N(document.querySelector('#view-record p.fine').textContent) };
}"""


class Site:
    """the page served from a state folder, with optional overrides (for synthetic states)"""
    def __init__(self, pw, root, clock_iso, feed='file', ledger='file', example='file', trades=None, candles=None, viewport=(1440, 900)):
        self.root = root
        page = open(os.path.join(root, 'docs/artifacts/member-site/index.html'), encoding='utf-8').read()
        self.doc = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page + '</body></html>'
        rd = lambda p: open(os.path.join(root, p), 'rb').read() if os.path.exists(os.path.join(root, p)) else None
        self.feed = rd('feed/ctzb_feed.json') if feed == 'file' else feed
        self.ledger = rd('datasets/ledger.csv') if ledger == 'file' else ledger
        self.example = rd('docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json') if example == 'file' else example
        self.trades = trades; self.candles = candles or {}
        self.b = pw.chromium.launch(); self.pg = self.b.new_page(viewport={'width': viewport[0], 'height': viewport[1]})
        self.errs = []; self.pg.on('pageerror', lambda e: self.errs.append(str(e)))
        self.pg.route('**/*', self.handle)
        if clock_iso: self.pg.clock.install(time=clock_iso)

    def bars(self, a, tf):
        p = os.path.join(self.root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        if not os.path.exists(p): return None
        return [dict(t=float(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]

    def handle(self, route):
        u = route.request.url
        f = lambda body, ct: route.fulfill(body=body, content_type=ct) if body is not None else route.fulfill(status=404, body='x')
        if u.rstrip('/') == 'http://site.test' or u.startswith('http://site.test/#'): return route.fulfill(body=self.doc, content_type='text/html')
        if 'fonts' in u: return route.abort()
        if u.endswith('data/ctzb_feed.json'): return f(self.feed, 'application/json')
        if u.endswith('data/ledger.csv'): return f(self.ledger, 'text/csv')
        if u.endswith('data/trades.json'): return f(self.trades, 'application/json')
        if u.endswith('data/example_ETH-2D-2024-09-22.json'): return f(self.example, 'application/json')
        m = re.search(r'data/candles/(ETH|BTC)_(1D|2D|3D|5D|8D)\.json$', u)
        if m:
            k = f'{m.group(1)} {m.group(2)}'
            if k in self.candles: return f(self.candles[k], 'application/json')
            bars = self.bars(m.group(1), m.group(2))
            return f(json.dumps({'chart': k, 'bars': bars}) if bars is not None else None, 'application/json')
        return route.fulfill(status=404, body='x')

    def goto(self, view='now'):
        self.pg.goto('http://site.test/#' + view); self.pg.wait_for_timeout(700)

    def now(self): return self.pg.evaluate(EXTRACT_NOW)

    def chart(self):
        self.pg.wait_for_timeout(250); return self.pg.evaluate(EXTRACT_CHART)

    def close(self): self.b.close()


# ------------------------------------------------------------------------------------------- expectations
def edge_of(mc): return mc['_edge']


def exp_card(mine, mc, kind, mo=None, is_best=False):
    """expected pieces of the Now card, from my model"""
    a, tf, g = mc['asset'], mc['timeframe'], mc['grade']
    mis = mine['example_if_it_misses'] if kind == 'example' else next((m for m in mine['if_it_misses'] if m['asset'] == a and m['grade'] == g), None)
    top = g == 'A+'
    e = {}
    e['where'] = f'{a} · {tf} chart' + (' · example' if kind == 'example' else '')
    e['state'] = {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind]
    if kind == 'forming':
        line = f"Low {date_long(mc['low_day'])} · confirms {date_long(mc['confirms_on'])}" + (f" if it closes above {money(mc['must_close_above'])}" if mc['must_close_above'] else '')
        note = ("Not confirmed yet. It can still vanish before it confirms." if top else
                ("Best setup forming today." if is_best else "Setup forming.") + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
    elif kind == 'open':
        line = f"Confirmed {date_long(mo['entry_date'])} · entry close {money(mo['entry_close'])} · day {mo['days_elapsed']} of 60 · best so far {pct(mo['best_so_far_pct'])} · worst {pct(mo['worst_so_far_pct'])}"
        lv = mo['edge_level_pct']; stt = mo['edge_status']
        if stt == 'lost': note = 'Edge lost. ' + ('Its odds were below the bar from the entry.' if lv == 0 else f'It fell to its edge level ({pct(lv, 0)}) before rising 10%.')
        elif stt == 'rose10': note = 'Rose 10%. ' + ('It has risen 10% from the entry close.' if lv is None else f'It rose 10% before falling to its edge level ({pct(lv, 0)}).')
        else: note = 'On track. ' + ('It has neither risen 10% nor lost its edge; its odds hold at every fall measured.' if lv is None else f'It has not fallen to its edge level ({pct(lv, 0)}) or risen 10% yet.')
        note += ' The odds below are as of the entry close, not from today.'
    else:
        line = f"Example: confirmed {date_long('2024-09-22')} · entry close {money(mc['entry_close'])}"; note = None
    e['headSmall'] = [line] + ([note] if note else [])
    n = mc['past_trades']
    e['odds'] = [pc(mc['rose10_within60d_pct']), 'rose 10% within 60 days' + (' · at the entry close, not from today' if kind == 'open' else ''),
                 f"{pc(mc['rose10_never_fell25_within60d_pct'])} did it without ever falling 25.3%", f"from {mc['sample']} · every figure covers the 60 days after entry"]
    edge = edge_of(mc)
    etxt = 'Below the 70% bar from entry' if edge == 0 else f'{pct(edge, 0)} before it rises 10%' if edge is not None else 'Holds at every level'
    mtxt = 'n/a' if not mis else 'none missed' if not mis['misses'] else f"{mis['up_first']} of {mis['misses']} · median best {pct(mis['median_peak_pct'])}"
    e['stats'] = [['Typical high', pct(mc['typical_biggest_rise_exact_pct'])], ['Typical drop from entry', pct(mc['typical_deepest_dip_exact_pct'])], ['Edge gone below', etxt],
                  ['If it misses: went above entry', mtxt]]
    grp = 'top-grade' if top else 'same-grade'
    pool_txt = (f"{'of the' if kind == 'example' else 'of all'} {mis['signals']} {a} {grp} signals" + (' known by then' if kind == 'example' else '')) if mis and mis['signals'] else None
    e['pool'] = [pool_txt] if pool_txt else []
    e['marker'] = 'Lead trader: unavailable'
    msuf = (f" · {mis['misses']} misses of {'the' if kind == 'example' else 'all'} {mis['signals']} {a} {grp} signals" + (' known by then' if kind == 'example' else '')) if mis and mis['signals'] else ''
    day = lambda v: 'n/a' if v is None else f'Day {v}'
    e['tiles'] = [['Dip before the high, from entry', pct(mc['typical_dip_before_rise_exact_pct'])], ['High lands around', day(mc['typical_day_of_60d_high'])],
                  [f'Reached +20% within 60 days · n {n}', pc(mc['rose20_within60d_pct'])], [f'Touched {MINUS}30% within 60 days · n {n}', pc(mc['fell30_within60d_pct'])],
                  ['Typical high', pct(mc['typical_biggest_rise_exact_pct'])], ['Deepest dip lands around', day(mc['typical_day_of_deepest_dip'])],
                  ['Typical worst drop, misses' + msuf, pct(mis['median_worst_drop_pct']) if mis else 'n/a'], ['Typical change by day 60, misses' + msuf, pct(mis['median_day60_pct']) if mis else 'n/a']]
    fe = mc['from_entry']
    gone = lambda x: x is not None and x < 70
    lad = [dict(lab=f'From entry n {n}', val=pc(fe['still_rose10_pct']), gone=gone(fe['still_rose10_exact_pct']), w=f"{fe['still_rose10_pct'] or 0}%")]
    for r in mc['if_it_falls_first']:
        lad.append(dict(lab=f"Falls {r['fell_pct']}% first n {r['past_trades']}", val=pc(r['still_rose10_pct']), gone=gone(r['still_rose10_exact_pct']), w=f"{r['still_rose10_pct'] or 0}%"))
    e['ladder'] = lad
    e['ladderFine'] = "Share of this setup's past signals that, after first falling that far, still rose 10% before ever falling 25.3%. Below 70% the edge is gone. Small samples: read the n."
    e['eras'] = [dict(lab=f"{t} n {x['past_trades']}", val=pc(x['rose10_never_fell25_within60d_pct']), gone=False, w=f"{x['rose10_never_fell25_within60d_pct'] or 0}%")
                 for t, x in (('Before 2022', mc['before_2022']), ('Since 2022', mc['since_2022']))]
    e['lbls'] = ['Where the odds fade · this setup', 'By era']
    e['frame'] = 'var(--fade)' if (kind == 'forming' and not top) or (kind == 'open' and mo['edge_status'] == 'lost') else 'var(--live)'
    e['bigDim'] = kind == 'open' and mo['edge_status'] == 'lost'
    return e


NUMTOK = re.compile(r'[+−-]?\$?\d[\d,]*(?:\.\d+)?%?')


def cmp_card(ck, loc, got, e):
    for k in ('where', 'state', 'marker', 'ladderFine', 'frame'): ck.add(loc, k, nt(got.get(k)), nt(e[k]), 'page card')
    for k in ('headSmall', 'odds', 'pool', 'lbls'):
        ck.add(loc, f'{k} count', len(got[k]), len(e[k]))
        for i, v in enumerate(e[k]): ck.add(loc, f'{k}[{i}]', nt(got[k][i]) if i < len(got[k]) else None, nt(v), 'page card')
    for k in ('stats', 'tiles'):
        ck.add(loc, f'{k} count', len(got[k]), len(e[k]))
        for i, (t, v) in enumerate(e[k]):
            g = got[k][i] if i < len(got[k]) else [None, None]
            ck.add(loc, f'{k}[{i}] label', nt(g[0]), nt(t), 'page card label'); ck.add(loc, f'{k}[{i}] {t[:40]}', nt(g[1]), nt(v), 'page card figure')
    for k in ('ladder', 'eras'):
        ck.add(loc, f'{k} rows', len(got[k]), len(e[k]))
        for i, r in enumerate(e[k]):
            g = got[k][i] if i < len(got[k]) else {}
            ck.add(loc, f'{k}[{i}] label', nt(g.get('lab')), nt(r['lab']), 'ladder/era label and n'); ck.add(loc, f'{k}[{i}] value {r["lab"]}', nt(g.get('val')), r['val'], 'ladder/era share')
            ck.add(loc, f'{k}[{i}] below-bar mark {r["lab"]}', g.get('gone'), r['gone'], '70% bar on the exact share'); ck.add(loc, f'{k}[{i}] bar width {r["lab"]}', g.get('w'), r['w'], 'bar width')
    ck.add(loc, 'big number dimmed', 'opacity: 0.5' in (got.get('bigStyle') or ''), e['bigDim'], 'edge-lost card dimmed')
    ck.add(loc, 'foot', FOOT in (got.get('foot') or ''), True)
    # every numeric token on the card is one I expect
    allexp = ' '.join([e['where'], e['state']] + e['headSmall'] + e['odds'] + [x for p in e['stats'] for x in p] + e['pool'] + [x for p in e['tiles'] for x in p]
                      + [r['lab'] + ' ' + r['val'] for r in e['ladder'] + e['eras']] + [e['ladderFine'], 'Share that rose 10% and never fell 25.3%.', FOOT, "Past results don't guarantee future results."])
    want = sorted(NUMTOK.findall(nt(allexp))); have = sorted(NUMTOK.findall(nt(got['text'])))
    ck.add(loc, 'every number on the card accounted for', json.dumps(have), json.dumps(want), 'unexpected or missing number on the card')


def bar_dates(bars, tfd, extend_to=None):
    opens = [dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date() for b in bars]
    if extend_to is not None:
        while opens[-1] <= extend_to: opens.append(C.next_open(opens[-1], tfd))
    return opens


def slot_of(opens, d):
    i = 0
    while i + 1 < len(opens) and opens[i + 1] <= d: i += 1
    return i


def close_enough(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def check_chart(ck, loc, got, mine, mc, kind, bars, tfd, mo=None, happened=False, feed_day=None):
    """bars: the chart file's bars (dicts). kind forming/open/example."""
    a = mc['asset']; top = mc['grade'] == 'A+'
    if kind == 'example':
        entry = mc['entry_close']; entry_day = dt.date(2024, 9, 22)
        title = 'ETH · 2-day · example: past confirmed setup'
        sub = f"Confirmed {date_long('2024-09-22')} · entry close {money(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them."
    elif kind == 'open':
        entry = mo['entry_close']; entry_day = dt.date.fromisoformat(mo['entry_date'])
        title = f"{mc['chart'].replace(' ', ' · ')} · live setup, day {mo['days_elapsed']} of 60"
        sub = f"Confirmed {date_long(mo['entry_date'])} · entry close {money(entry)}. Zones use this setup's own card ({mc['sample']})."
    else:
        entry = mc['price_now']; entry_day = dt.date.fromisoformat(mc['confirms_on'])
        title = f"{a} · {mc['timeframe']} · {'setup forming' if top else 'forming, not top grade'}"
        sub = (f"Low {date_long(mc['low_day'])} · confirms {date_long(mc['confirms_on'])} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; "
               "days count from the confirmation.")
    if not happened: sub += ' The shaded zones are the next 60 days, as the odds draw them.'
    ck.add(loc, 'title', nt(got['title']), nt(title), 'chart title'); ck.add(loc, 'subtitle', nt(got['sub']), nt(sub), 'chart subtitle')
    ck.add(loc, 'view toggle hidden', got['toggleHidden'], kind != 'example')
    future = kind != 'example'
    opens = bar_dates(bars, tfd, entry_day + dt.timedelta(days=61) if future else None)
    last_day = lambda i: C.next_open(opens[i], tfd) - D1
    # slots from the drawn candles
    wicks = [l for l in got['lines'] if l['sw'] == '1.5' and l['x1'] == l['x2'] and not (l['y1'] == 24 and l['y2'] == 480)]
    vl = [l for l in got['lines'] if l['x1'] == l['x2'] and l['y1'] == 24 and l['y2'] == 480]
    hl = [l for l in got['lines'] if l['sw'] == '2' and l['y1'] == l['y2']]
    n_draw = len(bars) if (future or happened) else None
    E = next((i for i in range(len(bars)) if last_day(i) == entry_day), None) if kind != 'forming' else len(bars) - 1
    if n_draw is None: n_draw = E + 1
    ck.add(loc, 'candles drawn', len(wicks), n_draw, 'At the alert shows nothing after the entry bar' if kind == 'example' and not happened else 'candle count')
    if len(wicks) < 2 or len(hl) < 4:
        ck.flag(loc, 'chart drawn', f'{len(wicks)} candles, {len(hl)} levels', 'a chart', 'chart not drawn'); return
    x0 = wicks[0]['x1']; slot = wicks[1]['x1'] - wicks[0]['x1']
    idx = lambda x: (x - x0) / slot
    isl = lambda x: round(idx(x))
    ck.add(loc, 'candles evenly spaced in bar order', all(abs(idx(w['x1']) - i) < 1e-6 for i, w in enumerate(wicks)), True)
    # price scale from the entry and +10% lines
    high_p = px_at(entry, mc['typical_biggest_rise_exact_pct']); t10 = px_at(entry, 10); drop_p = px_at(entry, mc['typical_deepest_dip_exact_pct'])
    yh, yt, ye, yd = (l['y1'] for l in hl[:4])
    P = lambda y: entry + (ye - y) / (ye - yt) * (t10 - entry)
    ck.add(loc, 'typical-high line at its price', close_enough(P(yh), high_p), True, f'line at {P(yh):.4f}, expected {high_p}')
    ck.add(loc, 'typical-drop line at its price', close_enough(P(yd), drop_p), True, f'line at {P(yd):.4f}, expected {drop_p}')
    badw = [i for i, w in enumerate(wicks) if not (close_enough(P(w['y1']), bars[i]['h']) and close_enough(P(w['y2']), bars[i]['l']))]
    ck.add(loc, 'every candle drawn at its high and low', len(badw), 0, f'first bad bar {badw[:1]}')
    known = bars if (future or happened) else bars[:E + 1]
    lo = min(min(b['l'] for b in known), drop_p, entry * 0.8) * 0.95; hi = max(max(b['h'] for b in known), high_p) * 1.07
    ck.add(loc, 'axis bottom uses only what was known', close_enough(P(480), lo, 1e-5), True, f'axis low {P(480):.4f}, expected {lo:.4f}')
    ck.add(loc, 'axis top uses only what was known', close_enough(P(24), hi, 1e-5), True, f'axis high {P(24):.4f}, expected {hi:.4f}')
    # price tags
    tags = [t['s'] for t in got['texts'] if t['fill'] == '#07060F']
    ck.add(loc, 'price tags (high, +10%, entry, drop)', json.dumps(sorted(tags)), json.dumps(sorted(money(p) for p in (high_p, t10, entry, drop_p))), 'price built by exact decimal arithmetic on cents')
    texts = [nt(t['s']) for t in got['texts']]
    has = lambda s: nt(s) in texts
    ck.add(loc, 'label: typical high', has(f"Typical high {pct(mc['typical_biggest_rise_exact_pct'])}"), True, 'chart label')
    ck.add(loc, 'label: +10% share', has(f"+10% · {pc(mc['rose10_within60d_pct'])} of past signals got here"), True, 'chart label')
    ck.add(loc, 'label: typical drop', has(f"Typical drop {pct(mc['typical_deepest_dip_exact_pct'])}"), True, 'chart label')
    # grid price labels sit at their own price; date labels at their own bar
    for t in got['texts']:
        s = t['s']
        if t['x'] == 968 and s.startswith('$'):
            v = float(s[1:].replace(',', ''))
            tol = 0.5 if (hi - lo) >= 200 else abs(v) * 1e-3 + 1e-9
            ck.add(loc, f'axis label {s} at its price', abs(P(t['y'] - 5) - v) <= tol + 1e-6, True, f'label {s} drawn at {P(t["y"] - 5):.3f}')
        if t['y'] == 502:
            i = isl(t['x']); d = opens[min(i, len(opens) - 1)]
            ck.add(loc, f'date label at slot {i}', nt(s), f'{d.day:02d} {MON[d.month]}', 'x-axis date')
    # vertical lines by date
    vtext = {}
    for l in vl:
        lab = [t for t in got['texts'] if abs(t['x'] - (l['x1'] + 6)) < 1e-6 and t['y'] in (36, 54, 72, 472)]
        for t in lab: vtext[nt(t['s'])] = isl(l['x1'])
    day60 = min(len(opens) - 1, slot_of(opens, entry_day + dt.timedelta(days=60))) if future else min(len(bars) - 1, slot_of(opens, entry_day + dt.timedelta(days=60)))
    exp_v = {}
    if kind == 'forming':
        lastbar_today = feed_day is None or last_day(len(bars) - 1) >= feed_day
        exp_v['Today' if lastbar_today else f'Latest bar · {date_long(opens[len(bars) - 1])}'] = len(bars) - 1
        conf_slot = slot_of(opens, entry_day)
        if conf_slot > len(bars) - 1: exp_v[f"Confirms {date_long(mc['confirms_on'])} · entry, day 0"] = conf_slot
        A_ = conf_slot
    else:
        exp_v['Entry'] = E; A_ = E
    hd = mc['typical_day_of_60d_high']
    if hd is not None: exp_v[f'High usually ~day {hd}'] = slot_of(opens, entry_day + dt.timedelta(days=hd))
    exp_v['Day 60'] = day60
    ck.add(loc, 'vertical lines: labels and bars', json.dumps(sorted(vtext.items())), json.dumps(sorted(exp_v.items())), 'a day line is not on the bar that holds its calendar day')
    if kind != 'forming':
        ck.add(loc, 'Entry bar closes on the entry date', str(last_day(E)) if E is not None else None, str(entry_day))
    # zones: from the entry bar to the day-60 bar; high zone entry..typical high, drop zone entry..typical drop
    zh = next((r for r in got['rects'] if r['op'] == '0.07'), None); zd = next((r for r in got['rects'] if r['op'] == '0.1'), None)
    if zh and zd:
        ck.add(loc, 'zones start on the entry bar', [isl(zh['x']), isl(zd['x'])], [A_, A_]); ck.add(loc, 'zones end on the day-60 bar', [isl(zh['x'] + zh['w']), isl(zd['x'] + zd['w'])], [day60, day60])
        ck.add(loc, 'high zone spans entry to typical high', close_enough(P(zh['y']), high_p) and close_enough(P(zh['y'] + zh['h']), entry), True)
        ck.add(loc, 'drop zone spans entry to typical drop', close_enough(P(zd['y']), entry) and close_enough(P(zd['y'] + zd['h']), drop_p), True)
    else: ck.flag(loc, 'zones', 'missing', 'two zones', 'zones not drawn')
    # ladder bands
    fe = mc['from_entry']; rows = mc['if_it_falls_first']
    steps = [(0, -5, fe['still_rose10_pct'], fe['still_rose10_exact_pct'], mc['past_trades'])] + [(-r['fell_pct'], -(rows[k + 1]['fell_pct'] if k + 1 < len(rows) else r['fell_pct'] + 5), r['still_rose10_pct'], r['still_rose10_exact_pct'], r['past_trades']) for k, r in enumerate(rows[:3])]
    bands = [r for r in got['rects'] if r['op'] == '0.24']
    ck.add(loc, 'ladder bands', len(bands), len(steps))
    for (a1, b1, v, vx, nn), r in zip(steps, bands):
        lab = 'n/a' if v is None else f'{v}% · n {nn}'
        col = 'var(--closed)' if v is None else 'var(--high)' if vx >= 70 else 'var(--drop)'
        ck.add(loc, f'band {a1}..{b1} label', has(lab), True, f'expected "{lab}"'); ck.add(loc, f'band {a1}..{b1} colour (exact share vs 70%)', r['fill'], col, 'band colour')
        ck.add(loc, f'band {a1}..{b1} starts on the entry bar', isl(r['x']), A_)
        y2e = min(480.0, ye + (entry * (1 + b1 / 100) - entry) / (t10 - entry) * (yt - ye))
        ck.add(loc, f'band {a1}..{b1} spans its prices', close_enough(P(r['y']), entry * (1 + a1 / 100), 1e-5) and abs((r['y'] + r['h']) - y2e) < 1e-3, True, 'band position')
    edge = edge_of(mc)
    eline = [l for l in got['lines'] if l['sw'] == '2.5']
    if edge:
        ep = px_at(entry, edge)
        ck.add(loc, 'edge line drawn', len(eline), 1)
        if eline: ck.add(loc, 'edge line at its price', close_enough(P(eline[0]['y1']), ep), True, f'line at {P(eline[0]["y1"]):.4f}, expected {ep}')
        ck.add(loc, 'edge label', has(f'Edge gone below {money(ep)} ({pct(edge, 0)}, before +10%)'), True, f'expected Edge gone below {money(ep)} ({pct(edge, 0)}, before +10%)')
    else: ck.add(loc, 'no edge line when the edge is 0 or none', len(eline), 0)
    # the low marker (forming) / the outcome (example, what happened)
    S = mine['S']
    if kind == 'forming':
        li = next((i for i, d in enumerate(opens[:len(bars)]) if str(d) == mc['low_date']), None)
        if li is not None:
            ck.add(loc, 'low marker label', has(f"Low {date_long(mc['low_day'])} · {money(bars[li]['l'])}"), True, 'low marker')
            ck.add(loc, 'low marker on the trough bar at its low', bool(got['circles']) and isl(got['circles'][0]['x']) == li and close_enough(P(got['circles'][0]['y']), bars[li]['l']), True)
            # my own value: the lowest daily low inside the trough bar
            dl = S.day[a]; d0 = dt.date.fromisoformat(mc['low_date']); nx = C.next_open(d0, tfd)
            lows = [dl.l[dl.pos[d0 + dt.timedelta(days=j)]] for j in range((nx - d0).days) if d0 + dt.timedelta(days=j) in dl.pos]
            ck.add(loc, 'low price = lowest daily low inside the trough bar', bars[li]['l'], min(lows), 'low price')
    elif kind == 'example' and happened:
        dl = S.day['ETH']; w = S.window('ETH', entry_day)
        kh = max(w, key=lambda k: (dl.h[k], -k)); kl = min(w, key=lambda k: (dl.l[k], k))
        for name, k, p in (('high', kh, dl.h[kh]), ('low', kl, dl.l[kl])):
            dd = (dl.date[k] - entry_day).days
            pat = re.compile(rf"^This one: {re.escape(money(p))} · {re.escape(pct((p / entry - 1) * 100))} · (?:day (\d+)|days (\d+)–(\d+))$")
            mm = [pat.match(t) for t in texts]; mm = [m for m in mm if m]
            ok = bool(mm) and ((mm[0].group(1) and int(mm[0].group(1)) == dd) or (mm[0].group(2) and int(mm[0].group(2)) <= dd <= int(mm[0].group(3))))
            ck.add(loc, f'outcome marker: 60-day {name}', ok, True, f'expected {money(p)} · {pct((p / entry - 1) * 100)} on day {dd}; drawn: {[t for t in texts if t.startswith("This one")]}')
        ck.add(loc, 'two outcome markers', len(got['circles']), 2)
    if kind == 'example' and not happened:
        ck.add(loc, 'At the alert shows no outcome', any(t.startswith('This one') for t in texts) or len(got['circles']) > 0, False)
    # ---- every text on the chart is one I expect (nothing unexplained)
    known_txt = {nt(f"Typical high {pct(mc['typical_biggest_rise_exact_pct'])}"), nt(f"+10% · {pc(mc['rose10_within60d_pct'])} of past signals got here"), nt(f"Typical drop {pct(mc['typical_deepest_dip_exact_pct'])}")}
    known_txt |= {nt(k) for k in exp_v} | {('n/a' if v is None else f'{v}% · n {nn}') for (a1, b1, v, vx, nn) in steps}
    if edge: known_txt.add(nt(f'Edge gone below {money(px_at(entry, edge))} ({pct(edge, 0)}, before +10%)'))
    stray = []
    for t in got['texts']:
        sx = nt(t['s'])
        if t['fill'] == '#07060F' or (t['x'] == 968 and sx.startswith('$')) or t['y'] == 502 or sx in known_txt: continue
        if kind == 'forming' and sx.startswith('Low ') or (kind == 'example' and happened and sx.startswith('This one: ')): continue   # checked above
        stray.append(sx)
    ck.add(loc, 'no unexplained text on the chart', json.dumps(stray), '[]', 'a chart text I did not expect')
    side_all = ' '.join(b['text'] for b in got['side'])
    # ---- cloud
    pp = mine.get('example_past_paths') if kind == 'example' else next((p for p in mine['past_paths'] if p['asset'] == a), None)
    if pp:
        X = lambda d: 20 + 940 * d / 60; Y = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
        pts = lambda s: [tuple(float(z) for z in p.split(',')) for p in s.split(' ')]
        gm = pts(got['poly'][0]) if got['poly'] else []
        ck.add(loc, 'cloud median path (61 points)', all(len(gm) == 61 and close_enough(gm[i][0], X(i)) and close_enough(gm[i][1], Y(d['median_pct'])) for i, d in enumerate(pp['days'])), True, 'median path')
        gb = pts(got['polygon'][0]) if got['polygon'] else []
        eb = [(X(d['day']), Y(d['q75_pct'])) for d in pp['days']] + [(X(d['day']), Y(d['q25_pct'])) for d in reversed(pp['days'])]
        ck.add(loc, 'cloud middle half (q25-q75)', len(gb) == len(eb) and all(close_enough(g[0], e_[0]) and close_enough(g[1], e_[1]) for g, e_ in zip(gb, eb)), True, 'quartile band')
        last = pp['days'][-1]
        subx = f"ETH top-grade signals whose 60 days had closed by 22 Sep 2024, n {pp['signals']}" if kind == 'example' else f"Every past {a} top-grade signal, n {pp['signals']}"
        ck.add(loc, 'cloud subtitle', nt(got['cloudSub']), subx, 'cloud n')
        note = f"Day 60: median {pct(last['median_pct'])}, middle half {pct(last['q25_pct'])} to {pct(last['q75_pct'])}. Daily closes."
        ck.add(loc, 'cloud day-60 note', note in nt(got['cloudNote']), True, f'expected "{note}" in "{nt(got["cloudNote"])}"')
        ck.add(loc, 'cloud "not top grade" remark', "the selected setup isn't top grade" in got['cloudNote'], kind != 'example' and not top)
        if kind == 'example' and happened:
            dl = S.day['ETH']; g2 = pts(got['poly'][1]) if len(got['poly']) > 1 else []
            e2 = [(X(0), Y(0))] + [(X(2 * k), Y((dl.c[dl.pos[entry_day + dt.timedelta(days=2 * k)]] / entry - 1) * 100)) for k in range(1, 31)]
            ck.add(loc, 'cloud: this signal\'s path = daily closes on even days', len(g2) == 31 and all(close_enough(g[0], e_[0]) and close_enough(g[1], e_[1]) for g, e_ in zip(g2, e2)), True)
    # ---- side box
    sb = got['side'][0] if got['side'] else {'kv': [], 'text': ''}
    es = 'below the bar already' if edge == 0 else 'holds at every level' if edge is None else f'{money(px_at(entry, edge))} ({pct(edge, 0)})'
    ekv = [['Typical high', f"{pct(mc['typical_biggest_rise_exact_pct'])} · {money(high_p)}"], ['+10% level', money(t10)], ['Reached +20% within 60 days', pc(mc['rose20_within60d_pct'])],
           ['Typical drop', f"{pct(mc['typical_deepest_dip_exact_pct'])} · {money(drop_p)}"], ['Edge gone below', es]]
    ck.add(loc, 'side box rows', len(sb['kv']), len(ekv))
    for i, (t, v) in enumerate(ekv):
        g = sb['kv'][i] if i < len(sb['kv']) else [None, None]
        ck.add(loc, f'side: {t} label', nt(g[0]), t); ck.add(loc, f'side: {t}', nt(g[1]), nt(v), 'side box figure')
    head = f"{mc['chart']}{' · example' if kind == 'example' else ''} · from {mc['sample']}{' · odds as of the entry close, not from today' if kind == 'open' else ''}"
    ck.add(loc, 'side: sample line', nt(head) in nt(sb['text']), True, f'expected "{head}"')
    s2 = f"{pc(mc['rose10_within60d_pct'])}rose 10% within 60 days, from {mc['past_trades']} past signals; {pc(mc['rose10_never_fell25_within60d_pct'])} without ever falling 25.3%"
    ck.add(loc, 'side: big number, n, surv10', nt(s2).replace(' ', '') in nt(sb['text']).replace(' ', ''), True, f'expected "{s2}"')
    b2 = got['side'][1] if len(got['side']) > 1 else {'kv': [], 'text': '', 'title': None}
    if kind == 'open':
        ck.add(loc, 'live box title', nt(b2['title']), f"Live: day {mo['days_elapsed']} of 60", 'day in progress')
        ekv2 = [['Best so far', pct(mo['best_so_far_pct'])], ['Worst so far', pct(mo['worst_so_far_pct'])], ['Day 10', 'not yet' if mo['day10_pct'] is None else pct(mo['day10_pct'])]]
        for i, (t, v) in enumerate(ekv2):
            g = b2['kv'][i] if i < len(b2['kv']) else [None, None]
            ck.add(loc, f'live box: {t}', nt(g[1]), v, 'live progress')
    elif kind == 'forming':
        ck.add(loc, 'forming box date', f"It confirms only if it holds through {date_long(mc['confirms_on'])}" in nt(b2['text']), True)
    elif happened:
        dl = S.day['ETH']; w = S.window('ETH', entry_day); ec = round(entry * 100)
        hi_ = max(dl.h[k] for k in w); lo_ = min(dl.l[k] for k in w)
        dh = (dl.date[next(k for k in w if dl.h[k] == hi_)] - entry_day).days; dlw = (dl.date[next(k for k in w if dl.l[k] == lo_)] - entry_day).days
        c10 = dl.c[dl.pos[entry_day + dt.timedelta(days=10)]]; c60 = dl.c[dl.pos[entry_day + dt.timedelta(days=60)]]
        kv = {x[0]: x[1] for x in b2['kv']}
        ck.add(loc, 'what this one did: +10% / +20%', kv.get('Reached +10% / +20%'), f"{'Yes' if round(hi_ * 100) * 100 >= ec * 110 else 'No'} / {'Yes' if round(hi_ * 100) * 100 >= ec * 120 else 'No'}", 'outcome')
        def rng(txt, val, dd):
            m = re.match(rf"^{re.escape(val)}, days (\d+)–(\d+)$", nt(txt or ''))
            return bool(m) and int(m.group(1)) <= dd <= int(m.group(2))
        ck.add(loc, 'what this one did: best price', rng(kv.get('Best price'), pct((hi_ / entry - 1) * 100), dh), True, f"shown {kv.get('Best price')}; mine {pct((hi_ / entry - 1) * 100)} on day {dh}")
        ck.add(loc, 'what this one did: deepest drop', rng(kv.get('Deepest drop'), pct((lo_ / entry - 1) * 100), dlw), True, f"shown {kv.get('Deepest drop')}; mine {pct((lo_ / entry - 1) * 100)} on day {dlw}")
        ck.add(loc, 'what this one did: day 10 check', nt(kv.get('Day 10 check')), f"{'Red' if c10 < entry else 'Green'}, {pct((c10 / entry - 1) * 100)}", 'day-10 close')
        ck.add(loc, 'what this one did: price on day 60', nt(kv.get('Price on day 60')), pct((c60 / entry - 1) * 100), 'day-60 close')
    ck.add(loc, 'side: entry-quality footer', any('Entry quality only' in x for x in got['sideFine']), True)
