"""Check 8: every number the rendered page shows, against my own values (never the feed's)."""
import sys, json, math, statistics as st, datetime as dt, csv
from common import *
import mycalc as M
import chk_feed

MINUS = '−'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']


def date_long(d):
    if isinstance(d, str): d = dt.date.fromisoformat(d)
    return f'{d.day} {MON[d.month - 1]} {d.year}'


def fmt(v, d=1):
    if v is None: return 'n/a'
    r = L.rhaz(v, d) if d else L.rhaz(v)
    if r == 0: return f'{0:.{d}f}'
    return f'{r:.{d}f}'.replace('-', MINUS)


def pct(v, d=1, sign=True):
    if v is None: return 'n/a'
    r = L.rhaz(v, d) if d else L.rhaz(v)
    return ('+' if sign and r > 0 else '') + fmt(v, d) + '%'


from decimal import Decimal as Dc, ROUND_HALF_UP as RHU


def dec(v):
    """the decimal number a float was read from (raw prices have 2 places, stored percentages 6)"""
    return v if isinstance(v, Dc) else Dc(repr(float(v)))


def lvl(entry, p):
    """a price built from a percentage, in exact decimal arithmetic: entry x (1 + p/100)"""
    return dec(entry) * (Dc(1) + dec(p) / Dc(100))


def money(v):
    """half away from zero, once, on the exact (decimal) value"""
    if v is None: return 'n/a'
    q = dec(v).quantize(Dc('0.01'), rounding=RHU)
    return '$' + f'{q:,.2f}'


def ipct(v):
    return 'n/a%' if v is None else f'{v}%'


def missfig(lst):
    ms = [x for x in lst if not x['m']['up'] >= 10]
    if not ms: return dict(signals=len(lst), misses=0, up_first=0, median_peak_pct=None, median_worst_drop_pct=None, median_day60_pct=None)
    best = [x['m']['up'] for x in ms]
    return dict(signals=len(lst), misses=len(ms), up_first=sum(b > 0 for b in best), median_peak_pct=L.rhaz(st.median(best), 1),
                median_worst_drop_pct=L.rhaz(st.median(x['m']['dd'] for x in ms), 1), median_day60_pct=L.rhaz(st.median(x['m']['ret'] for x in ms), 1))


def edge_txt(edge):
    return 'Below the 70% bar from entry' if edge == 0 else (pct(edge, 0) + ' before it rises 10%' if edge is not None else 'Holds at every level')


