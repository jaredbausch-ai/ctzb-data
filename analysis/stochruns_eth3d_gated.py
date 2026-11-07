import sys, statistics as st
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E, regimes as R
gate=R.rsi_regime('data/BTC_2D.csv',8,13,60,41)
b=E.load('data/ETH_3D.csv'); c=list(b['close']); d=b['date']; hi=b['high']; lo=b['low']
c[-1]=2231.91
k=E.sma(E.stoch_of(E.rsi(c,14),14),3); n=len(c)
runs=[];cur=0
for i,v in enumerate(k):
    if v is not None and v<=5: cur+=1
    else:
        if cur: runs.append((i-cur,i-1,cur)); 
        cur=0
if cur: runs.append((n-cur,n-1,cur))
def fwd(j,bars):
    s=c[j]; seg=c[j+1:j+1+bars]
    if len(seg)<bars: return None,None,None
    return (seg[-1]/s-1)*100,(max(hi[j+1:j+1+bars])/s-1)*100,(min(lo[j+1:j+1+bars])/s-1)*100
on=[]
print(f"{'start':12} {'end':12} {'bars':>4} {'gate@end':>9} {'during%':>8} {'+10b%':>7} {'+20b%':>7} {'maxUp20':>8} {'maxDn20':>8}")
for s,e,ln in runs:
    g=gate(d[e])
    r10,_,_=fwd(e,10); r20,u20,dn20=fwd(e,20)
    f=lambda x:f"{x:7.1f}" if x is not None else "      -"
    if g: on.append((s,e,ln,r10,r20,u20,dn20))
    print(f"{str(d[s]):12} {str(d[e]):12} {ln:4} {str(g):>9} {(c[e]/c[s]-1)*100:8.1f} {f(r10)} {f(r20)} {f(u20) if u20 is not None else '       -':>8} {f(dn20) if dn20 is not None else '       -':>8}")
print(f"\n--- GATE ON at run end: {len(on)} of {len(runs)} runs")
L=[x[2] for x in on]
print(f"  lengths: {sorted(L)}   median {st.median(L):.1f}  max {max(L)}")
done=[x for x in on if x[4] is not None]
for lab,idx in (('+10 bars',3),('+20 bars',4),('max up 20',5),('max down 20',6)):
    v=[x[idx] for x in done if x[idx] is not None]
    print(f"  {lab:12} median {st.median(v):+6.1f}%   n={len(v)}   up {sum(1 for y in v if y>0)}/{len(v)}")
print(f"\n  runs >=5 bars with gate ON: {[ (str(d[s]),ln) for s,e,ln,*_ in on if ln>=5 ]}")
