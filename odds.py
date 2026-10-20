#!/usr/bin/env python3
"""Generate the CTZB odds sheet dataset.

Gate: mechanical RSI regime (rsi_regime(BTC_2D,8,13,60,41)) -- NOT the
hindsight bull windows the first version of the sheet used.

Emits one JSON on stdout with three blocks:
  D[chart][tag]   horizon upside, risk, touch probabilities   (as before)
  C[chart][tag][band]   same graded by cycle day              (as before)
  E[chart][tag][lev]    entry quality: P(+Y% before -liq) + median days
"""
import sys, json, datetime as dt, statistics as st
sys.path.insert(0, '/home/claude/ctzb-data')
import engine as E_, regimes as R

CHARTS = [("ETH","1D"),("ETH","2D"),("ETH","3D"),("ETH","5D"),("BTC","1D"),("BTC","2D")]
HOR    = [10,20,30,60,90]
TOUCH  = [10,20,30,50]
BANDS  = [("0-200",0,200),("200-400",200,400),("400-600",400,600),
          ("600-900",600,900),("900+",900,10**9)]
# leverage -> liquidation distance in spot terms
LEV    = {"2x":0.50, "3x":0.3333, "3.3x":0.30, "5x":0.20}
TG     = [5,10,15,20]
HEATTG = 0.20

TAGS = [
  ("ALL troughs",        lambda s: True),
  ("A  trough <40",      lambda s: s['bk']=="A"),
  ("B  trough 40-55",    lambda s: s['bk']=="B"),
  ("C  trough 55-65",    lambda s: s['bk']=="C"),
  ("D  trough >65",      lambda s: s['bk']=="D"),
  ("Any diamond",        lambda s: s['dis']),
  ("GOLD diamond <50",   lambda s: s['dis'] and s['strong']),
  ("HOLLOW diamond >=50",lambda s: s['dis'] and not s['strong']),
  ("Diamond + prime dot",lambda s: s['dis'] and s['prime']),
  ("A + diamond",        lambda s: s['bk']=="A" and s['dis']),
  ("B + diamond",        lambda s: s['bk']=="B" and s['dis']),
  ("Prime K 20-50",      lambda s: s['prime']),
]

def med(xs):  return round(st.median(xs),1) if xs else None
def medi(xs): return int(round(st.median(xs))) if xs else None
def pc(k,n):  return int(round(k/n*100)) if n else None

