"""Audit #10 -- independent recomputation library. Written from the definitions only.

Prices are read as Decimal from the CSV text, so every threshold test (rose 10%, fell 25.3%, fell 30%,
fell X% first) is exact. Oscillators (RSI, stoch) are float, as they are only used to find pivots.
"""
import csv, datetime as dt, math, os, sys, json
from decimal import Decimal as Dec, getcontext, ROUND_HALF_UP
getcontext().prec = 80

ONE = Dec(1); HUND = Dec(100)
DAY = dt.timedelta(days=1)


def rhalf(x, nd=0):
    """Half away from zero, on the exact value given (Decimal or float's exact binary value)."""
    if not isinstance(x, Dec):
        x = Dec(float(x))
    q = Dec(1).scaleb(-nd)
    return x.quantize(q, rounding=ROUND_HALF_UP)


def r6(x):
    return rhalf(x, 6)


def udate(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def load(path, clamp=True):
    """Bars: list of dicts with date (bar open, UTC), o h l c as Decimal. Flash-print clamp: a low below
    half the body's low -> body low; a high above twice the body's high -> body high."""
    out, clamps = [], []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            o, h, l, c = (Dec(r[k]) for k in ('open', 'high', 'low', 'close'))
            d = udate(r['time'])
            if clamp:
                blo, bhi = min(o, c), max(o, c)
                if l < blo / 2:
                    clamps.append((d, 'low', l, blo)); l = blo
                if h > bhi * 2:
                    clamps.append((d, 'high', h, bhi)); h = bhi
            out.append(dict(date=d, t=int(r['time']), o=o, h=h, l=l, c=c))
    return out, clamps


def bucket_key(d, tf):
    return (d.year, (d - dt.date(d.year, 1, 1)).days // tf)


def bucket_span(d_open, tf):
    """All calendar days of the tf-day bucket that opens on d_open (restarts on 1 January)."""
    y, k = bucket_key(d_open, tf)
    start = dt.date(y, 1, 1) + dt.timedelta(days=k * tf)
    end = min(start + dt.timedelta(days=tf - 1), dt.date(y, 12, 31))
    return start, end


def rebucket(daily, tf):
    g = {}
    for b in daily:
        g.setdefault(bucket_key(b['date'], tf), []).append(b)
    out = []
    for k in sorted(g):
        bs = g[k]
        out.append(dict(date=bs[0]['date'], o=bs[0]['o'], h=max(x['h'] for x in bs), l=min(x['l'] for x in bs), c=bs[-1]['c']))
    return out


# ---------------------------------------------------------------- oscillators (own code)
def wilder_rsi(cl, n=14):
    out = [None] * len(cl)
    if len(cl) <= n:
        return out
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = cl[i] - cl[i - 1]
        if ch > 0: up += ch
        else: dn -= ch
    au, ad = up / n, dn / n
    out[n] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    for i in range(n + 1, len(cl)):
        ch = cl[i] - cl[i - 1]
        au = (au * (n - 1) + (ch if ch > 0 else 0.0)) / n
        ad = (ad * (n - 1) + (-ch if ch < 0 else 0.0)) / n
        out[i] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    return out


def rsi_state(cl, n=14):
    """Wilder averages after the last close (for solving the kill close)."""
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = cl[i] - cl[i - 1]
        if ch > 0: up += ch
        else: dn -= ch
    au, ad = up / n, dn / n
    for i in range(n + 1, len(cl)):
        ch = cl[i] - cl[i - 1]
        au = (au * (n - 1) + (ch if ch > 0 else 0.0)) / n
        ad = (ad * (n - 1) + (-ch if ch < 0 else 0.0)) / n
    return au, ad


def stoch_k(ct, n=14, sm=3):
    st = [None] * len(ct)
    for i in range(len(ct)):
        if i < n - 1: continue
        w = ct[i - n + 1:i + 1]
        if any(x is None for x in w): continue
        hi, lo = max(w), min(w)
        st[i] = 0.0 if hi == lo else 100.0 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    run = []
    for i, v in enumerate(st):
        if v is None:
            run = []; continue
        run.append(v)
        if len(run) >= sm:
            k[i] = sum(run[-sm:]) / sm
    return k


EPS = 1e-9


def pivots(bars):
    """Every RSI pivot low (3 bars each side, strictly lower), with tags; the previous-trough chain runs
    over all pivots (gated or not)."""
    cl = [float(b['c']) for b in bars]
    ct = wilder_rsi(cl); K = stoch_k(ct)
    out = []; pc = pk = None
    for ti in range(3, len(bars) - 3):
        v = ct[ti]
        w = ct[ti - 3:ti + 4]
        if v is None or any(x is None for x in w): continue
        if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)): continue
        k = K[ti]
        if k is None: continue
        dis = False
        if pc is not None:
            dc, dk = v - pc, k - pk
            dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
        out.append(dict(ti=ti, ei=ti + 3, ct=v, k=k, dis=dis, strong=dis and v < 50, prime=20 <= k < 50,
                        bk='A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'))
        pc, pk = v, k
    return out, ct, K


