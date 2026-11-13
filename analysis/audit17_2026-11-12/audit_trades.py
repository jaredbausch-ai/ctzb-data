"""Audit 17: synthetic state -- the lead trader's feed live (data/trades.json present), which the harness
normally 404s. Checks the panel's figures against the synthetic records and what the chart says about them."""
import csv, datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
from audit_page import Site
from playwright.sync_api import sync_playwright
root, out = sys.argv[1:3]
L = C.Log('SYNTH'); n = "lead trader's feed live (synthetic trades.json: BTC long open 10 Nov, ETH long closed 5 Nov)"
TR = {"trades": [
    {"id": "a:open", "mode": "live", "time": "2026-11-10T12:00:00Z", "asset": "BTC", "instrument": "BTC-PERP", "direction": "long", "action": "open", "price": 74000.5, "leverage": 3.3, "size_pct": 35.0, "reduced_pct": None, "move_pct": None, "account_pct": None, "held_days": None},
    {"id": "b:close", "mode": "live", "time": "2026-11-05T09:30:00Z", "asset": "ETH", "instrument": "ETH-PERP", "direction": "long", "action": "close", "price": 2300, "leverage": 3.3, "size_pct": 38.0, "reduced_pct": 100.0, "move_pct": 5.25, "account_pct": -0.04, "held_days": 3.0}]}
s = Site(root, clock=dt.datetime(2026, 11, 12, 4, 20, tzinfo=dt.timezone.utc))
h0 = s.handler
def h(route):
    if route.request.url.endswith('data/trades.json'):
        return route.fulfill(body=json.dumps(TR), content_type='application/json')
    return h0(route)
s.handler = h
def cmp(label, got, exp, cause='lead trader'):
    for i in range(max(len(got), len(exp))):
        g = got[i] if i < len(got) else ''; e = exp[i] if i < len(exp) else ''
        L.rows.append([L.state, n, f'{label} [{i}]', g, e, 'ok' if g == e else 'DISAGREE', '' if g == e else cause])
with sync_playwright() as pw:
    pg = s.open(pw, 'now')
    cmp('panel', s.texts('#leadBody'), ['Latest', 'BTC long · open', '10 Nov 2026', 'Price $74,000.50', '3.3x', '35.0% of acct',
        'ETH long · close', '5 Nov 2026', 'Price $2,300.00', '3.3x', '38.0% of acct', 'Move +5.3%', 'Account 0.0%'])
    pg.click('#picker [data-sel="BTC-2D-2026-09-21"]'); pg.wait_for_timeout(300)
    cmp('card marker, BTC live setup (his latest BTC event is an open long)', [t for t in s.texts('#card') if t.startswith('Lead trader')], ['Lead trader: in · long'])
    pg.click('#tab-chart'); pg.wait_for_timeout(500)
    note = [t for t in s.texts('#chartSide') if 'lead trader' in t.lower()]
    marks = pg.evaluate("() => Array.from(document.querySelectorAll('#chartSvg *')).filter(e => /lead|trade/i.test(e.textContent || '')).length")
    L.chk(n, 'BTC chart: his open BTC trade (10 Nov, inside this setup\'s 60 days) is drawn as a marker, as the note says', f'{marks} markers; note: {note[0] if note else ""}', '1 marker; note names it', 'chart says "None on this one" with a trade open')
    pg.click('#tab-now'); pg.click('#picker [data-sel="ETH-1D-2026-11-13"]'); pg.wait_for_timeout(300)
    cmp('card marker, ETH forming setup (his latest ETH event is a close)', [t for t in s.texts('#card') if t.startswith('Lead trader')], ['Lead trader: out'])
    s.close()
with open(out, 'w', newline='') as f:
    csv.writer(f).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + L.rows)
print(len(L.rows), 'comparisons', len(L.bad()), 'disagreements'); [print(r[2], '|', r[3], '|', r[4]) for r in L.bad()]
