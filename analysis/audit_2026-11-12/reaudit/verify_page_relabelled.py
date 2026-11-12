"""Check 7: compare every figure scraped from the page with my own recomputation. Writes page_checks.csv."""
import csv, json, os, re, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C

OUT = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(OUT, 'page_dump.json')))
PX = json.load(open(os.path.join(OUT, 'page_dump_with_example.json')))
F = json.load(open(os.path.join(C.REPO, 'feed', 'ctzb_feed.json')))
R = list(csv.DictReader(open(os.path.join(OUT, 'ledger_recomputed.csv'))))
for r in R:
    for k in ('up', 'dd', 'ret', 'ddpk', 'e'): r[k] = float(r[k])
    r['surv10'] = r['surv10'] == 'True'; r['dpk'] = int(r['dpk'])
C5 = json.load(open(os.path.join(OUT, 'check5.json')))
C4 = json.load(open(os.path.join(OUT, 'check4.json')))
rows = []

def num(s):
    s = s.replace('−', '-').replace('$', '').replace(',', '').replace('%', '').replace('+', '').strip()
    return float(s)

def chk(where, label, shown, mine, tol=0.0, cause=''):
    try: ok = abs(num(str(shown)) - float(mine)) <= tol + 1e-9
    except Exception: ok = str(shown).strip() == str(mine).strip()
    rows.append(dict(where=where, label=label, shown=shown, mine=mine, ok=ok, cause='' if ok else cause))

def SPAN(txt, day):
    if not txt: return False
    a, b = (int(x) for x in txt.split('–'))
    return a <= day <= b

def grab(text, pat, g=1):
    m = re.search(pat, text, re.S)
    return m.group(g) if m else None

pr = lambda G, f: C.r_half(100 * sum(1 for r in G if f(r)) / len(G))
med = lambda v: C.median(v)
mine5 = {}
for x in C5:
    sid = x['where'].split()[2]
    mine5.setdefault(sid, {})[x['field']] = x['mine']
fade10 = [x for x in C4['rows'] if x['method'].startswith('chart bars')]
first_gone10 = next(x for x in fade10 if x['kind'] == 'early_dip' and x['r10'] < 70)
dip_gone10 = float(re.search(r'-?\d+', first_gone10['band'].replace('worse than ', '').replace('shallower than ', '')).group())
red10 = next(x for x in fade10 if x['band'] == 'red on day 10')['r10']

def miss_mine(asset, grade):
    G = [r for r in R if r['asset'] == asset and r['grade'] == grade]; M = [r for r in G if r['up'] < 10]
    return dict(n=len(G), misses=len(M), up=sum(r['up'] > 0 for r in M), peak=round(med([r['up'] for r in M]), 1),
                worst=round(med([r['dd'] for r in M]), 1), d60=round(med([r['ret'] for r in M]), 1))