def exp_card(kind, x, mi, best_sid=None):
    """expected text of every element on the Now card, from my values. x: my dict for the setup."""
    f = x['figs']; e = {}
    a, tf = x['asset'], x['tf']
    high, drop, dipb = f['typical_biggest_rise_exact_pct'], f['typical_deepest_dip_exact_pct'], f['typical_dip_before_rise_exact_pct']
    top = x['grade'] == 'A+'
    if kind == 'forming':
        fm = x['f']
        line = f"Low {date_long(fm['low_day'])} · confirms {date_long(fm['confirms'])}" + (f" if it closes above {money(fm['kill'])}" if fm['kill'] is not None else '')
        head = [f'{a} · {tf} chart', 'Setup forming', line,
                (('Best setup forming today.' if best_sid == x['sid'] else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.") if not top
                else 'Not confirmed yet. It can still vanish before it confirms.']
    elif kind == 'open':
        s, pr = x['s'], x['pr']
        line = f"Confirmed {date_long(s['d0'])} · entry close {money(s['entry'])} · day {pr['days_elapsed']} of 60 · best so far {pct(pr['best_so_far_pct'])} · worst {pct(pr['worst_so_far_pct'])}"
        lost = x['status'] == 'lost'
        head = [f'{a} · {tf} chart', 'Live setup', line,
                ('Edge lost. ' + ('Its odds were below the bar from the entry.' if x['edge'] == 0 else f"It fell to its edge level ({pct(x['edge'], 0)}) before rising 10%.") if lost
                 else 'On track. It has not fallen to its edge level.') + ' The odds below are as of the entry close, not from today.']
    else:
        head = [f'{a} · {tf} chart · example', 'Confirmed setup', f"Example: confirmed {date_long('2024-09-22')} · entry close {money(x['s']['entry'])}"]
    e['head'] = head
    e['odds'] = [ipct(f['rose10_within60d_pct']), 'rose 10% within 60 days' + (' · at the entry close, not from today' if kind == 'open' else ''),
                 f"{f['rose10_never_fell25_within60d_pct']}% did it without ever falling 25.3%", f"from {x['text']} · every figure covers the 60 days after entry"]
    miss_txt = f"{mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}" if mi else 'n/a'
    e['stats'] = [['Typical high', pct(high)], ['Typical drop from entry', pct(drop)], ['Edge gone below', edge_txt(f['_edge'])], ['If it misses: went above entry', miss_txt]]
    if kind == 'forming' and not top and mi: e['stats'].append([f"all {mi['signals']} {a} signals of this grade"])
    e['marker'] = 'Lead trader: unavailable'
    pool = '' if not (mi and mi['signals']) else f" · {mi['misses']} misses of {'the' if kind == 'example' else 'all'} {mi['signals']} {a} {'top-grade' if top else 'same-grade'} signals{' known by then' if kind == 'example' else ''}"
    n = f['past_trades']
    e['tiles'] = [['Dip before the high, from entry', pct(dipb)], ['High lands around', f"Day {f['typical_day_of_60d_high']}"],
                  [f'Reached +20% within 60 days · n {n}', ipct(f['rose20_within60d_pct'])], [f'Touched {MINUS}30% within 60 days · n {n}', ipct(f['fell30_within60d_pct'])],
                  ['Typical high', pct(high)], ['Deepest dip lands around', f"Day {f['typical_day_of_deepest_dip']}"],
                  ['Typical worst drop, misses' + pool, pct(mi['median_worst_drop_pct']) if mi else 'n/a'], ['Typical change by day 60, misses' + pool, pct(mi['median_day60_pct']) if mi else 'n/a']]
    fe = f['from_entry']
    e['ladder'] = [dict(label=f'From entry n {n}', val=ipct(fe['still_rose10_pct']), width=f"{fe['still_rose10_pct']}%", gone=fe['_full'] is not None and fe['_full'] < 70)]
    for r in f['if_it_falls_first']:
        v = r['still_rose10_pct']
        e['ladder'].append(dict(label=f"Falls {r['fell_pct']}% first n {r['past_trades']}", val='n/a' if v is None else f'{v}%', width=f'{v if v is not None else 0}%',
                                gone=r['_full'] is not None and r['_full'] < 70))
    e['eras'] = []
    for t, k in (('Before 2022', 'before_2022'), ('Since 2022', 'since_2022')):
        v = f[k]['rose10_never_fell25_within60d_pct']
        e['eras'].append(dict(label=f"{t} n {f[k]['past_trades']}", val='n/a' if v is None else f'{v}%', width=f'{v if v is not None else 0}%'))
    return e


def cmp_now(C, loc, shown, e, g):
    low = lambda s: s.lower() if isinstance(s, str) else s
    for i, want in enumerate(e['head']):
        C.add(loc, f'card head line {i + 1}', low(shown['head'][i]) if i < len(shown['head']) else None, low(want), group=g)
    C.add(loc, 'card head line count', len(shown['head']), len(e['head']), group=g)
    for i, want in enumerate(e['odds']):
        C.add(loc, ['big number (rose 10%)', 'big-number caption', 'line under it (never fell 25.3%)', 'sample line'][i], shown['odds'][i], want, group=g)
    C.add(loc, 'stat rows', len(shown['stats']), len(e['stats']), group=g)
    for sh, want in zip(shown['stats'], e['stats']):
        C.add(loc, 'stat: ' + want[0][:40], sh, want, group=g)
    C.add(loc, 'lead-trader marker', shown['marker'], e['marker'], group=g)
    C.add(loc, 'tile count', len(shown['tiles']), len(e['tiles']), group=g)
    for sh, want in zip(shown['tiles'], e['tiles']):
        C.add(loc, 'tile label: ' + want[0][:34], low(sh[0]), low(want[0]), group=g)
        C.add(loc, 'tile value: ' + want[0][:34], sh[1], want[1], group=g)
    C.add(loc, 'ladder rows', len(shown['ladder']), len(e['ladder']), group=g)
    for sh, want in zip(shown['ladder'], e['ladder']):
        for k in ('label', 'val', 'width', 'gone'):
            C.add(loc, f"ladder '{want['label']}' {k}", sh[k], want[k], group=g)
    for sh, want in zip(shown['eras'], e['eras']):
        for k in ('label', 'val', 'width'):
            C.add(loc, f"era '{want['label']}' {k}", sh[k], want[k], group=g)
    C.add(loc, 'era rows', len(shown['eras']), len(e['eras']), group=g)
    C.add(loc, 'ladder note names the 70% bar', 'Below 70% the edge is gone' in (shown['ladderFine'] or ''), True, group=g)
    C.add(loc, 'card foot: entry quality only, not a trade or track record', 'Entry quality only: no exit, not a trade or a track record' in (shown['foot'] or ''), True, group=g)


# ---------------------------------------------------------------- chart
def svg_geom(svg):
    wicks = [e for e in svg if e['tag'] == 'line' and e.get('x1') == e.get('x2') and e.get('stroke-width') == '1.5' and 'stroke-dasharray' not in e]
    xs = sorted(float(e['x1']) for e in wicks)
    slot = min(b - a for a, b in zip(xs, xs[1:])) if len(xs) > 1 else None
    return wicks, xs, slot


def raw_bars(S, asset, tf, n=70):
    rows = list(csv.DictReader(open(f'{S.root}/data/{asset}_{tf}.csv')))[-n:]
    return [dict(t=int(float(r['time'])), d=L.udate(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in rows]


def chart_checks(C, loc, S, ch, bars, E_idx, entry_day, entry, f, tf, kind, g, n_drawn, known_upto=None, extra=None):
    """bars: my raw bars for the chart; E_idx my index of the 'Entry'/'Today' bar; entry_day the date day 0;
    n_drawn: how many candles must be drawn; known_upto: index up to which the axis may use bars (None = all)."""
    svg = ch['svg']; step = int(tf[:-1])
    wicks, xs, slot = svg_geom(svg)
    C.add(loc, 'candles drawn', len(wicks), n_drawn, group=g)
    nslots = round(940 / slot)
    idx = lambda x: (float(x) - 20) / slot - 0.5
    # slot dates: my own extension of the bar opens
    opens = [b['d'] for b in bars]
    while len(opens) < nslots + 2: opens.append(L.next_open(opens[-1], step))
    span = lambda i: (opens[i], opens[i + 1] - L.ONE)
    def slot_of(x):
        i = idx(x); return round(i), abs(i - round(i)) < 1e-3
    # candles at their own slots, wicks at their prices -> price scale
    pts = []
    order = sorted(wicks, key=lambda e: float(e['x1']))
    okpos = all(slot_of(e['x1']) == (i, True) for i, e in enumerate(order))
    C.add(loc, 'candles sit on consecutive bar slots from the first bar', okpos, True, group=g)
    for i, e in enumerate(order):
        pts.append((bars[i]['h'], float(e['y1']))); pts.append((bars[i]['l'], float(e['y2'])))
    # least squares y = a + b p
    n = len(pts); sx = sum(p for p, _ in pts); sy = sum(y for _, y in pts); sxx = sum(p * p for p, _ in pts); sxy = sum(p * y for p, y in pts)
    b_ = (n * sxy - sx * sy) / (n * sxx - sx * sx); a_ = (sy - b_ * sx) / n
    resid = max(abs(a_ + b_ * p - y) for p, y in pts)
    C.add(loc, 'candle highs/lows drawn at the raw candle prices (max px error)', round(resid, 3), 0.0, tol=0.02, group=g)
    price_at = lambda y: (float(y) - a_) / b_
    ptol = abs(0.02 / b_)
    lo_ax, hi_ax = price_at(480), price_at(24)
    hi_pct, drop_pct = f['typical_biggest_rise_exact_pct'], f['typical_deepest_dip_exact_pct']
    lv = dict(high=entry * (1 + hi_pct / 100), ten=entry * 1.10, entry=entry, drop=entry * (1 + drop_pct / 100))
    use = bars if known_upto is None else bars[:known_upto + 1]
    my_lo = min(min(b['l'] for b in use), lv['drop'], entry * 0.8) * 0.95; my_hi = max(max(b['h'] for b in use), lv['high']) * 1.07
    C.add(loc, 'axis bottom price (only bars a member had' + (' at the alert' if known_upto is not None else '') + ')', round(lo_ax, 2), round(my_lo, 2), tol=max(ptol, 0.01), group=g)
    C.add(loc, 'axis top price (only bars a member had' + (' at the alert' if known_upto is not None else '') + ')', round(hi_ax, 2), round(my_hi, 2), tol=max(ptol, 0.01), group=g)
    # axis grid labels at their prices
    for e in svg:
        if e['tag'] == 'text' and e.get('x') == '968' and e['text'].startswith('$'):
            C.add(loc, f"axis label {e['text']} position", round(price_at(float(e['y']) - 5)), int(e['text'][1:].replace(',', '')), tol=max(ptol, 0.6), group=g)
    # date labels under the axis
    for e in svg:
        if e['tag'] == 'text' and e.get('y') == '502':
            i, ok = slot_of(e['x']); d = opens[min(i, len(opens) - 1)]
            C.add(loc, f"date label '{e['text']}' = open date of its slot", e['text'], f'{d.day:02d} {MON[d.month - 1]}', group=g)
    # horizontal level lines (x1 != x2, stroke-width 2 or 2.5)
    hl = [e for e in svg if e['tag'] == 'line' and e.get('stroke-width') in ('2', '2.5') and e.get('y1') == e.get('y2')]
    by_col = {e['stroke2']: e for e in hl}
    for col, name, p in (('var(--high)', 'typical high line', lv['high']), ('var(--text)', '+10% line', lv['ten']), ('var(--soft)', 'entry line', lv['entry']), ('var(--drop)', 'typical drop line', lv['drop'])):
        e = by_col.get(col)
        C.add(loc, name + ' price', None if e is None else round(price_at(e['y1']), 2), round(p, 2), tol=max(ptol, 0.01), group=g)
    # price tags (dark text)
    tags = sorted([e for e in svg if e['tag'] == 'text' and e.get('fill') == '#07060F'], key=lambda e: float(e['y']))
    want = sorted([lvl(entry, hi_pct), lvl(entry, 10), dec(entry), lvl(entry, drop_pct)], reverse=True)
    C.add(loc, 'price tags', [e['text'] for e in tags], [money(p) for p in want], group=g)
    labels = {e['text']: e for e in svg if e['tag'] == 'text'}
    C.add(loc, 'label: typical high', f'Typical high {pct(hi_pct)}' in labels, True, group=g)
    C.add(loc, 'label: typical drop', f'Typical drop {pct(drop_pct)}' in labels, True, group=g)
    C.add(loc, 'label: +10% share', f"+10% · {f['rose10_within60d_pct']}% of past signals got here" in labels, True, group=g)
    # vertical lines
    vl = {}
    for i, e in enumerate(svg):
        if e['tag'] == 'line' and e.get('x1') == e.get('x2') and e.get('y1') == '24' and e.get('y2') == '480' and 'stroke-dasharray' in e:
            t = svg[i + 1]['text'] if i + 1 < len(svg) and svg[i + 1]['tag'] == 'text' else ''
            vl[t] = float(e['x1'])
    first = 'Today' if kind == 'forming' else 'Entry'
    C.add(loc, f"'{first}' line present", first in vl, True, group=g)
    if first in vl:
        i, ok = slot_of(vl[first])
        C.add(loc, f"'{first}' line on bar index", (i, ok), (E_idx, True), group=g)
        if kind != 'forming':
            C.add(loc, "'Entry' bar closes on the entry date", str(span(i)[1]), str(entry_day), group=g)
    day60 = entry_day + dt.timedelta(days=60)
    if 'Day 60' in vl:
        i, ok = slot_of(vl['Day 60'])
        inside = span(i)[0] <= day60 <= span(i)[1]
        C.add(loc, "'Day 60' line on the bar containing entry + 60 days", (ok and (inside or (i == nslots - 1 and span(i)[1] < day60))), True, group=g,
              cause=f'line on slot {i} = {span(i)}, day 60 = {day60}')
        C.add(loc, "'Day 60' line not clipped by the chart's right edge", inside, True, group=g, cause=f'line on last slot {span(i)}, day 60 = {day60}')
    else:
        C.add(loc, "'Day 60' line present", False, True, group=g)
    hd = f['typical_day_of_60d_high']; key = f'High usually ~day {hd}'
    C.add(loc, f"label '{key}'", key in vl, True, group=g)
    if key in vl:
        i, ok = slot_of(vl[key]); dd = entry_day + dt.timedelta(days=hd)
        C.add(loc, f"'{key}' line on the bar containing that day", ok and span(i)[0] <= dd <= span(i)[1], True, group=g, cause=f'slot {i} = {span(i)}, day = {dd}')
    if kind == 'forming':
        key = f'Confirms {date_long(entry_day)} · entry, day 0'
        i_today, _ = slot_of(vl.get('Today', 0))
        conf_slot = next(i for i in range(len(opens) - 1) if span(i)[0] <= entry_day <= span(i)[1])
        if conf_slot > E_idx:
            C.add(loc, f"label '{key}'", key in vl, True, group=g)
            if key in vl:
                i, ok = slot_of(vl[key])
                C.add(loc, 'confirmation line on the bar that closes on the confirmation date', (ok, str(span(i)[1])), (True, str(entry_day)), group=g)
    x_entry_line = vl.get(f'Confirms {date_long(entry_day)} · entry, day 0', vl.get(first))
    # zones
    zones = [e for e in svg if e['tag'] == 'rect' and e.get('opacity') in ('0.07', '0.1')]
    C.add(loc, 'zone rectangles', len(zones), 2, group=g)
    for e in zones:
        C.add(loc, f"zone {e['opacity']} starts at the entry line", round(float(e['x']), 2), round(x_entry_line, 2), tol=0.01, group=g)
        C.add(loc, f"zone {e['opacity']} ends at the day-60 line", round(float(e['x']) + float(e['width']), 2), round(vl.get('Day 60', -1), 2), tol=0.01, group=g)
        top_p, bot_p = price_at(e['y']), price_at(float(e['y']) + float(e['height']))
        want_top, want_bot = (lv['high'], lv['entry']) if e['opacity'] == '0.07' else (lv['entry'], lv['drop'])
        C.add(loc, f"zone {e['opacity']} top price", round(top_p, 2), round(want_top, 2), tol=max(ptol, 0.01), group=g)
        C.add(loc, f"zone {e['opacity']} bottom price", round(bot_p, 2), round(want_bot, 2), tol=max(ptol, 0.01), group=g)
    # ladder bands
    bands = [(i, e) for i, e in enumerate(svg) if e['tag'] == 'rect' and e.get('opacity') == '0.24']
    fe = f['from_entry']; rows = f['if_it_falls_first']
    wantb = [(0, -5, fe['still_rose10_pct'], fe['_full'], f['past_trades'])] + [(-rows[k]['fell_pct'], -rows[k + 1]['fell_pct'], rows[k]['still_rose10_pct'], rows[k]['_full'], rows[k]['past_trades']) for k in range(3)]
    C.add(loc, 'ladder bands drawn', len(bands), 4, group=g)
    for (i, e), (a1, b1, v, full, nn) in zip(bands, wantb):
        C.add(loc, f'ladder band {a1}..{b1}% top price', round(price_at(e['y']), 2), round(entry * (1 + a1 / 100), 2), tol=max(ptol, 0.01), group=g)
        bot = min(480.0, a_ + b_ * entry * (1 + b1 / 100))
        C.add(loc, f'ladder band {a1}..{b1}% bottom', round(float(e['y']) + float(e['height']), 2), round(bot, 2), tol=0.03, group=g)
        C.add(loc, f'ladder band {a1}..{b1}% text', svg[i + 1]['text'], 'n/a' if v is None else f'{v}% · n {nn}', group=g)
        C.add(loc, f'ladder band {a1}..{b1}% colour (exact share vs 70)', e['fill2'], 'var(--closed)' if v is None else 'var(--high)' if full >= 70 else 'var(--drop)', group=g)
        C.add(loc, f'ladder band {a1}..{b1}% starts at the entry line', round(float(e['x']), 2), round(x_entry_line, 2), tol=0.01, group=g)
    # edge line + label
    edge = f['_edge']
    et = [e['text'] for e in svg if e['tag'] == 'text' and e['text'].startswith('Edge gone below')]
    if edge:
        C.add(loc, 'edge label', et, [f'Edge gone below {money(lvl(entry, edge))} ({pct(edge, 0)}, before +10%)'], group=g)
        e = by_col.get('var(--fade-2)')
        C.add(loc, 'edge line price', None if e is None else round(price_at(e['y1']), 2), round(entry * (1 + edge / 100), 2), tol=max(ptol, 0.01), group=g)
    else:
        C.add(loc, 'no edge line when the edge is at entry / holds', et, [], group=g)
    return dict(price_at=price_at, slot_of=slot_of, span=span, vl=vl, labels=labels, ptol=ptol, opens=opens, a=a_, b=b_)


def side_checks(C, loc, side, x, entry, kind, g):
    f = x['figs']; box = side[0]
    hi, dr = f['typical_biggest_rise_exact_pct'], f['typical_deepest_dip_exact_pct']
    want_small = f"{x['chart']}{' · example' if kind == 'example' else ''} · from {x['text']}{' · odds as of the entry close, not from today' if kind == 'open' else ''}"
    C.add(loc, 'side: chart and sample', box['small'][0], want_small, group=g)
    C.add(loc, 'side: big number', box['big'], [ipct(f['rose10_within60d_pct'])], group=g)
    C.add(loc, 'side: caption', box['small'][1], f"rose 10% within 60 days, from {f['past_trades']} past signals; {f['rose10_never_fell25_within60d_pct']}% without ever falling 25.3%", group=g)
    edge = f['_edge']
    et = 'below the bar already' if edge == 0 else 'holds at every level' if edge is None else f'{money(lvl(entry, edge))} ({pct(edge, 0)})'
    want = [['Typical high', f'{pct(hi)} · {money(lvl(entry, hi))}'], ['+10% level', money(lvl(entry, 10))], ['Reached +20% within 60 days', ipct(f['rose20_within60d_pct'])],
            ['Typical drop', f'{pct(dr)} · {money(lvl(entry, dr))}'], ['Edge gone below', et]]
    C.add(loc, 'side: rows', len(box['kv']), len(want), group=g)
    for sh, w in zip(box['kv'], want):
        C.add(loc, 'side: ' + w[0], sh, w, group=g)
    C.add(loc, 'side: stand-in note only on forming', any('stand-in for the entry' in t for t in box['fine']), kind == 'forming', group=g)


def cloud_checks(C, loc, ch, n, days, sub, g, not_top=False):
    if not n:
        C.add(loc, "cloud: 'Past paths unavailable' when the asset has no top-grade path", any('Past paths unavailable' in (e.get('text') or '') for e in ch['cloud']), True, group=g)
        return []
    C.add(loc, 'cloud: sample line', ch['cloudSub'], sub, group=g)
    last = days[-1]
    note = f"Day 60: median {pct(last['median_pct'])}, middle half {pct(last['q25_pct'])} to {pct(last['q75_pct'])}. Daily closes."
    C.add(loc, 'cloud: day-60 note', note in ch['cloudNote'], True, group=g, cause=ch['cloudNote'])
    C.add(loc, "cloud: 'isn't top grade' caveat", "the selected setup isn't top grade" in ch['cloudNote'], not_top, group=g)
    X = lambda d: 20 + 940 * d / 60; Y = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
    pl = [e for e in ch['cloud'] if e['tag'] == 'polyline']; pg = [e for e in ch['cloud'] if e['tag'] == 'polygon']
    def pts(e): return [tuple(float(v) for v in p.split(',')) for p in e['points'].split()]
    med = pts(pl[0]); ok = len(med) == 61 and all(abs(px - X(d['day'])) < 1e-6 and abs(py - Y(d['median_pct'])) < 1e-6 for (px, py), d in zip(med, days))
    C.add(loc, 'cloud: median path (61 points) drawn at my medians', ok, True, group=g)
    band = pts(pg[0]); wantb = [(X(d['day']), Y(d['q75_pct'])) for d in days] + [(X(d['day']), Y(d['q25_pct'])) for d in reversed(days)]
    ok = len(band) == 122 and all(abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6 for a, b in zip(band, wantb))
    C.add(loc, 'cloud: middle-half band drawn at my quartiles', ok, True, group=g)
    return pl


def run(name, dump=None):
    S, Cf, mine = chk_feed.run(name)
    C = Checks(name)
    pg = json.load(open(dump or os.path.join(OUT, f'page_{name}.json')))
    C.add('page', 'no page errors', pg['errors'], [], group='8 page')
    P = mine['pool']; gen = S.now
    misses = {}
    for x in P: misses.setdefault((x['asset'], x['grade']), []).append(x)
    misses = {k: missfig(v) for k, v in misses.items()}
    ex_known = [x for x in M.pool(S, known_by=dt.date(2024, 9, 22)) if x['asset'] == 'ETH' and x['grade'] == 'A+']
    ex_miss = missfig(ex_known) if ex_known else None
    # ----- header / footer / banner
    g = '8 header, banner, footer'
    C.add('page banner', 'scored date and feed time', pg['page']['rvAsof'], f"{date_long(S.today)} (feed {gen:%H:%M} UTC)", group=g)
    C.add('page header', 'market filter', pg['page']['filter'], 'Market filter: ' + ('on' if S.gate(S.today) else 'off'), group=g)
    last_closed = S.day['ETH'].d[-2] if S.day['ETH'].d[-1] >= S.today else S.day['ETH'].d[-1]
    C.add('page footer', 'daily candles closed through / updated / checks', pg['page']['feedState'], f"Daily candles closed through {date_long(last_closed)} · updated {gen:%H:%M} UTC · checks passed", group=g)
    C.add('page footer', 'last daily bar in the raw data is today (open) for both assets', (str(S.day['ETH'].d[-1]), str(S.day['BTC'].d[-1])), (str(S.today), str(S.today)), group=g)
    C.add('page how-to-read', 'posting bar', pg['page']['howBar'], '70% bar', group=g)
    C.add('page banner', 'review-build text present', pg['page']['review'].startswith('Review build. Real pipeline data, scored'), True, group=g)
    C.add('page lead trader', 'feed unavailable (harness 404)', 'unavailable right now' in pg['page']['leadBody'], True, group=g)
    C.add('page footer', 'entry quality only disclaimer', 'entry quality only' in pg['page']['foot'], True, group=g)
    # ----- picker
    g = '8 picker'
    top_open = [o for o in mine['open'] if o['grade'] == 'A+']
    forming_sorted = sorted(mine['cards'], key=lambda c: -(c['figs']['rose10_within60d_pct'] if c['figs']['rose10_within60d_pct'] is not None else -1))
    topf = [c for c in forming_sorted if c['grade'] == 'A+']; forming_sorted = topf + [c for c in forming_sorted if c['grade'] != 'A+']
    want_btn = [(o['sid'], f"{o['s']['chart']} Day {o['pr']['days_elapsed']} best {pct(o['pr']['best_so_far_pct'])} · worst {pct(o['pr']['worst_so_far_pct'])}") for o in top_open]
    want_btn += [(c['sid'], f"{c['f']['chart']} {c['figs']['rose10_within60d_pct']}% rose 10% in 60 days · n {c['figs']['past_trades']} · {'top grade' if c['grade'] == 'A+' else 'not top grade'} · confirms {date_long(c['f']['confirms'])}") for c in forming_sorted]
    want_btn += [('example', 'Example: ETH 2D, Sep 2024')]
    shown_btn = [(b['sel'], b['text']) for b in pg['initial']['picker']]
    C.add('picker', 'buttons (which setups; order is layout)', sorted(b[0] for b in shown_btn), sorted(b[0] for b in want_btn), group=g)
    nl = len(top_open)
    C.add('picker', 'live buttons first, then forming, example last', ([b[0] for b in shown_btn[:nl]] == [o['sid'] for o in top_open], shown_btn[-1][0]), (True, 'example'), group=g)
    for (sid, txt) in want_btn:
        sh = dict(shown_btn).get(sid)
        C.add(f'picker {sid}', 'button text', sh, txt, group=g)
    if not top_open: C.add('picker', "'No live top-grade setups' note", 'No live top-grade setups right now.' in pg['initial']['pnone'], True, group=g)
    if not forming_sorted: C.add('picker', "'Nothing forming today' note", 'Nothing forming today.' in pg['initial']['pnone'], True, group=g)
    best_sid = (topf[0]['sid'] if topf else forming_sorted[0]['sid']) if forming_sorted else None
    # ----- cards + charts
    def as_x(kind, o):
        if kind == 'open': return dict(o, asset=o['s']['asset'], tf=o['s']['tf'], chart=o['s']['chart'])
        if kind == 'forming': return dict(o, asset=o['f']['asset'], tf=o['f']['tf'], chart=o['f']['chart'])
        return dict(o, asset='ETH', tf='2D', chart='ETH 2D', sid='example')
    todo = [('open', as_x('open', o)) for o in top_open] + [('forming', as_x('forming', c)) for c in forming_sorted] + ([('example', as_x('example', mine['example']))] if mine['example'] else [])
    if not mine['example']:
        d = pg['sel'].get('example')
        C.add('Now card example', "'Example unavailable' when the feed has no example card", d is not None and 'Example unavailable' in d['card']['text'] and "worked example isn't in the latest data" in d['card']['text'], True, group='8 Now card (example)')
        C.add('Chart example', "'Chart data unavailable' when the feed has no example card", d is not None and any('Chart data unavailable' in (e.get('text') or '') for e in d['chart']['svg']), True, group='8 Chart (example)')
    # the card behind the example switch when nothing is live or forming
    if not top_open and not forming_sorted:
        q = pg['switch_off']; g = '8 Now card (no setup)'
        on = S.gate(S.today)
        y1 = gen.year - 1; nA = sum(1 for x in P if x['grade'] == 'A+' and 2020 <= x['d0'].year <= y1)
        per = f"Top-grade setups come about {L.rhaz(nA / (y1 - 2020 + 1))} times a year (2020 to {y1} average; bear years, when the market filter is off, are included)." if nA and y1 >= 2020 else ''
        want = ("The market filter is on. Nothing at the top grade is forming or confirmed today. " + per).strip() if on else "The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year."
        C.add('Now card (no setup)', 'state', [h for h in q['head']], ['BTC · ETH', 'No setup right now'], group=g)
        C.add('Now card (no setup)', 'text', q['empty'], "Waiting for the next one " + want + " You'll get a push alert the moment one confirms.", group=g)
        C.add('Now card (no setup)', 'boot shows the example, not the quiet card (feed ok, not stale)', pg['page']['previewChecked'], bool(mine['example']) or True, group=g)
    for kind, x in todo:
        sid = x['sid']; d = pg['sel'].get(sid)
        g = f'8 Now card ({kind})'; loc = f'Now card {sid}'
        C.add(loc, 'rendered', d is not None, True, group=g)
        if d is None: continue
        mi = ex_miss if kind == 'example' else misses.get((x['asset'], x['grade']))
        cmp_now(C, loc, d['card'], exp_card(kind, x, mi, best_sid), g)
        if kind == 'open' and x['status'] != 'lost' and x['edge'] not in (None, 0):
            day_ = S.day[x['asset']]; ks_ = x['pr']['ks']; e_ = x['s']['entry']
            fell = bool(ks_) and min(day_.l[k] for k in ks_) <= e_ * (1 + x['edge'] / 100)
            C.add(loc, "'On track' sentence: 'It has not fallen to its edge level' is true", 'It has not fallen to its edge level' in d['card']['head'][3] and fell, False, group='9 on-track wording',
                  cause=f"it rose 10% first, then fell to {x['pr']['worst_so_far_pct']}% (edge level {x['edge']}%): status intact by rule, but the sentence is false")
        if kind == 'open':
            C.add(loc, 'edge-lost card dimmed / not in live colour', (d['card']['frameColor'], d['card']['bigOpacity']), ('var(--fade)', '0.5') if x['status'] == 'lost' else ('var(--live)', ''), group=g)
        # --- chart
        ch = d['chart']; g = f'8 Chart ({kind})'; loc = f'Chart {sid}'
        f = x['figs']
        if kind == 'example':
            exj = json.load(open(f'{S.root}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
            raw = {b.t[i]: i for i in range(S.ch[('ETH', '2D')].b.n) for b in [S.ch[('ETH', '2D')].b]}
            rb = list(csv.DictReader(open(f'{S.root}/data/ETH_2D.csv'))); rawrow = {int(float(r['time'])): r for r in rb}
            cutoff = dt.datetime.combine(S.today - dt.timedelta(days=2), dt.time(), dt.timezone.utc).timestamp()
            okbars = all(b['t'] > cutoff or (b['t'] in rawrow) and all(abs(float(rawrow[b['t']][k2]) - b[k1]) < 1e-9 for k1, k2 in (('o', 'open'), ('h', 'high'), ('l', 'low'), ('c', 'close'))) for b in exj['bars'])
            C.add(loc, f"example chart file: all {len(exj['bars'])} bars equal the raw ETH 2D candles", okbars, True, group=g)
            s = x['s']; bars = [dict(t=b['t'], d=L.udate(b['t']), o=b['o'], h=b['h'], l=b['l'], c=b['c']) for b in exj['bars']]
            E_idx = next(i for i, b in enumerate(bars) if b['d'] == s['cdate'])
            C.add(loc, 'example file entry_index = the confirmation bar', exj['entry_index'], E_idx, group=g)
            C.add(loc, 'example file entry_close', exj['entry_close'], L.rhaz(s['entry'], 2), group=g)
            entry = s['entry']; d0 = s['d0']
            C.add(loc, 'title', ch['title'], 'ETH · 2-day · example: past confirmed setup', group=g)
            C.add(loc, 'subtitle', ch['sub'], f"Confirmed {date_long(d0)} · entry close {money(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them. The shaded zones are the next 60 days, as the odds draw them.", group=g)
            C.add(loc, 'toggle shown, At the alert pressed', (ch['toggleHidden'], ch['alertPressed'], ch['hapPressed']), (False, 'true', 'false'), group=g)
            geo = chart_checks(C, loc + ' [At the alert]', S, ch, bars, E_idx, d0, entry, f, '2D', 'example', g, n_drawn=E_idx + 1, known_upto=E_idx)
            C.add(loc + ' [At the alert]', "no outcome shown ('This one' / later candles)", any('This one' in (e.get('text') or '') for e in ch['svg']), False, group=g)
            side_checks(C, loc + ' [At the alert]', ch['side'], x, entry, kind, g)
            C.add(loc + ' [At the alert]', 'side: second box says this is all a member had', 'This is all a member had at the alert' in ch['side'][1]['text'], True, group=g)
            n, days = mine['paths']['example']
            cloud_checks(C, loc + ' [At the alert]', ch, n, days, f'ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {n}', g)
            C.add(loc + ' [At the alert]', "cloud: no 'this signal' path", len([e for e in ch['cloud'] if e['tag'] == 'polyline']), 1, group=g)
            # --- what happened
            hp = d['chart_happened']; g2 = '8 Chart (example, What happened)'; loc2 = loc + ' [What happened]'
            geo = chart_checks(C, loc2, S, hp, bars, E_idx, d0, entry, f, '2D', 'example', g2, n_drawn=len(bars), known_upto=None)
            day = S.day['ETH']; m = s['m']
            hi_k = max(m['ks'], key=lambda k: (day.h[k], -k)); lo_k = min(m['ks'], key=lambda k: (day.l[k], k))
            def bar_days(dd):   # the 2D bar holding that calendar day, as day numbers from entry
                i = next(i for i, b in enumerate(bars) if b['d'] <= dd and (i + 1 == len(bars) or bars[i + 1]['d'] > dd))
                a = (bars[i]['d'] - d0).days; b2 = ((bars[i + 1]['d'] if i + 1 < len(bars) else L.next_open(bars[i]['d'], 2)) - d0).days - 1
                return a, min(60, b2), i
            texts = [e['text'] for e in hp['svg'] if e['tag'] == 'text' and e['text'].startswith('This one')]
            ha, hb, hidx = bar_days(day.d[hi_k]); la, lb, lidx = bar_days(day.d[lo_k])
            dtx = lambda a, b: f'days {a}–{b}' if b > a else f'day {a}'
            C.add(loc2, "'This one' high label", texts[0] if texts else None, f"This one: {money(day.h[hi_k])} · {pct((day.h[hi_k] / entry - 1) * 100)} · {dtx(ha, hb)}", group=g2)
            C.add(loc2, "'This one' low label", texts[1] if len(texts) > 1 else None, f"This one: {money(day.l[lo_k])} · {pct((day.l[lo_k] / entry - 1) * 100)} · {dtx(la, lb)}", group=g2)
            C.add(loc2, 'high label: the actual day is inside the stated days', ha <= m['dpk'] <= hb, True, group=g2)
            C.add(loc2, 'low label: the actual day is inside the stated days', la <= m['ddday'] <= lb, True, group=g2)
            circ = [e for e in hp['svg'] if e['tag'] == 'circle']
            C.add(loc2, 'high circle on its bar', geo['slot_of'](circ[0]['cx'])[0] if circ else None, hidx, group=g2)
            C.add(loc2, 'low circle on its bar', geo['slot_of'](circ[1]['cx'])[0] if len(circ) > 1 else None, lidx, group=g2)
            C.add(loc2, 'high circle price', round(geo['price_at'](circ[0]['cy']), 2), round(day.h[hi_k], 2), tol=max(geo['ptol'], 0.01), group=g2)
            C.add(loc2, 'low circle price', round(geo['price_at'](circ[1]['cy']), 2), round(day.l[lo_k], 2), tol=max(geo['ptol'], 0.01), group=g2)
            side_checks(C, loc2, hp['side'], x, entry, kind, g2)
            c10 = day.c[day.pos[d0 + dt.timedelta(days=10)]]; c60 = day.c[day.pos[d0 + dt.timedelta(days=60)]]
            hi = max(day.h[k] for k in m['ks']); lo = min(day.l[k] for k in m['ks'])
            want = [['Reached +10% / +20%', f"{'Yes' if hi >= entry * 1.1 else 'No'} / {'Yes' if hi >= entry * 1.2 else 'No'}"],
                    ['Best price', f"{pct(m['up'])}, days {ha}–{hb}"], ['Deepest drop', f"{pct(m['dd'])}, days {la}–{lb}"],
                    ['Day 10 check', f"{'Red' if c10 < entry else 'Green'}, {pct((c10 / entry - 1) * 100)}"], ['Price on day 60', pct(m['ret'])]]
            for sh, w in zip(hp['side'][1]['kv'], want):
                C.add(loc2, 'what this one did: ' + w[0], sh, w, group=g2)
            C.add(loc2, 'what this one did: rows', len(hp['side'][1]['kv']), 5, group=g2)
            # agrees with the Past signals row for the same signal
            pl = cloud_checks(C, loc2, hp, n, days, f'ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {n}', g2)
            C.add(loc2, "cloud: 'this signal' path drawn", len(pl), 2, group=g2)
            if len(pl) == 2:
                pts = [tuple(float(v) for v in p.split(',')) for p in pl[1]['points'].split()]
                X = lambda dd: 20 + 940 * dd / 60; Y = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
                wantp = [(X(0), Y(0))] + [(X(k), Y((day.c[day.pos[d0 + dt.timedelta(days=k)]] / entry - 1) * 100)) for k in range(2, 61, 2)]
                C.add(loc2, "cloud: 'this signal' path = daily closes on days 2,4..60", len(pts) == len(wantp) and all(abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6 for a, b in zip(pts, wantp)), True, group=g2)
            C.add(loc2, 'legend names this signal', 'this signal' in hp['cloudNote'], True, group=g2)
            # back to At the alert: identical to the first render
            C.add(loc, 'At the alert again equals first render (no outcome leaks)', d['chart_alert_again']['svg'] == ch['svg'], True, group=g)
            continue
        a, tf = x['asset'], x['tf']; bars = raw_bars(S, a, tf)
        served = [dict(t=int(float(r['time'])), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(f'{S.root}/datasets/candles_{a.lower()}_{tf.lower()}.csv'))]
        C.add(loc, 'served candle file = last 70 raw bars', served == [{k: b[k] for k in ('t', 'o', 'h', 'l', 'c')} for b in bars], True, group=g)
        C.add(loc, 'toggle hidden for a live/forming setup', ch['toggleHidden'], True, group=g)
        if kind == 'open':
            s, pr = x['s'], x['pr']; entry = s['entry']; d0 = s['d0']
            E_idx = next(i for i, b in enumerate(bars) if b['d'] == s['cdate'])
            C.add(loc, 'title', ch['title'], f"{a} · {tf} · live setup, day {pr['days_elapsed']} of 60", group=g)
            C.add(loc, 'subtitle', ch['sub'], f"Confirmed {date_long(d0)} · entry close {money(entry)}. Zones use this setup's own card ({x['text']}). The shaded zones are the next 60 days, as the odds draw them.", group=g)
            geo = chart_checks(C, loc, S, ch, bars, E_idx, d0, entry, f, tf, 'open', g, n_drawn=len(bars))
            side_checks(C, loc, ch['side'], x, entry, kind, g)
            want = [['Best so far', pct(pr['best_so_far_pct'])], ['Worst so far', pct(pr['worst_so_far_pct'])], ['Day 10', 'not yet' if pr['day10_pct'] is None else pct(pr['day10_pct'])]]
            C.add(loc, 'live box title', ch['side'][1]['text'].lower().startswith(f"live: day {pr['days_elapsed']} of 60"), True, group=g, cause=ch['side'][1]['text'][:60])
            for sh, w in zip(ch['side'][1]['kv'], want):
                C.add(loc, 'live box: ' + w[0], sh, w, group=g)
            n, days = mine['paths'].get(a, (0, []))
            cloud_checks(C, loc, ch, n, days, f'Every past {a} top-grade signal, n {n}', g, not_top=x['grade'] != 'A+')
        else:
            fm = x['f']; entry = L.rhaz(fm['price'], 2); d0 = fm['confirms']
            E_idx = len(bars) - 1
            C.add(loc, 'title', ch['title'], f"{a} · {tf} · {'setup forming' if x['grade'] == 'A+' else 'forming, not top grade'}", group=g)
            C.add(loc, 'subtitle', ch['sub'], f"Low {date_long(fm['low_day'])} · confirms {date_long(d0)} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them.", group=g)
            geo = chart_checks(C, loc, S, ch, bars, E_idx, d0, entry, f, tf, 'forming', g, n_drawn=len(bars))
            side_checks(C, loc, ch['side'], x, entry, kind, g)
            C.add(loc, 'forming box', ch['side'][1]['text'], f"Still forming. It confirms only if it holds through {date_long(d0)}, and it can vanish before then." + ('' if x['grade'] == 'A+' else " It isn't top grade, so no alert goes out for it."), group=g)
            # low marker
            day = S.day[a]; lowp = day.l[day.pos[fm['low_day']]]
            lt = [e for e in ch['svg'] if e['tag'] == 'text' and e['text'].startswith('Low ')]
            C.add(loc, 'low marker label', [e['text'] for e in lt], [f"Low {date_long(fm['low_day'])} · {money(lowp)}"], group=g)
            circ = [e for e in ch['svg'] if e['tag'] == 'circle']
            ti_idx = next(i for i, b in enumerate(bars) if b['d'] == fm['tdate'])
            C.add(loc, 'low marker on the trough bar', geo['slot_of'](circ[0]['cx'])[0] if circ else None, ti_idx, group=g)
            C.add(loc, 'low marker price', round(geo['price_at'](circ[0]['cy']), 2) if circ else None, round(lowp, 2), tol=max(geo['ptol'], 0.01), group=g)
            n, days = mine['paths'].get(a, (0, []))
            cloud_checks(C, loc, ch, n, days, f'Every past {a} top-grade signal, n {n}', g, not_top=x['grade'] != 'A+')
    # ----- initial selection renders one of the selectable setups (layout choice which)
    # ----- Previous signals column
    g = '8 Previous signals'
    intact = [o for o in top_open if o['status'] != 'lost']; fading = [o for o in top_open if o['status'] == 'lost']
    mini = lambda o: (o['s']['chart'], f"Day {o['pr']['days_elapsed']} of 60 · best {pct(o['pr']['best_so_far_pct'])} · worst {pct(o['pr']['worst_so_far_pct'])}")
    shown_int = [(r['name'], r['sub'], r['badge']) for r in pg['page']['prevIntact'] if r['name']]
    C.add('Previous signals', 'Edge intact list', shown_int, [mini(o) + ('On track',) for o in intact], group=g)
    if not intact: C.add('Previous signals', "'none intact' note", pg['page']['prevIntact'][0]['text'], 'No open top-grade setup with its edge intact.', group=g)
    A = [x for x in P if x['grade'] == 'A+']
    order = {(r['chart'], r['entry']): i for i, r in enumerate(S.ledger)}
    recent = sorted(A, key=lambda x: (-x['d0'].toordinal(), order[(x['chart'], str(x['d0']))]))[:5]
    r6 = lambda v: L.rhaz(v, 6)
    want = [mini(o) + ('Edge lost',) for o in fading] + [(x['chart'], f"{date_long(x['d0'])} · best {pct(r6(x['m']['up']))} · worst {pct(r6(x['m']['dd']))}",
            'Reached +20%' if x['m']['up'] >= 20 else 'Rose 10%' if x['m']['up'] >= 10 else 'Missed') for x in recent]
    shown = [(r['name'], r['sub'], r['badge']) for r in pg['page']['prevClosed']]
    C.add('Previous signals', 'Edge lost or closed: row count', len(shown), len(want), group=g)
    for sh, w in zip(shown, want):
        C.add(f'Previous signals {w[0]} {w[1][:11]}', 'row (chart, figures, badge)', sh, w, group=g)
    # ----- Past signals tab
    for asset in ('all', 'ETH', 'BTC'):
        g = f'8 Past signals tab ({asset})'; rec = pg['record'][asset]
        rows = sorted([x for x in A if asset == 'all' or x['asset'] == asset], key=lambda x: (-x['d0'].toordinal(), order[(x['chart'], str(x['d0']))]))
        C.add(f'Past signals {asset}', 'count line', rec['count'], f"{len(rows)} signals · {sum(not x['m']['up'] >= 10 for x in rows)} missed +10%", group=g)
        C.add(f'Past signals {asset}', 'rows', len(rec['rows']), len(rows), group=g)
        C.add(f'Past signals {asset}', 'column heads', rec['head'], ['CONFIRMED', 'CHART', 'ENTRY CLOSE', 'ROSE 10%', 'REACHED +20%', 'BEST', 'DEEPEST DROP', 'DAY 60', 'HIGH ON DAY'] if rec['head'] and rec['head'][0].isupper() else ['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'], group=g)
        for sh, x in zip(rec['rows'], rows):
            m = x['m']; loc = f"Past signals {asset} {x['chart']} {x['d0']}"
            want = [date_long(x['d0']), x['chart'], money(x['entry']), 'Yes' if m['up'] >= 10 else 'No', 'Yes' if m['up'] >= 20 else 'No', pct(r6(m['up'])), pct(r6(m['dd'])), pct(r6(m['ret'])), str(m['dpk'])]
            for lab, a_, b_ in zip(('Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'), sh, want):
                C.add(loc, lab, a_, b_, group=g)
        # summary boxes
        assets = [a3 for a3 in (['ETH', 'BTC'] if asset == 'all' else [asset]) if any(x['asset'] == a3 for x in A)]
        C.add(f'Past signals {asset}', 'summary boxes', len(rec['sum']), len(assets), group=g)
        for box, a2 in zip(rec['sum'], assets):
            G = [x for x in A if x['asset'] == a2]; n = len(G); mi = misses[(a2, 'A+')]
            if not n: continue
            want = [[a2, f'{n} signals'], ['Rose 10% in 60 days', f"{L.rhaz(100 * sum(x['m']['up'] >= 10 for x in G) / n)}%"], ['Reached +20% in 60 days', f"{L.rhaz(100 * sum(x['m']['up'] >= 20 for x in G) / n)}%"],
                    ['Rose 10%, never fell 25.3%', f"{L.rhaz(100 * sum(x['m']['up'] >= 10 and x['m']['dd'] > -25.3 for x in G) / n)}%"], ['Median deepest dip', pct(L.rhaz(st.median(x['m']['dd'] for x in G), 1))],
                    ['Misses: median best price', pct(mi['median_peak_pct'])]]
            for sh, w in zip(box, want):
                C.add(f'Past signals {asset} summary {a2}', w[0], sh, w, group=g)
            C.add(f'Past signals {asset} summary {a2}', 'rows', len(box), len(want), group=g)
        C.add(f'Past signals {asset}', 'footnote: computed, not trades, no track record', 'Computed signals, not trades' in rec['fine'] and 'not a return or a track record' in rec['fine'], True, group=g)
    return S, C, mine, pg

if __name__ == '__main__':
    from collections import Counter
    for name in (sys.argv[1:] or list(STATES)):
        S, C, mine, pg = run(name)
        C.save(f'checks_page_{name}.csv')
        print(name, len(C.rows), 'checks', len(C.bad()), 'bad')
        for k, v in sorted(Counter(r['group'] for r in C.rows).items()): print('   ', k, v)
        for r in C.bad()[:60]: print('  BAD', r['location'], '|', r['label'], '|', str(r['shown'])[:300], '|', str(r['yours'])[:300], '|', r['cause'][:200])
