"""Audit 17 -- independent recomputation of every member-facing number from the raw candles.

Written from the docs (CONTEXT.md, FEED_SPEC.md, CARD_SPEC.md) and the task definitions. Imports
nothing from the pipeline except regimes.rsi_regime (the gate), as allowed. Prices are exact
rationals (Fraction) parsed from the CSV strings; indicators (RSI / Stoch) are floats.
"""
import csv, datetime as dt, json, math, os, sys
from decimal import Decimal
from fractions import Fraction as F
from statistics import median as _median

ASSETS = ('ETH', 'BTC')
TFS = ('1D', '2D', '3D', '5D', '8D')
GRADED = ('1D', '2D', '3D', '5D')
LIQ = F(253, 1000)          # 25.3%
BAR = 70
EPS = 1e-9
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before',
         'FUND': 'funding at or above its 90-day median', 'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising',
         'FASTCT': 'CT recovering fast from the low'}
RPLAIN = {v: k for k, v in PLAIN.items()}


# ---------------------------------------------------------------- rounding
def rnd(x, nd=0):
    """Half away from zero on the exact (rational) value. Returns a Fraction."""
    x = F(x); s = 10 ** nd; y = x * s
    n = math.floor(abs(y) + F(1, 2))
    return F(n if y >= 0 else -n, s)


def floor_cent(x):
    return F(math.floor(F(x) * 100), 100)


def fr(v):
    """Anything numeric (str / Decimal / int / float-as-str) -> Fraction, None for blank."""
    if v is None or v == '':
        return None
    if isinstance(v, F):
        return v
    if isinstance(v, float):
        return F(repr(v))
    return F(str(v))