# ---- forming cards
for d in P['picks']:
    if d['sel'] == 'example': continue
    c = next(x for x in F['cards'] if x['signal_id'] == d['sel']); m = mine5[d['sel']]; t = d['card']; w = f"card {d['sel']}"
    chk(w, 'picker %', grab(P['picker'], re.escape(c['chart']) + r'\n(\d+)%'), m['rose10_within60d_pct'])
    chk(w, 'big number rose 10%', grab(t, r'\n(\d+)%\nrose 10% within 60 days'), m['rose10_within60d_pct'])
    chk(w, 'did it without ever falling 25%', grab(t, r'(\d+)% did it without'), m['rose10_never_fell25_within60d_pct'])
    chk(w, 'from N past signals', grab(t, r'from (?:all )?(\d+) (?:past|ETH top-grade|BTC top-grade) signals'), m['past_trades'])
    chk(w, 'Typical high', grab(t, r'Typical high\n([^\n]+)'), m['typical_biggest_rise_pct'], 0.05)
    chk(w, 'Typical drop from entry', grab(t, r'Typical drop from entry\n([^\n]+)'), m['typical_deepest_dip_pct'], 0.05)
    chk(w, 'Dip before the high', grab(t, r'Dip before the high, from entry\n([^\n]+)'), m['typical_dip_before_rise_pct'], 0.05)
    chk(w, 'High lands around Day', grab(t, r'High lands around\nDay (\d+)'), m['typical_day_of_60d_high'])
    chk(w, 'Reached +20%', grab(t, r'Reached \+20%\n(\d+)%'), m['rose20_within60d_pct'])
    chk(w, 'Touched -30%', grab(t, r'Touched −30%\n(\d+)%'), m['fell30_within60d_pct'])
    chk(w, 'Deepest dip lands around Day', grab(t, r'Deepest dip lands around\nDay (\d+)'), m['typical_day_of_deepest_dip'])
    lad = re.findall(r'Falls (\d+)% first n (\d+)\n(\d+)%', t)
    for th, n, v in lad:
        chk(w, f'ladder falls {th}% n', n, m[f'falls {th}% first: past_trades'])
        chk(w, f'ladder falls {th}% still rose 10%', v, m[f'falls {th}% first: still_rose10_pct'])
    chk(w, 'ladder From entry', grab(t, r'From entry n \d+\n(\d+)%'), m['rose10_within60d_pct'])
    chk(w, 'era before 2022 n', grab(t, r'Before 2022 n (\d+)'), m['before_2022.past_trades'])
    chk(w, 'era before 2022 %', grab(t, r'Before 2022 n \d+\n(\d+)%'), m['before_2022.surv10'], cause='5/8 = 62.5%: Python round() is banker\'s, shows 62' if c['signal_id'] == 'ETH-2D-2026-11-16' else '')
    chk(w, 'era since 2022 n', grab(t, r'Since 2022 n (\d+)'), m['since_2022.past_trades'])
    chk(w, 'era since 2022 %', grab(t, r'Since 2022 n \d+\n(\d+)%'), m['since_2022.surv10'])
    # edge gone: first ladder row below 70 among my values
    base = m['rose10_within60d_pct']
    if base < 70: edge = 'Below the 70% bar from entry'
    else:
        g = next((th for th in (5, 10, 15, 20) if m[f'falls {th}% first: still_rose10_pct'] is not None and m[f'falls {th}% first: still_rose10_pct'] < 70), None)
        edge = f'−{g}% before it rises 10%' if g else 'Holds at every level'
    chk(w, 'Edge gone below', grab(t, r'Edge gone below\n([^\n]+)'), edge)
    mm = miss_mine(c['asset'], c['grade'])
    shown_miss = grab(t, r'If it misses: up first\n([^\n]+)')
    mine_miss = ('Every time' if mm['up'] == mm['misses'] else f"{mm['up']} of {mm['misses']}") + f" · median peak +{mm['peak']:.1f}%"
    chk(w, 'If it misses: up first', shown_miss, mine_miss, cause='feed if_it_misses still on the +20% miss rule (generated before the +10% switch)')
    chk(w, 'all N signals of this grade', grab(t, r'all (\d+) \w+ signals of this grade'), mm['n'])
    chk(w, 'Worst drop, misses', grab(t, r'Worst drop, misses\n([^\n]+)'), mm['worst'], 0.05, cause='feed if_it_misses on +20% rule')
    chk(w, 'Price on day 60, misses', grab(t, r'Price on day 60, misses\n([^\n]+)'), mm['d60'], 0.05, cause='feed if_it_misses on +20% rule')
    # chart side panel: prices from today's close
    s = d['side']; pn = c['price_now']
    chk(w, 'chart: price used', grab(d['chart_sub'], r"today's price \(([^)]+)\)"), round(C.load(c['asset'], c['timeframe'])[-1]['c'], 2), 0.005)
    chk(w, 'chart: Typical high price', grab(s, r'Typical high\n[^·]+· ([^\n]+)'), round(pn * (1 + m['typical_biggest_rise_pct'] / 100), 2), 0.011)
    chk(w, 'chart: +10% target', grab(s, r'\+10% target\n([^\n]+)'), round(pn * 1.1, 2), 0.011)
    chk(w, 'chart: Typical drop price', grab(s, r'Typical drop\n[^·]+· ([^\n]+)'), round(pn * (1 + m['typical_deepest_dip_pct'] / 100), 2), 0.011)
    if edge.startswith('−'):
        chk(w, 'chart: Edge gone below price', grab(s, r'Edge gone below\n\$([\d,.]+)'), round(pn * (1 - int(edge[1:edge.index('%')]) / 100), 2), 0.011)
    else:
        chk(w, 'chart: Edge gone below', grab(s, r'Edge gone below\n([^\n]+)'), 'below the bar already' if base < 70 else 'holds at every level')
    bars = C.load(c['asset'], c['timeframe']); lowbar = next(b for b in bars if str(b['d']) == c['low_date'])
    chk(w, 'chart: Low marker price', grab(' '.join(d['svg_text']), r'Low \d+ \w+ \d+ · (\$[\d,.]+)'), round(lowbar['l'], 2), 0.005)
    chk(w, 'chart: High usually ~day', grab(' '.join(d['svg_text']), r'High usually ~day (\d+)'), m['typical_day_of_60d_high'])
    chk(w, 'chart: +10% line share', grab(' '.join(d['svg_text']), r'\+10% · (\d+)% of past'), m['rose10_within60d_pct'])
    chk(w, 'card line: confirms / must close above', grab(t, r'if it closes above ([^\n]+)') or 'none', ('$' + f"{m['must_close_above']:,.2f}") if m.get('must_close_above') else 'none')

