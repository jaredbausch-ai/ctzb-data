"""Audit 15 -- independent core. Everything here is my own code; only regimes.rsi_regime is imported
(the gate, as instructed). Exact arithmetic (Fractions built from the CSV decimal strings) wherever a
threshold or a rounding is decided; floats only inside the oscillators (RSI / Stoch), which have no
exact form."""
import csv, datetime as dt, os, sys, json
from fractions import Fraction as Fr
from decimal import Decimal

TFS = ('1D', '2D', '3D', '5D', '8D'); GRADED = ('1D', '2D', '3D', '5D'); ASSETS = ('ETH', 'BTC')
EPS = 1e-9
LIQ = Fr(253, 1000)          # 25.3%


def rhu(x, nd=0):
    """round half away from zero, exactly; returns Fraction"""
    x = Fr(x); s = 10 ** nd; y = abs(x) * s
    n = (2 * y.numerator + y.denominator) // (2 * y.denominator)
    r = Fr(n, s)
    return -r if x < 0 else r


def fstr(x, nd):
    """Fraction -> fixed string with nd decimals (x already rounded)"""
    x = Fr(x); neg = x < 0; y = abs(x) * 10 ** nd
    assert y.denominator == 1, x
    s = str(y.numerator).rjust(nd + 1, '0')
    out = (s[:-nd] + '.' + s[-nd:]) if nd else s
    return ('-' if neg and y != 0 else '') + out


def median(xs):
    s = sorted(xs); n = len(s)
    if not n: return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


class Candles:
    def __init__(self, path):
        self.date = []; self.o = []; self.h = []; self.l = []; self.c = []; self.clamped = []
        for r in csv.DictReader(open(path)):
            d = dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date()
            o, h, l, c = (Fr(Decimal(r[k])) for k in ('open', 'high', 'low', 'close'))
            lb, hb = min(o, c), max(o, c)
            # the documented flash-print clamp: a low under half the body's low, or a high over twice the
            # body's high, is pulled back to the body
            if lb > 0 and l < lb / 2: self.clamped.append((d, 'low', l, lb)); l = lb
            if hb > 0 and h > hb * 2: self.clamped.append((d, 'high', h, hb)); h = hb
            self.date.append(d); self.o.append(o); self.h.append(h); self.l.append(l); self.c.append(c)
        self.pos = {d: i for i, d in enumerate(self.date)}
        self.cf = [float(x) for x in self.c]
        self.n = len(self.c)


def wilder_rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n: return out
    ups = [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]
    dns = [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
    au = sum(ups[:n]) / n; ad = sum(dns[:n]) / n
    f = lambda u, d: 100.0 if d == 0 else 100.0 - 100.0 / (1.0 + u / d)
    out[n] = f(au, ad)
    for i in range(n, len(ups)):
        au = (au * (n - 1) + ups[i]) / n; ad = (ad * (n - 1) + dns[i]) / n
        out[i + 1] = f(au, ad)
    return out


def stoch_k(ct, n=14, sm=3):
    st = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0: continue
        w = ct[i - n + 1:i + 1]
        if any(v is None for v in w): continue
        hi, lo = max(w), min(w)
        st[i] = 0.0 if hi == lo else 100.0 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        if i - sm + 1 < 0: continue
        w = st[i - sm + 1:i + 1]
        if any(v is None for v in w): continue
        k[i] = sum(w) / sm
    return k


def ema_seeded(src, n=14):
    out = [None] * len(src)
    first = next((i for i, v in enumerate(src) if v is not None), None)
    if first is None or len(src) - first < n: return out
    prev = sum(src[first:first + n]) / n; out[first + n - 1] = prev; a = 2.0 / (n + 1)
    for i in range(first + n, len(src)):
        prev = prev + a * (src[i] - prev); out[i] = prev
    return out


def bucket_span(d, tfd):
    """(first day, last day) of the chart bar containing calendar day d: days are bucketed inside each
    calendar year, restarting on 1 January (fetch.py), so a year's last bar can be short."""
    j1 = dt.date(d.year, 1, 1); k = (d - j1).days // tfd
    a = j1 + dt.timedelta(days=k * tfd); b = min(a + dt.timedelta(days=tfd - 1), dt.date(d.year, 12, 31))
    return a, b


def bucket_of(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


def tagstr(bk, dis, strong, prime):
    return ' + '.join([bk] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))


class Chart:
    def __init__(self, S, a, tf):
        self.a, self.tf, self.tfd = a, tf, int(tf[:-1])
        self.b = Candles(f'{S}/data/{a}_{tf}.csv')
        self.ct = wilder_rsi(self.b.cf); self.k = stoch_k(self.ct); self.em = ema_seeded(self.ct)
        self.pivots = self._pivots()

    def _pivots(self):
        ct, k, n = self.ct, self.k, self.b.n
        out = []; prev = None
        for ti in range(3, n - 3):
            v = ct[ti]
            if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)): continue
            if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)): continue
            if k[ti] is None: continue
            dis = False
            if prev is not None:
                dc = v - prev['ct']; dk = k[ti] - prev['k']
                dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
            p = dict(ti=ti, ei=ti + 3, ct=v, k=k[ti], bk=bucket_of(v), dis=dis, strong=dis and v < 50,
                     prime=20 <= k[ti] < 50, tdate=self.b.date[ti], prevct=None if prev is None else prev['ct'],
                     prevk=None if prev is None else prev['k'])
            out.append(p); prev = p
        return out


