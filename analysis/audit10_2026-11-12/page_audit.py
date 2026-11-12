"""Audit #10: the member page, rendered with Playwright, every displayed number against my own values.

  python3 page_audit.py <state_dir> <label>
"""
import csv, json, os, re, sys, datetime as dt
from decimal import Decimal as Dec
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib as L
from playwright.sync_api import sync_playwright

STATE, LABEL = sys.argv[1], sys.argv[2]
MINE = json.load(open(os.path.join(HERE, f'mine_{LABEL}.json')))
FEED = json.load(open(os.path.join(STATE, 'feed', 'ctzb_feed.json')))
LEDGER_TXT = open(os.path.join(STATE, 'datasets', 'ledger.csv')).read()
PAGE = open(os.path.join(STATE, 'docs', 'artifacts', 'member-site', 'index.html')).read()
EXJ = open(os.path.join(STATE, 'docs', 'artifacts', 'member-site', 'data', 'example_ETH-2D-2024-09-22.json')).read()
TODAY = dt.date.fromisoformat(MINE['today'])
CHECKS = []
MINUS = '−'; NDASH = '–'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']


def chk(loc, label, shown, yours, cause=''):
    ok = str(shown).strip() == str(yours).strip()
    CHECKS.append(dict(state=LABEL, location='page ' + loc, label=label, shown=shown, yours=yours, ok=ok, cause='' if ok else cause))
    return ok


def D(x): return Dec(str(x))


def fmt(v, d=1):
    r = L.rhalf(D(v), d)
    if r == 0: return f'{Dec(0):.{d}f}'
    s = f'{abs(r):.{d}f}'
    return (MINUS if r < 0 else '') + s


def pct(v, d=1, sign=True):
    if v is None or v == 'None': return 'n/a'
    r = L.rhalf(D(v), d)
    return ('+' if sign and r > 0 else '') + fmt(v, d) + '%'


def money(v):
    r = L.rhalf(D(v), 2)
    return '$' + f'{r:,.2f}'


def dlong(iso):
    d = dt.date.fromisoformat(str(iso)[:10]); return f'{d.day} {MON[d.month - 1]} {d.year}'


def price(entry, p):
    return money(D(entry) * (1 + D(p) / 100))


# ---------------------------------------------------------------- routes
def candles_json(asset, tf):
    p = os.path.join(STATE, 'datasets', f'candles_{asset.lower()}_{tf.lower()}.csv')
    bars = [dict(t=int(r['time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close'])) for r in csv.DictReader(open(p))]
    return {'chart': f'{asset} {tf}', 'bars': bars}


CAND = {(a, tf): candles_json(a, tf) for a in ('ETH', 'BTC') for tf in ('1D', '2D', '3D', '5D', '8D')}
# candle files (served to the chart) vs the raw data: the last 70 bars
for (a, tf), cj in CAND.items():
    raw, _ = L.load(os.path.join(STATE, 'data', f'{a}_{tf}.csv'), clamp=False)
    last = raw[-70:]
    bad = sum(1 for x, y in zip(cj['bars'], last) if (x['t'], D(x['o']), D(x['h']), D(x['l']), D(x['c'])) != (y['t'], y['o'], y['h'], y['l'], y['c'])) + abs(len(last) - len(cj['bars']))
    chk(f'chart data {a} {tf}', 'candles = last 70 raw bars', bad, 0, 'chart candles differ from raw data')
# example json vs raw ETH 2D
EX = json.loads(EXJ)
raw2, _ = L.load(os.path.join(STATE, 'data', 'ETH_2D.csv'), clamp=False)
pos2 = {b['t']: b for b in raw2}
bad = sum(1 for b in EX['bars'] if b['t'] not in pos2 or (D(b['o']), D(b['h']), D(b['l']), D(b['c'])) != (pos2[b['t']]['o'], pos2[b['t']]['h'], pos2[b['t']]['l'], pos2[b['t']]['c']))
chk('example chart data', 'example bars = raw ETH 2D bars', bad, 0, 'example bars differ from raw data')
eb = EX['bars'][EX['entry_index']]
chk('example chart data', 'entry bar closes on 2024-09-22', str(L.bucket_span(L.udate(eb['t']), 2)[1]), '2024-09-22')
chk('example chart data', 'entry_close', money(EX['entry_close']), money(MINE['example_sig']['entry']))
ib = [L.udate(b['t']) for b in EX['bars']]
chk('example chart data', 'bars contiguous (no missing 2D bar)', all(L.bucket_span(ib[i], 2)[1] + dt.timedelta(days=1) == ib[i + 1] for i in range(len(ib) - 1)), True)
chk('example chart data', 'bars cover entry + 60 days', str(L.bucket_span(ib[-1], 2)[1]) >= str(dt.date(2024, 9, 22) + dt.timedelta(days=60)), True)

WRAP = '<!doctype html><html><head><meta charset=utf-8></head><body>' + PAGE + '</body></html>'


def route(r):
    u = r.request.url
    if 'fonts.googleapis' in u or 'fonts.gstatic' in u: return r.abort()
    p = u.split('site.test/', 1)[1].split('#')[0] if 'site.test/' in u else None
    if p is None: return r.fulfill(status=404, body='')
    if p == '': return r.fulfill(status=200, content_type='text/html', body=WRAP)
    if p == 'data/ctzb_feed.json': return r.fulfill(status=200, content_type='application/json', body=json.dumps(FEED))
    if p == 'data/ledger.csv': return r.fulfill(status=200, content_type='text/csv', body=LEDGER_TXT)
    m = re.match(r'data/candles/(ETH|BTC)_(1D|2D|3D|5D|8D)\.json$', p)
    if m: return r.fulfill(status=200, content_type='application/json', body=json.dumps(CAND[(m.group(1), m.group(2))]))
    if p == 'data/example_ETH-2D-2024-09-22.json': return r.fulfill(status=200, content_type='application/json', body=EXJ)
    return r.fulfill(status=404, body='')


