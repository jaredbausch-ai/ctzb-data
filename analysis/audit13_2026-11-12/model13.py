"""Audit 13: build my own model of everything for one state (signals, ledger, cards, extras)."""
import csv, datetime as dt, json, os, sys, statistics, importlib.util
from lib13 import *

HERE = os.path.dirname(os.path.abspath(__file__))
A13 = os.path.join(os.path.dirname(HERE), 'a13')
GRADED = ('1D', '2D', '3D', '5D')
ASSETS = ('ETH', 'BTC')


def state_dir(st):
    return os.path.join(A13, st)


def get_gate(S):
    # regimes.py imported for the gate only (it uses the state's engine.load for the BTC 2D closes)
    cwd = os.getcwd()
    sys.path.insert(0, S)
    for m in ('regimes', 'engine'):
        sys.modules.pop(m, None)
    import regimes as R
    g = R.rsi_regime(os.path.join(S, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
    sys.path.remove(S)
    return g


class Model:
    def __init__(self, st, now):
        self.st = st
        self.S = state_dir(st)
        self.now = now                       # aware datetime
        self.today = now.date()
        self.gate = get_gate(self.S)
        self.day = {a: Daily(os.path.join(self.S, 'data', f'{a}_1D.csv')) for a in ASSETS}
        self.vol = {a: Vol(self.day[a]) for a in ASSETS}
        self.bars = {}
        self.sig = {}
        self.piv = {}
        for a in ASSETS:
            for tf in ('1D', '2D', '3D', '5D', '8D'):
                b = load(os.path.join(self.S, 'data', f'{a}_{tf}.csv'))
                self.bars[(a, tf)] = b
                s, pv, ct, K = signals(b, tf, self.gate)
                self.sig[(a, tf)] = s
                self.piv[(a, tf)] = (pv, ct, K)
        # measures for every signal
        for (a, tf), lst in self.sig.items():
            for s in lst:
                s['a'] = a; s['tf'] = tf; s['chart'] = f'{a} {tf}'
                s['m'] = measure(self.day[a], s['d0'], s['entry'], self.today)
                r = self.vol[a].ratio(s['d0'])
                s['vr'] = r
                if s['m']:
                    s['sc'] = None if r is None else ((s['m']['hi'] / s['entry'] - 1) * 100 >= 20 * r)

    # ---- ledger membership: graded charts, 60 days closed
    def closed_signals(self):
        return [s for (a, tf), lst in self.sig.items() if tf in GRADED for s in lst if s['m']]

    def path60(self, a, d0, e):
        """(high, low) of each daily bar in the 60 calendar days after d0 (all closed, for sample signals)."""
        ks = self.day[a].window(d0, 60)
        return [(self.day[a].b['h'][k], self.day[a].b['l'][k]) for k in ks]
