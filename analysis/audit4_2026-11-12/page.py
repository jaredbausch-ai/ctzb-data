"""Serve the member page for one state under Playwright and capture every displayed text.
python3 page.py <tag> <state_dir>"""
import csv, datetime as dt, json, os, sys
from playwright.sync_api import sync_playwright

OUT = os.path.dirname(os.path.abspath(__file__))


def main(tag, sdir):
    page_html = open(f'{sdir}/docs/artifacts/member-site/index.html').read()
    wrapped = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
    feed_txt = open(f'{sdir}/feed/ctzb_feed.json').read()
    feed = json.loads(feed_txt)
    ledger_txt = open(f'{sdir}/datasets/ledger.csv').read()
    example_txt = open(f'{sdir}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json').read()
    candles = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            p = f'{sdir}/datasets/candles_{a.lower()}_{tf.lower()}.csv'
            if os.path.exists(p):
                bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
                candles[f'{a}_{tf}'] = json.dumps(dict(chart=f'{a} {tf}', bars=bars))
    seen = []

    def route(rt):
        u = rt.request.url; seen.append(u)
        path = u.split('://', 1)[1].split('/', 1)[1] if '/' in u.split('://', 1)[1] else ''
        path = path.split('?')[0]
        if rt.request.resource_type == 'font' or 'fonts.g' in u:
            return rt.abort()
        if not u.startswith('http://site.test/'):
            return rt.fulfill(status=404, body='')
        if path == '':
            return rt.fulfill(status=200, body=wrapped, content_type='text/html')
        if path == 'data/ctzb_feed.json':
            return rt.fulfill(status=200, body=feed_txt, content_type='application/json')
        if path == 'data/ledger.csv':
            return rt.fulfill(status=200, body=ledger_txt, content_type='text/csv')
        if path == 'data/example_ETH-2D-2024-09-22.json':
            return rt.fulfill(status=200, body=example_txt, content_type='application/json')
        if path.startswith('data/candles/') and path.endswith('.json'):
            k = path[len('data/candles/'):-5]
            if k in candles:
                return rt.fulfill(status=200, body=candles[k], content_type='application/json')
        return rt.fulfill(status=404, body='')

    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)
    cap = dict(state=tag, clock=gen.isoformat())
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport=dict(width=1440, height=1000))
        pg.clock.install(time=gen)
        pg.route('**/*', route)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://site.test/')
        pg.wait_for_timeout(800)
        T = lambda sel: pg.eval_on_selector(sel, 'e => e.innerText') if pg.query_selector(sel) else None
        cap['header'] = dict(rvAsof=T('#rvAsof'), feedState=T('#feedState'), filterText=T('#filterText'), review=T('#review'))
        cap['initial_card'] = T('#card')
        cap['prevIntact'] = T('#prevIntact'); cap['prevClosed'] = T('#prevClosed')
        btns = pg.eval_on_selector_all('#picker button', 'bs => bs.map(b => ({sel: b.dataset.sel, text: b.innerText, pressed: b.getAttribute("aria-pressed"), cls: b.className}))')
        cap['picker'] = btns
        cap['picker_text'] = T('#picker')
        cap['selections'] = []

        def svg_texts(sel):
            return pg.eval_on_selector_all(sel + ' text', 'ts => ts.map(t => ({x: +t.getAttribute("x"), y: +t.getAttribute("y"), text: t.textContent}))')

        def svg_lines(sel):
            return pg.eval_on_selector_all(sel + ' line', 'ls => ls.map(l => ({x1: +l.getAttribute("x1"), x2: +l.getAttribute("x2"), y1: +l.getAttribute("y1"), y2: +l.getAttribute("y2"), stroke: l.getAttribute("stroke") || l.style.stroke, dash: l.getAttribute("stroke-dasharray")}))')

        def svg_rects(sel):
            return pg.eval_on_selector_all(sel + ' rect', 'ls => ls.map(l => ({x: +l.getAttribute("x"), y: +l.getAttribute("y"), w: +l.getAttribute("width"), h: +l.getAttribute("height"), fill: l.getAttribute("fill") || l.style.fill}))')

        for b in btns:
            pg.click('#tab-now'); pg.wait_for_timeout(150)
            pg.click(f'#picker button[data-sel="{b["sel"]}"]'); pg.wait_for_timeout(250)
            rec = dict(sel=b['sel'], card=T('#card'), card_html=pg.eval_on_selector('#card', 'e => e.innerHTML'))
            pg.click('#tab-chart'); pg.wait_for_timeout(500)
            modes = {}
            for mode in ('bAlert', 'bHap'):
                hidden = pg.eval_on_selector('.toggle', 'e => e.hidden')
                if not hidden:
                    pg.click('#' + mode); pg.wait_for_timeout(400)
                elif mode == 'bHap':
                    break
                modes[mode] = dict(title=T('#chTitle'), sub=T('#chSub'), side=T('#chartSide'), cloudSub=T('#cloudSub'), cloudNote=T('#cloudNote'),
                                   texts=svg_texts('#chartSvg'), lines=svg_lines('#chartSvg'), rects=svg_rects('#chartSvg'),
                                   cloud_texts=svg_texts('#cloudSvg'),
                                   cloud_poly=pg.eval_on_selector_all('#cloudSvg polyline, #cloudSvg polygon', 'ps => ps.map(p => p.getAttribute("points"))'),
                                   toggle_hidden=hidden)
            rec['chart'] = modes
            cap['selections'].append(rec)
        # Past signals
        pg.click('#tab-record'); pg.wait_for_timeout(300)
        cap['record'] = {}
        for a in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(250)
            rows = pg.eval_on_selector_all('#recBody tr', 'trs => trs.map(tr => Array.from(tr.querySelectorAll("td")).map(td => td.innerText))')
            cap['record'][a] = dict(count=T('#recCount'), sum=T('#recSum'), rows=rows, head=pg.eval_on_selector_all('#view-record th', 'ths => ths.map(t => t.innerText)'),
                                    fine=pg.eval_on_selector('#view-record p.fine', 'e => e.innerText'), title=pg.eval_on_selector('#view-record .sec-title', 'e => e.innerText'))
        pg.click('#tab-read'); pg.wait_for_timeout(200)
        cap['read'] = T('#view-read')
        cap['footer'] = T('footer')
        cap['prev_section'] = T('section.prev')
        cap['lead'] = T('section.lead')
        cap['errors'] = errs
        cap['requests'] = seen
        br.close()
    json.dump(cap, open(os.path.join(OUT, f'page_{tag}.json'), 'w'), indent=1)
    print(tag, 'buttons', [b['sel'] for b in btns], 'errors', errs)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
