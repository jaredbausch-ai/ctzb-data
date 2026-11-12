import sys, csv, datetime as dt, statistics
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from lib8 import *

GTF = ('1D', '2D', '3D', '5D')


def funding_ok(state):
    """ETH ledger membership needs funding data (fund read + fcool window), per grade_live's own rule."""
    out = {}
    for a in ('ETH', 'BTC'):
        p = f"{STATES[state]}/data/derivs/{a}_funding_daily.csv"
        fv = {}; fm = {}
        for r in csv.DictReader(open(p)):
            d = dt.date.fromisoformat(r['date'])
            v = r.get('funding_oi_weighted') or r.get('funding_mean')
            if v not in ('', None): fv[d] = float(v)
            if r.get('funding_mean') not in ('', None): fm[d] = float(r['funding_mean'])
        out[a] = (fv, fm)
    def ok(a, d0):
        fv, fm = out[a]
        if d0 not in fv: return False
        back = [fv.get(d0 - dt.timedelta(days=k)) for k in range(1, 91)]
        if sum(x is not None for x in back) < 60: return False
        w7 = sum((d0 - dt.timedelta(days=k)) in fm for k in range(7))
        w7b = sum((d0 - dt.timedelta(days=14 + k)) in fm for k in range(7))
        return w7 >= 5 and w7b >= 5
    return ok


_ALL = {}


def all_signals(state):
    if state in _ALL: return _ALL[state]
    res = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            tr, bars, ct, K = troughs(state, a, tf)
            res[(a, tf)] = dict(tr=tr, bars=bars, ct=ct, K=K)
    _ALL[state] = res
    return res


def my_ledger(state):
    """Expected ledger membership and measures: gated, confirmed, graded TF, 60th day closed, ETH funding rule."""
    S = all_signals(state)
    fok = funding_ok(state)
    rows = {}
    for (a, tf), v in S.items():
        if tf not in GTF: continue
        for s in v['tr']:
            if not (s['gated'] and s['closed']): continue
            m = measure(state, a, s['d0'], s['entry'])
            if m is None: continue
            if a == 'ETH' and not fok(a, s['d0']): continue
            s = dict(s, m=m)
            rows[(s['chart'], str(s['d0']))] = s
    return rows
