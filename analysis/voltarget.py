"""Diminishing returns: does a volatility-scaled success target change the odds?
Jared's point, 26 Oct 2026: the market matures, moves shrink, so a fixed +20%
target is a harder bar every cycle, especially in the last bull run.

DECLARED BEFORE RUNNING. Same universe as analysis/grokpack.py (regime-on
signals, gate R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41), confirmation
entry, 60-day window on daily candles, all 10 ETH/BTC charts 1D-8D).

SCALED TARGET. At each entry, sigma = standard deviation of daily log returns
over the 365 days before the entry date (known at entry). Target =
20% x sigma / sigma_ref, where sigma_ref is that asset's median sigma across
its 2016-21 signal entries. So the target averages +20% in the old market and
shrinks as the market calms. Sensitivity: the same with a 180-day sigma.
Win (scaled) = the 60-day max daily high reaches the scaled target.

QUESTIONS (descriptive; this is a measurement change, not a filter):
 Q1 base rates by asset and period, by year, by chart: fixed +20% vs scaled.
    And the size of the scaled target by year.
 Q2 the random-day check: every regime-on day vs signals, scaled target.
    (Under the fixed target, signals were no better than a random regime-on
    day.)
 Q3 the filters: lift (with minus without) in each period under fixed and
    scaled, and whether each still passes the both-periods rule (lift > 0 in
    2016-21 and 2022-26, each group n >= 8). Filters, declared:
      CT > Signal by 5+; CT > Signal + prime; CT > Signal + diamond;
      higher entry than previous signal; 2+ other same-asset charts before;
      8D CT rising; ETH 1D/2D with a BTC 3D signal confirmed 0-10 days before.
 Q4 the last bull run: 2023, 2024, 2025, 2026 separately, fixed vs scaled.
Nothing is adopted from this run. The fixed +20% stays the headline
definition unless Jared decides otherwise.
ENTRY QUALITY ONLY. Signals are computed, never fills.
  python3 -I analysis/voltarget.py -> analysis/RESULTS_voltarget.txt, voltarget.json
"""
import sys, os, json, math, bisect, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import grokpack as GP
from tagstats import measure

ASSETS = GP.ASSETS; TFS = GP.TFS; SPLIT = GP.SPLIT
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
DAY = {a: E.load(f'data/{a}_1D.csv') for a in ASSETS}
POS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in ASSETS}


def sigma_at(a, d, win):
    i = POS[a].get(d)
    if i is None or i - win < 1: return None
    c = DAY[a]['close']
    r = [math.log(c[k] / c[k - 1]) for k in range(i - win + 1, i + 1)]
    return st.pstdev(r)


def rate(G, k):
    return (100 * sum(r[k] for r in G) / len(G), len(G)) if G else (None, 0)


def fr(v):
    return '   -    ' if v[0] is None else f'{v[0]:3.0f}% ({v[1]:>3})'


