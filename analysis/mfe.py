import engine as E, regimes as R, datetime as dt, statistics as st
U='/root/.claude/uploads/423587d8-0b23-5551-82c4-c1173e08d447/'
reg=R.rsi_regime('/mnt/user-data/uploads/COINBASE_BTCUSD__2D_da5ad.csv',8,13,60,41)
CH=[("XRP 5D",U+'e8d3d285-BITSTAMP_XRPUSD_5D_1a3ee.csv'),
    ("XRP 8D",U+'d74d319c-BITSTAMP_XRPUSD_8D_d2b95.csv'),
    ("XRP 10D",U+'ea27316e-BITSTAMP_XRPUSD_10D_b2a6b.csv'),
    ("XRP 12D",U+'623c54aa-BITSTAMP_XRPUSD_12D_4094e.csv'),
    ("XRP 15D",U+'898567da-BITSTAMP_XRPUSD_15D_8e427.csv'),
    ("HBAR 5D",U+'4c1b1a70-BYBIT_HBARUSDT.P_5D_40a0b.csv'),
    ("HBAR 8D",U+'6da20ccf-BYBIT_HBARUSDT.P_8D_1b7db.csv'),
    ("HBAR 10D",U+'c5fc6501-BYBIT_HBARUSDT.P_10D_4f477.csv'),
    ("HBAR 12D",U+'e6934090-BYBIT_HBARUSDT.P_12D_a8059.csv'),
    ("HBAR 15D",U+'ca7308b3-BYBIT_HBARUSDT.P_15D_775b3.csv')]
def zser(ct):
    o=[];z=None
    for v in ct:
        if v is None: o.append(None); continue
        z=None if v>=60 else (v if z is None else min(z,v)); o.append(z)
    return o
def run(name,path):
    sg,b=E.signals(path,regime=reg)
    C,H,L,D=b['close'],b['high'],b['low'],b['date']; n=len(C)
    ct=E.rsi(C,14); zm=zser(ct)
    out=[]
    for s in sg:
        ei=s['ei']; e=C[ei]
        # walk until first CLOSE below entry
        j=ei+1; pk=e; pkj=ei; mn=1e18; alive=True
        while j<n:
            if C[j]<e: break
            if H[j]>pk: pk=H[j]; pkj=j
            j+=1
        end=j-1
        if end<=ei: mfe=0.0; mae=0.0; days=0; closed=(j<n)
        else:
            mn=min(L[k] for k in range(ei+1,pkj+1)) if pkj>ei else L[ei+1]
            mfe=(pk/e-1)*100; mae=(mn/e-1)*100; days=(D[pkj]-D[ei]).days
        t=["all",s['bk']]
        if s['dis']: t+=["dia","filled" if s['strong'] else "hollow"]
        if s['prime']: t.append("dot")
        if s['bk']=='B' and s['ct']<60 and zm[s['ti']] is not None and zm[s['ti']]>=50: t.append("zoneB")
        out.append(dict(tags=set(t),mfe=mfe,mae=mae,days=days,d=s['edate'],dead=(j<n)))
    return out,D
NM={"all":"all troughs","A":"A <40","B":"B 40-55","C":"C 55-65","D":"D >=65","dia":"any diamond",
    "filled":"filled <50","hollow":"hollow >=50","dot":"prime dot","zoneB":"B out of zone"}
for name,path in CH:
    try: o,D=run(name,path)
    except Exception as ex: print(f"{name}: {ex}"); continue
    if not o: print(f"{name}: no signals"); continue
    print(f"\n### {name}   {D[0]} -> {D[-1]}   {len(o)} signals in regime")
    print(f"  {'tag':14s} {'n':>3s} {'medMFE':>8s} {'medMAE':>8s} {'worstMAE':>9s} {'MFE>50%':>8s} {'MAE<-20%':>9s} {'days':>5s}")
    for t in ["all","A","B","C","D","dia","filled","hollow","dot","zoneB"]:
        s=[x for x in o if t in x['tags']]
        if len(s)<4: continue
        print(f"  {NM[t]:14s} {len(s):3d} {E.med([x['mfe'] for x in s]):+7.1f}% {E.med([x['mae'] for x in s]):+7.1f}% "
              f"{min(x['mae'] for x in s):+8.1f}% {sum(1 for x in s if x['mfe']>50)/len(s)*100:7.0f}% "
              f"{sum(1 for x in s if x['mae']<-20)/len(s)*100:8.0f}% {int(st.median([x['days'] for x in s])):4d}d")
