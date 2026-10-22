"""Volatility-scaled forecast range — the first improvement to the market-state rating.

PROBLEM IT ADDRESSES. lastyear.py showed the base-rate range was far too wide in
2023 (actual landed inside the forecast middle half 90-98% of the time against
a 50% target) because it pooled every regime-on day since 2016, 2017 and 2021
included. How much price moves next is much better predicted by how much it has
been moving than by the long-run average.

DECLARED BEFORE RUNNING (22 Oct 2026).

  vol        sigma_D = standard deviation of daily log returns over the N days
             ending on D (knowable at D's close). Primary N = 30; sensitivity
             N = 14 and 60, reported, not chosen between after the fact.
  method     every pool day d has its H-day outcomes expressed in units of its
             own vol:  z = log(1 + x) / (sigma_d * sqrt(H)),  for x in
             ret, mfe, mae. The forecast for D takes the pool's z quantiles and
             multiplies by sigma_D * sqrt(H), then converts back to %. So the
             lean and the width both scale with today's vol; the SHAPE comes
             from history. Touch probabilities compare each pool day's z to the
             threshold log(1 +/- L%) / (sigma_D * sqrt(H)).
  pool       unchanged from lastyear.py / twoweek.py: gate-ON days (gate read on
             the last CLOSED BTC 2D bar), outcome closed before D, all 12
             indicator features present. Gate-ON forecast days only.
  compared   OLD = the unscaled base rate (lastyear.py BASE). NEW = vol-scaled.
  scores     band coverage (share inside the forecast middle half, target 50%),
             band width (median p75 - p25, points), mean |actual - median|,
             Brier for P(up), P(touch +/-10), P(touch +/-20)
  test       walk-forward: every 7th gate-ON day from 2019-01-01 with a closed
             outcome, both assets, H = 14/30/60/90, plus each year separately
  ACCEPT     NEW is adopted only if, at N = 30, across both assets and all four
             horizons: (a) coverage is closer to 50% than OLD in at least 6 of 8
             asset-horizon cells, (b) mean P(up) Brier is not worse than OLD by
             more than 0.005 in any cell, and (c) per-year coverage is closer to
             50% than OLD in a majority of testable years for ETH 30 days.
             Otherwise it is reported as failed and the old range stays.
  charts     2023 and 22 Oct - 31 Dec 2025, daily, written to
             analysis/forecasts_vol_<window>.csv with both OLD and NEW columns.

This still measures market state only. No exit, no strategy return.

Run from the repo root:  python3 -I analysis/volrange.py
"""
import sys, os, math, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import twoweek as T

LOOKBACKS = (30, 14, 60)
PRIMARY_N = 30
LEVELS = (10, 20)
WINDOWS = {'2023': (dt.date(2023, 1, 1), dt.date(2023, 12, 31)),
           'late2025': (dt.date(2025, 10, 22), dt.date(2025, 12, 31))}


def vol_series(day, n):
    c = np.array(day['close'], dtype=float)
    lr = np.diff(np.log(c))
    out = {}
    for i, d in enumerate(day['date']):
        if i >= n:
            out[d] = float(np.std(lr[i - n:i], ddof=1))
    return out


class Asset:
    def __init__(self, sym, gate):
        self.sym = sym
        self.day, self.state = T.live_state(sym)
        self.cl = dict(zip(self.day['date'], self.day['close']))
        self.last_closed = self.day['date'][-2]
        self.gate = gate
        self.vol = {n: vol_series(self.day, n) for n in LOOKBACKS}
        self.oc = {}
        for H in T.HORIZONS:
            oc, _ = T.outcomes(self.day, H)
            self.oc[H] = {d: o for d, o in oc.items() if d + dt.timedelta(days=H) <= self.last_closed}
        feats = T.SUBSETS['S12']
        self.on = [d for d in self.day['date'] if gate(d) and T.vec(self.state[d], feats) is not None]

    def pool(self, D, H):
        return [d for d in self.on if d in self.oc[H] and (D - d).days > H]

    def old(self, pool, H):
        o = self.oc[H]
        r = np.array([o[d]['ret'] for d in pool]); mf = np.array([o[d]['mfe'] for d in pool])
        ma = np.array([o[d]['mae'] for d in pool])
        f = dict(q25=np.percentile(r, 25), med=np.median(r), q75=np.percentile(r, 75), up=np.mean(r > 0))
        for L in LEVELS:
            f[f'+{L}'] = np.mean(mf >= L); f[f'-{L}'] = np.mean(ma <= -L)
        return f

    def new(self, pool, H, D, n):
        o = self.oc[H]; v = self.vol[n]
        pool = [d for d in pool if d in v]
        s = np.array([v[d] * math.sqrt(H) for d in pool])
        zr = np.log1p(np.array([o[d]['ret'] for d in pool]) / 100) / s
        zf = np.log1p(np.array([o[d]['mfe'] for d in pool]) / 100) / s
        za = np.log1p(np.array([o[d]['mae'] for d in pool]) / 100) / s
        s0 = v[D] * math.sqrt(H)
        back = lambda z: (math.exp(z * s0) - 1) * 100
        f = dict(q25=back(np.percentile(zr, 25)), med=back(np.median(zr)), q75=back(np.percentile(zr, 75)),
                 up=np.mean(zr > 0))
        for L in LEVELS:
            f[f'+{L}'] = np.mean(zf >= math.log1p(L / 100) / s0)
            f[f'-{L}'] = np.mean(za <= math.log1p(-L / 100) / s0)
        return f


