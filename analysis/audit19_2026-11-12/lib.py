"""Audit 19: independent re-implementation of every member-visible figure.
Nothing here imports the pipeline, except regimes.py for the gate (as the brief allows)."""
import csv, datetime as dt, math, os, sys, json, statistics
from fractions import Fraction as Fr
from decimal import Decimal, ROUND_HALF_UP

TFS = ('1D', '2D', '3D', '5D', '8D'); GRADED = ('1D', '2D', '3D', '5D'); ASSETS = ('ETH', 'BTC')
EPS = 1e-9
DAY = dt.timedelta(days=1)


def rha(x, nd=0):
    """round half away from zero on the exact value x (Fraction, Decimal, int, str or float->its binary value)"""
    if isinstance(x, Fr):
        s = 1 if x >= 0 else -1
        y = abs(x) * 10 ** nd
        q = (2 * y.numerator + y.denominator) // (2 * y.denominator)
        return Decimal(s * q) / (Decimal(10) ** nd)
    d = Decimal(x) if not isinstance(x, float) else Decimal(x)
    return d.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


def num_eq(shown, mine):
    """compare a shown value (number/str/None) to mine (Decimal/int/None/'')"""
    if mine is None or mine == '':
        return shown is None or shown == ''
    if shown is None or shown == '':
        return False
    try:
        return Decimal(str(shown)) == Decimal(str(mine))
    except Exception:
        return str(shown) == str(mine)


class Bars:
    pass


def load(path):
    """candles, with the documented flash-print clamp: a low under half the body's low is pulled to the body,
    a high over twice the body's high likewise."""
    b = Bars(); b.date = []; b.t = []; b.o = []; b.h = []; b.l = []; b.c = []; b.so = []; b.sh = []; b.sl = []; b.sc = []; b.clamped = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            t = int(float(r['time']))
            d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
            so, sh, sl, sc = r['open'], r['high'], r['low'], r['close']
            o, h, l, c = float(so), float(sh), float(sl), float(sc)
            lo_body, hi_body = (so, o) if o <= c else (sc, c), (so, o) if o >= c else (sc, c)
            if lo_body[1] > 0 and l < 0.5 * lo_body[1]:
                b.clamped.append((d, 'low', l, lo_body[1])); sl, l = lo_body
            if hi_body[1] > 0 and h > 2 * hi_body[1]:
                b.clamped.append((d, 'high', h, hi_body[1])); sh, h = hi_body
            b.date.append(d); b.t.append(t); b.o.append(o); b.h.append(h); b.l.append(l); b.c.append(c)
            b.so.append(so); b.sh.append(sh); b.sl.append(sl); b.sc.append(sc)
    b.pos = {d: i for i, d in enumerate(b.date)}
    return b


# ---------------- indicator (written from the definition in CONTEXT "The setup") ----------------
def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n: return out
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
    # running-sum SMA, the way Pine's ta.sma accumulates (float residue matters for the EPS guard)
    k = [None] * len(ct); q = []; s = 0.0
    for i, v in enumerate(st):
        if v is None: q = []; s = 0.0; continue
        q.append(v); s += v
        if len(q) > sm: s -= q.pop(0)
        if len(q) == sm: k[i] = s / sm
    return k


def ema(src, n):
    out = [None] * len(src); first = next((i for i, v in enumerate(src) if v is not None), None)
    if first is None or len(src) - first < n: return out
    prev = sum(src[first:first + n]) / n; out[first + n - 1] = prev; a = 2.0 / (n + 1)
    for i in range(first + n, len(src)):
        prev = (src[i] - prev) * a + prev; out[i] = prev
    return out


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


def troughs(b):
    """every confirmed-or-confirmable pivot low on CT (3 bars each side, strictly lower), with tags; the
    previous-trough chain runs over all troughs."""
    ct = rsi(b.c); k = stoch_k(ct); n = len(b.c); out = []; prev = None
    for ti in range(3, n - 3):
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)): continue
        if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)): continue
        if k[ti] is None: continue
        dis = False
        if prev is not None:
            dct, dk = v - prev[0], k[ti] - prev[1]
            dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
        out.append(dict(ti=ti, ei=ti + 3, tdate=b.date[ti], ct=v, k=k[ti], bk=bucket(v), dis=dis, strong=dis and v < 50,
                        prime=20 <= k[ti] < 50, prevct=prev[0] if prev else None, prevk=prev[1] if prev else None))
        prev = (v, k[ti])
    return out, ct, k


def tagtext(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))


def tf_days(tf): return int(tf.rstrip('D'))


