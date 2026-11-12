import sys, json, re
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from model8 import *
from c_page_now_helpers import cmp_lines
import chk

L_, R_, T_, B_ = 20, 960, 24, 480
TOL = 0.01


def next_open(d, tf):
    return bar_last_day(d, tf) + dt.timedelta(days=1)


def side_edge(m, entry):
    e = m['edge']['exact']
    if e == 0: return 'below the bar already'
    if e is None: return 'holds at every level'
    return f"{money(entry * (1 + F(e, 100)))} ({pct(e, 0)})"


ex_json = None
for st in ('REPLAY', 'CURRENT'):
    M = State(st)
    P = json.load(open(f'{chk.OUT}/code/page_{st}.json'))
    feed = M.feed
    ex_json = json.load(open(STATES[st] + '/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
    models = {}
    for o in feed['open_signals']:
        if o['grade'] == 'A+': models[o['signal_id']] = ('open', M.card_model(o['card'], 'open'), o)
    for c in feed['cards']:
        models[c['signal_id']] = ('forming', M.card_model(c, 'forming'), c)
    models['example'] = ('example', M.card_model(feed['example_card'], 'example'), feed['example_card'])
    # --- datasets candles vs raw (what the chart draws)
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            rows = list(csv.DictReader(open(f"{STATES[st]}/datasets/candles_{a.lower()}_{tf.lower()}.csv")))
            raw = list(csv.DictReader(open(f"{STATES[st]}/data/{a}_{tf}.csv")))[-70:]
            same = all(all(F(r[k]) == F(q[k]) for k in ('time', 'open', 'high', 'low', 'close')) for r, q in zip(rows, raw)) and len(rows) == len(raw)
            chk.add(st, f'datasets/candles_{a.lower()}_{tf.lower()}.csv', 'equals last 70 raw bars', same, True, 'chart candles')
    # --- example json bars vs my ETH 2D bars
    myb = {b['d']: b for b in all_signals(st)[('ETH', '2D')]['bars']}
    for i, b in enumerate(ex_json['bars']):
        d = fdate(b['t']); mb = myb.get(d)
        for k in ('o', 'h', 'l', 'c'):
            chk.add(st, f'example json bar {i} ({d})', k, b[k], None if mb is None else float(mb[k]), 'example bars')
    E_ex = ex_json['entry_index']
    chk.add(st, 'example json', 'entry bar closes on 2024-09-22', str(bar_last_day(fdate(ex_json['bars'][E_ex]['t']), '2D')), '2024-09-22', 'example bars')
    chk.add(st, 'example json', 'entry_close', ex_json['entry_close'], rhaz(models['example'][1]['entry'], 2), 'example bars')
    # consecutive bars, nothing missing
    exd = [fdate(b['t']) for b in ex_json['bars']]
    chk.add(st, 'example json', 'bars consecutive', all(next_open(exd[i], '2D') == exd[i + 1] for i in range(len(exd) - 1)), True, 'example bars')
    for sid, d in P['sel'].items():
        kind, m, c = models[sid]
        a, tf = m['asset'], m['tf']
        for mode, ch in d['chart'].items():
            loc = f'page chart {sid} [{mode}]'
            happened = kind == 'example' and mode == 'happened'
            forming = kind != 'example'
            # ---------------- bars, slots
            if kind == 'example':
                bars = [myb[x] for x in exd]
                E = next(i for i, b in enumerate(bars) if bar_last_day(b['d'], '2D') == EXD)
                entry = m['entry']; d0 = EXD
            else:
                bars = all_signals(st)[(a, tf)]['bars'][-70:]
                if kind == 'open':
                    E = next(i for i, b in enumerate(bars) if bar_last_day(b['d'], tf) == m['d0']); entry = m['entry']
                else:
                    E = len(bars) - 1; entry = m['entry']
                d0 = m['d0']
            opens = [b['d'] for b in bars]
            if forming:
                while opens[-1] <= d0 + dt.timedelta(days=61): opens.append(next_open(opens[-1], tf))
            nS = len(opens) if forming else len(bars)
            slot = (R_ - L_) / nS; X = lambda i: L_ + slot * i + slot / 2
            sl = lambda day: max(i for i, o in enumerate(opens) if o <= day)
            dayX = lambda k: sl(d0 + dt.timedelta(days=k))
            A = dayX(0) if kind == 'forming' else E
            # ---------------- scaling
            ent = F(entry)
            lv_high = ent * (1 + m['mu'] / 100); lv_t = ent * F(11, 10); lv_drop = ent * (1 + m['md'] / 100)
            e = m['edge']['exact']; lv_edge = ent * (1 + F(e, 100)) if e else None
            shown = bars[:E + 1] if (kind == 'example' and not happened) else bars
            lo = float(min(min(b['l'] for b in shown), lv_drop, ent * F(8, 10))) * 0.95
            hi = float(max(max(b['h'] for b in shown), lv_high)) * 1.07
            Y = lambda p: B_ - (float(p) - lo) / (hi - lo) * (B_ - T_)
            svg = ch['svg']
            texts = [x for x in svg if x['tag'] == 'text']
            grid = [(float(x['y']) - 5, float(x['text'][1:].replace(',', ''))) for x in texts if x.get('x') == '968']
            if len(grid) >= 2:
                (y1, p1), (y2, p2) = grid[0], grid[-1]
                rng = (p2 - p1) * (B_ - T_) / (y1 - y2); glo = p1 - (B_ - y1) * rng / (B_ - T_)
                chk.add(st, loc, 'price axis bottom (lo) from gridlines', round(glo, 4), round(lo, 4), 'axis scaling', ok=abs(glo - lo) < 0.01 * max(1, abs(lo)) * 1e-3 + 0.01)
                chk.add(st, loc, 'price axis top (hi) from gridlines', round(glo + rng, 4), round(hi, 4), 'axis scaling', ok=abs(glo + rng - hi) < 0.01 * max(1, abs(hi)) * 1e-3 + 0.01)
            # ---------------- vertical lines
            vl = []
            for i, x in enumerate(svg):
                if x['tag'] == 'line' and x.get('y1') == '24' and x.get('y2') == '480' and x.get('x1') == x.get('x2'):
                    vl.append((float(x['x1']), svg[i + 1]['text']))
            idx = lambda xv: (xv - L_) / slot - 0.5
            exp_v = []
            if kind == 'forming':
                exp_v.append(('Today', len(bars) - 1))
            else:
                exp_v.append(('Entry', E))
            hd = m['f']['typical_day_of_60d_high']
            exp_v.append((f'High usually ~day {hd}', dayX(hd)))
            exp_v.append(('Day 60', min(nS - 1, dayX(60))))
            if kind == 'forming' and A > E: exp_v.append((f"Confirms {dlong(d0)} · entry, day 0", A))
            chk.add(st, loc, 'vertical line labels', ' | '.join(sorted(t for _, t in vl)), ' | '.join(sorted(t for t, _ in exp_v)), 'chart lines')
            for t, i in exp_v:
                got = [xv for xv, tt in vl if tt == t]
                chk.add(st, loc, f'"{t}" sits on bar/slot', round(idx(got[0]), 6) if got else 'absent', i, 'chart line position',
                        ok=bool(got) and abs(idx(got[0]) - i) < 1e-6)
                # meaning: that slot really holds the calendar day
                if t.startswith('Day 60'):
                    day = d0 + dt.timedelta(days=60)
                    chk.add(st, loc, 'Day 60 slot contains calendar day 60', f"{opens[i]}..{bar_last_day(opens[i], tf)}", str(day), 'chart line meaning',
                            ok=opens[i] <= day <= bar_last_day(opens[i], tf))
                if t in ('Entry',) or t.startswith('Confirms'):
                    chk.add(st, loc, f'{t} slot closes on the entry date', str(bar_last_day(opens[i], tf)), str(d0), 'chart line meaning')
            # ---------------- level lines and price tags
            tags = [x['text'] for x in texts if x.get('x') == '1018']
            chk.add(st, loc, 'price tags', ' | '.join(sorted(tags)), ' | '.join(sorted([money(lv_high), money(lv_t), money(ent), money(lv_drop)])), 'chart prices')
            hl = [(float(x['y1']), x.get('css', '')) for x in svg if x['tag'] == 'line' and x.get('x1') != x.get('x2') and x.get('stroke-width') in ('2', '2.5')]
            for nm, p, col in (('typical high', lv_high, 'var(--high)'), ('+10%', lv_t, 'var(--text)'), ('entry', ent, 'var(--soft)'), ('typical drop', lv_drop, 'var(--drop)')) + ((('edge', lv_edge, 'var(--fade-2)'),) if lv_edge else ()):
                ys = [y for y, css in hl if col in css]
                chk.add(st, loc, f'{nm} line y', round(ys[0], 4) if ys else 'absent', round(Y(p), 4), 'chart line position', ok=bool(ys) and abs(ys[0] - Y(p)) < TOL)
            labs = [x['text'] for x in texts if x['text'].startswith(('Typical high', '+10%', 'Typical drop', 'Edge gone'))]
            exp_l = [f"Typical high {pct(m['mu'])}", f"+10% · {m['f']['rose10_within60d_pct']}% of past signals got here", f"Typical drop {pct(m['md'])}"]
            if lv_edge: exp_l.append(f"Edge gone below {money(lv_edge)} ({pct(e, 0)}, before +10%)")
            chk.add(st, loc, 'level labels', ' | '.join(sorted(labs)), ' | '.join(sorted(exp_l)), 'chart labels')
            # ---------------- ladder zones
            steps = [(0, -5, rhaz(m['base'] * 100))] + [(-r['fell'], -(m['rows'][k + 1]['fell'] if k + 1 < len(m['rows']) else r['fell'] + 5),
                                                        None if r['v'] is None else rhaz(r['v'] * 100)) for k, r in enumerate(m['rows'][:3])]
            zt = [x for x in texts if x.get('font-size') == '13' and x.get('font-weight') == '700' and x.get('text-anchor') == 'middle' and x.get('x') != '1018']
            for k, (a1, b1, v) in enumerate(steps):
                y1 = Y(ent * (1 + F(a1, 100))); y2 = min(B_, Y(ent * (1 + F(b1, 100))))
                z = zt[k] if k < len(zt) else None
                chk.add(st, loc, f'ladder zone {a1}..{b1}% text', z['text'] if z else 'absent', 'n/a' if v is None else f'{v}%', 'chart ladder')
                chk.add(st, loc, f'ladder zone {a1}..{b1}% y', round(float(z['y']), 4) if z else 'absent', round((y1 + y2) / 2 + 5, 4), 'chart ladder',
                        ok=bool(z) and abs(float(z['y']) - ((y1 + y2) / 2 + 5)) < TOL)
            # ---------------- candles
            upto = len(bars) if forming else (len(bars) if happened else E + 1)
            cl = [x for x in svg if x['tag'] == 'line' and x.get('stroke-width') == '1.5' and x.get('y1') != '24' and x['x1'] == x['x2']]
            chk.add(st, loc, 'candles drawn', len(cl), upto, 'candles (at the alert never shows the outcome)')
            badc = 0
            for i, x in enumerate(cl[:upto]):
                b = bars[i]
                if abs(float(x['x1']) - X(i)) > TOL or abs(float(x['y1']) - Y(b['h'])) > TOL or abs(float(x['y2']) - Y(b['l'])) > TOL: badc += 1
            chk.add(st, loc, 'candle wicks at my high/low and slot', badc, 0, 'candle position')
            # ---------------- x axis dates
            xd = [x for x in texts if x.get('y') == '502']
            every = max(1, int(F(nS, 8) + F(1, 2)))
            exp_x = [(X(i), dshort(opens[min(i, len(opens) - 1)])) for i in range(0, nS, every)]
            chk.add(st, loc, 'x-axis date labels', ' | '.join(x['text'] for x in xd), ' | '.join(t for _, t in exp_x), 'x axis')
            # ---------------- low marker / outcome circles
            circ = [(x, svg[i + 1]) for i, x in enumerate(svg) if x['tag'] == 'circle']
            if kind == 'forming':
                li = next(i for i, b in enumerate(bars) if b['d'] == m['tdate'])
                lowp = min(daily(st, a)[0][daily(st, a)[1][dd]]['l'] for dd in [m['tdate'] + dt.timedelta(days=k) for k in range(TFD[tf])] if dd in daily(st, a)[1])
                chk.add(st, loc, 'low marker text', circ[0][1]['text'] if circ else 'absent', f"Low {dlong(m['low_day'])} · {money(lowp)}", 'low marker')
                chk.add(st, loc, 'low marker position', f"{float(circ[0][0]['cx']):.4f},{float(circ[0][0]['cy']):.4f}" if circ else 'absent', f'{X(li):.4f},{Y(lowp):.4f}', 'low marker',
                        ok=bool(circ) and abs(float(circ[0][0]['cx']) - X(li)) < TOL and abs(float(circ[0][0]['cy']) - Y(lowp)) < TOL)
            elif happened:
                tEnd = d0 + dt.timedelta(days=61)
                win = [(i, b) for i, b in enumerate(bars) if i > E and b['d'] < tEnd]
                hiB = max(win, key=lambda x: (x[1]['h'], -x[0])); loB = min(win, key=lambda x: (x[1]['l'], x[0]))
                exp_c = []
                for (i, b), p in ((hiB, hiB[1]['h']), (loB, loB[1]['l'])):
                    dd0 = (b['d'] - d0).days; dd1 = min(60, (next_open(b['d'], tf) - d0).days - 1)
                    exp_c.append((X(i), Y(p), f"This one: {money(p)} · {pct((p / ent - 1) * 100)} · " + (f'days {dd0}–{dd1}' if dd1 > dd0 else f'day {dd0}')))
                for k, (cx, cy, t) in enumerate(exp_c):
                    got = circ[k] if k < len(circ) else None
                    chk.add(st, loc, f'outcome marker {k} text', got[1]['text'] if got else 'absent', t, 'outcome marker')
                    chk.add(st, loc, f'outcome marker {k} position', f"{float(got[0]['cx']):.3f},{float(got[0]['cy']):.3f}" if got else 'absent', f'{cx:.3f},{cy:.3f}', 'outcome marker',
                            ok=bool(got) and abs(float(got[0]['cx']) - cx) < TOL and abs(float(got[0]['cy']) - cy) < TOL)
                # meaning: the bars hold the daily extremes of the 60 days
                mm = m['sig']['m']
                chk.add(st, loc, 'outcome high equals the 60-day daily high', f"{(hiB[1]['h'] / ent - 1) * 100:.6f}", f"{mm['up']:.6f}" if False else f"{float(mm['up']):.6f}", 'outcome marker')
                chk.add(st, loc, 'outcome low equals the 60-day daily low', f"{float((loB[1]['l'] / ent - 1) * 100):.6f}", f"{float(mm['dd']):.6f}", 'outcome marker')
            else:
                chk.add(st, loc, 'no outcome markers at the alert', len(circ), 0, 'at the alert')
            # ---------------- texts: title, sub, side, cloud
            if kind == 'open':
                s = m['sig']
                t_exp = f"{a} · {tf} · live setup, day {s['days']} of 60"
                sub = f"Confirmed {dlong(d0)} · entry close {money(ent)}. Zones use this setup's own card ({m['basis']})." + ' The shaded zones are the next 60 days, as the odds draw them.'
            elif kind == 'forming':
                t_exp = f"{a} · {tf} · {'setup forming' if m['grade'] == 'A+' else 'forming, not top grade'}"
                sub = f"Low {dlong(m['low_day'])} · confirms {dlong(d0)} · price levels drawn from today's price ({money(ent)}), since the entry price is the confirmation close; days count from the confirmation. The shaded zones are the next 60 days, as the odds draw them."
            else:
                t_exp = 'ETH · 2-day · example: past confirmed setup'
                sub = f"Confirmed {dlong(EXD)} · entry close {money(ent)} · a past computed signal. Its odds use only the signals whose 60 days had closed by then, as a member would have seen them." + ('' if happened else ' The shaded zones are the next 60 days, as the odds draw them.')
            chk.add(st, loc, 'title', ch['title'], t_exp.upper(), 'chart text')
            chk.add(st, loc, 'subtitle', ch['sub'], sub, 'chart text')
            f = m['f']
            side = ['WHAT THE CARD SAYS', f"{a} {tf} · " + (f"from {m['basis']}" if forming else 'example'), f"{f['rose10_within60d_pct']}%",
                    f"rose 10% within 60 days, from {f['past_trades']} past signals; {f['rose10_never_fell25_within60d_pct']}% without ever falling 25.3%",
                    'Typical high', f"{pct(m['mu'])} · {money(lv_high)}", '+10% target', money(lv_t), 'Reached +20% within 60 days', f"{f['rose20_within60d_pct']}%",
                    'Typical drop', f"{pct(m['md'])} · {money(lv_drop)}", 'Edge gone below', side_edge(m, ent)]
            if kind == 'forming':
                side += ["Prices use the latest price (today's bar is still open) as a stand-in for the entry.",
                         f"Still forming. It confirms only if it holds through {dlong(d0)}, and it can vanish before then. " + ('' if m['grade'] == 'A+' else "It isn't top grade, so no alert goes out for it.")]
            elif kind == 'open':
                s = m['sig']
                side += [f"LIVE: DAY {s['days']} OF 60", 'Best so far', pct(s['best']), 'Worst so far', pct(s['worst']), 'Day 10', 'not yet' if s['day10'] is None else pct(s['day10'])]
            elif happened:
                w = window(st, 'ETH', EXD); mm = m['sig']['m']
                hiB = max(win, key=lambda x: (x[1]['h'], -x[0])); loB = min(win, key=lambda x: (x[1]['l'], x[0]))
                rng = lambda i: f"days {(i - E) * 2 - 1}–{(i - E) * 2}"
                c10 = next(x['c'] for dd, x in w if dd == 10); c60 = next(x['c'] for dd, x in w if dd == 60)
                side += ['WHAT THIS ONE DID', 'Reached +10% / +20%', f"{'Yes' if mm['r10'] else 'No'} / {'Yes' if mm['r20'] else 'No'}",
                         'Best price', f"{pct(mm['up'])}, {rng(hiB[0])}", 'Deepest drop', f"{pct(mm['dd'])}, {rng(loB[0])}",
                         'Day 10 check', f"{'Red' if c10 < ent else 'Green'}, {pct((c10 / ent - 1) * 100)}", 'Price on day 60', pct(mm['ret'])]
                lo_r = (hiB[0] - E) * 2 - 1, (hiB[0] - E) * 2
                chk.add(st, loc, 'best-price day range contains the daily high day', f'{lo_r[0]}-{lo_r[1]}', mm['dpk'], 'outcome days', ok=lo_r[0] <= mm['dpk'] <= lo_r[1])
                lo_r = (loB[0] - E) * 2 - 1, (loB[0] - E) * 2
                chk.add(st, loc, 'deepest-drop day range contains the daily low day', f'{lo_r[0]}-{lo_r[1]}', mm['ddday'], 'outcome days', ok=lo_r[0] <= mm['ddday'] <= lo_r[1])
            else:
                side += ['This is all a member had at the alert: the zones, the target and the timing. Press', 'What happened', 'to see the real path.']
            side += ["The lead trader's real entries and exits show on the chart as markers. None on this one.",
                     "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record. Past results don't guarantee future results."]
            cmp_lines(st, f'{loc} side panel', ch['side'], side, 'chart side panel')
            # cloud
            if kind == 'example':
                G = M.group('ETH', 'A+', EXD); csub = f"ETH top-grade signals whose 60 days had closed by {dlong(EXD)}, n "
            else:
                G = M.group(a, 'A+'); csub = f"Every past {a} top-grade signal, n "
            Pp = [x['m']['path'] for x in G if x['m']['days_present'] == list(range(1, 61))]
            q = {fr: [rhaz(quant([p[dd] for p in Pp], fr), 1) for dd in range(61)] for fr in (F(1, 4), F(1, 2), F(3, 4))}
            chk.add(st, loc, 'cloud subtitle', ch['cloudSub'], csub + str(len(Pp)), 'cloud')
            note = f"━ median path   █ middle half of outcomes{'   ━ this signal' if happened else ''}. Day 60: median {pct(q[F(1, 2)][60])}, middle half {pct(q[F(1, 4)][60])} to {pct(q[F(3, 4)][60])}. Daily closes." + \
                   (" Top-grade signals only; the selected setup isn't top grade." if kind != 'example' and m['grade'] != 'A+' else '')
            chk.add(st, loc, 'cloud note', ch['cloudNote'].replace('\xa0', ' '), note, 'cloud')
            CX = lambda dd: 20 + 940 * dd / 60; CY = lambda v: 230 - (max(-40, min(100, float(v))) + 40) / 140 * 218
            polys = [x for x in ch['cloud'] if x['tag'] == 'polyline']
            pts = [tuple(map(float, p.split(','))) for p in polys[0]['points'].split()]
            badp = sum(1 for dd, (px, py) in enumerate(pts) if abs(px - CX(dd)) > TOL or abs(py - CY(q[F(1, 2)][dd])) > TOL)
            chk.add(st, loc, 'cloud median line points (61) at my medians', badp, 0, 'cloud', ok=badp == 0 and len(pts) == 61)
            band = [tuple(map(float, p.split(','))) for p in [x for x in ch['cloud'] if x['tag'] == 'polygon'][0]['points'].split()]
            expb = [(CX(dd), CY(q[F(3, 4)][dd])) for dd in range(61)] + [(CX(dd), CY(q[F(1, 4)][dd])) for dd in reversed(range(61))]
            badb = sum(1 for (px, py), (ex_, ey) in zip(band, expb) if abs(px - ex_) > TOL or abs(py - ey) > TOL)
            chk.add(st, loc, 'cloud middle-half band points (122) at my quartiles', badb, 0, 'cloud', ok=badb == 0 and len(band) == 122)
            if happened:
                w = window(st, 'ETH', EXD)
                expp = [(0.0, 0.0)] + [(dd, float((x['c'] / ent - 1) * 100)) for dd, x in w if dd % 2 == 0]
                pts2 = [tuple(map(float, p.split(','))) for p in polys[1]['points'].split()] if len(polys) > 1 else []
                badt = sum(1 for (px, py), (dd, v) in zip(pts2, expp) if abs(px - CX(dd)) > TOL or abs(py - CY(v)) > TOL)
                chk.add(st, loc, "cloud 'this signal' line (31 points) at my daily closes on days 0,2..60", badt, 0, 'cloud', ok=badt == 0 and len(pts2) == 31)
            elif len(polys) > 1:
                chk.add(st, loc, "no 'this signal' line at the alert", len(polys) - 1, 0, 'at the alert')
            chk.add(st, loc, 'toggle shown only for the example', not ch['toggle_hidden'], kind == 'example', 'chart toggle')
chk.dump('_page_chart.csv')
bad = [c for c in chk.CHECKS if c['ok'] == 'no']
print(len(chk.CHECKS), 'checks', len(bad), 'bad')
for c in bad[:80]: print(c)
