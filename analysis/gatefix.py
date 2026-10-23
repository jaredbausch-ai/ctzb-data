"""The regime gate's cycle-top blind spot — can a live overlay switch it off sooner?

DECLARED BEFORE RUNNING (23 Oct 2026). Free rein from Jared to test what
improves odds; this is the first pick because the largest losses on record sit
in it: the gate stayed ON through the 2018 crash (episode 2016-06 -> 2018-07),
the Nov 2021 top (2021-08 -> 2022-01) and late 2025 (2023-01 -> 2025-12).

  base       every signal on ETH 1D/2D/3D/5D and BTC 1D/2D/3D/5D under the
             current gate R.rsi_regime(BTC_2D, 8, 13, 60, 41), engine
             convention unchanged. Entry = confirmation close, timed at the
             day that bar closes (d0). Outcomes on daily candles.
  overlays   each is an EXTRA condition, evaluated with BTC data knowable at
             d0, that must also hold or the signal is removed. Parameters
             fixed here from first principles, not fitted, and not tuned after:
             O1  BTC daily close above its 200-day simple moving average
             O2  BTC 2D CT RSI closed >= 60 at least once in the last 30
                 completed 2D bars (~60 days): the bull zone is still being
                 revisited. Our dwell study: the longest neutral stay inside a
                 bull phase was 46 days
             O3  BTC daily close no more than 25% below its highest daily
                 close of the last 365 days
             O4  a faster bear exit: the same gate rule with 8 bars below 41
                 instead of 13 (signal kept only if that gate is on at the
                 trough date, engine convention)
  outcome    reach +20% within 60 days (primary, as in PRETRADE.md);
             also median 60d return, median 60d drawdown from entry,
             dead (-30% before +5%)
  judged on  the signals each overlay REMOVES vs the ones it KEEPS:
             per chart, per year, and in vs out of the three blind-spot
             episodes' final 180 days
  ACCEPT     an overlay is worth adopting only if ALL hold:
             (a) removed signals reach +20% at least 10 points less often
                 than kept ones, pooled
             (b) kept rate >= base rate on at least 6 of the 8 charts
             (c) it removes no more than 25% of signals
             (d) removed < kept in a majority of the years it removes from
             Otherwise reported as failed.
  note       charts are not independent (ETH and BTC share dates; 1D/2D/3D/5D
             of one asset share moves) so pooled n overstates the sample.

Entry quality only: no exit, no strategy return. Signals computed, never fills.

Run from the repo root:  python3 -I analysis/gatefix.py
"""
import sys, os, bisect, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end, measure, dead

CHARTS = ['ETH_1D', 'ETH_2D', 'ETH_3D', 'ETH_5D', 'BTC_1D', 'BTC_2D', 'BTC_3D', 'BTC_5D']
EPISODE_ENDS = [dt.date(2018, 7, 2), dt.date(2022, 1, 25), dt.date(2025, 12, 3)]


