import json, statistics as st
R=[r for r in json.load(open('/home/claude/ctzb-data/analysis/ctema.json')) if r['up60'] is not None]
TOP=[('C  gap > +5',       lambda r: r['gap']>5),
     ('U  above AND prime',lambda r: r['above'] and r['prime']),
     ('T  above AND diamond',lambda r: r['above'] and r['dis']),
     ('A  CT above EMA',   lambda r: r['above'])]
def t20(S): return sum(1 for r in S if r['up60']>=20)/len(S)*100 if S else None

print('PER-CHART BREAKDOWN of the three standouts  (+20% hit rate in 60d, feature vs that chart baseline)')
print(f"{'chart':<9}{'base n':>7}{'base':>7}", end='')
for nm,_ in TOP[:3]: print(f"{nm.split()[0]:>16}", end='')
print()
for ch in ['ETH 1D','ETH 2D','ETH 3D','ETH 5D','ETH 1W','BTC 1D','BTC 2D','BTC 3D','BTC 5D']:
    S=[r for r in R if r['ch']==ch]
    if not S: continue
    print(f"{ch:<9}{len(S):>7}{t20(S):>6.0f}%", end='')
    for nm,fn in TOP[:3]:
        G=[r for r in S if fn(r)]
        print(f"{(f'{t20(G):.0f}% (n={len(G)})' if len(G)>=5 else f'- (n={len(G)})'):>16}", end='')
    print()
print()
print('YEAR-BY-YEAR STABILITY  (edge in +20% hit rate vs that year\'s baseline, pooled all charts)')
yrs=sorted({r['year'] for r in R})
print(f"{'year':<7}{'n':>5}{'base':>7}", end='')
for nm,_ in TOP: print(f"{nm.split()[0]:>14}", end='')
print()
agg={nm:[] for nm,_ in TOP}
for y in yrs:
    S=[r for r in R if r['year']==y]
    if len(S)<15: continue
    bb=t20(S)
    print(f"{y:<7}{len(S):>5}{bb:>6.0f}%", end='')
    for nm,fn in TOP:
        G=[r for r in S if fn(r)]
        if len(G)<5: print(f"{'-':>14}", end=''); continue
        e=t20(G)-bb; agg[nm].append(e)
        print(f"{f'{e:+.0f} (n={len(G)})':>14}", end='')
    print()
print()
print('STABILITY SUMMARY')
for nm,_ in TOP:
    v=agg[nm]
    if not v: continue
    pos=sum(1 for x in v if x>0)
    print(f"   {nm:<24} years tested {len(v):>2}   positive in {pos:>2} ({pos/len(v)*100:>3.0f}%)   mean edge {st.mean(v):>+6.1f}   median {st.median(v):>+6.1f}   worst {min(v):>+6.0f}")
print()
print('TRUE WALK-FORWARD: take the rule in year Y only if its edge was positive on all data BEFORE Y')
for nm,fn in TOP:
    took=[];skipped=0
    for y in yrs:
        prior=[r for r in R if r['year']<y]
        if len(prior)<60: continue
        pg=[r for r in prior if fn(r)]
        if len(pg)<15: continue
        if t20(pg)-t20(prior) <= 0: skipped+=1; continue
        cur=[r for r in R if r['year']==y and fn(r)]
        took.extend(cur)
    if not took: print(f'   {nm:<24} never qualified'); continue
    allyr=[r for r in R if r['year']>=min(yrs)+2]
    print(f"   {nm:<24} OOS n={len(took):<4} +20% {t20(took):>5.1f}%   vs all-signal baseline {t20(allyr):>5.1f}%   edge {t20(took)-t20(allyr):>+5.1f}   (years skipped: {skipped})")
