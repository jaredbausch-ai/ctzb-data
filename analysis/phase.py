"""Hurst cycle PHASE at entry -- tested 27 Oct 2026, FAILED, kept for the reason why.

Phase = fraction of the measured period elapsed since the last CONFIRMED trough.
It cannot answer the question it was built for. A trough is only confirmed a
quarter-period after it happens, so the phase<0.2 bin -- "just past a cycle low",
exactly the region of interest -- is MATHEMATICALLY UNREACHABLE and comes back
empty, while 60% of rows pile into the top bin. Edges ran -7 to +2 across three
degrees. The lesson is not that cycles are useless here; it is that a backward-
looking phase measure is the wrong instrument. See proj.py for the one that works.
"""
import sys, os, datetime as dt
sys.path.insert(0,'/home/claude/ctzb-data'); sys.path.insert(0,'/home/claude/ctzb-data/analysis')
import numpy as np, engine as E, regimes as R, fld as F
from tagstats import bucket_end, measure

CH=['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']

def confirmed_troughs(bp, k):
    """Indices of local minima of bp, each paired with the bar it is CONFIRMED."""
    out=[]
    n=len(bp)
    for j in range(k, n-k):
        w=bp[j-k:j+k+1]
        if not np.all(np.isfinite(w)): continue
        if bp[j]==w.min() and bp[j]<bp[j-1]:
            out.append((j, j+k))        # trough bar, confirmation bar
    return out

def phase_series(b, target_days, tf_days):
    """phase in [0,1): fraction of the measured period elapsed since the last
    CONFIRMED trough of this degree. None where unknown."""
    tgt=target_days/tf_days
    lx=np.log(np.clip(np.asarray(b['close'],float),1e-9,None))
    bp=F._bandpass(lx, tgt*1.5, tgt*0.5)
    per=F.measure_period(b, target_days, tf_days)
    k=max(2,int(round(tgt*0.25)))
    tr=confirmed_troughs(bp,k)
    n=len(b['close']); out=[None]*n; ti=0; last=None
    for i in range(n):
        while ti<len(tr) and tr[ti][1]<=i:
            last=tr[ti][0]; ti+=1
        p=per[i] or tgt
        if last is not None and p:
            out[i]=min(0.999,(i-last)/p)
    return out

def run(target, label):
    gate=R.rsi_regime('data/BTC_2D.csv',8,13,60,41)
    rows=[]
    for ch in CH:
        a,tf=ch.split('_'); td=F.TF_DAYS[tf]
        sig,b=E.signals(f'data/{ch}.csv',regime=gate)
        day=E.load(f'data/{a}_1D.csv'); P={d:i for i,d in enumerate(day['date'])}; last=day['date'][-2]
        ph=phase_series(b,target,td)
        c=b['close']; ct=E.rsi(c,14); em=E.ema(ct,14)
        for s in sig:
            i=s['ei']; d0=bucket_end(b['date'],i)
            if d0 is None or d0 not in P or d0+dt.timedelta(days=61)>last: continue
            if ph[i] is None: continue
            m=measure(day,P,d0,s['entry'],60)
            if not m: continue
            g=ct[i]-em[i] if (ct[i] is not None and em[i] is not None) else None
            rows.append(dict(ch=ch,a=a,yr=d0.year,ph=ph[i],win=m['up']>=20,d30=m['dd']<=-30,
                             g5=(g is not None and g>5)))
    if len(rows)<100: print(f'{label}: only {len(rows)} rows'); return None
    W=100*sum(r['win'] for r in rows)/len(rows)
    print(f'\n{label}  n={len(rows)}  baseline win {W:.0f}%  -30% {100*sum(r["d30"] for r in rows)/len(rows):.0f}%')
    print(f'  {"phase bin":<14}{"n":>6}{"win":>7}{"edge":>7}{"-30%":>7}')
    for lo,hi in ((0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.0)):
        S=[r for r in rows if lo<=r['ph']<hi]
        if len(S)<20: continue
        w=100*sum(r['win'] for r in S)/len(S)
        print(f'  {f"{lo:.1f}-{hi:.1f}":<14}{len(S):>6}{w:>6.0f}%{w-W:>+7.0f}{100*sum(r["d30"] for r in S)/len(S):>6.0f}%')
    return rows


if __name__ == '__main__':
    for tgt,lab in ((F.NOMINAL['40D'],'40D degree'),(F.NOMINAL['80D'],'80D degree'),(F.NOMINAL['160D'],'160D degree')):
        run(tgt,lab)
