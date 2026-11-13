"""Audit 19 page checks (item 8): every figure the member page displays, against MY values.
usage: page_check.py <state dir> <clock ISO> <label> <out csv>"""
import csv, json, os, sys, math, datetime as dt, re
from decimal import Decimal
from fractions import Fraction as Fr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
import pagelib as PL
from pagelib import pct, pc, money, px_at, norm, DL, MINUS
import audit_data as AD

FOOT = "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record. Past results don't guarantee future results."
W, H, L, RR, T, B = 1100, 520, 20, 960, 24, 480


def close(a, b, tol=0.02):
    try: return abs(float(a) - float(b)) <= tol
    except Exception: return False


def tg(grade): return 'top-grade' if grade == 'A+' else 'same-grade'


def exp_now(info, sid, best_sid):
    """expected text of the Now card for one of my cards"""
    mc = info['mycards'][sid]; o = mc['o']; idn = mc['ident']; kind = mc['kind']; a = mc['a']; g = mc['grade']; n = o['past_trades']
    mi = info['miss_stats'](info['knownA']) if kind == 'example' else (info['miss_stats'](info['byg'][(a, g)]) if (a, g) in info['byg'] else None)
    lvl = AD.edge_level(o); e = {}
    e['where'] = f"{a} · {mc['tf']} chart" + (' · example' if kind == 'example' else '')
    e['state'] = {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind]
    if kind == 'forming':
        line = f"Low {DL(idn['low_day'])} · confirms {DL(idn['confirms_on'])}" + (f" if it closes above {money(idn['must_close_above'])}" if idn['must_close_above'] else '')
        note = (("Best setup forming today." if sid == best_sid else "Setup forming.") + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.") if g != 'A+' else "Not confirmed yet. It can still vanish before it confirms."
    elif kind == 'open':
        line = f"Confirmed {DL(idn['confirms_on'])} · entry close {money(idn['entry_close'])} · day {mc['days']} of 60 · best so far {pct(mc['best'])} · worst {pct(mc['worst'])}"
        st, lv = mc['status'], mc['lvl']
        if st == 'lost': note = "Edge lost. " + ("Its odds were below the bar from the entry." if lv == 0 else f"It fell to its edge level ({pct(lv, 0)}) before rising 10%.")
        elif st == 'rose10': note = "Rose 10%. " + ("It has risen 10% from the entry close." if lv is None else f"It rose 10% before falling to its edge level ({pct(lv, 0)}).")
        else: note = "On track. " + ("It has neither risen 10% nor lost its edge; its odds hold at every fall measured." if lv is None else f"It has not fallen to its edge level ({pct(lv, 0)}) or risen 10% yet.")
        note += " The odds below are as of the entry close, not from today."
    else:
        line = f"Example: confirmed {DL('2024-09-22')} · entry close {money(idn['entry_close'])}"; note = None
    e['smalls'] = [line] + ([note] if note else [])
    e['big'] = pc(o['rose10_within60d_pct'])
    e['odds'] = [e['big'], 'rose 10% within 60 days' + (' · at the entry close, not from today' if kind == 'open' else ''), f"{pc(o['rose10_never_fell25_within60d_pct'])} did it without ever falling 25.3%",
                 f"from {mc['basis']} · every figure covers the 60 days after entry"]
    edge = (f"Below the 70% bar from entry" if lvl == 0 else f"{pct(lvl, 0)} before it rises 10%" if lvl is not None else 'Holds at every level')
    miss = 'n/a' if mi is None else 'none missed' if not mi['misses'] else f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}"
    e['kv'] = [['Typical high', pct(o['typical_biggest_rise_exact_pct'])], ['Typical drop from entry', pct(o['typical_deepest_dip_exact_pct'])], ['Edge gone below', edge], ['If it misses: went above entry', miss]]
    pooltxt = (f"{mi['misses']} misses of {'the' if kind == 'example' else 'all'} {mi['signals']} {a} {tg(g)} signals" + (' known by then' if kind == 'example' else '')) if mi and mi['signals'] else None
    e['pool'] = (f"{'of the' if kind == 'example' else 'of all'} {mi['signals']} {a} {tg(g)} signals" + (' known by then' if kind == 'example' else '')) if mi and mi['signals'] else None
    e['marker'] = 'Lead trader: unavailable'
    e['tiles'] = [['Dip before the high, from entry', pct(o['typical_dip_before_rise_exact_pct'])], ['High lands around', f"Day {o['typical_day_of_60d_high']}"],
                  [f'Reached +20% within 60 days · n {n}', pc(o['rose20_within60d_pct'])], [f'Touched {MINUS}30% within 60 days · n {n}', pc(o['fell30_within60d_pct'])],
                  ['Typical high', pct(o['typical_biggest_rise_exact_pct'])], ['Deepest dip lands around', f"Day {o['typical_day_of_deepest_dip']}"],
                  ['Typical worst drop, misses' + (f' · {pooltxt}' if pooltxt else ''), pct(mi['median_worst_drop_pct']) if mi else 'n/a'],
                  ['Typical change by day 60, misses' + (f' · {pooltxt}' if pooltxt else ''), pct(mi['median_day60_pct']) if mi else 'n/a']]
    lad = [dict(label=f'From entry n {n}', val=pc(o['from_entry.still_rose10_pct']), gone=o['from_entry.still_rose10_exact_pct'] is not None and o['from_entry.still_rose10_exact_pct'] < 70, width=f"{o['from_entry.still_rose10_pct'] or 0}%")]
    for th in (5, 10, 15, 20):
        v = o[f'falls{th}.still_rose10_pct']; x = o[f'falls{th}.still_rose10_exact_pct']
        lad.append(dict(label=f"Falls {th}% first n {o[f'falls{th}.past_trades']}", val=pc(v), gone=x is not None and x < 70, width=f'{v or 0}%'))
    e['ladder'] = lad
    e['ladderLbl'] = ['Where the odds fade · this setup', 'By era']
    e['ladderNote'] = "Share of this setup's past signals that, after first falling that far, still rose 10% before ever falling 25.3%. Below 70% the edge is gone. Small samples: read the n."
    e['eras'] = [dict(label=f"{t} n {o[k + '.past_trades']}", val=pc(o[k + '.rose10_never_fell25_within60d_pct']), gone=False, width=f"{o[k + '.rose10_never_fell25_within60d_pct'] or 0}%") for t, k in (('Before 2022', 'before_2022'), ('Since 2022', 'since_2022'))]
    e['foot'] = FOOT
    e['bigOpacity'] = '0.5' if kind == 'open' and mc['status'] == 'lost' else ''
    return e


