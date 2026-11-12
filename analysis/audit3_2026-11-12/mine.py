"""Independent audit code (audit3). Written from the stated definitions only.
Imports regimes.py from the audited state for the gate function, nothing else."""
import csv, datetime as dt, json, math, os, sys, statistics as st
from decimal import Decimal, ROUND_HALF_UP

S = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'
STATES = {'REPLAY': S + '/audit3_replay_0414', 'CURRENT': S + '/audit3_current'}
NOWS = {'REPLAY': dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc),
        'CURRENT': dt.datetime(2026, 11, 12, 15, 9, 9, tzinfo=dt.timezone.utc)}
LIQ_FRAC = 0.253       # liquidation line used by the repo (CARD_SPEC / measures.LIQ)
EPS = 1e-9


def rhaz(x, nd=0):
    """round half away from zero on the exact binary value"""
    q = Decimal(1) if nd == 0 else Decimal(1).scaleb(-nd)
    d = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if nd == 0 else float(d)


def utcd(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def load(root, asset, tf, clamp=False):
    rows = list(csv.DictReader(open(f'{root}/data/{asset}_{tf}.csv')))
    out = []
    for r in rows:
        b = dict(t=int(r['time']), d=utcd(r['time']), o=float(r['open']), h=float(r['high']),
                 l=float(r['low']), c=float(r['close']))
        if clamp:
            lo_b, hi_b = min(b['o'], b['c']), max(b['o'], b['c'])
            if b['l'] < 0.5 * lo_b: b['l'] = lo_b
            if b['h'] > 2 * hi_b: b['h'] = hi_b
        out.append(b)
    return out


def my_rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n: return out
    ups = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    dns = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    au = sum(ups[:n]) / n; ad = sum(dns[:n]) / n
    def val(u, d): return 100.0 if d == 0 else 100 - 100 / (1 + u / d)
    out[n] = val(au, ad)
    for i in range(n + 1, len(c)):
        au = (au * (n - 1) + ups[i - 1]) / n; ad = (ad * (n - 1) + dns[i - 1]) / n
        out[i] = val(au, ad)
    return out


def my_k(ct, n=14, sm=3):
    raw = [None] * len(ct)
    for i in range(len(ct)):
        if i - n + 1 < 0: continue
        w = ct[i - n + 1:i + 1]
        if any(v is None for v in w): continue
        hi, lo = max(w), min(w)
        raw[i] = 0.0 if hi == lo else 100 * (ct[i] - lo) / (hi - lo)
    k = [None] * len(ct)
    for i in range(len(ct)):
        w = raw[max(0, i - sm + 1):i + 1]
        if len(w) == sm and all(v is not None for v in w): k[i] = sum(w) / sm
    return k


def gate_fn(root):
    sys.path.insert(0, root)
    import importlib
    for m in ('regimes', 'engine'):
        if m in sys.modules: del sys.modules[m]
    R = importlib.import_module('regimes')
    g = R.rsi_regime(os.path.join(root, 'data/BTC_2D.csv'), 8, 13, 60, 41)
    sys.path.remove(root)
    return g


def troughs(bars):
    """every pivot low of CT RSI with 3 bars each side, strictly lower; with K at the trough"""
    c = [b['c'] for b in bars]
    ct = my_rsi(c); k = my_k(ct)
    out = []
    for ti in range(3, len(bars) - 3):
        v = ct[ti]
        w = ct[ti - 3:ti + 4]
        if any(x is None for x in w): continue
        if all(ct[j] > v for j in range(ti - 3, ti)) and all(ct[j] > v for j in range(ti + 1, ti + 4)):
            if k[ti] is None: continue
            out.append(dict(ti=ti, ct=v, k=k[ti]))
    return out, ct, k


def signals(bars, gate, gate_on='trough'):
    """gated troughs, tagged. diamond vs previous trough in the chain of ALL troughs (CONTEXT)."""
    T, ct, k = troughs(bars)
    sig = []
    prev = None
    for t in T:
        ti = t['ti']; ei = ti + 3
        gd = bars[ti]['d'] if gate_on == 'trough' else bars[ei]['d']
        dct = dk = None; dis = False
        if prev is not None:
            dct = t['ct'] - prev['ct']; dk = t['k'] - prev['k']
            dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
        bk = 'A' if t['ct'] < 40 else 'B' if t['ct'] < 55 else 'C' if t['ct'] < 65 else 'D'
        s = dict(ti=ti, ei=ei, tdate=bars[ti]['d'], cdate=bars[ei]['d'], ct=t['ct'], k=t['k'], bk=bk, dis=dis,
                 filled=dis and t['ct'] < 50, prime=20 <= t['k'] < 50, entry=bars[ei]['c'], gated=gate(gd),
                 prev=prev, dct=dct, dk=dk, tlow=bars[ti]['l'])
        s['d0'] = bars[ei + 1]['d'] - dt.timedelta(days=1) if ei + 1 < len(bars) else None
        sig.append(s)
        prev = t
    return sig, ct, k


def tagstr(s):
    return ' + '.join([s['bk']] + (['filled diamond'] if s['filled'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))


class Daily:
    def __init__(self, bars):
        self.b = bars; self.pos = {b['d']: i for i, b in enumerate(bars)}


def window(day, d0, entry, now, H=60):
    """daily bars d0+1 .. d0+H; None unless the day-H bar exists and has closed (UTC)."""
    end = d0 + dt.timedelta(days=H)
    if end not in day.pos: return None
    close_time = dt.datetime.combine(end + dt.timedelta(days=1), dt.time(), dt.timezone.utc)
    if close_time > now: return None
    w = [day.b[day.pos[d0 + dt.timedelta(days=k)]] for k in range(1, H + 1) if d0 + dt.timedelta(days=k) in day.pos]
    return w


def metrics(w, d0, entry):
    hs = [b['h'] for b in w]; ls = [b['l'] for b in w]
    mh = max(hs); kp = hs.index(mh); ml = min(ls); kl = ls.index(ml)
    pre = min(ls[:kp + 1])
    liq = entry * (1 - LIQ_FRAC)
    return dict(up=(mh / entry - 1) * 100, dd=(ml / entry - 1) * 100, ddpk=(pre / entry - 1) * 100,
                ret=(w[-1]['c'] / entry - 1) * 100, dpk=(w[kp]['d'] - d0).days, ddday=(w[kl]['d'] - d0).days,
                r10=any(h >= entry * 1.10 for h in hs), r15=any(h >= entry * 1.15 for h in hs),
                r20=any(h >= entry * 1.20 for h in hs), t30=any(l <= entry * 0.70 for l in ls),
                liq=any(l <= liq for l in ls),
                surv10=any(h >= entry * 1.10 for h in hs) and not any(l <= liq for l in ls),
                surv10_25=any(h >= entry * 1.10 for h in hs) and not any(l <= entry * 0.75 for l in ls),
                d10=next(((b['d'] - d0).days for b in w if b['h'] >= entry * 1.10), None),
                d20=next(((b['d'] - d0).days for b in w if b['h'] >= entry * 1.20), None),
                n=len(w))


def funding(root, a):
    f_any, f_mean = {}, {}
    for r in csv.DictReader(open(f'{root}/data/derivs/{a}_funding_daily.csv')):
        d = dt.date.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): f_any[d] = float(v)
        if r.get('funding_mean') not in ('', None): f_mean[d] = float(r['funding_mean'])
    return f_any, f_mean


def eth_funded(fa, fm, d0):
    """ledger eligibility for ETH (grade lenses FUND/FCOOL need data): value on d0 with 60+ of the prior 90
    days, and 5+ of the last 7 days and 5+ of days 14-20 before (funding_mean)."""
    if d0 not in fa: return False
    back = sum(1 for k in range(1, 91) if d0 - dt.timedelta(days=k) in fa)
    if back < 60: return False
    w7 = sum(1 for k in range(7) if d0 - dt.timedelta(days=k) in fm)
    w7b = sum(1 for k in range(7) if d0 - dt.timedelta(days=14 + k) in fm)
    return w7 >= 5 and w7b >= 5


def vol_ratio_fn(root, a):
    b = load(root, a, '1D')
    c = [x['c'] for x in b]
    lr = [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]  # lr[i-1] = return into bar i
    vol = {}
    for i in range(365, len(c)):
        seg = lr[i - 365:i]  # 365 returns ending at bar i
        vol[b[i]['d']] = st.pstdev(seg)
    med = st.median(v for d, v in vol.items() if d.year <= 2021)
    return lambda d: (vol[d] / med) if d in vol else None
