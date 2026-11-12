"""Audit 9 -- independent recomputation core. Written from the definitions only; imports regimes.py for the gate."""
import csv, datetime as dt, math, os, sys, statistics as st, importlib.util
from decimal import Decimal, ROUND_HALF_UP

LIQ = 0.253
EPS = 1e-9
TFD = {'1D': 1, '2D': 2, '3D': 3, '5D': 5, '8D': 8}


def rha(x, nd=0):
    """Round half away from zero on the float's exact binary value."""
    q = Decimal(1).scaleb(-nd) if nd else Decimal(1)
    d = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if nd == 0 else float(d)


def r6(x):
    return rha(x, 6)


def udate(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def bucket_end(d, tf):
    n = TFD[tf]
    if n == 1:
        return d
    j1 = dt.date(d.year, 1, 1)
    idx = (d - j1).days // n
    end = j1 + dt.timedelta(days=(idx + 1) * n - 1)
    return min(end, dt.date(d.year, 12, 31))


def load(state, asset, tf, clamp=True):
    rows = list(csv.DictReader(open(os.path.join(state, 'data', f'{asset}_{tf}.csv'))))
    out = []
    for r in rows:
        o, h, l, c = (float(r[k]) for k in ('open', 'high', 'low', 'close'))
        if clamp:
            lb, hb = min(o, c), max(o, c)
            if lb > 0 and l < 0.5 * lb:
                l = lb
            if hb > 0 and h > 2 * hb:
                h = hb
        d = udate(r['time'])
        out.append(dict(t=int(r['time']), date=d, end=bucket_end(d, tf), o=o, h=h, l=l, c=c))
    return out


def rsi(x, n=14):
    out = [None] * len(x)
    if len(x) <= n:
        return out
    up = sum(max(x[i] - x[i - 1], 0) for i in range(1, n + 1)) / n
    dn = sum(max(x[i - 1] - x[i], 0) for i in range(1, n + 1)) / n
    out[n] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    for i in range(n + 1, len(x)):
        ch = x[i] - x[i - 1]
        up = (up * (n - 1) + max(ch, 0)) / n
        dn = (dn * (n - 1) + max(-ch, 0)) / n
        out[i] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    return out


def stochk(ct, n=14, sm=3):
    s = [None] * len(ct)
    for i in range(len(ct)):
        w = ct[max(0, i - n + 1):i + 1]
        if len(w) < n or any(v is None for v in w):
            continue
        hi, lo = max(w), min(w)
        s[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        w = s[max(0, i - sm + 1):i + 1]
        if len(w) == sm and all(v is not None for v in w):
            k[i] = sum(w) / sm
    return k


_GATE = {}


def gate(state):
    if state not in _GATE:
        spec = importlib.util.spec_from_file_location('regimes_' + str(len(_GATE)), os.path.join(state, 'regimes.py'))
        sys.path.insert(0, state)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        sys.path.remove(state)
        _GATE[state] = m.rsi_regime(os.path.join(state, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
    return _GATE[state]


def troughs(bars):
    """Every pivot low of CT RSI (3 strictly higher bars each side), all troughs, with tags."""
    c = [b['c'] for b in bars]
    ct = rsi(c); k = stochk(ct)
    out = []
    prev = None
    for ti in range(3, len(bars) - 3):
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)):
            continue
        if not all(ct[j] > v for j in list(range(ti - 3, ti)) + list(range(ti + 1, ti + 4))):
            continue
        if k[ti] is None:
            continue
        dis = False
        if prev is not None:
            dct, dk = v - prev[0], k[ti] - prev[1]
            dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
        prev = (v, k[ti])
        bk = 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'
        out.append(dict(ti=ti, ei=ti + 3, ct=v, k=k[ti], bk=bk, dis=dis, strong=dis and v < 50, prime=20 <= k[ti] < 50))
    return out, ct, k


def tagstr(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))


class Daily:
    def __init__(self, state, asset, now):
        self.b = load(state, asset, '1D')
        self.pos = {x['date']: i for i, x in enumerate(self.b)}
        self.today = now.date()

    def closed(self, d):
        return d < self.today

    def window(self, d0, H=60, only_closed=True):
        """Daily bars dated d0+1 .. d0+H (only closed ones if only_closed)."""
        out = []
        for k in range(1, H + 1):
            d = d0 + dt.timedelta(days=k)
            i = self.pos.get(d)
            if i is None:
                continue
            if only_closed and not self.closed(d):
                continue
            out.append((k, self.b[i]))
        return out

    def complete(self, d0, H=60):
        d = d0 + dt.timedelta(days=H)
        return d in self.pos and self.closed(d)


def measure(daily, d0, e):
    """60-day measures from the entry close e on d0 (only when day 60's bar has closed)."""
    if not daily.complete(d0):
        return None
    w = daily.window(d0)
    hs = [b['h'] for _, b in w]; ls = [b['l'] for _, b in w]
    mx = max(hs); kp = next(k for k, b in w if b['h'] == mx)
    mn = min(ls); kl = next(k for k, b in w if b['l'] == mn)
    pre = [b['l'] for k, b in w if k <= kp]
    last = [b for k, b in w if k == 60][0]
    return dict(up=(mx / e - 1) * 100, dd=(mn / e - 1) * 100, ddpk=(min(pre) / e - 1) * 100,
                ret=(last['c'] / e - 1) * 100, dpk=kp, ddday=kl,
                r10=mx >= e * 1.10, r15=mx >= e * 1.15, r20=mx >= e * 1.20, t30=mn <= e * 0.70,
                surv10=mx >= e * 1.10 and mn > e * (1 - LIQ),
                d10=next((k for k, b in w if b['h'] >= e * 1.10), None),
                d20=next((k for k, b in w if b['h'] >= e * 1.20), None),
                w=[(b['h'], b['l']) for _, b in w])


def from_entry(G):
    ok = liq = 0
    for s in G:
        for h, l in s['m']['w']:
            if l <= s['e'] * (1 - LIQ): liq += 1; break
            if h >= s['e'] * 1.10: ok += 1; break
    n = len(G)
    return n, ok, liq


def ladder_row(G, th):
    hit = ok = liq = 0
    for s in G:
        w = s['m']['w']; e = s['e']
        for j, (h, l) in enumerate(w):
            if l <= e * (1 - th / 100):
                hit += 1
                for hh, ll in w[j:]:
                    if ll <= e * (1 - LIQ): liq += 1; break
                    if hh >= e * 1.10: ok += 1; break
                break
            if h >= e * 1.10:
                break
    return hit, ok, liq


def q7(vals, f):
    s = sorted(vals); k = (len(s) - 1) * f; lo = int(math.floor(k)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
