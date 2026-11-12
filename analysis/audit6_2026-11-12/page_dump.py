"""Drive the member page in Playwright for one state and dump everything it displays (DOM text, SVG
elements with their attributes) to page_<STATE>.json. Comparison happens in page_check.py."""
import csv, datetime as dt, json, os, sys
from playwright.sync_api import sync_playwright

SP = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/a6'
OUT = os.path.dirname(os.path.abspath(__file__))
ROOTS = {'REPLAY': f'{SP}/replay_0414', 'CURRENT': f'{SP}/current'}


def candles_json(root, chart):
    a, tf = chart.split('_')
    bars = []
    with open(os.path.join(root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')) as f:
        for r in csv.DictReader(f):
            bars.append({'t': int(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])})
    return json.dumps({'chart': f'{a} {tf}', 'bars': bars})


SVG_JS = """(sel) => { const s = document.querySelector(sel); if (!s) return null;
  return Array.from(s.children).map(e => { const a = {}; for (const x of e.attributes) a[x.name] = x.value;
    return {tag: e.tagName, attrs: a, style: e.getAttribute('style') || '', text: e.textContent}; }); }"""


def dump(name):
    root = ROOTS[name]
    feed = json.load(open(os.path.join(root, 'feed', 'ctzb_feed.json')))
    page_html = open(os.path.join(root, 'docs', 'artifacts', 'member-site', 'index.html')).read()
    wrapped = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    clock = gen + dt.timedelta(minutes=6)
    out = {'state': name, 'clock': clock.isoformat(), 'views': {}}
    log = []

    def route(r):
        u = r.request.url
        if 'fonts.googleapis' in u or 'fonts.gstatic' in u:
            return r.abort()
        p = u.split('://', 1)[1].split('/', 1)[1] if '/' in u.split('://', 1)[1] else ''
        p = p.split('?')[0]
        log.append(p)
        if p == '':
            return r.fulfill(status=200, content_type='text/html', body=wrapped)
        if p == 'data/ctzb_feed.json':
            return r.fulfill(status=200, content_type='application/json', body=open(os.path.join(root, 'feed', 'ctzb_feed.json')).read())
        if p == 'data/ledger.csv':
            return r.fulfill(status=200, content_type='text/csv', body=open(os.path.join(root, 'datasets', 'ledger.csv')).read())
        if p.startswith('data/candles/') and p.endswith('.json'):
            ch = p[len('data/candles/'):-5]
            a, tf = ch.split('_')
            if a in ('ETH', 'BTC') and tf in ('1D', '2D', '3D', '5D', '8D'):
                return r.fulfill(status=200, content_type='application/json', body=candles_json(root, ch))
        if p == 'data/example_ETH-2D-2024-09-22.json':
            return r.fulfill(status=200, content_type='application/json',
                             body=open(os.path.join(root, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')).read())
        return r.fulfill(status=404, body='not found')

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={'width': 1440, 'height': 1000})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console ' + m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
        pg.clock.install(time=clock)
        pg.route('**/*', route)
        pg.goto('http://site.test/')
        pg.wait_for_timeout(1500)

        def now_view(tag):
            pg.click('#tab-now'); pg.wait_for_timeout(300)
            d = pg.evaluate("""() => ({
              picker: Array.from(document.querySelectorAll('#picker .pick')).map(b => ({sel: b.dataset.sel, pressed: b.getAttribute('aria-pressed'), cls: b.className, text: b.innerText})),
              pnone: Array.from(document.querySelectorAll('#picker .pnone')).map(b => b.innerText),
              cardText: document.querySelector('#card').innerText,
              head: {where: (document.querySelector('#card .where')||{}).innerText, state: (document.querySelector('#card .state')||{}).innerText,
                     lines: Array.from(document.querySelectorAll('#card .card-head .small')).map(x => x.innerText)},
              odds: Array.from(document.querySelectorAll('#card .odds > div')).map(x => x.innerText),
              stats: Array.from(document.querySelectorAll('#card .stats .kv')).map(k => Array.from(k.children).map(c => c.innerText)),
              pool: Array.from(document.querySelectorAll('#card .stats > .fine')).map(x => x.innerText),
              marker: (document.querySelector('#card .marker')||{}).innerText,
              tiles: Array.from(document.querySelectorAll('#card .tile')).map(t => [t.querySelector('.t').innerText, t.querySelector('.v').innerText]),
              ladderLbl: Array.from(document.querySelectorAll('#card .box .lbl')).map(x => x.innerText),
              ladder: Array.from(document.querySelectorAll('#ladder .bar')).map(b => ({label: b.children[0].innerText, width: b.querySelector('.f').style.width, gone: b.querySelector('.f').classList.contains('gone'), val: b.children[2].innerText})),
              ladderFine: Array.from(document.querySelectorAll('#ladder .fine')).map(x => x.innerText),
              eras: Array.from(document.querySelectorAll('#eras .bar')).map(b => ({label: b.children[0].innerText, width: b.querySelector('.f').style.width, val: b.children[2].innerText})),
              erasFine: Array.from(document.querySelectorAll('#card .box.teal .fine')).map(x => x.innerText),
              foot: (document.querySelector('#card .card-foot')||{}).innerText,
              frameColor: document.querySelector('#cardFrame').style.getPropertyValue('--c'),
              prevIntact: Array.from(document.querySelectorAll('#prevIntact > div')).map(x => ({cls: x.className, text: x.innerText})),
              prevClosed: Array.from(document.querySelectorAll('#prevClosed > div')).map(x => ({cls: x.className, text: x.innerText, badge: (x.querySelector('.badge')||{}).className})),
              prevHead: document.querySelector('section.prev').innerText,
              lead: document.querySelector('#leadBody').innerText,
              preview: document.querySelector('#previewSwitch').checked,
            })""")
            out['views'][f'now:{tag}'] = d
            return d

        def chart_view(tag):
            pg.click('#tab-chart'); pg.wait_for_timeout(700)
            d = pg.evaluate("""() => ({title: document.querySelector('#chTitle').innerText, sub: document.querySelector('#chSub').innerText,
              toggleHidden: document.querySelector('.toggle').hidden,
              alertPressed: document.querySelector('#bAlert').getAttribute('aria-pressed'), hapPressed: document.querySelector('#bHap').getAttribute('aria-pressed'),
              side: Array.from(document.querySelectorAll('#chartSide > div')).map(x => x.innerText),
              sideKV: Array.from(document.querySelectorAll('#chartSide .kv')).map(k => Array.from(k.children).map(c => c.innerText)),
              cloudSub: document.querySelector('#cloudSub').innerText, cloudNote: document.querySelector('#cloudNote').innerText})""")
            d['svg'] = pg.evaluate(SVG_JS, '#chartSvg')
            d['cloud'] = pg.evaluate(SVG_JS, '#cloudSvg')
            out['views'][f'chart:{tag}'] = d
            return d

        # header, banner, footer
        out['header'] = pg.evaluate("""() => ({review: document.querySelector('#review').innerText, filter: document.querySelector('#filterText').innerText,
            pillOff: document.querySelector('#filterPill').classList.contains('off'), feedState: document.querySelector('#feedState').innerText,
            footer: document.querySelector('footer.foot').innerText, forming: document.querySelector('#forming').innerText,
            tabs: Array.from(document.querySelectorAll('nav.tabs button')).map(b => b.innerText), stale: !!document.querySelector('.stale-note')})""")
        first = now_view('initial')
        sels = [b['sel'] for b in first['picker']]
        out['initial_selection'] = [b['sel'] for b in first['picker'] if b['pressed'] == 'true']
        for sel in sels:
            pg.click('#tab-now'); pg.wait_for_timeout(200)
            pg.click(f'#picker .pick[data-sel="{sel}"]'); pg.wait_for_timeout(300)
            now_view(sel)
            chart_view(sel)
            if sel == 'example':
                pg.click('#bHap'); pg.wait_for_timeout(500)
                chart_view('example:happened')
                pg.click('#bAlert'); pg.wait_for_timeout(500)
                chart_view('example:alert-again')
        # past signals
        pg.click('#tab-record'); pg.wait_for_timeout(300)
        for a in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(300)
            out['views'][f'record:{a}'] = pg.evaluate("""() => ({count: document.querySelector('#recCount').innerText,
              head: Array.from(document.querySelectorAll('#view-record thead th')).map(x => x.innerText),
              rows: Array.from(document.querySelectorAll('#recBody tr')).map(tr => Array.from(tr.children).map(td => td.innerText)),
              badges: Array.from(document.querySelectorAll('#recBody tr')).map(tr => Array.from(tr.querySelectorAll('.badge')).map(b => b.className)),
              sum: Array.from(document.querySelectorAll('#recSum .sidebox')).map(b => ({title: b.querySelector('.kv').innerText, kv: Array.from(b.querySelectorAll('.kv')).slice(1).map(k => Array.from(k.children).map(c => c.innerText))})),
              title: document.querySelector('#view-record .sec-title').innerText, fine: document.querySelector('#view-record p.fine').innerText})""")
        pg.click('#tab-read'); pg.wait_for_timeout(200)
        out['views']['read'] = pg.evaluate("() => document.querySelector('#view-read').innerText")
        out['errors'] = errs
        out['requests'] = sorted(set(log))
        br.close()
    json.dump(out, open(os.path.join(OUT, f'page_{name}.json'), 'w'), indent=1)
    print(name, 'views', len(out['views']), 'errors', errs[:5])


if __name__ == '__main__':
    for n in sys.argv[1:] or ['REPLAY', 'CURRENT']:
        dump(n)
