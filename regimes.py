"""Regime definitions. The point of this file is the LIVE column:
could you have known, on the day, whether you were in the regime?"""
import engine as E, datetime as dt

D=dt.date.fromisoformat

# BTC halvings. Block-height driven, so the date is predictable YEARS ahead
# to within a couple of weeks. This is the only cycle anchor that is genuinely
# knowable in advance.
HALV=[D('2012-11-28'),D('2016-07-09'),D('2020-05-11'),D('2024-04-19'),D('2028-04-01')]

# The user's cycle lows. A low is only known to BE a low in hindsight, so any
# rule anchored here is at best semi-live: you would have had to call the
# bottom in real time.
LOWS=[D('2015-01-14'),D('2018-12-15'),D('2022-11-21'),D('2026-06-24')]

def _since(d, anchors):
    last=None
    for a in anchors:
        if d>=a: last=a
    return None if last is None else (d-last).days

def halving(lo, hi):
    """Bull from halving+lo to halving+hi days. FULLY LIVE."""
    def f(d):
        n=_since(d,HALV)
        return n is not None and lo<=n<=hi
    return f

def from_low(lo, hi):
    """Bull from cycle low +lo to +hi days. SEMI-LIVE (needs the low called)."""
    def f(d):
        n=_since(d,LOWS)
        return n is not None and lo<=n<=hi
    return f

def ma_regime(path, n=200):
    """BTC close above its own n-day SMA. FULLY LIVE, no cycle theory at all."""
    b=E.load(path)
    sm=E.sma(b['close'],n)
    ok={}
    for i,d in enumerate(b['date']):
        ok[d]= (sm[i] is not None and b['close'][i]>sm[i])
    # carry forward for dates not on the BTC grid (e.g. 2D/3D/5D bars)
    days=sorted(ok)
    def f(d):
        if d in ok: return ok[d]
        prev=[x for x in days if x<=d]
        return ok[prev[-1]] if prev else False
    return f

def always(d): return True

BTC1D='/mnt/user-data/uploads/COINBASE_BTCUSD__1D_f16bd.csv'

def build():
    return [
      ('HINDSIGHT windows (current)', E.bull,            'NO  - ends on known tops'),
      ('halving +0 to +365d',         halving(0,365),    'YES - date known years out'),
      ('halving +0 to +550d',         halving(0,550),    'YES'),
      ('halving +0 to +730d',         halving(0,730),    'YES'),
      ('halving +180 to +550d',       halving(180,550),  'YES'),
      ('cycle low +0 to +900d',       from_low(0,900),   'PART- needs the low called'),
      ('BTC above its 200D SMA',      ma_regime(BTC1D,200),'YES - fully live'),
      ('BTC above its 100D SMA',      ma_regime(BTC1D,100),'YES - fully live'),
      ('NO regime filter at all',     always,            'YES - trivially'),
    ]


def rsi_regime(path, enterN=5, exitN=10, enterLvl=60, exitLvl=50,
               rsiLen=14, ret_series=False):
    """Jared's rule. CT RSI on a 2D chart holding the BULL CONTROL ZONE.

    State machine, fully live - every input is known on the bar:
      BEAR -> BULL  when CT RSI has been >= enterLvl for enterN consecutive bars
      BULL -> BEAR  when CT RSI has been <  exitLvl  for exitN  consecutive bars

    The asymmetry is the point: reclaiming the bull zone and HOLDING it is the
    bull signal; failing to hold it for an extended stretch is the bear signal.
    """
    b=E.load(path)
    ct=E.rsi(b['close'],rsiLen)
    state=False; up=0; dn=0
    ok={}
    for i,d in enumerate(b['date']):
        v=ct[i]
        if v is not None:
            up = up+1 if v>=enterLvl else 0
            dn = dn+1 if v< exitLvl  else 0
            if not state and up>=enterN: state=True; dn=0
            elif state and dn>=exitN:    state=False; up=0
        ok[d]=state
    days=sorted(ok)
    if ret_series: return ok,days
    def f(d):
        if d in ok: return ok[d]
        prev=[x for x in days if x<=d]
        return ok[prev[-1]] if prev else False
    return f

def combo(*fns):
    """All conditions must hold."""
    return lambda d: all(f(d) for f in fns)

def either(*fns):
    return lambda d: any(f(d) for f in fns)
