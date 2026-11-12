"""Audit #4 -- independent recomputation library. Written from the stated definitions only.

Nothing here imports the pipeline except regimes.py (the gate), loaded from the state folder.
Prices are parsed exactly (Fraction of the CSV decimal string); every threshold test and every
percentage is exact; rounding is half away from zero, once, on the exact value.
"""
import csv, datetime as dt, importlib.util, os, sys
from fractions import Fraction as F
from decimal import Decimal, ROUND_HALF_UP

EPS = 1e-9
LIQ = F(253, 1000)          # fell 25.3%
D = dt.date


def rnd(x, nd=0):
    """Half away from zero on the exact rational value."""
    if x is None:
        return None
    if not isinstance(x, F):
        x = F(x)
    s = 1 if x >= 0 else -1
    y = abs(x) * (10 ** nd)
    q = int(y)
    if y - q >= F(1, 2):
        q += 1
    v = s * F(q, 10 ** nd)
    return int(v) if nd == 0 else float(v)


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs); m = n // 2
    return xs[m] if n % 2 else (xs[m - 1] + xs[m]) / 2


def quantile(xs, f):
    """Linear interpolation between order statistics (the usual 'type 7')."""
    s = sorted(xs); k = (len(s) - 1) * F(f); lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def pct(a, e):
    return (a / e - 1) * 100


class Bars:
    """A candle file. t = unix seconds of bar OPEN; date = UTC date of the open."""
    def __init__(self, path, clamp=True):
        self.path = path
        rows = list(csv.DictReader(open(path, newline='', encoding='utf-8-sig')))
        self.t = [int(r['time']) for r in rows]
        self.date = [dt.datetime.fromtimestamp(t, dt.timezone.utc).date() for t in self.t]
        self.o = [F(r['open']) for r in rows]; self.h = [F(r['high']) for r in rows]
        self.l = [F(r['low']) for r in rows]; self.c = [F(r['close']) for r in rows]
        self.clamped = []
        if clamp:   # documented flash-print clamp: low < half the body low, or high > twice the body high
            for i in range(len(rows)):
                blo = min(self.o[i], self.c[i]); bhi = max(self.o[i], self.c[i])
                if blo > 0 and self.l[i] < blo / 2:
                    self.clamped.append((self.date[i], 'low', float(self.l[i]), float(blo))); self.l[i] = blo
                if bhi > 0 and self.h[i] > bhi * 2:
                    self.clamped.append((self.date[i], 'high', float(self.h[i]), float(bhi))); self.h[i] = bhi
        self.cf = [float(x) for x in self.c]
        self.pos = {d: i for i, d in enumerate(self.date)}

    def close_date(self, i):
        """Last calendar day the bar covers (the day it closes on, UTC)."""
        if i + 1 < len(self.date):
            return self.date[i + 1] - dt.timedelta(days=1)
        return None


def rsi(src, n=14):
    out = [None] * len(src)
    if len(src) < n + 1:
        return out
    up = sum(max(src[i] - src[i - 1], 0.0) for i in range(1, n + 1)) / n
    dn = sum(max(src[i - 1] - src[i], 0.0) for i in range(1, n + 1)) / n
    out[n] = 100.0 if dn == 0 else 100.0 - 100.0 / (1.0 + up / dn)
    for i in range(n + 1, len(src)):
        ch = src[i] - src[i - 1]
        up = (up * (n - 1) + max(ch, 0.0)) / n
        dn = (dn * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if dn == 0 else 100.0 - 100.0 / (1.0 + up / dn)
    return out


def stoch(src, n=14):
    out = [None] * len(src)
    for i in range(n - 1, len(src)):
        w = src[i - n + 1:i + 1]
        if any(v is None for v in w):
            continue
        hi, lo = max(w), min(w)
        out[i] = 0.0 if hi == lo else 100.0 * (src[i] - lo) / (hi - lo)
    return out


def sma(src, n):
    out = [None] * len(src)
    for i in range(n - 1, len(src)):
        w = src[i - n + 1:i + 1]
        if any(v is None for v in w):
            continue
        out[i] = sum(w) / n
    return out


def load_gate(state):
    spec = importlib.util.spec_from_file_location('regimes_' + os.path.basename(state), os.path.join(state, 'regimes.py'))
    sys.path.insert(0, state)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    sys.path.pop(0)
    return m.rsi_regime(os.path.join(state, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)


def troughs(b):
    """Every CT pivot low (3 bars each side, strictly lower) with K available.
    Returns list of dict(ti, ei, ct, k) in time order. Uses every bar in the file."""
    ct = rsi(b.cf, 14); k = sma(stoch(ct, 14), 3)
    out = []
    for ti in range(3, len(ct) - 3):
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)):
            continue
        if all(ct[j] > v for j in range(ti - 3, ti)) and all(ct[j] > v for j in range(ti + 1, ti + 4)):
            if k[ti] is None:
                continue
            out.append(dict(ti=ti, ei=ti + 3, ct=v, k=k[ti]))
    return out, ct, k


