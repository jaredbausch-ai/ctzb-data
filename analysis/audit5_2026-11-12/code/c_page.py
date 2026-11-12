"""Check 8 (and the page side of 9/10): every number the member page displays, against my own values."""
import json, re, math, csv, datetime as dt
from fractions import Fraction as Fr
import core as K
from rec import chk

S = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'
MON = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
MINUS = '\u2212'
BAR = 70


def fdate(d):
    d = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d))
    return f'{d.day} {MON[d.month]} {d.year}'


def faxis(d):
    return f'{d.day:02d} {MON[d.month]}'


def fpct(x, d=1, sign=True):
    if x is None:
        return 'n/a'
    r = K.rhaz(Fr(x), d)
    s = f'{abs(r):.{d}f}' if d else f'{abs(r)}'
    if r > 0 and sign:
        s = '+' + s
    elif r < 0:
        s = MINUS + s
    return s + '%'


def fmoney(x):
    if x is None:
        return 'n/a'
    r = K.rhaz(Fr(x), 2)
    return f'${r:,.2f}'


def norm(s):
    return re.sub(r'\s+', ' ', (s or '')).strip()


# ---------------------------------------------------------------- my models
def misses(pairs, a, g, known_by=None):
    rows = [(r, s) for r, s in pairs if r['asset'] == a and r['grade'] == g and (known_by is None or s['d0'] + dt.timedelta(days=60) <= known_by)]
    ms = [s['m'] for _, s in rows]; miss = [m for m in ms if not m['r10']]
    best = [m['up'] for m in miss]
    return dict(signals=len(ms), misses=len(miss), up_first=sum(b > 0 for b in best), peak=K.median(best),
                worst=K.median([m['dd'] for m in miss]), day60=K.median([m['ret'] for m in miss]),
                up_after_low=sum(1 for m in miss if m['up'] > 0 and m['dpk'] > m['ddday']),
                up_before_low=sum(1 for m in miss if m['up'] > 0 and m['dpk'] < m['ddday']))


def edge_of(fig):
    """(kind, pct): 'base' when the setup is under the bar from entry, 'fall' at the first fall whose share is under it."""
    if Fr(100 * fig['n_r10'], fig['n']) < BAR:
        return 'base', 0
    for L in fig['lad']:
        if L['n'] and L['ok_exact'] < BAR:
            return 'fall', -L['fell']
    return 'holds', None


def future_opens(last_open, tf, k):
    """Open dates of the k bars after the last one, on the real calendar (multi-day bars restart on 1 Jan)."""
    nd = int(tf.rstrip('D')); out = []; d = last_open
    for _ in range(k):
        nx = d + dt.timedelta(days=nd)
        if nx.year > d.year:
            nx = dt.date(nx.year, 1, 1)
        out.append(nx); d = nx
    return out


def slot_calendar(bars_t, tf, nslots):
    opens = [dt.datetime.fromtimestamp(t, dt.timezone.utc).date() for t in bars_t]
    if nslots > len(opens):
        opens += future_opens(opens[-1], tf, nslots - len(opens))
    return opens


def covering(opens, d):
    for i in range(len(opens)):
        nxt = opens[i + 1] if i + 1 < len(opens) else None
        if opens[i] <= d and (nxt is None or d < nxt):
            return i
    return None


# ---------------------------------------------------------------- geometry helpers
def vlines(chart):
    out = []
    for i, e in enumerate(chart):
        if e['tag'] == 'line' and e.get('y1') == '24' and e.get('y2') == '480':
            lab = chart[i + 1]['text'] if i + 1 < len(chart) and chart[i + 1]['tag'] == 'text' else ''
            out.append((lab, float(e['x1'])))
    return out


def wicks(chart):
    return [e for e in chart if e['tag'] == 'line' and e.get('stroke-width') == '1.5' and not (e.get('y1') == '24' and e.get('y2') == '480')]


def hlines(chart):
    return [e for e in chart if e['tag'] == 'line' and e.get('stroke-width') in ('2', '2.5') and e.get('y1') == e.get('y2')]


def texts(chart):
    return [e for e in chart if e['tag'] == 'text']


