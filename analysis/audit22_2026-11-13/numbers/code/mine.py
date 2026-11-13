"""Auditor's own computation of every figure, from raw daily candles (audit 22, numbers on real data).
Written independently: only regimes.py is imported from the pipeline (for the gate).
Entry quality only: computed signals, not fills; there is no exit in the data."""
import csv, os, sys, math, statistics as st, datetime as dt, bisect
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

D = dt.date
ONE = dt.timedelta(days=1)
TFS = ('1D', '2D', '3D', '5D', '8D')
GRADED = ('1D', '2D', '3D', '5D')
EPS = 1e-9
LIQ = 0.253
SPLIT = D(2022, 1, 1)
EX_D0 = D(2024, 9, 22)


def rnd(x, nd=0):
    """half away from zero on the float's exact binary value"""
    q = Decimal(1) if nd == 0 else Decimal(1).scaleb(-nd)
    v = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(v) if nd == 0 else float(v)


def floor_cent(x):
    return float(Decimal(float(x)).quantize(Decimal('0.01'), rounding=ROUND_FLOOR))


def px_at(entry, pct):
    """price pct% away from entry, exact decimal on cents, half away from zero"""
    e = Decimal(str(rnd(entry, 2)))
    p = Decimal(repr(float(pct)))
    v = e * (Decimal(1) + p / Decimal(100))
    return float(v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quant(xs, q):
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo = int(math.floor(k)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def udate(t):
    return dt.datetime.fromtimestamp(int(float(t)), dt.timezone.utc).date()


def read_csv(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def clamp(o, h, l, c):
    lo_b, hi_b = min(o, c), max(o, c)
    if lo_b > 0 and l < 0.5 * lo_b:
        l = lo_b
    if hi_b > 0 and h > 2 * hi_b:
        h = hi_b
    return h, l


# ------------------------------------------------------------------ indicator (Pine definitions)
def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) < n + 1:
        return out, [None] * len(c)
    g = [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]
    l = [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
    ag = sum(g[:n]) / n; al = sum(l[:n]) / n
    a = 1.0 / n
    def val(ag, al):
        return 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    out[n] = val(ag, al)
    st_ = [(ag, al)] * len(c)
    st_[n] = (ag, al)
    for i in range(n + 1, len(c)):
        ag = a * g[i - 1] + (1 - a) * ag
        al = a * l[i - 1] + (1 - a) * al
        out[i] = val(ag, al)
        st_[i] = (ag, al)
    return out, st_


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


def zone_min(ct):
    out, z = [], None
    for v in ct:
        if v is None:
            out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        out.append(z)
    return out


def bucket(v):
    return 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'


# ------------------------------------------------------------------ state
class State:
    def __init__(self, sdir, now, gate_fn=None):
        self.dir = sdir
        self.now = now
        self.today = now.date()
        self.daily = {}
        self.bars = {}
        self.file_mismatch = []
        for a in ('ETH', 'BTC'):
            rows = read_csv(os.path.join(sdir, 'data', f'{a}_1D.csv'))
            d = dict(date=[], o=[], h=[], l=[], c=[], rawl=[], rawh=[])
            for r in rows:
                o, h, l, c = (float(r[k]) for k in ('open', 'high', 'low', 'close'))
                hh, ll = clamp(o, h, l, c)
                d['date'].append(udate(r['time'])); d['o'].append(o); d['h'].append(hh); d['l'].append(ll); d['c'].append(c)
                d['rawh'].append(h); d['rawl'].append(l)
            d['pos'] = {x: i for i, x in enumerate(d['date'])}
            self.daily[a] = d
            for tf in TFS:
                self.bars[(a, tf)] = self._bucket(a, tf)
                self._compare_file(a, tf)
        if gate_fn is None:
            sys.path.insert(0, '/home/claude/ctzb-data')
            import regimes as R
            gate_fn = R.rsi_regime(os.path.join(sdir, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
        self.gate = gate_fn
        self.sig = {}; self.piv = {}; self.prov = {}; self.ind = {}
        for a in ('ETH', 'BTC'):
            for tf in TFS:
                self._signals(a, tf)

    def _bucket(self, a, tf):
        n = int(tf[:-1]); d = self.daily[a]
        groups = {}
        order = []
        for i, x in enumerate(d['date']):
            if n == 1:
                key = (x.year, (x - D(x.year, 1, 1)).days)
            else:
                key = (x.year, (x - D(x.year, 1, 1)).days // n)
            if key not in groups:
                groups[key] = []; order.append(key)
            groups[key].append(i)
        out = []
        for key in order:
            ix = groups[key]
            start = D(key[0], 1, 1) + dt.timedelta(days=key[1] * n)
            end = min(start + dt.timedelta(days=n - 1), D(key[0], 12, 31))
            o = d['o'][ix[0]]; c = d['c'][ix[-1]]
            h = max(d['rawh'][i] for i in ix); l = min(d['rawl'][i] for i in ix)
            hh, ll = clamp(o, h, l, c)
            out.append(dict(open=d['date'][ix[0]], cal_open=start, close_date=end, o=o, h=hh, l=ll, c=c, rawh=h, rawl=l, days=ix))
        return out

    def _compare_file(self, a, tf):
        p = os.path.join(self.dir, 'data', f'{a}_{tf}.csv')
        rows = read_csv(p)
        mine = self.bars[(a, tf)]
        if len(rows) != len(mine):
            self.file_mismatch.append((a, tf, 'length', len(rows), len(mine))); return
        for r, b in zip(rows, mine):
            vals = tuple(float(r[k]) for k in ('open', 'high', 'low', 'close'))
            if udate(r['time']) != b['open'] or vals != (b['o'], b['rawh'], b['rawl'], b['c']):
                self.file_mismatch.append((a, tf, str(udate(r['time'])), vals, (b['o'], b['rawh'], b['rawl'], b['c'])))
                if len(self.file_mismatch) > 20:
                    return

    def _signals(self, a, tf):
        B = self.bars[(a, tf)]
        c = [b['c'] for b in B]
        ct, rst = rsi(c)
        K = stochK(ct)
        zm = zone_min(ct)
        self.ind[(a, tf)] = dict(ct=ct, K=K, zm=zm, rst=rst, c=c)
        n = len(B)
        piv = []
        for ti in range(3, n - 3):
            v = ct[ti]
            w = ct[ti - 3:ti + 4]
            if v is None or any(x is None for x in w):
                continue
            if any(ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] <= v for j in range(ti + 1, ti + 4)):
                continue
            if K[ti] is None:
                continue
            piv.append(ti)
        out = []; allp = []
        prev = None
        for ti in piv:
            v, k = ct[ti], K[ti]
            if prev is not None:
                dct, dk = v - prev[0], k - prev[1]
                dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
                near = min(abs(abs(dct) - EPS), abs(abs(dk) - EPS)) < 1e-12
            else:
                dis = False; near = False
            prev = (v, k)
            ei = ti + 3
            conf = B[ei]
            closed = ei < n - 1          # the confirmation bar has a successor: it has closed
            s = dict(a=a, tf=tf, ti=ti, ei=ei, tdate=B[ti]['open'], ct=v, k=k, bk=bucket(v), dis=dis, strong=dis and v < 50,
                     prime=20 <= k < 50, d0=conf['close_date'] if closed else None, entry=conf['c'],
                     gated=bool(self.gate(B[ti]['open'])), zm=zm[ti], near_eps=near,
                     next_open=B[ei + 1]['open'] if closed else None)
            allp.append(s)
            if s['gated'] and closed:
                out.append(s)
        self.piv[(a, tf)] = allp
        self.sig[(a, tf)] = out
        # forming low
        self.prov[(a, tf)] = None
        for back in (1, 2, 3):
            ti = n - 1 - back
            if ti - 3 < 0 or ct[ti] is None:
                continue
            v = ct[ti]
            if any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)):
                continue
            if any(ct[j] < v for j in range(ti + 1, n)):
                continue
            prevp = [x for x in allp if x['ti'] < ti]
            k = K[ti]
            if prevp and k is not None:
                dct, dk = v - prevp[-1]['ct'], k - prevp[-1]['k']
                dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
            else:
                dis = False
            need = 3 - back
            # confirmation bar: `need` bars after the open bar, by the calendar bar rule
            cb_open = B[-1]['cal_open']
            for _ in range(need):
                cb_open = next_cal_open(cb_open, int(tf[:-1]))
            cb_close = next_cal_open(cb_open, int(tf[:-1])) - ONE
            kill = None
            if need in (0, 1):
                base_n = n - 1 if need == 0 else n      # replace the open bar's close, or append the next bar
                kill = kill_close(c, rst, base_n, v)
            self.prov[(a, tf)] = dict(ti=ti, tdate=B[ti]['open'], ct=v, k=k, bk=bucket(v), dis=dis, strong=dis and v < 50,
                                      prime=k is not None and 20 <= k < 50, need=need, d0=cb_close, kill=kill,
                                      gated=bool(self.gate(B[ti]['open'])), price=c[-1])
            break

    # ------------------------------------------------------------ measures on daily candles
    def window(self, a, d0):
        d = self.daily[a]
        i0 = d['pos'].get(d0)
        if i0 is None:
            return None, []
        ks = []
        for k in range(i0 + 1, len(d['date'])):
            off = (d['date'][k] - d0).days
            if off > 60:
                break
            ks.append((k, off))
        return i0, ks

    def closed60(self, a, d0):
        i0, ks = self.window(a, d0)
        if i0 is None or not ks or ks[-1][1] != 60:
            return False
        return self.daily[a]['date'][ks[-1][0]] < self.today

    def measure(self, a, d0, c0):
        d = self.daily[a]
        i0, ks = self.window(a, d0)
        if not self.closed60(a, d0):
            return None
        H = [d['h'][k] for k, _ in ks]; L = [d['l'][k] for k, _ in ks]
        jh = max(range(len(H)), key=lambda j: (H[j], -j))
        jl = min(range(len(L)), key=lambda j: (L[j], j))
        m = dict(up=(max(H) / c0 - 1) * 100, dd=(min(L) / c0 - 1) * 100,
                 ddpk=(min(L[:jh + 1]) / c0 - 1) * 100, ret=(d['c'][ks[-1][0]] / c0 - 1) * 100,
                 dpk=ks[jh][1], ddday=ks[jl][1])
        m['r10'] = max(H) >= c0 * 1.10
        m['r15'] = max(H) >= c0 * 1.15
        m['r20'] = max(H) >= c0 * 1.20
        m['r30'] = max(H) >= c0 * 1.30
        m['t30'] = min(L) <= c0 * 0.70
        m['liq'] = min(L) <= c0 * (1 - LIQ)
        m['surv10'] = m['r10'] and not m['liq']
        # percent-space twins, to catch any boundary where float order would matter
        m['pct_space_differs'] = ((m['up'] >= 10) != m['r10']) or ((m['up'] >= 20) != m['r20']) or ((m['up'] >= 30) != m['r30']) or ((m['up'] >= 15) != m['r15']) or ((m['dd'] <= -30) != m['t30']) or ((m['dd'] > -25.3) != (not m['liq']))
        # days to +10 / +20
        for p in (10, 20):
            m[f't{p}'] = next((off for (k, off) in ks if d['h'][k] >= c0 * (1 + p / 100)), None)
        # ladder walk
        m['ks'] = ks
        return m

    def ladder_one(self, a, d0, c0, th):
        """returns None (did not fall th% first), 'ok', 'liq', or 'none' (fell first, neither after)"""
        d = self.daily[a]
        _, ks = self.window(a, d0)
        for j, (k, off) in enumerate(ks):
            if th > 0 and d['l'][k] <= c0 * (1 - th / 100):
                for k2, _ in ks[j:]:
                    if d['l'][k2] <= c0 * (1 - LIQ):
                        return 'liq'
                    if d['h'][k2] >= c0 * 1.10:
                        return 'ok'
                return 'none'
            if th == 0:
                if d['l'][k] <= c0 * (1 - LIQ):
                    return 'liq'
                if d['h'][k] >= c0 * 1.10:
                    return 'ok'
                continue
            if d['h'][k] >= c0 * 1.10:
                return None
        return 'none' if th == 0 else None

    # ------------------------------------------------------------ volatility (scaled20)
    def vol(self, a):
        if not hasattr(self, '_vol'):
            self._vol = {}
        if a not in self._vol:
            d = self.daily[a]; c = d['c']
            lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            v = {}
            for i in range(365, len(c)):
                v[d['date'][i]] = st.pstdev(lr[i - 364:i + 1])
            medv = median([x for k, x in v.items() if k.year <= 2021])
            self._vol[a] = (v, medv)
        return self._vol[a]

    def scaled20(self, a, d0, m):
        v, medv = self.vol(a)
        x = v.get(d0)
        if x is None:
            return None
        return m['up'] >= 20 * (x / medv)

    def daily_close(self, a, d0):
        d = self.daily[a]
        return d['c'][d['pos'][d0]]

    def low_day(self, a, tf, tdate):
        B = self.bars[(a, tf)]
        b = next(x for x in B if x['open'] == tdate)
        d = self.daily[a]
        cand = [(d['l'][i], d['date'][i]) for i in b['days']]
        return min(cand)[1]


def next_cal_open(d, n):
    if n == 1:
        return d + ONE
    start = D(d.year, 1, 1)
    k = (d - start).days // n
    nx = start + dt.timedelta(days=(k + 1) * n)
    return min(nx, D(d.year + 1, 1, 1))


def kill_close(c, rst, base_n, target):
    """the close of bar base_n (replacing the open bar if base_n == len(c) - 1, else appended) at which CT
    equals the trough's CT; returned as the exact threshold"""
    ag, al = rst[base_n - 1]
    cp = c[base_n - 1]
    rs = target / (100 - target)
    a = 1 / 14
    # up move: ag' = a*(X-cp) + (1-a)*ag ; al' = (1-a)*al ; ag'/al' = rs
    x_up = cp + ((rs * (1 - a) * al) - (1 - a) * ag) / a
    if x_up >= cp:
        return x_up
    # down move: ag' = (1-a)*ag ; al' = a*(cp-X) + (1-a)*al
    x_dn = cp - (((1 - a) * ag / rs) - (1 - a) * al) / a
    return x_dn


def tags_of(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))
