"""Which inputs actually separate forward returns? Screen before building.

Declared candidate list, fixed before running. Each is converted to a
percentile rank over a trailing 504-day window, then forward 30d and 60d
returns are compared across its own top and bottom quintile.

  funding      OI-weighted funding rate
  lsr          long/short account ratio (12-market mean)
  oi           aggregate perp open interest, USD
  oi_chg       30-day change in open interest
  mvrv         market cap / realised cap
  mvrv_chg     30-day change in MVRV
  exsply       exchange-held supply
  exflow       14-day net exchange flow (in - out)
  adr          active addresses
  stable       40-day growth in total stablecoin supply
  premium      Coinbase premium (BTC only)

Nothing is added to this list after seeing results. A candidate "separates"
if top and bottom quintile differ by more than 8 points of median 60d return
AND the sign agrees across BTC and ETH.
"""
import csv, datetime as dt, statistics as st

def px(p):
    return {str(dt.datetime.fromtimestamp(int(r['time']), dt.UTC).date()): float(r['close'])
            for r in csv.DictReader(open(p))}
P = {'BTC': px('data/BTC_1D.csv'), 'ETH': px('data/ETH_1D.csv')}

def col(path, name):
    out = {}
    for r in csv.DictReader(open(path)):
        if r.get(name):
            try: out[r['date']] = float(r[name])
            except ValueError: pass
    return out

def chg(series, days):
    out = {}
    ks = sorted(series)
    idx = {k: i for i, k in enumerate(ks)}
    for k in ks:
        d0 = str(dt.date.fromisoformat(k) - dt.timedelta(days=days))
        if d0 in series and series[d0]:
            out[k] = 100 * (series[k] / series[d0] - 1)
    return out

FEAT = {}
for a in ('BTC', 'ETH'):
    f = {}
    f['funding'] = col(f'data/derivs/{a}_funding_daily.csv', 'funding_oi_weighted')
    f['lsr']     = col(f'data/derivs/{a}_lsratio_daily.csv', 'ls_ratio_mean')
    f['oi']      = col(f'data/derivs/{a}_oi_daily.csv', 'oi_usd_total')
    f['oi_chg']  = chg(f['oi'], 30)
    f['mvrv']    = col(f'data/onchain/{a}_cm_daily.csv', 'CapMVRVCur')
    f['mvrv_chg']= chg(f['mvrv'], 30)
    f['exsply']  = col(f'data/onchain/{a}_cm_daily.csv', 'SplyExNtv')
    fin  = col(f'data/onchain/{a}_cm_daily.csv', 'FlowInExNtv')
    fout = col(f'data/onchain/{a}_cm_daily.csv', 'FlowOutExNtv')
    f['exflow'] = {d: fin[d] - fout[d] for d in fin if d in fout}
    f['adr']    = col(f'data/onchain/{a}_cm_daily.csv', 'AdrActCnt')
    stab = col('data/flows/stablecoin_supply_daily.csv', 'total_usd')
    f['stable'] = chg(stab, 40)
    if a == 'BTC':
        f['premium'] = col('data/flows/BTC_premium_daily.csv', 'premium_pct')
    FEAT[a] = f

def fwd(a, d, h):
    ks = sorted(P[a])
    if d not in P[a]: return None
    i = ks.index(d)
    return (P[a][ks[i+h]] / P[a][d] - 1) * 100 if i + h < len(ks) else None

