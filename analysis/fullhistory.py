"""The adopted volatility-scaled range (volrange.py), run over all of ETH history.

DECLARED BEFORE RUNNING (22 Oct 2026). Jared asked how well the range holds
across the whole record, bear years included, and whether price ever leaves it.

  days       every ETH day whose outcome is closed by the last closed daily bar,
             gate ON and gate OFF both. Each day is forecast from days with the
             SAME gate state only, so bear periods are judged against bear
             history. A day is skipped until its pool has 200 closed outcomes.
  pool       same gate state, outcome closed before the forecast day,
             30-day vol available. The 12 indicator features are NOT required
             here, since the vol-scaled range does not use them; this lets the
             record start earlier. Otherwise identical to volrange.py (N = 30).
  bands      middle half  p25-p75   target: 50% inside, 25% below, 25% above
             wide band    p5-p95    target: 90% inside,  5% below,  5% above
  breach     when the actual price lands outside the wide band, how far past
             the band edge it went, in % of the edge price
  scored     per year and per gate state, H = 14 / 30 / 60 / 90
  charts     weekly sample (every 7th day) of ETH 30d to keep the chart legible,
             written to analysis/forecasts_full_eth.csv (all days, all H)

Neighbouring days share most of their outcome window, so the 90d figures are
far fewer independent outcomes than the day counts suggest. Market state only:
no exit, no strategy return.

Run from the repo root:  python3 -I analysis/fullhistory.py
"""
import sys, os, math, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E
import twoweek as T
import volrange as V

SYM = 'ETH'
N = 30
QS = (5, 25, 50, 75, 95)
MINPOOL = 200


def main():
    gate = T.gate_daily()
    day = E.load(f'data/{SYM}_1D.csv')
    dates = day['date']; cl = dict(zip(dates, day['close']))
    last_closed = dates[-2]
    vol = V.vol_series(day, N)
    g = {d: bool(gate(d)) for d in dates}
    out = open('analysis/forecasts_full_eth.csv', 'w')
    out.write('H,forecast_date,target_date,gate,start,p5,p25,p50,p75,p95,actual\n')
    for H in T.HORIZONS:
        oc, _ = T.outcomes(day, H)
        oc = {d: o for d, o in oc.items() if d + dt.timedelta(days=H) <= last_closed}
        valid = [d for d in dates if d in oc and d in vol]
        vd = np.array([d.toordinal() for d in valid])
        vg = np.array([g[d] for d in valid])
        s = np.array([vol[d] * math.sqrt(H) for d in valid])
        z = np.log1p(np.array([oc[d]['ret'] for d in valid]) / 100) / s
        rows = []
        for D in valid:
            k = np.searchsorted(vd, D.toordinal() - H, side='left')   # pool days d with D - d > H
            m = vg[:k] == g[D]
            if m.sum() < MINPOOL:
                continue
            q = np.percentile(z[:k][m], QS)
            s0 = vol[D] * math.sqrt(H)
            fc = {p: (math.exp(v * s0) - 1) * 100 for p, v in zip(QS, q)}
            rows.append(dict(d=D, g=g[D], fc=fc, act=oc[D]['ret']))
            c0 = cl[D]; px = lambda x: round(c0 * (1 + x / 100), 2)
            out.write(f"{H},{D},{D + dt.timedelta(days=H)},{int(g[D])},{c0}," +
                      ','.join(str(px(fc[p])) for p in QS) + f",{px(oc[D]['ret'])}\n")

        def summ(sel):
            a = np.array([r['act'] for r in sel])
            p5 = np.array([r['fc'][5] for r in sel]); p25 = np.array([r['fc'][25] for r in sel])
            p75 = np.array([r['fc'][75] for r in sel]); p95 = np.array([r['fc'][95] for r in sel])
            p50 = np.array([r['fc'][50] for r in sel])
            lo = a < p5; hi = a > p95
            # breach size, % past the band-edge PRICE
            blo = (1 + a[lo] / 100) / (1 + p5[lo] / 100) - 1
            bhi = (1 + a[hi] / 100) / (1 + p95[hi] / 100) - 1
            return dict(n=len(sel), mid=100 * np.mean((a >= p25) & (a <= p75)),
                        mlo=100 * np.mean(a < p25), mhi=100 * np.mean(a > p75),
                        wide=100 * np.mean(~lo & ~hi), wlo=100 * lo.mean(), whi=100 * hi.mean(),
                        blo_med=100 * np.median(blo) if len(blo) else 0, blo_max=100 * blo.min() if len(blo) else 0,
                        bhi_med=100 * np.median(bhi) if len(bhi) else 0, bhi_max=100 * bhi.max() if len(bhi) else 0,
                        miss=float(np.mean(np.abs(a - p50))))

        def line(s):
            return (f"n={s['n']:>4}  middle half {s['mid']:4.0f}% (below {s['mlo']:3.0f} / above {s['mhi']:3.0f})  "
                    f"wide band {s['wide']:4.0f}% (below {s['wlo']:4.1f} / above {s['whi']:4.1f})  "
                    f"breach below med {s['blo_med']:+6.1f}% worst {s['blo_max']:+6.1f}%  "
                    f"breach above med {s['bhi_med']:+6.1f}% worst {s['bhi_max']:+6.1f}%  |miss| {s['miss']:5.1f}")

        print(f'==================== ETH H={H}  forecasts {rows[0]["d"]} .. {rows[-1]["d"]}')
        print(f'  ALL        {line(summ(rows))}')
        for lab, gs in (('GATE ON ', True), ('GATE OFF', False)):
            sel = [r for r in rows if r['g'] == gs]
            if sel:
                print(f'  {lab}   {line(summ(sel))}')
        for y in sorted({r['d'].year for r in rows}):
            sel = [r for r in rows if r['d'].year == y]
            on = 100 * np.mean([r['g'] for r in sel])
            print(f'  {y} on{on:4.0f}%  {line(summ(sel))}')
        # the worst single breaches, declustered
        for side, sign, key in (('BELOW', -1, 5), ('ABOVE', 1, 95)):
            br = [r for r in rows if sign * (r['act'] - r['fc'][key]) > 0]
            br.sort(key=lambda r: -sign * ((1 + r['act'] / 100) / (1 + r['fc'][key] / 100) - 1))
            kept = []
            for r in br:
                if all(abs((r['d'] - q['d']).days) > 30 for q in kept):
                    kept.append(r)
                if len(kept) == 5:
                    break
            for r in kept:
                c0 = cl[r['d']]
                print(f"    worst {side}: {r['d']} gate {'ON ' if r['g'] else 'OFF'} start {c0:,.0f}  "
                      f"band {c0*(1+r['fc'][5]/100):,.0f}-{c0*(1+r['fc'][95]/100):,.0f}  "
                      f"actual {c0*(1+r['act']/100):,.0f}  "
                      f"({100*((1+r['act']/100)/(1+r['fc'][key]/100)-1):+.1f}% past the edge)")
        print()
    out.close()


if __name__ == '__main__':
    main()
