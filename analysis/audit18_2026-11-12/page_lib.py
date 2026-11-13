"""Audit 18 page harness: serve the member page from a state folder under Playwright and dump what a member reads."""
import csv, json, os, datetime as dt

EXTRACT = r"""
() => {
  const T = (e) => e ? e.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const svg = (id) => qa('#' + id + ' > *').map((e) => {
    const o = { tag: e.tagName, text: e.tagName === 'text' ? e.textContent : undefined };
    for (const a of e.attributes) o[a.name] = a.value;
    return o; });
  const card = q('#card');
  const out = {
    review: T(q('#review')), filter: T(q('#filterText')), filterOff: q('#filterPill').classList.contains('off'), footer: T(q('#feedState')), foot: T(q('footer.foot')),
    picker: qa('#picker .prow').map((r) => ({ label: T(q('.plabel', r)), none: T(q('.pnone', r)), btns: qa('button', r).map((b) => ({ sel: b.dataset.sel, pressed: b.getAttribute('aria-pressed'), cls: b.className, text: T(b) })) })),
    card: {
      where: T(q('.card-head .where', card)), state: T(q('.card-head .state', card)), dstate: q('.card-head .state', card) ? q('.card-head .state', card).dataset.state || null : null,
      head: qa('.card-head .small', card).map(T), stale: T(q('.stale-note', card)), empty: T(q('.empty-card', card)),
      big: T(q('.odds .big', card)), bigDim: q('.odds .big', card) ? q('.odds .big', card).style.opacity : null, odds: qa('.odds > div', card).map(T),
      stats: qa('.stats .kv', card).map((k) => qa(':scope > span', k).map(T)), pool: T(q('.stats > .fine', card)), marker: T(q('.marker', card)),
      tiles: qa('.tile', card).map((t) => [T(q('.t', t)), T(q('.v', t))]), ladderLbl: qa('.box .lbl', card).map(T),
      ladder: qa('#ladder .bar', card).map((b) => ({ t: T(b.children[0]), w: q('.f', b).style.width, gone: q('.f', b).classList.contains('gone'), v: T(b.children[2]) })),
      ladderNote: T(q('#ladder .fine', card)),
      eras: qa('#eras .bar', card).map((b) => ({ t: T(b.children[0]), w: q('.f', b).style.width, v: T(b.children[2]) })),
      foot: T(q('.card-foot', card)), frame: q('#cardFrame').style.getPropertyValue('--c'), all: T(card) },
    lead: T(q('#leadBody')), leadAll: T(q('.frame.lead')),
    prevIntact: qa('#prevIntact > *').map((m) => ({ cls: m.className, name: T(q('.name', m)), sub: T(q('.sub', m)), badge: T(q('.badge', m)), text: T(m) })),
    prevClosed: qa('#prevClosed > *').map((m) => ({ cls: m.className, name: T(q('.name', m)), sub: T(q('.sub', m)), badge: T(q('.badge', m)), bcls: q('.badge', m) ? q('.badge', m).className : null, text: T(m) })),
    chart: { title: T(q('#chTitle')), sub: T(q('#chSub')), toggleHidden: q('.toggle').hidden, alert: q('#bAlert').getAttribute('aria-pressed'), hap: q('#bHap').getAttribute('aria-pressed'),
      svg: svg('chartSvg'), cloud: svg('cloudSvg'), cloudSub: T(q('#cloudSub')), cloudNote: T(q('#cloudNote')),
      side: qa('#chartSide > *').map((b) => ({ text: T(b), title: T(q('.sec-title', b)), kv: qa('.kv', b).map((k) => Array.from(k.children).map(T)), small: qa('.small', b).map(T), fine: qa('.fine', b).map(T), big: T(q('div[style*="42px"]', b)) })) },
    record: { count: T(q('#recCount')), head: T(q('#view-record .rec-head .sec-title')), sum: qa('#recSum .sidebox').map((b) => ({ kv: qa('.kv', b).map((k) => Array.from(k.children).map(T)) })),
      th: qa('#view-record thead th').map(T), rows: qa('#recBody tr').map((tr) => qa('td', tr).map(T)), note: T(q('#view-record p.fine')), seg: qa('.seg button').map((b) => [b.dataset.asset, b.getAttribute('aria-pressed')]) },
    read: T(q('#view-read')), howBar: T(q('#howBar')), preview: q('#previewSwitch').checked,
    views: ['now', 'chart', 'record', 'read'].filter((v) => !q('#view-' + v).hidden), body: document.body.innerText,
  };
  return out;
}
"""


