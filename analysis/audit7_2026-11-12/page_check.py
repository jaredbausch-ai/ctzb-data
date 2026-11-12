"""Check every number the page displays against my own values."""
import datetime as dt, json, math, os, re, statistics as st
import audit as A
from build import State
from lib import *  # noqa

CK = A.CK
MON = {m: i + 1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}


def num(s):
    s = s.strip().replace('−', '-').replace('$', '').replace(',', '').replace('%', '').replace('+', '')
    return float(s)


def find_num(pattern, text):
    m = re.search(pattern, text)
    return None if not m else num(m.group(1))


def pdate(s):
    m = re.match(r'(\d{1,2}) (\w{3,4}) (\d{4})', s.strip())
    return dt.date(int(m.group(3)), MON[m.group(2)[:3]], int(m.group(1)))


def ddmon(s, year_hint):
    m = re.match(r'(\d{2}) (\w{3,4})', s.strip())
    return (int(m.group(1)), MON[m.group(2)[:3]])


def sgn(v, d=1):
    """my display rule: rounded once, half away from zero; values that round to zero show no sign"""
    r = rnd(v, d)
    return r


def setup_edge(f):
    """edge from my own ladder: 0 = below the bar from entry; -x = first fall below 70%; None = holds"""
    base = f['l0ok'] if f['l0ok'] != '' else f['reach10']
    if base != '' and base < 70: return 0
    for th in (5, 10, 15, 20):
        v = f[f'l{th}ok']
        if v != '' and v < 70: return -th
    return None


def X(i, n): return 20 + (940 / n) * i + (940 / n) / 2


