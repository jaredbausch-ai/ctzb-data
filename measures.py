"""Success measures (set by Jared 28 Oct 2026, after tonight's yardstick comparison).

SURV10    (the card's headline until 11 Nov 2026; since then the line under the big number, which
          is "rose 10% within 60 days") price reached +10% above entry within 60 days AND never touched
          -25.3% below entry in those 60 days (-25.3% is where 3.3x leverage with 5%
          maintenance margin liquidates). When it was chosen (28 Oct 2026) it barely
          drifted between markets (66% to 2021, 62% from 2022) and separated A+ (79%) from C (58%);
          those are that day's figures, the current ones are in datasets/grades.csv.
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
        # the median uses closed bars only: the file's last row is today's open bar (13 Nov 2026 audit #26: a
        # replay dated in 2016-21 counted it, which moved scaled20; today's runs are unaffected, the open bar is 2026)
        med = st.median(v for k, v in vol.items() if k.year <= 2021 and k < d['date'][-1])
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


_D = {}


def days_to(a, d0, entry, pct, H=60):
    """Calendar days from entry (d0) to the first 1D high at least pct% above entry,
    within H days; None if it never got there (card timing, 1 Nov 2026)."""
    import datetime as _dt
    if a not in _D:
        d = E.load(os.path.join(HERE, 'data', f'{a}_1D.csv')); _D[a] = (d, {x: i for i, x in enumerate(d['date'])})
    d, pos = _D[a]; i = pos.get(d0)
    if i is None: return None
    end = d0 + _dt.timedelta(days=H)
    for k in range(i + 1, len(d['date'])):
        if d['date'][k] > end: break
        if d['high'][k] >= entry * (1 + pct / 100): return (d['date'][k] - d0).days
    return None
