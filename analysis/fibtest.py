"""Fibonacci retracements and extensions as lenses on CTZB signals. Declared 31 Oct 2026.

RE-TEST BY REQUEST. PRETRADE's failed list says "Fibs ... All empty" and CONTEXT says
"Fib levels are not special", but that test predates the repo: no script, no record of
the method. Jared asked 31 Oct for a declared re-test, as general knowledge or as a
card line, in fine-tuning mode: does any fib reading raise the odds without cutting a
disproportionate share of good trades?

UNIVERSE: regime-gated signals (R.rsi_regime BTC 2D 8/13/60/41) on the 10 system
charts (ETH/BTC 1D 2D 3D 5D 8D), entry = close of the confirmation bar ei = ti + 3.
OUTCOME: the card measure -- SURV10 (rose 10%, never fell 25.3%, within 60 days) and
LIQ30 (fell 30%+ within 60 days). stochdwell.Chart.outcome, unchanged.

SWING (knowable at entry; every bar used is BEFORE the trough bar ti):
  For each lookback W in {30, 60, 90, 180, 365} calendar days:
    H  = highest high of the chart's bars dated in [date(ti) - W, ti), at bar h
    L0 = lowest low from the window start to bar h (the low the rise to H started from)
    Skipped if H <= L0.
  Retracement depth of the signal low:  r = (H - low[ti]) / (H - L0)
    (0 = the trough is at the high, 1 = it is back at L0, > 1 = below L0)
  Fib retracement level f sits at price H - f * (H - L0).
  Room overhead: (H / entry - 1), the distance from entry back to the 1.0 (the high).

LENSES (7 per window, 35 cells):
  R1 POCKET   0.5 <= r <= 0.786        (trough in the 0.5-0.786 zone)
  R2 SHALLOW  r < 0.382
  R3 DEEP     0.786 < r <= 1
  R4 BROKE    r > 1                    (trough under the swing's starting low)
  R5 TAGGED   trough low within 2% of the 0.382, 0.5, 0.618 or 0.786 level
  X1 ROOM20   swing high at least 20% above entry
  X2 ROOM10-  swing high less than 10% above entry

PASS RULES (stochdwell part A, unchanged), each cell:
  A1 n with >= 40 and n without >= 40
  A2 SURV10 with minus without >= +8 pooled (<= -8 = a caution lens)
  A3 LIQ30 with no higher than without (caution: no lower)
  A4 same sign before 2022 and 2022 on
  A5 same sign on >= 2/3 of charts with n >= 8 both sides
  A6 same sign in >= 60% of years with n >= 5 both sides
  A7 holds at >= 5 (caution <= -5) stratified by bucket and by prime dot
  PLUS, because 35 cells will throw up chance passes:
  A8 the same lens passes A1-A7 in at least 2 of the 5 windows
  For R5 only (are the LEVELS special, or just the depth?): its lift stratified by depth
  band (r < 0.382, 0.382-0.618, 0.618-1, > 1) is printed; a level effect needs that to
  hold too.
Collinearity: phi against bucket A, prime, diamond and the Promising "shallow
pullback" read (entry close in the top third of its 30-day range) printed beside each.
Anything that passes is checked by chart, year and asset before it goes near a card.
Entry quality only: no exit in the data, not a strategy return or a track record.

Run from the repo root:  python3 -I analysis/fibtest.py
"""
import sys, os, statistics, datetime as dt
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import stochdwell as S

WINDOWS = (30, 60, 90, 180, 365)
LENSES = ('R1_POCKET', 'R2_SHALLOW', 'R3_DEEP', 'R4_BROKE', 'R5_TAGGED', 'X1_ROOM20', 'X2_ROOM10')
LEVELS = (0.382, 0.5, 0.618, 0.786)


def swing(ch, ti, W):
    d = ch.b['date']; hi = ch.b['high']; lo = ch.b['low']
    start = d[ti] - dt.timedelta(days=W)
    js = [j for j in range(max(0, ti - 400), ti) if d[j] >= start]
    if len(js) < 3: return None
    h = max(js, key=lambda j: hi[j])
    pre = [j for j in js if j <= h]
    L0 = min(lo[j] for j in pre); H = hi[h]
    if H <= L0: return None
    return H, L0


