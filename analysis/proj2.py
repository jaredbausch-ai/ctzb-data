"""Validation of the 160D projected-trough feature -- 27 Oct 2026.

Four checks: the momentum benchmark that killed the FLD, year stability, regime-
age strata, and whether it adds to gap>5. Results in RESULTS_proj.txt and
summarised in CONTEXT.md.
"""
import sys, os, datetime as dt
sys.path.insert(0,'/home/claude/ctzb-data'); sys.path.insert(0,'/home/claude/ctzb-data/analysis')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, engine as E, regimes as R, fld as F
from tagstats import bucket_end, measure
from proj import dist_series
CH=['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']
gate=R.rsi_regime('data/BTC_2D.csv',8,13,60,41)
# regime episode starts, to stratify by regime age
reg=[]; on=False
d0_=dt.date(2015,1,1)
for n in range(4300):
    d=d0_+dt.timedelta(days=n)
    s=gate(d)
    if s and not on: reg.append(d); on=True
    elif not s: on=False
def regage(d):
    p=[x for x in reg if x<=d]
    return (d-p[-1]).days if p else None
rows=[]
for ch in CH:
    a,tf=ch.split('_'); td=F.TF_DAYS[tf]
    sig,b=E.signals(f'data/{ch}.csv',regime=gate)
    day=E.load(f'data/{a}_1D.csv'); P={d:i for i,d in enumerate(day['date'])}; last=day['date'][-2]
    ds=dist_series(b,F.NOMINAL['160D'],td); c=b['close']; ct=E.rsi(c,14); em=E.ema(ct,14)
    sh=max(1,int(round(F.NOMINAL['160D']/2.0/td)))
    for s in sig:
        i=s['ei']; d0=bucket_end(b['date'],i)
        if d0 is None or d0 not in P or d0+dt.timedelta(days=61)>last or ds[i] is None: continue
        m=measure(day,P,d0,s['entry'],60)
        if not m: continue
        g=ct[i]-em[i] if (ct[i] is not None and em[i] is not None) else None
        rows.append(dict(ch=ch,yr=d0.year,due=ds[i]<0.2,win=m['up']>=20,d30=m['dd']<=-30,
                         g5=(g is not None and g>5),
                         mom=(c[i]>c[i-sh]) if i-sh>=0 else None,
                         age=regage(d0)))
def w(S): return 100*sum(r['win'] for r in S)/len(S) if S else float('nan')
A=[r for r in rows if r['due']]; B=[r for r in rows if not r['due']]
print(f'n={len(rows)}  DUE n={len(A)} win {w(A):.0f}%   not-due n={len(B)} win {w(B):.0f}%   edge {w(A)-w(B):+.0f}\n')
print('1. MOMENTUM BENCHMARK (close > close[half-period], the trap that killed the FLD)')
M=[r for r in rows if r['mom'] is not None]
mt=[r for r in M if r['mom']]; mf=[r for r in M if not r['mom']]
print(f'   plain momentum  n={len(mt)} win {w(mt):.0f}% vs {w(mf):.0f}%  edge {w(mt)-w(mf):+.0f}')
ag=sum(1 for r in M if r['due']==r['mom'])
print(f'   agrees with DUE on {ag}/{len(M)} = {ag/len(M)*100:.0f}%')
d1=[r for r in M if r['due'] and not r['mom']]; d2=[r for r in M if r['mom'] and not r['due']]
print(f'   DUE but not momentum: n={len(d1)} win {w(d1):.0f}%   momentum but not DUE: n={len(d2)} win {w(d2):.0f}%\n')
print('2. BY YEAR')
for y in sorted({r['yr'] for r in rows}):
    S=[r for r in rows if r['yr']==y]; a=[r for r in S if r['due']]; bb=[r for r in S if not r['due']]
    if len(a)<8 or len(bb)<8: continue
    print(f'   {y}  due n={len(a):<4} win {w(a):>3.0f}%   not n={len(bb):<4} win {w(bb):>3.0f}%   edge {w(a)-w(bb):+.0f}')
print('\n3. REGIME AGE STRATA (the check that exposed the higher-low filter)')
for lo,hi in ((0,60),(60,150),(150,300),(300,10000)):
    S=[r for r in rows if r['age'] is not None and lo<=r['age']<hi]
    a=[r for r in S if r['due']]; bb=[r for r in S if not r['due']]
    if len(a)<10 or len(bb)<10: continue
    print(f'   {lo}-{hi if hi<9999 else "+"} days  due n={len(a):<4} {w(a):>3.0f}%   not n={len(bb):<4} {w(bb):>3.0f}%   edge {w(a)-w(bb):+.0f}')
print('\n4. ADDS TO gap>5?')
g=[r for r in rows if r['g5']]; gd=[r for r in g if r['due']]
print(f'   gap>5 alone      n={len(g):<5} win {w(g):.0f}%  -30% {100*sum(r["d30"] for r in g)/len(g):.0f}%')
print(f'   gap>5 AND due    n={len(gd):<5} win {w(gd):.0f}%  -30% {100*sum(r["d30"] for r in gd)/len(gd):.0f}%')
