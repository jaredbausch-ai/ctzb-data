"""Audit 7: independent recomputation of the ETHKROS member figures from raw candles.
Own code throughout; regimes.py is imported for the gate only."""
import csv, datetime as dt, math, os, sys, statistics as st
from decimal import Decimal, ROUND_HALF_UP

EPS = 1e-9
LIQF = 1 - 0.253          # never fell 25.3%: no daily low <= entry * (1 - 0.253)
SPLIT = dt.date(2022, 1, 1)
TFS = ('1D', '2D', '3D', '5D', '8D')
GRADED = ('1D', '2D', '3D', '5D')


def rnd(x, nd=0):
    """half away from zero on the exact binary value"""
    q = Decimal(1) if nd == 0 else Decimal(1).scaleb(-nd)
    d = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if nd == 0 else float(d)


def day_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def clamp(o, h, l, c):
    lb, hb = min(o, c), max(o, c)
    if lb > 0 and l < 0.5 * lb: l = lb
    if hb > 0 and h > hb / 0.5: h = hb
    return h, l


def read_raw(path):
    out = []
    for r in csv.DictReader(open(path)):
        out.append((day_of(r['time']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])))
    return out


class Daily:
    def __init__(self, path):
        raw = read_raw(path)
        self.raw = raw
        self.D = [x[0] for x in raw]; self.O = [x[1] for x in raw]; self.C = [x[4] for x in raw]
        self.H, self.L = [], []
        self.clamps = []
        for d, o, h, l, c in raw:
            h2, l2 = clamp(o, h, l, c)
            if (h2, l2) != (h, l): self.clamps.append((d, h, l, h2, l2))
            self.H.append(h2); self.L.append(l2)
        self.pos = {d: i for i, d in enumerate(self.D)}