GRAB_CARD = """() => {
 const t = (s, r=document) => { const e = r.querySelector(s); return e ? e.textContent.replace(/\\s+/g,' ').trim() : null; };
 const c = document.querySelector('#card');
 return {
  where: t('.card-head .where', c), state: t('.card-head .state', c),
  heads: Array.from(c.querySelectorAll('.card-head .small')).map(e => e.textContent.replace(/\\s+/g,' ').trim()),
  big: t('.odds .big', c), odds: Array.from(c.querySelectorAll('.odds > div')).map(e => e.textContent.replace(/\\s+/g,' ').trim()),
  stats: Array.from(c.querySelectorAll('.stats .kv')).map(k => Array.from(k.children).map(e => e.textContent.replace(/\\s+/g,' ').trim())),
  pool: Array.from(c.querySelectorAll('.stats > .fine')).map(e => e.textContent.trim()),
  marker: t('.marker', c),
  tiles: Array.from(c.querySelectorAll('.tile')).map(e => [t('.t', e), t('.v', e)]),
  ladder: Array.from(c.querySelectorAll('#ladder .bar')).map(b => [b.children[0].textContent.replace(/\\s+/g,' ').trim(), b.children[2].textContent.trim(), b.querySelector('.f').classList.contains('gone'), b.querySelector('.f').style.width]),
  ladnote: t('#ladder .fine', c),
  eras: Array.from(c.querySelectorAll('#eras .bar')).map(b => [b.children[0].textContent.replace(/\\s+/g,' ').trim(), b.children[2].textContent.trim()]),
  frame: document.querySelector('#cardFrame').style.getPropertyValue('--c'),
  picker: Array.from(document.querySelectorAll('#picker button')).map(b => [b.dataset.sel, b.textContent.replace(/\\s+/g,' ').trim(), b.getAttribute('aria-pressed')]),
  pnone: Array.from(document.querySelectorAll('#picker .pnone')).map(e => e.textContent.trim()),
 }; }"""

GRAB_CHART = """() => {
 const svg = document.querySelector('#chartSvg');
 const els = Array.from(svg.children).map(e => ({tag: e.tagName, a: Object.fromEntries(Array.from(e.attributes).map(x => [x.name, x.value])), style: e.getAttribute('style') || '', text: e.textContent}));
 const cl = document.querySelector('#cloudSvg');
 const cels = Array.from(cl.children).map(e => ({tag: e.tagName, a: Object.fromEntries(Array.from(e.attributes).map(x => [x.name, x.value])), text: e.textContent}));
 return {title: document.querySelector('#chTitle').textContent, sub: document.querySelector('#chSub').textContent,
   toggleHidden: document.querySelector('.toggle').hidden, els, cels,
   cloudSub: document.querySelector('#cloudSub').textContent, cloudNote: document.querySelector('#cloudNote').textContent.replace(/\\s+/g,' ').trim(),
   side: Array.from(document.querySelectorAll('#chartSide .sidebox')).map(b => ({title: (b.querySelector('.sec-title')||{}).textContent || null,
      kv: Array.from(b.querySelectorAll('.kv')).map(k => Array.from(k.children).map(x => x.textContent.replace(/\\s+/g,' ').trim())),
      text: b.textContent.replace(/\\s+/g,' ').trim(), big: (b.querySelector('div[style*=\"42px\"]')||{}).textContent || null,
      smalls: Array.from(b.querySelectorAll(':scope > .small')).map(x => x.textContent.replace(/\\s+/g,' ').trim())}))};
 }"""


# ---------------------------------------------------------------- expected card models (from MY values)
def model_for(kind, sid):
    if kind == 'open':
        f = MINE['open'][sid]; o = next(x for x in FEED['open_signals'] if x['signal_id'] == sid)
        asset, tf = o['chart'].split()
        return dict(kind='open', f=f, asset=asset, tf=tf, grade=f['grade'], entry=f['entry'], top=f['grade'] == 'A+', chart=o['chart'],
                    misses=MINE['misses'].get(f"{asset}|{f['grade']}"), sid=sid)
    if kind == 'forming':
        f = MINE['cards'][sid]; fm = MINE['forming'][sid]
        grade = next(c['grade'] for c in FEED['cards'] if c['signal_id'] == sid)   # grade taken as given
        return dict(kind='forming', f=f, fm=fm, asset=fm['a'], tf=fm['tf'], grade=grade, entry=fm['price'], top=grade == 'A+',
                    chart=f"{fm['a']} {fm['tf']}", misses=MINE['misses'].get(f"{fm['a']}|{grade}"), sid=sid)
    f = MINE['example']
    return dict(kind='example', f=f, asset='ETH', tf='2D', grade='A+', entry=MINE['example_sig']['entry'], top=True, chart='ETH 2D',
                misses=MINE['exmiss'], sid='ETH-2D-2024-09-22')


def edge_txt(f):
    e = f['edge']
    return 'Below the 70% bar from entry' if e == 0 else 'Holds at every level' if e is None else f'{pct(e, 0)} before it rises 10%'


