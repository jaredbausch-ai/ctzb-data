import sys, datetime as dt
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E

def pivlows(lo, L=3, R=3):
    out=[]
    for i in range(L, len(lo)-R):
        w=lo[i-L:i+R+1]
        if lo[i]==min(w) and w.count(lo[i])==1: out.append(i)
    return out

for tf,tfd in (('ETH_1D',1),('ETH_2D',2),('ETH_3D',3)):
    b=E.load(f'data/{tf}.csv')
    c,lo,d = b['close'], b['low'], b['date']
    r=E.rsi(c,14)
    n=len(c)
    print(f"\n===== {tf}  bars={n}  last={d[-1]}  close={c[-1]:.2f}  rsi={r[-1]:.2f}")
    ps=[i for i in pivlows(lo) if i>n-90]
    print(" recent confirmed pivot lows (L3/R3):")
    for i in ps[-5:]:
        print(f"   {d[i]}  low {lo[i]:8.2f}  close {c[i]:8.2f}  rsi {r[i]:6.2f}")
    # current leg: lowest low since the last confirmed pivot low
    if ps:
        last=ps[-1]
        seg=range(last+1,n)
        if seg:
            cur=min(seg,key=lambda i:lo[i])
            print(f" lowest low since that pivot: {d[cur]} low {lo[cur]:.2f} rsi {r[cur]:.2f}")
            print(f"   price {'LOWER' if lo[cur]<lo[last] else 'higher'} low ({lo[cur]-lo[last]:+.2f})"
                  f"   rsi {'HIGHER' if r[cur]>r[last] else 'lower'} low ({r[cur]-r[last]:+.2f})"
                  f"   -> {'BULL DIV' if (lo[cur]<lo[last] and r[cur]>r[last]) else 'no div'}")
    # what close today keeps rsi above the prior pivot's rsi
    if ps:
        last=ps[-1]; target=r[last]
        src=c[:-1]
        lo_,hi_=c[-1]*0.80, c[-1]*1.20
        for _ in range(60):
            mid=(lo_+hi_)/2
            rr=E.rsi(src+[mid],14)[-1]
            if rr<target: lo_=mid
            else: hi_=mid
        print(f" close needed for RSI to hold above prior pivot RSI {target:.2f}: {(lo_+hi_)/2:.2f}")
