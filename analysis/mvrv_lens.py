"""MVRV and on-chain flows as CTZB lenses. Jared asked 8 Nov 2026.

Candidate list declared BEFORE running, per docs/PRETRADE.md:
  1 MVRV at entry in the bottom quintile of that asset's 2019+ distribution
  2 MVRV at entry below the asset's fixed 25th-pct level (ETH 0.967, BTC 1.285)
  3 MVRV falling vs rising over the 30 days into the trough
  4 MVRV z-score vs its own trailing 365d mean, bottom tercile
  5 net exchange flow (in - out) negative over the 14 days into the trough
  6 exchange supply at a trailing 365d low at entry
  7 active addresses above their own 90d mean at entry
Nothing added after seeing results.

Reported for every candidate: win rate AND the failure metrics.
  WIN    reached20     - price reached +20% inside 60d
  LIQ30  touched30     - drawdown ever hit -30%  (liquidation proxy at ~3.3x)
  LIQ20  maxDrawdown <= -20
  EARLY  dipBeforeHigh <= -15
  DD     median maxDrawdown
"""
import csv, datetime as dt, statistics as st, random

LED = list(csv.DictReader(open("datasets/ledger.csv")))

ON = {}
for a in ("BTC", "ETH"):
    rows = list(csv.DictReader(open(f"data/onchain/{a}_cm_daily.csv")))
    ON[a] = {r["date"]: r for r in rows}
    ON[a+"_dates"] = sorted(ON[a])

def val(a, d, col, back=7):
    d0 = dt.date.fromisoformat(d)
    for k in range(back):
        r = ON[a].get(str(d0 - dt.timedelta(days=k)))
        if r and r.get(col):
            return float(r[col])
    return None

def series_before(a, d, col, days):
    d0 = dt.date.fromisoformat(d)
    out = []
    for k in range(days):
        r = ON[a].get(str(d0 - dt.timedelta(days=k)))
        if r and r.get(col): out.append(float(r[col]))
    return out

# ---- attach features ----
rows = []
for r in LED:
    a = r["asset"]
    if a not in ("BTC", "ETH"): continue
    e = r["entry"]
    mv = val(a, e, "CapMVRVCur")
    if mv is None: continue
    mv30 = val(a, str(dt.date.fromisoformat(e) - dt.timedelta(days=30)), "CapMVRVCur")
    hist = series_before(a, e, "CapMVRVCur", 365)
    z = None
    if len(hist) > 300:
        m, s = st.mean(hist), st.pstdev(hist)
        if s > 0: z = (mv - m) / s
    fin  = series_before(a, e, "FlowInExNtv", 14)
    fout = series_before(a, e, "FlowOutExNtv", 14)
    netflow = (sum(fin) - sum(fout)) if (len(fin) >= 10 and len(fout) >= 10) else None
    sply = val(a, e, "SplyExNtv")
    shist = series_before(a, e, "SplyExNtv", 365)
    sply_low = (sply is not None and len(shist) > 300 and sply <= min(shist) * 1.005)
    adr = val(a, e, "AdrActCnt")
    ahist = series_before(a, e, "AdrActCnt", 90)
    adr_hot = (adr is not None and len(ahist) > 60 and adr > st.mean(ahist))
    try: dd = float(r["maxDrawdown"])
    except: dd = None
    try: dbh = float(r["dipBeforeHigh"])
    except: dbh = None
    rows.append(dict(asset=a, chart=r["chart"], entry=e, year=int(r["year"]),
                     grade=r["grade"], lenses=r["lenses"] or "",
                     win=r["reached20"] == "yes", liq30=r["touched30"] == "yes",
                     dd=dd, dbh=dbh,
                     mvrv=mv, dmv=(mv - mv30) if mv30 else None, z=z,
                     netflow=netflow, sply_low=sply_low, adr_hot=adr_hot))

print(f"ledger rows {len(LED)}   with on-chain coverage {len(rows)}"
      f"   {min(r['entry'] for r in rows)} -> {max(r['entry'] for r in rows)}")

# ---- per-asset MVRV thresholds from the 2019+ distribution ----
Q1, P25 = {}, {"ETH": 0.967, "BTC": 1.285}
for a in ("BTC", "ETH"):
    v = sorted(float(ON[a][d]["CapMVRVCur"]) for d in ON[a+"_dates"]
               if d >= "2019-01-01" and ON[a][d]["CapMVRVCur"])
    Q1[a] = v[int(0.20 * len(v))]
print(f"2019+ bottom-quintile ceilings:  " + "  ".join(f"{a} {Q1[a]:.3f}" for a in Q1))

