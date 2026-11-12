import sys, json, re
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from model8 import *
import chk

DIS = {}


def cmp_lines(st, loc, shown_txt, exp_lines, cause):
    sh = [x for x in shown_txt.split('\n') if x.strip() != '']
    ex = [x for x in exp_lines if x is not None]
    n = max(len(sh), len(ex))
    lab = ''
    for i in range(n):
        s = sh[i] if i < len(sh) else '<missing>'
        e = ex[i] if i < len(ex) else '<missing>'
        if not re.search(r'\d', e) and not re.search(r'\d', s) and s == e:
            lab = e; chk.add(st, loc, f'text line {i}', s, e, cause); continue
        chk.add(st, loc, f'line {i}' + (f' (after "{lab}")' if lab else ''), s, e, cause)
        lab = e if not re.search(r'^[\d+−$-]', e) else lab


def edge_txt(m):
    e = m['edge']['exact']
    if e == 0: return 'Below the 70% bar from entry'
    if e is not None: return f'{pct(e, 0)} before it rises 10%'
    return 'Holds at every level'


def card_lines(M, m, kind, best_id=None, sid=None):
    f = m['f']; n = f['past_trades']
    where = f"{m['asset']} · {m['tf']} CHART" + (' · EXAMPLE' if kind == 'example' else '')
    state = {'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind]
    if kind == 'open':
        s = m['sig']
        line = f"Confirmed {dlong(m['d0'])} · entry close {money(m['entry'])} · day {s['days']} of 60 · best so far {pct(s['best'])} · worst {pct(s['worst'])}"
    elif kind == 'example':
        line = f"Example: confirmed {dlong(EXD)} · entry close {money(m['entry'])}"
    else:
        line = f"Low {dlong(m['low_day'])} · confirms {dlong(m['d0'])}" + (f" if it closes above {money(m['kill'])}" if m['kill'] else '')
    below = kind == 'forming' and m['grade'] != 'A+'
    L = [where, state, line]
    if below:
        L.append(('Best setup forming today.' if best_id == sid else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
    mi = m['mi']
    miss = 'n/a' if not mi else (('Every time' if mi['up_first'] == mi['misses'] else f"{mi['up_first']} of {mi['misses']}") + f" · median best {pct(mi['median_peak'])}")
    L += [f"{f['rose10_within60d_pct']}%", 'rose 10% within 60 days', f"{f['rose10_never_fell25_within60d_pct']}% did it without ever falling 25.3%",
          f'from {n} past signals like this one', 'Typical high', pct(m['mu']), 'Typical drop from entry', pct(m['md']),
          'Edge gone below', edge_txt(m), 'If it misses: went above entry', miss]
    if below and mi: L.append(f"all {mi['signals']} {m['asset']} signals of this grade")
    g = m['grade']
    L += ['Lead trader: unavailable', 'THE DETAIL', 'Dip before the high, from entry', pct(m['mp']), 'High lands around', f"Day {f['typical_day_of_60d_high']}",
          f'Reached +20% within 60 days · n {n}', f"{f['rose20_within60d_pct']}%", f'Touched {MINUS}30% within 60 days · n {n}', f"{f['fell30_within60d_pct']}%",
          'Typical high', pct(m['mu']), 'Deepest dip lands around', f"Day {f['typical_day_of_deepest_dip']}",
          f"Typical worst drop, misses · all {mi['signals']} {m['asset']} {g}", pct(mi['median_worst']),
          f"Typical change by day 60, misses · all {mi['signals']} {m['asset']} {g}", pct(mi['median_day60']),
          'WHERE THE ODDS FADE · THIS SETUP', f'From entry n {n}', f"{rhaz(m['base'] * 100)}%"]
    for r in m['rows']:
        L += [f"Falls {r['fell']}% first n {r['n']}", 'n/a' if r['v'] is None else f"{rhaz(r['v'] * 100)}%"]
    L += ["Share of this setup's past signals that, after first falling that far, still rose 10% before ever falling 25.3%. Below 70% the edge is gone. Small samples: read the n.",
          'BY ERA', f"Before 2022 n {f['before_2022.past_trades']}", f"{f['before_2022.rose10_never_fell25_within60d_pct']}%",
          f"Since 2022 n {f['since_2022.past_trades']}", f"{f['since_2022.rose10_never_fell25_within60d_pct']}%",
          'Share that rose 10% and never fell 25.3%.', 'Open on the chart →',
          "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record. Past results don't guarantee future results."]
    return L


def status_open(M, s, m):
    if s['best'] is not None and s['best'] >= 10: return 'intact'
    e = m['edge']['exact']
    if e == 0: return 'fading'
    return 'fading' if (e is not None and s['worst'] is not None and s['worst'] <= e) else 'intact'


for st in ('REPLAY', 'CURRENT'):
    M = State(st)
    P = json.load(open(f'{chk.OUT}/code/page_{st}.json'))
    feed = M.feed
    gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    # ---------------- header / banner / footer
    regime_on = gate(st)(M.today)
    chk.add(st, 'page header', 'Market filter', P['header']['#filterText'], f"Market filter: {'on' if regime_on else 'off'}", 'regime')
    chk.add(st, 'page banner', 'scored date and feed time', P['header']['#rvAsof'], f"{dlong(M.today)} (feed {gen:%H:%M} UTC)", 'banner')
    last_closed = max(d for d in daily(st, 'ETH')[1] if d < M.today)
    chk.add(st, 'page footer', 'feed state', P['header']['#feedState'], f"Daily candles closed through {dlong(last_closed)} · updated {gen:%H:%M} UTC · checks passed", 'footer')
    chk.add(st, 'page lead panel', 'lead trader text', P['header']['#leadBody'], "The lead trader's feed is unavailable right now. His real entries and exits appear here the moment they fill.", 'lead')
    # ---------------- models
    opens = M.open_sigs()
    top_open = [s for s in opens if True]
    open_cards = {o['signal_id']: o for o in feed['open_signals']}
    models = {}
    for o in feed['open_signals']:
        if o['grade'] == 'A+': models[o['signal_id']] = ('open', M.card_model(o['card'], 'open'))
    for c in feed['cards']:
        models[c['signal_id']] = ('forming', M.card_model(c, 'forming'))
    models['example'] = ('example', M.card_model(feed['example_card'], 'example'))
    pickle.dump({k: (v[0], {kk: vv for kk, vv in v[1].items() if kk not in ('G',)}) for k, v in models.items()}, open(f'{chk.OUT}/code/_models_{st}.pkl', 'wb'))
    # ---------------- picker
    forming_sorted = sorted([c for c in feed['cards']], key=lambda c: -(models[c['signal_id']][1]['f']['rose10_within60d_pct']))
    best_id = forming_sorted[0]['signal_id'] if forming_sorted else None
    exp_btn = []
    for o in feed['open_signals']:
        if o['grade'] != 'A+': continue
        s = models[o['signal_id']][1]['sig']
        exp_btn.append((o['signal_id'], f"{o['chart']}\nDay {s['days']}\nbest {pct(s['best'])} · worst {pct(s['worst'])}"))
    for c in forming_sorted:
        m = models[c['signal_id']][1]
        exp_btn.append((c['signal_id'], f"{m['chart']}\n{m['f']['rose10_within60d_pct']}%\nrose 10% in 60 days · n {m['f']['past_trades']} · {'top grade' if m['grade'] == 'A+' else 'not top grade'} · confirms {dlong(m['d0'])}"))
    exp_btn.append(('example', 'Example: ETH 2D, Sep 2024'))
    chk.add(st, 'page picker', 'buttons (ids, order)', ' '.join(x[0] for x in P['picker']), ' '.join(x[0] for x in exp_btn), 'picker')
    for (sid, txt, _), (esid, etxt) in zip(P['picker'], exp_btn):
        chk.add(st, f'page picker {sid}', 'button text', txt, etxt, 'picker')
    if not feed['cards']:
        chk.add(st, 'page picker', 'Forming row empty text', 'Nothing forming today.' if 'Nothing forming today.' in P['picker_html'] else 'absent', 'Nothing forming today.' if not myform_any(st) else '', 'picker') if False else \
            chk.add(st, 'page picker', 'Forming row empty text present', 'Nothing forming today.' in P['picker_html'], True, 'picker')
        forming_mine = [1 for a in ('ETH', 'BTC') for tf in ('1D', '2D', '3D', '5D', '8D') if provisional(st, a, tf)]
        chk.add(st, 'page picker', 'my forming setups (none expected)', 0, len(forming_mine), 'forming detection')
    # default selection
    default = best_id or next((x[0] for x in exp_btn), None)
    chk.add(st, 'page picker', 'default selection', next(x[0] for x in P['picker'] if x[2] == 'true'), default, 'picker')
    # ---------------- cards
    for sid, d in P['sel'].items():
        kind, m = models[sid]
        exp = card_lines(M, m, kind, best_id, sid)
        cmp_lines(st, f'page card {sid}', d['card'], exp, 'card display')
        if m['edge']['exact'] != m['edge']['rounded']:
            chk.add(st, f'page card {sid}', 'edge: exact vs rounded comparison', m['edge']['rounded'], m['edge']['exact'], 'edge rule rounds before comparing')
    # ---------------- previous signals column
    prev = P['default']['prev']
    exp = ['PREVIOUS SIGNALS', 'updates each close', 'EDGE INTACT']
    tops = [o for o in feed['open_signals'] if o['grade'] == 'A+']
    stat = {o['signal_id']: status_open(M, models[o['signal_id']][1]['sig'], models[o['signal_id']][1]) for o in tops}
    intact = [o for o in tops if stat[o['signal_id']] == 'intact']; fading = [o for o in tops if stat[o['signal_id']] == 'fading']
    mini = lambda o, cls: [o['chart'], f"Day {models[o['signal_id']][1]['sig']['days']} of 60 · best {pct(models[o['signal_id']][1]['sig']['best'])} · worst {pct(models[o['signal_id']][1]['sig']['worst'])}", 'Edge lost' if cls else 'On track']
    if intact:
        for o in intact: exp += mini(o, '')
    else:
        exp.append('No open top-grade setup with its edge intact.')
    exp.append('EDGE LOST OR CLOSED')
    for o in fading: exp += mini(o, 'fading')
    aplus = sorted([x for x in M.L.values() if x['grade'] == 'A+'], key=lambda x: (x['d0'], 0 if x['asset'] == 'BTC' else 1), reverse=True)
    # page: stable sort of ledger order (ETH rows before BTC rows) by date desc
    led_order = [x for x in csv.DictReader(open(STATES[st] + '/datasets/ledger.csv')) if x['grade'] == 'A+']
    led_sorted = sorted(range(len(led_order)), key=lambda i: led_order[i]['entry'], reverse=False)
    recent_keys = [(r['chart'], r['entry']) for r in sorted(led_order, key=lambda r: r['entry'], reverse=True)][:5]
    my_recent = sorted([x for x in M.L.values() if x['grade'] == 'A+'], key=lambda x: x['d0'], reverse=True)
    cut = my_recent[4]['d0']
    chk.add(st, 'page previous signals', 'recent five are the five latest A+ (no tie at the cut)',
            sum(1 for x in my_recent if x['d0'] == cut), 1 if sum(1 for x in my_recent[:5] if x['d0'] == cut) == sum(1 for x in my_recent if x['d0'] == cut) else 'tie', 'previous')
    for k in recent_keys:
        x = M.L[k]; mm = x['m']
        exp += [x['chart'], f"{dlong(x['d0'])} · best {pct(mm['up'])} · worst {pct(mm['dd'])}", 'Reached +20%' if mm['r20'] else 'Rose 10%' if mm['r10'] else 'Missed']
    chk.add(st, 'page previous signals', 'recent five (set)', ' '.join(sorted(f'{a}|{b}' for a, b in recent_keys)), ' '.join(sorted(f"{x['chart']}|{x['d0']}" for x in my_recent[:5])), 'previous')
    exp.append('See every past signal, misses included')
    cmp_lines(st, 'page previous signals', prev, exp, 'previous signals')
    # ---------------- record tab
    for a in ('all', 'ETH', 'BTC'):
        R = P['record'][a]
        rows = [x for x in M.L.values() if x['grade'] == 'A+' and (a == 'all' or x['asset'] == a)]
        chk.add(st, f'page past signals [{a}]', 'count line', R['count'], f"{len(rows)} signals · {sum(not x['m']['r10'] for x in rows)} missed +10%", 'record')
        pr = {(r[1], r[0]): r for r in R['rows']}
        chk.add(st, f'page past signals [{a}]', 'row count', len(R['rows']), len(rows), 'record')
        # order: newest first
        dates = [r[0] for r in R['rows']]
        mydates = [dlong(x['d0']) for x in sorted(rows, key=lambda x: x['d0'], reverse=True)]
        chk.add(st, f'page past signals [{a}]', 'row order (newest first, by date)', '|'.join(dates), '|'.join(mydates), 'record')
        for x in rows:
            k = (x['chart'], dlong(x['d0'])); r = pr.get(k); mm = x['m']; loc = f"page past signals [{a}] {x['chart']} {x['d0']}"
            if r is None:
                chk.add(st, loc, 'row present', 'absent', 'present', 'record'); continue
            exp = [dlong(x['d0']), x['chart'], money(x['entry']), 'Yes' if mm['r10'] else 'No', 'Yes' if mm['r20'] else 'No', pct(mm['up']), pct(mm['dd']), pct(mm['ret']), str(mm['dpk'])]
            for lab, s, e in zip(['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day'], r, exp):
                chk.add(st, loc, lab, s, e, 'record row')
        exp = []
        for asset in (('ETH', 'BTC') if a == 'all' else (a,)):
            G = M.group(asset, 'A+'); n = len(G); mi = misses_of(G)
            exp += [asset, f'{n} signals', 'Rose 10% in 60 days', f"{pct_(G, 'r10')}%", 'Reached +20% in 60 days', f"{pct_(G, 'r20')}%",
                    'Rose 10%, never fell 25.3%', f"{pct_(G, 'surv10')}%", 'Median deepest dip', pct(med([x['m']['dd'] for x in G])),
                    'Misses: median best price', pct(mi['median_peak'])] if False else []
        def pct_(G, k): return rhaz(F(100 * sum(bool(x['m'][k]) for x in G), len(G)))
        for asset in (('ETH', 'BTC') if a == 'all' else (a,)):
            G = M.group(asset, 'A+'); n = len(G); mi = misses_of(G)
            exp += [asset, f'{n} signals', 'Rose 10% in 60 days', f"{pct_(G, 'r10')}%", 'Reached +20% in 60 days', f"{pct_(G, 'r20')}%",
                    'Rose 10%, never fell 25.3%', f"{pct_(G, 'surv10')}%", 'Median deepest dip', pct(med([x['m']['dd'] for x in G])),
                    'Misses: median best price', pct(mi['median_peak'])]
        sh = R['sum'].replace('\t', '\n')
        cmp_lines(st, f'page past signals [{a}] summary', sh, exp, 'record summary')
        chk.add(st, f'page past signals [{a}]', 'title', R['head'].split('\n')[0], 'EVERY TOP-GRADE SIGNAL WHOSE 60 DAYS HAVE CLOSED · COMPUTED, NEVER TRADED', 'record')
chk.dump('_page_now.csv')
bad = [c for c in chk.CHECKS if c['ok'] == 'no']
print(len(chk.CHECKS), 'checks', len(bad), 'bad')
for c in bad[:80]: print(c)