def tagstr(p):
    return ' + '.join([p['bk']] + (['filled diamond'] if p['strong'] else ['hollow diamond'] if p['dis'] else []) + (['prime dot'] if p['prime'] else []))


# ---------------------------------------------------------------- forward measures on daily candles
class Daily:
    def __init__(self, bars, today):
        self.b = bars; self.pos = {b['date']: i for i, b in enumerate(bars)}; self.today = today

    def window(self, d0, H=60, closed_only=True):
        """Daily bars on calendar days d0+1 .. d0+H, closed only (date < today)."""
        i = self.pos[d0]; out = []
        for k in range(i + 1, len(self.b)):
            b = self.b[k]
            if (b['date'] - d0).days > H: break
            if closed_only and b['date'] >= self.today: break
            out.append(b)
        return out

    def complete(self, d0, H=60):
        end = d0 + dt.timedelta(days=H)
        return end in self.pos and end < self.today

    def measure(self, d0, e, H=60):
        if d0 not in self.pos or not self.complete(d0, H): return None
        w = self.window(d0, H)
        gaps = H - len(w)
        hs = [b['h'] for b in w]; ls = [b['l'] for b in w]
        mx = max(hs); kp = hs.index(mx); mn = min(ls); kl = ls.index(mn)
        pre = min(ls[:kp + 1])
        pc = lambda p: (p / e - ONE) * HUND
        m = dict(up=pc(mx), dd=pc(mn), ddpk=pc(pre), ret=pc(w[-1]['c']),
                 dpk=(w[kp]['date'] - d0).days, ddday=(w[kl]['date'] - d0).days, gaps=gaps)
        m['r10'] = mx >= e * Dec('1.10'); m['r15'] = mx >= e * Dec('1.15'); m['r20'] = mx >= e * Dec('1.20')
        m['r30'] = mx >= e * Dec('1.30')
        m['t30'] = mn <= e * Dec('0.70')
        m['liq'] = mn <= e * (ONE - Dec('0.253'))
        m['surv10'] = m['r10'] and not m['liq']
        m['d10'] = next(((b['date'] - d0).days for b in w if b['h'] >= e * Dec('1.10')), None)
        m['d20'] = next(((b['date'] - d0).days for b in w if b['h'] >= e * Dec('1.20')), None)
        # from entry: rose 10% before falling 25.3% (low checked first within a day)
        fe = None
        for b in w:
            if b['l'] <= e * (ONE - Dec('0.253')): fe = 'liq'; break
            if b['h'] >= e * Dec('1.10'): fe = 'ok'; break
        m['fe'] = fe
        lad = {}
        for th in (5, 10, 15, 20):
            res = None
            for j, b in enumerate(w):
                if b['l'] <= e * (ONE - Dec(th) / HUND):
                    res = 'none'
                    for bb in w[j:]:
                        if bb['l'] <= e * (ONE - Dec('0.253')): res = 'liq'; break
                        if bb['h'] >= e * Dec('1.10'): res = 'ok'; break
                    break
                if b['h'] >= e * Dec('1.10'): break
            lad[th] = res     # None: never fell th% first; 'ok'/'liq'/'none' if it did
        m['lad'] = lad
        return m


def median(xs):
    s = sorted(xs); n = len(s)
    if not n: return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quant(xs, f):
    s = sorted(xs); k = (len(s) - 1) * Dec(str(f)); lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def share(k, n):
    return Dec(100) * k / n
