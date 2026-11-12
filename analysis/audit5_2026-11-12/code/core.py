"""Audit 5 -- independent core. Written from the stated definitions, not from the pipeline.

Prices are exact (Fraction from the CSV's decimal strings). The oscillators (RSI, stoch, K) are
floats, as on TradingView. regimes.py is imported for the gate only.
"""
import csv, math, sys, os, datetime as dt, statistics
from fractions import Fraction as Fr
from decimal import Decimal, ROUND_HALF_UP

ONE_DAY = dt.timedelta(days=1)
H = 60
LIQ = Fr(253, 1000)


# ---------------------------------------------------------------- rounding
def rhaz(x, nd=0):
    """Round half away from zero on the EXACT value (Fraction or float's exact binary value)."""
    if x is None:
        return None
    if isinstance(x, float):
        x = Fr(x)
    q = Fr(10) ** nd
    y = abs(x) * q
    k = int(y)              # floor for non-negative
    if y - k >= Fr(1, 2):
        k += 1
    v = Fr(k, 1) / q * (1 if x >= 0 else -1)
    if nd == 0:
        return int(v)
    return float(v)


def pct(x):
    """Fraction ratio-1 -> percent Fraction."""
    return x * 100


# ---------------------------------------------------------------- candles
class Bars:
    def __init__(self, path, tf):
        self.tf = tf
        self.path = path
        rows = list(csv.DictReader(open(path, newline='')))
        self.t = []; self.D = []; self.O = []; self.H = []; self.L = []; self.C = []; self.clamps = []
        for r in rows:
            t = int(r['time'])
            d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
            o, h, l, c = (Fr(r[k].strip()) for k in ('open', 'high', 'low', 'close'))
            lb, hb = min(o, c), max(o, c)
            if lb > 0 and l < lb / 2:
                self.clamps.append((d, 'low', l, lb)); l = lb
            if hb > 0 and h > hb * 2:
                self.clamps.append((d, 'high', h, hb)); h = hb
            self.t.append(t); self.D.append(d); self.O.append(o); self.H.append(h); self.L.append(l); self.C.append(c)
        self.n = len(self.D)
        self.Cf = [float(c) for c in self.C]
        self.pos = {d: i for i, d in enumerate(self.D)}

    def end_date(self, i):
        """Last calendar day the bar covers: the day before the next bar opens; for the last bar,
        open + tf - 1, never past 31 Dec (bars restart on 1 Jan)."""
        if i + 1 < self.n:
            return self.D[i + 1] - ONE_DAY
        nd = int(self.tf.rstrip('D'))
        e = self.D[i] + dt.timedelta(days=nd - 1)
        ye = dt.date(self.D[i].year, 12, 31)
        return min(e, ye)

    def closed(self, i, now):
        """A bar has closed once the clock is at or past 00:00 UTC of the day after its last day."""
        e = self.end_date(i)
        return now >= dt.datetime.combine(e + ONE_DAY, dt.time(0), tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------- oscillators (float)
def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: g += ch
        else: l -= ch
    ag, al = g / n, l / n
    out[n] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        up = ch if ch > 0 else 0.0
        dn = -ch if ch < 0 else 0.0
        ag = (ag * (n - 1) + up) / n
        al = (al * (n - 1) + dn) / n
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def rsi_state(c, n=14):
    """RSI plus the running averages, for solving the kill close."""
    ags = [None] * len(c); als = [None] * len(c)
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: g += ch
        else: l -= ch
    ag, al = g / n, l / n; ags[n] = ag; als[n] = al
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        ag = (ag * (n - 1) + (ch if ch > 0 else 0.0)) / n
        al = (al * (n - 1) + (-ch if ch < 0 else 0.0)) / n
        ags[i] = ag; als[i] = al
    return ags, als


def stoch(src, n=14):
    out = [None] * len(src)
    for i in range(n - 1, len(src)):
        w = src[i - n + 1:i + 1]
        if any(x is None for x in w):
            continue
        hi, lo = max(w), min(w)
        out[i] = 0.0 if hi == lo else 100.0 * (src[i] - lo) / (hi - lo)
    return out


def sma(src, n):
    out = [None] * len(src)
    for i in range(n - 1, len(src)):
        w = src[i - n + 1:i + 1]
        if any(x is None for x in w):
            continue
        out[i] = sum(w) / n
    return out


def ema(src, n):
    out = [None] * len(src)
    first = next((i for i, v in enumerate(src) if v is not None), None)
    if first is None or len(src) - first < n:
        return out
    a = 2.0 / (n + 1)
    prev = sum(src[first:first + n]) / n
    out[first + n - 1] = prev
    for i in range(first + n, len(src)):
        prev = prev + a * (src[i] - prev)
        out[i] = prev
    return out


EPS = 1e-9


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


# ---------------------------------------------------------------- gate
_GATE = {}


def gate_for(root):
    if root not in _GATE:
        sys.path.insert(0, root)
        import importlib
        import regimes as R  # gate only
        importlib.reload(R)
        _GATE[root] = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        sys.path.remove(root)
    return _GATE[root]


# ---------------------------------------------------------------- signals
def pivots(b):
    ct = rsi(b.Cf, 14)
    K = sma(stoch(ct, 14), 3)
    out = []
    for ti in range(3, b.n - 3):
        w = ct[ti - 3:ti + 4]
        if any(x is None for x in w):
            continue
        v = ct[ti]
        if all(ct[j] > v for j in range(ti - 3, ti)) and all(ct[j] > v for j in range(ti + 1, ti + 4)):
            if K[ti] is None:
                continue
            out.append(ti)
    return ct, K, out


def signals(root, a, tf, now):
    """Every gated trough on a chart whose confirmation bar has CLOSED by `now`.
    Gate read on the trough bar's open date. Diamond vs the previous trough of the whole chain."""
    b = Bars(os.path.join(root, 'data', f'{a}_{tf}.csv'), tf)
    gate = gate_for(root)
    ct, K, piv = pivots(b)
    em = ema(ct, 14)
    out = []
    prev = None
    for ti in piv:
        v, k = ct[ti], K[ti]
        dis = False
        if prev is not None:
            dct, dk = v - prev[0], k - prev[1]
            dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
        prev = (v, k)
        if not gate(b.D[ti]):
            continue
        ei = ti + 3
        s = dict(a=a, tf=tf, ti=ti, ei=ei, trough=b.D[ti], ct=v, k=k, bk=bucket(v), dis=dis,
                 filled=dis and v < 50, prime=20 <= k < 50, entry=b.C[ei],
                 confirmed=b.closed(ei, now), d0=b.end_date(ei), conf_open=b.D[ei],
                 gap=(ct[ei] - em[ei]) if ct[ei] is not None and em[ei] is not None else None)
        s['tags'] = ' + '.join([s['bk']] + (['filled diamond'] if s['filled'] else ['hollow diamond'] if dis else []) + (['prime dot'] if s['prime'] else []))
        out.append(s)
    return out, b, ct, K


# ---------------------------------------------------------------- daily
class Daily:
    def __init__(self, root, a):
        self.b = Bars(os.path.join(root, 'data', f'{a}_1D.csv'), '1D')
        self.pos = self.b.pos

    def bar(self, d):
        i = self.pos.get(d)
        return None if i is None else (self.b.H[i], self.b.L[i], self.b.C[i])

    def window(self, d0, now, upto=H):
        """[(k, high, low, close)] for k = 1..upto calendar days after d0, closed bars only."""
        out = []
        for k in range(1, upto + 1):
            d = d0 + dt.timedelta(days=k)
            i = self.pos.get(d)
            if i is None:
                continue
            if not self.b.closed(i, now):
                break
            out.append((k, self.b.H[i], self.b.L[i], self.b.C[i]))
        return out

    def complete(self, d0, now):
        d60 = d0 + dt.timedelta(days=H)
        i = self.pos.get(d60)
        return i is not None and self.b.closed(i, now)


def measure(e, w):
    """60-day forward measures from entry close e over window w (k, h, l, c)."""
    hs = [x[1] for x in w]; ls = [x[2] for x in w]
    mh = max(hs); ml = min(ls)
    kp = next(x[0] for x in w if x[1] == mh)          # first day of the 60-day high
    kl = next(x[0] for x in w if x[2] == ml)          # first day of the deepest low
    pre = [x[2] for x in w if x[0] <= kp]
    up = (mh / e - 1) * 100
    dd = (ml / e - 1) * 100
    ddpk = (min(pre) / e - 1) * 100
    ret = (w[-1][3] / e - 1) * 100
    first = lambda f: next((x[0] for x in w if x[1] >= e * f), None)
    return dict(up=up, dd=dd, ddpk=ddpk, ret=ret, dpk=kp, ddday=kl, ret_day=w[-1][0],
                r10=mh >= e * Fr(11, 10), r15=mh >= e * Fr(115, 100), r20=mh >= e * Fr(6, 5),
                t30=ml <= e * Fr(7, 10), surv10=(mh >= e * Fr(11, 10)) and not (ml <= e * (1 - LIQ)),
                d10=first(Fr(11, 10)), d20=first(Fr(6, 5)), n=len(w))


def ladder_one(e, w, th, low_first=True):
    """('rose'|'none'|'hit', outcome) for one signal and one first-fall threshold.
    low_first: within one daily bar the low is checked before the high (choice (c))."""
    fall = e * (1 - Fr(th, 100)); up = e * Fr(11, 10); liq = e * (1 - LIQ)
    for j, (k, h, l, c) in enumerate(w):
        if low_first:
            if l <= fall:
                break
            if h >= up:
                return 'rose', None
        else:
            if h >= up:
                return 'rose', None
            if l <= fall:
                break
    else:
        return 'none', None
    for (k, h, l, c) in w[j:]:
        if l <= liq:
            return 'hit', 'liq'
        if h >= up:
            return 'hit', 'ok'
    return 'hit', None


def ladder(G, low_first=True):
    res = []
    for th in (5, 10, 15, 20):
        hit = ok = lq = 0
        for s in G:
            r, o = ladder_one(s['e'], s['w'], th, low_first)
            if r == 'hit':
                hit += 1; ok += o == 'ok'; lq += o == 'liq'
        res.append(dict(fell=th, n=hit, ok=rhaz(Fr(100 * ok, hit)) if hit else None, liq=rhaz(Fr(100 * lq, hit)) if hit else None,
                        ok_exact=(Fr(100 * ok, hit) if hit else None)))
    return res


# ---------------------------------------------------------------- volatility (beat a normal move)
_VOL = {}


def vol_ratio(root, a, d0):
    key = (root, a)
    if key not in _VOL:
        b = Bars(os.path.join(root, 'data', f'{a}_1D.csv'), '1D')
        lr = [0.0] + [math.log(b.Cf[i] / b.Cf[i - 1]) for i in range(1, b.n)]
        vol = {}
        for i in range(365, b.n):
            vol[b.D[i]] = statistics.pstdev(lr[i - 364:i + 1])
        med = statistics.median(v for d, v in vol.items() if d.year <= 2021)
        _VOL[key] = (vol, med)
    vol, med = _VOL[key]
    v = vol.get(d0)
    return None if v is None else v / med


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(xs, f):
    s = sorted(xs)
    k = (len(s) - 1) * Fr(f).limit_denominator(1000)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def share(k, n):
    return None if not n else rhaz(Fr(100 * k, n))
