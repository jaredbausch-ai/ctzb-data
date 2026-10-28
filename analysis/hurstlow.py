"""Hurst forward cycle lows, rebuilt on PRICE swing lows. DECLARED 27 Oct 2026
22:50 ET, before running.

WHY. analysis/proj.py projected from troughs of a bandpass (long trailing average
minus short trailing average of log price). Checked 27 Oct: those troughs are not
price lows. Where price sits in its surrounding cycle range at each one: median
0.43 (ETH 1D), 0.47 (BTC 1D), 0.44 (ETH 2D), only 33-40% in the bottom third.
So "160D low due" timed a phase point of the filter, not a bottom. Jared wants
forward-looking cycle LOWS he can check by eye, so the construct is rebuilt on
price and retested. proj.py's result stands as what it was, but it is not a
cycle-low result.

CONSTRUCT (identical in the Pine indicator pine/ctzb_hurst_lows.pine):
  degree D (nominal days: 160D = 136.4, 80D = 68.2); chart bar = tf days;
  tgt = D / tf bars.
  Swing low of degree D at bar j: low[j] is the lowest low of bars
  j-L .. j+R, L = round(0.5 tgt), R = round(0.25 tgt). Known at bar j+R.
  Separation: a new confirmed low within 0.6 tgt bars of the last one replaces
  it only if lower; otherwise it is ignored.
  Period: median of the last 3 spacings between kept lows (needs >= 2),
  clamped to 0.8-1.6 tgt; fallback 1.25 tgt (crypto cycles measured 1.15-1.34x
  nominal, CONTEXT.md).
  Projected next low = last kept low + period, rolled forward by whole periods
  if more than half a period has lapsed. dist = (projected - i) / period.
  DUE = dist < 0.2 (same threshold as proj.py). Everything known at bar i.

QUESTIONS:
 Q1 How good are the predictions? For every projection standing when a new
    low is confirmed, error = (actual low bar - projected bar) / period. Median
    absolute error, and share within 0.2 periods. Plus where price sits in its
    cycle range at the kept lows (sanity: should be near 0).
 Q2 Signals (analysis/grokpack.py rows, regime-on, confirmation entry; ETH and
    BTC 1D 2D 3D 5D): DUE vs not, reported as touched -30%, touched -20%,
    median worst dip, +20% in 60 days, n; per chart, per period, per year.
 Q3 ETH: DUE x 2+ same-asset charts agreeing, the four cells.
 Q4 Same rows under proj.py's bandpass construct, side by side.
 Q5 Placebo for Q2 if DUE shows any gain: shift every projected date by a
    random 0.3-0.7 period, 40 times; real gain vs p95.
WORTH CARRYING AS A LENS (context, never a filter) if at 160D: DUE cuts
touched -30% by >= 3 points OR lifts +20% by >= 5, without the other getting
worse by more than 3; in both periods; on at least 6 of 8 charts in the same
direction; and beats the placebo p95.
ENTRY QUALITY ONLY. Signals are computed, never fills.
  python3 -I analysis/hurstlow.py -> analysis/RESULTS_hurstlow.txt
"""
import sys, os, random, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import grokpack as GP
import fld as F
import proj as PJ

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
TFD = {'1D': 1, '2D': 2, '3D': 3, '5D': 5, '8D': 8}
SPLIT = dt.date(2022, 1, 1)


def swing_lows(low, tgt):
    """Kept swing lows as (bar, confirm_bar) in confirmation order, with the separation rule."""
    Lb, Rb = max(2, round(0.5 * tgt)), max(2, round(0.25 * tgt))
    n = len(low); kept = []
    for j in range(Lb, n - Rb):
        w = low[j - Lb:j + Rb + 1]
        if low[j] != min(w) or any(low[x] == low[j] for x in range(j - Lb, j)):
            continue
        if kept and j - kept[-1][0] < 0.6 * tgt:
            if low[j] < low[kept[-1][0]]:
                kept[-1] = (j, j + Rb)
            continue
        kept.append((j, j + Rb))
    return kept


def stream(low, tgt):
    """Causal version of swing_lows, identical to the Pine indicator: at bar i a
    low confirmed at i (candidate j = i - R) is appended, or replaces the last
    low if within 0.6 tgt and lower, or is ignored. Returns per bar the list of
    known lows and an event code ('new' / 'replace' / None). Fixed 27 Oct 2026
    late: swing_lows() resolved replacements with hindsight, so a low that was
    later replaced was never 'known' even while it stood."""
    Lb, Rb = max(2, round(0.5 * tgt)), max(2, round(0.25 * tgt))
    n = len(low); known = []; ev = [None] * n; snap = [None] * n
    for i in range(n):
        j = i - Rb
        if j >= Lb:
            w = low[j - Lb:i + 1]
            if low[j] == min(w) and not any(low[x] == low[j] for x in range(j - Lb, j)):
                if known and j - known[-1] < 0.6 * tgt:
                    if low[j] < low[known[-1]]:
                        known = known[:-1] + [j]; ev[i] = 'replace'
                else:
                    known = known + [j]; ev[i] = 'new'
        snap[i] = known
    return snap, ev