# ---- cloud (past paths) and record summaries
for a in ('ETH', 'BTC'):
    G = [r for r in R if r['asset'] == a and r['grade'] == 'A+']
    paths = [[(c / r['e'] - 1) * 100 for c in json.loads(r['closes'])] for r in G]
    d60 = [p[59] for p in paths]
    d = next(x for x in P['picks'] if x['sel'].startswith(a))
    w = f'chart cloud {a}'
    chk(w, 'n', grab(d['cloud_sub'], r'n (\d+)'), len(G))
    chk(w, 'Day 60 median', grab(d['cloud_note'], r'Day 60: median ([+−\d.]+%)'), round(C.quant(d60, .5), 1), 0.1)
    chk(w, 'Day 60 q25', grab(d['cloud_note'], r'middle half ([^ ]+) to'), round(C.quant(d60, .25), 1), 0.1)
    chk(w, 'Day 60 q75', grab(d['cloud_note'], r' to ([+−\d.]+%)'), round(C.quant(d60, .75), 1), 0.1)
    rs = PX['record'][a]['sum']; mm = miss_mine(a, 'A+'); w = f'Record summary {a}'
    chk(w, 'signals', grab(rs, r'(\d+) signals'), len(G))
    chk(w, 'Rose 10% in 60 days', grab(rs, r'Rose 10% in 60 days\n([^\n]+)'), pr(G, lambda r: r['up'] >= 10), cause='feed grade_odds has no rose10_within60d_pct, page prints n/a')
    chk(w, 'Reached +20% in 60 days', grab(rs, r'Reached \+20% in 60 days\n(\d+)'), pr(G, lambda r: r['up'] >= 20))
    chk(w, 'Rose 10%, never fell 25%', grab(rs, r'never fell 25%\n(\d+)'), pr(G, lambda r: r['surv10']))
    chk(w, 'Median deepest dip', grab(rs, r'Median deepest dip\n([^\n]+)'), round(med([r['dd'] for r in G]), 1), 0.05)
    chk(w, 'Misses: median peak first', grab(rs, r'median peak first\n([^\n]+)'), mm['peak'], 0.05, cause='feed if_it_misses on +20% rule')
    chk(w, 'count line', PX['record'][a]['count'], f"{len(G)} signals · {mm['misses']} missed +10%")
GA = [r for r in R if r['grade'] == 'A+']
chk('Record summary all', 'count line', PX['record']['all']['count'], f"{len(GA)} signals · {sum(r['up'] < 10 for r in GA)} missed +10%")

