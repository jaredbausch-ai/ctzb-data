"""BTC crowded-long while ETH is not: how often, and what followed.

Declared before running:
  A) BTC L/S >= 2.07 (BTC Q5 floor) AND ETH L/S in [1.98, 2.62] (ETH Q3 band)
  B) continuous: BTC L/S percentile - ETH L/S percentile, top decile of the gap
Outcomes: BTC and ETH forward 30d/60d close returns, plus 60d max adverse
excursion on ETH. Events declustered to one per 14 days.
"""
import csv, datetime as dt, statistics as st

def px(p):
    o={}
    for r in csv.DictReader(open(p)):
        d=str(dt.datetime.fromtimestamp(int(r['time']),dt.UTC).date())
        o[d]=(float(r['close']),float(r['low']))
    return o
B=px('data/BTC_1D.csv'); E=px('data/ETH_1D.csv')
def ls(a):
    return {r['date']:float(r['ls_ratio_mean'])
            for r in csv.DictReader(open(f'data/derivs/{a}_lsratio_daily.csv')) if r['ls_ratio_mean']}
LB, LE = ls('BTC'), ls('ETH')
days=sorted(set(LB)&set(LE)&set(B)&set(E))
bd=sorted(B); ed=sorted(E)

def fwd(P, order, day, h):
    i=order.index(day)
    return (P[order[i+h]][0]/P[day][0]-1)*100 if i+h<len(order) else None
def mae(P, order, day, h):
    i=order.index(day); seg=order[i+1:i+1+h]
    return (min(P[x][1] for x in seg)/P[day][0]-1)*100 if len(seg)==h else None

bl=sorted(LB[d] for d in days); el=sorted(LE[d] for d in days)
def pct(v,arr): return 100*sum(1 for x in arr if x<=v)/len(arr)

def report(name, ev):
    ev=sorted(ev); keep=[]; last=None
    for d in ev:
        dd=dt.date.fromisoformat(d)
        if last is None or (dd-last).days>14: keep.append(d); last=dd
    print(f"\n{name}   {len(ev)} days, {len(keep)} declustered")
    if not keep: return
    print(f"  {'date':12} {'BTC L/S':>8} {'ETH L/S':>8} {'BTC+30':>8} {'BTC+60':>8} {'ETH+30':>8} {'ETH+60':>8} {'ETHmae60':>9}")
    rows=[]
    for d in keep:
        r=[fwd(B,bd,d,30),fwd(B,bd,d,60),fwd(E,ed,d,30),fwd(E,ed,d,60),mae(E,ed,d,60)]
        rows.append(r)
        f=lambda x: f"{x:8.2f}" if x is not None else "       -"
        print(f"  {d:12} {LB[d]:8.3f} {LE[d]:8.3f} "+" ".join(f(x) for x in r[:4])+f" {f(r[4])}")
    for i,lab in enumerate(('BTC +30d','BTC +60d','ETH +30d','ETH +60d','ETH MAE60')):
        v=[r[i] for r in rows if r[i] is not None]
        if not v: continue
        print(f"  {lab:10} median {st.median(v):+7.2f}%   up {sum(1 for x in v if x>0)}/{len(v)}")

A=[d for d in days if LB[d]>=2.07 and 1.98<=LE[d]<=2.62]
report("A) BTC crowded (Q5) + ETH mid (Q3)", A)

gaps=[(pct(LB[d],bl)-pct(LE[d],el), d) for d in days]
thr=sorted(g for g,_ in gaps)[int(0.90*len(gaps))]
cur=pct(LB[days[-1]],bl)-pct(LE[days[-1]],el)
print(f"\n\nB) percentile gap: top-decile threshold {thr:+.1f} pts;  today = {cur:+.1f} pts"
      f"  (BTC {pct(LB[days[-1]],bl):.0f}th, ETH {pct(LE[days[-1]],el):.0f}th)")
report("B) BTC pctile - ETH pctile in top decile", [d for g,d in gaps if g>=thr])

bb=[fwd(B,bd,d,60) for d in bd[::1]]; bb=[x for x in bb if x is not None]
ee=[fwd(E,ed,d,60) for d in ed[::1]]; ee=[x for x in ee if x is not None]
print(f"\nbaselines  BTC +60d median {st.median(bb):+.2f}% ({100*sum(1 for x in bb if x>0)/len(bb):.0f}% up)"
      f"   ETH +60d median {st.median(ee):+.2f}% ({100*sum(1 for x in ee if x>0)/len(ee):.0f}% up)")
