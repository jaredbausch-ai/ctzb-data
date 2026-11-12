"""Audit 13 part 3b: compare every number the page shows against my own values."""
import csv, datetime as dt, json, os, pickle, re, sys
from decimal import Decimal
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib13 import *
from audit_data import build, share
from audit_cards import sample_for, card_figs, lens_codes, forming_setups
import rec13 as R

OUT = os.path.dirname(os.path.abspath(__file__))
A13 = os.path.join(os.path.dirname(OUT), 'a13')
MON = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
MINUS = '−'


def dlong(d):
    d = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d))
    return f'{d.day} {MON[d.month]} {d.year}'


def dshort(d):
    return f'{d.day:02d} {MON[d.month]}'


def fnum(v, nd=1):
    r = rha(v if isinstance(v, (Decimal, str)) else Decimal(repr(float(v))), nd)
    if r == 0:
        return f'{0:.{nd}f}'
    s = f'{abs(r):.{nd}f}'
    return (MINUS if r < 0 else '') + s


def fpct(v, nd=1, sign=True):
    if v is None:
        return 'n/a'
    r = rha(v if isinstance(v, (Decimal, str)) else Decimal(repr(float(v))), nd)
    return ('+' if sign and r > 0 else '') + fnum(v, nd) + '%'


def money(v):
    if v is None:
        return 'n/a'
    r = rha(v if isinstance(v, (Decimal, str)) else Decimal(repr(float(v))), 2)
    return f'${r:,.2f}'


def D6(x):
    return Decimal(repr(float(x)))


def price_from(entry, pct6):
    return Decimal(repr(float(entry))) * (1 + D6(pct6) / 100)


def ws(s):
    return re.sub(r'\s+', ' ', s or '').strip()


class Chk:
    def __init__(self, st, loc):
        self.st, self.loc = st, loc

    def __call__(self, label, shown, yours, cause=''):
        return R.add(self.st, self.loc, label, ws(shown) if isinstance(shown, str) else shown,
                     ws(yours) if isinstance(yours, str) else yours, cause or label)


# --------------------------------------------------------------------------- card
def expected_card(M, kind, feedc, mine, misses, extra):
    """kind: open / forming / example. Returns dict of expected display strings."""
    f = mine['f']; edge = mine['edge']
    a, tf = feedc['asset'], feedc['timeframe']
    E = {}
    E['where'] = f'{a} · {tf} chart' + (' · example' if kind == 'example' else '')
    E['state'] = {'open': 'Live setup', 'forming': 'Setup forming', 'example': 'Confirmed setup'}[kind]
    if kind == 'open':
        o = extra
        E['line'] = (f"Confirmed {dlong(o['d0'])} · entry close {money(o['entry'])} · day {o['days']} of 60 · "
                     f"best so far {fpct(o['best_mine'])} · worst {fpct(o['worst_mine'])}")
    elif kind == 'forming':
        x = extra
        E['line'] = f"Low {dlong(x['lowday'])} · confirms {dlong(x['d0'])}" + (f" if it closes above {money(rha_bin(x['kill'], 2))}" if x['kill'] is not None else '')
    else:
        E['line'] = f"Example: confirmed {dlong('2024-09-22')} · entry close {money(extra['entry'])}"
    E['big'] = f"{f['r10']}%"
    E['surv'] = f"{f['surv']}% did it without ever falling 25.3%"
    E['from'] = f"from {mine['sample']} · every figure covers the 60 days after entry"
    E['high'] = fpct(D6(f['best6'])); E['drop'] = fpct(D6(f['dd6'])); E['dip'] = fpct(D6(f['dpk6']))
    E['edge'] = 'Below the 70% bar from entry' if edge == 0 else ('Holds at every level' if edge is None else f"{fpct(edge, 0)} before it rises 10%")
    mi = misses
    E['miss'] = f"{mi['up_first']} of {mi['misses']} · median best {fpct(mi['median_peak_pct'])}"
    word = 'top-grade' if feedc['grade'] == 'A+' else 'same-grade'
    E['tiles'] = [
        ['Dip before the high, from entry', E['dip']], ['High lands around', f"Day {f['dhigh']}"],
        [f"Reached +20% within 60 days · n {f['n']}", f"{f['r20']}%"], [f"Touched {MINUS}30% within 60 days · n {f['n']}", f"{f['t30']}%"],
        ['Typical high', E['high']], ['Deepest dip lands around', f"Day {f['dlow']}"],
        [f"Typical worst drop, misses · {mi['misses']} misses of all {mi['signals']} {a} {word} signals", fpct(mi['median_worst_drop_pct'])],
        [f"Typical change by day 60, misses · {mi['misses']} misses of all {mi['signals']} {a} {word} signals", fpct(mi['median_day60_pct'])]]
    lad = [dict(t=f"From entry n {f['n']}", v=f"{f['lad'][0]['ok']}%", gone=f['lad'][0]['exf'] < 70)]
    for k in (5, 10, 15, 20):
        l = f['lad'][k]
        lad.append(dict(t=f"Falls {k}% first n {l['n']}", v='n/a' if l['n'] == 0 else f"{l['ok']}%", gone=(l['exf'] is not None and l['exf'] < 70)))
    E['ladder'] = lad
    E['eras'] = [dict(t=f"Before 2022 n {f['nOld']}", v=f"{f['sOld']}%" if f['sOld'] is not None else 'n/a%'),
                 dict(t=f"Since 2022 n {f['nNew']}", v=f"{f['sNew']}%" if f['sNew'] is not None else 'n/a%')]
    E['pool'] = f"all {mi['signals']} {a} signals of this grade" if (kind == 'forming' and feedc['grade'] != 'A+') else None
    return E


