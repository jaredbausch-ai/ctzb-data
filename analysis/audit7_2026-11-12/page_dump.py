"""Render the member page for one state with Playwright and dump everything displayed."""
import csv, datetime as dt, json, os, sys
from playwright.sync_api import sync_playwright

SP = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/a7'
OUT = os.path.dirname(os.path.abspath(__file__))

SVG_DUMP = """(sel) => { const s = document.querySelector(sel); if (!s) return null;
  return Array.from(s.children).map((e) => ({tag: e.tagName, text: e.textContent,
    a: Object.fromEntries(Array.from(e.attributes).map((x) => [x.name, x.value])), style: e.getAttribute('style')})); }"""


def candles_json(state_dir, chart):
    a, tf = chart.split('_')
    p = os.path.join(state_dir, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p): return None
    bars = [{'t': int(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])}
            for r in csv.DictReader(open(p))]
    return json.dumps({'chart': f'{a} {tf}', 'bars': bars})


def dump(state):
    d = os.path.join(SP, state)
    feed = json.load(open(os.path.join(d, 'feed', 'ctzb_feed.json')))
    page_html = open(os.path.join(d, 'docs', 'artifacts', 'member-site', 'index.html')).read()
    wrapped = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
    t0 = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)
    out = {'state': state, 'clock': t0.isoformat(), 'views': []}
    reqs = []

    def route(rt):
        u = rt.request.url; reqs.append(u)
        path = u.split('http://site.test/', 1)[-1].split('?')[0]
        if 'fonts.g' in u: return rt.abort()
        if u.startswith('http://site.test/') and path in ('', 'index.html'):
            return rt.fulfill(status=200, content_type='text/html', body=wrapped)
        if path == 'data/ctzb_feed.json':
            return rt.fulfill(status=200, content_type='application/json', body=open(os.path.join(d, 'feed', 'ctzb_feed.json')).read())
        if path == 'data/ledger.csv':
            return rt.fulfill(status=200, content_type='text/csv', body=open(os.path.join(d, 'datasets', 'ledger.csv')).read())
        if path.startswith('data/candles/') and path.endswith('.json'):
            b = candles_json(d, path[len('data/candles/'):-5])
            return rt.fulfill(status=200, content_type='application/json', body=b) if b else rt.fulfill(status=404, body='')
        if path == 'data/example_ETH-2D-2024-09-22.json':
            return rt.fulfill(status=200, content_type='application/json',
                              body=open(os.path.join(d, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')).read())
        return rt.fulfill(status=404, body='')

    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 1500, 'height': 1000})
        pg.clock.install(time=t0)
        pg.route('**/*', route)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console ' + m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
        pg.goto('http://site.test/')
        pg.wait_for_timeout(800)

        def grab(tag):
            v = {'tag': tag}
            v['review'] = pg.inner_text('#review')
            v['header'] = pg.inner_text('header.top')
            v['footer'] = pg.inner_text('footer.foot')
            v['picker'] = pg.eval_on_selector_all('#picker button', 'bs => bs.map(b => ({sel: b.dataset.sel, text: b.innerText, pressed: b.getAttribute("aria-pressed")}))')
            v['picker_text'] = pg.inner_text('#picker')
            v['card'] = pg.inner_text('#card')
            v['card_html'] = pg.inner_html('#card')
            v['ladder'] = pg.eval_on_selector_all('#ladder .bar', 'bs => bs.map(b => ({t: b.children[0].innerText, w: b.querySelector(".f") && b.querySelector(".f").style.width, cls: b.querySelector(".f") && b.querySelector(".f").className, v: b.children[2].innerText}))')
            v['eras'] = pg.eval_on_selector_all('#eras .bar', 'bs => bs.map(b => ({t: b.children[0].innerText, w: b.querySelector(".f").style.width, v: b.children[2].innerText}))')
            v['tiles'] = pg.eval_on_selector_all('#card .tile', 'ts => ts.map(t => ({t: t.querySelector(".t").innerText, v: t.querySelector(".v").innerText}))')
            v['stats'] = pg.eval_on_selector_all('#card .stats .kv', 'ks => ks.map(k => ({t: k.children[0].innerText, v: k.children[1].innerText}))')
            v['prev'] = pg.inner_text('section.prev')
            v['prev_minis'] = pg.eval_on_selector_all('section.prev .mini', 'ms => ms.map(m => ({cls: m.className, name: m.querySelector(".name").innerText, sub: m.querySelector(".sub").innerText, badge: m.querySelector(".badge").innerText}))')
            return v

        def chart_views(v):
            pg.click('#tab-chart'); pg.wait_for_timeout(500)
            for mode in ('alert', 'happened'):
                tog_hidden = pg.eval_on_selector('.toggle', 'e => e.hidden')
                if mode == 'happened':
                    if tog_hidden: break
                    pg.click('#bHap'); pg.wait_for_timeout(400)
                v['chart_' + mode] = {'title': pg.inner_text('#chTitle'), 'sub': pg.inner_text('#chSub'), 'toggle_hidden': tog_hidden,
                                      'svg': pg.evaluate(SVG_DUMP, '#chartSvg'), 'cloud': pg.evaluate(SVG_DUMP, '#cloudSvg'),
                                      'cloudSub': pg.inner_text('#cloudSub'), 'cloudNote': pg.inner_text('#cloudNote'),
                                      'side': pg.inner_text('#chartSide')}
            if not pg.eval_on_selector('.toggle', 'e => e.hidden'):
                pg.click('#bAlert'); pg.wait_for_timeout(200)
            pg.click('#tab-now'); pg.wait_for_timeout(300)

        initial = grab('initial')
        initial['selected_initial'] = [b['sel'] for b in initial['picker'] if b['pressed'] == 'true']
        out['views'].append(initial)
        sels = [b['sel'] for b in initial['picker']]
        for s in sels:
            pg.click(f'#picker button[data-sel="{s}"]'); pg.wait_for_timeout(300)
            v = grab('select ' + s)
            chart_views(v)
            out['views'].append(v)
        # record tab
        pg.click('#tab-record'); pg.wait_for_timeout(300)
        rec = {}
        for a in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(200)
            rec[a] = {'count': pg.inner_text('#recCount'), 'sum': pg.inner_text('#recSum'),
                      'rows': pg.eval_on_selector_all('#recBody tr', 'rs => rs.map(r => Array.from(r.children).map(c => c.innerText))'),
                      'head': pg.eval_on_selector_all('#view-record thead th', 'hs => hs.map(h => h.innerText)'),
                      'title': pg.inner_text('#view-record .rec-head .sec-title'), 'fine': pg.inner_text('#view-record p.fine')}
        out['record'] = rec
        pg.click('#tab-read'); pg.wait_for_timeout(200)
        out['read'] = pg.inner_text('#view-read')
        out['errors'] = errs
        out['requests'] = sorted(set(r.split('?')[0] for r in reqs))
        br.close()
    json.dump(out, open(os.path.join(OUT, f'page_{state}.json'), 'w'), indent=1)
    return out


if __name__ == '__main__':
    for s in sys.argv[1:]:
        o = dump(s)
        print(s, len(o['views']), 'views', 'errors', o['errors'][:5])
