"""Distance from a fib level as a graded quantity. Declared 31 Oct 2026.

Jared, 31 Oct, after fibreclaim: "what about distance from a fib level?" fibreclaim and
fibtest only asked yes/no questions (within 2%, reclaimed or not). This asks whether
the DISTANCE itself grades the trade, in quintiles.

UNIVERSE / OUTCOME / SWINGS / LEVELS as fibreclaim.py (1,172 signals, card measure,
30/60/90-day and 90-bar swings, fib levels 0.236-0.786 vs placebo 0.30-0.85).

MEASURES (percent of price, from the entry close or the trough low):
  D1 UP     distance from the entry close UP to the nearest level above it (room to resistance)
  D2 DOWN   distance from the entry close DOWN to the nearest level below it (cushion to support)
  D3 LOW    distance from the trough low to the nearest level, either side
  (no level on that side -> the signal is left out of that measure)

Signals are split into quintiles of each measure (per measure and swing, pooled).
PASS, each measure-swing cell:
  Q1 top-vs-bottom quintile SURV10 gap >= 8 points
  Q2 the five quintiles move in order: |Spearman(quintile, SURV10)| >= 0.9
  Q3 same direction before 2022 and 2022 on (top vs bottom quintile)
  Q4 LIQ30 gap no worse in the better quintile
  Q5 beats the PLACEBO version of the same cell by >= 5 points on the top-bottom gap
  Q6 passes Q1-Q5 at two of the four swings, same direction

Run from the repo root:  python3 -I analysis/fibdist.py
"""
import sys, os, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import stochdwell as S
import fibreclaim as FR

MEAS = ('D1_UP', 'D2_DOWN', 'D3_LOW')


def dists(H, L0, cen, low, fs):
    rng = H - L0
    lv = [H - f * rng for f in fs if H - f * rng > 0]
    up = [p / cen - 1 for p in lv if p > cen]
    dn = [1 - p / cen for p in lv if p <= cen]
    return {'D1_UP': 100 * min(up) if up else None,
            'D2_DOWN': 100 * min(dn) if dn else None,
            'D3_LOW': 100 * min(abs(low / p - 1) for p in lv) if lv else None}


def build():
    rows = []
    for ch in S.load_charts(S.SYS_TF):
        sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=S.GATE)
        c, lo = ch.b['close'], ch.b['low']
        for s in sig:
            ti, ei = s['ti'], s['ei']; o = ch.outcome(ei)
            if o is None: continue
            r = dict(date=ch.b['date'][ei], **o)
            for sw in FR.SWINGS:
                g = FR.swing_of(ch, ti, sw)
                for tag, fs in (('F', FR.FIB), ('P', FR.PLACEBO)):
                    dd = dists(*g, c[ei], lo[ti], fs) if g else {m: None for m in MEAS}
                    for m in MEAS: r[f'{tag}:{m}@{sw}'] = dd[m]
            rows.append(r)
    return rows


def spearman(xs, ys):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
        for k, i in enumerate(o): r[i] = k
        return r
    rx, ry = rank(xs), rank(ys); n = len(xs)
    return 1 - 6 * sum((a - b) ** 2 for a, b in zip(rx, ry)) / (n * (n * n - 1))


def quint(rows, key):
    v = sorted([r for r in rows if r[key] is not None], key=lambda r: r[key])
    if len(v) < 100: return None
    q = [v[i * len(v) // 5:(i + 1) * len(v) // 5] for i in range(5)]
    pct = lambda xs, f: 100 * statistics.mean(x[f] for x in xs)
    sv = [pct(x, 'surv') for x in q]; lq = [pct(x, 'liq') for x in q]
    edges = [x[-1][key] for x in q[:-1]]
    def gap(f):
        a = [r for r in q[0] if f(r)]; b = [r for r in q[4] if f(r)]
        return pct(b, 'surv') - pct(a, 'surv') if a and b else None
    return dict(sv=sv, lq=lq, edges=edges, gap=sv[4] - sv[0], rho=spearman(list(range(5)), sv),
                old=gap(lambda r: r['date'] < S.CUT), new=gap(lambda r: r['date'] >= S.CUT), n=len(v))


def main():
    print(__doc__.split('Run from')[0])
    rows = build()
    passes = {}
    for m in MEAS:
        print(f'{m}   SURV10 by quintile, nearest-to-farthest (LIQ30 in brackets)')
        for sw in FR.SWINGS:
            e = quint(rows, f'F:{m}@{sw}'); p = quint(rows, f'P:{m}@{sw}')
            if e is None: print(f'  {sw}: too few'); continue
            sg = 1 if e['gap'] > 0 else -1
            ok = [abs(e['gap']) >= 8, abs(e['rho']) >= 0.9,
                  e['old'] is not None and e['new'] is not None and e['old'] * sg > 0 and e['new'] * sg > 0,
                  (e['lq'][4] <= e['lq'][0]) if sg > 0 else (e['lq'][0] <= e['lq'][4]),
                  p is not None and (e['gap'] - p['gap']) * sg >= 5]
            failed = [f'Q{j + 1}' for j, x in enumerate(ok) if not x]
            if not failed: passes.setdefault(m, []).append((sw, sg))
            qs = '  '.join(f'{s:.0f}({l:.0f})' for s, l in zip(e['sv'], e['lq']))
            ed = '/'.join(f'{x:.1f}' for x in e['edges'])
            print(f'  {sw:<8} n={e["n"]:<5} {qs}   gap {e["gap"]:+.0f}  rho {e["rho"]:+.1f}  '
                  f'<2022 {e["old"]:+.0f} 2022+ {e["new"]:+.0f}  placebo gap {p["gap"]:+.0f}   '
                  f'cuts {ed}%   {"PASS Q1-Q5" if not failed else "fail " + ",".join(failed)}')
        print()
    print('Q6 (two of four swings, same direction):')
    for m in MEAS:
        h = passes.get(m, [])
        print(f'  {m:<8} ' + ('PASS at ' + ', '.join(w for w, _ in h) if len(h) >= 2 and len({s for _, s in h}) == 1
                              else 'one swing only: ' + h[0][0] if len(h) == 1 else 'none'))
    print('\nEntry quality only. No exit in the data; not a strategy return or a track record.')


if __name__ == '__main__':
    main()
