"""Audit 19: page harness (Playwright) and my own formatting of what the page should show."""
import csv, json, os, re, datetime as dt
from decimal import Decimal
from fractions import Fraction as Fr
from lib import rha, next_open, bar_open_of, tf_days, DAY

MINUS = '−'
OVERRIDES = {}   # mutation tests set this
MONTHS = None   # filled from the browser's en-GB short month names (text, not a figure)


def DL(iso):
    d = dt.date.fromisoformat(str(iso)[:10]); return f'{d.day} {MONTHS[d.month - 1]} {d.year}'


def pct(v, d=1, sign=True):
    if v is None or v == '': return 'n/a'
    x = rha(v, d) if isinstance(v, Fr) else rha(Decimal(str(v)), d)
    if x == 0: return f'{Decimal(0):.{d}f}%'
    s = f'{abs(x):.{d}f}'
    return ('+' if x > 0 and sign else MINUS if x < 0 else '') + s + '%'


def pc(v): return 'n/a' if v is None or v == '' else f'{v}%'


def money(v):
    if v is None: return 'n/a'
    x = rha(Decimal(str(v)), 2); return ('-' if x < 0 else '') + '$' + f'{abs(x):,.2f}'


def px_at(entry, p):
    """a price p percent from the entry: exact decimal arithmetic on cents, half away from zero"""
    if entry is None or p is None: return None
    cents = rha(Decimal(str(entry)) * 100, 0)
    return rha(Fr(int(cents)) * (Fr(100) + Fr(Decimal(str(p)))) / 100, 0) / 100


def norm(s): return None if s is None else re.sub(r'\s+', ' ', s).strip()


WRAP = '<!doctype html><html><head><meta charset=utf-8></head><body>{}</body></html>'


