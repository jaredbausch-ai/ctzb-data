"""MVRV exhaustion bands for BTC and ETH, full history.

5D bars rebuilt from Coin Metrics daily PriceUSD on the same 5-day grid as the
repo's TradingView exports (BTC anchor epoch-day %5==1, ETH ==4), so the 2016+
portion lines up while history extends back to each asset's start.

A "long streak" is 6+ consecutive 5D bars closing below their open. MVRV is read
at the first bar's OPEN date and the last bar's CLOSE date (open + 4 days).
The band is the trimmed range of prior streak exits: min and max dropped.
The streak in progress or just ended is excluded so the band is not circular.
"""
import csv, datetime as dt, statistics as st, sys

ANCHOR = {"BTC": 1, "ETH": 4}
MINRUN = 6

def load(a):
    px, mv = {}, {}
    for r in csv.DictReader(open(f"data/onchain/{a}_cm_daily.csv")):
        if r["PriceUSD"]:   px[r["date"]] = float(r["PriceUSD"])
        if r["CapMVRVCur"]: mv[r["date"]] = float(r["CapMVRVCur"])
    return px, mv

def make5d(px, anchor):
    days = sorted(px)
    out = []
    i = 0
    while i < len(days):
        d0 = dt.date.fromisoformat(days[i])
        if (d0 - dt.date(1970,1,1)).days % 5 != anchor:
            i += 1; continue
        grp = [days[i+k] for k in range(5) if i+k < len(days)
               and dt.date.fromisoformat(days[i+k]) == d0 + dt.timedelta(days=k)]
        if len(grp) == 5:
            out.append({"o_d": d0, "c_d": d0+dt.timedelta(days=4),
                        "o": px[grp[0]], "c": px[grp[-1]]})
        i += 5
    return out

def streaks(B):
    runs, cur = [], 0
    for i, b in enumerate(B):
        if b["c"] < b["o"]: cur += 1
        else:
            if cur: runs.append((i-cur, i-1, cur))
            cur = 0
    if cur: runs.append((len(B)-cur, len(B)-1, cur))
    return [r for r in runs if r[2] >= MINRUN]

for a in ("BTC", "ETH"):
    px, mv = load(a)
    B = make5d(px, ANCHOR[a])
    def M(d):
        for k in range(5):
            v = mv.get(str(d - dt.timedelta(days=k)))
            if v: return v
    L = sorted(streaks(B), key=lambda r: -r[2])
    print(f"\n===== {a}   {len(B)} 5D bars   {B[0]['o_d']} -> {B[-1]['c_d']}   long streaks: {len(L)}")
    print(f"  {'bars':>4} {'opens':12} {'closes':12} {'price':>8} {'MVRV in':>8} {'MVRV out':>9}")
    rows = []
    for s, e, ln in L:
        m0, m1 = M(B[s]["o_d"]), M(B[e]["c_d"])
        tot = (B[e]["c"]/B[s]["o"] - 1) * 100
        rows.append((ln, B[s]["o_d"], B[e]["c_d"], tot, m0, m1))
        f = lambda v, w=8: f"{v:{w}.3f}" if v is not None else " "*(w-1)+"-"
        print(f"  {ln:>4} {str(B[s]['o_d']):12} {str(B[e]['c_d']):12} {tot:7.1f}% {f(m0)} {f(m1,9)}")
    RECENT = dt.date(2026, 9, 1)
    ex = sorted(r[5] for r in rows if r[5] is not None and r[2] < RECENT)
    core = ex[1:-1] if len(ex) >= 4 else ex
    lo, hi, md = min(core), max(core), st.median(ex)
    last_d = max(mv)
    cur_m, cur_p = mv[last_d], px[last_d]
    rp = cur_p / cur_m
    print(f"\n  prior exits ({len(ex)}): {[round(v,3) for v in ex]}")
    print(f"  BAND  floor {lo:.3f}   median {md:.3f}   ceiling {hi:.3f}   (trimmed to {len(core)})")
    print(f"  now {last_d}  price ${cur_p:,.2f}  MVRV {cur_m:.3f}  realised ${rp:,.2f}"
          f"   {'INSIDE BAND' if lo<=cur_m<=hi else 'outside band'}")
    for lvl, lab in ((hi,"ceiling"),(md,"median"),(lo,"floor")):
        print(f"     {lab:8} MVRV {lvl:5.3f} -> ${lvl*rp:>11,.0f}  {100*(lvl*rp/cur_p-1):+6.1f}%")
