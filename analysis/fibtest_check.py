"""Checks on the fibtest survivors. 31 Oct 2026.

fibtest.py A1-A8 left two lenses:
  R4_BROKE  the signal low is under the starting low of the prior swing (90d, 180d, 365d)
  R3_DEEP   the signal low is 0.786-1.0 of the prior swing (90d and 365d) -- but with
            OPPOSITE signs (-22 at 90d, +13 at 365d). A lens whose direction flips with the
            lookback is not one finding; reported here only to show it.

Standing checks before believing anything:
  1. de-duplication. One market low prints on 1D, 2D, 3D, 5D and 8D and on both assets,
     so a date-anchored read can be one event counted ten times. Signals with the lens on
     are clustered into EPISODES (any signal within 14 days of the previous one, any chart,
     either asset) and scored once per episode (majority outcome) and per asset.
  2. by asset, chart, year; leave-one-year-out.
  3. collinearity with Tier 1 #4 (higher low: entry above the previous signal's entry on
     the same chart) and with price under its 200-day average (killed in the 23 Oct sweep).
  4. inside the grade, on the graded ledger.

Run from the repo root:  python3 -I analysis/fibtest_check.py
"""
import sys, os, csv, statistics, datetime as dt
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import stochdwell as S
import fibtest as F


def pct(v): return 100 * statistics.mean(v) if v else float('nan')


def extra(charts, rows):
    """Add higher-low and under-200d flags, and the bucket-end date for the ledger join."""
    day = {s: S.day_series(s) for s in ('ETH', 'BTC')}
    sma200 = {}
    for s in ('ETH', 'BTC'):
        d, pos = day[s]; sma200[s] = (E.sma(d['close'], 200), pos)
    by = defaultdict(list)
    for r in rows: by[r['chart']].append(r)
    for ch in charts:
        sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=S.GATE)
        m = {ch.b['date'][s['ei']]: s for s in sig}
        prev = None
        for s in sig:
            s['_prev'] = prev; prev = s['entry']
        for r in by[ch.name]:
            s = m.get(r['date'])
            r['hl'] = bool(s and s['_prev'] is not None and s['entry'] > s['_prev'])
            ei = [i for i, x in enumerate(ch.b['date']) if x == r['date']][0]
            r['end'] = S.bucket_end(ch.b['date'], ei)
            sm, pos = sma200[ch.sym]
            j = pos.get(r['end'])
            r['u200'] = bool(j is not None and sm[j] is not None and day[ch.sym][0]['close'][j] < sm[j])


def episodes(rs):
    rs = sorted(rs, key=lambda r: r['date'])
    eps = []
    for r in rs:
        if eps and (r['date'] - eps[-1][-1]['date']).days <= 14: eps[-1].append(r)
        else: eps.append([r])
    return eps


def table(rows, key, kf, label):
    g = defaultdict(lambda: ([], []))
    for r in rows:
        if r[key] is None: continue
        g[kf(r)][0 if r[key] else 1].append(r)
    print(f'    {label:<10}{"n with":>7}{"SURV":>6}{"LIQ":>5}{"n w/o":>7}{"SURV":>6}{"LIQ":>5}{"diff":>6}')
    for k in sorted(g, key=str):
        w, wo = g[k]
        if not w or not wo: continue
        print(f'    {str(k):<10}{len(w):>7}{pct([r["surv"] for r in w]):>6.0f}{pct([r["liq"] for r in w]):>5.0f}'
              f'{len(wo):>7}{pct([r["surv"] for r in wo]):>6.0f}{pct([r["liq"] for r in wo]):>5.0f}'
              f'{pct([r["surv"] for r in w]) - pct([r["surv"] for r in wo]):>+6.0f}')


def main():
    charts = S.load_charts(S.SYS_TF)
    rows = F.rows_for(charts)
    extra(charts, rows)
    for key in ('R4_BROKE@90', 'R4_BROKE@180', 'R4_BROKE@365', 'R3_DEEP@90', 'R3_DEEP@365'):
        v = [r for r in rows if r[key] is not None]
        w = [r for r in v if r[key]]; wo = [r for r in v if not r[key]]
        print('=' * 90); print(key); print('=' * 90)
        print(f'  signals with: {len(w)}  SURV {pct([r["surv"] for r in w]):.0f}%  LIQ {pct([r["liq"] for r in w]):.0f}%'
              f'   without: {len(wo)}  SURV {pct([r["surv"] for r in wo]):.0f}%  LIQ {pct([r["liq"] for r in wo]):.0f}%')
        ew, ewo = episodes(w), episodes(wo)
        maj = lambda ep, f: statistics.mean(x[f] for x in ep) >= 0.5
        print(f'  EPISODES (14-day clusters, any chart, both assets): with {len(ew)}, SURV '
              f'{pct([maj(e, "surv") for e in ew]):.0f}%, LIQ {pct([maj(e, "liq") for e in ew]):.0f}%'
              f'   without {len(ewo)}, SURV {pct([maj(e, "surv") for e in ewo]):.0f}%, LIQ {pct([maj(e, "liq") for e in ewo]):.0f}%')
        for a in ('ETH', 'BTC'):
            ea = episodes([r for r in w if r['asset'] == a]); eo = episodes([r for r in wo if r['asset'] == a])
            print(f'    {a} episodes: with {len(ea)} SURV {pct([maj(e, "surv") for e in ea]):.0f}%'
                  f'  without {len(eo)} SURV {pct([maj(e, "surv") for e in eo]):.0f}%')
        print('  episode list (start date, signals, charts, share SURV10):')
        for e in ew:
            chs = sorted({x['chart'] for x in e})
            print(f'    {e[0]["date"]}  {len(e):>2}  {pct([x["surv"] for x in e]):>4.0f}%  {", ".join(chs)}')
        table(v, key, lambda r: r['asset'], 'asset')
        table(v, key, lambda r: r['chart'], 'chart')
        table(v, key, lambda r: r['date'].year, 'year')
        yrs = sorted({r['date'].year for r in w})
        loo = []
        for y in yrs:
            ww = [r['surv'] for r in w if r['date'].year != y]; oo = [r['surv'] for r in wo if r['date'].year != y]
            loo.append((y, pct(ww) - pct(oo)))
        print('  leave-one-year-out lift: ' + '  '.join(f'{y}:{d:+.0f}' for y, d in loo))
        print(f'  overlap: with higher low (Tier 1 #4) {pct([r["hl"] for r in w]):.0f}% vs {pct([r["hl"] for r in wo]):.0f}%;'
              f' under 200d average {pct([r["u200"] for r in w]):.0f}% vs {pct([r["u200"] for r in wo]):.0f}%')
        print(f'  stratified by under-200d: {S.strat_lift(v, key, lambda r: r["u200"]):+.0f};'
              f' by higher low: {S.strat_lift(v, key, lambda r: r["hl"]):+.0f}')
        led = list(csv.DictReader(open('datasets/ledger.csv')))
        idx = {(r['chart'], r['end'].isoformat()): r for r in v if r['end']}
        idx.update({(r['chart'], r['date'].isoformat()): r for r in v})
        j = [dict(idx[(L['chart'], L['entry'])], grade=L['grade']) for L in led if (L['chart'], L['entry']) in idx]
        print(f'  inside the grade (graded ledger, {len(j)} matched):')
        table(j, key, lambda r: r['grade'], 'grade')
        print()


if __name__ == '__main__':
    main()
