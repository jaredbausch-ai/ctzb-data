"""Item 8: every number the page shows vs my values."""
import csv, datetime as dt, json, os, pickle, re, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = sys.argv[1]
NAME = os.path.basename(STATE.rstrip('/'))
P = pickle.load(open(os.path.join(HERE, f'sig_{NAME}.pkl'), 'rb'))
NOW, SIG = P['NOW'], P['SIG']; TODAY = NOW.date()
L = pickle.load(open(os.path.join(HERE, f'led_{NAME}.pkl'), 'rb')); LG, groups = L['LG'], L['groups']
M = pickle.load(open(os.path.join(HERE, f'mine_{NAME}.pkl'), 'rb')); MYC = M['MYCARDS']; EXPO = M['exp_open']
PG = json.load(open(os.path.join(HERE, f'page_{NAME}.json')))
feed = json.load(open(os.path.join(STATE, 'feed', 'ctzb_feed.json')))
daily = {a: Daily(STATE, a, NOW) for a in ('ETH', 'BTC')}
G = gate(STATE)
OUT = []
MINUS = '−'


def chk(loc, label, shown, mine, cause=''):
    ok = str(shown) == str(mine)
    OUT.append(dict(state=NAME, location=loc, label=label, shown=shown, yours=mine, ok=ok, cause='' if ok else cause))
    return ok


def pct(v, d=1, sign=True):
    if v is None: return 'n/a'
    r = rha(v, d)
    s = f'{abs(r):.{d}f}'
    if r == 0: return ('0' if d == 0 else '0.' + '0' * d) + '%'
    return ('+' if (r > 0 and sign) else '' if r > 0 else MINUS) + s + '%'


def money(v):
    return '$' + f'{rha(v, 2):,.2f}'


MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
def dlong(d):
    d = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d))
    return f'{d.day} {MON[d.month - 1]} {d.year}'


# ---------------- my per-card model (expected display values)
def misses_of(G_):
    Ms = [s for s in G_ if not s['m']['r10']]
    if not Ms: return None
    return dict(signals=len(G_), misses=len(Ms), up_first=sum(max(h for h, l in s['m']['w']) > s['e'] for s in Ms),
                med_best=st.median([r6(s['m']['up']) for s in Ms]), med_worst=st.median([r6(s['m']['dd']) for s in Ms]),
                med_d60=st.median([r6(s['m']['ret']) for s in Ms]))


def model(key, a, grade, Gx_override=None):
    """Recompute the expected card numbers from my own sample (MYC[key] holds G-derived exacts)."""
    mc = MYC[key]
    return mc


