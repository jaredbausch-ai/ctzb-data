"""Independent audit library (audit12). Own implementation of the CTZB definitions.
Only regimes.py is imported from the pipeline, for the gate."""
import csv, math, os, sys, datetime as dt, statistics as st, json
from decimal import Decimal, ROUND_HALF_UP

D = dt.date
EPS = 1e-9
LIQ = 0.253
SPLIT = D(2022, 1, 1)


def rh(x, nd=0):
    """Half away from zero on the exact binary value."""
    if x is None or x == '':
        return None
    q = Decimal(1) if nd == 0 else Decimal(1).scaleb(-nd)
    d = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if nd == 0 else float(d)


def todate(t):
    return dt.datetime.fromtimestamp(int(t), dt.timezone.utc).date()


def load(path, clamp=True):
    rows = list(csv.DictReader(open(path, newline='')))
    out = dict(t=[], date=[], open=[], high=[], low=[], close=[], clamps=[])
    for r in rows:
        o, h, l, c = float(r['open']), float(r['high']), float(r['low']), float(r['close'])
        d = todate(r['time'])
        if clamp:
            blo, bhi = min(o, c), max(o, c)
            if blo > 0 and l < 0.5 * blo:
                out['clamps'].append((d, 'low', l, blo)); l = blo
            if bhi > 0 and h > 2 * bhi:
                out['clamps'].append((d, 'high', h, bhi)); h = bhi
        out['t'].append(int(r['time'])); out['date'].append(d)
        out['open'].append(o); out['high'].append(h); out['low'].append(l); out['close'].append(c)
    return out


