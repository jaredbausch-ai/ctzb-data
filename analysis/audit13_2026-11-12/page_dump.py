"""Audit 13 part 3a: render the member site in Chromium for each state and dump everything it shows."""
import csv, datetime as dt, json, os, sys
from playwright.sync_api import sync_playwright

OUT = os.path.dirname(os.path.abspath(__file__))
A13 = os.path.join(os.path.dirname(OUT), 'a13')

JS_CARD = r"""
() => {
  const q = (s, r=document) => r.querySelector(s);
  const card = q('#card');
  const out = {text: card.innerText, frameC: q('#cardFrame').style.getPropertyValue('--c')};
  out.where = q('.card-head .where', card)?.innerText; out.state = q('.card-head .state', card)?.innerText;
  out.head_smalls = Array.from(card.querySelectorAll('.card-head .small')).map(e => e.innerText);
  out.big = q('.odds .big', card)?.innerText;
  out.odds_lines = Array.from(card.querySelectorAll('.odds > div')).map(e => e.innerText);
  out.stats = Array.from(card.querySelectorAll('.stats .kv')).map(e => Array.from(e.children).map(c => c.innerText));
  out.pool = q('.stats .fine', card)?.innerText || null;
  out.marker = q('.marker', card)?.innerText;
  out.tiles = Array.from(card.querySelectorAll('.tile')).map(e => [q('.t', e).innerText, q('.v', e).innerText]);
  out.ladder_lbl = q('.box.violet .lbl', card)?.innerText;
  out.ladder = Array.from(card.querySelectorAll('#ladder .bar')).map(e => ({t: e.children[0].innerText, v: e.children[2].innerText, gone: e.querySelector('.f').classList.contains('gone'), w: e.querySelector('.f').style.width}));
  out.ladder_fine = q('#ladder .fine', card)?.innerText;
  out.eras = Array.from(card.querySelectorAll('#eras .bar')).map(e => ({t: e.children[0].innerText, v: e.children[2].innerText, w: e.querySelector('.f').style.width}));
  out.foot = q('.card-foot', card)?.innerText;
  out.stale = q('.stale-note', card)?.innerText || null;
  out.picker = Array.from(document.querySelectorAll('#picker .prow')).map(r => r.innerText);
  out.pickbtns = Array.from(document.querySelectorAll('#picker button')).map(b => ({sel: b.dataset.sel, txt: b.innerText, pressed: b.getAttribute('aria-pressed'), cls: b.className}));
  return out;
}
"""

JS_CHART = r"""
() => {
  const q = (s) => document.querySelector(s);
  const svg = q('#chartSvg');
  const els = Array.from(svg.children).map(e => {
    const a = {}; for (const at of e.attributes) a[at.name] = at.value;
    return {tag: e.tagName, a, text: e.textContent, style: e.getAttribute('style')};
  });
  const cloud = Array.from(q('#cloudSvg').children).map(e => { const a = {}; for (const at of e.attributes) a[at.name] = at.value; return {tag: e.tagName, a, text: e.textContent}; });
  return {title: q('#chTitle').innerText, sub: q('#chSub').innerText, toggleHidden: q('.toggle').hidden,
          alertPressed: q('#bAlert').getAttribute('aria-pressed'), els, cloud, cloudSub: q('#cloudSub').innerText, cloudNote: q('#cloudNote').innerText,
          side: Array.from(q('#chartSide').children).map(e => e.innerText),
          sideKV: Array.from(q('#chartSide').querySelectorAll('.kv')).map(e => Array.from(e.children).map(c => c.innerText))};
}
"""

JS_REC = r"""
() => {
  const q = (s) => document.querySelector(s);
  return {head: q('#view-record .rec-head .sec-title').innerText, count: q('#recCount').innerText,
          rows: Array.from(document.querySelectorAll('#recBody tr')).map(tr => Array.from(tr.children).map(td => td.innerText)),
          sum: Array.from(document.querySelectorAll('#recSum .sidebox')).map(b => ({head: b.querySelector('.kv').innerText, kv: Array.from(b.querySelectorAll('.kv')).slice(1).map(k => Array.from(k.children).map(c => c.innerText))})),
          fine: q('#view-record p.fine').innerText,
          ths: Array.from(document.querySelectorAll('#view-record th')).map(t => t.innerText)};
}
"""

JS_MISC = r"""
() => {
  const q = (s) => document.querySelector(s);
  return {review: q('#review').innerText, filter: q('#filterText').innerText, pillOff: q('#filterPill').classList.contains('off'),
          foot: q('footer.foot').innerText, feedState: q('#feedState').innerText,
          lead: q('#leadBody').innerText, leadPanel: q('.lead-in').innerText,
          prevIntact: Array.from(document.querySelectorAll('#prevIntact > div')).map(e => ({cls: e.className, txt: e.innerText})),
          prevClosed: Array.from(document.querySelectorAll('#prevClosed > div')).map(e => ({cls: e.className, txt: e.innerText, badge: e.querySelector('.badge')?.className})),
          prevAll: q('.prev').innerText,
          read: q('#view-read').innerText, howBar: q('#howBar').innerText, tabs: Array.from(document.querySelectorAll('nav.tabs button')).map(b => b.innerText)};
}
"""


