import sys, datetime as dt, statistics as st
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E, regimes as R

TFS=['1D','2D','3D','5D','1W','8D','10D','12D','15D','1M']
gate=R.rsi_regime('data/BTC_2D.csv',8,13,60,41)

# every gated signal on every chart, for the confluence test
universe=[]
for tf in TFS:
    sig,_=E.signals(f'data/tradingview/ETH_{tf}_tv.csv',regime=gate,ungated=True)
    for s in sig: universe.append((tf,s['edate']))

sig,b=E.signals('data/tradingview/ETH_1D_tv.csv',regime=gate,ungated=True)
C,H,L,D=b['close'],b['high'],b['low'],b['date']
n=len(C)

def conf_back(tf,ed,w=10):
    return len({t for t,d in universe if t!=tf and 0 <= (ed-d).days <= w})

def profile(s):
    """Time-to-resolution from the entry close."""
    ei=s['ei']; e=C[ei]
    out=dict(e=e)
    # days until first CLOSE outside +/-5%
    res=None; side=None
    for j in range(ei+1,n):
        r=C[j]/e-1
        if r>=0.05: res=(D[j]-D[ei]).days; side='up'; break
        if r<=-0.05: res=(D[j]-D[ei]).days; side='down'; break
    out['res_days']=res; out['res_side']=side
    # days to first touch +10% on highs
    t10=None
    for j in range(ei+1,n):
        if H[j]/e-1>=0.10: t10=(D[j]-D[ei]).days; break
    out['t10']=t10
    # 90d peak and its day
    end=D[ei]+dt.timedelta(days=90)
    w=[j for j in range(ei+1,n) if D[j]<=end]
    if w and D[-1]>=end:
        pk=max(w,key=lambda j:H[j])
        out['pk_days']=(D[pk]-D[ei]).days
        out['pk_up']=(H[pk]/e-1)*100
        out['dd']=(min(C[k] for k in range(ei,pk+1))/e-1)*100
        out['ret90']=(C[w[-1]]/e-1)*100
    return out

def cluster_rank(i):
    """how many 1D signals in the 14 days before this one, inclusive of self"""
    d=sig[i]['edate']
    return sum(1 for k in range(0,i+1) if 0 <= (d-sig[k]['edate']).days <= 14)

sets={}
sets['All ETH 1D signals']=list(range(len(sig)))
sets['Zero confluence (no other chart within 10d)']=[i for i,s in enumerate(sig) if conf_back('1D',s['edate'])==0]
sets['3rd+ signal in a 14-day cluster']=[i for i,s in enumerate(sig) if cluster_rank(i)>=3]
sets['Bucket A, filled, plain (no diamond/prime)']=[i for i,s in enumerate(sig) if s['bk']=='A' and s['ct']<50 and not s['dis'] and not s['prime']]
sets['Zero confluence AND in a cluster']=[i for i,s in enumerate(sig) if conf_back('1D',s['edate'])==0 and cluster_rank(i)>=3]

def show(name, idxs):
    ps=[profile(sig[i]) for i in idxs]
    res=[p['res_days'] for p in ps if p['res_days'] is not None]
    up=[p for p in ps if p['res_side']=='up']; dn=[p for p in ps if p['res_side']=='down']
    t10=[p['t10'] for p in ps if p['t10'] is not None]
    pk=[p['pk_days'] for p in ps if 'pk_days' in p]
    pkup=[p['pk_up'] for p in ps if 'pk_up' in p]
    dd=[p['dd'] for p in ps if 'dd' in p]
    r90=[p['ret90'] for p in ps if 'ret90' in p]
    print(f'--- {name}   n={len(ps)}')
    if res:
        print(f'    days chopping inside +/-5% before resolving : mean {st.mean(res):.0f}  median {st.median(res):.0f}  '
              f'quartiles {sorted(res)[len(res)//4]}/{sorted(res)[3*len(res)//4]}')
    print(f'    resolved UP first {len(up)} ({len(up)/max(1,len(up)+len(dn))*100:.0f}%)   DOWN first {len(dn)} ({len(dn)/max(1,len(up)+len(dn))*100:.0f}%)')
    if t10: print(f'    days to first touch +10%                   : mean {st.mean(t10):.0f}  median {st.median(t10):.0f}   ({len(t10)}/{len(ps)} ever got there)')
    if pk:  print(f'    days to the 90-day peak                    : mean {st.mean(pk):.0f}  median {st.median(pk):.0f}')
    if pkup:print(f'    size of that peak                          : mean {st.mean(pkup):+.1f}%  median {st.median(pkup):+.1f}%')
    if dd:  print(f'    drawdown before it                         : mean {st.mean(dd):+.1f}%  median {st.median(dd):+.1f}%  worst {min(dd):+.1f}%')
    if r90: print(f'    where it closed at 90 days                 : mean {st.mean(r90):+.1f}%  median {st.median(r90):+.1f}%')
    print()

print(f"MEASURED FROM: the entry close, which for today's 1D signal is $2,446.62 on 20 Oct.")
print(f"All day counts are calendar days from that close. Upside uses intrabar highs; resolution uses closes.")
print()
for k,v in sets.items(): show(k,v)
