"""Render the member page for one state with Playwright and dump everything a member can see."""
import json, csv, os, sys, datetime as dt
from playwright.sync_api import sync_playwright

S = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'
STATES = {'REPLAY': f'{S}/a5/replay_0414', 'CURRENT': f'{S}/a5/current'}

DUMP_JS = r"""
() => {
  const txt = (s) => { const e = document.querySelector(s); return e ? e.innerText : null; };
  const svg = (id) => Array.from(document.querySelectorAll('#' + id + ' > *')).map((e) => {
    const o = { tag: e.tagName };
    for (const a of ['x','y','x1','x2','y1','y2','width','height','cx','cy','r','points','stroke-dasharray','opacity','fill','stroke','stroke-width','text-anchor']) if (e.getAttribute(a) !== null) o[a] = e.getAttribute(a);
    if (e.style.stroke) o.sstroke = e.style.stroke; if (e.style.fill) o.sfill = e.style.fill;
    if (e.tagName === 'text') o.text = e.textContent;
    return o; });
  return {
    review: txt('#review'), pill: txt('#filterPill'), feedState: txt('#feedState'), picker: txt('#picker'),
    pickerButtons: Array.from(document.querySelectorAll('#picker button')).map((b) => ({ sel: b.dataset.sel, text: b.innerText, pressed: b.getAttribute('aria-pressed'), cls: b.className })),
    card: txt('#card'),
    cardParts: {
      where: txt('#card .where'), state: txt('#card .state'), heads: Array.from(document.querySelectorAll('#card .card-head .small')).map((e) => e.innerText),
      big: txt('#card .odds .big'), odds: txt('#card .odds'),
      stats: Array.from(document.querySelectorAll('#card .stats .kv')).map((k) => Array.from(k.children).map((c) => c.innerText)),
      pool: Array.from(document.querySelectorAll('#card .stats .fine')).map((e) => e.innerText),
      marker: txt('#card .marker'),
      tiles: Array.from(document.querySelectorAll('#card .tile')).map((t) => [t.querySelector('.t').innerText, t.querySelector('.v').innerText]),
      ladderLbl: txt('#card .box.violet .lbl'),
      ladder: Array.from(document.querySelectorAll('#ladder .bar')).map((b) => [b.children[0].innerText, b.children[2].innerText, b.querySelector('.f').style.width, b.querySelector('.f').className]),
      ladderNote: txt('#ladder .fine'),
      eras: Array.from(document.querySelectorAll('#eras .bar')).map((b) => [b.children[0].innerText, b.children[2].innerText, b.querySelector('.f').style.width]),
      erasNote: txt('#card .box.teal .fine'), foot: txt('#card .card-foot'), stale: txt('#card .stale-note'),
    },
    prevIntact: txt('#prevIntact'), prevClosed: txt('#prevClosed'),
    prevMinis: Array.from(document.querySelectorAll('.prev .mini')).map((m) => ({ cls: m.className, name: m.querySelector('.name').innerText, sub: m.querySelector('.sub').innerText, badge: m.querySelector('.badge').innerText, bcls: m.querySelector('.badge').className })),
    chTitle: txt('#chTitle'), chSub: txt('#chSub'), cloudSub: txt('#cloudSub'), cloudNote: txt('#cloudNote'), side: txt('#chartSide'),
    sideKV: Array.from(document.querySelectorAll('#chartSide .kv')).map((k) => Array.from(k.children).map((c) => c.innerText)),
    toggleHidden: document.querySelector('.toggle') ? document.querySelector('.toggle').hidden : null, toggleDisplay: document.querySelector('.toggle') ? getComputedStyle(document.querySelector('.toggle')).display : null, toggleRect: document.querySelector('.toggle') ? document.querySelector('.toggle').getBoundingClientRect().width : null, altPressed: document.querySelector('#bAlert') ? document.querySelector('#bAlert').getAttribute('aria-pressed') : null,
    chart: svg('chartSvg'), cloud: svg('cloudSvg'),
    recCount: txt('#recCount'), recSum: Array.from(document.querySelectorAll('#recSum .sidebox')).map((b) => b.innerText),
    recRows: Array.from(document.querySelectorAll('#recBody tr')).map((tr) => Array.from(tr.children).map((td) => td.innerText)),
    readTab: txt('#view-read'), recordTab: txt('#view-record .rec-head') , recordFine: txt('#view-record .fine'),
    footer: txt('footer.foot'), hash: location.hash,
    views: ['now','chart','record','read'].map((v) => [v, document.querySelector('#view-' + v).hidden]),
  };
}
"""


