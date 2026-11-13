"""Render the member page for a state with Playwright and dump everything a member sees, as JSON.
Usage: python3 page.py <state dir> <out.json>"""
import sys, os, json, csv, datetime as dt
from playwright.sync_api import sync_playwright

EXTRACT_CARD = r"""() => {
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const t = (e) => e ? e.innerText.trim() : null;
  const card = q('#card');
  return {
    where: t(q('.card-head .where', card)), state: t(q('.card-head .state', card)),
    smalls: qa('.card-head .small', card).map(t), stale: t(q('.stale-note', card)),
    big: t(q('.odds .big', card)), bigStyle: q('.odds .big', card) ? q('.odds .big', card).getAttribute('style') : null,
    odds: q('.odds', card) ? Array.from(q('.odds', card).children).map(t) : [],
    stats: qa('.stats .kv', card).map((kv) => [t(kv.children[0]), t(kv.children[1])]),
    pool: t(q('.stats .fine', card)), marker: t(q('.marker', card)),
    tiles: qa('.tile', card).map((x) => [t(q('.t', x)), t(q('.v', x))]),
    ladderTitle: t(q('.box.violet .lbl', card)),
    ladder: qa('#ladder .bar', card).map((b) => ({ label: t(b.children[0]), val: t(b.children[2]), gone: !!q('.f.gone', b), width: q('.f', b).style.width })),
    ladderNote: t(q('#ladder .fine', card)),
    eras: qa('#eras .bar', card).map((b) => ({ label: t(b.children[0]), val: t(b.children[2]), width: q('.f', b).style.width })),
    erasNote: t(q('.box.teal .fine', card)),
    foot: t(q('.card-foot', card)), empty: t(q('.empty-card', card)),
    frame: q('#cardFrame').style.getPropertyValue('--c'),
    all: t(card),
  };
}"""

EXTRACT_CHART = r"""() => {
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const t = (e) => e ? e.innerText.trim() : null;
  const el = (e) => { const o = { tag: e.tagName }; for (const a of e.getAttributeNames()) o[a] = e.getAttribute(a);
    for (const k of ['stroke', 'fill']) { const v = e.style.getPropertyValue(k); if (v) o['css_' + k] = v; }
    if (e.tagName === 'text') o.text = e.textContent; return o; };
  return {
    title: t(q('#chTitle')), sub: t(q('#chSub')), toggleHidden: q('.toggle').hidden,
    alertPressed: q('#bAlert').getAttribute('aria-pressed'),
    svg: Array.from(q('#chartSvg').children).map(el),
    cloud: Array.from(q('#cloudSvg').children).map(el),
    cloudSub: t(q('#cloudSub')), cloudNote: t(q('#cloudNote')),
    side: qa('#chartSide .sidebox').map((b) => ({ text: t(b), kv: qa('.kv', b).map((kv) => [t(kv.children[0]), t(kv.children[1])]) })),
    sideAll: t(q('#chartSide')),
  };
}"""

EXTRACT_FRAME = r"""() => {
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const t = (e) => e ? e.innerText.trim() : null;
  return {
    filter: t(q('#filterText')), filterOff: q('#filterPill').classList.contains('off'), rvAsof: t(q('#rvAsof')), review: t(q('#review')),
    feedState: t(q('#feedState')), footer: t(q('footer')),
    picker: qa('#picker .prow').map((r) => ({ label: t(q('.plabel', r)), none: t(q('.pnone', r)),
      buttons: qa('button', r).map((b) => ({ sel: b.dataset.sel, text: t(b), cls: b.className, pressed: b.getAttribute('aria-pressed') })) })),
    prevIntact: qa('#prevIntact > *').map((x) => ({ cls: x.className, text: t(x), name: t(q('.name', x)), sub: t(q('.sub', x)), badge: t(q('.badge', x)) })),
    prevClosed: qa('#prevClosed > *').map((x) => ({ cls: x.className, text: t(x), name: t(q('.name', x)), sub: t(q('.sub', x)), badge: t(q('.badge', x)) })),
    lead: t(q('#leadBody')), howBar: t(q('#howBar')), read: t(q('#view-read')),
    previewChecked: q('#previewSwitch').checked,
  };
}"""

EXTRACT_RECORD = r"""() => {
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const t = (e) => e ? e.innerText.trim() : null;
  return { count: t(q('#recCount')), head: t(q('#view-record .rec-head .sec-title')),
    rows: qa('#recBody tr').map((tr) => Array.from(tr.children).map(t)),
    sum: qa('#recSum .sidebox').map((b) => ({ head: t(q('.kv', b)), kv: qa('.kv', b).slice(1).map((kv) => [t(kv.children[0]), t(kv.children[1])]) })),
    fine: t(q('#view-record p.fine')) };
}"""


