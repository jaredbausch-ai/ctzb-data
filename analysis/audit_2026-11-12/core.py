"""Independent audit core. Own candle reader, own RSI / pivot / forward measures.
Only regimes.rsi_regime is imported from the repo (it is the gate definition)."""
import csv, datetime as dt, math, os, sys

REPO = '/home/claude/ctzb-data'
UTC = dt.timezone.utc
TFD = {'1D': 1, '2D': 2, '3D': 3, '5D': 5, '8D': 8}
LIQ = -25.3


def load(asset, tf, clamp=True):
    rows = list(csv.DictReader(open(os.path.join(REPO, 'data', f'{asset}_{tf}.csv'))))
    out = []
    for r in rows:
        o, h, l, c = (float(r[k]) for k in ('open', 'high', 'low', 'close'))
        d = dt.datetime.fromtimestamp(int(r['time']), UTC).date()
        if clamp:  # stated rule: low < half the body bottom / high > twice the body top is not tradable
            lb, hb = min(o, c), max(o, c)
            if l < 0.5 * lb: l = lb
            if h > 2 * hb: h = hb
        out.append(dict(t=int(r['time']), d=d, o=o, h=h, l=l, c=c))
    return out


def bar_end(bars, i, tf):
    """Last calendar day covered by bar i."""
    if i + 1 < len(bars):
        return bars[i + 1]['d'] - dt.timedelta(days=1)
    return bars[i]['d'] + dt.timedelta(days=TFD[tf] - 1)


def wilder_rsi(x, n=14):
    out = [None] * len(x)
    if len(x) <= n: return out
    up = sum(max(x[i] - x[i - 1], 0) for i in range(1, n + 1)) / n
    dn = sum(max(x[i - 1] - x[i], 0) for i in range(1, n + 1)) / n
    out[n] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    for i in range(n + 1, len(x)):
        ch = x[i] - x[i - 1]
        up = (up * (n - 1) + max(ch, 0)) / n
        dn = (dn * (n - 1) + max(-ch, 0)) / n
        out[i] = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
    return out


def kline(ct, n=14, m=3):
    st = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0: continue
        w = ct[i - n + 1:i + 1]
        if any(v is None for v in w): continue
        lo, hi = min(w), max(w)
        st[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        w = st[i - m + 1:i + 1] if i - m + 1 >= 0 else []
        if len(w) == m and all(v is not None for v in w): k[i] = sum(w) / m
    return k


_GATE = None
def gate():
    global _GATE
    if _GATE is None:
        sys.path.insert(0, REPO)
        cwd = os.getcwd(); os.chdir(REPO)
        import regimes
        _GATE = regimes.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
        os.chdir(cwd)
    return _GATE


def troughs(asset, tf, clamp=True):
    """Every pivot low of CT RSI (3 bars each side, strictly lower), ungated, with tags."""
    b = load(asset, tf, clamp)
    c = [x['c'] for x in b]
    ct = wilder_rsi(c); k = kline(ct)
    out = []; prev = None
    zmin = []; z = None
    for v in ct:
        if v is None: zmin.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v)); zmin.append(z)
    for ti in range(3, len(b) - 3):
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)): continue
        if not all(ct[j] > v for j in list(range(ti - 3, ti)) + list(range(ti + 1, ti + 4))): continue
        if k[ti] is None: continue
        bk = 'A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'
        dis = prev is not None and ((v - prev[0]) * (k[ti] - prev[1]) < 0)
        ei = ti + 3
        out.append(dict(asset=asset, tf=tf, ti=ti, ei=ei, tdate=b[ti]['d'], edate_open=b[ei]['d'],
                        d0=bar_end(b, ei, tf), entry=c[ei], ct=v, k=k[ti], bk=bk, dis=dis,
                        strong=dis and v < 50, prime=20 <= k[ti] < 50,
                        zexit=bk == 'B' and v < 60 and zmin[ti] is not None and zmin[ti] >= 50,
                        complete_bar=ei + 1 < len(b)))
        prev = (v, k[ti])
    return out, b


_DAY = {}
def daily(asset, clamp=True):
    key = (asset, clamp)
    if key not in _DAY:
        b = load(asset, '1D', clamp)
        _DAY[key] = (b, {x['d']: i for i, x in enumerate(b)})
    return _DAY[key]


def fwd(asset, d0, e, H=60, clamp=True, last_complete=None):
    """Daily candles on days d0+1 .. d0+H. None if any day missing."""
    b, pos = daily(asset, clamp)
    days = []
    for k in range(1, H + 1):
        j = pos.get(d0 + dt.timedelta(days=k))
        if j is None: return None
        days.append((k, b[j]))
    hs = [x['h'] for _, x in days]; ls = [x['l'] for _, x in days]
    mx = max(hs); mn = min(ls)
    kh = next(k for k, x in days if x['h'] == mx)
    kl = next(k for k, x in days if x['l'] == mn)
    pre = [x['l'] for k, x in days if k <= kh]
    first = lambda p: next((k for k, x in days if x['h'] >= e * (1 + p / 100)), None)
    return dict(up=(mx / e - 1) * 100, dd=(mn / e - 1) * 100, ret=(days[-1][1]['c'] / e - 1) * 100,
                dpk=kh, ddday=kl, ddpk=(min(pre) / e - 1) * 100, t10=first(10), t20=first(20),
                closes=[x['c'] for _, x in days], highs=hs, lows=ls,
                lastday=days[-1][1]['d'])


def surv10(m, liq=LIQ):
    return m['up'] >= 10 and m['dd'] > liq


def median(v):
    s = sorted(v); n = len(s)
    if not n: return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quant(v, f):
    s = sorted(v); kk = (len(s) - 1) * f; lo = int(math.floor(kk)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (kk - lo)


def r_half(x, nd=0):
    """Round half away from zero (what a reader expects); Python round() is banker's."""
    q = 10 ** nd
    return math.floor(abs(x) * q + 0.5) / q * (1 if x >= 0 else -1)
