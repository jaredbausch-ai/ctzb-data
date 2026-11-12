"""Check 7: serve the member page with Playwright and read every displayed figure. Writes page_dump.json.
Usage: page_scrape.py [--with-example]   (the second mode also serves the example JSON from the member-site folder)"""
import csv, json, os, sys
from playwright.sync_api import sync_playwright

REPO = '/home/claude/ctzb-data'
OUT = os.path.dirname(os.path.abspath(__file__))
WITH_EX = '--with-example' in sys.argv
PAGE = open(os.path.join(REPO, 'docs/artifacts/member-site/index.html')).read()
HTML = f'<!doctype html><html><head><meta charset=utf-8></head><body>{PAGE}</body></html>'
FEED = open(os.path.join(REPO, 'feed/ctzb_feed.json')).read()
LEDGER = open(os.path.join(REPO, 'datasets/ledger.csv')).read()

def candles(k):
    a, tf = k.split('_')
    p = os.path.join(REPO, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p): return None
    bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
    return json.dumps(dict(chart=f'{a} {tf}', bars=bars))

requests = []
def route(rt):
    u = rt.request.url; requests.append(u)
    path = u.split('http://site.test/', 1)[-1].split('?')[0]
    if path in ('', 'index.html'): return rt.fulfill(status=200, content_type='text/html', body=HTML)
    if path == 'data/ctzb_feed.json': return rt.fulfill(status=200, content_type='application/json', body=FEED)
    if path == 'data/ledger.csv': return rt.fulfill(status=200, content_type='text/csv', body=LEDGER)
    if path.startswith('data/candles/') and path.endswith('.json'):
        b = candles(path[len('data/candles/'):-5])
        if b: return rt.fulfill(status=200, content_type='application/json', body=b)
    if WITH_EX and path == 'data/example_ETH-2D-2024-09-22.json':
        return rt.fulfill(status=200, content_type='application/json', body=open(os.path.join(REPO, 'docs/artifacts/member-site', path)).read())
    return rt.fulfill(status=404, body='')

dump = {'picks': [], 'record': {}, 'prev': None}
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1500, 'height': 1000})
    pg.route('**/*', route)
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://site.test/')
    pg.wait_for_selector('#card .card-head, #card .empty-card', timeout=15000)
    pg.wait_for_timeout(500)
    dump['header'] = pg.inner_text('header')
    dump['footer'] = pg.inner_text('footer')
    dump['picker'] = pg.inner_text('#picker')
    dump['lead'] = pg.inner_text('#leadBody')
    dump['prev'] = {'intact': pg.inner_text('#prevIntact'), 'closed': pg.inner_text('#prevClosed')}
    sels = pg.eval_on_selector_all('#picker [data-sel]', 'els => els.map(e => e.dataset.sel)')
    for s in sels:
        pg.click('#tab-now'); pg.wait_for_timeout(150)
        pg.click(f'#picker [data-sel="{s}"]'); pg.wait_for_timeout(300)
        d = {'sel': s, 'card': pg.inner_text('#card')}
        pg.click('#tab-chart'); pg.wait_for_timeout(700)
        d['chart_title'] = pg.inner_text('#chTitle'); d['chart_sub'] = pg.inner_text('#chSub')
        d['side'] = pg.inner_text('#chartSide'); d['cloud_sub'] = pg.inner_text('#cloudSub'); d['cloud_note'] = pg.inner_text('#cloudNote')
        d['svg_text'] = pg.eval_on_selector_all('#chartSvg text', 'els => els.map(e => e.textContent)')
        d['cloud_text'] = pg.eval_on_selector_all('#cloudSvg text', 'els => els.map(e => e.textContent)')
        if s == 'example':
            try:
                pg.click('#bHap'); pg.wait_for_timeout(500)
                d['side_happened'] = pg.inner_text('#chartSide'); d['svg_text_happened'] = pg.eval_on_selector_all('#chartSvg text', 'els => els.map(e => e.textContent)')
                d['cloud_note_happened'] = pg.inner_text('#cloudNote')
            except Exception as ex:
                d['side_happened'] = f'not clickable: {ex.__class__.__name__}'
        dump['picks'].append(d)
    pg.click('#tab-record'); pg.wait_for_timeout(300)
    for a in ('all', 'ETH', 'BTC'):
        pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(300)
        rows = pg.eval_on_selector_all('#recBody tr', 'trs => trs.map(t => Array.from(t.cells).map(c => c.innerText))')
        dump['record'][a] = {'count': pg.inner_text('#recCount'), 'sum': pg.inner_text('#recSum'), 'rows': rows}
    pg.click('#tab-read'); pg.wait_for_timeout(200)
    dump['read'] = pg.inner_text('#view-read')
    dump['errors'] = errs
    dump['requests'] = sorted(set(requests))
    br.close()
fn = 'page_dump_with_example.json' if WITH_EX else 'page_dump.json'
json.dump(dump, open(os.path.join(OUT, fn), 'w'), indent=1)
print('picks', [d['sel'] for d in dump['picks']], 'errors', dump['errors'])
print('requests', dump['requests'])
