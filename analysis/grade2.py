"""Conviction grade, addendum: three more candidate lenses. DECLARED 27 Oct 2026
23:55 ET, before running. Same universe, rules and grade cut points as
analysis/grade.py; this only asks whether these lenses earn a place.

CANDIDATES
  DIVS  bullish divergence on the signal's OWN chart: price made a lower low
        while Stoch K made a higher low, versus the previous Stoch K trough
        (analysis/htfdiv.divergences, osc='k'), confirmed within the 10 days up
        to and including entry. Jared's question, 27 Oct. Earlier record: 2D/3D
        stoch divergence was the best single drawdown filter (-30% cut -8) but
        unstable by year (+13 in 2025); "if revisited, test it as a drawdown
        filter with a placebo" (CONTEXT.md).
  DIVH  the same on any HIGHER chart than the signal's (of 2D 3D 5D 8D),
        confirmed within the 10 days up to entry.
  BTCX  BTC only: an ETH 2D signal confirmed 0-10 days before a BTC 1D or 2D
        entry (PRETRADE "Promising": BTC 1D + ETH 2D before, 60% vs 44%).
        Left out of grade.py, which is why BTC tops out at B.

RULES (unchanged from grade.py)
  STEP 1 keep for an asset if it cuts touched -30% by >= 2 points OR lifts +20%
  by >= 5, the other no more than 3 worse, in both periods, each group n >= 15.
  STEP 2 overlap against every lens already in that asset's grade (ETH: GAP
  HIGH AGREE BTC3 FUND; BTC: GAP UP8) and against each other: a lens with
  both its -30% cut and +20% lift under 1 point inside either half of another
  is that lens counted twice and is dropped (the smaller pooled effect goes).
  PLACEBO, new here, for every candidate that survives steps 1-2: the lens flag
  is reassigned at random among the asset's signals within each year, keeping
  each year's count, 40 times; the real effect on the measure that qualified
  it must beat the shuffled 95th percentile. Fail -> not added.
  STEP 3 grade rebuilt with the surviving candidates added, same cut points
  (C 0-1, B 2, A 3, A+ 4+), reported exactly as grade.py reports it, with the
  dip and upside columns, beside the grade without them.
ENTRY QUALITY ONLY. Computed signals, never fills.
  python3 -I analysis/grade2.py -> analysis/RESULTS_grade2.txt
"""
import sys, os, json, random, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import grokpack as GP
import pcrtest as PT
import grade as G1
from htfdiv import divergences

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)
ORDER = ('1D', '2D', '3D', '5D', '8D')
BASE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grade.json')))['lenses']


