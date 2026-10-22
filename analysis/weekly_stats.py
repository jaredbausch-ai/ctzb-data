import sys, datetime as dt, statistics as st
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E_, regimes as R

PATH='data/tradingview/ETH_1W_tv.csv'
HOR=[30,60,90,180,365]
TOUCH=[10,20,30,50]
LEV={"2x":0.50,"3x":0.3333,"3.3x":0.30,"5x":0.20}
TG=[5,10,15,20]
TAGS=[
  ("ALL troughs",        lambda s: True),
  ("A  trough <40",      lambda s: s['bk']=="A"),
  ("B  trough 40-55",    lambda s: s['bk']=="B"),
  ("C  trough 55-65",    lambda s: s['bk']=="C"),
  ("D  trough >65",      lambda s: s['bk']=="D"),
  ("Any diamond",        lambda s: s['dis']),
  ("GOLD diamond <50",   lambda s: s['dis'] and s['strong']),
  ("HOLLOW diamond >=50",lambda s: s['dis'] and not s['strong']),
  ("Diamond + prime dot",lambda s: s['dis'] and s['prime']),
  ("A + diamond",        lambda s: s['bk']=="A" and s['dis']),
  ("B + diamond",        lambda s: s['bk']=="B" and s['dis']),
  ("Prime K 20-50",      lambda s: s['prime']),
]
def med(xs): return round(st.median(xs),1) if xs else None
def pc(k,n): return int(round(k/n*100)) if n else None

def build(regime):
    sigs,b = E_.signals(PATH, regime=regime, ungated=True)
    c,hi,lo,dates=b['close'],b['high'],b['low'],b['date']
    n=len(c); last=dates[-1]
    recs=[]
    for s in sigs:
        ei=s['ei']; e=c[ei]; d0=dates[ei]
        r=dict(tag=s,h={})
        for H in HOR:
            w=[j for j in range(ei+1,n) if dates[j]<=d0+dt.timedelta(days=H)]
            if not w or last < d0+dt.timedelta(days=H):
                r['h'][H]=None; continue
            best=max(hi[j]/e-1 for j in w)
            pk=max(w,key=lambda j: hi[j])
            wc=min(c[k] for k in range(ei,pk+1))
            r['h'][H]=dict(up=best*100, ret=(c[w[-1]]/e-1)*100,
                           risk=(wc/e-1)*100, days=(dates[pk]-d0).days,
                           touch={T:(best>=T/100) for T in TOUCH})
        r['path']=[((dates[j]-d0).days, hi[j]/e-1, lo[j]/e-1) for j in range(ei+1,n)]
        recs.append(r)
    return recs

def race(recs, tgt, liq):
    """P(reach +tgt% before a -liq% adverse move), and median days to it."""
    win=0; tot=0; days=[]
    for r in recs:
        if not r['path']: continue
        tot+=1; hit=None
        for d,up,dn in r['path']:
            if dn <= -liq: break
            if up >= tgt/100: hit=d; break
        if hit is not None: win+=1; days.append(hit)
    return pc(win,tot), tot, (int(round(st.median(days))) if days else None)

for label,regime in [("REGIME-GATED  rsi_regime(BTC_2D,8,13,60,41)", R.rsi_regime('data/BTC_2D.csv',8,13,60,41)),
                     ("UNGATED  every weekly trough in ETH history", lambda d: True)]:
    recs=build(regime)
    print("="*118)
    print(f"ETH 1W — {label}")
    print("="*118)
    hdr=f"{'tag':<22}{'n':>4}"
    for H in HOR: hdr+=f"{('+'+str(H)+'d'):>26}"
    print(hdr)
    print(f"{'':<22}{'':>4}" + "".join(f"{'  n  +10/+20/+30/+50  med':>26}" for H in HOR))
    print("-"*118)
    for name,fn in TAGS:
        sub=[r for r in recs if fn(r['tag'])]
        if not sub: continue
        line=f"{name:<22}{len(sub):>4}"
        for H in HOR:
            hs=[r['h'][H] for r in sub if r['h'][H]]
            if not hs: line+=f"{'--':>26}"; continue
            t=[pc(sum(1 for h in hs if h['touch'][T]),len(hs)) for T in TOUCH]
            line+=f"{len(hs):>5}{t[0]:>4}/{t[1]:>3}/{t[2]:>3}/{t[3]:>3}{med([h['up'] for h in hs]):>8.0f}%"
        print(line)
    print()
    print(f"  drawdown to the peak, and worst single outcome (90d window)")
    for name,fn in TAGS:
        sub=[r for r in recs if fn(r['tag']) and r['h'][90]]
        if not sub: continue
        rk=[r['h'][90]['risk'] for r in sub]
        dd=[r['h'][90]['days'] for r in sub]
        print(f"    {name:<22} n={len(sub):<3} med dd {med(rk):>6.1f}%   worst {min(rk):>6.1f}%   med days to peak {int(round(st.median(dd))):>4}")
    print()
    print("  ENTRY QUALITY — P(reach target before liquidation), median days")
    print(f"    {'tag':<22}" + "".join(f"{('  '+L):>30}" for L in LEV))
    print(f"    {'':<22}" + "".join(f"{'+5 / +10 / +15 / +20':>30}" for L in LEV))
    for name,fn in TAGS:
        sub=[r for r in recs if fn(r['tag'])]
        if len(sub)<4: continue
        line=f"    {name:<22}"
        for L,liq in LEV.items():
            cells=[]
            for t in TG:
                p,tot,d=race(sub,t,liq)
                cells.append(f"{p if p is not None else 0:>3}")
            line+=f"{'/'.join(cells):>30}"
        print(line)
    print()
