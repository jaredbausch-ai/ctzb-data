"""Audit 21 -- independent engine. Own code throughout; only regimes.py is imported (the gate)."""
import csv, datetime as dt, math, os, statistics as st, sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D'); GRADED = ('1D', '2D', '3D', '5D')
EPS = 1e-9
D1 = dt.timedelta(days=1)


def rnd(x, nd=0):
    """half away from zero on the float's binary value"""
    q = Decimal(1).scaleb(-nd)
    d = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    v = float(d)
    if v == 0: v = 0.0
    return int(d) if nd == 0 else v


def rnd_exact(fr, nd=0):
    """half away from zero on an exact Fraction"""
    s = fr * (10 ** nd); neg = s < 0; a = -s if neg else s
    q = (2 * a.numerator + a.denominator) // (2 * a.denominator)
    v = Fraction(-q if neg else q, 10 ** nd)
    return int(v) if nd == 0 else float(v)


class Bars:
    def __init__(self, path):
        self.date = []; self.t = []; self.o = []; self.h = []; self.l = []; self.c = []
        self.hc = []; self.lc = []; self.cc = []   # integer cents
        self.clamped = []
        with open(path, newline='') as f:
            for r in csv.DictReader(f):
                t = int(float(r['time']))
                d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
                o, h, l, c = (float(r[k]) for k in ('open', 'high', 'low', 'close'))
                lob, hib = min(o, c), max(o, c)
                if lob > 0 and l < 0.5 * lob: self.clamped.append((d, 'low', l, lob)); l = lob
                if hib > 0 and h > hib / 0.5: self.clamped.append((d, 'high', h, hib)); h = hib
                self.date.append(d); self.t.append(t); self.o.append(o); self.h.append(h); self.l.append(l); self.c.append(c)
                self.hc.append(round(h * 100)); self.lc.append(round(l * 100)); self.cc.append(round(c * 100))
        self.pos = {d: i for i, d in enumerate(self.date)}
        self.n = len(self.c)


