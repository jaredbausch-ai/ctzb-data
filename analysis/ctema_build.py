import sys, datetime as dt, json
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E, regimes as R

gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
CH=[('ETH','1D','data/tradingview/ETH_1D_tv.csv',1),('ETH','2D','data/tradingview/ETH_2D_tv.csv',2),
    ('ETH','3D','data/tradingview/ETH_3D_tv.csv',3),('ETH','5D','data/tradingview/ETH_5D_tv.csv',5),
    ('ETH','1W','data/tradingview/ETH_1W_tv.csv',7),
    ('BTC','1D','data/BTC_1D.csv',1),('BTC','2D','data/BTC_2D.csv',2),
    ('BTC','3D','data/BTC_3D.csv',3),('BTC','5D','data/BTC_5D.csv',5)]

out=[]
for sym,tf,p,tfd in CH:
    sig,b = E.signals(p, regime=gate, ungated=True)
    D,C,Hh,Ll = b['date'],b['close'],b['high'],b['low']; n=len(C)
    ct = E.rsi(C,14); em = E.ema(ct,14)
    # episode age: bars since the last CT/EMA cross
    age=[None]*n; st_=None; sign=None
    for i in range(16,n):
        if None in (ct[i],em[i]): continue
        s = ct[i]>em[i]
        if sign is None or s!=sign: sign=s; st_=i
        age[i]=i-st_
    for s in sig:
        ei=s['ei']
        if ct[ei] is None or em[ei] is None or ei<20: continue
        e=C[ei]
        rec=dict(ch=f'{sym} {tf}', sym=sym, tf=tf, date=str(s['edate']), year=s['edate'].year,
                 bk=s['bk'], dis=bool(s['dis']), strong=bool(s['strong']), prime=bool(s['prime']),
                 ct=round(ct[ei],3), em=round(em[ei],3), gap=round(ct[ei]-em[ei],3),
                 above=bool(ct[ei]>em[ei]),
                 em_slope=round(em[ei]-em[ei-1],3) if em[ei-1] is not None else None,
                 em_slope3=round(em[ei]-em[ei-3],3) if em[ei-3] is not None else None,
                 ct_slope=round(ct[ei]-ct[ei-1],3) if ct[ei-1] is not None else None,
                 em_above50=bool(em[ei]>50), ct_above50=bool(ct[ei]>50),
                 age=age[ei], cyc=s['cyc'])
        for H in (30,60,90):
            end=D[ei]+dt.timedelta(days=H)
            w=[j for j in range(ei+1,n) if D[j]<=end]
            if not w or D[-1]<end:
                rec[f'up{H}']=None; rec[f'ret{H}']=None; rec[f'dd{H}']=None; continue
            pj=max(w,key=lambda j:Hh[j])
            rec[f'up{H}']=round((Hh[pj]/e-1)*100,2)
            rec[f'ret{H}']=round((C[w[-1]]/e-1)*100,2)
            rec[f'dd{H}']=round((min(Ll[j] for j in range(ei+1,pj+1))/e-1)*100,2)
        out.append(rec)
json.dump(out, open('/home/claude/ctzb-data/analysis/ctema.json','w'))
print(f'built {len(out)} signal records across {len(CH)} charts')
from collections import Counter
print(Counter(r['ch'] for r in out))
print('with complete 60d outcomes:', sum(1 for r in out if r['up60'] is not None))
