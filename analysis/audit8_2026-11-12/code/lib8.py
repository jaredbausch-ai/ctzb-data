"""Audit #8 independent engine. Own code; regimes.py imported for the gate only."""
import csv, datetime as dt, math, os, sys, statistics
from fractions import Fraction as F
from decimal import Decimal, ROUND_HALF_UP

SCR = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'
STATES = {'REPLAY': SCR + '/a8/replay_0414', 'CURRENT': SCR + '/a8/current'}
TODAY = {'REPLAY': dt.date(2026, 11, 12), 'CURRENT': dt.date(2026, 11, 12)}
TFD = {'1D': 1, '2D': 2, '3D': 3, '5D': 5, '8D': 8}
LIQ = F(253, 1000)


def rhaz(x, nd=0):
    """round half away from zero on the EXACT value (Fraction or int)."""
    if x is None: return None
    x = F(x)
    q = F(1, 10 ** nd)
    n = x / q
    s = -1 if n < 0 else 1
    n = abs(n)
    fl = n.numerator // n.denominator
    r = n - fl
    k = fl + 1 if r >= F(1, 2) else fl
    v = s * k * q
    if nd == 0: return int(v)
    return float(Decimal(v.numerator) / Decimal(v.denominator))


def fdate(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def load(state, asset, tf):
    rows = list(csv.DictReader(open(f"{STATES[state]}/data/{asset}_{tf}.csv")))
    out = []
    clamps = []
    for r in rows:
        o, h, l, c = (F(r[k]) for k in ('open', 'high', 'low', 'close'))
        lb, hb = min(o, c), max(o, c)
        d = fdate(r['time'])
        if lb > 0 and l < lb / 2:
            clamps.append((d, 'low', l, lb)); l = lb
        if hb > 0 and h > hb * 2:
            clamps.append((d, 'high', h, hb)); h = hb
        out.append(dict(d=d, o=o, h=h, l=l, c=c, cf=float(c), t=int(r['time'])))
    return out, clamps


def bar_last_day(d, tf):
    n = TFD[tf]
    if n == 1: return d
    j1 = dt.date(d.year, 1, 1)
    idx = (d - j1).days // n
    end = j1 + dt.timedelta(days=(idx + 1) * n - 1)
    return min(end, dt.date(d.year, 12, 31))


def bar_open_of(day, tf):
    n = TFD[tf]
    j1 = dt.date(day.year, 1, 1)
    return j1 + dt.timedelta(days=((day - j1).days // n) * n)


def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1: return out
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        g += max(ch, 0.0); l += max(-ch, 0.0)
    ag, al = g / n, l / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        ag = (ag * (n - 1) + max(ch, 0.0)) / n
        al = (al * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def stochK(ct, n=14, sm=3):
    st_ = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0: continue
        w = ct[i - n + 1:i + 1]
        if any(x is None for x in w): continue
        hi, lo = max(w), min(w)
        st_[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        w = st_[max(0, i - sm + 1):i + 1]
        if len(w) == sm and all(x is not None for x in w):
            k[i] = sum(w) / sm
    return k


_GATE = {}


def gate(state):
    if state not in _GATE:
        sys.path.insert(0, STATES[state])
        cwd = os.getcwd(); os.chdir(STATES[state])
        import importlib
        for m in ('regimes', 'engine'):
            if m in sys.modules: del sys.modules[m]
        R = importlib.import_module('regimes')
        _GATE[state] = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
        os.chdir(cwd); sys.path.pop(0)
    return _GATE[state]


EPS = 1e-9


def troughs(state, asset, tf):
    """All confirmed pivots (conf bar closed), ungated chain, gate flag on trough date."""
    bars, _ = load(state, asset, tf)
    today = TODAY[state]
    c = [b['cf'] for b in bars]
    ct = rsi(c); K = stochK(ct)
    g = gate(state)
    out = []
    prev = None
    n = len(bars)
    for ti in range(3, n - 3):
        v = ct[ti]
        if v is None: continue
        nb = [ct[j] for j in range(ti - 3, ti + 4) if j != ti]
        if any(x is None for x in nb): continue
        if not all(x > v for x in nb): continue
        k = K[ti]
        if k is None: continue
        ei = ti + 3
        d0 = bar_last_day(bars[ei]['d'], tf)
        conf_closed = d0 < today and ei < n - 1
        dis = False
        if prev is not None:
            dc = v - prev[0]; dk = k - prev[1]
            dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
        prev = (v, k)
        bk = 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'
        out.append(dict(asset=asset, tf=tf, chart=f'{asset} {tf}', ti=ti, ei=ei, tdate=bars[ti]['d'], d0=d0,
                        conf_open=bars[ei]['d'], entry=bars[ei]['c'], ct=v, k=k, bk=bk, dis=dis, strong=dis and v < 50,
                        prime=20 <= k < 50, gated=bool(g(bars[ti]['d'])), closed=conf_closed,
                        next_open=bars[ei + 1]['d'] if ei + 1 < n else None, tlow=bars[ti]['l']))
    return out, bars, ct, K


def tags(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))


_DAY = {}


def daily(state, asset):
    if (state, asset) not in _DAY:
        b, cl = load(state, asset, '1D')
        _DAY[(state, asset)] = (b, {x['d']: i for i, x in enumerate(b)}, cl)
    return _DAY[(state, asset)]


def window(state, asset, d0, H=60, closed_only=True):
    """daily bars of calendar days d0+1..d0+H, only closed ones (date < today) if closed_only."""
    b, pos, _ = daily(state, asset)
    today = TODAY[state]
    i0 = pos[d0]
    w = []
    for k in range(i0 + 1, len(b)):
        dd = (b[k]['d'] - d0).days
        if dd > H: break
        if closed_only and b[k]['d'] >= today: break
        w.append((dd, b[k]))
    return w


def measure(state, asset, d0, entry):
    """Full 60-day forward measures (exact Fractions), or None if day 60 hasn't closed."""
    w = window(state, asset, d0)
    if not w or w[-1][0] != 60: return None
    E = entry
    his = [x['h'] for _, x in w]; los = [x['l'] for _, x in w]
    mh = max(his); ml = min(los)
    kp = his.index(mh); kl = los.index(ml)
    pre = min(los[:kp + 1])
    up = (mh / E - 1) * 100; dd = (ml / E - 1) * 100
    m = dict(up=up, dd=dd, ddpk=(pre / E - 1) * 100, ret=(w[-1][1]['c'] / E - 1) * 100,
             dpk=w[kp][0], ddday=w[kl][0], ndays=len(w))
    m['r10'] = mh >= E * F(11, 10); m['r15'] = mh >= E * F(115, 100); m['r20'] = mh >= E * F(12, 10)
    m['t30'] = ml <= E * F(7, 10)
    m['surv10'] = m['r10'] and ml > E * (1 - LIQ)
    first = lambda th: next((dd_ for dd_, x in w if x['h'] >= E * th), None)
    m['d10'] = first(F(11, 10)); m['d20'] = first(F(12, 10))
    # ladder walk, low before high
    def walk(start):
        for dd_, x in w[start:]:
            if x['l'] <= E * (1 - LIQ): return 'liq'
            if x['h'] >= E * F(11, 10): return 'ok'
        return None
    m['l0'] = walk(0)
    lad = {}
    for th in (5, 10, 15, 20):
        res = None
        for j, (dd_, x) in enumerate(w):
            if x['l'] <= E * (1 - F(th, 100)):
                res = ('hit', walk(j)); break
            if x['h'] >= E * F(11, 10):
                break
        lad[th] = res
    m['lad'] = lad
    m['path'] = [F(0)] + [(x['c'] / E - 1) * 100 for _, x in w]
    m['days_present'] = [dd_ for dd_, _ in w]
    return m


_VOL = {}


def volratio(state, asset, d0):
    if (state, asset) not in _VOL:
        b, pos, _ = daily(state, asset)
        c = [x['cf'] for x in b]
        lr = [None] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
        vol = {}
        for i in range(365, len(c)):
            vol[b[i]['d']] = statistics.pstdev(lr[i - 364:i + 1])
        med = statistics.median(v for k, v in vol.items() if k.year <= 2021)
        _VOL[(state, asset)] = (vol, med)
    vol, med = _VOL[(state, asset)]
    v = vol.get(d0)
    return None if v is None else v / med


def med(xs):
    s = sorted(xs)
    n = len(s)
    if not n: return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quant(xs, f):
    s = sorted(xs); k = (len(s) - 1) * F(f); lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def pct(k, n):
    return rhaz(F(100 * k, n)) if n else None
