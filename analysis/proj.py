"""Hurst FORWARD projection -- tested 27 Oct 2026, WORKS at the 160D degree.

projected_next = last CONFIRMED trough + measured period, everything known at the
entry bar. dist = (projected_next - i) / period; 0 means a trough of that degree
is due now. This is what Hurst is actually for, and it is the question
Jared asked after the FLD test came back negative: not "where is price relative
to the line" but "is a larger-degree low due, and does that make the small prints
real". The edge strengthens with degree -- 40D +4, 80D +3, 160D +12 -- and only
the 160D is positive on all eight charts.
"""
import sys, os, datetime as dt
sys.path.insert(0,'/home/claude/ctzb-data'); sys.path.insert(0,'/home/claude/ctzb-data/analysis')
import numpy as np, engine as E, regimes as R, fld as F
from tagstats import bucket_end, measure
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase import confirmed_troughs

CH=['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']

def dist_series(b,target_days,tf_days):
    tgt=target_days/tf_days
    lx=np.log(np.clip(np.asarray(b['close'],float),1e-9,None))
    bp=F._bandpass(lx,tgt*1.5,tgt*0.5)
    per=F.measure_period(b,target_days,tf_days)
    k=max(2,int(round(tgt*0.25)))
    tr=confirmed_troughs(bp,k)
    n=len(b['close']); out=[None]*n; ti=0; last=None
    for i in range(n):
        while ti<len(tr) and tr[ti][1]<=i:
            last=tr[ti][0]; ti+=1
        p=per[i] or tgt
        if last is None or not p: continue
        nxt=last+p
        while nxt<i-p*0.5: nxt+=p          # roll forward if the projection lapsed
        out[i]=(nxt-i)/p                    # in periods; 0 = due now
    return out

def run(target,label):
    gate=R.rsi_regime('data/BTC_2D.csv',8,13,60,41)
    rows=[]
    for ch in CH:
        a,tf=ch.split('_'); td=F.TF_DAYS[tf]
        sig,b=E.signals(f'data/{ch}.csv',regime=gate)
        day=E.load(f'data/{a}_1D.csv'); P={d:i for i,d in enumerate(day['date'])}; last=day['date'][-2]
        ds=dist_series(b,target,td); c=b['close']; ct=E.rsi(c,14); em=E.ema(ct,14)
        for s in sig:
            i=s['ei']; d0=bucket_end(b['date'],i)
            if d0 is None or d0 not in P or d0+dt.timedelta(days=61)>last or ds[i] is None: continue
            m=measure(day,P,d0,s['entry'],60)
            if not m: continue
            g=ct[i]-em[i] if (ct[i] is not None and em[i] is not None) else None
            rows.append(dict(ch=ch,a=a,yr=d0.year,d=ds[i],win=m['up']>=20,d30=m['dd']<=-30,
                             g5=(g is not None and g>5)))
    W=100*sum(r['win'] for r in rows)/len(rows)
    print(f'\n{label}  n={len(rows)}  baseline win {W:.0f}%')
    print(f'  {"periods to next":<18}{"n":>6}{"win":>7}{"edge":>7}{"-30%":>7}')
    for lo,hi,nm in ((-0.5,0.1,'due / overdue'),(0.1,0.3,'0.1-0.3'),(0.3,0.5,'0.3-0.5'),
                     (0.5,0.7,'0.5-0.7'),(0.7,1.1,'0.7-1.0 (just had one)')):
        S=[r for r in rows if lo<=r['d']<hi]
        if len(S)<20: continue
        w=100*sum(r['win'] for r in S)/len(S)
        print(f'  {nm:<18}{len(S):>6}{w:>6.0f}%{w-W:>+7.0f}{100*sum(r["d30"] for r in S)/len(S):>6.0f}%')
    near=[r for r in rows if r['d']<0.2]
    if len(near)>=40:
        far=[r for r in rows if r['d']>=0.2]
        wn=100*sum(r['win'] for r in near)/len(near); wf=100*sum(r['win'] for r in far)/len(far)
        print(f'  -> trough DUE (<0.2 periods): n={len(near)} win {wn:.0f}%  vs rest {wf:.0f}%  edge {wn-wf:+.0f}')
        print('     per chart: ', end='')
        for ch in CH:
            A=[r for r in near if r['ch']==ch]; B=[r for r in far if r['ch']==ch]
            if len(A)>=8 and len(B)>=8:
                e=100*sum(r['win'] for r in A)/len(A)-100*sum(r['win'] for r in B)/len(B)
                print(f'{ch.split("_")[0][0]}{ch.split("_")[1]} {e:+.0f}  ', end='')
        print()
    return rows

if __name__ == '__main__':
    for tgt, lab in ((F.NOMINAL['40D'], '40D'), (F.NOMINAL['80D'], '80D'), (F.NOMINAL['160D'], '160D')):
        run(tgt, lab)