def candles_json(sdir, chart):
    a, tf = chart.split('_')
    p = os.path.join(sdir, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p):
        return None
    bars = [dict(t=int(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']))
            for r in csv.DictReader(open(p))]
    return json.dumps({'chart': f'{a} {tf}', 'bars': bars})


def dump(sdir, out_path, preview_off_too=True):
    feed_txt = open(os.path.join(sdir, 'feed', 'ctzb_feed.json')).read()
    feed = json.loads(feed_txt)
    led_txt = open(os.path.join(sdir, 'datasets', 'ledger.csv')).read()
    ex_txt = open(os.path.join(sdir, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')).read()
    page_html = open(os.path.join(sdir, 'docs', 'artifacts', 'member-site', 'index.html')).read()
    wrapper = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    clock = gen + dt.timedelta(minutes=6)
    res = {'clock': clock.isoformat(), 'errors': [], 'console': []}

    def route(r):
        u = r.request.url
        path = u.split('site.test/', 1)[1] if 'site.test/' in u else None
        if 'fonts.g' in u:
            return r.abort()
        if path is None:
            return r.fulfill(status=404, body='')
        path = path.split('?')[0]
        if path in ('', 'index.html'):
            return r.fulfill(status=200, body=wrapper, content_type='text/html')
        if path == 'data/ctzb_feed.json':
            return r.fulfill(status=200, body=feed_txt, content_type='application/json')
        if path == 'data/ledger.csv':
            return r.fulfill(status=200, body=led_txt, content_type='text/csv')
        if path == 'data/example_ETH-2D-2024-09-22.json':
            return r.fulfill(status=200, body=ex_txt, content_type='application/json')
        if path.startswith('data/candles/') and path.endswith('.json'):
            j = candles_json(sdir, path[len('data/candles/'):-5])
            if j:
                return r.fulfill(status=200, body=j, content_type='application/json')
        return r.fulfill(status=404, body='')

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1500, 'height': 1000})
        pg.on('pageerror', lambda e: res['errors'].append(str(e)))
        pg.on('console', lambda m: res['console'].append(m.text))
        pg.clock.install(time=clock)
        pg.route('**/*', route)
        pg.goto('http://site.test/')
        pg.wait_for_function("document.querySelector('#feedState') && document.querySelector('#feedState').textContent.length > 0 || document.querySelector('#filterText').textContent !== 'Market filter …'", timeout=15000)
        pg.wait_for_timeout(300)
        res['frame'] = pg.evaluate(EXTRACT_FRAME)
        res['initial_card'] = pg.evaluate(EXTRACT_CARD)
        sels = [btn['sel'] for row in res['frame']['picker'] for btn in row['buttons']]
        res['items'] = []
        for sel in sels:
            pg.click('#tab-now'); pg.wait_for_timeout(50)
            pg.click(f'#picker button[data-sel="{sel}"]'); pg.wait_for_timeout(80)
            item = {'sel': sel, 'card': pg.evaluate(EXTRACT_CARD), 'frame_after': pg.evaluate(EXTRACT_FRAME)['picker']}
            pg.click('#tab-chart'); pg.wait_for_timeout(250)
            item['chart_alert'] = pg.evaluate(EXTRACT_CHART)
            if sel == 'example' and pg.is_visible('#bHap'):
                pg.click('#bHap'); pg.wait_for_timeout(200)
                item['chart_happened'] = pg.evaluate(EXTRACT_CHART)
                pg.click('#bAlert'); pg.wait_for_timeout(100)
            res['items'].append(item)
        pg.click('#tab-record'); pg.wait_for_timeout(150)
        res['record'] = {}
        for a in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(100)
            res['record'][a] = pg.evaluate(EXTRACT_RECORD)
        pg.click('#tab-read'); pg.wait_for_timeout(50)
        res['read'] = pg.evaluate("() => document.querySelector('#view-read').innerText")
        pg.click('#tab-now'); pg.wait_for_timeout(50)
        # the quiet card: switch the example off when nothing is live or forming
        if preview_off_too and res['frame']['previewChecked']:
            pg.click('#previewSwitch'); pg.wait_for_timeout(100)
            res['quiet_card'] = pg.evaluate(EXTRACT_CARD)
        b.close()
    json.dump(res, open(out_path, 'w'), indent=0)
    return res


if __name__ == '__main__':
    dump(sys.argv[1], sys.argv[2])
