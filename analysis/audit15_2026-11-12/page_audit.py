"""Audit 15 -- check 8: every number the member page displays, against MY values (mine_<state>.pkl, computed
by audit_data.py from the raw candles). Usage: python3 page_audit.py <state dir> <state name>"""
import sys, csv, json, pickle, datetime as dt, re, itertools
from fractions import Fraction as Fr
from decimal import Decimal
from core import rhu, fstr, Checks, bucket_span, Candles
from harness import Site, norm_ws

S, NAME = sys.argv[1], sys.argv[2]
M = pickle.load(open(f'mine_{NAME}.pkl', 'rb'))
C = Checks(NAME)
MINUS = '−'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
def date_long(d):
    if isinstance(d, str): d = dt.date.fromisoformat(d)
    return f'{d.day} {MON[d.month - 1]} {d.year}'
def fmt(v, d=1):
    if v is None or v == '': return 'n/a'
    r = rhu(Fr(v), d)
    return fstr(r, d).replace('-', MINUS)
def pct(v, d=1, sign=True):
    if v is None or v == '': return 'n/a'
    r = rhu(Fr(v), d)
    return ('+' if sign and r > 0 else '') + fmt(v, d) + '%'
def money(v):
    if v is None: return 'n/a'
    r = rhu(Fr(v), 2); s = fstr(abs(r), 2); i, f = s.split('.')
    return ('-' if r < 0 else '') + '$' + f'{int(i):,}' + '.' + f
def T(loc, label, shown, mine, cause=''):
    return C.add(loc, label, norm_ws(shown).lower() if isinstance(shown, str) else shown, norm_ws(mine).lower() if isinstance(mine, str) else mine, cause)
def lines(txt): return [norm_ws(x) for x in (txt or '').split('\n') if norm_ws(x)]
def cmp_lines(loc, shown, mine, names=None):
    for i, (a, b) in enumerate(itertools.zip_longest(shown, mine, fillvalue='(missing)')):
        T(loc, f'line {i + 1}: {b[:60]}' if names is None else names[i], a, b)

FOOT = "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record. Past results don't guarantee future results."
def cardv(cid):
    c = M['cards'][cid]; g = lambda k: c[k]
    kind = c['_kind']; a, tf = c['_a'], c['_tf']; n = c['_n']
    ex = kind == 'example'; top = c['_grade'] == 'A+'
    mi = M['ex_misses'] if ex else M['misses'].get((a, c['_grade']))
    v = dict(kind=kind, a=a, tf=tf, n=n, ex=ex, top=top, mi=mi, grade=c['_grade'], basis=c['_basis'], edge=None if c['_edge'] == '' else c['_edge'],
             r10=g('rose10_within60d_pct'), surv=g('rose10_never_fell25_within60d_pct'), r20=g('rose20_within60d_pct'), t30=g('fell30_within60d_pct'),
             high=c['_med']['up'], drop=c['_med']['dd'], dipb=c['_med']['ddpk'], hday=g('typical_day_of_60d_high'), lday=g('typical_day_of_deepest_dip'),
             fe=g('from_entry still_rose10_pct'), fex=g('from_entry still_rose10_exact_pct'),
             lad=[(th, g(f'falls {th}% first: n'), g(f'falls {th}% first: still_rose10_pct'), g(f'falls {th}% first: still_rose10_exact_pct')) for th in (5, 10, 15, 20)],
             eras=[('Before 2022', g('before_2022 n'), g('before_2022 rose10 never fell 25.3%')), ('Since 2022', g('since_2022 n'), g('since_2022 rose10 never fell 25.3%'))],
             d0=c['_d0'], tdate=c['_tdate'], lowday=g('low_day (day the low printed)'), kill=c['_kill'], need=c['_need'],
             entry=c['_price'] if kind == 'forming' else c['_entry'], real_entry=c['_entry'])
    return v

