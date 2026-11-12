"""Compute every audited figure independently for one state. python3 mine.py <state_dir> <now ISO>"""
import csv, datetime as dt, json, os, sys, statistics as stt, math
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D'); GRADED = ('1D', '2D', '3D', '5D')
SPLIT = dt.date(2022, 1, 1)


class State:
    def __init__(self, path, now):
        self.path = path; self.now = now
        self.gate = load_gate(path)
        self.day = {a: Bars(f'{path}/data/{a}_1D.csv') for a in ASSETS}
        self.bars = {(a, tf): (self.day[a] if tf == '1D' else Bars(f'{path}/data/{a}_{tf}.csv')) for a in ASSETS for tf in TFS}
        self.sig = {}
        for k, b in self.bars.items():
            s, ct, kk = signals(b, self.gate)
            self.sig[k] = s
        self.ledger = list(csv.DictReader(open(f'{path}/datasets/ledger.csv')))
        self.feed = json.load(open(f'{path}/feed/ctzb_feed.json'))
        self._vol = {}

    # ---- funding availability (ETH sample restriction; data reading only) ----
    def funding(self, a):
        fb, fm = {}, {}
        for r in csv.DictReader(open(f'{self.path}/data/derivs/{a}_funding_daily.csv')):
            v = r.get('funding_oi_weighted') or r.get('funding_mean')
            d = dt.date.fromisoformat(r['date'])
            if v not in ('', None): fb[d] = float(v)
            if r.get('funding_mean') not in ('', None): fm[d] = float(r['funding_mean'])
        return fb, fm

    def eth_available(self, d0):
        if not hasattr(self, '_fund'):
            self._fund = self.funding('ETH')
        fb, fm = self._fund
        if d0 not in fb: return False
        back = [fb.get(d0 - dt.timedelta(days=k)) for k in range(1, 91)]
        if len([v for v in back if v is not None]) < 60: return False
        w7 = [d0 - dt.timedelta(days=k) for k in range(7) if d0 - dt.timedelta(days=k) in fm]
        w7b = [d0 - dt.timedelta(days=14 + k) for k in range(7) if d0 - dt.timedelta(days=14 + k) in fm]
        return len(w7) >= 5 and len(w7b) >= 5

    # ---- volatility-scaled +20% ----
    def volratio(self, a, d0):
        if a not in self._vol:
            c = self.day[a].cf
            lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
            vol = {self.day[a].date[i]: stt.pstdev(lr[i - 364:i + 1]) for i in range(365, len(c))}
            med = stt.median(v for k, v in vol.items() if k.year <= 2021)
            self._vol[a] = (vol, med)
        vol, med = self._vol[a]
        v = vol.get(d0)
        return None if v is None else v / med

    def measured(self, a, s, now=None, by=None):
        """Measures for a signal whose 60th day has closed by `now` (or by date `by`)."""
        day = self.day[a]
        w = window(day, s['d0'], now or self.now)
        if w is None: return None
        m = measure(day, s['d0'], s['entry'], w)
        r = self.volratio(a, s['d0'])
        m['scaled20'] = None if r is None else (float(m['up']) >= 20 * r)
        m['w'] = w
        return m


def all_rows(S):
    """Every gated signal on every chart with its measures when closed."""
    out = []
    for (a, tf), lst in S.sig.items():
        for s in lst:
            if s['d0'] is None: continue
            # the entry close must be the daily close on the entry date
            dpos = S.day[a].pos.get(s['d0'])
            s['daily_close_match'] = dpos is not None and S.day[a].c[dpos] == s['entry']
            s['a'] = a; s['tf'] = tf; s['chart'] = f'{a} {tf}'
            s['m'] = S.measured(a, s)
            out.append(s)
    return out


if __name__ == '__main__':
    st_dir, now = sys.argv[1], dt.datetime.fromisoformat(sys.argv[2].replace('Z', '+00:00'))
    S = State(st_dir, now)
    rows = all_rows(S)
    print(len(rows), sum(1 for r in rows if r['m']))
    print('clamps', {a: S.day[a].clamped for a in ASSETS})
    print('entry != daily close', [(r['chart'], r['d0']) for r in rows if not r['daily_close_match']][:20])