# ---- record table rows (all A+ rows)
bykey = {(r['chart'], r['entry']): r for r in GA}
mon = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'], 1)}
def iso(s):
    dd, mm_, yy = s.split(); return f'{yy}-{mon[mm_]:02d}-{int(dd):02d}'
tbad = 0; tn = 0
for row in PX['record']['all']['rows']:
    r = bykey.get((row[1], iso(row[0])))
    if r is None: rows.append(dict(where='Record table', label='row', shown=row, mine='no such A+ signal', ok=False, cause='')); continue
    exp = [f"${r['e']:,.2f}", 'Yes' if r['up'] >= 10 else 'No', 'Yes' if r['up'] >= 20 else 'No', round(r['up'], 1), round(r['dd'], 1), round(r['ret'], 1), r['dpk']]
    for lab, sv, mv, tol in zip(['Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'], row[2:], exp, [0.005, 0, 0, 0.1, 0.1, 0.1, 0]):
        tn += 1
        before = len(rows); chk(f"Record table {row[1]} {iso(row[0])}", lab, sv, mv, tol)
        if rows[-1]['ok']: rows.pop()
        else: tbad += 1
rows.append(dict(where='Record table', label=f'{len(PX["record"]["all"]["rows"])} rows x 7 figures', shown=tn, mine=f'{tbad} disagree', ok=tbad == 0, cause=''))
chk('Record table', 'row count', len(PX['record']['all']['rows']), len(GA))

# ---- previous alerts column
recent = sorted(GA, key=lambda r: r['entry'], reverse=True)[:5]
items = re.findall(r'(\w+ \dD)\n(\d+ \w+ \d+) · best ([^ ]+) · worst ([^\n]+)\n([^\n]+)', P['prev']['closed'])
for (chart, date, best, worst, badge), r in zip(items, recent):
    w = f'Previous alerts {chart} {iso(date)}'
    chk(w, 'which signal', f'{chart} {iso(date)}', f"{r['chart']} {r['entry']}")
    chk(w, 'best', best, round(r['up'], 1), 0.1); chk(w, 'worst', worst, round(r['dd'], 1), 0.1)
    chk(w, 'badge', badge, 'Reached +20%' if r['up'] >= 20 else 'Rose 10%' if r['up'] >= 10 else 'Missed')

# ---- example card
E = [r for r in R if r['asset'] == 'ETH' and r['grade'] == 'A+']
ex = next(x for x in P['picks'] if x['sel'] == 'example'); t = ex['card']; w = 'example card'
mm = miss_mine('ETH', 'A+')
chk(w, 'entry close $2,580.92', grab(t, r'entry close ([^\n]+)'), round(next(b for b in C.load('ETH', '2D') if str(C.bar_end(C.load('ETH', '2D'), C.load('ETH', '2D').index(b), '2D')) == '2024-09-22')['c'], 2), 0.005)
chk(w, 'big number rose 10%', grab(t, r'\n(\d+)%\nrose 10%'), pr(E, lambda r: r['up'] >= 10))
chk(w, 'did it without ever falling 25%', grab(t, r'(\d+)% did it without'), pr(E, lambda r: r['surv10']))
chk(w, 'from N past signals', grab(t, r'from (?:all )?(\d+) (?:past|ETH top-grade|BTC top-grade)'), len(E))
chk(w, 'Typical high', grab(t, r'Typical high\n([^\n]+)'), round(med([r['up'] for r in E]), 1), 0.05, cause='page takes the median of the ledger\'s 0.1-rounded bestMove')
chk(w, 'Typical drop from entry', grab(t, r'Typical drop from entry\n([^\n]+)'), round(med([r['dd'] for r in E]), 1), 0.05)
chk(w, 'Edge gone below', grab(t, r'Edge gone below\n([^\n]+)'), f"−{abs(int(dip_gone10))}% in the first 10 days · ${2580.92 * (1 + dip_gone10 / 100):,.2f}",
    cause='feed odds_fade edges still marked on +20% (generated before the +10% switch); on +10% the first band below 70% is "worse than -20%"')
