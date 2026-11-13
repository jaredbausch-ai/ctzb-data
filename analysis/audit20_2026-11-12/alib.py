"""Audit #20 -- independent recomputation library. Written from the docs' definitions.
Nothing is imported from the pipeline except regimes.rsi_regime (the gate), as allowed.
Prices are exact rationals (Fraction of the CSV's decimal text); thresholds are tested exactly;
rounding is half away from zero, once, on the exact value.
"""
import csv, json, os, sys, math, datetime as dt, bisect
from fractions import Fraction as Fr
from decimal import Decimal as Dc

ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D'); GRADED = ('1D', '2D', '3D', '5D')
EPS = 1e-9
LIQ = Fr(253, 1000)          # 25.3%
BAR = 70
D = dt.date
SPLIT = D(2022, 1, 1)
EX_DATE = D(2024, 9, 22)
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
RPLAIN = {v: k for k, v in PLAIN.items()}


# ---------------------------------------------------------------- rounding (exact)
def rha(x, nd=0):
    """Round a Fraction half away from zero to nd places; returns Fraction."""
    x = Fr(x); s = 10 ** nd; y = abs(x) * s
    q = (2 * y.numerator + y.denominator) // (2 * y.denominator)
    r = Fr(q, s)
    return -r if x < 0 else r


def fstr(x, nd):
    """Fraction (already rounded) -> plain decimal string with nd places."""
    x = Fr(x); neg = x < 0; y = abs(x) * 10 ** nd
    q = y.numerator // y.denominator
    s = str(q).rjust(nd + 1, '0')
    out = (s[:-nd] + '.' + s[-nd:]) if nd else s
    return ('-' if neg and q != 0 else '') + out


def to_fr(v):
    if v is None or v == '': return None
    if isinstance(v, Fr): return v
    if isinstance(v, bool): return None
    if isinstance(v, int): return Fr(v)
    if isinstance(v, float): return Fr(Dc(repr(v)))
    try: return Fr(Dc(str(v).strip()))
    except Exception: return None


def med(xs):
    s = sorted(xs); n = len(s)
    if not n: return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quant(xs, f):
    s = sorted(xs); k = (len(s) - 1) * Fr(f); lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def share(k, n, nd=0):
    return None if not n else rha(Fr(100 * k, n), nd)


# ---------------------------------------------------------------- candles
class Chart:
    def __init__(self, path):
        self.t = []; self.date = []; self.o = []; self.h = []; self.l = []; self.c = []; self.clamped = []
        with open(path, newline='') as f:
            for r in csv.DictReader(f):
                t = int(float(r['time'])); o, h, l, c = (Fr(Dc(r[k])) for k in ('open', 'high', 'low', 'close'))
                d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
                lo_body, hi_body = min(o, c), max(o, c)
                # documented flash-print clamp: a low below half the bar's body, or a high above twice it
                if lo_body > 0 and l < lo_body / 2: self.clamped.append((d, 'low', l, lo_body)); l = lo_body
                if hi_body > 0 and h > hi_body * 2: self.clamped.append((d, 'high', h, hi_body)); h = hi_body
                self.t.append(t); self.date.append(d); self.o.append(o); self.h.append(h); self.l.append(l); self.c.append(c)
        self.cf = [float(x) for x in self.c]
        self.pos = {d: i for i, d in enumerate(self.date)}
        self.n = len(self.c)


