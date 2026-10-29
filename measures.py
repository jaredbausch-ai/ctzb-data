"""Success measures (set by Jared 28 Oct 2026, after tonight's yardstick comparison).

HEADLINE  surv10: price reached +10% above entry within 60 days AND never touched
          -25% below entry in those 60 days (-25.3% is where 3.3x leverage with 5%
          maintenance margin liquidates). Barely drifts between markets (66% to
          2021, 62% from 2022) and separates A+ (79%) from C (58%).
MOVE      scaled20: the best move within 60 days reached +20% x (365-day daily
          volatility at entry / the asset's 2016-21 median of it), so a calm market
          asks less of a signal than a wild one (analysis/voltarget.py).
CONTEXT   fixed +20% in 60 days, unchanged.
Entry quality only. Computed signals, not fills.
"""
import math, os, statistics as st
import engine as E

HERE = os.path.dirname(os.path.abspath(__file__))
LIQ = -25.3
_C = {}


def _vol(a):
    if a not in _C:
        d = E.load(os.path.join(HERE, 'data', f'{a}_1D.csv')); c = d['close']
        lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
        vol = {d['date'][i]: st.pstdev(lr[i - 364:i + 1]) for i in range(365, len(c))}
        med = st.median(v for k, v in vol.items() if k.year <= 2021)
        _C[a] = (vol, med)
    return _C[a]


def vol_ratio(a, d0):
    vol, med = _vol(a)
    v = vol.get(d0)
    return None if v is None else v / med


def surv10(m):
    return m['up'] >= 10 and m['dd'] > LIQ


def scaled20(a, d0, m):
    r = vol_ratio(a, d0)
    return None if r is None else m['up'] >= 20 * r