chk(w, 'If it misses: up first', grab(t, r'If it misses: up first\n([^\n]+)'), ('Every time' if mm['up'] == mm['misses'] else f"{mm['up']} of {mm['misses']}") + f" · median peak +{mm['peak']:.1f}%", cause='feed if_it_misses on +20% rule')
chk(w, 'Dip before the high', grab(t, r'Dip before the high, from entry\n([^\n]+)'), round(med([r['ddpk'] for r in E]), 1), 0.05)
chk(w, 'High lands around Day', grab(t, r'High lands around\nDay ([\d.]+)'), med([r['dpk'] for r in E]))
chk(w, 'Reached +20%', grab(t, r'Reached \+20%\n(\d+)%'), pr(E, lambda r: r['up'] >= 20))
chk(w, 'Touched -30%', grab(t, r'Touched −30%\n(\d+)%'), pr(E, lambda r: r['dd'] <= -30))
chk(w, 'Red on day 10 odds', grab(t, r'Red on day 10\n(\d+)% still rose 10%'), red10, cause='feed day10 row has no rose10 field; page falls back to the +20% share under a +10% page')
chk(w, 'Worst drop, misses', grab(t, r'Worst drop, misses\n([^\n]+)'), mm['worst'], 0.05, cause='feed if_it_misses on +20% rule')
chk(w, 'Price on day 60', grab(t, r'Price on day 60\n([^\n]+)'), round(med([r['ret'] for r in E]), 1), 0.05)
old = [r for r in E if r['entry'] < '2022']; new = [r for r in E if r['entry'] >= '2022']
chk(w, 'era before 2022 n', grab(t, r'Before 2022 n (\d+)'), len(old)); chk(w, 'era before 2022 %', grab(t, r'Before 2022 n \d+\n(\d+)%'), pr(old, lambda r: r['surv10']))
chk(w, 'era since 2022 n', grab(t, r'Since 2022 n (\d+)'), len(new)); chk(w, 'era since 2022 %', grab(t, r'Since 2022 n \d+\n(\d+)%'), pr(new, lambda r: r['surv10']))
labs = [('Dip < −2%', 'shallower than -2%'), ('Dip −2% to −5%', '-2% to -5%'), ('Dip −5% to −10%', '-5% to -10%'), ('Dip −10% to −20%', '-10% to -20%'), ('Dip past −20%', 'worse than -20%'), ('Green day 10', 'green on day 10'), ('Red day 10', 'red on day 10')]
for shown_lab, band in labs:
    x = next(y for y in fade10 if y['band'] == band)
    chk(w, f'all-kept fade "{shown_lab}" (labelled rose 10%)', grab(t, re.escape(shown_lab) + r'\n(\d+)%'), x['r10'], cause='feed odds_fade has no rose10 field; page shows the +20% share')
# example chart (served example json)
exx = next(x for x in PX['picks'] if x['sel'] == 'example'); s = exx['side']; svg = ' '.join(exx['svg_text']); w = 'example chart'
mE = C.fwd('ETH', dt.date(2024, 9, 22), 2580.92)
up_med = med([r['up'] for r in E]); dd_med = med([r['dd'] for r in E])
chk(w, 'Typical high price', grab(s, r'Typical high\n[^·]+· ([^\n]+)'), round(2580.92 * (1 + round(up_med, 1) / 100), 2), 0.011, cause='typical high pct 35.0 vs 34.9')
chk(w, '+10% target', grab(s, r'\+10% target\n([^\n]+)'), round(2580.92 * 1.1, 2), 0.011)
chk(w, 'Typical drop price', grab(s, r'Typical drop\n[^·]+· ([^\n]+)'), round(2580.92 * (1 + round(dd_med, 1) / 100), 2), 0.011)
chk(w, 'Edge gone below', grab(s, r'Edge gone below\n([^\n]+)'), f"${2580.92 * (1 + dip_gone10 / 100):,.2f} ({'−' if dip_gone10 < 0 else ''}{abs(int(dip_gone10))}%)", cause='stale +20% edge marks')
for lab, i, key in (('0 to -5 band', 0, None), ('-5 to -10 band', 1, None), ('-10 to -20 band', 2, None)):
    vals = re.findall(r'(\d+)%', ' '.join(exx['svg_text'][13:16]))
    mine = [max(fade10[0]['r10'], fade10[1]['r10']), fade10[2]['r10'], fade10[3]['r10']][i]
    chk(w, f'chart early-dip band {lab}', vals[i] if i < len(vals) else None, mine, cause='bands drawn from the +20% shares')