def check_card_view(S, st_, loc, v, mc, mi, F):
    f = mc['figs']; kind = mc['kind']; a = mc['asset']
    txt = v['card']
    # head line
    if kind == 'forming':
        CK.add(st_, loc, 'line: low day', pdate(re.search(r'Low (\d+ \w+ \d{4})', txt).group(1)).isoformat(), mc['low_day'], 'value')
        CK.add(st_, loc, 'line: confirms', pdate(re.search(r'confirms (\d+ \w+ \d{4})', txt).group(1)).isoformat(), mc['confirms_on'], 'value')
        CK.add(st_, loc, 'line: must close above', find_num(r'closes above (\$[\d,]+\.\d\d)', txt), mc['must_close_above'], 'value')
        CK.add(st_, loc, 'state', 'Setup forming' in txt, True, 'label')
    elif kind == 'open':
        o = mc['open']
        CK.add(st_, loc, 'line: confirmed', pdate(re.search(r'Confirmed (\d+ \w+ \d{4})', txt).group(1)).isoformat(), mc['confirms_on'], 'value')
        CK.add(st_, loc, 'line: entry close', find_num(r'entry close (\$[\d,]+\.\d\d)', txt), mc['entry_close'], 'value')
        CK.add(st_, loc, 'line: day N of 60', find_num(r'day (\d+) of 60', txt), o['days_elapsed'], 'value')
        CK.add(st_, loc, 'line: best so far', find_num(r'best so far ([+−\-]?[\d\.]+)%', txt), o['best_so_far_pct'], 'value')
        CK.add(st_, loc, 'line: worst so far', find_num(r'worst ([+−\-]?[\d\.]+)%', txt), o['worst_so_far_pct'], 'value')
    else:
        CK.add(st_, loc, 'line: confirmed', pdate(re.search(r'confirmed (\d+ \w+ \d{4})', txt).group(1)).isoformat(), '2024-09-22', 'value')
        CK.add(st_, loc, 'line: entry close', find_num(r'entry close (\$[\d,]+\.\d\d)', txt), mc['entry_close'], 'value')
    CK.add(st_, loc, 'big number: rose 10% within 60 days', find_num(r'\n(\d+)%\nrose 10% within 60 days', txt), f['reach10'], 'value')
    CK.add(st_, loc, 'line under: without ever falling 25.3%', find_num(r'(\d+)% did it without ever falling 25.3%', txt), f['surv10'], 'value')
    CK.add(st_, loc, 'from N past signals', find_num(r'from (\d+) past signals', txt), f['n'], 'value')
    stats = {x['t']: x['v'] for x in v['stats']}
    CK.add(st_, loc, 'Typical high', num(stats['Typical high']), rnd(f['bestMoveExact'], 1), 'value')
    CK.add(st_, loc, 'Typical drop from entry', num(stats['Typical drop from entry']), rnd(f['maxDip60Exact'], 1), 'value')
    eg = setup_edge(f)
    exp_edge = f'Below the 70% bar from entry' if eg == 0 else (f'{"−" if eg else ""}{abs(eg)}% before it rises 10%' if eg else 'Holds at every level')
    CK.add(st_, loc, 'Edge gone below', stats['Edge gone below'], exp_edge, 'value')
    mtxt = stats['If it misses: up first']
    exp_m = ('Every time' if mi['up_first'] == mi['misses'] else f"{mi['up_first']} of {mi['misses']}") + f" · median best {fmt_pct(mi['median_peak_exact'])}"
    CK.add(st_, loc, 'If it misses: up first', mtxt, exp_m, 'value')
    # the stricter reading of "up first" (above entry before ever below it)
    CK.add(st_, loc, 'If it misses: "up first" read literally (above entry before ever below)', mtxt.split(' · ')[0],
           f"{mi['above_before_below']} of {mi['misses']}", 'label: "up first" counts misses ever above entry within 60 days, not above entry first',
           ok=mi['above_before_below'] == mi['up_first'])
    tiles = {x['t']: x['v'] for x in v['tiles']}
    CK.add(st_, loc, 'tile Dip before the high, from entry', num(tiles['Dip before the high, from entry']), rnd(f['dipBeforeHighExact'], 1), 'value')
    CK.add(st_, loc, 'tile High lands around', num(tiles['High lands around'].replace('Day ', '')), f['daysToHigh'], 'value')
    CK.add(st_, loc, 'tile Reached +20%', num(tiles['Reached +20%']), f['reach20'], 'value')
    CK.add(st_, loc, 'tile Touched −30%', num(tiles['Touched −30%']), f['touched30'], 'value')
    CK.add(st_, loc, 'tile Typical high', num(tiles['Typical high']), rnd(f['bestMoveExact'], 1), 'value')
    CK.add(st_, loc, 'tile Deepest dip lands around', num(tiles['Deepest dip lands around'].replace('Day ', '')), f['daysToLow'], 'value')
    wk = [k for k in tiles if k.startswith('Worst drop, misses')][0]
    ck = [k for k in tiles if k.startswith('Typical change by day 60')][0]
    CK.add(st_, loc, 'tile Worst drop, misses: pool size', find_num(r'all (\d+)', wk), mi['signals'], 'value')
    CK.add(st_, loc, 'tile Worst drop, misses (median of misses)', num(tiles[wk]), rnd(mi['median_worst_exact'], 1), 'value')
    CK.add(st_, loc, 'tile Typical change by day 60, misses', num(tiles[ck]), rnd(mi['median_day60_exact'], 1), 'value')
    CK.add(st_, loc, 'tile "Worst drop, misses" wording', wk, 'Median worst drop, misses ...',
           'label: tile says "Worst drop" but shows the MEDIAN worst drop of the misses', ok=False)
    # ladder
    lad = v['ladder']
    exp_l = [('From entry', f['n'], f['l0ok'])] + [(f'Falls {t}% first', f[f'l{t}n'], f[f'l{t}ok']) for t in (5, 10, 15, 20)]
    CK.add(st_, loc, 'ladder rows', len(lad), len(exp_l), 'membership')
    for (t, n, val), r in zip(exp_l, lad):
        CK.add(st_, loc, f'ladder {t}: n', find_num(r'n (\d+)', r['t']), n, 'value')
        shownv = None if r['v'] == 'n/a' else num(r['v'])
        CK.add(st_, loc, f'ladder {t}: %', shownv, None if val == '' else val, 'value')
        CK.add(st_, loc, f'ladder {t}: bar marked gone', 'gone' in (r['cls'] or ''), val != '' and val < 70, 'value')
        CK.add(st_, loc, f'ladder {t}: bar width', r['w'], f'{val if val != "" else 0}%', 'value')
    eras = v['eras']
    for (t, n, val), r in zip([('Before 2022', f['nOld'], f['surv10Old']), ('Since 2022', f['nNew'], f['surv10New'])], eras):
        CK.add(st_, loc, f'era {t}: n', find_num(r'n (\d+)', r['t']), n, 'value')
        CK.add(st_, loc, f'era {t}: %', None if r['v'].startswith('n/a') else num(r['v']), None if val == '' else val, 'value')
    if kind == 'forming' and mc['grade'] != 'A+':
        CK.add(st_, loc, 'miss pool note', find_num(r'all (\d+) \w+ signals of this grade', txt), mi['signals'], 'value')


