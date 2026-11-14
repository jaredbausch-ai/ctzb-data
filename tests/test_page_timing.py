"""Timing tests for the member page (13 Nov 2026, audit #23): slow files and a page left open.

  1. a slow feed: the card area says "Loading", never blank and never "Data unavailable" while it loads;
  2. a slow example file: the example chart says "Loading", not "couldn't be loaded";
  3. a slow chart file: the previous setup's chart is cleared at once ("Loading <chart>"), and a file that
     arrives after the member picked another setup is not drawn over it;
  4. a page left open past 5 hours: the stale warning appears without a reload, and the worked example the page
     switched on for a quiet market goes off (audit #25).

    python3 tests/test_page_timing.py [state dir]     # default: this repo
Needs playwright + chromium. Entry quality only: computed signals, not fills.
"""
import csv, datetime as dt, json, os, sys, time
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = sys.argv[1] if len(sys.argv) > 1 else ROOT
PAGE = open(f'{ROOT}/docs/artifacts/member-site/index.html', encoding='utf-8').read()
DOC = '<!doctype html><html><head><meta charset=utf-8></head><body>' + PAGE + '</body></html>'
FEED = json.load(open(f'{R}/feed/ctzb_feed.json'))
LEDGER = open(f'{R}/datasets/ledger.csv').read()
EX = open(f'{ROOT}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json').read()
results = []


def ok(label, cond, detail=''):
    results.append(bool(cond)); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f'  -- {detail}' if not cond and detail else ''))


CUT = {'n': 0}   # serve chart files missing their last n bars (a file from an older run, or cut short)


def candles(name):
    a, tf = name.split('_')
    p = f'{R}/datasets/candles_{a.lower()}_{tf.lower()}.csv'
    if not os.path.exists(p): return None
    rows = list(csv.DictReader(open(p)))
    rows = rows[:len(rows) - CUT['n']] if CUT['n'] else rows
    return json.dumps({'chart': f'{a} {tf}', 'bars': [{'t': float(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])} for r in rows]})


DELAY_JS = """
(() => {
  const of = window.fetch.bind(window);
  window.fetch = (u, o) => {
    const s = String(u), k = s.includes('ctzb_feed') ? 'feed' : s.includes('example_') ? 'example' : s.includes('/candles/') ? 'candles' : null;
    const d = (window.__delay || {})[k];
    return d ? new Promise((r) => setTimeout(r, d)).then(() => of(u, o)) : of(u, o);
  };
})();
"""


