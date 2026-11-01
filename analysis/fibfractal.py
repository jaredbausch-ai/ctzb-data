"""The fibtest survivor at smaller, fractal scales. Declared 31 Oct 2026.

fibtest.py found R4_BROKE@180 (signal low under the low the prior 180-day swing started
from): 81% vs 58% SURV10, but only 17 independent episodes. Jared asked 31 Oct whether
shrinking the swing, in a fractal way, gives more signals. Shrinking the CALENDAR window
already failed in fibtest (30d -3, 60d -2, 90d +8 but only the 200-day average). This
tests two fractal versions instead, where the swing scales with the chart.

SCALES (every bar used is before the trough bar ti; knowable at entry):
  BARS-N   the last N bars of the chart itself, N in {20, 40, 60, 90, 120}.
           H = highest high in [ti-N, ti), L0 = lowest low from the window start to H.
           (So 20 bars = 20 days on 1D, 100 days on 5D, 160 days on 8D.)
  PIV-k    the chart's own swing pivots, k in {3, 5, 8, 13}: H = the last pivot high
           (k bars each side, confirmed by ti) before the trough; L0 = the last pivot
           low (k each side) before that pivot high. A zigzag at four sizes.
  BROKE = low[ti] < L0.

PASS RULES: fibtest/stochdwell A1-A7 unchanged, plus
  A8 same direction and A1-A7 passed at two neighbouring scales of the same kind
  A9 lift >= +5 inside price-under / over its 200-day average (fibtest showed the 90-day
     calendar version was only that)
  Independent EPISODES (14-day clusters across all charts and both assets) printed for
  every cell, because more signals only helps if it is more independent events.

Run from the repo root:  python3 -I analysis/fibfractal.py
"""
import sys, os, statistics
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import stochdwell as S
import fibtest_check as FC

BARS = (20, 40, 60, 90, 120)
PIVS = (3, 5, 8, 13)


def pivots(hi, lo, k):
    n = len(hi); ph = [False] * n; pl = [False] * n
    for i in range(k, n - k):
        if all(hi[i] > hi[j] for j in range(i - k, i)) and all(hi[i] >= hi[j] for j in range(i + 1, i + k + 1)):
            ph[i] = True
        if all(lo[i] < lo[j] for j in range(i - k, i)) and all(lo[i] <= lo[j] for j in range(i + 1, i + k + 1)):
            pl[i] = True
    return ph, pl


def build():
    charts = S.load_charts(S.SYS_TF)
    rows = []
    for ch in charts:
        sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=S.GATE)
        hi, lo, d = ch.b['high'], ch.b['low'], ch.b['date']
        pv = {k: pivots(hi, lo, k) for k in PIVS}
        for s in sig:
            ti, ei = s['ti'], s['ei']; o = ch.outcome(ei)
            if o is None: continue
            r = dict(chart=ch.name, asset=ch.sym, date=d[ei], bk=s['bk'], prime=s['prime'], **o)
            for N in BARS:
                js = list(range(max(0, ti - N), ti))
                if len(js) < N:
                    r[f'BARS-{N}'] = None; continue
                h = max(js, key=lambda j: hi[j]); L0 = min(lo[j] for j in js if j <= h)
                r[f'BARS-{N}'] = lo[ti] < L0 if hi[h] > L0 else None
            for k in PIVS:
                ph, pl = pv[k]
                # pivots confirmed by the trough bar: index <= ti - k, and before ti
                p = next((j for j in range(ti - k, -1, -1) if ph[j]), None)
                q = next((j for j in range(p - 1, -1, -1) if pl[j]), None) if p is not None else None
                r[f'PIV-{k}'] = (lo[ti] < lo[q]) if q is not None else None
            rows.append(r)
    FC.extra(charts, rows)
    return rows