def fmt_pct(v, d=1):
    r = rnd(v, d)
    s = f'{abs(r):.{d}f}'
    return ('+' if r > 0 else '−' if r < 0 else '') + s + '%'


def money(v):
    return '$' + f'{rnd(v, 2):,.2f}'


def misses_for(S, a, grade, known_by=None):
    G = [s for s in S.led if s['a'] == a and s['grade'] == grade and (known_by is None or s['d0'] + dt.timedelta(days=60) <= known_by)]
    mi = A.misses_of(G)
    ms = [s for s in G if not s['m']['r10']]
    mi['median_peak_exact'] = st.median(s['m']['up'] for s in ms)
    mi['median_worst_exact'] = st.median(s['m']['dd'] for s in ms)
    mi['median_day60_exact'] = st.median(s['m']['ret'] for s in ms)
    mi['above_before_below'] = mi['_above_before_below']
    return mi


def next_open(d, tfd):
    return bucket_last_day(d, tfd) + dt.timedelta(days=1)


def ts(d):
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())


def check_chart(S, st_, loc, cv, mc, mode, F, ex_json):
    """cv: dumped chart view; mc: my card; mode 'alert'/'happened'"""
    f = mc['figs']; kind = mc['kind']; a = mc['asset']; tf = mc['timeframe']; tfd = int(tf[0])
    if kind == 'example':
        ch = S.ch[('ETH', '2D')]
        i0 = ch.D.index(day_of(ex_json['bars'][0]['t']))
        bars = ch.bars[i0:i0 + len(ex_json['bars'])]
        E = [b[0] for b in bars].index(dt.date(2024, 9, 21))
        entry = S.ledkey[('ETH 2D', '2024-09-22')]['entry']; tEntry = dt.date(2024, 9, 22)
        opens = [b[0] for b in bars]; forming = False
    else:
        bars = S.ch[(a, tf)].bars[-70:]
        opens = [b[0] for b in bars]; forming = True
        if kind == 'open':
            tEntry = dt.date.fromisoformat(mc['confirms_on'])
            E = next(i for i, b in enumerate(bars) if bucket_last_day(b[0], tfd) == tEntry)
            entry = S.ledkey.get((mc['chart'], mc['confirms_on']), None)
            entry = mc['entry_close_exact']
        else:
            tEntry = dt.date.fromisoformat(mc['confirms_on']); E = len(bars) - 1; entry = mc['price_now_exact']
        while opens[-1] <= tEntry + dt.timedelta(days=61):
            opens.append(next_open(opens[-1], tfd))
    nS = len(opens) if forming else len(bars)
    slot_of = lambda d: max(i for i, o in enumerate(opens) if o <= d)
    dayX = lambda k: slot_of(tEntry + dt.timedelta(days=k))
    A_ = dayX(0) if kind == 'forming' else E
    eg = setup_edge(f)
    lv = dict(high=entry * (1 + f['bestMoveExact'] / 100), t10=entry * 1.1, entry=entry, drop=entry * (1 + f['maxDip60Exact'] / 100),
              edge=entry * (1 + eg / 100) if eg else None)
    happened = mode == 'happened'
    shown = bars[:E + 1] if (not forming and not happened) else bars
    lo = min(min(b[3] for b in shown), lv['drop'], entry * 0.8) * 0.95
    hi = max(max(b[2] for b in shown), lv['high']) * 1.07
    Y = lambda p: 480 - (p - lo) / (hi - lo) * 456
    svg = cv['svg']
    texts = [e for e in svg if e['tag'] == 'text']
    lines = [e for e in svg if e['tag'] == 'line']
    # vertical lines: each followed by its label
    vl = {}
    for i, e in enumerate(svg):
        if e['tag'] == 'line' and e['a'].get('x1') == e['a'].get('x2') and e['a'].get('y1') == '24' and e['a'].get('y2') == '480':
            lab = svg[i + 1]['text'] if i + 1 < len(svg) and svg[i + 1]['tag'] == 'text' else ''
            vl[lab] = float(e['a']['x1'])
    exp_v = {}
    exp_v['Entry' if kind != 'forming' else 'Today'] = (X(E, nS), f'bar {opens[E]}')
    exp_v['Day 60'] = (X(min(nS - 1, dayX(60)), nS), f'bar containing {tEntry + dt.timedelta(days=60)} (opens {opens[min(nS - 1, dayX(60))]})')
    exp_v[f"High usually ~day {f['daysToHigh']}"] = (X(dayX(f['daysToHigh']), nS), f"bar containing {tEntry + dt.timedelta(days=f['daysToHigh'])}")
    if kind == 'forming' and A_ > E:
        exp_v[f"Confirms {mc['confirms_label']} · entry, day 0"] = (X(A_, nS), f'bar containing {tEntry}')
    if eg is None and False:
        pass
    for lab, (x, why) in exp_v.items():
        got = vl.get(lab)
        CK.add(st_, loc, f'vertical line "{lab}" x ({why})', None if got is None else round(got, 3), round(x, 3), 'chart position')
    for lab in vl:
        if lab not in exp_v:
            CK.add(st_, loc, f'unexpected vertical line "{lab}"', round(vl[lab], 3), '', 'chart', ok=False)
    # price tags: rect + money text in the right gutter
    tags = [e['text'] for e in texts if e['a'].get('fill') == '#07060F']
    exp_tags = sorted([money(lv['high']), money(lv['t10']), money(lv['entry']), money(lv['drop'])], key=lambda s: -num(s))
    CK.add(st_, loc, 'price tags (high, +10%, entry, drop)', ' '.join(sorted(tags, key=lambda s: -num(s))), ' '.join(exp_tags), 'value')
    # horizontal level lines: y of each
    hl = [e for e in lines if e['a'].get('stroke-width') == '2' and e['a'].get('y1') == e['a'].get('y2') and abs(float(e['a']['x1']) - X(A_, nS)) < 1e-6]
    exp_y = sorted([Y(lv['high']), Y(lv['t10']), Y(lv['entry']), Y(lv['drop'])])
    got_y = sorted(float(e['a']['y1']) for e in hl)
    CK.add(st_, loc, 'level lines y (scale: lo/hi from what is shown)', ' '.join(f'{y:.2f}' for y in got_y), ' '.join(f'{y:.2f}' for y in exp_y), 'chart scale',
           ok=len(got_y) == 4 and all(abs(g - e_) < 0.01 for g, e_ in zip(got_y, exp_y)))
    for e in hl:
        CK.add(st_, loc, 'level line ends at Day 60 x', round(float(e['a']['x2']), 3), round(X(min(nS - 1, dayX(60)), nS), 3), 'chart position')
    if lv['edge']:
        el = [e for e in lines if e['a'].get('stroke-width') == '2.5']
        CK.add(st_, loc, 'edge line y', round(float(el[0]['a']['y1']), 2) if el else None, round(Y(lv['edge']), 2), 'chart scale')
        et = [e['text'] for e in texts if e['text'].startswith('Edge gone below')]
        CK.add(st_, loc, 'edge label', et[0] if et else None, f"Edge gone below {money(lv['edge'])} ({'−' if eg < 0 else ''}{abs(eg)}%, before +10%)", 'value')
    lt = {e['text'] for e in texts}
    CK.add(st_, loc, 'label Typical high', f"Typical high {fmt_pct(f['bestMoveExact'])}" in lt, True, 'value')
    CK.add(st_, loc, 'label +10%', f"+10% · {f['reach10']}% of past signals got here" in lt, True, 'value')
    CK.add(st_, loc, 'label Typical drop', f"Typical drop {fmt_pct(f['maxDip60Exact'])}" in lt, True, 'value')
    # ladder zones
    zone = [e['text'] for e in texts if re.fullmatch(r'\d+%|n/a', e['text'] or '')]
    exp_z = [f"{f['l0ok']}%"] + [('n/a' if f[f'l{t}ok'] == '' else f"{f[f'l{t}ok']}%") for t in (5, 10, 15)]
    CK.add(st_, loc, 'ladder zones on the chart', ' '.join(zone), ' '.join(exp_z), 'value')
    # date axis labels
    every = max(1, int(math.floor(nS / 8 + 0.5)))
    axis = [e['text'] for e in texts if re.fullmatch(r'\d{2} \w{3,4}', e['text'] or '')]
    exp_axis = [opens[min(i, len(opens) - 1)] for i in range(0, nS, every)]
    CK.add(st_, loc, 'date axis labels', ' '.join(axis), ' '.join(f'{d.day:02d} {d.strftime("%b")}' for d in exp_axis), 'value',
           ok=len(axis) == len(exp_axis) and all(ddmon(x, 0) == (d.day, d.month) for x, d in zip(axis, exp_axis)))
    # candles drawn
    ncand = sum(1 for e in svg if e['tag'] == 'rect' and e['a'].get('width') and e['a'].get('rx') is None
                and e['a'].get('x') not in ('0',) and e.get('style') and 'var(--high)' in e['style'] or
                (e['tag'] == 'rect' and e.get('style') and 'var(--drop)' in e['style'] and e['a'].get('opacity') is None and e['a'].get('rx') is None))
    expn = (E + 1) if (not forming and not happened) else len(bars)
    wicks = [e for e in lines if e['a'].get('stroke-width') == '1.5' and e['a'].get('x1') == e['a'].get('x2') and e['a'].get('y1') != '24']
    CK.add(st_, loc, 'candles drawn (wicks)', len(wicks), expn, 'chart')
    for i, w in enumerate(wicks[:expn]):
        b = bars[i]
        if abs(float(w['a']['x1']) - X(i, nS)) > 1e-6 or abs(float(w['a']['y1']) - Y(b[2])) > 0.01 or abs(float(w['a']['y2']) - Y(b[3])) > 0.01:
            CK.add(st_, loc, f'candle {b[0]} wick', w['a'], 'x/high/low mismatch', 'chart', ok=False)
            break
    else:
        CK.add(st_, loc, 'candle wicks at slot x, high and low', 'all', 'all', 'chart')
    # low circle (forming / open) and outcome circles (example, happened)
    circ = [e for e in svg if e['tag'] == 'circle']
    if kind == 'forming':
        li = [i for i, b in enumerate(bars) if str(b[0]) == mc['low_date']]
        CK.add(st_, loc, 'low circle present', len(circ), 1 if li else 0, 'chart')
        if li and circ:
            CK.add(st_, loc, 'low circle x', round(float(circ[0]['a']['cx']), 3), round(X(li[0], nS), 3), 'chart position')
            lowp = S.day[a].L[S.day[a].pos[dt.date.fromisoformat(mc['low_day'])]]
            t = [e['text'] for e in texts if e['text'].startswith('Low ')][0]
            CK.add(st_, loc, 'low label day', pdate(t[4:]).isoformat(), mc['low_day'], 'value')
            CK.add(st_, loc, 'low label price (daily low on the low day)', find_num(r'· (\$[\d,]+\.\d\d)', t), rnd(lowp, 2), 'value')
    if kind == 'example' and happened:
        day = S.day['ETH']; ks = window(day, tEntry)
        Hs = [day.H[k] for k in ks]; Ls = [day.L[k] for k in ks]
        kh = Hs.index(max(Hs)) + 1; kl = Ls.index(min(Ls)) + 1
        out = [e['text'] for e in texts if e['text'].startswith('This one:')]
        for t, (p, k) in zip(out, ((max(Hs), kh), (min(Ls), kl))):
            CK.add(st_, loc, 'This one: price', find_num(r'This one: (\$[\d,]+\.\d\d)', t), rnd(p, 2), 'value')
            CK.add(st_, loc, 'This one: pct', find_num(r'· ([+−\-][\d\.]+)%', t), rnd((p / entry - 1) * 100, 1), 'value')
            m = re.search(r'days (\d+)–(\d+)', t) or re.search(r'day (\d+)', t)
            rng = (int(m.group(1)), int(m.group(2) if m.lastindex == 2 else m.group(1)))
            CK.add(st_, loc, 'This one: day range contains the actual day', f'{rng[0]}-{rng[1]}', k, 'value', ok=rng[0] <= k <= rng[1])
    return dict(entry=entry, lv=lv, eg=eg, E=E, opens=opens, tEntry=tEntry)