CI = {'where', 'ladderLbl'}   # shown through CSS text-transform: uppercase; compared case-insensitively


def cmp_struct(R, loc, got, exp, keys):
    for k in keys:
        g, x = got.get(k), exp.get(k)
        if k in CI:
            g = [y.lower() for y in g] if isinstance(g, list) else (g.lower() if g else g); x = [y.lower() for y in x] if isinstance(x, list) else x.lower()
        if isinstance(x, list):
            R.add(loc, f'{k} (count)', len(g or []), len(x))
            for i, (gi, xi) in enumerate(zip(g or [], x)):
                if isinstance(xi, dict):
                    for kk in xi: R.add(loc, f'{k}[{i}].{kk}', gi.get(kk), xi[kk], gi.get(kk) == xi[kk])
                elif isinstance(xi, list):
                    for j, (a, b) in enumerate(zip(gi, xi)): R.add(loc, f'{k}[{i}][{j}]', a, b, a == b)
                else: R.add(loc, f'{k}[{i}]', gi, xi, gi == xi)
        else: R.add(loc, k, g, x, g == x)


def exp_chart_check(R, loc, ch, info, sid, bars, happened=False, ex_file=None):
    """geometry and text of the Chart tab for one of my cards. bars: list of dict(t,o,h,l,c) the page was served."""
    mc = info['mycards'][sid]; o = mc['o']; idn = mc['ident']; kind = mc['kind']; a = mc['a']; tf = mc['tf']; g = mc['grade']; n = o['past_trades']; S = info['S']
    dates = [dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date() for b in bars]
    entry_day = dt.date.fromisoformat(idn['confirms_on'])
    forming = kind != 'example'
    opens = list(dates)
    if forming:
        while opens[-1] <= entry_day + 61 * DAY: opens.append(next_open(opens[-1], tf))
    nS = len(opens) if forming else len(bars); slot = (RR - L) / nS; X = lambda i: L + slot * i + slot / 2
    slot_of = lambda d: max(i for i in range(len(opens)) if opens[i] <= d) if opens[0] <= d else 0
    if kind == 'forming':
        E = len(bars) - 1; A = slot_of(entry_day); entry = idn['price_now']
        R.add(loc, "today's bar is the last candle", str(bar_open_of(S.today, tf)), str(dates[-1]), bar_open_of(S.today, tf) == dates[-1])
        R.add(loc, 'confirmation date is the last day of its bar', str(next_open(opens[A], tf) - DAY), str(entry_day), next_open(opens[A], tf) - DAY == entry_day)
    else:
        E = next((i for i, d in enumerate(dates) if next_open(d, tf) - DAY == entry_day), None); A = E; entry = idn['entry_close']
        R.add(loc, 'a bar closes on the entry date', E is not None, True, E is not None)
        if E is None: return
        R.add(loc, 'entry close = that bar\'s close', bars[E]['c'], entry)
    high_px, t10_px, drop_px = px_at(entry, o['typical_biggest_rise_exact_pct']), px_at(entry, 10), px_at(entry, o['typical_deepest_dip_exact_pct'])
    lvl = AD.edge_level(o); edge_px = px_at(entry, lvl) if lvl else None
    shown = bars[:E + 1] if (kind == 'example' and not happened) else bars
    lo = min(min(b['l'] for b in shown), float(drop_px), float(entry) * 0.8) * 0.95; hi = max(max(b['h'] for b in shown), float(high_px)) * 1.07
    Y = lambda p: B - (float(p) - lo) / (hi - lo) * (B - T)
    xE = X(A); i60 = min(nS - 1, slot_of(entry_day + 60 * DAY)); x60 = X(i60); hd = o['typical_day_of_60d_high']; xH = X(slot_of(entry_day + hd * DAY))
    if forming or happened:
        R.add(loc, 'Day 60 slot holds the 60th calendar day', f'{opens[i60]}..{(opens[i60 + 1] - DAY) if i60 + 1 < len(opens) else next_open(opens[i60], tf) - DAY}', str(entry_day + 60 * DAY),
              opens[i60] <= entry_day + 60 * DAY < (opens[i60 + 1] if i60 + 1 < len(opens) else next_open(opens[i60], tf)))
    svg = ch['svg']; texts = [e for e in svg if e['tag'] == 'text']; lines = [e for e in svg if e['tag'] == 'line']; rects = [e for e in svg if e['tag'] == 'rect']
    vl = [l for l in lines if l['x1'] == l['x2'] and close(l['y1'], T) and close(l['y2'], B)]
    def vline(label_exp, x_exp, what):
        t = [e for e in texts if e['text'] == label_exp]
        R.add(loc, f'{what}: label', t[0]['text'] if t else None, label_exp, bool(t))
        if t: R.add(loc, f'{what}: x position', round(float(t[0]['x']) - 6, 2), round(x_exp, 2), close(float(t[0]['x']) - 6, x_exp) and any(close(l['x1'], x_exp) for l in vl))
    vline('Today' if kind == 'forming' else 'Entry', X(E), 'Today line on the open bar' if kind == 'forming' else 'Entry line on the entry bar')
    vline(f'High usually ~day {hd}', xH, 'typical-high-day line on the bar holding that day')
    vline('Day 60', x60, 'Day 60 line on the bar holding day 60')
    nv = 3
    if kind == 'forming' and A > E: vline(f"Confirms {DL(idn['confirms_on'])} · entry, day 0", X(A), 'Confirms line on the confirmation bar'); nv += 1
    R.add(loc, 'number of vertical day lines', len(vl), nv)
    # horizontal levels
    hl = [l for l in lines if l['y1'] == l['y2'] and l.get('stroke-width') in ('2', '2.5')]
    for nm, p in (('typical high', high_px), ('+10% level', t10_px), ('entry', entry), ('typical drop', drop_px)) + ((('edge level', edge_px),) if edge_px is not None else ()):
        m = [l for l in hl if close(l['y1'], Y(p)) and close(l['x1'], xE) and close(l['x2'], x60)]
        R.add(loc, f'{nm} line at {money(p)}: y, from the entry to day 60', len(m) >= 1, True, len(m) >= 1)
    R.add(loc, 'number of level lines', len(hl), 4 + (1 if edge_px is not None else 0))
    tags = sorted(e['text'] for e in texts if e.get('fill') == '#07060F')
    R.add(loc, 'price tags', ' | '.join(tags), ' | '.join(sorted([money(high_px), money(t10_px), money(entry), money(drop_px)])), tags == sorted([money(high_px), money(t10_px), money(entry), money(drop_px)]))
    zones = [r for r in rects if r.get('opacity') in ('0.07', '0.1')]
    R.add(loc, 'upside zone: entry to typical high, entry to day 60', bool(zones) and (zones[0]['x'], zones[0]['y'], zones[0]['width'], zones[0]['height']), 'ok',
          len(zones) == 2 and close(zones[0]['x'], xE) and close(zones[0]['y'], Y(high_px)) and close(zones[0]['width'], x60 - xE) and close(zones[0]['height'], Y(entry) - Y(high_px)))
    R.add(loc, 'downside zone: entry to typical drop, entry to day 60', bool(zones) and (zones[-1]['x'], zones[-1]['y'], zones[-1]['width'], zones[-1]['height']), 'ok',
          len(zones) == 2 and close(zones[1]['x'], xE) and close(zones[1]['y'], Y(entry)) and close(zones[1]['width'], x60 - xE) and close(zones[1]['height'], Y(drop_px) - Y(entry)))
    # ladder bands
    bands = [r for r in rects if r.get('opacity') == '0.24']
    steps = [(0, -5, o['from_entry.still_rose10_pct'], o['from_entry.still_rose10_exact_pct'], n)] + [(-th, -th - 5, o[f'falls{th}.still_rose10_pct'], o[f'falls{th}.still_rose10_exact_pct'], o[f'falls{th}.past_trades']) for th in (5, 10, 15)]
    R.add(loc, 'ladder bands drawn', len(bands), 4)
    for (a1, b1, v, vx, nn), r in zip(steps, bands):
        y1 = Y(float(entry) * (1 + a1 / 100)); y2 = min(B, Y(float(entry) * (1 + b1 / 100)))
        col = 'var(--closed)' if v is None else 'var(--high)' if vx >= 70 else 'var(--drop)'
        R.add(loc, f'ladder band {a1}..{b1}%: position and colour (exact share vs 70)', (r['y'], r['height'], r['fill']), (round(y1, 2), round(y2 - y1, 2), col), close(r['y'], y1) and close(r['height'], y2 - y1) and r['fill'] == col and close(r['x'], xE))
        lab = 'n/a' if v is None else f'{v}% · n {nn}'
        t = [e for e in texts if e['text'] == lab and close(e['y'], (y1 + y2) / 2 + 5, 0.05)]
        R.add(loc, f'ladder band {a1}..{b1}%: text', t[0]['text'] if t else [e['text'] for e in texts if '· n ' in e['text']], lab, bool(t))
    # labels with figures
    def has(label, what):
        R.add(loc, what, next((e['text'] for e in texts if e['text'] == label), [e['text'] for e in texts if e['text'][:8] == label[:8]]), label, any(e['text'] == label for e in texts))
    has(f"Typical high {pct(o['typical_biggest_rise_exact_pct'])}", 'typical high label'); has(f"+10% · {pc(o['rose10_within60d_pct'])} of past signals got here", '+10% label')
    has(f"Typical drop {pct(o['typical_deepest_dip_exact_pct'])}", 'typical drop label')
    if edge_px is not None: has(f"Edge gone below {money(edge_px)} ({pct(lvl, 0)}, before +10%)", 'edge label')
    else: R.add(loc, 'no edge line when the edge is 0 or holds', sum('Edge gone' in e['text'] for e in texts), 0)
    # axis labels: price labels sit on my scale; date labels name their slot's open date
    ax = [e for e in texts if re.fullmatch(r'\$[\d,]+', e['text']) and close(e['x'], RR + 8)]
    okax = all(abs(int(e['text'][1:].replace(',', '')) - (lo + (B - (float(e['y']) - 5)) / (B - T) * (hi - lo))) <= 0.51 for e in ax)
    R.add(loc, f'price-axis labels on my scale ({len(ax)} labels)', okax, True, okax and len(ax) > 0)
    dl = [e for e in texts if close(e['y'], B + 22)]
    okd = True
    for e in dl:
        i = round((float(e['x']) - L) / slot - 0.5); d = opens[min(i, len(opens) - 1)]
        if e['text'] != f'{d.day:02d} {PL.MONTHS[d.month - 1]}': okd = False
    R.add(loc, f'date-axis labels name their bar ({len(dl)} labels)', okd, True, okd and len(dl) > 0)
    # candles
    wicks = [l for l in lines if l['x1'] == l['x2'] and not (close(l['y1'], T) and close(l['y2'], B))]
    upto = len(bars) if (forming or happened) else E + 1
    R.add(loc, 'candles drawn', len(wicks), upto)
    okw = all(close(w['x1'], X(i)) and close(w['y1'], Y(bars[i]['h'])) and close(w['y2'], Y(bars[i]['l'])) for i, w in enumerate(wicks[:upto]))
    R.add(loc, 'every candle on its bar and at its high/low', okw, True, okw)
    circ = [e for e in svg if e['tag'] == 'circle']
    if kind == 'forming':
        li = next((i for i, d in enumerate(dates) if str(d) == idn['low_date']), None)
        lab = f"Low {DL(idn['low_day'])} · {money(mc['tlow'])}"
        R.add(loc, 'low marker label (day and price of the low)', next((e['text'] for e in texts if e['text'].startswith('Low ')), None), lab, any(e['text'] == lab for e in texts))
        R.add(loc, 'low marker on the trough bar at its low', bool(circ) and (circ[0]['cx'], circ[0]['cy']), 'ok', li is not None and len(circ) == 1 and close(circ[0]['cx'], X(li)) and close(circ[0]['cy'], Y(bars[li]['l'])) and bars[li]['l'] == mc['tlow'])
    elif kind == 'example' and happened:
        d1 = S.day[a]; s = mc['sig']; m = info['M'](s); e_ = Fr(s['entry_s'])
        for nm, kk, below in (('best', max(m['ks'], key=lambda k: (d1.h[k], -k)), False), ('deepest', min(m['ks'], key=lambda k: (d1.l[k], k)), True)):
            day = d1.date[kk]; price = d1.sl[kk] if below else d1.sh[kk]; bi = max(i for i in range(len(dates)) if dates[i] <= day)
            d0_ = (dates[bi] - entry_day).days; d1_ = min(60, (next_open(dates[bi], tf) - entry_day).days - 1)
            lab = f"This one: {money(price)} · {pct((Fr(price) / e_ - 1) * 100)} · " + (f'days {d0_}–{d1_}' if d1_ > d0_ else f'day {d0_}')
            R.add(loc, f'what happened: {nm} price, percent and days', next((e['text'] for e in texts if e['text'].startswith('This one') and (MINUS in e['text'].split('·')[1]) == below), None), lab, any(e['text'] == lab for e in texts))
            R.add(loc, f'what happened: {nm} day inside the labelled range', (day - entry_day).days, f'{d0_}-{d1_}', d0_ <= (day - entry_day).days <= d1_)
        R.add(loc, 'what happened: two outcome markers', len(circ), 2)
    else:
        R.add(loc, 'no outcome marker at the alert / on a live card', len(circ), 0)
        R.add(loc, 'no "This one" outcome text', sum(e['text'].startswith('This one') for e in texts), 0)
    # known figure texts: nothing else numeric is drawn
    return dict(X=X, Y=Y, E=E, opens=opens, entry=entry, high_px=high_px, t10_px=t10_px, drop_px=drop_px, edge_px=edge_px, lvl=lvl)


