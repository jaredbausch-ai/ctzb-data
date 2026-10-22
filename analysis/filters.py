import engine as E, regimes as R, datetime as dt
reg=R.rsi_regime('/mnt/user-data/uploads/COINBASE_BTCUSD__2D_da5ad.csv',8,13,60,41)
P='newdata/eth2d_new.csv'
sg,b=E.signals(P,regime=reg)
C=b['close']; H=b['high']; L=b['low']; O=b['open']; D=b['date']; n=len(C)
def sma(src,k):
    out=[None]*len(src); s=0
    for i,v in enumerate(src):
        s+=v
        if i>=k: s-=src[i-k]
        if i>=k-1: out[i]=s/k
    return out
def ema(src,k):
    out=[None]*len(src); a=2/(k+1); e=None
    for i,v in enumerate(src):
        e=v if e is None else a*v+(1-a)*e; out[i]=e
    return out
S50,S100,S150,S200=sma(C,50),sma(C,100),sma(C,150),sma(C,200)
e12,e26=ema(C,12),ema(C,26)
macd=[e12[i]-e26[i] for i in range(n)]; sig=ema(macd,9)
hist=[macd[i]-sig[i] for i in range(n)]
tr=[0.0]*n
for i in range(1,n): tr[i]=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]))
atr=sma(tr,14)
HOR=60
def fw(ei):
    e=C[ei]; end=D[ei]+dt.timedelta(days=HOR); j=ei+1; best=-1e9; mn=1e9; last=None
    while j<n and D[j]<=end: best=max(best,H[j]); mn=min(mn,L[j]); last=C[j]; j+=1
    return None if last is None else ((last/e-1)*100,(best/e-1)*100,(mn/e-1)*100)
U=[]
for s in sg:
    f=fw(s['ei'])
    if not f: continue
    ei=s['ei']; ti=s['ti']
    if ei<200: continue
    hi30=max(H[max(0,ei-30):ei+1]); lo=L[ti]
    d={'s':s,'f':f,'win':f[0]>0,'date':s['edate'],
       'c':C[ei],'s50':S50[ei],'s100':S100[ei],'s150':S150[ei],'s200':S200[ei],
       'macd':macd[ei],'sig':sig[ei],'hist':hist[ei],'hist1':hist[ei-1],
       'atr':atr[ei],'dd':(lo/hi30-1)*100,'atrdip':(hi30-lo)/atr[ei] if atr[ei] else None,
       'rngpos':(C[ti]-L[ti])/(H[ti]-L[ti]) if H[ti]>L[ti] else 0.5,
       'ft':C[ei]>H[ti]}
    d['band']=min(abs(d['c']/x-1)*100 for x in (d['s50'],d['s100'],d['s150']) if x)
    U.append(d)
base=sum(1 for d in U if d['win'])/len(U)*100
print(f"ETH 2D universe: {len(U)} signals, base win {base:.0f}%, median upside {E.med([d['f'][1] for d in U]):+.1f}%, median MAE {E.med([d['f'][2] for d in U]):+.1f}%\n")
F={
 "close > SMA50":            lambda d: d['c']>d['s50'],
 "close < SMA50":            lambda d: d['c']<d['s50'],
 "close > SMA100":           lambda d: d['c']>d['s100'],
 "close > SMA150":           lambda d: d['c']>d['s150'],
 "close > SMA200":           lambda d: d['c']>d['s200'],
 "SMA50 > SMA150 (stack)":   lambda d: d['s50']>d['s150'],
 "near the MA band (<8%)":   lambda d: d['band']<8,
 "near the MA band (<15%)":  lambda d: d['band']<15,
 "dip < 20% off 30-bar high":lambda d: d['dd']>-20,
 "dip > 20% off 30-bar high":lambda d: d['dd']<=-20,
 "ATR dip < 4":              lambda d: d['atrdip'] is not None and d['atrdip']<4,
 "ATR dip > 6":              lambda d: d['atrdip'] is not None and d['atrdip']>6,
 "MACD > 0":                 lambda d: d['macd']>0,
 "MACD > signal":            lambda d: d['macd']>d['sig'],
 "MACD hist rising":         lambda d: d['hist']>d['hist1'],
 "MACD hist rising AND >0":  lambda d: d['hist']>d['hist1'] and d['hist']>0,
 "trough closed upper 1/3":  lambda d: d['rngpos']>=0.667,
 "trough closed lower 1/3":  lambda d: d['rngpos']<=0.333,
 "follow-through > trough hi":lambda d: d['ft'],
}
print(f"{'filter':30s} {'kept':>5s} {'win':>5s} {'lift':>5s} | {'cut':>4s} {'Lcut':>5s} {'Wcut':>5s} {'ratio':>6s} | {'up':>7s} {'MAE':>7s}")
rows=[]
for name,fn in F.items():
    keep=[d for d in U if fn(d)]; cut=[d for d in U if not fn(d)]
    if len(keep)<15 or not cut: continue
    wk=sum(1 for d in keep if d['win'])/len(keep)*100
    Lc=sum(1 for d in cut if not d['win']); Wc=sum(1 for d in cut if d['win'])
    ratio=Lc/Wc if Wc else float('inf')
    print(f"{name:30s} {len(keep):5d} {wk:4.0f}% {wk-base:+5.0f} | {len(cut):4d} {Lc:5d} {Wc:5d} {ratio:6.2f} | "
          f"{E.med([d['f'][1] for d in keep]):+6.1f}% {E.med([d['f'][2] for d in keep]):+6.1f}%")
    rows.append((name,fn,wk-base,ratio,len(keep)))
