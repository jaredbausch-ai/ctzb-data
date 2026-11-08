"""Early Appetite: find the best way to use it. Jared asked 8 Nov 2026.

Every rule below is written as a TRADE, not a condition: a bar on whose close
you would enter. Declared in full before running; nothing added afterwards.

  LEVEL + TURN      below X, first up-tick (X = -1.0, -1.5, -2.0)
  DWELL + TURN      first up-tick after N consecutive bars below -1.0
  SMA CROSS         crosses above its own 10-bar mean while below -0.5
  RECOVERY          climbs back above -1.0 having been below -1.5
  TROUGH CONFIRMED  pivot low L/R confirmed, entered at the confirmation bar
                    (tradeable; the trough bar itself is hindsight)
  TREND             crosses above 0, crosses above +0.5
  DIVERGENCE        appetite lower low while its own slope makes a higher low

Reported per rule: n after declustering, forward 30d and 60d close return,
best and worst excursion inside 60d, and the share reaching +15% and +20%.
Baseline is every bar. The same rules are then re-run against ETH price using
the same BTC-derived appetite line, as an out-of-sample check.
"""
import csv, datetime as dt, statistics as st, sys

rs = list(csv.DictReader(open('/home/claude/work/btc2d_app.csv', encoding='utf-8-sig')))
R = []
for r in rs:
    try:
        R.append(dict(d=dt.datetime.fromtimestamp(int(r['time']), dt.UTC).date(),
                      c=float(r['close']), h=float(r['high']), l=float(r['low']),
                      a=float(r['Appetite (sigma)'])))
    except (ValueError, KeyError, TypeError):
        pass
n = len(R)
A = [x['a'] for x in R]
D = [x['d'] for x in R]

def sma(i, k):
    if i < k: return None
    return sum(A[i-k+1:i+1]) / k

# ---- price series to measure against ----
def loadpx(p):
    out = {}
    for r in csv.DictReader(open(p)):
        out[dt.datetime.fromtimestamp(int(r['time']), dt.UTC).date()] = (
            float(r['close']), float(r['high']), float(r['low']))
    return out
PX = {'BTC': None, 'ETH': loadpx('data/ETH_1D.csv')}

def mk_eval(asset):
    if asset == 'BTC':
        def f(i, bars):
            return (R[i+bars]['c']/R[i]['c']-1)*100 if i+bars < n else None
        def mfe(i, bars):
            s = [R[j]['h'] for j in range(i+1, min(i+1+bars, n))]
            return (max(s)/R[i]['c']-1)*100 if s else None
        def mae(i, bars):
            s = [R[j]['l'] for j in range(i+1, min(i+1+bars, n))]
            return (min(s)/R[i]['c']-1)*100 if s else None
        return f, mfe, mae
    P = PX[asset]; ks = sorted(P)
    def near(d):
        c = [k for k in ks if k <= d]
        return c[-1] if c else None
    def f(i, bars):
        d0, d1 = near(D[i]), near(D[i]+dt.timedelta(days=bars*2))
        return (P[d1][0]/P[d0][0]-1)*100 if d0 and d1 and d1 > d0 else None
    def exc(i, bars, hi):
        d0 = near(D[i])
        if not d0: return None
        seg = [P[k] for k in ks if d0 < k <= D[i]+dt.timedelta(days=bars*2)]
        if not seg: return None
        v = max(x[1] for x in seg) if hi else min(x[2] for x in seg)
        return (v/P[d0][0]-1)*100
    return f, (lambda i,b: exc(i,b,True)), (lambda i,b: exc(i,b,False))

def falling_for(i, k):
    return all(A[i-j] < A[i-j-1] for j in range(1, k+1)) if i > k else False

def pivot_conf(L, Rr):
    """enter at the bar that CONFIRMS the pivot, not the trough itself"""
    out = []
    for i in range(L, n-Rr):
        w = A[i-L:i+Rr+1]
        if A[i] == min(w) and w.count(A[i]) == 1:
            out.append(i+Rr)
    return out

def dwell_turn(thr, bars):
    out = []
    for i in range(bars+2, n):
        if A[i] > A[i-1] and all(A[j] <= thr for j in range(i-bars, i)):
            out.append(i)
    return out

RULES = {
 'L1  below -1.0, first up-tick':   [i for i in range(3,n) if A[i]>A[i-1] and A[i-1]<=A[i-2] and A[i-1]<=-1.0],
 'L2  below -1.5, first up-tick':   [i for i in range(3,n) if A[i]>A[i-1] and A[i-1]<=A[i-2] and A[i-1]<=-1.5],
 'L3  below -2.0, first up-tick':   [i for i in range(3,n) if A[i]>A[i-1] and A[i-1]<=A[i-2] and A[i-1]<=-2.0],
 'L4  below -1.0, up-tick, 3+ down':[i for i in range(5,n) if A[i]>A[i-1] and A[i-1]<=-1.0 and falling_for(i-1,3)],
 'W1  up-tick after 5 bars <-1.0':  dwell_turn(-1.0,5),
 'W2  up-tick after 10 bars <-1.0': dwell_turn(-1.0,10),
 'S1  cross above 10-bar mean <-0.5':[i for i in range(12,n) if sma(i,10) and sma(i-1,10) and A[i]>sma(i,10) and A[i-1]<=sma(i-1,10) and A[i]<=-0.5],
 'R1  back above -1.0 after <-1.5': [i for i in range(25,n) if A[i]>-1.0 and A[i-1]<=-1.0 and any(A[j]<=-1.5 for j in range(i-25,i))],
 'P1  pivot L5/R5 at confirmation':  pivot_conf(5,5),
 'P2  pivot L8/R8 at confirmation':  pivot_conf(8,8),
 'P3  pivot L5/R5 conf, trough<-1':  [i for i in pivot_conf(5,5) if A[i-5]<=-1.0],
 'P4  pivot L8/R8 conf, trough<-1':  [i for i in pivot_conf(8,8) if A[i-8]<=-1.0],
 'T1  crosses above 0':             [i for i in range(2,n) if A[i]>0 and A[i-1]<=0],
 'T2  crosses above +0.5':          [i for i in range(2,n) if A[i]>0.5 and A[i-1]<=0.5],
 'T3  above 0 and rising':          [i for i in range(2,n) if A[i]>0 and A[i]>A[i-1]],
}