def check_card_view(st, sel, cv, E, kind, below, best_id):
    C = Chk(st, f'page Now card {sel}')
    C('header: chart', cv['where'].upper(), E['where'].upper())
    C('header: state', cv['state'], E['state'])
    C('header: line', cv['head_smalls'][0], E['line'], 'card line')
    if kind == 'forming':
        note = (('Best setup forming today.' if best_id == sel else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.") if below \
            else 'Not confirmed yet. It can still vanish before it confirms.'
        C('header: forming note', cv['head_smalls'][1] if len(cv['head_smalls']) > 1 else '', note)
    else:
        C('header: no forming note', len(cv['head_smalls']), 1)
    C('big number (rose 10% within 60 days)', cv['big'], E['big'])
    C('big number caption', cv['odds_lines'][1], 'rose 10% within 60 days')
    C('line under big number', cv['odds_lines'][2], E['surv'])
    C('sample line', cv['odds_lines'][3], E['from'])
    st_ = {k: v for k, v in cv['stats']}
    C('Typical high', st_.get('Typical high'), E['high'])
    C('Typical drop from entry', st_.get('Typical drop from entry'), E['drop'])
    C('Edge gone below', st_.get('Edge gone below'), E['edge'])
    C('If it misses: went above entry', st_.get('If it misses: went above entry'), E['miss'])
    C('misses pool line', cv['pool'], E['pool'])
    C('Lead trader marker', cv['marker'], 'Lead trader: unavailable')
    C('tile count', len(cv['tiles']), 8)
    for (t, v), (et, ev) in zip(cv['tiles'], E['tiles']):
        C(f'tile title "{et}"', t, et)
        C(f'tile value "{et}"', v, ev)
    C('ladder title', cv['ladder_lbl'].upper(), 'WHERE THE ODDS FADE · THIS SETUP')
    C('ladder rows', len(cv['ladder']), 5)
    for r, e in zip(cv['ladder'], E['ladder']):
        C(f'ladder "{e["t"]}" label', r['t'], e['t'])
        C(f'ladder "{e["t"]}" value', r['v'], e['v'])
        C(f'ladder "{e["t"]}" colour (below 70% on the exact share)', r['gone'], e['gone'])
        C(f'ladder "{e["t"]}" bar width', r['w'], (e['v'] if e['v'] != 'n/a' else '0%'))
    for r, e in zip(cv['eras'], E['eras']):
        C(f'era "{e["t"]}" label', r['t'], e['t'])
        C(f'era "{e["t"]}" value', r['v'], e['v'])
    C('frame colour', cv['frameC'], 'var(--fade)' if below else 'var(--live)')


# --------------------------------------------------------------------------- chart
def chart_geometry(view_chart):
    els = view_chart['els']
    wicks = [e for e in els if e['tag'] == 'line' and e['style'] and ('var(--high)' in e['style'] or 'var(--drop)' in e['style'])
             and e['a']['x1'] == e['a']['x2'] and not (float(e['a']['y1']) == 24 and float(e['a']['y2']) == 480)
             and e['a'].get('stroke-width') == '1.5']
    xs = [float(w['a']['x1']) for w in wicks]
    slot = xs[1] - xs[0] if len(xs) > 1 else None
    return wicks, xs, slot


def idx_of(x, slot, L=20):
    return round((x - L - slot / 2) / slot)


def fit_y(els):
    pts = []
    for e in els:
        if e['tag'] == 'text' and e['text'].startswith('$') and e['a'].get('x') == '968':
            p = float(e['text'][1:].replace(',', ''))
            pts.append((p, float(e['a']['y']) - 5))
    (p1, y1), (p2, y2) = pts[0], pts[-1]
    a = (y2 - y1) / (p2 - p1); b = y1 - a * p1
    return (lambda p: a * p + b), (lambda y: (y - b) / a), pts


def slot_dates(bars_dates, tf, upto):
    """bar open dates of the page's slots: the candles, then future bars by the calendar rule."""
    opens = list(bars_dates)
    while opens[-1] <= upto:
        opens.append(next_open(opens[-1], tf))
    return opens


def span_of(opens, i, tf):
    s = opens[i]
    e = (opens[i + 1] if i + 1 < len(opens) else next_open(s, tf)) - dt.timedelta(days=1)
    return s, e


def check_chart(st, sel, vc, M, kind, feedc, mine, extra, mode='alert', exjson=None):
    C = Chk(st, f'page Chart {sel}' + (f' ({mode})' if kind == 'example' else ''))
    f = mine['f']; edge = mine['edge']
    a, tf = feedc['asset'], feedc['timeframe']
    els = vc['els']
    texts = [e for e in els if e['tag'] == 'text']
    T = lambda pfx: [e for e in texts if e['text'].startswith(pfx)]
    if kind == 'example':
        bars = exjson['bars']; E_idx = exjson['entry_index']
        entry = extra['entry']; entry_day = dt.date(2024, 9, 22)
        bdates = [dt.datetime.fromtimestamp(b['t'], UTC).date() for b in bars]
        opens = bdates
    else:
        cs = list(csv.DictReader(open(os.path.join(M.S, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv'))))
        bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in cs]
        bdates = [dt.datetime.fromtimestamp(b['t'], UTC).date() for b in bars]
        entry_day = dt.date.fromisoformat(extra['d0'])
        opens = slot_dates(bdates, tf, entry_day + dt.timedelta(days=61))
        entry = extra['entry'] if kind == 'open' else extra['price']
    # candles dataset = the chart's own bars (last 70)
    if kind != 'example':
        b = M.bars[(a, tf)]
        n = len(b['date'])
        ok = len(bars) == min(70, n) and all(bdates[i] == b['date'][n - len(bars) + i] and bars[i]['h'] == b['rawh'][n - len(bars) + i]
                                               and bars[i]['l'] == b['rawl'][n - len(bars) + i] and bars[i]['c'] == b['c'][n - len(bars) + i]
                                               and bars[i]['o'] == b['o'][n - len(bars) + i] for i in range(len(bars)))
        C('candles served = the chart\'s last 70 bars', 'yes' if ok else 'no', 'yes', 'candle data')
    wicks, xs, slot = chart_geometry(vc)
    nS = len(opens)
    # candles drawn
    exp_n = (E_idx + 1) if (kind == 'example' and mode == 'alert') else len(bars)
    C('candles drawn', len(wicks), exp_n, 'candles at the alert must stop at the entry bar' if kind == 'example' else 'candle count')
    C('slot width', round(slot, 9), round((960 - 20) / nS, 9), 'slot count (bars + future bars to day 61)')
    Y, P, grid = fit_y(els)
    # every candle at its date and price
    bad = 0
    for k, w in enumerate(wicks):
        i = idx_of(float(w['a']['x1']), slot)
        if i != k or abs(float(w['a']['y1']) - Y(bars[i]['h'])) > 1e-6 or abs(float(w['a']['y2']) - Y(bars[i]['l'])) > 1e-6:
            bad += 1
    C('candles at their dates and prices', bad, 0, 'candle placement')
    # y-axis scale (layout rule; checks that "at the alert" uses only what was known)
    shown = bars[:E_idx + 1] if (kind == 'example' and mode == 'alert') else bars
    hiL = entry * (1 + f['best6'] / 100); drL = entry * (1 + f['dd6'] / 100)
    lo = min(min(b_['l'] for b_ in shown), drL, entry * 0.8) * 0.95; hi = max(max(b_['h'] for b_ in shown), hiL) * 1.07
    C('y-axis low/high from what is shown', f"{round(Y(lo), 6)}/{round(Y(hi), 6)}", f"{round(480.0, 6)}/{round(24.0, 6)}", 'axis scaling')
    if kind == 'example' and mode == 'alert':
        lo2 = min(min(b_['l'] for b_ in bars), drL, entry * 0.8) * 0.95; hi2 = max(max(b_['h'] for b_ in bars), hiL) * 1.07
        R.add(st, f'page Chart {sel} (alert)', 'note: full-history scale would differ', 'yes' if (lo2, hi2) != (lo, hi) else 'no', 'yes' if (lo2, hi2) != (lo, hi) else 'no')
    # level lines and price tags
    lines = [e for e in els if e['tag'] == 'line' and e['a']['y1'] == e['a']['y2'] and float(e['a']['x1']) != 20]
    def line_y(col, dash=''):
        c = [e for e in lines if e['style'] and f'var(--{col})' in e['style'] and e['a'].get('stroke-dasharray', '') == dash]
        return [float(e['a']['y1']) for e in c]
    t20 = entry * 1.1
    lv = {'high': (price_from(entry, f['best6']), 'high', ''), 't20': (Decimal(repr(float(entry))) * Decimal('1.1'), 'text', '6 5'),
          'entry': (Decimal(repr(float(entry))), 'soft', ''), 'drop': (price_from(entry, f['dd6']), 'drop', '')}
    if edge not in (None, 0):
        lv['edge'] = (Decimal(repr(float(entry))) * (1 + Decimal(edge) / 100), 'fade-2', '8 4')
    for k, (p, col, dash) in lv.items():
        ys = line_y(col, dash)
        C(f'{k} line at its price', 'yes' if any(abs(y - Y(float(p))) < 1e-6 for y in ys) else 'no', 'yes', 'line position')
    tags = [e['text'] for e in texts if e['a'].get('x') == '1018']
    C('price tags', ' | '.join(sorted(tags)), ' | '.join(sorted(money(lv[k][0]) for k in ('high', 't20', 'entry', 'drop'))), 'price built from the exact percentage')
    C('label Typical high', next((e['text'] for e in T('Typical high')), None), f"Typical high {fpct(D6(f['best6']))}")
    C('label +10%', next((e['text'] for e in T('+10% ·')), None), f"+10% · {f['r10']}% of past signals got here")
    C('label Typical drop', next((e['text'] for e in T('Typical drop')), None), f"Typical drop {fpct(D6(f['dd6']))}")
    eg = next((e['text'] for e in T('Edge gone below')), None)
    C('label Edge gone below', eg, None if edge in (None, 0) else f"Edge gone below {money(lv['edge'][0])} ({fpct(edge, 0)}, before +10%)")
    # ladder zones
    zl = [e['text'] for e in texts if e['style'] and 'font-weight' not in (e['a']) and False]
    zones = [e for e in els if e['tag'] == 'rect' and e['a'].get('opacity') == '0.24']
    ztexts = [e['text'] for e in texts if e['a'].get('text-anchor') == 'middle' and e['a'].get('font-weight') == '700' and e['text'].endswith('%') or (e['tag'] == 'text' and e['text'] == 'n/a')]
    expz = [f"{f['lad'][0]['ok']}%"] + [('n/a' if f['lad'][k]['n'] == 0 else f"{f['lad'][k]['ok']}%") for k in (5, 10, 15)]
    C('ladder zone labels', ' | '.join(ztexts), ' | '.join(expz))
    for z, (a1, b1) in zip(zones, [(0, -5), (-5, -10), (-10, -15), (-15, -20)]):
        C(f'ladder zone {a1}..{b1} top at its price', round(float(z['a']['y']), 6), round(Y(entry * (1 + a1 / 100)), 6), 'zone position')
    # vertical lines by date
    def vx(pfx):
        e = next((e for e in texts if e['text'].startswith(pfx)), None)
        return None if e is None else float(e['a']['x']) - 6
    def slot_date_check(lab, pfx, day):
        x = vx(pfx)
        if x is None:
            C(f'{lab} present', 'no', 'yes'); return
        i = idx_of(x, slot)
        s, e = span_of(opens, min(i, len(opens) - 1), tf)
        C(f'{lab} on the bar containing {day}', f'{s}..{e}', 'contains' if s <= day <= e else f'{s}..{e}',
          'line not on the bar containing that day') if not (s <= day <= e) else C(f'{lab} on the bar containing {day}', 'ok', 'ok')
        return i
    if kind == 'forming':
        last = len(bars) - 1
        x = vx('Today'); C('"Today" line on the last (open) bar', idx_of(x, slot), last)
        slot_date_check('Confirms line', 'Confirms', entry_day)
        C('Confirms line label', next((e['text'] for e in T('Confirms')), None), f"Confirms {dlong(entry_day)} · entry, day 0") \
            if any(e['text'].startswith('Confirms') for e in texts) else None
    else:
        x = vx('Entry'); i = idx_of(x, slot)
        s, e = span_of(opens, i, tf)
        C('"Entry" line on the bar that closes on the entry date', str(e), str(entry_day))
    slot_date_check(f"High line (day {f['dhigh']})", 'High usually', entry_day + dt.timedelta(days=f['dhigh']))
    C('High line label', next((e['text'] for e in T('High usually')), None), f"High usually ~day {f['dhigh']}")
    slot_date_check('Day 60 line', 'Day 60', entry_day + dt.timedelta(days=60))
    zr = [e for e in els if e['tag'] == 'rect' and e['a'].get('opacity') == '0.07']
    if zr:
        x0 = float(zr[0]['a']['x']); x1 = x0 + float(zr[0]['a']['width'])
        i0 = idx_of(x0, slot); i1 = idx_of(x1, slot)
        s0, e0 = span_of(opens, i0, tf); s1, e1 = span_of(opens, min(i1, len(opens) - 1), tf)
        C('zones start on the entry/confirmation bar', 'ok' if s0 <= entry_day <= e0 else f'{s0}..{e0}', 'ok')
        C('zones end on the day-60 bar', 'ok' if s1 <= entry_day + dt.timedelta(days=60) <= e1 else f'{s1}..{e1}', 'ok')
    # x-axis date labels
    dl = [e for e in texts if e['a'].get('y') == '502']
    badd = sum(1 for e in dl if e['text'] != dshort(opens[idx_of(float(e['a']['x']), slot)]))
    C('x-axis date labels at their bars', badd, 0)
    # low circle (forming)
    if kind == 'forming':
        lowtxt = next((e['text'] for e in T('Low ')), None)
        bt = M.bars[(a, tf)]; ti = extra['ti']
        lowp = bt['l'][ti]
        C('low marker label', lowtxt, f"Low {dlong(extra['lowday'])} · {money(lowp)}")
        circ = [e for e in els if e['tag'] == 'circle']
        if circ:
            i = idx_of(float(circ[0]['a']['cx']), slot)
            C('low marker on the trough bar', str(opens[i]), extra['tdate'])
    if kind == 'example' and mode == 'happened':
        m = extra['m']
        one = [e['text'] for e in T('This one:')]
        def rng(d):
            k = (d + 1) // 2
            return f'days {2 * k - 1}–{2 * k}'
        exp = [f"This one: {money(m['hi'])} · {fpct((m['hi'] / extra['entry'] - 1) * 100)} · {rng(m['dpk'])}",
               f"This one: {money(m['lo'])} · {fpct((m['lo'] / extra['entry'] - 1) * 100)} · {rng(m['ddday'])}"]
        C('"This one" high/low labels', ' | '.join(one), ' | '.join(exp))
    if kind == 'example' and mode == 'alert':
        C('no outcome shown at the alert', len(T('This one')), 0)
    # cloud
    return opens


def check_cloud(st, sel, vc, paths, asset, kind, grade):
    C = Chk(st, f'page Chart {sel} cloud')
    pp = paths
    if kind == 'example':
        C('cloud caption', vc['cloudSub'], f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {pp['signals']}")
    else:
        C('cloud caption', vc['cloudSub'], f"Every past {asset} top-grade signal, n {pp['signals']}")
    last = pp['days'][60]
    note = (f"━ median path █ middle half of outcomes" + (" ━ this signal" if 'this signal' in vc['cloudNote'] else '') +
            f". Day 60: median {fpct(last['median_pct'])}, middle half {fpct(last['q25_pct'])} to {fpct(last['q75_pct'])}. Daily closes.")
    if kind != 'example' and grade != 'A+':
        note += " Top-grade signals only; the selected setup isn't top grade."
    C('cloud note', vc['cloudNote'], note)
    poly = next(e for e in vc['cloud'] if e['tag'] == 'polyline')
    pts = [tuple(map(float, p.split(','))) for p in poly['a']['points'].split()]
    L, R_, T_, B_, P0, P1 = 20, 960, 12, 230, -40, 100
    bad = 0
    for d, (x, y) in enumerate(pts):
        v = max(P0, min(P1, pp['days'][d]['median_pct']))
        if abs(x - (L + (R_ - L) * d / 60)) > 1e-6 or abs(y - (B_ - (v - P0) / (P1 - P0) * (B_ - T_))) > 1e-6:
            bad += 1
    C('cloud median line: 61 points at my medians', f'{len(pts)} points, {bad} off', '61 points, 0 off')
    band = next(e for e in vc['cloud'] if e['tag'] == 'polygon')
    pts = [tuple(map(float, p.split(','))) for p in band['a']['points'].split()]
    exp = [(L + (R_ - L) * d / 60, max(P0, min(P1, pp['days'][d]['q75_pct']))) for d in range(61)] + \
          [(L + (R_ - L) * d / 60, max(P0, min(P1, pp['days'][d]['q25_pct']))) for d in range(60, -1, -1)]
    bad = sum(1 for (x, y), (ex, ev) in zip(pts, exp) if abs(x - ex) > 1e-6 or abs(y - (B_ - (ev - P0) / (P1 - P0) * (B_ - T_))) > 1e-6)
    C('cloud middle-half band: 122 points at my quartiles', f'{len(pts)} points, {bad} off', '122 points, 0 off')


def check_side(st, sel, vc, kind, feedc, mine, extra, mode, o=None):
    C = Chk(st, f'page Chart {sel} side' + (f' ({mode})' if kind == 'example' else ''))
    f = mine['f']; edge = mine['edge']
    entry = extra['entry'] if kind != 'forming' else extra['price']
    kv = {k: v for k, v in vc['sideKV']}
    s0 = vc['side'][0].split('\n')
    C('side: chart and sample', s0[1], f"{feedc['chart']} · from {mine['sample']}" if kind != 'example' else f"{feedc['chart']} · example")
    C('side: big number', s0[2], f"{f['r10']}%")
    C('side: caption', s0[3], f"rose 10% within 60 days, from {f['n']} past signals; {f['surv']}% without ever falling 25.3%")
    C('side: Typical high', kv.get('Typical high'), f"{fpct(D6(f['best6']))} · {money(price_from(entry, f['best6']))}")
    C('side: +10% level', kv.get('+10% level'), money(Decimal(repr(float(entry))) * Decimal('1.1')))
    C('side: Reached +20%', kv.get('Reached +20% within 60 days'), f"{f['r20']}%")
    C('side: Typical drop', kv.get('Typical drop'), f"{fpct(D6(f['dd6']))} · {money(price_from(entry, f['dd6']))}")
    C('side: Edge gone below', kv.get('Edge gone below'), 'below the bar already' if edge == 0 else 'holds at every level' if edge is None
      else f"{money(Decimal(repr(float(entry))) * (1 + Decimal(edge) / 100))} ({fpct(edge, 0)})")
    if kind == 'open':
        C('side: live day', vc['side'][1].split('\n')[0].upper(), f"LIVE: DAY {extra['days']} OF 60")
        C('side: Best so far', kv.get('Best so far'), fpct(extra['best_mine']))
        C('side: Worst so far', kv.get('Worst so far'), fpct(extra['worst_mine']))
        C('side: Day 10', kv.get('Day 10'), 'not yet' if extra['d10_mine'] is None else fpct(extra['d10_mine']))
    if kind == 'forming':
        C('side: stand-in note', s0[-1], "Prices use the latest price (today's bar is still open) as a stand-in for the entry.")
        C('side: forming box', vc['side'][1], f"Still forming. It confirms only if it holds through {dlong(extra['d0'])}, and it can vanish before then. "
          + ("" if feedc['grade'] == 'A+' else "It isn't top grade, so no alert goes out for it."))
    if kind == 'example' and mode == 'happened':
        m = extra['m']; en = extra['entry']
        rng = lambda d: f"days {2 * ((d + 1) // 2) - 1}–{2 * ((d + 1) // 2)}"
        C('side: Reached +10% / +20%', kv.get('Reached +10% / +20%'), f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}")
        C('side: Best price', kv.get('Best price'), f"{fpct((m['hi'] / en - 1) * 100)}, {rng(m['dpk'])}")
        C('side: Deepest drop', kv.get('Deepest drop'), f"{fpct((m['lo'] / en - 1) * 100)}, {rng(m['ddday'])}")
        c10 = m['closes'][m['days'].index(10)]
        C('side: Day 10 check', kv.get('Day 10 check'), f"{'Red' if c10 < en else 'Green'}, {fpct((c10 / en - 1) * 100)}")
        C('side: Price on day 60', kv.get('Price on day 60'), fpct(m['ret']))
    if kind == 'example' and mode == 'alert':
        C('side: at-the-alert box', vc['side'][1], "This is all a member had at the alert: the zones, the +10% level and the timing. Press What happened to see the real path.")
    C('side: lead note', vc['side'][-2], "The lead trader's feed is unavailable right now, so his entries and exits can't be shown.")


def main():
    p1 = pickle.load(open(os.path.join(OUT, 'part1.pkl'), 'rb'))
    p2 = pickle.load(open(os.path.join(OUT, 'part2.pkl'), 'rb'))
    for st in ('replay_0414', 'current'):
        S = os.path.join(A13, st)
        feed = json.load(open(os.path.join(S, 'feed', 'ctzb_feed.json')))
        pg = json.load(open(os.path.join(OUT, f'page_{st}.json')))
        now = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
        M = build(st, now)
        today = M.today
        mine2 = p2[st]; mi = p1[st]['misses']; pa = p1[st]['paths']
        exjson = json.load(open(os.path.join(S, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')))
        # example json vs data
        C = Chk(st, 'example chart data (example_ETH-2D-2024-09-22.json)')
        b2 = M.bars[('ETH', '2D')]
        pos = {d: i for i, d in enumerate(b2['date'])}
        bad = 0
        for bb in exjson['bars']:
            d = dt.datetime.fromtimestamp(bb['t'], UTC).date(); i = pos.get(d)
            if i is None or (bb['o'], bb['h'], bb['l'], bb['c']) != (b2['o'][i], b2['rawh'][i], b2['rawl'][i], b2['c'][i]): bad += 1
        C('bars equal the ETH 2D data', bad, 0)
        ei = exjson['entry_index']; de = dt.datetime.fromtimestamp(exjson['bars'][ei]['t'], UTC).date()
        C('entry bar closes on 2024-09-22', str(bar_span(b2['date'], pos[de], '2D')[1]), '2024-09-22')
        C('entry_close', exjson['entry_close'], rha_bin(mine2['example']['entry'], 2))
        # misc
        misc = pg['misc']
        C = Chk(st, 'page banner/header/footer')
        gen = feed['generated_at']
        C('banner', misc['review'].split('\n')[0], f"Review build. Real pipeline data, scored {dlong(today)} (feed {gen[11:16]} UTC). Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run.")
        C('market filter pill', misc['filter'], f"Market filter: {'on' if M.gate(today) else 'off'}")
        lastclosed = max(d for d in M.day['ETH'].dates if d + dt.timedelta(days=1) <= today)
        C('footer: daily candles closed through', misc['feedState'], f"Daily candles closed through {dlong(lastclosed)} · updated {gen[11:16]} UTC · checks passed")
        C('lead panel', misc['lead'], "The lead trader's feed is unavailable right now. His real entries and exits appear here the moment they fill.")
        C('How to read: posting bar', pg['read']['howBar'], f"{feed['odds_fade']['posting_bar_pct']}% bar")
        # stale note must be absent (clock = generated + 6 min)
        C('no stale-data note', pg['initial']['stale'], None)
        # ---------- picker
        opensA = [o for o in feed['open_signals'] if o['grade'] == 'A+']
        forming = sorted(feed['cards'], key=lambda c: -(c['rose10_within60d_pct'] if c['rose10_within60d_pct'] is not None else -1))
        top = [c for c in forming if c['grade'] == 'A+']
        order = [o['signal_id'] for o in opensA] + [c['signal_id'] for c in top] + [c['signal_id'] for c in forming if c not in top] + ['example']
        C = Chk(st, 'page Now picker')
        C('picker order', ' | '.join(b_['sel'] for b_ in pg['initial']['pickbtns']), ' | '.join(order))
        Fm = {f"{x['a']}-{x['tf']}-{x['d0']}": x for x in forming_setups(M)}
        for btn in pg['initial']['pickbtns']:
            sid = btn['sel']
            if sid == 'example':
                C('example button', btn['txt'], 'Example: ETH 2D, Sep 2024'); continue
            if sid in mine2['open']:
                o = mine2['open'][sid]
                d0 = dt.date.fromisoformat(o['d0']); e = o['entry']; day = M.day[sid[:3]]
                ks = day.window(d0, 60, closed_before=today)
                bm = (max(day.b['h'][j] for j in ks) / e - 1) * 100; wm = (min(day.b['l'][j] for j in ks) / e - 1) * 100
                C(f'button {sid}', btn['txt'], f"{sid[:3]} {sid[4:6]}\nDay {(today - d0).days}\nbest {fpct(bm)} · worst {fpct(wm)}")
            else:
                f = mine2['cards'][sid]['f']; x = Fm[sid]; c = next(c for c in feed['cards'] if c['signal_id'] == sid)
                C(f'button {sid}', btn['txt'], f"{x['a']} {x['tf']}\n{f['r10']}%\nrose 10% in 60 days · n {f['n']} · {'top grade' if c['grade'] == 'A+' else 'not top grade'} · confirms {dlong(x['d0'])}")
        best_id = (top[0]['signal_id'] if top else (forming[0]['signal_id'] if forming else None))
        initial_sel = (opensA[0]['signal_id'] if opensA else best_id)
        C('selected on open', next(b_['sel'] for b_ in pg['initial']['pickbtns'] if b_['pressed'] == 'true'), initial_sel or 'example')
        # ---------- each view
        for sel, v in pg['views'].items():
            if sel == 'example':
                kind = 'example'; feedc = feed['example_card']; mine = mine2['example']
                extra = dict(entry=mine['entry'], m=mine['m'])
                misses = mi['example']; below = False
            elif sel in mine2['open']:
                kind = 'open'; o = next(o for o in feed['open_signals'] if o['signal_id'] == sel)
                feedc = o['card']; mine = mine2['open'][sel]
                d0 = dt.date.fromisoformat(mine['d0']); e = mine['entry']; day = M.day[feedc['asset']]
                ks = day.window(d0, 60, closed_before=today)
                d10 = next(((day.b['c'][j] / e - 1) * 100 for j in ks if (day.dates[j] - d0).days == 10), None)
                extra = dict(d0=mine['d0'], entry=e, days=(today - d0).days, best_mine=(max(day.b['h'][j] for j in ks) / e - 1) * 100,
                             worst_mine=(min(day.b['l'][j] for j in ks) / e - 1) * 100, d10_mine=d10)
                misses = mi[(feedc['asset'], feedc['grade'])]; below = False
            else:
                kind = 'forming'; feedc = next(c for c in feed['cards'] if c['signal_id'] == sel); mine = mine2['cards'][sel]
                extra = dict(Fm[sel]); extra['d0'] = str(extra['d0']); extra['tdate'] = str(extra['tdate']); extra['lowday'] = str(extra['lowday'])
                misses = mi[(feedc['asset'], feedc['grade'])]; below = feedc['grade'] != 'A+'
            E = expected_card(M, kind, feedc, mine, misses, extra)
            check_card_view(st, sel, v['card'], E, kind, below, best_id)
            Cc = Chk(st, f'page Chart {sel}')
            if kind == 'example':
                Cc('title', v['chart']['title'].upper(), 'ETH · 2-DAY · EXAMPLE: PAST CONFIRMED SETUP')
                Cc('subtitle', v['chart']['sub'], f"Confirmed {dlong('2024-09-22')} · entry close {money(extra['entry'])} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them. The shaded zones are the next 60 days, as the odds draw them.")
                Cc('toggle shown', v['chart']['toggleHidden'], False)
                check_chart(st, sel, v['chart'], M, kind, feedc, mine, extra, 'alert', exjson)
                check_chart(st, sel, v['chart_happened'], M, kind, feedc, mine, extra, 'happened', exjson)
                check_side(st, sel, v['chart'], kind, feedc, mine, extra, 'alert')
                check_side(st, sel, v['chart_happened'], kind, feedc, mine, extra, 'happened')
                check_cloud(st, sel, v['chart'], pa['example'], 'ETH', kind, 'A+')
                Cc('happened: cloud has "this signal"', 'this signal' in v['chart_happened']['cloudNote'], True)
                Cc('alert: cloud has no "this signal"', 'this signal' in v['chart']['cloudNote'], False)
                # the example's own path in the cloud (2D closes at days 2..60)
                pl = [e_ for e_ in v['chart_happened']['cloud'] if e_['tag'] == 'polyline']
                pts = [tuple(map(float, p_.split(','))) for p_ in pl[1]['a']['points'].split()]
                m = extra['m']; en = extra['entry']
                expd = [(0, 0.0)] + [(d, (m['closes'][m['days'].index(d)] / en - 1) * 100) for d in range(2, 61, 2)]
                bad = sum(1 for (x, y), (d, val) in zip(pts, expd) if abs(x - (20 + 940 * d / 60)) > 1e-6 or abs(y - (230 - (max(-40, min(100, val)) + 40) / 140 * 218)) > 1e-6)
                Cc('happened: this signal\'s path in the cloud', f'{len(pts)} points, {bad} off', '31 points, 0 off')
                Cc('alert again: no outcome', len([e_ for e_ in v['chart_alert_again']['els'] if e_['tag'] == 'text' and e_['text'].startswith('This one')]), 0)
            else:
                if kind == 'open':
                    Cc('title', v['chart']['title'].upper(), f"{feedc['chart'].replace(' ', ' · ')} · live setup, day {extra['days']} of 60".upper())
                    Cc('subtitle', v['chart']['sub'], f"Confirmed {dlong(extra['d0'])} · entry close {money(extra['entry'])}. Zones use this setup's own card ({mine['sample']}). The shaded zones are the next 60 days, as the odds draw them.")
                else:
                    Cc('title', v['chart']['title'].upper(), f"{feedc['asset']} · {feedc['timeframe']} · {'setup forming' if feedc['grade'] == 'A+' else 'forming, not top grade'}".upper())
                    Cc('subtitle', v['chart']['sub'], f"Low {dlong(extra['lowday'])} · confirms {dlong(extra['d0'])} · price levels drawn from today's price ({money(extra['price'])}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them.")
                Cc('toggle hidden', v['chart']['toggleHidden'], True)
                check_chart(st, sel, v['chart'], M, kind, feedc, mine, extra)
                check_side(st, sel, v['chart'], kind, feedc, mine, extra, 'alert')
                check_cloud(st, sel, v['chart'], pa[feedc['asset']], feedc['asset'], kind, feedc['grade'])
        # example via the switch = the example card
        Chk(st, 'page Now example via switch')('same as the example button', pg['switch_example']['text'], pg['views']['example']['card']['text'])
        # ---------- previous signals
        C = Chk(st, 'page Previous signals')
        intact = [sid for sid in (o['signal_id'] for o in opensA) if mine2['open'][sid]['status'] == 'intact']
        lost = [sid for sid in (o['signal_id'] for o in opensA) if mine2['open'][sid]['status'] == 'lost']
        if not intact:
            C('Edge intact group', ' | '.join(x['txt'] for x in misc['prevIntact']), 'No open top-grade setup with its edge intact.')
        def mini(sid):
            o = mine2['open'][sid]; d0 = dt.date.fromisoformat(o['d0']); e = o['entry']; day = M.day[sid[:3]]
            ks = day.window(d0, 60, closed_before=today)
            return f"{sid[:3]} {sid[4:6]}\nDay {(today - d0).days} of 60 · best {fpct((max(day.b['h'][j] for j in ks) / e - 1) * 100)} · worst {fpct((min(day.b['l'][j] for j in ks) / e - 1) * 100)}"
        exp_int = [mini(s) + '\nOn track' for s in intact]
        if intact:
            C('Edge intact group', ' | '.join(x['txt'] for x in misc['prevIntact']), ' | '.join(exp_int))
        recent = sorted([s for s in M.ledgerset if s['grade'] == 'A+'], key=lambda s: s['d0'], reverse=True)
        # stable order for ties: ledger order within a date
        led_rows = [r for r in csv.DictReader(open(os.path.join(S, 'datasets', 'ledger.csv'))) if r['grade'] == 'A+']
        led_sorted = sorted(led_rows, key=lambda r: r['entry'], reverse=True)[:5]
        mym = {(s['chart'], str(s['d0'])): s for s in M.ledgerset}
        exp_closed = [mini(s) + '\nEdge lost' for s in lost]
        for r in led_sorted:
            s = mym[(r['chart'], r['entry'])]; m = s['m']
            badge = 'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed'
            exp_closed.append(f"{s['chart']}\n{dlong(s['d0'])} · best {fpct(D6(rha_bin(m['up'], 6)))} · worst {fpct(D6(rha_bin(m['dd'], 6)))}\n{badge}")
        C('Edge lost or closed group', ' | '.join(x['txt'] for x in misc['prevClosed']), ' | '.join(exp_closed))
        top5 = sorted(recent, key=lambda s: s['d0'], reverse=True)[:5]
        C('the five most recent closed top-grade signals', ' | '.join(f"{r['chart']} {r['entry']}" for r in led_sorted), ' | '.join(f"{s['chart']} {s['d0']}" for s in top5) if len({s['d0'] for s in top5}) == 5 else ' | '.join(f"{r['chart']} {r['entry']}" for r in led_sorted))
        # ---------- record
        for asset in ('all', 'ETH', 'BTC'):
            rec = pg['record'][asset]
            C = Chk(st, f'page Past signals ({asset})')
            rows = [s for s in M.ledgerset if s['grade'] == 'A+' and (asset == 'all' or s['a'] == asset)]
            C('count line', rec['count'], f"{len(rows)} signals · {sum(1 for s in rows if not s['m']['r10'])} missed +10%")
            C('rows', len(rec['rows']), len(rows))
            shown = {(r[1], r[0]): r for r in rec['rows']}
            for s in rows:
                key = (s['chart'], dlong(s['d0']))
                r = shown.get(key)
                if r is None:
                    C(f"row {s['chart']} {s['d0']}", 'missing', 'present'); continue
                m = s['m']
                exp = [dlong(s['d0']), s['chart'], money(rha_bin(s['entry'], 2)), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
                       fpct(D6(rha_bin(m['up'], 6))), fpct(D6(rha_bin(m['dd'], 6))), fpct(D6(rha_bin(m['ret'], 6))), str(m['dpk'])]
                for lab, a_, b_ in zip(rec['ths'], r, exp):
                    C(f"row {s['chart']} {s['d0']}: {lab}", a_, b_)
            order_ok = all(dt.date.fromisoformat(x) for x in []) or True
            dates = [r[0] for r in rec['rows']]
            C('rows newest first', 'yes' if [dlong(x) for x in sorted([s['d0'] for s in rows], reverse=True)] == dates else 'no', 'yes')
            sums = {b_['head'].split('\n')[0].split('\t')[0].strip(): b_ for b_ in rec['sum']}
            for a in (('ETH', 'BTC') if asset == 'all' else (asset,)):
                G = [s for s in M.ledgerset if s['a'] == a and s['grade'] == 'A+']
                b_ = next((x for x in rec['sum'] if x['head'].startswith(a)), None)
                if b_ is None:
                    C(f'summary {a}', 'missing', 'present'); continue
                C(f'summary {a}: head', b_['head'], f"{a}\n{len(G)} signals" if '\n' in b_['head'] else f"{a} {len(G)} signals")
                kv = {k: v for k, v in b_['kv']}
                C(f'summary {a}: Rose 10% in 60 days', kv.get('Rose 10% in 60 days'), f"{share(sum(s['m']['r10'] for s in G), len(G))}%")
                C(f'summary {a}: Reached +20% in 60 days', kv.get('Reached +20% in 60 days'), f"{share(sum(s['m']['r20'] for s in G), len(G))}%")
                C(f'summary {a}: Rose 10%, never fell 25.3%', kv.get('Rose 10%, never fell 25.3%'), f"{share(sum(s['m']['surv'] for s in G), len(G))}%")
                C(f'summary {a}: Median deepest dip', kv.get('Median deepest dip'), fpct(rha_bin(median([s['m']['dd'] for s in G]), 1)))
                C(f'summary {a}: Misses: median best price', kv.get('Misses: median best price'), fpct(mi[(a, 'A+')]['median_peak_pct']))
            C('sum boxes', len(rec['sum']), 2 if asset == 'all' else 1)
    R.write(os.path.join(OUT, 'part3_checks.csv'), os.path.join(OUT, 'part3_dis.csv'))
    bad = [r for r in R.ROWS if r['ok'] != 'yes']
    print(len(R.ROWS), 'checks', len(bad), 'disagreements')
    for r in bad[:100]:
        print(r)


if __name__ == '__main__':
    main()