def candles_json(root, a, tf):
    p = os.path.join(root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p):
        return None
    return json.dumps({"chart": f"{a} {tf}", "bars": [{"t": float(r["time"]), "o": float(r["open"]), "h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"])} for r in csv.DictReader(open(p))]})


class Site:
    """feed: dict | None (503) | 'file'.  ledger: str | None | 'file'.  example: 'file' | None | str.  trades: None (404) | dict.
    candles: 'file' | None (all 404) | callable(a, tf) -> json str or None"""

    def __init__(self, pw, root, feed='file', ledger='file', example='file', trades=None, candles='file', clock=None, viewport=(1440, 900), tz=None, locale=None):
        self.root = root
        page_html = open(os.path.join(root, 'docs/artifacts/member-site/index.html'), encoding='utf-8').read()
        self.doc = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
        self.feed = json.load(open(os.path.join(root, 'feed/ctzb_feed.json'))) if feed == 'file' else feed
        self.ledger = open(os.path.join(root, 'datasets/ledger.csv')).read() if ledger == 'file' else ledger
        self.example = open(os.path.join(root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')).read() if example == 'file' else example
        self.trades = trades; self.candles = candles
        self.b = pw.chromium.launch()
        kw = {'viewport': {'width': viewport[0], 'height': viewport[1]}}
        if tz: kw['timezone_id'] = tz
        if locale: kw['locale'] = locale
        self.pg = self.b.new_context(**kw).new_page()
        self.errs = []; self.requests = []
        self.pg.on('pageerror', lambda e: self.errs.append(str(e)))
        self.pg.on('console', lambda m: self.errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        self.pg.route('**/*', self._route)
        if clock is None and isinstance(self.feed, dict) and self.feed.get('generated_at'):
            clock = (dt.datetime.fromisoformat(self.feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ')
        if clock:
            self.pg.clock.install(time=clock)
        self.clock = clock

    def _route(self, route):
        u = route.request.url; self.requests.append(u)
        if u in ('http://site.test/',) or u.startswith('http://site.test/#'):
            return route.fulfill(body=self.doc, content_type='text/html')
        if u == 'http://site.test/data/ctzb_feed.json':
            return route.fulfill(body=json.dumps(self.feed), content_type='application/json') if self.feed is not None else route.fulfill(status=503, body='x')
        if u == 'http://site.test/data/ledger.csv':
            return route.fulfill(body=self.ledger, content_type='text/csv') if self.ledger is not None else route.fulfill(status=503, body='x')
        if u == 'http://site.test/data/example_ETH-2D-2024-09-22.json':
            return route.fulfill(body=self.example, content_type='application/json') if self.example is not None else route.fulfill(status=404, body='x')
        if u == 'http://site.test/data/trades.json':
            return route.fulfill(body=json.dumps(self.trades), content_type='application/json') if self.trades is not None else route.fulfill(status=404, body='x')
        if u.startswith('http://site.test/data/candles/') and u.endswith('.json'):
            a, tf = u.rsplit('/', 1)[1][:-5].split('_')
            if self.candles is None:
                return route.fulfill(status=404, body='x')
            c = candles_json(self.root, a, tf) if self.candles == 'file' else self.candles(a, tf)
            return route.fulfill(body=c, content_type='application/json') if c else route.fulfill(status=404, body='x')
        if 'fonts' in u:
            return route.abort()
        return route.fulfill(status=404, body='x')

    def open(self, view='now'):
        self.pg.goto('http://site.test/#' + view); self.pg.wait_for_timeout(700)

    def show(self, view):
        self.pg.click(f'#tab-{view}'); self.pg.wait_for_timeout(350)

    def select(self, sel):
        self.pg.click(f'button[data-sel="{sel}"]'); self.pg.wait_for_timeout(350)

    def dump(self):
        return self.pg.evaluate(EXTRACT)

    def close(self):
        self.b.close()