def expected_card(cid, best_forming_id=None, osig=None):
    v = cardv(cid); a, tf, n, mi = v['a'], v['tf'], v['n'], v['mi']
    below = v['kind'] == 'forming' and not v['top']
    L = [f"{a} · {tf} chart" + (" · example" if v['ex'] else ""), {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[v['kind']]]
    if v['kind'] == 'forming':
        L.append(f"Low {date_long(v['lowday'])} · confirms {date_long(v['d0'])}" + (f" if it closes above {money(v['kill'])}" if v['kill'] else ""))
        L.append(("Best setup forming today." if best_forming_id == cid else "Setup forming.") + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms."
                 if below else "Not confirmed yet. It can still vanish before it confirms.")
    elif v['kind'] == 'open':
        L.append(f"Confirmed {date_long(v['d0'])} · entry close {money(v['real_entry'])} · day {osig['elapsed']} of 60 · best so far {pct(osig['best'])} · worst {pct(osig['worst'])}")
        lost = osig['status'] == 'lost'
        L.append(("Edge lost. " + ("Its odds were below the bar from the entry." if osig['edge'] == 0 else f"It fell to its edge level ({pct(osig['edge'], 0)}) before rising 10%.")
                  if lost else "On track. It has not fallen to its edge level.") + " The odds below are as of the entry close, not from today.")
    else:
        L.append(f"Example: confirmed {date_long('2024-09-22')} · entry close {money(v['real_entry'])}")
    L += [f"{v['r10']}%", "rose 10% within 60 days" + (" · at the entry close, not from today" if v['kind'] == 'open' else ""),
          f"{v['surv']}% did it without ever falling 25.3%", f"from {v['basis']} · every figure covers the 60 days after entry",
          "Typical high", pct(v['high']), "Typical drop from entry", pct(v['drop']), "Edge gone below",
          ("Below the 70% bar from entry" if v['edge'] == 0 else f"{pct(v['edge'], 0)} before it rises 10%" if v['edge'] is not None else "Holds at every level"),
          "If it misses: went above entry", (f"{mi['up_first']} of {mi['misses']} · median best {pct(mi.get('median_peak_pct'))}" if mi else "n/a")]
    if below and mi: L.append(f"all {mi['signals']} {a} signals of this grade")
    tail = (f" · {mi['misses']} misses of {'the' if v['ex'] else 'all'} {mi['signals']} {a} {'top-grade' if v['top'] else 'same-grade'} signals" + (" known by then" if v['ex'] else "")) if mi and mi['signals'] else ""
    L += ["Lead trader: unavailable", "The detail", "Dip before the high, from entry", pct(v['dipb']), "High lands around", f"Day {v['hday']}",
          f"Reached +20% within 60 days · n {n}", f"{v['r20']}%", f"Touched {MINUS}30% within 60 days · n {n}", f"{v['t30']}%", "Typical high", pct(v['high']),
          "Deepest dip lands around", f"Day {v['lday']}", "Typical worst drop, misses" + tail, pct(mi.get('median_worst_drop_pct')) if mi else "n/a",
          "Typical change by day 60, misses" + tail, pct(mi.get('median_day60_pct')) if mi else "n/a",
          "Where the odds fade · this setup", f"From entry n {n}", f"{v['fe']}%"]
    for th, hit, sh, _ in v['lad']:
        L += [f"Falls {th}% first n {hit}", f"{sh}%" if hit else "n/a"]
    L += ["Share of this setup's past signals that, after first falling that far, still rose 10% before ever falling 25.3%. Below 70% the edge is gone. Small samples: read the n.", "By era"]
    for t, en, ev in v['eras']:
        L += [f"{t} n {en}", f"{ev}%" if en else "n/a"]
    L += ["Share that rose 10% and never fell 25.3%.", "Open on the chart →", FOOT]
    return L

# ---------------------------------------------------------------- chart geometry helpers
def fnum(x): return float(x)
def chart_checks(loc, st, cid, mode, osig=None):
    v = cardv(cid); a, tf, tfd = v['a'], v['tf'], int(v['tf'][:-1])
    els = st.svg('#chartSvg')
    if v['ex']:
        exj = json.load(open(f'{S}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
        bars = [(dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date(), Fr(Decimal(str(b['o']))), Fr(Decimal(str(b['h']))), Fr(Decimal(str(b['l']))), Fr(Decimal(str(b['c'])))) for b in exj['bars']]
    else:
        raw = list(csv.DictReader(open(f'{S}/data/{a}_{tf}.csv')))[-70:]
        bars = [(dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date(),) + tuple(Fr(Decimal(r[k])) for k in ('open', 'high', 'low', 'close')) for r in raw]
    forming = v['kind'] == 'forming'; happened = mode == 'happened'
    entry = v['entry']; d0 = v['d0']
    wicks = [e for e in els if e['tag'] == 'line' and e.get('x1') == e.get('x2') and e.get('y1') != '24']
    n_draw = len(bars) if (not v['ex'] or happened) else next(i for i, b in enumerate(bars) if bucket_span(b[0], tfd)[1] == d0) + 1
    T(loc, 'candles drawn (At the alert: none after the entry bar)', len(wicks), n_draw)
    if len(wicks) < 2: return
    x0 = fnum(wicks[0]['x1']); slot = fnum(wicks[1]['x1']) - x0
    # every candle sits in its own slot, in order, at its own high and low
    opens = [b[0] for b in bars]
    while opens[-1] <= d0 + dt.timedelta(days=62): opens.append(bucket_span(opens[-1], tfd)[1] + dt.timedelta(days=1))
    def slot_of_date(d):
        i = 0
        while i + 1 < len(opens) and opens[i + 1] <= d: i += 1
        return i
    def slot_of_x(x): return (fnum(x) - x0) / slot
    # price scale from the candles themselves
    pts = [(float(bars[i][2]), fnum(w['y1'])) for i, w in enumerate(wicks)] + [(float(bars[i][3]), fnum(w['y2'])) for i, w in enumerate(wicks)]
    p1, y1 = max(pts); p2, y2 = min(pts); k = (y2 - y1) / (p2 - p1)
    Y = lambda p: y1 + (float(p) - p1) * k
    P = lambda y: p1 + (fnum(y) - y1) / k
    def PMX(py, mine):
        return (money(mine) if abs(py - float(mine)) < 0.0051 else money(Fr(Decimal(repr(round(py, 2))))), money(mine))
    worst = max(abs(Y(p) - y) for p, y in pts)
    T(loc, 'every candle drawn at its own high and low on one linear price scale (max error, px)', 'ok' if worst < 1e-6 else f'{worst:.6f}', 'ok')
    okx = all(abs(slot_of_x(w['x1']) - i) < 1e-6 for i, w in enumerate(wicks))
    T(loc, 'candles evenly spaced, one slot per bar', 'ok' if okx else 'uneven', 'ok')
    near = lambda a_, b_, tol=1e-6: abs(a_ - b_) <= tol * max(1.0, abs(b_))
    # axis range: what was known
    known = bars[:n_draw] if (v['ex'] and not happened) else bars
    hi_lv = entry * (1 + v['high'] / 100); lo_lv = entry * (1 + v['drop'] / 100)
    lo = min(min(b[3] for b in known), lo_lv, entry * Fr(8, 10)) * Fr(95, 100); hi = max(max(b[2] for b in known), hi_lv) * Fr(107, 100)
    T(loc, 'price axis bottom (from bars known then, the typical drop and entry -20%)', *PMX(P(480), lo))
    T(loc, 'price axis top (from bars known then and the typical high)', *PMX(P(24), hi))
    txt = [e for e in els if e['tag'] == 'text']
    def find_text(pred): return [e for e in txt if pred(e['text'])]
    vl = {}
    for i, e in enumerate(els):
        if e['tag'] == 'line' and e.get('x1') == e.get('x2') and e.get('y1') == '24' and i + 1 < len(els) and els[i + 1]['tag'] == 'text':
            vl[els[i + 1]['text']] = fnum(e['x1'])
    def vcheck(label_pred, exp_label, exp_date, what):
        m = [(t, x) for t, x in vl.items() if label_pred(t)]
        if exp_label is None:
            T(loc, f'{what} line absent', len(m), 0); return None
        if not m:
            T(loc, f'{what} line', '(missing)', exp_label); return None
        t, x = m[0]
        T(loc, f'{what} line label', t, exp_label)
        si = slot_of_x(x); want = slot_of_date(exp_date)
        T(loc, f'{what} line sits on the bar containing {exp_date}', f'bar {si:.3f} ({opens[int(round(si))] if abs(si - round(si)) < 1e-6 and 0 <= round(si) < len(opens) else "?"})', f'bar {want:.3f} ({opens[want]})')
        return x
    e_bar_date = bars[-1][0] if forming else d0
    xT = vcheck(lambda t: t in ('Today', 'Entry'), 'Today' if forming else 'Entry', e_bar_date, 'Today/Entry')
    x60 = vcheck(lambda t: t == 'Day 60', 'Day 60', d0 + dt.timedelta(days=60), 'Day 60')
    xH = vcheck(lambda t: t.startswith('High usually'), f"High usually ~day {v['hday']}", d0 + dt.timedelta(days=int(v['hday'])), 'Typical-high day')
    if forming:
        conf_slot = slot_of_date(d0); today_slot = slot_of_date(bars[-1][0])
        xC = vcheck(lambda t: t.startswith('Confirms'), f"Confirms {date_long(d0)} · entry, day 0" if conf_slot > today_slot else None, d0, 'Confirms')
    T(loc, 'no Day 10 line (the card has its own ladder)', len([t for t in vl if t.startswith('Day 10')]), 0)
    xE = x0 + slot * slot_of_date(d0)
    # horizontal levels
    hl = [e for e in els if e['tag'] == 'line' and e.get('y1') == e.get('y2') and e.get('stroke-width') in ('2', '2.5')]
    exp_levels = [('typical high', hi_lv), ('+10% level', entry * Fr(11, 10)), ('entry', entry), ('typical drop', lo_lv)]
    edge_p = entry * (1 + Fr(v['edge']) / 100) if v['edge'] not in (None, 0) else None
    if edge_p is not None: exp_levels.append(('edge level', edge_p))
    T(loc, 'horizontal level lines drawn', len(hl), len(exp_levels))
    for (nm, p), e in zip(exp_levels, hl):
        T(loc, f'{nm} line price (from its height on the chart)', *PMX(P(e["y1"]), p))
        T(loc, f'{nm} line starts on the entry bar', f'{slot_of_x(e["x1"]):.3f}', f'{slot_of_date(d0):.3f}')
        if nm != 'edge level' or True:
            T(loc, f'{nm} line ends on the day-60 bar', f'{slot_of_x(e["x2"]):.3f}', f'{slot_of_date(d0 + dt.timedelta(days=60)):.3f}')
    tags = [e['text'] for e in txt if e.get('fill') == '#07060F']
    T(loc, 'price tags (typical high, +10%, entry, typical drop)', ' | '.join(sorted(tags)), ' | '.join(sorted(money(p) for nm, p in exp_levels[:4])))
    lab = lambda pre: next((e['text'] for e in txt if e['text'].startswith(pre)), '(missing)')
    T(loc, 'Typical high label', lab('Typical high'), f"Typical high {pct(v['high'])}")
    T(loc, '+10% label', lab('+10%'), f"+10% · {v['r10']}% of past signals got here")
    T(loc, 'Typical drop label', lab('Typical drop'), f"Typical drop {pct(v['drop'])}")
    T(loc, 'Edge label', lab('Edge gone below') if edge_p is not None else str(len([e for e in txt if e['text'].startswith('Edge gone')])),
      f"Edge gone below {money(edge_p)} ({pct(v['edge'], 0)}, before +10%)" if edge_p is not None else '0')
    # zones and ladder bands
    zones = [e for e in els if e['tag'] == 'rect' and e.get('opacity') in ('0.07', '0.1')]
    T(loc, 'shaded zones', len(zones), 2)
    if len(zones) == 2:
        z = zones[0]
        T(loc, 'typical-high zone: from the entry bar', f'{slot_of_x(z["x"]):.3f}', f'{slot_of_date(d0):.3f}')
        T(loc, 'typical-high zone: to the day-60 bar', f'{slot_of_x(fnum(z["x"]) + fnum(z["width"])):.3f}', f'{slot_of_date(d0 + dt.timedelta(days=60)):.3f}')
        T(loc, 'typical-high zone: top price', *PMX(P(z["y"]), hi_lv))
        T(loc, 'typical-high zone: bottom price (entry)', *PMX(P(fnum(z["y"]) + fnum(z["height"])), entry))
        z = zones[1]
        T(loc, 'typical-drop zone: top price (entry)', *PMX(P(z["y"]), entry))
        T(loc, 'typical-drop zone: bottom price', *PMX(P(fnum(z["y"]) + fnum(z["height"])), lo_lv))
        T(loc, 'typical-drop zone: to the day-60 bar', f'{slot_of_x(fnum(z["x"]) + fnum(z["width"])):.3f}', f'{slot_of_date(d0 + dt.timedelta(days=60)):.3f}')
    bands = [(e, els[i + 1]) for i, e in enumerate(els) if e['tag'] == 'rect' and e.get('opacity') == '0.24']
    steps = [(0, -5, v['fe'], v['fex'], v['n'])] + [(-th, -th - 5, sh, shx, hit) for th, hit, sh, shx in v['lad'][:3]]
    T(loc, 'ladder bands drawn', len(bands), 4)
    for (a1, b1, sh, shx, nn), (r, t) in zip(steps, bands):
        nm = 'from entry' if a1 == 0 else f'after falling {-a1}% first'
        T(loc, f'ladder band {nm}: text (share and n)', t['text'], f'{sh}% · n {nn}' if nn else 'n/a')
        T(loc, f'ladder band {nm}: top price', *PMX(P(r["y"]), entry * Fr(100 + a1, 100)))
        ybot = fnum(r['y']) + fnum(r['height'])
        bp = entry * Fr(100 + b1, 100)
        T(loc, f'ladder band {nm}: bottom price', PMX(P(ybot), bp)[0] if ybot < 480 - 1e-6 else 'axis bottom', money(bp) if Y(bp) < 480 - 1e-6 else 'axis bottom')
        T(loc, f'ladder band {nm}: colour (exact share vs 70%)', r['cssFill'], 'var(--closed)' if not nn else 'var(--high)' if shx >= 70 else 'var(--drop)')
        T(loc, f'ladder band {nm}: starts on the entry bar', f'{slot_of_x(r["x"]):.3f}', f'{slot_of_date(d0):.3f}')
    # x-axis date labels and y-axis grid labels
    for e in txt:
        if e.get('fill') == '#7E78A3':
            si = slot_of_x(e['x']); i = int(round(si)); d = opens[min(i, len(opens) - 1)]
            T(loc, f'x-axis date label at bar {i}', e['text'], f'{d.day:02d} {MON[d.month - 1]}')
        if re.fullmatch(r'\$[\d,]+', e['text']) and e.get('x') == '968':
            T(loc, f'y-axis grid label {e["text"]} height', f'{P(fnum(e["y"]) - 5):.2f}', f'{float(e["text"][1:].replace(",", "")):.2f}')
    circ = [(e, els[i + 1]) for i, e in enumerate(els) if e['tag'] == 'circle']
    if forming:
        ti = next(i for i, b in enumerate(bars) if b[0] == v['tdate'])
        dl = Candles(f'{S}/data/{a}_1D.csv'); lowp = dl.l[dl.pos[dt.date.fromisoformat(v['lowday'])]]
        T(loc, 'low marker count', len(circ), 1)
        if circ:
            c_, t_ = circ[0]
            T(loc, 'low marker label (day the low printed, its price)', t_['text'], f"Low {date_long(v['lowday'])} · {money(lowp)}")
            T(loc, 'low marker on the trough bar', f'{slot_of_x(c_["cx"]):.3f}', f'{ti:.3f}')
            T(loc, 'low marker at the low price', *PMX(P(c_["cy"]), lowp))
    elif v['ex'] and happened:
        m = M['example']['m']; dl = Candles(f'{S}/data/ETH_1D.csv')
        T(loc, 'outcome markers', len(circ), 2)
        for (c_, t_), key, dkey in zip(circ, ('up', 'dd'), ('dpk', 'ddday')):
            day = d0 + dt.timedelta(days=m[dkey]); kk = dl.pos[day]; price = dl.h[kk] if key == 'up' else dl.l[kk]
            b0, b1 = bucket_span(day, 2); da, db = (b0 - d0).days, (b1 - d0).days
            T(loc, f"'This one' label ({'best' if key == 'up' else 'deepest'})", t_['text'], f"This one: {money(price)} · {pct(m[key])} · " + (f"days {da}–{db}" if db > da else f"day {da}"))
            T(loc, f"'This one' marker on the bar containing day {m[dkey]}", f'{slot_of_x(c_["cx"]):.3f}', f'{slot_of_date(day):.3f}')
            T(loc, f"'This one' marker at its price", *PMX(P(c_["cy"]), price))
    else:
        T(loc, 'no outcome markers at the alert / on a live setup', len(circ), 0)
    T(loc, "no 'This one' outcome text unless What happened", len([e for e in txt if e['text'].startswith('This one')]), 2 if (v['ex'] and happened) else 0)

    known_pre = ('Typical high', '+10%', 'Typical drop', 'Edge gone below', 'Low ', 'This one', 'Today', 'Entry', 'High usually', 'Day 60', 'Confirms')
    left = [e['text'] for e in txt if not (e.get('fill') in ('#7E78A3', '#07060F') or e.get('x') == '968' or e['text'].startswith(known_pre) or re.fullmatch(r'\d+% · n \d+|n/a', e['text']))]
    T(loc, 'no text on the chart that was not checked above', ' | '.join(left), '')
    # ---- title, subtitle
    if v['ex']:
        T(loc, 'chart title', st.text('#chTitle'), 'ETH · 2-day · example: past confirmed setup')
        T(loc, 'chart subtitle', st.text('#chSub'), f"Confirmed {date_long('2024-09-22')} · entry close {money(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them."
          + ("" if happened else " The shaded zones are the next 60 days, as the odds draw them."))
    elif forming:
        T(loc, 'chart title', st.text('#chTitle'), f"{a} · {tf} · " + ("setup forming" if v['top'] else "forming, not top grade"))
        T(loc, 'chart subtitle', st.text('#chSub'), f"Low {date_long(v['lowday'])} · confirms {date_long(d0)} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them.")
    else:
        T(loc, 'chart title', st.text('#chTitle'), f"{a} · {tf} · live setup, day {osig['elapsed']} of 60")
        T(loc, 'chart subtitle', st.text('#chSub'), f"Confirmed {date_long(d0)} · entry close {money(entry)}. Zones use this setup's own card ({v['basis']}). The shaded zones are the next 60 days, as the odds draw them.")
    # ---- cloud
    pp = M['ex_paths'] if v['ex'] else M['paths'][a]
    T(loc, 'cloud heading', st.text('#cloudSub'), f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {pp['n']}" if v['ex'] else f"Every past {a} top-grade signal, n {pp['n']}")
    last = pp['days'][60]
    T(loc, 'cloud note', st.text('#cloudNote'), "━ median path █ middle half of outcomes" + (" ━ this signal" if happened else "") + f". Day 60: median {pct(last['med'])}, middle half {pct(last['q25'])} to {pct(last['q75'])}. Daily closes."
      + ("" if v['top'] else " Top-grade signals only; the selected setup isn't top grade."))
    cl = st.svg('#cloudSvg'); ct = {e['text']: e for e in cl if e['tag'] == 'text'}
    cy = lambda val: fnum(ct['+100%']['y']) - 5 + (100 - max(-40.0, min(100.0, float(val)))) * ((fnum(ct['-40%']['y']) - fnum(ct['+100%']['y'])) / 140)
    cx = lambda d: fnum(ct['Day 0']['x']) + d * (fnum(ct['Day 60']['x']) - fnum(ct['Day 0']['x'])) / 60
    poly = [e for e in cl if e['tag'] == 'polyline']; pg = [e for e in cl if e['tag'] == 'polygon']
    pts_of = lambda e: [tuple(float(z) for z in p.split(',')) for p in e['points'].split()]
    med = pts_of(poly[0]); bad = sum(1 for d, (x, y) in enumerate(med) if not (near(x, cx(d)) and near(y, cy(pp['days'][d]['med']))))
    T(loc, 'cloud median line: 61 points at my daily medians (points off)', f'{len(med)} points, {bad} off', '61 points, 0 off')
    band = pts_of(pg[0]); exp_band = [(cx(d), cy(pp['days'][d]['q75'])) for d in range(61)] + [(cx(d), cy(pp['days'][d]['q25'])) for d in range(60, -1, -1)]
    bad = sum(1 for (x, y), (ex_, ey_) in zip(band, exp_band) if not (near(x, ex_) and near(y, ey_)))
    T(loc, 'cloud middle-half band: 122 points at my quartiles (points off)', f'{len(band)} points, {bad} off', '122 points, 0 off')
    T(loc, "cloud: 'this signal' line only in What happened", len(poly) - 1, 1 if (v['ex'] and happened) else 0)
    if v['ex'] and happened and len(poly) > 1:
        dl = Candles(f'{S}/data/ETH_1D.csv'); me = [(0, Fr(0))] + [(k, (dl.c[dl.pos[d0 + dt.timedelta(days=k)]] / entry - 1) * 100) for k in range(2, 61, 2)]
        got = pts_of(poly[1]); bad = sum(1 for (x, y), (d, val) in zip(got, me) if not (near(x, cx(d)) and near(y, cy(val))))
        T(loc, "cloud 'this signal' line: day 0 and the 30 two-day closes to day 60 (points off)", f'{len(got)} points, {bad} off', '31 points, 0 off')
    # ---- side box
    side = lines(st.text('#chartSide'))
    E = ["What the card says", f"{a} {tf}" + (" · example" if v['ex'] else "") + f" · from {v['basis']}" + (" · odds as of the entry close, not from today" if v['kind'] == 'open' else ""),
         f"{v['r10']}%", f"rose 10% within 60 days, from {v['n']} past signals; {v['surv']}% without ever falling 25.3%",
         "Typical high", f"{pct(v['high'])} · {money(hi_lv)}", "+10% level", money(entry * Fr(11, 10)), "Reached +20% within 60 days", f"{v['r20']}%",
         "Typical drop", f"{pct(v['drop'])} · {money(lo_lv)}", "Edge gone below",
         "below the bar already" if v['edge'] == 0 else "holds at every level" if v['edge'] is None else f"{money(edge_p)} ({pct(v['edge'], 0)})"]
    if forming: E.append("Prices use the latest price (today's bar is still open) as a stand-in for the entry.")
    E.append("Bands beside the entry: this setup's own ladder. From entry, then after first falling 5%, 10% and 15%: the share of its past signals that still rose 10% before ever falling 25.3%, with the number of signals.")
    if v['kind'] == 'open':
        E += [f"Live: day {osig['elapsed']} of 60", "Best so far", pct(osig['best']), "Worst so far", pct(osig['worst']), "Day 10", "not yet" if osig['d10'] is None else pct(osig['d10'])]
    elif forming:
        E.append(f"Still forming. It confirms only if it holds through {date_long(d0)}, and it can vanish before then." + ("" if v['top'] else " It isn't top grade, so no alert goes out for it."))
    elif happened:
        m = M['example']['m']; dl = Candles(f'{S}/data/ETH_1D.csv')
        def span(dn):
            b0, b1 = bucket_span(d0 + dt.timedelta(days=dn), 2); return f"days {(b0 - d0).days}–{(b1 - d0).days}"
        c10 = (dl.c[dl.pos[d0 + dt.timedelta(days=10)]] / entry - 1) * 100
        E += ["What this one did", "Reached +10% / +20%", f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}", "Best price", f"{pct(m['up'])}, {span(m['dpk'])}",
              "Deepest drop", f"{pct(m['dd'])}, {span(m['ddday'])}", "Day 10 check", f"{'Red' if c10 < 0 else 'Green'}, {pct(c10)}", "Price on day 60", pct(m['ret'])]
    else:
        E += ["This is all a member had at the alert: the zones, the +10% level and the timing. Press", "What happened", "to see the real path."]
    E += ["The lead trader's feed is unavailable right now, so his entries and exits can't be shown.", FOOT]
    cmp_lines(loc + ' side box', side, E)

# ================================================================= run
st = Site(S)
T('page', 'JavaScript errors', len(st.errors), 0)
T('page', 'requests answered 404 (only the trades feed, by the harness)', ' '.join(sorted(set(st.log))), 'http://site.test/data/trades.json')
feed = st.feed
gen = feed['generated_at']
# banner, header, footer
T('page banner', 'review banner', st.text('#review'), f"Review build. Real pipeline data, scored {date_long(M['today'])} (feed {gen[11:16]} UTC). Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run. Show the example card")
T('page header', 'market filter pill', st.text('#filterPill'), f"Market filter: {'on' if M['gate_today'] else 'off'}")
T('page footer', 'feed state', st.text('#feedState'), f"Daily candles closed through {date_long(M['last_closed'])} · updated {gen[11:16]} UTC · checks passed")
T('page footer', 'disclaimer', st.text('footer.foot .fine'), "ETHKROS publishes computed statistics, not personal advice. Odds are statistics based on past signal history and data, entry quality only. Past results don't guarantee future results. Crypto is volatile and leveraged trading can lose more than you put in.")
T('page lead trader', 'lead trader panel (trades feed 404 in this harness)', st.text('#leadBody'), "The lead trader's feed is unavailable right now. His real entries and exits appear here the moment they fill.")
# picker
live_ids = [i for i in M['open_order'] if M['opens'][i]['grade'] == 'A+']
form_ids = sorted([k for k, c in M['cards'].items() if c['_kind'] == 'forming'], key=lambda k: -int(M['cards'][k]['rose10_within60d_pct']))
btn = st.page.evaluate("Array.from(document.querySelectorAll('#picker button')).map(b => [b.dataset.sel, b.innerText])")
T('page picker', 'live buttons (top-grade open signals)', ' '.join(b[0] for b in btn if b[0] in M['opens']), ' '.join(live_ids))
T('page picker', 'forming buttons (set)', ' '.join(sorted(b[0] for b in btn if b[0] not in M['opens'] and b[0] != 'example')), ' '.join(sorted(form_ids)))
# order is a layout choice (definitional note l): top-grade forming cards first, then the rest by their +10% share
rest_shown = [int(M['cards'][b[0]]['rose10_within60d_pct']) for b in btn if b[0] in form_ids and M['cards'][b[0]]['_grade'] != 'A+']
T('page picker', 'below-grade forming buttons ordered by their +10% share, highest first', ' '.join(map(str, rest_shown)), ' '.join(map(str, sorted(rest_shown, reverse=True))))
for sid, text in btn:
    if sid in M['opens']:
        o = M['opens'][sid]
        T('page picker', f'live button {sid}', text, f"{o['chart']} Day {o['elapsed']} best {pct(o['best'])} · worst {pct(o['worst'])}")
    elif sid == 'example':
        T('page picker', 'example button', text, 'Example: ETH 2D, Sep 2024')
    elif sid in M['cards']:
        c = M['cards'][sid]
        T('page picker', f'forming button {sid}', text, f"{c['_a']} {c['_tf']} {c['rose10_within60d_pct']}% rose 10% in 60 days · n {c['_n']} · {'top grade' if c['_grade'] == 'A+' else 'not top grade'} · confirms {date_long(c['_d0'])}")
if not live_ids: T('page picker', 'no live setups text', st.text('#picker .prow .pnone'), 'No live top-grade setups right now.')
if not form_ids: T('page picker', 'nothing forming text', st.page.evaluate("document.querySelectorAll('#picker .prow')[1].querySelector('.pnone').innerText"), 'Nothing forming today.')
# which card the page opens on (layout, note l) -- recorded only
opened = st.page.evaluate("(document.querySelector('#picker button[aria-pressed=\"true\"]')||{dataset:{}}).dataset.sel")
print('page opens on', opened)
best_forming = next((b[0] for b in btn if b[0] in form_ids and M['cards'][b[0]]['_grade'] == 'A+'), form_ids[0] if form_ids else None)
# previous signals column
pv = lines(st.text('.prev'))
E = ["Previous signals", "updates each close", "Edge intact"]
intact = [i for i in live_ids if M['opens'][i]['status'] == 'intact']; fading = [i for i in live_ids if M['opens'][i]['status'] == 'lost']
mini = lambda i, lost: [M['opens'][i]['chart'], f"Day {M['opens'][i]['elapsed']} of 60 · best {pct(M['opens'][i]['best'])} · worst {pct(M['opens'][i]['worst'])}", "Edge lost" if lost else "On track"]
E += sum([mini(i, False) for i in intact], []) if intact else ["No open top-grade setup with its edge intact."]
E.append("Edge lost or closed"); E += sum([mini(i, True) for i in fading], [])
order = sorted(range(len(M['aplus'])), key=lambda i: M['aplus'][i]['entry'], reverse=True)
recent = []
for e_ in sorted({M['aplus'][i]['entry'] for i in order}, reverse=True):
    recent += [M['aplus'][i] for i in range(len(M['aplus'])) if M['aplus'][i]['entry'] == e_]
for r in recent[:5]:
    E += [r['chart'], f"{date_long(r['entry'])} · best {pct(r['best'])} · worst {pct(r['dd'])}", "Reached +20%" if r['r20'] else "Rose 10%" if r['r10'] else "Missed"]
E.append("See every past signal, misses included")
cmp_lines('page previous signals', pv, E)

# every card: live, forming, example
def select(sid):
    st.click(f'#picker button[data-sel="{sid}"]')
sel_list = live_ids + form_ids + (['example'] if 'example' in M['cards'] else [])
for sid in sel_list:
    st.click('#tab-now'); select(sid)
    osig = M['opens'].get(sid)
    loc = f'page card {sid}'
    cmp_lines(loc, lines(st.text('#card')), expected_card(sid, best_forming, osig))
    v = cardv(sid)
    # the bars' widths carry numbers too
    w = st.page.evaluate("Array.from(document.querySelectorAll('#ladder .bar .f, #eras .bar .f')).map(e => [e.style.width, e.classList.contains('gone')])")
    expw = [(f"{v['fe']}%", v['fex'] < 70)] + [((f"{sh}%" if hit else "0%"), bool(hit) and shx < 70) for th, hit, sh, shx in v['lad']] + [((f"{ev}%" if en else "0%"), False) for t, en, ev in v['eras']]
    T(loc, 'ladder and era bar widths, and which rows are marked below the 70% bar (exact share)', ' '.join(f"{a}{'*' if g else ''}" for a, g in w), ' '.join(f"{a}{'*' if g else ''}" for a, g in expw))
    dim = st.page.evaluate("document.querySelector('#card .big').style.opacity")
    T(loc, 'big number dimmed only when a live setup has lost its edge', dim or '1', '0.5' if (osig and osig['status'] == 'lost') else '1')
    # chart
    st.click('#tab-chart'); st.page.wait_for_timeout(350)
    T(loc + ' chart', 'At the alert / What happened toggle shown only for the example', str(st.page.evaluate("document.querySelector('.toggle').hidden")).lower(), 'false' if sid == 'example' else 'true')
    chart_checks(loc + ' chart' + (' (At the alert)' if sid == 'example' else ''), st, sid, 'alert', osig)
    if sid == 'example':
        st.click('#bHap'); st.page.wait_for_timeout(350)
        chart_checks(loc + ' chart (What happened)', st, sid, 'happened', osig)
        st.click('#bAlert'); st.page.wait_for_timeout(200)

# the quiet state: no live or forming setup, example switched off
if not live_ids and not form_ids:
    st.click('#tab-now')
    T('page quiet state', 'the page opens on the example when nothing is live or forming', opened, 'example')
    st.page.evaluate("document.querySelector('#previewSwitch').click()"); st.page.wait_for_timeout(250)
    n_year = sum(1 for r in M['aplus'] if '2020-01-01' <= r['entry'] <= '2025-12-31')
    msg = (f"The market filter is on. Nothing at the top grade is forming or confirmed today. Top-grade setups come about {int(rhu(Fr(n_year, 6)))} times a year (2020 to 2025 average)."
           if M['gate_today'] else "The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.")
    cmp_lines('page quiet state', lines(st.text('#card')), ["BTC · ETH", "No setup right now", "Waiting for the next one", msg, "You'll get a push alert the moment one confirms.",
                                                             "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record."])
    st.page.evaluate("document.querySelector('#previewSwitch').click()"); st.page.wait_for_timeout(250)
# Past signals tab
st.click('#tab-record'); st.page.wait_for_timeout(200)
T('page past signals', 'heading', st.text('#view-record .sec-title'), 'Every top-grade signal whose 60 days have closed · computed, never traded')
T('page past signals', 'footnote', st.text('#view-record p.fine'), "Computed signals, not trades. Each row is a signal at its confirmation close, measured over the next 60 days. There is no exit in the data, so this is entry quality, not a return or a track record.")
for asset in ('all', 'ETH', 'BTC'):
    st.click(f'.seg button[data-asset="{asset}"]')
    loc = f'page past signals ({asset})'
    rows = [r for r in recent if asset == 'all' or r['asset'] == asset]
    T(loc, 'count line', st.text('#recCount'), f"{len(rows)} signals · {sum(1 for r in rows if not r['r10'])} missed +10%")
    got = st.page.evaluate("Array.from(document.querySelectorAll('#recBody tr')).map(tr => Array.from(tr.children).map(td => td.innerText))")
    T(loc, 'table rows', len(got), len(rows))
    for g, r in zip(got, rows):
        rl = f"{loc} {r['chart']} {r['entry']}"
        T(rl, 'Confirmed', g[0], date_long(r['entry'])); T(rl, 'Chart', g[1], r['chart']); T(rl, 'Entry close', g[2], money(r['price']))
        T(rl, 'Rose 10%', g[3], 'Yes' if r['r10'] else 'No'); T(rl, 'Reached +20%', g[4], 'Yes' if r['r20'] else 'No')
        T(rl, 'Best', g[5], pct(r['best'])); T(rl, 'Deepest drop', g[6], pct(r['dd'])); T(rl, 'Day 60', g[7], pct(r['ret'])); T(rl, 'High on day', g[8], str(r['dpk']))
    boxes = [lines(x) for x in st.texts('#recSum .sidebox')]
    want = [a for a in ('ETH', 'BTC') if asset in ('all', a)]
    T(loc, 'summary boxes', len(boxes), len(want))
    for b, a in zip(boxes, want):
        g = M['gstat'][(a, 'A+')]; mi = M['misses'][(a, 'A+')]
        cmp_lines(f'{loc} summary {a}', b, [a, f"{g['n']} signals", "Rose 10% in 60 days", f"{g['r10']}%", "Reached +20% in 60 days", f"{g['r20']}%", "Rose 10%, never fell 25.3%", f"{g['surv']}%",
                                            "Median deepest dip", pct(g['meddip']), "Misses: median best price", pct(mi['median_peak_pct'])])
T('page past signals', 'table header', ' | '.join(st.page.evaluate("Array.from(document.querySelectorAll('#view-record th')).map(e => e.innerText)")), 'Confirmed | Chart | Entry close | Rose 10% | Reached +20% | Best | Deepest drop | Day 60 | High on day')
# How to read
st.click('#tab-read'); st.page.wait_for_timeout(150)
T('page how to read', 'posting bar', st.text('#howBar'), '70% bar')
hr = norm_ws(st.text('#view-read'))
for phrase in ("rose 10% within 60 days of the entry close", "without ever falling 25.3% below the entry close, where 3.3x leverage with 5% maintenance margin liquidates",
               "after it first falls 5%, 10%, 15% or 20%, the share of its past signals that still rose 10% before ever falling 25.3%",
               "The first fall at which this setup's odds drop below our 70% bar.", "They measure the quality of the entry, not a trading result.",
               "Of the past signals that did not rise 10% within 60 days, how many went above entry at some point in the 60 days, and the median best price of all those misses within the 60 days."):
    T('page how to read', f'text present: {phrase[:70]}', 'yes' if phrase in hr else 'no', 'yes')
T('page how to read', '3.3x with 5% maintenance liquidates 25.3% below entry (1/3.3 - 0.05)', '25.3', str(float(rhu((Fr(10, 33) - Fr(5, 100)) * 100, 1))))
st.close()

bad = [x for x in C.rows if x[5] == 'NO']
print('PAGE TOTAL', len(C.rows), 'disagreements', len(bad))
for x in bad: print('  ', x[1:5])
csv.writer(open(f'checks_page_{NAME}.csv', 'w', newline='')).writerows(C.rows)