def main():
    reg = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    D, C, E = {}, {}, {}
    for sym, tf in CHARTS:
        name = f"{sym} {tf}"
        path = f"data/{sym}_{tf}.csv"
        sigs, b = E_.signals(path, regime=reg)
        c, hi, lo, dates = b['close'], b['high'], b['low'], b['date']
        n = len(c)
        last = dates[-1]

        recs = []
        for s in sigs:
            ei, e = s['ei'], c[s['ei']]
            d0 = dates[ei]
            r = dict(tag=s, d0=d0, e=e)
            # per-horizon measurements
            r['h'] = {}
            for H in HOR:
                w = [j for j in range(ei+1, n) if dates[j] <= d0+dt.timedelta(days=H)]
                if not w or last < d0+dt.timedelta(days=H):
                    r['h'][H] = None; continue
                best = max(hi[j]/e-1 for j in w)
                pk   = max(w, key=lambda j: hi[j])
                wc   = min(c[k] for k in range(ei, pk+1))
                r['h'][H] = dict(
                    up   = best*100,
                    ret  = (c[w[-1]]/e-1)*100,
                    risk = (wc/e-1)*100,
                    days = (dates[pk]-d0).days,
                    touch= {T: (best >= T/100) for T in TOUCH})
            # full forward path for the entry-quality race
            r['path'] = [((dates[j]-d0).days, hi[j]/e-1, lo[j]/e-1)
                         for j in range(ei+1, n)]
            recs.append(r)

        # ---- baseline: every bar on the chart, same horizons ----
        D[name] = {"_b": {}}
        for H in HOR:
            ups, rets, closed = [], [], 0
            step = max(1, H // max(1, int(tf[:-1])))
            for i in range(n-1):
                w = [j for j in range(i+1, n) if dates[j] <= dates[i]+dt.timedelta(days=H)]
                if not w or last < dates[i]+dt.timedelta(days=H): continue
                ups.append(max(hi[j]/c[i]-1 for j in w)*100)
                rets.append((c[w[-1]]/c[i]-1)*100)
                closed += 1 if c[w[-1]] > c[i] else 0
            D[name]["_b"][str(H)] = [pc(closed, len(rets)), med(rets), med(ups)]

        C[name], E[name] = {}, {}
        span_years = max(0.5, (last - recs[0]['d0']).days/365.25) if recs else 1
        for tname, fn in TAGS:
            sel = [r for r in recs if fn(r['tag'])]
            if not sel: continue
            # ---------- D: horizon table ----------
            h = {}
            for H in HOR:
                v = [r['h'][H] for r in sel if r['h'][H]]
                if not v: continue
                h[str(H)] = [pc(sum(1 for x in v if x['ret']>0), len(v)),
                             med([x['ret'] for x in v]),
                             med([x['up'] for x in v])] + \
                            [pc(sum(1 for x in v if x['touch'][T]), len(v)) for T in TOUCH]
            v60 = [r['h'][60] for r in sel if r['h'][60]]
            v10 = [r['h'][10] for r in sel if r['h'][10]]
            v90 = [r['h'][90] for r in sel if r['h'][90]]
            D[name][tname] = dict(
                n=len(sel), y=round(len(sel)/span_years,1),
                r = med([x['risk'] for x in v60]) if v60 else None,
                r10= med([x['risk'] for x in v10]) if v10 else None,
                rw = round(min(x['risk'] for x in v60),1) if v60 else None,
                d  = medi([x['days'] for x in v90]) if v90 else None,
                h=h)
            # ---------- C: by cycle band ----------
            cb = {}
            for bn, a, z in BANDS:
                g = [r for r in sel if a <= E_.cycday(r['d0']) < z and r['h'][60]]
                if len(g) < 4: continue
                u = lambda H: med([r['h'][H]['up'] for r in g if r['h'][H]])
                cb[bn] = [len(g),
                          pc(sum(1 for r in g if r['h'][60]['ret']>0), len(g)),
                          med([r['h'][60]['ret'] for r in g]),
                          u(10), u(20), u(30), u(60),
                          med([r['h'][60]['risk'] for r in g])]
            if cb: C[name][tname] = cb
            # ---------- E: entry quality, per leverage ----------
            ev = {}
            for lname, liq in LEV.items():
                row = {}
                for Y in TG:
                    ok, days = 0, []
                    for r in sel:
                        for dd, up, dn in r['path']:
                            if dn <= -liq: break
                            if up >= Y/100: ok += 1; days.append(dd); break
                    row[str(Y)] = [pc(ok, len(sel)), medi(days)]
                # liquidated before ever +3%
                dead = 0
                for r in sel:
                    for dd, up, dn in r['path']:
                        if dn <= -liq: dead += 1; break
                        if up >= 0.03: break
                row['liq'] = pc(dead, len(sel))
                # heat eaten to collect +20%
                heat = []
                for r in sel:
                    w = 0.0
                    for dd, up, dn in r['path']:
                        if dn <= -liq: break          # wiped out, no heat to record
                        w = min(w, dn)
                        if up >= HEATTG: heat.append(-w*100); break
                hs = sorted(heat)
                row['heat'] = [med(hs),
                               round(hs[min(len(hs)-1,int(.75*len(hs)))],1) if hs else None,
                               round(hs[min(len(hs)-1,int(.90*len(hs)))],1) if hs else None,
                               len(hs)]
                ev[lname] = row
            E[name][tname] = ev
    json.dump(dict(D=D, C=C, E=E, gate="rsi_regime(BTC_2D,8,13,60,41)",
                   built=str(dt.date.today()), lev=LEV, tg=TG),
              sys.stdout, separators=(",",":"), default=str)

if __name__ == "__main__":
    main()