def rows_for(charts):
    rows = []
    for ch in charts:
        sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=S.GATE)
        c = ch.b['close']; lo = ch.b['low']; hi = ch.b['high']; d = ch.b['date']
        for s in sig:
            ti, ei = s['ti'], s['ei']
            o = ch.outcome(ei)
            if o is None: continue
            # Promising "shallow pullback": entry close in top third of its 30-day range
            js = [j for j in range(max(0, ei - 200), ei + 1) if d[j] >= d[ei] - dt.timedelta(days=30)]
            h30 = max(hi[j] for j in js); l30 = min(lo[j] for j in js)
            shal = h30 > l30 and (c[ei] - l30) / (h30 - l30) >= 2 / 3
            r = dict(chart=ch.name, asset=ch.sym, date=d[ei], bk=s['bk'], bkA=s['bk'] == 'A',
                     prime=s['prime'], dia=s['dis'], shal=shal, **o)
            for W in WINDOWS:
                sw = swing(ch, ti, W)
                if sw is None:
                    for L in LENSES: r[f'{L}@{W}'] = None
                    r[f'r@{W}'] = None
                    continue
                H, L0 = sw; rng = H - L0; low = lo[ti]
                rr = (H - low) / rng
                room = (H / c[ei] - 1) * 100
                tag = any(abs(low - (H - f * rng)) / (H - f * rng) <= 0.02 for f in LEVELS if H - f * rng > 0)
                r[f'r@{W}'] = rr
                r[f'R1_POCKET@{W}'] = 0.5 <= rr <= 0.786
                r[f'R2_SHALLOW@{W}'] = rr < 0.382
                r[f'R3_DEEP@{W}'] = 0.786 < rr <= 1
                r[f'R4_BROKE@{W}'] = rr > 1
                r[f'R5_TAGGED@{W}'] = tag
                r[f'X1_ROOM20@{W}'] = room >= 20
                r[f'X2_ROOM10@{W}'] = room < 10
            rows.append(r)
    return rows


def depth_band(rr):
    return 'a' if rr < 0.382 else 'b' if rr < 0.618 else 'c' if rr <= 1 else 'd'


def evaluate(rows, key):
    v = [r for r in rows if r[key] is not None]
    w = [r for r in v if r[key]]; wo = [r for r in v if not r[key]]
    if not w or not wo: return None
    pct = lambda xs, f: 100 * statistics.mean(x[f] for x in xs)
    sw, so, lw, lo = pct(w, 'surv'), pct(wo, 'surv'), pct(w, 'liq'), pct(wo, 'liq')
    lift = sw - so; sgn = 1 if lift > 0 else -1
    def split(kf, minn):
        g = defaultdict(lambda: ([], []))
        for r in v: g[kf(r)][0 if r[key] else 1].append(r['surv'])
        return {k: (100 * statistics.mean(a) - 100 * statistics.mean(b), min(len(a), len(b)))
                for k, (a, b) in g.items() if len(a) >= minn and len(b) >= minn}
    per = split(lambda r: 'old' if r['date'] < S.CUT else 'new', 10)
    chs = split(lambda r: r['chart'], 8)
    yrs = split(lambda r: r['date'].year, 5)
    cs, cn = S.same_sign_share(chs, sgn, 0)
    ys, yn = S.same_sign_share(yrs, sgn, 0)
    bka = S.strat_lift(v, key, lambda r: r['bk'])
    pra = S.strat_lift(v, key, lambda r: r['prime'])
    W = int(key.split('@')[1])
    dpa = S.strat_lift(v, key, lambda r: depth_band(r[f'r@{W}']))
    checks = [len(w) >= 40 and len(wo) >= 40, abs(lift) >= 8,
              (lw <= lo) if sgn > 0 else (lw >= lo),
              'old' in per and 'new' in per and per['old'][0] * sgn > 0 and per['new'][0] * sgn > 0,
              cs is not None and cs >= 2 / 3, ys is not None and ys >= 0.6,
              bka is not None and pra is not None and bka * sgn >= 5 and pra * sgn >= 5]
    failed = [f'A{j + 1}' for j, ok in enumerate(checks) if not ok]
    return dict(nw=len(w), nwo=len(wo), sw=sw, so=so, lw=lw, lo=lo, lift=lift, per=per,
                cs=(cs, cn), ys=(ys, yn), bka=bka, pra=pra, dpa=dpa, failed=failed,
                phis=[S.phi(v, key, x) for x in ('bkA', 'prime', 'dia', 'shal')])