print(f"{'feature':10} {'asset':5} {'n':>5} {'bottom quintile':>24} {'top quintile':>24} {'spread':>8}")
print(f"{'':10} {'':5} {'':>5} {'+30d':>11} {'+60d':>11} {'+30d':>11} {'+60d':>11}")
res = {}
for name in ('funding','lsr','oi','oi_chg','mvrv','mvrv_chg','exsply','exflow','adr','stable','premium'):
    for a in ('BTC','ETH'):
        s = FEAT[a].get(name)
        if not s: continue
        ds = sorted(d for d in s if d in P[a])
        if len(ds) < 400: continue
        # trailing 504d percentile
        rank = {}
        vals = []
        for d in ds:
            vals.append(s[d])
            w = vals[-504:]
            rank[d] = 100 * sum(1 for x in w if x <= s[d]) / len(w)
        lo = [d for d in ds if rank[d] <= 20]
        hi = [d for d in ds if rank[d] >= 80]
        def med(g, h):
            v = [fwd(a, d, h) for d in g]
            v = [x for x in v if x is not None]
            return st.median(v) if len(v) > 20 else None
        l30, l60, h30, h60 = med(lo,30), med(lo,60), med(hi,30), med(hi,60)
        if None in (l60, h60): continue
        spread = h60 - l60
        res[(name,a)] = spread
        f = lambda x: f'{x:+10.1f}%' if x is not None else '          -'
        print(f"{name:10} {a:5} {len(ds):>5} {f(l30)} {f(l60)} {f(h30)} {f(h60)} {spread:+8.1f}")
print()
print("agree in sign across both assets AND |spread| > 8 on both:")
for name in sorted(set(k[0] for k in res)):
    b, e = res.get((name,'BTC')), res.get((name,'ETH'))
    if b is None or e is None: 
        print(f"   {name:10} BTC only ({b:+.1f})" if b is not None else f"   {name:10} incomplete")
        continue
    ok = (b > 0) == (e > 0) and abs(b) > 8 and abs(e) > 8
    print(f"   {name:10} BTC {b:+6.1f}   ETH {e:+6.1f}   {'PASS' if ok else 'fail'}")

# ================= composite from the two survivors =================
print("\n\n==== COMPOSITE: MVRV percentile + inverted OI percentile ====")
print("MVRV high = holders in profit = trend intact. OI low = leverage flushed.")
print("Both scored as trailing-504d percentile; OI inverted. Equal weight.\n")

for a in ('BTC','ETH'):
    mv, oi = FEAT[a]['mvrv'], FEAT[a]['oi']
    ds = sorted(d for d in mv if d in oi and d in P[a])
    def rk(series, keys):
        out, buf = {}, []
        for d in keys:
            buf.append(series[d]); w = buf[-504:]
            out[d] = 100*sum(1 for x in w if x <= series[d])/len(w)
        return out
    rm, ro = rk(mv, ds), rk(oi, ds)
    comp = {d: (rm[d] + (100-ro[d]))/2 for d in ds}
    vals = sorted(comp.values()); n = len(vals)
    def med(g,h):
        v=[fwd(a,d,h) for d in g]; v=[x for x in v if x is not None]
        return (st.median(v), 100*sum(1 for x in v if x>0)/len(v), len(v)) if len(v)>20 else None
    print(f"  {a}  n={n}  {ds[0]} -> {ds[-1]}")
    print(f"    {'bucket':18} {'n':>5} {'+30d':>9} {'up':>5} {'+60d':>9} {'up':>5}")
    for lab, lo_, hi_ in (('0-20 worst',0,20),('20-40',20,40),('40-60',40,60),('60-80',60,80),('80-100 best',80,100)):
        g=[d for d in ds if lo_ <= comp[d] < hi_ or (hi_==100 and comp[d]==100)]
        r1,r2 = med(g,30), med(g,60)
        if r1 and r2:
            print(f"    {lab:18} {r2[2]:>5} {r1[0]:+8.1f}% {r1[1]:4.0f}% {r2[0]:+8.1f}% {r2[1]:4.0f}%")
    b=[fwd(a,d,60) for d in ds]; b=[x for x in b if x is not None]
    b30=[fwd(a,d,30) for d in ds]; b30=[x for x in b30 if x is not None]
    print(f"    {'baseline':18} {len(b):>5} {st.median(b30):+8.1f}% {100*sum(1 for x in b30 if x>0)/len(b30):4.0f}% {st.median(b):+8.1f}% {100*sum(1 for x in b if x>0)/len(b):4.0f}%")
    last = ds[-1]
    print(f"    NOW {last}: MVRV pct {rm[last]:.0f}, OI pct {ro[last]:.0f} -> composite {comp[last]:.0f}/100")
    print()
