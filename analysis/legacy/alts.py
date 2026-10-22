import engine as E, regimes as R, datetime as dt
reg=R.rsi_regime('/mnt/user-data/uploads/COINBASE_BTCUSD__2D_da5ad.csv',8,13,60,41)
ALT=[("ADA 2D",'/mnt/user-data/uploads/BINANCE_ADAUSD__2D_94d24.csv'),
     ("BNB 2D",'/mnt/user-data/uploads/BINANCE_BNBUSD__2D_75143.csv'),
     ("XRP 2D",'/mnt/user-data/uploads/BITSTAMP_XRPUSD__2D_1248e.csv'),
     ("ETH 2D",'newdata/eth2d_new.csv')]
def zser(ct):
    out=[];z=None
    for v in ct:
        if v is None: out.append(None); continue
        z=None if v>=60 else (v if z is None else min(z,v)); out.append(z)
    return out
TAGS=["all","A","B","C","D","dia","filled","hollow","dot","dia+dot","zoneB"]
NM={"all":"all troughs","A":"A <40","B":"B 40-55","C":"C 55-65","D":"D >=65","dia":"any diamond",
    "filled":"filled <50","hollow":"hollow >=50","dot":"prime dot","dia+dot":"diamond+dot","zoneB":"B out of zone"}
for name,path in ALT:
    sg,b=E.signals(path,regime=reg)
    C,H,L,D=b['close'],b['high'],b['low'],b['date']; n=len(C)
    ct=E.rsi(C,14); zm=zser(ct)
    U=[]
    for s in sg:
        ei=s['ei']; e=C[ei]; end=D[ei]+dt.timedelta(days=60)
        j=ei+1; best=-1e9; mn=1e9; last=None
        while j<n and D[j]<=end: best=max(best,H[j]); mn=min(mn,L[j]); last=C[j]; j+=1
        if last is None: continue
        t=["all",s['bk']]
        if s['dis']: t+=["dia","filled" if s['strong'] else "hollow"]
        if s['prime']: t.append("dot")
        if s['dis'] and s['prime']: t.append("dia+dot")
        if s['bk']=='B' and s['ct']<60 and zm[s['ti']] is not None and zm[s['ti']]>=50: t.append("zoneB")
        U.append(dict(tags=set(t),win=(last/e-1)>0,up=(best/e-1)*100,mae=(mn/e-1)*100,d=s['edate']))
    base=sum(1 for d in U if d['win'])/len(U)*100
    print(f"\n### {name}   {D[0]} -> {D[-1]}   {len(U)} signals in regime   base {base:.0f}%")
    print(f"  {'tag':14s} {'n':>4s} {'win':>5s} {'edge':>5s} {'upside':>8s} {'MAE':>8s}")
    for t in TAGS:
        sub=[d for d in U if t in d['tags']]
        if len(sub)<5: continue
        w=sum(1 for d in sub if d['win'])/len(sub)*100
        print(f"  {NM[t]:14s} {len(sub):4d} {w:4.0f}% {('' if t=='all' else f'{w-base:+4.0f}'):>5s} "
              f"{E.med([d['up'] for d in sub]):+7.1f}% {E.med([d['mae'] for d in sub]):+7.1f}%")