def med(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def share(k, n, nd=0):
    return None if not n else rnd(F(100 * k, n), nd)


def utc_date(ts):
    return dt.datetime.fromtimestamp(int(float(ts)), dt.timezone.utc).date()


def tfdays(tf):
    return int(tf.rstrip('D'))


def next_open(d, tf):
    """Open date of the bar after the one opening on d (bars bucket days within a calendar year)."""
    n = tfdays(tf)
    if n == 1:
        return d + dt.timedelta(days=1)
    j1 = dt.date(d.year, 1, 1)
    k = (d - j1).days // n
    nx = j1 + dt.timedelta(days=(k + 1) * n)
    return min(nx, dt.date(d.year + 1, 1, 1))


def bar_open_of(day, tf):
    """Open date of the bar that contains calendar day `day`."""
    n = tfdays(tf); j1 = dt.date(day.year, 1, 1)
    return j1 + dt.timedelta(days=((day - j1).days // n) * n)


# ---------------------------------------------------------------- candles
class Chart:
    def __init__(self, path, clamp=True):
        self.path = path
        rows = list(csv.DictReader(open(path)))
        self.raw = rows
        self.t = [int(float(r['time'])) for r in rows]
        self.d = [utc_date(r['time']) for r in rows]
        self.o = [F(r['open']) for r in rows]; self.h = [F(r['high']) for r in rows]
        self.l = [F(r['low']) for r in rows]; self.c = [F(r['close']) for r in rows]
        self.clamped = []
        if clamp:
            for i in range(len(rows)):
                lb, hb = min(self.o[i], self.c[i]), max(self.o[i], self.c[i])
                if lb > 0 and self.l[i] < lb / 2:
                    self.clamped.append((self.d[i], 'low', self.l[i], lb)); self.l[i] = lb
                if hb > 0 and self.h[i] > hb * 2:
                    self.clamped.append((self.d[i], 'high', self.h[i], hb)); self.h[i] = hb
        self.pos = {d: i for i, d in enumerate(self.d)}
        self.n = len(rows)
        self.cf = [float(x) for x in self.c]


def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1:
        return out
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


def rsi_state(c, n=14):
    """avg gain / avg loss after the last close of c (for the kill-close solve)."""
    g = l = 0.0
    for i in range(1, n + 1):
        ch = c[i] - c[i - 1]
        if ch > 0: g += ch
        else: l -= ch
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
    for i in range(len(ct)):
        if i - sm + 1 < 0:
            continue
        w = st[i - sm + 1:i + 1]
        if any(x is None for x in w):
            continue
        k[i] = sum(w) / sm
    return k


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


def tagstr(bk, dis, strong, prime):
    return ' + '.join([bk] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))


class State:
    def __init__(self, root, now):
        self.root = root
        self.now = now
        self.today = now.date()
        sys.path.insert(0, root)
        import regimes
        self.gate = regimes.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        self.ch = {(a, tf): Chart(os.path.join(root, 'data', f'{a}_{tf}.csv')) for a in ASSETS for tf in TFS}
        self.day = {a: self.ch[(a, '1D')] for a in ASSETS}
        self.ind = {}
        self.piv = {}
        for k, c in self.ch.items():
            ct = rsi(c.cf); kk = stoch_k(ct)
            self.ind[k] = (ct, kk)
            self.piv[k] = self._pivots(k)
        self._vol = {}

    # ---- pivots (every trough, gated or not) with tags
    def _pivots(self, key):
        c = self.ch[key]; ct, kk = self.ind[key]; out = []; pc = pk = None
        a, tf = key
        for ti in range(3, c.n - 3):
            v = ct[ti]
            w = ct[ti - 3:ti + 4]
            if v is None or any(x is None for x in w):
                continue
            if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)):
                continue
            if kk[ti] is None:
                continue
            dis = False
            if pc is not None:
                dc, dk = v - pc, kk[ti] - pk
                dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
            ei = ti + 3
            d0 = next_open(c.d[ei], tf) - dt.timedelta(days=1)       # the confirmation bar's last calendar day
            out.append(dict(a=a, tf=tf, chart=f'{a} {tf}', ti=ti, ei=ei, tdate=c.d[ti], edate=c.d[ei], d0=d0,
                            ct=v, k=kk[ti], bk=bucket(v), dis=dis, strong=dis and v < 50, prime=20 <= kk[ti] < 50,
                            entry=c.c[ei], gate=self.gate(c.d[ti]), dck=(None if pc is None else (v - pc, kk[ti] - pk))))
            pc, pk = v, kk[ti]
        for s in out:
            s['tags'] = tagstr(s['bk'], s['dis'], s['strong'], s['prime'])
            s['confirmed'] = s['d0'] < self.today          # its confirmation bar has closed (UTC)
        return out

    def signals(self, a, tf):
        """Gated, confirmed signals."""
        return [s for s in self.piv[(a, tf)] if s['gate'] and s['confirmed']]

    # ---- forming low
    def forming(self, a, tf):
        """The pivot low still waiting on right-hand bars. The open bar is the bar that contains today (the
        clock's UTC date); if the file's last bar ended before today, every bar in the file has closed and the
        open bar has no candle yet."""
        key = (a, tf); c = self.ch[key]; ct, kk = self.ind[key]; n = c.n
        last_open = next_open(c.d[-1], tf) - dt.timedelta(days=1) >= self.today
        # with no candle yet for the open bar, a trough on the last closed bar cannot be asserted (no price to
        # hold it), so only troughs with at least one closed right-hand bar are candidates
        for back in ((1, 2, 3) if last_open else (2, 3)):
            ti = (n - 1 - back) if last_open else (n - back)
            if ti - 3 < 0 or ct[ti] is None:
                continue
            v = ct[ti]
            if any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)):
                continue
            if any(ct[j] < v for j in range(ti + 1, n)):
                continue
            need = 3 - back
            conf_open = c.d[-1] if last_open else next_open(c.d[-1], tf)
            for _ in range(need):
                conf_open = next_open(conf_open, tf)
            d0 = next_open(conf_open, tf) - dt.timedelta(days=1)
            prevp = [p for p in self.piv[key] if p['ti'] < ti]
            dis = False
            if prevp and kk[ti] is not None:
                dc, dk = v - prevp[-1]['ct'], kk[ti] - prevp[-1]['k']
                dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
            prime = kk[ti] is not None and 20 <= kk[ti] < 50
            f = dict(a=a, tf=tf, chart=f'{a} {tf}', ti=ti, tdate=c.d[ti], need=need, d0=d0, ct=v, k=kk[ti], bk=bucket(v),
                     dis=dis, strong=dis and v < 50, prime=prime, price=c.c[-1], gate=self.gate(c.d[ti]), last_open=last_open)
            f['tags'] = tagstr(f['bk'], f['dis'], f['strong'], f['prime'])
            # kill close: the confirmation-bar close X* at which CT equals the trough CT. Known when the
            # confirmation bar is the open bar, or the one after it (then today's bar is taken at its latest price)
            f['kill_exact'] = None
            base = None
            if last_open and need in (0, 1):
                base = c.cf[:-1] if need == 0 else c.cf[:]
            elif not last_open and need == 0:
                base = c.cf[:]
            if base is not None:
                ag, al = rsi_state(base)
                r = v / 100.0
                ch = 13 * r * al / (1 - r) - 13 * ag            # if the bar closes up
                if ch < 0:
                    ch = 13 * al - 13 * ag * (1 - r) / r        # it closes down
                f['kill_exact'] = base[-1] + ch
                f['kill_base'] = base
            return f
        return None

    def rsi_if_close(self, base, x):
        return rsi(base + [x])[-1]

    # ---- low day inside the trough bar
    def low_day(self, a, tf, tdate):
        nx = next_open(tdate, tf); d = self.day[a]
        cand = [(d.l[d.pos[x]], x) for x in (tdate + dt.timedelta(days=i) for i in range((nx - tdate).days)) if x in d.pos]
        return min(cand)[1] if cand else tdate

    # ---- forward window on closed daily bars
    def window(self, a, d0, upto=60):
        d = self.day[a]; i = d.pos.get(d0)
        if i is None:
            return []
        out = []
        for k in range(i + 1, d.n):
            n = (d.d[k] - d0).days
            if n > upto: break
            if d.d[k] >= self.today: break        # that daily bar has not closed
            out.append((n, k))
        return out

    def measure(self, a, d0, entry):
        """Full 60-day measures, or None unless day 60's daily bar has closed."""
        w = self.window(a, d0)
        if not w or w[-1][0] != 60:
            return None
        d = self.day[a]
        hs = [d.h[k] for _, k in w]; ls = [d.l[k] for _, k in w]
        mh, ml = max(hs), min(ls)
        ih = hs.index(mh); il = ls.index(ml)
        pct = lambda p: (p / entry - 1) * 100
        r10 = next((n for (n, k) in w if d.h[k] >= entry * F(11, 10)), None)
        r20 = next((n for (n, k) in w if d.h[k] >= entry * F(12, 10)), None)
        return dict(up=pct(mh), dd=pct(ml), ddpk=pct(min(ls[:ih + 1])), ret=pct(d.c[w[-1][1]]), dpk=w[ih][0], ddday=w[il][0],
                    r10=mh >= entry * F(11, 10), r15=mh >= entry * F(115, 100), r20=mh >= entry * F(12, 10), r30=mh >= entry * F(13, 10),
                    t30=ml <= entry * F(7, 10), surv=mh >= entry * F(11, 10) and ml > entry * (1 - LIQ),
                    d10=r10, d20=r20, w=w)

    def vol_ratio(self, a, d0):
        if a not in self._vol:
            d = self.day[a]; c = d.cf
            lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            vol = {}
            for i in range(365, len(c)):
                w = lr[i - 364:i + 1]; m = sum(w) / len(w)
                vol[d.d[i]] = math.sqrt(sum((x - m) ** 2 for x in w) / len(w))
            base = _median([v for k, v in vol.items() if k.year <= 2021])
            self._vol[a] = (vol, base)
        vol, base = self._vol[a]
        v = vol.get(d0)
        return None if v is None else v / base

    def scaled20(self, a, d0, m):
        r = self.vol_ratio(a, d0)
        return None if r is None else float(m['up']) >= 20 * r

    # ---- ladder / from entry on a sample of (a, d0, entry)
    def from_entry(self, G):
        ok = liq = n = 0
        for s in G:
            d = self.day[s['a']]; e = s['entry']; n += 1
            for _, k in s['m']['w']:
                if d.l[k] <= e * (1 - LIQ): liq += 1; break
                if d.h[k] >= e * F(11, 10): ok += 1; break
        return n, ok, liq

    def ladder(self, G, th):
        hit = ok = liq = 0
        for s in G:
            d = self.day[s['a']]; e = s['entry']; w = s['m']['w']
            for j, (_, k) in enumerate(w):
                if d.l[k] <= e * (1 - F(th, 100)):
                    hit += 1
                    for _, kk in w[j:]:
                        if d.l[kk] <= e * (1 - LIQ): liq += 1; break
                        if d.h[kk] >= e * F(11, 10): ok += 1; break
                    break
                if d.h[k] >= e * F(11, 10):
                    break
        return hit, ok, liq


# ---------------------------------------------------------------- check log
class Log:
    def __init__(self, state):
        self.state = state; self.rows = []

    def chk(self, loc, label, shown, mine, cause=''):
        ok = same(shown, mine)
        self.rows.append([self.state, loc, label, show(shown), show(mine), 'ok' if ok else 'DISAGREE', '' if ok else cause])
        return ok

    def bad(self):
        return [r for r in self.rows if r[5] != 'ok']


def show(v):
    if v is None: return ''
    if isinstance(v, F):
        return str(v.numerator) if v.denominator == 1 else format(float(v), '.10g')
    if isinstance(v, bool): return 'yes' if v else 'no'
    return str(v)


def same(a, b):
    na, nb = norm(a), norm(b)
    return na == nb


def norm(v):
    if v is None or v == '':
        return None
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, (int, F, Decimal)):
        return F(str(v)) if not isinstance(v, F) else v
    if isinstance(v, float):
        return F(repr(v))
    if isinstance(v, (dt.date,)):
        return str(v)
    s = str(v)
    try:
        return F(s)
    except (ValueError, ZeroDivisionError):
        return s


def load_feed(path):
    return json.load(open(path), parse_float=Decimal)