def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1:
        return out
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        g += max(ch, 0.0); l += max(-ch, 0.0)
    ag, al = g / n, l / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        ag = (ag * (n - 1) + max(ch, 0.0)) / n
        al = (al * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def stochK(ct, n=14, sm=3):
    s = [None] * len(ct)
    for i in range(len(ct)):
        w = ct[max(0, i - n + 1):i + 1]
        if len(w) < n or any(x is None for x in w):
            continue
        hi, lo = max(w), min(w)
        s[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        w = s[max(0, i - sm + 1):i + 1]
        if len(w) == sm and all(x is not None for x in w):
            k[i] = sum(w) / sm
    return k


def bar_close_date(tf, open_date):
    """Bucket rule (fetch.py): 1D = same day; 2D+ buckets within the calendar year, restarting 1 Jan."""
    if tf == 1:
        return open_date
    end = open_date + dt.timedelta(days=tf - 1)
    dec31 = D(open_date.year, 12, 31)
    return min(end, dec31)


class Market:
    def __init__(self, root, now):
        self.root = root; self.now = now; self.today = now.date()
        self.c = {}
        sys.path.insert(0, root)
        cwd = os.getcwd(); os.chdir(root)
        import importlib
        R = importlib.import_module('regimes')
        self.gate = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        os.chdir(cwd)
        self.day = {a: self.chart(a, 1) for a in ('ETH', 'BTC')}
        self.pos = {a: {d: i for i, d in enumerate(self.day[a]['date'])} for a in ('ETH', 'BTC')}

    def chart(self, a, tf):
        k = (a, tf)
        if k not in self.c:
            self.c[k] = load(os.path.join(self.root, 'data', f'{a}_{tf}D.csv'))
        return self.c[k]

    def troughs(self, a, tf, gated=True):
        b = self.chart(a, tf); C = b['close']; n = len(C)
        ct = rsi(C); K = stochK(ct)
        out = []; pct = pk = None
        for ti in range(3, n - 3):
            v = ct[ti]
            w = ct[ti - 3:ti + 4]
            if v is None or any(x is None for x in w):
                continue
            if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)):
                continue
            if K[ti] is None:
                continue
            dct = None if pct is None else v - pct
            dk = None if pk is None else K[ti] - pk
            dis = pct is not None and ((dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS))
            ei = ti + 3
            td = b['date'][ti]
            # confirmation bar must have closed: its close date strictly before today (its bar closes at next midnight)
            cd = bar_close_date(tf, b['date'][ei])
            closed = ei + 1 < n and cd < self.today
            nxt_ok = ei + 1 < n and b['date'][ei + 1] - dt.timedelta(days=1) == cd
            on = self.gate(td)
            s = dict(a=a, tf=tf, ch=f'{a} {tf}D', ti=ti, ei=ei, tdate=td, d0=cd, closed=closed, nxt_ok=nxt_ok,
                     ct=v, k=K[ti], bk='A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D',
                     dis=dis, strong=dis and v < 50, prime=20 <= K[ti] < 50, entry=C[ei], gate=on)
            pct, pk = v, K[ti]
            if on or not gated:
                out.append(s)
        return out, ct, K

    def tags(self, s):
        return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))

    def window(self, a, d0, H=60, closed_only=True):
        """daily bar indices for days 1..H after d0 (calendar), and whether complete & closed"""
        P = self.pos[a]; dd = self.day[a]['date']
        i0 = P.get(d0)
        if i0 is None:
            return None, False
        ks = []
        for k in range(i0 + 1, len(dd)):
            if (dd[k] - d0).days > H:
                break
            ks.append(k)
        complete = bool(ks) and (dd[ks[-1]] - d0).days == H and dd[ks[-1]] < self.today
        return ks, complete

    def measure(self, a, d0, e):
        ks, ok = self.window(a, d0)
        if not ok:
            return None
        day = self.day[a]
        hs = [day['high'][k] for k in ks]; ls = [day['low'][k] for k in ks]
        mh = max(hs); jh = hs.index(mh); ml = min(ls); jl = ls.index(ml)
        pre = ls[:jh + 1]
        m = dict(up=(mh / e - 1) * 100, dd=(ml / e - 1) * 100, ddpk=(min(pre) / e - 1) * 100,
                 ret=(day['close'][ks[-1]] / e - 1) * 100, dpk=(day['date'][ks[jh]] - d0).days,
                 ddday=(day['date'][ks[jl]] - d0).days, nbars=len(ks))
        m['r10'] = mh >= e * 1.10; m['r15'] = mh >= e * 1.15; m['r20'] = mh >= e * 1.20; m['r30'] = mh >= e * 1.30
        m['t30'] = ml <= e * 0.70
        m['liq'] = ml <= e * (1 - LIQ)
        m['surv10'] = m['r10'] and not m['liq']
        # first day of +10 / +20
        def first(p):
            for k in ks:
                if day['high'][k] >= e * (1 + p / 100):
                    return (day['date'][k] - d0).days
            return None
        m['d10'] = first(10); m['d20'] = first(20)
        # from entry: rose 10% before ever falling 25.3% (low first within a day)
        fe = None
        for k in ks:
            if day['low'][k] <= e * (1 - LIQ): fe = 'liq'; break
            if day['high'][k] >= e * 1.10: fe = 'ok'; break
        m['fe'] = fe
        lad = {}
        for th in (5, 10, 15, 20):
            res = None
            for j, k in enumerate(ks):
                if day['low'][k] <= e * (1 - th / 100):
                    res = 'none'
                    for k2 in ks[j:]:
                        if day['low'][k2] <= e * (1 - LIQ): res = 'liq'; break
                        if day['high'][k2] >= e * 1.10: res = 'ok'; break
                    break
                if day['high'][k] >= e * 1.10:
                    break
            lad[th] = res     # None = never fell th% before +10%
        m['lad'] = lad
        return m

    # volatility ratio: 365 daily log returns ending at d0, population stdev, / median over dates in 2016-2021
    def volratio(self, a, d0):
        if not hasattr(self, '_vol'):
            self._vol = {}
        if a not in self._vol:
            c = self.day[a]['close']; dd = self.day[a]['date']
            lr = [None] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            vol = {}
            for i in range(365, len(c)):
                vol[dd[i]] = st.pstdev(lr[i - 364:i + 1])
            med = st.median(v for k, v in vol.items() if k.year <= 2021)
            self._vol[a] = (vol, med)
        vol, med = self._vol[a]
        v = vol.get(d0)
        return None if v is None else v / med


def funding_maps(root):
    out = {}
    for a in ('ETH', 'BTC'):
        anyv, meanv = {}, {}
        for r in csv.DictReader(open(os.path.join(root, 'data', 'derivs', f'{a}_funding_daily.csv'))):
            d = D.fromisoformat(r['date'])
            v = r.get('funding_oi_weighted') or r.get('funding_mean')
            if v not in ('', None): anyv[d] = float(v)
            if r.get('funding_mean') not in ('', None): meanv[d] = float(r['funding_mean'])
        out[a] = (anyv, meanv)
    return out


def eth_member(fm, d0):
    anyv, meanv = fm['ETH']
    fund = d0 in anyv and sum(1 for k in range(1, 91) if d0 - dt.timedelta(days=k) in anyv) >= 60
    w7 = sum(1 for k in range(7) if d0 - dt.timedelta(days=k) in meanv)
    w7b = sum(1 for k in range(7) if d0 - dt.timedelta(days=14 + k) in meanv)
    return fund and w7 >= 5 and w7b >= 5


def med(xs):
    return st.median(xs) if xs else None


def q(vals, f):
    s = sorted(vals); k = (len(s) - 1) * f; lo = math.floor(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
