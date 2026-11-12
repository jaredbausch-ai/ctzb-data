"""Build my own model of one state: candles, signals, ledger, measures. Own code; regimes.py for the gate only."""
import csv, datetime as dt, importlib, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa

SP = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/a7'


def gate_for(state_dir):
    # regimes.py imported for the gate only
    sys.path.insert(0, state_dir)
    for m in ('regimes', 'engine'):
        sys.modules.pop(m, None)
    R = importlib.import_module('regimes')
    g = R.rsi_regime(os.path.join(state_dir, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
    sys.path.pop(0)
    return g


def funding(state_dir, a):
    f_any, f_mean = {}, {}
    for r in csv.DictReader(open(os.path.join(state_dir, 'data', 'derivs', f'{a}_funding_daily.csv'))):
        d = dt.date.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): f_any[d] = float(v)
        if r.get('funding_mean') not in ('', None): f_mean[d] = float(r['funding_mean'])
    return f_any, f_mean


def eth_member(fa, fm, d0):
    """ETH ledger membership (funding data exists for the FUND and FCOOL reads at entry)"""
    if d0 not in fa: return False
    back = [fa.get(d0 - dt.timedelta(days=k)) for k in range(1, 91)]
    if sum(v is not None for v in back) < 60: return False
    w7 = sum((d0 - dt.timedelta(days=k)) in fm for k in range(7))
    w7b = sum((d0 - dt.timedelta(days=14 + k)) in fm for k in range(7))
    return w7 >= 5 and w7b >= 5


class State:
    def __init__(self, name, clock):
        self.name = name; self.dir = os.path.join(SP, name)
        self.clock = clock; self.today = clock.date()
        self.day = {a: Daily(os.path.join(self.dir, 'data', f'{a}_1D.csv')) for a in ('ETH', 'BTC')}
        self.ch = {(a, tf): Chart(self.day[a], tf) for a in ('ETH', 'BTC') for tf in TFS}
        self.gate = gate_for(self.dir)
        self.vol = {a: Vol(self.day[a]) for a in ('ETH', 'BTC')}
        self.sig = {k: signals(c, self.gate, self.today) for k, c in self.ch.items()}
        for (a, tf), lst in self.sig.items():
            for s in lst:
                s['a'] = a; s['tf'] = tf; s['chart'] = f'{a} {tf}'
                s['dclose'] = self.day[a].C[self.day[a].pos[s['d0']]] if s['d0'] in self.day[a].pos else None
                s['m'] = measure(self.day[a], s['d0'], s['entry'], self.today)
        self.fund = {a: funding(self.dir, a) for a in ('ETH', 'BTC')}
        # my ledger: graded charts, 60th day closed, ETH only where funding reads exist
        self.led = []
        for a in ('ETH', 'BTC'):
            for tf in GRADED:
                for s in self.sig[(a, tf)]:
                    if s['m'] is None: continue
                    if a == 'ETH' and not eth_member(*self.fund['ETH'], s['d0']): continue
                    self.led.append(s)
        self.led.sort(key=lambda s: (s['d0'], s['tf']))
        self.ledkey = {(s['chart'], str(s['d0'])): s for s in self.led}

    def csv(self, name):
        return list(csv.DictReader(open(os.path.join(self.dir, 'datasets', name))))

    def feed(self):
        return json.load(open(os.path.join(self.dir, 'feed', 'ctzb_feed.json')))