def main():
    print(__doc__.split('Run from')[0])
    rows = build()
    pct = lambda v: 100 * statistics.mean(v) if v else float('nan')
    print(f'  {"scale":<9}{"n with":>7}{"SURV":>6}{"LIQ":>5}{"n w/o":>7}{"SURV":>6}{"LIQ":>5}{"lift":>6}'
          f'{"<2022":>7}{"2022+":>7}{"charts":>8}{"years":>7}{"bk-adj":>7}{"pr-adj":>7}{"200-adj":>8}'
          f'{"episodes":>10}{"ep SURV":>8}  verdict')
    res = {}
    for key in [f'BARS-{n}' for n in BARS] + [f'PIV-{k}' for k in PIVS]:
        v = [r for r in rows if r[key] is not None]
        for r in v: r['_k'] = r[key]
        w = [r for r in v if r['_k']]; wo = [r for r in v if not r['_k']]
        sw, so = pct([r['surv'] for r in w]), pct([r['surv'] for r in wo])
        lw, lo = pct([r['liq'] for r in w]), pct([r['liq'] for r in wo])
        lift = sw - so; sgn = 1 if lift > 0 else -1
        def split(kf, minn):
            g = defaultdict(lambda: ([], []))
            for r in v: g[kf(r)][0 if r['_k'] else 1].append(r['surv'])
            return {x: (pct(a) - pct(b), min(len(a), len(b))) for x, (a, b) in g.items()
                    if len(a) >= minn and len(b) >= minn}
        per = split(lambda r: 'old' if r['date'] < S.CUT else 'new', 10)
        cs, cn = S.same_sign_share(split(lambda r: r['chart'], 8), sgn, 0)
        ys, yn = S.same_sign_share(split(lambda r: r['date'].year, 5), sgn, 0)
        bka = S.strat_lift(v, '_k', lambda r: r['bk']); pra = S.strat_lift(v, '_k', lambda r: r['prime'])
        u2 = S.strat_lift(v, '_k', lambda r: r['u200'])
        eps = FC.episodes(w)
        eps_s = pct([statistics.mean(x['surv'] for x in e) >= 0.5 for e in eps])
        checks = [len(w) >= 40 and len(wo) >= 40, abs(lift) >= 8, (lw <= lo) if sgn > 0 else (lw >= lo),
                  'old' in per and 'new' in per and per['old'][0] * sgn > 0 and per['new'][0] * sgn > 0,
                  cs is not None and cs >= 2 / 3, ys is not None and ys >= 0.6,
                  bka is not None and pra is not None and bka * sgn >= 5 and pra * sgn >= 5]
        failed = [f'A{j + 1}' for j, ok in enumerate(checks) if not ok]
        if u2 is None or u2 * sgn < 5: failed.append('A9')
        res[key] = (not failed, sgn)
        fx = lambda x: f'{x:+.0f}' if x is not None else '-'
        fp = lambda x: f'{per[x][0]:+.0f}' if x in per else '-'
        print(f'  {key:<9}{len(w):>7}{sw:>6.0f}{lw:>5.0f}{len(wo):>7}{so:>6.0f}{lo:>5.0f}{lift:>+6.0f}'
              f'{fp("old"):>7}{fp("new"):>7}{(f"{cs*100:.0f}%/{cn}" if cs is not None else "-"):>8}'
              f'{(f"{ys*100:.0f}%/{yn}" if ys is not None else "-"):>7}{fx(bka):>7}{fx(pra):>7}{fx(u2):>8}'
              f'{len(eps):>10}{eps_s:>7.0f}%  {"pass A1-A7,A9" if not failed else "fail " + ",".join(failed)}')
    print('\nA8 (passes at two neighbouring scales of the same kind, same direction):')
    for kind, scales in (('BARS', BARS), ('PIV', PIVS)):
        ks = [f'{kind}-{s}' for s in scales]
        hits = [f'{a} + {b}' for a, b in zip(ks, ks[1:]) if res[a][0] and res[b][0] and res[a][1] == res[b][1]]
        print(f'  {kind}: ' + (', '.join(hits) if hits else 'none'))
    print('\nEntry quality only. No exit in the data; not a strategy return or a track record.')


if __name__ == '__main__':
    main()
