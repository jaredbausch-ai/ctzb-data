"""Stoch %K (the BLUE line) going FLAT in the bearish control zone. 31 Oct 2026.

Jared's question. Blue = `kL` in ct_zone_bounce_v15.pine line 225 =
sma(stoch(ct,ct,ct,14), 3). Bearish control zone = CT RSI < 40 (the zBear
parameter).

"Flat" has three readings, all declared before running, because K pinning at its
floor and K merely not moving are different animals:
  F_pin2   K below 2 for 3 consecutive bars   (pinned at the floor)
  F_pin5   K below 5 for 3 consecutive bars
  F_still  K moves less than 1.0 point per bar for 3 consecutive bars, at any level

Each is scored with CT < 40 at the trigger bar. Forward windows measured from the
third bar's close, so nothing reaches back into the observation period -- the
tautology trap recorded on 29 Oct.

Reported with win / drawdown together per the standing change in CONTEXT.md.

Run from the repo root:  python3 -I analysis/flatk.py
"""
import sys, os, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
Z = 40


def events(sym, tf, kind):
    b = E.load(f'data/{sym}_{tf}.csv')
    c = b['close']; hi = b['high']; lo = b['low']; d = b['date']
    ct = E.rsi(c, 14); k = E.sma(E.stoch_of(ct, 14), 3)
    n = len(c); out = []
    for i in range(30, n):
        if ct[i] is None or k[i] is None or k[i-1] is None or k[i-2] is None or k[i-3] is None:
            continue
        if ct[i] >= Z:                      # must be in the bearish control zone
            continue
        if kind == 'F_pin2':
            ok = all(k[i-j] < 2 for j in range(3))
        elif kind == 'F_pin5':
            ok = all(k[i-j] < 5 for j in range(3))
        else:
            ok = all(abs(k[i-j] - k[i-j-1]) < 1.0 for j in range(3))
        if not ok: continue
        out.append((i, d[i], c[i], b))
    return out, b


def fwd(b, i, bars):
    c = b['close']; hi = b['high']; lo = b['low']
    w = range(i + 1, min(i + 1 + bars, len(c)))
    w = list(w)
    if len(w) < bars: return None
    base = c[i]
    return dict(up=(max(hi[j] for j in w)/base-1)*100,
                dn=(min(lo[j] for j in w)/base-1)*100,
                ret=(c[w[-1]]/base-1)*100)


def main():
    print(f'BLUE LINE (Stoch %K) FLAT for 3 bars while CT RSI < {Z}\n')
    for kind, desc in (('F_pin2', 'K below 2 for 3 bars (pinned at the floor)'),
                       ('F_pin5', 'K below 5 for 3 bars'),
                       ('F_still', 'K moving <1.0/bar for 3 bars, any level')):
        print(f'{"="*92}\n{desc}\n{"="*92}')
        print(f'  {"chart":<9}{"n":>5}{"dedup":>7}{"med ret 10b":>13}{"up":>6}'
              f'{"med max up":>12}{"med max dn":>12}{"fell>10%":>10}{"rose>10%":>10}')
        for sym in ('ETH', 'BTC'):
            for tf in ('1D', '2D', '3D'):
                ev, b = events(sym, tf, kind)
                ev = [e for e in ev if GATE(e[1])]
                keep = []
                for e in ev:
                    if not keep or (e[1] - keep[-1][1]).days > 20: keep.append(e)
                res = [fwd(b, e[0], 10) for e in keep]
                res = [r for r in res if r]
                if len(res) < 8:
                    print(f'  {sym+" "+tf:<9}{len(ev):>5}{len(keep):>7}{"too thin":>13}'); continue
                r = [x['ret'] for x in res]
                print(f'  {sym+" "+tf:<9}{len(ev):>5}{len(keep):>7}{statistics.median(r):>+12.1f}%'
                      f'{100*sum(1 for x in r if x>0)/len(r):>5.0f}%'
                      f'{statistics.median([x["up"] for x in res]):>+11.1f}%'
                      f'{statistics.median([x["dn"] for x in res]):>+11.1f}%'
                      f'{100*sum(1 for x in res if x["dn"]<=-10)/len(res):>9.0f}%'
                      f'{100*sum(1 for x in res if x["up"]>=10)/len(res):>9.0f}%')
        print()
    # baseline for comparison
    print(f'{"="*92}\nBASELINE: all bars with CT < {Z}, regime ON (what flat K is measured against)\n{"="*92}')
    print(f'  {"chart":<9}{"n":>6}{"med ret 10b":>13}{"up":>6}{"med max up":>12}{"med max dn":>12}{"fell>10%":>10}{"rose>10%":>10}')
    for sym in ('ETH','BTC'):
        for tf in ('1D','2D','3D'):
            b = E.load(f'data/{sym}_{tf}.csv'); c=b['close']; d=b['date']; ct=E.rsi(c,14)
            res=[]
            for i in range(30,len(c)-11):
                if ct[i] is None or ct[i]>=Z or not GATE(d[i]): continue
                f=fwd(b,i,10)
                if f: res.append(f)
            if len(res)<10: continue
            r=[x['ret'] for x in res]
            print(f'  {sym+" "+tf:<9}{len(res):>6}{statistics.median(r):>+12.1f}%'
                  f'{100*sum(1 for x in r if x>0)/len(r):>5.0f}%'
                  f'{statistics.median([x["up"] for x in res]):>+11.1f}%'
                  f'{statistics.median([x["dn"] for x in res]):>+11.1f}%'
                  f'{100*sum(1 for x in res if x["dn"]<=-10)/len(res):>9.0f}%'
                  f'{100*sum(1 for x in res if x["up"]>=10)/len(res):>9.0f}%')


if __name__ == '__main__':
    main()
