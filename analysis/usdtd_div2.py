"""USDT.D 2D divergence + CT 50 rejection, LOOSENED. DECLARED 28 Oct 2026 15:35 ET,
before running, after Jared doubted one prior case in ten years. usdtd_div.py's rules
were strict; this reports every variant below, all of them, so none is picked after
the fact. Same data, outcomes and episode rule (10 bars) as usdtd_div.py.
  V0  usdtd_div.py as run (combine within 3 bars)
  V1  combine within 6 bars
  V2  V1 + CT high of the last 3 bars anywhere 45-55, drop of 1+ point
  V3  V2 + Stoch peak threshold 60, previous peak 3-30 bars back
  V4  V3 + no "came up from below 45" requirement, combine within 10 bars
Every V4 event is listed with its date so it can be checked on the chart.
Context only; nothing adopted.  python3 -I analysis/usdtd_div2.py
"""
import os, sys, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usdtd_div as U
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))

def ev(B, comb, lo, hi, drop, kmin, back, below):
    n = len(B); div, rej = set(), set()
    pk = [p for p in range(1, n - 1) if B[p]['k'] > B[p-1]['k'] and B[p]['k'] >= B[p+1]['k'] and B[p]['k'] >= kmin]
    for j, p in enumerate(pk):
        for q in reversed(pk[:j]):
            if p - q < 3: continue
            if p - q > back: break
            hp = max(B[i]['h'] for i in range(max(0, p-2), p+1)); hq = max(B[i]['h'] for i in range(max(0, q-2), q+1))
            if B[q]['k'] > B[p]['k'] and hp > hq: div.add(p + 1)
            break
    for t in range(18, n):
        m = max(B[i]['ct'] for i in range(t-3, t)); ti = max(range(t-3, t), key=lambda i: B[i]['ct'])
        if B[t]['ct'] < 50 and lo <= m <= hi and B[t]['ct'] <= m - drop and (not below or any(B[i]['ct'] < 45 for i in range(ti-15, ti))):
            rej.add(t)
    both = {t for t in range(n) if (t in div or t in rej) and any(i in div for i in range(t-comb+1, t+1)) and any(i in rej for i in range(t-comb+1, t+1))}
    out, last = [], -99
    for t in sorted(both):
        if t - last > 10: out.append(t)
        last = t
    return out

def main():
    B = U.load_dom(); PX = {a: U.load_px(a) for a in ('ETH', 'BTC')}
    V = [('V0 as run', (3, 48, 53, 2, 70, 20, True)), ('V1 combine 6 bars', (6, 48, 53, 2, 70, 20, True)),
         ('V2 + CT 45-55, drop 1', (6, 45, 55, 1, 70, 20, True)), ('V3 + Stoch 60, 30 bars', (6, 45, 55, 1, 60, 30, True)),
         ('V4 + any start, 10 bars', (10, 45, 55, 1, 60, 30, False))]
    P('USDT.D 2D DIVERGENCE + CT 50 REJECTION, LOOSENED -- declared 28 Oct 2026, run', dt.date.today())
    U.L.clear()
    P('variant                      n  USDT.D 60d lower | ETH 60d  up  best  worst | BTC 60d  up')
    last = None
    for name, a in V:
        idx = ev(B, *a); O = [U.outcome(B, t, PX) for t in idx]
        def md(k): v = [o[k] for o in O if k in o]; return f'{st.median(v):+6.1f}' if v else '    - '
        def pc(k, s): v = [o[k] for o in O if k in o]; return f'{100*sum((x<0) if s<0 else (x>0) for x in v)/len(v):3.0f}%' if v else '  - '
        P(f'{name:24} {len(idx):3}  {md("dom30")} {pc("dom30",-1)} | {md("ETH60")} {pc("ETH60",1)} {md("ETHup")} {md("ETHdn")} | {md("BTC60")} {pc("BTC60",1)}')
        last = idx
    P('\nevery V4 event: close date | CT  K | USDT.D 60d | ETH 60d best worst | BTC 60d')
    for t in last:
        o = U.outcome(B, t, PX); f = lambda k: f'{o[k]:+6.1f}' if k in o else '    - '
        P(f'  {B[t]["d"]} | {B[t]["ct"]:4.1f} {B[t]["k"]:5.1f} | {f("dom30")} | {f("ETH60")} {f("ETHup")} {f("ETHdn")} | {f("BTC60")}')
    P('\n  Context only. Nothing adopted.')
    open(os.path.join(U.ROOT, 'analysis/RESULTS_usdtd_div2.txt'), 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    main()
