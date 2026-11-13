"""Scan every date from Sep 2020 for what a replay on that date would hold (own code, partial bars emulated):
the gate today, forming lows per chart (trough date, gate at the trough), open signals. Used to choose replay dates."""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mycore import *


def daily(sdir, a):
    return load(os.path.join(sdir, 'data', f'{a}_1D.csv'))


def rsi_states(c, n=14):
    """(g, l) after each index, and rsi"""
    st = [None] * len(c); out = [None] * len(c)
    if len(c) < n + 1:
        return st, out
    g = sum(max(c[i] - c[i - 1], 0.0) for i in range(1, n + 1)) / n
    l = sum(max(c[i - 1] - c[i], 0.0) for i in range(1, n + 1)) / n
    st[n] = (g, l); out[n] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        g = (g * (n - 1) + max(ch, 0.0)) / n; l = (l * (n - 1) + max(-ch, 0.0)) / n
        st[i] = (g, l); out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return st, out


def step(state, prev_close, close, n=14):
    g, l = state; ch = close - prev_close
    g = (g * (n - 1) + max(ch, 0.0)) / n; l = (l * (n - 1) + max(-ch, 0.0)) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def main(sdir, out):
    D1 = {a: daily(sdir, a) for a in ASSETS}
    pos = {a: {b['d']: i for i, b in enumerate(D1[a])} for a in ASSETS}
    full = {}
    for a in ASSETS:
        for tf in TFS:
            b = load(os.path.join(sdir, 'data', f'{a}_{tf}.csv'))
            c = [x['c'] for x in b]
            st, ct = rsi_states(c)
            full[(a, tf)] = dict(d=[x['d'] for x in b], c=c, st=st, ct=ct, idx={x['d']: i for i, x in enumerate(b)})
    # gate: Jared's state machine on BTC 2D CT (8 bars >= 60 on, 13 bars < 41 off), my own code
    g2 = full[('BTC', '2D')]

    def gate_series(ct):
        state = False; up = dn = 0; out = []
        for v in ct:
            if v is not None:
                up = up + 1 if v >= 60 else 0
                dn = dn + 1 if v < 41 else 0
                if not state and up >= 8: state = True; dn = 0
                elif state and dn >= 13: state = False; up = 0
            out.append(state)
        return out
    gfull = gate_series(g2['ct'])
    # precompute the state machine before each bar
    def gate_state_before(i):
        state = False; up = dn = 0
        for v in g2['ct'][:i]:
            if v is not None:
                up = up + 1 if v >= 60 else 0
                dn = dn + 1 if v < 41 else 0
                if not state and up >= 8: state = True; dn = 0
                elif state and dn >= 13: state = False; up = 0
        return state, up, dn
    GS = []
    state = False; up = dn = 0
    for v in g2['ct']:
        GS.append((state, up, dn))
        if v is not None:
            up = up + 1 if v >= 60 else 0
            dn = dn + 1 if v < 41 else 0
            if not state and up >= 8: state = True; dn = 0
            elif state and dn >= 13: state = False; up = 0
    # signals in hindsight (closed bars are final)
    gate_h = lambda d: gfull[max(i for i in [g2['idx'].get(bar_start(d, 2))] if i is not None)]
    res = []
    d = dt.date(2020, 9, 1)
    end = max(D1['ETH'][-1]['d'], D1['BTC'][-1]['d'])
    while d <= end:
        row = dict(date=str(d))
        # live gate today: BTC 2D partial bar = bar_start(d) with close = BTC daily close on d
        bs = bar_start(d, 2); i = g2['idx'][bs]
        cpart = D1['BTC'][pos['BTC'][d]]['c']
        ctp = step(g2['st'][i - 1], g2['c'][i - 1], cpart)
        stt, upp, dnn = GS[i]
        upp = upp + 1 if ctp >= 60 else 0; dnn = dnn + 1 if ctp < 41 else 0
        if not stt and upp >= 8: stt = True
        elif stt and dnn >= 13: stt = False
        gate_today = stt

        def gate_at(x):
            if bar_start(x, 2) == bs:
                return gate_today
            return gfull[g2['idx'][bar_start(x, 2)]]
        row['gate'] = gate_today
        forming = []
        for a in ASSETS:
            for tf in TFS:
                F = full[(a, tf)]; tfd = int(tf[:-1])
                bsd = bar_start(d, tfd); j = F['idx'].get(bsd)
                if j is None or j < 20:
                    continue
                ccl = D1[a][pos[a][d]]['c']
                ct = F['ct'][:j] + [step(F['st'][j - 1], F['c'][j - 1], ccl)]
                n = len(ct)
                for back in (1, 2, 3):
                    ti = n - 1 - back
                    v = ct[ti]
                    if v is None or any(ct[k] is None or ct[k] <= v for k in range(ti - 3, ti)):
                        continue
                    if any(ct[k] < v for k in range(ti + 1, n)):
                        continue
                    td = F['d'][ti]
                    forming.append(dict(ch=f'{a} {tf}', trough=str(td), need=3 - back, gate_trough=gate_at(td)))
                    break
        row['forming'] = forming
        res.append(row)
        d += ONE_DAY
    json.dump(res, open(out, 'w'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
