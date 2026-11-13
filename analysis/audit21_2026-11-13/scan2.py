"""fast scan of every day since Sep 2020 for forming lows (own engine, truncated bars), to pick replay dates"""
import sys, datetime as dt, json, collections
sys.path.insert(0, '.')
import core as C
S = C.State('../a21/current', dt.date(2026, 11, 13))
out = {}
for a in C.ASSETS:
    day = S.day[a]
    for tf in C.TFS:
        ch = S.ch[(a, tf)]; b = ch.b; step = C.bar_len(tf)
        closes_full = b.c; st = C.rsi_state(closes_full)
        for di in range(day.pos[dt.date(2020, 9, 1)], day.n):
            D = day.date[di]
            # index of the bar holding D
            j = max(i for i in range(max(0, b.n - 1 - (day.n - di) // step - 3), b.n) if b.date[i] <= D) if step > 1 else b.pos[D]
            if j < 20 or st[j - 1] is None: continue
            au, ad = st[j - 1]; chg = day.c[di] - closes_full[j - 1]
            au2 = (au * 13 + max(chg, 0.0)) / 14; ad2 = (ad * 13 + max(-chg, 0.0)) / 14
            last = 100.0 if ad2 == 0 else 100 - 100 / (1 + au2 / ad2)
            ct = ch.ct[:j] + [last]
            for back in (1, 2, 3):
                ti = j - back; v = ct[ti]
                if any(ct[k] <= v for k in range(ti - 3, ti)): continue
                if any(ct[k] < v for k in range(ti + 1, j + 1)): continue
                need = 3 - back; co = b.date[j]
                for _ in range(need): co = C.next_open(co, step)
                conf = C.next_open(co, step) - C.D1
                out.setdefault(str(D), []).append(dict(chart=f'{a} {tf}', need=need, tdate=str(b.date[ti]), conf=str(conf), gate_t=bool(S.gate(b.date[ti])), gate_now=bool(S.gate(D)),
                                                       cross=conf.year != b.date[ti].year or conf.year != D.year, lastday=(C.next_open(b.date[j], step) - C.D1) == D))
                break
json.dump(out, open('scan2.json', 'w'))
sel = collections.OrderedDict()
def pick(name, f, k=6):
    c = [(d, x) for d, v in sorted(out.items()) for x in v if f(d, x)]
    print(name, len(c), [(d, x['chart'], x['need'], x['conf']) for d, x in c[:: max(1, len(c) // k)][:k + 2]])
pick('year-crossing confirm, graded multi-day, gate on at trough', lambda d, x: x['cross'] and x['chart'][-2:] in ('2D', '3D', '5D') and x['gate_t'], 12)
pick('gate on at trough, off today (graded)', lambda d, x: x['gate_t'] and not x['gate_now'] and x['chart'][-2:] != '8D', 8)
pick('gate off at trough, on today (graded)', lambda d, x: not x['gate_t'] and x['gate_now'] and x['chart'][-2:] != '8D', 8)
pick('need 0 on 5D', lambda d, x: x['need'] == 0 and x['chart'][-2:] == '5D' and x['gate_t'], 8)
pick('need 0 on 3D, last day of bar', lambda d, x: x['need'] == 0 and x['chart'][-2:] == '3D' and x['gate_t'] and x['lastday'], 6)
pick('8D forming, gate on', lambda d, x: x['chart'][-2:] == '8D' and x['gate_t'], 6)
n = collections.Counter(len([x for x in v if x['gate_t'] and x['chart'][-2:] != '8D']) for v in out.values()); print('graded gate-on forming lows per day:', sorted(n.items()))
big = [(d, len([x for x in v if x['gate_t'] and x['chart'][-2:] != '8D'])) for d, v in sorted(out.items())]; print('days with 6+:', [d for d, k in big if k >= 6][:12])
