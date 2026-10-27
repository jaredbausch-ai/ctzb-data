"""Confidence battery for the 160D projected-low feature. 27 Oct 2026.

Four tests, in the order they would change my mind:

1 PLACEBO   Shift every projected trough date by a random offset and re-score,
            many times. If a shuffled projection scores like the real one, the
            feature is measuring the shape of the signal distribution rather than
            the cycle, and the whole thing is dead.
2 GRADIENT  Win rate against distance-to-projected-low in fine bins. A real cycle
            effect should decay smoothly. A cliff at exactly the 0.2 threshold I
            happened to choose would mean I fitted the threshold.
3 HOLDOUT   Discovery 2016-2021 / holdout 2022-2025. Fixed rule, applied blind.
4 PARAMS    Vary the confirmation lag k and the bandpass width. If the edge only
            exists at the settings I happened to write, it is fitted.
"""
import sys, os, random, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, engine as E, regimes as R, fld as F
from tagstats import bucket_end, measure
from phase import confirmed_troughs

CH = ['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']
GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)


def dists(b, target_days, tf_days, kmult=0.25, bandlo=1.5, bandhi=0.5, jitter=None, rng=None):
    tgt = target_days/tf_days
    lx = np.log(np.clip(np.asarray(b['close'],float),1e-9,None))
    bp = F._bandpass(lx, tgt*bandlo, tgt*bandhi)
    per = F.measure_period(b, target_days, tf_days)
    k = max(2, int(round(tgt*kmult)))
    tr = confirmed_troughs(bp, k)
    n=len(b['close']); out=[None]*n; ti=0; last=None
    for i in range(n):
        while ti<len(tr) and tr[ti][1]<=i:
            last=tr[ti][0]; ti+=1
        p=per[i] or tgt
        if last is None or not p: continue
        base = last + (rng.uniform(-p/2, p/2) if jitter else 0.0)
        nxt = base + p
        while nxt < i - p*0.5: nxt += p
        out[i]=(nxt-i)/p
    return out


def rows_for(**kw):
    out=[]
    for ch in CH:
        a,tf = ch.split('_'); td=F.TF_DAYS[tf]
        sig,b = E.signals(f'data/{ch}.csv', regime=GATE)
        day=E.load(f'data/{a}_1D.csv'); P={d:i for i,d in enumerate(day['date'])}; last=day['date'][-2]
        ds = dists(b, F.NOMINAL['160D'], td, **kw)
        for s in sig:
            i=s['ei']; d0=bucket_end(b['date'], i)
            if d0 is None or d0 not in P or d0+dt.timedelta(days=61)>last or ds[i] is None: continue
            m=measure(day,P,d0,s['entry'],60)
            if not m: continue
            out.append(dict(ch=ch,a=a,yr=d0.year,d=ds[i],win=m['up']>=20,d30=m['dd']<=-30))
    return out

def W(S): return 100*sum(r['win'] for r in S)/len(S) if S else float('nan')
def edge(rows, thr=0.2):
    A=[r for r in rows if r['d']<thr]; B=[r for r in rows if r['d']>=thr]
    return (W(A)-W(B)) if (len(A)>=30 and len(B)>=30) else float('nan')


def main():
    real = rows_for()
    e0 = edge(real)
    print(f'REAL  n={len(real)}  edge {e0:+.1f}\n')

    print('1 PLACEBO: projected troughs jittered by a random offset, 40 draws')
    rng = random.Random(20261027)
    es=[]
    for t in range(40):
        r = rows_for(jitter=True, rng=rng)
        v = edge(r)
        if v==v: es.append(v)
    es.sort()
    beat = sum(1 for v in es if v >= e0)
    print(f'   shuffled edges: median {es[len(es)//2]:+.1f}  p5 {es[max(0,len(es)//20)]:+.1f}  '
          f'p95 {es[min(len(es)-1,len(es)*19//20)]:+.1f}  max {es[-1]:+.1f}')
    print(f'   real edge {e0:+.1f} beaten by {beat}/{len(es)} shuffles  -> empirical p = {beat/len(es):.3f}\n')

    print('2 GRADIENT: win rate by distance to projected low (fine bins)')
    print(f'   {"bin":<14}{"n":>6}{"win":>7}')
    for lo,hi in ((-0.5,0.0),(0.0,0.1),(0.1,0.2),(0.2,0.3),(0.3,0.45),(0.45,0.6),(0.6,1.1)):
        S=[r for r in real if lo<=r['d']<hi]
        if len(S)<25: continue
        print(f'   {f"{lo:+.2f} to {hi:+.2f}":<14}{len(S):>6}{W(S):>6.0f}%')

    print('\n3 HOLDOUT: discovery 2016-2021, holdout 2022-2025, same fixed rule')
    for nm,sel in (('discovery', lambda r: r['yr']<=2021), ('holdout', lambda r: r['yr']>=2022)):
        S=[r for r in real if sel(r)]
        A=[r for r in S if r['d']<0.2]; B=[r for r in S if r['d']>=0.2]
        print(f'   {nm:<10} n={len(S):<5} due {len(A):<4} win {W(A):>3.0f}%   not {len(B):<4} win {W(B):>3.0f}%   edge {W(A)-W(B):+.0f}')
        for a in ('ETH','BTC'):
            A2=[r for r in A if r['a']==a]; B2=[r for r in B if r['a']==a]
            if len(A2)>=20 and len(B2)>=20:
                print(f'     {a}  due {len(A2):<4} {W(A2):>3.0f}%   not {len(B2):<4} {W(B2):>3.0f}%   edge {W(A2)-W(B2):+.0f}')

    print('\n4 PARAMETERS: does the edge survive different settings?')
    print(f'   {"setting":<30}{"n":>6}{"edge":>8}')
    print(f'   {"as written (k=.25, band 1.5/0.5)":<30}{len(real):>6}{e0:>+8.1f}')
    for nm,kw in (('confirm lag k=0.15', dict(kmult=0.15)), ('confirm lag k=0.35', dict(kmult=0.35)),
                  ('band 1.3/0.7', dict(bandlo=1.3, bandhi=0.7)), ('band 2.0/0.4', dict(bandlo=2.0, bandhi=0.4)),
                  ('threshold 0.15', dict()), ('threshold 0.30', dict())):
        r = real if nm.startswith('threshold') else rows_for(**kw)
        thr = 0.15 if nm=='threshold 0.15' else (0.30 if nm=='threshold 0.30' else 0.2)
        print(f'   {nm:<30}{len(r):>6}{edge(r,thr):>+8.1f}')


if __name__ == '__main__':
    main()