def score(rows, which):
    a = [r['act'] for r in rows]; f = [r[which] for r in rows]
    out = dict(n=len(rows))
    out['cov'] = 100 * np.mean([x['q25'] <= y['ret'] <= x['q75'] for x, y in zip(f, a)])
    out['below'] = 100 * np.mean([y['ret'] < x['q25'] for x, y in zip(f, a)])
    out['width'] = float(np.median([x['q75'] - x['q25'] for x in f]))
    out['abs'] = float(np.mean([abs(y['ret'] - x['med']) for x, y in zip(f, a)]))
    ev = {'up': lambda y: y['ret'] > 0}
    for L in LEVELS:
        ev[f'+{L}'] = (lambda L: lambda y: y['mfe'] >= L)(L)
        ev[f'-{L}'] = (lambda L: lambda y: y['mae'] <= -L)(L)
    for k, fn in ev.items():
        out[f'B{k}'] = float(np.mean([(x[k] - float(fn(y))) ** 2 for x, y in zip(f, a)]))
    return out


def line(s):
    return (f"n={s['n']:>4} cover {s['cov']:4.0f}% (below {s['below']:3.0f}%) width {s['width']:5.1f} "
            f"|miss| {s['abs']:5.1f}  B up {s['Bup']:.3f} +10 {s['B+10']:.3f} -10 {s['B-10']:.3f} "
            f"+20 {s['B+20']:.3f} -20 {s['B-20']:.3f}")


def main():
    gate = T.gate_daily()
    verdict = []
    csvs = {w: open(f'analysis/forecasts_vol_{w}.csv', 'w') for w in WINDOWS}
    for f in csvs.values():
        f.write('sym,H,forecast_date,target_date,start,old_q25,old_med,old_q75,new_q25,new_med,new_q75,actual\n')
    for sym in ('ETH', 'BTC'):
        A = Asset(sym, gate)
        for H in T.HORIZONS:
            print(f'==================== {sym} H={H}')
            # walk-forward
            tests = [d for d in A.on if d >= T.WF_START and d in A.oc[H]][::T.WF_STEP]
            rows = {n: [] for n in LOOKBACKS}
            for t in tests:
                p = A.pool(t, H)
                if len(p) < 200 or t not in A.vol[max(LOOKBACKS)]:
                    continue
                old = A.old(p, H)
                for n in LOOKBACKS:
                    rows[n].append(dict(d=t, old=old, new=A.new(p, H, t, n), act=A.oc[H][t]))
            r30 = rows[PRIMARY_N]
            so, sn = score(r30, 'old'), score(r30, 'new')
            print(f'  WALK-FORWARD {r30[0]["d"]} .. {r30[-1]["d"]}')
            print(f'    OLD         {line(so)}')
            for n in LOOKBACKS:
                print(f'    NEW vol{n:<3}   {line(score(rows[n], "new"))}')
            yrs = sorted({r['d'].year for r in r30}); closer = 0
            ytxt = []
            for y in yrs:
                sel = [r for r in r30 if r['d'].year == y]
                a, b = score(sel, 'old')['cov'], score(sel, 'new')['cov']
                closer += abs(b - 50) < abs(a - 50)
                ytxt.append(f'{y}:{a:.0f}->{b:.0f}')
            print(f'    coverage by year OLD->NEW (vol{PRIMARY_N}): ' + '  '.join(ytxt) +
                  f'   closer to 50% in {closer} of {len(yrs)}')
            verdict.append(dict(sym=sym, H=H, cov_closer=abs(sn['cov'] - 50) < abs(so['cov'] - 50),
                                brier_ok=sn['Bup'] <= so['Bup'] + 0.005, yrs=(closer, len(yrs))))
            # windows for charts
            for w, (a0, a1) in WINDOWS.items():
                wr = []
                for D in A.on:
                    if not (a0 <= D <= a1) or D not in A.oc[H]:
                        continue
                    p = A.pool(D, H)
                    wr.append(dict(d=D, old=A.old(p, H), new=A.new(p, H, D, PRIMARY_N), act=A.oc[H][D]))
                    c0 = A.cl[D]; px = lambda x: round(c0 * (1 + x / 100), 2)
                    o, nw = wr[-1]['old'], wr[-1]['new']
                    csvs[w].write(f"{sym},{H},{D},{D + dt.timedelta(days=H)},{c0},{px(o['q25'])},{px(o['med'])},"
                                  f"{px(o['q75'])},{px(nw['q25'])},{px(nw['med'])},{px(nw['q75'])},"
                                  f"{px(A.oc[H][D]['ret'])}\n")
                print(f'  WINDOW {w:<8} OLD {line(score(wr, "old"))}')
                print(f'  WINDOW {w:<8} NEW {line(score(wr, "new"))}')
    print('\nACCEPTANCE (declared in the docstring)')
    a = sum(v['cov_closer'] for v in verdict); b = all(v['brier_ok'] for v in verdict)
    e30 = [v for v in verdict if v['sym'] == 'ETH' and v['H'] == 30][0]['yrs']
    c = e30[0] > e30[1] / 2
    for v in verdict:
        print(f"  {v['sym']} {v['H']:>2}d  coverage closer to 50%: {v['cov_closer']}  P(up) Brier within 0.005: {v['brier_ok']}  "
              f"years closer {v['yrs'][0]}/{v['yrs'][1]}")
    print(f'  (a) coverage closer in {a} of 8 cells -> {"PASS" if a >= 6 else "FAIL"}')
    print(f'  (b) P(up) Brier never worse by >0.005 -> {"PASS" if b else "FAIL"}')
    print(f'  (c) ETH 30d coverage closer in {e30[0]} of {e30[1]} years -> {"PASS" if c else "FAIL"}')
    print(f'  VERDICT: {"ADOPT" if (a >= 6 and b and c) else "REJECT"}')
    for f in csvs.values():
        f.close()


if __name__ == '__main__':
    main()
