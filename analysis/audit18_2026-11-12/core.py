"""Audit 18 -- independent core. Everything here is written from the docs' definitions.
Only regimes.py (the gate) is imported from the repo, as the brief allows."""
import csv, datetime as dt, json, math, os, sys
from fractions import Fraction as Fr
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

D = dt.date
ASSETS = ('ETH', 'BTC')
TFS = ('1D', '2D', '3D', '5D', '8D')
GRADED = ('1D', '2D', '3D', '5D')
EPS = 1e-9
LIQ = Fr(253, 1000)


def utcdate(ts):
    return (dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(ts))).date()


def rnd(x, nd=0):
    """half away from zero on an exact value (Fraction, int, or float taken at its exact binary value)"""
    if x is None:
        return None
    fx = Fr(x)
    q = Fr(10) ** nd
    v = fx * q
    s = -1 if v < 0 else 1
    n = (abs(v) * 2 + 1) // 2
    r = Fr(s * n, 1) / q
    if nd <= 0:
        return int(r)
    return float(r)


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


class Candles:
    """one chart; float arrays for indicators, exact Fractions for price tests; flash clamp applied"""

    def __init__(self, path):
        self.t, self.date = [], []
        self.o, self.h, self.l, self.c = [], [], [], []
        self.xo, self.xh, self.xl, self.xc = [], [], [], []
        self.clamped = []
        self.raw = []
        with open(path, newline='') as f:
            for r in csv.DictReader(f):
                t = int(r['time'])
                o, h, l, c = (Fr(r[k]) for k in ('open', 'high', 'low', 'close'))
                self.raw.append((t, r['open'], r['high'], r['low'], r['close']))
                lob, hib = min(o, c), max(o, c)
                if lob > 0 and l < lob / 2:
                    self.clamped.append((utcdate(t), 'low', float(l), float(lob))); l = lob
                if hib > 0 and h > hib * 2:
                    self.clamped.append((utcdate(t), 'high', float(h), float(hib))); h = hib
                self.t.append(t); self.date.append(utcdate(t))
                self.xo.append(o); self.xh.append(h); self.xl.append(l); self.xc.append(c)
                self.o.append(float(o)); self.h.append(float(h)); self.l.append(float(l)); self.c.append(float(c))
        self.pos = {d: i for i, d in enumerate(self.date)}
        self.n = len(self.t)


def wilder_rsi(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1:
        return out
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: g += ch
        else: l += -ch
    ag, al = g / n, l / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        up = ch if ch > 0 else 0.0
        dn = -ch if ch < 0 else 0.0
        ag = (ag * (n - 1) + up) / n
        al = (al * (n - 1) + dn) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def rsi_state(c, n=14):
    """avg gain / avg loss after the last bar (for the must-close-above solve)"""
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: g += ch
        else: l += -ch
    ag, al = g / n, l / n
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        ag = (ag * (n - 1) + (ch if ch > 0 else 0.0)) / n
        al = (al * (n - 1) + (-ch if ch < 0 else 0.0)) / n
    return ag, al


def stoch_k(ct, n=14, sm=3):
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
    # running-sum SMA, the way Pine / the engine accumulate it (the float residue matters for the EPS guard)
    s = 0.0; q = []
    for i, v in enumerate(st):
        if v is None:
            q = []; s = 0.0; continue
        q.append(v); s += v
        if len(q) > sm:
            s -= q.pop(0)
        if len(q) == sm:
            k[i] = s / sm
    return k


def bar_next_open(d, tfd):
    """open date of the bar after the one opening on d: bars bucket days within each calendar year"""
    if tfd == 1:
        return d + dt.timedelta(days=1)
    jan1 = D(d.year, 1, 1)
    idx = (d - jan1).days // tfd
    nxt = jan1 + dt.timedelta(days=(idx + 1) * tfd)
    return min(nxt, D(d.year + 1, 1, 1))


def bar_close_date(d, tfd):
    return bar_next_open(d, tfd) - dt.timedelta(days=1)


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


def troughs(ch, tfd, gate, today):
    """every confirmed pivot low on the chart: trough index ti, entry index ei = ti+3, tags.
    A signal exists once the confirmation bar has CLOSED (its close date < today)."""
    ct = wilder_rsi(ch.c); k = stoch_k(ct)
    out = []
    pct_, pk = None, None
    for ei in range(ch.n):
        ti = ei - 3
        if ti - 3 < 0:
            continue
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)):
            continue
        if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)):
            continue
        tk = k[ti]
        if tk is None:
            continue
        dis = False
        if pct_ is not None:
            dc, dk = v - pct_, tk - pk
            dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
        strong = dis and v < 50
        prime = 20 <= tk < 50
        d0 = bar_close_date(ch.date[ei], tfd)
        s = dict(ti=ti, ei=ei, tdate=ch.date[ti], edate=ch.date[ei], d0=d0, ct=v, k=tk, bk=bucket(v), dis=dis, strong=strong,
                 prime=prime, entry=ch.c[ei], xentry=ch.xc[ei], gate=gate(ch.date[ti]), closed=d0 < today)
        s['tags'] = ' + '.join([s['bk']] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))
        out.append(s)
        pct_, pk = v, tk
    return out, ct, k