def candles_json(root, chart):
    a, tf = chart.split('_')
    p = f'{root}/datasets/candles_{a.lower()}_{tf.lower()}.csv'
    if not os.path.exists(p):
        return None
    bars = [{'t': int(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])} for r in csv.DictReader(open(p))]
    return json.dumps({'chart': f'{a} {tf}', 'bars': bars})


def run(state):
    root = STATES[state]
    feed = json.load(open(f'{root}/feed/ctzb_feed.json'))
    page_html = open(f'{root}/docs/artifacts/member-site/index.html').read()
    html = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)
    log = []

    def handle(route):
        u = route.request.url
        if 'fonts.googleapis' in u or 'fonts.gstatic' in u:
            return route.abort()
        path = u.split('http://site.test/', 1)[-1].split('?')[0] if u.startswith('http://site.test/') else None
        log.append(u)
        if path == '' :
            return route.fulfill(status=200, body=html, content_type='text/html')
        if path == 'data/ctzb_feed.json':
            return route.fulfill(status=200, body=open(f'{root}/feed/ctzb_feed.json').read(), content_type='application/json')
        if path == 'data/ledger.csv':
            return route.fulfill(status=200, body=open(f'{root}/datasets/ledger.csv').read(), content_type='text/csv')
        if path and path.startswith('data/candles/') and path.endswith('.json'):
            k = path[len('data/candles/'):-5]
            if k.split('_')[1] in ('1D', '2D', '3D', '5D', '8D'):
                b = candles_json(root, k)
                if b:
                    return route.fulfill(status=200, body=b, content_type='application/json')
        if path == 'data/example_ETH-2D-2024-09-22.json':
            return route.fulfill(status=200, body=open(f'{root}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json').read(), content_type='application/json')
        return route.fulfill(status=404, body='not found')

    out = {'state': state, 'clock': gen.isoformat(), 'snaps': []}
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 1440, 'height': 1000})
        pg.clock.install(time=gen)
        pg.route('**/*', handle)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.type + ':' + m.text) if m.type in ('error', 'warning') else None)
        pg.goto('http://site.test/')
        pg.wait_for_timeout(800)

        def snap(tag):
            d = pg.evaluate(DUMP_JS); d['tag'] = tag; out['snaps'].append(d)

        snap('boot')
        sels = [b['sel'] for b in out['snaps'][0]['pickerButtons']]
        for sel in sels:
            pg.click('#tab-now'); pg.wait_for_timeout(150)
            pg.click(f'#picker button[data-sel="{sel}"]'); pg.wait_for_timeout(250)
            snap(f'now:{sel}')
            pg.click('#tab-chart'); pg.wait_for_timeout(500)
            snap(f'chart:{sel}:alert')
            if pg.is_visible('#bHap'):
                pg.click('#bHap'); pg.wait_for_timeout(400)
                snap(f'chart:{sel}:happened')
                pg.click('#bAlert'); pg.wait_for_timeout(300)
                snap(f'chart:{sel}:alert-again')
        # the preview switch (example) from the banner
        pg.click('#tab-now'); pg.wait_for_timeout(150)
        pg.click(f'#picker button[data-sel="{sels[0]}"]'); pg.wait_for_timeout(250)
        pg.click('#previewSwitch'); pg.wait_for_timeout(250)
        snap('now:switch')
        pg.click('#previewSwitch'); pg.wait_for_timeout(250)
        pg.click('#tab-record'); pg.wait_for_timeout(300)
        for a in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(250)
            snap(f'record:{a}')
        pg.click('#tab-read'); pg.wait_for_timeout(200)
        snap('read')
        out['errors'] = errs
        out['requests'] = sorted(set(log))
        br.close()
    return out


if __name__ == '__main__':
    os.makedirs(f'{S}/audit5/work', exist_ok=True)
    for st in sys.argv[1:] or STATES:
        d = run(st)
        json.dump(d, open(f'{S}/audit5/work/page_{st}.json', 'w'), indent=1)
        print(st, len(d['snaps']), 'snaps', 'errors:', d['errors'][:5])
