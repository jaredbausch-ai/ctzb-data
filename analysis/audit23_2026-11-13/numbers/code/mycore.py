"""Independent recomputation of every member-facing figure (audit 23, numbers on real data).
Own code throughout; regimes.py is imported for the gate only.
Prices are compared in exact decimal (from the CSV text); percentages are computed exactly
(Fraction / Decimal) and rounded half away from zero once, on the stored value's binary float."""
import csv, datetime as dt, os, sys, math, importlib.util
from decimal import Decimal, ROUND_HALF_UP, getcontext
from fractions import Fraction

getcontext().prec = 50
D = Decimal
EPS = 1e-9
ONE_DAY = dt.timedelta(days=1)
GRADED = ('1D', '2D', '3D', '5D')
TFS = ('1D', '2D', '3D', '5D', '8D')
ASSETS = ('ETH', 'BTC')
SPLIT = dt.date(2022, 1, 1)
EX_D0 = dt.date(2024, 9, 22)
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before',
         'FUND': 'funding at or above its 90-day median', 'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising',
         'FASTCT': 'CT recovering fast from the low'}
UNPLAIN = {v: k for k, v in PLAIN.items()}


# ---------------------------------------------------------------- rounding (my own)
def rnd(x, nd=0):
    """half away from zero on the float's exact binary value"""
    if x is None:
        return None
    q = D(1) if nd == 0 else D(1).scaleb(-nd)
    v = D(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(v) if nd == 0 else float(v)


def rnd_exact(x, nd=0):
    """half away from zero on an exact Fraction/Decimal value"""
    if isinstance(x, Fraction):
        x = D(x.numerator) / D(x.denominator)
    q = D(1) if nd == 0 else D(1).scaleb(-nd)
    v = D(x).quantize(q, rounding=ROUND_HALF_UP)
    return int(v) if nd == 0 else float(v)


def share(k, n):
    """whole-percent share, rounded once from the ratio's float"""
    return None if not n else rnd(float(Fraction(100 * k, n)), 0)


def share6(k, n):
    return None if not n else rnd(100 * k / n, 6)


def med(xs):
    s = sorted(xs)
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


# ---------------------------------------------------------------- candles
def udate(t):
    return dt.datetime.fromtimestamp(int(float(t)), dt.timezone.utc).date()


def load(path):
    """bars: list of dicts d (open date), o h l c floats, H L C Decimals (clamped as documented)."""
    out = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            o, h, l, c = (float(r[k]) for k in ('open', 'high', 'low', 'close'))
            Hs, Ls = r['high'], r['low']
            lob, hib = min(o, c), max(o, c)
            if lob > 0 and l < 0.5 * lob:      # flash-print clamp, CONTEXT "Traps"
                l = lob; Ls = r['open'] if o <= c else r['close']
            if hib > 0 and h > hib / 0.5:
                h = hib; Hs = r['open'] if o >= c else r['close']
            out.append(dict(t=int(float(r['time'])), d=udate(r['time']), o=o, h=h, l=l, c=c,
                            H=D(Hs), L=D(Ls), C=D(r['close'])))
    return out


def bar_start(d, tf):
    if tf == 1:
        return d
    j1 = dt.date(d.year, 1, 1)
    return j1 + dt.timedelta(days=((d - j1).days // tf) * tf)


def next_open(d, tf):
    """open date of the bar after the one opening on d (bars bucketed inside each calendar year)"""
    return min(d + dt.timedelta(days=tf), dt.date(d.year + 1, 1, 1))


# ---------------------------------------------------------------- indicators (my own)
def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1:
        return out
    g = sum(max(c[i] - c[i - 1], 0.0) for i in range(1, n + 1)) / n
    l = sum(max(c[i - 1] - c[i], 0.0) for i in range(1, n + 1)) / n
    out[n] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        g = (g * (n - 1) + max(ch, 0.0)) / n
        l = (l * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return out


def stochk(ct, n=14, sm=3):
    st = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0:
            continue
        w = ct[i - n + 1:i + 1]
        if any(x is None for x in w):
            continue
        hi, lo = max(w), min(w)
        st[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    run = []
    for i, v in enumerate(st):
        if v is None:
            run = []; continue
        run.append(v)
        if len(run) > sm:
            run.pop(0)
        if len(run) == sm:
            k[i] = sum(run) / sm
    return k


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


def tagtext(bk, dis, strong, prime):
    return ' + '.join([bk] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))


def zser(ct):
    out, z = [], None
    for v in ct:
        if v is None:
            out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        out.append(z)
    return out


class Chart:
    def __init__(self, sdir, a, tf, gate):
        self.a, self.tf, self.tfd = a, tf, int(tf[:-1])
        self.bars = load(os.path.join(sdir, 'data', f'{a}_{tf}.csv'))
        self.dates = [b['d'] for b in self.bars]
        c = [b['c'] for b in self.bars]
        self.ct = rsi(c)
        self.k = stochk(self.ct)
        n = len(c)
        piv = []
        for ti in range(3, n - 3):
            w = self.ct[ti - 3:ti + 4]
            if any(x is None for x in w) or self.k[ti] is None:
                continue
            v = self.ct[ti]
            if all(self.ct[j] > v for j in range(ti - 3, ti)) and all(self.ct[j] > v for j in range(ti + 1, ti + 4)):
                piv.append(ti)
        self.pivots = piv
        sig = []
        prev = None
        for ti in piv:
            v, kk = self.ct[ti], self.k[ti]
            dis = False
            if prev is not None:
                dct, dk = v - self.ct[prev], kk - self.k[prev]
                dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
            prev = ti
            td = self.dates[ti]
            if not gate(td):
                continue
            ei = ti + 3
            d0 = self.dates[ei + 1] - ONE_DAY if ei + 1 < n else None
            sig.append(dict(a=a, tf=tf, ch=f'{a} {tf}', ti=ti, ei=ei, tdate=td, cdate=self.dates[ei], d0=d0,
                            e=self.bars[ei]['c'], E=self.bars[ei]['C'], ct=v, kk=kk, bk=bucket(v), dis=dis,
                            strong=dis and v < 50, prime=20 <= kk < 50,
                            tlow=self.bars[ti]['l']))
        for s in sig:
            s['tags'] = tagtext(s['bk'], s['dis'], s['strong'], s['prime'])
        self.sig = sig
        self.zm = zser(self.ct)

    def forming(self):
        """the pivot low still waiting on right-hand bars (1-3 right bars so far, none lower)"""
        n = len(self.bars)
        for back in (1, 2, 3):
            ti = n - 1 - back
            if ti - 3 < 0:
                continue
            v = self.ct[ti]
            if v is None:
                continue
            if any(self.ct[j] is None or self.ct[j] <= v for j in range(ti - 3, ti)):
                continue
            if any(self.ct[j] < v for j in range(ti + 1, n)):
                continue
            return ti, 3 - back
        return None


# ---------------------------------------------------------------- daily windows
class Daily:
    def __init__(self, sdir, a):
        self.bars = load(os.path.join(sdir, 'data', f'{a}_1D.csv'))
        self.pos = {b['d']: i for i, b in enumerate(self.bars)}
        cl = [b['c'] for b in self.bars]
        lr = [0.0] + [math.log(cl[i] / cl[i - 1]) for i in range(1, len(cl))]
        import statistics as stt
        self.vol = {}
        for i in range(365, len(cl)):
            self.vol[self.bars[i]['d']] = stt.pstdev(lr[i - 364:i + 1])
        self.volmed = med([v for k, v in self.vol.items() if k.year <= 2021])

    def window(self, d0, today, H=60):
        """bars of days d0+1..d0+H; complete (and day H closed) or None"""
        i = self.pos.get(d0)
        if i is None:
            return None
        w = []
        for k in range(1, H + 1):
            j = self.pos.get(d0 + dt.timedelta(days=k))
            if j is None:
                return None
            w.append(self.bars[j])
        if w[-1]['d'] >= today:
            return None
        return w

    def closed_window(self, d0, today, H=60):
        """the closed bars of days d0+1..d0+H so far"""
        out = []
        for k in range(1, H + 1):
            d = d0 + dt.timedelta(days=k)
            if d >= today:
                break
            j = self.pos.get(d)
            if j is None:
                break
            out.append(self.bars[j])
        return out


def measures(day, s, today):
    """60-day measures from the entry close, daily candles, exact"""
    w = day.window(s['d0'], today)
    if w is None:
        return None
    i0 = day.pos[s['d0']]
    e, E = s['e'], s['E']
    assert day.bars[i0]['C'] == E, (s['ch'], s['d0'], day.bars[i0]['C'], E)
    Hs = [b['H'] for b in w]; Ls = [b['L'] for b in w]
    hmax = max(Hs); kp = Hs.index(hmax)
    lmin = min(Ls); kl = Ls.index(lmin)
    pre = min(Ls[:kp + 1])
    pc = lambda x: (x / E - 1) * 100
    m = dict(up=pc(hmax), dd=pc(lmin), ddpk=pc(pre), ret=pc(w[-1]['C']), dpk=kp + 1, ddday=kl + 1,
             r10=hmax >= E * D('1.10'), r15=hmax >= E * D('1.15'), r20=hmax >= E * D('1.20'),
             r30=hmax >= E * D('1.30'), t30=lmin <= E * D('0.70'), liq=lmin <= E * D('0.747'), w=w)
    m['surv10'] = m['r10'] and not m['liq']
    v = day.vol.get(s['d0'])
    if v is None:
        m['sc'] = None
    else:
        ratio = v / day.volmed
        m['sc'] = float(m['up']) >= 20 * ratio   # float comparison: the ratio is itself a float statistic
    # timing
    m['t10'] = next((k + 1 for k, b in enumerate(w) if b['H'] >= E * D('1.10')), None)
    m['t20'] = next((k + 1 for k, b in enumerate(w) if b['H'] >= E * D('1.20')), None)
    return m


def r6(x):
    """a measure stored to 6 places: the exact value taken as a float, rounded half away from zero"""
    return rnd(float(x), 6)


def disp(x, nd):
    """a displayed figure: the value's float, rounded once half away from zero"""
    return None if x is None else rnd(float(x), nd)


# ---------------------------------------------------------------- funding membership (ETH)
def funding(sdir, a):
    fb_val, mean = {}, {}
    with open(os.path.join(sdir, 'data', 'derivs', f'{a}_funding_daily.csv')) as f:
        for r in csv.DictReader(f):
            d = dt.date.fromisoformat(r['date'])
            v = r.get('funding_oi_weighted') or r.get('funding_mean')
            if v not in ('', None):
                fb_val[d] = float(v)
            if r.get('funding_mean') not in ('', None):
                mean[d] = float(r['funding_mean'])
    return fb_val, mean


def eth_member(fb_val, mean, d0):
    if d0 not in fb_val:
        return False
    back = [fb_val.get(d0 - dt.timedelta(days=k)) for k in range(1, 91)]
    if sum(v is not None for v in back) < 60:
        return False
    w7 = sum((d0 - dt.timedelta(days=k)) in mean for k in range(7))
    w7b = sum((d0 - dt.timedelta(days=14 + k)) in mean for k in range(7))
    return w7 >= 5 and w7b >= 5


# ---------------------------------------------------------------- the gate
def gate_fn(sdir):
    sdir = os.path.abspath(sdir)
    sys.path.insert(0, sdir)
    if 'engine' in sys.modules:
        del sys.modules['engine']
    if 'regimes' in sys.modules:
        del sys.modules['regimes']
    import regimes as R
    g = R.rsi_regime(os.path.join(sdir, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
    sys.path.remove(sdir)
    cache = {}

    def f(d):
        if d not in cache:
            cache[d] = bool(g(d))
        return cache[d]
    return f