def window60(day, d0, today):
    """indices of the daily bars on the 60 calendar days after d0; complete = day 60's bar exists and has closed"""
    i0 = day.pos.get(d0)
    if i0 is None:
        return None, False
    ks = []
    for k in range(i0 + 1, day.n):
        if (day.date[k] - d0).days > 60:
            break
        ks.append(k)
    end = d0 + dt.timedelta(days=60)
    complete = bool(ks) and day.date[ks[-1]] == end and end < today
    return ks, complete


def measure(day, d0, xe, today):
    ks, complete = window60(day, d0, today)
    if not complete:
        return None
    hi = max(day.xh[k] for k in ks); lo = min(day.xl[k] for k in ks)
    kp = next(k for k in ks if day.xh[k] == hi); kl = next(k for k in ks if day.xl[k] == lo)
    pre = min(day.xl[k] for k in ks if k <= kp)
    pc = lambda p: (p / xe - 1) * 100
    m = dict(up=pc(hi), dd=pc(lo), ddpk=pc(pre), ret=pc(day.xc[ks[-1]]), dpk=(day.date[kp] - d0).days, ddday=(day.date[kl] - d0).days,
             r10=hi >= xe * Fr(11, 10), r15=hi >= xe * Fr(115, 100), r20=hi >= xe * Fr(12, 10), t30=lo <= xe * Fr(7, 10),
             nofall=not (lo <= xe * (1 - LIQ)), ks=ks)
    m['surv'] = m['r10'] and m['nofall']
    # first day at +10 / +20
    for nm, mult in (('d10', Fr(11, 10)), ('d20', Fr(12, 10))):
        m[nm] = next(((day.date[k] - d0).days for k in ks if day.xh[k] >= xe * mult), None)
    return m


def vol_table(day):
    """365-day daily volatility (population sd of log returns, the day and the 364 before it) and the
    2016-21 median of it"""
    c = day.c
    lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
    vol = {}
    for i in range(365, len(c)):
        w = lr[i - 364:i + 1]
        mu = sum(w) / len(w)
        vol[day.date[i]] = math.sqrt(sum((x - mu) ** 2 for x in w) / len(w))
    med = median([v for d, v in vol.items() if d.year <= 2021])
    return vol, med


def ladder_walk(day, ks, xe, th):
    """th = None: from entry. Returns (hit, ok, liq) booleans. Low before high within a day."""
    liqp = xe * (1 - LIQ); up = xe * Fr(11, 10)
    if th is None:
        for k in ks:
            if day.xl[k] <= liqp: return True, False, True
            if day.xh[k] >= up: return True, True, False
        return True, False, False
    lvl = xe * (1 - Fr(th, 100))
    for j, k in enumerate(ks):
        if day.xl[k] <= lvl:
            for k2 in ks[j:]:
                if day.xl[k2] <= liqp: return True, False, True
                if day.xh[k2] >= up: return True, True, False
            return True, False, False
        if day.xh[k] >= up:
            return False, False, False
    return False, False, False


def load_state(root):
    ch = {(a, tf): Candles(os.path.join(root, 'data', f'{a}_{tf}.csv')) for a in ASSETS for tf in TFS}
    feed = json.load(open(os.path.join(root, 'feed', 'ctzb_feed.json')))
    led = list(csv.DictReader(open(os.path.join(root, 'datasets', 'ledger.csv'))))
    return ch, feed, led


def get_gate(root):
    here = os.getcwd()
    sys.path.insert(0, root)
    import importlib
    for m in ('regimes', 'engine'):
        sys.modules.pop(m, None)
    R = importlib.import_module('regimes')
    g = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
    sys.path.remove(root)
    return g


class Checks:
    def __init__(self, state):
        self.state = state; self.rows = []

    def add(self, loc, label, shown, mine, ok=None, cause=''):
        if ok is None:
            ok = same(shown, mine)
        self.rows.append([self.state, loc, label, '' if shown is None else shown, '' if mine is None else mine, 'ok' if ok else 'DISAGREE', '' if ok else cause])
        return ok

    def summary(self):
        bad = [r for r in self.rows if r[5] != 'ok']
        return len(self.rows), len(bad)


def same(a, b):
    if a is None or a == '':
        return b is None or b == ''
    if b is None or b == '':
        return False
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return str(a) == str(b)
