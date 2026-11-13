"""Audit 17: synthetic page states (states neither frozen state shows), rendered from the REPLAY state.
Each row: what the page shows vs what it should show (from my own values where a number is involved).

usage: audit_states.py <REPLAY root> <synth dir with held/ extras_off/ failclosed/> <out csv>
"""
import copy, csv, datetime as dt, json, os, re, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
from core import rnd
import audit_feed as AF
import audit_page as AP
from audit_page import Site, pct, money, date_long, MINUS
from playwright.sync_api import sync_playwright

root, synth, out = sys.argv[1:4]
NOW = dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc)
M, L0 = AF.run(root, NOW, 'REPLAY')
L = C.Log('SYNTH')
V = AP.models(M)
FEED = json.load(open(os.path.join(root, 'feed/ctzb_feed.json')))
BAD = re.compile(r'\$\{|undefined|NaN|null|n/a%|\[object|Infinity|%%')
FOOT = 'Statistics from past signal history. Entry quality only: no exit, not a trade or a track record.'
LIVE = 'BTC-2D-2026-09-21'


def cmp_list(L, loc, label, got, exp, cause='page text'):
    got = got or []
    if len(got) != len(exp):
        L.chk(loc, f'{label}: number of text items', len(got), len(exp), cause)
    for i in range(max(len(got), len(exp))):
        g = got[i] if i < len(got) else None; e = exp[i] if i < len(exp) else None
        L.rows.append([L.state, loc, f'{label} [{i}]', '' if g is None else g, '' if e is None else e, 'ok' if g == e else 'DISAGREE', '' if g == e else cause])


def grab(site, pw, clicks=(), views=('now', 'chart', 'record', 'read')):
    pg = site.open(pw, 'now'); o = {}
    for c in clicks:
        if c.startswith('wait'): pg.wait_for_timeout(300)
        else: pg.click(c); pg.wait_for_timeout(300)
    o['card'] = site.texts('#card'); o['picker'] = site.texts('#picker'); o['prev'] = site.texts('section.prev')
    o['filter'] = site.texts('#filterPill'); o['asof'] = site.texts('#rvAsof'); o['foot'] = site.texts('#feedState')
    o['frame'] = pg.evaluate("() => document.querySelector('#cardFrame').style.getPropertyValue('--c')")
    o['preview'] = pg.is_checked('#previewSwitch')
    o['body_now'] = ' '.join(site.texts('.app'))
    if 'chart' in views:
        pg.click('#tab-chart'); pg.wait_for_timeout(500)
        o['chTitle'] = site.texts('#chTitle'); o['chSub'] = site.texts('#chSub'); o['side'] = site.texts('#chartSide')
        o['svgtext'] = [e['text'] for e in site.svg('#chartSvg') if e['tag'] == 'text']
        o['cloudtext'] = [e['text'] for e in site.svg('#cloudSvg') if e['tag'] == 'text']
        o['cloudSub'] = site.texts('#cloudSub'); o['cloudNote'] = site.texts('#cloudNote')
        o['toggle_hidden'] = pg.evaluate("() => document.querySelector('.toggle').hidden")
        o['body_chart'] = ' '.join(site.texts('.app'))
    if 'record' in views:
        pg.click('#tab-record'); pg.wait_for_timeout(300)
        o['recCount'] = site.texts('#recCount'); o['recSum'] = site.texts('#recSum'); o['recRows'] = len(site.texts('#recBody')) // 9
        o['body_record'] = ' '.join(site.texts('.app'))
    if 'read' in views:
        pg.click('#tab-read'); pg.wait_for_timeout(200)
        o['howBar'] = site.texts('#howBar'); o['body_read'] = ' '.join(site.texts('.app'))
    o['errors'] = list(site.errors)
    return o, pg


def clean(name, o):
    for v in ('now', 'chart', 'record', 'read'):
        t = o.get('body_' + v)
        if t is None: continue
        m = BAD.search(t)
        L.chk(name, f'no raw placeholder in the {v} view', t[max(0, m.start() - 50):m.end() + 30] if m else '', '', 'placeholder shown to a member')
    L.chk(name, 'no page error', ' | '.join(o['errors'][:2]), '', 'page error')