def check_side(S, st_, loc, cv, mc, geo, kind):
    f = mc['figs']; side = cv['side']; entry = geo['entry']; eg = geo['eg']
    CK.add(st_, loc, 'side big number', find_num(r'\n(\d+)%\nrose 10%', side), f['reach10'], 'value')
    CK.add(st_, loc, 'side from N past signals', find_num(r'from (\d+) past signals', side), f['n'], 'value')
    CK.add(st_, loc, 'side without falling 25.3%', find_num(r'(\d+)% without ever falling', side), f['surv10'], 'value')
    CK.add(st_, loc, 'side Typical high %', find_num(r'Typical high\n([+−\-][\d\.]+)%', side), rnd(f['bestMoveExact'], 1), 'value')
    CK.add(st_, loc, 'side Typical high price', find_num(r'Typical high\n[^\n]*· (\$[\d,]+\.\d\d)', side), rnd(geo['lv']['high'], 2), 'value')
    CK.add(st_, loc, 'side +10% target', find_num(r'\+10% target\n(\$[\d,]+\.\d\d)', side), rnd(entry * 1.1, 2), 'value')
    CK.add(st_, loc, 'side Reached +20%', find_num(r'Reached \+20%\n(\d+)%', side), f['reach20'], 'value')
    CK.add(st_, loc, 'side Typical drop %', find_num(r'Typical drop\n([+−\-][\d\.]+)%', side), rnd(f['maxDip60Exact'], 1), 'value')
    CK.add(st_, loc, 'side Typical drop price', find_num(r'Typical drop\n[^\n]*· (\$[\d,]+\.\d\d)', side), rnd(geo['lv']['drop'], 2), 'value')
    m = re.search(r'Edge gone below\n([^\n]*)', side).group(1)
    exp = 'below the bar already' if eg == 0 else 'holds at every level' if eg is None else f"{money(entry * (1 + eg / 100))} (−{abs(eg)}%)"
    CK.add(st_, loc, 'side Edge gone below', m, exp, 'value')
    if kind == 'forming':
        CK.add(st_, loc, 'side stand-in note', 'stand-in for the entry' in side, True, 'label')
    if kind == 'open':
        o = mc['open']
        CK.add(st_, loc, 'side live day N of 60', find_num(r'day (\d+) of 60', side.lower()), o['days_elapsed'], 'value')
        CK.add(st_, loc, 'side best so far', find_num(r'Best so far\n([+−\-]?[\d\.]+)%', side), o['best_so_far_pct'], 'value')
        CK.add(st_, loc, 'side worst so far', find_num(r'Worst so far\n([+−\-]?[\d\.]+)%', side), o['worst_so_far_pct'], 'value')
        d10 = re.search(r'Day 10\n([^\n]*)', side).group(1)
        CK.add(st_, loc, 'side day 10', None if d10 == 'not yet' else num(d10), o['day10_pct'], 'value')
    if kind == 'example' and 'WHAT THIS ONE DID' in side:
        day = S.day['ETH']; ks = window(day, geo['tEntry']); e = entry
        Hs = [day.H[k] for k in ks]; Ls = [day.L[k] for k in ks]
        kh = Hs.index(max(Hs)) + 1; kl = Ls.index(min(Ls)) + 1
        CK.add(st_, loc, 'happened: reached +10% / +20%', re.search(r'Reached \+10% / \+20%\n([^\n]*)', side).group(1),
               f"{'Yes' if max(Hs) >= e * 1.1 else 'No'} / {'Yes' if max(Hs) >= e * 1.2 else 'No'}", 'value')
        bp = re.search(r'Best price\n([+−\-][\d\.]+)%, days (\d+)–(\d+)', side)
        CK.add(st_, loc, 'happened: best price %', num(bp.group(1)), rnd((max(Hs) / e - 1) * 100, 1), 'value')
        CK.add(st_, loc, 'happened: best price days contain the day', f'{bp.group(2)}-{bp.group(3)}', kh, 'value', ok=int(bp.group(2)) <= kh <= int(bp.group(3)))
        dp = re.search(r'Deepest drop\n([+−\-][\d\.]+)%, days (\d+)–(\d+)', side)
        CK.add(st_, loc, 'happened: deepest drop %', num(dp.group(1)), rnd((min(Ls) / e - 1) * 100, 1), 'value')
        CK.add(st_, loc, 'happened: deepest drop days contain the day', f'{dp.group(2)}-{dp.group(3)}', kl, 'value', ok=int(dp.group(2)) <= kl <= int(dp.group(3)))
        c10 = day.C[ks[9]]
        d10 = re.search(r'Day 10 check\n(\w+), ([+−\-][\d\.]+)%', side)
        CK.add(st_, loc, 'happened: day 10 check', f"{d10.group(1)} {num(d10.group(2))}", f"{'Red' if c10 < e else 'Green'} {rnd((c10 / e - 1) * 100, 1)}", 'value')
        CK.add(st_, loc, 'happened: price on day 60', find_num(r'Price on day 60\n([+−\-][\d\.]+)%', side), rnd((day.C[ks[59]] / e - 1) * 100, 1), 'value')


