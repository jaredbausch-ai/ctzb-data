"""Item 8: drive the member page with Playwright on one state and dump everything shown."""
import csv, datetime as dt, json, os, sys, re
from playwright.sync_api import sync_playwright

STATE = sys.argv[1]
NAME = os.path.basename(STATE.rstrip('/'))
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = open(os.path.join(STATE, 'docs/artifacts/member-site/index.html')).read()
HTML = '<!doctype html><html><head><meta charset=utf-8></head><body>' + PAGE + '</body></html>'
feed_txt = open(os.path.join(STATE, 'feed/ctzb_feed.json')).read()
feed = json.loads(feed_txt)
ledger_txt = open(os.path.join(STATE, 'datasets/ledger.csv')).read()
example_txt = open(os.path.join(STATE, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')).read()


def candles(path):
    m = re.match(r'.*/data/candles/(ETH|BTC)_(1D|2D|3D|5D|8D)\.json$', path)
    if not m:
        return None
    a, tf = m.groups()
    rows = list(csv.DictReader(open(os.path.join(STATE, f'datasets/candles_{a.lower()}_{tf.lower()}.csv'))))
    bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in rows]
    return json.dumps(dict(chart=f'{a} {tf}', bars=bars))

LOG = []
def route(r):
    u = r.request.url
    p = u.split('?')[0]
    if 'fonts.g' in u:
        return r.abort()
    if p in ('http://site.test/', 'http://site.test/index.html'):
        return r.fulfill(status=200, content_type='text/html', body=HTML)
    if p == 'http://site.test/data/ctzb_feed.json':
        return r.fulfill(status=200, content_type='application/json', body=feed_txt)
    if p == 'http://site.test/data/ledger.csv':
        return r.fulfill(status=200, content_type='text/csv', body=ledger_txt)
    if p == 'http://site.test/data/example_ETH-2D-2024-09-22.json':
        return r.fulfill(status=200, content_type='application/json', body=example_txt)
    c = candles(p)
    if c is not None:
        LOG.append(p)
        return r.fulfill(status=200, content_type='application/json', body=c)
    LOG.append('404 ' + p)
    return r.fulfill(status=404, body='')

SVGDUMP = """(sel) => { const s = document.querySelector(sel); if (!s) return null; const out = [];
  for (const e of s.children) { const o = {tag: e.tagName}; for (const a of e.getAttributeNames()) o[a] = e.getAttribute(a);
    if (e.style && e.style.cssText) o.style = e.style.cssText; if (e.textContent) o.text = e.textContent; out.push(o); } return out; }"""


def dump(page):
    g = lambda sel: page.eval_on_selector(sel, 'e => e.innerText') if page.query_selector(sel) else None
    return dict(card=g('#card'), picker=g('#picker'), prev=g('.prev'), header=g('header.top'), review=g('#review'), footer=g('footer.foot'),
                frame=page.eval_on_selector('#cardFrame', 'e => e.style.getPropertyValue("--c")'),
                ladder=page.eval_on_selector_all('#ladder .bar', 'es => es.map(e => ({text: e.innerText, gone: !!e.querySelector(".f.gone"), w: e.querySelector(".f").style.width}))'),
                eras=page.eval_on_selector_all('#eras .bar', 'es => es.map(e => ({text: e.innerText, w: e.querySelector(".f").style.width}))'))


def dump_chart(page):
    g = lambda sel: page.eval_on_selector(sel, 'e => e.innerText') if page.query_selector(sel) else None
    return dict(title=g('#chTitle'), sub=g('#chSub'), side=g('#chartSide'), cloudSub=g('#cloudSub'), cloudNote=g('#cloudNote'),
                toggle_hidden=page.eval_on_selector('.toggle', 'e => e.hidden'),
                svg=page.evaluate(SVGDUMP, '#chartSvg'), cloud=page.evaluate(SVGDUMP, '#cloudSvg'))


out = dict(state=NAME, selections=[], record={}, read=None)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport=dict(width=1440, height=1000))
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.on('console', lambda m: errs.append('console ' + m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
    ga = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)
    page.clock.install(time=ga)
    page.route('**/*', route)
    page.goto('http://site.test/')
    page.wait_for_timeout(1500)
    out['initial'] = dump(page)
    sels = page.eval_on_selector_all('#picker button[data-sel]', 'es => es.map(e => e.dataset.sel)')
    for sid in sels:
        page.click(f'#picker button[data-sel="{sid}"]')
        page.wait_for_timeout(300)
        d = dump(page); d['sel'] = sid
        page.click('#tab-chart'); page.wait_for_timeout(700)
        d['chart_alert'] = dump_chart(page)
        if not page.eval_on_selector('.toggle', 'e => e.hidden'):
            page.click('#bHap'); page.wait_for_timeout(500)
            d['chart_happened'] = dump_chart(page)
            page.click('#bAlert'); page.wait_for_timeout(300)
        page.click('#tab-now'); page.wait_for_timeout(300)
        out['selections'].append(d)
    page.click('#tab-record'); page.wait_for_timeout(400)
    for a in ('all', 'ETH', 'BTC'):
        page.click(f'.seg button[data-asset="{a}"]'); page.wait_for_timeout(300)
        out['record'][a] = dict(count=page.eval_on_selector('#recCount', 'e => e.innerText'),
                                title=page.eval_on_selector('#view-record .sec-title', 'e => e.innerText'),
                                sum=page.eval_on_selector('#recSum', 'e => e.innerText'),
                                head=page.eval_on_selector_all('#view-record thead th', 'es => es.map(e => e.innerText)'),
                                rows=page.eval_on_selector_all('#recBody tr', 'es => es.map(r => Array.from(r.cells).map(c => c.innerText))'),
                                fine=page.eval_on_selector('#view-record p.fine', 'e => e.innerText'))
    page.click('#tab-read'); page.wait_for_timeout(300)
    out['read'] = page.eval_on_selector('#view-read', 'e => e.innerText')
    out['tabs'] = page.eval_on_selector_all('nav.tabs button', 'es => es.map(e => e.innerText)')
    out['errors'] = errs
    out['requests'] = LOG
    page.screenshot(path=os.path.join(HERE, f'shot_{NAME}_read.png'))
    page.click('#tab-now'); page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(HERE, f'shot_{NAME}_now.png'), full_page=True)
    b.close()
json.dump(out, open(os.path.join(HERE, f'page_{NAME}.json'), 'w'), indent=1)
print(NAME, 'selections', [s['sel'] for s in out['selections']], 'errors', errs[:5], 'requests', sorted(set(LOG)))