def side_check(R, loc, ch, info, sid, geo, happened=False):
    mc = info['mycards'][sid]; o = mc['o']; idn = mc['ident']; kind = mc['kind']; a = mc['a']; g = mc['grade']; n = o['past_trades']; S = info['S']
    sb = ch['side']; main = sb[0]
    R.add(loc, 'side: title', main['title'], 'What the card says', (main['title'] or '').lower() == 'what the card says')
    s1 = f"{a} {mc['tf']}" + (' · example' if kind == 'example' else '') + f" · from {mc['basis']}" + (' · odds as of the entry close, not from today' if kind == 'open' else '')
    R.add(loc, 'side: sample line', main['smalls'][0], s1, main['smalls'][0] == s1)
    R.add(loc, 'side: big number', main['big'], pc(o['rose10_within60d_pct']), main['big'] == pc(o['rose10_within60d_pct']))
    s2 = f"rose 10% within 60 days, from {n} past signals; {pc(o['rose10_never_fell25_within60d_pct'])} without ever falling 25.3%"
    R.add(loc, 'side: n and surv10 line', main['smalls'][1], s2, main['smalls'][1] == s2)
    lvl = geo['lvl']
    kv = [['Typical high', f"{pct(o['typical_biggest_rise_exact_pct'])} · {money(geo['high_px'])}"], ['+10% level', money(geo['t10_px'])], ['Reached +20% within 60 days', pc(o['rose20_within60d_pct'])],
          ['Typical drop', f"{pct(o['typical_deepest_dip_exact_pct'])} · {money(geo['drop_px'])}"],
          ['Edge gone below', 'below the bar already' if lvl == 0 else 'holds at every level' if lvl is None else f"{money(geo['edge_px'])} ({pct(lvl, 0)})"]]
    cmp_struct(R, loc, dict(kv=main['kv']), dict(kv=kv), ['kv'])
    if kind == 'forming':
        R.add(loc, 'side: stand-in price note', main['fines'][0] if main['fines'] else None, "Prices use the latest price (today's bar is still open) as a stand-in for the entry.", bool(main['fines']) and main['fines'][0] == "Prices use the latest price (today's bar is still open) as a stand-in for the entry.")
        t = f"Still forming. It confirms only if it holds through {DL(idn['confirms_on'])}, and it can vanish before then." + ('' if g == 'A+' else " It isn't top grade, so no alert goes out for it.")
        R.add(loc, 'side: forming box', sb[1]['text'], t, sb[1]['text'] == t)
    elif kind == 'open':
        R.add(loc, 'side: live box title', sb[1]['title'], f"Live: day {mc['days']} of 60", (sb[1]['title'] or '').lower() == f"live: day {mc['days']} of 60")
        cmp_struct(R, loc + ' live box', dict(kv=sb[1]['kv']), dict(kv=[['Best so far', pct(mc['best'])], ['Worst so far', pct(mc['worst'])], ['Day 10', 'not yet' if mc['d10'] is None else pct(mc['d10'])]]), ['kv'])
    elif happened:
        d1 = S.day[a]; s = mc['sig']; m = info['M'](s); e_ = Fr(s['entry_s']); ed = s['d0']
        def rng(kk):
            bi_open = bar_open_of(d1.date[kk], mc['tf']); return f"days {(bi_open - ed).days}–{min(60, (next_open(bi_open, mc['tf']) - ed).days - 1)}"
        kh = max(m['ks'], key=lambda k: (d1.h[k], -k)); kl = min(m['ks'], key=lambda k: (d1.l[k], k)); c10 = Fr(d1.sc[d1.pos[ed + 10 * DAY]])
        kv2 = [['Reached +10% / +20%', f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}"], ['Best price', f"{pct(m['up'])}, {rng(kh)}"], ['Deepest drop', f"{pct(m['dd'])}, {rng(kl)}"],
               ['Day 10 check', f"{'Red' if c10 < e_ else 'Green'}, {pct((c10 / e_ - 1) * 100)}"], ['Price on day 60', pct(m['ret'])]]
        R.add(loc, 'side: outcome box title', sb[1]['title'], 'What this one did', (sb[1]['title'] or '').lower() == 'what this one did')
        cmp_struct(R, loc + ' outcome box', dict(kv=sb[1]['kv']), dict(kv=kv2), ['kv'])
    else:
        R.add(loc, 'side: at the alert shows no outcome', sb[1]['text'][:40], 'This is all a member had at the alert', sb[1]['text'].startswith('This is all a member had at the alert') and not sb[1]['kv'])
    lead = [b['text'] for b in sb if 'lead trader' in b['text'].lower()]
    R.add(loc, 'side: lead-trader note says unavailable', lead[0] if lead else None, "The lead trader's feed is unavailable right now, so his entries and exits can't be shown.", bool(lead) and lead[0] == "The lead trader's feed is unavailable right now, so his entries and exits can't be shown.")
    R.add(loc, 'side: entry-quality footer', sb[-1]['text'], FOOT, sb[-1]['text'] == FOOT)


