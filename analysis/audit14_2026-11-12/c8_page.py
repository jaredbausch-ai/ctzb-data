"""Check 8: every number the rendered page displays vs my values."""
import json, re, sys
from expect import *

L_, R_, T_, B_ = 20.0, 960.0, 24.0, 480.0
norm = lambda s: re.sub(r'\s+', ' ', s or '').strip()
low = lambda s: norm(s).lower()

def close(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))

def exp_card(X, sid, best_sid):
    e = X.sel[sid]; fig = e['fig']; kind = e['kind']; a, tf = e['a'], e['tf']; top = e['grade'] == 'A+'
    high, drop, dipb = fig['typical_biggest_rise_exact_pct'], fig['typical_deepest_dip_exact_pct'], fig['typical_dip_before_rise_exact_pct']
    c = dict(where=f'{a} · {tf} chart' + (' · example' if kind == 'example' else ''),
             state={'forming': 'Setup forming', 'open': 'Live setup', 'example': 'Confirmed setup'}[kind])
    heads = []
    if kind == 'forming':
        f = e['f']
        heads.append(f"Low {date_long(e['low_day'])} · confirms {date_long(f['conf'])}" + (f" if it closes above {money(repr(f['kill']))}" if f['kill'] is not None else ''))
        if not top: heads.append(('Best setup forming today.' if sid == best_sid else 'Setup forming.') + " It isn't top grade, so no alert goes out for it. It can still vanish before it confirms.")
        else: heads.append('Not confirmed yet. It can still vanish before it confirms.')
    elif kind == 'open':
        heads.append(f"Confirmed {date_long(e['entry_date'])} · entry close {money(e['entry_ref'])} · day {e['elapsed']} of 60 · best so far {pct(e['best'])} · worst {pct(e['worst'])}")
    else:
        heads.append(f"Example: confirmed {date_long(EX)} · entry close {money(e['entry_ref'])}")
    c['heads'] = heads
    c['big'] = f"{fig['rose10_within60d_pct']}%"
    c['odds'] = [c['big'], 'rose 10% within 60 days', f"{fig['rose10_never_fell25_within60d_pct']}% did it without ever falling 25.3%",
                 f"from {e['sample']} · every figure covers the 60 days after entry"]
    edge = fig['edge']
    edge_txt = 'Below the 70% bar from entry' if edge == 0 else f'{pct(edge, 0)} before it rises 10%' if edge is not None else 'Holds at every level'
    mi = X.ex_miss if kind == 'example' else X.miss[(a, e['grade'])]
    stats = [f'Typical high {pct(high)}', f'Typical drop from entry {pct(drop)}', f'Edge gone below {edge_txt}',
             f"If it misses: went above entry {mi['up_first']} of {mi['misses']} · median best {pct(mi['median_peak_pct'])}"]
    if kind == 'forming' and not top: stats.append(f"all {mi['signals']} {a} signals of this grade")
    c['stats'] = stats
    n = fig['past_trades']
    pool = f" · {mi['misses']} misses of {'the' if kind == 'example' else 'all'} {mi['signals']} {a} {'top-grade' if top else 'same-grade'} signals{' known by then' if kind == 'example' else ''}"
    c['tiles'] = [('Dip before the high, from entry', pct(dipb)), ('High lands around', f"Day {fig['typical_day_of_60d_high']}"),
                  (f'Reached +20% within 60 days · n {n}', f"{fig['rose20_within60d_pct']}%"), (f'Touched {MIN}30% within 60 days · n {n}', f"{fig['fell30_within60d_pct']}%"),
                  ('Typical high', pct(high)), ('Deepest dip lands around', f"Day {fig['typical_day_of_deepest_dip']}"),
                  ('Typical worst drop, misses' + pool, pct(mi['median_worst_drop_pct'])), ('Typical change by day 60, misses' + pool, pct(mi['median_day60_pct']))]
    fe = fig['from_entry']
    c['ladder'] = [(f'From entry n {n}', f"{fe['ok']}%", fe['frac'] < 70)] + [
        (f"Falls {r['th']}% first n {r['n']}", 'n/a' if r['ok'] is None else f"{r['ok']}%", r['frac'] is not None and r['frac'] < 70) for r in fig['ladder']]
    c['eras'] = [(f'{t} n {fig[k][0]}', f"{fig[k][1] if fig[k][1] is not None else 'n/a'}%") for t, k in (('Before 2022', 'before_2022'), ('Since 2022', 'since_2022'))]
    return c

def check_card(R, loc, got, exp):
    R.add(loc, 'card: where', low(got['where']), low(exp['where']))
    R.add(loc, 'card: state', got['state'], exp['state'])
    R.add(loc, 'card: lines under the state (count)', len(got['heads']), len(exp['heads']))
    for i, (g, x) in enumerate(zip(got['heads'], exp['heads'])): R.add(loc, f'card: line {i + 1} under the state', norm(g), x)
    R.add(loc, 'card: big number', got['big'], exp['big'])
    for i, (g, x) in enumerate(zip(got['odds'], exp['odds'])): R.add(loc, f'card: odds block line {i + 1}', norm(g), x)
    R.add(loc, 'card: stats rows (count)', len(got['stats']), len(exp['stats']))
    for g, x in zip(got['stats'], exp['stats']): R.add(loc, 'card: ' + x.split(' +')[0].split(' ' + MIN)[0][:34], norm(g), x)
    R.add(loc, 'card: tiles (count)', len(got['tiles']), 8)
    for g, (t, v) in zip(got['tiles'], exp['tiles']):
        R.add(loc, f'card tile label: {t[:40]}', norm(g['t']), t); R.add(loc, f'card tile value: {t[:40]}', g['v'], v)
    R.add(loc, 'card: ladder rows (count)', len(got['ladder']), len(exp['ladder']))
    for g, (t, v, gone) in zip(got['ladder'], exp['ladder']):
        R.add(loc, f'ladder "{t}" label and n', norm(g['text']), t); R.add(loc, f'ladder "{t}" share', g['val'], v)
        R.add(loc, f'ladder "{t}" bar width', g['width'], v if v != 'n/a' else '0%')
        R.add(loc, f'ladder "{t}" marked gone (exact share below 70)', g['gone'], gone)
    for g, (t, v) in zip(got['eras'], exp['eras']):
        R.add(loc, f'era "{t}" label and n', norm(g['text']), t); R.add(loc, f'era "{t}" share', g['val'], v)
    R.add(loc, 'ladder note names the 70% bar', 'yes' if got['ladderNote'] and 'Below 70% the edge is gone' in got['ladderNote'] else 'no', 'yes')
    R.add(loc, 'card: lead trader marker', got['marker'], 'Lead trader: unavailable')
    R.add(loc, 'card foot says entry quality only, not a trade or a track record', 'yes' if 'Entry quality only: no exit, not a trade or a track record' in got['foot'] else 'no', 'yes')

