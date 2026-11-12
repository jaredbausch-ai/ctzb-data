import sys, time; sys.path.insert(0,'.')
from state import *
t=time.time()
S=State('REPLAY'); print('built',time.time()-t, S.today)
for a in S.A:
    print(a,'clamped',S.A[a].clamped)
    for tf in TFS:
        mine=S.A[a].bars[tf]; theirs=read_csv_bars(f'{S.root}/data/{a}_{tf}.csv')
        mm=[(m['t'],m['o'],m['h'],m['l'],m['c']) for m in mine]
        diff=[(x,y) for x,y in zip(mm,theirs) if x!=y]
        print(a,tf,len(mm),len(theirs),'diffs',len(diff),diff[:3])
exp=S.expected_ledger()
E={(f"{s['a']} {s['tf']}",str(s['d0'])) for s in exp}
L={(r['chart'],r['entry']) for r in S.ledger}
print('exp',len(E),'ledger',len(L),'mine-only',sorted(E-L)[:20],'ledger-only',sorted(L-E)[:20])
