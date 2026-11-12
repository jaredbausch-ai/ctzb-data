"""Check 8-10: every number the page displayed (page_<STATE>.json) against my own values."""
import csv, datetime as dt, json, math, os, re, sys
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import *  # noqa
from run import run

OUT = os.path.dirname(os.path.abspath(__file__))
MON = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
MINUS = '−'
L_, R_, T_, B_ = 20, 960, 24, 480


def fpct(x, d=1, sign=True):
    if x is None:
        return 'n/a'
    r = rh(x, d)
    if r == 0:
        return f'{0:.{d}f}%'
    s = f'{abs(r):.{d}f}'
    return ('+' if (sign and r > 0) else '') + (MINUS if r < 0 else '') + s + '%'


def money(x):
    return '$' + f'{rh(x, 2):,.2f}'


def dlong(d):
    d = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d))
    return f'{d.day} {MON[d.month]} {d.year}'


def dshort(d):
    return f'{d.day:02d} {MON[d.month]}'


def P(s):
    """parse a displayed number: '+19.1%', '−9.5%', '$73,533.06', '84%' -> float"""
    s = s.replace(MINUS, '-').replace('$', '').replace(',', '').replace('%', '').replace('+', '').strip()
    return float(s)


def edge_of(fig, bar=70):
    base = fig['from_entry']['still_rose10_pct']
    if base is not None and base < bar:
        return 0
    for r in fig['if_it_falls_first']:
        if r['still_rose10_pct'] is not None and r['still_rose10_pct'] < bar:
            return -r['fell_pct']
    return None


def edge_txt(e, bar=70):
    return f'Below the {bar}% bar from entry' if e == 0 else (f'{fpct(e, 0)} before it rises 10%' if e is not None else 'Holds at every level')


class Mine:
    """Everything I expect the page to show, from my own computation."""
    def __init__(self, S, E, L):
        self.S, self.E, self.L = S, E, L
        self.rows = [(r, E[k]) for k, r in L.items() if k in E]
        self.aplus = [(r, s) for r, s in self.rows if r['grade'] == 'A+']
        self.open = {o['sid']: o for o in open_mine(S)}
        self.cards = {}
        for c in S.feed['cards']:
            a, tf = c['asset'], c['timeframe']
            lens = frozenset(UNPLAIN[x] for x in c['confirmations'].split('; ') if x != 'none')
            basis, G = card_sample(S, E, L, a, tf, c['grade'], lens)
            self.cards[c['signal_id']] = dict(fig=card_figures(G), basis=basis, G=G)
        for o in S.feed['open_signals']:
            c = o['card']
            lens = frozenset(UNPLAIN[x] for x in c['confirmations'].split('; ') if x != 'none')
            a, tf = o['chart'].split()
            basis, G = card_sample(S, E, L, a, tf, c['grade'], lens)
            self.cards[o['signal_id']] = dict(fig=card_figures(G), basis=basis, G=G)
        k = ('ETH 2D', '2024-09-22'); r = L[k]
        basis, G = card_sample(S, E, L, 'ETH', '2D', r['grade'], frozenset(r['lenses'].split(' + ')), known_by=dt.date(2024, 9, 22), example=True)
        self.cards['example'] = dict(fig=card_figures(G), basis=basis, G=G)

    def misses(self, a, g):
        return misses_of([s for r, s in self.rows if r['asset'] == a and r['grade'] == g])

    def misses_known(self, a, date):
        return misses_of([s for r, s in self.aplus if r['asset'] == a and s['d0'] + dt.timedelta(days=60) <= date])


def kv_dict(kvs):
    return {k[0]: k[1] for k in kvs if len(k) >= 2}