def fit_axis(svg):
    g = [(float(e['text'].replace('$', '').replace(',', '')), float(e['y']) - 5) for e in svg if e['tag'] == 'text' and e.get('x') == '968']
    (p1, y1), (p2, y2) = g[0], g[-1]
    k = (p1 - p2) / (y2 - y1); lo = p1 - (B_ - y1) * k; hi = lo + (B_ - T_) * k
    return lo, hi, len(g)

def check_chart(R, X, sid, sc, mode, exbars=None):
    S = X.S; e = X.sel[sid]; fig = e['fig']; kind = e['kind']; a, tf = e['a'], e['tf']; top = e['grade'] == 'A+'
    loc = f'page Chart [{sid}{"" if kind != "example" else ", " + mode}]'
    ch = sc['chart']; svg = ch['svg']
    high, drop = fig['typical_biggest_rise_exact_pct'], fig['typical_deepest_dip_exact_pct']
    entry = e['entry_ref']; fentry = float(entry)
    edge = fig['edge']; n = fig['past_trades']
    happened = mode == 'happened'
    zones_txt = '' if happened else ' The shaded zones are the next 60 days, as the odds draw them.'
    # ---- title / subtitle / toggle
    if kind == 'open':
        title = f"{a} · {tf} · live setup, day {e['elapsed']} of 60"
        sub = f"Confirmed {date_long(e['entry_date'])} · entry close {money(entry)}. Zones use this setup's own card ({e['sample']})." + zones_txt
    elif kind == 'forming':
        title = f"{a} · {tf} · " + ('setup forming' if top else 'forming, not top grade')
        sub = f"Low {date_long(e['low_day'])} · confirms {date_long(e['f']['conf'])} · price levels drawn from today's price ({money(entry)}), since the entry price is the confirmation close; days count from the confirmation." + zones_txt
    else:
        title = 'ETH · 2-day · example: past confirmed setup'
        sub = f"Confirmed {date_long(EX)} · entry close {money(entry)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them." + zones_txt
    R.add(loc, 'chart title', low(ch['title']), low(title)); R.add(loc, 'chart subtitle', norm(ch['sub']), sub)
    R.add(loc, 'At the alert / What happened toggle shown only on the example', ch['toggleHidden'], kind != 'example')
    # ---- bars and slots
    if kind == 'example':
        bars = exbars; E = next(i for i, b in enumerate(bars) if bar_close_date(b['d'], '2D') == EX)
        opens = [b['d'] for b in bars]; shown = bars if happened else bars[:E + 1]; drawn = len(shown)
    else:
        chx = S.ch[(a, tf)]; idx = range(chx.n - 70, chx.n)
        bars = [dict(d=chx.date[i], o=chx.o[i], h=chx.h[i], l=chx.l[i], c=chx.c[i]) for i in idx]
        opens = [b['d'] for b in bars]
        while opens[-1] <= e['entry_date'] + dt.timedelta(days=61): opens.append(next_open(opens[-1], tf))
        shown = bars; drawn = len(bars)
        E = next(i for i, b in enumerate(bars) if bar_close_date(b['d'], tf) == e['entry_date']) if kind == 'open' else len(bars) - 1
    def slot_of(d):
        i = 0
        while i + 1 < len(opens) and opens[i + 1] <= d: i += 1
        return i
    A = slot_of(e['entry_date']) if kind == 'forming' else E
    R.add(loc, 'entry slot is the bar that closes on the entry / confirmation date', str(bar_close_date(opens[A], tf)), str(e['entry_date']))
    lv_high, lv_drop = fentry * (1 + high / 100), fentry * (1 + drop / 100)
    lo_x = min(min(b['l'] for b in shown), lv_drop, fentry * 0.8) * 0.95; hi_x = max(max(b['h'] for b in shown), lv_high) * 1.07
    lo_g, hi_g, ng = fit_axis(svg)
    R.add(loc, 'price axis bottom (scaled from the bars shown' + (', only up to the entry bar' if kind == 'example' and not happened else '') + ')', round(lo_g, 4), round(lo_x, 4), ok=close(lo_g, lo_x, 1e-7))
    R.add(loc, 'price axis top', round(hi_g, 4), round(hi_x, 4), ok=close(hi_g, hi_x, 1e-7))
    if kind == 'example' and not happened:
        hi_all = max(max(b['h'] for b in bars), lv_high) * 1.07; lo_all = min(min(b['l'] for b in bars), lv_drop, fentry * 0.8) * 0.95
        R.add(loc, 'axis does NOT use bars after the alert (would be top/bottom ' + f'{hi_all:.2f}/{lo_all:.2f})', 'known-only' if close(hi_g, hi_x, 1e-7) and close(lo_g, lo_x, 1e-7) else 'uses later bars', 'known-only')
    Y = lambda p: B_ - (p - lo_x) / (hi_x - lo_x) * (B_ - T_)
    wicks = [el for el in svg if el['tag'] == 'line' and el.get('stroke-width') == '1.5' and el['x1'] == el['x2'] and not (el['y1'] == '24' and el['y2'] == '480')]
    bodies = [el for el in svg if el['tag'] == 'rect' and 'opacity' not in el and el.get('rx') is None and float(el['width']) <= 12.0001]
    R.add(loc, 'candles drawn (At the alert: none after the entry bar)', len(wicks), drawn)
    slot = (float(wicks[1]['x1']) - float(wicks[0]['x1'])) if len(wicks) > 1 else None
    n_slots = len(opens)
    R.add(loc, 'slots across the chart (bars + future bars by the calendar-year rule)', round((R_ - L_) / slot, 6), n_slots, ok=close((R_ - L_) / slot, n_slots))
    slot = (R_ - L_) / n_slots; Xs = lambda i: L_ + slot * i + slot / 2
    bad = 0
    for i, (w, b) in enumerate(zip(wicks, bars)):
        if not (close(w['x1'], Xs(i)) and close(w['y1'], Y(b['h'])) and close(w['y2'], Y(b['l']))): bad += 1
    R.add(loc, f'candle wicks whose x / high / low differ from the raw candles (of {len(wicks)})', bad, 0)
    bad = 0
    for i, (r, b) in enumerate(zip(bodies, bars)):
        if not (close(r['y'], Y(max(b['o'], b['c']))) and close(r['height'], max(1, abs(Y(b['o']) - Y(b['c']))))): bad += 1
    R.add(loc, f'candle bodies whose open / close differ from the raw candles (of {len(bodies)})', bad, 0)
    # date axis labels
    dl = [el for el in svg if el['tag'] == 'text' and el.get('y') == '502']
    bad = [(el['text'], f"{opens[min(round((float(el['x']) - L_) / slot - 0.5), len(opens) - 1)].day:02d} {MONTHS[opens[min(round((float(el['x']) - L_) / slot - 0.5), len(opens) - 1)].month - 1]}") for el in dl]
    R.add(loc, f'date-axis labels that are not the open date of their bar (of {len(dl)})', sum(1 for g, x in bad if g != x), 0, cause=str([b for b in bad if b[0] != b[1]][:3]))
    # ---- vertical lines
    vl = [el for el in svg if el['tag'] == 'line' and el['y1'] == '24' and el['y2'] == '480']
    vt = {}
    for el in svg:
        if el['tag'] == 'text' and el.get('y') in ('36', '54', '72', '472'):
            vt[round(float(el['x']) - 6, 4)] = el['text']
    lines = {vt.get(round(float(el['x1']), 4), '?'): float(el['x1']) for el in vl}
    sl = lambda x: round((x - L_) / slot - 0.5)
    hd = fig['typical_day_of_60d_high']
    ent_lab = 'Today' if kind == 'forming' else 'Entry'
    exp_lines = {ent_lab: E, f'High usually ~day {hd}': slot_of(e['entry_date'] + dt.timedelta(days=hd)), 'Day 60': slot_of(e['entry_date'] + dt.timedelta(days=60))}
    if kind == 'forming' and A > E: exp_lines[f"Confirms {date_long(e['f']['conf'])} · entry, day 0"] = A
    R.add(loc, 'vertical lines and their labels', ' | '.join(sorted(lines)), ' | '.join(sorted(exp_lines)))
    for lab, i in exp_lines.items():
        if lab in lines:
            g = sl(lines[lab])
            R.add(loc, f'"{lab}" line sits on the bar opening', str(opens[g]) if 0 <= g < len(opens) else g, str(opens[i]), ok=(g == i and close(lines[lab], Xs(i))))
    if kind == 'forming':
        R.add(loc, '"Today" bar contains today (the bar still open)', 'yes' if opens[E] <= S.today <= bar_close_date(opens[E], tf) else 'no', 'yes')
    d60 = e['entry_date'] + dt.timedelta(days=60); i60 = exp_lines['Day 60']
    R.add(loc, 'Day 60 bar contains entry + 60 days', 'yes' if opens[i60] <= d60 <= bar_close_date(opens[i60], tf) else 'no', 'yes', cause=f'{opens[i60]} .. {bar_close_date(opens[i60], tf)} vs {d60}')
    ih = exp_lines[f'High usually ~day {hd}']; dh = e['entry_date'] + dt.timedelta(days=hd)
    R.add(loc, 'typical-high-day bar contains entry + that many days', 'yes' if opens[ih] <= dh <= bar_close_date(opens[ih], tf) else 'no', 'yes')
    xE, x60 = Xs(A), Xs(i60); i10 = slot_of(e['entry_date'] + dt.timedelta(days=10)); x10 = Xs(i10)
    # ---- horizontal lines / price tags / labels
    hl = [el for el in svg if el['tag'] == 'line' and el['y1'] == el['y2'] and el.get('stroke') != '#1C1736']
    lv = [('typical high', lv_high, 'var(--high)', level(entry, high)), ('+10% level', fentry * 1.1, 'var(--text)', entry * Decimal('1.10')),
          ('entry', fentry, 'var(--soft)', entry), ('typical drop', lv_drop, 'var(--drop)', level(entry, drop))]
    if edge: lv.append(('edge', fentry * (1 + edge / 100), 'var(--fade-2)', level(entry, edge)))
    R.add(loc, 'horizontal level lines (count)', len(hl), len(lv))
    for (nm, p, col, dp), el in zip(lv, hl):
        R.add(loc, f'{nm} line: price level (y position)', round(lo_x + (B_ - float(el['y1'])) * (hi_x - lo_x) / (B_ - T_), 2), round(p, 2), ok=close(el['y1'], Y(p)) and el.get('s_stroke') == col)
        R.add(loc, f'{nm} line: runs from the entry bar to the day-60 bar', f"{float(el['x1']):.3f}-{float(el['x2']):.3f}", f'{xE:.3f}-{x60:.3f}', ok=close(el['x1'], xE) and close(el['x2'], x60))
    tags = [el['text'] for el in svg if el['tag'] == 'text' and el.get('x') == '1018']
    R.add(loc, 'price tags (typical high, +10%, entry, typical drop)', ' '.join(tags), ' '.join(money(dp) for nm, p, col, dp in sorted(lv[:4], key=lambda t: -t[1])))
    labels = {el['text']: el for el in svg if el['tag'] == 'text' and el.get('font-weight') == '600' and el.get('font-size') in ('13', '12') and el.get('y') not in ('36', '54', '72', '472')}
    exp_lab = [f'Typical high {pct(high)}', f"+10% · {fig['rose10_within60d_pct']}% of past signals got here", f'Typical drop {pct(drop)}']
    if edge: exp_lab.append(f'Edge gone below {money(level(entry, edge))} ({pct(edge, 0)}, before +10%)')
    R.add(loc, 'level labels', ' | '.join(sorted(labels)), ' | '.join(sorted(exp_lab)))
    plus10 = labels.get(exp_lab[1])
    if plus10 is not None:
        g = sl(float(plus10['x']) - 8)
        R.add(loc, 'day-10 anchor (the +10% label starts at the day-10 bar) is the bar containing entry + 10 days', str(opens[g]), str(opens[i10]), ok=g == i10)
    # ---- zones
    zs = [el for el in svg if el['tag'] == 'rect' and 'opacity' in el]
    z = zs[0]
    R.add(loc, 'upside zone: entry bar to day-60 bar, entry to typical high', 'ok' if close(z['x'], xE) and close(float(z['x']) + float(z['width']), x60) and close(z['y'], Y(lv_high)) and close(float(z['y']) + float(z['height']), Y(fentry)) else 'off', 'ok')
    z = zs[1]
    R.add(loc, 'downside zone: entry bar to day-60 bar, entry to typical drop', 'ok' if close(z['x'], xE) and close(float(z['x']) + float(z['width']), x60) and close(z['y'], Y(fentry)) and close(float(z['y']) + float(z['height']), Y(lv_drop)) else 'off', 'ok')
    steps = [(0, -5, fig['from_entry']['ok'], fig['from_entry']['frac'])] + [(-r['th'], -(r['th'] + 5), r['ok'], r['frac']) for r in fig['ladder'][:3]]
    stx = [el['text'] for el in svg if el['tag'] == 'text' and el.get('font-weight') == '700' and el.get('text-anchor') == 'middle' and el.get('x') != '1018']
    R.add(loc, 'odds-fade zone shares (from entry, falls 5 / 10 / 15% first)', ' '.join(stx), ' '.join('n/a' if v is None else f'{v}%' for _, _, v, _ in steps))
    for (a1, b1, v, fr), z in zip(steps, zs[2:6]):
        col = 'var(--closed)' if v is None else 'var(--high)' if fr >= 70 else 'var(--drop)'
        R.add(loc, f'odds-fade zone {a1}% to {b1}%: price band and colour (exact share vs 70)', 'ok' if close(z['y'], Y(fentry * (1 + a1 / 100))) and close(float(z['y']) + float(z['height']), min(B_, Y(fentry * (1 + b1 / 100)))) and z.get('s_fill') == col and close(z['x'], xE) else 'off', 'ok')
    # ---- forming: the low marker
    circ = [el for el in svg if el['tag'] == 'circle']
    if kind == 'forming':
        li = next(i for i, b in enumerate(bars) if b['d'] == e['f']['tdate'])
        R.add(loc, 'low marker on the trough bar at its low', 'ok' if len(circ) == 1 and close(circ[0]['cx'], Xs(li)) and close(circ[0]['cy'], Y(bars[li]['l'])) else 'off', 'ok')
        lt = [el['text'] for el in svg if el['tag'] == 'text' and el['text'].startswith('Low ')]
        dd = S.day[a]; lday = e['low_day']
        R.add(loc, 'low marker label (day of the low and its price)', lt[0] if lt else None, f"Low {date_long(lday)} · {money(dd.sl[dd.pos[lday]])}")
    elif kind == 'open':
        R.add(loc, 'no outcome markers on a live chart', len(circ), 0)
    else:
        dd = S.day['ETH']; w = [(n_, k) for n_, k in S.window('ETH', EX)]
        hi = max(dd.h[k] for _, k in w); lo = min(dd.l[k] for _, k in w)
        nh = next(n_ for n_, k in w if dd.h[k] == hi); nl = next(n_ for n_, k in w if dd.l[k] == lo)
        this = [el['text'] for el in svg if el['tag'] == 'text' and el['text'].startswith('This one')]
        if not happened:
            R.add(loc, 'no outcome shown at the alert (markers, "This one" labels)', len(circ) + len(this), 0)
        else:
            def rng(nd):
                o = next(b['d'] for b in bars if b['d'] <= EX + dt.timedelta(days=nd) <= bar_close_date(b['d'], '2D'))
                d0, d1 = (o - EX).days, min(60, (bar_close_date(o, '2D') - EX).days)
                return (f'days {d0}–{d1}' if d1 > d0 else f'day {d0}'), o
            th, oh = rng(nh); tl, ol = rng(nl)
            sh = next(s_ for s_, k in zip([dd.sh[k] for _, k in w], w) if dd.h[k[1]] == hi); sl_ = next(s_ for s_, k in zip([dd.sl[k] for _, k in w], w) if dd.l[k[1]] == lo)
            R.add(loc, 'outcome label: 60-day high (price, % from entry, days)', this[0] if this else None, f'This one: {money(sh)} · {pct(rnd(repr((hi / fentry - 1) * 100), 6))} · {th}')
            R.add(loc, 'outcome label: 60-day low (price, % from entry, days)', this[1] if len(this) > 1 else None, f'This one: {money(sl_)} · {pct(rnd(repr((lo / fentry - 1) * 100), 6))} · {tl}')
            ih_ = next(i for i, b in enumerate(bars) if b['d'] == oh); il_ = next(i for i, b in enumerate(bars) if b['d'] == ol)
            R.add(loc, 'outcome markers sit on the high bar and the low bar', 'ok' if len(circ) == 2 and close(circ[0]['cx'], Xs(ih_)) and close(circ[0]['cy'], Y(hi)) and close(circ[1]['cx'], Xs(il_)) and close(circ[1]['cy'], Y(lo)) else 'off', 'ok')
    # ---- cloud
    grade_note = ''
    if kind == 'example': npth, q = X.ex_paths; sub_x = f'ETH top-grade signals whose 60 days had closed by 22 Sept 2024, n {npth}'
    else: npth, q = X.paths[a]; sub_x = f'Every past {a} top-grade signal, n {npth}'
    R.add(loc, 'cloud: caption and n', norm(ch['cloudSub']), sub_x)
    note_x = f"━ median path █ middle half of outcomes{' ━ this signal' if happened else ''}. Day 60: median {pct(q[60][1])}, middle half {pct(q[60][0])} to {pct(q[60][2])}. Daily closes." + ('' if top else " Top-grade signals only; the selected setup isn't top grade.")
    R.add(loc, 'cloud: day-60 median and middle half', norm(ch['cloudNote']), note_x)
    cx = lambda d: 20 + 940 * d / 60; cy = lambda v: 230 - (max(-40, min(100, v)) + 40) / 140 * 218
    pl = [el for el in ch['cloud'] if el['tag'] == 'polyline']; pg = [el for el in ch['cloud'] if el['tag'] == 'polygon']
    pts = lambda s: [tuple(float(v) for v in p.split(',')) for p in s.split()]
    med_pts = pts(pl[0]['points']); band = pts(pg[0]['points'])
    R.add(loc, 'cloud: median path points that differ from my per-day medians (of 61)', sum(1 for d, (x, y) in enumerate(med_pts) if not (close(x, cx(d)) and close(y, cy(q[d][1])))) + abs(len(med_pts) - 61), 0)
    exp_band = [(cx(d), cy(q[d][2])) for d in range(61)] + [(cx(d), cy(q[d][0])) for d in range(60, -1, -1)]
    R.add(loc, 'cloud: middle-half band points that differ from my quartiles (of 122)', sum(1 for (x, y), (ex_, ey) in zip(band, exp_band) if not (close(x, ex_) and close(y, ey))) + abs(len(band) - 122), 0)
    if kind == 'example':
        R.add(loc, 'cloud: this signal\'s own path drawn only in What happened', len(pl) - 1, 1 if happened else 0)
        if happened and len(pl) > 1:
            dd = S.day['ETH']; own = pts(pl[1]['points'])
            expo = [(cx(0), cy(0.0))] + [(cx(2 * k), cy((dd.c[dd.pos[EX + dt.timedelta(days=2 * k)]] / fentry - 1) * 100)) for k in range(1, 31)]
            R.add(loc, 'cloud: this signal\'s path points that differ from the daily closes on days 2,4..60 (of 31)', sum(1 for (x, y), (ex_, ey) in zip(own, expo) if not (close(x, ex_) and close(y, ey))) + abs(len(own) - 31), 0)
    # ---- grid labels and cloud axes
    gl = [(float(el['text'].replace('$', '').replace(',', '')), float(el['y']) - 5) for el in svg if el['tag'] == 'text' and el.get('x') == '968']
    R.add(loc, f'price-axis grid labels not at their own price (of {len(gl)})', sum(1 for p, y in gl if not close(y, Y(p))), 0)
    ca = [el for el in ch['cloud'] if el['tag'] == 'text']
    badc = 0
    for el in ca:
        t = el['text']
        if t.startswith('Day '):
            if not close(el['x'], cx(int(t[4:]))): badc += 1
        else:
            if not close(float(el['y']) - 5, cy(float(t.replace('%', '').replace('+', '')))): badc += 1
    R.add(loc, f'cloud axis labels (days, percent levels) not at their own position (of {len(ca)})', badc, 0)
    R.add(loc, 'cloud axis labels shown', ' '.join(el['text'] for el in ca), '+100% +50% +20% 0% -20% -40% Day 0 Day 10 Day 20 Day 30 Day 40 Day 50 Day 60')
    # ---- side panel
    sd = ch['side']; b0 = sd[0]
    R.add(loc, 'side: chart and sample line', norm(b0['small'][0]), f"{e['chart']} · from {e['sample']}" if kind != 'example' else f"{e['chart']} · example")
    R.add(loc, 'side: big number and the line under it', 'yes' if f"{fig['rose10_within60d_pct']}% rose 10% within 60 days, from {n} past signals; {fig['rose10_never_fell25_within60d_pct']}% without ever falling 25.3%" in norm(b0['text']) else norm(b0['text'])[:200],
          'yes')
    kv_x = [f'Typical high {pct(high)} · {money(level(entry, high))}', f"+10% level {money(entry * Decimal('1.10'))}", f"Reached +20% within 60 days {fig['rose20_within60d_pct']}%",
            f'Typical drop {pct(drop)} · {money(level(entry, drop))}',
            'Edge gone below ' + ('below the bar already' if edge == 0 else 'holds at every level' if edge is None else f'{money(level(entry, edge))} ({pct(edge, 0)})')]
    for g, x in zip(b0['kv'], kv_x): R.add(loc, 'side: ' + x.split(' $')[0].split(' +')[0].split(' ' + MIN)[0][:32], norm(g), x)
    R.add(loc, 'side: stand-in note only on a forming setup', len(b0['fine']), 1 if kind == 'forming' else 0)
    b1 = sd[1]
    if kind == 'open':
        R.add(loc, 'side live box: title', low(b1['title']), low(f"Live: day {e['elapsed']} of 60"))
        for g, x in zip(b1['kv'], [f"Best so far {pct(e['best'])}", f"Worst so far {pct(e['worst'])}", 'Day 10 ' + ('not yet' if e['d10'] is None else pct(e['d10']))]):
            R.add(loc, 'side live box: ' + x.split(' +')[0].split(' ' + MIN)[0], norm(g), x)
    elif kind == 'forming':
        R.add(loc, 'side: still-forming note', norm(b1['text']), f"Still forming. It confirms only if it holds through {date_long(e['f']['conf'])}, and it can vanish before then." + ('' if top else " It isn't top grade, so no alert goes out for it."))
    elif not happened:
        R.add(loc, 'side: at the alert shows no outcome box', 'none' if b1['title'] is None and not b1['kv'] else 'outcome shown', 'none')
    else:
        dd = S.day['ETH']; w = S.window('ETH', EX); m = e['s']['m']
        c10 = dd.c[dd.pos[EX + dt.timedelta(days=10)]]; c60 = dd.c[dd.pos[EX + dt.timedelta(days=60)]]
        brng = lambda nd: f'days {nd - 1 + nd % 2}–{nd + nd % 2}'
        kvx = [f"Reached +10% / +20% {'Yes' if m['r10'] else 'No'} / {'Yes' if m['r20'] else 'No'}",
               f"Best price {pct(rnd(repr(m['up']), 6))}, {brng(m['dpk'])}", f"Deepest drop {pct(rnd(repr(m['dd']), 6))}, {brng(m['ddday'])}",
               f"Day 10 check {'Red' if c10 < fentry else 'Green'}, {pct(rnd(repr((c10 / fentry - 1) * 100), 6))}", f"Price on day 60 {pct(rnd(repr(m['ret']), 6))}"]
        R.add(loc, 'side outcome box: title', low(b1['title']), 'what this one did')
        for g, x in zip(b1['kv'], kvx): R.add(loc, 'side outcome box: ' + x.split(' +')[0].split(' ' + MIN)[0].split(',')[0][:30], norm(g), x)
    R.add(loc, 'side: lead-trader note says unavailable', norm(sd[2]['text']), "The lead trader's feed is unavailable right now, so his entries and exits can't be shown.")
    R.add(loc, 'side: entry-quality-only footer', 'yes' if 'Entry quality only: no exit, not a trade or a track record' in sd[3]['text'] else 'no', 'yes')