def candles_json(root, chart):
    a, tf = chart.split('_') if '_' in chart else chart.split(' ')
    p = os.path.join(root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p): return None
    bars = [dict(t=int(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
    return dict(chart=f'{a} {tf}', bars=bars)


class Site:
    """serves one state to the page; any file can be overridden (bytes/str/dict) or dropped (None -> 404)"""
    def __init__(self, root, overrides=None, page_html=None):
        self.root = root; self.ov = dict(OVERRIDES, **(overrides or {}))
        self.html = page_html or open(os.path.join(root, 'docs/artifacts/member-site/index.html')).read()

    def body(self, path):
        if path in self.ov:
            v = self.ov[path]
            return None if v is None else (json.dumps(v) if isinstance(v, (dict, list)) else v)
        r = self.root
        if path == 'data/ctzb_feed.json': return open(os.path.join(r, 'feed/ctzb_feed.json')).read()
        if path == 'data/ledger.csv': return open(os.path.join(r, 'datasets/ledger.csv')).read()
        m = re.fullmatch(r'data/candles/((?:ETH|BTC)_(?:1D|2D|3D|5D|8D))\.json', path)
        if m:
            j = candles_json(r, m.group(1)); return None if j is None else json.dumps(j)
        if path == 'data/example_ETH-2D-2024-09-22.json':
            p = os.path.join(r, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')
            return open(p).read() if os.path.exists(p) else None
        return None

    def open(self, browser, at_iso, hash_='', viewport=(1500, 1100)):
        global MONTHS
        ctx = browser.new_context(viewport=dict(width=viewport[0], height=viewport[1]))
        page = ctx.new_page()
        self.errors = []
        page.on('pageerror', lambda e: self.errors.append(str(e)))
        def handle(route):
            u = route.request.url
            if 'fonts.g' in u: return route.abort()
            if not u.startswith('http://site.test/'): return route.abort()
            path = u[len('http://site.test/'):].split('?')[0].split('#')[0]
            if path == '': return route.fulfill(status=200, content_type='text/html; charset=utf-8', body=WRAP.format(self.html))
            b = self.body(path)
            if b is None: return route.fulfill(status=404, body='not found')
            return route.fulfill(status=200, content_type='application/json' if path.endswith('.json') else 'text/csv', body=b)
        page.route('**/*', handle)
        page.clock.install(time=dt.datetime.fromisoformat(at_iso.replace('Z', '+00:00')))
        page.goto('http://site.test/' + hash_)
        page.wait_for_function("document.querySelector('#card') && document.querySelector('#card').innerHTML.length > 0", timeout=10000)
        page.wait_for_timeout(150)
        if MONTHS is None:
            MONTHS = page.evaluate("Array.from({length:12},(_, i) => new Date(Date.UTC(2024, i, 15)).toLocaleDateString('en-GB', {month:'short', timeZone:'UTC'}))")
        return page


JS_NOW = r"""() => {
  const T = (el) => el ? el.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => Array.from(r.querySelectorAll(s));
  const c = document.querySelector('#card');
  const bars = (sel) => q(sel + ' .bar').map((b) => ({ label: T(b.children[0]), val: T(b.children[2]), gone: !!b.querySelector('.f.gone'), width: b.querySelector('.f') ? b.querySelector('.f').style.width : null }));
  const big = c.querySelector('.odds .big');
  return {
    banner: T(document.querySelector('#review span')), filter: T(document.querySelector('#filterText')), pillOff: document.querySelector('#filterPill').classList.contains('off'),
    foot: T(document.querySelector('#feedState')), footer: T(document.querySelector('footer.foot .fine')), howBar: T(document.querySelector('#howBar')),
    preview: document.querySelector('#previewSwitch').checked,
    picker: q('#picker .pick').map((b) => ({ t: T(b), sel: b.dataset.sel, pressed: b.getAttribute('aria-pressed'), cls: b.className })), pnone: q('#picker .pnone').map(T),
    lead: T(document.querySelector('#leadBody')), trades: q('#leadBody .trade').map(T),
    frame: document.querySelector('#cardFrame').style.getPropertyValue('--c'),
    card: { where: T(c.querySelector('.where')), state: T(c.querySelector('.state')), dstate: c.querySelector('.state') ? c.querySelector('.state').dataset.state || null : null,
      smalls: q('.card-head .small', c).map(T), stale: T(c.querySelector('.stale-note')), empty: T(c.querySelector('.empty-card')),
      big: T(big), bigOpacity: big ? big.style.opacity : null, odds: q('.odds > div', c).map(T),
      kv: q('.stats .kv', c).map((k) => [T(k.children[0]), T(k.children[1])]), pool: T(c.querySelector('.stats .fine')), marker: T(c.querySelector('.marker')),
      tiles: q('.tile', c).map((t) => [T(t.querySelector('.t')), T(t.querySelector('.v'))]),
      ladderLbl: q('.box .lbl', c).map(T), ladder: bars('#ladder'), ladderNote: T(c.querySelector('#ladder .fine')), eras: bars('#eras'), foot: T(c.querySelector('.card-foot .fine')) },
    prevIntact: q('#prevIntact .mini').map((m) => ({ name: T(m.querySelector('.name')), sub: T(m.querySelector('.sub')), badge: T(m.querySelector('.badge')) })), prevIntactNone: T(document.querySelector('#prevIntact .none')),
    prevClosed: q('#prevClosed .mini').map((m) => ({ cls: m.className, name: T(m.querySelector('.name')), sub: T(m.querySelector('.sub')), badge: T(m.querySelector('.badge')), bcls: m.querySelector('.badge').className })),
    prevClosedNone: q('#prevClosed .none').map(T),
    text: document.querySelector('.app').innerText };
}"""

JS_CHART = r"""() => {
  const T = (el) => el ? el.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => Array.from(r.querySelectorAll(s));
  const dump = (svg) => Array.from(svg.children).map((e) => { const o = { tag: e.tagName, text: e.tagName === 'text' ? e.textContent : undefined, fill: e.getAttribute('fill') || e.style.getPropertyValue('fill'), stroke: e.getAttribute('stroke') || e.style.getPropertyValue('stroke') };
    for (const a of ['x', 'y', 'x1', 'x2', 'y1', 'y2', 'width', 'height', 'cx', 'cy', 'points', 'stroke-width', 'stroke-dasharray', 'opacity', 'text-anchor']) if (e.hasAttribute(a)) o[a] = e.getAttribute(a); return o; });
  return { title: T(document.querySelector('#chTitle')), sub: T(document.querySelector('#chSub')), toggleHidden: document.querySelector('.toggle').hidden,
    alertPressed: document.querySelector('#bAlert').getAttribute('aria-pressed'), hapPressed: document.querySelector('#bHap').getAttribute('aria-pressed'),
    svg: dump(document.querySelector('#chartSvg')), cloud: dump(document.querySelector('#cloudSvg')), cloudSub: T(document.querySelector('#cloudSub')), cloudNote: T(document.querySelector('#cloudNote')),
    side: q('#chartSide > *').map((b) => ({ text: T(b), title: T(b.querySelector('.sec-title')), kv: q('.kv', b).map((k) => [T(k.children[0]), T(k.children[1])]), smalls: q('.small', b).filter((x) => !x.closest('.kv')).map(T), big: T(b.querySelector('div[style*="42px"]')), fines: q('.fine', b).map(T) })),
    viewText: document.querySelector('#view-chart').innerText };
}"""

JS_RECORD = r"""() => {
  const T = (el) => el ? el.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => Array.from(r.querySelectorAll(s));
  return { head: T(document.querySelector('#view-record .sec-title')), count: T(document.querySelector('#recCount')), rows: q('#recBody tr').map((tr) => q('td', tr).map(T)),
    badges: q('#recBody tr').map((tr) => q('.badge', tr).map((b) => b.className)),
    sum: q('#recSum .sidebox').map((b) => q('.kv', b).map((k) => [T(k.children[0]), T(k.children[1])])), pressed: q('.seg button').map((b) => [b.dataset.asset, b.getAttribute('aria-pressed')]),
    th: q('#view-record th').map(T), note: T(document.querySelector('#view-record p.fine')) };
}"""