# ------------------------------------------------------------------ the Now card
def check_now(pk, M, v, sel, feed):
    S = M.S
    loc = f'page Now card [{sel}]'
    fe = M.cards[sel]['fig']
    if sel == 'example':
        a, tf, grade, kind = 'ETH', '2D', 'A+', 'example'
        mi = M.misses_known('ETH', dt.date(2024, 9, 22))
    elif sel in M.open:
        o = M.open[sel]; s = o['s']; a, tf = s['a'], s['tf']; kind = 'open'
        grade = next(x['grade'] for x in feed['open_signals'] if x['signal_id'] == sel)
        mi = M.misses(a, grade)
    else:
        c = next(x for x in feed['cards'] if x['signal_id'] == sel); a, tf, grade, kind = c['asset'], c['timeframe'], c['grade'], 'forming'
        mi = M.misses(a, grade)
    pk.add(loc, 'where', v['head']['where'], f"{a} · {tf} CHART" + (' · EXAMPLE' if kind == 'example' else ''))
    pk.add(loc, 'state', v['head']['state'], {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind])
    if kind == 'open':
        o = M.open[sel]; s = o['s']
        exp = f"Confirmed {dlong(s['d0'])} · entry close {money(s['entry'])} · day {o['el']} of 60 · best so far {fpct(o['best'])} · worst {fpct(o['worst'])}"
    elif kind == 'example':
        exp = f"Example: confirmed {dlong('2024-09-22')} · entry close {money(M.E[('ETH 2D', '2024-09-22')]['entry'])}"
    else:
        p, conf = M.forming[sel]
        kc = kill_close(S, a, tf, p['ti'])
        exp = f"Low {dlong(low_day_mine(S, a, tf, p['tdate']))} · confirms {dlong(conf)}" + (f" if it closes above {money(kc)}" if kc else '')
    pk.add(loc, 'card line', v['head']['lines'][0], exp, cause='card head line')
    if kind == 'forming' and grade != 'A+':
        best = max(feed['cards'], key=lambda c: c['rose10_within60d_pct'])
        lead = 'Best setup forming today.' if best['signal_id'] == sel else 'Setup forming.'
        pk.add(loc, 'below-grade line', v['head']['lines'][1], f"{lead} It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
        pk.add(loc, 'pool line', v['pool'][0] if v['pool'] else None, f"all {mi['signals']} {a} signals of this grade", cause='misses pool size')
    pk.add(loc, 'big number', v['odds'][0], f"{fe['rose10_within60d_pct']}%", cause='rose 10% share')
    pk.add(loc, 'big number caption', v['odds'][1], 'rose 10% within 60 days')
    pk.add(loc, 'line under big number', v['odds'][2], f"{fe['rose10_never_fell25_within60d_pct']}% did it without ever falling 25.3%", cause='surv10 share')
    pk.add(loc, 'sample line', v['odds'][3], f"from {fe['past_trades']} past signals like this one", cause='sample size')
    st_ = kv_dict(v['stats'])
    pk.add(loc, 'Typical high', st_.get('Typical high'), fpct(med([s['m']['up'] for s in M.cards[sel]['G']])), cause='median best move')
    pk.add(loc, 'Typical drop from entry', st_.get('Typical drop from entry'), fpct(med([s['m']['dd'] for s in M.cards[sel]['G']])), cause='median deepest dip')
    e = edge_of(fe)
    pk.add(loc, 'Edge gone below', st_.get('Edge gone below'), edge_txt(e), cause='edge from own ladder')
    mt = (('Every time' if mi['up_first'] == mi['misses'] else f"{mi['up_first']} of {mi['misses']}") + f" · median best {fpct(mi['median_peak_pct'])}") if mi['misses'] else 'n/a'
    pk.add(loc, 'If it misses: up first', st_.get('If it misses: up first'), mt, cause='misses line')
    pk.add(loc, 'lead trader marker', v['marker'], 'Lead trader: not in')
    tl = {t[0]: t[1] for t in v['tiles']}
    G = M.cards[sel]['G']
    pk.add(loc, 'tile Dip before the high, from entry', tl.get('Dip before the high, from entry'), fpct(med([s['m']['ddpk'] for s in G])), cause='median dip before high')
    pk.add(loc, 'tile High lands around', tl.get('High lands around'), f"Day {fe['typical_day_of_60d_high']}", cause='median day of high')
    pk.add(loc, 'tile Reached +20%', tl.get('Reached +20%'), f"{fe['rose20_within60d_pct']}%", cause='+20% share')
    pk.add(loc, 'tile Touched -30%', tl.get(f'Touched {MINUS}30%'), f"{fe['fell30_within60d_pct']}%", cause='-30% share')
    pk.add(loc, 'tile Typical high', tl.get('Typical high'), fpct(med([s['m']['up'] for s in G])))
    pk.add(loc, 'tile Deepest dip lands around', tl.get('Deepest dip lands around'), f"Day {fe['typical_day_of_deepest_dip']}", cause='median day of deepest dip')
    pk.add(loc, 'tile Worst drop, misses', tl.get('Worst drop, misses'), fpct(mi['median_worst_drop_pct']) if mi['misses'] else 'n/a', cause='misses worst drop')
    pk.add(loc, 'tile Typical price on day 60, misses', tl.get('Typical price on day 60, misses'), fpct(mi['median_day60_pct']) if mi['misses'] else 'n/a', cause='misses day-60')
    pk.add(loc, 'ladder title', v['ladderLbl'][0], 'Where the odds fade · this setup'.upper())
    lad = v['ladder']
    exp_l = [('From entry', fe['past_trades'], fe['from_entry']['still_rose10_pct'])] + \
            [(f"Falls {r['fell_pct']}% first", r['past_trades'], r['still_rose10_pct']) for r in fe['if_it_falls_first']]
    pk.add(loc, 'ladder rows', len(lad), len(exp_l))
    for x, (t, n, val) in zip(lad, exp_l):
        pk.add(loc, f'ladder "{t}" label', x['label'], f'{t} n {n}', cause='ladder n')
        pk.add(loc, f'ladder "{t}" value', x['val'], 'n/a' if val is None else f'{val}%', cause='ladder share')
        pk.add(loc, f'ladder "{t}" bar width', x['width'], f'{val if val is not None else 0}%')
        pk.add(loc, f'ladder "{t}" marked gone', x['gone'], (val is not None and val < 70), cause='gone mark')
    for x, (t, k) in zip(v['eras'], (('Before 2022', 'before_2022'), ('Since 2022', 'since_2022'))):
        pk.add(loc, f'era {t}', x['label'] + ' ' + x['val'], f"{t} n {fe[k]['past_trades']} {fe[k]['rose10_never_fell25_within60d_pct']}%", cause='era split')
    pk.add(loc, 'frame colour', v['frameColor'], 'var(--fade)' if (kind == 'forming' and grade != 'A+') else 'var(--live)')


def check_picker(pk, M, v, feed, state):
    loc = 'page picker'
    ids = [b['sel'] for b in v['picker']]
    opn = sorted([x for x in feed['open_signals'] if x['grade'] == 'A+'], key=lambda x: 0)
    exp = [x['signal_id'] for x in opn] + [c['signal_id'] for c in sorted(feed['cards'], key=lambda c: -c['rose10_within60d_pct'])] + ['example']
    pk.add(loc, 'buttons', ' | '.join(ids), ' | '.join(exp), cause='picker contents')
    for b in v['picker']:
        s = b['sel']
        if s in M.open:
            o = M.open[s]
            pk.add(loc, f'{s} text', b['text'], f"{o['s']['a']} {o['s']['tf']}\nDay {o['el']}\nbest {fpct(o['best'])} · worst {fpct(o['worst'])}", cause='live button')
        elif s == 'example':
            pk.add(loc, 'example text', b['text'], 'Example: ETH 2D, Sep 2024')
        else:
            c = next(x for x in feed['cards'] if x['signal_id'] == s)
            fe = M.cards[s]['fig']; p, conf = M.forming[s]
            pk.add(loc, f'{s} text', b['text'], f"{c['chart']}\n{fe['rose10_within60d_pct']}%\n{'top grade' if c['grade'] == 'A+' else 'not top grade'} · confirms {dlong(conf)}", cause='forming button')
    if not v['picker'] or not [x for x in v['picker'] if x['sel'] not in M.open and x['sel'] != 'example']:
        pk.add(loc, 'forming row', ' '.join(v['pnone']), 'No live top-grade setups right now.' if not opn else 'Nothing forming today.')


def check_prev(pk, M, v, feed):
    loc = 'page Previous signals'
    opn = [x for x in feed['open_signals'] if x['grade'] == 'A+']
    of = feed['odds_fade']
    gone = next((b for b in of['early_dip'] if b['edge'] == 'gone'), None)
    dip = float(re.search(r'-?\d+(\.\d+)?', gone['band']).group(0)) if gone else None
    mini = []
    for x in opn:
        o = M.open[x['signal_id']]
        fe = M.cards[x['signal_id']]['fig']
        e = edge_of(fe)
        # own-ladder reading: edge lost once price has fallen to the edge level before rising 10%
        lost_own = (e == 0) or (e is not None and o['worst'] is not None and o['worst'] <= e and (o['best'] or 0) < 10)
        pooled = ((o['d10'] if o['d10'] is not None else 0) < 0) if o['el'] >= 10 else (dip is not None and o['worst'] <= dip)
        txt = f"{o['s']['a']} {o['s']['tf']}\nDay {o['el']} of 60 · best {fpct(o['best'])} · worst {fpct(o['worst'])}\n"
        shown = next((m for m in v['prevIntact'] + v['prevClosed'] if m['text'].startswith(f"{o['s']['a']} {o['s']['tf']}\nDay ")), None)
        pk.add(loc, f"{x['signal_id']} mini", shown['text'] if shown else None, txt + ('Edge lost' if pooled else 'On track'), cause='live mini')
        pk.add(loc, f"{x['signal_id']} badge rule (own ladder vs pooled ETH table)", 'Edge lost' if pooled else 'On track',
               'Edge lost' if lost_own else 'On track', cause='badge uses the pooled ETH-only odds_fade, not the setup\'s own ladder')
    if not [x for x in opn if not ((M.open[x['signal_id']]['d10'] or 0) < 0)]:
        pk.add(loc, 'intact group', v['prevIntact'][0]['text'] if v['prevIntact'] else None, 'No open top-grade setup with its edge intact.')
    rec = sorted(M.aplus, key=lambda rs: rs[1]['d0'], reverse=True)
    # stable order inside a date = ledger order
    order = {k: i for i, k in enumerate((r['chart'], r['entry']) for r in M.S.ledger)}
    rec = sorted(M.aplus, key=lambda rs: (-rs[1]['d0'].toordinal(), order[(rs[0]['chart'], rs[0]['entry'])]))[:5]
    closed = [m for m in v['prevClosed'] if 'closed' in m['cls']]
    pk.add(loc, 'closed rows', len(closed), len(rec))
    for m, (r, s) in zip(closed, rec):
        b = 'Reached +20%' if s['m']['r20'] else 'Rose 10%' if s['m']['r10'] else 'Missed'
        pk.add(loc, f"closed {r['chart']} {r['entry']}", m['text'], f"{r['chart']}\n{dlong(s['d0'])} · best {fpct(s['m']['up'])} · worst {fpct(s['m']['dd'])}\n{b}", cause='closed mini')
        pk.add(loc, f"closed {r['chart']} {r['entry']} badge colour", m['badge'], 'badge yes' if s['m']['r10'] else 'badge no')


# ------------------------------------------------------------------ chart geometry
def slot_of(opens, t):
    i = 0
    while i + 1 < len(opens) and opens[i + 1] <= t:
        i += 1
    return i


def next_open(t, tfd):
    if tfd == 1:
        return t + dt.timedelta(days=1)
    return bucket_span(t, tfd)[1] + dt.timedelta(days=1)


def price_fit(svg):
    pts = []
    for e in svg:
        if e['tag'] == 'text' and e['attrs'].get('x') == '968' and e['text'].startswith('$'):
            pts.append((float(e['attrs']['y']) - 5, float(e['text'][1:].replace(',', ''))))
    (y1, p1), (y2, p2) = pts[0], pts[-1]
    b = (y2 - y1) / (p2 - p1)
    a = y1 - b * p1
    return (lambda y: (y - a) / b), (lambda p: a + b * p), pts


def check_chart(pk, M, v, sel, feed, mode):
    S = M.S
    loc = f'page Chart [{sel}{" · " + mode if mode else ""}]'
    svg = v['svg']
    fe = M.cards[sel]['fig']; G = M.cards[sel]['G']
    exact = lambda k: med([s['m'][k] for s in G])
    if sel == 'example':
        ex = json.load(open(os.path.join(S.root, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')))
        bars = ex['bars']; a, tf = 'ETH', '2D'; entry_day = dt.date(2024, 9, 22); forming = False; is_open = False
        s = M.E[('ETH 2D', '2024-09-22')]; entry = s['entry']
        # example data file vs my own 2D bars
        mb = {b['t']: b for b in S.A['ETH'].bars['2D']}
        bad = [x for x in bars if (lambda m: m is None or (m['o'], m['h'], m['l'], m['c']) != (x['o'], x['h'], x['l'], x['c']))(mb.get(utc_date(x['t'])))]
        pk.add('page data example_ETH-2D-2024-09-22.json', 'bars equal my 2D bars', len(bad), 0, cause='example bars')
        Ei = ex['entry_index']
        pk.add('page data example_ETH-2D-2024-09-22.json', 'entry bar closes on 2024-09-22', str(bucket_span(utc_date(bars[Ei]['t']), 2)[1]), '2024-09-22')
        pk.add('page data example_ETH-2D-2024-09-22.json', 'entry_close', ex['entry_close'], rh(entry, 2))
    else:
        a, tf = (M.open[sel]['s']['a'], M.open[sel]['s']['tf']) if sel in M.open else sel.split('-')[:2]
        bars = []
        with open(os.path.join(S.root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')) as f:
            for r in csv.DictReader(f):
                bars.append(dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])))
        mb = {b['t']: b for b in S.A[a].bars[tf]}
        bad = [x for x in bars if (lambda m: m is None or (m['o'], m['h'], m['l'], m['c']) != (x['o'], x['h'], x['l'], x['c']))(mb.get(utc_date(x['t'])))]
        pk.add(f'page data candles/{a}_{tf}.json', 'bars equal my raw bars', len(bad), 0, cause='candle data')
        pk.add(f'page data candles/{a}_{tf}.json', 'last bar is today\'s', str(utc_date(bars[-1]['t'])) <= str(S.today) <= str(bucket_span(utc_date(bars[-1]['t']), int(tf[:-1]))[1]), True)
        is_open = sel in M.open; forming = True
        if is_open:
            s = M.open[sel]['s']; entry = s['entry']; entry_day = s['d0']
            Ei = next(i for i, b in enumerate(bars) if bucket_span(utc_date(b['t']), int(tf[:-1]))[1] == entry_day)
        else:
            c = next(x for x in feed['cards'] if x['signal_id'] == sel)
            entry = S.A[a].C[-1]; p, conf = M.forming[sel]; entry_day = conf; Ei = len(bars) - 1
    tfd = int(tf[:-1])
    happened = mode == 'happened'
    # wick lines -> slot geometry
    wicks = [e for e in svg if e['tag'] == 'line' and e['attrs'].get('stroke-width') == '1.5' and e['attrs'].get('y1') != '24'
             and e['attrs']['x1'] == e['attrs']['x2']]
    xs = [float(w['attrs']['x1']) for w in wicks]
    slot = xs[1] - xs[0]; nslots = round((R_ - L_) / slot)
    opens = [utc_date(b['t']) for b in bars]
    if forming:
        lim = entry_day + dt.timedelta(days=61)
        while opens[-1] <= lim:
            opens.append(next_open(opens[-1], tfd))
    pk.add(loc, 'slots on the x axis', nslots, len(opens), cause='slot count')
    exp_candles = len(bars) if (forming or happened) else Ei + 1
    pk.add(loc, 'candles drawn', len(wicks), exp_candles, cause='candles shown' + (' (outcome hidden at the alert)' if not forming and not happened else ''))
    X = lambda i: L_ + slot * i + slot / 2
    idx = lambda x: round((x - L_) / slot - 0.5)
    span = lambda i: (opens[i], bucket_span(opens[i], tfd)[1] if tfd > 1 else opens[i])
    # x-axis labels
    for e in svg:
        if e['tag'] == 'text' and e['attrs'].get('y') == '502':
            i = idx(float(e['attrs']['x']))
            pk.add(loc, f'x-axis label at slot {i}', e['text'], dshort(opens[min(i, len(opens) - 1)]), cause='axis date')
    # vertical lines with their labels
    vls = []
    for j, e in enumerate(svg):
        if e['tag'] == 'line' and e['attrs'].get('y1') == '24' and e['attrs'].get('y2') == '480':
            lab = svg[j + 1]['text'] if j + 1 < len(svg) and svg[j + 1]['tag'] == 'text' else ''
            vls.append((float(e['attrs']['x1']), lab))

    def day_slot(k):
        return slot_of(opens, entry_day + dt.timedelta(days=k))

    for x, lab in vls:
        i = idx(x); f0, l0 = span(min(i, len(opens) - 1))
        if lab in ('Entry',):
            pk.add(loc, 'Entry line bar', f'{f0}..{l0}', f'bar closing {entry_day}', l0 == entry_day, cause='entry line placement')
        elif lab == 'Today':
            pk.add(loc, 'Today line bar', f'{f0}..{l0}', f'bar containing {S.today}', f0 <= S.today <= l0, cause='today line placement')
        elif lab.startswith('Confirms'):
            pk.add(loc, 'Confirms line bar', f'{f0}..{l0}', f'bar closing {entry_day}', l0 == entry_day, cause='confirms line placement')
            pk.add(loc, 'Confirms line label', lab, f'Confirms {dlong(entry_day)} · entry, day 0')
        elif lab == 'Day 60':
            d = entry_day + dt.timedelta(days=60)
            pk.add(loc, 'Day 60 line bar', f'{f0}..{l0}', f'bar containing {d}', f0 <= d <= l0, cause='day-60 line placement')
        elif lab.startswith('High usually'):
            n = fe['typical_day_of_60d_high']; d = entry_day + dt.timedelta(days=n)
            pk.add(loc, 'High line label', lab, f'High usually ~day {n}')
            pk.add(loc, 'High line bar', f'{f0}..{l0}', f'bar containing {d}', f0 <= d <= l0, cause='high-day line placement')
        elif lab.startswith('Day 10'):
            d = entry_day + dt.timedelta(days=10)
            pk.add(loc, 'Day 10 line bar', f'{f0}..{l0}', f'bar containing {d}', f0 <= d <= l0, cause='day-10 line placement')
        else:
            pk.add(loc, 'unexpected vertical line', lab, '', False, cause='unexpected line')
    # prices
    p_of, y_of, pts = price_fit(svg)
    hi_ = entry * (1 + exact('up') / 100); dr_ = entry * (1 + exact('dd') / 100); t10 = entry * 1.1
    e = edge_of(fe)
    shown_bars = bars if (forming or happened) else bars[:Ei + 1]
    lo_exp = min(min(b['l'] for b in shown_bars), dr_, entry * 0.8) * 0.95
    hi_exp = max(max(b['h'] for b in shown_bars), hi_) * 1.07
    rel = lambda x, y: abs(x - y) <= 1e-6 * abs(y)
    pk.add(loc, 'price axis bottom', round(p_of(B_), 4), round(lo_exp, 4), rel(p_of(B_), lo_exp), cause='axis scaling' + ('' if forming or happened else ' (only what was known at the alert)'))
    pk.add(loc, 'price axis top', round(p_of(T_), 4), round(hi_exp, 4), rel(p_of(T_), hi_exp), cause='axis scaling' + ('' if forming or happened else ' (only what was known at the alert)'))
    hl = [e_ for e_ in svg if e_['tag'] == 'line' and e_['attrs'].get('y1') == e_['attrs'].get('y2') and e_['attrs'].get('stroke-width') in ('2', '2.5')]
    want = {'var(--high)': ('Typical high line', hi_), 'var(--text)': ('+10% line', t10), 'var(--soft)': ('entry line', entry),
            'var(--drop)': ('Typical drop line', dr_)}
    for h in hl:
        col = re.search(r'stroke: (var\([^)]*\))', h['style']).group(1)
        y = float(h['attrs']['y1']); pr = p_of(y)
        if col == 'var(--fade-2)':
            pk.add(loc, 'edge line price', round(pr, 4), round(entry * (1 + e / 100), 4) if e else None, bool(e) and rel(pr, entry * (1 + e / 100)), cause='edge line')
        elif col in want:
            nm, ex_ = want[col]
            pk.add(loc, nm + ' price', round(pr, 4), round(ex_, 4), rel(pr, ex_), cause='level placement')
        # every horizontal level starts on the entry bar and ends on the day-60 bar
        pk.add(loc, f'{col} level starts at entry bar', idx(float(h['attrs']['x1'])), Ei if not (forming and not is_open) else day_slot(0), cause='zone start')
        pk.add(loc, f'{col} level ends at day-60 bar', idx(float(h['attrs']['x2'])), min(nslots - 1, day_slot(60)), cause='zone end')
    # gridline labels sit on their gridlines and the price scale is linear through all of them
    gl = sorted(float(e_['attrs']['y1']) for e_ in svg if e_['tag'] == 'line' and e_['attrs'].get('stroke') == '#1C1736')
    offl = sum(1 for (y, pr) in pts if not any(abs(y - g) < 1e-9 for g in gl) or abs(y_of(pr) - y) > 1e-6)
    pk.add(loc, 'axis labels off their gridlines / off the linear scale', offl, 0, cause='axis labels')
    # shaded zones
    zr = [e_ for e_ in svg if e_['tag'] == 'rect' and e_['attrs'].get('opacity') in ('0.07', '0.1')]
    x60 = X(min(nslots - 1, day_slot(60))); xE = X(Ei if not (forming and not is_open) else day_slot(0))
    for z_ in zr:
        y0, hh = float(z_['attrs']['y']), float(z_['attrs']['height'])
        top, bot = (hi_, entry) if z_['attrs']['opacity'] == '0.07' else (entry, dr_)
        hy = {re.search(r'stroke: (var\([^)]*\))', h['style']).group(1): float(h['attrs']['y1']) for h in hl}
        ty, by = (hy['var(--high)'], hy['var(--soft)']) if z_['attrs']['opacity'] == '0.07' else (hy['var(--soft)'], hy['var(--drop)'])
        okz = abs(y0 - ty) < 1e-6 and abs(y0 + hh - by) < 1e-6 and abs(float(z_['attrs']['x']) - xE) < 1e-6 and abs(float(z_['attrs']['width']) - (x60 - xE)) < 1e-6
        pk.add(loc, ('upside' if z_['attrs']['opacity'] == '0.07' else 'downside') + ' zone rectangle', 'placed', 'entry..typical level, entry bar..day 60', okz, cause='zone placement')
    br = [e_ for e_ in svg if e_['tag'] == 'rect' and e_['attrs'].get('opacity') == '0.24']
    for k, (z_, lo_p, val) in enumerate(zip(br, (0, -5, -10, -15), [fe['from_entry']['still_rose10_pct']] + [r['still_rose10_pct'] for r in fe['if_it_falls_first'][:3]])):
        y0, hh = float(z_['attrs']['y']), float(z_['attrs']['height'])
        okb = abs(y0 - y_of(entry * (1 + lo_p / 100))) < 1e-6 and abs(y0 + hh - min(B_, y_of(entry * (1 + (lo_p - 5) / 100)))) < 1e-6
        pk.add(loc, f'ladder band {k} rectangle', 'placed', f'{lo_p}% to {lo_p - 5}% of entry', okb, cause='band placement')
        col = re.search(r'fill: (var\([^)]*\))', z_['style']).group(1)
        pk.add(loc, f'ladder band {k} colour', col, 'var(--closed)' if val is None else 'var(--high)' if val >= 70 else 'var(--drop)', cause='band colour')
    tags_ = sorted([P(e_['text']) for e_ in svg if e_['tag'] == 'text' and e_['attrs'].get('x') == '1018'], reverse=True)
    exp_tags = sorted([rh(hi_, 2), rh(t10, 2), rh(entry, 2), rh(dr_, 2)], reverse=True)
    pk.add(loc, 'price tags', ' '.join(f'{x:,.2f}' for x in tags_), ' '.join(f'{x:,.2f}' for x in exp_tags), cause='price tags')
    labels = [e_['text'] for e_ in svg if e_['tag'] == 'text']
    pk.add(loc, 'Typical high label', next((l for l in labels if l.startswith('Typical high')), None), f"Typical high {fpct(exact('up'))}")
    pk.add(loc, '+10% label', next((l for l in labels if l.startswith('+10% ·')), None), f"+10% · {fe['rose10_within60d_pct']}% of past signals got here")
    pk.add(loc, 'Typical drop label', next((l for l in labels if l.startswith('Typical drop')), None), f"Typical drop {fpct(exact('dd'))}")
    if e:
        pk.add(loc, 'Edge label', next((l for l in labels if l.startswith('Edge gone below')), None), f"Edge gone below {money(entry * (1 + e / 100))} ({fpct(e, 0)}, before +10%)")
    # ladder bands
    bandtxt = [e_ for e_ in svg if e_['tag'] == 'text' and e_['attrs'].get('font-weight') == '700' and e_['attrs'].get('text-anchor') == 'middle' and e_['attrs'].get('x') != '1018']
    lad = [fe['from_entry']['still_rose10_pct']] + [r['still_rose10_pct'] for r in fe['if_it_falls_first'][:3]]
    pk.add(loc, 'ladder bands', ' '.join(x['text'] for x in bandtxt), ' '.join('n/a' if x is None else f'{x}%' for x in lad), cause='ladder bands')
    for k, (x, lo_p) in enumerate(zip(bandtxt, (0, -5, -10, -15))):
        mid = (min(y_of(entry * (1 + lo_p / 100)), B_) + min(y_of(entry * (1 + (lo_p - 5) / 100)), B_)) / 2 + 5
        pk.add(loc, f'ladder band {k} position', round(float(x['attrs']['y']), 3), round(mid, 3), abs(float(x['attrs']['y']) - mid) < 1e-6, cause='band placement')
    # forming: low circle
    if forming and not is_open:
        p, conf = M.forming[sel]
        lowl = next((l for l in labels if l.startswith('Low ')), None)
        ld = low_day_mine(S, a, tf, p['tdate'])
        rawlow = next(r[3] for r in S.A[a].raw if str(r[0]) == ld)
        pk.add(loc, 'Low label', lowl, f"Low {dlong(ld)} · {money(rawlow)}", cause='low label')
        circ = [e_ for e_ in svg if e_['tag'] == 'circle']
        if circ:
            pk.add(loc, 'Low circle bar', str(opens[idx(float(circ[0]['attrs']['cx']))]), str(p['tdate']), cause='low circle placement')
    # happened: "This one"
    if happened:
        w = window(S.A['ETH'], entry_day)
        raw = {r[0]: r for r in S.A['ETH'].raw}
        hiD = max(range(1, 61), key=lambda k: (raw[entry_day + dt.timedelta(days=k)][2], -k))
        loD = min(range(1, 61), key=lambda k: (raw[entry_day + dt.timedelta(days=k)][3], k))
        hp = raw[entry_day + dt.timedelta(days=hiD)][2]; lp = raw[entry_day + dt.timedelta(days=loD)][3]
        def rng(k):
            i = slot_of(opens, entry_day + dt.timedelta(days=k)); f0, l0 = span(i)
            d0_, d1_ = (f0 - entry_day).days, min(60, (l0 - entry_day).days)
            return f'days {d0_}–{d1_}' if d1_ > d0_ else f'day {d0_}'
        one = [l for l in labels if l.startswith('This one')]
        pk.add(loc, 'This one (high)', one[0] if one else None, f"This one: {money(hp)} · {fpct((hp / entry - 1) * 100)} · {rng(hiD)}", cause='outcome marker')
        pk.add(loc, 'This one (low)', one[1] if len(one) > 1 else None, f"This one: {money(lp)} · {fpct((lp / entry - 1) * 100)} · {rng(loD)}", cause='outcome marker')
    elif not forming:
        pk.add(loc, 'outcome hidden at the alert', any(l.startswith('This one') for l in labels) or any(e_['tag'] == 'circle' for e_ in svg), False)
    # title / subtitle
    if sel == 'example':
        pk.add(loc, 'title', v['title'], 'ETH · 2-DAY · EXAMPLE: PAST CONFIRMED SETUP')
        sub = f"Confirmed {dlong('2024-09-22')} · entry close {money(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them."
    elif is_open:
        o = M.open[sel]
        pk.add(loc, 'title', v['title'], f"{a} · {tf} · LIVE SETUP, DAY {o['el']} OF 60", cause='day count')
        sub = f"Confirmed {dlong(entry_day)} · entry close {money(entry)}. Zones use this setup's own card ({M.cards[sel]['basis']})."
    else:
        c = next(x for x in feed['cards'] if x['signal_id'] == sel); p, conf = M.forming[sel]
        pk.add(loc, 'title', v['title'], f"{a} · {tf} · " + ('SETUP FORMING' if c['grade'] == 'A+' else 'FORMING, NOT TOP GRADE'))
        sub = f"Low {dlong(low_day_mine(S, a, tf, p['tdate']))} · confirms {dlong(conf)} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; days count from the confirmation."
    if not happened:
        sub += ' The shaded zones are the next 60 days, as the odds draw them.'
    pk.add(loc, 'subtitle', v['sub'], sub, cause='subtitle')
    # side box
    kv = kv_dict(v['sideKV'])
    pk.add(loc, 'side big number', v['side'][0].split('\n')[2], f"{fe['rose10_within60d_pct']}%")
    pk.add(loc, 'side line', v['side'][0].split('\n')[3], f"rose 10% within 60 days, from {fe['past_trades']} past signals; {fe['rose10_never_fell25_within60d_pct']}% without ever falling 25.3%")
    pk.add(loc, 'side Typical high', kv.get('Typical high'), f"{fpct(exact('up'))} · {money(hi_)}", cause='typical high price')
    pk.add(loc, 'side +10% target', kv.get('+10% target'), money(t10), cause='target price')
    pk.add(loc, 'side Reached +20%', kv.get('Reached +20%'), f"{fe['rose20_within60d_pct']}%")
    pk.add(loc, 'side Typical drop', kv.get('Typical drop'), f"{fpct(exact('dd'))} · {money(dr_)}", cause='typical drop price')
    pk.add(loc, 'side Edge gone below', kv.get('Edge gone below'), 'below the bar already' if e == 0 else ('holds at every level' if e is None else f"{money(entry * (1 + e / 100))} ({fpct(e, 0)})"), cause='edge price')
    if is_open:
        o = M.open[sel]
        pk.add(loc, 'side Best so far', kv.get('Best so far'), fpct(o['best']))
        pk.add(loc, 'side Worst so far', kv.get('Worst so far'), fpct(o['worst']))
        pk.add(loc, 'side Day 10', kv.get('Day 10'), 'not yet' if o['d10'] is None else fpct(o['d10']))
    if sel == 'example' and happened:
        def dayrange(k):
            i = slot_of(opens, entry_day + dt.timedelta(days=k)); f0, l0 = span(i)
            return f'{(f0 - entry_day).days}–{(l0 - entry_day).days}'
        raw = {r[0]: r for r in S.A['ETH'].raw}
        days = [entry_day + dt.timedelta(days=k) for k in range(1, 61)]
        hiD = max(range(1, 61), key=lambda k: (raw[days[k - 1]][2], -k)); loD = min(range(1, 61), key=lambda k: (raw[days[k - 1]][3], k))
        m = s['m']
        pk.add(loc, 'side Reached +10% / +20%', kv.get('Reached +10% / +20%'), f"{'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}")
        pk.add(loc, 'side Best price', kv.get('Best price'), f"{fpct(m['up'])}, days {dayrange(hiD)}", cause='best price')
        pk.add(loc, 'side Deepest drop', kv.get('Deepest drop'), f"{fpct(m['dd'])}, days {dayrange(loD)}", cause='deepest drop')
        c10 = raw[entry_day + dt.timedelta(days=10)][4]
        pk.add(loc, 'side Day 10 check', kv.get('Day 10 check'), f"{'Red' if c10 < entry else 'Green'}, {fpct((c10 / entry - 1) * 100)}", cause='day-10 check')
        pk.add(loc, 'side Price on day 60', kv.get('Price on day 60'), fpct(m['ret']), cause='day-60 close')
    # cloud
    check_cloud(pk, M, v, sel, a, happened, loc, entry_day if sel == 'example' else None)


def check_cloud(pk, M, v, sel, a, happened, loc, ex_day):
    S = M.S
    P_ = paths_mine(S, M.E, M.L)[a]
    allP = P_
    if ex_day is not None and not happened:
        # at the alert only the paths of signals whose 60 days had closed are known
        keep = [s for r, s in M.aplus if r['asset'] == a and s['d0'] + dt.timedelta(days=60) <= ex_day]
        Pk = [[0.0] + [(S.A[a].C[S.A[a].pos[s['d0'] + dt.timedelta(days=d)]] / s['entry'] - 1) * 100 for d in range(1, 61)] for s in keep]
        P_ = Pk
    pk.add(loc, 'cloud subtitle', v['cloudSub'], f"Every past {a} top-grade signal, n {len(P_)}", cause='cloud sample' + (' (signals not yet known at the alert are included)' if ex_day and not happened else ''))
    q = lambda d, f: rh(quant([p[d] for p in P_], f), 1)
    note = f"━ median path   █ middle half of outcomes{'   ━ this signal' if happened and sel == 'example' else ''}. Day 60: median {fpct(q(60, .5))}, middle half {fpct(q(60, .25))} to {fpct(q(60, .75))}. Daily closes."
    if sel != 'example' and not (sel in M.open and next(x for x in M.S.feed['open_signals'] if x['signal_id'] == sel)['grade'] == 'A+') and sel not in M.open:
        c = next(x for x in M.S.feed['cards'] if x['signal_id'] == sel)
        if c['grade'] != 'A+':
            note += " Top-grade signals only; the selected setup isn't top grade."
    pk.add(loc, 'cloud note', v['cloudNote'].replace(' ', ' '), note, cause='cloud quantiles' + (' (hindsight at the alert)' if ex_day and not happened else ''))
    X = lambda d: 20 + 940 * d / 60
    Y = lambda val: 230 - (max(-40, min(100, val)) + 40) / 140 * 218
    pl = [e for e in v['cloud'] if e['tag'] == 'polyline']
    med_pts = [tuple(map(float, p.split(','))) for p in pl[0]['attrs']['points'].split()]
    bad = sum(1 for d, (x, y) in enumerate(med_pts) if abs(x - X(d)) > 1e-6 or abs(y - Y(q(d, .5))) > 1e-6)
    pk.add(loc, 'cloud median polyline points off', bad, 0, cause='median path drawn' + (' (hindsight at the alert)' if ex_day and not happened else ''))
    pg = next(e for e in v['cloud'] if e['tag'] == 'polygon')
    band = [tuple(map(float, p.split(','))) for p in pg['attrs']['points'].split()]
    exp = [(X(d), Y(q(d, .75))) for d in range(61)] + [(X(d), Y(q(d, .25))) for d in range(60, -1, -1)]
    bad = sum(1 for (x, y), (ex, ey) in zip(band, exp) if abs(x - ex) > 1e-6 or abs(y - ey) > 1e-6)
    pk.add(loc, 'cloud middle-half band points off', bad, 0, cause='band drawn' + (' (hindsight at the alert)' if ex_day and not happened else ''))
    if happened and sel == 'example':
        pts = [tuple(map(float, p.split(','))) for p in pl[1]['attrs']['points'].split()]
        A = S.A['ETH']; e = M.E[('ETH 2D', '2024-09-22')]['entry']; d0 = dt.date(2024, 9, 22)
        exp = [(X(0), Y(0))] + [(X(2 * k), Y((A.C[A.pos[d0 + dt.timedelta(days=2 * k)]] / e - 1) * 100)) for k in range(1, 31)]
        bad = sum(1 for (x, y), (ex, ey) in zip(pts, exp) if abs(x - ex) > 1e-6 or abs(y - ey) > 1e-6)
        pk.add(loc, 'this-signal path points off', bad, 0, cause='this signal path')
        pk.add(loc, 'this-signal path length', len(pts), len(exp))


# ------------------------------------------------------------------ record, header, read
def check_record(pk, M, views, feed):
    for asset in ('all', 'ETH', 'BTC'):
        v = views[f'record:{asset}']; loc = f'page Past signals [{asset}]'
        rows = [(r, s) for r, s in M.aplus if asset == 'all' or r['asset'] == asset]
        order = {k: i for i, k in enumerate((r['chart'], r['entry']) for r in M.S.ledger)}
        rows = sorted(rows, key=lambda rs: (-rs[1]['d0'].toordinal(), order[(rs[0]['chart'], rs[0]['entry'])]))
        miss = sum(1 for r, s in rows if not s['m']['r10'])
        pk.add(loc, 'count line', v['count'], f'{len(rows)} signals · {miss} missed +10%', cause='record count')
        pk.add(loc, 'table rows', len(v['rows']), len(rows))
        bad = 0
        for shown, (r, s) in zip(v['rows'], rows):
            m = s['m']
            exp = [dlong(s['d0']), r['chart'], money(s['entry']), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
                   fpct(m['up']), fpct(m['dd']), fpct(m['ret']), str(m['dpk'])]
            for h, x, y in zip(v['head'], shown, exp):
                ok = pk.add(f'{loc} {r["chart"]} {r["entry"]}', h, x, y, cause='record cell')
        for b in v['sum']:
            ast = b['title'].split()[0]
            G = [s for r, s in M.aplus if r['asset'] == ast]; n = len(G)
            kv = {k[0]: k[1] for k in b['kv']}
            sl = f'{loc} summary {ast}'
            pk.add(sl, 'signals', b['title'].replace('\n', ' ').replace('\t', ' '), f'{ast} {n} signals')
            pk.add(sl, 'Rose 10% in 60 days', kv.get('Rose 10% in 60 days'), f"{share(sum(s['m']['r10'] for s in G), n)}%")
            pk.add(sl, 'Reached +20% in 60 days', kv.get('Reached +20% in 60 days'), f"{share(sum(s['m']['r20'] for s in G), n)}%")
            pk.add(sl, 'Rose 10%, never fell 25.3%', kv.get('Rose 10%, never fell 25.3%'), f"{share(sum(s['m']['surv10'] for s in G), n)}%")
            pk.add(sl, 'Median deepest dip', kv.get('Median deepest dip'), fpct(med([s['m']['dd'] for s in G])))
            mi = M.misses(ast, 'A+')
            pk.add(sl, 'Misses: median best price', kv.get('Misses: median best price'), fpct(mi['median_peak_pct']))
        pk.add(loc, 'summary boxes', ' '.join(b['title'].split()[0] for b in v['sum']), ' '.join(a for a in ('ETH', 'BTC') if asset in ('all', a)))


def check_header(pk, M, d, feed):
    S = M.S; h = d['header']; loc = 'page header/banner/footer'
    gen = feed['generated_at']
    pk.add(loc, 'review banner', h['review'].split('\n')[0],
           f"Review build. Real pipeline data, scored {dlong(feed['scored_as_of'])} (feed {gen[11:16]} UTC). Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run.")
    pk.add(loc, 'scored date = today', feed['scored_as_of'], str(S.today))
    pk.add(loc, 'market filter', h['filter'], f"Market filter: {'on' if S.gate(S.today) else 'off'}", cause='regime gate today')
    last_closed = max(dd for dd in S.A['ETH'].D if dd < S.today)
    pk.add(loc, 'footer feed state', h['feedState'], f"Daily candles closed through {dlong(last_closed)} · updated {gen[11:16]} UTC · checks passed", cause='closed-through date')
    pk.add(loc, 'stale warning shown', h['stale'], False)


def scan_wording(pk, d, name):
    """10. entry quality only: no wording that reads as a return, a trade taken or a track record."""
    texts = [d['header']['review'], d['header']['footer'], d['views']['read']]
    for k, v in d['views'].items():
        if k.startswith('now:'):
            texts += [v['cardText'], v['prevHead']]
        elif k.startswith('chart:'):
            texts += v['side'] + [v['title'], v['sub'], v['cloudNote']]
        elif k.startswith('record:'):
            texts += [v['title'], v['fine']] + [' '.join(x) for x in v['head']]
    blob = '\n'.join(texts)
    hits = sorted(set(m.group(0) for m in re.finditer(r'[^.\n]*\b(profit|returns?|win rate|track record|our trades|trades? taken|P&L|gain)\b[^.\n]*', blob, re.I)))
    for x in hits:
        pk.add('page wording scan', 'phrase', x.strip(), '(review)', True)
    return blob


def check_read(pk, d, feed):
    t = d['views']['read']; loc = 'page How to read'
    lev, mm = Fraction(33, 10), Fraction(5, 100)
    liq = rh((1 / lev - mm) * 100, 1)
    pk.add(loc, 'liquidation level 25.3% at 3.3x with 5% maintenance', '25.3' if '25.3%' in t and '3.3x' in t and '5% maintenance' in t else 'missing', str(liq), cause='liquidation arithmetic')
    pk.add(loc, 'posting bar', '70' if 'our 70% bar' in t else 'missing', str(feed['odds_fade']['posting_bar_pct']))
    pk.add(loc, 'ladder levels', '5,10,15,20' if 'falls 5%, 10%, 15% or 20%' in t else 'missing', '5,10,15,20')
    pk.add(loc, 'window', '60' if 'within 60 days' in t else 'missing', '60')


def label_rows(pk, M, d, feed):
    """9. labels vs meaning: wording whose measure differs from what it says (found by reading code + output)."""
    loc = 'labels vs meaning'
    if any(o['grade'] == 'A+' for o in feed['open_signals']):
        pk.add(loc, 'Previous signals badge "Edge lost"/"On track"',
               'rule: red on day 10 (or early dip past the first "gone" band) in the pooled odds_fade table, which is ETH tier signals only, applied to a BTC setup',
               "rule per CONTEXT/How-to-read: the setup's own ladder (\"the player, not the league\"); outcome happens to agree here", False,
               cause='badge basis differs from the documented edge definition')
    pk.add(loc, 'feed odds_fade rose10_within60d_pct / rose20_within60d_pct / edge_measured_on "rose 10% within 60 days"',
           'field names and edge_measured_on say within 60 days', 'the value counts highs on days 11-60 only (after day 10)', False,
           cause='field label says a different window than it measures (sample text explains; the names do not)')
    pk.add(loc, 'tile "Typical price on day 60, misses"', 'labelled a price', 'shows the median day-60 change from entry, in %', False, cause='label says price, value is a percentage')
    pk.add(loc, 'tiles "Worst drop, misses" / "Typical price on day 60, misses" / "If it misses" on non-A+ forming cards',
           "read as this card's sample", "computed from every signal of the asset at that grade (e.g. 95 misses of 312 BTC C), not the card's sample; the pool note sits only under the stats",
           not feed['cards'], cause='sample of the misses tiles not stated on the tiles')
    pk.add(loc, 'Previous signals header "odds update each close"', 'says odds', 'the column shows best/worst so far and a badge; no odds', False, cause='header promises figures the column does not show')


def main(name):
    S, ck, E, L = run(name)
    M = Mine(S, E, L)
    M.forming = {}
    for p in check_cards(S, Checker('tmp'), E, L):
        pass
    # rebuild the forming map (sid -> (p, conf)) exactly as check_cards does
    for a in ('ETH', 'BTC'):
        for tf in TFS:
            bars = S.A[a].bars[tf]
            tr, ct, K = troughs(bars); n = len(bars)
            for back in (1, 2, 3):
                ti = n - 1 - back; v = ct[ti]
                if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, n)):
                    continue
                o = bars[ti]['t']
                for _ in range(3):
                    o = bucket_span(o, int(tf[:-1]))[1] + dt.timedelta(days=1)
                conf = bucket_span(o, int(tf[:-1]))[1]
                M.forming[f'{a}-{tf}-{conf}'] = (dict(a=a, tf=tf, ti=ti, need=3 - back, tdate=bars[ti]['t']), conf)
                break
    d = json.load(open(os.path.join(OUT, f'page_{name}.json')))
    feed = S.feed
    pk = Checker(name)
    check_header(pk, M, d, feed)
    check_picker(pk, M, d['views']['now:initial'], feed, name)
    # initial selection
    exp_init = (sorted(feed['cards'], key=lambda c: -c['rose10_within60d_pct'])[0]['signal_id'] if feed['cards']
                else next((x['signal_id'] for x in feed['open_signals'] if x['grade'] == 'A+'), 'example'))
    pk.add('page picker', 'initially selected', ','.join(d['initial_selection']), exp_init)
    check_prev(pk, M, d['views']['now:initial'], feed)
    for k, v in d['views'].items():
        if k.startswith('now:') and k != 'now:initial':
            check_now(pk, M, v, k[4:], feed)
        elif k.startswith('chart:'):
            sel = k[6:]
            mode = ''
            if sel.startswith('example:'):
                mode = 'happened' if sel.endswith('happened') else 'alert'
                sel = 'example'
            check_chart(pk, M, v, sel, feed, mode)
    check_record(pk, M, d['views'], feed)
    scan_wording(pk, d, name)
    check_read(pk, d, feed)
    label_rows(pk, M, d, feed)
    return ck.rows, pk.rows


if __name__ == '__main__':
    allrows = []
    for nm in sys.argv[1:] or ['REPLAY', 'CURRENT']:
        frows, prows = main(nm)
        allrows += frows + prows
        bad = [r for r in prows if r['ok'] != 'yes']
        print(nm, 'feed', len(frows), 'page', len(prows), 'page disagreements', len(bad))
        for r in bad:
            print('  ', r['location'], '|', r['label'], '|', r['shown'][:150], '|', r['yours'][:150])
    with open(os.path.join(OUT, 'all_checks.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(allrows)
    with open(os.path.join(OUT, 'disagreements.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows([r for r in allrows if r['ok'] != 'yes'])
