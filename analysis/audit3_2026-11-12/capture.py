"""Serve the member page for one state with Playwright and capture every displayed text, per view and selection."""
import json, sys, csv, os
from playwright.sync_api import sync_playwright
from mine import S, STATES

state = sys.argv[1]; root = STATES[state]
site = f'{root}/docs/artifacts/member-site'
page_html = open(f'{site}/index.html').read()
WRAP = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
feed = open(f'{root}/feed/ctzb_feed.json').read()
ledger = open(f'{root}/datasets/ledger.csv').read()
example = open(f'{site}/data/example_ETH-2D-2024-09-22.json').read()


def candles(name):
    a, tf = name.split('_')
    p = f'{root}/datasets/candles_{a.lower()}_{tf.lower()}.csv'
    if not os.path.exists(p): return None
    bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
    return json.dumps({'chart': f'{a} {tf}', 'bars': bars})


def route(r):
    u = r.request.url
    path = u.split('http://site.test/', 1)[1].split('?')[0] if u.startswith('http://site.test/') else None
    if path is None:
        return r.abort()
    if path in ('', 'index.html'): return r.fulfill(status=200, content_type='text/html', body=WRAP)
    if path == 'data/ctzb_feed.json': return r.fulfill(status=200, content_type='application/json', body=feed)
    if path == 'data/ledger.csv': return r.fulfill(status=200, content_type='text/csv', body=ledger)
    if path == 'data/example_ETH-2D-2024-09-22.json': return r.fulfill(status=200, content_type='application/json', body=example)
    if path.startswith('data/candles/') and path.endswith('.json'):
        b = candles(path[len('data/candles/'):-5])
        if b: return r.fulfill(status=200, content_type='application/json', body=b)
    return r.fulfill(status=404, body='')


JS_TEXT = """() => {
  const t = (s) => { const e = document.querySelector(s); return e ? e.innerText : null; };
  const svgt = (s) => Array.from(document.querySelectorAll(s + ' text')).map(e => e.textContent);
  return {header: t('header.top'), review: t('#review'), picker: t('#picker'), card: t('#card'), prevIntact: t('#prevIntact'),
          prevClosed: t('#prevClosed'), foot: t('footer.foot'), chTitle: t('#chTitle'), chSub: t('#chSub'), chartSvg: svgt('#chartSvg'),
          cloudSub: t('#cloudSub'), cloudNote: t('#cloudNote'), cloudSvg: svgt('#cloudSvg'), side: t('#chartSide'),
          recCount: t('#recCount'), recSum: t('#recSum'),
          recRows: Array.from(document.querySelectorAll('#recBody tr')).map(tr => Array.from(tr.children).map(td => td.innerText)),
          read: t('#view-read'), recordFine: t('#view-record .fine'), toggleHidden: document.querySelector('.toggle') ? document.querySelector('.toggle').hidden : null,
          cloudPoly: Array.from(document.querySelectorAll('#cloudSvg polyline')).map(e => e.getAttribute('points')),
          stale: !!document.querySelector('[data-state=stale]')};
}"""

out = {}
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={'width': 1600, 'height': 1000})
    pg = ctx.new_page()
    if state == 'REPLAY':
        pg.clock.set_fixed_time('2026-11-12T04:20:00Z')
    pg.route('**/*', route)
    pg.goto('http://site.test/')
    pg.wait_for_timeout(1500)
    out['initial'] = pg.evaluate(JS_TEXT)
    sels = pg.eval_on_selector_all('#picker button[data-sel]', 'els => els.map(e => e.dataset.sel)')
    out['sels'] = sels
    for sel in sels:
        pg.click('nav.tabs #tab-now')
        pg.click(f'#picker button[data-sel="{sel}"]')
        pg.wait_for_timeout(300)
        out[f'now:{sel}'] = pg.evaluate(JS_TEXT)
        pg.click('nav.tabs #tab-chart'); pg.wait_for_timeout(500)
        out[f'chart-alert:{sel}'] = pg.evaluate(JS_TEXT)
        if not out[f'chart-alert:{sel}']['toggleHidden']:
            pg.click('#bHap'); pg.wait_for_timeout(400)
            out[f'chart-happened:{sel}'] = pg.evaluate(JS_TEXT)
            pg.click('#bAlert'); pg.wait_for_timeout(200)
    # no-preview state (switch off) when nothing is selected
    pg.click('nav.tabs #tab-now')
    if pg.is_checked('#previewSwitch'):
        pg.click('#previewSwitch'); pg.wait_for_timeout(300)
        out['now:switch-off'] = pg.evaluate(JS_TEXT)
        pg.click('#previewSwitch'); pg.wait_for_timeout(300)
    pg.click('nav.tabs #tab-record'); pg.wait_for_timeout(300)
    for a in ('all', 'ETH', 'BTC'):
        pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(300)
        out[f'record:{a}'] = pg.evaluate(JS_TEXT)
    pg.click('nav.tabs #tab-read'); pg.wait_for_timeout(200)
    out['read'] = pg.evaluate(JS_TEXT)
    pg.screenshot(path=f'{S}/audit3/shot_{state}_read.png')
    pg.click('nav.tabs #tab-now'); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{S}/audit3/shot_{state}_now.png')
    br.close()
json.dump(out, open(f'{S}/audit3/page_{state}.json', 'w'), indent=1)
print(state, 'captured', list(out))