def main():
    rows, allsig = GP.build()
    for r in rows:
        r['s365'] = sigma_at(r['a'], r['d0'], 365); r['s180'] = sigma_at(r['a'], r['d0'], 180)
    rows = [r for r in rows if r['s365'] and r['s180']]
    ref = {}
    for a in ASSETS:
        for w in ('s365', 's180'):
            ref[(a, w)] = st.median(r[w] for r in rows if r['a'] == a and r['per'] == '16-21')
    for r in rows:
        r['T'] = 20 * r['s365'] / ref[(r['a'], 's365')]
        r['T180'] = 20 * r['s180'] / ref[(r['a'], 's180')]
        r['wS'] = r['m']['up'] >= r['T']; r['wS180'] = r['m']['up'] >= r['T180']
    # BTC 3D before, for ETH 1D/2D
    b3 = [x['d0'] for x in allsig[('BTC', '3D')]]
    for r in rows:
        r['btc3'] = r['a'] == 'ETH' and r['tf'] in ('1D', '2D') and any(0 <= (r['d0'] - d).days <= 10 for d in b3)
    OUT = {}
    P('VOL-SCALED TARGET -- declared, run', dt.date.today(), '| entry quality only, signals not fills')
    P(f'  sigma_ref (2016-21 median daily sigma, 365d): ETH {100 * ref[("ETH", "s365")]:.2f}%  BTC {100 * ref[("BTC", "s365")]:.2f}%\n')

    P('Q1  base rate, all regime-on signals: fixed +20% | scaled (365d) | scaled (180d)')
    for a in ASSETS:
        for p in ('16-21', '22-26'):
            G = [r for r in rows if r['a'] == a and r['per'] == p]
            P(f'  {a} {p}: fixed {fr(rate(G, "win"))} | scaled {fr(rate(G, "wS"))} | scaled180 {fr(rate(G, "wS180"))}'
              f'   median target {st.median(r["T"] for r in G):4.1f}%')
    P('  by year (both assets): fixed | scaled | median scaled target ETH / BTC')
    years = sorted({r['yr'] for r in rows})
    OUT['years'] = {}
    for y in years:
        G = [r for r in rows if r['yr'] == y]
        te = [r['T'] for r in G if r['a'] == 'ETH']; tb = [r['T'] for r in G if r['a'] == 'BTC']
        P(f'    {y}: fixed {fr(rate(G, "win"))} | scaled {fr(rate(G, "wS"))} | target ETH {st.median(te) if te else float("nan"):4.1f}%  BTC {st.median(tb) if tb else float("nan"):4.1f}%')
        OUT['years'][y] = dict(fixed=rate(G, 'win'), scaled=rate(G, 'wS'), tE=st.median(te) if te else None, tB=st.median(tb) if tb else None)
    P('  by chart: fixed 16-21 / 22-26 | scaled 16-21 / 22-26')
    for a in ASSETS:
        for tf in TFS:
            G = [r for r in rows if r['ch'] == f'{a} {tf}']
            o = [rate([r for r in G if r['per'] == p], k) for k in ('win', 'wS') for p in ('16-21', '22-26')]
            P(f'    {a} {tf}: fixed {fr(o[0])} / {fr(o[1])} | scaled {fr(o[2])} / {fr(o[3])}')

    P('\nQ2  signals vs every regime-on day, scaled (365d) target')
    for a in ASSETS:
        day = DAY[a]; days = []
        for i, d in enumerate(day['date']):
            if not GP.GATE(d): continue
            s = sigma_at(a, d, 365)
            if not s: continue
            m = measure(day, POS[a], d, day['close'][i], 60)
            if not m: continue
            T = 20 * s / ref[(a, 's365')]
            days.append(dict(per='16-21' if d < SPLIT else '22-26', w=m['up'] >= T, f=m['up'] >= 20))
        for p in ('16-21', '22-26'):
            D = [x for x in days if x['per'] == p]; G = [r for r in rows if r['a'] == a and r['per'] == p]
            P(f'  {a} {p}: signals scaled {fr(rate(G, "wS"))} vs regime-on days {fr(rate(D, "w"))}'
              f'  (fixed: {fr(rate(G, "win"))} vs {fr(rate(D, "f"))})')

    P('\nQ3  filter lift (with minus without), 2016-21 / 2022-26, fixed vs scaled')
    F = [('CT > Signal by 5+', lambda r: r['gap'] is not None and r['gap'] > 5, None),
         ('CT > Signal + prime', lambda r: r['gap'] is not None and r['gap'] > 0 and r['prime'], None),
         ('CT > Signal + diamond', lambda r: r['gap'] is not None and r['gap'] > 0 and r['dis'], None),
         ('higher entry', lambda r: r['higher'], None),
         ('2+ own charts before', lambda r: r['agree'] >= 2, None),
         ('8D CT rising', lambda r: r['up8'], None),
         ('BTC 3D before (ETH 1D/2D)', lambda r: r['btc3'], lambda r: r['a'] == 'ETH' and r['tf'] in ('1D', '2D'))]
    OUT['filters'] = {}
    for a in ASSETS:
        P(f'  {a}')
        for lab, fn, uni in F:
            U = [r for r in rows if r['a'] == a and (uni is None or uni(r))]
            if not U: continue
            line = f'    {lab:26}'; res = {}
            for k, kl in (('win', 'fixed'), ('wS', 'scaled')):
                lifts = []; ok = True
                for p in ('16-21', '22-26'):
                    W = [r for r in U if r['per'] == p and fn(r)]; O = [r for r in U if r['per'] == p and not fn(r)]
                    wv, wn = rate(W, k); ov, on = rate(O, k)
                    lift = wv - ov if wn and on else None
                    lifts.append(lift)
                    if not (wn >= 8 and on >= 8 and lift is not None and lift > 0): ok = False
                    line += f' {kl[:3]} {p} {wv if wv is not None else 0:3.0f}%({wn:>3}) vs {ov if ov is not None else 0:3.0f}% lift {lift:+4.0f} |' if lift is not None else f' {kl[:3]} {p}   -   |'
                res[kl] = dict(lifts=lifts, both=ok)
                line += f' {"BOTH" if ok else "no"} ||'
            P(line)
            OUT['filters'][f'{a} {lab}'] = res

    P('\nQ4  the last bull run, by year and asset: fixed | scaled (365d)')
    for y in (2023, 2024, 2025, 2026):
        for a in ASSETS:
            G = [r for r in rows if r['yr'] == y and r['a'] == a]
            if not G: continue
            P(f'  {y} {a}: fixed {fr(rate(G, "win"))} | scaled {fr(rate(G, "wS"))}  median target {st.median(r["T"] for r in G):4.1f}%')
    P('\n  ENTRY QUALITY ONLY. Computed signals, not fills. Nothing adopted from this run.')
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, 'RESULTS_voltarget.txt'), 'w').write('\n'.join(L) + '\n')
    json.dump(OUT, open(os.path.join(here, 'voltarget.json'), 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
