"""Audit 16 -- independent re-implementation. Nothing imported from the repo except regimes.py (gate only)."""
import csv, datetime as dt, math, os, sys, json, statistics as st
from decimal import Decimal, ROUND_HALF_UP

D = dt.date
ONE = dt.timedelta(days=1)
LIQ = 0.253
ASSETS = ("ETH", "BTC")
TFS_ALL = ("1D", "2D", "3D", "5D", "8D")
TFS_G = ("1D", "2D", "3D", "5D")
EPS = 1e-9


def rhaz(x, nd=0):
    """round half away from zero on the float's exact binary value"""
    q = Decimal(1).scaleb(-nd) if nd else Decimal(1)
    d = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if nd == 0 else float(d)


def udate(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


class Bars:
    def __init__(self, path, clamp=True):
        self.t = []; self.d = []; self.o = []; self.h = []; self.l = []; self.c = []
        self.clamps = []
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                self.t.append(int(float(r["time"]))); self.d.append(udate(float(r["time"])))
                o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
                if clamp:
                    lo_b, hi_b = min(o, c), max(o, c)
                    if lo_b > 0 and l < 0.5 * lo_b:
                        self.clamps.append((self.d[-1], "low", l, lo_b)); l = lo_b
                    if hi_b > 0 and h > 2 * hi_b:
                        self.clamps.append((self.d[-1], "high", h, hi_b)); h = hi_b
                self.o.append(o); self.h.append(h); self.l.append(l); self.c.append(c)
        self.pos = {d: i for i, d in enumerate(self.d)}
        self.n = len(self.d)


def wilder_rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    gains = [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]
    losses = [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
    ag = sum(gains[:n]) / n; al = sum(losses[:n]) / n
    out[n] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for i in range(n + 1, len(c)):
        ag = (ag * (n - 1) + gains[i - 1]) / n; al = (al * (n - 1) + losses[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def stoch_k(ct, n=14, sm=3):
    raw = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0:
            continue
        w = ct[i - n + 1:i + 1]
        if any(v is None for v in w):
            continue
        hi, lo = max(w), min(w)
        raw[i] = 0.0 if hi == lo else 100.0 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        if i - sm + 1 < 0:
            continue
        w = raw[i - sm + 1:i + 1]
        if any(v is None for v in w):
            continue
        k[i] = math.fsum(w) / sm
    return k


def pivots(ct, k, upto=None):
    """indices ti where ct[ti] is strictly below the 3 bars either side (all present) and K exists."""
    out = []
    n = len(ct) if upto is None else upto
    for ti in range(3, n - 3):
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)):
            continue
        if all(ct[j] > v for j in range(ti - 3, ti)) and all(ct[j] > v for j in range(ti + 1, ti + 4)) and k[ti] is not None:
            out.append(ti)
    return out


def bucket(v):
    return "A" if v < 40 else "B" if v < 55 else "C" if v < 65 else "D"


def tagstr(bk, dis, strong, prime):
    return " + ".join([bk] + (["filled diamond"] if strong else ["hollow diamond"] if dis else []) + (["prime dot"] if prime else []))


def bar_close_date(b, j):
    """last calendar day of bar j = day before the next bar's open; None if no next bar in file"""
    return b.d[j + 1] - ONE if j + 1 < b.n else None


def next_open(d, step):
    """open date of the bar after the one opening on d: step days on, or 1 January, whichever first"""
    return min(d + dt.timedelta(days=step), D(d.year + 1, 1, 1))


class Chart:
    def __init__(self, root, asset, tf, gate):
        self.asset, self.tf, self.name = asset, tf, f"{asset} {tf}"
        self.step = int(tf[:-1])
        self.b = Bars(os.path.join(root, "data", f"{asset}_{tf}.csv"))
        b = self.b
        self.ct = wilder_rsi(b.c); self.k = stoch_k(self.ct)
        self.piv = pivots(self.ct, self.k)
        self.sig = []       # gated, confirmed (ei exists); d0 may be None when conf bar is the last bar
        prev = None
        for ti in self.piv:
            v, kk = self.ct[ti], self.k[ti]
            dis = False
            if prev is not None:
                dct, dk = v - prev[0], kk - prev[1]
                dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
            strong = dis and v < 50
            prime = 20 <= kk < 50
            if gate(b.d[ti]):
                ei = ti + 3
                self.sig.append(dict(asset=asset, tf=tf, chart=self.name, ti=ti, ei=ei, tdate=b.d[ti], cdate=b.d[ei],
                                     d0=bar_close_date(b, ei), entry=b.c[ei], ct=v, k=kk, bk=bucket(v), dis=dis,
                                     strong=strong, prime=prime, tags=tagstr(bucket(v), dis, strong, prime), tlow=b.l[ti],
                                     prev=prev))
            prev = (v, kk)


def measure60(day, d0, entry, today, H=60):
    """forward window on daily candles: the H calendar days after d0. None unless day d0+H exists and has closed."""
    end = d0 + dt.timedelta(days=H)
    if end not in day.pos or d0 not in day.pos:
        return None
    if end >= today:          # the 60th day's daily bar must have closed (UTC)
        return None
    ks = [k for k in range(day.pos[d0] + 1, day.pos[end] + 1)]
    hs = [day.h[k] for k in ks]; ls = [day.l[k] for k in ks]
    mh, ml = max(hs), min(ls)
    kh = ks[hs.index(mh)]; kl = ks[ls.index(ml)]
    pre = min(day.l[k] for k in ks if k <= kh)
    return dict(up=(mh / entry - 1) * 100, dd=(ml / entry - 1) * 100, ret=(day.c[ks[-1]] / entry - 1) * 100,
                ddpk=(pre / entry - 1) * 100, dpk=(day.d[kh] - d0).days, ddday=(day.d[kl] - d0).days,
                ks=ks, ndays=len(ks))


def first_day_reach(day, d0, entry, pct, H=60):
    i = day.pos.get(d0)
    if i is None:
        return None
    for k in range(i + 1, day.n):
        nd = (day.d[k] - d0).days
        if nd > H:
            break
        if day.h[k] >= entry * (1 + pct / 100):
            return nd
    return None


def walk(day, d0, entry, H=60):
    """(high, low, dayno) for each daily bar in the H calendar days after d0 that exists in the file"""
    i = day.pos[d0]; out = []
    for k in range(i + 1, day.n):
        nd = (day.d[k] - d0).days
        if nd > H:
            break
        out.append((day.h[k], day.l[k], nd, k))
    return out


def from_entry_outcome(day, d0, entry):
    """'ok' rose 10% before ever falling 25.3% (low first within a day), 'liq' fell first, None neither"""
    for h, l, nd, k in walk(day, d0, entry):
        if l <= entry * (1 - LIQ):
            return "liq"
        if h >= entry * 1.10:
            return "ok"
    return None


def ladder_outcome(day, d0, entry, th):
    """None if it did not fall th% before rising 10%; else 'ok' / 'liq' / 'neither' for what followed"""
    w = walk(day, d0, entry)
    for j, (h, l, nd, k) in enumerate(w):
        if l <= entry * (1 - th / 100):
            for hh, ll, _, _ in w[j:]:
                if ll <= entry * (1 - LIQ):
                    return "liq"
                if hh >= entry * 1.10:
                    return "ok"
            return "neither"
        if h >= entry * 1.10:
            return None
    return None


class Vol:
    """365-day daily volatility of log returns ending on the day, over the asset's 2016-21 median of it"""
    def __init__(self, day):
        lr = [0.0] + [math.log(day.c[i] / day.c[i - 1]) for i in range(1, day.n)]
        self.v = {}
        for i in range(365, day.n):
            self.v[day.d[i]] = st.pstdev(lr[i - 364:i + 1])
        self.med = st.median(v for d, v in self.v.items() if d.year <= 2021)

    def ratio(self, d0):
        v = self.v.get(d0)
        return None if v is None else v / self.med


def quant(vals, f):
    s = sorted(vals); pos = (len(s) - 1) * f; lo = math.floor(pos); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


class State:
    def __init__(self, root, now):
        self.root = root; self.now = now; self.today = now.date()
        sys.path.insert(0, root)
        import importlib
        for m in ("regimes", "engine"):
            sys.modules.pop(m, None)
        cwd = os.getcwd(); os.chdir(root)
        try:
            R = importlib.import_module("regimes")
            self.gate = R.rsi_regime(os.path.join(root, "data", "BTC_2D.csv"), 8, 13, 60, 41)
        finally:
            os.chdir(cwd); sys.path.remove(root)
            for m in ("regimes", "engine"):
                sys.modules.pop(m, None)
        self.day = {a: Bars(os.path.join(root, "data", f"{a}_1D.csv")) for a in ASSETS}
        self.vol = {a: Vol(self.day[a]) for a in ASSETS}
        self.ch = {(a, tf): Chart(root, a, tf, self.gate) for a in ASSETS for tf in TFS_ALL}
        self.feed = json.load(open(os.path.join(root, "feed", "ctzb_feed.json")))
        self.ledger = list(csv.DictReader(open(os.path.join(root, "datasets", "ledger.csv"))))
        # my measures for every gated, confirmed signal
        self.sigs = []
        for (a, tf), c in self.ch.items():
            for s in c.sig:
                if s["d0"] is None or s["d0"] >= self.today:
                    s["m"] = None
                else:
                    s["m"] = measure60(self.day[a], s["d0"], s["entry"], self.today)
                self.sigs.append(s)
        self.by = {(s["chart"], str(s["d0"])): s for s in self.sigs if s["d0"] is not None}

    def csvrows(self, name):
        p = os.path.join(self.root, "datasets", name)
        return list(csv.DictReader(open(p))) if os.path.exists(p) else []
