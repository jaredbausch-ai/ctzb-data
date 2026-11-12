"""Render the member page for one state with Playwright and dump everything displayed."""
import sys, json, csv, os, datetime as dt
from playwright.sync_api import sync_playwright

SCR = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'
st = sys.argv[1]
root = {'REPLAY': SCR + '/a8/replay_0414', 'CURRENT': SCR + '/a8/current'}[st]
page_html = open(root + '/docs/artifacts/member-site/index.html').read()
wrapped = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
feed_txt = open(root + '/feed/ctzb_feed.json').read()
feed = json.loads(feed_txt)
ledger_txt = open(root + '/datasets/ledger.csv').read()
example_txt = open(root + '/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json').read()


def candles(asset, tf):
    p = f"{root}/datasets/candles_{asset.lower()}_{tf.lower()}.csv"
    if not os.path.exists(p): return None
    bars = [{'t': int(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])} for r in csv.DictReader(open(p))]
    return json.dumps({'chart': f'{asset} {tf}', 'bars': bars})


requests = []


def handler(route):
    url = route.request.url
    requests.append(url)
    if 'fonts.g' in url: return route.abort()
    path = url.split('http://site.test/', 1)[-1].split('?')[0]
    if path in ('', 'index.html'):
        return route.fulfill(status=200, content_type='text/html', body=wrapped)
    if path == 'data/ctzb_feed.json':
        return route.fulfill(status=200, content_type='application/json', body=feed_txt)
    if path == 'data/ledger.csv':
        return route.fulfill(status=200, content_type='text/csv', body=ledger_txt)
    if path == 'data/example_ETH-2D-2024-09-22.json':
        return route.fulfill(status=200, content_type='application/json', body=example_txt)
    if path.startswith('data/candles/') and path.endswith('.json'):
        k = path[len('data/candles/'):-5]
        if '_' in k:
            a, tf = k.split('_', 1)
            if a in ('ETH', 'BTC') and tf in ('1D', '2D', '3D', '5D', '8D'):
                body = candles(a, tf)
                if body: return route.fulfill(status=200, content_type='application/json', body=body)
    return route.fulfill(status=404, body='not found')


SVG_JS = """(sel) => { const s = document.querySelector(sel); if (!s) return null;
  return Array.from(s.querySelectorAll('*')).map(e => { const o = {tag: e.tagName}; for (const a of e.getAttributeNames()) o[a] = e.getAttribute(a);
    if (e.tagName === 'text') o.text = e.textContent; if (e.style && e.style.cssText) o.css = e.style.cssText; return o; }); }"""


def grab(page, sels):
    out = {}
    for s in sels:
        el = page.query_selector(s)
        out[s] = None if el is None else el.inner_text()
    return out


res = {'state': st}
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={'width': 1600, 'height': 1000})
    page = ctx.new_page()
    page.route('**/*', handler)
    t0 = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)
    page.clock.install(time=t0)
    page.goto('http://site.test/')
    page.wait_for_timeout(1500)
    res['header'] = grab(page, ['#review', '#filterText', '#rvAsof', '#feedState', 'footer.foot', '#leadBody', '#forming'])
    res['picker_html'] = page.inner_html('#picker')
    btns = page.query_selector_all('#picker button[data-sel]')
    sels = [(b.get_attribute('data-sel'), b.inner_text(), b.get_attribute('aria-pressed')) for b in btns]
    res['picker'] = sels
    res['default'] = {'card': page.inner_text('#card'), 'prevIntact': page.inner_text('#prevIntact'), 'prevClosed': page.inner_text('#prevClosed'),
                      'prev': page.inner_text('section.prev')}
    res['sel'] = {}
    for sid, txt, _ in sels:
        page.evaluate("() => { location.hash = '#now'; }"); page.wait_for_timeout(200)
        page.click(f'#picker button[data-sel="{sid}"]'); page.wait_for_timeout(300)
        d = {'card': page.inner_text('#card'), 'card_html': page.inner_html('#card'),
             'prev': page.inner_text('section.prev'), 'pressed': page.get_attribute(f'#picker button[data-sel="{sid}"]', 'aria-pressed')}
        page.click('#tab-chart'); page.wait_for_timeout(1200)
        modes = ['alert'] + (['happened'] if page.is_visible('#bHap') else [])
        d['chart'] = {}
        for mode in modes:
            if mode == 'happened': page.click('#bHap'); page.wait_for_timeout(800)
            else:
                if page.is_visible('#bAlert'): page.click('#bAlert'); page.wait_for_timeout(800)
            d['chart'][mode] = {'title': page.inner_text('#chTitle'), 'sub': page.inner_text('#chSub'), 'side': page.inner_text('#chartSide'),
                                'cloudSub': page.inner_text('#cloudSub'), 'cloudNote': page.inner_text('#cloudNote'),
                                'svg': page.evaluate(SVG_JS, '#chartSvg'), 'cloud': page.evaluate(SVG_JS, '#cloudSvg'),
                                'toggle_hidden': page.evaluate("() => document.querySelector('.toggle').hidden")}
        page.click('#tab-now'); page.wait_for_timeout(300)
        res['sel'][sid] = d
    # past signals tab
    page.click('#tab-record'); page.wait_for_timeout(500)
    res['record'] = {}
    for a in ('all', 'ETH', 'BTC'):
        page.click(f'.seg button[data-asset="{a}"]'); page.wait_for_timeout(300)
        rows = page.evaluate("() => Array.from(document.querySelectorAll('#recBody tr')).map(tr => Array.from(tr.children).map(td => td.innerText))")
        res['record'][a] = {'count': page.inner_text('#recCount'), 'sum': page.inner_text('#recSum'), 'rows': rows,
                            'head': page.inner_text('#view-record .rec-head'), 'fine': page.inner_text('#view-record p.fine'),
                            'thead': page.inner_text('#view-record thead')}
    page.click('#tab-read'); page.wait_for_timeout(300)
    res['read'] = page.inner_text('#view-read')
    res['requests'] = sorted(set(requests))
    br.close()
json.dump(res, open(f'{SCR}/audit8/code/page_{st}.json', 'w'), indent=1)
print(st, 'picker', [s[0] for s in sels])
