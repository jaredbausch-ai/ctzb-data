"""Audit #20 group C -- page-level synthetic / broken states. The page is served tampered inputs; each row is
(state, location, label, shown, expected-by-me, ok, cause). 'Expected' = the value fed in, or a safe "unavailable"."""
import json, csv, os, re, sys, copy, datetime as dt, gzip
from playwright.sync_api import sync_playwright
import apage as P
from apage import norm, low
from adata import Checks

ROOT = os.path.abspath(sys.argv[1]); OUT = sys.argv[2]
FEED = json.load(open(f'{ROOT}/feed/ctzb_feed.json')); LEDGER = open(f'{ROOT}/datasets/ledger.csv').read()
EX = open(f'{ROOT}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json').read()
BAD = re.compile(r"\$\{|undefined|NaN|null%|n/a%|\[object|Infinity|null\b")
GEN = dt.datetime.fromisoformat(FEED['generated_at'].replace('Z', '+00:00'))
rows = []


def snap(pw, name, feed='keep', ledger='file', example='file', candles='file', trades=None, clock_h=0.1, picks=(), tabs=('now', 'chart', 'record', 'read'), preview=None, hap=False):
    fb = (json.dumps(feed) if isinstance(feed, dict) else feed) if feed != 'keep' else json.dumps(FEED)
    s = P.Site(ROOT, feed=fb, ledger=ledger, example=example, candles=candles, trades=trades, pw=pw, clock=GEN + dt.timedelta(hours=clock_h)).open()
    out = dict(name=name)
    for p in picks: s.pick(p)
    if preview is not None and s.pg.is_checked('#previewSwitch') != preview: s.pg.click('#previewSwitch'); s.pg.wait_for_timeout(300)
    out['now'] = s.now()
    if 'chart' in tabs:
        s.tab('chart')
        if hap and s.pg.is_visible('#bHap'): s.pg.click('#bHap'); s.pg.wait_for_timeout(300)
        out['chart'] = s.chart(); out['chart_text'] = s.pg.inner_text('#view-chart')
    if 'record' in tabs: s.tab('record'); out['rec'] = s.rec('all'); out['rec_text'] = s.pg.inner_text('#view-record')
    if 'read' in tabs: s.tab('read'); out['read_text'] = s.pg.inner_text('#view-read')
    out['all'] = ' '.join([out['now']['body'], out.get('chart_text', ''), out.get('rec_text', ''), out.get('read_text', '')])
    out['errors'] = list(s.errors); s.close()
    return out


