"""Cross-asset confluence: does a BTC 3D signal improve an ETH 1D / ETH 2D signal?

DECLARED BEFORE RUNNING (22 Oct 2026). Asked by Jared. Candidate list fixed here;
nothing is added after seeing results.

  trades     every regime-gated ETH 1D and ETH 2D signal, entry = close of the
             confirmation bar, timed at the day that bar closes (last day of
             its bucket). Gate R.rsi_regime(BTC_2D, 8, 13, 60, 41).
  condition  a regime-gated BTC 3D signal had ALREADY confirmed (its bar had
             closed) within W days before the ETH entry, same day included.
             Backward only: knowable at the ETH entry. W = 10 primary (the
             AGREE_DAYS used everywhere else); W = 5 and 20 sensitivity.
  outcome    reach +20% within 60 days (the standard used in PRETRADE.md),
             plus median 60d return, median 60d drawdown from entry, and
             median days closed under the entry price within 60 days.
             Daily candles.
  guards     1. per chart (ETH 1D and ETH 2D separately, never pooled)
             2. per year
             3. collinearity: ETH's own backward agreement (other ETH charts
                1D/2D/3D/5D/8D confirmed within 10 days) is the validated
                confluence filter. Report the BTC 3D effect inside ETH-agreement
                0-1 and 2+ separately; if it vanishes there, it is the same
                feature
             4. ETH and BTC are one sample for anything date-anchored; this is
                date-anchored, so the per-year split is the real test

Entry quality only: no exit, no strategy return. Signals are computed, never fills.

Run from the repo root:  python3 -I analysis/xconf.py
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end, measure

WINDOWS = (10, 5, 20)
ETH_REF = ['1D', '2D', '3D', '5D', '8D']


def confirmed(chart, gate):
    sig, b = E.signals(f'data/{chart}.csv', regime=gate)
    out = []
    for s in sig:
        d0 = bucket_end(b['date'], s['ei'])
        if d0 is not None:
            out.append((d0, s))
    return out


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    day = E.load('data/ETH_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}
    last_closed = day['date'][-2]
    btc3 = [d for d, _ in confirmed('BTC_3D', gate)]
    ethref = {tf: [d for d, _ in confirmed(f'ETH_{tf}', gate)] for tf in ETH_REF}
    for tf in ('1D', '2D'):
        rows = []
        for d0, s in confirmed(f'ETH_{tf}', gate):
            if d0 > last_closed:
                continue
            m = measure(day, pos, d0, s['entry'], 60)
            if not m:
                continue
            cf = sum(1 for t, ds in ethref.items() if t != tf and any(0 <= (d0 - x).days <= 10 for x in ds))
            r = dict(d=d0, y=d0.year, m=m, cf=cf, s=s)
            for W in WINDOWS:
                r[W] = any(0 <= (d0 - x).days <= W for x in btc3)
            rows.append(r)

        def st(sel):
            if not sel:
                return '   n=  0'
            up = np.array([r['m']['up'] for r in sel])
            return (f'n={len(sel):>3}  +20% {100*np.mean(up >= 20):3.0f}%  med ret {np.median([r["m"]["ret"] for r in sel]):+6.1f}%  '
                    f'med DD {np.median([r["m"]["dd"] for r in sel]):+6.1f}%  days under {np.median([r["m"]["under"] for r in sel]):4.0f}')

        print(f'==================== ETH {tf}  ({len(rows)} gated signals with a full 60d window)')
        print(f'  baseline                      {st(rows)}')
        for W in WINDOWS:
            tag = ' <- primary' if W == 10 else ''
            print(f'  BTC 3D within {W:>2}d before    {st([r for r in rows if r[W]])}{tag}')
            print(f'  no BTC 3D within {W:>2}d         {st([r for r in rows if not r[W]])}')
        print('  by year, W=10 (with / without, +20% in 60d)')
        for y in sorted({r['y'] for r in rows}):
            a = [r for r in rows if r['y'] == y and r[10]]; b_ = [r for r in rows if r['y'] == y and not r[10]]
            f = lambda sel: f'{100*np.mean([r["m"]["up"] >= 20 for r in sel]):3.0f}% (n={len(sel):>2})' if sel else '   - (n= 0)'
            diff = (100 * np.mean([r['m']['up'] >= 20 for r in a]) - 100 * np.mean([r['m']['up'] >= 20 for r in b_])) if a and b_ else None
            print(f'    {y}  with {f(a)}  without {f(b_)}  ' + (f'diff {diff:+4.0f}' if diff is not None else 'diff  n/a'))
        print('  collinearity, W=10, inside ETH own agreement')
        for lab, sel in (('ETH agree 0-1', [r for r in rows if r['cf'] <= 1]), ('ETH agree 2+ ', [r for r in rows if r['cf'] >= 2])):
            print(f'    {lab}  with BTC 3D    {st([r for r in sel if r[10]])}')
            print(f'    {lab}  without        {st([r for r in sel if not r[10]])}')
        print('  max drawdown from entry (worst daily low), W=10, added 22 Oct after the declared run')
        for H in (30, 60, 90):
            for lab, sel in (('with BTC 3D', [r for r in rows if r[10]]), ('without   ', [r for r in rows if not r[10]])):
                x = [measure(day, pos, r['d'], r['s']['entry'], H) for r in sel]
                x = [v for v in x if v]
                dd = np.array([v['dd'] for v in x]); pk = np.array([v['ddpk'] for v in x])
                print(f'    {H}d {lab} n={len(dd):>3}  median {np.median(dd):+6.1f}%  25th pct {np.percentile(dd,25):+6.1f}%  '
                      f'worst {dd.min():+6.1f}%  touch -10% {100*np.mean(dd<=-10):3.0f}%  -20% {100*np.mean(dd<=-20):3.0f}%  '
                      f'-30% {100*np.mean(dd<=-30):3.0f}%  | before the high: median {np.median(pk):+6.1f}%  worst {pk.min():+6.1f}%')
        print('  worst 60d drawdowns, with BTC 3D (W=10)')
        sel = sorted([r for r in rows if r[10]], key=lambda r: r['m']['dd'])[:6]
        for r in sel:
            print(f"    {r['d']}  entry {r['s']['entry']:,.0f}  worst {r['m']['dd']:+.1f}% on day {r['m']['ddday']}  "
                  f"60d high {r['m']['up']:+.1f}%  60d ret {r['m']['ret']:+.1f}%")
        both = sum(1 for r in rows if r[10] and r['cf'] >= 2); a10 = sum(1 for r in rows if r[10]); c2 = sum(1 for r in rows if r['cf'] >= 2)
        print(f'    overlap: BTC 3D {a10}, ETH agree 2+ {c2}, both {both}, expected by chance {a10*c2/len(rows):.1f}')
        print()


if __name__ == '__main__':
    main()