def check_card(loc, g, M, best_forming_sid):
    f = M['f']; mi = M['misses']
    chk(loc, 'where', g['where'], f"{M['asset']} · {M['tf']} chart" + (' · example' if M['kind'] == 'example' else ''))
    chk(loc, 'state', g['state'], {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[M['kind']])
    if M['kind'] == 'open':
        line = f"Confirmed {dlong(f['entry_date'])} · entry close {money(f['entry'])} · day {f['days']} of 60 · best so far {pct(f['bsf'])} · worst {pct(f['wsf'])}"
    elif M['kind'] == 'forming':
        fm = M['fm']; line = f"Low {dlong(fm['lowday'])} · confirms {dlong(fm['d0'])}" + (f" if it closes above {money(fm['kill'])}" if fm['kill'] != 'None' else '')
    else:
        line = f"Example: confirmed {dlong('2024-09-22')} · entry close {money(M['entry'])}"
    chk(loc, 'header line', g['heads'][0] if g['heads'] else None, line)
    if M['kind'] == 'forming':
        note = ((('Best setup forming today.' if best_forming_sid == M['sid'] else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
                if not M['top'] else 'Not confirmed yet. It can still vanish before it confirms.')
        chk(loc, 'forming note', g['heads'][1] if len(g['heads']) > 1 else None, note)
    chk(loc, 'big number (rose 10% within 60 days)', g['big'], f"{f['reach10']}%")
    chk(loc, 'line under big number', g['odds'][2], f"{f['surv10']}% did it without ever falling 25.3%")
    chk(loc, 'sample line', g['odds'][3], f"from {f['n']} past signals like this one · every figure covers the 60 days after entry")
    st = {x[0]: x[1] for x in g['stats']}
    chk(loc, 'Typical high', st.get('Typical high'), pct(f['bestX']))
    chk(loc, 'Typical drop from entry', st.get('Typical drop from entry'), pct(f['deepX']))
    chk(loc, 'Edge gone below', st.get('Edge gone below'), edge_txt(f))
    chk(loc, 'If it misses: went above entry', st.get('If it misses: went above entry'),
        f"{mi['up_first']} of {mi['misses']} · median best {pct(mi.get('median_peak_pct'))}" if mi else 'n/a')
    if M['kind'] == 'forming' and not M['top']:
        chk(loc, 'misses pool line', g['pool'][0] if g['pool'] else None, f"all {mi['signals']} {M['asset']} signals of this grade")
    chk(loc, 'lead trader marker', g['marker'], 'Lead trader: unavailable')
    tl = {x[0]: x[1] for x in g['tiles']}
    chk(loc, 'tile Dip before the high', tl.get('Dip before the high, from entry'), pct(f['dipbX']))
    chk(loc, 'tile High lands around', tl.get('High lands around'), f"Day {f['tH']}")
    chk(loc, 'tile Reached +20%', tl.get(f"Reached +20% within 60 days · n {f['n']}"), f"{f['reach20']}%", 'tile label n or value')
    chk(loc, 'tile Touched -30%', tl.get(f"Touched {MINUS}30% within 60 days · n {f['n']}"), f"{f['touched30']}%", 'tile label n or value')
    chk(loc, 'tile Typical high', tl.get('Typical high'), pct(f['bestX']))
    chk(loc, 'tile Deepest dip lands around', tl.get('Deepest dip lands around'), f"Day {f['tL']}")
    ms = f" · {mi['misses']} misses of all {mi['signals']} {M['asset']} {M['grade']}"
    chk(loc, 'tile Typical worst drop, misses', tl.get('Typical worst drop, misses' + ms), pct(mi.get('median_worst_drop_pct')), 'tile label or value')
    chk(loc, 'tile Typical change by day 60, misses', tl.get('Typical change by day 60, misses' + ms), pct(mi.get('median_day60_pct')), 'tile label or value')
    exp = [(f"From entry n {f['n']}", f"{f['l0ok']}%", float(f['l0x']) < 70)]
    for th in (5, 10, 15, 20):
        v = f[f'l{th}ok']
        exp.append((f"Falls {th}% first n {f[f'l{th}n']}", 'n/a' if v in (None, 'None') else f'{v}%', v not in (None, 'None') and float(f[f'l{th}x']) < 70))
    chk(loc, 'ladder rows', len(g['ladder']), len(exp))
    for (lab, val, gone, w), (el, ev, eg) in zip(g['ladder'], exp):
        chk(loc, f'ladder "{el}" label', lab, el); chk(loc, f'ladder "{el}" value', val, ev); chk(loc, f'ladder "{el}" below 70% mark (exact)', gone, eg)
    era = [(f"Before 2022 n {f['nOld']}", f"{f['sOld']}%"), (f"Since 2022 n {f['nNew']}", f"{f['sNew']}%")]
    for (lab, val), (el, ev) in zip(g['eras'], era):
        chk(loc, f'era {el}', f'{lab} {val}', f'{el} {ev}')


# ---------------------------------------------------------------- chart expectations
LX, RX, TY, BY = 20, 960, 24, 480


def next_open(d, tfd):
    return d + dt.timedelta(days=1) if tfd == 1 else L.bucket_span(d, tfd)[1] + dt.timedelta(days=1)


def slot_of(opens, d):
    i = 0
    while i + 1 < len(opens) and opens[i + 1] <= d: i += 1
    return i


def find_text(els, prefix):
    return [e for e in els if e['tag'] == 'text' and e['text'].startswith(prefix)]


def check_chart(loc, g, M, mode):
    f = M['f']; tfd = int(M['tf'][:-1]); els = g['els']
    if M['kind'] == 'example':
        bars = EX['bars']; E = EX['entry_index']; entry = D(M['entry']); entry_day = dt.date(2024, 9, 22)
        opens = [L.udate(b['t']) for b in bars]; nslots = len(bars)
    else:
        cj = CAND[(M['asset'], M['tf'])]; bars = cj['bars']; opens = [L.udate(b['t']) for b in bars]
        if M['kind'] == 'open':
            entry_day = dt.date.fromisoformat(f['entry_date']); entry = D(f['entry'])
            E = next(i for i, d in enumerate(opens) if (L.bucket_span(d, tfd)[1] if tfd > 1 else d) == entry_day)
        else:
            entry_day = dt.date.fromisoformat(M['fm']['d0']); entry = D(M['entry']); E = len(bars) - 1
        while opens[-1] <= entry_day + dt.timedelta(days=61): opens.append(next_open(opens[-1], tfd))
        nslots = len(opens)
    slot = (RX - LX) / nslots; X = lambda i: LX + slot * i + slot / 2
    dayslot = lambda k: slot_of(opens, entry_day + dt.timedelta(days=k))
    # price levels
    hi_p = entry * (1 + D(f['bestX']) / 100); dr_p = entry * (1 + D(f['deepX']) / 100); t10 = entry * D('1.1')
    tags = [e['text'] for e in els if e['tag'] == 'text' and e['a'].get('fill') == '#07060F']
    chk(loc, 'price tags (high, +10%, entry, drop)', sorted(tags), sorted([money(hi_p), money(t10), money(entry), money(dr_p)]))
    chk(loc, 'label Typical high', len(find_text(els, f"Typical high {pct(f['bestX'])}")), 1)
    chk(loc, 'label +10%', len(find_text(els, f"+10% · {f['reach10']}% of past signals got here")), 1)
    chk(loc, 'label Typical drop', len(find_text(els, f"Typical drop {pct(f['deepX'])}")), 1)
    edge = f['edge']
    et = find_text(els, 'Edge gone below')
    if edge not in (None, 0):
        chk(loc, 'edge line label', et[0]['text'] if et else None, f"Edge gone below {price(entry, edge)} ({pct(edge, 0)}, before +10%)")
    else:
        chk(loc, 'no edge line (edge 0 or none)', len(et), 0)
    # vertical lines by date
    def vx(label):
        t = find_text(els, label)
        return round(float(t[0]['a']['x']) - 6, 4) if t else None
    if M['kind'] == 'forming':
        chk(loc, 'Today line on the last (open) bar', vx('Today'), round(X(len(bars) - 1), 4))
        cs = dayslot(0)
        chk(loc, 'Confirms line on the bar that closes on confirms_on', vx('Confirms'), round(X(cs), 4) if cs > len(bars) - 1 else None)
        chk(loc, 'Confirms label', (find_text(els, 'Confirms') or [{'text': None}])[0]['text'], f"Confirms {dlong(M['fm']['d0'])} · entry, day 0")
    else:
        chk(loc, 'Entry line on the bar that closes on the entry date', vx('Entry'), round(X(E), 4))
    chk(loc, 'Day 60 line on the bar containing entry+60', vx('Day 60'), round(X(min(nslots - 1, dayslot(60))), 4))
    chk(loc, 'High line on the bar containing entry+typical day', vx(f"High usually ~day {f['tH']}"), round(X(dayslot(int(f['tH']))), 4))
    chk(loc, 'no Day 10 pooled line (own ladder)', len(find_text(els, 'Day 10')), 0)
    # ladder zones
    zt = [e for e in els if e['tag'] == 'text' and e['a'].get('font-weight') == '700' and 'var(--text)' in e['style'] and re.fullmatch(r'(\d+%|n/a)', e['text'])]
    zt.sort(key=lambda e: float(e['a']['y']))
    exp = [f"{f['l0ok']}%"] + [('n/a' if f[f'l{t}ok'] in (None, 'None') else f"{f[f'l{t}ok']}%") for t in (5, 10, 15)]
    chk(loc, 'ladder zones on chart (from entry, 5, 10, 15)', [e['text'] for e in zt], exp)
    zr = [e for e in els if e['tag'] == 'rect' and 'opacity' in e['a'] and e['a']['opacity'] == '0.24']
    zr.sort(key=lambda e: float(e['a']['y']))
    expc = ['var(--high)' if float(f['l0x']) >= 70 else 'var(--drop)'] + [
        ('var(--closed)' if f[f'l{t}ok'] in (None, 'None') else 'var(--high)' if float(f[f'l{t}x']) >= 70 else 'var(--drop)') for t in (5, 10, 15)]
    chk(loc, 'ladder zone colours (exact share vs 70%)', [re.search(r'fill:\s*([^;]+)', e['style']).group(1).strip() if 'fill' in e['style'] else e['a'].get('fill') for e in zr], expc)
    # y scaling
    if M['kind'] == 'example' and mode == 'alert':
        shown = bars[:E + 1]
    else:
        shown = bars
    lo = min([D(b['l']) for b in shown] + [dr_p, entry * D('0.8')]) * D('0.95'); hi = max([D(b['h']) for b in shown] + [hi_p]) * D('1.07')
    Y = lambda p: float(BY - (p - lo) / (hi - lo) * (BY - TY))
    hl = [e for e in els if e['tag'] == 'line' and e['a'].get('y1') == e['a'].get('y2') and e['a'].get('stroke-width') == '2']
    ys = sorted(float(e['a']['y1']) for e in hl)
    for nm, p in (('entry', entry), ('+10%', t10), ('typical high', hi_p), ('typical drop', dr_p)):
        chk(loc, f'y of {nm} line (axis scaled on {"known bars only" if mode == "alert" and M["kind"] == "example" else "all bars"})',
            any(abs(y - Y(p)) < 0.01 for y in ys), True, 'axis scaling')
    # candles drawn
    cand = [e for e in els if e['tag'] == 'rect' and e['a'].get('width') and e['a'].get('x') and 'height' in e['a'] and e['a'].get('rx') is None
            and e['a'].get('opacity') is None and ('var(--high)' in e['style'] or 'var(--drop)' in e['style'])]
    ndrawn = len([e for e in els if e['tag'] == 'line' and e['a'].get('x1') == e['a'].get('x2') and e['a'].get('stroke-width') == '1.5' and ('var(--high)' in e['style'] or 'var(--drop)' in e['style']) and e['a'].get('stroke-dasharray', '') == ''])
    expn = (E + 1) if (M['kind'] == 'example' and mode == 'alert') else len(bars)
    chk(loc, 'candles drawn (alert: up to the entry bar only)', ndrawn, expn)
    this = find_text(els, 'This one:')
    if M['kind'] == 'example' and mode == 'happened':
        es = MINE['example_sig']
        def span(k):
            b = (k + 1) // 2; return f"days {2 * b - 1}{NDASH}{2 * b}"
        exp = sorted([f"This one: {money(es['hi'])} · {pct((D(es['hi']) / entry - 1) * 100)} · {span(es['hiday'])}",
                      f"This one: {money(es['lo'])} · {pct((D(es['lo']) / entry - 1) * 100)} · {span(es['loday'])}"])
        chk(loc, 'What happened markers', sorted(e['text'] for e in this), exp)
    else:
        chk(loc, 'no outcome markers', len(this), 0)
    if M['kind'] == 'forming':
        lowt = find_text(els, 'Low ')
        chk(loc, 'low marker', lowt[0]['text'] if lowt else None, f"Low {dlong(M['fm']['lowday'])} · {money(M['fm']['tlow'])}")
        circ = [e for e in els if e['tag'] == 'circle']
        li = next(i for i, d in enumerate(opens) if str(d) == M['fm']['tdate'])
        chk(loc, 'low marker on the trough bar (x, y)', (round(float(circ[0]['a']['cx']), 4), round(float(circ[0]['a']['cy']), 4)) if circ else None,
            (round(X(li), 4), round(Y(D(M['fm']['tlow'])), 4)))
    # positions: x-axis date labels, y-axis price labels, zones and level lines
    A = (dayslot(0) if M['kind'] == 'forming' else E); xE = X(A); x60 = X(min(nslots - 1, dayslot(60)))
    xl = [e for e in els if e['tag'] == 'text' and e['a'].get('y') == str(BY + 22)]
    lab = lambda i: f"{opens[min(i, len(opens) - 1)].day:02d} {MON[opens[min(i, len(opens) - 1)].month - 1]}"
    bad = [(e['text'], lab(round((float(e['a']['x']) - LX - slot / 2) / slot))) for e in xl if lab(round((float(e['a']['x']) - LX - slot / 2) / slot)) != e['text']]
    chk(loc, 'x-axis labels present', len(xl) > 0, True)
    chk(loc, 'x-axis date labels = open date of the bar under them', bad, [], 'axis label')
    yl = [e for e in els if e['tag'] == 'text' and e['a'].get('x') == str(RX + 8) and e['text'].startswith('$')]
    bad = [e['text'] for e in yl if abs(Y(D(e['text'][1:].replace(',', ''))) + 5 - float(e['a']['y'])) > 0.6]
    chk(loc, 'y-axis price labels at their own price', bad, [], 'axis label')
    rects = [e for e in els if e['tag'] == 'rect' and e['a'].get('opacity') in ('0.07', '0.1')]
    exp_r = sorted([(round(xE, 3), round(Y(hi_p), 3), round(x60 - xE, 3), round(Y(entry) - Y(hi_p), 3)),
                    (round(xE, 3), round(Y(entry), 3), round(x60 - xE, 3), round(Y(dr_p) - Y(entry), 3))])
    got_r = sorted((round(float(e['a']['x']), 3), round(float(e['a']['y']), 3), round(float(e['a']['width']), 3), round(float(e['a']['height']), 3)) for e in rects)
    chk(loc, 'shaded 60-day zones (entry to typical high / typical drop, entry bar to day 60)', got_r == exp_r or all(abs(a - b) < 0.01 for r1, r2 in zip(got_r, exp_r) for a, b in zip(r1, r2)), True, 'zone position')
    zr2 = sorted([e for e in els if e['tag'] == 'rect' and e['a'].get('opacity') == '0.24'], key=lambda e: float(e['a']['y']))
    exp_z = [(Y(entry * (1 - D(a) / 100)), min(BY, Y(entry * (1 - D(b) / 100)))) for a, b in ((0, 5), (5, 10), (10, 15), (15, 20))]
    chk(loc, 'ladder zones at 0/-5/-10/-15/-20% of entry', len(zr2) == 4 and all(abs(float(e['a']['y']) - y1) < 0.01 and abs(float(e['a']['y']) + float(e['a']['height']) - y2) < 0.01 for e, (y1, y2) in zip(zr2, exp_z)), True, 'zone position')
    lv = [e for e in hl if 'var(--fade-2)' not in e['style']]
    chk(loc, 'level lines run from the entry bar to day 60', all(abs(float(e['a']['x1']) - xE) < 0.01 and abs(float(e['a']['x2']) - x60) < 0.01 for e in lv) and len(lv) == 4, True, 'line position')
    if M['kind'] == 'example' and mode == 'happened':
        es = MINE['example_sig']; circ = [e for e in els if e['tag'] == 'circle']
        bi = lambda k: E + (k + 1) // 2
        exp_c = sorted([(round(X(bi(es['hiday'])), 3), round(Y(D(es['hi'])), 3)), (round(X(bi(es['loday'])), 3), round(Y(D(es['lo'])), 3))])
        chk(loc, 'What happened circles on the bars of the 60-day high and low', sorted((round(float(c['a']['cx']), 3), round(float(c['a']['cy']), 3)) for c in circ), exp_c)
    return dict(nslots=nslots, opens=opens, entry=entry, entry_day=entry_day)


def check_side(loc, g, M, mode):
    f = M['f']; entry = D(M['entry']); sb = g['side']
    card = sb[0]
    chk(loc, 'side big number', card['big'], f"{f['reach10']}%")
    chk(loc, 'side line', card['smalls'][1] if len(card['smalls']) > 1 else None,
        f"rose 10% within 60 days, from {f['n']} past signals; {f['surv10']}% without ever falling 25.3%")
    kv = {x[0]: x[1] for x in card['kv']}
    chk(loc, 'side Typical high', kv.get('Typical high'), f"{pct(f['bestX'])} · {price(entry, f['bestX'])}")
    chk(loc, 'side +10% target', kv.get('+10% target'), money(entry * D('1.1')))
    chk(loc, 'side Reached +20%', kv.get('Reached +20% within 60 days'), f"{f['reach20']}%")
    chk(loc, 'side Typical drop', kv.get('Typical drop'), f"{pct(f['deepX'])} · {price(entry, f['deepX'])}")
    e = f['edge']
    chk(loc, 'side Edge gone below', kv.get('Edge gone below'), 'below the bar already' if e == 0 else 'holds at every level' if e is None else f"{price(entry, e)} ({pct(e, 0)})")
    if M['kind'] == 'open':
        lv = sb[1]
        chk(loc, 'side live title', lv['title'], f"Live: day {f['days']} of 60")
        k2 = {x[0]: x[1] for x in lv['kv']}
        chk(loc, 'side Best so far', k2.get('Best so far'), pct(f['bsf'])); chk(loc, 'side Worst so far', k2.get('Worst so far'), pct(f['wsf']))
        chk(loc, 'side Day 10', k2.get('Day 10'), 'not yet' if f['d10'] in (None, 'None') else pct(f['d10']))
    if M['kind'] == 'example' and mode == 'happened':
        es = MINE['example_sig']; k2 = {x[0]: x[1] for x in sb[1]['kv']}
        span = lambda k: f"days {2 * ((k + 1) // 2) - 1}{NDASH}{2 * ((k + 1) // 2)}"
        chk(loc, 'side Reached +10% / +20%', k2.get('Reached +10% / +20%'), f"{'Yes' if es['r10'] else 'No'} / {'Yes' if es['r20'] else 'No'}")
        chk(loc, 'side Best price', k2.get('Best price'), f"{pct((D(es['hi']) / entry - 1) * 100)}, {span(es['hiday'])}")
        chk(loc, 'side Deepest drop', k2.get('Deepest drop'), f"{pct((D(es['lo']) / entry - 1) * 100)}, {span(es['loday'])}")
        c10 = D(es['c10'])
        chk(loc, 'side Day 10 check', k2.get('Day 10 check'), f"{'Red' if c10 < entry else 'Green'}, {pct((c10 / entry - 1) * 100)}")
        chk(loc, 'side Price on day 60', k2.get('Price on day 60'), pct((D(es['c60']) / entry - 1) * 100))


def check_cloud(loc, g, M, mode):
    key = 'example' if M['kind'] == 'example' else M['asset']
    days = MINE['paths_full'][key]; n = MINE['paths'][key]['n']; last = days[-1]
    chk(loc, 'cloud subtitle', g['cloudSub'], f"ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {n}" if key == 'example' else f"Every past {M['asset']} top-grade signal, n {n}")
    note = g['cloudNote']
    m = re.search(r'Day 60: median (\S+), middle half (\S+) to (\S+)\. Daily closes\.', note)
    chk(loc, 'cloud day-60 median / middle half', m.groups() if m else None, (pct(last['median_pct']), pct(last['q25_pct']), pct(last['q75_pct'])))
    if M['kind'] == 'forming' and not M['top']:
        chk(loc, 'cloud not-top-grade note', 'the selected setup isn\'t top grade' in note, True)
    Yc = lambda v: 230 - (max(-40, min(100, float(v))) + 40) / 140 * (230 - 12)
    Xc = lambda d: 20 + 940 * d / 60
    pl = [e for e in g['cels'] if e['tag'] == 'polyline']
    med = [tuple(map(float, p.split(','))) for p in pl[0]['a']['points'].split()]
    chk(loc, 'cloud median path points', all(abs(x - Xc(d['day'] if isinstance(d['day'], int) else int(d['day']))) < 1e-6 and abs(y - Yc(d['median_pct'])) < 1e-6
                                             for (x, y), d in zip(med, days)) and len(med) == 61, True)
    poly = [tuple(map(float, p.split(','))) for p in [e for e in g['cels'] if e['tag'] == 'polygon'][0]['a']['points'].split()]
    band = [(Xc(int(d['day'])), Yc(d['q75_pct'])) for d in days] + [(Xc(int(d['day'])), Yc(d['q25_pct'])) for d in reversed(days)]
    chk(loc, 'cloud middle-half band points', len(poly) == len(band) and all(abs(a - c) < 1e-6 and abs(b - e) < 1e-6 for (a, b), (c, e) in zip(poly, band)), True)
    if M['kind'] == 'example' and mode == 'happened':
        es = MINE['example_sig']; entry = D(es['entry'])
        pts = [tuple(map(float, p.split(','))) for p in pl[1]['a']['points'].split()]
        exp = [(Xc(0), Yc(0))] + [(Xc(k), Yc((D(es['closes'][str(k)]) / entry - 1) * 100)) for k in range(2, 61, 2)]
        chk(loc, 'cloud "this signal" path = daily closes on days 0,2..60', len(pts) == len(exp) and all(abs(a - c) < 1e-6 and abs(b - e) < 1e-6 for (a, b), (c, e) in zip(pts, exp)), True)


# ---------------------------------------------------------------- run
with sync_playwright() as pw:
    br = pw.chromium.launch(); ctx = br.new_context(viewport={'width': 1500, 'height': 1000}); page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.route('**/*', route)
    gen = dt.datetime.fromisoformat(FEED['generated_at'].replace('Z', '+00:00'))
    page.clock.install(time=gen + dt.timedelta(minutes=6))
    page.goto('http://site.test/')
    page.wait_for_timeout(1500)
    # banner, header, footer
    chk('banner', 'scored date and feed time', page.text_content('#rvAsof'), f"{dlong(MINE['today'])} (feed {FEED['generated_at'][11:16]} UTC)")
    chk('header', 'market filter', page.text_content('#filterText'), f"Market filter: {'on' if MINE['gate_today'] else 'off'}")
    chk('footer', 'feed state', page.text_content('#feedState'), f"Daily candles closed through {dlong(MINE['last_closed_daily'])} · updated {FEED['generated_at'][11:16]} UTC · checks passed")
    chk('footer', 'no stale-data note', page.locator('.stale-note').count(), 0)
    # picker contents
    g = page.evaluate(GRAB_CARD)
    open_ap = [sid for sid, o in MINE['open'].items() if o['grade'] == 'A+']
    my_live = [o['signal_id'] for o in FEED['open_signals'] if o['grade'] == 'A+']
    chk('picker', 'live buttons (open A+ signals)', [p[0] for p in g['picker'] if p[0] in MINE['open']], sorted(open_ap, key=my_live.index) if set(open_ap) == set(my_live) else open_ap)
    for sid in open_ap:
        o = MINE['open'][sid]; t = next(p[1] for p in g['picker'] if p[0] == sid)
        chk(f'picker {sid}', 'live button', t, f"{next(x['chart'] for x in FEED['open_signals'] if x['signal_id'] == sid)} Day {o['days']}best {pct(o['bsf'])} · worst {pct(o['wsf'])}")
    forming_sorted = sorted(MINE['cards'].keys(), key=lambda s: -int(MINE['cards'][s]['reach10']))
    # stable on feed order for ties
    feed_order = [c['signal_id'] for c in FEED['cards']]
    forming_sorted = sorted(feed_order, key=lambda s: -int(MINE['cards'][s]['reach10']))
    aplus_forming = [s for s in feed_order if next(c['grade'] for c in FEED['cards'] if c['signal_id'] == s) == 'A+']
    exp_forming = aplus_forming + [s for s in forming_sorted if s not in aplus_forming]
    chk('picker', 'forming buttons (order by rose-10% share)', [p[0] for p in g['picker'] if p[0] not in MINE['open'] and p[0] != 'example'], exp_forming)
    for sid in exp_forming:
        M = model_for('forming', sid); f = M['f']; t = next((p[1] for p in g['picker'] if p[0] == sid), None)
        chk(f'picker {sid}', 'forming button', t, f"{M['chart']} {f['reach10']}%rose 10% in 60 days · n {f['n']} · {'top grade' if M['top'] else 'not top grade'} · confirms {dlong(M['fm']['d0'])}")
    if not exp_forming: chk('picker', 'forming empty text', g['pnone'][-1] if g['pnone'] else None, 'Nothing forming today.')
    best_forming = exp_forming[0] if exp_forming else None
    chk('picker', 'initially selected', next((p[0] for p in g['picker'] if p[2] == 'true'), None), best_forming or (my_live[0] if my_live else 'example'))
    # every selection: Now card and Chart
    sels = [('open', s) for s in open_ap] + [('forming', s) for s in exp_forming] + [('example', 'example')]
    for kind, sid in sels:
        page.click('[data-view="now"]') if False else page.evaluate("location.hash='#now'")
        page.wait_for_timeout(200)
        page.click(f'#picker button[data-sel="{sid}"]'); page.wait_for_timeout(300)
        M = model_for(kind, sid)
        g = page.evaluate(GRAB_CARD)
        check_card(f'Now card {sid}', g, M, best_forming)
        chk(f'Now card {sid}', 'frame colour', g['frame'], 'var(--fade)' if (kind == 'forming' and not M['top']) else 'var(--live)')
        page.click('#tab-chart'); page.wait_for_timeout(800)
        modes = ['alert', 'happened'] if kind == 'example' else ['alert']
        for mode in modes:
            if kind == 'example':
                page.click('#bAlert' if mode == 'alert' else '#bHap'); page.wait_for_timeout(500)
            gc = page.evaluate(GRAB_CHART)
            loc = f'Chart {sid} ({mode})'
            if kind == 'open':
                o = MINE['open'][sid]
                chk(loc, 'title', gc['title'], f"{M['chart'].replace(' ', ' · ')} · live setup, day {o['days']} of 60")
                csamp = next(x['card']['sample'] for x in FEED['open_signals'] if x['signal_id'] == sid)
                chk(loc, 'subtitle', gc['sub'], f"Confirmed {dlong(o['entry_date'])} · entry close {money(o['entry'])}. Zones use this setup's own card ({csamp}). The shaded zones are the next 60 days, as the odds draw them.")
            elif kind == 'forming':
                fm = M['fm']
                chk(loc, 'title', gc['title'], f"{M['asset']} · {M['tf']} · {'setup forming' if M['top'] else 'forming, not top grade'}")
                chk(loc, 'subtitle', gc['sub'], f"Low {dlong(fm['lowday'])} · confirms {dlong(fm['d0'])} · price levels drawn from today's price ({money(fm['price'])}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them.")
            else:
                chk(loc, 'subtitle', gc['sub'], f"Confirmed {dlong('2024-09-22')} · entry close {money(M['entry'])} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them." + ('' if mode == 'happened' else ' The shaded zones are the next 60 days, as the odds draw them.'))
            chk(loc, 'At the alert / What happened toggle shown only for the example', gc['toggleHidden'], kind != 'example')
            check_chart(loc, gc, M, mode); check_side(loc, gc, M, mode); check_cloud(loc, gc, M, mode)
        page.evaluate("location.hash='#now'"); page.wait_for_timeout(200)
    # Previous signals column
    page.evaluate("location.hash='#now'"); page.wait_for_timeout(300)
    pv = page.evaluate("""() => ({intact: Array.from(document.querySelectorAll('#prevIntact .mini')).map(m => [m.querySelector('.name').textContent, m.querySelector('.sub').textContent, m.querySelector('.badge').textContent]),
      closed: Array.from(document.querySelectorAll('#prevClosed .mini')).map(m => [m.querySelector('.name').textContent, m.querySelector('.sub').textContent, m.querySelector('.badge').textContent]),
      none: (document.querySelector('#prevIntact .none')||{}).textContent || null})""")
    exp_int = [[MINE['open'][s] and next(x['chart'] for x in FEED['open_signals'] if x['signal_id'] == s), f"Day {MINE['open'][s]['days']} of 60 · best {pct(MINE['open'][s]['bsf'])} · worst {pct(MINE['open'][s]['wsf'])}", 'On track'] for s in my_live if MINE['open'][s]['status'] == 'intact']
    exp_fad = [[next(x['chart'] for x in FEED['open_signals'] if x['signal_id'] == s), f"Day {MINE['open'][s]['days']} of 60 · best {pct(MINE['open'][s]['bsf'])} · worst {pct(MINE['open'][s]['wsf'])}", 'Edge lost'] for s in my_live if MINE['open'][s]['status'] == 'lost']
    chk('Previous signals', 'edge intact list', pv['intact'], exp_int)
    if not exp_int: chk('Previous signals', 'empty intact text', pv['none'], 'No open top-grade setup with its edge intact.')
    LA = MINE['ledger_aplus']; order = MINE['ledger_aplus_order']
    recent = sorted(order, key=lambda k: k.split('|')[1], reverse=True)
    # stable sort by entry descending keeps ledger order for ties
    recent = [k for _, k in sorted(((k.split('|')[1], k) for k in order), key=lambda x: x[0], reverse=True)]
    rr = []
    for k in order[::-1]: pass
    byd = {}
    for k in order: byd.setdefault(k.split('|')[1], []).append(k)
    recent = [k for d in sorted(byd, reverse=True) for k in byd[d]][:5]
    exp_cl = [[k.split('|')[0], f"{dlong(k.split('|')[1])} · best {pct(LA[k]['best'])} · worst {pct(LA[k]['dd'])}", 'Reached +20%' if LA[k]['r20'] else 'Rose 10%' if LA[k]['r10'] else 'Missed'] for k in recent]
    chk('Previous signals', 'edge lost list', pv['closed'][:len(exp_fad)], exp_fad)
    got = pv['closed'][len(exp_fad):]
    chk('Previous signals', '5 most recent closed: dates', [r[1].split(' · ')[0] for r in got], [r[1].split(' · ')[0] for r in exp_cl])
    exp_by = {(r[0], r[1].split(' · ')[0]): r for r in exp_cl}
    # ties on the 5th date: the set of that date's rows may be cut differently; compare every shown row to my value for that chart/date
    allk = {(k.split('|')[0], dlong(k.split('|')[1])): k for k in LA}
    for r in got:
        k = allk.get((r[0], r[1].split(' · ')[0]))
        x = LA[k] if k else None
        chk('Previous signals closed ' + str(k), 'row', r, [k.split('|')[0], f"{dlong(k.split('|')[1])} · best {pct(x['best'])} · worst {pct(x['dd'])}", 'Reached +20%' if x['r20'] else 'Rose 10%' if x['r10'] else 'Missed'] if k else None)
    # Past signals tab
    page.click('#tab-record'); page.wait_for_timeout(400)
    for asset in ('all', 'ETH', 'BTC'):
        page.click(f'.seg button[data-asset="{asset}"]'); page.wait_for_timeout(300)
        rec = page.evaluate("""() => ({count: document.querySelector('#recCount').textContent,
           rows: Array.from(document.querySelectorAll('#recBody tr')).map(tr => Array.from(tr.children).map(td => td.textContent.trim())),
           sums: Array.from(document.querySelectorAll('#recSum .sidebox')).map(b => ({head: Array.from(b.querySelector('.kv').children).map(x=>x.textContent), kv: Array.from(b.querySelectorAll('.kv.num')).map(k => Array.from(k.children).map(x => x.textContent))}))})""")
        keys = [k for d in sorted(byd, reverse=True) for k in byd[d] if asset == 'all' or LA[k]['a'] == asset]
        chk(f'Past signals ({asset})', 'count line', rec['count'], f"{len(keys)} signals · {sum(1 for k in keys if not LA[k]['r10'])} missed +10%")
        chk(f'Past signals ({asset})', 'row count', len(rec['rows']), len(keys))
        rowkeys = [f"{r[1]}|{dt.datetime.strptime(r[0].replace('Sept', 'Sep'), '%d %b %Y').date()}" for r in rec['rows']]
        chk(f'Past signals ({asset})', 'rows = my A+ signals (set)', sorted(rowkeys), sorted(keys))
        chk(f'Past signals ({asset})', 'rows sorted newest first', [k.split('|')[1] for k in rowkeys], sorted([k.split('|')[1] for k in rowkeys], reverse=True))
        for row, k in zip(rec['rows'], rowkeys):
            if k not in LA: continue
            ch, d = k.split('|'); x = LA[k]
            exp = [dlong(d), ch, money(x['entry']), 'Yes' if x['r10'] else 'No', 'Yes' if x['r20'] else 'No', pct(x['best']), pct(x['dd']), pct(x['ret']), str(x['dpk'])]
            for i, (a_, b_) in enumerate(zip(row, exp)):
                chk(f'Past signals ({asset}) {ch} {d}', ['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'][i], a_, b_)
        for s in rec['sums']:
            a = s['head'][0]; gr = MINE['grades'][f'{a}|A+']; mi = MINE['misses'][f'{a}|A+']
            chk(f'Past signals ({asset}) summary {a}', 'signals', s['head'][1], f"{gr['n']} signals")
            kv = {x[0]: x[1] for x in s['kv']}
            chk(f'Past signals ({asset}) summary {a}', 'Rose 10% in 60 days', kv.get('Rose 10% in 60 days'), f"{gr['r10']}%")
            chk(f'Past signals ({asset}) summary {a}', 'Reached +20% in 60 days', kv.get('Reached +20% in 60 days'), f"{gr['r20']}%")
            chk(f'Past signals ({asset}) summary {a}', 'Rose 10%, never fell 25.3%', kv.get('Rose 10%, never fell 25.3%'), f"{gr['s10']}%")
            chk(f'Past signals ({asset}) summary {a}', 'Median deepest dip', kv.get('Median deepest dip'), pct(gr['med']))
            chk(f'Past signals ({asset}) summary {a}', 'Misses: median best price', kv.get('Misses: median best price'), pct(mi['median_peak_pct']))
        chk(f'Past signals ({asset})', 'summary boxes', [s['head'][0] for s in rec['sums']], ['ETH', 'BTC'] if asset == 'all' else [asset])
    # How to read
    page.click('#tab-read'); page.wait_for_timeout(300)
    txt = page.text_content('#view-read')
    for frag in ('rose 10% within 60 days of the entry close', 'without ever falling 25.3% below the entry close', 'after it first falls 5%, 10%, 15% or 20%',
                 'still rose 10% before ever falling 25.3%', 'drop below our 70% bar', 'did not rise 10% within 60 days', 'The median best price within 60 days',
                 'The median deepest dip within 60 days'):
        chk('How to read', f'states "{frag}"', frag in txt, True, 'wording')
    full = page.evaluate("document.body.innerText")
    chk('page', 'JavaScript errors', len(errs), 0, '; '.join(errs))
    br.close()

with open(os.path.join(HERE, f'page_checks_{LABEL}.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(CHECKS)
bad = [c for c in CHECKS if not c['ok']]
print(f'{LABEL} page: {len(CHECKS)} checks, {len(bad)} disagreements')
for c in bad: print('  ', {k: c[k] for k in ('location', 'label', 'shown', 'yours')})