def resample(raw, tf):
    """calendar-year buckets restarting on 1 January (fetch.py's documented rule)"""
    g = {}
    for d, o, h, l, c in raw:
        key = (d.year, (d - dt.date(d.year, 1, 1)).days // tf)
        g.setdefault(key, []).append((d, o, h, l, c))
    out = []
    for key in sorted(g):
        xs = g[key]
        out.append((xs[0][0], xs[0][1], max(x[2] for x in xs), min(x[3] for x in xs), xs[-1][4]))
    return out


def bucket_last_day(d_open, tf):
    """last calendar day of the bucket that opens on d_open"""
    if tf == 1: return d_open
    y0 = dt.date(d_open.year, 1, 1)
    k = (d_open - y0).days // tf
    end = y0 + dt.timedelta(days=k * tf + tf - 1)
    return min(end, dt.date(d_open.year, 12, 31))


def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n: return out
    up = sum(max(c[i] - c[i - 1], 0) for i in range(1, n + 1)) / n
    dn = sum(max(c[i - 1] - c[i], 0) for i in range(1, n + 1)) / n
    out[n] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    for i in range(n + 1, len(c)):
        ch = c[i] - c[i - 1]
        up = (up * (n - 1) + max(ch, 0)) / n
        dn = (dn * (n - 1) + max(-ch, 0)) / n
        out[i] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    return out


def stochK(ct, n=14, sm=3):
    s = [None] * len(ct)
    for i in range(len(ct)):
        w = ct[i - n + 1:i + 1] if i - n + 1 >= 0 else []
        if len(w) < n or any(x is None for x in w): continue
        hi, lo = max(w), min(w)
        s[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        w = s[i - sm + 1:i + 1] if i - sm + 1 >= 0 else []
        if len(w) == sm and all(x is not None for x in w): k[i] = sum(w) / sm
    return k


def ema(src, n):
    out = [None] * len(src); a = 2 / (n + 1)
    first = next((i for i, v in enumerate(src) if v is not None), None)
    if first is None or len(src) - first < n: return out
    prev = sum(src[first:first + n]) / n; out[first + n - 1] = prev
    for i in range(first + n, len(src)):
        prev = (src[i] - prev) * a + prev; out[i] = prev
    return out


class Chart:
    """one asset/timeframe built from the daily raw candles"""
    def __init__(self, daily, tf):
        self.tf = int(tf.rstrip('D'))
        bars = daily.raw if self.tf == 1 else resample(daily.raw, self.tf)
        self.bars = bars
        self.D = [b[0] for b in bars]; self.C = [b[4] for b in bars]
        self.ct = rsi(self.C); self.K = stochK(self.ct)


def troughs(ch):
    """every pivot low on CT (3 either side, strictly lower), K defined, in bar order"""
    ct, K = ch.ct, ch.K; out = []
    for ti in range(3, len(ct) - 3):
        v = ct[ti]
        w = ct[ti - 3:ti + 4]
        if any(x is None for x in w): continue
        if all(ct[j] > v for j in range(ti - 3, ti)) and all(ct[j] > v for j in range(ti + 1, ti + 4)) and K[ti] is not None:
            out.append(ti)
    return out


def signals(ch, gate, today):
    """gated, confirmed signals. today = clock UTC date; a confirmation bar counts once its last day < today"""
    out = []; prev = None
    for ti in troughs(ch):
        v, k = ch.ct[ti], ch.K[ti]
        dis = False
        if prev is not None:
            dc, dk = v - prev[0], k - prev[1]
            dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
        prev = (v, k)
        tdate = ch.D[ti]
        if not gate(tdate): continue
        ei = ti + 3
        d0 = bucket_last_day(ch.D[ei], ch.tf)
        if d0 >= today: continue          # confirmation bar still open
        bk = 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'
        out.append(dict(ti=ti, ei=ei, tdate=tdate, d0=d0, entry=ch.C[ei], ct=v, k=k, bk=bk, dis=dis,
                        strong=dis and v < 50, prime=20 <= k < 50))
    return out


def tags_text(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))


def window(day, d0, H=60):
    """indices of the daily bars on calendar days d0+1 .. d0+H (must all exist)"""
    ks = []
    for k in range(1, H + 1):
        i = day.pos.get(d0 + dt.timedelta(days=k))
        if i is None: return None
        ks.append(i)
    return ks


def measure(day, d0, e, today):
    """60-day forward measures from the entry close on d0; None unless day 60 has closed"""
    if d0 + dt.timedelta(days=60) >= today: return None
    ks = window(day, d0)
    if ks is None: return None
    H = [day.H[i] for i in ks]; L = [day.L[i] for i in ks]
    mh, ml = max(H), min(L)
    kp = H.index(mh); kl = L.index(ml)
    return dict(up=(mh / e - 1) * 100, dd=(ml / e - 1) * 100, ddpk=(min(L[:kp + 1]) / e - 1) * 100,
                ret=(day.C[ks[-1]] / e - 1) * 100, dpk=kp + 1, ddday=kl + 1,
                r10=mh >= e * 1.10, r15=mh >= e * 1.15, r20=mh >= e * 1.20, t30=ml <= e * 0.70,
                fell25=ml <= e * LIQF, H=H, L=L,
                d10=next((k + 1 for k in range(60) if H[k] >= e * 1.10), None),
                d20=next((k + 1 for k in range(60) if H[k] >= e * 1.20), None))


class Vol:
    def __init__(self, day):
        c = day.C
        lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
        self.v = {}
        for i in range(365, len(c)):
            self.v[day.D[i]] = st.pstdev(lr[i - 364:i + 1])
        self.med = st.median(v for d, v in self.v.items() if d.year <= 2021)

    def scaled20(self, d0, up):
        v = self.v.get(d0)
        return None if v is None else up >= 20 * v / self.med


def ladder_one(H, L, e, th):
    """fell th% first (before rising 10%, low checked first in a day): None (not hit) / 'ok' / 'liq' / 'neither'"""
    for j in range(len(H)):
        if L[j] <= e * (1 - th / 100):
            for h, l in zip(H[j:], L[j:]):
                if l <= e * LIQF: return 'liq'
                if h >= e * 1.10: return 'ok'
            return 'neither'
        if H[j] >= e * 1.10: return None
    return None


def from_entry_one(H, L, e):
    for h, l in zip(H, L):
        if l <= e * LIQF: return 'liq'
        if h >= e * 1.10: return 'ok'
    return 'neither'


def pctr(k, n):
    return rnd(100 * k / n) if n else ''


def medr(xs, nd=1):
    return rnd(st.median(xs), nd) if xs else ''


def card_figs(G, vol):
    """G: list of dicts with a, d0, entry, m (measure). returns dict of card fields"""
    n = len(G)
    f = {'n': n}
    f['reach10'] = pctr(sum(g['m']['r10'] for g in G), n)
    f['surv10'] = pctr(sum(g['m']['r10'] and not g['m']['fell25'] for g in G), n)
    f['reach20'] = pctr(sum(g['m']['r20'] for g in G), n)
    f['touched30'] = pctr(sum(g['m']['t30'] for g in G), n)
    sc = [vol[g['a']].scaled20(g['d0'], g['m']['up']) for g in G]; sc = [x for x in sc if x is not None]
    f['scaled20'] = pctr(sum(sc), len(sc)) if sc else ''
    for k, key in (('bestMove', 'up'), ('dipBeforeHigh', 'ddpk'), ('maxDip60', 'dd')):
        xs = [g['m'][key] for g in G]
        f[k] = medr(xs, 1); f[k + 'Exact'] = st.median(xs) if xs else ''
    old = [g for g in G if g['d0'] < SPLIT]; new = [g for g in G if g['d0'] >= SPLIT]
    f['nOld'] = len(old); f['nNew'] = len(new)
    f['surv10Old'] = pctr(sum(g['m']['r10'] and not g['m']['fell25'] for g in old), len(old))
    f['surv10New'] = pctr(sum(g['m']['r10'] and not g['m']['fell25'] for g in new), len(new))
    fe = [from_entry_one(g['m']['H'], g['m']['L'], g['entry']) for g in G]
    f['l0ok'] = pctr(fe.count('ok'), n); f['l0liq'] = pctr(fe.count('liq'), n)
    for th in (5, 10, 15, 20):
        rs = [ladder_one(g['m']['H'], g['m']['L'], g['entry'], th) for g in G]
        hit = [r for r in rs if r is not None]
        f[f'l{th}n'] = len(hit); f[f'l{th}ok'] = pctr(hit.count('ok'), len(hit)); f[f'l{th}liq'] = pctr(hit.count('liq'), len(hit))
    t10 = [g['m']['d10'] for g in G if g['m']['d10'] is not None]
    t20 = [g['m']['d20'] for g in G if g['m']['d20'] is not None]
    f['daysTo10'] = medr(t10, 0); f['daysTo20'] = medr(t20, 0)
    f['daysToHigh'] = medr([g['m']['dpk'] for g in G], 0); f['daysToLow'] = medr([g['m']['ddday'] for g in G], 0)
    return f


def q_lin(vals, p):
    s = sorted(vals); k = (len(s) - 1) * p; lo = math.floor(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
