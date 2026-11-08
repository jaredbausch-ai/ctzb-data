"""BTC MVRV as a free stand-in for Glassnode's percent-supply-in-profit.

Jared asked 8 Nov 2026 after a post claiming 58.3% supply in profit marks a
historic accumulation zone.

Source: Coin Metrics community data, free, no key:
    git clone --depth 1 --filter=blob:none --sparse https://github.com/coinmetrics/data
    git sparse-checkout set --no-cone --skip-checks csv/btc.csv
Pass the path to csv/btc.csv as argv[1].

MVRV = market cap / realised cap. It is NOT percent supply in profit -- it is
the closest metric available without a paid Glassnode or CryptoQuant key.
Community data lags; as of this run it ended 2026-05-24.

Declared before running: quintile the MVRV distribution, report forward 60d,
180d and 365d median return and hit rate against the unconditional baseline,
on 2015+ and 2019+ separately.
"""
import csv, sys, statistics as st

rs=[r for r in csv.DictReader(open(sys.argv[1])) if r['CapMVRVCur'] and r['PriceUSD']]
d=[(r['time'][:10],float(r['CapMVRVCur']),float(r['PriceUSD'])) for r in rs]
CUR=float(sys.argv[2]) if len(sys.argv)>2 else d[-1][1]

print(f"MVRV {d[0][0]} -> {d[-1][0]}   n={len(d)}   latest {d[-1][1]:.3f} @ ${d[-1][2]:,.0f}\n")
print("MVRV at the lows the post points to:")
for lab,dt_ in [('2016 low','2016-01-15'),('2018-19 low','2018-12-15'),('2020 covid','2020-03-13'),
                ('2022 Jun','2022-06-18'),('2022 Nov','2022-11-21')]:
    m=[x for x in d if x[0]==dt_]
    if m: print(f"  {lab:12} {dt_}  MVRV {m[0][1]:5.2f}  ${m[0][2]:>10,.0f}")

for start,lab in (('2015-01-01','2015+'),('2019-01-01','2019+')):
    s=[x for x in d if x[0]>=start]; P=[x[2] for x in s]
    fwd=lambda i,h: (P[i+h]/P[i]-1)*100 if i+h<len(P) else None
    vals=sorted(x[1] for x in s); n=len(vals)
    q=[vals[int(f*n)] for f in (0.2,0.4,0.6,0.8)]
    def bk(v):
        for i,t in enumerate(q):
            if v<=t: return i
        return 4
    print(f"\n=== forward returns by MVRV quintile, {lab}  n={n}")
    print(f"  {'Q':3} {'MVRV range':>14} {'n':>5} {'+60d':>9} {'%up':>5} {'+180d':>9} {'%up':>5} {'+365d':>9} {'%up':>5}")
    for b in range(5):
        idx=[i for i,x in enumerate(s) if bk(x[1])==b]
        vv=[s[i][1] for i in idx]
        row=[f"  Q{b+1:<2} {min(vv):6.2f}-{max(vv):6.2f} {len(idx):5}"]
        for h in (60,180,365):
            r=[x for x in (fwd(i,h) for i in idx) if x is not None]
            row.append(f"{st.median(r):+9.2f} {100*sum(1 for x in r if x>0)/len(r):4.0f}%")
        print(' '.join(row))
    for h in (60,180,365):
        r=[x for x in (fwd(i,h) for i in range(len(s))) if x is not None]
        print(f"  baseline +{h}d: {st.median(r):+.2f}%  {100*sum(1 for x in r if x>0)/len(r):.0f}% up")
    print(f"  current MVRV {CUR:.3f} -> Q{bk(CUR)+1}")