def main():
    rows, allsig = GP.build()
    rows = [r for r in rows if r['tf'] in ('1D', '2D', '3D', '5D')]
    b3 = [x['d0'] for x in allsig[('BTC', '3D')]]
    e2 = [x['d0'] for x in allsig[('ETH', '2D')]]
    fb = PT.funding_below()
    DV = {(a, tf): [d for d, _ in divergences(f'data/{a}_{tf}.csv', osc='k')] for a in ('ETH', 'BTC') for tf in ORDER}
    for r in rows:
        r['btc3'] = r['a'] == 'ETH' and r['tf'] in ('1D', '2D') and any(0 <= (r['d0'] - d).days <= 10 for d in b3)
        v = fb.get((r['a'], r['d0'])); r['fund'] = None if v is None else (not v)
        near = lambda lst: any(0 <= (r['d0'] - d).days <= 10 for d in lst)
        r['divs'] = near(DV[(r['a'], r['tf'])])
        r['divh'] = any(near(DV[(r['a'], t)]) for t in ORDER[ORDER.index(r['tf']) + 1:])
        r['btcx'] = r['a'] == 'BTC' and r['tf'] in ('1D', '2D') and near(e2)
    G1.LENS['DIVS'] = lambda r: r['divs']
    G1.LENS['DIVH'] = lambda r: r['divh']
    G1.LENS['BTCX'] = lambda r: r['btcx']
    P('GRADE ADDENDUM: DIVS, DIVH, BTCX -- declared 27 Oct 2026, run', dt.date.today(), '| entry quality only, computed signals, not fills\n')
    added = {}
    for a in ('ETH', 'BTC'):
        A = [r for r in rows if r['a'] == a]
        cands = ['DIVS', 'DIVH'] + (['BTCX'] if a == 'BTC' else [])
        P(f'{a}')
        keep = []
        for k in cands:
            U = [r for r in A if r['tf'] in ('1D', '2D')] if k == 'BTCX' else A
            per = [G1.eff([r for r in U if sel(r)], k) for sel in (lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT)]
            ok = all(e and e['nw'] >= 15 and e['no'] >= 15 and
                     ((e['cut'] >= 2 and e['lift'] >= -3) or (e['lift'] >= 5 and e['cut'] >= -3)) for e in per)
            tot = G1.eff(U, k)
            P(f'  STEP 1 {k}: ' + ' | '.join(f'{lab} cut {e["cut"]:+5.1f} lift {e["lift"]:+5.1f} (n {e["nw"]}/{e["no"]})' if e else f'{lab} -'
                                             for lab, e in zip(('to 2021', '2022 on'), per))
              + (f' | pooled cut {tot["cut"]:+.1f} lift {tot["lift"]:+.1f}' if tot else '') + f'  -> {"pass" if ok else "drop"}')
            if not ok: continue
            twice = False
            for other in BASE[a] + [c for c in keep]:
                UU = [r for r in A if (other != 'FUND' or r['fund'] is not None)]
                for h in (True, False):
                    e = G1.eff([r for r in UU if G1.LENS[other](r) == h], k)
                    if e is None or (e['cut'] < 1 and e['lift'] < 1):
                        P(f'  STEP 2 {k} adds nothing inside {other}={h}: dropped'); twice = True; break
                if twice: break
            if twice: continue
            metric = 'cut' if (tot['cut'] >= 2) else 'lift'
            real = tot[metric]; sh = []; rnd = random.Random(5)
            for _ in range(40):
                byy = {}
                for r in U: byy.setdefault(r['yr'], []).append(r)
                flag = {}
                for y, lst in byy.items():
                    m = sum(G1.LENS[k](r) for r in lst); pick = set(id(x) for x in rnd.sample(lst, m))
                    for r in lst: flag[id(r)] = id(r) in pick
                W = [r for r in U if flag[id(r)]]; O = [r for r in U if not flag[id(r)]]
                sw, so = G1.S(W), G1.S(O)
                sh.append((so['l30'] - sw['l30']) if metric == 'cut' else (sw['win'] - so['win']))
            sh.sort(); p95 = sh[int(0.95 * len(sh)) - 1]
            ok = real > p95
            P(f'  PLACEBO {k} on {metric}: real {real:+.1f} vs shuffled median {st.median(sh):+.1f}, p95 {p95:+.1f} -> {"KEEP" if ok else "drop"}')
            if ok: keep.append(k)
        added[a] = keep
        P(f'  {a} lenses added: {", ".join(keep) or "none"}\n')
    for a in ('ETH', 'BTC'):
        for label, lens in (('grade.py lenses', BASE[a]), ('with additions', BASE[a] + added[a])):
            if label == 'with additions' and not added[a]: continue
            A = [r for r in rows if r['a'] == a and ('FUND' not in lens or r['fund'] is not None)]
            yrs = max(1, len({r['yr'] for r in A}))
            P(f'STEP 3 {a}, {label} ({", ".join(lens)}; {len(A)} signals)')
            for r in A:
                c = sum(G1.LENS[k](r) for k in lens); r['g'] = 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'
            for g in ('A+', 'A', 'B', 'C'):
                Gs = [r for r in A if r['g'] == g]
                if not Gs: P(f'    {g:2} n=0'); continue
                s = G1.S(Gs); dds = sorted(r['m']['dd'] for r in Gs); ups = sorted(r['m']['up'] for r in Gs)
                P(f'    {g:2} {len(Gs) / yrs:5.1f}/yr {G1.fs(s)} | 1-in-10 dip {dds[int(0.10 * (len(Gs) - 1))]:+6.1f}% '
                  f'dip before high {st.median(r["m"]["ddpk"] for r in Gs):+5.1f}% median upside {st.median(ups):+5.1f}%')
                for pl, sel in (('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
                    P(f'         {pl}: {G1.fs(G1.S([r for r in Gs if sel(r)]))}')
    P('\n  ENTRY QUALITY ONLY. Computed signals, not fills.')
    json.dump(added, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grade2.json'), 'w'))
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_grade2.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
