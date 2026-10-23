"""CTZB on the ETH/BTC ratio — does the indicator say anything about ETH vs BTC?

DECLARED BEFORE RUNNING (23 Oct 2026). Jared: "just turning over stones".
Candidate list fixed here; failures reported beside hits.

  series     ETH/BTC = ETH close / BTC close (Coinbase daily, data/*_1D.csv),
             2016-05-18 on. Multi-day bars bucket days inside each calendar
             year (the TradingView rule fetch.py uses); bar close = ratio on
             the bucket's last day; bar high/low = max/min daily ratio close.
             Jared's chart is the MARKET-CAP ratio (CRYPTOCAP:ETH/CRYPTOCAP:BTC),
             = this ratio x a slowly drifting supply ratio (5.7-6.2). Checked on
             his 3D export: 107 of 110 signals on the same dates, and the
             engine reproduces his CT RSI column exactly.
  charts     1D, 2D, 3D, 5D, 8D
  signals    engine.signals() unchanged: CT RSI pivot low, 3 bars either side,
             entry = close of the confirmation bar, timed at the day it closes
  gates      G0 none (primary: the ratio is a relative trade)
             G1 the usual BTC 2D control-zone gate (BTC bull regime)
             G2 the same control-zone rule run on the ratio's own 2D chart
  tags       all, bucket A, B, C, D, diamond, filled diamond, hollow diamond,
             prime dot, diamond + prime, CT > 5 above the Signal line,
             CT above the Signal line + prime
  outcome    ON THE RATIO, from the entry close, daily closes:
             primary  ratio higher after 60 days (ETH beat BTC)
             also     reach +10% / +20% within 60d, median 60d ratio change,
                      median worst close-to-close drawdown in 60d, median days
                      closed below entry; 30d and 90d for "all"
  baseline   every day on that chart's span (same gate state) with a full
             window: what a random day did. A tag is judged against this.
  guards     per chart; per year for "all" and any tag that clears +10 pts on
             3+ charts; tags with n < 15 shown but not judged. Added after
             the first run, before reading it as a result: for those tags,
             every completed bar with CT in the same bucket range, to tell
             the pivot apart from plain oversold (PRETRADE guard 4)
  secondary  ETH in USD 60 days after a ratio signal (G0, all tags) vs the
             all-days ETH-USD baseline: does a ratio low help an ETH long?

Drawdowns use daily ratio CLOSES, since true ratio wicks are not derivable
from separate ETH and BTC candles. Entry quality only: no exit, no strategy
return. Signals computed, never fills.

Run from the repo root:  python3 -I analysis/ethbtc.py
"""
import sys, os, math, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R

TFS = [('1D', 1), ('2D', 2), ('3D', 3), ('5D', 5), ('8D', 8)]
HS = (30, 60, 90)
OUT = 'analysis/ethbtc_bars'


def bucket(d, n):
    return (d.year, (d.timetuple().tm_yday - 1) // n)


def build():
    e = E.load('data/ETH_1D.csv'); b = E.load('data/BTC_1D.csv')
    bc = dict(zip(b['date'], b['close']))
    days = [(d, c / bc[d]) for d, c in zip(e['date'][:-1], e['close'][:-1]) if d in bc]  # drop forming bar
    os.makedirs(OUT, exist_ok=True)
    for tf, n in TFS:
        bars = {}
        for d, r in days:
            k = bucket(d, n)
            if k not in bars:
                bars[k] = [d, r, r, r, r]
            else:
                bars[k][2] = max(bars[k][2], r); bars[k][3] = min(bars[k][3], r); bars[k][4] = r
        with open(f'{OUT}/ETHBTC_{tf}.csv', 'w') as f:
            f.write('time,open,high,low,close\n')
            for d, o, h, l, c in bars.values():
                t = int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())
                f.write(f'{t},{o},{h},{l},{c}\n')
    return days


def bucket_end(dates, j):
    return dates[j + 1] - dt.timedelta(days=1) if j + 1 < len(dates) else None


def fwd(series, pos, d0, H):
    i = pos[d0]; end = d0 + dt.timedelta(days=H)
    w = [k for k in range(i + 1, len(series)) if series[k][0] <= end]
    if not w or series[w[-1]][0] < end:
        return None
    c0 = series[i][1]; cs = [series[k][1] for k in w]
    return dict(ret=(cs[-1] / c0 - 1) * 100, up=(max(cs) / c0 - 1) * 100, dd=(min(cs) / c0 - 1) * 100,
                under=sum(c < c0 for c in cs))


