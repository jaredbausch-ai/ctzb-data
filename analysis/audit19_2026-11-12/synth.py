"""Audit 19: synthetic page states. Each scenario serves an altered copy of a frozen state's files to the page
and checks what a member would read. usage: synth.py <out csv>"""
import copy, csv, json, os, sys, datetime as dt, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import Rec, rha
import pagelib as PL
from pagelib import pct, pc, money, DL, MINUS
from playwright.sync_api import sync_playwright

A19 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'a19')
RP, CU = os.path.join(A19, 'replay_0414'), os.path.join(A19, 'current')
R = Rec('SYNTH')
feedR = json.load(open(RP + '/feed/ctzb_feed.json')); feedC = json.load(open(CU + '/feed/ctzb_feed.json'))
ledR = open(RP + '/datasets/ledger.csv').read()
AT = lambda f, mins=6: (dt.datetime.fromisoformat(f['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=mins)).isoformat()
NUM = re.compile(r'[-+−]?\$?\d[\d,]*\.?\d*%?')


def view(br, root, ov=None, at=None, sel=None, tab=None, pre=None, feed=None):
    site = PL.Site(root, ov or {}); page = site.open(br, at or AT(feed or (feedR if root == RP else feedC)))
    if pre: pre(page)
    if sel: page.click(f'#picker .pick[data-sel="{sel}"]'); page.wait_for_timeout(100)
    now = page.evaluate(PL.JS_NOW); ch = rc = None
    if tab == 'chart': page.click('#tab-chart'); page.wait_for_timeout(300); ch = page.evaluate(PL.JS_CHART)
    if tab == 'record': page.click('#tab-record'); page.wait_for_timeout(200); rc = page.evaluate(PL.JS_RECORD)
    errs = list(site.errors); page.context.close()
    return now, ch, rc, errs


def ok(loc, label, shown, want, cond=None):
    R.add(loc, label, shown if not isinstance(shown, str) else shown[:300], want if not isinstance(want, str) else want[:300], (shown == want) if cond is None else bool(cond))


def nonum(s): return not re.search(r'\d', s or '')


with sync_playwright() as pw:
    br = pw.chromium.launch()
    # 1 feed down
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': None}, at=AT(feedR), tab='chart')
    L = 'synthetic: feed down'
    ok(L, 'header', n['filter'], 'Feed unavailable'); ok(L, 'card state', n['card']['state'], 'Data unavailable')
    ok(L, 'card says outage, not quiet', n['card']['empty'], '', 'outage, not a quiet market' in (n['card']['empty'] or ''))
    ok(L, 'picker rows', n['pnone'], ['Feed unavailable.', 'Feed unavailable.']); ok(L, 'previous signals', n['prevIntactNone'], "Unavailable: the feed can't be read right now.")
    ok(L, 'banner scored date', n['banner'], '', 'scored unavailable' in n['banner']); ok(L, 'footer state empty', n['foot'], '')
    ok(L, 'posting bar not typed', n['howBar'], 'posting bar'); ok(L, 'chart', ch['viewText'], '', 'Chart data unavailable' in ch['viewText'] and nonum(ch['cloudNote']) and not ch['side'])
    ok(L, 'no script errors', e, [])
    # 2 held
    f = copy.deepcopy(feedR); f.update(cards_withheld=True, alerts_withheld=True, cards=[], open_signals=[], example_card=None); f['checks'].update(all_passed=False, failed_steps=['cards'])
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, tab='chart'); L = 'synthetic: cards held back'
    ok(L, 'card state', n['card']['state'], 'Setups held back'); ok(L, 'picker rows', n['pnone'], ['Held back: a data check failed on the latest run.'] * 2)
    ok(L, 'previous signals', n['prevIntactNone'], 'Held back: a data check failed on the latest run.'); ok(L, 'footer', n['foot'], '', n['foot'].endswith('checks FAILED, cards held back'))
    ok(L, 'example not auto-shown', n['preview'], False); ok(L, 'chart blank', ch['viewText'], '', 'Chart data unavailable' in ch['viewText']); ok(L, 'no script errors', e, [])
    # 3 fail-closed feed (as feed_live.fail_closed writes it)
    fc = {"schema_version": 6, "generated_at": feedR['generated_at'], "posting_bar_pct": 70, "scored_as_of": None, "label": feedR['label'], "checks": {"passed": False, "all_passed": False, "lines": [], "steps": {}, "failed_steps": ["feed"]},
          "feed_error": "KeyError", "cards_withheld": True, "alerts_withheld": True, "extras_withheld": True, "alerts": [], "cards": [], "prints": [], "open_signals": [], "confluence_windows": [], "grade_odds": [], "if_it_misses": [], "past_paths": [],
          "candle_check": None, "example_card": None, "example_past_paths": None, "example_if_it_misses": None, "odds_fade": {"label": "", "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}}
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': fc}, tab='record'); L = 'synthetic: fail-closed feed'
    ok(L, 'header', n['filter'], 'Market filter: unavailable'); ok(L, 'banner', n['banner'], '', 'scored unavailable (feed 04:14 UTC)' in n['banner']); ok(L, 'card state', n['card']['state'], 'Setups held back')
    ok(L, 'past signals tab still lists the ledger', len(rc['rows']), 137); ok(L, 'no summary boxes without grade odds', rc['sum'], []); ok(L, 'no script errors', e, [])
    # 4 stale
    for mins, want in ((299, None), (301, 5), (6 * 60 + 30, 6), (49 * 60, 49)):
        n, ch, rc, e = view(br, RP, at=AT(feedR, mins)); L = f'synthetic: feed {mins} minutes old'
        ok(L, 'stale note', n['card']['stale'], None if want is None else f"This data is {want} hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.")
    f = copy.deepcopy(feedR); f['cards'] = []; f['open_signals'] = []
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, at=AT(feedR, 400)); L = 'synthetic: stale and quiet'
    ok(L, 'quiet card with the stale note, example not auto-shown', (n['card']['state'], n['preview'], bool(n['card']['stale'])), ('No setup right now', False, True))
    # 5 quiet market: filter on / off
    led = [r for r in csv.DictReader(open(RP + '/datasets/ledger.csv')) if r['grade'] == 'A+']
    y1 = 2025; npy = int(rha(__import__('fractions').Fraction(sum(1 for r in led if 2020 <= int(r['entry'][:4]) <= y1), y1 - 2020 + 1), 0))
    for reg in ('Bullish', 'Bearish'):
        f = copy.deepcopy(feedR); f['cards'] = []; f['open_signals'] = []; f['market_regime'] = reg
        n0, _, _, _ = view(br, RP, {'data/ctzb_feed.json': f}); L = f'synthetic: no setup, filter {reg}'
        ok(L, 'example shown by default', (n0['preview'], n0['card']['state']), (True, 'Confirmed setup'))
        n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, pre=lambda p: (p.uncheck('#previewSwitch'), p.wait_for_timeout(100)))
        ok(L, 'quiet card', n['card']['state'], 'No setup right now')
        want = (f"Waiting for the next one The market filter is on. Nothing at the top grade is forming or confirmed today. Top-grade setups come about {npy} times a year (2020 to {y1} average; bear years, when the market filter is off, are included). You'll get a push alert the moment one confirms."
                if reg == 'Bullish' else "Waiting for the next one The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year. You'll get a push alert the moment one confirms.")
        ok(L, 'quiet text and signals-a-year (my count from the ledger, 2020-2025)', n['card']['empty'], want)
        ok(L, 'picker rows', n['pnone'], ['No live top-grade setups right now.', 'Nothing forming today.']); ok(L, 'no script errors', e, [])
    # 6 a top-grade forming card (grade flipped on a real forming card; miss pool must follow the grade)
    f = copy.deepcopy(feedR); c = next(x for x in f['cards'] if x['signal_id'] == 'BTC-1D-2026-11-13'); c['grade'] = 'A+'
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, sel='BTC-1D-2026-11-13', tab='chart'); L = 'synthetic: top-grade forming card'
    mi = next(x for x in feedR['if_it_misses'] if x['asset'] == 'BTC' and x['grade'] == 'A+')
    ok(L, 'opens on the top-grade forming card', [p['sel'] for p in n['picker'] if p['pressed'] == 'true'], ['BTC-1D-2026-11-13'])
    ok(L, 'state and vanish note', (n['card']['state'], n['card']['smalls'][1]), ('Setup forming', 'Not confirmed yet. It can still vanish before it confirms.'))
    ok(L, 'picker says top grade', next(p['t'] for p in n['picker'] if p['sel'] == 'BTC-1D-2026-11-13'), '', ' · top grade · ' in next(p['t'] for p in n['picker'] if p['sel'] == 'BTC-1D-2026-11-13'))
    ok(L, 'miss row uses the top-grade pool', (n['card']['kv'][3][1], n['card']['pool']), (f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}", f"of all {mi['signals']} BTC top-grade signals"))
    ok(L, 'chart title', ch['title'].lower(), 'btc · 1d · setup forming'); ok(L, 'cloud has no not-top-grade remark', 'isn\'t top grade' in ch['cloudNote'], False)
    ok(L, 'forming side box', ch['side'][1]['text'], 'Still forming. It confirms only if it holds through 13 Nov 2026, and it can vanish before then.')
    # 7 live card, every edge status
    oid = 'BTC-2D-2026-09-21'
    cases = [('lost', -5, 'Edge lost. It fell to its edge level (−5%) before rising 10%.', 'Edge lost', 'closed'), ('lost', 0, 'Edge lost. Its odds were below the bar from the entry.', 'Edge lost', 'closed'),
             ('rose10', -5, 'Rose 10%. It rose 10% before falling to its edge level (−5%).', 'Rose 10%', 'intact'), ('rose10', None, 'Rose 10%. It has risen 10% from the entry close.', 'Rose 10%', 'intact'),
             ('intact', -10, 'On track. It has not fallen to its edge level (−10%) or risen 10% yet.', 'On track', 'intact'), ('intact', None, 'On track. It has neither risen 10% nor lost its edge; its odds hold at every fall measured.', 'On track', 'intact')]
    for st, lv, sent, badge, grp in cases:
        f = copy.deepcopy(feedC); o = next(x for x in f['open_signals'] if x['signal_id'] == oid); o['edge_status'] = st; o['edge_level_pct'] = lv
        n, ch, rc, e = view(br, CU, {'data/ctzb_feed.json': f}, sel=oid); L = f'synthetic: live card, edge {st}, level {lv}'
        ok(L, 'status sentence', n['card']['smalls'][1], sent + ' The odds below are as of the entry close, not from today.')
        ok(L, 'big number dimmed only when lost', n['card']['bigOpacity'], '0.5' if st == 'lost' else '')
        g = n['prevIntact'] if grp == 'intact' else [x for x in n['prevClosed'] if 'fading' in x['cls']]
        ok(L, f'previous-signals group and badge', [x['badge'] for x in g], [badge]); ok(L, 'other group empty', len(n['prevIntact']) if grp != 'intact' else len([x for x in n['prevClosed'] if 'fading' in x['cls']]), 0)
        ok(L, 'card says as of the entry close', n['card']['odds'][1], 'rose 10% within 60 days · at the entry close, not from today')
    # day 60 of 60, and a live setup with no closed bar yet
    f = copy.deepcopy(feedC); o = next(x for x in f['open_signals'] if x['signal_id'] == oid); o.update(days_elapsed=60)
    n, ch, rc, e = view(br, CU, {'data/ctzb_feed.json': f}, sel=oid, tab='chart'); L = 'synthetic: live signal on day 60'
    ok(L, 'card line', n['card']['smalls'][0], '', ' · day 60 of 60 · ' in n['card']['smalls'][0]); ok(L, 'chart title', ch['title'].lower(), 'btc · 2d · live setup, day 60 of 60'); ok(L, 'picker', n['picker'][0]['t'], '', n['picker'][0]['t'].startswith('BTC 2D Day 60 '))
    f = copy.deepcopy(feedC); o = next(x for x in f['open_signals'] if x['signal_id'] == oid); o.update(days_elapsed=1, best_so_far_pct=None, worst_so_far_pct=None, day10_pct=None, edge_status='intact')
    n, ch, rc, e = view(br, CU, {'data/ctzb_feed.json': f}, sel=oid, tab='chart'); L = 'synthetic: live signal, day 1, no closed bar'
    ok(L, 'card line shows n/a, never n/a%', n['card']['smalls'][0], '', n['card']['smalls'][0].endswith('day 1 of 60 · best so far n/a · worst n/a')); ok(L, 'chart live box', ch['side'][1]['kv'], [['Best so far', 'n/a'], ['Worst so far', 'n/a'], ['Day 10', 'not yet']])
    # 8 extras withheld
    f = copy.deepcopy(feedR); f.update(extras_withheld=True, if_it_misses=[], past_paths=[], example_past_paths=None, example_if_it_misses=None); f['odds_fade'] = {"label": "", "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, sel='BTC-1D-2026-11-13', tab='chart'); L = 'synthetic: extras withheld'
    ok(L, 'miss row', n['card']['kv'][3][1], 'n/a'); ok(L, 'miss tiles', [t[1] for t in n['card']['tiles'][6:]], ['n/a', 'n/a']); ok(L, 'miss tiles name no pool', [t[0] for t in n['card']['tiles'][6:]], ['Typical worst drop, misses', 'Typical change by day 60, misses'])
    ok(L, 'ladder still read against the top-level 70 bar', n['card']['ladderNote'], '', 'Below 70% the edge is gone' in n['card']['ladderNote']); ok(L, 'how-to bar', n['howBar'], '70% bar')
    ok(L, 'cloud unavailable', [x['text'] for x in ch['cloud'] if x['tag'] == 'text'], ['Past paths unavailable in this feed']); ok(L, 'no script errors', e, [])
    ok(L, 'cloud caption cleared (no stale figures)', (ch['cloudSub'], ch['cloudNote']), ('', ''))
    # 9 ledger missing / empty / cut short / malformed
    hdr = ledR.split('\n')[0]; lines = ledR.strip().split('\n')
    for nm, body in (('missing', None), ('empty file', ''), ('header only', hdr + '\n'), ('cut short', '\n'.join(lines[:400]) + '\n' + lines[400][:37]), ('one top-grade row dropped', '\n'.join(l for i, l in enumerate(lines) if i != next(j for j, x in enumerate(lines) if ',A+,' in x)) + '\n'),
                     ('a row with a column missing', '\n'.join(l if i != next(j for j, x in enumerate(lines) if ',A+,' in x) else l.rsplit(',', 1)[0] for i, l in enumerate(lines)) + '\n'), ('garbage', '<html>502 Bad Gateway</html>')):
        n, ch, rc, e = view(br, RP, {'data/ledger.csv': body}, tab='record'); L = f'synthetic: ledger {nm}'
        ok(L, 'previous signals says unavailable, lists none', (n['prevClosedNone'], len([x for x in n['prevClosed'] if 'closed' in x['cls']])), (['Past signals unavailable right now.'], 0))
        ok(L, 'past signals tab', (rc['count'], len(rc['rows'])), ('Past signals unavailable right now', 0)); ok(L, 'no script errors', e, [])
    # a ledger cut after its last top-grade row is still whole for the page (it shows top-grade rows only)
    # 10 chart file missing / empty / short / malformed / one bar behind
    cj = PL.candles_json(RP, 'BTC_1D')
    for nm, body in (('missing', None), ('empty', ''), ('9 bars', dict(cj, bars=cj['bars'][-9:])), ('a non-numeric bar', dict(cj, bars=cj['bars'][:-3] + [dict(cj['bars'][-3], h=None)] + cj['bars'][-2:])), ('not JSON', '<html>'), ('no bars key', {'chart': 'BTC 1D'})):
        n, ch, rc, e = view(br, RP, {'data/candles/BTC_1D.json': body}, sel='BTC-1D-2026-11-13', tab='chart'); L = f'synthetic: chart file {nm}'
        ok(L, 'chart says unavailable for this chart', [x['text'] for x in ch['svg'] if x['tag'] == 'text'], ['Chart data unavailable for BTC 1D']); ok(L, 'side box, cloud cleared', (len(ch['side']), ch['cloudSub'], ch['cloudNote'], len(ch['cloud'])), (0, '', '', 0)); ok(L, 'no script errors', e, [])
    cj2 = PL.candles_json(CU, 'BTC_2D')
    n, ch, rc, e = view(br, CU, {'data/candles/BTC_2D.json': dict(cj2, bars=cj2['bars'][-12:])}, sel=oid, tab='chart'); L = 'synthetic: chart file too short to reach a live entry'
    ok(L, 'says it does not reach the entry', [x['text'] for x in ch['svg'] if x['tag'] == 'text'], ["This chart's data doesn't reach back to the entry"]); ok(L, 'side cleared', len(ch['side']), 0)
    n, ch, rc, e = view(br, RP, {'data/candles/BTC_1D.json': dict(cj, bars=cj['bars'][:-1])}, sel='BTC-1D-2026-11-13', tab='chart'); L = 'synthetic: chart file one daily bar behind the feed'
    tl = next((x for x in ch['svg'] if x['tag'] == 'text' and x['text'] == 'Today'), None); nb = len(cj['bars']) - 1
    opens = nb + 62  # slots
    ok(L, '"Today" line is drawn on the last bar served (yesterday\'s), though the feed is today\'s', 'Today on bar of ' + str(dt.datetime.fromtimestamp(cj['bars'][-2]['t'], dt.timezone.utc).date()), 'Today = 2026-11-12', False if tl else None)
    # 11 example files
    exj = json.load(open(RP + '/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
    for nm, body in (('missing', None), ('empty', ''), ('cut short (stops before day 60)', dict(exj, bars=exj['bars'][:exj['entry_index'] + 20])), ('a non-numeric bar', dict(exj, bars=exj['bars'][:5] + [dict(exj['bars'][5], c='x')] + exj['bars'][6:])), ('no entry_index', {k: v for k, v in exj.items() if k != 'entry_index'})):
        n, ch, rc, e = view(br, RP, {'data/example_ETH-2D-2024-09-22.json': body}, sel='example', tab='chart'); L = f'synthetic: example chart file {nm}'
        ok(L, 'example chart unavailable', (ch['sub'], [x['text'] for x in ch['svg'] if x['tag'] == 'text']), ("The example's chart data couldn't be loaded.", ['Chart data unavailable']))
        ok(L, 'the example card itself still shows (it comes from the feed)', n['card']['state'], 'Confirmed setup'); ok(L, 'no script errors', e, [])
    f = copy.deepcopy(feedR); f['example_card'] = None
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, sel='example', tab='chart'); L = 'synthetic: example card missing from the feed'
    ok(L, 'card', n['card']['state'], 'Example unavailable'); ok(L, 'chart', ch['viewText'], '', 'Chart data unavailable' in ch['viewText'] and not ch['side'])
    # 12 an asset/grade with no misses
    f = copy.deepcopy(feedR)
    for x in f['if_it_misses']:
        if x['asset'] == 'BTC' and x['grade'] == 'C': x.update(misses=0, up_first=0, median_peak_pct=None, mean_peak_pct=None, peaked_5_or_more=0, peaked_10_or_more=0, median_worst_drop_pct=None, median_day60_pct=None)
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, sel='BTC-1D-2026-11-13'); L = 'synthetic: asset/grade with no misses'
    sg = next(x for x in feedR['if_it_misses'] if x['asset'] == 'BTC' and x['grade'] == 'C')['signals']
    ok(L, 'miss row', n['card']['kv'][3][1], 'none missed'); ok(L, 'miss tiles', n['card']['tiles'][6:], [[f'Typical worst drop, misses · 0 misses of all {sg} BTC same-grade signals', 'n/a'], [f'Typical change by day 60, misses · 0 misses of all {sg} BTC same-grade signals', 'n/a']])
    # 13 a card with an empty sample
    f = copy.deepcopy(feedR); c = next(x for x in f['cards'] if x['signal_id'] == 'BTC-1D-2026-11-13')
    for k in list(c):
        if k.endswith('_pct') or k.startswith('typical_day'): c[k] = None
    c.update(past_trades=0, past_signals=0, sample='all 0 past signals of the same grade across all BTC charts (BTC 1D alone has only 0, too few to use)')
    c['from_entry'] = dict(past_trades=0, past_signals=0, still_rose10_pct=None, went_on_to_fall25_pct=None, still_rose10_exact_pct=None)
    for r_ in c['if_it_falls_first']: r_.update(past_trades=0, past_signals=0, still_rose10_pct=None, went_on_to_fall25_pct=None, still_rose10_exact_pct=None)
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, sel='BTC-1D-2026-11-13', tab='chart'); L = 'synthetic: card with an empty sample'
    ok(L, 'card', (n['card']['state'], n['card']['empty']), ('No odds yet', 'No past signals like this one yet This setup has no finished past signals to draw odds from, so no figures are shown for it.'))
    ok(L, 'picker shows n/a and n 0, no stray %', next(p['t'] for p in n['picker'] if p['sel'] == 'BTC-1D-2026-11-13'), 'BTC 1D n/a rose 10% in 60 days · n 0 · not top grade · confirms 13 Nov 2026')
    ok(L, 'chart', [x['text'] for x in ch['svg'] if x['tag'] == 'text'], ['No odds to draw yet']); ok(L, 'no script errors', e, [])
    # 14 lead-trader feed with trades
    tr = {"trades": [{"asset": "ETH", "direction": "long", "action": "open", "time": "2026-11-11T15:04:00Z", "price": 2031.5, "leverage": 3.3, "size_pct": 37.5},
                     {"asset": "BTC", "direction": "long", "action": "close", "time": "2026-11-09T10:00:00Z", "price": 1234567.891, "leverage": 3.25, "size_pct": 35, "move_pct": -0.04, "account_pct": -12.345},
                     {"asset": "BTC", "direction": "long", "action": "open", "time": "2026-11-01T10:00:00Z", "price": 0.5, "leverage": 1, "size_pct": 100, "move_pct": 0, "account_pct": 4.25}]}
    n, ch, rc, e = view(br, RP, {'data/trades.json': tr}, sel='ETH-1D-2026-11-13', tab='chart'); L = 'synthetic: lead-trader feed with trades'
    ok(L, 'trade 1', n['trades'][0], 'ETH long · open 11 Nov 2026 Price $2,031.50 3.3x 37.5% of acct'); ok(L, 'trade 2 (large price, values that round to zero show no sign)', n['trades'][1], f'BTC long · close 9 Nov 2026 Price $1,234,567.89 3.3x 35.0% of acct Move 0.0% Account {MINUS}12.3%')
    ok(L, 'trade 3 (small price, 0% and 100%)', n['trades'][2], 'BTC long · open 1 Nov 2026 Price $0.50 1.0x 100.0% of acct Move 0.0% Account +4.3%')
    ok(L, 'card marker for ETH', n['card']['marker'], 'Lead trader: in · long'); ok(L, 'chart note', ch['side'][-2]['text'], "The lead trader's real entries and exits are listed on the Now tab; they are not drawn on this chart.")
    n2, _, _, _ = view(br, RP, {'data/trades.json': tr}, sel='BTC-1D-2026-11-13'); ok(L, 'card marker for BTC (last trade a close)', n2['card']['marker'], 'Lead trader: out')
    n3, _, _, _ = view(br, RP, {'data/trades.json': {"trades": []}}, sel='BTC-1D-2026-11-13'); ok(L + ', empty list', 'marker and panel', (n3['card']['marker'], n3['lead']), ('Lead trader: not in', "No trades posted yet. The lead trader's real entries and exits appear here the moment they fill."))
    n4, _, _, _ = view(br, RP, {'data/trades.json': {"trades": tr['trades'][:1]}}, sel='BTC-1D-2026-11-13'); ok(L + ', trades in the other asset only', 'marker for an asset he has not traded', n4['card']['marker'], 'Lead trader: not in')
    ok(L, 'no dollar amounts other than prices', [x for x in n['trades'] if x.count('$') != 1], [])
    # 15 odd but valid values
    f = copy.deepcopy(feedR); c = next(x for x in f['cards'] if x['signal_id'] == 'BTC-1D-2026-11-13')
    c.update(rose10_within60d_pct=100, rose10_never_fell25_within60d_pct=0, rose20_within60d_pct=0, fell30_within60d_pct=100, typical_biggest_rise_exact_pct=0.04, typical_biggest_rise_pct=0.0, typical_deepest_dip_exact_pct=-0.049999, typical_deepest_dip_pct=0.0,
             typical_dip_before_rise_exact_pct=-0.05, typical_dip_before_rise_pct=-0.1, must_close_above=1234567.89, price_now=1234567.89)
    c['from_entry'].update(still_rose10_pct=70, still_rose10_exact_pct=69.999999); c['if_it_falls_first'][0].update(still_rose10_pct=100, still_rose10_exact_pct=100.0); c['if_it_falls_first'][1].update(still_rose10_pct=70, still_rose10_exact_pct=70.0); c['if_it_falls_first'][3].update(still_rose10_pct=0, still_rose10_exact_pct=0.0)
    c['before_2022'].update(past_trades=0, past_signals=0, rose10_never_fell25_within60d_pct=None)
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f}, sel='BTC-1D-2026-11-13', tab='chart'); L = 'synthetic: odd but valid values'
    ok(L, 'big 100%, line 0%', (n['card']['big'], n['card']['odds'][2]), ('100%', '0% did it without ever falling 25.3%'))
    ok(L, 'values that round to zero show no sign', (n['card']['kv'][0][1], n['card']['kv'][1][1]), ('0.0%', '0.0%')); ok(L, '-0.05 rounds half away to -0.1', n['card']['tiles'][0][1], f'{MINUS}0.1%')
    ok(L, 'edge on the exact share: 69.999999 shown as 70% is below the bar', (n['card']['kv'][2][1], n['card']['ladder'][0]['val'], n['card']['ladder'][0]['gone']), ('Below the 70% bar from entry', '70%', True))
    ok(L, 'exact 70.0 is not below the bar; 100% and 0% rows', [(x['val'], x['gone']) for x in n['card']['ladder'][1:]], [('100%', False), ('70%', False), (n['card']['ladder'][3]['val'], n['card']['ladder'][3]['gone']), ('0%', True)])
    ok(L, 'era with no signals', (n['card']['eras'][0]['label'], n['card']['eras'][0]['val']), ('Before 2022 n 0', 'n/a')); ok(L, 'large price', n['card']['smalls'][0], '', n['card']['smalls'][0].endswith('if it closes above $1,234,567.89'))
    tags = sorted(x['text'] for x in ch['svg'] if x['tag'] == 'text' and x.get('fill') == '#07060F')
    ok(L, 'chart price tags at a large price (exact cents)', tags, sorted(['$1,234,567.89', money(PL.px_at('1234567.89', 10)), money(PL.px_at('1234567.89', '0.04')), money(PL.px_at('1234567.89', '-0.049999'))]))
    ok(L, 'no script errors', e, [])
    # tiny prices
    f = copy.deepcopy(feedR); c = next(x for x in f['cards'] if x['signal_id'] == 'BTC-1D-2026-11-13'); c.update(price_now=0.37, must_close_above=0.36)
    small = dict(cj, bars=[dict(b, o=b['o'] / 2e5, h=b['h'] / 2e5, l=b['l'] / 2e5, c=b['c'] / 2e5) for b in cj['bars']])
    n, ch, rc, e = view(br, RP, {'data/ctzb_feed.json': f, 'data/candles/BTC_1D.json': small}, sel='BTC-1D-2026-11-13', tab='chart'); L = 'synthetic: very small prices'
    tags = sorted(x['text'] for x in ch['svg'] if x['tag'] == 'text' and x.get('fill') == '#07060F')
    ok(L, 'price tags to the cent', tags, sorted([money('0.37'), money(PL.px_at('0.37', 10)), money(PL.px_at('0.37', c['typical_biggest_rise_exact_pct'])), money(PL.px_at('0.37', c['typical_deepest_dip_exact_pct']))]))
    ax = [x['text'] for x in ch['svg'] if x['tag'] == 'text' and re.fullmatch(r'\$[\d,]+', x['text'])]
    ok(L, 'price-axis labels distinguish their gridlines', ax, 'distinct labels', len(ax) == len(set(ax)) and len(ax) > 0)
    # 16 the page never shows a grade letter or an internal name
    for root, fd in ((RP, feedR), (CU, feedC)):
        n, ch, rc, e = view(br, root, sel=fd['open_signals'][0]['signal_id'] if False else None, tab='chart')
        txt = n['text'] + ' ' + ch['viewText']
        ok(f'synthetic: wording scan {os.path.basename(root)}', 'no grade letter / internal names in member text', re.findall(r'\b(A\+|grade [ABC]\b|surv10|scaled20|GAP|FCOOL|UP8|BTCX|FASTCT|bucket|lens)\b', txt), [])
        ok(f'synthetic: wording scan {os.path.basename(root)}', 'no "trade taken" / "return" / "track record" claim', [m for m in re.findall(r'[^.]*\b(?:track record|strategy return|win rate|profit)\b[^.]*\.', txt) if 'not a' not in m and 'not ' not in m], [])
    br.close()

with open(sys.argv[1], 'w', newline='') as fo:
    w = csv.writer(fo); w.writerow(['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writerows(R.rows)
bad = R.bad(); print('SYNTH comparisons', len(R.rows), 'defects', len(bad))
for r in bad: print('  ', r[1], '|', r[2], '|', r[3][:160], '|', r[4][:160])
