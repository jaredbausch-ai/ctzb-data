"""Audit 13 -- independent reimplementation (written from the docs, not imported from the pipeline).
Only regimes.py is imported from the state, for the gate."""
import csv, datetime as dt, math, os, sys, statistics
from decimal import Decimal, ROUND_HALF_UP

D = dt.date
UTC = dt.timezone.utc
TFD = {'1D': 1, '2D': 2, '3D': 3, '5D': 5, '8D': 8}


# ---------------------------------------------------------------- rounding
def rha(x, nd=0):
    """half away from zero on the decimal value given (str or Decimal or float via repr)."""
    if x is None or x == '':
        return None
    if isinstance(x, float):
        d = Decimal(repr(x))
    else:
        d = Decimal(str(x))
    q = Decimal(1).scaleb(-nd)
    r = d.quantize(q, rounding=ROUND_HALF_UP)
    return int(r) if nd == 0 else float(r)


def rha_bin(x, nd=0):
    d = Decimal(float(x))
    q = Decimal(1).scaleb(-nd)
    r = d.quantize(q, rounding=ROUND_HALF_UP)
    return int(r) if nd == 0 else float(r)


def store6(x):
    """a measure as stored: 6 places, half away from zero, from the full-precision float."""
    return rha_bin(x, 6)


def disp(x6, nd):
    """display rounding of a 6-place stored value, on its decimal value."""
    return rha(Decimal(repr(float(x6))), nd)


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2


# ---------------------------------------------------------------- candles
def load(path, clamp=True):
    rows = list(csv.DictReader(open(path)))
    out = dict(date=[], o=[], h=[], l=[], c=[], t=[], rawl=[], rawh=[], clamped=[])
    for r in rows:
        t = int(float(r['time']))
        d0 = dt.datetime.fromtimestamp(t, UTC).date()
        o, h, l, c = (float(r[k]) for k in ('open', 'high', 'low', 'close'))
        out['rawl'].append(l); out['rawh'].append(h)
        if clamp:
            lb, hb = min(o, c), max(o, c)
            if lb > 0 and l < 0.5 * lb:
                out['clamped'].append((d0, 'low', l, lb)); l = lb
            if hb > 0 and h > 2 * hb:
                out['clamped'].append((d0, 'high', h, hb)); h = hb
        out['t'].append(t); out['date'].append(d0)
        out['o'].append(o); out['h'].append(h); out['l'].append(l); out['c'].append(c)
    return out


def bar_span(dates, j, tf):
    """calendar days covered by bar j (open date .. last day)."""
    if j + 1 < len(dates):
        end = dates[j + 1] - dt.timedelta(days=1)
    else:
        # last bar: by the calendar rule
        d = dates[j]
        k = TFD[tf]
        jan1 = D(d.year, 1, 1)
        idx = (d - jan1).days // k
        nxt = jan1 + dt.timedelta(days=(idx + 1) * k)
        if nxt.year != d.year:
            nxt = D(d.year + 1, 1, 1)
        end = nxt - dt.timedelta(days=1)
    return dates[j], end


def next_open(d, tf):
    k = TFD[tf]
    jan1 = D(d.year, 1, 1)
    idx = (d - jan1).days // k
    nxt = jan1 + dt.timedelta(days=(idx + 1) * k)
    if nxt.year != d.year:
        nxt = D(d.year + 1, 1, 1)
    return nxt


# ---------------------------------------------------------------- indicator
def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: up += ch
        else: dn -= ch
    au, ad = up / n, dn / n
    def val(au, ad):
        return 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    out[n] = val(au, ad)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        au = (au * (n - 1) + (ch if ch > 0 else 0.0)) / n
        ad = (ad * (n - 1) + (-ch if ch < 0 else 0.0)) / n
        out[i] = val(au, ad)
    return out


def rsi_state(c, n=14):
    """(avg up, avg down) after the last close, to extend by one bar."""
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: up += ch
        else: dn -= ch
    au, ad = up / n, dn / n
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        au = (au * (n - 1) + (ch if ch > 0 else 0.0)) / n
        ad = (ad * (n - 1) + (-ch if ch < 0 else 0.0)) / n
    return au, ad


def stochK(ct, n=14, sm=3):
    st = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0: continue
        w = ct[i - n + 1:i + 1]
        if any(x is None for x in w): continue
        hi, lo = max(w), min(w)
        st[i] = 0.0 if hi == lo else 100.0 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        if i - sm + 1 < 0: continue
        w = st[i - sm + 1:i + 1]
        if any(x is None for x in w): continue
        k[i] = sum(w) / sm
    return k


EPS = 1e-9


def pivots(b):
    """every pivot low on CT with 3 bars each side, strictly lower; K known at the trough."""
    ct = rsi(b['c'])
    K = stochK(ct)
    n = len(ct)
    out = []
    for ti in range(3, n - 3):
        v = ct[ti]
        if v is None: continue
        nb = ct[ti - 3:ti] + ct[ti + 1:ti + 4]
        if any(x is None for x in nb): continue
        if all(x > v for x in nb) and K[ti] is not None:
            out.append(dict(ti=ti, ct=v, k=K[ti]))
    return out, ct, K


