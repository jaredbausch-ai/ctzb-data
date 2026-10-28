"""Grade audit, last item. DECLARED 28 Oct 2026 01:00 ET, before running.
The cross-asset map (analysis/xmap.py) recorded one near miss that no grade run
had tried: an ETH 3D signal confirmed 0-10 days before a BTC 1D entry (+7, 6 of
9 years). Candidate BTCX3: ETH 3D confirmed 0-10 days before a BTC 1D or 2D
entry. Same rules as grade3.py: per-period keep rule, overlap against BTC's
current lenses (GAP UP8 BTCX), placebo, and the ordering-score adoption rule.
ENTRY QUALITY ONLY. Computed signals, never fills.
  python3 -I analysis/grade4.py -> analysis/RESULTS_grade4.txt
"""
import sys, os, random, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import grokpack as GP
import grade as G1
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)

def main():
    rows, allsig = GP.build()
    e2 = [x['d0'] for x in allsig[('ETH', '2D')]]; e3 = [x['d0'] for x in allsig[('ETH', '3D')]]
    A = [r for r in rows if r['a'] == 'BTC' and r['tf'] in ('1D', '2D', '3D', '5D')]
    for r in A:
        near = lambda lst: any(0 <= (r['d0'] - d).days <= 10 for d in lst)
        r['btcx'] = r['tf'] in ('1D', '2D') and near(e2); r['btcx3'] = r['tf'] in ('1D', '2D') and near(e3)
    G1.LENS['BTCX'] = lambda r: r['btcx']; G1.LENS['BTCX3'] = lambda r: r['btcx3']
    U = [r for r in A if r['tf'] in ('1D', '2D')]
    P('GRADE AUDIT, last item: BTCX3 -- declared 28 Oct 2026, run', dt.date.today())
    per = [G1.eff([r for r in U if sel(r)], 'BTCX3') for sel in (lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT)]
    ok = all(e and e['nw'] >= 15 and e['no'] >= 15 and ((e['cut'] >= 2 and e['lift'] >= -3) or (e['lift'] >= 5 and e['cut'] >= -3)) for e in per)
    tot = G1.eff(U, 'BTCX3')
    P('  STEP 1 BTCX3 ' + ' | '.join(f'{lab} cut {e["cut"]:+5.1f} lift {e["lift"]:+5.1f} (n {e["nw"]}/{e["no"]})' for lab, e in zip(('to 2021', '2022 on'), per))
      + f' | pooled cut {tot["cut"]:+.1f} lift {tot["lift"]:+.1f} -> {"pass" if ok else "drop"}')
    if ok:
        for other in ('GAP', 'UP8', 'BTCX'):
            for h in (True, False):
                e = G1.eff([r for r in U if G1.LENS[other](r) == h], 'BTCX3')
                P(f'  STEP 2 inside {other}={h}: ' + (f'cut {e["cut"]:+.1f} lift {e["lift"]:+.1f}' if e else 'n/a'))
                if e is None or (e['cut'] < 1 and e['lift'] < 1): ok = False
        both = sum(r['btcx'] and r['btcx3'] for r in U); P(f'  overlap with BTCX: {both} of {sum(r["btcx3"] for r in U)} BTCX3 signals also have BTCX')
    P(f'  VERDICT: {"passes steps 1-2; placebo and ordering would follow" if ok else "NOT ADDED"}')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_grade4.txt'), 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    main()