def has(name, label, text, want, cause=''):
    L.chk(name, label, want if want in text else f'(absent) …{text[:160]}', want, cause or 'wording / figure')


def hasnot(name, label, text, bad, cause=''):
    L.chk(name, label, f'shows "{bad}"' if bad in text else '', '', cause or 'unknown shown as none / stale figure')


aplus = [s for s in M.G if s['grade'] == 'A+']
order = {(r['chart'], r['entry']): i for i, r in enumerate(M.led)}
recent = sorted(sorted(aplus, key=lambda s: order[(s['chart'], str(s['d0']))]), key=lambda s: str(s['d0']), reverse=True)[:5]
RECENT = []
for s in recent:
    m = s['m']
    RECENT += [s['chart'], f"{date_long(s['d0'])} · best {pct(rnd(m['up'], 6))} · worst {pct(rnd(m['dd'], 6))}", 'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed']
NYR = sum(1 for s in aplus if 2020 <= s['d0'].year <= 2025)
PER = f"Top-grade setups come about {rnd(F(NYR, 6))} times a year (2020 to 2025 average; bear years, when the market filter is off, are included)."
CLK = NOW + dt.timedelta(minutes=6)

with sync_playwright() as pw:
    # ---------------- 1. feed down
    n = 'feed down (503)'
    s = Site(root, clock=CLK, feed_status=503); o, pg = grab(s, pw)
    cmp_list(L, n, 'card', o['card'], ['BTC · ETH', 'Data unavailable', "Can't reach the data right now",
             "This is an outage, not a quiet market. Setups may be forming that this page can't show. It recovers on its own once the data source is back.", FOOT])
    cmp_list(L, n, 'picker', o['picker'], ['Live', 'Feed unavailable.', 'Forming', 'Feed unavailable.', 'Example: ETH 2D, Sep 2024'])
    cmp_list(L, n, 'previous signals (the ledger still loads, so past signals stay)', o['prev'],
             ['Previous signals', 'updates each close', 'Edge intact', "Unavailable: the feed can't be read right now.", 'Edge lost or closed'] + RECENT + ['See every past signal, misses included'])
    cmp_list(L, n, 'header', o['filter'] + o['asof'] + o['foot'], ['Feed unavailable', 'unavailable'])
    L.chk(n, 'the example does not stand in for an outage', o['preview'], False)
    cmp_list(L, n, 'chart tab', o['chTitle'] + o['chSub'] + o['svgtext'] + o['side'], ['ETH · 2-day · example', "The example's chart data couldn't be loaded.", 'Chart data unavailable'])
    cmp_list(L, n, 'past signals count (from the ledger)', o['recCount'], [f"{len(aplus)} signals · {sum(1 for x in aplus if not x['m']['r10'])} missed +10%"])
    L.chk(n, 'past signals rows', o['recRows'], len(aplus)); L.chk(n, 'past signals summary boxes (feed figures) absent', len(o['recSum']), 0)
    cmp_list(L, n, 'how to read: the bar has no typed number', o['howBar'], ['posting bar'])
    clean(n, o)
    pg.click('#tab-now'); pg.click('#picker [data-sel="example"]'); pg.wait_for_timeout(300)
    cmp_list(L, n, 'example card with no feed', s.texts('#card'), ['ETH · 2D chart · example', 'Example unavailable', "The worked example isn't in the latest data",
             'It comes back with the next good run. Live and forming setups are unaffected.', FOOT])
    s.close()
    # ---------------- 2. feed down and ledger missing
    n = 'feed down, ledger missing'
    s = Site(root, clock=CLK, feed_status=503, ledger=None); o, pg = grab(s, pw)
    cmp_list(L, n, 'previous signals', o['prev'], ['Previous signals', 'updates each close', 'Edge intact', "Unavailable: the feed can't be read right now.", 'Edge lost or closed',
             'Past signals unavailable right now.', 'See every past signal, misses included'])
    cmp_list(L, n, 'past signals count', o['recCount'], ['Past signals unavailable right now']); L.chk(n, 'past signals rows', o['recRows'], 0)
    clean(n, o); s.close()
    # ---------------- 3. held back (a real withheld feed: a gating step failed)
    n = 'held back (real withheld feed)'
    hf = json.load(open(os.path.join(synth, 'held/feed/ctzb_feed.json')))
    s = Site(root, feed_obj=hf, clock=CLK); o, pg = grab(s, pw)
    cmp_list(L, n, 'card', o['card'], ['BTC · ETH', 'Setups held back', 'A data check failed on the latest run',
             'The system holds every setup and alert back until its checks pass, so nothing unverified is shown. They return on the next clean run, usually within the hour.', FOOT])
    cmp_list(L, n, 'picker', o['picker'], ['Live', 'Held back: a data check failed on the latest run.', 'Forming', 'Held back: a data check failed on the latest run.', 'Example: ETH 2D, Sep 2024'])
    cmp_list(L, n, 'previous signals', o['prev'], ['Previous signals', 'updates each close', 'Edge intact', 'Held back: a data check failed on the latest run.', 'Edge lost or closed'] + RECENT + ['See every past signal, misses included'])
    cmp_list(L, n, 'header / footer', o['filter'] + o['asof'] + o['foot'], ['Market filter: on', '12 Nov 2026 (feed 04:14 UTC)', 'Daily candles closed through 11 Nov 2026 · updated 04:14 UTC · checks FAILED, cards held back'])
    L.chk(n, 'the example does not stand in for a failed check', o['preview'], False)
    cmp_list(L, n, 'chart tab', o['chTitle'] + o['chSub'] + o['svgtext'] + o['side'], ['ETH · 2-day · example', "The example's chart data couldn't be loaded.", 'Chart data unavailable'], )
    clean(n, o); s.close()
    # ---------------- 3b. fail-closed feed (feed_live.py itself crashed)
    n = 'fail-closed feed (feed_live crashed)'
    ff = json.load(open(os.path.join(synth, 'failclosed/feed/ctzb_feed.json')))
    s = Site(root, feed_obj=ff, clock=CLK); o, pg = grab(s, pw)
    cmp_list(L, n, 'card', o['card'][:3], ['BTC · ETH', 'Setups held back', 'A data check failed on the latest run'])
    cmp_list(L, n, 'header: the market filter is unknown in this feed, so it must not read as off', o['filter'], ['Market filter: unavailable'])
    cmp_list(L, n, 'banner: scored date is unknown in this feed', o['asof'], ['unavailable (feed 04:14 UTC)'])
    cmp_list(L, n, 'footer', o['foot'], ['Daily candles closed through 11 Nov 2026 · updated 04:14 UTC · checks FAILED, cards held back'])
    cmp_list(L, n, 'how to read: the bar', o['howBar'], ['70% bar'])
    clean(n, o); s.close()
    # ---------------- 4. stale
    for hrs, mins in ((4, 59), (5, 1), (29, 30)):
        n = f'stale feed (clock {hrs}h{mins:02d} after the feed)'
        s = Site(root, clock=NOW + dt.timedelta(hours=hrs, minutes=mins)); o, pg = grab(s, pw, views=('now',))
        note = [t for t in o['card'] if t.startswith('This data is')]
        want = [f'This data is {hrs} hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.'] if (hrs, mins) != (4, 59) else []
        cmp_list(L, n, 'stale note (whole hours since the feed, shown past 5 hours)', note, want)
        clean(n, o); s.close()
    n = 'stale feed, nothing live or forming'
    q = copy.deepcopy(FEED); q['cards'] = []; q['open_signals'] = []
    s = Site(root, feed_obj=q, clock=NOW + dt.timedelta(hours=7)); o, pg = grab(s, pw, views=('now',))
    L.chk(n, 'the example does not stand in for stale data', o['preview'], False)
    cmp_list(L, n, 'quiet card with the stale note', o['card'], ['BTC · ETH', 'No setup right now',
             'This data is 7 hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does.',
             'Waiting for the next one', f'The market filter is on. Nothing at the top grade is forming or confirmed today. {PER}', "You'll get a push alert the moment one confirms.", FOOT])
    s.close()
    # ---------------- 5. no setup (filter on / off)
    for reg in ('Bullish', 'Bearish'):
        n = f'no setup, market filter {"on" if reg == "Bullish" else "off"}'
        q = copy.deepcopy(FEED); q['cards'] = []; q['open_signals'] = []; q['market_regime'] = reg
        s = Site(root, feed_obj=q, clock=CLK); o, pg = grab(s, pw)
        L.chk(n, 'opens on the example', o['preview'], True)
        cmp_list(L, n, 'picker', o['picker'], ['Live', 'No live top-grade setups right now.', 'Forming', 'Nothing forming today.', 'Example: ETH 2D, Sep 2024'])
        pg.click('#tab-now'); pg.click('#previewSwitch'); pg.wait_for_timeout(300)
        cmp_list(L, n, 'quiet card (per-year count from my top-grade signals, 2020 to 2025)', s.texts('#card'), ['BTC · ETH', 'No setup right now', 'Waiting for the next one',
                 f'The market filter is on. Nothing at the top grade is forming or confirmed today. {PER}' if reg == 'Bullish' else 'The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.',
                 "You'll get a push alert the moment one confirms.", FOOT])
        cmp_list(L, n, 'header', s.texts('#filterPill'), [f'Market filter: {"on" if reg == "Bullish" else "off"}'])
        clean(n, o); s.close()
    # ---------------- 6. a top-grade forming card
    n = 'top-grade forming card (ETH 1D marked top grade)'
    q = copy.deepcopy(FEED)
    for c in q['cards']:
        if c['signal_id'] == 'ETH-1D-2026-11-13': c['grade'] = 'A+'
    q['open_signals'] = [x for x in q['open_signals'] if x['grade'] != 'A+']
    s = Site(root, feed_obj=q, clock=CLK); o, pg = grab(s, pw)
    v = V['ETH-1D-2026-11-13']; mi = M.miss[('ETH', 'A+')]
    has(n, 'picker says top grade', ' | '.join(o['picker']), f"rose 10% in 60 days · n {v['n']} · top grade · confirms 13 Nov 2026")
    L.chk(n, 'it is the card the page opens on, in the live colour', f"{o['card'][0]} / {o['card'][1]} / {o['frame']}", 'ETH · 1D chart / Setup forming / var(--live)')
    has(n, 'says it can still vanish', ' | '.join(o['card']), 'Not confirmed yet. It can still vanish before it confirms.')
    has(n, 'miss pool is the top-grade pool', ' | '.join(o['card']), f"of all {mi['signals']} ETH top-grade signals")
    has(n, 'miss figures are the top-grade ones', ' | '.join(o['card']), f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak'])}")
    cmp_list(L, n, 'chart title', o['chTitle'], ['ETH · 1D · setup forming'])
    has(n, 'chart side: still forming, no below-grade sentence', ' | '.join(o['side']), 'Still forming. It confirms only if it holds through 13 Nov 2026, and it can vanish before then.')
    hasnot(n, 'chart side: no below-grade sentence', ' | '.join(o['side']), "It isn't top grade")
    hasnot(n, 'cloud: no below-grade note', ' | '.join(o['cloudNote']), "isn't top grade")
    clean(n, o); s.close()
    # ---------------- 7. live cards with each edge status
    combos = [('lost', 0, 'Edge lost.', 'Its odds were below the bar from the entry.'), ('lost', -5, 'Edge lost.', f'It fell to its edge level ({MINUS}5%) before rising 10%.'),
              ('rose10', -5, 'Rose 10%.', f'It rose 10% before falling to its edge level ({MINUS}5%).'), ('rose10', None, 'Rose 10%.', 'It has risen 10% from the entry close.'),
              ('intact', -10, 'On track.', f'It has not fallen to its edge level ({MINUS}10%) or risen 10% yet.'), ('intact', None, 'On track.', 'It has neither risen 10% nor lost its edge; its odds hold at every fall measured.')]
    lv = V[LIVE]
    for st, lvl, head, sent in combos:
        n = f'live card, edge_status {st}, edge level {lvl}'
        q = copy.deepcopy(FEED)
        for x in q['open_signals']:
            if x['signal_id'] == LIVE: x['edge_status'] = st; x['edge_level_pct'] = lvl
        s = Site(root, feed_obj=q, clock=CLK); o, pg = grab(s, pw, clicks=(f'#picker [data-sel="{LIVE}"]',), views=('now',))
        cmp_list(L, n, 'status line', o['card'][3:5], [head, sent + ' The odds below are as of the entry close, not from today.'])
        L.chk(n, 'card colour (dimmed only when the edge is lost)', o['frame'], 'var(--fade)' if st == 'lost' else 'var(--live)')
        mini = [lv['chart'], f"Day {lv['days']} of 60 · best {pct(lv['best'])} · worst {pct(lv['worst'])}", 'Edge lost' if st == 'lost' else 'Rose 10%' if st == 'rose10' else 'On track']
        exp = ['Previous signals', 'updates each close', 'Edge intact'] + (mini if st != 'lost' else ['No open top-grade setup with its edge intact.']) + ['Edge lost or closed'] + (mini if st == 'lost' else []) + RECENT + ['See every past signal, misses included']
        cmp_list(L, n, 'previous signals grouping and badge', o['prev'], exp)
        clean(n, o); s.close()
    # ---------------- 8. extras withheld (a real feed: the extras step failed)
    n = 'extras withheld (real feed)'
    ef = json.load(open(os.path.join(synth, 'extras_off/feed/ctzb_feed.json')))
    s = Site(root, feed_obj=ef, clock=CLK); o, pg = grab(s, pw, clicks=(f'#picker [data-sel="{LIVE}"]',))
    i = o['card'].index('If it misses: went above entry')
    cmp_list(L, n, 'card: the miss row and tiles read n/a, no pool named', o['card'][i:i + 3] + [t for t in o['card'] if t.startswith('Typical worst drop') or t.startswith('Typical change by day 60')],
             ['If it misses: went above entry', 'n/a', 'Lead trader: unavailable', 'Typical worst drop, misses', 'Typical change by day 60, misses'])
    j = o['card'].index('Typical worst drop, misses')
    cmp_list(L, n, 'miss tiles values', [o['card'][j + 1], o['card'][j + 3]], ['n/a', 'n/a'])
    has(n, 'the card keeps its own ladder and edge (bar from the top level)', ' | '.join(o['card']), f"Below 70% the edge is gone")
    cmp_list(L, n, 'cloud', o['cloudtext'] + o['cloudSub'] + o['cloudNote'], ['Past paths unavailable in this feed'])
    cmp_list(L, n, 'how to read: the bar', o['howBar'], ['70% bar'])
    hasnot(n, 'past signals summary has no miss row', ' | '.join(o['recSum']), 'Misses: median best price')
    clean(n, o); s.close()
    # ---------------- 9. ledger missing
    n = 'ledger missing (feed fine)'
    s = Site(root, clock=CLK, ledger=None); o, pg = grab(s, pw)
    cmp_list(L, n, 'past signals count', o['recCount'], ['Past signals unavailable right now']); L.chk(n, 'past signals rows', o['recRows'], 0)
    has(n, 'previous signals says unavailable', ' | '.join(o['prev']), 'Past signals unavailable right now.')
    hasnot(n, 'never "0 signals"', o['body_record'], '0 signals')
    clean(n, o); s.close()
    n = 'ledger missing, nothing live or forming'
    q = copy.deepcopy(FEED); q['cards'] = []; q['open_signals'] = []
    s = Site(root, feed_obj=q, clock=CLK, ledger=None); o, pg = grab(s, pw, clicks=('#previewSwitch',), views=('now',))
    cmp_list(L, n, 'quiet card without the per-year sentence', o['card'], ['BTC · ETH', 'No setup right now', 'Waiting for the next one',
             'The market filter is on. Nothing at the top grade is forming or confirmed today.', "You'll get a push alert the moment one confirms.", FOOT])
    clean(n, o); s.close()
    # ---------------- 10. a chart file missing
    n = 'chart file missing (BTC 2D)'
    s = Site(root, clock=CLK, candles={'ETH 1D', 'ETH 2D', 'BTC 1D'}); o, pg = grab(s, pw, clicks=('#picker [data-sel="ETH-1D-2026-11-13"]', '#tab-chart', 'wait', '#tab-now', f'#picker [data-sel="{LIVE}"]'), views=('now', 'chart'))
    cmp_list(L, n, 'chart tab reads unavailable, nothing left from the setup charted before', o['chTitle'] + o['chSub'] + o['svgtext'] + o['side'] + o['cloudtext'] + o['cloudSub'] + o['cloudNote'],
             ['BTC · 2D', "This chart's candles couldn't be loaded.", 'Chart data unavailable for BTC 2D'])
    clean(n, o); s.close()
    # ---------------- 11. the example's chart file missing
    n = 'example chart file missing'
    s = Site(root, clock=CLK, example=False); o, pg = grab(s, pw, clicks=(f'#picker [data-sel="{LIVE}"]', '#tab-chart', 'wait', '#tab-now', '#picker [data-sel="example"]'), views=('now', 'chart'))
    cmp_list(L, n, 'chart tab reads unavailable, nothing left from the setup charted before (cloud included)', o['chTitle'] + o['chSub'] + o['svgtext'] + o['side'] + o['cloudtext'] + o['cloudSub'] + o['cloudNote'],
             ['ETH · 2-day · example', "The example's chart data couldn't be loaded.", 'Chart data unavailable'], 'previous setup\'s figures left on screen')
    L.chk(n, 'At the alert / What happened toggle', o['toggle_hidden'], True, 'toggle left from the previous setup')
    clean(n, o); s.close()
    # ---------------- 11b. a chart file that does not reach back to the entry
    n = 'chart file too short to reach the entry (BTC 2D, last 20 bars)'
    s = Site(root, clock=CLK)
    full = s.candle_json
    def short(a, tf, full=full):
        j = json.loads(full(a, tf))
        if (a, tf) == ('BTC', '2D'): j['bars'] = j['bars'][-20:]
        return json.dumps(j)
    s.candle_json = short
    o, pg = grab(s, pw, clicks=('#picker [data-sel="ETH-1D-2026-11-13"]', '#tab-chart', 'wait', '#tab-now', f'#picker [data-sel="{LIVE}"]'), views=('now', 'chart'))
    cmp_list(L, n, 'chart tab: title and subtitle are this setup\'s, nothing left from the setup charted before', o['chTitle'] + o['svgtext'] + o['side'] + o['cloudSub'],
             ['BTC · 2D · live setup, day 52 of 60', "This chart's data doesn't reach back to the entry"], 'previous setup\'s title / cloud left on screen')
    hasnot(n, 'subtitle is not the previous setup\'s', ' '.join(o['chSub']), 'Low 10 Nov 2026')
    clean(n, o); s.close()
    # ---------------- 12. an asset/grade with no misses
    n = 'asset/grade with no misses (BTC top grade)'
    q = copy.deepcopy(FEED)
    for r in q['if_it_misses']:
        if (r['asset'], r['grade']) == ('BTC', 'A+'): r.update(misses=0, up_first=0, median_peak_pct=None, mean_peak_pct=None, peaked_5_or_more=0, peaked_10_or_more=0, median_worst_drop_pct=None, median_day60_pct=None)
    s = Site(root, feed_obj=q, clock=CLK); o, pg = grab(s, pw, clicks=(f'#picker [data-sel="{LIVE}"]',))
    i = o['card'].index('If it misses: went above entry')
    cmp_list(L, n, 'miss row', o['card'][i:i + 3], ['If it misses: went above entry', 'none missed', 'of all 33 BTC top-grade signals'])
    j = o['card'].index('Typical worst drop, misses · 0 misses of all 33 BTC top-grade signals') if 'Typical worst drop, misses · 0 misses of all 33 BTC top-grade signals' in o['card'] else -1
    L.chk(n, 'miss tiles name 0 misses and read n/a', ' | '.join(o['card'][j:j + 4]) if j >= 0 else '(tile not found)',
          'Typical worst drop, misses · 0 misses of all 33 BTC top-grade signals | n/a | Typical change by day 60, misses · 0 misses of all 33 BTC top-grade signals | n/a')
    has(n, 'past signals summary: misses row', ' | '.join(o['recSum']), 'Misses: median best price | n/a')
    clean(n, o); s.close()
    # ---------------- 13. an era with no signals, a ladder row with no signals
    n = 'card with an empty era and an empty ladder row'
    q = copy.deepcopy(FEED)
    for x in q['open_signals']:
        if x['signal_id'] == LIVE:
            x['card']['before_2022'] = {'past_trades': 0, 'past_signals': 0, 'rose10_never_fell25_within60d_pct': None}
            x['card']['if_it_falls_first'][3].update(past_trades=0, past_signals=0, still_rose10_pct=None, went_on_to_fall25_pct=None, still_rose10_exact_pct=None)
            x['card']['if_it_falls_first'][2].update(past_trades=0, past_signals=0, still_rose10_pct=None, went_on_to_fall25_pct=None, still_rose10_exact_pct=None)
    s = Site(root, feed_obj=q, clock=CLK); o, pg = grab(s, pw, clicks=(f'#picker [data-sel="{LIVE}"]',))
    i = o['card'].index('Falls 15% first')
    cmp_list(L, n, 'ladder rows with no signals', o['card'][i:i + 6], ['Falls 15% first', 'n 0', 'n/a', 'Falls 20% first', 'n 0', 'n/a'])
    i = o['card'].index('Before 2022')
    cmp_list(L, n, 'era with no signals', o['card'][i:i + 3], ['Before 2022', 'n 0', 'n/a'])
    L.chk(n, 'chart band for the empty row', [t for t in o['svgtext'] if t == 'n/a'], ['n/a'])
    clean(n, o); s.close()
    # ---------------- 14. a live setup with no closed daily bar yet
    n = 'live setup with no closed daily bar yet (best / worst unknown)'
    q = copy.deepcopy(FEED)
    for x in q['open_signals']:
        if x['signal_id'] == LIVE: x.update(days_elapsed=1, day10_pct=None, day30_pct=None, best_so_far_pct=None, worst_so_far_pct=None, edge_status='intact')
    s = Site(root, feed_obj=q, clock=CLK); o, pg = grab(s, pw, clicks=(f'#picker [data-sel="{LIVE}"]',))
    has(n, 'picker', ' | '.join(o['picker']), 'best n/a · worst n/a')
    has(n, 'card line', ' | '.join(o['card']), 'day 1 of 60 · best so far n/a · worst n/a')
    cmp_list(L, n, 'chart live box', o['side'][o['side'].index('Live: day 1 of 60'):][:7], ['Live: day 1 of 60', 'Best so far', 'n/a', 'Worst so far', 'n/a', 'Day 10', 'not yet'])
    clean(n, o); s.close()

with open(out, 'w', newline='') as f:
    csv.writer(f).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + L.rows)
bad = L.bad()
print(f'SYNTH: {len(L.rows)} comparisons, {len(bad)} disagreements, {len(set(r[1] for r in L.rows))} states')
for r in bad:
    print('  ', r[1], '|', r[2], '|', repr(r[3])[:230], '|', repr(r[4])[:160])
