"""Audit 21 -- drive the member page for one state and compare everything shown with my model."""
import csv, datetime as dt, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C, datacheck as D, pagecheck as P
from pagecheck import nt, pct, pc, money, date_long, MINUS
from core import rnd

BAD = re.compile(r"\$\{|undefined|NaN|null%|n/a%|\[object|Infinity")
REVIEW = "Review build. Real pipeline data, scored {asof}. Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run. Show the example card"
STRATEGY = re.compile(r"\b(profit|P&L|PnL|win rate|won|track record of|returned|our trades|we bought|we sold|filled at|realis|realiz)\b", re.I)


def page_state(pw, ck, mine, root, full=True):
    feed = mine['feed']; now = mine['now']; today = mine['today']
    gen = feed.get('generated_at')
    clock = (dt.datetime.fromisoformat(gen.replace('Z', '+00:00')) + dt.timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ')
    site = P.Site(pw, root, clock)
    site.goto('now'); g = site.now()
    loc = 'page header'
    on = mine['market_on']
    ck.add(loc, 'market filter', g['filter'], f"Market filter: {'on' if on else 'off'}", 'gate today'); ck.add(loc, 'filter pill off-style', g['filterOff'], not on)
    hhmm = f'{now:%H:%M}'
    ck.add(loc, 'banner: scored date and feed time', nt(g['rv']), f'{date_long(str(today))} (feed {hhmm} UTC)', 'scored date / clock')
    ck.add(loc, 'banner text', nt(g['review']), nt(REVIEW.format(asof=f'{date_long(str(today))} (feed {hhmm} UTC)')))
    ck.add('page footer', 'feed state', nt(g['feedState']), f'Daily candles closed through {date_long(str(today - C.D1))} · updated {hhmm} UTC · checks passed', 'last closed daily bar is yesterday')
    ck.add('page footer', 'entry-quality disclaimer', 'entry quality only' in g['foot'], True)
    ck.add('page how-to', 'posting bar', g['howBar'], '70% bar', 'bar from the feed')
    rd = g['read']
    typed = sorted(set(P.NUMTOK.findall(rd)))
    ck.add('page how-to', 'numbers typed on the page are definitions only', json.dumps(typed), json.dumps(sorted({'10%', '60', '25.3%', '3.3', '5%', '15%', '20%', '70%'})), 'a figure typed in How to read')
    ck.add('page lead', 'lead trader panel (feed 404 in this harness)', 'unavailable right now' in (g['lead'] or ''), True)
    # ---- picker
    opens = [o for o in mine['open_signals'] if o['grade'] == 'A+']; cards = mine['cards']
    live_row = g['picker'][0]; form_row = g['picker'][1]
    exp_live = sorted(f"{o['chart']} Day {o['days_elapsed']}best {pct(o['best_so_far_pct'])} · worst {pct(o['worst_so_far_pct'])}" for o in opens)
    ck.add('page picker', 'live buttons', json.dumps(sorted(nt(b['t']) for b in live_row['btns'])), json.dumps([nt(x) for x in exp_live]), 'live button: day, best, worst')
    ck.add('page picker', 'live none-text', live_row['none'], None if opens else 'No live top-grade setups right now.')
    exp_form = sorted(f"{c['chart']} {pc(c['rose10_within60d_pct'])}rose 10% in 60 days · n {c['past_trades']} · {'top grade' if c['grade'] == 'A+' else 'not top grade'} · confirms {date_long(c['confirms_on'])}" for c in cards)
    ck.add('page picker', 'forming buttons', json.dumps(sorted(nt(b['t']) for b in form_row['btns'] if b['sel'] != 'example')), json.dumps([nt(x) for x in exp_form]), 'forming button: share, n, grade, date')
    ck.add('page picker', 'forming none-text', form_row['none'], None if cards else 'Nothing forming today.')
    ck.add('page picker', 'example button', any(b['sel'] == 'example' and nt(b['t']) == 'Example: ETH 2D, Sep 2024' for b in form_row['btns']), True)
    # ---- previous signals
    intact = [o for o in opens if o['edge_status'] != 'lost']; fading = [o for o in opens if o['edge_status'] == 'lost']
    msub = lambda o: f"Day {o['days_elapsed']} of 60 · best {pct(o['best_so_far_pct'])} · worst {pct(o['worst_so_far_pct'])}"
    ei = [[o['chart'], msub(o), 'Rose 10%' if o['edge_status'] == 'rose10' else 'On track'] for o in intact]
    ck.add('page previous', 'edge-intact list', json.dumps([[m['name'], nt(m['sub']), m['badge']] for m in g['prevIntact']]), json.dumps(ei), 'live signals with their edge')
    ck.add('page previous', 'edge-intact none-text', g['prevIntactNone'], None if intact else 'No open top-grade setup with its edge intact.')
    Lap = [x for x in mine['L'] if x[0]['grade'] == 'A+']
    recent = sorted(Lap, key=lambda x: x[0]['entry'], reverse=True)[:5]
    ec = [[o['chart'], msub(o), 'Edge lost'] for o in fading] + [[r['chart'], f"{date_long(r['entry'])} · best {pct(rnd(s['m']['up'], 6))} · worst {pct(rnd(s['m']['dd'], 6))}",
                                                                 'Reached +20%' if s['m']['r20'] else 'Rose 10%' if s['m']['r10'] else 'Missed'] for r, s in recent]
    ck.add('page previous', 'edge lost or closed list', json.dumps([[m['name'], nt(m['sub']), m['badge']] for m in g['prevClosed']]), json.dumps(ec), 'fading live signals then the 5 latest closed top-grade signals')
    bodies = {'now': g['body']}

    def one(kind, mc, mo, sel):
        tag = f"page card {kind} {mc['signal_id']}"
        site.pg.click(f'[data-sel="{sel}"]'); site.pg.wait_for_timeout(250)
        gg = site.now()
        best_id = None
        if kind == 'forming':
            tops = [c for c in cards if c['grade'] == 'A+']
            ranked = sorted(cards, key=lambda c: -(c['rose10_within60d_pct'] if c['rose10_within60d_pct'] is not None else -1))
            best_id = (tops[0] if tops else ranked[0])['signal_id']
        P.cmp_card(ck, tag, gg['card'], P.exp_card(mine, mc, kind, mo, is_best=(mc['signal_id'] == best_id)))
        ck.add(tag, 'no raw placeholder', bool(BAD.search(gg['card']['text'])), False)
        ck.add(tag, 'nothing reads as a strategy return or a trade taken', bool(STRATEGY.search(gg['card']['text'].replace('not a trade or a track record', ''))), False)
        # chart
        site.pg.click('#tab-chart'); gc = site.chart()
        tfd = C.bar_len(mc['timeframe'])
        if kind == 'example':
            ex = json.loads(site.example); bars = ex['bars']
            ck.add(tag + ' chart', 'example file: entry bar closes on 2024-09-22', str(P.bar_dates(bars, 2)[ex['entry_index']] + C.D1), '2024-09-22')
            S = mine['S']; dl = S.day['ETH']
            ck.add(tag + ' chart', 'example file: entry close', ex['entry_close'], rnd(dl.c[dl.pos[dt.date(2024, 9, 22)]], 2), 'example entry close')
            src = S.ch[('ETH', '2D')].b; bad = 0
            for b in bars:
                d = dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date(); i = src.pos.get(d)
                if i is None or (b['o'], b['h'], b['l'], b['c']) != (src.o[i], src.h[i], src.l[i], src.c[i]): bad += 1
            ck.add(tag + ' chart', 'example file: every bar equals the ETH 2D candle', bad, 0, 'static example chart file')
            ck.add(tag + ' chart', 'example file: ends with the bar that holds day 60', str(C.next_open(P.bar_dates(bars, 2)[-1], 2) - C.D1), '2024-11-21')
            P.check_chart(ck, tag + ' chart (at the alert)', gc, mine, mc, 'example', bars, 2, happened=False)
            site.pg.click('#bHap'); gh = site.chart()
            P.check_chart(ck, tag + ' chart (what happened)', gh, mine, mc, 'example', bars, 2, happened=True)
            site.pg.click('#bAlert'); site.pg.wait_for_timeout(100)
            bodies['chart-example'] = site.pg.inner_text('body')
        else:
            a = mc['asset']; bars = site.bars(a, mc['timeframe'])
            # the chart file must be the chart's own last candles
            src = mine['S'].ch[(a, mc['timeframe'])].b
            tail = [(float(src.t[i]), src.o[i], src.h[i], src.l[i], src.c[i]) for i in range(max(0, src.n - 70), src.n)]
            raw = list(csv.DictReader(open(os.path.join(root, 'data', f"{a}_{mc['timeframe']}.csv"))))[-70:]
            ck.add(tag + ' chart', 'chart file = the last 70 raw candles', [(b['t'], b['o'], b['h'], b['l'], b['c']) for b in bars] == [(float(r['time']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in raw], True, 'chart candles')
            P.check_chart(ck, tag + ' chart', gc, mine, mc, kind, bars, tfd, mo=mo, feed_day=today)
            bodies['chart-' + sel] = site.pg.inner_text('body')
        site.pg.click('#tab-now'); site.pg.wait_for_timeout(100)

    for o in opens: one('open', o['card'], o, o['signal_id'])
    for c in cards: one('forming', c, None, c['signal_id'])
    if mine.get('example_card'): one('example', mine['example_card'], None, 'example')
    else:
        site.pg.click('[data-sel="example"]'); site.pg.wait_for_timeout(200); gg = site.now()
        ck.add('page card example', 'example unavailable (no example card in the feed)', gg['card']['state'], 'Example unavailable')
    # ---- the quiet card (nothing selectable): switch the example off
    if not opens and not cards:
        ck.add('page quiet', 'opens on the example when nothing is live or forming', g['preview'], True)
        if g['preview']: site.pg.click('#previewSwitch'); site.pg.wait_for_timeout(200)
        gq = site.now()['card']
        ck.add('page quiet', 'state', gq['state'], 'No setup right now')
        y1 = today.year - 1; nA = sum(1 for r, s in Lap if 2020 <= int(r['entry'][:4]) <= y1)
        per = f"Top-grade setups come about {int(nA / (y1 - 2020 + 1) + 0.5)} times a year (2020 to {y1} average; bear years, when the market filter is off, are included)." if nA and y1 >= 2020 else ''
        exp = (f"The market filter is on. Nothing at the top grade is forming or confirmed today. {per}".strip() if on else "The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.")
        ck.add('page quiet', 'quiet text', exp in nt(gq['empty']), True, f'expected "{exp}" in "{nt(gq["empty"])}"')
    # ---- past signals tab
    site.pg.click('#tab-record'); site.pg.wait_for_timeout(200)
    for asset in ('all', 'ETH', 'BTC'):
        site.pg.click(f'[data-asset="{asset}"]'); site.pg.wait_for_timeout(150)
        gr = site.pg.evaluate(P.EXTRACT_REC); tag = f'page past signals ({asset})'
        rows = sorted([x for x in Lap if asset == 'all' or x[0]['asset'] == asset], key=lambda x: x[0]['entry'], reverse=True)
        ck.add(tag, 'count line', gr['count'], f"{len(rows)} signals · {sum(1 for r, s in rows if not s['m']['r10'])} missed +10%", 'count and misses')
        ck.add(tag, 'rows', len(gr['rows']), len(rows))
        for (r, s), cells in zip(rows, gr['rows']):
            m = s['m']
            exp = [date_long(r['entry']), r['chart'], money(rnd(s['entry'], 2)), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No', pct(rnd(m['up'], 6)), pct(rnd(m['dd'], 6)), pct(rnd(m['ret'], 6)), str(m['dpk'])]
            for name, sh, ex_ in zip(('Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'), cells, exp):
                ck.add(f"{tag} {r['chart']} {r['entry']}", name, nt(sh), ex_, 'past-signal row')
        gos = [x for x in mine['grade_odds'] if x['grade'] == 'A+' and (asset == 'all' or x['asset'] == asset)]
        ck.add(tag, 'summary boxes', len(gr['sum']), len(gos))
        for go, box in zip(gos, gr['sum']):
            mi = next((m for m in mine['if_it_misses'] if m['asset'] == go['asset'] and m['grade'] == 'A+'), None)
            exp = [[go['asset'], f"{go['past_trades']} signals"], ['Rose 10% in 60 days', pc(go['rose10_within60d_pct'])], ['Reached +20% in 60 days', pc(go['rose20_within60d_pct'])],
                   ['Rose 10%, never fell 25.3%', pc(go['rose10_never_fell25_within60d_pct'])], ['Median deepest dip', pct(go['median_deepest_dip_pct'])]] + ([['Misses: median best price', pct(mi['median_peak_pct'])]] if mi else [])
            ck.add(tag, f"summary {go['asset']} rows", len(box), len(exp))
            for bx, ex_ in zip(box, exp): ck.add(f"{tag} summary {go['asset']}", ex_[0], json.dumps([nt(x) for x in bx]), json.dumps(ex_), 'summary figure')
        ck.add(tag, 'head and foot say computed, never traded', 'computed, never traded' in gr['head'] and 'not a return or a track record' in gr['foot'], True)
    bodies['record'] = site.pg.inner_text('body')
    site.pg.click('#tab-read'); site.pg.wait_for_timeout(100); bodies['read'] = site.pg.inner_text('body')
    for k, t in bodies.items():
        ck.add('page', f'no raw placeholder in view {k}', bool(BAD.search(t)), False, str(BAD.search(t)))
    ck.add('page', 'no page error', json.dumps(site.errs[:2]), '[]', 'javascript error')
    site.close()


if __name__ == '__main__':
    from playwright.sync_api import sync_playwright
    root, state, now = sys.argv[1], sys.argv[2], sys.argv[3]
    now = dt.datetime.fromisoformat(now.replace('Z', '+00:00'))
    ck, mine = D.run(root, state, now)
    nd = ck.n
    with sync_playwright() as pw: page_state(pw, ck, mine, root)
    print(state, 'data checks', nd, 'page checks', ck.n - nd, 'diffs', len(ck.bad))
    for r in ck.bad[:50]: print('  ', r[1], '|', r[2], '|', str(r[3])[:300], '|', str(r[4])[:300], '|', r[6][:200])