# ---------------------------------------------------------------- the check
def check(st, C):
    feed, pairs, W = C['feed'], C['pairs'], C['W']
    root, now = W['root'], W['now']
    today = now.date()
    P = json.load(open(f'{S}/audit5/work/page_{st}.json'))
    snaps = {s['tag']: s for s in P['snaps']}
    CF = C['cardfig']
    for v in CF.values():
        f = v['fig']; f['n_r10'] = sum(s['m']['r10'] for _, s in [(None, x) for x in []])  # placeholder
    # exact +10% counts for the edge rule
    from c_cards import sample_for
    for sid, v in CF.items():
        kb = dt.date(2024, 9, 22) if v['kind'] == 'example' else None
        G, _ = sample_for(v['card'], pairs, known_by=kb)
        v['fig']['n_r10'] = sum(s['m']['r10'] for _, s in G)
        v['G'] = G
    gate = K.gate_for(root)
    led_grade = {(r['chart'], r['entry']): r['grade'] for r, _ in pairs}
    mine_open = {sid: v for sid, v in CF.items() if v['kind'] == 'open'}
    aplus_open = [v for v in mine_open.values() if v['o']['grade'] == 'A+']
    forming = {sid: v for sid, v in CF.items() if v['kind'] == 'forming'}
    boot = snaps['boot']
    L = f'page {st}'

    # ---------------- banner, header, footer
    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    chk(st, L + ' banner', 'scored date', re.search(r'scored (.+?) \(feed', boot['review']).group(1), fdate(today), 'banner date')
    chk(st, L + ' banner', 'feed time (UTC)', re.search(r'\(feed (\d\d:\d\d) UTC\)', boot['review']).group(1), gen.strftime('%H:%M'), 'feed time')
    chk(st, L + ' header', 'market filter pill', norm(boot['pill']), 'Market filter: ' + ('on' if gate(today) else 'off'), 'regime gate today')
    chk(st, L + ' footer', 'data through / checks', norm(boot['feedState']), f'Data through {fdate(today)} · checks passed', 'footer')

    # ---------------- picker
    pb = boot['pickerButtons']
    live_btns = [b for b in pb if 'top' in b['cls'] and b['sel'] in mine_open]
    exp_live = sorted(aplus_open, key=lambda v: (v['o']['entry_date'], v['o']['chart']))
    chk(st, L + ' picker', 'live buttons (open top-grade signals)', str([b['sel'] for b in live_btns]), str([v['o']['signal_id'] for v in exp_live]), 'live set')
    for b in live_btns:
        v = mine_open[b['sel']]; s = v['s']; w = v['w']
        best = (max(x[1] for x in w) / s['entry'] - 1) * 100; worst = (min(x[2] for x in w) / s['entry'] - 1) * 100
        chk(st, L + ' picker', f'{b["sel"]} button', norm(b['text']), norm(f"{s['a']} {s['tf']} Day {(today - s['d0']).days} best {fpct(best)} · worst {fpct(worst)}"), 'picker live button')
    fb = [b for b in pb if b['sel'] in forming]
    exp_f = sorted(forming.values(), key=lambda v: -v['fig']['reach10'])
    chk(st, L + ' picker', 'forming buttons, ranked by +10% odds', str([b['sel'] for b in fb]), str([v['card']['signal_id'] for v in exp_f]), 'forming order')
    for b in fb:
        v = forming[b['sel']]; c = v['card']
        chk(st, L + ' picker', f'{b["sel"]} button', norm(b['text']),
            norm(f"{c['chart']} {v['fig']['reach10']}% {'top grade' if c['grade'] == 'A+' else 'not top grade'} · confirms {fdate(v['fm']['d0'])}"), 'picker forming button')
    if not forming:
        chk(st, L + ' picker', 'forming row says nothing forming', 'Nothing forming today.' in boot['picker'], True, 'forming text')
    chk(st, L + ' picker', 'example button', 'Example: ETH 2D, Sep 2024' in boot['picker'], True, 'example button')
    # default card
    best_forming = exp_f[0]['card']['signal_id'] if exp_f else None
    default = best_forming or (exp_live[0]['o']['signal_id'] if exp_live else 'example')
    pressed = [b['sel'] for b in pb if b['pressed'] == 'true']
    chk(st, L + ' picker', 'card shown on arrival', str(pressed), str([default]), 'default selection')

    # ---------------- previous signals column
    minis = boot['prevMinis']
    intact, fading = [], []
    for v in aplus_open:
        o = v['o']; s = v['s']; w = v['w']
        d10 = next((x for x in w if x[0] == 10), None)
        el = (today - s['d0']).days
        worst = (min(x[2] for x in w) / s['entry'] - 1) * 100
        if el >= 10:
            fad = d10 is not None and d10[3] < s['entry']
        else:
            gone = next((r for r in feed['odds_fade']['early_dip'] if r['edge'] == 'gone'), None)
            dp = float(re.search(r'-?\d+(\.\d+)?', gone['band']).group(0)) if gone else None
            fad = dp is not None and worst <= dp
        (fading if fad else intact).append(v)
    om = [m for m in minis if 'closed' not in m['cls']]
    exp = [(v, '') for v in intact] + [(v, 'fading') for v in fading]
    chk(st, L + ' previous', 'open top-grade minis', str(sorted((m['name'], m['badge']) for m in om)),
        str(sorted((f"{v['s']['a']} {v['s']['tf']}", 'Edge lost' if k else 'On track') for v, k in exp)), 'open minis')
    for v, k in exp:
        s = v['s']; w = v['w']
        m = next((m for m in om if m['name'] == f"{s['a']} {s['tf']}"), None)
        if m:
            best = (max(x[1] for x in w) / s['entry'] - 1) * 100; worst = (min(x[2] for x in w) / s['entry'] - 1) * 100
            chk(st, L + ' previous', f"{v['o']['signal_id']} mini", norm(m['sub']), f"Day {(today - s['d0']).days} of 60 · best {fpct(best)} · worst {fpct(worst)}", 'open mini')
    aplus = sorted([(r, s) for r, s in pairs if r['grade'] == 'A+'], key=lambda x: (x[1]['d0'], x[0]['asset'] == 'ETH'), reverse=True)
    rec5 = aplus[:5]
    cm = [m for m in minis if 'closed' in m['cls']]
    chk(st, L + ' previous', 'five most recent closed top-grade signals', str([(m['name'], m['sub'].split(' · ')[0]) for m in cm]),
        str([(r['chart'], fdate(s['d0'])) for r, s in rec5]), 'recent list')
    for (r, s), m in zip(rec5, cm):
        mm = s['m']
        chk(st, L + ' previous', f"{r['chart']} {s['d0']} mini", norm(m['sub']), f"{fdate(s['d0'])} · best {fpct(mm['up'])} · worst {fpct(mm['dd'])}", 'closed mini')
        chk(st, L + ' previous', f"{r['chart']} {s['d0']} badge", m['badge'], 'Reached +20%' if mm['r20'] else 'Rose 10%' if mm['r10'] else 'Missed', 'badge')

    # ---------------- each card on the Now view
    def card_expect(sid):
        v = CF[sid]; f = v['fig']; c = v['card']; kind = v['kind']
        a = c['asset']; tf = c['timeframe']
        if kind == 'example':
            mi = misses(pairs, 'ETH', 'A+', known_by=dt.date(2024, 9, 22))
        else:
            mi = misses(pairs, a, c['grade'])
        e = {}
        e['where'] = f"{a} · {tf} chart" + (' · example' if kind == 'example' else '')
        e['state'] = {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind]
        if kind == 'forming':
            fm = v['fm']
            line = f"Low {fdate(v['low_day'])} · confirms {fdate(fm['d0'])}" + (f" if it closes above {fmoney(Fr(v['kill']))}" if v['kill'] is not None else '')
        elif kind == 'open':
            s = v['s']; w = v['w']
            line = (f"Confirmed {fdate(s['d0'])} · entry close {fmoney(s['entry'])} · day {(today - s['d0']).days} of 60 · "
                    f"best so far {fpct((max(x[1] for x in w) / s['entry'] - 1) * 100)} · worst {fpct((min(x[2] for x in w) / s['entry'] - 1) * 100)}")
        else:
            line = f"Example: confirmed {fdate(v['s']['d0'])} · entry close {fmoney(v['s']['entry'])}"
        e['line'] = line
        below = kind == 'forming' and c['grade'] != 'A+'
        e['below'] = below
        if below:
            e['belowline'] = ('Best setup forming today.' if sid == best_forming else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms."
        e['big'] = f"{f['reach10']}%"
        e['odds'] = norm(f"{f['reach10']}% rose 10% within 60 days {f['surv10']}% did it without ever falling 25.3% from {f['n']} past signals like this one")
        ek, ep = edge_of(f)
        e['edge'] = ek, ep
        edge_txt = f'Below the {BAR}% bar from entry' if ek == 'base' else (f'{fpct(ep, 0)} before it rises 10%' if ek == 'fall' else 'Holds at every level')
        miss_txt = ('Every time' if mi['up_first'] == mi['misses'] else f"{mi['up_first']} of {mi['misses']}") + f" · median best {fpct(mi['peak'])}"
        e['stats'] = [['Typical high', fpct(f['best'])], ['Typical drop from entry', fpct(f['deepest'])], ['Edge gone below', edge_txt], ['If it misses: up first', miss_txt]]
        e['pool'] = [f"all {mi['signals']} {a} signals of this grade"] if below else []
        e['tiles'] = [['Dip before the high, from entry', fpct(f['dip_before'])], ['High lands around', f"Day {f['dHigh']}"],
                      ['Reached +20%', f"{f['reach20']}%"], [f'Touched {MINUS}30%', f"{f['touched30']}%"], ['Typical high', fpct(f['best'])],
                      ['Deepest dip lands around', f"Day {f['dLow']}"], ['Worst drop, misses', fpct(mi['worst'])], ['Typical price on day 60, misses', fpct(mi['day60'])]]
        lad = [[f"From entry n {f['n']}", f"{f['reach10']}%"]] + [[f"Falls {x['fell']}% first n {x['n']}", 'n/a' if x['ok'] is None else f"{x['ok']}%"] for x in f['lad']]
        e['ladder'] = lad
        e['ladder_gone'] = [Fr(100 * f['n_r10'], f['n']) < BAR] + [x['ok_exact'] is not None and x['ok_exact'] < BAR for x in f['lad']]
        e['eras'] = [[f"Before 2022 n {f['nOld']}", f"{f['sOld']}%"], [f"Since 2022 n {f['nNew']}", f"{f['sNew']}%"]]
        e['mi'] = mi
        return e

    def check_card_view(tag, sid):
        s_ = snaps.get(tag)
        if not s_:
            return
        e = card_expect(sid); cp = s_['cardParts']; loc = f'{L} Now card [{sid}]'; v_ = CF[sid]
        chk(st, loc, 'where', norm(cp['where']).lower(), e['where'].lower(), 'card head')
        chk(st, loc, 'state', norm(cp['state']), e['state'], 'card state')
        chk(st, loc, 'head line', norm(cp['heads'][0]), e['line'], 'card head line')
        if e['below']:
            chk(st, loc, 'below-grade line', norm(cp['heads'][1]) if len(cp['heads']) > 1 else '', e['belowline'], 'below-grade line')
        chk(st, loc, 'big number', norm(cp['big']), e['big'], 'big number')
        chk(st, loc, 'odds block', norm(cp['odds']), e['odds'], 'odds block')
        for got, want in zip(cp['stats'], e['stats']):
            chk(st, loc, want[0], norm(got[1]), want[1], f'{want[0]}')
            chk(st, loc, want[0] + ' (label)', norm(got[0]), want[0], 'label')
        chk(st, loc, 'pool line', str([norm(x) for x in cp['pool']]), str(e['pool']), 'pool line')
        chk(st, loc, 'lead trader marker', norm(cp['marker']), 'Lead trader: not in', 'marker')
        chk(st, loc, 'tile count', len(cp['tiles']), len(e['tiles']), 'tiles')
        for got, want in zip(cp['tiles'], e['tiles']):
            chk(st, loc, f'tile {want[0]}', norm(got[1]), want[1], f'tile {want[0]}')
            chk(st, loc, f'tile {want[0]} (label)', norm(got[0]), want[0], 'label')
        chk(st, loc, 'ladder title', norm(cp['ladderLbl']).lower(), 'where the odds fade · this setup', 'ladder title')
        chk(st, loc, 'ladder rows', len(cp['ladder']), len(e['ladder']), 'ladder rows')
        hf = [[f"From entry n {v_['fig']['n']}", f"{v_['fig']['reach10']}%"]] + [[f"Falls {x['fell']}% first n {x['n']}", 'n/a' if x['ok'] is None else f"{x['ok']}%"] for x in v_['fig']['lad_hf']]
        for got, want, gone, h_ in zip(cp['ladder'], e['ladder'], e['ladder_gone'], hf):
            why = 'first-fall step checks the HIGH before the LOW within a daily bar (stated choice (c): low first)' if (norm(got[0]) + ' | ' + norm(got[1])) == (h_[0] + ' | ' + h_[1]) else 'ladder'
            chk(st, loc, f'ladder {want[0]}', norm(got[0]) + ' | ' + norm(got[1]), want[0] + ' | ' + want[1], why)
            chk(st, loc, f'ladder {want[0]} colour (gone below 70%)', 'gone' in got[3], gone, 'ladder colour')
        for got, want in zip(cp['eras'], e['eras']):
            chk(st, loc, f'era {want[0]}', norm(got[0]) + ' | ' + norm(got[1]), want[0] + ' | ' + want[1], 'era')
        chk(st, loc, 'stale note absent (feed 6 minutes old)', cp['stale'], None, 'stale note')
        return e

    for b in pb:
        tag = f"now:{b['sel']}"
        sid = b['sel']
        if sid in CF:
            check_card_view(tag, sid)
    check_card_view('now:switch', 'example')
    # the arrival card is the default selection's card
    if default in CF:
        a1 = norm(boot['card']); a2 = norm(snaps[f'now:{default}']['card'])
        chk(st, L + ' Now', 'arrival card = its picker card', a1 == a2, True, 'arrival card')

    check_record(st, L, snaps, pairs, feed)
    check_read(st, L, snaps)
    # ---------------- chart views
    for b in pb:
        sid = b['sel']
        if sid not in CF:
            continue
        for mode in ('alert', 'happened', 'alert-again'):
            s_ = snaps.get(f'chart:{sid}:{mode}')
            if s_:
                check_chart(st, L, s_, sid, mode, CF[sid], card_expect(sid), C, pairs, today, now, feed, snaps)


def check_chart(st, L, s_, sid, mode, v, e, C, pairs, today, now, feed, snaps):
    loc = f'{L} Chart [{sid} · {mode}]'
    f = v['fig']; c = v['card']; kind = v['kind']; a = c['asset']; tf = c['timeframe']; tfd = int(tf.rstrip('D'))
    root = C['root']
    happened = kind == 'example' and mode == 'happened'
    # ----- the candles the page drew, and my bars for the same chart
    if kind == 'example':
        ex = json.load(open(f'{root}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
        bars_t = [b['t'] for b in ex['bars']]; bar_src = ex['bars']
    else:
        rows = list(csv.DictReader(open(f"{root}/datasets/candles_{a.lower()}_{tf.lower()}.csv")))
        bars_t = [int(r['time']) for r in rows]; bar_src = [{'t': int(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])} for r in rows]
    mb = C['W']['bars'][(a, tf)]
    # every drawn bar against the raw chart candles
    if mode == 'alert':
        for b in bar_src:
            d = dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date(); i = mb.pos.get(d)
            raw = (mb.O[i], mb.H[i], mb.L[i], mb.C[i]) if i is not None else None
            ok = raw is not None and all(Fr(str(x)) == y for x, y in zip((b['o'], b['h'], b['l'], b['c']), raw))
            chk(st, loc, f'candle {d} o/h/l/c = raw chart bar', ok, True, 'chart candle')
    opens = [dt.datetime.fromtimestamp(t, dt.timezone.utc).date() for t in bars_t]
    W_ = wicks(s_['chart'])
    x0 = float(W_[0]['x1']); slot = float(W_[1]['x1']) - x0
    X = lambda i: x0 + slot * i
    ncand = len(W_)
    if kind == 'example':
        E_mine = next(i for i in range(len(opens)) if (opens[i + 1] - dt.timedelta(days=1) if i + 1 < len(opens) else None) == v['s']['d0'])
        chk(st, loc, 'example entry_index = the bar that closes on 22 Sept 2024', ex['entry_index'], E_mine, 'example entry bar')
        chk(st, loc, 'example entry_close', ex['entry_close'], K.rhaz(v['s']['entry'], 2), 'example entry close')
        chk(st, loc, 'candles drawn', ncand, (len(opens) if happened else E_mine + 1), 'candles drawn (At the alert must stop at the entry bar)')
        A = E_mine; d0 = v['s']['d0']; entry = v['s']['entry']
    elif kind == 'open':
        s = v['s']; d0 = s['d0']; entry = s['entry']
        E_mine = covering(opens, d0)
        chk(st, loc, 'entry bar closes on the entry date', (opens[E_mine + 1] - dt.timedelta(days=1)) if E_mine + 1 < len(opens) else None, d0, 'entry bar')
        A = E_mine
        chk(st, loc, 'candles drawn (all, live)', ncand, len(opens), 'candles drawn')
    else:
        fm = v['fm']; d0 = fm['d0']; entry = v['price_now']
        E_mine = len(opens) - 1
        A = None
        chk(st, loc, 'candles drawn (all)', ncand, len(opens), 'candles drawn')
        chk(st, loc, 'last drawn bar contains today', opens[-1] <= today, True, 'today bar')
    nslots_needed = 200
    cal = slot_calendar(bars_t, tf, nslots_needed)
    if kind == 'forming':
        A = covering(cal, d0)
        chk(st, loc, 'confirmation bar closes on confirms_on', cal[A + 1] - dt.timedelta(days=1), d0, 'confirmation bar')
    V = vlines(s_['chart'])
    vd = {lab.split(' ')[0] if not lab.startswith('High') else 'High': x for lab, x in V}
    # Entry / Today line
    lab0 = 'Today' if kind == 'forming' else 'Entry'
    chk(st, loc, f'"{lab0}" line on bar {opens[E_mine]}', round(vd.get(lab0, -1), 6), round(X(E_mine), 6), f'{lab0} line position')
    # Day 60 line: on the bar that covers day 60 after the entry close
    i60 = covering(cal, d0 + dt.timedelta(days=60))
    chk(st, loc, f'"Day 60" line on the bar covering {d0 + dt.timedelta(days=60)}', round(vd.get('Day', -1), 6), round(X(i60), 6),
        'Day 60 line one bar early: the page counts 60/tf bars and ignores the 1 Jan bar restart' if i60 is not None and abs(vd.get('Day', -1) - X(i60 - 1)) < 1e-6 else 'Day 60 line position')
    # High line
    hl = next((lab for lab, x in V if lab.startswith('High usually')), None)
    chk(st, loc, 'High line label', hl, f"High usually ~day {f['dHigh']}", 'high label')
    ih = covering(cal, d0 + dt.timedelta(days=f['dHigh']))
    chk(st, loc, f'High line on the bar covering day {f["dHigh"]} ({d0 + dt.timedelta(days=f["dHigh"])})', round(vd.get('High', -1), 6), round(X(ih), 6), 'high line position')
    if kind == 'forming':
        cl = next((lab for lab, x in V if lab.startswith('Confirms')), None)
        chk(st, loc, 'Confirms line label', cl, f"Confirms {fdate(d0)} · entry, day 0", 'confirms label')
        chk(st, loc, 'Confirms line position', round(vd.get('Confirms', -1), 6), round(X(A), 6), 'confirms line position')
    # date axis labels
    for t in texts(s_['chart']):
        if t.get('y') == '502':
            i = round((float(t['x']) - x0) / slot)
            chk(st, loc, f'axis date label at slot {i}', t['text'], faxis(cal[i]),
                'axis date past 1 Jan: the page steps tf days and ignores the bar restart' if cal[i].year > opens[-1].year else 'axis label')
    # ----- price levels
    T = {t['text']: t for t in texts(s_['chart'])}
    hi_p = entry * (1 + Fr(f['best']) / 100); t10 = entry * Fr(11, 10); dr_p = entry * (1 + Fr(f['deepest']) / 100)
    ek, ep = e['edge']
    want_texts = [f"Typical high {fpct(f['best'])}", f"+10% · {f['reach10']}% of past signals got here", f"Typical drop {fpct(f['deepest'])}",
                  fmoney(hi_p), fmoney(t10), fmoney(entry), fmoney(dr_p)]
    if ek == 'fall':
        want_texts.append(f"Edge gone below {fmoney(entry * (1 + Fr(ep, 100)))} ({fpct(ep, 0)}, before +10%)")
    for wt in want_texts:
        chk(st, loc, f'chart text "{wt}"', wt in T, True, 'chart level text')
    # y geometry: fit price->y from the entry and +10% lines, then every level line, wick and zone
    HL = hlines(s_['chart'])
    byc = {}
    for h in HL:
        byc.setdefault(h.get('sstroke'), []).append(float(h['y1']))
    ye = byc['var(--soft)'][0]; y10 = byc['var(--text)'][0]
    k = (ye - y10) / float(t10 - entry)
    Yp = lambda p: ye - k * (float(p) - float(entry))
    chk(st, loc, 'Typical high line y', round(byc['var(--high)'][0], 4), round(Yp(hi_p), 4), 'level line y')
    chk(st, loc, 'Typical drop line y', round(byc['var(--drop)'][0], 4), round(Yp(dr_p), 4), 'level line y')
    if ek == 'fall':
        chk(st, loc, 'Edge line y', round(byc.get('var(--fade-2)', [-1])[0], 4), round(Yp(entry * (1 + Fr(ep, 100))), 4), 'edge line y')
    else:
        chk(st, loc, 'no edge line', 'var(--fade-2)' in byc, False, 'edge line')
    bad = 0
    for i, w in enumerate(W_):
        b = bar_src[i]
        if abs(float(w['y1']) - Yp(Fr(str(b['h'])))) > 1e-3 or abs(float(w['y2']) - Yp(Fr(str(b['l'])))) > 1e-3:
            bad += 1
    chk(st, loc, 'every candle wick at its high/low', bad, 0, 'wick y')
    # ladder zones (this setup's own fade): 0/-5 base, then -5/-10, -10/-15, -15/-20
    zr = [r for r in s_['chart'] if r['tag'] == 'rect' and r.get('opacity') == '0.24']
    steps = [(0, -5, f['reach10'])] + [(-x['fell'], -(x['fell'] + 5), x['ok']) for x in f['lad'][:3]]
    for (a1, b1, val), r in zip(steps, zr):
        y1 = Yp(entry * (1 + Fr(a1, 100))); y2 = min(480, Yp(entry * (1 + Fr(b1, 100))))
        chk(st, loc, f'zone {a1}% to {b1}% top/height', (round(float(r['y']), 3), round(float(r['height']), 3)), (round(y1, 3), round(y2 - y1, 3)), 'zone')
    ztxt = [t['text'] for t in texts(s_['chart']) if t.get('sfill') == 'var(--text)' and re.fullmatch(r'\d+%|n/a', t['text'] or '')]
    hsteps = [f['reach10']] + [x['ok'] for x in f['lad_hf'][:3]]
    chk(st, loc, 'zone labels', str(ztxt), str([('n/a' if v_ is None else f'{v_}%') for _, _, v_ in steps]),
        'first-fall step checks the HIGH before the LOW within a daily bar (stated choice (c): low first)' if str(ztxt) == str([('n/a' if v_ is None else f'{v_}%') for v_ in hsteps]) else 'zone labels')
    # low marker (forming) / outcome markers (example, What happened)
    circ = [x for x in s_['chart'] if x['tag'] == 'circle']
    if kind == 'forming':
        fm = v['fm']; it = opens.index(fm['trough'])
        dd = K.Daily(root, a); lo_day = dt.date.fromisoformat(v['low_day'])
        lt = next((t['text'] for t in texts(s_['chart']) if t['text'].startswith('Low ')), None)
        chk(st, loc, 'low marker label', lt, f"Low {fdate(lo_day)} · {fmoney(dd.bar(lo_day)[1])}", 'low marker')
        chk(st, loc, 'low marker x on the trough bar', round(float(circ[0]['cx']), 6), round(X(it), 6), 'low marker x')
    else:
        lt = [t['text'] for t in texts(s_['chart']) if t['text'].startswith('This one')]
        if kind == 'example' and happened:
            w = v['s']['w']; en = v['s']['entry']
            hi = max(w, key=lambda x: (x[1], -x[0])); lo = min(w, key=lambda x: (x[2], x[0]))
            def rng(k_):
                j = covering(cal, d0 + dt.timedelta(days=k_)); d_ = (j - A) * 2
                return f'days {d_ - 1}–{d_}'
            want = [f"This one: {fmoney(hi[1])} · {fpct((hi[1] / en - 1) * 100)} · {rng(hi[0])}", f"This one: {fmoney(lo[2])} · {fpct((lo[2] / en - 1) * 100)} · {rng(lo[0])}"]
            chk(st, loc, 'outcome markers', str(lt), str(want), 'outcome marker')
        else:
            chk(st, loc, 'no outcome markers', str(lt), '[]', 'outcome shown at the alert')
    # the y-axis range in "At the alert" (example): set by bars after the entry?
    if kind == 'example' and mode == 'alert':
        top_p = float(entry) + (ye - 24) / k; bot_p = float(entry) - (480 - ye) / k
        pre = bar_src[:A + 1]
        lo_all = min(min(b['l'] for b in bar_src), float(dr_p), float(entry) * 0.8) * 0.95; hi_all = max(max(b['h'] for b in bar_src), float(hi_p)) * 1.07
        lo_pre = min(min(b['l'] for b in pre), float(dr_p), float(entry) * 0.8) * 0.95; hi_pre = max(max(b['h'] for b in pre), float(hi_p)) * 1.07
        chk(st, loc, 'y-axis range uses only what was known at the alert', (round(top_p, 2), round(bot_p, 2)), (round(hi_pre, 2), round(lo_pre, 2)),
            'At the alert, the price axis is scaled by bars AFTER the entry (outcome leaks into the axis)' if abs(top_p - hi_all) < 0.01 and abs(hi_all - hi_pre) > 0.01 else 'axis range')
    # ----- title, subtitle, side panel
    if kind == 'forming':
        title = f"{a} · {tf} · " + ('setup forming' if c['grade'] == 'A+' else 'forming, not top grade')
        sub = (f"Low {fdate(v['low_day'])} · confirms {fdate(d0)} · price levels drawn from today's price ({fmoney(entry)}), since the entry price is the "
               f"confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them.")
    elif kind == 'open':
        title = f"{a} · {tf} · live setup, day {(today - d0).days} of 60"
        sub = f"Confirmed {fdate(d0)} · entry close {fmoney(entry)}. Zones use this setup's own card ({c['sample']}). The shaded zones are the next 60 days, as the odds draw them."
    else:
        title = 'ETH · 2-day · example: past confirmed setup'
        sub = (f"Confirmed {fdate(d0)} · entry close {fmoney(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them."
               + ('' if happened else ' The shaded zones are the next 60 days, as the odds draw them.'))
    chk(st, loc, 'title', norm(s_['chTitle']).lower(), title.lower(), 'chart title')
    chk(st, loc, 'subtitle', norm(s_['chSub']), sub, 'chart subtitle')
    kv = {norm(x[0]): norm(x[1]) for x in s_['sideKV']}
    chk(st, loc, 'side: Typical high', kv.get('Typical high'), f"{fpct(f['best'])} · {fmoney(hi_p)}", 'side price')
    chk(st, loc, 'side: +10% target', kv.get('+10% target'), fmoney(t10), 'side price')
    chk(st, loc, 'side: Reached +20%', kv.get('Reached +20%'), f"{f['reach20']}%", 'side')
    chk(st, loc, 'side: Typical drop', kv.get('Typical drop'), f"{fpct(f['deepest'])} · {fmoney(dr_p)}", 'side price')
    chk(st, loc, 'side: Edge gone below', kv.get('Edge gone below'),
        'below the bar already' if ek == 'base' else (f"{fmoney(entry * (1 + Fr(ep, 100)))} ({fpct(ep, 0)})" if ek == 'fall' else 'holds at every level'), 'side edge')
    side = norm(s_['side'])
    chk(st, loc, 'side: big number and line', f"{f['reach10']}% rose 10% within 60 days, from {f['n']} past signals; {f['surv10']}% without ever falling 25.3%" in side, True, 'side big number')
    chk(st, loc, 'side: sample line', (f"{c['chart']} · from {c['sample']}" if kind != 'example' else f"{c['chart']} · example") in side, True, 'side sample')
    if kind == 'open':
        w = v['w']; s = v['s']
        d10 = next((x for x in w if x[0] == 10), None)
        chk(st, loc, 'side: Live day', f"Live: day {(today - d0).days} of 60".lower() in side.lower(), True, 'side live day')
        chk(st, loc, 'side: Best so far', kv.get('Best so far'), fpct((max(x[1] for x in w) / s['entry'] - 1) * 100), 'side best')
        chk(st, loc, 'side: Worst so far', kv.get('Worst so far'), fpct((min(x[2] for x in w) / s['entry'] - 1) * 100), 'side worst')
        chk(st, loc, 'side: Day 10', kv.get('Day 10'), 'not yet' if d10 is None else fpct((d10[3] / s['entry'] - 1) * 100), 'side day 10')
    if kind == 'example' and happened:
        w = v['s']['w']; en = v['s']['entry']
        hi = max(w, key=lambda x: (x[1], -x[0])); lo = min(w, key=lambda x: (x[2], x[0]))
        def rng(k_):
            j = covering(cal, d0 + dt.timedelta(days=k_)); d_ = (j - A) * 2
            return f'days {d_ - 1}–{d_}'
        d10 = next(x for x in w if x[0] == 10); d60 = next(x for x in w if x[0] == 60)
        chk(st, loc, 'side: Reached +10% / +20%', kv.get('Reached +10% / +20%'), f"{'Yes' if hi[1] >= en * Fr(11, 10) else 'No'} / {'Yes' if hi[1] >= en * Fr(6, 5) else 'No'}", 'side reached')
        chk(st, loc, 'side: Best price', kv.get('Best price'), f"{fpct((hi[1] / en - 1) * 100)}, {rng(hi[0])}", 'side best')
        chk(st, loc, 'side: Deepest drop', kv.get('Deepest drop'), f"{fpct((lo[2] / en - 1) * 100)}, {rng(lo[0])}", 'side deepest')
        chk(st, loc, 'side: Day 10 check', kv.get('Day 10 check'), f"{'Red' if d10[3] < en else 'Green'}, {fpct((d10[3] / en - 1) * 100)}", 'side day 10')
        chk(st, loc, 'side: Price on day 60', kv.get('Price on day 60'), fpct((d60[3] / en - 1) * 100), 'side day 60')
    if kind == 'forming':
        chk(st, loc, 'side: forming note', f"Still forming. It confirms only if it holds through {fdate(d0)}, and it can vanish before then." in side, True, 'side forming')
    # ----- the cloud
    pp = next(p for p in feed['past_paths'] if p['asset'] == a)
    mine_pp = C['pp'][a]
    chk(st, loc, 'cloud subtitle', norm(s_['cloudSub']), f"Every past {a} top-grade signal, n {mine_pp['n']}", 'cloud n')
    note = norm(s_['cloudNote'])
    want_note = f"Day 60: median {fpct(mine_pp['med'][60])}, middle half {fpct(mine_pp['q25'][60])} to {fpct(mine_pp['q75'][60])}. Daily closes."
    chk(st, loc, 'cloud day-60 note', want_note in note, True, 'cloud note')
    chk(st, loc, 'cloud "not top grade" note', 'the selected setup isn\'t top grade' in note, c['grade'] != 'A+', 'cloud note')
    pl = [x for x in s_['cloud'] if x['tag'] == 'polyline']
    med_pts = [tuple(map(float, p.split(','))) for p in pl[0]['points'].split()]
    Xc = lambda d_: 20 + 940 * d_ / 60
    Yc = lambda v_: 230 - (max(-40, min(100, v_)) + 40) / 140 * 218
    badp = sum(1 for d_, (px, py) in enumerate(med_pts) if abs(px - Xc(d_)) > 1e-6 or abs(py - Yc(K.rhaz(mine_pp['med'][d_], 1))) > 1e-6)
    chk(st, loc, 'cloud median path points (61 days)', badp, 0, 'cloud path')
    poly = [x for x in s_['cloud'] if x['tag'] == 'polygon'][0]
    pts = [tuple(map(float, p.split(','))) for p in poly['points'].split()]
    want = [(Xc(d_), Yc(K.rhaz(mine_pp['q75'][d_], 1))) for d_ in range(61)] + [(Xc(d_), Yc(K.rhaz(mine_pp['q25'][d_], 1))) for d_ in range(60, -1, -1)]
    badb = sum(1 for p, q in zip(pts, want) if abs(p[0] - q[0]) > 1e-6 or abs(p[1] - q[1]) > 1e-6)
    chk(st, loc, 'cloud middle-half band (122 vertices)', badb, 0, 'cloud band')
    if kind == 'example':
        if happened:
            w = v['s']['w']; en = v['s']['entry']
            ws = [(0, Fr(0))] + [(x[0], (x[3] / en - 1) * 100) for x in w if x[0] % 2 == 0]
            pts2 = [tuple(map(float, p.split(','))) for p in pl[1]['points'].split()] if len(pl) > 1 else []
            badt = sum(1 for (d_, v_), (px, py) in zip(ws, pts2) if abs(px - Xc(d_)) > 1e-6 or abs(py - Yc(float(v_))) > 1e-6)
            chk(st, loc, 'cloud "this signal" path', (len(pts2), badt), (31, 0), 'cloud this-signal path')
        else:
            chk(st, loc, 'cloud has no "this signal" path at the alert', len(pl), 1, 'outcome shown at the alert')
    chk(st, loc, 'toggle shown only for the example', s_['toggleHidden'], kind != 'example', 'toggle')


def check_record(st, L, snaps, pairs, feed):
    for a in ('all', 'ETH', 'BTC'):
        s_ = snaps.get(f'record:{a}')
        loc = f'{L} Past signals [{a}]'
        rows = [(r, s) for r, s in pairs if r['grade'] == 'A+' and (a == 'all' or r['asset'] == a)]
        miss = sum(1 for _, s in rows if not s['m']['r10'])
        chk(st, loc, 'count line', norm(s_['recCount']), f'{len(rows)} signals · {miss} missed +10%', 'record count')
        got = s_['recRows']
        chk(st, loc, 'rows listed', len(got), len(rows), 'record rows')
        dates = [dt.date(int(x[0].split()[2]), MON.index(x[0].split()[1]), int(x[0].split()[0])) for x in got]
        chk(st, loc, 'newest first', dates == sorted(dates, reverse=True), True, 'record order')
        mine = {(fdate(s['d0']), r['chart']): (r, s) for r, s in rows}
        for x in got:
            k = (x[0], x[1]); rs = mine.get(k)
            if not rs:
                chk(st, loc, f'row {k}', 'listed', 'not a top-grade signal', 'record row'); continue
            r, s = rs; m = s['m']
            want = [fdate(s['d0']), r['chart'], fmoney(s['entry']), 'Yes' if m['r10'] else 'No', 'Yes' if m['r20'] else 'No',
                    fpct(m['up']), fpct(m['dd']), fpct(m['ret']), str(m['dpk'])]
            heads = ['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day']
            for h, g_, w_ in zip(heads, x, want):
                chk(st, loc, f'{k[1]} {s["d0"]} {h}', norm(g_), w_, f'record {h}')
        # summary boxes
        for box in s_['recSum']:
            t = norm(box); asset = t.split()[0]
            rr = [(r, s) for r, s in pairs if r['grade'] == 'A+' and r['asset'] == asset]
            ms = [s['m'] for _, s in rr]; n = len(ms)
            mi = misses(pairs, asset, 'A+')
            want = (f"{asset} {n} signals Rose 10% in 60 days {K.share(sum(m['r10'] for m in ms), n)}% Reached +20% in 60 days {K.share(sum(m['r20'] for m in ms), n)}% "
                    f"Rose 10%, never fell 25.3% {K.share(sum(m['surv10'] for m in ms), n)}% Median deepest dip {fpct(K.median([m['dd'] for m in ms]))} "
                    f"Misses: median best price {fpct(mi['peak'])}")
            chk(st, loc, f'summary box {asset}', t, want, 'record summary')
        chk(st, loc, 'summary boxes shown', len(s_['recSum']), 2 if a == 'all' else 1, 'record summary')


def check_read(st, L, snaps):
    s_ = snaps.get('read')
    t = norm(s_['readTab'])
    for phrase in ('rose 10% within 60 days of the entry close', 'without ever falling 25.3% below the entry close',
                   '3.3x leverage with 5% maintenance margin', 'The median best price within 60 days, from the entry close',
                   'The median deepest dip within 60 days', 'our 70% bar'):
        chk(st, f'{L} How to read', f'text: "{phrase}"', phrase in t, True, 'how-to-read text')