def main():
    print(__doc__.split('Run from')[0])
    charts = S.load_charts(S.SYS_TF)
    rows = rows_for(charts)
    print(f'Signals: {len(rows)}  SURV10 {100 * statistics.mean(r["surv"] for r in rows):.0f}%  '
          f'LIQ30 {100 * statistics.mean(r["liq"] for r in rows):.0f}%\n')
    fx = lambda x: f'{x:+.0f}' if x is not None else '-'
    print(f'  {"lens@window":<17}{"n with":>7}{"SURV":>6}{"LIQ":>5}{"n w/o":>7}{"SURV":>6}{"LIQ":>5}{"lift":>6}'
          f'{"<2022":>7}{"2022+":>7}{"charts":>8}{"years":>7}{"bk-adj":>7}{"pr-adj":>7}{"dp-adj":>7}'
          f'{"phiA":>6}{"phiPr":>6}{"phiDi":>6}{"phiSh":>6}  verdict')
    passes = defaultdict(list)
    for L in LENSES:
        for W in WINDOWS:
            key = f'{L}@{W}'
            e = evaluate(rows, key)
            if e is None:
                print(f'  {key:<17} (empty)'); continue
            v = 'PASS A1-A7' if not e['failed'] else 'fail ' + ','.join(e['failed'])
            if not e['failed']: passes[L].append(W)
            fp = lambda k: f'{e["per"][k][0]:+.0f}' if k in e['per'] else '  -'
            cs = f'{e["cs"][0] * 100:.0f}%/{e["cs"][1]}' if e['cs'][0] is not None else '-'
            ys = f'{e["ys"][0] * 100:.0f}%/{e["ys"][1]}' if e['ys'][0] is not None else '-'
            print(f'  {key:<17}{e["nw"]:>7}{e["sw"]:>6.0f}{e["lw"]:>5.0f}{e["nwo"]:>7}{e["so"]:>6.0f}{e["lo"]:>5.0f}'
                  f'{e["lift"]:>+6.0f}{fp("old"):>7}{fp("new"):>7}{cs:>8}{ys:>7}{fx(e["bka"]):>7}{fx(e["pra"]):>7}'
                  f'{fx(e["dpa"]):>7}' + ''.join(f'{p:>6.2f}' for p in e['phis']) + f'  {v}')
        print()
    print('Depth of the signal low in its prior swing (share of signals), and SURV10 / LIQ30 by band:')
    for W in WINDOWS:
        g = defaultdict(list)
        for r in rows:
            if r[f'r@{W}'] is not None: g[depth_band(r[f'r@{W}'])].append(r)
        lab = {'a': '<0.382', 'b': '0.382-0.618', 'c': '0.618-1', 'd': '>1'}
        print(f'  {W:>3}d  ' + '   '.join(
            f'{lab[k]}: {len(g[k])} {100 * statistics.mean(r["surv"] for r in g[k]):.0f}%/'
            f'{100 * statistics.mean(r["liq"] for r in g[k]):.0f}%' for k in 'abcd' if g[k]))
    print('\nSUMMARY (A8: a lens must pass A1-A7 in at least 2 of the 5 windows)')
    found = [f'{L} ({", ".join(f"{w}d" for w in ws)})' for L, ws in passes.items() if len(ws) >= 2]
    single = [f'{L} ({ws[0]}d only)' for L, ws in passes.items() if len(ws) == 1]
    print('  Passing A1-A8:', ', '.join(found) or 'none')
    print('  Passing A1-A7 in one window only (chance-level, not a finding):', ', '.join(single) or 'none')
    print('  Entry quality only. No exit in the data; not a strategy return or a track record.')


if __name__ == '__main__':
    main()