def rsi14(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1: return out
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: g += ch
        else: l -= ch
    ag, al = g / n, l / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        ag = (ag * (n - 1) + (ch if ch > 0 else 0.0)) / n
        al = (al * (n - 1) + (-ch if ch < 0 else 0.0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def stoch_k(ct, n=14, sm=3):
    st = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0: continue
        w = ct[i - n + 1:i + 1]
        if any(x is None for x in w): continue
        hi, lo = max(w), min(w)
        st[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        if i - sm + 1 < 0: continue
        w = st[i - sm + 1:i + 1]
        if any(x is None for x in w): continue
        k[i] = sum(w) / sm
    return k


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


def next_open(d, tf):
    """Open date of the bar after the bar opening on d: bars bucket days within a calendar year, restart 1 Jan."""
    if tf == 1: return d + dt.timedelta(days=1)
    jan1 = D(d.year, 1, 1); k = (d - jan1).days // tf
    n = jan1 + dt.timedelta(days=(k + 1) * tf)
    return min(n, D(d.year + 1, 1, 1))


def pivots(ch):
    """Every confirmed CT pivot low (3 bars either side, strictly lower), gated or not, with tags."""
    ct = rsi14(ch.cf); k = stoch_k(ct); out = []; pct_ = pk = None
    for conf in range(ch.n):
        ti = conf - 3
        if ti - 3 < 0: continue
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)): continue
        if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)): continue
        tk = k[ti]
        if tk is None: continue
        dis = False
        if pct_ is not None:
            dct, dk = v - pct_, tk - pk
            dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
        d0 = (ch.date[conf + 1] - dt.timedelta(days=1)) if conf + 1 < ch.n else None
        out.append(dict(ti=ti, ei=conf, tdate=ch.date[ti], edate=ch.date[conf], d0=d0, ct=v, k=tk, bk=bucket(v), dis=dis,
                        strong=dis and v < 50, prime=20 <= tk < 50, entry=ch.c[conf], tlow=ch.l[ti]))
        pct_, pk = v, tk
    return out, ct, k


def tagstr(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))


