"""Audit 11: independent recomputation of every member-facing figure from raw candles.
Own code throughout; regimes.py imported for the gate only."""
import csv, datetime as dt, math, os, sys, json, statistics as st
from decimal import Decimal, ROUND_HALF_UP

D = dt.date
TD = dt.timedelta
ASSETS = ('ETH', 'BTC')
TFS = ('1D', '2D', '3D', '5D', '8D')
GRADED = ('1D', '2D', '3D', '5D')
EPS = 1e-9
LIQ = 0.253


def rh(x, nd=0):
    """Round half away from zero, once, on the float's exact binary value."""
    q = Decimal(1).scaleb(-nd) if nd else Decimal(1)
    v = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(v) if nd == 0 else float(v)


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def lin_q(xs, f):
    s = sorted(xs)
    k = (len(s) - 1) * f
    lo = math.floor(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def bucket_end(op, tf):
    n = int(tf[:-1])
    if n == 1:
        return op
    j1 = D(op.year, 1, 1)
    k = (op - j1).days // n
    return min(j1 + TD(days=(k + 1) * n - 1), D(op.year, 12, 31))


def next_open(op, tf):
    n = int(tf[:-1])
    e = bucket_end(op, tf)
    return e + TD(days=1)


def read_raw(path):
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            d = dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date()
            out.append([d, float(r['open']), float(r['high']), float(r['low']), float(r['close'])])
    return out


def clamp(rows):
    """Documented flash-print clamp: a low under half the bar's body min, or a high over twice its
    body max, is pulled back to the body."""
    out, log = [], []
    for d, o, h, l, c in rows:
        bl, bh = min(o, c), max(o, c)
        if bl > 0 and l < 0.5 * bl:
            log.append((d, 'low', l, bl)); l = bl
        if bh > 0 and h > 2 * bh:
            log.append((d, 'high', h, bh)); h = bh
        out.append([d, o, h, l, c])
    return out, log


def resample(daily_raw, tf):
    n = int(tf[:-1])
    g = {}
    for d, o, h, l, c in daily_raw:
        g.setdefault((d.year, (d - D(d.year, 1, 1)).days // n), []).append((d, o, h, l, c))
    out = []
    for k in sorted(g):
        x = g[k]
        out.append([x[0][0], x[0][1], max(y[2] for y in x), min(y[3] for y in x), x[-1][4]])
    return out


def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        up += max(ch, 0.0); dn += max(-ch, 0.0)
    au, ad = up / n, dn / n
    out[n] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        au = (au * (n - 1) + max(ch, 0.0)) / n
        ad = (ad * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def rsi_state(c, n=14):
    """Wilder averages after the last bar, for solving the next close."""
    up = dn = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        up += max(ch, 0.0); dn += max(-ch, 0.0)
    au, ad = up / n, dn / n
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        au = (au * (n - 1) + max(ch, 0.0)) / n
        ad = (ad * (n - 1) + max(-ch, 0.0)) / n
    return au, ad


def stoch_k(ct, n=14, sm=3):
    st_ = [None] * len(ct)
    for i in range(len(ct)):
        w = ct[i - n + 1:i + 1] if i - n + 1 >= 0 else None
        if not w or any(v is None for v in w):
            continue
        hi, lo = max(w), min(w)
        st_[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        w = st_[i - sm + 1:i + 1] if i - sm + 1 >= 0 else None
        if w and all(v is not None for v in w):
            k[i] = sum(w) / sm
    return k


class State:
    def __init__(self, root, now):
        self.root = root
        self.now = now                     # datetime UTC
        self.today = now.date()            # the daily bar of this date is still open
        sys.path.insert(0, root)
        import regimes as R
        self.gate = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        self.raw = {}
        self.bars = {}
        self.clamps = {}
        for a in ASSETS:
            for tf in TFS:
                r = read_raw(os.path.join(root, 'data', f'{a}_{tf}.csv'))
                self.raw[(a, tf)] = r
                self.bars[(a, tf)], self.clamps[(a, tf)] = clamp(r)
        self.day = {a: self.bars[(a, '1D')] for a in ASSETS}
        self.dpos = {a: {b[0]: i for i, b in enumerate(self.day[a])} for a in ASSETS}
        self._vol = {}
        self._fund = {}
        self.sig = {}
        for a in ASSETS:
            for tf in TFS:
                self.sig[(a, tf)] = self.signals(a, tf)

    # ---------------- checks on the raw files
    def bucket_check(self):
        bad = []
        for a in ASSETS:
            for tf in TFS[1:]:
                mine = resample(self.raw[(a, '1D')], tf)
                theirs = self.raw[(a, tf)]
                if len(mine) != len(theirs):
                    bad.append((a, tf, 'len', len(mine), len(theirs)))
                for x, y in zip(mine, theirs):
                    if x[0] != y[0] or any(abs(x[k] - y[k]) > 1e-9 for k in range(1, 5)):
                        bad.append((a, tf, str(x), str(y)))
        return bad

    # ---------------- signals
    def signals(self, a, tf):
        b = self.bars[(a, tf)]
        C = [x[4] for x in b]
        ct = rsi(C)
        K = stoch_k(ct)
        n = len(b)
        out = []
        pct_ = pk = None
        for ti in range(3, n - 3):
            v = ct[ti]
            w = ct[ti - 3:ti + 4]
            if v is None or any(x is None for x in w):
                continue
            if not all(ct[j] > v for j in range(ti - 3, ti)) or not all(ct[j] > v for j in range(ti + 1, ti + 4)):
                continue
            if K[ti] is None:
                continue
            k = K[ti]
            dis = pct_ is not None and ((v - pct_ > EPS and k - pk < -EPS) or (v - pct_ < -EPS and k - pk > EPS))
            gated = self.gate(b[ti][0])
            pct_, pk = v, k
            if not gated:
                continue
            ei = ti + 3
            d0 = bucket_end(b[ei][0], tf)
            out.append(dict(a=a, tf=tf, ch=f'{a} {tf}', ti=ti, ei=ei, tdate=b[ti][0], eopen=b[ei][0], d0=d0,
                            entry=C[ei], ct=v, k=k, bk='A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D',
                            dis=dis, strong=dis and v < 50, prime=20 <= k < 50, tlow=b[ti][3]))
        return out

    def tags(self, s):
        return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else [])
                          + (['prime dot'] if s['prime'] else []))

    # ---------------- daily windows
    def window(self, a, d0, H=60):
        """Daily bars for calendar days d0+1 .. d0+H that exist, as (k, bar)."""
        p = self.dpos[a]
        out = []
        for k in range(1, H + 1):
            i = p.get(d0 + TD(days=k))
            if i is not None:
                out.append((k, self.day[a][i]))
        return out

    def complete(self, a, d0, H=60):
        """60th day's daily bar exists and has closed."""
        dd = d0 + TD(days=H)
        return dd in self.dpos[a] and dd < self.today

    def measure(self, a, d0, e):
        w = self.window(a, d0)
        hs = [x[1][2] for x in w]; ls = [x[1][3] for x in w]
        mh = max(hs); kp = hs.index(mh); ml = min(ls); kl = ls.index(ml)
        pre = min(ls[:kp + 1])
        last = w[-1][1][4]
        return dict(up=(mh / e - 1) * 100, dd=(ml / e - 1) * 100, ddpk=(pre / e - 1) * 100, ret=(last / e - 1) * 100,
                    dpk=w[kp][0], ddday=w[kl][0], mh=mh, ml=ml,
                    r10=mh >= e * 1.10, r15=mh >= e * 1.15, r20=mh >= e * 1.20, t30=ml <= e * 0.70,
                    liq=ml <= e * (1 - LIQ),
                    surv10=(mh >= e * 1.10) and not (ml <= e * (1 - LIQ)))

    def days_to(self, a, d0, e, pct):
        for k, b in self.window(a, d0):
            if b[2] >= e * (1 + pct / 100):
                return k
        return None

    def vol_ratio(self, a, d0):
        if a not in self._vol:
            day = self.day[a]
            c = [x[4] for x in day]
            lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            vol = {}
            for i in range(365, len(c)):
                vol[day[i][0]] = st.pstdev(lr[i - 364:i + 1])
            med = median([v for d, v in vol.items() if d.year <= 2021])
            self._vol[a] = (vol, med)
        vol, med = self._vol[a]
        v = vol.get(d0)
        return None if v is None else v / med

    # ---------------- ETH funding availability (ledger membership)
    def funding(self, a):
        if a not in self._fund:
            f1, f2 = {}, {}
            with open(os.path.join(self.root, 'data', 'derivs', f'{a}_funding_daily.csv')) as fh:
                for r in csv.DictReader(fh):
                    d = D.fromisoformat(r['date'])
                    v = r.get('funding_oi_weighted') or r.get('funding_mean')
                    if v not in ('', None): f1[d] = float(v)
                    if r.get('funding_mean') not in ('', None): f2[d] = float(r['funding_mean'])
            self._fund[a] = (f1, f2)
        return self._fund[a]

    def eth_member(self, d0):
        f1, f2 = self.funding('ETH')
        if d0 not in f1:
            return False
        back = [f1.get(d0 - TD(days=k)) for k in range(1, 91)]
        if sum(v is not None for v in back) < 60:
            return False
        w7 = [d0 - TD(days=k) for k in range(7) if d0 - TD(days=k) in f2]
        w7b = [d0 - TD(days=14 + k) for k in range(7) if d0 - TD(days=14 + k) in f2]
        return len(w7) >= 5 and len(w7b) >= 5

    # ---------------- every scored signal with a closed 60-day window
    def scored(self):
        out = []
        for a in ASSETS:
            for tf in TFS:
                for s in self.sig[(a, tf)]:
                    if s['d0'] >= self.today or s['d0'] not in self.dpos[a]:
                        continue
                    if not self.complete(a, s['d0']):
                        continue
                    r = dict(s)
                    r['m'] = self.measure(a, s['d0'], s['entry'])
                    out.append(r)
        return out
