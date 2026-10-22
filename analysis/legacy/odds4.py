"""CTZB odds v4. Primary figures = v11 LIVE regime.
Hand-drawn (hindsight) win/edge kept as a reference column."""
import engine as E, regimes as R, datetime as dt, json

P='/mnt/user-data/uploads/'
BTC2D=P+'COINBASE_BTCUSD__2D_da5ad.csv'
LIVE=R.rsi_regime(BTC2D,enterN=8,exitN=13,enterLvl=60,exitLvl=41)  # >=60 x8 bull, <=40 x12 bear
CUT=dt.date(2021,12,31)

CH=[('ETH 1D',P+'COINBASE_ETHUSD__1D_2aba2.csv',1),
    ('ETH 2D',P+'COINBASE_ETHUSD__2D_41167.csv',2),
    ('ETH 3D',P+'COINBASE_ETHUSD__3D_ad149.csv',3),
    ('ETH 5D',P+'COINBASE_ETHUSD__5D_75095.csv',5),
    ('BTC 1D',P+'COINBASE_BTCUSD__1D_f16bd.csv',1),
    ('BTC 2D',BTC2D,2)]

TAGS=[('ALL troughs',    lambda s: True,                             'all'),
      ('A  trough <40',  lambda s: s['bk']=='A',                     'A'),
      ('B  trough 40-55',lambda s: s['bk']=='B',                     'B'),
      ('C  trough 55-65',lambda s: s['bk']=='C',                     'C'),
      ('D  trough >65',  lambda s: s['bk']=='D',                     'D'),
      ('Any diamond',    lambda s: s['dis'],                         'dia'),
      ('GOLD diamond <50',   lambda s: s['strong'],                  'gold'),
      ('HOLLOW diamond >=50',lambda s: s['dis'] and not s['strong'], 'holl'),
      ('A + diamond',    lambda s: s['dis'] and s['bk']=='A',        'Adia'),
      ('B + diamond',    lambda s: s['dis'] and s['bk']=='B',        'Bdia'),
      ('Prime K 20-50',  lambda s: s['prime'],                       'prime')]

def years(b, reg):
    d=[x for x in b['date'] if reg(x)]
    if len(d)<2: return 0
    return (d[-1]-d[0]).days/365.0*(len(d)/max(1,(d[-1]-d[0]).days/ (
        (b['date'][-1]-b['date'][0]).days/len(b['date']))))/1.0 or 0

def bull_days(b, reg):
    return sum(1 for x in b['date'] if reg(x))

def build(reg):
    rows={}; bases={}; store={}
    for name,p,tf in CH:
        sg,b=E.signals(p,regime=reg)
        store[name]=(sg,b,tf)
        allr=[E.fwd(b,s['ei'],60,tf) for s in sg]; allr=[x for x in allr if x]
        if len(allr)<8: continue
        base=round(100*sum(1 for x in allr if x['ret']>0)/len(allr)); bases[name]=base
        # years in regime, from bar count x days per bar
        dpb=(b['date'][-1]-b['date'][0]).days/max(1,len(b['date'])-1)
        yrs=bull_days(b,reg)*dpb/365.0
        for lbl,sel,key in TAGS:
            sub=[s for s in sg if sel(s)]
            f={d:[x for x in (E.fwd(b,s['ei'],d,tf) for s in sub) if x] for d in (10,20,30,60)}
            if len(f[60])<3: continue
            r60=f[60]; wr=100*sum(1 for x in r60 if x['ret']>0)/len(r60)
            rows[(name,lbl)]=dict(chart=name,tag=lbl,key=key,n=len(r60),
                per_yr=len(r60)/yrs if yrs>0 else 0, win=wr, edge=round(wr-base),
                u10=E.med([x['up'] for x in f[10]]), u30=E.med([x['up'] for x in f[30]]),
                u60=E.med([x['up'] for x in r60]), risk=E.med([x['risk'] for x in r60]),
                worst=min(x['risk'] for x in r60))
    return rows,bases,store

def confluence(store):
    troughs={n:[s['date'] for s in store[n][0]] for n in store}
    CTAG=[('any trough',lambda s:True),('A bucket',lambda s:s['bk']=='A'),
          ('B bucket',lambda s:s['bk']=='B'),('diamond',lambda s:s['dis'])]
    out=[]
    for tn,(sg,b,tf) in store.items():
        for lbl,sel,key in TAGS:
            sub=[s for s in sg if sel(s)]
            if len(sub)<8: continue
            for cn in store:
                if cn==tn: continue
                csg=store[cn][0]
                for clbl,csel in CTAG:
                    cd=[s['date'] for s in csg if csel(s)]
                    if not cd: continue
                    W=[];A=[]
                    for s in sub:
                        f=E.fwd(b,s['ei'],60,tf)
                        if not f: continue
                        (W if any(abs((s['date']-d).days)<=10 for d in cd) else A).append(f)
                    if len(W)<8 or len(A)<8: continue
                    w=100*sum(1 for x in W if x['ret']>0)/len(W)
                    a=100*sum(1 for x in A if x['ret']>0)/len(A)
                    out.append(dict(trade=tn,tag=lbl,conf=cn,ctag=clbl,n=len(W),
                        win=w,alone=a,gain=round(w-a),u30=E.med([x['up'] for x in W]),
                        u60=E.med([x['up'] for x in W]),risk=E.med([x['risk'] for x in W])))
    out.sort(key=lambda r:-r['gain'])
    return out

if __name__=='__main__':
    L,LB,LS=build(LIVE)
    H,HB,_ =build(E.bull)
    rows=[]
    for k,v in L.items():
        h=H.get(k)
        v=dict(v); v['h_win']=h['win'] if h else None; v['h_edge']=h['edge'] if h else None
        rows.append(v)
    rows.sort(key=lambda r:(-r['edge'],-r['n']))
    C=confluence(LS)
    json.dump(dict(rows=rows,bases=LB,hbases=HB,conf=C),open('odds4.json','w'),default=str)
    print('solo rows',len(rows),'confluence',len(C))
    print('live baselines',LB)
    print('hindsight baselines',HB)
    for r in rows[:6]:
        print('  %-7s %-21s n=%-3d %3.0f%% e%+d  (hindsight %3.0f%% e%+d)'%(
          r['chart'],r['tag'],r['n'],r['win'],r['edge'],r['h_win'] or 0,r['h_edge'] or 0))