def wilder_rsi(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1: return out
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        up += max(ch, 0.0); dn += max(-ch, 0.0)
    au = up / n; ad = dn / n
    out[n] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        au = (au * (n - 1) + max(ch, 0.0)) / n
        ad = (ad * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def rsi_state(c, n=14):
    """(avg up, avg down) after each bar, for solving the confirmation close"""
    out = [None] * len(c)
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        up += max(ch, 0.0); dn += max(-ch, 0.0)
    au = up / n; ad = dn / n; out[n] = (au, ad)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        au = (au * (n - 1) + max(ch, 0.0)) / n
        ad = (ad * (n - 1) + max(-ch, 0.0)) / n
        out[i] = (au, ad)
    return out


def stoch_k(ct, n=14, sm=3):
    raw = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0: continue
        w = ct[i - n + 1:i + 1]
        if any(x is None for x in w): continue
        hi, lo = max(w), min(w)
        raw[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    # running-sum SMA, the indicator's ta.sma (the EPS guard exists because of its residue)
    out = [None] * len(ct); q = []; s = 0.0
    for i, v in enumerate(raw):
        if v is None: q = []; s = 0.0; continue
        q.append(v); s += v
        if len(q) > sm: s -= q.pop(0)
        if len(q) == sm: out[i] = s / sm
    return out


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


def bar_len(tf): return int(tf.rstrip('D'))


def next_open(d, step):
    """open date of the bar after the one opening on d: bars bucket within the calendar year"""
    if step == 1: return d + D1
    jan1 = dt.date(d.year, 1, 1)
    k = (d - jan1).days // step
    n = jan1 + dt.timedelta(days=(k + 1) * step)
    return min(n, dt.date(d.year + 1, 1, 1))


def tagstr(bk, dis, strong, prime):
    return ' + '.join([bk] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))


class Chart:
    def __init__(self, root, a, tf, gate):
        self.a, self.tf = a, tf
        self.b = Bars(os.path.join(root, 'data', f'{a}_{tf}.csv'))
        b = self.b
        self.ct = wilder_rsi(b.c); self.k = stoch_k(self.ct)
        self.piv = []      # every pivot low (ungated)
        self.sig = []      # gate-on pivots
        pct = pk = None
        n = b.n
        for ti in range(3, n - 3):
            v = self.ct[ti]
            if v is None or any(self.ct[j] is None for j in range(ti - 3, ti + 4)): continue
            if any(self.ct[j] <= v for j in range(ti - 3, ti)) or any(self.ct[j] <= v for j in range(ti + 1, ti + 4)): continue
            kk = self.k[ti]
            if kk is None: continue
            dct = v - pct if pct is not None else None; dk = kk - pk if pct is not None else None
            dis = bool(pct is not None and ((dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)))
            strong = dis and v < 50; prime = 20 <= kk < 50
            ei = ti + 3
            d0 = (b.date[ei + 1] - D1) if ei + 1 < n else None    # the confirmation bar's last day; None while it is open
            s = dict(a=a, tf=tf, chart=f'{a} {tf}', ti=ti, ei=ei, tdate=b.date[ti], edate=b.date[ei], d0=d0, entry=b.c[ei], entry_c=b.cc[ei],
                     ct=v, k=kk, bk=bucket(v), dis=dis, strong=strong, prime=prime, tags=tagstr(bucket(v), dis, strong, prime),
                     gate=gate(b.date[ti]))
            self.piv.append(s)
            if s['gate']: self.sig.append(s)
            pct, pk = v, kk

    def forming(self):
        """the pivot low still waiting on right-hand bars (first of 1, 2, 3 bars back)"""
        b = self.b; n = b.n; ct = self.ct
        for back in (1, 2, 3):
            ti = n - 1 - back
            if ti - 3 < 0: continue
            v = ct[ti]
            if v is None: continue
            if any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)): continue
            if any(ct[j] < v for j in range(ti + 1, n)): continue
            need = 3 - back
            step = bar_len(self.tf)
            co = b.date[-1]
            for _ in range(need): co = next_open(co, step)
            conf = next_open(co, step) - D1
            kk = self.k[ti]
            prev = [x for x in self.piv if x['ti'] < ti]
            dis = False
            if prev and kk is not None:
                dct = v - prev[-1]['ct']; dk = kk - prev[-1]['k']
                dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
            strong = dis and v < 50; prime = kk is not None and 20 <= kk < 50
            return dict(a=self.a, tf=self.tf, chart=f'{self.a} {self.tf}', ti=ti, tdate=b.date[ti], need=need, confirms=conf,
                        bk=bucket(v), tags=tagstr(bucket(v), dis, strong, prime), ct=v, price=b.c[-1], kill=self.kill(ti, need))
        return None

    def kill(self, ti, need):
        """the confirmation-bar close at or below which CT would not stay above the trough CT, floored to the cent.
        need 0: the confirmation bar is the last (open) bar; need 1: it is the next bar (today's bar taken at its
        current close). Solved in closed form from Wilder's averages."""
        b = self.b
        if need == 0: closes = b.c[:-1]
        elif need == 1: closes = b.c[:]
        else: return None
        stt = rsi_state(closes)
        au, ad = stt[-1]; p = closes[-1]; v = self.ct[ti]
        ratio = v / (100 - v)          # RSI <= v  <=>  avgUp/avgDown <= ratio
        # case X >= p: au' = (13 au + (X-p))/14, ad' = 13 ad/14
        x = p + ratio * 13 * ad - 13 * au
        if x < p:
            # case X < p: au' = 13 au/14, ad' = (13 ad + (p-X))/14 ; au'/ad' <= ratio <=> p - X >= 13 au/ratio - 13 ad
            x = p - (13 * au / ratio - 13 * ad)
        # verify by evaluation and nudge to the true float threshold
        def r_at(X):
            return wilder_rsi(closes + [X])[-1]
        lo, hi = x - 0.02, x + 0.02
        if not (r_at(lo) <= v < r_at(hi)):
            lo, hi = p * 0.5, p * 1.5
        for _ in range(80):
            mid = (lo + hi) / 2
            if r_at(mid) <= v: lo = mid
            else: hi = mid
        return math.floor(lo * 100 + 1e-9) / 100


