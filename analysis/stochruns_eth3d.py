"""Descriptive distribution of Stoch %K floor runs on ETH 3D. Jared asked 7 Nov.

Threshold <=5 is the one declared in analysis/stochdwell.py (31 Oct); it is not
re-chosen here. This is DESCRIPTIVE ONLY. stochdwell already tested whether pin
duration predicts the release and it failed 24 of 24 configs; the forward
columns below are shown because they were asked for, not as a result.
"""
import sys, statistics as st
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E

b=E.load('data/ETH_3D.csv'); c=list(b['close']); d=b['date']; hi=b['high']; lo=b['low']
c[-1]=2231.91
ct=E.rsi(c,14); k=E.sma(E.stoch_of(ct,14),3)
n=len(c)

runs=[]; cur=0
for i,v in enumerate(k):
    if v is not None and v<=5: cur+=1
    else:
        if cur: runs.append((i-cur, i-1, cur))
        cur=0
if cur: runs.append((n-cur, n-1, cur))

def fwd(j, bars):
    s=c[j]; seg=c[j+1:j+1+bars]
    if len(seg)<bars: return None,None,None
    return (seg[-1]/s-1)*100, (max(hi[j+1:j+1+bars])/s-1)*100, (min(lo[j+1:j+1+bars])/s-1)*100

print(f"ETH 3D  Stoch %K <= 5 runs   ({n} bars, {d[0]} to {d[-1]})\n")
print(f"{'start':12} {'end':12} {'bars':>4} {'days':>5} {'px start':>10} {'px end':>10} {'during%':>8} "
      f"{'+10bar%':>8} {'+20bar%':>8} {'maxUp20':>8} {'maxDn20':>8}")
L=[]
for s,e,ln in runs:
    L.append(ln)
    during=(c[e]/c[s]-1)*100
    r10,_,_ = fwd(e,10); r20,u20,d20 = fwd(e,20)
    f=lambda x: f"{x:8.1f}" if x is not None else "       -"
    print(f"{str(d[s]):12} {str(d[e]):12} {ln:4} {ln*3:5} {c[s]:10,.2f} {c[e]:10,.2f} {during:8.1f} "
          f"{f(r10)} {f(r20)} {f(u20)} {f(d20)}")

print(f"\nrun-length distribution  n={len(L)}")
print(f"  median {st.median(L):.1f}   mean {st.mean(L):.2f}   max {max(L)}   "
      f"p75 {sorted(L)[int(.75*len(L))]}   p90 {sorted(L)[int(.90*len(L))]}")
from collections import Counter
print("  lengths:", dict(sorted(Counter(L).items())))
print(f"  runs >= 5 bars: {sum(1 for x in L if x>=5)}   >= 7: {sum(1 for x in L if x>=7)}   >= 9: {sum(1 for x in L if x>=9)}")