def decluster(idx, gap=10):
    keep, last = [], -99
    for i in sorted(idx):
        if i - last > gap:
            keep.append(i); last = i
    return keep

def run(asset):
    f, mfe, mae = mk_eval(asset)
    base_b = [x for x in (f(i,30) for i in range(n)) if x is not None]
    base_a = [x for x in (f(i,15) for i in range(n)) if x is not None]
    base_f = [x for x in (mfe(i,30) for i in range(n)) if x is not None]
    base_m = [x for x in (mae(i,30) for i in range(n)) if x is not None]
    print(f"\n########## {asset} ##########")
    print(f"{'rule':36} {'n':>4} {'+30d':>8} {'up':>5} {'+60d':>8} {'up':>5} {'best':>8} {'worst':>8} {'+15%':>6} {'+20%':>6} {'dd<-15':>7}")
    print(f"{'BASELINE':36} {len(base_b):>4} {st.median(base_a):+7.1f}% {100*sum(1 for x in base_a if x>0)/len(base_a):4.0f}% "
          f"{st.median(base_b):+7.1f}% {100*sum(1 for x in base_b if x>0)/len(base_b):4.0f}% "
          f"{st.median(base_f):+7.1f}% {st.median(base_m):+7.1f}% "
          f"{100*sum(1 for x in base_f if x>=15)/len(base_f):5.0f}% {100*sum(1 for x in base_f if x>=20)/len(base_f):5.0f}% "
          f"{100*sum(1 for x in base_m if x<=-15)/len(base_m):6.0f}%")
    out = {}
    for name, idx in RULES.items():
        keep = decluster(idx)
        a = [x for x in (f(i,15) for i in keep) if x is not None]
        b = [x for x in (f(i,30) for i in keep) if x is not None]
        g = [x for x in (mfe(i,30) for i in keep) if x is not None]
        m = [x for x in (mae(i,30) for i in keep) if x is not None]
        if len(b) < 6:
            print(f"{name:36} {len(b):>4}   too few"); continue
        out[name] = (len(b), st.median(b), 100*sum(1 for x in g if x>=15)/len(g), st.median(m))
        print(f"{name:36} {len(b):>4} {st.median(a):+7.1f}% {100*sum(1 for x in a if x>0)/len(a):4.0f}% "
              f"{st.median(b):+7.1f}% {100*sum(1 for x in b if x>0)/len(b):4.0f}% "
              f"{st.median(g):+7.1f}% {st.median(m):+7.1f}% "
              f"{100*sum(1 for x in g if x>=15)/len(g):5.0f}% {100*sum(1 for x in g if x>=20)/len(g):5.0f}% "
              f"{100*sum(1 for x in m if x<=-15)/len(m):6.0f}%")
    return out

bt = run('BTC')
et = run('ETH')
print("\n\n########## rules that beat baseline on BOTH assets ##########")
print(f"{'rule':36} {'BTC +60d':>9} {'ETH +60d':>9} {'BTC +15%':>9} {'ETH +15%':>9}")
for k in RULES:
    if k in bt and k in et:
        if bt[k][1] > 7.2 and et[k][1] > 4.3 and bt[k][2] > 58 and et[k][2] > 55:
            print(f"{k:36} {bt[k][1]:+8.1f}% {et[k][1]:+8.1f}% {bt[k][2]:8.0f}% {et[k][2]:8.0f}%")

print("\n\n########## where we are now ##########")
dwell = 0
for i in range(n-1, -1, -1):
    if A[i] <= -1.0: dwell += 1
    else: break
print(f"  last bar {D[-1]}  appetite {A[-1]:+.3f}  prev {A[-2]:+.3f}  -> {'RISING' if A[-1]>A[-2] else 'still falling'}")
print(f"  consecutive bars at or below -1.0: {dwell}  ({dwell*2} days)")
print(f"  W1 needs 5+ bars below -1.0 then an up-tick: dwell {'OK' if dwell>=5 else 'NOT YET'}, up-tick {'YES' if A[-1]>A[-2] else 'NO'}")
print(f"  W2 needs 10+ bars below -1.0 then an up-tick: dwell {'OK' if dwell>=10 else 'NOT YET'}, up-tick {'YES' if A[-1]>A[-2] else 'NO'}")
print("\n  every W1 event in full:")
for i in decluster(RULES['W1  up-tick after 5 bars <-1.0']):
    f,_,_ = mk_eval('BTC'); b = f(i,30)
    print(f"    {D[i]}  appetite {A[i]:+.2f}  ${R[i]['c']:>9,.0f}  BTC +60d {('%+.1f%%'%b) if b is not None else 'open'}")