def cloud_check(R, loc, ch, info, sid, happened=False, ex=None):
    mc = info['mycards'][sid]; a = mc['a']; kind = mc['kind']; S = info['S']
    G = info['knownA'] if kind == 'example' else info['byg'].get((a, 'A+'), [])
    P = info['paths'](G); q = lambda k, f: rha(quantile([p[k] for p in P], f), 1)
    Xc = lambda d: 20 + 940 * d / 60; Yc = lambda v: 230 - (max(-40, min(100, float(v))) + 40) / 140 * 218
    sub = f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {len(P)}" if kind == 'example' else f"Every past {a} top-grade signal, n {len(P)}"
    R.add(loc, 'cloud: sample and n', ch['cloudSub'], sub, ch['cloudSub'] == sub)
    note = f"━ median path █ middle half of outcomes{' ━ this signal' if happened else ''}. Day 60: median {pct(q(60, Fr(1, 2)))}, middle half {pct(q(60, Fr(1, 4)))} to {pct(q(60, Fr(3, 4)))}. Daily closes." + (" Top-grade signals only; the selected setup isn't top grade." if kind != 'example' and mc['grade'] != 'A+' else '')
    R.add(loc, 'cloud: day-60 note', ch['cloudNote'], note, norm(ch['cloudNote']) == note)
    pl = [e for e in ch['cloud'] if e['tag'] == 'polyline']; pg = [e for e in ch['cloud'] if e['tag'] == 'polygon']
    def pts(s): return [tuple(float(x) for x in p.split(',')) for p in s.split(' ')]
    med_ = [(Xc(d), Yc(q(d, Fr(1, 2)))) for d in range(61)]
    got = pts(pl[0]['points']) if pl else []
    R.add(loc, 'cloud: median line, 61 days, each at my median', len(got), 61, len(got) == 61 and all(close(g[0], m[0]) and close(g[1], m[1]) for g, m in zip(got, med_)))
    band = [(Xc(d), Yc(q(d, Fr(3, 4)))) for d in range(61)] + [(Xc(d), Yc(q(d, Fr(1, 4)))) for d in range(60, -1, -1)]
    got = pts(pg[0]['points']) if pg else []
    R.add(loc, 'cloud: middle-half band, each day at my quartiles', len(got), 122, len(got) == 122 and all(close(g[0], m[0]) and close(g[1], m[1]) for g, m in zip(got, band)))
    if happened:
        d1 = S.day[a]; s = mc['sig']; e_ = Fr(s['entry_s'])
        mine = [(Xc(0), Yc(0))] + [(Xc(k), Yc((Fr(d1.sc[d1.pos[s['d0'] + k * DAY]]) / e_ - 1) * 100)) for k in range(2, 61, 2)]
        got = pts(pl[1]['points']) if len(pl) > 1 else []
        R.add(loc, "cloud: this signal's path = daily closes on days 2,4..60", len(got), 31, len(got) == 31 and all(close(g[0], m[0]) and close(g[1], m[1]) for g, m in zip(got, mine)))
    else: R.add(loc, 'cloud: no path of this signal at the alert / live', len(pl), 1)
    lab = sorted(e['text'] for e in ch['cloud'] if e['tag'] == 'text')
    R.add(loc, 'cloud: axis labels', '|'.join(lab), 'fixed set', lab == sorted(['+100%', '+50%', '+20%', '0%', '-20%', '-40%'] + [f'Day {d}' for d in range(0, 61, 10)]))