def dist_series(low, tgt, shift=0.0):
    snap, ev = stream(low, tgt); n = len(low); out = [None] * n; proj_at = [None] * n
    kept = [(snap[i][-1], i) for i in range(n) if ev[i] == 'new']
    for i in range(n):
        known = snap[i]
        if not known: continue
        sp = [known[k] - known[k - 1] for k in range(max(1, len(known) - 3), len(known))]
        per = st.median(sp) if len(sp) >= 2 else 1.25 * tgt
        per = min(max(per, 0.8 * tgt), 1.6 * tgt)
        nxt = known[-1] + per + shift * per
        while nxt < i - 0.5 * per: nxt += per
        out[i] = (nxt - i) / per; proj_at[i] = (nxt, per)
    return out, proj_at, kept


def summ(G):
    if not G: return None
    n = len(G)
    return dict(n=n, l30=100 * sum(r['t30'] for r in G) / n, l20=100 * sum(r['t20'] for r in G) / n,
                dd=st.median(r['m']['dd'] for r in G), win=100 * sum(r['win'] for r in G) / n)


def fs(s):
    return 'n=   0' if not s else f'n={s["n"]:>4} -30% {s["l30"]:3.0f}% -20% {s["l20"]:3.0f}% dip {s["dd"]:+6.1f}% +20% {s["win"]:3.0f}%'


def attach(rows, deg, shift=0.0, construct='price'):
    cache = {}
    for r in rows:
        key = (r['a'], r['tf'])
        if key not in cache:
            b = E.load(f'data/{r["a"]}_{r["tf"]}.csv'); tgt = deg / TFD[r['tf']]
            if construct == 'price':
                cache[key] = dist_series(list(b['low']), tgt, shift)[0]
            else:
                cache[key] = PJ.dist_series(b, deg, TFD[r['tf']])
        ds = cache[key]; i = r['ei']
        r['dist'] = ds[i] if i < len(ds) else None
    return [r for r in rows if r['dist'] is not None]