def card_numbers(c, key):
    """My values for a feed card: re-derive from my ledger using the same rule as checks2 (already verified equal to feed);
    here I rebuild them so the page is compared against MY numbers, not the feed's."""
    a, tf = c['asset'], c['timeframe']
    lenses = set() if c['confirmations'] in ('none', '-', '') else set(c['confirmations'].split('; '))
    PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
             'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
             'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
             'CT recovering fast from the low': 'FASTCT'}
    lenses = {PLAIN.get(x, x) for x in lenses}
    base = LG if key != 'example_card' else [s for s in LG if s['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
    ll = lambda s: set() if s['lenses'] in ('-', '') else set(s['lenses'].split(' + '))
    ex = [s for s in base if s['chart'] == f'{a} {tf}' and ll(s) == lenses]
    sg = [s for s in base if s['chart'] == f'{a} {tf}' and s['grade'] == c['grade']]
    ag = [s for s in base if s['a'] == a and s['grade'] == c['grade']]
    Gx = ex if len(ex) >= 15 else sg if len(sg) >= 15 else ag
    n = len(Gx); pc = lambda k: rha(100 * k / n)
    nn, ok, liq = from_entry(Gx)
    rows = []
    for th in (5, 10, 15, 20):
        h, o, q = ladder_row(Gx, th)
        rows.append(dict(th=th, n=h, v=rha(100 * o / h) if h else None, x=100 * o / h if h else None))
    x0 = 100 * ok / nn
    edge = 0 if x0 < 70 else next((-r['th'] for r in rows if r['x'] is not None and r['x'] < 70), None)
    old = [s for s in Gx if s['d0'] < dt.date(2022, 1, 1)]; new = [s for s in Gx if s['d0'] >= dt.date(2022, 1, 1)]
    sv = lambda X: rha(100 * sum(s['m']['surv10'] for s in X) / len(X)) if X else None
    medfull = lambda k: st.median([s['m'][k] for s in Gx])
    return dict(n=n, r10=pc(sum(s['m']['r10'] for s in Gx)), s10=pc(sum(s['m']['surv10'] for s in Gx)), r20=pc(sum(s['m']['r20'] for s in Gx)),
                t30=pc(sum(s['m']['t30'] for s in Gx)), high=medfull('up'), drop=medfull('dd'), dipb=medfull('ddpk'),
                high6=st.median([r6(s['m']['up']) for s in Gx]), drop6=st.median([r6(s['m']['dd']) for s in Gx]), dipb6=st.median([r6(s['m']['ddpk']) for s in Gx]),
                hday=rha(st.median([s['m']['dpk'] for s in Gx])), lday=rha(st.median([s['m']['ddday'] for s in Gx])),
                fe=rha(x0), fex=x0, rows=rows, edge=edge, eras=[('Before 2022', len(old), sv(old)), ('Since 2022', len(new), sv(new))], G=Gx)


def check_card_text(loc, txt, ladder, eras, c, kind, cn, mi, entry, line, below, best_forming):
    lines = [x.strip() for x in txt.split('\n') if x.strip()]
    J = '\n'.join(lines)
    def has(label, s, cause='display'):
        chk(loc, label, s if s in J else f'(not found) {s}', s, cause)
    a, tf = c['asset'], c['timeframe']
    chk(loc, 'where', lines[0], f"{a} · {tf} CHART" + (' · EXAMPLE' if kind == 'example' else ''))
    chk(loc, 'state', lines[1], {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind])
    chk(loc, 'card line', lines[2], line)
    if below:
        chk(loc, 'below-grade note', lines[3], ('Best setup forming today.' if best_forming else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
    has('big number', f"{cn['r10']}%\nrose 10% within 60 days\n{cn['s10']}% did it without ever falling 25.3%\nfrom {cn['n']} past signals like this one · every figure covers the 60 days after entry")
    has('typical high', f"Typical high\n{pct(cn['high'])}")
    if pct(cn['high']) != pct(cn['high6']): chk(loc, 'typical high (6dp median)', pct(cn['high']), pct(cn['high6']), 'precision')
    has('typical drop', f"Typical drop from entry\n{pct(cn['drop'])}")
    if pct(cn['drop']) != pct(cn['drop6']): chk(loc, 'typical drop (6dp median)', pct(cn['drop']), pct(cn['drop6']), 'precision')
    et = f"Below the 70% bar from entry" if cn['edge'] == 0 else (f"{pct(cn['edge'], 0)} before it rises 10%" if cn['edge'] is not None else 'Holds at every level')
    has('edge gone', f"Edge gone below\n{et}")
    has('if it misses', f"If it misses: went above entry\n{mi['up_first']} of {mi['misses']} · median best {pct(mi['med_best'])}" if mi else 'If it misses: went above entry\nn/a')
    if below:
        has('misses pool', f"all {mi['signals']} {a} signals of this grade")
    has('dip before high', f"Dip before the high, from entry\n{pct(cn['dipb'])}")
    if pct(cn['dipb']) != pct(cn['dipb6']): chk(loc, 'dip before high (6dp median)', pct(cn['dipb']), pct(cn['dipb6']), 'precision')
    has('high day', f"High lands around\nDay {cn['hday']}")
    has('reached +20%', f"Reached +20% within 60 days · n {cn['n']}\n{cn['r20']}%")
    has('touched -30%', f"Touched {MINUS}30% within 60 days · n {cn['n']}\n{cn['t30']}%")
    has('deepest dip day', f"Deepest dip lands around\nDay {cn['lday']}")
    g = c['grade']
    has('misses worst drop', f"Typical worst drop, misses · {mi['misses']} misses of all {mi['signals']} {a} {g}\n{pct(mi['med_worst'])}")
    has('misses day 60', f"Typical change by day 60, misses · {mi['misses']} misses of all {mi['signals']} {a} {g}\n{pct(mi['med_d60'])}")
    # ladder
    exp = [(f"From entry n {cn['n']}", cn['fe'], cn['fex'] < 70)] + [(f"Falls {r['th']}% first n {r['n']}", r['v'], r['x'] is not None and r['x'] < 70) for r in cn['rows']]
    chk(loc, 'ladder rows', len(ladder), len(exp))
    for (t, v, gone), sh in zip(exp, ladder):
        chk(loc, f'ladder {t.split(" n ")[0]}', sh['text'].replace('\n', ' | '), f"{t} | {'n/a' if v is None else str(v) + '%'}")
        chk(loc, f'ladder {t.split(" n ")[0]} gone colour (exact < 70)', sh['gone'], gone)
        chk(loc, f'ladder {t.split(" n ")[0]} bar width', sh['w'], f"{v if v is not None else 0}%")
    chk(loc, 'era rows', len(eras), 2)
    for (t, n_, v), sh in zip(cn['eras'], eras):
        chk(loc, f'era {t}', sh['text'].replace('\n', ' | '), f"{t} n {n_} | {'n/a' if v is None else str(v)}%")
    return J


# ---------------- per selection
sel_by = {s['sel']: s for s in PG['selections']}
open_A = [o for o in feed['open_signals'] if o['grade'] == 'A+']
forming = feed['cards']
best_id = (sorted([c for c in forming if c['grade'] == 'A+'], key=lambda c: 0) or sorted(forming, key=lambda c: -(c['rose10_within60d_pct'] or -1)) or [None])[0]
for c in [o['card'] for o in open_A] + forming + [feed['example_card']]:
    pass

def candles_bars(a, tf):
    rows = list(csv.DictReader(open(os.path.join(STATE, f'datasets/candles_{a.lower()}_{tf.lower()}.csv'))))
    return [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in rows]

# candle files served to the page vs raw data
for a in ('ETH', 'BTC'):
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        cb = candles_bars(a, tf)
        raw = list(csv.DictReader(open(os.path.join(STATE, 'data', f'{a}_{tf}.csv'))))[-70:]
        chk(f'candles {a} {tf}', 'last 70 bars equal raw data', [(b['t'], b['o'], b['h'], b['l'], b['c']) for b in cb] == [(int(r['time']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in raw], True)

# example json vs raw ETH 2D
EXJ = json.load(open(os.path.join(STATE, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
raw2 = {int(r['time']): r for r in csv.DictReader(open(os.path.join(STATE, 'data', 'ETH_2D.csv')))}
for i, b in enumerate(EXJ['bars']):
    r = raw2.get(b['t'])
    chk('example json', f'bar {i} {udate(b["t"])}', (b['o'], b['h'], b['l'], b['c']), None if r is None else (float(r['open']), float(r['high']), float(r['low']), float(r['close'])), 'static example file vs raw candles')
chk('example json', 'entry_index bar closes 2024-09-22', str(bucket_end(udate(EXJ['bars'][EXJ['entry_index']]['t']), '2D')), '2024-09-22')
chk('example json', 'entry_close', EXJ['entry_close'], rha(daily['ETH'].b[daily['ETH'].pos[dt.date(2024, 9, 22)]]['c'], 2))
chk('example json', 'bars cover 60 days after entry', bucket_end(udate(EXJ['bars'][-1]['t']), '2D') >= dt.date(2024, 11, 21), True)

def nextopen(t, tfd):
    if tfd == 1: return t + 86400
    d = udate(t); e = bucket_end(d, f'{tfd}D')
    return int(dt.datetime.combine(e + dt.timedelta(days=1), dt.time(), dt.timezone.utc).timestamp())

def ts(d): return int(dt.datetime.combine(d, dt.time(), dt.timezone.utc).timestamp())

def svg_find(svg, prefix):
    return [e for e in svg if e['tag'] == 'text' and e.get('text', '').startswith(prefix)]

def check_chart(loc, ch, kind, c, cn, entry, bars, E, tfd, entry_day, happened=False, low_day_=None, low_price=None, sample=None):
    Lx, Rx, T, B = 20, 960, 24, 480
    opens = [b['t'] for b in bars]
    forming = kind in ('forming', 'open')
    tE = ts(entry_day)
    if forming:
        while opens[-1] <= tE + 61 * 86400: opens.append(nextopen(opens[-1], tfd))
    nS = len(opens) if forming else len(bars)
    slot = (Rx - Lx) / nS; X = lambda i: Lx + slot * i + slot / 2
    def slot_of_date(d):
        t = ts(d)
        return max(i for i, o in enumerate(opens) if o <= t)
    # my date->bar mapping by the bucket rule, independent of the page's slotOf
    def bar_of(d):
        o = ts(bucket_end(d, f'{tfd}D') - dt.timedelta(days=0)) if tfd == 1 else None
        if tfd == 1: return opens.index(ts(d)) if ts(d) in opens else None
        j1 = dt.date(d.year, 1, 1); start = j1 + dt.timedelta(days=((d - j1).days // tfd) * tfd)
        return opens.index(ts(start)) if ts(start) in opens else None
    svg = ch['svg']
    def vline_x(prefix):
        t = svg_find(svg, prefix)
        return None if not t else round(float(t[0]['x']) - 6, 6)
    xs = lambda i: round(X(i), 6)
    if kind == 'forming':
        chk(loc, 'Today line on the last (open) bar', vline_x('Today'), xs(len(bars) - 1))
        ci = bar_of(dt.date.fromisoformat(c['confirms_on']))
        chk(loc, 'Confirms line on the confirmation bar', vline_x('Confirms'), xs(ci))
        chk(loc, 'Confirms label', svg_find(svg, 'Confirms')[0]['text'] if svg_find(svg, 'Confirms') else None, f"Confirms {dlong(c['confirms_on'])} · entry, day 0")
        xE = xs(ci)
    else:
        chk(loc, 'Entry line on the bar closing on the entry date', vline_x('Entry'), xs(bar_of(entry_day)))
        xE = xs(bar_of(entry_day))
    d60 = bar_of(entry_day + dt.timedelta(days=60)); d60 = min(d60 if d60 is not None else nS - 1, nS - 1)
    chk(loc, 'Day 60 line on the bar containing day 60', vline_x('Day 60'), xs(d60))
    hb = bar_of(entry_day + dt.timedelta(days=cn['hday']))
    chk(loc, 'High line on the bar containing the typical high day', vline_x('High usually'), xs(hb) if hb is not None else None)
    chk(loc, 'High line label', svg_find(svg, 'High usually')[0]['text'], f"High usually ~day {cn['hday']}")
    # zones
    rects = [e for e in svg if e['tag'] == 'rect' and e.get('opacity') in ('0.07', '0.1')]
    for r_ in rects:
        chk(loc, 'zone starts at entry bar', round(float(r_['x']), 6), xE); chk(loc, 'zone ends at day 60 bar', round(float(r_['x']) + float(r_['width']), 6), xs(d60))
    # level labels and price tags
    lvh, lvd = entry * (1 + cn['high'] / 100), entry * (1 + cn['drop'] / 100)
    chk(loc, 'Typical high label', svg_find(svg, 'Typical high')[0]['text'], f"Typical high {pct(cn['high'])}")
    chk(loc, '+10% label', svg_find(svg, '+10%')[0]['text'], f"+10% · {cn['r10']}% of past signals got here")
    chk(loc, 'Typical drop label', svg_find(svg, 'Typical drop')[0]['text'], f"Typical drop {pct(cn['drop'])}")
    tags = sorted([e['text'] for e in svg if e['tag'] == 'text' and e.get('x') == '1018'])
    chk(loc, 'price tags', tags, sorted([money(lvh), money(entry * 1.1), money(entry), money(lvd)]))
    eg = svg_find(svg, 'Edge gone below')
    if cn['edge'] not in (0, None):
        chk(loc, 'edge line label', eg[0]['text'] if eg else None, f"Edge gone below {money(entry * (1 + cn['edge'] / 100))} ({pct(cn['edge'], 0)}, before +10%)")
    else:
        chk(loc, 'edge line absent (no edge level)', bool(eg), False)
    # ladder zone labels (from entry + falls 5/10/15)
    zl = [e['text'] for e in svg if e['tag'] == 'text' and e.get('font-weight') == '700' and e.get('style', '').find('var(--text)') >= 0 and re.fullmatch(r'(\d+%|n/a)', e.get('text', ''))]
    expz = [f"{cn['fe']}%"] + [('n/a' if r['v'] is None else f"{r['v']}%") for r in cn['rows'][:3]]
    chk(loc, 'ladder zone labels on chart', zl, expz)
    # axis scale: only what was known at the alert for the example
    shown = bars[:E + 1] if (kind == 'example' and not happened) else bars
    lo = min(min(b['l'] for b in shown), lvd, entry * 0.8) * 0.95; hi = max(max(b['h'] for b in shown), lvh) * 1.07
    Y = lambda p: B - (p - lo) / (hi - lo) * (B - T)
    ticks = [e for e in svg if e['tag'] == 'text' and e.get('x') == '968']
    for tk in ticks:
        p = float(tk['text'].replace('$', '').replace(',', ''))
        okp = abs(float(tk['y']) - (Y(p) + 5)) < 1e-3
        chk(loc, f"axis tick {tk['text']} position within 0.001px (scale from {'bars to the alert' if kind == 'example' and not happened else 'all bars'})", okp, True)
    # x-axis date labels sit on the slot whose bar opens that day
    MS_ = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
    for tx in [e for e in svg if e['tag'] == 'text' and e.get('y') == '502']:
        i = round((float(tx['x']) - Lx) / slot - 0.5)
        d = udate(opens[min(i, len(opens) - 1)])
        chk(loc, f"x-axis label at slot {i}", tx['text'], f"{d.day:02d} {MS_[d.month - 1]}")
    # ladder zone colours: tested on the exact share (audit #8 rule)
    zr = [e for e in svg if e['tag'] == 'rect' and e.get('opacity') == '0.24']
    expc = [cn['fex']] + [r['x'] for r in cn['rows'][:3]]
    for k, (r_, x_) in enumerate(zip(zr, expc)):
        want = 'var(--closed)' if x_ is None else 'var(--high)' if x_ >= 70 else 'var(--drop)'
        chk(loc, f'ladder zone {k} colour (exact share vs 70%)', r_.get('style', ''), f'fill: {want};', 'zone colour tested on rounded share')
    # candles drawn
    wicks = [e for e in svg if e['tag'] == 'line' and e.get('stroke-width') == '1.5' and e.get('y1') != str(T)]
    chk(loc, 'candles drawn', len(wicks), len(bars) if (forming or happened) else E + 1)
    if kind == 'forming' and low_day_ is not None:
        lt = svg_find(svg, 'Low ')
        chk(loc, 'Low marker label', lt[0]['text'] if lt else None, f"Low {dlong(low_day_)} · {money(low_price)}")
        circ = [e for e in svg if e['tag'] == 'circle']
        li = bar_of(dt.date.fromisoformat(c['low_date']))
        chk(loc, 'Low circle on the trough bar', round(float(circ[0]['cx']), 6) if circ else None, xs(li))
    # side box
    side = '\n'.join(x.strip() for x in ch['side'].split('\n') if x.strip())
    def has(label, s):
        chk(loc, label, s if s in side else f'(not found) {s}', s, 'display')
    has('side: source', f"{c['chart']} · from {sample}" if kind != 'example' else f"{c['chart']} · example")
    has('side: big', f"{cn['r10']}%\nrose 10% within 60 days, from {cn['n']} past signals; {cn['s10']}% without ever falling 25.3%")
    has('side: typical high', f"Typical high\n{pct(cn['high'])} · {money(lvh)}")
    has('side: +10% target', f"+10% target\n{money(entry * 1.1)}")
    has('side: +20%', f"Reached +20% within 60 days\n{cn['r20']}%")
    has('side: typical drop', f"Typical drop\n{pct(cn['drop'])} · {money(lvd)}")
    eg_txt = 'below the bar already' if cn['edge'] == 0 else ('holds at every level' if cn['edge'] is None else f"{money(entry * (1 + cn['edge'] / 100))} ({pct(cn['edge'], 0)})")
    has('side: edge', f"Edge gone below\n{eg_txt}")
    return side


def cloud_check(loc, ch, G_, label):
    P = []
    for s in G_:
        dd = daily[s['a']]; p = [0.0]
        for k in range(1, 61):
            i = dd.pos.get(s['d0'] + dt.timedelta(days=k)); p.append((dd.b[i]['c'] / s['e'] - 1) * 100)
        P.append(p)
    q = {f: [rha(q7([p[k] for p in P], f), 1) for k in range(61)] for f in (.25, .5, .75)}
    chk(loc, 'cloud subtitle', ch['cloudSub'], label.format(n=len(P)))
    note = ch['cloudNote']
    chk(loc, 'cloud day-60 note', re.search(r'Day 60:.*?Daily closes\.', note).group(0), f"Day 60: median {pct(q[.5][60])}, middle half {pct(q[.25][60])} to {pct(q[.75][60])}. Daily closes.")
    # median polyline points
    Lx, Rx, T, B, P0, P1 = 20, 960, 12, 230, -40, 100
    Xd = lambda d: Lx + (Rx - Lx) * d / 60; Yv = lambda v: B - (max(P0, min(P1, v)) - P0) / (P1 - P0) * (B - T)
    pl = [e for e in ch['cloud'] if e['tag'] == 'polyline']
    pts = [tuple(map(float, x.split(','))) for x in pl[0]['points'].split()]
    chk(loc, 'cloud median line: 61 points', len(pts), 61)
    bad = [k for k, (x, y) in enumerate(pts) if abs(x - Xd(k)) > 1e-9 or abs(y - Yv(q[.5][k])) > 1e-9]
    chk(loc, 'cloud median line points = my medians', bad, [])
    poly = [e for e in ch['cloud'] if e['tag'] == 'polygon'][0]
    pp = [tuple(map(float, x.split(','))) for x in poly['points'].split()]
    exp = [(Xd(k), Yv(q[.75][k])) for k in range(61)] + [(Xd(k), Yv(q[.25][k])) for k in reversed(range(61))]
    chk(loc, 'cloud middle-half band = my quartiles', [k for k, (u, v) in enumerate(zip(pp, exp)) if abs(u[0] - v[0]) > 1e-9 or abs(u[1] - v[1]) > 1e-9], [])


misses_grade = {}
for (a, g), G_ in groups.items():
    if g in ('A+', 'A', 'B', 'C'): misses_grade[(a, g)] = misses_of(G_)

fsorted = sorted(forming, key=lambda c: -(c['rose10_within60d_pct'] if c['rose10_within60d_pct'] is not None else -1))
best_forming_id = fsorted[0]['signal_id'] if fsorted else None

for s in PG['selections']:
    sid = s['sel']
    if sid == 'example':
        c = feed['example_card']; key = 'example_card'; kind = 'example'
        cn = card_numbers(c, key)
        known = [x for x in groups[('ETH', 'A+')] if x['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
        mi = misses_of(known)
        sx = next(x for x in SIG[('ETH', '2D')]['sig'] if x['d0'] == dt.date(2024, 9, 22))
        entry = sx['e']; line = f"Example: confirmed {dlong('2024-09-22')} · entry close {money(entry)}"
        check_card_text('page example card', s['card'], s['ladder'], s['eras'], c, kind, cn, mi, entry, line, False, False)
        bars = EXJ['bars']; E = EXJ['entry_index']
        check_chart('page example chart (at the alert)', s['chart_alert'], 'example', c, cn, entry, bars, E, 2, dt.date(2024, 9, 22))
        chk('page example chart (at the alert)', 'title', s['chart_alert']['title'], 'ETH · 2-DAY · EXAMPLE: PAST CONFIRMED SETUP')
        chk('page example chart (at the alert)', 'subtitle', s['chart_alert']['sub'], f"Confirmed {dlong('2024-09-22')} · entry close {money(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them. The shaded zones are the next 60 days, as the odds draw them.")
        chk('page example chart (at the alert)', 'no outcome markers at the alert', [e['text'] for e in s['chart_alert']['svg'] if e['tag'] == 'text' and e.get('text', '').startswith('This one')], [])
        cloud_check('page example chart (at the alert)', s['chart_alert'], known, 'ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {n}')
        if 'chart_happened' in s:
            ch = s['chart_happened']; loc = 'page example chart (what happened)'
            check_chart(loc, ch, 'example', c, cn, entry, bars, E, 2, dt.date(2024, 9, 22), happened=True)
            cloud_check(loc, ch, known, 'ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {n}')
            w = daily['ETH'].window(dt.date(2024, 9, 22))
            hi = max(w, key=lambda kb: (kb[1]['h'], -kb[0])); lo_ = min(w, key=lambda kb: (kb[1]['l'], kb[0]))
            d10 = [b for k, b in w if k == 10][0]; d60 = [b for k, b in w if k == 60][0]
            span = lambda k: (k - 1, k) if k % 2 == 0 else (k, k + 1)   # 2D bars cover days (1,2),(3,4)... after a bar ending on day 0
            side = '\n'.join(x.strip() for x in ch['side'].split('\n') if x.strip())
            def has(label, t):
                chk(loc, label, t if t in side else f'(not found) {t}', t, 'display')
            has('side: reached', f"Reached +10% / +20%\n{'Yes' if hi[1]['h'] >= entry * 1.1 else 'No'} / {'Yes' if hi[1]['h'] >= entry * 1.2 else 'No'}")
            a1, b1 = span(hi[0]); a2, b2 = span(lo_[0])
            has('side: best price', f"Best price\n{pct((hi[1]['h'] / entry - 1) * 100)}, days {a1}–{b1}")
            has('side: deepest drop', f"Deepest drop\n{pct((lo_[1]['l'] / entry - 1) * 100)}, days {a2}–{b2}")
            has('side: day 10', f"Day 10 check\n{'Red' if d10['c'] < entry else 'Green'}, {pct((d10['c'] / entry - 1) * 100)}")
            has('side: day 60', f"Price on day 60\n{pct((d60['c'] / entry - 1) * 100)}")
            ot = sorted(e['text'] for e in ch['svg'] if e['tag'] == 'text' and e.get('text', '').startswith('This one'))
            chk(loc, 'outcome markers', ot, sorted([f"This one: {money(hi[1]['h'])} · {pct((hi[1]['h'] / entry - 1) * 100)} · days {a1}–{b1}",
                                                     f"This one: {money(lo_[1]['l'])} · {pct((lo_[1]['l'] / entry - 1) * 100)} · days {a2}–{b2}"]))
            chk(loc, 'deepest dip (min daily low)/ 2D bar low agree', min(b['l'] for b in bars[E + 1:E + 31]), lo_[1]['l'])
        continue
    o = next((x for x in open_A if x['signal_id'] == sid), None)
    if o is not None:
        c = o['card']; key = f'open card {sid}'; kind = 'open'
        cn = card_numbers(c, key); a = c['asset']
        e = EXPO[sid]; entry = e['e']
        w = daily[a].window(e['d0'])
        best = (max(b['h'] for _, b in w) / entry - 1) * 100; worst = (min(b['l'] for _, b in w) / entry - 1) * 100
        el = (TODAY - e['d0']).days
        line = f"Confirmed {dlong(e['d0'])} · entry close {money(entry)} · day {el} of 60 · best so far {pct(best)} · worst {pct(worst)}"
        mi = misses_grade[(a, c['grade'])]
        J = check_card_text(f'page live card {sid}', s['card'], s['ladder'], s['eras'], c, kind, cn, mi, entry, line, False, False)
        bars = candles_bars(a, e['tf'])
        ch = s['chart_alert']; loc = f'page live chart {sid}'
        check_chart(loc, ch, 'open', c, cn, entry, bars, None, TFD[e['tf']], e['d0'], sample=c['sample'])
        chk(loc, 'title', ch['title'], f"{a} · {e['tf']} · LIVE SETUP, DAY {el} OF 60")
        chk(loc, 'subtitle', ch['sub'], f"Confirmed {dlong(e['d0'])} · entry close {money(entry)}. Zones use this setup's own card ({c['sample']}). The shaded zones are the next 60 days, as the odds draw them.")
        side = '\n'.join(x.strip() for x in ch['side'].split('\n') if x.strip())
        d10 = [b for k, b in w if k == 10]
        exp_live = f"LIVE: DAY {el} OF 60\nBest so far\n{pct(best)}\nWorst so far\n{pct(worst)}\nDay 10\n{pct((d10[0]['c'] / entry - 1) * 100) if d10 else 'not yet'}"
        chk(loc, 'live box', exp_live if exp_live in side else '(not found) ' + exp_live, exp_live, 'display')
        cloud_check(loc, ch, groups[(a, 'A+')], f'Every past {a} top-grade signal, n {{n}}')
        continue
    c = next(x for x in forming if x['signal_id'] == sid); key = f'card {sid}'; kind = 'forming'
    cn = card_numbers(c, key); a, tf = c['asset'], c['timeframe']; mc = MYC[key]
    entry = daily[a].b[-1]['c']
    ld = dt.date.fromisoformat(c['low_day'])
    kill = mc['kill']
    line = f"Low {dlong(ld)} · confirms {dlong(c['confirms_on'])}" + (f" if it closes above {money(kill)}" if kill else '')
    below = c['grade'] != 'A+'
    mi = misses_grade[(a, c['grade'])]
    check_card_text(f'page forming card {sid}', s['card'], s['ladder'], s['eras'], c, kind, cn, mi, entry, line, below, sid == best_forming_id)
    bars = candles_bars(a, tf)
    ch = s['chart_alert']; loc = f'page forming chart {sid}'
    # the low marker: lowest daily low of the low day
    lowp = daily[a].b[daily[a].pos[ld]]['l']
    check_chart(loc, ch, 'forming', c, cn, entry, bars, len(bars) - 1, TFD[tf], dt.date.fromisoformat(c['confirms_on']), low_day_=ld, low_price=lowp, sample=c['sample'])
    chk(loc, 'title', ch['title'], f"{a} · {tf} · " + ('SETUP FORMING' if c['grade'] == 'A+' else 'FORMING, NOT TOP GRADE'))
    chk(loc, 'subtitle', ch['sub'], f"Low {dlong(ld)} · confirms {dlong(c['confirms_on'])} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them.")
    side = '\n'.join(x.strip() for x in ch['side'].split('\n') if x.strip())
    chk(loc, 'stand-in note', 'Prices use the latest price (today\'s bar is still open) as a stand-in for the entry.' in side, True)
    chk(loc, 'still forming box', f"Still forming. It confirms only if it holds through {dlong(c['confirms_on'])}" in side, True)
    cloud_check(loc, ch, groups[(a, 'A+')], f'Every past {a} top-grade signal, n {{n}}')

# ---------------- picker
pk = [x.strip() for x in PG['initial']['picker'].split('\n') if x.strip()]
J = '\n'.join(pk)
for o in open_A:
    e = EXPO[o['signal_id']]; a = o['chart'].split()[0]; w = daily[a].window(e['d0'])
    best = (max(b['h'] for _, b in w) / e['e'] - 1) * 100; worst = (min(b['l'] for _, b in w) / e['e'] - 1) * 100
    t = f"{o['chart']}\nDay {(TODAY - e['d0']).days}\nbest {pct(best)} · worst {pct(worst)}"
    chk('page picker live', o['signal_id'], t if t in J else '(not found) ' + t, t)
for c in forming:
    cn = card_numbers(c, f"card {c['signal_id']}")
    t = f"{c['chart']}\n{cn['r10']}%\nrose 10% in 60 days · n {cn['n']} · {'top grade' if c['grade'] == 'A+' else 'not top grade'} · confirms {dlong(c['confirms_on'])}"
    chk('page picker forming', c['signal_id'], t if t in J else '(not found) ' + t, t)
if not forming:
    chk('page picker forming', 'empty text', 'Nothing forming today.' in J, True)
chk('page picker', 'forming order by rose 10% (desc)', [x for x in (s['sel'] for s in PG['selections']) if x not in ('example',) and x not in {o['signal_id'] for o in open_A}],
    [c['signal_id'] for c in sorted(forming, key=lambda c: -card_numbers(c, f"card {c['signal_id']}")['r10'])])

# ---------------- previous signals column
pv = '\n'.join(x.strip() for x in PG['initial']['prev'].split('\n') if x.strip())
for o in open_A:
    e = EXPO[o['signal_id']]; a = o['chart'].split()[0]; w = daily[a].window(e['d0']); en = e['e']
    cn = card_numbers(o['card'], f"open card {o['signal_id']}")
    rose10 = next((k for k, b in w if b['h'] >= en * 1.1), None)
    edge = cn['edge']
    if cn['edge'] == 0: status = 'fading'
    elif edge is None: status = 'intact'
    else:
        # fell past its own edge before rising 10% (low before high within a day)
        st_ = 'intact'
        for k, b in w:
            if b['l'] <= en * (1 + edge / 100): st_ = 'fading'; break
            if b['h'] >= en * 1.1: break
        status = st_
    best = (max(b['h'] for _, b in w) / en - 1) * 100; worst = (min(b['l'] for _, b in w) / en - 1) * 100
    t = f"{o['chart']}\nDay {(TODAY - e['d0']).days} of 60 · best {pct(best)} · worst {pct(worst)}\n{'Edge lost' if status == 'fading' else 'On track'}"
    chk('page previous signals', o['signal_id'], t if t in pv else '(not found) ' + t, t)
    grp = pv.split('EDGE LOST OR CLOSED')
    chk('page previous signals', o['signal_id'] + ' group', 'lost' if o['chart'] + '\nDay' in grp[1] else 'intact', 'lost' if status == 'fading' else 'intact')
recent = sorted(groups[('ETH', 'A+')] + groups[('BTC', 'A+')], key=lambda s: s['d0'], reverse=True)[:5]
for s in recent:
    m = s['m']
    t = f"{s['chart']}\n{dlong(s['d0'])} · best {pct(m['up'])} · worst {pct(m['dd'])}\n{'Reached +20%' if m['r20'] else 'Rose 10%' if m['r10'] else 'Missed'}"
    chk('page previous signals (closed)', f"{s['chart']} {s['d0']}", t if t in pv else '(not found) ' + t, t)

# ---------------- record tab
for asset in ('all', 'ETH', 'BTC'):
    R = PG['record'][asset]
    G_ = sorted([s for s in groups[('ETH', 'A+')] + groups[('BTC', 'A+')] if asset == 'all' or s['a'] == asset], key=lambda s: s['d0'], reverse=True)
    chk(f'page past signals ({asset})', 'count', R['count'], f"{len(G_)} signals · {sum(not s['m']['r10'] for s in G_)} missed +10%")
    chk(f'page past signals ({asset})', 'rows', len(R['rows']), len(G_))
    # same-date ties: compare as multisets per date
    exp = [[dlong(s['d0']), s['chart'], money(s['e']), 'Yes' if s['m']['r10'] else 'No', 'Yes' if s['m']['r20'] else 'No',
            pct(s['m']['up']), pct(s['m']['dd']), pct(s['m']['ret']), str(s['m']['dpk'])] for s in G_]
    sh = R['rows']
    for e_ in exp:
        chk(f'page past signals ({asset})', f'row {e_[0]} {e_[1]}', e_ if e_ in sh else ['(not found)'] + e_, e_)
    chk(f'page past signals ({asset})', 'sorted newest first', [r[0] for r in sh], [e_[0] for e_ in exp])
    sm = '\n'.join(x.strip() for x in R['sum'].split('\n') if x.strip())
    for a in (('ETH', 'BTC') if asset == 'all' else (asset,)):
        Ga = groups[(a, 'A+')]; n = len(Ga); mi = misses_grade[(a, 'A+')]
        t = (f"{a}\n{n} signals\nRose 10% in 60 days\n{rha(100 * sum(s['m']['r10'] for s in Ga) / n)}%\nReached +20% in 60 days\n{rha(100 * sum(s['m']['r20'] for s in Ga) / n)}%\n"
             f"Rose 10%, never fell 25.3%\n{rha(100 * sum(s['m']['surv10'] for s in Ga) / n)}%\nMedian deepest dip\n{pct(st.median([r6(s['m']['dd']) for s in Ga]))}\n"
             f"Misses: median best price\n{pct(mi['med_best'])}")
        chk(f'page past signals ({asset})', f'summary {a}', t if t in sm else '(not found) ' + t, t)

# ---------------- banner, header, footer
ga = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
chk('page banner', 'scored', re.search(r'scored (.*?\(feed .*? UTC\))', PG['initial']['review']).group(1), f"{dlong(TODAY)} (feed {ga:%H:%M} UTC)")
last_closed = max(d for a in ('ETH', 'BTC') for d in daily[a].pos if d < TODAY)
ft = PG['initial']['footer'].split('\n')[-1]
chk('page footer', 'closed through / updated / checks', ft, f"Daily candles closed through {dlong(last_closed)} · updated {ga:%H:%M} UTC · checks passed")
chk('page footer', 'both assets have a closed daily bar for that date', all(last_closed in daily[a].pos for a in ('ETH', 'BTC')), True)
hd = PG['initial']['header']
chk('page header', 'market filter', re.search(r'Market filter: (on|off)', hd).group(1), 'on' if G(TODAY) else 'off')
# how-to-read: the one derived number
chk('page how to read', '25.3% = 1/3.3 - 5% maintenance', rha((1 / 3.3 - 0.05) * 100, 1), 25.3)
chk('page how to read', '70% bar = WINMIN', '70% bar' in PG['read'], True)
chk('page errors', 'page script errors', [e for e in PG['errors'] if 'pageerror' in e or 'TypeError' in e], [])

with open(os.path.join(HERE, f'pagechecks_{NAME}.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(OUT)
bad = [o for o in OUT if not o['ok']]
print(NAME, len(OUT), 'page checks', len(bad), 'disagree')
for o in bad[:100]:
    print('  ', o['location'], '|', o['label'], '| shown', o['shown'], '| mine', o['yours'], '|', o['cause'])
