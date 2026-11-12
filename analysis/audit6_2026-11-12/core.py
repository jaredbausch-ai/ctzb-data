"""Audit 6 -- independent recomputation core. Written from the documented definitions only.

Only regimes.py is imported from the repo (the gate). Everything else (candles, bucketing, clamp,
RSI, stochastic, pivots, tags, forward measures, ladder, rounding) is my own code.
"""
import csv, datetime as dt, math, os, sys, statistics
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

LIQ = Fraction(253, 1000)          # 25.3%
EPS = 1e-9                         # documented engine.EPS (12 Nov 2026 audit corrections (3))
SPLIT = dt.date(2022, 1, 1)
GRADED = ('1D', '2D', '3D', '5D')
TFS = ('1D', '2D', '3D', '5D', '8D')


# ------------------------------------------------------------------ rounding
def rh(x, nd=0):
    """Half away from zero, once, on the exact value (Fraction exact, float = its binary value)."""
    if x is None:
        return None
    if isinstance(x, Fraction):
        q = Fraction(1, 10 ** nd)
        k = x / q
        n = math.floor(abs(k) + Fraction(1, 2))
        v = (n if k >= 0 else -n) * q
        return int(v) if nd == 0 else float(v)
    d = Decimal(float(x)).quantize(Decimal(1).scaleb(-nd) if nd else Decimal(1), rounding=ROUND_HALF_UP)
    return int(d) if nd == 0 else float(d)


def share(k, n):
    return None if not n else rh(Fraction(100 * k, n))


