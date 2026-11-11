"""Re-entry by CT RSI level vs by the confirmed turn (Jared, 11 Nov 2026, ETH 5D).
For each completed swing (between runs of CT >= 60):
  LEVEL X: buy the close of the first bar with CT <= X. TURN: buy a CTZB signal's
  confirmation close (ei = ti + 3) whose trough CT < 40 (gated and ungated).
  drawdown = lowest low until CT is back >= 60, vs the buy close.
  up = highest high over the next 20 bars. Forming bar excluded.
ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
"""
import sys, os, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E, regimes as R
chart = sys.argv[1] if len(sys.argv) > 1 else 'ETH_5D'
G = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
b = E.load(f'data/{chart}.csv'); d, c, lo, hi = b['date'], b['close'], b['low'], b['high']
ct = E.rsi(c, 14); n = len(c) - 1
out = [f'{chart}: re-entry by CT level vs by the confirmed turn']
def back60(k): return next((j for j in range(k, n) if ct[j] is not None and ct[j] >= 60), None)
def summ(lab, rows, miss=None):
    dd = sorted(r[0] for r in rows); up = [r[1] for r in rows]
    out.append(f'{lab:<22} n {len(rows):2d}{"" if miss is None else f" (swings never reaching it: {miss})"}  '
               f'drawdown after: median {st.median(dd):+.0f}%, worse than -30% {sum(x <= -30 for x in dd)}, worst {dd[0]:+.0f}%  '
               f'| next-100d high median {st.median(up):+.0f}%')
above = [x is not None and x >= 60 for x in ct[:n]]; segs = []; t = 0
while t < n:
    if not above[t]: t += 1; continue
    while t < n and above[t]: t += 1
    s = t
    while t < n and not above[t]: t += 1
    if t < n and s < t: segs.append((s, t))
for X in (45, 40, 38, 35, 33, 30):
    rows = []; miss = 0
    for s, e in segs:
        j = next((k for k in range(s, e) if ct[k] is not None and ct[k] <= X), None)
        if j is None: miss += 1; continue
        rows.append((100 * (min(lo[j + 1:e + 1]) / c[j] - 1), 100 * (max(hi[j + 1:j + 21]) / c[j] - 1)))
    summ(f'first CT <= {X}', rows, miss)
for lab, reg, cap in (('turn, CT<40, gated', G, 40), ('turn, CT<40, ungated', lambda x: True, 40), ('turn, CT<35, ungated', lambda x: True, 35)):
    sig, _ = E.signals(f'data/{chart}.csv', regime=reg); rows = []
    for s in sig:
        ti, ei = s['ti'], s['ei']
        if ct[ti] is None or ct[ti] >= cap or ei >= n: continue
        e = back60(ei)
        if e is None: continue
        rows.append((100 * (min(lo[ei + 1:e + 1]) / c[ei] - 1) if e > ei else 0, 100 * (max(hi[ei + 1:ei + 21]) / c[ei] - 1)))
    summ(lab, rows)
out.append('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
open(os.path.join(HERE, f'RESULTS_ct_reentry_{chart}.txt'), 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
