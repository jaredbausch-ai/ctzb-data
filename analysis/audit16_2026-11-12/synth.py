"""Synthetic page states (the feed served to the page is altered in memory; the frozen state is not touched)."""
import json, copy, csv, re, sys, datetime as dt
from playwright.sync_api import sync_playwright
import render as R
from common import *
import chk_page, chk_feed, mycalc as M

root = STATES['REPLAY'][0]
FEED = json.load(open(root + '/feed/ctzb_feed.json'))
LED = open(root + '/datasets/ledger.csv').read()
PAGE = open(f"{root}/docs/artifacts/member-site/index.html", encoding="utf-8").read()
DOC = "<!doctype html><html><head><meta charset=utf-8></head><body>" + PAGE + "</body></html>"
EX = open(f"{root}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json").read()
BAD = re.compile(r"\$\{|undefined|NaN|null%|n/a%|\[object|null")
C = Checks('SYNTH')
S, _, mine = chk_feed.run('REPLAY')
P = mine['pool']


def session(feed, offset_min=6, ledger=LED, miss=(), example=EX, steps=None):
    """open the page; steps(pg) may drive it; returns dict of captures"""
    out = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        def h(route):
            u = route.request.url
            if u == "http://site.test/": return route.fulfill(body=DOC, content_type="text/html")
            if "fonts" in u: return route.abort()
            if any(m in u for m in miss): return route.fulfill(status=404, body="x")
            if u.endswith("data/ctzb_feed.json"): return route.fulfill(body=json.dumps(feed), content_type="application/json") if feed is not None else route.fulfill(status=503, body="x")
            if u.endswith("data/ledger.csv"): return route.fulfill(body=ledger, content_type="text/csv") if ledger is not None else route.fulfill(status=404, body="x")
            if "data/example_" in u: return route.fulfill(body=example, content_type="application/json") if example else route.fulfill(status=404, body="x")
            if "/data/candles/" in u:
                a, tf = u.rsplit("/", 1)[1][:-5].split("_"); c = R.candles_json(root, a, tf)
                return route.fulfill(body=c, content_type="application/json") if c else route.fulfill(status=404, body="x")
            return route.fulfill(status=404, body="x")
        pg.route("**/*", h)
        base = feed["generated_at"] if feed else FEED["generated_at"]
        pg.clock.install(time=dt.datetime.fromisoformat(base.replace("Z", "+00:00")) + dt.timedelta(minutes=offset_min))
        pg.goto("http://site.test/#now"); pg.wait_for_timeout(1500)
        out['page'] = pg.evaluate(R.JS_PAGE); out['card'] = pg.evaluate(R.JS_CARD); out['body_now'] = pg.inner_text('body')
        if steps: steps(pg, out)
        else:
            if pg.is_checked('#previewSwitch'):
                pg.click('#previewSwitch'); pg.wait_for_timeout(400); out['card_off'] = pg.evaluate(R.JS_CARD)
            pg.click('#tab-chart'); pg.wait_for_timeout(900); out['chart'] = pg.evaluate(R.JS_CHART); out['body_chart'] = pg.inner_text('body')
            pg.click('#tab-record'); pg.wait_for_timeout(500); out['record'] = pg.evaluate(R.JS_REC); out['body_record'] = pg.inner_text('body')
            pg.click('#tab-read'); pg.wait_for_timeout(300); out['body_read'] = pg.inner_text('body')
        out['errors'] = errs
        b.close()
    return out


def pick_live(pg, out):
    pg.click('#picker button[data-sel="BTC-2D-2026-09-21"]'); pg.wait_for_timeout(400)
    out['page'] = pg.evaluate(R.JS_PAGE); out['card'] = pg.evaluate(R.JS_CARD)
    pg.click('#tab-chart'); pg.wait_for_timeout(900); out['chart'] = pg.evaluate(R.JS_CHART); out['body_chart'] = pg.inner_text('body')


def noraw(name, out):
    bad = [(k, m.group(0), v[max(0, m.start() - 50):m.end() + 30].replace('\n', ' ')) for k, v in out.items() if k.startswith('body') for m in BAD.finditer(v)]
    C.add(name, 'no raw placeholder (${, undefined, NaN, null, n/a%) in any view', bad[:3], [], group='synthetic')
    C.add(name, 'no page error', out['errors'], [], group='synthetic')