def run():
    C = Checks('synthetic')
    def std(o, allow_err=False):
        st = o['name']; C.state = 'C:' + st
        C.add('page', 'no raw placeholder anywhere (${, undefined, NaN, null, [object)', (BAD.search(o['all']).group(0) if BAD.search(o['all']) else ''), '', 'placeholder shown')
        C.add('page', 'javascript errors', len(o['errors']), 0, 'page error: ' + '; '.join(o['errors'])[:160])
    with sync_playwright() as pw:
        figs = lambda t: re.findall(r'[+−-]?\d+(?:\.\d+)?%', t or '')
        # ---------- C1 feed down (404), C2 malformed, C2b 5xx-ish empty body
        for nm, fb in (('feed-404', None), ('feed-malformed-json', '{"schema_version": 6, "cards": [ {'), ('feed-empty-body', ''), ('feed-html-error-page', '<html>502 Bad Gateway</html>')):
            o = snap(pw, nm, feed=fb); std(o); n = o['now']
            C.add('header', 'filter pill', norm(n['filter']), 'Feed unavailable', 'feed down'); C.add('card', 'state', norm(n['card']['state']), 'Data unavailable', 'feed down')
            C.add('card', 'says outage, not a quiet market', 'This is an outage, not a quiet market' in ' '.join(n['card']['emptySmalls']), True, 'feed down')
            C.add('picker', 'rows', ' | '.join(norm(x) for x in n['pnone']), 'Feed unavailable. | Feed unavailable.', 'feed down'); C.add('previous', 'intact', norm(n['prevIntactNone']), "Unavailable: the feed can't be read right now.", 'feed down')
            C.add('banner', 'scored', 'scored unavailable' in norm(n['rv']), True, 'feed down'); C.add('footer', 'state', norm(n['foot']), '', 'feed down')
            C.add('card', 'no percentage on the card', len(figs(n['card']['big'] or '') + figs(' '.join(n['card']['emptySmalls']))), 0, 'figure shown with the feed down')
            C.add('chart', 'chart unavailable', 'Chart data unavailable' in o['chart_text'] or "couldn't be loaded" in o['chart_text'], True, 'feed down chart')
            C.add('chart', 'no figure in the chart side box', len(figs(' '.join(b['text'] or '' for b in o['chart']['side']))), 0, 'figure shown with the feed down')
            C.add('past signals', 'summary boxes (need the feed)', len(o['rec']['sum']), 0, 'feed down record')
            C.add('how-to', 'bar not typed', 'posting bar' in o['read_text'] and '70%' not in o['read_text'], True, 'feed down how-to')
        # ---------- C3 held
        f = copy.deepcopy(FEED); f.update(cards_withheld=True, alerts_withheld=True, cards=[], open_signals=[], example_card=None); f['checks'].update(all_passed=False, failed_steps=['cards'])
        o = snap(pw, 'feed-held');
        o = snap(pw, 'feed-held', feed=f); std(o); n = o['now']
        C.add('card', 'state', norm(n['card']['state']), 'Setups held back', 'held'); C.add('picker', 'rows', ' | '.join(norm(x) for x in n['pnone']), 'Held back: a data check failed on the latest run. | Held back: a data check failed on the latest run.', 'held')
        C.add('footer', 'checks', 'checks FAILED, cards held back' in norm(n['foot']), True, 'held'); C.add('previous', 'intact', norm(n['prevIntactNone']), 'Held back: a data check failed on the latest run.', 'held')
        C.add('card', 'example not auto-shown', n['preview'], False, 'held')
        # held but cards left in by mistake (hand edit): page must still not show them? (it shows what the feed lists)
        f2 = copy.deepcopy(FEED); f2['cards_withheld'] = True
        o = snap(pw, 'feed-held-flag-but-cards-present', feed=f2); std(o); n = o['now']
        C.add('card', 'a feed flagged withheld shows no setup card', norm(n['card']['state']) in ('Setups held back',), True, 'withheld flag ignored when cards are present')
        # ---------- C4 fail-closed feed
        fc = {"schema_version": 6, "generated_at": FEED['generated_at'], "posting_bar_pct": 70, "scored_as_of": None, "label": FEED['label'],
              "checks": {"passed": False, "all_passed": False, "lines": [], "steps": {}, "failed_steps": ["feed"]}, "feed_error": "KeyError", "cards_withheld": True, "alerts_withheld": True,
              "extras_withheld": True, "alerts": [], "cards": [], "prints": [], "open_signals": [], "confluence_windows": [], "grade_odds": [], "if_it_misses": [], "past_paths": [], "candle_check": None,
              "example_card": None, "example_past_paths": None, "example_if_it_misses": None, "odds_fade": {"label": FEED['label'], "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}}
        o = snap(pw, 'feed-fail-closed', feed=fc); std(o); n = o['now']
        C.add('header', 'filter pill', norm(n['filter']), 'Market filter: unavailable', 'fail-closed'); C.add('banner', 'scored', 'scored unavailable' in norm(n['rv']), True, 'fail-closed')
        C.add('card', 'state', norm(n['card']['state']), 'Setups held back', 'fail-closed'); C.add('past signals', 'ledger still listed (count line)', bool(re.match(r'\d+ signals', norm(o['rec']['count']))), True, 'fail-closed record')
        o = snap(pw, 'feed-fail-closed-example-on', feed=fc, preview=True); std(o)
        C.add('card', 'example', norm(o['now']['card']['state']), 'Example unavailable', 'fail-closed example')
        # ---------- C5 stale
        for h, nm in ((5.5, 'feed-stale-5h30'), (30, 'feed-stale-30h'), (4.9, 'feed-4h54-not-stale')):
            o = snap(pw, nm, clock_h=h); std(o); n = o['now']; st = n['card']['stale']
            C.add('card', 'stale note', norm(st), (f'This data is {int(h)} hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.' if h > 5 else ''), 'stale note')
        q = copy.deepcopy(FEED); q['cards'] = []; q['open_signals'] = []
        o = snap(pw, 'quiet-feed-stale-9h', feed=q, clock_h=9); std(o); n = o['now']
        C.add('card', 'stale quiet feed: example not auto-shown, stale note on the quiet card', [n['preview'], bool(n['card']['stale'])], [False, True], 'stale quiet')
        o = snap(pw, 'quiet-feed-fresh', feed=q); std(o); n = o['now']
        C.add('card', 'fresh quiet feed opens on the example', n['preview'], True, 'quiet')
        o = snap(pw, 'quiet-feed-fresh-example-off', feed=q, preview=False); std(o); n = o['now']
        led = [r for r in csv.DictReader(LEDGER.splitlines()) if r['grade'] == 'A+']; y1 = int(FEED['generated_at'][:4]) - 1
        k = sum(1 for r in led if 2020 <= int(r['entry'][:4]) <= y1); per = int(k / (y1 - 2019) + 0.5)
        C.add('card', 'quiet text, times a year', norm(n['card']['emptySmalls'][0]), f'The market filter is on. Nothing at the top grade is forming or confirmed today. Top-grade setups come about {per} times a year (2020 to {y1} average; bear years, when the market filter is off, are included).', 'quiet times a year')
        qo = copy.deepcopy(q); qo['market_regime'] = 'Bearish'
        o = snap(pw, 'quiet-feed-filter-off', feed=qo, preview=False); std(o); n = o['now']
        C.add('card', 'quiet text, filter off', norm(n['card']['emptySmalls'][0]), 'The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.', 'quiet off')
        C.add('header', 'filter pill', norm(n['filter']), 'Market filter: off', 'filter off')
        # ---------- C6/7 ledger missing / empty / cut / malformed / edited
        half = '\n'.join(LEDGER.splitlines()[:400]) + '\n'
        for nm, lb in (('ledger-404', None), ('ledger-header-only', LEDGER.splitlines()[0] + '\n'), ('ledger-cut-short', half), ('ledger-garbage', 'this is not a csv\n\x00\x01'), ('ledger-cut-mid-row', LEDGER[:len(LEDGER) // 2])):
            o = snap(pw, nm, ledger=lb); std(o); n = o['now']
            C.add('past signals', 'count line', norm(o['rec']['count']), 'Past signals unavailable right now', 'ledger unavailable'); C.add('past signals', 'rows', len(o['rec']['rows']), 0, 'ledger unavailable')
            C.add('previous', 'closed list', norm(n['prevClosedNone']), 'Past signals unavailable right now.', 'ledger unavailable')
            C.add('card', 'card still shown from the feed', norm(n['card']['state']) in ('Setup forming', 'Live setup'), True, 'ledger unavailable')
        o = snap(pw, 'ledger-404-quiet', feed=q, ledger=None, preview=False); std(o)
        C.add('card', 'quiet text without a ledger has no times-a-year figure', 'times a year' in norm(o['now']['card']['emptySmalls'][0]), False, 'ledger unavailable quiet')
        # one extra top-grade row / one dropped row -> count differs from grade_odds -> unavailable
        L = LEDGER.splitlines(); ia = next(i for i, l in enumerate(L) if ',A+,' in l)
        for nm, lb in (('ledger-one-row-dropped', '\n'.join(L[:ia] + L[ia + 1:]) + '\n'), ('ledger-one-row-duplicated', '\n'.join(L[:ia] + [L[ia]] + L[ia:]) + '\n')):
            o = snap(pw, nm, ledger=lb); std(o)
            C.add('past signals', 'count line', norm(o['rec']['count']), 'Past signals unavailable right now', 'ledger count mismatch')
        # a hand-edited figure (same row count): the page cannot know; it must show the file's value, formatted
        hdr = L[0].split(','); cells = next(csv.reader([L[ia]])); bi = hdr.index('bestMove'); cells[bi] = '999.949999'
        import io; buf = io.StringIO(); csv.writer(buf, lineterminator='').writerow(cells)
        o = snap(pw, 'ledger-hand-edited-figure', ledger='\n'.join(L[:ia] + [buf.getvalue()] + L[ia + 1:]) + '\n'); std(o)
        C.add('past signals', 'edited best move is shown as fed (the page trusts the file)', any('+999.9%' in ' '.join(r) for r in o['rec']['rows']), True, 'ledger edit shown')
        # ---------- C9 candles
        def cj(n_=None, mut=None):
            def f(a, tf):
                p = f'{ROOT}/datasets/candles_{a.lower()}_{tf.lower()}.csv'
                bars = [{'t': float(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])} for r in csv.DictReader(open(p))]
                if n_ is not None: bars = bars[:n_] if n_ > 0 else bars[n_:]
                if mut: bars = mut(bars)
                return json.dumps({'chart': f'{a} {tf}', 'bars': bars})
            return f
        livesid = next(o_['signal_id'] for o_ in FEED['open_signals'] if o_['grade'] == 'A+')
        formsid = FEED['cards'][0]['signal_id'] if FEED['cards'] else None
        def strbar(b): b[3]['c'] = 'abc'; return b
        def nullbar(b): b[5]['h'] = None; return b
        for nm, cd in (('candles-404', None), ('candles-9-bars', cj(-9)), ('candles-non-numeric-bar', cj(mut=strbar)), ('candles-null-high', cj(mut=nullbar)), ('candles-not-json', 'oops'), ('candles-empty-bars', json.dumps({'chart': 'x', 'bars': []})),
                       ('candles-bars-not-a-list', json.dumps({'chart': 'x', 'bars': {'a': 1}}))):
            for sel in [x for x in (livesid, formsid) if x]:
                o = snap(pw, f'{nm} {sel}', candles=cd, picks=(sel,), tabs=('now', 'chart')); std(o)
                C.add('chart', 'unavailable message', 'Chart data unavailable for' in o['chart_text'], True, 'chart file broken')
                C.add('chart', 'side box and cloud cleared', [len(o['chart']['side']), len(o['chart']['cloud']), norm(o['chart']['cloudNote'])], [0, 0, ''], 'chart leftovers')
        # live setup whose chart file doesn't reach back to the entry
        o = snap(pw, f'candles-last-12-bars {livesid}', candles=cj(-12), picks=(livesid,), tabs=('now', 'chart')); std(o)
        C.add('chart', 'entry not in the file', "This chart's data doesn't reach back to the entry" in o['chart_text'], True, 'chart entry missing')
        # stale chart file (last bars missing): forming chart must not say "Today"
        if formsid:
            o = snap(pw, f'candles-2-days-old {formsid}', candles=cj(68), picks=(formsid,), tabs=('now', 'chart')); std(o)
            tx = [e['text'] for e in o['chart']['svg'] if e['tag'] == 'text']
            C.add('chart', 'last bar labelled as a past date, not "Today"', ['Today' in tx, any((t or '').startswith('Latest bar · ') for t in tx)], [False, True], 'stale chart label')
        # ---------- C10 example file
        exj = json.loads(EX); cut = dict(exj, bars=exj['bars'][:exj['entry_index'] + 10]); bad = copy.deepcopy(exj); bad['bars'][3]['c'] = None
        for nm, eb in (('example-file-404', None), ('example-file-cut-short', json.dumps(cut)), ('example-file-null-close', json.dumps(bad)), ('example-file-garbage', '<html>'), ('example-file-no-entry-index', json.dumps({'bars': exj['bars']}))):
            o = snap(pw, nm, example=eb, picks=('example',), tabs=('now', 'chart')); std(o)
            C.add('chart', 'example chart unavailable', "The example's chart data couldn't be loaded." in o['chart_text'], True, 'example file broken')
            C.add('card', 'example card itself still shown (it is in the feed)', norm(o['now']['card']['state']), 'Confirmed setup', 'example card')
        fx = copy.deepcopy(FEED); fx['example_card'] = None
        o = snap(pw, 'example-card-null', feed=fx, picks=('example',), tabs=('now', 'chart')); std(o)
        C.add('card', 'example', norm(o['now']['card']['state']), 'Example unavailable', 'example card null'); C.add('chart', 'example chart', 'Chart data unavailable' in o['chart_text'], True, 'example card null')
        # ---------- C11 extras withheld
        fe = copy.deepcopy(FEED); fe.update(extras_withheld=True, if_it_misses=[], past_paths=[], example_past_paths=None, example_if_it_misses=None)
        fe['odds_fade'] = {"label": FEED['label'], "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}
        for sel in [x for x in (livesid, formsid, 'example') if x]:
            o = snap(pw, f'extras-withheld {sel}', feed=fe, picks=(sel,), tabs=('now', 'chart')); std(o); n = o['now']
            C.add('card', 'if it misses', norm(n['card']['kv'][3][1]), 'n/a', 'extras withheld'); C.add('card', 'miss tiles', [norm(n['card']['tiles'][6][1]), norm(n['card']['tiles'][7][1])], ['n/a', 'n/a'], 'extras withheld')
            C.add('card', 'ladder still read against the 70% bar', 'Below 70% the edge is gone' in norm(n['card']['ladderFine']), True, 'extras withheld bar')
            C.add('chart', 'cloud', 'Past paths unavailable in this feed' in ' '.join(e.get('text') or '' for e in o['chart']['cloud']), True, 'extras withheld cloud')
        fb_ = copy.deepcopy(fe); fb_['posting_bar_pct'] = None
        for sel in [x for x in (livesid, formsid) if x]:
            o = snap(pw, f'no-posting-bar-anywhere {sel}', feed=fb_, picks=(sel,), tabs=('now', 'chart', 'read')); std(o); n = o['now']
            C.add('card', 'edge gone below', norm(n['card']['kv'][2][1]), 'n/a', 'no bar: no edge read'); C.add('how-to', 'bar', '70%' in o['read_text'], False, 'no typed bar')
        # ---------- C12 made-up asset / chart
        fm = copy.deepcopy(FEED); c0 = copy.deepcopy(FEED['cards'][0] if FEED['cards'] else FEED['open_signals'][0]['card'])
        c0.update(chart='SOL 1D', asset='SOL', timeframe='1D', signal_id='SOL-1D-2026-11-13', grade='A+', bars_to_confirm=1, confirms_on='2026-11-13', low_date='2026-11-10', low_day='2026-11-10', price_now=199.99, must_close_above=180.0); fm['cards'] = [c0] + fm['cards']
        o = snap(pw, 'made-up-asset-forming-card', feed=fm, picks=('SOL-1D-2026-11-13',), tabs=('now', 'chart')); std(o); n = o['now']
        C.add('card', 'where', low(n['card']['where']), 'sol · 1d chart', 'made-up asset'); C.add('card', 'if it misses (no SOL pool)', norm(n['card']['kv'][3][1]), 'n/a', 'made-up asset misses')
        C.add('chart', 'chart', 'Chart data unavailable for SOL 1D' in o['chart_text'], True, 'made-up asset chart')
        fo = copy.deepcopy(FEED); o0 = copy.deepcopy(next(x for x in FEED['open_signals'] if x['grade'] == 'A+')); o0.update(chart='DOGE 7D', signal_id='DOGE-7D-2026-10-01', entry_date='2026-10-01'); o0['card'].update(chart='DOGE 7D', asset='DOGE', timeframe='7D')
        fo['open_signals'] = [o0] + fo['open_signals']
        o = snap(pw, 'made-up-asset-live-signal', feed=fo, picks=('DOGE-7D-2026-10-01',), tabs=('now', 'chart')); std(o)
        C.add('chart', 'chart', 'Chart data unavailable for DOGE 7D' in o['chart_text'], True, 'made-up asset chart')
        # ---------- C13 made-up prices / figures in the feed (the page shows what it is fed, formatted, never a placeholder)
        if FEED['cards']:
            for nm, mut in (('price_now-null', dict(price_now=None)), ('price_now-zero', dict(price_now=0)), ('price_now-negative', dict(price_now=-5)), ('price_now-string', dict(price_now='abc')), ('price_now-huge', dict(price_now=1e15)),
                            ('must_close_above-zero', dict(must_close_above=0)), ('rose10-null', dict(rose10_within60d_pct=None)), ('medians-null', dict(typical_biggest_rise_exact_pct=None, typical_biggest_rise_pct=None, typical_deepest_dip_exact_pct=None, typical_deepest_dip_pct=None)),
                            ('timing-null', dict(typical_day_of_60d_high=None, typical_day_of_deepest_dip=None)), ('ladder-missing', dict(if_it_falls_first=None, from_entry=None)), ('eras-missing', dict(before_2022=None, since_2022=None)),
                            ('low_day-missing', dict(low_day=None, low_date=None)), ('confirms_on-missing', dict(confirms_on=None)), ('sample-html', dict(sample='all 17 <img src=x onerror=alert(1)> signals')),
                            ('n-zero', dict(past_trades=0, past_signals=0)), ('rose10-150', dict(rose10_within60d_pct=150))):
                f_ = copy.deepcopy(FEED); f_['cards'][0].update(mut); sid_ = f_['cards'][0]['signal_id']
                o = snap(pw, f'card-{nm}', feed=f_, picks=(sid_,), tabs=('now', 'chart')); std(o); n = o['now']
                if nm == 'rose10-null': C.add('card', 'big number', norm(n['card']['big']), 'n/a', 'null share')
                if nm == 'n-zero': C.add('card', 'state', norm(n['card']['state']), 'No odds yet', 'empty sample')
                if nm == 'sample-html': C.add('card', 'markup in a feed string is shown as text, not run', '<img' in (n['card']['odds'][3] if len(n['card']['odds']) > 3 else ''), True, 'html injection')
                if nm == 'rose10-150': C.add('card', 'an impossible share is shown as fed (the page does not range-check)', norm(n['card']['big']), '150%', 'out-of-range share shown')
                if nm == 'price_now-null': C.add('chart', 'levels fall back to the last bar close', 'price levels drawn from today' in o['chart_text'], True, 'price fallback')
        # hand-edited shares: shown share says 70, exact says 69.9 -> the bar is tested on the exact one
        if FEED['cards']:
            f_ = copy.deepcopy(FEED); c_ = f_['cards'][0]; c_['from_entry'].update(still_rose10_pct=70, still_rose10_exact_pct=69.999999)
            o = snap(pw, 'card-edge-exact-vs-shown', feed=f_, picks=(c_['signal_id'],), tabs=('now',)); std(o); n = o['now']
            C.add('card', 'edge read on the exact share', norm(n['card']['kv'][2][1]), 'Below the 70% bar from entry', '70% bar on exact share'); C.add('card', 'ladder row 0 shows 70% marked below the bar', [norm(n['card']['ladder'][0][1]), 'gone' in n['card']['ladder'][0][3]], ['70%', True], '70% bar on exact share')
            f_ = copy.deepcopy(FEED); c_ = f_['cards'][0]; c_['from_entry'].update(still_rose10_pct=70, still_rose10_exact_pct=70.0)
            for r_ in c_['if_it_falls_first']: r_.update(still_rose10_pct=70, still_rose10_exact_pct=70.0)
            o = snap(pw, 'card-edge-exactly-70-everywhere', feed=f_, picks=(c_['signal_id'],), tabs=('now',)); std(o)
            C.add('card', 'exactly 70% is not below the bar', norm(o['now']['card']['kv'][2][1]), 'Holds at every level', '70% bar boundary')
        # ---------- C15 live signal without card / status; made-up status / days
        for nm, mut, exp in (('live-card-null', dict(card=None), 'Card unavailable'),):
            f_ = copy.deepcopy(FEED); o_ = next(x for x in f_['open_signals'] if x['grade'] == 'A+'); o_.update(mut)
            o = snap(pw, nm, feed=f_, picks=(o_['signal_id'],), tabs=('now', 'chart')); std(o)
            C.add('card', 'state', norm(o['now']['card']['state']), exp, 'live card missing'); C.add('chart', 'chart', 'Card unavailable' in o['chart_text'], True, 'live card missing')
        for nm, st_, badge, grp in (('live-status-missing', None, 'Status unavailable', 'intact'), ('live-status-intact', 'intact', 'On track', 'intact'), ('live-status-rose10', 'rose10', 'Rose 10%', 'intact'),
                                    ('live-status-made-up', 'banana', 'Status unavailable', 'intact'), ('live-status-empty-string', '', 'Status unavailable', 'intact')):
            f_ = copy.deepcopy(FEED); o_ = next(x for x in f_['open_signals'] if x['grade'] == 'A+'); o_['edge_status'] = st_
            o = snap(pw, nm, feed=f_, picks=(o_['signal_id'],), tabs=('now',)); std(o); n = o['now']
            got = next((r for r in n['prevIntact'] + n['prevClosed'] if norm(r[0]) == o_['chart'] and 'Day' in r[1]), [None, None, None])
            C.add('previous', f'badge for edge_status={st_!r}', norm(got[2]), badge, 'unknown status read as on track')
            if nm == 'live-status-made-up': C.add('card', 'card status line for an unknown status', 'On track' in ' '.join(n['card']['smalls']), False, 'unknown status read as on track')
        for nm, mut in (('live-day-75', dict(days_elapsed=75)), ('live-day-negative', dict(days_elapsed=-3)), ('live-best-null', dict(best_so_far_pct=None, worst_so_far_pct=None)), ('live-entry-close-null', dict(entry_close=None))):
            f_ = copy.deepcopy(FEED); o_ = next(x for x in f_['open_signals'] if x['grade'] == 'A+'); o_.update(mut)
            o = snap(pw, nm, feed=f_, picks=(o_['signal_id'],), tabs=('now', 'chart')); std(o); n = o['now']
            if nm == 'live-best-null': C.add('card', 'best / worst with no closed bar', 'best so far n/a · worst n/a' in norm(n['card']['smalls'][0]), True, 'n/a best worst')
            if nm == 'live-day-75': C.add('card', 'a day count past 60 is shown as fed ("day 75 of 60")', 'day 75 of 60' in norm(n['card']['smalls'][0]), True, 'impossible day count shown')
        # ---------- C18 regime strings
        for nm, v, exp in (('regime-made-up', 'Sideways', 'Market filter: unavailable'), ('regime-null', None, 'Market filter: unavailable'), ('regime-empty', '', 'Market filter: unavailable'), ('regime-bearish', 'Bearish', 'Market filter: off'), ('regime-lowercase-bullish', 'bullish', 'Market filter: on')):
            f_ = copy.deepcopy(FEED); f_['market_regime'] = v
            o = snap(pw, nm, feed=f_, tabs=('now',)); std(o); C.add('header', f'filter pill for market_regime={v!r}', norm(o['now']['filter']), exp, 'unknown regime read as off')
        # ---------- C19 structural damage to the feed
        for nm, mut in (('feed-no-generated_at', lambda f_: f_.pop('generated_at')), ('feed-generated_at-null', lambda f_: f_.update(generated_at=None)), ('feed-generated_at-garbage', lambda f_: f_.update(generated_at='yesterday')),
                        ('feed-no-checks', lambda f_: f_.pop('checks')), ('feed-cards-null', lambda f_: f_.update(cards=None)), ('feed-open_signals-null', lambda f_: f_.update(open_signals=None)),
                        ('feed-grade_odds-missing', lambda f_: f_.pop('grade_odds')), ('feed-is-a-list', None), ('feed-is-null', None), ('feed-scored_as_of-missing', lambda f_: f_.pop('scored_as_of')),
                        ('feed-odds_fade-missing', lambda f_: f_.pop('odds_fade')), ('feed-past_paths-days-short', lambda f_: [p_.update(days=p_['days'][:20]) for p_ in f_['past_paths']]),
                        ('feed-past_paths-null-values', lambda f_: [d_.update(median_pct=None) for p_ in f_['past_paths'] for d_ in p_['days'][:5]])):
            if mut is None: fb = '[]' if 'list' in nm else 'null'
            else: f_ = copy.deepcopy(FEED); mut(f_); fb = f_
            o = snap(pw, nm, feed=fb); std(o); n = o['now']
            state = norm(n['card']['state'])
            C.add('card', 'renders a card or an explicit unavailable state (never blank)', state != '', True, 'blank page on a damaged feed')
            if nm in ('feed-is-null',): C.add('card', 'state', state, 'Data unavailable', 'null feed')
        # ---------- C14 live lead-trader feed
        tr = {"mode": "live", "trades": [
            {"asset": "ETH", "direction": "long", "action": "open", "time": "2026-11-11T14:03:22Z", "price": 2051.337, "leverage": 3.3, "size_pct": 37.5},
            {"asset": "BTC", "direction": "long", "action": "close", "time": "2026-11-09T09:00:00Z", "price": 81234.5, "leverage": 4, "size_pct": 35.049, "move_pct": -4.25, "account_pct": -5.949},
            {"asset": "BTC", "direction": "long", "action": "open", "time": "2026-10-20T01:00:00Z", "price": 83000, "leverage": 4, "size_pct": 35}]}
        o = snap(pw, 'lead-trader-live', trades=json.dumps(tr), picks=(livesid,), tabs=('now', 'chart')); std(o); n = o['now']; ld = norm(n['lead'])
        for frag, why in (('ETH long · open', 'trade 1'), ('11 Nov 2026', 'trade 1 date'), ('Price $2,051.34', 'trade 1 price to the cent'), ('3.3x', 'leverage'), ('37.5% of acct', 'size as share'), ('BTC long · close', 'trade 2'),
                          ('Price $81,234.50', 'trade 2 price'), ('4.0x', 'leverage 4'), ('35.0% of acct', 'size 35.049 -> 35.0'), ('Move −4.3%', 'move -4.25 -> -4.3 (half away from zero)'), ('Account −5.9%', 'account -5.949 -> -5.9')):
            C.add('lead trader', why, frag in ld, True, f'lead trader figure: expected "{frag}" in "{ld[:160]}"')
        C.add('lead trader', 'card marker for a BTC card (latest BTC trade is a close)', norm(n['card']['marker']), 'Lead trader: out', 'lead marker')
        C.add('lead trader', 'chart note says trades are on the Now tab, not drawn', 'listed on the Now tab; they are not drawn on this chart' in o['chart_text'], True, 'lead chart note')
        C.add('lead trader', 'no dollar amount other than the fill price', len(re.findall(r'\$[\d,]+', ld)), 3, 'dollar amounts')
        ethsid = next((c_['signal_id'] for c_ in FEED['cards'] if c_['asset'] == 'ETH'), None)
        if ethsid:
            o = snap(pw, 'lead-trader-live-eth-card', trades=json.dumps(tr), picks=(ethsid,), tabs=('now',)); std(o)
            C.add('lead trader', 'card marker for an ETH card (latest ETH trade is an open long)', norm(o['now']['card']['marker']), 'Lead trader: in · long', 'lead marker')
        o = snap(pw, 'lead-trader-no-trades', trades=json.dumps({"mode": "live", "trades": []}), tabs=('now',)); std(o)
        C.add('lead trader', 'empty list', 'No trades posted yet' in norm(o['now']['lead']), True, 'lead none'); C.add('lead trader', 'card marker', norm(o['now']['card']['marker']), 'Lead trader: not in', 'lead marker')
        o = snap(pw, 'lead-trader-only-other-asset', trades=json.dumps({"trades": [tr['trades'][0]]}), picks=(livesid,), tabs=('now',)); std(o)
        C.add('lead trader', 'he has trades, none on this asset', norm(o['now']['card']['marker']), 'Lead trader: not in', 'lead marker')
        for nm, tb in (('lead-trader-garbage', 'not json'), ('lead-trader-trades-not-a-list', json.dumps({"trades": {"a": 1}})), ('lead-trader-null-fields', json.dumps({"trades": [{"asset": "BTC", "direction": None, "action": None, "time": None, "price": None}]})),
                       ('lead-trader-dollar-fields', json.dumps({"trades": [{"asset": "BTC", "direction": "long", "action": "open", "time": "2026-11-11T00:00:00Z", "price": 80000, "size_usd": 123456, "contracts": 1800}]}))):
            o = snap(pw, nm, trades=tb, picks=(livesid,), tabs=('now',)); std(o); ld = norm(o['now']['lead'])
            if nm == 'lead-trader-garbage': C.add('lead trader', 'unreadable feed', 'feed is unavailable right now' in ld, True, 'lead garbage')
            if nm == 'lead-trader-dollar-fields': C.add('lead trader', 'dollar size and contract count never shown', '123' in ld or '1,800' in ld or '1800' in ld, False, 'dollar amount / contracts shown')
    return C


if __name__ == '__main__':
    C = run(); bad = C.bad()
    print('synthetic page states:', len({r[0] for r in C.rows}), 'comparisons', C.n(), 'disagreements', len(bad))
    for r in bad: print('  ', r)
    os.makedirs(OUT, exist_ok=True)
    with gzip.open(os.path.join(OUT, 'checks_synthetic_page.csv.gz'), 'wt', newline='') as f: csv.writer(f).writerows(C.rows)