chk(w, 'Day 10 vline red odds', grab(svg, r'red here: (\d+)% still rose 10%'), red10, cause='+20% share shown')
chk(w, 'This one: best price', grab(svg, r'This one: (\$[\d,.]+) · \+'), round(max(mE['highs']), 2), 0.005)
chk(w, 'This one: best %', grab(svg, r'This one: \$[\d,.]+ · (\+[\d.]+%)'), round(mE['up'], 1), 0.05)
chk(w, 'This one: best day (in span)', SPAN(grab(svg, r'This one: \$[\d,.]+ · \+[\d.]+% · days (\d+–\d+)'), mE['dpk']), True, cause='page counts 2D bars and reports the day the bar closes, not the day of the high')
chk(w, 'This one: low price', grab(svg, r'This one: (\$[\d,.]+) · −'), round(min(mE['lows']), 2), 0.005)
chk(w, 'This one: low day (in span)', SPAN(grab(svg, r'· −[\d.]+% · days (\d+–\d+)'), mE['ddday']), True, cause='2D bar close day, not the day of the low')
sh = exx['side_happened']
chk(w, 'What this one did: reached +10/+20', grab(sh, r'Reached \+10% / \+20%\n([^\n]+)'), f"{'Yes' if mE['up'] >= 10 else 'No'} / {'Yes' if mE['up'] >= 20 else 'No'}")
chk(w, 'What this one did: best', grab(sh, r'Best price\n([^,]+),'), round(mE['up'], 1), 0.05)
chk(w, 'What this one did: best day (in span)', SPAN(grab(sh, r'Best price\n[^,]+, days (\d+–\d+)'), mE['dpk']), True, cause='2D bar close day')
chk(w, 'What this one did: deepest', grab(sh, r'Deepest drop\n([^,]+),'), round(mE['dd'], 1), 0.05)
chk(w, 'What this one did: deepest day (in span)', SPAN(grab(sh, r'Deepest drop\n[^,]+, days (\d+–\d+)'), mE['ddday']), True, cause='2D bar close day')
chk(w, 'What this one did: day 10', grab(sh, r'Day 10 check\n[^,]+, ([^\n]+)'), round((mE['closes'][9] / 2580.92 - 1) * 100, 1), 0.05)
chk(w, 'What this one did: day 60', grab(sh, r'Price on day 60\n([^\n]+)'), round(mE['ret'], 1), 0.05)
# spec routing (example json 404): chart tab keeps the previous setup's panel
chk('example chart (spec routing, example json 404)', 'panel cleared, says data could not be loaded', (ex['side'].strip() == '' and "couldn't be loaded" in ex.get('chart_sub', '') ), True, cause='renderChart returns early on missing example data and leaves the previous setup\'s title, side panel and cloud on screen')
# header
chk('header', 'Market filter', 'on' if 'Market filter: on' in P['header'] else 'off', 'on' if C.gate()(dt.date(2026, 11, 12)) else 'off')

with open(os.path.join(OUT, 'page_checks.csv'), 'w', newline='') as f:
    wr = csv.DictWriter(f, fieldnames=['where', 'label', 'shown', 'mine', 'ok', 'cause']); wr.writeheader(); wr.writerows(rows)
bad = [r for r in rows if not r['ok']]
for r in bad: print(r)
print(len(rows), 'page checks,', len(bad), 'disagree; table figures', tn)