def btc_overlays():
    b = E.load('data/BTC_1D.csv')
    D, C = b['date'], b['close']
    sma = E.sma(C, 200)
    c = {d: (C[i], sma[i], max(C[max(0, i - 364):i + 1])) for i, d in enumerate(D)}
    b2 = E.load('data/BTC_2D.csv')
    ct2 = E.rsi(b2['close'], 14)
    ends = [(b2['date'][j + 1] - dt.timedelta(days=1)) for j in range(len(b2['date']) - 1)]   # bar j closes on ends[j]

    def o2(d):
        k = bisect.bisect_right(ends, d) - 1        # last 2D bar closed by end of d
        if k < 0:
            return False
        w = [x for x in ct2[max(0, k - 29):k + 1] if x is not None]
        return any(x >= 60 for x in w)

    g4 = R.rsi_regime('data/BTC_2D.csv', 8, 8, 60, 41)
    return {
        'O1 BTC > 200d SMA': lambda d0, td: c[d0][1] is not None and c[d0][0] > c[d0][1],
        'O2 bull zone seen in 60d': lambda d0, td: o2(d0),
        'O3 BTC < 25% off 1y high': lambda d0, td: c[d0][0] >= 0.75 * c[d0][2],
        'O4 faster exit (8 bars <41)': lambda d0, td: g4(td),
    }


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    ovs = btc_overlays()
    rows = []
    for ch in CHARTS:
        sym = ch.split('_')[0]
        day = E.load(f'data/{sym}_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}
        last_closed = day['date'][-2]
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        for s in sig:
            d0 = bucket_end(b['date'], s['ei'])
            if d0 is None or d0 > last_closed or d0 not in pos:
                continue
            m = measure(day, pos, d0, s['entry'], 60)
            if not m:
                continue
            r = dict(ch=ch, d=d0, y=d0.year, m=m, dead=dead(day, pos, d0, s['entry']) is not None,
                     late=any(0 <= (e - d0).days <= 180 for e in EPISODE_ENDS))
            for name, f in ovs.items():
                r[name] = bool(f(d0, s['date']))
            rows.append(r)

    def rate(sel):
        return 100 * np.mean([r['m']['up'] >= 20 for r in sel]) if sel else float('nan')

    def line(sel):
        if not sel:
            return f'{"n=   0":<10}'
        return (f'n={len(sel):>4}  +20% {rate(sel):3.0f}%  med ret {np.median([r["m"]["ret"] for r in sel]):+6.1f}%  '
                f'med DD {np.median([r["m"]["dd"] for r in sel]):+6.1f}%  dead {sum(r["dead"] for r in sel):>2}')

    print(f'BASE (current gate), 8 charts pooled: {line(rows)}')
    late = [r for r in rows if r['late']]
    print(f'  of which in the last 180 days of the three blind-spot episodes: {line(late)}')
    print(f'  everything else:                                             {line([r for r in rows if not r["late"]])}')
    verdicts = []
    for name in ovs:
        keep = [r for r in rows if r[name]]; rem = [r for r in rows if not r[name]]
        print(f'\n==================== {name}')
        print(f'  KEPT     {line(keep)}')
        print(f'  REMOVED  {line(rem)}   ({100*len(rem)/len(rows):.0f}% of signals)')
        print(f'  removed from the blind-spot tails: {sum(1 for r in rem if r["late"])} of {len(late)} there; '
              f'from everywhere else: {sum(1 for r in rem if not r["late"])} of {len(rows)-len(late)}')
        better = 0; ctxt = []
        for ch in CHARTS:
            a = [r for r in rows if r['ch'] == ch]; k = [r for r in keep if r['ch'] == ch]
            better += rate(k) >= rate(a)
            ctxt.append(f'{ch.replace("_"," ")} {rate(a):.0f}->{rate(k):.0f}')
        print('  per chart, base -> kept: ' + '  '.join(ctxt) + f'   kept >= base on {better} of 8')
        ytxt = []; yw = yt = 0
        for y in sorted({r['y'] for r in rem}):
            ry = [r for r in rem if r['y'] == y]; ky = [r for r in keep if r['y'] == y]
            if not ky:
                ytxt.append(f'{y}: removed {rate(ry):.0f}% (n={len(ry)}) / kept none')
                continue
            yt += 1; yw += rate(ry) < rate(ky)
            ytxt.append(f'{y}: {rate(ry):.0f}%/{rate(ky):.0f}% (n={len(ry)})')
        print('  by year, removed/kept: ' + '  '.join(ytxt) + f'   removed worse in {yw} of {yt}')
        a = rate(rem) <= rate(keep) - 10; b_ = better >= 6; c = len(rem) <= 0.25 * len(rows); d = yt > 0 and yw > yt / 2
        v = a and b_ and c and d
        verdicts.append((name, a, b_, c, d, v))
    print('\nACCEPTANCE (declared): (a) removed >=10 pts worse  (b) kept>=base on 6/8 charts  (c) removes <=25%  (d) worse in most years')
    for name, a, b_, c, d, v in verdicts:
        print(f'  {name:<30} a {a!s:<5} b {b_!s:<5} c {c!s:<5} d {d!s:<5} -> {"ADOPT" if v else "REJECT"}')


if __name__ == '__main__':
    main()
