"""Render the member page for one state with Playwright and dump everything displayed.
python3 page_extract.py <state_dir> <out.json>"""
import sys, os, json, csv, datetime as dt
from playwright.sync_api import sync_playwright

root, outp = sys.argv[1:3]
page_html = open(os.path.join(root, 'docs/artifacts/member-site/index.html')).read()
doc = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
feed_txt = open(os.path.join(root, 'feed/ctzb_feed.json')).read()
feed = json.loads(feed_txt)
ledger_txt = open(os.path.join(root, 'datasets/ledger.csv')).read()
example_txt = open(os.path.join(root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')).read()


def candles(a, tf):
    p = os.path.join(root, f'datasets/candles_{a.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p):
        return None
    bars = []
    for r in csv.DictReader(open(p)):
        bars.append(dict(t=float(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])))
    for b in bars:
        b['t'] = int(b['t'])
    return json.dumps(dict(chart=f'{a} {tf}', bars=bars))


def route(r):
    u = r.request.url
    path = u.split('://', 1)[1].split('/', 1)[1] if '/' in u.split('://', 1)[1] else ''
    path = path.split('?')[0]
    if 'fonts.googleapis' in u or 'fonts.gstatic' in u:
        return r.abort()
    if not u.startswith('http://site.test/'):
        return r.abort()
    if path in ('', 'index.html'):
        return r.fulfill(status=200, content_type='text/html; charset=utf-8', body=doc)
    if path == 'data/ctzb_feed.json':
        return r.fulfill(status=200, content_type='application/json', body=feed_txt)
    if path == 'data/ledger.csv':
        return r.fulfill(status=200, content_type='text/csv', body=ledger_txt)
    if path == 'data/example_ETH-2D-2024-09-22.json':
        return r.fulfill(status=200, content_type='application/json', body=example_txt)
    if path.startswith('data/candles/'):
        k = path[len('data/candles/'):-len('.json')]
        a, tf = k.split('_')
        body = candles(a, tf)
        if body:
            return r.fulfill(status=200, content_type='application/json', body=body)
    return r.fulfill(status=404, body='not found')


JS_SVG = """(sel) => { const s = document.querySelector(sel); if (!s) return null;
  return Array.from(s.children).map(e => ({tag: e.tagName, text: e.textContent, attrs: Object.fromEntries(Array.from(e.attributes).map(a => [a.name, a.value])), style: e.getAttribute('style')})); }"""
JS_CARD = """() => { const c = document.querySelector('#card'); const t = (s) => { const e = c.querySelector(s); return e ? e.innerText : null; };
  return { text: c.innerText, where: t('.where'), state: t('.state'), big: t('.odds .big'),
    odds: Array.from(c.querySelectorAll('.odds > div')).map(e => e.innerText),
    head: Array.from(c.querySelectorAll('.card-head > div')).map(e => e.innerText),
    kv: Array.from(c.querySelectorAll('.stats .kv')).map(e => Array.from(e.children).map(x => x.innerText)),
    statsAll: Array.from(c.querySelectorAll('.stats > div')).map(e => e.innerText),
    marker: t('.marker'),
    tiles: Array.from(c.querySelectorAll('.tile')).map(e => [e.querySelector('.t').innerText, e.querySelector('.v').innerText, e.querySelector('.v').className]),
    ladder: Array.from(c.querySelectorAll('#ladder .bar')).map(e => [e.children[0].innerText, e.querySelector('.f').style.width, e.querySelector('.f').className, e.children[2].innerText]),
    ladderNote: Array.from(c.querySelectorAll('#ladder .fine')).map(e => e.innerText),
    eras: Array.from(c.querySelectorAll('#eras .bar')).map(e => [e.children[0].innerText, e.querySelector('.f').style.width, e.children[2].innerText]),
    boxLbls: Array.from(c.querySelectorAll('.box .lbl')).map(e => e.innerText),
    foot: t('.card-foot'), frameC: document.querySelector('#cardFrame').style.getPropertyValue('--c') }; }"""
JS_COMMON = """() => ({ pill: document.querySelector('#filterPill').innerText, pillOff: document.querySelector('#filterPill').classList.contains('off'),
  review: document.querySelector('#review').innerText, feedState: document.querySelector('#feedState').innerText,
  lead: document.querySelector('#leadBody').innerText,
  picker: Array.from(document.querySelectorAll('#picker button')).map(b => ({sel: b.dataset.sel, text: b.innerText, cls: b.className, pressed: b.getAttribute('aria-pressed')})),
  pickerText: document.querySelector('#picker').innerText,
  prevIntact: Array.from(document.querySelectorAll('#prevIntact > div')).map(e => ({text: e.innerText, cls: e.className})),
  prevClosed: Array.from(document.querySelectorAll('#prevClosed > div')).map(e => ({text: e.innerText, cls: e.className})),
  prevText: document.querySelector('section.prev').innerText,
  footer: document.querySelector('footer').innerText,
  read: document.querySelector('#view-read').innerText,
  switchChecked: document.querySelector('#previewSwitch').checked })"""
JS_CHART = """() => ({ title: document.querySelector('#chTitle').innerText, sub: document.querySelector('#chSub').innerText,
  side: document.querySelector('#chartSide').innerText, cloudSub: document.querySelector('#cloudSub').innerText,
  cloudNote: document.querySelector('#cloudNote').innerText, toggleHidden: document.querySelector('.toggle').hidden,
  sideBoxes: Array.from(document.querySelectorAll('#chartSide .sidebox')).map(e => e.innerText) })"""
JS_REC = """() => ({ count: document.querySelector('#recCount').innerText, title: document.querySelector('#view-record .sec-title').innerText,
  sum: Array.from(document.querySelectorAll('#recSum > div')).map(e => e.innerText),
  head: Array.from(document.querySelectorAll('#view-record thead th')).map(e => e.innerText),
  rows: Array.from(document.querySelectorAll('#recBody tr')).map(r => Array.from(r.children).map(td => td.innerText)),
  fine: document.querySelector('#view-record p.fine').innerText })"""

gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
clock = gen + dt.timedelta(minutes=6)
out = dict(clock=clock.isoformat(), selections={}, record={})
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport=dict(width=1500, height=1000))
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append('console ' + m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
    pg.route('**/*', route)
    pg.clock.install(time=clock)
    pg.goto('http://site.test/')
    pg.wait_for_function("() => document.querySelector('#card') && document.querySelector('#card').innerText.length > 20")
    pg.wait_for_timeout(300)
    out['initial'] = pg.evaluate(JS_COMMON)
    out['initial_card'] = pg.evaluate(JS_CARD)
    sels = [b['sel'] for b in out['initial']['picker']]
    for s in sels:
        pg.click(f'#picker button[data-sel="{s}"]')
        pg.wait_for_timeout(150)
        d = dict(common=pg.evaluate(JS_COMMON), card=pg.evaluate(JS_CARD))
        pg.click('#tab-chart'); pg.wait_for_timeout(400)
        d['chart_alert'] = dict(info=pg.evaluate(JS_CHART), svg=pg.evaluate(JS_SVG, '#chartSvg'), cloud=pg.evaluate(JS_SVG, '#cloudSvg'))
        if s == 'example':
            pg.click('#bHap'); pg.wait_for_timeout(300)
            d['chart_happened'] = dict(info=pg.evaluate(JS_CHART), svg=pg.evaluate(JS_SVG, '#chartSvg'), cloud=pg.evaluate(JS_SVG, '#cloudSvg'))
            pg.click('#bAlert'); pg.wait_for_timeout(200)
        pg.click('#tab-now'); pg.wait_for_timeout(150)
        out['selections'][s] = d
    pg.click('#tab-record'); pg.wait_for_timeout(200)
    for a in ('all', 'ETH', 'BTC'):
        pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(150)
        out['record'][a] = pg.evaluate(JS_REC)
    pg.click('#tab-read'); pg.wait_for_timeout(100)
    out['read'] = pg.evaluate("() => document.querySelector('#view-read').innerText")
    out['errors'] = errs
    br.close()
json.dump(out, open(outp, 'w'), indent=1)
print('selections', list(out['selections']), 'errors', errs[:5])