# 1 feed down
o = session(None); n = 'feed down'
C.add(n, 'card state', o['card']['head'], ['BTC · ETH', 'Data unavailable'], group='synthetic')
C.add(n, 'says outage, not a quiet market', 'This is an outage, not a quiet market' in o['card']['text'], True, group='synthetic')
C.add(n, 'header', o['page']['filter'], 'Feed unavailable', group='synthetic')
C.add(n, 'banner date', o['page']['rvAsof'], 'unavailable', group='synthetic')
C.add(n, 'picker Forming row says the feed is unavailable', o['card']['pnone'][1], 'Feed unavailable.', group='synthetic')
C.add(n, "picker Live row does not state 'none' during an outage", o['card']['pnone'][0], 'Feed unavailable.', group='synthetic', cause="the Live row reads 'No live top-grade setups right now.' although the feed is down (unknown, not none)")
C.add(n, 'example not auto-shown', o['page']['previewChecked'], False, group='synthetic')
C.add(n, 'footer feed line empty', o['page']['feedState'], '', group='synthetic')
C.add(n, 'Past signals: no summary boxes without the feed', len(o['record']['sum']), 0, group='synthetic')
C.add(n, "Previous signals does not state 'none' during an outage", o['page']['prevIntact'][0]['text'], 'unavailable', group='synthetic', cause="reads 'No open top-grade setup with its edge intact.' although the feed is down")
noraw(n, o)
# 2 held
f = copy.deepcopy(FEED); f.update(cards=[], open_signals=[], cards_withheld=True, alerts_withheld=True, example_card=None); f['checks'].update(all_passed=False, failed_steps=['cards'])
o = session(f); n = 'held (a check failed)'
C.add(n, 'card state', o['card']['head'], ['BTC · ETH', 'Setups held back'], group='synthetic')
C.add(n, 'footer says checks FAILED', 'checks FAILED, cards held back' in o['page']['feedState'], True, group='synthetic')
C.add(n, 'picker forming note', 'Held back: a data check failed on the latest run.' in o['card']['pnone'], True, group='synthetic')
C.add(n, "picker Live row does not state 'none' during a hold", o['card']['pnone'][0], 'Held back', group='synthetic', cause="the Live row reads 'No live top-grade setups right now.' although live setups are held back, not absent")
C.add(n, "Previous signals does not state 'none' during a hold", o['page']['prevIntact'][0]['text'], 'held back', group='synthetic', cause="reads 'No open top-grade setup with its edge intact.' although open setups are held back")
noraw(n, o)
# 3 stale
for off, want in ((299, None), (301, 5), (26 * 60 + 5, 26), (6 * 60 + 30, 6)):
    o = session(copy.deepcopy(FEED), offset_min=off, steps=lambda pg, out: None); n = f'stale: clock {off} min after the feed'
    C.add(n, 'stale note (hours = whole hours since the feed)', o['card']['stale'], None if want is None else f'This data is {want} hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.', group='synthetic')
    noraw(n, o)
q = copy.deepcopy(FEED); q['cards'] = []; q['open_signals'] = []
o = session(q, offset_min=400); n = 'stale and nothing live or forming'
C.add(n, 'example not auto-shown when stale', o['page']['previewChecked'], False, group='synthetic')
C.add(n, 'quiet card carries the stale note', (o['card']['head'], 'This data is 6 hours old' in (o['card']['stale'] or '')), (['BTC · ETH', 'No setup right now'], True), group='synthetic')
# 4 no setup, filter on / off
y1 = 2025; nA = sum(1 for x in P if x['grade'] == 'A+' and 2020 <= x['d0'].year <= y1)
per = f"Top-grade setups come about {L.rhaz(nA / (y1 - 2020 + 1))} times a year (2020 to {y1} average; bear years, when the market filter is off, are included)."
for reg, want in (('Bullish', "The market filter is on. Nothing at the top grade is forming or confirmed today. " + per), ('Bearish', "The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.")):
    q2 = copy.deepcopy(q); q2['market_regime'] = reg
    o = session(q2); n = f'no setup, filter {reg}'
    C.add(n, 'boots on the example', o['page']['previewChecked'], True, group='synthetic')
    C.add(n, 'quiet card text (per-year count from my ledger pool)', o['card_off']['empty'], "Waiting for the next one " + want + " You'll get a push alert the moment one confirms.", group='synthetic')
    C.add(n, 'header filter', o['page']['filter'], 'Market filter: ' + ('on' if reg == 'Bullish' else 'off'), group='synthetic')
    noraw(n, o)