# ---------------------------------------------------------------- the world
class World:
    def __init__(self, root, now):
        self.root = root; self.now = now; self.today = now.date()
        self.ch = {(a, tf): Chart(os.path.join(root, 'data', f'{a}_{tf}.csv')) for a in ASSETS for tf in TFS}
        self.day = {a: self.ch[(a, '1D')] for a in ASSETS}
        sys.path.insert(0, root)
        import regimes as R
        cwd = os.getcwd(); os.chdir(root)
        try: self.gate = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        finally: os.chdir(cwd)
        self.piv = {}; self.ct = {}; self.k = {}; self.sig = {}
        for key, ch in self.ch.items():
            p, ct, k = pivots(ch)
            self.piv[key] = p; self.ct[key] = ct; self.k[key] = k
            self.sig[key] = [s for s in p if self.gate(s['tdate'])]
        for (a, tf), lst in self.sig.items():
            for s in lst:
                s['a'] = a; s['tf'] = tf; s['chart'] = f'{a} {tf}'
                s['m'] = self.measure(a, s['d0'], s['entry']) if s['d0'] is not None else None
        self._vol = {}

    # 60 calendar days after the entry date on daily candles; only once day 60's bar has closed
    def window(self, a, d0, upto=60, closed_only=True):
        dy = self.day[a]; i0 = dy.pos.get(d0)
        if i0 is None: return None
        ks = []
        for k in range(i0 + 1, dy.n):
            dd = (dy.date[k] - d0).days
            if dd > upto: break
            if closed_only and dy.date[k] >= self.today: break
            ks.append(k)
        return ks

    def measure(self, a, d0, e):
        dy = self.day[a]
        if d0 not in dy.pos: return None
        end = d0 + dt.timedelta(days=60)
        if end >= self.today or end not in dy.pos: return None        # day 60's bar must exist and have closed
        ks = self.window(a, d0)
        if not ks or dy.date[ks[-1]] != end: return None
        hi = max(dy.h[k] for k in ks); lo = min(dy.l[k] for k in ks)
        kp = next(k for k in ks if dy.h[k] == hi); kl = next(k for k in ks if dy.l[k] == lo)
        pre = min(dy.l[k] for k in ks if k <= kp)
        pc = lambda p: (p / e - 1) * 100
        r10 = hi * 100 >= e * 110; r15 = hi * 100 >= e * 115; r20 = hi * 100 >= e * 120; r30 = hi * 100 >= e * 130
        nofall = lo > e * (1 - LIQ)
        return dict(up=pc(hi), dd=pc(lo), ddpk=pc(pre), ret=pc(dy.c[ks[-1]]), dpk=(dy.date[kp] - d0).days, ddday=(dy.date[kl] - d0).days,
                    r10=r10, r15=r15, r20=r20, r30=r30, t30=lo * 100 <= e * 70, t20=lo * 100 <= e * 80, surv=r10 and nofall, ks=ks)

    def vol_ratio(self, a, d0):
        if a not in self._vol:
            c = self.day[a].cf; dts = self.day[a].date
            lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            vol = {}
            for i in range(365, len(c)):
                w = lr[i - 364:i + 1]; mu = sum(w) / len(w)
                vol[dts[i]] = math.sqrt(sum((x - mu) ** 2 for x in w) / len(w))
            base = sorted(v for d_, v in vol.items() if d_.year <= 2021)
            m = None
            if base:
                n = len(base); m = base[n // 2] if n % 2 else (base[n // 2 - 1] + base[n // 2]) / 2
            self._vol[a] = (vol, m)
        vol, m = self._vol[a]; v = vol.get(d0)
        return None if v is None or m is None else v / m

    def scaled20(self, s):
        r = self.vol_ratio(s['a'], s['d0'])
        return None if r is None else float(s['m']['up']) >= 20 * r

    def days_to(self, s, pct):
        dy = self.day[s['a']]; e = s['entry']
        for k in s['m']['ks']:
            if dy.h[k] * 100 >= e * (100 + pct): return (dy.date[k] - s['d0']).days
        return None

    # ladder / from-entry, low before high within a day, exact prices
    def from_entry(self, G):
        ok = liq = 0
        for s in G:
            dy = self.day[s['a']]; e = s['entry']
            for k in s['m']['ks']:
                if dy.l[k] <= e * (1 - LIQ): liq += 1; break
                if dy.h[k] * 100 >= e * 110: ok += 1; break
        return ok, liq, len(G)

    def ladder(self, G, th):
        hit = ok = liq = 0
        for s in G:
            dy = self.day[s['a']]; e = s['entry']; ks = s['m']['ks']
            for j, k in enumerate(ks):
                if dy.l[k] * 100 <= e * (100 - th):
                    hit += 1
                    for kk in ks[j:]:
                        if dy.l[kk] <= e * (1 - LIQ): liq += 1; break
                        if dy.h[kk] * 100 >= e * 110: ok += 1; break
                    break
                if dy.h[k] * 100 >= e * 110: break
        return hit, ok, liq

    def low_day(self, a, tf, tdate):
        nx = next_open(tdate, int(tf[:-1])); dy = self.day[a]
        cand = [(dy.l[dy.pos[tdate + dt.timedelta(days=i)]], tdate + dt.timedelta(days=i)) for i in range((nx - tdate).days) if tdate + dt.timedelta(days=i) in dy.pos]
        return min(cand)[1] if cand else tdate

    def forming(self, a, tf):
        ch = self.ch[(a, tf)]; ct = self.ct[(a, tf)]; k = self.k[(a, tf)]; n = ch.n; step = int(tf[:-1])
        for back in (1, 2, 3):
            ti = n - 1 - back
            if ti - 3 < 0 or ct[ti] is None: continue
            v = ct[ti]
            if any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)): continue
            if any(ct[j] < v for j in range(ti + 1, n)): continue
            need = 3 - back
            co = ch.date[-1]
            for _ in range(need): co = next_open(co, step)
            d0f = next_open(co, step) - dt.timedelta(days=1)
            prev = [p for p in self.piv[(a, tf)] if p['ti'] < ti]
            kx = k[ti]; dis = False
            if prev and kx is not None:
                dct, dk = v - prev[-1]['ct'], kx - prev[-1]['k']
                dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
            f = dict(a=a, tf=tf, chart=f'{a} {tf}', ti=ti, tdate=ch.date[ti], need=need, d0=d0f, bk=bucket(v), dis=dis, strong=dis and v < 50,
                     prime=kx is not None and 20 <= kx < 50, price=ch.c[-1], ctv=v, kill=None)
            if need in (0, 1):
                base = ch.cf[:-1] if need == 0 else ch.cf
                rs = lambda x: rsi14(base + [x])[-1]
                lo, hi = ch.cf[-1] * 0.5, ch.cf[-1] * 1.5
                for _ in range(200):
                    mid = (lo + hi) / 2
                    if rs(mid) <= v: lo = mid
                    else: hi = mid
                kc = math.floor(lo * 100 + 1e-9) / 100
                # independent cent test: the largest cent price at which CT does NOT stay above the trough
                c0 = round(lo * 100)
                cand = [x for x in range(c0 - 3, c0 + 4) if rs(x / 100) <= v]
                f['kill'] = Fr(max(cand), 100) if cand else Fr(Dc(repr(kc)))
                f['kill_bis'] = kc
            return f
        return None