def run(name):
    X = Exp(name); S = X.S; F = X.F; R = Rec(name, 'c8')
    P = json.load(open(f'{OUTDIR}/page_{name}.json')); sc = P['scenes']
    gen = dt.datetime.fromisoformat(F['generated_at'].replace('Z', '+00:00'))
    R.add('harness', 'page clock = feed generated_at + 6 minutes (to the second)', P['now_date'][:16], (gen + dt.timedelta(minutes=6)).isoformat()[:16])
    R.add('harness', 'requests answered 404 (only the trades feed)', ' '.join(sorted({u.split('/')[-1] for s_, u in P['requests'] if s_ == '404'})), 'trades.json')
    R.add('harness', 'page errors other than the aborted font and the 404', len([x for x in P['errors'] if x[0] == 'pageerror']), 0)
    # served data = raw data
    for a in ASSETS:
        for tf in TFS:
            got = S.ds(f'candles_{a.lower()}_{tf.lower()}.csv'); ch = S.ch[(a, tf)]; raw = list(csv.DictReader(open(f'{S.root}/data/{a}_{tf}.csv')))[-70:]
            bad = sum(1 for g, r in zip(got, raw) if any(g[k] != r[k] for k in ('time', 'open', 'high', 'low', 'close'))) + abs(len(got) - 70)
            R.add(f'datasets/candles_{a.lower()}_{tf.lower()}.csv', 'bars that differ from the last 70 raw bars', bad, 0)
    exj = json.load(open(f'{S.root}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')); ch = S.ch[('ETH', '2D')]
    bad = 0; exbars = []
    for b in exj['bars']:
        d = utcdate(b['t']); i = ch.pos.get(d)
        if i is None or (ch.o[i], ch.h[i], ch.l[i], ch.c[i]) != (b['o'], b['h'], b['l'], b['c']): bad += 1
        exbars.append(dict(d=d, o=b['o'], h=b['h'], l=b['l'], c=b['c']))
    R.add('data/example_ETH-2D-2024-09-22.json', f"bars that differ from the raw ETH 2D candles (of {len(exj['bars'])})", bad, 0)
    R.add('data/example_ETH-2D-2024-09-22.json', 'entry_index is the bar that closes on 2024-09-22', str(bar_close_date(exbars[exj['entry_index']]['d'], '2D')), '2024-09-22')
    R.add('data/example_ETH-2D-2024-09-22.json', 'entry_close', exj['entry_close'], rnd(X.exs['sentry'], 2))
    R.add('data/example_ETH-2D-2024-09-22.json', 'bars after the entry cover all 60 days', 'yes' if bar_close_date(exbars[-1]['d'], '2D') >= EX + dt.timedelta(days=60) else 'no', 'yes')
    # ---- banner, header, footer
    b = sc['boot']; hhmm = F['generated_at'][11:16]
    R.add('page banner', 'scored date and feed time', norm(b['review']), f"Review build. Real pipeline data, scored {date_long(S.today)} (feed {S.now.strftime('%H:%M')} UTC). Alerts go out for top-grade setups only; below-grade forming setups are shown for context. The lead trader's feed is in dry run. Show the example card")
    R.add('page header', 'market filter', b['filter'], 'Market filter: ' + ('on' if S.gate(S.today) else 'off'))
    last_closed = max(d for d in S.day['BTC'].date if d < S.today)
    R.add('page footer', 'daily candles closed through / updated / checks', b['feedState'], f"Daily candles closed through {date_long(last_closed)} · updated {S.now.strftime('%H:%M')} UTC · checks passed")
    R.add('page footer', 'last closed daily bar is yesterday on both assets', str(max(d for d in S.day['ETH'].date if d < S.today)), str(S.today - DAY1))
    R.add('page footer', 'disclaimer says computed statistics, entry quality only', 'yes' if 'computed statistics, not personal advice' in b['footer'] and 'entry quality only' in b['footer'] else 'no', 'yes')
    R.add('page tabs', 'tab names', ' | '.join(b['tabs']), 'Now | Chart | Past signals | How to read a card')
    R.add('page Now, lead trader', 'panel says the feed is unavailable', 'yes' if "The lead trader's feed is unavailable right now." in b['lead'] else 'no', 'yes')
    # ---- picker
    live = [(sid, e) for sid, e in X.sel.items() if e['kind'] == 'open' and e['grade'] == 'A+']
    formc = sorted([(sid, e) for sid, e in X.sel.items() if e['kind'] == 'forming'], key=lambda t: -t[1]['fig']['rose10_within60d_pct'])
    pk = b['picker']
    R.add('page Now, picker', 'Live buttons (top-grade open signals)', ' || '.join(x['text'] for x in pk[0]['btns']) or norm(pk[0]['none']),
          ' || '.join(f"{e['chart']} Day {e['elapsed']} best {pct(e['best'])} · worst {pct(e['worst'])}" for sid, e in live) or 'No live top-grade setups right now.')
    fb = [x for x in pk[1]['btns'] if x['sel'] != 'example']
    R.add('page Now, picker', 'Forming buttons (count)', len(fb), len(formc))
    got_by = {x['sel']: x for x in fb}
    for sid, e in formc:
        x = f"{e['chart']} {e['fig']['rose10_within60d_pct']}% rose 10% in 60 days · n {e['fig']['past_trades']} · {'top grade' if e['grade'] == 'A+' else 'not top grade'} · confirms {date_long(e['f']['conf'])}"
        R.add('page Now, picker', f'Forming button {sid}', got_by.get(sid, {}).get('text'), x)
    R.add('page Now, picker', 'Forming buttons ordered by the rose-10% share, highest first', ' '.join(str(X.sel[x['sel']]['fig']['rose10_within60d_pct']) for x in fb), ' '.join(str(e['fig']['rose10_within60d_pct']) for sid, e in formc))
    if not formc: R.add('page Now, picker', 'nothing forming text', norm(pk[1]['none']), 'Nothing forming today.')
    R.add('page Now, picker', 'example button', [x['text'] for x in pk[1]['btns'] if x['sel'] == 'example'][0], 'Example: ETH 2D, Sep 2024')
    best_sid = formc[0][0] if formc else None
    # ---- every selection: card + chart
    for sid in P['sels']:
        key = sid
        check_card(R, f'page Now [{sid}]', sc[f'now:{sid}']['card'], exp_card(X, key, best_sid))
        R.add(f'page Now [{sid}]', 'this button is the one pressed', [x['pressed'] for r in sc[f'now:{sid}']['picker'] for x in r['btns'] if x['sel'] == sid][0], 'true')
        check_chart(R, X, key, sc[f'chart:{sid}:alert'], 'alert', exbars)
        if sid == 'example':
            check_chart(R, X, key, sc['chart:example:happened'], 'happened', exbars)
            R.add('page Chart [example]', 'back to At the alert redraws the same chart', 'same' if sc['chart:example:alert2']['chart'] == sc['chart:example:alert']['chart'] else 'differs', 'same')
    R.add('page Now [example via the banner switch]', 'same card as the Example button', 'same' if sc['now:switch-example']['card']['all'] == sc['now:example']['card']['all'] else 'differs', 'same')
    # ---- previous signals
    pv = b['prev']
    intact = [(sid, e) for sid, e in live if e['status'] == 'intact']; fading = [(sid, e) for sid, e in live if e['status'] == 'lost']
    exp_int = [f"{e['chart']} | Day {e['elapsed']} of 60 · best {pct(e['best'])} · worst {pct(e['worst'])} | On track" for sid, e in intact] or ['No open top-grade setup with its edge intact.']
    got_int = [(f"{m['name']} | {norm(m['sub'])} | {m['badge']}" if m['name'] else norm(m['text'])) for m in pv['intact']]
    R.add('page Now, Previous signals', 'Edge intact list', ' || '.join(got_int), ' || '.join(exp_int))
    recent = sorted(X.aplus, key=lambda x: str(x['edate']), reverse=True)[:5]
    exp_cl = [f"{e['chart']} | Day {e['elapsed']} of 60 · best {pct(e['best'])} · worst {pct(e['worst'])} | Edge lost" for sid, e in fading]
    got_cl = [f"{m['name']} | {norm(m['sub'])} | {m['badge']}" for m in pv['closed']]
    R.add('page Now, Previous signals', 'Edge lost (open) entries', ' || '.join(got_cl[:len(fading)]), ' || '.join(exp_cl))
    R.add('page Now, Previous signals', 'closed entries shown', len(got_cl) - len(fading), 5)
    R.add('page Now, Previous signals', 'closed entries are the 5 latest entry dates', ' '.join(sorted(m['sub'].split(' · ')[0] for m in pv['closed'][len(fading):])), ' '.join(sorted(date_long(x['edate']) for x in recent)))
    mk = {(x['chart'], date_long(x['edate'])): x for x in X.aplus}
    for m in pv['closed'][len(fading):]:
        x = mk.get((m['name'], m['sub'].split(' · ')[0]))
        if x is None: R.add('page Now, Previous signals', f"{m['name']} {m['sub'][:12]} is a top-grade closed signal", 'yes', 'no'); continue
        mm = x['m']
        R.add('page Now, Previous signals', f"{x['chart']} {x['edate']}: date, best, worst", norm(m['sub']), f"{date_long(x['edate'])} · best {pct(rnd(repr(mm['up']), 6))} · worst {pct(rnd(repr(mm['dd']), 6))}")
        R.add('page Now, Previous signals', f"{x['chart']} {x['edate']}: badge", m['badge'], 'Reached +20%' if mm['r20'] else 'Rose 10%' if mm['r10'] else 'Missed')
    # ---- past signals tab
    for A_ in ('all', 'ETH', 'BTC'):
        rc = sc[f'record:{A_}']['record']; loc = f'page Past signals [{A_}]'
        rows = sorted([x for x in X.aplus if A_ == 'all' or x['a'] == A_], key=lambda x: str(x['edate']), reverse=True)
        R.add(loc, 'count line', rc['count'], f"{len(rows)} signals · {sum(1 for x in rows if not x['m']['r10'])} missed +10%")
        R.add(loc, 'heading', low(rc['head'].split(' All ETH BTC')[0]), 'every top-grade signal whose 60 days have closed · computed, never traded')
        R.add(loc, 'columns', ' | '.join(rc['th']), 'Confirmed | Chart | Entry close | Rose 10% | Reached +20% | Best | Deepest drop | Day 60 | High on day')
        R.add(loc, 'table rows', len(rc['rows']), len(rows))
        R.add(loc, 'rows in date order, newest first', 'yes' if [r[0] for r in rc['rows']] == [date_long(x['edate']) for x in rows] else 'no', 'yes')
        gotrows = {(r[1], r[0]): r for r in rc['rows']}
        for x in rows:
            m = x['m']; g = gotrows.get((x['chart'], date_long(x['edate']))); l2 = f"{loc} {x['chart']} {x['edate']}"
            if g is None: R.add(l2, 'row present', 'no', 'yes'); continue
            R.add(l2, 'Entry close', g[2], money(x['sentry'])); R.add(l2, 'Rose 10%', g[3], 'Yes' if m['r10'] else 'No'); R.add(l2, 'Reached +20%', g[4], 'Yes' if m['r20'] else 'No')
            R.add(l2, 'Best', g[5], pct(rnd(repr(m['up']), 6))); R.add(l2, 'Deepest drop', g[6], pct(rnd(repr(m['dd']), 6))); R.add(l2, 'Day 60', g[7], pct(rnd(repr(m['ret']), 6)))
            R.add(l2, 'High on day', g[8], m['dpk'])
        sums = [a for a in ASSETS if A_ in ('all', a)]
        R.add(loc, 'summary boxes', len(rc['sum']), len(sums))
        for bx, a in zip(rc['sum'], sums):
            G = [x for x in X.aplus if x['a'] == a]; nn = len(G); mi = X.miss[(a, 'A+')]
            kvx = [f'{a} {nn} signals', f"Rose 10% in 60 days {share(sum(x['m']['r10'] for x in G), nn)}%", f"Reached +20% in 60 days {share(sum(x['m']['r20'] for x in G), nn)}%",
                   f"Rose 10%, never fell 25.3% {share(sum(x['m']['surv10'] for x in G), nn)}%", f"Median deepest dip {pct(rnd(repr(st.median(x['m']['dd'] for x in G)), 1))}",
                   f"Misses: median best price {pct(mi['median_peak_pct'])}"]
            R.add(f'{loc} summary {a}', 'lines', len(bx['kv']), len(kvx))
            for g, x in zip(bx['kv'], kvx): R.add(f'{loc} summary {a}', x.rsplit(' ', 1)[0][:40], norm(g), x)
        R.add(loc, 'note says computed signals, entry quality, not a return or a track record', 'yes' if 'Computed signals, not trades.' in rc['fine'] and 'entry quality, not a return or a track record' in rc['fine'] else 'no', 'yes')
    # ---- how to read
    rd = sc['read']
    R.add('page How to read', 'posting bar', rd['howBar'], '70% bar')
    for phrase in ('rose 10% within 60 days of the entry close', 'without ever falling 25.3% below the entry close, where 3.3x leverage with 5% maintenance margin liquidates',
                   'after it first falls 5%, 10%, 15% or 20%, the share of its past signals that still rose 10% before ever falling 25.3%',
                   'The first fall at which this setup\'s odds drop below our 70% bar.', 'Of the past signals that did not rise 10% within 60 days',
                   'They measure the quality of the entry, not a trading result.', 'measure entry quality only'):
        R.add('page How to read', f'text present: "{phrase[:60]}"', 'yes' if phrase in rd['read'] else 'no', 'yes')
    # ---- wording scans over every rendered scene
    alltxt = []
    for k, v in sc.items():
        alltxt += [v['review'], v['footer'], v['lead'], v['card']['all'], v['prev']['all'], v['chart']['title'], v['chart']['sub'], v['chart']['cloudSub'], v['chart']['cloudNote'], v['read'],
                   v['record']['head'], v['record']['count'], v['record']['fine']] + [b['text'] for b in v['chart']['side']] + [x['text'] for r in v['picker'] for x in r['btns']] \
                  + [el.get('text', '') for el in v['chart']['svg'] if el['tag'] == 'text'] + [' '.join(kv) for bx in v['record']['sum'] for kv in [bx['kv']]]
    blob = ' \n '.join(t for t in alltxt if t)
    R.add('page, all scenes', 'grade letters in member-facing text (A+, grade A/B/C, graded)', len(re.findall(r'A\+|\bgrade [ABC]\b|\bgraded\b', blob)), 0)
    R.add('page, all scenes', 'words that read as a result of trading (profit, won, win rate, winner, P&L, return of, gained, performance)',
          len(re.findall(r'profit|\bwon\b|win rate|winner|P&L|\bgained\b|performance|returned', blob, re.I)), 0)
    # 'trade' / 'track record' only as the lead trader's real trades or in a denial
    sents = set()
    for t in alltxt:
        for snt in re.split(r'(?<=[.!?])\s+', t or ''):
            if re.search(r'\btrad(e|es|ed|ing)\b|track record|\breturn\b', snt, re.I): sents.add(norm(snt))
    okpat = re.compile(r"lead trader|not a trade|not trades|never traded|not a return|not a trading result|leveraged trading|his real|real trades|real entries|Every trade is posted|never dollar amounts|no exit", re.I)
    bad = sorted(x for x in sents if not okpat.search(x))
    R.add('page, all scenes', 'sentences using trade / track record / return other than the lead trader\'s real trades, a denial or the risk warning', len(bad), 0, cause=' ## '.join(bad)[:600])
    R.save()
    print(name, 'sentences with trade/track record/return:'); [print('     ', x[:230]) for x in sorted(sents)]
    return X, P

if __name__ == '__main__':
    for nm in (sys.argv[1:] or list(STATES)):
        run(nm)