def run(root, clock, label, out):
    from playwright.sync_api import sync_playwright
    RD, info = AD.run(root, clock, label)
    R = Rec(label); S = info['S']; feed = info['feed']; today = info['today']
    gen = feed['generated_at']; at = (dt.datetime.fromisoformat(gen.replace('Z', '+00:00')) + dt.timedelta(minutes=6)).isoformat()
    mycards = info['mycards']
    # the chart files served: last 70 bars of each chart, raw
    for a in ASSETS:
        for tf in TFS:
            j = PL.candles_json(root, f'{a}_{tf}'); raw = list(csv.DictReader(open(os.path.join(root, 'data', f'{a}_{tf}.csv'))))[-70:]
            ok = j is not None and [(b['t'], b['o'], b['h'], b['l'], b['c']) for b in j['bars']] == [(int(float(r['time'])), float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in raw]
            R.add('page.files', f'candles_{a}_{tf}: the last 70 bars of the chart', ok, True, ok)
    exj = json.load(open(os.path.join(root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
    rawd = {int(float(r['time'])): r for r in csv.DictReader(open(os.path.join(root, 'data', 'ETH_2D.csv')))}
    lastt = max(rawd) - (0 if S.today >= dt.date(2024, 11, 23) else 10 ** 12)   # in a replay dated before the example's window ends, the static file runs past the data
    ok = all(b['t'] in rawd and (b['o'], b['h'], b['l'], b['c']) == tuple(float(rawd[b['t']][k]) for k in ('open', 'high', 'low', 'close')) for b in exj['bars'] if b['t'] < lastt)
    R.add('page.files', f"example chart file: {len(exj['bars'])} bars equal the ETH 2D candles", ok, True, ok)
    eb = exj['bars'][exj['entry_index']]; ed = dt.datetime.fromtimestamp(eb['t'], dt.timezone.utc).date()
    R.add('page.files', 'example chart file: entry_index is the bar closing 2024-09-22', str(next_open(ed, '2D') - DAY), '2024-09-22', str(next_open(ed, '2D') - DAY) == '2024-09-22')
    if 'example' in mycards: R.add('page.files', 'example chart file: entry_close', exj['entry_close'], mycards['example']['ident']['entry_close'])
    R.add('page.files', 'example chart file reaches 60 days past entry', exj['bars'][-1]['t'] >= eb['t'] + 60 * 86400, True, exj['bars'][-1]['t'] >= eb['t'] + 60 * 86400)

    led = [r for r in info['lk'].values() if r['grade'] == 'A+']
    aplus_open = [sid for sid, m in mycards.items() if m['kind'] == 'open' and m['grade'] == 'A+']
    aplus_open.sort(key=lambda sid: (mycards[sid]['ident']['confirms_on'], mycards[sid]['ident']['chart']))
    forming = [sid for sid, m in mycards.items() if m['kind'] == 'forming']
    order_feed = [c['signal_id'] for c in feed['cards']]
    forming.sort(key=lambda sid: order_feed.index(sid))
    topf = [sid for sid in forming if mycards[sid]['grade'] == 'A+']
    byodds = sorted(forming, key=lambda sid: -(mycards[sid]['o']['rose10_within60d_pct'] if mycards[sid]['o']['rose10_within60d_pct'] is not None else -1))
    best_sid = (topf or byodds or [None])[0]
    pick_forming = topf + [s for s in byodds if s not in topf]

    with sync_playwright() as pw:
        br = pw.chromium.launch(); site = PL.Site(root); page = site.open(br, at)
        now = page.evaluate(PL.JS_NOW)
        # ---- banner, header, footer ----
        hhmm = gen[11:16]
        b_exp = f"Review build. Real pipeline data, scored {DL(str(today))} (feed {hhmm} UTC). Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run."
        R.add('page.banner', 'banner text, scored date and feed time', now['banner'], b_exp, now['banner'] == b_exp)
        f_exp = f"Market filter: {'on' if S.gate(today) else 'off'}"
        R.add('page.header', 'market filter (gate read today)', now['filter'], f_exp, now['filter'] == f_exp)
        ft = f"Daily candles closed through {DL(str(S.day['ETH'].date[-2]))} · updated {hhmm} UTC · checks passed"
        R.add('page.footer', 'closed-through date, update time, checks', now['foot'], ft, now['foot'] == ft)
        R.add('page.howto', 'posting bar', now['howBar'], '70% bar', now['howBar'] == '70% bar')
        R.add('page.lead', 'lead trader panel says unavailable (feed 404 in this harness)', now['lead'][:47], "The lead trader's feed is unavailable right now.", now['lead'].startswith("The lead trader's feed is unavailable right now."))
        # ---- picker ----
        exp_pick = [dict(sel=sid, t=f"{mycards[sid]['ident']['chart']} Day {mycards[sid]['days']} best {pct(mycards[sid]['best'])} · worst {pct(mycards[sid]['worst'])}") for sid in aplus_open]
        exp_pick += [dict(sel=sid, t=f"{mycards[sid]['ident']['chart']} {pc(mycards[sid]['o']['rose10_within60d_pct'])} rose 10% in 60 days · n {mycards[sid]['o']['past_trades']} · {'top grade' if mycards[sid]['grade'] == 'A+' else 'not top grade'} · confirms {DL(mycards[sid]['ident']['confirms_on'])}") for sid in pick_forming]
        exp_pick += [dict(sel='example', t='Example: ETH 2D, Sep 2024')]
        cmp_struct(R, 'page.picker', dict(p=now['picker']), dict(p=exp_pick), ['p'])
        exp_none = ([] if aplus_open else ['No live top-grade setups right now.']) + ([] if pick_forming else ['Nothing forming today.'])
        R.add('page.picker', 'empty-row texts', '|'.join(now['pnone']), '|'.join(exp_none), now['pnone'] == exp_none)
        # ---- previous signals ----
        intact = [sid for sid in aplus_open if mycards[sid]['status'] != 'lost']; fading = [sid for sid in aplus_open if mycards[sid]['status'] == 'lost']
        mini = lambda sid: dict(name=mycards[sid]['ident']['chart'], sub=f"Day {mycards[sid]['days']} of 60 · best {pct(mycards[sid]['best'])} · worst {pct(mycards[sid]['worst'])}",
                                badge='Edge lost' if mycards[sid]['status'] == 'lost' else 'Rose 10%' if mycards[sid]['status'] == 'rose10' else 'On track')
        cmp_struct(R, 'page.previous.intact', dict(p=now['prevIntact']), dict(p=[mini(s) for s in intact]), ['p'])
        if not intact: R.add('page.previous.intact', 'empty text', now['prevIntactNone'], 'No open top-grade setup with its edge intact.', now['prevIntactNone'] == 'No open top-grade setup with its edge intact.')
        ledsorted = sorted(enumerate(led), key=lambda ir: ir[1]['entry'], reverse=True)   # stable on the file order within a date
        ledsorted = sorted(led, key=lambda r: r['entry'], reverse=True)
        rec5 = []
        for r in ledsorted[:5]:
            s = info['elig'][(r['chart'], r['entry'])]; m = info['M'](s)
            rec5.append(dict(name=r['chart'], sub=f"{DL(r['entry'])} · best {pct(rha(m['up'], 6))} · worst {pct(rha(m['dd'], 6))}", badge='Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed', bcls='badge ' + ('yes' if m['r10'] else 'no')))
        expc = [dict(mini(s), cls='mini fading') for s in fading] + [dict(x, cls='mini closed') for x in rec5]
        cmp_struct(R, 'page.previous.lost_or_closed', dict(p=now['prevClosed']), dict(p=expc), ['p'])
        # ---- default card ----
        first = (aplus_open + pick_forming + [None])[0]
        default = best_sid or first
        R.add('page.now', 'card shown on opening', next((p['sel'] for p in now['picker'] if p['pressed'] == 'true'), None), default or 'example', next((p['sel'] for p in now['picker'] if p['pressed'] == 'true'), None) == (default or 'example'))
        keys = ['where', 'state', 'smalls', 'big', 'odds', 'kv', 'pool', 'marker', 'tiles', 'ladderLbl', 'ladder', 'ladderNote', 'eras', 'foot', 'bigOpacity']
        if not (aplus_open or pick_forming):
            # quiet market: the example stands in; with it switched off the quiet card must say why it is quiet
            page.uncheck('#previewSwitch'); page.wait_for_timeout(80); nq = page.evaluate(PL.JS_NOW)
            y1 = int(gen[:4]) - 1; cnt = sum(1 for r in led if 2020 <= int(r['entry'][:4]) <= y1)
            per = f" Top-grade setups come about {int(rha(Fr(cnt, y1 - 2019), 0))} times a year (2020 to {y1} average; bear years, when the market filter is off, are included)." if cnt and y1 >= 2020 else ' '
            wantq = ("Waiting for the next one The market filter is on. Nothing at the top grade is forming or confirmed today." + per.rstrip() + " You'll get a push alert the moment one confirms.") if S.gate(today) else "Waiting for the next one The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year. You'll get a push alert the moment one confirms."
            R.add('page.now quiet card', 'state', nq['card']['state'], 'No setup right now', nq['card']['state'] == 'No setup right now')
            R.add('page.now quiet card', 'text, filter state and signals a year (my count)', nq['card']['empty'], wantq, nq['card']['empty'] == wantq)
            page.check('#previewSwitch'); page.wait_for_timeout(80)
        # ---- every picker button: Now card + Chart tab ----
        for sid in aplus_open + pick_forming + ['example']:
            if sid == 'example' and 'example' not in mycards: continue
            page.evaluate("location.hash = '#now'"); page.wait_for_timeout(60)
            page.click(f'#picker .pick[data-sel="{sid}"]'); page.wait_for_timeout(80)
            n1 = page.evaluate(PL.JS_NOW); loc = f'page.now card {sid}'
            cmp_struct(R, loc, n1['card'], exp_now(info, sid, best_sid), keys)
            mc = mycards[sid]
            if mc['kind'] != 'example':
                bars = PL.candles_json(root, mc['ident']['chart'])['bars']
                page.click('#tab-chart'); page.wait_for_timeout(250)
                ch = page.evaluate(PL.JS_CHART); loc = f'page.chart {sid}'; idn = mc['ident']
                if mc['kind'] == 'forming':
                    t_exp = f"{mc['a']} · {mc['tf']} · {'setup forming' if mc['grade'] == 'A+' else 'forming, not top grade'}"
                    s_exp = f"Low {DL(idn['low_day'])} · confirms {DL(idn['confirms_on'])} · price levels drawn from today's price ({money(idn['price_now'])}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them."
                else:
                    t_exp = f"{mc['a']} · {mc['tf']} · live setup, day {mc['days']} of 60"
                    s_exp = f"Confirmed {DL(idn['confirms_on'])} · entry close {money(idn['entry_close'])}. Zones use this setup's own card ({mc['basis']}). The shaded zones are the next 60 days, as the odds draw them."
                R.add(loc, 'title', ch['title'], t_exp, norm(ch['title']).lower() == t_exp.lower()); R.add(loc, 'subtitle', ch['sub'], s_exp, ch['sub'] == s_exp)
                R.add(loc, 'At the alert / What happened toggle hidden for a setup without an outcome', ch['toggleHidden'], True, ch['toggleHidden'] is True)
                geo = exp_chart_check(R, loc, ch, info, sid, bars)
                if geo: side_check(R, loc, ch, info, sid, geo)
                cloud_check(R, loc, ch, info, sid)
            else:
                page.click('#tab-chart'); page.wait_for_timeout(250)
                for mode in ('alert', 'happened'):
                    page.click('#bAlert' if mode == 'alert' else '#bHap'); page.wait_for_timeout(250)
                    ch = page.evaluate(PL.JS_CHART); loc = f'page.chart example ({"At the alert" if mode == "alert" else "What happened"})'
                    R.add(loc, 'title', ch['title'], 'ETH · 2-day · example: past confirmed setup', norm(ch['title']).lower() == 'eth · 2-day · example: past confirmed setup')
                    s_exp = f"Confirmed {DL('2024-09-22')} · entry close {money(mc['ident']['entry_close'])} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them." + ('' if mode == 'happened' else ' The shaded zones are the next 60 days, as the odds draw them.')
                    R.add(loc, 'subtitle', ch['sub'], s_exp, ch['sub'] == s_exp)
                    R.add(loc, 'toggle shown and pressed', (ch['toggleHidden'], ch['alertPressed'], ch['hapPressed']), (False, str(mode == 'alert').lower(), str(mode == 'happened').lower()), (ch['toggleHidden'], ch['alertPressed'], ch['hapPressed']) == (False, str(mode == 'alert').lower(), str(mode == 'happened').lower()))
                    geo = exp_chart_check(R, loc, ch, info, 'example', exj['bars'], happened=mode == 'happened')
                    if geo: side_check(R, loc, ch, info, 'example', geo, happened=mode == 'happened')
                    cloud_check(R, loc, ch, info, 'example', happened=mode == 'happened')
        # ---- Past signals tab ----
        page.click('#tab-record'); page.wait_for_timeout(120)
        for asset in ('all', 'ETH', 'BTC'):
            page.click(f'.seg button[data-asset="{asset}"]'); page.wait_for_timeout(120)
            rc = page.evaluate(PL.JS_RECORD); loc = f'page.past_signals[{asset}]'
            rows = sorted([r for r in led if asset == 'all' or r['asset'] == asset], key=lambda r: r['entry'], reverse=True)
            miss = 0; exp_rows = []
            for r in rows:
                s = info['elig'][(r['chart'], r['entry'])]; m = info['M'](s); miss += not m['r10']
                exp_rows.append([DL(r['entry']), r['chart'], money(rha(Fr(s['entry_s']), 2)), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No', pct(rha(m['up'], 6)), pct(rha(m['dd'], 6)), pct(rha(m['ret'], 6)), str(m['dpk'])])
            cnt = f"{len(rows)} signals · {miss} missed +10%"
            R.add(loc, 'count line', rc['count'], cnt, rc['count'] == cnt)
            R.add(loc, 'rows', len(rc['rows']), len(exp_rows))
            got = {(r[0], r[1]): r for r in rc['rows']}
            R.add(loc, 'row order (newest first)', [r[0] for r in rc['rows']][:3], [r[0] for r in exp_rows][:3], [r[0] for r in rc['rows']] == [r[0] for r in exp_rows])
            for x in exp_rows:
                g_ = got.get((x[0], x[1]))
                for j, nm in enumerate(['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day']):
                    R.add(f'{loc} {x[1]} {x[0]}', nm, g_[j] if g_ else None, x[j], bool(g_) and g_[j] == x[j])
            exps = []
            for a in ASSETS:
                if asset not in ('all', a) or (a, 'A+') not in info['gstat']: continue
                gs = info['gstat'][(a, 'A+')]; mi = info['miss_stats'](info['byg'][(a, 'A+')])
                exps.append([[a, f"{gs['n']} signals"], ['Rose 10% in 60 days', pc(gs['reach10'])], ['Reached +20% in 60 days', pc(gs['reach20'])], ['Rose 10%, never fell 25.3%', pc(gs['surv10'])],
                             ['Median deepest dip', pct(gs['medDip'])], ['Misses: median best price', pct(mi['median_peak_pct'])]])
            cmp_struct(R, loc + ' summary', dict(s=rc['sum']), dict(s=exps), ['s'])
            R.add(loc, 'heading says computed, never traded', rc['head'], 'Every top-grade signal whose 60 days have closed · computed, never traded', rc['head'].lower() == 'every top-grade signal whose 60 days have closed · computed, never traded')
        R.add('page', 'no script errors', len(site.errors), 0, len(site.errors) == 0, '; '.join(site.errors)[:200])
        info['now_text'] = now['text']
        br.close()
    with open(out, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writerows(R.rows)
    return R, info


if __name__ == '__main__':
    root, clock, label, out = sys.argv[1:5]
    R, info = run(root, clock, label, out)
    bad = R.bad(); print(label, 'page comparisons', len(R.rows), 'disagreements', len(bad))
    for r in bad[:60]: print('  ', r[1], '|', r[2], '|', r[3][:110], '|', r[4][:110])