def bar_open_of(d, tf):
    """open date of the chart bar containing calendar day d (bars bucket days within each calendar year)"""
    j1 = dt.date(d.year, 1, 1); n = tf_days(tf)
    return j1 + dt.timedelta(days=((d - j1).days // n) * n)


def next_open(d, tf):
    return min(d + dt.timedelta(days=tf_days(tf)), dt.date(d.year + 1, 1, 1))


class State:
    def __init__(self, root, today):
        root = os.path.abspath(root); self.root = root; self.today = today
        self.bars = {(a, tf): load(os.path.join(root, 'data', f'{a}_{tf}.csv')) for a in ASSETS for tf in TFS}
        self.day = {a: self.bars[(a, '1D')] for a in ASSETS}
        sys.path.insert(0, root)
        import importlib
        for m in ('regimes', 'engine'):
            sys.modules.pop(m, None)
        R = importlib.import_module('regimes')
        cwd = os.getcwd(); os.chdir(root)
        self.gate = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        os.chdir(cwd); sys.path.remove(root)
        self.tr = {}; self.sig = {}; self.ct = {}; self.k = {}
        for key, b in self.bars.items():
            a, tf = key
            tr, ct, k = troughs(b); self.tr[key] = tr; self.ct[key] = ct; self.k[key] = k
            sg = []
            for s in tr:
                if not self.gate(s['tdate']): continue
                ei = s['ei']
                if ei + 1 >= len(b.date): continue          # confirmation bar still open: not a signal yet
                s = dict(s, a=a, tf=tf, chart=f'{a} {tf}', d0=b.date[ei + 1] - DAY, entry=b.c[ei], entry_s=b.sc[ei], tlow=b.l[s['ti']])
                sg.append(s)
            self.sig[key] = sg
        self._vol = {}

    # ---- forward window on daily candles: the 60 calendar days after the entry date ----
    def window(self, a, d0, closed_only=True, H=60):
        d = self.day[a]; i0 = d.pos.get(d0)
        if i0 is None: return None
        ks = []
        for k in range(i0 + 1, len(d.date)):
            if (d.date[k] - d0).days > H: break
            if closed_only and d.date[k] >= self.today: break
            ks.append(k)
        return ks

    def measure(self, s):
        """None unless the 60th day's daily bar has closed. Exact rational arithmetic on the candle strings."""
        a, d0 = s['a'], s['d0']; d = self.day[a]
        ks = self.window(a, d0)
        if not ks or d.date[ks[-1]] != d0 + 60 * DAY: return None
        e = Fr(s['entry_s'])
        kh = max(ks, key=lambda k: (d.h[k], -k)); kl = min(ks, key=lambda k: (d.l[k], k))
        pre = [k for k in ks if k <= kh]; kpre = min(pre, key=lambda k: d.l[k])
        pc = lambda x: (Fr(x) / e - 1) * 100
        m = dict(up=pc(d.sh[kh]), dd=pc(d.sl[kl]), ddpk=pc(d.sl[kpre]), ret=pc(d.sc[ks[-1]]),
                 dpk=(d.date[kh] - d0).days, ddday=(d.date[kl] - d0).days, ks=ks)
        m['r10'] = Fr(d.sh[kh]) >= e * Fr(110, 100); m['r15'] = Fr(d.sh[kh]) >= e * Fr(115, 100)
        m['r20'] = Fr(d.sh[kh]) >= e * Fr(120, 100); m['r30'] = Fr(d.sh[kh]) >= e * Fr(130, 100)
        m['t30'] = Fr(d.sl[kl]) <= e * Fr(70, 100)
        m['nofall253'] = not (Fr(d.sl[kl]) <= e * Fr(747, 1000))
        m['surv10'] = m['r10'] and m['nofall253']
        return m

    def vol_ratio(self, a, d0):
        if a not in self._vol:
            c = self.day[a].c; dts = self.day[a].date
            lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            vol = {dts[i]: statistics.pstdev(lr[i - 364:i + 1]) for i in range(365, len(c))}
            med = statistics.median(v for k, v in vol.items() if k.year <= 2021)
            self._vol[a] = (vol, med)
        vol, med = self._vol[a]; v = vol.get(d0)
        return None if v is None else v / med

    def scaled20(self, s, m):
        r = self.vol_ratio(s['a'], s['d0'])
        return None if r is None else float(m['up']) >= 20 * r

    def days_to(self, s, pct, ks):
        d = self.day[s['a']]; e = Fr(s['entry_s']); lvl = e * Fr(100 + pct, 100)
        for k in ks:
            if Fr(d.sh[k]) >= lvl: return (d.date[k] - s['d0']).days
        return None

    def from_entry(self, s, ks):
        d = self.day[s['a']]; e = Fr(s['entry_s'])
        for k in ks:
            if Fr(d.sl[k]) <= e * Fr(747, 1000): return 'liq'
            if Fr(d.sh[k]) >= e * Fr(110, 100): return 'ok'
        return None

    def falls_first(self, s, ks, th):
        """None = never fell th% before rising 10%; else 'ok' / 'liq' / 'neither'"""
        d = self.day[s['a']]; e = Fr(s['entry_s'])
        for j, k in enumerate(ks):
            if Fr(d.sl[k]) <= e * Fr(100 - th, 100):
                for k2 in ks[j:]:
                    if Fr(d.sl[k2]) <= e * Fr(747, 1000): return 'liq'
                    if Fr(d.sh[k2]) >= e * Fr(110, 100): return 'ok'
                return 'neither'
            if Fr(d.sh[k]) >= e * Fr(110, 100): return None
        return None


def share(k, n, nd=0):
    return None if not n else rha(Fr(100 * k, n), nd)


def med(xs):
    xs = sorted(xs); n = len(xs)
    if not n: return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def quantile(vals, f):
    s = sorted(vals); k = Fr(len(s) - 1) * Fr(f); lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
UNPLAIN = {v: k for k, v in PLAIN.items()}


class Rec:
    def __init__(self, state): self.state = state; self.rows = []
    def add(self, loc, label, shown, mine, ok=None, cause=''):
        if ok is None: ok = num_eq(shown, mine)
        self.rows.append((self.state, loc, label, '' if shown is None else str(shown), '' if mine is None else str(mine), 'ok' if ok else 'DISAGREE', cause))
        return ok
    def bad(self): return [r for r in self.rows if r[5] != 'ok']