def main():
    P('HURST FORWARD CYCLE LOWS ON PRICE -- declared 27 Oct 2026, run', dt.date.today())
    P('entry quality only, computed signals, not fills\n')
    P('Q1  prediction accuracy (error = actual low - projected, in periods)')
    for deg_name in ('160D', '80D'):
        deg = F.NOMINAL[deg_name]
        for a in ('ETH', 'BTC'):
            for tf in ('1D', '2D', '3D', '5D'):
                b = E.load(f'data/{a}_{tf}.csv'); low = list(b['low']); tgt = deg / TFD[tf]
                ds, pa, kept = dist_series(low, tgt)
                errs = []
                for j, cb in kept[1:]:
                    p = pa[cb - 1] if cb - 1 >= 0 else None
                    if p: errs.append((j - p[0]) / p[1])
                pos = []
                for j, cb in kept:
                    h = int(tgt / 2); w = low[max(0, j - h):j + h + 1]; c = list(b['close'])[max(0, j - h):j + h + 1]
                    hi = max(c); lo = min(w)
                    if hi > lo: pos.append((low[j] - lo) / (hi - lo))
                if errs:
                    P(f'  {deg_name} {a} {tf}: lows {len(kept):>2}  median |error| {st.median(abs(e) for e in errs):.2f} periods,'
                      f' within 0.2: {100 * sum(abs(e) <= 0.2 for e in errs) / len(errs):3.0f}%, median error {st.median(errs):+.2f}'
                      f' | price position at kept lows median {st.median(pos):.2f}')
    rows0 = [r for r in GP.build()[0] if r['tf'] in ('1D', '2D', '3D', '5D')]
    for deg_name in ('160D', '80D'):
        deg = F.NOMINAL[deg_name]
        rows = attach([dict(r) for r in rows0], deg)
        P(f'\nQ2  {deg_name}: signals by whether a price-cycle low is DUE (dist < 0.2)')
        for a in ('ETH', 'BTC', 'ALL'):
            G = [r for r in rows if a == 'ALL' or r['a'] == a]
            D = [r for r in G if r['dist'] < 0.2]; N = [r for r in G if r['dist'] >= 0.2]
            P(f'  {a:3} DUE {fs(summ(D))}')
            P(f'      not {fs(summ(N))}')
        G = rows; D = [r for r in G if r['dist'] < 0.2]; N = [r for r in G if r['dist'] >= 0.2]
        for pl, sel in (('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
            P(f'    {pl}: DUE {fs(summ([r for r in D if sel(r)]))} | not {fs(summ([r for r in N if sel(r)]))}')
        dirn = []
        for a in ('ETH', 'BTC'):
            for tf in ('1D', '2D', '3D', '5D'):
                d = summ([r for r in D if r['a'] == a and r['tf'] == tf]); o = summ([r for r in N if r['a'] == a and r['tf'] == tf])
                if d and o:
                    dirn.append((o['l30'] - d['l30'], d['win'] - o['win']))
                    P(f'    {a} {tf}: -30% {d["l30"]:3.0f}% vs {o["l30"]:3.0f}%  +20% {d["win"]:3.0f}% vs {o["win"]:3.0f}%  (n {d["n"]}/{o["n"]})')
        for y in sorted({r['yr'] for r in G}):
            d = summ([r for r in D if r['yr'] == y]); o = summ([r for r in N if r['yr'] == y])
            if d and o: P(f'    {y}: -30% {d["l30"]:3.0f}% vs {o["l30"]:3.0f}%  +20% {d["win"]:3.0f}% vs {o["win"]:3.0f}%  (n {d["n"]}/{o["n"]})')
        if deg_name == '160D':
            P('\nQ3  ETH, 160D DUE x 2+ same-asset charts agreeing')
            E_ = [r for r in rows if r['a'] == 'ETH']
            for lab, sel in (('due, 2+ agree', lambda r: r['dist'] < 0.2 and r['agree'] >= 2),
                             ('due, 0-1 agree', lambda r: r['dist'] < 0.2 and r['agree'] < 2),
                             ('not due, 2+ agree', lambda r: r['dist'] >= 0.2 and r['agree'] >= 2),
                             ('not due, 0-1 agree', lambda r: r['dist'] >= 0.2 and r['agree'] < 2)):
                P(f'  {lab:20} {fs(summ([r for r in E_ if sel(r)]))}')
            P('\nQ4  same rows, proj.py bandpass construct, 160D')
            rb = attach([dict(r) for r in rows0], deg, construct='bandpass')
            Db = [r for r in rb if r['dist'] < 0.2]; Nb = [r for r in rb if r['dist'] >= 0.2]
            P(f'  bandpass DUE {fs(summ(Db))}\n  bandpass not {fs(summ(Nb))}')
            sd, so = summ(D), summ(N)
            cut, lift = so['l30'] - sd['l30'], sd['win'] - so['win']
            pers = []
            for sel in (lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT):
                a1 = summ([r for r in D if sel(r)]); b1 = summ([r for r in N if sel(r)])
                pers.append((b1['l30'] - a1['l30'], a1['win'] - b1['win']) if a1 and b1 else (None, None))
            gain_kind = 'cut' if cut >= 3 and lift >= -3 else 'lift' if lift >= 5 and cut >= -3 else None
            ok = gain_kind is not None
            if ok:
                idx = 0 if gain_kind == 'cut' else 1
                ok = all(p[idx] is not None and p[idx] > 0 for p in pers) and sum(x[idx] > 0 for x in dirn) >= 6
            P(f'\n  160D: -30% cut {cut:+.1f}, +20% lift {lift:+.1f}; by period {pers}; charts same direction '
              f'{sum((x[0] if gain_kind != "lift" else x[1]) > 0 for x in dirn)}/{len(dirn)}')
            if ok:
                real = cut if gain_kind == 'cut' else lift; sh = []; rnd = random.Random(11)
                for _ in range(40):
                    s = rnd.choice([-1, 1]) * rnd.uniform(0.3, 0.7)
                    rs = attach([dict(r) for r in rows0], deg, shift=s)
                    d = summ([r for r in rs if r['dist'] < 0.2]); o = summ([r for r in rs if r['dist'] >= 0.2])
                    if d and o: sh.append(o['l30'] - d['l30'] if gain_kind == 'cut' else d['win'] - o['win'])
                sh.sort(); p95 = sh[int(0.95 * len(sh)) - 1]
                ok = real > p95
                P(f'  PLACEBO: real {real:+.1f} vs shuffled median {st.median(sh):+.1f}, p95 {p95:+.1f}')
            P(f'  VERDICT 160D: {"WORTH CARRYING AS A LENS" if ok else "NOT CARRIED"}')
    P('\n  ENTRY QUALITY ONLY. Computed signals, not fills.')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_hurstlow.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
