"""Audit 11: render the member page with Playwright on a frozen state and dump everything shown.
  python3 page_dump.py <name> <state_root>"""
import csv, datetime as dt, json, os, re, sys
from playwright.sync_api import sync_playwright

NAME, ROOT = sys.argv[1], sys.argv[2]
OUT = os.path.dirname(os.path.abspath(__file__))
page_html = open(os.path.join(ROOT, 'docs/artifacts/member-site/index.html')).read()
wrapped = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
feed_txt = open(os.path.join(ROOT, 'feed/ctzb_feed.json')).read()
feed = json.loads(feed_txt)
ledger_txt = open(os.path.join(ROOT, 'datasets/ledger.csv')).read()
example_txt = open(os.path.join(ROOT, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')).read()


def candles_json(a, tf):
    p = os.path.join(ROOT, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
    if not os.path.exists(p):
        return None
    bars = [{'t': int(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])}
            for r in csv.DictReader(open(p))]
    return json.dumps({'chart': f'{a} {tf}', 'bars': bars})


requests = []


def route(r):
    url = r.request.url
    requests.append(url)
    if 'fonts.googleapis' in url or 'fonts.gstatic' in url:
        return r.abort()
    if url in ('http://site.test/', 'http://site.test'):
        return r.fulfill(status=200, body=wrapped, content_type='text/html; charset=utf-8')
    path = url.split('http://site.test/', 1)[-1].split('?')[0]
    if path == 'data/ctzb_feed.json':
        return r.fulfill(status=200, body=feed_txt, content_type='application/json')
    if path == 'data/ledger.csv':
        return r.fulfill(status=200, body=ledger_txt, content_type='text/csv')
    if path == 'data/example_ETH-2D-2024-09-22.json':
        return r.fulfill(status=200, body=example_txt, content_type='application/json')
    m = re.fullmatch(r'data/candles/(ETH|BTC)_(1D|2D|3D|5D|8D)\.json', path)
    if m:
        body = candles_json(m.group(1), m.group(2))
        if body:
            return r.fulfill(status=200, body=body, content_type='application/json')
    return r.fulfill(status=404, body='not found')


DUMP_NOW = r"""() => {
  const t = (s) => { const e = document.querySelector(s); return e ? e.innerText : null; };
  const all = (s) => Array.from(document.querySelectorAll(s));
  const bars = (s) => all(s + ' .bar').map((b) => ({label: b.children[0].innerText, value: b.children[2].innerText,
      gone: !!b.querySelector('.f.gone'), width: b.querySelector('.f') ? b.querySelector('.f').style.width : null}));
  return {
    filter: t('#filterText'), pillOff: document.querySelector('#filterPill').classList.contains('off'),
    rvAsof: t('#rvAsof'), review: t('#review'), feedState: t('#feedState'), forming: t('#forming'),
    picker: all('#picker button').map((b) => ({sel: b.dataset.sel, text: b.innerText, pressed: b.getAttribute('aria-pressed'), cls: b.className})),
    pnone: all('#picker .pnone').map((e) => e.innerText),
    card: {
      where: t('#card .card-head .where'), state: t('#card .card-head .state'),
      head: all('#card .card-head .small').map((e) => e.innerText),
      stale: t('#card .stale-note'),
      big: t('#card .odds .big'), odds: all('#card .odds > div').map((e) => e.innerText),
      stats: all('#card .stats .kv').map((k) => [k.children[0].innerText, k.children[1].innerText]),
      pool: all('#card .stats > .fine').map((e) => e.innerText),
      marker: t('#card .marker'),
      tiles: all('#card .tile').map((k) => [k.querySelector('.t').innerText, k.querySelector('.v').innerText]),
      ladderLbl: t('#card .box.violet .lbl'), ladder: bars('#ladder'), ladderNote: all('#ladder .fine').map((e) => e.innerText),
      eras: bars('#eras'), erasNote: all('#card .box.teal > .fine').map((e) => e.innerText),
      foot: t('#card .card-foot'), empty: t('#card .empty-card'), full: t('#card'),
    },
    prevIntact: all('#prevIntact .mini, #prevIntact .none').map((e) => ({cls: e.className, text: e.innerText, badge: e.querySelector('.badge') ? e.querySelector('.badge').innerText : null})),
    prevClosed: all('#prevClosed .mini').map((e) => ({cls: e.className, text: e.innerText, badge: e.querySelector('.badge') ? e.querySelector('.badge').innerText : null, badgeCls: e.querySelector('.badge') ? e.querySelector('.badge').className : null})),
    prevAll: t('.prev'), footer: t('footer.foot'),
  };
}"""

DUMP_CHART = r"""() => {
  const t = (s) => { const e = document.querySelector(s); return e ? e.innerText : null; };
  const els = (sel) => Array.from(document.querySelector(sel).children).map((e) => {
    const a = {}; for (const x of e.attributes) a[x.name] = x.value;
    return {tag: e.tagName, a, text: e.tagName === 'text' ? e.textContent : null};
  });
  return { title: t('#chTitle'), sub: t('#chSub'), toggleHidden: document.querySelector('.toggle').hidden,
    alertPressed: document.querySelector('#bAlert').getAttribute('aria-pressed'), hapPressed: document.querySelector('#bHap').getAttribute('aria-pressed'),
    svg: els('#chartSvg'), cloud: els('#cloudSvg'), cloudSub: t('#cloudSub'), cloudNote: t('#cloudNote'), side: t('#chartSide'),
    sideBoxes: Array.from(document.querySelectorAll('#chartSide .sidebox')).map((b) => ({text: b.innerText, kv: Array.from(b.querySelectorAll('.kv')).map((k) => [k.children[0].innerText, k.children[1].innerText])})) };
}"""

DUMP_RECORD = r"""() => ({
  title: document.querySelector('#view-record .sec-title').innerText,
  count: document.querySelector('#recCount').innerText,
  head: Array.from(document.querySelectorAll('#view-record thead th')).map((e) => e.innerText),
  rows: Array.from(document.querySelectorAll('#recBody tr')).map((tr) => Array.from(tr.children).map((td) => td.innerText)),
  sum: Array.from(document.querySelectorAll('#recSum .sidebox')).map((b) => ({head: b.querySelector('.kv').innerText, kv: Array.from(b.querySelectorAll('.kv.num')).map((k) => [k.children[0].innerText, k.children[1].innerText])})),
  note: document.querySelector('#view-record p.fine').innerText })"""

res = {'state': NAME}
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1600, 'height': 1000})
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append('console ' + m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    pg.clock.install(time=gen + dt.timedelta(minutes=6))
    pg.route('**/*', route)
    pg.goto('http://site.test/')
    pg.wait_for_function("document.querySelector('#rvAsof') && document.querySelector('#rvAsof').innerText !== '…'")
    pg.wait_for_timeout(300)
    res['initial'] = pg.evaluate(DUMP_NOW)
    sels = [b['sel'] for b in res['initial']['picker']]
    res['views'] = {}
    for sel in sels:
        pg.click(f'#picker button[data-sel="{sel}"]')
        pg.wait_for_timeout(150)
        v = {'now': pg.evaluate(DUMP_NOW)}
        pg.click('#tab-chart'); pg.wait_for_timeout(400)
        v['chart_alert'] = pg.evaluate(DUMP_CHART)
        if sel == 'example':
            pg.click('#bHap'); pg.wait_for_timeout(300)
            v['chart_happened'] = pg.evaluate(DUMP_CHART)
            pg.click('#bAlert'); pg.wait_for_timeout(300)
            v['chart_alert_again'] = pg.evaluate(DUMP_CHART)
        pg.click('#tab-now'); pg.wait_for_timeout(150)
        res['views'][sel] = v
    # the "Show the example card" switch
    pg.click(f'#picker button[data-sel="{sels[0]}"]'); pg.wait_for_timeout(150)
    res['before_switch'] = pg.evaluate(DUMP_NOW)
    pg.click('#previewSwitch'); pg.wait_for_timeout(150)
    res['switch_on'] = pg.evaluate(DUMP_NOW)
    pg.click('#previewSwitch'); pg.wait_for_timeout(150)
    pg.click('#tab-record'); pg.wait_for_timeout(200)
    res['record'] = {}
    for a in ('all', 'ETH', 'BTC'):
        pg.click(f'#view-record .seg button[data-asset="{a}"]'); pg.wait_for_timeout(200)
        res['record'][a] = pg.evaluate(DUMP_RECORD)
    pg.click('#tab-read'); pg.wait_for_timeout(150)
    res['read'] = pg.evaluate("() => document.querySelector('#view-read').innerText")
    res['read_dl'] = pg.evaluate("() => Array.from(document.querySelectorAll('#view-read dt')).map((d) => [d.innerText, d.nextElementSibling.innerText])")
    res['errors'] = errors
    res['requests'] = sorted(set(requests))
    br.close()
json.dump(res, open(os.path.join(OUT, f'_{NAME}_page.json'), 'w'), indent=1)
print('dumped', NAME, len(res['views']), 'views; errors', errors)