def bars_json(S, a, tf):
    rows = list(csv.DictReader(open(os.path.join(S, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv'))))
    return {"chart": f"{a} {tf}", "bars": [{"t": int(r['time']), "o": float(r['open']), "h": float(r['high']), "l": float(r['low']), "c": float(r['close'])} for r in rows]}


def run(st):
    S = os.path.join(A13, st)
    feed_txt = open(os.path.join(S, 'feed', 'ctzb_feed.json')).read()
    feed = json.loads(feed_txt)
    page_html = open(os.path.join(S, 'docs', 'artifacts', 'member-site', 'index.html')).read()
    wrapped = '<!doctype html><html><head><meta charset=utf-8></head><body>' + page_html + '</body></html>'
    ledger = open(os.path.join(S, 'datasets', 'ledger.csv')).read()
    example = open(os.path.join(S, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')).read()
    log = []

    def handler(route):
        url = route.request.url
        if 'fonts.googleapis' in url or 'fonts.gstatic' in url:
            return route.abort()
        if not url.startswith('http://site.test/'):
            return route.abort()
        p = url[len('http://site.test/'):].split('?')[0].split('#')[0]
        log.append(p)
        if p == '':
            return route.fulfill(status=200, content_type='text/html', body=wrapped)
        if p == 'data/ctzb_feed.json':
            return route.fulfill(status=200, content_type='application/json', body=feed_txt)
        if p == 'data/ledger.csv':
            return route.fulfill(status=200, content_type='text/csv', body=ledger)
        if p == 'data/example_ETH-2D-2024-09-22.json':
            return route.fulfill(status=200, content_type='application/json', body=example)
        if p.startswith('data/candles/') and p.endswith('.json'):
            k = p[len('data/candles/'):-5]
            a, tf = k.split('_')
            if a in ('ETH', 'BTC') and tf in ('1D', '2D', '3D', '5D', '8D'):
                return route.fulfill(status=200, content_type='application/json', body=json.dumps(bars_json(S, a, tf)))
        return route.fulfill(status=404, body='not found')

    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    clock = gen + dt.timedelta(minutes=6)
    res = {'clock': clock.isoformat(), 'views': {}}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1500, 'height': 1000})
        pg.clock.install(time=clock)
        pg.route('**/*', handler)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console ' + m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
        pg.goto('http://site.test/')
        pg.wait_for_timeout(800)
        res['initial'] = pg.evaluate(JS_CARD)
        res['misc'] = pg.evaluate(JS_MISC)
        sels = [x['sel'] for x in res['initial']['pickbtns']]
        for sel in sels:
            pg.evaluate("() => { location.hash = '#now'; }"); pg.wait_for_timeout(150)
            pg.click(f'#picker button[data-sel="{sel}"]'); pg.wait_for_timeout(150)
            v = {'card': pg.evaluate(JS_CARD)}
            pg.click('#tab-chart'); pg.wait_for_timeout(400)
            v['chart'] = pg.evaluate(JS_CHART)
            if sel == 'example':
                pg.click('#bHap'); pg.wait_for_timeout(300)
                v['chart_happened'] = pg.evaluate(JS_CHART)
                pg.click('#bAlert'); pg.wait_for_timeout(200)
                v['chart_alert_again'] = pg.evaluate(JS_CHART)
            pg.click('#tab-now'); pg.wait_for_timeout(150)
            v['misc'] = pg.evaluate(JS_MISC)
            res['views'][sel] = v
        # past signals
        pg.click('#tab-record'); pg.wait_for_timeout(200)
        res['record'] = {}
        for a in ('all', 'ETH', 'BTC'):
            pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(150)
            res['record'][a] = pg.evaluate(JS_REC)
        pg.click('#tab-read'); pg.wait_for_timeout(150)
        res['read'] = pg.evaluate(JS_MISC)
        pg.click('#tab-now'); pg.wait_for_timeout(200)
        # the example via the switch too
        pg.check('#previewSwitch'); pg.wait_for_timeout(200)
        res['switch_example'] = pg.evaluate(JS_CARD)
        pg.uncheck('#previewSwitch'); pg.wait_for_timeout(200)
        res['after_switch'] = pg.evaluate(JS_CARD)
        res['errors'] = errs
        res['requests'] = sorted(set(log))
        b.close()
    json.dump(res, open(os.path.join(OUT, f'page_{st}.json'), 'w'), indent=1)
    print(st, 'views', list(res['views']), 'errors', errs[:5], 'requests', res['requests'])


if __name__ == '__main__':
    for st in ('replay_0414', 'current'):
        run(st)
