"""Audit 21 -- group C, page level: deliberately broken or synthetic feeds/files served to the page.
Each state states what the docs say the page must show; the page is compared with that."""
import copy, csv, datetime as dt, gzip, io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import datacheck as D, pagecheck as P, pagerun as PR
from pagecheck import nt, pct, pc, money, date_long
from playwright.sync_api import sync_playwright

ROOT = os.path.join(HERE, '..', 'a21', 'replay_0414')
FEED = json.load(open(os.path.join(ROOT, 'feed/ctzb_feed.json')))
LEDGER = open(os.path.join(ROOT, 'datasets/ledger.csv')).read()
EX = json.load(open(os.path.join(ROOT, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
GEN = dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc)
iso = lambda t: t.strftime('%Y-%m-%dT%H:%M:%SZ')
J = lambda o: json.dumps(o).encode()
PCT_FIG = re.compile(r'\d+(\.\d+)?%')


def load(pw, feed='file', clock=None, **kw):
    if isinstance(feed, (dict, list)): feed = J(feed)
    s = P.Site(pw, ROOT, clock or iso(GEN + dt.timedelta(minutes=6)), feed=feed, **kw)
    s.goto('now'); return s


def main():
    ck = D.Checks('synthetic')
    def st(name): ck.state = 'C ' + name
    with sync_playwright() as pw:
        # ---------- C1/C2: feed down or not a feed
        for name, body in (('feed down (404)', None), ('feed not JSON', b'{'), ('feed is a list', b'[]'), ('feed is null', b'null'), ('feed is a number', b'7'), ('feed is a string', b'"x"'),
                           ('feed without generated_at', J({k: v for k, v in FEED.items() if k != 'generated_at'})), ('feed generated_at malformed', J(dict(FEED, generated_at='yesterday'))),
                           ('feed generated_at a number', J(dict(FEED, generated_at=1794456840))), ('feed empty object', b'{}'), ('feed empty file', b'')):
            st(name); s = load(pw, feed=body); g = s.now()
            ck.add('page', 'card state', g['card']['state'], 'Data unavailable', 'a feed that cannot be read must say Data unavailable')
            ck.add('page', 'header', g['filter'], 'Feed unavailable'); ck.add('page', 'no card figure shown', bool(PCT_FIG.search(g['card']['text'])), False)
            ck.add('page', 'picker', json.dumps([r['none'] for r in g['picker']]), json.dumps(['Feed unavailable.', 'Feed unavailable.']))
            ck.add('page', 'previous signals', g['prevIntactNone'], "Unavailable: the feed can't be read right now.")
            ck.add('page', 'example does not stand in for an outage', g['preview'], False); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]', 'javascript error')
            ck.add('page', 'no raw placeholder', bool(PR.BAD.search(g['body'])), False, str(PR.BAD.search(g['body'])))
            s.pg.click('#tab-chart'); gc = s.chart()
            ck.add('page', 'chart tab under an outage shows no setup figures', bool(PCT_FIG.search(' '.join(t['s'] for t in gc['texts']))) or bool(PCT_FIG.search(' '.join(b['text'] for b in gc['side']))), False, 'chart tab shows figures although the feed is down')
            ck.add('page', 'no page error (chart)', json.dumps(s.errs[:1]), '[]', 'javascript error')
            s.close()
        # ---------- C3: held
        held = copy.deepcopy(FEED); held['cards_withheld'] = True; held['checks']['all_passed'] = False
        for name, f in (('held, cards still in the feed', held), ('held, cards_withheld the string "true"', dict(held, cards_withheld='true')), ('held, cards_withheld 1', dict(held, cards_withheld=1))):
            st(name); s = load(pw, feed=f); g = s.now()
            ck.add('page', 'card state', g['card']['state'], 'Setups held back', 'cards ignored when cards_withheld is true')
            ck.add('page', 'picker', json.dumps([r['none'] for r in g['picker']]), json.dumps(['Held back: a data check failed on the latest run.'] * 2))
            ck.add('page', 'no live or forming button', sum(1 for r in g['picker'] for b in r['btns'] if b['sel'] != 'example'), 0)
            ck.add('page', 'previous signals', g['prevIntactNone'], 'Held back: a data check failed on the latest run.'); ck.add('page', 'no open signal listed', sum(1 for m in g['prevClosed'] if 'Day' in (m['sub'] or '')), 0)
            ck.add('page', 'footer', 'checks FAILED, cards held back' in g['feedState'], True); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]')
            s.close()
        st('held flag true but checks.all_passed true (hand-edited)'); s = load(pw, feed=dict(FEED, cards_withheld=True)); g = s.now()
        ck.add('page', 'card state', g['card']['state'], 'Setups held back'); ck.add('page', 'footer does not say checks passed while setups are held back', 'checks passed' in g['feedState'], False, 'footer reads checks.all_passed, the card reads cards_withheld'); s.close()
        # ---------- C4: fail-closed feed, as feed_live.fail_closed writes it
        fc = {"schema_version": 6, "generated_at": iso(GEN), "posting_bar_pct": 70, "scored_as_of": None, "label": FEED['label'], "checks": {"passed": False, "all_passed": False, "lines": [], "steps": {}, "failed_steps": ["feed"]},
              "feed_error": "KeyError", "cards_withheld": True, "alerts_withheld": True, "extras_withheld": True, "alerts": [], "cards": [], "prints": [], "open_signals": [], "confluence_windows": [], "grade_odds": [], "if_it_misses": [],
              "past_paths": [], "candle_check": None, "example_card": None, "example_past_paths": None, "example_if_it_misses": None, "odds_fade": {"label": FEED['label'], "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}}
        st('fail-closed feed'); s = load(pw, feed=fc); g = s.now()
        ck.add('page', 'card state', g['card']['state'], 'Setups held back'); ck.add('page', 'header', g['filter'], 'Market filter: unavailable', 'unknown regime must not read as off')
        ck.add('page', 'banner scored date', g['rv'].startswith('unavailable'), True); ck.add('page', 'example does not stand in', g['preview'], False)
        s.pg.click('[data-sel="example"]'); s.pg.wait_for_timeout(150); ck.add('page', 'example', s.now()['card']['state'], 'Example unavailable')
        s.pg.click('#tab-record'); s.pg.wait_for_timeout(150); gr = s.pg.evaluate(P.EXTRACT_REC)
        ck.add('page', 'past signals still listed from the ledger', len(gr['rows']) > 0, True); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        # ---------- C5: stale
        for mins, want in ((6, None), (295, None), (301, 5), (29 * 60 + 30, 29), (10 * 24 * 60, 240)):
            st(f'feed {mins} minutes old'); s = load(pw, clock=iso(GEN + dt.timedelta(minutes=mins))); g = s.now()
            exp = None if want is None else f'This data is {want} hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.'
            ck.add('page', 'stale warning', g['card']['stale'], exp, 'warn when the feed is over 5 hours old'); s.close()
        quiet = copy.deepcopy(FEED); quiet['cards'] = []; quiet['open_signals'] = []
        st('stale and quiet'); s = load(pw, feed=quiet, clock=iso(GEN + dt.timedelta(hours=7))); g = s.now()
        ck.add('page', 'example does not stand in for a stale feed', g['preview'], False); ck.add('page', 'stale warning on the quiet card', (g['card']['stale'] or '').startswith('This data is 7 hours old'), True)
        ck.add('page', 'card state', g['card']['state'], 'No setup right now'); s.close()
        st('quiet, filter on'); s = load(pw, feed=quiet); g = s.now(); ck.add('page', 'opens on the example', g['preview'], True)
        s.pg.click('#previewSwitch'); s.pg.wait_for_timeout(150); g = s.now()
        ap = [r for r in csv.DictReader(io.StringIO(LEDGER)) if r['grade'] == 'A+' and 2020 <= int(r['entry'][:4]) <= 2025]
        exp = f"The market filter is on. Nothing at the top grade is forming or confirmed today. Top-grade setups come about {int(len(ap) / 6 + 0.5)} times a year (2020 to 2025 average; bear years, when the market filter is off, are included)."
        ck.add('page', 'quiet text and per-year count', exp in nt(g['card']['empty']), True, f'expected "{exp}"; shown "{nt(g["card"]["empty"])}"'); s.close()
        st('quiet, filter off'); s = load(pw, feed=dict(quiet, market_regime='Bearish')); s.pg.click('#previewSwitch'); s.pg.wait_for_timeout(150); g = s.now()
        ck.add('page', 'quiet text', 'The market filter is off, so the system is quiet.' in g['card']['empty'], True); ck.add('page', 'header', g['filter'], 'Market filter: off'); s.close()
        # ---------- C6: ledger
        lines = LEDGER.splitlines(keepends=True); hdr = lines[0].strip().split(',')
        ap_i = [i for i, l in enumerate(lines) if i and l.split(',')[hdr.index('grade')] == 'A+']
        cut = ''.join(lines[:-50]); midrow = ''.join(lines[:ap_i[-1]]) + lines[ap_i[-1]][:40]; tailrow = ''.join(lines[:-1]) + lines[-1][:40]
        swap = lines[:]; swap[ap_i[5]] = swap[ap_i[6]]
        edited = lines[:]; c = edited[ap_i[-1]].split(','); c[hdr.index('bestMove')] = '99.999999'; edited[ap_i[-1]] = ','.join(c)
        noentry = lines[:]; c = noentry[ap_i[-1]].split(','); c[hdr.index('entry')] = ''; noentry[ap_i[-1]] = ','.join(c)
        for name, led, ok in (('ledger missing', None, False), ('ledger empty', b'', False), ('ledger header only', lines[0].encode(), False), ('ledger cut short (50 rows)', cut.encode(), False),
                              ('ledger cut in the middle of a top-grade row', midrow.encode(), False), ('ledger: last row (not top grade) cut mid-row, every top-grade row intact', tailrow.encode(), True), ('ledger: one top-grade row with no entry date', ''.join(noentry).encode(), False),
                              ('ledger: a top-grade row replaced by a copy of another (same count)', ''.join(swap).encode(), True), ('ledger: a best-move value hand-edited', ''.join(edited).encode(), True)):
            st(name); s = load(pw, ledger=led); g = s.now()
            s.pg.click('#tab-record'); s.pg.wait_for_timeout(150); gr = s.pg.evaluate(P.EXTRACT_REC)
            if not ok:
                ck.add('page', 'past signals read as unavailable', gr['count'], 'Past signals unavailable right now', 'a broken ledger must read as unavailable'); ck.add('page', 'no rows', len(gr['rows']), 0)
                ck.add('page', 'previous-signals column says unavailable', g['prevClosedNone'], 'Past signals unavailable right now.')
            else:
                ck.add('page', 'accepted by the count rule (documented limit: only the count per asset is checked)', gr['count'] != 'Past signals unavailable right now', True)
            ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        # ---------- C7: chart files
        bars = None
        def cj(k, fn):
            a, tf = k.split()
            b = [dict(t=float(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(os.path.join(ROOT, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')))]
            return J({'chart': k, 'bars': fn(b)})
        def strbar(b): b = copy.deepcopy(b); b[10]['h'] = 'abc'; return b
        def nullbar(b): b = copy.deepcopy(b); b[10]['l'] = None; return b
        for name, key, sel, body, title_has, msg in (
                ('chart file missing (forming)', 'BTC 1D', 'BTC-1D-2026-11-13', b'x', None, 'Chart data unavailable for BTC 1D'),
                ('chart file 9 bars', 'BTC 1D', 'BTC-1D-2026-11-13', cj('BTC 1D', lambda b: b[-9:]), None, 'Chart data unavailable for BTC 1D'),
                ('chart file with a text price', 'BTC 1D', 'BTC-1D-2026-11-13', cj('BTC 1D', strbar), None, 'Chart data unavailable for BTC 1D'),
                ('chart file with a null price', 'BTC 1D', 'BTC-1D-2026-11-13', cj('BTC 1D', nullbar), None, 'Chart data unavailable for BTC 1D'),
                ('chart file bars not a list', 'BTC 1D', 'BTC-1D-2026-11-13', J({'chart': 'BTC 1D', 'bars': {}}), None, 'Chart data unavailable for BTC 1D'),
                ('chart file does not reach the entry (live)', 'BTC 2D', 'BTC-2D-2026-09-21', cj('BTC 2D', lambda b: b[-12:]), None, "This chart's data doesn't reach back to the entry")):
            st(name); s = load(pw, candles={key: body if body != b'x' else None}); s.pg.click(f'[data-sel="{sel}"]'); s.pg.click('#tab-chart'); gc = s.chart()
            ck.add('page', 'chart message', json.dumps([t['s'] for t in gc['texts']]), json.dumps([msg]), 'a broken chart file must read as unavailable')
            ck.add('page', 'nothing left from another setup', (gc['side'], gc['cloudSub'], gc['cloudNote']), ([], '', '')); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        st('chart file whose last bar is older than the feed'); s = load(pw, candles={'BTC 1D': cj('BTC 1D', lambda b: b[:-2])}); s.pg.click('[data-sel="BTC-1D-2026-11-13"]'); s.pg.click('#tab-chart'); gc = s.chart()
        ck.add('page', 'last bar labelled by its date, not Today', any(nt(t['s']) == 'Latest bar · 10 Nov 2026' for t in gc['texts']) and not any(t['s'] == 'Today' for t in gc['texts']), True, 'a stale chart file must not call its last bar Today'); s.close()
        # ---------- C8: example file
        for name, body in (('example file missing', None), ('example file cut short (no day 60)', J(dict(EX, bars=EX['bars'][:40]))), ('example file entry_index a string', J(dict(EX, entry_index='20'))),
                           ('example file a bar with text', J(dict(EX, bars=EX['bars'][:5] + [dict(EX['bars'][5], h='x')] + EX['bars'][6:]))), ('example file not JSON', b'{{')):
            st(name); s = load(pw, example=body); s.pg.click('[data-sel="example"]'); s.pg.click('#tab-chart'); gc = s.chart()
            ck.add('page', 'chart message', json.dumps([t['s'] for t in gc['texts']]), json.dumps(['Chart data unavailable']), 'a broken example file must read as unavailable')
            s.pg.click('#tab-now'); g = s.now(); ck.add('page', 'the example card itself still shows (it comes from the feed)', g['card']['state'], 'Confirmed setup'); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        # ---------- C9: hand-edited feeds
        def ed(fn):
            f = copy.deepcopy(FEED); fn(f); return f
        top = next(i for i, o in enumerate(FEED['open_signals']) if o['grade'] == 'A+'); sel_open = FEED['open_signals'][top]['signal_id']
        bi = next(i for i, c in enumerate(FEED['cards']) if c['chart'] == 'BTC 1D'); sel_f = FEED['cards'][bi]['signal_id']
        def card_of(f, sel):
            s = load(pw, feed=f); s.pg.click(f'[data-sel="{sel}"]'); s.pg.wait_for_timeout(200); g = s.now(); return s, g
        st('must_close_above not a number'); s, g = card_of(ed(lambda f: f['cards'][bi].update(must_close_above='abc')), sel_f)
        ck.add('page', 'price prints n/a', 'if it closes above n/a' in g['card']['headSmall'][0], True, f"shown: {g['card']['headSmall'][0]}"); s.close()
        st('price_now not a number'); s, g = card_of(ed(lambda f: f['cards'][bi].update(price_now='abc')), sel_f); s.pg.click('#tab-chart'); gc = s.chart()
        ck.add('page', 'chart: no NaN and no figure built from a non-number', bool(re.search(r'NaN|\$n/a|undefined', gc['sub'] + ' '.join(t['s'] for t in gc['texts']) + ' '.join(b['text'] for b in gc['side']))), False, f"sub: {gc['sub'][:120]}")
        ck.add('page', 'chart: price in the subtitle prints n/a', "today's price (n/a)" in gc['sub'], True, gc['sub'][:160]); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        st('entry_close of a live signal not a number'); s, g = card_of(ed(lambda f: f['open_signals'][top].update(entry_close='abc')), sel_open)
        ck.add('page', 'price prints n/a', 'entry close n/a' in g['card']['headSmall'][0], True, g['card']['headSmall'][0][:120]); s.pg.click('#tab-chart'); gc = s.chart()
        ck.add('page', 'chart: no NaN', bool(re.search(r'NaN|undefined', gc['sub'] + ' '.join(t['s'] for t in gc['texts']) + ' '.join(b['text'] for b in gc['side']))), False, (gc['sub'] + ' | ' + ' '.join(t['s'] for t in gc['texts']))[:300]); s.close()
        for val in ('banana', None, '', 'LOST', 5):
            st(f'edge_status {val!r}'); s, g = card_of(ed(lambda f: f['open_signals'][top].update(edge_status=val)), sel_open)
            ck.add('page', 'card status', g['card']['headSmall'][1].startswith('Status unavailable.'), True, g['card']['headSmall'][1][:80])
            lst = g['prevIntact'] + g['prevClosed']; b = next((m['badge'] for m in lst if m['name'] == 'BTC 2D' and 'Day' in m['sub']), None)
            ck.add('page', 'previous-signals badge', b, 'Status unavailable');
            ck.add('page', 'a setup with unknown status is not listed under "Edge intact"', any(m['name'] == 'BTC 2D' for m in g['prevIntact']), False, 'listed under the heading Edge intact with the badge Status unavailable'); s.close()
        for val in ('Sideways', None, '', 'bull', 7, 'Bullish market', ' Bearish '):
            st(f'market_regime {val!r}'); s = load(pw, feed=dict(FEED, market_regime=val)); g = s.now()
            want = 'Market filter: off' if val == ' Bearish ' else 'Market filter: unavailable'
            ck.add('page', 'header', g['filter'], want, 'a regime other than Bullish / Bearish reads unavailable'); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        st('quiet with an unknown regime'); s = load(pw, feed=dict(quiet, market_regime='Sideways')); s.pg.click('#previewSwitch'); s.pg.wait_for_timeout(150); g = s.now()
        ck.add('page', 'quiet card does not say the filter is off when the regime is unknown', 'The market filter is off' in (g['card']['empty'] or ''), False, f"header: {g['filter']}; card: {nt(g['card']['empty'])[:120]}"); s.close()
        st('odds_fade with one empty list'); s, g = card_of(ed(lambda f: f['odds_fade'].update(day10=[])), sel_f)
        ck.add('page', 'card still uses its own ladder and the top-level bar', g['card']['lbls'][0], 'Where the odds fade · this setup'); ck.add('page', 'bar', g['howBar'], '70% bar'); s.close()
        st('no posting bar anywhere'); s, g = card_of(ed(lambda f: (f.pop('posting_bar_pct'), f.update(odds_fade=None))), sel_f)
        ck.add('page', 'edge reads n/a without a bar', g['card']['stats'][2][1], 'n/a', 'no typed fallback for the 70% bar'); ck.add('page', 'how-to does not type a bar', g['howBar'], 'posting bar'); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        st('forming card with no past signals'); s, g = card_of(ed(lambda f: f['cards'][bi].update(past_trades=0, past_signals=0)), sel_f)
        ck.add('page', 'card state', g['card']['state'], 'No odds yet'); ck.add('page', 'no figure', bool(PCT_FIG.search(g['card']['text'])), False); s.close()
        st('live signal with no card'); s, g = card_of(ed(lambda f: f['open_signals'][top].update(card=None)), sel_open)
        ck.add('page', 'card state', g['card']['state'], 'Card unavailable'); ck.add('page', 'no figure', bool(PCT_FIG.search(g['card']['text'])), False); s.close()
        st('card shares null'); s, g = card_of(ed(lambda f: f['cards'][bi].update(rose10_within60d_pct=None, rose10_never_fell25_within60d_pct=None, rose20_within60d_pct=None, fell30_within60d_pct=None)), sel_f)
        ck.add('page', 'a share with no value prints n/a, never n/a%', (g['card']['odds'][0], 'n/a%' in g['card']['text']), ('n/a', False)); s.close()
        st('extras withheld'); s, g = card_of(ed(lambda f: f.update(extras_withheld=True, if_it_misses=[], past_paths=[], example_past_paths=None, example_if_it_misses=None, odds_fade={"label": "", "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []})), sel_f)
        ck.add('page', 'misses read n/a', g['card']['stats'][3][1], 'n/a'); ck.add('page', 'the card keeps its own ladder', len(g['card']['ladder']), 5)
        s.pg.click('#tab-chart'); gc = s.chart(); ck.add('page', 'cloud unavailable', 'Past paths unavailable in this feed' in gc['cloudTexts'], True); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        st('made-up asset');
        def doge(f):
            c = copy.deepcopy(f['cards'][bi]); c.update(chart='DOGE 1D', asset='DOGE', signal_id='DOGE-1D-2026-11-13', price_now=0.123456, must_close_above=0.12); f['cards'].append(c)
        s, g = card_of(ed(doge), 'DOGE-1D-2026-11-13')
        ck.add('page', 'misses for an unknown asset read n/a', g['card']['stats'][3][1], 'n/a'); ck.add('page', 'no raw placeholder', bool(PR.BAD.search(g['card']['text'])), False)
        s.pg.click('#tab-chart'); gc = s.chart(); ck.add('page', 'chart for an unknown asset reads unavailable', json.dumps([t['s'] for t in gc['texts']]), json.dumps(['Chart data unavailable for DOGE 1D'])); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        st('made-up prices (negative, huge, zero)')
        for val, lab in ((-5, 'negative'), (1e15, 'huge'), (0, 'zero')):
            s, g = card_of(ed(lambda f: f['cards'][bi].update(price_now=val)), sel_f); s.pg.click('#tab-chart'); gc = s.chart()
            txt = gc['sub'] + ' '.join(t['s'] for t in gc['texts']) + ' '.join(b['text'] for b in gc['side'])
            ck.add('page', f'{lab} price: no NaN / Infinity / page error', (bool(re.search(r'NaN|Infinity|undefined', txt)), json.dumps(s.errs[:1])), (False, '[]'), txt[:200]); s.close()
        st('markup in a feed string'); s, g = card_of(ed(lambda f: f['cards'][bi].update(sample='<img src=x onerror="window.__x=1"><b>all 37</b>', chart='BTC 1D<script>window.__y=1</script>')), sel_f)
        ck.add('page', 'feed text is escaped, never run', s.pg.evaluate('() => [window.__x, window.__y, document.querySelectorAll("#card img, #picker script").length]'), [None, None, 0]); s.close()
        st('cards not a list'); s = load(pw, feed=dict(FEED, cards={'a': 1}, open_signals='x')); g = s.now()
        ck.add('page', 'no setup button and no page error', (sum(1 for r in g['picker'] for b in r['btns'] if b['sel'] != 'example'), json.dumps(s.errs[:1])), (0, '[]')); s.close()
        st('a card missing most fields'); s, g = card_of(ed(lambda f: f['cards'].__setitem__(bi, {k: FEED['cards'][bi][k] for k in ('signal_id', 'chart', 'asset', 'timeframe', 'grade', 'past_trades')})), sel_f)
        ck.add('page', 'no raw placeholder and no page error', (bool(PR.BAD.search(g['card']['text'])), json.dumps(s.errs[:1])), (False, '[]'), (PR.BAD.search(g['card']['text']) or [''])[0] + ' | ' + g['card']['text'][:200])
        s.pg.click('#tab-chart'); gc = s.chart(); txt = gc['sub'] + ' '.join(t['s'] for t in gc['texts']) + ' '.join(b['text'] for b in gc['side'])
        ck.add('page', 'chart: no raw placeholder and no page error', (bool(PR.BAD.search(txt)), json.dumps(s.errs[:1])), (False, '[]'), (PR.BAD.search(txt) or [''])[0] + ' | ' + txt[:240]); s.close()
        st('open signal with empty progress fields'); s, g = card_of(ed(lambda f: f['open_signals'][top].update(days_elapsed=None, best_so_far_pct=None, worst_so_far_pct=None)), sel_open)
        ck.add('page', 'no raw placeholder (day null, best/worst n/a)', bool(re.search(r'null|undefined|NaN', g['card']['text'] + json.dumps(g['picker']))), False, g['card']['headSmall'][0][:140]); s.close()
        st('example_card missing'); s = load(pw, feed=dict(FEED, example_card=None)); s.pg.click('[data-sel="example"]'); s.pg.wait_for_timeout(150); g = s.now()
        ck.add('page', 'card state', g['card']['state'], 'Example unavailable'); s.pg.click('#tab-chart'); gc = s.chart()
        ck.add('page', 'chart message', json.dumps([t['s'] for t in gc['texts']]), json.dumps(['Chart data unavailable'])); s.close()
        st('grade_odds missing'); s = load(pw, feed=dict(FEED, grade_odds=[])); s.pg.click('#tab-record'); s.pg.wait_for_timeout(150); gr = s.pg.evaluate(P.EXTRACT_REC)
        ck.add('page', 'no summary boxes, rows still listed, no error', (len(gr['sum']), len(gr['rows']) > 0, json.dumps(s.errs[:1])), (0, True, '[]')); s.close()
        for name, fn in (('live signal with no chart field', lambda f: f['open_signals'][top].pop('chart')), ('a null entry in cards', lambda f: f['cards'].append(None)),
                         ('a text entry in open_signals', lambda f: f['open_signals'].append('x')), ('a null entry in grade_odds', lambda f: f['grade_odds'].append(None)),
                         ('a null entry in if_it_misses', lambda f: f['if_it_misses'].append(None)), ('checks missing', lambda f: f.pop('checks')),
                         ('odds_fade a string', lambda f: f.update(odds_fade='x')), ('past_paths entry without days', lambda f: f['past_paths'][1].pop('days')),
                         ('example_card a string', lambda f: f.update(example_card='x')), ('card ladder not a list', lambda f: f['cards'][bi].update(if_it_falls_first='x'))):
            st('hand-edited feed: ' + name); s = load(pw, feed=ed(fn)); g = s.now()
            blank = not (g['card']['text'] or '').strip()
            ck.add('page', 'the page still renders (a card, or an unavailable message), no page error', (blank, json.dumps([e[:80] for e in s.errs[:1]])), (False, '[]'),
                   f"card area {'BLANK' if blank else 'shows: ' + (g['card']['state'] or '')}; header: {g['filter']}; errors: {[e[:120] for e in s.errs[:2]]}")
            if not blank and not s.errs:
                for tab in ('#tab-chart', '#tab-record'):
                    s.pg.click(tab); s.pg.wait_for_timeout(300)
                ck.add('page', 'chart and past-signals tabs: no page error', json.dumps([e[:80] for e in s.errs[:1]]), '[]', f"errors: {[e[:160] for e in s.errs[:2]]}")
            s.close()
        # ---------- C10: a live lead-trader feed
        tr = {'trades': [{'asset': 'BTC', 'direction': 'long', 'action': 'open', 'time': '2026-11-11T14:02:00Z', 'price': 75210.5, 'leverage': 3.3, 'size_pct': 37.5},
                         {'asset': 'ETH', 'direction': 'long', 'action': 'close', 'time': '2026-11-09T09:30:00Z', 'price': 2101.129, 'leverage': 3.3, 'size_pct': 35, 'move_pct': -4.25, 'account_pct': -4.9},
                         {'asset': 'ETH', 'direction': 'long', 'action': 'open', 'time': '2026-11-02T10:00:00Z', 'price': 2194.4, 'leverage': 3.3, 'size_pct': 35}] + [{'asset': 'BTC', 'direction': 'long', 'action': 'close', 'time': f'2026-10-{d:02d}T10:00:00Z', 'price': 80000 + d, 'move_pct': 0.04, 'account_pct': -0.04} for d in range(1, 6)]}
        st('live lead-trader feed'); s = load(pw, trades=J(tr)); g = s.now()
        lead = nt(g['lead'])
        lead = lead.replace(' ', '')
        ck.add('page', 'latest trade: asset, action, date, price', 'BTClong·open11Nov2026Price$75,210.503.3x37.5%ofacct' in lead, True, lead[:160])
        ck.add('page', 'closed trade: move and account, signed and rounded', 'Price$2,101.133.3x35.0%ofacctMove−4.3%Account−4.9%' in lead, True, lead[160:330])
        ck.add('page', 'a move that rounds to zero shows no sign', 'Move0.0%Account0.0%' in lead, True, lead[-120:]); ck.add('page', 'at most 6 trades listed', lead.count('Price$'), 6)
        s.pg.click('[data-sel="BTC-1D-2026-11-13"]'); s.pg.wait_for_timeout(150); ck.add('page', 'card marker BTC (latest is an open)', s.now()['card']['marker'], 'Lead trader: in · long')
        s.pg.click('[data-sel="ETH-1D-2026-11-13"]'); s.pg.wait_for_timeout(150); ck.add('page', 'card marker ETH (latest is a close)', s.now()['card']['marker'], 'Lead trader: out')
        s.pg.click('#tab-chart'); gc = s.chart(); ck.add('page', 'chart note: trades listed on the Now tab, not drawn', any('they are not drawn on this chart' in b['text'] for b in gc['side']), True)
        ck.add('page', 'no dollar position size or contract count shown', bool(re.search(r'contracts?|\bqty\b|notional', lead, re.I)), False); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        for name, t, mk in (('lead feed: no trades yet', {'trades': []}, 'not in'), ('lead feed: only another asset', {'trades': [tr['trades'][1]]}, 'not in'), ('lead feed: a row with no action', {'trades': [{'asset': 'BTC', 'direction': 'long'}]}, 'unavailable'),
                            ('lead feed: a list, not an object', [], 'unavailable'), ('lead feed: not JSON', None, 'unavailable')):
            st(name); s = load(pw, trades=J(t) if t is not None else b'{'); s.pg.click('[data-sel="BTC-1D-2026-11-13"]'); s.pg.wait_for_timeout(150); g = s.now()
            ck.add('page', 'card marker', g['card']['marker'], 'Lead trader: ' + mk); ck.add('page', 'no raw placeholder in the lead panel', bool(PR.BAD.search(g['lead'])), False, g['lead'][:160]); ck.add('page', 'no page error', json.dumps(s.errs[:1]), '[]'); s.close()
        st('lead feed: non-numeric leverage and size'); s = load(pw, trades=J({'trades': [{'asset': 'BTC', 'direction': 'long', 'action': 'open', 'time': '2026-11-11T14:02:00Z', 'price': 'n', 'leverage': 'abc', 'size_pct': 'x', 'move_pct': 'y', 'account_pct': None}]})); g = s.now()
        ck.add('page', 'no "n/ax" / "n/a%" in the lead panel', bool(re.search(r'n/ax|n/a%', g['lead'])), False, g['lead'][:200]); s.close()
    with gzip.open(os.path.join(HERE, 'checks_C_page.csv.gz'), 'wt', newline='') as fh: csv.writer(fh).writerows(ck.rows)
    print('C page-level: states', len({r[0] for r in ck.rows}), 'checks', ck.n, 'diffs', len(ck.bad))
    for r in ck.bad: print('  ', r[0], '|', r[2], '|', str(r[3])[:160], '|', str(r[4])[:110], '|', r[6][:200])


if __name__ == '__main__':
    main()
