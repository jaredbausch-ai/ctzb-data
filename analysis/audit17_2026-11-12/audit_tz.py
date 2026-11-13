"""Audit 17: the page read in other time zones and locales must show the same dates and numbers (every date on
the page is UTC). Renders REPLAY in UTC, UTC+14, UTC-11 and a German-locale browser and compares all text."""
import csv, datetime as dt, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
from audit_page import Site, JS_TEXT
from playwright.sync_api import sync_playwright
root, out = sys.argv[1:3]
CLK = dt.datetime(2026, 11, 12, 4, 20, tzinfo=dt.timezone.utc)
L = C.Log('SYNTH')

def grab(pw, tz, locale):
    s = Site(root, clock=CLK)
    s.browser = pw.chromium.launch()
    ctx = s.browser.new_context(viewport={'width': 1440, 'height': 900}, timezone_id=tz, locale=locale)
    pg = ctx.new_page(); s.pg = pg; pg.route('**/*', s.handler); pg.clock.install(time=CLK)
    pg.goto('http://site.test/#now'); pg.wait_for_timeout(700)
    o = {}
    for sid in ('BTC-2D-2026-09-21', 'ETH-2D-2026-11-16', 'example'):
        pg.click('#tab-now'); pg.click(f'#picker [data-sel="{sid}"]'); pg.wait_for_timeout(300)
        o[f'now {sid}'] = s.texts('.app')
        pg.click('#tab-chart'); pg.wait_for_timeout(500); o[f'chart {sid}'] = s.texts('.app')
        if sid == 'example':
            pg.click('#bHap'); pg.wait_for_timeout(400); o['chart example happened'] = s.texts('.app')
    pg.click('#tab-record'); pg.wait_for_timeout(300); o['record'] = s.texts('.app')
    s.browser.close()
    return o

with sync_playwright() as pw:
    base = grab(pw, 'UTC', 'en-GB')
    for tz, loc in (('Pacific/Kiritimati', 'en-GB'), ('Pacific/Pago_Pago', 'en-US'), ('Europe/Berlin', 'de-DE')):
        o = grab(pw, tz, loc)
        for k in base:
            diff = [(a, b) for a, b in zip(o[k], base[k]) if a != b]
            L.chk(f'viewer in {tz}, browser locale {loc}', f'{k}: every text item equals the UTC render ({len(base[k])} items)', f'{len(o[k])} items, {len(diff)} differ' + (f': {diff[0]}' if diff else ''), f'{len(base[k])} items, 0 differ', 'time zone / locale')
with open(out, 'w', newline='') as f:
    csv.writer(f).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + L.rows)
print(len(L.rows), 'comparisons', len(L.bad()), 'disagreements'); [print(r) for r in L.bad()[:5]]