def stats(g):
    if not g: return None
    n = len(g)
    dds = [r["dd"] for r in g if r["dd"] is not None]
    dbhs = [r["dbh"] for r in g if r["dbh"] is not None]
    return dict(n=n,
        win=100*sum(r["win"] for r in g)/n,
        liq30=100*sum(r["liq30"] for r in g)/n,
        liq20=100*sum(1 for x in dds if x <= -20)/len(dds) if dds else float("nan"),
        early=100*sum(1 for x in dbhs if x <= -15)/len(dbhs) if dbhs else float("nan"),
        dd=st.median(dds) if dds else float("nan"))

BASE = stats(rows)
def line(name, g):
    s = stats(g)
    if not s or s["n"] < 8:
        print(f"  {name:38} n={s['n'] if s else 0:<4}  too few"); return None
    print(f"  {name:38} n={s['n']:<4} win {s['win']:5.1f}% ({s['win']-BASE['win']:+5.1f})"
          f"  LIQ30 {s['liq30']:5.1f}% ({s['liq30']-BASE['liq30']:+5.1f})"
          f"  LIQ20 {s['liq20']:5.1f}%  EARLY {s['early']:5.1f}%  DD {s['dd']:6.1f}%")
    return s

print(f"\nBASELINE  n={BASE['n']}  win {BASE['win']:.1f}%  LIQ30 {BASE['liq30']:.1f}%"
      f"  LIQ20 {BASE['liq20']:.1f}%  EARLY {BASE['early']:.1f}%  DD {BASE['dd']:.1f}%")

CAND = [
 ("1 MVRV in bottom quintile (2019+)", lambda r: r["mvrv"] <= Q1[r["asset"]]),
 ("1b MVRV NOT bottom quintile",       lambda r: r["mvrv"] >  Q1[r["asset"]]),
 ("2 MVRV below fixed 25th pct",       lambda r: r["mvrv"] <= P25[r["asset"]]),
 ("2b MVRV above fixed 25th pct",      lambda r: r["mvrv"] >  P25[r["asset"]]),
 ("3 MVRV falling over 30d",           lambda r: r["dmv"] is not None and r["dmv"] < 0),
 ("3b MVRV rising over 30d",           lambda r: r["dmv"] is not None and r["dmv"] > 0),
 ("4 MVRV z < -0.5 vs 365d",           lambda r: r["z"] is not None and r["z"] < -0.5),
 ("4b MVRV z > +0.5 vs 365d",          lambda r: r["z"] is not None and r["z"] >  0.5),
 ("5 net exchange flow negative 14d",  lambda r: r["netflow"] is not None and r["netflow"] < 0),
 ("5b net exchange flow positive 14d", lambda r: r["netflow"] is not None and r["netflow"] > 0),
 ("6 exchange supply at 365d low",     lambda r: r["sply_low"]),
 ("7 active addresses above 90d mean", lambda r: r["adr_hot"]),
]
print("\n==== CANDIDATES ====")
res = {}
for name, f in CAND:
    res[name] = line(name, [r for r in rows if f(r)])

# ================== KILL CHECKS on candidates 1 and 2 ==================
print("\n\n==== KILL CHECKS: MVRV below the fixed 25th pct (candidate 2, n=55) ====")
hit = [r for r in rows if r["mvrv"] <= P25[r["asset"]]]

print("\nA) CLUSTERING -- when do these actually happen?")
from collections import Counter
cy = Counter(r["year"] for r in hit)
print("   by year: " + "  ".join(f"{y}:{c}" for y, c in sorted(cy.items())))
ds = sorted(set(r["entry"] for r in hit))
blocks, cur = [], [ds[0]]
for d in ds[1:]:
    if (dt.date.fromisoformat(d) - dt.date.fromisoformat(cur[-1])).days <= 30:
        cur.append(d)
    else:
        blocks.append(cur); cur = [d]
blocks.append(cur)
print(f"   {len(ds)} distinct entry dates collapse into {len(blocks)} episodes (30-day gap rule):")
for b in blocks:
    g = [r for r in hit if r["entry"] in b]
    print(f"      {b[0]} .. {b[-1]}   {len(g)} signals   win {100*sum(x['win'] for x in g)/len(g):3.0f}%")

print("\nB) BY CHART")
for ch in sorted(set(r["chart"] for r in hit)):
    line(ch, [r for r in hit if r["chart"] == ch])

print("\nC) BY ASSET")
for a in ("BTC", "ETH"):
    line(a, [r for r in hit if r["asset"] == a])