def tags_for(pv, prev):
    v, k = pv['ct'], pv['k']
    bk = 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'
    dis = False
    if prev is not None:
        dct, dk = v - prev['ct'], k - prev['k']
        dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
    strong = dis and v < 50
    prime = 20 <= k < 50
    return bk, dis, strong, prime


def tagstr(bk, dis, strong, prime):
    return ' + '.join([bk] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))


def signals(b, tf, gate):
    """gated signals, entry = close of ti+3, dated by the confirmation bar's last day.
    The diamond chain runs over every pivot (gated or not)."""
    pv, ct, K = pivots(b)
    out = []
    prev = None
    for p in pv:
        bk, dis, strong, prime = tags_for(p, prev)
        prev = p
        ti = p['ti']; ei = ti + 3
        tdate = b['date'][ti]
        if not gate(tdate):
            continue
        if ei >= len(b['c']) - 1:
            continue          # confirmation bar is the open bar: not confirmed
        s, e = bar_span(b['date'], ei, tf)
        out.append(dict(ti=ti, ei=ei, tdate=tdate, d0=e, entry=b['c'][ei], bk=bk, dis=dis, strong=strong,
                        prime=prime, ct=p['ct'], k=p['k'], tags=tagstr(bk, dis, strong, prime)))
    return out, pv, ct, K


# ---------------------------------------------------------------- daily windows
class Daily:
    def __init__(self, path):
        self.b = load(path)
        self.pos = {d: i for i, d in enumerate(self.b['date'])}
        self.dates = self.b['date']

    def window(self, d0, H=60, closed_before=None):
        """indices of daily bars d0 < date <= d0+H (and date < closed_before if given)."""
        i0 = self.pos.get(d0)
        if i0 is None:
            return None
        ks = []
        for k in range(i0 + 1, len(self.dates)):
            dd = (self.dates[k] - d0).days
            if dd > H: break
            if closed_before is not None and self.dates[k] >= closed_before: break
            ks.append(k)
        return ks


def measure(day, d0, c0, now_date):
    """60-day measures if day 60's daily bar has closed (closes at the start of the next UTC day)."""
    ks = day.window(d0, 60)
    if ks is None or not ks:
        return None
    end = d0 + dt.timedelta(days=60)
    if day.dates[ks[-1]] != end:
        return None
    if not (end + dt.timedelta(days=1) <= now_date):   # bar of `end` closes at end+1 00:00 UTC
        return None
    # contiguous?
    gaps = [k for k in ks if (day.dates[k] - d0).days != ks.index(k) + 1]
    H = day.b['h']; L = day.b['l']; C = day.b['c']
    hi = max(H[k] for k in ks); lo = min(L[k] for k in ks)
    kp = next(k for k in ks if H[k] == hi)
    kl = next(k for k in ks if L[k] == lo)
    pre = min(L[k] for k in ks if k <= kp)
    t10 = next(((day.dates[k] - d0).days for k in ks if H[k] >= c0 * 1.10), None)
    t20 = next(((day.dates[k] - d0).days for k in ks if H[k] >= c0 * 1.20), None)
    return dict(up=(hi / c0 - 1) * 100, dd=(lo / c0 - 1) * 100, ddpk=(pre / c0 - 1) * 100,
                ret=(C[ks[-1]] / c0 - 1) * 100, dpk=(day.dates[kp] - d0).days, ddday=(day.dates[kl] - d0).days,
                hi=hi, lo=lo, r10=hi >= c0 * 1.10, r15=hi >= c0 * 1.15, r20=hi >= c0 * 1.20, r30=hi >= c0 * 1.30,
                t30=lo <= c0 * 0.70, surv=(hi >= c0 * 1.10) and (lo > c0 * (1 - 0.253)),
                upabove=hi > c0, p5=hi >= c0 * 1.05, p10=hi >= c0 * 1.10, t10=t10, t20=t20, gaps=gaps,
                hl=[(H[k], L[k]) for k in ks], closes=[C[k] for k in ks], days=[(day.dates[k] - d0).days for k in ks])


def ladder(paths):
    """paths: list of (hl list, c0). Returns from-entry and 5/10/15/20 rows: counts and exact shares."""
    out = {}
    n = ok = liq = 0
    for hl, e in paths:
        n += 1
        for h, l in hl:
            if l <= e * (1 - 0.253): liq += 1; break
            if h >= e * 1.10: ok += 1; break
    out[0] = dict(n=n, ok=ok, liq=liq)
    for th in (5, 10, 15, 20):
        hit = ok = liq = 0
        for hl, e in paths:
            for j, (h, l) in enumerate(hl):
                if l <= e * (1 - th / 100):
                    hit += 1
                    for hh, ll in hl[j:]:
                        if ll <= e * (1 - 0.253): liq += 1; break
                        if hh >= e * 1.10: ok += 1; break
                    break
                if h >= e * 1.10: break
        out[th] = dict(n=hit, ok=ok, liq=liq)
    return out


# ---------------------------------------------------------------- volatility
class Vol:
    def __init__(self, day):
        c = day.b['c']; ds = day.dates
        lr = [None] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
        self.v = {}
        for i in range(365, len(c)):
            w = lr[i - 364:i + 1]
            self.v[ds[i]] = statistics.pstdev(w)
        self.med = statistics.median(v for d0, v in self.v.items() if d0.year <= 2021)

    def ratio(self, d0):
        v = self.v.get(d0)
        return None if v is None else v / self.med
