"""Audit 15 -- Playwright harness for the member page (my own)."""
import json, csv, datetime as dt, re, os
from playwright.sync_api import sync_playwright

def candles_json(S, a, tf):
    p = f'{S}/datasets/candles_{a.lower()}_{tf.lower()}.csv'
    if not os.path.exists(p): return None
    bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
    return json.dumps({"chart": f"{a} {tf}", "bars": bars})

class Site:
    def __init__(self, S, feed_override=None, width=1500, height=1000):
        self.S = S
        self.feed_text = open(f'{S}/feed/ctzb_feed.json').read() if feed_override is None else json.dumps(feed_override)
        self.feed = json.loads(self.feed_text)
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        self.ctx = self.browser.new_context(viewport={'width': width, 'height': height})
        self.page = self.ctx.new_page()
        self.log = []
        html = '<!doctype html><html><head><meta charset=utf-8></head><body>' + open(f'{S}/docs/artifacts/member-site/index.html').read() + '</body></html>'
        def handle(route):
            u = route.request.url
            if 'fonts.googleapis.com' in u or 'fonts.gstatic.com' in u: return route.abort()
            if u == 'http://site.test/': return route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html)
            if u == 'http://site.test/data/ctzb_feed.json': return route.fulfill(status=200, content_type='application/json', body=self.feed_text)
            if u == 'http://site.test/data/ledger.csv': return route.fulfill(status=200, content_type='text/csv', body=open(f'{S}/datasets/ledger.csv').read())
            m = re.fullmatch(r'http://site\.test/data/candles/(ETH|BTC)_(1D|2D|3D|5D|8D)\.json', u)
            if m:
                b = candles_json(S, m.group(1), m.group(2))
                if b: return route.fulfill(status=200, content_type='application/json', body=b)
            if u == 'http://site.test/data/example_ETH-2D-2024-09-22.json':
                return route.fulfill(status=200, content_type='application/json', body=open(f'{S}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json').read())
            self.log.append(u)
            return route.fulfill(status=404, body='not found')
        self.ctx.route('**/*', handle)
        gen = dt.datetime.fromisoformat(self.feed['generated_at'].replace('Z', '+00:00'))
        self.page.clock.install(time=gen + dt.timedelta(minutes=6))
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.goto('http://site.test/')
        self.page.wait_for_function("document.querySelector('#feedState') && document.querySelector('#feedState').textContent.length > 0")
        self.page.wait_for_timeout(300)

    def text(self, sel):
        return self.page.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText : null; }", sel)

    def texts(self, sel):
        return self.page.evaluate("(s) => Array.from(document.querySelectorAll(s)).map(e => e.innerText)", sel)

    def click(self, sel):
        self.page.evaluate("(s) => document.querySelector(s).click()", sel); self.page.wait_for_timeout(250)

    def svg(self, sel):
        return self.page.evaluate("""(s) => Array.from(document.querySelector(s).children).map(e => {
            const o = {tag: e.tagName, text: e.textContent};
            for (const a of e.attributes) o[a.name] = a.value;
            o.cssStroke = e.style.getPropertyValue('stroke'); o.cssFill = e.style.getPropertyValue('fill');
            return o; })""", sel)

    def close(self):
        self.browser.close(); self.pw.stop()

def norm_ws(s): return re.sub(r'\s+', ' ', s or '').strip()