class State:
    def __init__(self, root, today):
        self.root = root; self.today = today
        sys.path.insert(0, root)
        import regimes as R
        self.gate = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        self.ch = {(a, tf): Chart(root, a, tf, self.gate) for a in ASSETS for tf in TFS}
        self.day = {a: self.ch[(a, '1D')].b for a in ASSETS}
        self._vol = {}
        for c in self.ch.values():
            for s in c.piv:
                s['m'] = self.measure(s) if s['d0'] is not None else None

    # ---- the 60 calendar days after the entry date, daily candles
    def window(self, a, d0, upto=60):
        b = self.day[a]; i = b.pos.get(d0)
        if i is None: return []
        out = []
        for k in range(i + 1, b.n):
            dd = (b.date[k] - d0).days
            if dd > upto: break
            out.append(k)
        return out

    def measure(self, s):
        a, d0 = s['a'], s['d0']; b = self.day[a]
        if d0 not in b.pos: return None
        end = d0 + dt.timedelta(days=60)
        if end >= self.today or end not in b.pos: return None       # day 60's daily bar must have closed
        w = self.window(a, d0)
        e = s['entry']; ec = s['entry_c']
        hi = max(b.h[k] for k in w); lo = min(b.l[k] for k in w)
        kp = next(k for k in w if b.h[k] == hi); kl = next(k for k in w if b.l[k] == lo)
        pre = min(b.l[k] for k in w if k <= kp)
        hic = max(b.hc[k] for k in w); loc = min(b.lc[k] for k in w)
        m = dict(up=(hi / e - 1) * 100, dd=(lo / e - 1) * 100, ddpk=(pre / e - 1) * 100, ret=(b.c[w[-1]] / e - 1) * 100,
                 dpk=(b.date[kp] - d0).days, ddday=(b.date[kl] - d0).days,
                 r10=hic * 100 >= ec * 110, r15=hic * 100 >= ec * 115, r20=hic * 100 >= ec * 120, r30=hic * 100 >= ec * 130,
                 t30=loc * 100 <= ec * 70, t20=loc * 100 <= ec * 80, fell253=loc * 1000 <= ec * 747, above=hic > ec)
        m['surv10'] = m['r10'] and not m['fell253']
        r = self.vol_ratio(a, d0)
        m['sc'] = None if r is None else m['up'] >= 20 * r
        m['t10'] = self.days_to(a, d0, ec, 110, w); m['t20d'] = self.days_to(a, d0, ec, 120, w)
        return m

    def days_to(self, a, d0, ec, mult, w):
        b = self.day[a]
        for k in w:
            if b.hc[k] * 100 >= ec * mult: return (b.date[k] - d0).days
        return None

    def vol_ratio(self, a, d0):
        if a not in self._vol:
            b = self.day[a]; c = b.c
            lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            vol = {b.date[i]: st.pstdev(lr[i - 364:i + 1]) for i in range(365, len(c))}
            base = [v for d, v in vol.items() if d.year <= 2021]
            self._vol[a] = (vol, st.median(base) if base else None)
        vol, med = self._vol[a]
        v = vol.get(d0)
        return None if v is None or med is None else v / med

    # ---- ladder pieces (low before high inside a day), exact cents
    def from_entry(self, s):
        """'ok' rose 10% before ever falling 25.3%; 'liq' fell 25.3% first; None neither"""
        b = self.day[s['a']]; ec = s['entry_c']
        for k in self.window(s['a'], s['d0']):
            if b.lc[k] * 1000 <= ec * 747: return 'liq'
            if b.hc[k] * 100 >= ec * 110: return 'ok'
        return None

    def falls_first(self, s, th):
        """None if it never fell th% before rising 10%; else 'ok' / 'liq' / 'none'"""
        b = self.day[s['a']]; ec = s['entry_c']; w = self.window(s['a'], s['d0'])
        for j, k in enumerate(w):
            if b.lc[k] * 100 <= ec * (100 - th):
                for k2 in w[j:]:
                    if b.lc[k2] * 1000 <= ec * 747: return 'liq'
                    if b.hc[k2] * 100 >= ec * 110: return 'ok'
                return 'none'
            if b.hc[k] * 100 >= ec * 110: return None
        return None


def med(xs):
    return st.median(xs) if xs else None


def quant(vals, f):
    s = sorted(vals); k = (len(s) - 1) * f; lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