def med(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def med_exact(xs):
    """median as Fraction for integer lists (so x.5 rounds correctly)"""
    xs = sorted(Fraction(x) for x in xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


# ------------------------------------------------------------------ candles
def utc_date(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def read_csv_bars(path):
    out = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            out.append((utc_date(r['time']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])))
    return out


def clamp(o, h, l, c):
    """Documented flash-print clamp: a low under half the bar's body bottom (or a high over twice its top)
    is pulled back to the body."""
    lb, hb = min(o, c), max(o, c)
    if lb > 0 and l < 0.5 * lb:
        l = lb
    if hb > 0 and h > hb / 0.5:
        h = hb
    return o, h, l, c


def bucket_key(d, tf):
    return (d.year, (d - dt.date(d.year, 1, 1)).days // tf)


def bucket_span(d_open, tf):
    """(first day, nominal last day) of the bucket that opens on d_open; 2D+ restart on 1 January."""
    y0 = dt.date(d_open.year, 1, 1)
    k = (d_open - y0).days // tf
    first = y0 + dt.timedelta(days=k * tf)
    last = min(first + dt.timedelta(days=tf - 1), dt.date(d_open.year, 12, 31))
    return first, last


def build_bars(daily, tf):
    """daily: list of (date,o,h,l,c) raw. Returns list of dict(open_date, o,h,l,c, days=[...], last_day)."""
    if tf == 1:
        return [dict(t=d, o=o, h=h, l=l, c=c, days=[d]) for d, o, h, l, c in daily]
    g = {}
    for row in daily:
        g.setdefault(bucket_key(row[0], tf), []).append(row)
    out = []
    for k in sorted(g):
        rs = g[k]
        out.append(dict(t=rs[0][0], o=rs[0][1], h=max(r[2] for r in rs), l=min(r[3] for r in rs), c=rs[-1][4],
                        days=[r[0] for r in rs]))
    return out


class Asset:
    def __init__(self, root, a, today):
        self.a = a
        self.raw = read_csv_bars(os.path.join(root, 'data', f'{a}_1D.csv'))
        self.today = today
        self.D = [r[0] for r in self.raw]
        cl = [clamp(*r[1:]) for r in self.raw]
        self.O = [x[0] for x in cl]; self.H = [x[1] for x in cl]; self.L = [x[2] for x in cl]; self.C = [x[3] for x in cl]
        self.pos = {d: i for i, d in enumerate(self.D)}
        self.clamped = [(self.raw[i][0], self.raw[i][3], self.L[i]) for i in range(len(self.raw)) if self.raw[i][3] != self.L[i]] + \
                       [(self.raw[i][0], self.raw[i][2], self.H[i]) for i in range(len(self.raw)) if self.raw[i][2] != self.H[i]]
        self.bars = {}
        for tf in TFS:
            self.bars[tf] = build_bars(self.raw, int(tf[:-1]))

    def closed(self, d):
        return d < self.today          # a daily bar has closed once its UTC day is over

    def bar(self, d):
        i = self.pos.get(d)
        return None if i is None else (self.H[i], self.L[i], self.C[i])


# ------------------------------------------------------------------ indicator
def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        up += max(ch, 0.0); dn += max(-ch, 0.0)
    au, ad = up / n, dn / n
    out[n] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        au = (au * (n - 1) + max(ch, 0.0)) / n
        ad = (ad * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    return out


def stoch_k(ct, n=14, sm=3):
    st = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0:
            continue
        w = ct[i - n + 1:i + 1]
        if any(v is None for v in w):
            continue
        hi, lo = max(w), min(w)
        st[i] = 0.0 if hi == lo else 100.0 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        if i - sm + 1 < 0:
            continue
        w = st[i - sm + 1:i + 1]
        if any(v is None for v in w):
            continue
        k[i] = sum(w) / sm
    return k


def troughs(bars):
    """Every pivot low on CT (3 strictly higher bars each side), with K, CT, diamond vs previous trough."""
    C = [b['c'] for b in bars]
    ct = rsi(C); K = stoch_k(ct)
    out = []
    prev = None
    for ti in range(3, len(bars) - 3):
        w = ct[ti - 3:ti + 4]
        if any(v is None for v in w):
            continue
        v = ct[ti]
        if not all(ct[j] > v for j in range(ti - 3, ti + 4) if j != ti):
            continue
        if K[ti] is None:
            continue
        dis = False
        if prev is not None:
            dc, dk = v - prev[0], K[ti] - prev[1]
            dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
        out.append(dict(ti=ti, ei=ti + 3, ct=v, k=K[ti], dis=dis, strong=dis and v < 50,
                        prime=20 <= K[ti] < 50, bk='A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'))
        prev = (v, K[ti])
    return out, ct, K


def tagstr(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else [])
                      + (['prime dot'] if s['prime'] else []))


def signals(asset, tf, gate):
    """Gated signals with entry date d0 (close date of the confirmation bar) when that bar has closed."""
    bars = asset.bars[tf]
    tr, ct, K = troughs(bars)
    out = []
    for s in tr:
        tb = bars[s['ti']]
        if not gate(tb['t']):          # (a) the gate is read on the trough date
            continue
        eb = bars[s['ei']]
        first, last = bucket_span(eb['t'], int(tf[:-1]))
        s = dict(s, tdate=tb['t'], conf_open=eb['t'], d0=last, entry=eb['c'], tf=tf, a=asset.a,
                 confirmed=asset.closed(last) and eb['days'][-1] == last,
                 trough_days=tb['days'])
        out.append(s)
    return out, ct, K


# ------------------------------------------------------------------ forward measures (daily, calendar)
def window(asset, d0, upto=60, closed_only=True):
    """[(k, H, L, C)] for k = 1..upto calendar days after d0, only bars present (and closed if asked)."""
    out = []
    for k in range(1, upto + 1):
        d = d0 + dt.timedelta(days=k)
        i = asset.pos.get(d)
        if i is None:
            continue
        if closed_only and not asset.closed(d):
            continue
        out.append((k, asset.H[i], asset.L[i], asset.C[i]))
    return out


def complete(asset, d0):
    d60 = d0 + dt.timedelta(days=60)
    return all((d0 + dt.timedelta(days=k)) in asset.pos for k in range(1, 61)) and asset.closed(d60)


def measures(asset, d0, e):
    w = window(asset, d0)
    if len(w) != 60 or not complete(asset, d0):
        return None
    hs = [x[1] for x in w]; ls = [x[2] for x in w]
    mh = max(hs); kh = next(x[0] for x in w if x[1] == mh)
    ml = min(ls); kl = next(x[0] for x in w if x[2] == ml)
    pre = [x[2] for x in w if x[0] <= kh]          # low before high: the high day's low counts
    F = lambda p: (p / e - 1) * 100
    E = Fraction(e)
    m = dict(up=F(mh), dd=F(ml), ddpk=F(min(pre)), ret=F(w[-1][3]), dpk=kh, ddday=kl,
             r10=Fraction(mh) >= E * Fraction(11, 10), r15=Fraction(mh) >= E * Fraction(115, 100),
             r20=Fraction(mh) >= E * Fraction(12, 10), t30=Fraction(ml) <= E * Fraction(7, 10),
             f25=Fraction(ml) <= E * (1 - LIQ))
    m['surv10'] = m['r10'] and not m['f25']
    # day of first +10% / +20% (calendar days)
    m['d10'] = next((x[0] for x in w if Fraction(x[1]) >= E * Fraction(11, 10)), None)
    m['d20'] = next((x[0] for x in w if Fraction(x[1]) >= E * Fraction(12, 10)), None)
    # from entry: rose 10% before ever falling 25.3% (low first within a day)
    fe = None
    for k, h, l, c in w:
        if Fraction(l) <= E * (1 - LIQ):
            fe = 'liq'; break
        if Fraction(h) >= E * Fraction(11, 10):
            fe = 'ok'; break
    m['fe'] = fe
    lad = {}
    for th in (5, 10, 15, 20):
        res = None
        for j, (k, h, l, c) in enumerate(w):
            if Fraction(l) <= E * (1 - Fraction(th, 100)):
                res = 'hit'
                for k2, h2, l2, c2 in w[j:]:
                    if Fraction(l2) <= E * (1 - LIQ):
                        res = 'liq'; break
                    if Fraction(h2) >= E * Fraction(11, 10):
                        res = 'ok'; break
                break
            if Fraction(h) >= E * Fraction(11, 10):
                break
        lad[th] = res
    m['lad'] = lad
    return m


# ------------------------------------------------------------------ volatility ratio (scaled20)
class Vol:
    def __init__(self, asset):
        c = [x[4] for x in asset.raw]
        lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
        self.v = {}
        for i in range(365, len(c)):
            self.v[asset.raw[i][0]] = statistics.pstdev(lr[i - 364:i + 1])
        self.med = statistics.median(v for d, v in self.v.items() if d.year <= 2021)

    def ratio(self, d):
        x = self.v.get(d)
        return None if x is None else x / self.med


def quant(vals, f):
    s = sorted(vals)
    k = (len(s) - 1) * f
    lo = int(math.floor(k)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
