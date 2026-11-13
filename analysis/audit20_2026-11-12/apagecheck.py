"""Audit #20 -- walk the whole member page for one state and compare with my model (check 8, 9, 10)."""
import json, csv, os, re, math, datetime as dt
from fractions import Fraction as Fr
from decimal import Decimal as Dc
import alib as A
from alib import rha, fstr, to_fr, D
import apage as P
from apage import norm, low, pct, pc, money, date_long, MINUS

BAD = re.compile(r"\$\{|undefined|NaN|null%|n/a%|\[object|Infinity")
TRACK = re.compile(r"\b(win rate|track record of|returned|profit of|we made|our trades|strategy return of|P&L|realised gain)\b", re.I)


def run_page(C, M, W, feed, root, pw):
    raw = P.load_raw(root)
    gen = feed['generated_at']; clock = dt.datetime.fromisoformat(gen.replace('Z', '+00:00')) + dt.timedelta(minutes=6)
    s = P.Site(root, pw=pw, clock=clock).open()
    today = W.today; top_open = [o for o in M['open_signals'] if o['grade'] == 'A+']
    cards = M['cards']; topc = [c for c in cards if c['grade'] == 'A+']
    fsorted = sorted(cards, key=lambda c: -(int(c['rose10_within60d_pct']) if c['rose10_within60d_pct'] is not None else -1))
    forming_order = topc + [c for c in fsorted if c not in topc]
    best = (topc or fsorted or [None])[0]
    best_sid = best['signal_id'] if best else None
    d = s.now()
    # ---- banner, header, footer
    C.add('page banner', 'scored date and feed time', norm(d['rv']).split('. Alerts go out')[0], f"Review build. Real pipeline data, scored {date_long(str(today))} (feed {gen[11:16]} UTC)", 'banner')
    C.add('page header', 'market filter', norm(d['filter']), f"Market filter: {'on' if W.gate(today) else 'off'}", 'header filter')
    dy = W.day['ETH']; closed = max(x for x in dy.date if x < today)
    C.add('page footer', 'candles closed through / updated / checks', norm(d['foot']), f"Daily candles closed through {date_long(str(closed))} · updated {gen[11:16]} UTC · checks passed", 'footer')
    C.add('page footer', 'last closed candle is yesterday', str(closed), str(today - dt.timedelta(days=1)), 'footer date')
    C.add('page how-to', 'posting bar', d['howBar'], f'{A.BAR}% bar', 'how to read bar')
    # ---- picker
    pk = d['picker']; live_b = [b for b in pk if 'top' in b['cls'] and b['sel'] in {o['signal_id'] for o in top_open}]
    exp_live = [(o['signal_id'], f"{o['chart']} Day {o['days_elapsed']} best {pct(o['best_so_far_pct'])} · worst {pct(o['worst_so_far_pct'])}") for o in top_open]
    form_b = [b for b in pk if b['sel'] != 'example' and b not in live_b]
    exp_form = [(c['signal_id'], f"{c['chart']} {pc(c['rose10_within60d_pct'])} rose 10% in 60 days · n {c['past_trades']} · {'top grade' if c['grade'] == 'A+' else 'not top grade'} · confirms {date_long(c['confirms_on'])}") for c in forming_order]
    C.add('page picker', 'live buttons', ' | '.join(norm(b['text']) for b in live_b), ' | '.join(t for _, t in exp_live), 'picker live')
    C.add('page picker', 'forming buttons', ' | '.join(norm(b['text']) for b in form_b), ' | '.join(t for _, t in exp_form), 'picker forming')
    C.add('page picker', 'example button', norm(next((b['text'] for b in pk if b['sel'] == 'example'), None)), 'Example: ETH 2D, Sep 2024', 'picker example')
    pn = [norm(x) for x in d['pnone']]
    C.add('page picker', 'empty-row messages', ' | '.join(pn), ' | '.join(([] if exp_live else ['No live top-grade setups right now.']) + ([] if exp_form else ['Nothing forming today.'])), 'picker empty text')
    # ---- previous signals
    sub = lambda o: f"Day {o['days_elapsed']} of 60 · best {pct(o['best_so_far_pct'])} · worst {pct(o['worst_so_far_pct'])}"
    exp_int = [[o['chart'], sub(o), 'Rose 10%' if o['edge_status'] == 'rose10' else 'On track'] for o in top_open if o['edge_status'] != 'lost']
    C.add('page previous', 'edge intact list', json.dumps([[norm(x) for x in r] for r in d['prevIntact']], ensure_ascii=False), json.dumps(exp_int, ensure_ascii=False), 'previous signals (intact)')
    if not exp_int: C.add('page previous', 'edge intact: none text', norm(d['prevIntactNone']), 'No open top-grade setup with its edge intact.', 'previous none')
    led = [r for r in M['ledger'] if r['grade'] == 'A+']
    order = sorted(led, key=lambda r: (A.ASSETS.index(r['asset']), r['entry'], r['chart']))
    recent = sorted(order, key=lambda r: r['entry'], reverse=True)
    badge = lambda r: 'Reached +20%' if r['reached20'] == 'yes' else 'Rose 10%' if r['reached10'] == 'yes' else 'Missed'
    exp_cl = [[o['chart'], sub(o), 'Edge lost'] for o in top_open if o['edge_status'] == 'lost'] + \
             [[r['chart'], f"{date_long(r['entry'])} · best {pct(r['bestMove'])} · worst {pct(r['maxDrawdown'])}", badge(r)] for r in recent[:5]]
    C.add('page previous', 'edge lost or closed list', json.dumps([[norm(x) for x in r[:3]] for r in d['prevClosed']], ensure_ascii=False), json.dumps(exp_cl, ensure_ascii=False), 'previous signals (closed)')
    C.add('page lead', 'lead trader panel', 'feed is unavailable right now' in (d['lead'] or ''), True, 'lead trader (404)')
    C.add('page now', 'no raw placeholder', bool(BAD.search(d['body'])), False, 'placeholder text')
    M['_initial'] = dict(preview=d['preview'], pressed=[b['sel'] for b in pk if b['pressed'] == 'true'])

    def chart_for(kind, mc, mo, loc, sel):
        a, tf = mc['asset'], mc['timeframe']; tfd = int(tf[:-1]); bars = raw[(a, tf)][-70:]
        # the chart file the page reads must be my last 70 raw bars
        p = os.path.join(root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        fb = [(int(float(r['time'])), Fr(Dc(r['open'])), Fr(Dc(r['high'])), Fr(Dc(r['low'])), Fr(Dc(r['close']))) for r in csv.DictReader(open(p))] if os.path.exists(p) else []
        C.add(loc, 'chart file = last 70 raw bars', fb == [(b['t'], b['o'], b['h'], b['l'], b['c']) for b in bars], True, 'candles file')
        s.tab('chart'); dc = s.chart()
        ex = P.exp_chart(M, kind, mc, mo, bars, tfd, feed_day=gen[:10])
        if ex is None: C.add(loc, 'chart: entry bar found', 'no', 'yes', 'entry bar not in chart file'); s.tab('now'); return
        entry = ex['entry']
        if kind == 'open':
            C.add(loc, 'chart title', low(dc['title']), f"{mc['chart'].replace(' ', ' · ')} · live setup, day {mo['days_elapsed']} of 60".lower(), 'chart title')
            C.add(loc, 'chart subtitle', norm(dc['sub']), norm(f"Confirmed {date_long(mo['entry_date'])} · entry close {money(entry)}. Zones use this setup's own card ({mc['sample']}). The shaded zones are the next 60 days, as the odds draw them."), 'chart subtitle')
            C.add(loc, 'entry bar closes on the entry date', str(A.next_open(P.dayof(bars[ex['E']]['t']), tfd) - dt.timedelta(days=1)), mo['entry_date'], 'entry bar')
            C.add(loc, 'entry bar close = entry close', P.money(bars[ex['E']]['c']), money(entry), 'entry close')
        else:
            C.add(loc, 'chart title', low(dc['title']), f"{a} · {tf} · {'setup forming' if mc['grade'] == 'A+' else 'forming, not top grade'}".lower(), 'chart title')
            C.add(loc, 'chart subtitle', norm(dc['sub']), norm(f"Low {date_long(mc['low_day'])} · confirms {date_long(mc['confirms_on'])} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them."), 'chart subtitle')
        low_label = None
        if kind == 'forming':
            lb = next((b for b in bars if str(P.dayof(b['t'])) == mc['low_date']), None)
            dyy = W.day[a]; lowp = dyy.l[dyy.pos[D.fromisoformat(mc['low_day'])]]
            low_label = f"Low {date_long(mc['low_day'])} · {money(lowp)}"
            C.add(loc, 'trough bar low = daily low on the low day', money(lb['l']) if lb else None, money(lowp), 'low marker price')
            if lb: ex['low_xy'] = (ex['X'](bars.index(lb)), ex['Y'](lb['l']))
        P.cmp_chart(C, loc, dc, ex, bars, kind, mc, low_label=low_label)
        P.cmp_side(C, loc, dc, P.exp_side(M, kind, mc, mo, entry))
        C.add(loc, 'view toggle hidden (no outcome yet)', dc['toggleHidden'], True, 'toggle')
        box = dc['side'][1] if len(dc['side']) > 1 else dict(kv=[], text='', title='')
        if kind == 'open':
            C.add(loc, 'side: live box title', low(box['title']), f"Live: day {mo['days_elapsed']} of 60".lower(), 'live day count')
            ek = [['Best so far', pct(mo['best_so_far_pct'])], ['Worst so far', pct(mo['worst_so_far_pct'])], ['Day 10', 'not yet' if mo['day10_pct'] is None else pct(mo['day10_pct'])]]
            for i, (lab, val) in enumerate(ek):
                got = box['kv'][i] if i < len(box['kv']) else [None, None]
                C.add(loc, f'side: {lab}', norm(got[1]), val, 'live box figure')
        else:
            C.add(loc, 'side: still-forming box', norm(box['text']), norm(f"Still forming. It confirms only if it holds through {date_long(mc['confirms_on'])}, and it can vanish before then. " + ('' if mc['grade'] == 'A+' else "It isn't top grade, so no alert goes out for it.")), 'forming box')
            C.add(loc, 'side: stand-in price note', any('Prices use the latest price' in (x or '') for x in dc['side'][0]['fines']), True, 'stand-in note')
        pp = next((p_ for p_ in M['past_paths'] if p_['asset'] == a), None)
        P.cmp_cloud(C, loc, dc, pp, f"Every past {a} top-grade signal, n {pp['signals']}" if pp else None)
        if pp: C.add(loc, 'cloud: not-top-grade caveat', "selected setup isn't top grade" in (dc['cloudNote'] or ''), mc['grade'] != 'A+', 'cloud caveat')
        s.tab('now')

    # ---- every live button
    for o in top_open:
        loc = f"page live {o['signal_id']}"; s.pick(o['signal_id']); dd = s.now()
        if o['card'].get('_empty'):
            C.add(loc, 'card with no past signals', norm(dd['card']['state']), 'No odds yet', 'empty-sample live card')
            C.add(loc, 'card with no past signals: no figure shown', bool(re.search(r'\d+%', ' '.join(x or '' for x in [dd['card']['big']] + dd['card']['emptySmalls']))), False, 'empty-sample live card')
            s.tab('chart'); dc = s.chart(); C.add(loc, 'chart with no past signals', any('No odds to draw yet' in (e_.get('text') or '') for e_ in dc['svg']), True, 'empty-sample chart'); s.tab('now'); continue
        e = P.exp_card(M, 'open', o['card'], o, best_sid); P.cmp_card(C, loc, dd, e)
        C.add(loc, 'edge-lost card dimmed', 'opacity: 0.5' in (dd['card']['bigStyle'] or ''), o['edge_status'] == 'lost', 'dim'); C.add(loc, 'frame colour not live when edge lost', dd['card']['frameC'], 'var(--fade)' if o['edge_status'] == 'lost' else 'var(--live)', 'frame colour')
        C.add(loc, 'no raw placeholder', bool(BAD.search(dd['body'])), False, 'placeholder text')
        chart_for('open', o['card'], o, loc, o['signal_id'])
    # ---- every forming button
    for c in forming_order:
        loc = f"page forming {c['signal_id']}"; s.pick(c['signal_id']); dd = s.now()
        e = P.exp_card(M, 'forming', c, None, best_sid); P.cmp_card(C, loc, dd, e)
        C.add(loc, 'no raw placeholder', bool(BAD.search(dd['body'])), False, 'placeholder text')
        chart_for('forming', c, None, loc, c['signal_id'])
    # ---- the example
    s.pick('example'); dd = s.now(); xc = M['example_card']; loc = 'page example'
    if xc is None:
        C.add(loc, 'state', norm(dd['card']['state']), 'Example unavailable', 'example unavailable')
        s.tab('chart'); dc = s.chart()
        C.add(loc, 'chart', any('Chart data unavailable' in (e_.get('text') or '') for e_ in dc['svg']), True, 'example chart unavailable'); s.tab('now')
    else:
        e = P.exp_card(M, 'example', xc, None, best_sid); P.cmp_card(C, loc, dd, e)
        C.add(loc, 'no raw placeholder', bool(BAD.search(dd['body'])), False, 'placeholder text')
        exf = json.load(open(os.path.join(root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
        mine2 = {b['t']: b for b in raw[('ETH', '2D')]}
        badb = sum(1 for b in exf['bars'] if b['t'] not in mine2 or any(Fr(Dc(repr(b[k]))) != mine2[b['t']][k] for k in 'ohlc'))
        C.add(loc, 'example chart file bars differ from raw ETH 2D', badb, 0, 'example chart file')
        E = exf['entry_index']; eb = exf['bars'][E]
        C.add(loc, 'example entry bar closes 2024-09-22', str(A.next_open(P.dayof(eb['t']), 2) - dt.timedelta(days=1)), '2024-09-22', 'example entry bar')
        C.add(loc, 'example file entry_close', exf['entry_close'], xc['entry_close'], 'example entry close'); C.add(loc, 'example entry bar close', eb['c'], xc['entry_close'], 'example entry close')
        bars = [dict(t=b['t'], o=Fr(Dc(repr(b['o']))), h=Fr(Dc(repr(b['h']))), l=Fr(Dc(repr(b['l']))), c=Fr(Dc(repr(b['c'])))) for b in exf['bars']]
        sig = next(x for x in W.sig[('ETH', '2D')] if x['d0'] == A.EX_DATE); m = sig['m']; dyy = W.day['ETH']; en = sig['entry']
        xpp = M['example_past_paths']
        for happened in (False, True):
            s.tab('chart')
            if happened: s.pg.click('#bHap'); s.pg.wait_for_timeout(350)
            dc = s.chart(); l2 = loc + (' what-happened' if happened else ' at-the-alert')
            ex = P.exp_chart(M, 'example', xc, None, bars, 2, happened=happened, E_idx=E)
            C.add(l2, 'chart title', low(dc['title']), 'ETH · 2-day · example: past confirmed setup'.lower(), 'chart title')
            C.add(l2, 'chart subtitle', norm(dc['sub']), norm(f"Confirmed {date_long('2024-09-22')} · entry close {money(en)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them." + ('' if happened else ' The shaded zones are the next 60 days, as the odds draw them.')), 'chart subtitle')
            hl = None
            if happened:
                hi = max(dyy.h[k] for k in m['ks']); lo = min(dyy.l[k] for k in m['ks'])
                rng = lambda dn: (lambda j: f'days {2 * j - 1}–{2 * j}')(math.ceil(dn / 2))
                hl = [f"This one: {money(hi)} · {pct(m['up'])} · {rng(m['dpk'])}", f"This one: {money(lo)} · {pct(m['dd'])} · {rng(m['ddday'])}"]
                jb = lambda dn: E + math.ceil(dn / 2)
                ex['out_xy'] = [(ex['X'](jb(m['dpk'])), ex['Y'](hi)), (ex['X'](jb(m['ddday'])), ex['Y'](lo))]
            P.cmp_chart(C, l2, dc, ex, bars, 'example', xc, happened_labels=hl)
            P.cmp_side(C, l2, dc, P.exp_side(M, 'example', xc, None, en))
            C.add(l2, 'view toggle shown', dc['toggleHidden'], False, 'toggle')
            box = dc['side'][1] if len(dc['side']) > 1 else dict(kv=[], text='', title='')
            if happened:
                c10 = dyy.c[dyy.pos[sig['d0'] + dt.timedelta(days=10)]]
                ek = [['Reached +10% / +20%', f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}"], ['Best price', f"{pct(m['up'])}, {rng(m['dpk'])}"], ['Deepest drop', f"{pct(m['dd'])}, {rng(m['ddday'])}"],
                      ['Day 10 check', f"{'Red' if c10 < en else 'Green'}, {pct((c10 / en - 1) * 100)}"], ['Price on day 60', pct(m['ret'])]]
                for i, (lab, val) in enumerate(ek):
                    got = box['kv'][i] if i < len(box['kv']) else [None, None]
                    C.add(l2, f'side: {lab}', norm(got[1]), val, 'example outcome figure')
                poly = [(0, 0.0)] + [((k + 1) * 2, float((dyy.c[dyy.pos[sig['d0'] + dt.timedelta(days=(k + 1) * 2)]] / en - 1) * 100)) for k in range(30)]
            else:
                C.add(l2, 'side: at-the-alert box shows no outcome', 'This is all a member had at the alert' in (box['text'] or ''), True, 'outcome at the alert'); poly = None
            P.cmp_cloud(C, l2, dc, xpp, f"ETH top-grade signals whose 60 days had closed by 22 Sep 2024, n {xpp['signals']}" if xpp else None, extra_poly=poly)
            s.tab('now')
    # ---- quiet card (only reachable with nothing selectable)
    if not top_open and not cards:
        if s.pg.is_checked('#previewSwitch'): s.pg.click('#previewSwitch'); s.pg.wait_for_timeout(300)
        dd = s.now(); y1 = int(gen[:4]) - 1; n = sum(1 for r in led if 2020 <= int(r['entry'][:4]) <= y1)
        on = W.gate(today)
        per = '' if (not n or y1 < 2020) else f"Top-grade setups come about {rha(Fr(n, y1 - 2020 + 1))} times a year (2020 to {y1} average; bear years, when the market filter is off, are included)."
        exp_q = norm(f"The market filter is on. Nothing at the top grade is forming or confirmed today. {per}") if on else 'The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.'
        C.add('page quiet', 'state', norm(dd['card']['state']), 'No setup right now', 'quiet card')
        C.add('page quiet', 'text and times-a-year', norm((dd['card']['emptySmalls'] or [None])[0]), exp_q, 'quiet card / times a year')
        C.add('page quiet', 'no raw placeholder', bool(BAD.search(dd['body'])), False, 'placeholder text')
        M['_quiet'] = True
    # ---- past signals tab
    s.tab('record')
    for asset in ('all', 'ETH', 'BTC'):
        r = s.rec(asset); loc = f'page past-signals {asset}'
        rows = [x for x in recent if asset == 'all' or x['asset'] == asset]
        C.add(loc, 'count line', norm(r['count']), f"{len(rows)} signals · {sum(1 for x in rows if x['reached10'] != 'yes')} missed +10%", 'past signals count')
        C.add(loc, 'row count', len(r['rows']), len(rows), 'past signals rows')
        for i, x in enumerate(rows):
            got = [norm(v) for v in r['rows'][i]] if i < len(r['rows']) else [None] * 9
            exp = [date_long(x['entry']), x['chart'], money(x['entryPrice']), 'Yes' if x['reached10'] == 'yes' else 'No', 'Yes' if x['reached20'] == 'yes' else 'No',
                   pct(x['bestMove']), pct(x['maxDrawdown']), pct(x['return60d']), str(x['daysToHigh'])]
            rl = f"{loc} {x['chart']} {x['entry']}"
            for lab, g_, e_ in zip(('Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'), got, exp): C.add(rl, lab, g_, e_, 'past signals table')
        go = [g for g in M['grade_odds'] if g['grade'] == 'A+' and (asset == 'all' or g['asset'] == asset)]
        C.add(loc, 'summary boxes', len(r['sum']), len(go), 'past signals summary')
        for i, g in enumerate(go):
            mi = P.miss_for(M, g['asset'], 'A+'); got = r['sum'][i] if i < len(r['sum']) else []
            exp = [[g['asset'], f"{g['past_trades']} signals"], ['Rose 10% in 60 days', pc(g.get('rose10_within60d_pct'))], ['Reached +20% in 60 days', pc(g.get('rose20_within60d_pct'))],
                   ['Rose 10%, never fell 25.3%', pc(g.get('rose10_never_fell25_within60d_pct'))], ['Median deepest dip', pct(g.get('median_deepest_dip_pct'))]] + ([['Misses: median best price', pct(mi['median_peak_pct'])]] if mi else [])
            for j, (lab, val) in enumerate(exp):
                gg = got[j] if j < len(got) else [None, None]
                C.add(f"{loc} summary {g['asset']}", lab, norm(gg[1]), val, 'past signals summary figure'); C.add(f"{loc} summary {g['asset']}", lab + ' (label)', norm(gg[0]), lab, 'label')
        C.add(loc, 'heading says computed, never traded', 'computed, never traded' in (r['head'] or '').lower(), True, 'entry-quality wording')
    body = s.pg.inner_text('body')
    C.add('page past-signals', 'no raw placeholder', bool(BAD.search(body)), False, 'placeholder text')
    C.add('page past-signals', 'says not a return or a track record', 'this is entry quality, not a return or a track record' in body, True, 'entry-quality wording')
    # ---- how to read
    s.tab('read'); body = s.pg.inner_text('#view-read')
    for frag in ('rose 10% within 60 days of the entry close', 'without ever falling 25.3% below the entry close', '3.3x leverage with 5% maintenance margin', 'median best price within 60 days',
                 'median deepest dip within 60 days', 'after it first falls 5%, 10%, 15% or 20%', f'drop below our {A.BAR}% bar', 'They measure the quality of the entry, not a trading result',
                 'The header shows the filter as it is today', 'A confirmed alert is final'):
        C.add('page how-to', f'definition: {frag[:40]}', frag in norm(body), True, 'how-to-read wording')
    full = s.pg.inner_text('body')
    C.add('page whole', 'footer: entry quality only', 'entry quality only' in full, True, 'entry-quality wording')
    C.add('page whole', 'nothing reads as a strategy return / trades taken', bool(TRACK.search(full)), False, 'entry-quality wording')
    C.add('page whole', 'javascript errors', len(s.errors), 0, 'page error: ' + '; '.join(s.errors)[:200])
    s.close()