def signals(b, gate):
    """Gated signals with tags. Diamond: CT and K moved opposite ways vs the previous trough in the
    chain of ALL troughs (gated or not), a change smaller than EPS being no change."""
    tr, ct, k = troughs(b)
    out = []; prev = None
    for t in tr:
        dis = False
        if prev is not None:
            dc = t['ct'] - prev['ct']; dk = t['k'] - prev['k']
            dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
        prev = t
        if not gate(b.date[t['ti']]):
            continue
        v = t['ct']
        bk = 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'
        filled = dis and v < 50
        prime = 20 <= t['k'] < 50
        tags = ' + '.join([bk] + (['filled diamond'] if filled else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))
        d0 = b.close_date(t['ei'])
        out.append(dict(t, bk=bk, dis=dis, filled=filled, prime=prime, tags=tags, tdate=b.date[t['ti']],
                        edate_open=b.date[t['ei']], d0=d0, entry=b.c[t['ei']]))
    return out, ct, k


def closed_by(day_date, now):
    """A daily bar dated day_date (open) has closed at day_date+1 00:00 UTC."""
    return dt.datetime.combine(day_date + dt.timedelta(days=1), dt.time(), dt.timezone.utc) <= now


def window(day, d0, now, H=60):
    """Daily bars for days 1..H after d0 (the entry date). Returns list of (k, idx) or None if
    day H's bar is missing or has not closed."""
    i0 = day.pos.get(d0)
    if i0 is None:
        return None
    w = []
    for k in range(1, H + 1):
        j = day.pos.get(d0 + dt.timedelta(days=k))
        if j is not None:
            w.append((k, j))
    if not w or w[-1][0] != H or not closed_by(day.date[w[-1][1]], now):
        return None
    return w


def measure(day, d0, e, w):
    """Forward measures over the 60-day window w, from entry e (exact)."""
    hs = [(day.h[j], k) for k, j in w]; ls = [(day.l[j], k) for k, j in w]
    mh = max(h for h, _ in hs); kp = next(k for h, k in hs if h == mh)
    ml = min(l for l, _ in ls); kl = next(k for l, k in ls if l == ml)
    pre = [day.l[j] for k, j in w if k <= kp]
    last = day.c[w[-1][1]]
    up = pct(mh, e); dd = pct(ml, e)
    t10 = next((k for k, j in w if day.h[j] >= e * F(11, 10)), None)
    t20 = next((k for k, j in w if day.h[j] >= e * F(12, 10)), None)
    return dict(up=up, dd=dd, ddpk=pct(min(pre), e), ret=pct(last, e), dpk=kp, ddday=kl,
                r10=mh >= e * F(11, 10), r15=mh >= e * F(115, 100), r20=mh >= e * F(12, 10),
                t30=ml <= e * F(7, 10), surv10=(mh >= e * F(11, 10)) and not (ml <= e * (1 - LIQ)),
                t10=t10, t20=t20)


def ladder(day, d0, e, w, th):
    """If it falls th% before rising 10%: returns None (did not fall first), or 'ok'/'liq'/'neither'.
    Same-day ambiguity: on the day of the fall, if the same daily bar also rose 10% the rise is
    counted first (the bar is read as 'rose first'); after the fall, a bar that both hits -25.3%
    and +10% is read as falling first. The ambiguous cases are counted separately."""
    up10 = e * F(11, 10); fall = e * (1 - F(th, 100)); liq = e * (1 - LIQ)
    amb = 0
    for n, (k, j) in enumerate(w):
        if day.h[j] >= up10:
            if day.l[j] <= fall:
                amb += 1
            return None, amb
        if day.l[j] <= fall:
            for k2, j2 in w[n:]:
                hl = day.l[j2] <= liq; hh = day.h[j2] >= up10
                if hl and hh:
                    amb += 1
                if hl:
                    return 'liq', amb
                if hh:
                    return 'ok', amb
            return 'neither', amb
    return None, amb
