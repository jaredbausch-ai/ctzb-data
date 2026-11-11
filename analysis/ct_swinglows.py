"""Where does CT RSI bottom before it turns? (Jared, 11 Nov 2026, ETH 5D)
Descriptive, not a filter: the low is only known after the fact.
Swing low = the lowest CT between one run of CT >= 60 and the next run of CT >= 60.
Rise = highest high over the next 20 bars vs the close of the swing-low bar (hindsight
price, not an entry; a CTZB entry is 3 bars later).
  python3 -I analysis/ct_swinglows.py [ETH_5D] -> analysis/RESULTS_ct_swinglows_<chart>.txt
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E
chart = sys.argv[1] if len(sys.argv) > 1 else 'ETH_5D'
b = E.load(f'data/{chart}.csv'); d, c = b['date'], b['close']; ct = E.rsi(c, 14); n = len(c)
above = [x is not None and x >= 60 for x in ct]
out = [f'CT RSI swing lows, {chart} (last bar {d[-1]} is still forming)', 'date        CT    close     back above 60   rise next 20 bars']
t = 0
while t < n:
    if not above[t]: t += 1; continue
    while t < n and above[t]: t += 1
    s = t
    while t < n and not above[t]: t += 1
    seg = [(ct[j], j) for j in range(s, t) if ct[j] is not None]
    if not seg: continue
    v, j = min(seg)
    rise = f'{100 * (max(b["high"][j + 1:j + 21]) / c[j] - 1):+.0f}%' if j + 1 < n else '-'
    out.append(f'{d[j]}  {v:5.1f}  {c[j]:9.1f}  {"yes" if t < n else "NOT YET":<14}  {rise}')
out.append('Descriptive only: the swing low is known in hindsight. Entry quality only, no exit in the data.')
open(os.path.join(HERE, f'RESULTS_ct_swinglows_{chart}.txt'), 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
