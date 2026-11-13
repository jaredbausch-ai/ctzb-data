"""Audit 18 synthetic page states (on copies; the frozen states are only read). Each state: a feed / file condition the
frozen states don't show, rendered under Playwright, and compared with what the page should say."""
import copy, csv, datetime as dt, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import core as K, stage_data as SD, page_lib as P, page_expect as PE, run_page as RP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'a18', 'replay_0414'); TODAY = dt.date(2026, 11, 12)
BAD = RP.BAD
Cb, ctx = SD.run('base', ROOT, TODAY)
FEED = ctx['feed']
C = K.Checks('synthetic')
EXJ = json.load(open(os.path.join(ROOT, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
LEDGER = open(os.path.join(ROOT, 'datasets/ledger.csv')).read()
A_ROWS = sorted([r for r in ctx['L'] if r['grade'] == 'A+'], key=lambda r: tuple(-ord(ch) for ch in r['entry']))
notes = []


def clock(feed, **kw):
    return (dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%SZ')


def ctx_with(my):
    c2 = dict(ctx); c2['MY'] = my; return c2


def add(loc, label, shown, mine, cause=''):
    return C.add(loc, label, shown, mine, ok=(shown == mine), cause=cause)


def clean(loc, d, s):
    add(loc, 'no raw placeholder (undefined / NaN / null / ${)', len(BAD.findall(d['body'])), 0, cause=str(BAD.findall(d['body'])[:3]))
    add(loc, 'no script error', len(s.errs), 0, cause='; '.join(s.errs[:2]))


with sync_playwright() as pw:
    # ---------------------------------------------------------------- 1. feed down
    loc = 'synthetic: feed down (503)'
    s = P.Site(pw, ROOT, feed=None, clock='2026-11-12T04:20:00Z'); s.open('now'); d = s.dump()
    add(loc, 'header', d['filter'], 'Feed unavailable')
    add(loc, 'banner', d['review'].split('. Alerts')[0], 'Review build. Real pipeline data, scored unavailable')
    add(loc, 'footer feed state', d['footer'], '')
    add(loc, 'card state', d['card']['state'], 'Data unavailable')
    add(loc, 'card text', d['card']['empty'], "Can't reach the data right now This is an outage, not a quiet market. Setups may be forming that this page can't show. It recovers on its own once the data source is back.")
    add(loc, 'picker Live', d['picker'][0]['none'], 'Feed unavailable.'); add(loc, 'picker Forming', d['picker'][1]['none'], 'Feed unavailable.')
    add(loc, 'Edge intact panel', [x['text'] for x in d['prevIntact']], ["Unavailable: the feed can't be read right now."])
    add(loc, 'past rows still listed from the ledger', len(d['prevClosed']), 5)
    add(loc, 'example not shown in place of an outage', d['preview'], False)
    add(loc, 'How to read: no bar figure typed in', d['howBar'], 'posting bar')
    s.show('chart'); d = s.dump()
    add(loc, 'chart', [t['text'] for t in d['chart']['svg'] if t['tag'] == 'text'], ['Chart data unavailable'])
    add(loc, 'chart side / cloud empty', [len(d['chart']['side']), len(d['chart']['cloud'])], [0, 0])
    s.show('record'); d = s.dump()
    add(loc, 'past signals count from the ledger', d['record']['count'], f"{len(A_ROWS)} signals · {sum(1 for r in A_ROWS if not r['_s']['m']['r10'])} missed +10%")
    add(loc, 'no summary boxes without the feed', len(d['record']['sum']), 0)
    clean(loc, d, s); s.close()

    # ---------------------------------------------------------------- 2. held back: a real failed run (no today's bar)
    loc = 'synthetic: held back (real run, clock 12 Nov 00:05, candles end 11 Nov)'
    held = os.path.join(HERE, 'rep', 'held')
    if not os.path.exists(os.path.join(held, 'feed', 'ctzb_feed.json')):
        subprocess.run(['bash', os.path.join(HERE, 'rep', 'src', 'tests', 'replay_at.sh'), '2026-11-11', held, '2026-11-12T00:05:00Z', '--keep-going'], capture_output=True, text=True)
    hf = json.load(open(os.path.join(held, 'feed', 'ctzb_feed.json'))); st = open(os.path.join(held, 'datasets', 'stack_status.txt')).read()
    add(loc, 'envelope: stack_live fails closed', 'FAILED' in st and "today's bar is missing" in st, True)
    add(loc, 'envelope: feed withholds cards, open signals, example', [hf['cards_withheld'], len(hf['cards']), len(hf['open_signals']), hf['example_card']], [True, 0, 0, None])
    s = P.Site(pw, held); s.open('now'); d = s.dump()
    add(loc, 'card state', d['card']['state'], 'Setups held back')
    add(loc, 'card text', d['card']['empty'], "A data check failed on the latest run The system holds every setup and alert back until its checks pass, so nothing unverified is shown. They return on the next clean run, usually within the hour.")
    add(loc, 'picker', [d['picker'][0]['none'], d['picker'][1]['none']], ['Held back: a data check failed on the latest run.'] * 2)
    add(loc, 'Edge intact panel', [x['text'] for x in d['prevIntact']], ['Held back: a data check failed on the latest run.'])
    add(loc, 'footer', d['footer'], 'Daily candles closed through 11 Nov 2026 · updated 00:05 UTC · checks FAILED, cards held back')
    add(loc, 'example not shown in place of a held run', d['preview'], False)
    s.select('example'); d2 = s.dump(); add(loc, 'example card', d2['card']['state'], 'Example unavailable')
    clean(loc, d, s); s.close()

    # ---------------------------------------------------------------- 3. fail-closed feed (feed_live.fail_closed)
    loc = 'synthetic: fail-closed feed'
    fc_dir = os.path.join(HERE, 'rep', 'failclosed'); os.makedirs(fc_dir, exist_ok=True)
    subprocess.run([sys.executable, '-c', "import sys; sys.path.insert(0, sys.argv[1]); import feed_live as F; F.fail_closed(sys.argv[2], KeyError('x'))",
                    os.path.join(HERE, 'rep', 'src'), os.path.join(fc_dir, 'feed.json')], env=dict(os.environ, CTZB_NOW='2026-11-12T04:14:00Z'))
    fc = json.load(open(os.path.join(fc_dir, 'feed.json')))
    s = P.Site(pw, ROOT, feed=fc); s.open('now'); d = s.dump()
    add(loc, 'header', d['filter'], 'Market filter: unavailable')
    add(loc, 'banner', d['review'].split('. Alerts')[0], 'Review build. Real pipeline data, scored unavailable (feed 04:14 UTC)')
    add(loc, 'card state', d['card']['state'], 'Setups held back')
    add(loc, 'footer says checks failed', d['footer'].endswith('checks FAILED, cards held back'), True)
    notes.append(('fail-closed footer', d['footer']))
    s.show('record'); d = s.dump(); add(loc, 'past signals still listed', d['record']['count'], f"{len(A_ROWS)} signals · {sum(1 for r in A_ROWS if not r['_s']['m']['r10'])} missed +10%")
    s.show('chart'); d = s.dump(); add(loc, 'chart', [t['text'] for t in d['chart']['svg'] if t['tag'] == 'text'], ['Chart data unavailable'])
    clean(loc, d, s); s.close()

    # ---------------------------------------------------------------- 4. stale
    for mins, want in ((299, None), (301, 5), (6 * 60 + 59, 6), (29 * 60 + 30, 29)):
        loc = f'synthetic: feed {mins} minutes old'
        s = P.Site(pw, ROOT, clock=clock(FEED, minutes=mins)); s.open('now'); d = s.dump()
        add(loc, 'stale note', d['card']['stale'], None if want is None else f"This data is {want} hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.")
        clean(loc, d, s); s.close()
    loc = 'synthetic: stale and quiet'
    q = copy.deepcopy(FEED); q['cards'] = []; q['open_signals'] = []
    s = P.Site(pw, ROOT, feed=q, clock=clock(q, hours=7)); s.open('now'); d = s.dump()
    add(loc, 'quiet card, not the example', [d['preview'], d['card']['state']], [False, 'No setup right now'])
    add(loc, 'stale note', d['card']['stale'], "This data is 7 hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.")
    clean(loc, d, s); s.close()

    # ---------------------------------------------------------------- 5. no setup, filter on / off
    yA = sum(1 for r in ctx['L'] if r['grade'] == 'A+' and 2020 <= int(r['entry'][:4]) <= 2025)
    for regime, body in (('Bullish', f"The market filter is on. Nothing at the top grade is forming or confirmed today. Top-grade setups come about {K.rnd(K.Fr(yA, 6))} times a year (2020 to 2025 average; bear years, when the market filter is off, are included)."),
                         ('Bearish', "The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.")):
        loc = f'synthetic: no setup, filter {regime}'
        q = copy.deepcopy(FEED); q['cards'] = []; q['open_signals'] = []; q['market_regime'] = regime
        s = P.Site(pw, ROOT, feed=q); s.open('now'); d = s.dump()
        add(loc, 'opens on the example', d['preview'], True)
        add(loc, 'header', d['filter'], 'Market filter: ' + ('on' if regime == 'Bullish' else 'off'))
        s.pg.click('#previewSwitch'); s.pg.wait_for_timeout(300); d = s.dump()
        add(loc, 'quiet card', d['card']['empty'], f"Waiting for the next one {body} You'll get a push alert the moment one confirms.")
        add(loc, 'picker', [d['picker'][0]['none'], d['picker'][1]['none']], ['No live top-grade setups right now.', 'Nothing forming today.'])
        add(loc, 'Edge intact panel', [x['text'] for x in d['prevIntact']], ['No open top-grade setup with its edge intact.'])
        clean(loc, d, s); s.close()

    # ---------------------------------------------------------------- 6. a top-grade forming card; 7. each edge status; 12. no misses
    def variant(loc, mut_feed, mut_my, sel, kind='open', trades=None, views=('now', 'chart')):
        f = copy.deepcopy(FEED); my = copy.deepcopy(ctx['MY'])
        mut_feed(f); mut_my(my)
        c2 = ctx_with(my); Cv = K.Checks('synthetic'); pc = PE.PageCheck(Cv, c2, ROOT, EXJ); M = pc.models()
        s = P.Site(pw, ROOT, feed=f, trades=trades); s.open('now'); d0 = s.dump()
        init = M['best'].x['signal_id'] if M['best'] else (M['opens'][0].x['signal_id'] if M['opens'] else None)
        if trades is None:
            pc.chrome(loc, d0, M, init)
        m = next(x for x in M['opens'] + M['forming'] if x.x['signal_id'] == sel)
        s.select(sel); d = s.dump()
        if trades is None:
            pc.card(loc, d, m, M['best'].x['signal_id'] if M['best'] else None)
            s.show('chart'); s.pg.wait_for_timeout(300); dc = s.dump(); pc.chart(loc + ' chart', dc, m)
            s.show('record'); dr = s.dump(); pc.record(loc + ' record', dr, 'all')
        clean(loc, d, s)
        C.rows += Cv.rows
        return s, d, d0

    def top_feed(f):
        c = next(x for x in f['cards'] if x['signal_id'] == 'ETH-2D-2026-11-16'); c['grade'] = 'A+'
    def top_my(my):
        my['cards']['feed.cards ETH-2D-2026-11-16']['grade'] = 'A+'
    s, d, d0 = variant('synthetic: a top-grade forming card (ETH 2D marked top grade)', top_feed, top_my, 'ETH-2D-2026-11-16', 'forming')
    add('synthetic: a top-grade forming card (ETH 2D marked top grade)', 'page opens on the top-grade forming card', [b['sel'] for r in d0['picker'] for b in r['btns'] if b['pressed'] == 'true'], ['ETH-2D-2026-11-16'])
    s.close()

    SID = 'BTC-2D-2026-09-21'
    for lvl, stt, best, worst in ((-5, 'lost', 0.8, -16.1), (0, 'lost', 0.8, -16.1), (-10, 'rose10', 12.4, -3.2), (None, 'rose10', 10.0, -0.04), (-5, 'intact', 3.1, -4.9),
                                  (None, 'intact', None, None), (-20, 'intact', 0.04, -19.96)):
        loc = f'synthetic: live card, edge level {lvl}, status {stt}, best {best}, worst {worst}'
        def mf(f, lvl=lvl, stt=stt, best=best, worst=worst):
            o = next(x for x in f['open_signals'] if x['signal_id'] == SID)
            o['edge_level_pct'] = lvl; o['edge_status'] = stt; o['best_so_far_pct'] = best; o['worst_so_far_pct'] = worst
            lad = o['card']['if_it_falls_first']; fe = o['card']['from_entry']
            # make the card's own ladder agree with the edge level
            vals = {0: [69.9, 60, 38, 17, 0], -5: [82, 69.999999, 38, 17, 0], -10: [82, 70.0, 69.5, 17, 0], -20: [82, 75, 72, 70, 69.99], None: [82, 75, 72, 71, 70]}[lvl]
            fe['still_rose10_exact_pct'] = vals[0]; fe['still_rose10_pct'] = K.rnd(K.Fr(str(vals[0])))
            for row, v in zip(lad, vals[1:]): row['still_rose10_exact_pct'] = v; row['still_rose10_pct'] = K.rnd(K.Fr(str(v)))
            if best is None: o['day10_pct'] = None; o['days_elapsed'] = 1
        def mm(my, lvl=lvl, stt=stt, best=best, worst=worst):
            o = next(x for x in my['opens'] if x['signal_id'] == SID)
            o['edge_level'] = lvl; o['edge_status'] = stt; o['best'] = best; o['worst'] = worst
            vals = {0: [69.9, 60, 38, 17, 0], -5: [82, 69.999999, 38, 17, 0], -10: [82, 70.0, 69.5, 17, 0], -20: [82, 75, 72, 70, 69.99], None: [82, 75, 72, 71, 70]}[lvl]
            lad = o['card']['ladder']
            o['card']['ladder'] = [(t[0], t[1], K.rnd(K.Fr(str(v))), t[3], v, K.Fr(str(v))) for t, v in zip(lad, vals)]
            o['card']['edge'] = lvl
            if best is None: o['d10'] = None; o['elapsed'] = 1
        s, d, d0 = variant(loc, mf, mm, SID); s.close()

    def nm_feed(f):
        x = next(m for m in f['if_it_misses'] if m['asset'] == 'BTC' and m['grade'] == 'A+')
        x.update(misses=0, up_first=0, median_peak_pct=None, mean_peak_pct=None, peaked_5_or_more=0, median_worst_drop_pct=None, median_day60_pct=None)
    def nm_my(my):
        my['misses'][('BTC', 'A+')].update(misses=0, up_first=0, median_peak_pct=None, mean_peak_pct=None, peaked_5_or_more=0, median_worst_drop_pct=None, median_day60_pct=None)
    s, d, d0 = variant('synthetic: an asset/grade with no misses (BTC top grade)', nm_feed, nm_my, SID); s.close()

    # ---------------------------------------------------------------- 8. extras withheld
    loc = 'synthetic: extras withheld'
    def xw_feed(f):
        f.update(extras_withheld=True, if_it_misses=[], past_paths=[], example_past_paths=None, example_if_it_misses=None)
        f['odds_fade'] = {"label": f['label'], "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}
    def xw_my(my):
        my['misses'] = {}; my['paths'] = {}; my.pop('ex_misses', None)
    s, d, d0 = variant(loc, xw_feed, xw_my, SID)
    s.show('chart'); dc = s.dump()
    add(loc, 'cloud says unavailable', [t['text'] for t in dc['chart']['cloud'] if t['tag'] == 'text'], ['Past paths unavailable in this feed'])
    add(loc, 'cloud heading / note', [dc['chart']['cloudSub'], dc['chart']['cloudNote']], ['', ''])
    s.show('now'); s.select('example'); de = s.dump()
    add(loc, 'example card: If it misses', dict((k[0], k[1]) for k in de['card']['stats']).get('If it misses: went above entry'), 'n/a')
    s.close()

    # ---------------------------------------------------------------- 9. ledger missing / short
    loc = 'synthetic: ledger missing (503)'
    s = P.Site(pw, ROOT, ledger=None); s.open('now'); d = s.dump()
    add(loc, 'previous signals', [x['text'] for x in d['prevClosed'] if 'mini closed' in x['cls'] or x['cls'] == 'none'], ['Past signals unavailable right now.'])
    s.show('record'); d = s.dump(); add(loc, 'past signals tab', [d['record']['count'], len(d['record']['rows'])], ['Past signals unavailable right now', 0])
    clean(loc, d, s); s.close()
    for name, text in (('header only', LEDGER.split('\n')[0] + '\n'), ('cut after 400 lines, mid-row', '\n'.join(LEDGER.split('\n')[:400]) + '\n' + LEDGER.split('\n')[400][:60]), ('empty file', '')):
        loc = f'synthetic: ledger short ({name})'
        s = P.Site(pw, ROOT, ledger=text); s.open('record'); d = s.dump()
        nA = len([r for r in csv.DictReader(text.splitlines()) if r.get('grade') == 'A+' and r.get('dayScaled20') is not None]) if text else 0
        notes.append((loc, d['record']['count'], 'summary boxes say ' + ' / '.join(k['kv'][0][1] for k in d['record']['sum']), 'rows shown', len(d['record']['rows'])))
        add(loc, 'a short ledger does not read as a complete record (count line vs the feed\'s totals)', d['record']['count'].startswith('Past signals unavailable') or d['record']['count'].startswith('137 signals'), True,
            cause='page lists a truncated ledger as the whole record, with no warning')
        clean(loc, d, s); s.close()

    # ---------------------------------------------------------------- 10. chart file missing / short
    loc = 'synthetic: chart files missing (404)'
    s = P.Site(pw, ROOT, candles=None); s.open('now'); s.select(SID); s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump()
    add(loc, 'chart text', [t['text'] for t in d['chart']['svg'] if t['tag'] == 'text'], ['Chart data unavailable for BTC 2D'])
    add(loc, 'title / subtitle for this setup', [d['chart']['title'].upper(), d['chart']['sub']], ['BTC · 2D', "This chart's candles couldn't be loaded."])
    add(loc, 'side box, cloud, toggle cleared', [len(d['chart']['side']), len(d['chart']['cloud']), d['chart']['cloudSub'], d['chart']['cloudNote'], d['chart']['toggleHidden']], [0, 0, '', '', True])
    # after a chart that drew: nothing left over
    s.show('now'); s.select('example'); s.show('chart'); s.pg.wait_for_timeout(300); s.show('now'); s.select(SID); s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump()
    add(loc, 'nothing left from the example charted before', [len(d['chart']['svg']), len(d['chart']['side']), len(d['chart']['cloud'])], [1, 0, 0])
    clean(loc, d, s); s.close()

    def short_candles(n):
        def f(a, tf):
            j = json.loads(P.candles_json(ROOT, a, tf)); j['bars'] = j['bars'][-n:] if n else []; return json.dumps(j)
        return f
    for n in (10, 1, 0):
        loc = f'synthetic: chart file short ({n} bars)'
        s = P.Site(pw, ROOT, candles=short_candles(n)); s.open('now'); s.select('example'); s.show('chart'); s.pg.wait_for_timeout(300)
        s.show('now'); s.select(SID); s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump()
        notes.append((loc, 'live BTC 2D after the example was charted: title', d['chart']['title'], 'side', [x['text'][:70] for x in d['chart']['side']][:1], 'errors', s.errs[:1]))
        add(loc, 'live setup whose entry is not in the file', [t['text'] for t in d['chart']['svg'] if t['tag'] == 'text'], ["This chart's data doesn't reach back to the entry"])
        add(loc, 'side box and cloud cleared', [len(d['chart']['side']), len(d['chart']['cloud'])], [0, 0])
        s.show('now'); s.select('BTC-1D-2026-11-13'); s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump()
        tx = [t['text'] for t in d['chart']['svg'] if t['tag'] == 'text']
        nanattr = sum(1 for e in d['chart']['svg'] for k, v in e.items() if isinstance(v, str) and ('NaN' in v or 'Infinity' in v))
        notes.append((loc, 'forming BTC 1D chart texts', tx[:6], 'elements with NaN/Infinity geometry', nanattr, 'errors', s.errs[:1]))
        add(loc, 'forming setup: chart either draws correctly or says unavailable (no broken geometry)', nanattr, 0, cause='chart drawn with NaN / Infinity coordinates from a short candle file')
        clean(loc, d, s); s.close()

    # ---------------------------------------------------------------- 11. example file missing / short
    loc = 'synthetic: example chart file missing (404)'
    s = P.Site(pw, ROOT, example=None); s.open('now'); s.select('example'); d = s.dump()
    add(loc, 'example card still shown from the feed', d['card']['state'], 'Confirmed setup')
    s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump()
    add(loc, 'chart', [t['text'] for t in d['chart']['svg'] if t['tag'] == 'text'], ['Chart data unavailable'])
    add(loc, 'side box and cloud cleared', [len(d['chart']['side']), len(d['chart']['cloud'])], [0, 0])
    clean(loc, d, s); s.close()
    for keep in (30, 21):
        loc = f'synthetic: example chart file short ({keep} bars; entry is bar 20)'
        ej = copy.deepcopy(EXJ); ej['bars'] = ej['bars'][:keep]
        s = P.Site(pw, ROOT, example=json.dumps(ej)); s.open('now'); s.select('example'); s.show('chart'); s.pg.wait_for_timeout(300)
        d1 = s.dump(); s.pg.click('#bHap'); s.pg.wait_for_timeout(300); d = s.dump()
        side = [x['text'] for x in d['chart']['side']]
        notes.append((loc, 'errors', s.errs[:2], 'side', side[1][:160] if len(side) > 1 else None, 'This one', [t['text'] for t in d['chart']['svg'] if t['tag'] == 'text' and t['text'].startswith('This one')]))
        add(loc, '"What happened" with an incomplete file: no script error', len(s.errs), 0, cause='; '.join(s.errs[:1])[:200])
        add(loc, '"What happened" with an incomplete file: no outcome figures from a partial window', any('What this one did' in x or 'WHAT THIS ONE DID' in x for x in side), False,
            cause='outcome box / markers computed from a file that stops before day 60')
        s.close()

    # ---------------------------------------------------------------- 13. a live lead-trader feed with trades
    loc = 'synthetic: lead-trader feed live'
    TR = {"label": "x", "disclosure": "x", "updated_at": "2026-11-12T04:10:00Z", "trades": [
        {"id": "3:close", "mode": "live", "time": "2026-11-11T15:04:05Z", "asset": "ETH", "instrument": "perp", "direction": "long", "action": "close", "price": 2051.07, "leverage": 3.3, "size_pct": 36, "move_pct": -4.3, "account_pct": -5.1, "held_days": 12},
        {"id": "2:open", "mode": "live", "time": "2026-11-10T09:00:00Z", "asset": "BTC", "instrument": "perp", "direction": "long", "action": "open", "price": 73650.5, "leverage": 3.3, "size_pct": 37.5},
        {"id": "1:open", "mode": "live", "time": "2026-10-30T23:59:59Z", "asset": "ETH", "instrument": "perp", "direction": "long", "action": "open", "price": 2142, "size_pct": 36}]}
    s = P.Site(pw, ROOT, trades=TR); s.open('now'); s.select(SID); d = s.dump()
    lead = d['leadAll']
    exp = ("Latest ETH long · close 11 Nov 2026 Price $2,051.07 3.3x 36.0% of acct Move −4.3% Account −5.1% "
           "BTC long · open 10 Nov 2026 Price $73,650.50 3.3x 37.5% of acct ETH long · open 30 Oct 2026 Price $2,142.00 36.0% of acct")
    add(loc, 'trades listed: price, leverage, size, move, account', d['lead'].upper(), exp.upper())
    add(loc, 'card marker for a BTC setup (latest BTC trade is an open long)', d['card']['marker'], 'Lead trader: in · long')
    s.select('ETH-1D-2026-11-13'); d2 = s.dump(); add(loc, 'card marker for an ETH setup (latest ETH trade is a close)', d2['card']['marker'], 'Lead trader: out')
    s.show('chart'); s.pg.wait_for_timeout(300); d3 = s.dump()
    add(loc, 'chart note', d3['chart']['side'][2]['text'], "The lead trader's real entries and exits are listed on the Now tab; they are not drawn on this chart.")
    add(loc, 'no lead-trader mark drawn on the chart', len([e for e in d3['chart']['svg'] if 'lead' in json.dumps(e)]), 0)
    clean(loc, d, s); s.close()
    TR2 = {"trades": []}
    s = P.Site(pw, ROOT, trades=TR2); s.open('now'); d = s.dump()
    add(loc + ' (no trades yet)', 'panel', d['lead'], "No trades posted yet. The lead trader's real entries and exits appear here the moment they fill.")
    add(loc + ' (no trades yet)', 'card marker', d['card']['marker'], 'Lead trader: not in'); s.close()

    # ---------------------------------------------------------------- 14. half-way and near-zero figures through the page's own rounding
    loc = 'synthetic: rounding edge values on a live card'
    def rf(f):
        o = next(x for x in f['open_signals'] if x['signal_id'] == SID); c = o['card']
        c['typical_biggest_rise_exact_pct'] = 0.04; c['typical_deepest_dip_exact_pct'] = -0.049999; c['typical_dip_before_rise_exact_pct'] = -2.25
        c['typical_biggest_rise_pct'] = 0.0; c['typical_deepest_dip_pct'] = 0.0; c['typical_dip_before_rise_pct'] = -2.3
        o['entry_close'] = 3359.9; c['entry_close'] = 3359.9
    def rm(my):
        o = next(x for x in my['opens'] if x['signal_id'] == SID); c = o['card']
        c['typical_biggest_rise_exact_pct'] = 0.04; c['typical_deepest_dip_exact_pct'] = -0.049999; c['typical_dip_before_rise_exact_pct'] = -2.25
        c['typical_biggest_rise_pct'] = 0.0; c['typical_deepest_dip_pct'] = 0.0; c['typical_dip_before_rise_pct'] = -2.3
        o['entry'] = 3359.9; c['entry'] = 3359.9
    try:
        s, d, d0 = variant(loc, rf, rm, SID); s.close()
    except StopIteration:
        add(loc, 'chart drew', 'entry bar not found', 'drawn')

json.dump(notes, open(os.path.join(HERE, 'synth_notes.json'), 'w'), indent=1, default=str, ensure_ascii=False)
with open(os.path.join(HERE, 'synth_checks.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writerows(C.rows)
n, b = C.summary(); print('synthetic comparisons', n, 'disagreements', b)
for r in C.rows:
    if r[5] != 'ok': print('  ', r[1], '|', r[2], '| shown:', str(r[3])[:200], '| mine:', str(r[4])[:200], '|', r[6][:120])
for x in notes: print('NOTE', x)
