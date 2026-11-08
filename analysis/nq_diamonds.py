"""Filled A diamonds on NASDAQ (CME_MINI NQ1!, daily). Jared asked 8 Nov 2026.

Filled A diamond = engine.signals bucket 'A' with dis=True. Bucket A is CT < 40
and the fill rule is ct < zMid(50), so every A diamond is filled.

No regime gate: the project gate is BTC-derived and meaningless on an index.
No win-rate threshold is invented here -- the repo's +20%/-30% are calibrated to
crypto. Reported as the forward-return distribution and excursions instead.

Entry = close of the confirmation bar (ei = ti + 3), per CONTEXT.
"""
import sys, statistics as st
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E

PATH='/home/claude/work/nq1d_tv.csv'
WARMUP='2017-05-03'
HOR=[10,20,40,60]

sigs,b = E.signals(PATH, regime=lambda d: True)
c,hi,lo,d = b['close'],b['high'],b['low'],b['date']
n=len(c)
sigs=[s for s in sigs if str(s['date'])>=WARMUP]

def outcomes(ei):
    o={}
    for h in HOR:
        o[h] = (c[ei+h]/c[ei]-1)*100 if ei+h<n else None
    seg_h=hi[ei+1:ei+61]; seg_l=lo[ei+1:ei+61]
    o['mfe']=(max(seg_h)/c[ei]-1)*100 if len(seg_h)==60 else None
    o['mae']=(min(seg_l)/c[ei]-1)*100 if len(seg_l)==60 else None
    return o

def block(name, rows):
    done=[r for r in rows if r[1][60] is not None]
    print(f"\n{name}   n={len(rows)}  (with full 60-bar window: {len(done)})")
    if not done: return
    print(f"  {'horizon':>9} {'median':>8} {'mean':>8} {'% up':>6} {'worst':>8} {'best':>8}")
    for h in HOR:
        v=[r[1][h] for r in done if r[1][h] is not None]
        print(f"  {str(h)+' bars':>9} {st.median(v):+8.2f} {st.mean(v):+8.2f} "
              f"{100*sum(1 for x in v if x>0)/len(v):5.0f}% {min(v):+8.2f} {max(v):+8.2f}")
    mfe=[r[1]['mfe'] for r in done]; mae=[r[1]['mae'] for r in done]
    print(f"  {'MFE 60':>9} {st.median(mfe):+8.2f} {st.mean(mfe):+8.2f}")
    print(f"  {'MAE 60':>9} {st.median(mae):+8.2f} {st.mean(mae):+8.2f}"
          f"   worse than -5%: {100*sum(1 for x in mae if x<=-5)/len(mae):.0f}%"
          f"   worse than -10%: {100*sum(1 for x in mae if x<=-10)/len(mae):.0f}%")

fA=[(s,outcomes(s['ei'])) for s in sigs if s['bk']=='A' and s['dis']]
allA=[(s,outcomes(s['ei'])) for s in sigs if s['bk']=='A']
alls=[(s,outcomes(s['ei'])) for s in sigs]
base=[(None,outcomes(i)) for i in range(60,n-61,5)]

print(f"NQ1! daily  {d[0]} -> {d[-1]}   {n} bars   signals after warm-up: {len(sigs)}")
block("FILLED A DIAMONDS", fA)
block("all bucket A (diamond or not)", allA)
block("every signal", alls)
block("unconditional baseline (every 5th bar)", base)

print("\nfilled A diamonds, by year")
print(f"  {'year':>6} {'n':>3} {'med20':>8} {'med60':>8} {'%up60':>6} {'medMAE':>8}")
ys=sorted({s['date'].year for s,_ in fA})
for y in ys:
    g=[r for r in fA if r[0]['date'].year==y and r[1][60] is not None]
    if not g: 
        print(f"  {y:>6} {sum(1 for r in fA if r[0]['date'].year==y):>3}   (window not complete)"); continue
    v20=[r[1][20] for r in g]; v60=[r[1][60] for r in g]; mae=[r[1]['mae'] for r in g]
    print(f"  {y:>6} {len(g):>3} {st.median(v20):+8.2f} {st.median(v60):+8.2f} "
          f"{100*sum(1 for x in v60 if x>0)/len(v60):5.0f}% {st.median(mae):+8.2f}")

print("\nevery filled A diamond")
print(f"  {'trough':12} {'entry bar':12} {'entry':>10} {'+20b%':>7} {'+60b%':>7} {'MAE60':>7} {'MFE60':>7}")
for s,o in fA:
    f=lambda x: f"{x:7.2f}" if x is not None else "      -"
    print(f"  {str(s['date']):12} {str(s['edate']):12} {s['entry']:10,.2f} {f(o[20])} {f(o[60])} {f(o['mae'])} {f(o['mfe'])}")
