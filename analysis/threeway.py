"""Check the two three-way confluence rows from the 24 Oct 7:27 PM email to Joe
("ETH 1D/2D + BTC 3D signal before + 2 or more ETH charts"), under the
capabilities-pack rules (analysis/grokpack.py): BTC 3D confirmed 0-10 days
before entry, same-asset agreement = 2+ other ETH charts confirmed 0-10 days
before. Joe asked on 25 Oct because they were not in the recompute.
"Without" = same agreement level, no BTC 3D signal before.
  python3 -I analysis/threeway.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import grokpack as G

rows, allsig = G.build()
cd = [x['d0'] for x in allsig[('BTC', '3D')]]
hasb = lambda r: any(0 <= (r['d0'] - d).days <= 10 for d in cd)
for ch in ('ETH 1D', 'ETH 2D'):
    G0 = [r for r in rows if r['ch'] == ch]
    for lab, cond in (('2+ ETH charts', lambda r: r['agree'] >= 2), ('0-1 ETH charts', lambda r: r['agree'] < 2)):
        W = [r for r in G0 if cond(r) and hasb(r)]; A = [r for r in G0 if cond(r) and not hasb(r)]
        print(f'{ch} {lab:<15} with BTC 3D  {G.fmt(G.stats(W))}')
        print(f'{ch} {lab:<15} without     {G.fmt(G.stats(A))}')