C.add('no setup', 'top-grade signals 2020-2025 in my pool / years', f'{nA} / 6 = {nA / 6:.3f}', f'{nA} / 6 = {nA / 6:.3f}', group='synthetic')
# 5 a top-grade forming card (grade flipped on a real forming card; figures unchanged)
f = copy.deepcopy(FEED); c0 = f['cards'][2]; c0['grade'] = 'A+'
def st5(pg, out):
    pg.click(f'#picker button[data-sel="{c0["signal_id"]}"]'); pg.wait_for_timeout(400); out['card2'] = pg.evaluate(R.JS_CARD)
    pg.click('#tab-chart'); pg.wait_for_timeout(900); out['chart'] = pg.evaluate(R.JS_CHART); out['body_chart'] = pg.inner_text('body')
o = session(f, steps=st5); n = 'top-grade forming card'
k = o['card2']
C.add(n, 'opens on the top-grade forming card', o['card']['head'][:2] == k['head'][:2] and o['card']['head'][2] == k['head'][2], True, group='synthetic')
C.add(n, 'state + vanish warning', k['head'][1:2] + k['head'][3:4], ['Setup forming', 'Not confirmed yet. It can still vanish before it confirms.'], group='synthetic')
C.add(n, 'frame in the live colour', k['frameColor'], 'var(--live)', group='synthetic')
btn = next(b for b in k['picker'] if b['sel'] == c0['signal_id'])
C.add(n, 'picker says top grade', '· top grade ·' in btn['text'] and 'pick top' in btn['cls'], True, group='synthetic')
mi = chk_page.missfig([x for x in P if x['asset'] == c0['asset'] and x['grade'] == 'A+'])
C.add(n, 'misses come from the top-grade pool', k['stats'][3], ['If it misses: went above entry', f"{mi['up_first']} of {mi['misses']} · median best {chk_page.pct(mi['median_peak_pct'])}"], group='synthetic')
C.add(n, 'no below-grade pool line', len(k['stats']), 4, group='synthetic')
C.add(n, 'chart title', o['chart']['title'], f"{c0['asset']} · {c0['timeframe']} · setup forming", group='synthetic')
C.add(n, "chart: no 'isn't top grade' text", "isn't top grade" in o['chart']['sideText'] + o['chart']['cloudNote'], False, group='synthetic')
noraw(n, o)
# 6 an "On track" live card (status flipped on the real live setup)
f = copy.deepcopy(FEED); ob = next(x for x in f['open_signals'] if x['signal_id'] == 'BTC-2D-2026-09-21'); ob['edge_status'] = 'intact'
o = session(f, steps=pick_live); n = 'on-track live card'
C.add(n, 'card wording', o['card']['head'][3], 'On track. It has not fallen to its edge level. The odds below are as of the entry close, not from today.', group='synthetic')
C.add(n, 'live colour, not dimmed', (o['card']['frameColor'], o['card']['bigOpacity']), ('var(--live)', ''), group='synthetic')
C.add(n, 'Previous signals lists it under Edge intact / On track', [(r['name'], r['badge']) for r in o['page']['prevIntact']], [('BTC 2D', 'On track')], group='synthetic')
C.add(n, 'same card: says it has not fallen to its edge level (−5%) while showing worst −16.1%', ('worst −16.1%' in o['card']['head'][2], 'It has not fallen to its edge level' in o['card']['head'][3]), (True, True), group='synthetic')
noraw(n, o)
# 7 extras withheld
f = copy.deepcopy(FEED); f.update(extras_withheld=True, if_it_misses=[], past_paths=[], example_past_paths=None, example_if_it_misses=None)
f['odds_fade'] = {"label": FEED["label"], "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}
o = session(f, steps=pick_live); n = 'extras withheld'; k = o['card']
C.add(n, 'miss row n/a', k['stats'][3], ['If it misses: went above entry', 'n/a'], group='synthetic')
C.add(n, 'miss tiles n/a, no pool text', [t for t in k['tiles'][6:]], [['Typical worst drop, misses', 'n/a'], ['Typical change by day 60, misses', 'n/a']], group='synthetic')
C.add(n, 'ladder still this setup (bar from the top-level field)', (k['boxLabels'][0].lower(), k['ladder'][0]['label'], k['stats'][2]), ('where the odds fade · this setup', 'From entry n 33', ['Edge gone below', '−5% before it rises 10%']), group='synthetic')
C.add(n, 'cloud unavailable', any('Past paths unavailable' in (e.get('text') or '') for e in o['chart']['cloud']), True, group='synthetic')
C.add(n, 'cloud caption cleared (no stale numbers)', (o['chart']['cloudSub'], o['chart']['cloudNote']), ('', ''), group='synthetic', cause='caption/legend left from before')
noraw(n, o)
# 8 ledger missing
o = session(copy.deepcopy(FEED), ledger=None); n = 'ledger file unavailable'
C.add(n, 'Past signals count line', o['record']['count'], 'unavailable', group='synthetic', cause="reads as an empty record: '0 signals · 0 missed +10%', no 'unavailable' notice")
C.add(n, 'Past signals summary boxes still show feed totals', [b[0] for b in o['record']['sum']], [['ETH', '104 signals'], ['BTC', '33 signals']], group='synthetic')
noraw(n, o)
# 9 chart candles missing for the selected setup after another chart was viewed
def st9(pg, out):
    pg.click('#picker button[data-sel="example"]'); pg.wait_for_timeout(300)
    pg.click('#tab-chart'); pg.wait_for_timeout(900); out['chart_ex'] = pg.evaluate(R.JS_CHART)
    pg.click('#tab-now'); pg.wait_for_timeout(200)
    pg.click('#picker button[data-sel="BTC-2D-2026-09-21"]'); pg.wait_for_timeout(300)
    pg.click('#tab-chart'); pg.wait_for_timeout(900); out['chart'] = pg.evaluate(R.JS_CHART); out['body_chart'] = pg.inner_text('body')
o = session(copy.deepcopy(FEED), miss=('candles/BTC_2D.json',), steps=st9); n = 'candle file missing for the selected setup'
C.add(n, 'chart says unavailable', [e['text'] for e in o['chart']['svg'] if e['tag'] == 'text'], ['Chart data unavailable for BTC 2D'], group='synthetic')
C.add(n, 'title/side/cloud are not left over from the previously viewed setup', (o['chart']['title'] == o['chart_ex']['title'], o['chart']['sideText'][:60] == o['chart_ex']['sideText'][:60], o['chart']['cloudSub'] == o['chart_ex']['cloudSub']), (False, False, False), group='synthetic',
      cause=f"heading still '{o['chart']['title']}', side box and cloud still the example's figures, beside 'Chart data unavailable for BTC 2D'")
noraw(n, o)
# 10 example chart file missing
o = session(q, example=None); n = 'example chart file unavailable'
C.add(n, 'chart says unavailable', any('Chart data unavailable' in (e.get('text') or '') for e in o['chart']['svg']), True, group='synthetic')
noraw(n, o)
# 11 an era with no signals, a ladder row with none
f = copy.deepcopy(FEED); ob = next(x for x in f['open_signals'] if x['signal_id'] == 'BTC-2D-2026-09-21')
ob['card']['before_2022'] = {"past_trades": 0, "past_signals": 0, "rose10_never_fell25_within60d_pct": None}
ob['card']['if_it_falls_first'][3].update(past_trades=0, past_signals=0, still_rose10_pct=None, went_on_to_fall25_pct=None, still_rose10_exact_pct=None)
o = session(f, steps=pick_live); n = 'empty era and empty ladder row'
C.add(n, 'era shows n 0 and n/a', (o['card']['eras'][0]['label'], o['card']['eras'][0]['val']), ('Before 2022 n 0', 'n/a'), group='synthetic')
C.add(n, 'ladder row shows n 0 and n/a', (o['card']['ladder'][4]['label'], o['card']['ladder'][4]['val']), ('Falls 20% first n 0', 'n/a'), group='synthetic')
noraw(n, o)
C.save('checks_SYNTH.csv')
print(len(C.rows), 'checks', len(C.bad()), 'bad')
for b in C.bad(): print('  BAD', b['location'], '|', b['label'], '|', str(b['shown'])[:300], '|', str(b['yours'])[:200], '|', b['cause'][:200])
