import engine as E, regimes as R, datetime as dt, json, statistics as st
reg=R.rsi_regime('/mnt/user-data/uploads/COINBASE_BTCUSD__2D_da5ad.csv',8,13,60,41)
TODAY=dt.date(2026,10,15)
CH=[("ETH 1D",'newdata/eth1d_new.csv',1),("ETH 2D",'newdata/eth2d_new.csv',2),
    ("ETH 3D",'newdata/eth3d_new.csv',3),("ETH 5D",'/mnt/user-data/uploads/COINBASE_ETHUSD__5D_815f1.csv',5),
    ("ETH 8D",'/mnt/user-data/uploads/COINBASE_ETHUSD__8D_8e082.csv',8)]
def zser(ct):
    o=[];z=None
    for v in ct:
        if v is None: o.append(None); continue
        z=None if v>=60 else (v if z is None else min(z,v)); o.append(z)
    return o
print("=== confirmation (buy) dates for what is forming ===")
SIG={}
for name,path,tf in CH:
    sg,b=E.signals(path,regime=reg)
    C,D=b['close'],b['date']; n=len(C); ct=E.rsi(C,14); zm=zser(ct); kL=E.sma(E.stoch_of(ct,14),3)
    SIG[name]=[s['edate'] for s in sg]
    # bar cadence
    step=int(st.median([(D[i]-D[i-1]).days for i in range(max(1,n-20),n)]))
    prov=None
    for r_ in (1,2,3):
        ti=n-1-r_
        if ti-3<0: continue
        v=ct[ti]
        if v is None: continue
        if any(ct[j] is None or ct[j]<=v for j in range(ti-3,ti)): continue
        if any(ct[j]<v for j in range(ti+1,n)): continue
        need=3-((n-1)-ti)
        conf=D[-1]+dt.timedelta(days=step*need)
        bk="A" if v<40 else "B" if v<55 else "C" if v<65 else "D"
        tags=[bk]
        if bk=="B" and v<60 and zm[ti] is not None and zm[ti]>=50: tags.append("zone-exit B")
        if kL[ti] is not None and 20<=kL[ti]<50: tags.append("prime dot")
        prov=dict(trough=str(D[ti]),need=need,step=step,conf=str(conf),
                  past=conf<=TODAY,tags=tags)
        break
    print(f"  {name:7s} step {step}d  data->{D[-1]}  prov {prov['trough'] if prov else '-'}  needs {prov['need'] if prov else '-'}  "
          f"BUY {prov['conf'] if prov else '-'}  {'ALREADY PASSED - need fresh data' if prov and prov['past'] else ''}")
print("\n=== confluence: how many ETH charts printed within 10 days of each other ===")
allsig=[]
for name in SIG:
    for d in SIG[name]: allsig.append((d,name))
allsig.sort()
# for each signal, count distinct other charts with a signal within +-10d
b2=E.load('newdata/eth2d_new.csv'); D2,C2,H2,L2=b2['date'],b2['close'],b2['high'],b2['low']; n2=len(C2)
sg2,_=E.signals('newdata/eth2d_new.csv',regime=reg)
def fwd(ei):
    e=C2[ei]; end=D2[ei]+dt.timedelta(days=60); j=ei+1; best=-1e9; mn=1e9; last=None
    while j<n2 and D2[j]<=end: best=max(best,H2[j]); mn=min(mn,L2[j]); last=C2[j]; j+=1
    return None if last is None else ((last/e-1)*100,(best/e-1)*100,(mn/e-1)*100)
buck={}
for s in sg2:
    f=fwd(s['ei'])
    if not f: continue
    others={nm for d,nm in allsig if nm!="ETH 2D" and abs((d-s['edate']).days)<=10}
    k=len(others)
    buck.setdefault(k,[]).append(f)
print(f"  {'other charts':14s} {'n':>4s} {'win':>5s} {'median run':>11s} {'median DD':>10s}")
for k in sorted(buck):
    v=buck[k]
    w=sum(1 for x in v if x[0]>0)/len(v)*100
    print(f"  {k:<14d} {len(v):4d} {w:4.0f}% {E.med([x[1] for x in v]):+10.1f}% {E.med([x[2] for x in v]):+9.1f}%")
print("\n=== right now: which charts have a signal or provisional within 10 days ===")
for name,path,tf in CH:
    recent=[d for d in SIG[name] if (TODAY-d).days<=10 and d<=TODAY]
    print(f"  {name:7s} confirmed in last 10d: {recent if recent else 'none'}")
