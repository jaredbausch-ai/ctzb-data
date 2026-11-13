"""Load the member page against one state with Playwright and harvest everything it displays."""
import csv, json, os, sys, datetime as dt
from playwright.sync_api import sync_playwright

TFS = ('1D', '2D', '3D', '5D', '8D')


def candles_json(sdir, asset, tf):
    p = os.path.join(sdir, 'datasets', f'candles_{asset.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p):
        return None
    bars = [dict(t=int(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']))
            for r in csv.DictReader(open(p))]
    return json.dumps({'chart': f'{asset} {tf}', 'bars': bars})


HARVEST = r"""() => {
  const T = (s) => { const e = document.querySelector(s); return e ? e.innerText : null; };
  const svgTexts = (id) => Array.from(document.querySelectorAll('#' + id + ' text')).map((t) => ({ text: t.textContent, x: +t.getAttribute('x'), y: +t.getAttribute('y') }));
  const svgLines = (id) => Array.from(document.querySelectorAll('#' + id + ' line')).map((t) => ({ x1: +t.getAttribute('x1'), x2: +t.getAttribute('x2'), y1: +t.getAttribute('y1'), y2: +t.getAttribute('y2'), stroke: t.getAttribute('stroke') || t.style.stroke, dash: t.getAttribute('stroke-dasharray') }));
  const svgRects = (id) => Array.from(document.querySelectorAll('#' + id + ' rect')).map((t) => ({ x: +t.getAttribute('x'), y: +t.getAttribute('y'), w: +t.getAttribute('width'), h: +t.getAttribute('height'), fill: t.getAttribute('fill') || t.style.fill }));
  const poly = (id) => Array.from(document.querySelectorAll('#' + id + ' polyline, #' + id + ' polygon')).map((t) => ({ tag: t.tagName, points: t.getAttribute('points') }));
  const circles = (id) => Array.from(document.querySelectorAll('#' + id + ' circle')).map((t) => ({ cx: +t.getAttribute('cx'), cy: +t.getAttribute('cy') }));
  return {
    filter: T('#filterText'), rvAsof: T('#rvAsof'), feedState: T('#feedState'), review: T('#review'),
    picker: Array.from(document.querySelectorAll('#picker button')).map((b) => ({ sel: b.dataset.sel, text: b.innerText, pressed: b.getAttribute('aria-pressed') })),
    pickerText: T('#picker'), card: T('#card'), cardHTML: (document.querySelector('#card') || {}).innerHTML,
    ladder: Array.from(document.querySelectorAll('#ladder .bar')).map((b) => ({ text: b.innerText, gone: !!b.querySelector('.f.gone') })),
    eras: Array.from(document.querySelectorAll('#eras .bar')).map((b) => b.innerText),
    tiles: Array.from(document.querySelectorAll('#card .tile')).map((b) => ({ t: b.querySelector('.t').innerText, v: b.querySelector('.v').innerText })),
    kvs: Array.from(document.querySelectorAll('#card .stats .kv')).map((b) => b.innerText),
    prevIntact: Array.from(document.querySelectorAll('#prevIntact > div')).map((b) => b.innerText),
    prevClosed: Array.from(document.querySelectorAll('#prevClosed > div')).map((b) => b.innerText),
    lead: T('#leadBody'), howBar: T('#howBar'), read: T('#view-read'),
    chTitle: T('#chTitle'), chSub: T('#chSub'), side: T('#chartSide'),
    sideKV: Array.from(document.querySelectorAll('#chartSide .kv')).map((b) => b.innerText),
    chartTexts: svgTexts('chartSvg'), chartLines: svgLines('chartSvg'), chartRects: svgRects('chartSvg'), chartCircles: circles('chartSvg'),
    cloudTexts: svgTexts('cloudSvg'), cloudPoly: poly('cloudSvg'), cloudSub: T('#cloudSub'), cloudNote: T('#cloudNote'),
    toggleHidden: (document.querySelector('.toggle') || {}).hidden,
    recCount: T('#recCount'), recSum: Array.from(document.querySelectorAll('#recSum .sidebox')).map((b) => b.innerText),
    recRows: Array.from(document.querySelectorAll('#recBody tr')).map((tr) => Array.from(tr.querySelectorAll('td')).map((td) => td.innerText)),
    preview: (document.querySelector('#previewSwitch') || {}).checked,
  };
}"""


def run(sdir, out_json, page_path=None, shots=None):
    feedp = os.path.join(sdir, 'feed', 'ctzb_feed.json')
    feed = json.load(open(feedp))
    page_path = page_path or os.path.join(sdir, 'docs', 'artifacts', 'member-site', 'index.html')
    html = '<!doctype html><html><head><meta charset=utf-8></head><body>' + open(page_path).read() + '</body></html>'
    ledger = open(os.path.join(sdir, 'datasets', 'ledger.csv')).read()
    ex = open(os.path.join(sdir, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')).read()
    files = {'http://site.test/data/ctzb_feed.json': (open(feedp).read(), 'application/json'),
             'http://site.test/data/ledger.csv': (ledger, 'text/csv'),
             'http://site.test/data/example_ETH-2D-2024-09-22.json': (ex, 'application/json')}
    for a in ('ETH', 'BTC'):
        for tf in TFS:
            j = candles_json(sdir, a, tf)
            if j is not None:
                files[f'http://site.test/data/candles/{a}_{tf}.json'] = (j, 'application/json')
    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)
    res = {'errors': [], 'states': []}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1440, 'height': 1000})
        pg.on('pageerror', lambda e: res['errors'].append(str(e)))
        pg.clock.install(time=gen)

        def route(r):
            u = r.request.url.split('#')[0].split('?')[0]
            if u in ('http://site.test/', 'http://site.test'):
                return r.fulfill(status=200, body=html, content_type='text/html')
            if u in files:
                body, ct = files[u]
                return r.fulfill(status=200, body=body, content_type=ct)
            if 'fonts.' in u:
                return r.abort()
            return r.fulfill(status=404, body='not found')
        pg.route('**/*', route)
        pg.goto('http://site.test/')
        pg.wait_for_timeout(600)
        H = lambda: pg.evaluate(HARVEST)
        first = H()
        res['initial'] = first
        sels = [x['sel'] for x in first['picker']]
        for sel in sels:
            pg.click(f'#picker button[data-sel="{sel}"]')
            pg.wait_for_timeout(150)
            now = H()
            pg.click('#tab-chart'); pg.wait_for_timeout(250)
            ch = H()
            hap = None
            if not ch['toggleHidden']:
                pg.click('#bHap'); pg.wait_for_timeout(200)
                hap = H()
                pg.click('#bAlert'); pg.wait_for_timeout(150)
            pg.click('#tab-now'); pg.wait_for_timeout(100)
            res['states'].append({'sel': sel, 'now': now, 'chart': ch, 'happened': hap})
        pg.click('#tab-record'); pg.wait_for_timeout(200)
        rec = {}
        for a in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(150)
            rec[a] = H()
        res['record'] = rec
        pg.click('#tab-read'); pg.wait_for_timeout(100)
        res['read'] = H()
        b.close()
    json.dump(res, open(out_json, 'w'))
    return res


if __name__ == '__main__':
    r = run(sys.argv[1], sys.argv[2])
    print('errors', r['errors'], 'selections', [s['sel'] for s in r['states']])