def check_cloud(S, st_, loc, cv, mc, paths):
    """paths: my quantiles dict {day: (q25, med, q75)} and n"""
    P, n, sub_exp = paths
    CK.add(st_, loc, 'cloud n', find_num(r'n (\d+)', cv['cloudSub']), n, 'value')
    CK.add(st_, loc, 'cloud subtitle', cv['cloudSub'].rsplit(', n', 1)[0], sub_exp, 'label')
    note = cv['cloudNote']
    m = re.search(r'Day 60: median ([+−\-]?[\d\.]+)%, middle half ([+−\-]?[\d\.]+)% to ([+−\-]?[\d\.]+)%', note)
    q = P[60]
    for lab, g, e in (('day 60 median', m.group(1), q[1]), ('day 60 q25', m.group(2), q[0]), ('day 60 q75', m.group(3), q[2])):
        CK.add(st_, loc, f'cloud note {lab}', num(g), rnd(e, 1), 'value')
    Xc = lambda d: 20 + 940 * d / 60
    Yc = lambda v: 230 - (max(-40, min(100, v)) - (-40)) / 140 * 218
    pl = [e for e in cv['cloud'] if e['tag'] == 'polyline']
    med = [tuple(map(float, p.split(','))) for p in pl[0]['a']['points'].split()]
    bad = [d for d in range(61) if abs(med[d][0] - Xc(d)) > 1e-6 or abs(med[d][1] - Yc(rnd(q[1] if False else P[d][1], 1))) > 1e-6]
    CK.add(st_, loc, 'cloud median line (61 points at my day-d median)', len(bad), 0, 'chart', ok=not bad)
    poly = [e for e in cv['cloud'] if e['tag'] == 'polygon'][0]
    pts = [tuple(map(float, p.split(','))) for p in poly['a']['points'].split()]
    expp = [(Xc(d), Yc(rnd(P[d][2], 1))) for d in range(61)] + [(Xc(d), Yc(rnd(P[d][0], 1))) for d in range(60, -1, -1)]
    badp = [i for i, (g, e_) in enumerate(zip(pts, expp)) if abs(g[0] - e_[0]) > 1e-6 or abs(g[1] - e_[1]) > 1e-6]
    CK.add(st_, loc, 'cloud middle-half band (q75 then q25, 122 points)', len(badp) + abs(len(pts) - len(expp)), 0, 'chart', ok=not badp and len(pts) == len(expp))
    if len(pl) > 1 and mc['kind'] == 'example':
        S_ = S; day = S_.day['ETH']; e = mc['entry_close']
        exp_this = [(Xc(0), Yc(0.0))] + [(Xc(2 * k), Yc((day.C[day.pos[dt.date(2024, 9, 22) + dt.timedelta(days=2 * k)]] / e - 1) * 100)) for k in range(1, 31)]
        got = [tuple(map(float, p.split(','))) for p in pl[1]['a']['points'].split()]
        badt = [i for i, (g, e_) in enumerate(zip(got, exp_this)) if abs(g[0] - e_[0]) > 1e-6 or abs(g[1] - e_[1]) > 1e-3]
        CK.add(st_, loc, 'cloud "this signal" line (daily closes on days 2..60)', len(badt) + abs(len(got) - len(exp_this)), 0, 'chart', ok=not badt and len(got) == len(exp_this))
    clip = [d for d in range(61) if not (-40 <= P[d][0] and P[d][2] <= 100)]
    CK.add(st_, loc, 'cloud quartiles inside the drawn -40%..+100% range', ','.join(map(str, clip)) or 'none', 'none',
           'chart: quartile band clipped at the axis limits', ok=not clip)