class World:
    def __init__(self, S, now):
        self.S = S; self.now = now; self.today = now.date()
        sys.path.insert(0, S)
        import regimes as R
        self.gate = R.rsi_regime(f'{S}/data/BTC_2D.csv', 8, 13, 60, 41)
        self.day = {a: Candles(f'{S}/data/{a}_1D.csv') for a in ASSETS}
        self.ch = {(a, tf): Chart(S, a, tf) for a in ASSETS for tf in TFS}
        self.sig = {}
        for key, c in self.ch.items():
            a, tf = key; lst = []
            for p in c.pivots:
                if not self.gate(p['tdate']): continue
                conf_open = c.b.date[p['ei']]
                d0 = bucket_span(conf_open, c.tfd)[1]         # the confirmation bar's CLOSE date
                if d0 >= self.today: continue                 # confirmation bar still open: not a signal yet
                s = dict(p, a=a, tf=tf, chart=f'{a} {tf}', d0=d0, entry=c.b.c[p['ei']], tlow=c.b.l[p['ti']],
                         tags=tagstr(p['bk'], p['dis'], p['strong'], p['prime']))
                s['m'] = self.measure(a, d0, s['entry'])
                lst.append(s)
            self.sig[key] = lst
        self._vol = {}

    # ---- daily forward window: the 60 calendar days after the entry date
    def window(self, a, d0, upto=60, closed_only=True):
        D = self.day[a]; i = D.pos.get(d0)
        if i is None: return None
        ks = []
        for k in range(i + 1, D.n):
            n = (D.date[k] - d0).days
            if n > upto: break
            if closed_only and D.date[k] >= self.today: break   # a daily bar counts only once it has closed (UTC)
            ks.append(k)
        return ks

    def measure(self, a, d0, e):
        D = self.day[a]; ks = self.window(a, d0)
        if not ks or (D.date[ks[-1]] - d0).days != 60: return None      # the 60th day's bar has not closed
        hi = max(D.h[k] for k in ks); lo = min(D.l[k] for k in ks)
        kp = next(k for k in ks if D.h[k] == hi); kl = next(k for k in ks if D.l[k] == lo)
        pre = min(D.l[k] for k in ks if k <= kp)                         # low before high within the high's day
        pc = lambda x: (x / e - 1) * 100
        t10 = next(((D.date[k] - d0).days for k in ks if D.h[k] >= e * Fr(110, 100)), None)
        t20 = next(((D.date[k] - d0).days for k in ks if D.h[k] >= e * Fr(120, 100)), None)
        return dict(up=pc(hi), dd=pc(lo), ddpk=pc(pre), ret=pc(D.c[ks[-1]]), dpk=(D.date[kp] - d0).days,
                    ddday=(D.date[kl] - d0).days, r10=hi >= e * Fr(110, 100), r15=hi >= e * Fr(115, 100),
                    r20=hi >= e * Fr(120, 100), r30=hi >= e * Fr(130, 100), t30=lo <= e * Fr(70, 100),
                    liq=lo <= e * (1 - LIQ), t10=t10, t20=t20, ks=ks)

    def hl(self, a, d0):
        D = self.day[a]; ks = self.window(a, d0)
        return [(D.h[k], D.l[k]) for k in ks]

    # ---- 365-day daily volatility at entry / the asset's 2016-21 median of it
    def vol_ratio(self, a, d0):
        import math, statistics as st
        if a not in self._vol:
            D = self.day[a]; lr = [None] + [math.log(D.cf[i] / D.cf[i - 1]) for i in range(1, D.n)]
            v = {}
            for i in range(365, D.n):
                w = lr[i - 364:i + 1]; mu = sum(w) / 365
                v[D.date[i]] = math.sqrt(sum((x - mu) ** 2 for x in w) / 365)
            med = st.median([x for d, x in v.items() if d.year <= 2021])
            self._vol[a] = (v, med)
        v, med = self._vol[a]
        return None if d0 not in v else v[d0] / med

    def scaled20(self, s):
        r = self.vol_ratio(s['a'], s['d0'])
        if r is None or s['m'] is None: return None
        return float(s['m']['up']) >= 20 * r

    # ---- ladder rows (low before high within a day)
    def from_entry(self, G):
        ok = liq = 0
        for s in G:
            e = s['entry']
            for h, l in self.hl(s['a'], s['d0']):
                if l <= e * (1 - LIQ): liq += 1; break
                if h >= e * Fr(110, 100): ok += 1; break
        return ok, liq, len(G)

    def falls_first(self, G, th):
        hit = ok = liq = 0
        for s in G:
            e = s['entry']; w = self.hl(s['a'], s['d0'])
            for j, (h, l) in enumerate(w):
                if l <= e * Fr(100 - th, 100):
                    hit += 1
                    for hh, ll in w[j:]:
                        if ll <= e * (1 - LIQ): liq += 1; break
                        if hh >= e * Fr(110, 100): ok += 1; break
                    break
                if h >= e * Fr(110, 100): break
        return hit, ok, liq


def now_of(S):
    f = json.load(open(f'{S}/feed/ctzb_feed.json'))
    return dt.datetime.fromisoformat(f['generated_at'].replace('Z', '+00:00')), f


class Checks:
    def __init__(self, state):
        self.state = state; self.rows = []

    def add(self, loc, label, shown, mine, cause=''):
        ok = norm(shown) == norm(mine)
        self.rows.append([self.state, loc, label, disp(shown), disp(mine), 'yes' if ok else 'NO', '' if ok else cause])
        return ok


def disp(v):
    if v is None: return ''
    if isinstance(v, Fr): return str(float(v)) if v.denominator != 1 else str(v.numerator)
    if isinstance(v, bool): return 'true' if v else 'false'
    return str(v)


def norm(v):
    if v is None or v == '': return ''
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, Fr): return v
    if isinstance(v, int): return Fr(v)
    if isinstance(v, float): return Fr(Decimal(repr(v)))
    if isinstance(v, str):
        try: return Fr(Decimal(v.strip()))
        except Exception: return v.strip()
    return v