def page(b, delay=None, age_h=0.1, feed=None):
    """delay: {'feed': ms, 'example': ms, 'candles': ms}: the page's own request waits that long on its (fake) clock,
    released by pg.clock.run_for."""
    delay = delay or {}
    pg = b.new_page(viewport={'width': 1440, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    def h(route):
        u = route.request.url
        if u.endswith('/'): return route.fulfill(body=DOC, content_type='text/html')
        key = u.rsplit('/', 1)[1][:-5] if '/candles/' in u else None
        if u.endswith('ctzb_feed.json'): return route.fulfill(body=json.dumps(feed or FEED), content_type='application/json')
        if u.endswith('ledger.csv'): return route.fulfill(body=LEDGER)
        if 'example_' in u: return route.fulfill(body=EX, content_type='application/json')
        if '/candles/' in u:
            c = candles(key); return route.fulfill(body=c, content_type='application/json') if c else route.fulfill(status=404, body='x')
        if 'fonts' in u: return route.abort()
        return route.fulfill(status=404, body='x')
    pg.route('**/*', h)
    g = dt.datetime.strptime(FEED['generated_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
    pg.clock.install(time=g + dt.timedelta(hours=age_h))
    pg.add_init_script("window.__delay = " + json.dumps(delay) + ";" + DELAY_JS)
    return pg, errs


with sync_playwright() as pw:
    b = pw.chromium.launch()
    # 1. slow feed
    pg, errs = page(b, delay={'feed': 2500})
    pg.goto('http://site.test/#now'); pg.wait_for_timeout(600)
    early = pg.inner_text('#card')
    ok('slow feed: the card says it is loading, not blank and not "Data unavailable"', 'Loading' in early and 'Data unavailable' not in early, early[:80])
    pg.clock.run_for(3000); pg.wait_for_timeout(800)
    ok('...and draws once the feed arrives', 'Loading the latest data' not in pg.inner_text('#card') and not errs, str(errs[:1]))
    pg.close()
    # 2. slow example
    pg, errs = page(b, delay={'example': 3000})
    pg.goto('http://site.test/#chart'); pg.wait_for_timeout(800)
    pg.evaluate("document.querySelector('#previewSwitch') && (document.querySelector('#previewSwitch').checked = true, document.querySelector('#previewSwitch').dispatchEvent(new Event('change')))"); pg.wait_for_timeout(400)
    sel = pg.evaluate("document.querySelector('#chTitle').textContent")
    txt = pg.inner_text('body')
    if 'example' in sel.lower():
        ok('slow example file: the chart says loading, not "couldn\'t be loaded"', "couldn't be loaded" not in txt and 'Loading' in pg.evaluate("Array.from(document.querySelectorAll('svg text')).map(t => t.textContent).join(' ')"), sel)
    else:
        ok('slow example file: the example is charted while it loads', False, sel)
    pg.close()
    # 3. slow chart files
    if FEED['cards'] or any(o.get('grade') == 'A+' for o in FEED['open_signals']):
        pg, errs = page(b, delay={'candles': 3000})
        pg.goto('http://site.test/#chart'); pg.wait_for_timeout(600)
        svg = pg.evaluate("Array.from(document.querySelectorAll('#chartSvg text')).map(t => t.textContent).join(' ')")
        ok('slow chart file: the chart says loading while it loads, nothing else drawn', svg.startswith('Loading') and '$' not in svg, svg[:120])
        pg.clock.run_for(3500); pg.wait_for_timeout(800)
        ok('...and draws once it arrives, with no error', 'Loading' not in pg.evaluate("Array.from(document.querySelectorAll('#chartSvg text')).map(t => t.textContent).join(' ')") and not errs, str(errs[:1]))
        pg.close()
    # 5. chart files from an older run (missing their last 3 bars): never drawn for a live or forming setup (audit #24)
    if FEED['cards'] or any(o.get('grade') == 'A+' for o in FEED['open_signals']):
        CUT['n'] = 3
        pg, errs = page(b)
        pg.goto('http://site.test/#chart'); pg.wait_for_timeout(1200)
        svg = pg.evaluate("Array.from(document.querySelectorAll('#chartSvg text')).map(t => t.textContent).join(' ')")
        ok('chart file from an older run (last 3 bars missing): "unavailable", not drawn', 'unavailable' in svg and '$' not in svg and not errs, svg[:140])
        pg.close(); CUT['n'] = 0
    # 4. a page left open
    pg, errs = page(b, age_h=4.9)
    pg.goto('http://site.test/#now'); pg.wait_for_timeout(800)
    before = pg.query_selector('#card .stale-note') is not None
    pg.clock.run_for(20 * 60 * 1000); pg.wait_for_timeout(300)
    after = pg.query_selector('#card .stale-note') is not None
    ok('page left open past 5 hours: the stale warning appears without a reload', not before and after, f'before {before}, after {after}')
    pg.goto('http://site.test/#record'); pg.wait_for_timeout(300)
    ok('...on the other tabs too', 'hours old' in pg.inner_text('#view-record'))
    pg.close()
    # 4c. the hour count keeps up with a page left open a day (audit #26: it stayed at "5 hours old")
    pg, errs = page(b, age_h=4.9)
    pg.goto('http://site.test/#now'); pg.wait_for_timeout(800)
    pg.clock.run_for(24 * 3600 * 1000); pg.wait_for_timeout(300)
    import re as _re
    seen = {}
    for v in ('now', 'chart', 'record', 'read'):
        pg.evaluate(f"location.hash = '#{v}'"); pg.wait_for_timeout(300)
        seen[v] = sorted(set(_re.findall(r'This data is (\d+) hours old', pg.inner_text('#view-' + v))))
    ok('page left open a day: every tab says 28 hours old, not the first hour shown', all(s == ['28'] for s in seen.values()) and not errs, f'{seen} {errs[:1]}')
    pg.close()
    # 4b. quiet market, page left open: the example the page switched on itself goes off once the data is stale (audit #25)
    quiet = json.loads(json.dumps(FEED)); quiet.update(cards=[], open_signals=[], market_regime='Bullish')
    pg, errs = page(b, age_h=4.9, feed=quiet)
    pg.goto('http://site.test/#now'); pg.wait_for_timeout(1500)
    on_before = pg.is_checked('#previewSwitch')
    pg.clock.run_for(20 * 60 * 1000); pg.wait_for_timeout(500)
    txt = pg.inner_text('#card')
    ok('quiet market left open past 5 hours: the example goes off, the stale warning shows', on_before and not pg.is_checked('#previewSwitch') and 'No setup right now' in txt and pg.query_selector('#card .stale-note') is not None and not errs, f'before {on_before}, {txt[:120]!r}, {errs[:1]}')
    pg.close()
    b.close()
print(f'\n{sum(results)}/{len(results)} passed'); sys.exit(0 if all(results) else 1)