TAGS = {
    'all': lambda s, g: True,
    'A': lambda s, g: s['bk'] == 'A', 'B': lambda s, g: s['bk'] == 'B',
    'C': lambda s, g: s['bk'] == 'C', 'D': lambda s, g: s['bk'] == 'D',
    'diamond': lambda s, g: s['dis'], 'filled dmd': lambda s, g: s['dis'] and s['strong'],
    'hollow dmd': lambda s, g: s['dis'] and not s['strong'], 'prime': lambda s, g: s['prime'],
    'dmd+prime': lambda s, g: s['dis'] and s['prime'],
    'gap>5': lambda s, g: g is not None and g > 5,
    'above+prime': lambda s, g: g is not None and g > 0 and s['prime'],
}


def main():
    days = build()
    pos = {d: i for i, d in enumerate(d for d, _ in days)}
    eth = E.load('data/ETH_1D.csv'); epos = {d: i for i, d in enumerate(eth['date'])}
    eser = list(zip(eth['date'][:-1], eth['close'][:-1]))
    gb = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    gr = R.rsi_regime(f'{OUT}/ETHBTC_2D.csv', 8, 13, 60, 41)
    gates = {'G0 none': lambda d: True, 'G1 BTC gate': gb, 'G2 ratio gate': gr}
    allfw = {H: {d: fwd(days, pos, d, H) for d, _ in days} for H in HS}
    efw = {d: fwd(eser, epos, d, 60) for d, _ in eser}
    summary = {}
    for gname, gate in gates.items():
        print(f'#################### {gname}')
        for tf, n in TFS:
            sig, b = E.signals(f'{OUT}/ETHBTC_{tf}.csv', regime=gate)
            ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
            rows = []
            for s in sig:
                d0 = bucket_end(b['date'], s['ei'])
                if d0 is None or d0 not in pos:
                    continue
                ei = s['ei']
                gap = ct[ei] - em[ei] if ct[ei] is not None and em[ei] is not None else None
                rows.append(dict(d=d0, s=s, gap=gap, f={H: allfw[H][d0] for H in HS}, e=efw.get(d0)))
            span0 = rows[0]['d'] if rows else None
            base = [d for d, _ in days if span0 and d >= span0 and gate(d) and allfw[60][d]]
            bf = [allfw[60][d] for d in base]
            bwin = 100 * np.mean([x['ret'] > 0 for x in bf]); b10 = 100 * np.mean([x['up'] >= 10 for x in bf])
            print(f'== ETH/BTC {tf}: {len(rows)} signals; all-days baseline (n={len(bf)}): ETH beat BTC at 60d {bwin:.0f}%, '
                  f'+10% {b10:.0f}%, +20% {100*np.mean([x["up"]>=20 for x in bf]):.0f}%, med ret {np.median([x["ret"] for x in bf]):+.1f}%')
            print(f'   {"tag":<12}{"n":>4}{"ETH>BTC 60d":>12}{"edge":>6}{"+10%":>6}{"edge":>6}{"+20%":>6}'
                  f'{"med ret":>9}{"med DD":>8}{"days under":>11}')
            for tname, fn in TAGS.items():
                sel = [r for r in rows if fn(r['s'], r['gap']) and r['f'][60]]
                if not sel:
                    print(f'   {tname:<12}{0:>4}'); continue
                f6 = [r['f'][60] for r in sel]
                win = 100 * np.mean([x['ret'] > 0 for x in f6]); h10 = 100 * np.mean([x['up'] >= 10 for x in f6])
                flag = '' if len(sel) >= 15 else '  (n<15, not judged)'
                print(f'   {tname:<12}{len(sel):>4}{win:>11.0f}%{win-bwin:>+6.0f}{h10:>5.0f}%{h10-b10:>+6.0f}'
                      f'{100*np.mean([x["up"]>=20 for x in f6]):>5.0f}%{np.median([x["ret"] for x in f6]):>+8.1f}%'
                      f'{np.median([x["dd"] for x in f6]):>+7.1f}%{np.median([x["under"] for x in f6]):>11.0f}{flag}')
                summary.setdefault((gname, tname), []).append((tf, len(sel), win - bwin, h10 - b10))
            al = [r for r in rows if r['f'][60]]
            for H in (30, 90):
                fh = [r['f'][H] for r in rows if r['f'][H]]
                bh = [allfw[H][d] for d in base if allfw[H][d]]
                if fh and bh:
                    print(f'   all {H}d: ETH>BTC {100*np.mean([x["ret"]>0 for x in fh]):.0f}% vs base '
                          f'{100*np.mean([x["ret"]>0 for x in bh]):.0f}%, med ret {np.median([x["ret"] for x in fh]):+.1f}% vs '
                          f'{np.median([x["ret"] for x in bh]):+.1f}%')
            yrs = sorted({r['d'].year for r in al}); txt = []; pos_y = 0; tested = 0
            for y in yrs:
                sel = [r['f'][60] for r in al if r['d'].year == y]
                by = [allfw[60][d] for d in base if d.year == y]
                if len(sel) < 3 or not by:
                    continue
                a_ = 100 * np.mean([x['ret'] > 0 for x in sel]); b_ = 100 * np.mean([x['ret'] > 0 for x in by])
                tested += 1; pos_y += a_ > b_
                txt.append(f'{y}:{a_:.0f}/{b_:.0f}')
            print(f'   all by year (ETH>BTC 60d, signals/base): ' + '  '.join(txt) + f'   signals ahead in {pos_y} of {tested}')
            if gname == 'G0 none':
                ee = [r['e'] for r in rows if r['e']]
                eb = [efw[d] for d, _ in eser if span0 and d >= span0 and efw.get(d)]
                print(f'   secondary, ETH-USD 60d after a ratio signal: up {100*np.mean([x["ret"]>0 for x in ee]):.0f}% '
                      f'(base {100*np.mean([x["ret"]>0 for x in eb]):.0f}%), +20% {100*np.mean([x["up"]>=20 for x in ee]):.0f}% '
                      f'(base {100*np.mean([x["up"]>=20 for x in eb]):.0f}%), n={len(ee)}')
        print()
    # guard for any tag clearing +10 on 3+ charts (G0): per year, and against
    # every completed bar of that chart with CT in the same bucket range
    # (collinearity: is it the pivot, or just "the ratio is oversold"?)
    rng = {'A': (-1, 40), 'B': (40, 55), 'C': (55, 65), 'D': (65, 101)}
    for tname in ('A', 'B'):
        print(f'#################### GUARDS FOR BUCKET {tname}, G0 (ETH beat BTC at 60d)')
        lo, hi = rng[tname]
        for tf, n in TFS:
            sig, b = E.signals(f'{OUT}/ETHBTC_{tf}.csv', regime=lambda d: True)
            ct = E.rsi(b['close'], 14)
            sel = []
            for s_ in sig:
                d0 = bucket_end(b['date'], s_['ei'])
                if d0 and d0 in pos and s_['bk'] == tname and allfw[60][d0]:
                    sel.append((d0, allfw[60][d0]))
            bars = []
            for j in range(len(b['date'])):
                d0 = bucket_end(b['date'], j)
                if d0 and d0 in pos and ct[j] is not None and lo <= ct[j] < hi and allfw[60][d0]:
                    bars.append((d0, allfw[60][d0]))
            w = lambda L: 100 * np.mean([x['ret'] > 0 for _, x in L]) if L else float('nan')
            yrs = sorted({d.year for d, _ in sel}); ahead = tested = 0; txt = []
            for y in yrs:
                a_ = [x for x in sel if x[0].year == y]; b_ = [x for x in allfw[60].items() if x[0].year == y and x[1]]
                if len(a_) < 3:
                    continue
                tested += 1; ahead += w(a_) > w(b_); txt.append(f'{y}:{w(a_):.0f}/{w(b_):.0f}')
            print(f'  {tf}: signals {w(sel):.0f}% (n={len(sel)})  every bar with CT in {tname} range {w(bars):.0f}% (n={len(bars)})  '
                  f'by year vs all days: ' + ' '.join(txt) + f'  ahead {ahead}/{tested}')
    print('#################### TAGS CLEARING +10 PTS (ETH beat BTC at 60d) ON 3+ CHARTS WITH n>=15')
    any_ = False
    for (gname, tname), lst in summary.items():
        ok = [x for x in lst if x[1] >= 15 and x[2] >= 10]
        if len(ok) >= 3:
            any_ = True
            print(f'  {gname:<14}{tname:<12}' + '  '.join(f'{tf} n={n} {d:+.0f}' for tf, n, d, _ in lst))
    if not any_:
        print('  none')


if __name__ == '__main__':
    main()