print("\nD) COLLINEARITY -- what else is true of these signals?")
allv = len(hit)
for lens in ("GAP", "HIGH", "AGREE", "BTC3", "FUND", "FCOOL", "DIVH", "UP8"):
    k = sum(1 for r in hit if lens in r["lenses"])
    kb = sum(1 for r in rows if lens in r["lenses"])
    print(f"   {lens:6} present in {k:3}/{allv} of hits ({100*k/allv:4.1f}%)  vs {100*kb/len(rows):4.1f}% of all signals")
gr = Counter(r["grade"] for r in hit)
print("   grade mix: " + "  ".join(f"{g}:{c}" for g, c in sorted(gr.items())))

print("\nE) PLACEBO -- shuffle the MVRV series dates, 200 draws")
mv_by_asset = {a: [float(ON[a][d]["CapMVRVCur"]) for d in ON[a+"_dates"] if ON[a][d]["CapMVRVCur"]] for a in ("BTC","ETH")}
real_edge = stats(hit)["win"] - BASE["win"]
beat = 0; edges = []
random.seed(7)
for _ in range(200):
    fake = []
    for r in rows:
        fm = random.choice(mv_by_asset[r["asset"]])
        if fm <= P25[r["asset"]]: fake.append(r)
    if len(fake) < 10: continue
    e = stats(fake)["win"] - BASE["win"]
    edges.append(e)
    if e >= real_edge: beat += 1
edges.sort()
print(f"   real edge {real_edge:+.1f} pts")
print(f"   shuffled: median {st.median(edges):+.1f}  p95 {edges[int(.95*len(edges))]:+.1f}  max {max(edges):+.1f}")
print(f"   beaten by {beat}/{len(edges)} shuffles  -> empirical p = {beat/len(edges):.3f}")

print("\nF) WHAT HAPPENED NEXT regardless of signal -- is this just 'buy the cycle low'?")
for a in ("BTC","ETH"):
    dts = [d for d in ON[a+"_dates"] if ON[a][d]["CapMVRVCur"] and ON[a][d]["PriceUSD"]
           and float(ON[a][d]["CapMVRVCur"]) <= P25[a]]
    pxs = {d: float(ON[a][d]["PriceUSD"]) for d in ON[a+"_dates"] if ON[a][d]["PriceUSD"]}
    order = sorted(pxs)
    wins = 0; tot = 0
    for d in dts:
        i = order.index(d)
        if i + 60 >= len(order): continue
        fwd = max(pxs[x] for x in order[i+1:i+61])
        tot += 1; wins += (fwd / pxs[d] - 1) >= 0.20
    print(f"   {a}: ANY day with MVRV <= {P25[a]}: {tot} days, {100*wins/tot:.1f}% saw +20% within 60d")

print("\nG) HOLDOUT -- episodes split in time, same fixed rule")
disc = [r for r in hit if r["entry"] < "2022-01-01"]
hold = [r for r in hit if r["entry"] >= "2022-01-01"]
bd = stats([r for r in rows if r["entry"] <  "2022-01-01"])
bh = stats([r for r in rows if r["entry"] >= "2022-01-01"])
for lab, g, b in (("discovery 2016-2021", disc, bd), ("holdout 2022-2026", hold, bh)):
    s = stats(g)
    print(f"   {lab:22} n={s['n']:<3} win {s['win']:5.1f}%  LIQ30 {s['liq30']:4.1f}%  DD {s['dd']:6.1f}%"
          f"   |  baseline same period n={b['n']:<4} win {b['win']:5.1f}%  LIQ30 {b['liq30']:4.1f}%")

print("\nH) EPISODE-LEVEL test -- each episode counts once, not each signal")
ep = []
for b in blocks:
    g = [r for r in hit if r["entry"] in b]
    ep.append(100*sum(x["win"] for x in g)/len(g))
print(f"   {len(ep)} episodes, win rate per episode: {[round(x) for x in ep]}")
print(f"   episodes where the majority won: {sum(1 for x in ep if x > 50)}/{len(ep)}")
print(f"   if each episode were a coin flip at the {BASE['win']:.0f}% baseline,")
print(f"   P(all {len(ep)} majority-win) = {(BASE['win']/100)**len(ep):.4f}")

print("\nI) WHERE IS IT NOW")
for a in ("BTC", "ETH"):
    d = max(x for x in ON[a+"_dates"] if ON[a][x]["CapMVRVCur"])
    m = float(ON[a][d]["CapMVRVCur"]); p = float(ON[a][d]["PriceUSD"])
    trig = P25[a] * (p/m)
    print(f"   {a}  MVRV {m:.3f}  threshold {P25[a]:.3f}  -> {'ARMED' if m<=P25[a] else 'not armed'}"
          f"   triggers at ${trig:,.0f}  ({100*(trig/p-1):+.1f}% from ${p:,.0f})")
