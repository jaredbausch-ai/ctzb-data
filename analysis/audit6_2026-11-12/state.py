"""Build my independent view of one frozen state: signals, measures, ledger expectation."""
import csv, datetime as dt, json, os, sys, statistics
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *  # noqa

SP = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/a6'
STATES = {'REPLAY': (f'{SP}/replay_0414', dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc)),
          'CURRENT': (f'{SP}/current', None)}


def load_gate(root):
    cwd = os.getcwd()
    sys.path.insert(0, root)
    import importlib
    for m in ('regimes', 'engine'):
        sys.modules.pop(m, None)
    R = importlib.import_module('regimes')
    g = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)
    sys.path.remove(root)
    return g


def funding(root, a):
    f = {}
    for r in csv.DictReader(open(os.path.join(root, 'data', 'derivs', f'{a}_funding_daily.csv'))):
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None):
            f[dt.date.fromisoformat(r['date'])] = float(v)
    fm = {}
    for r in csv.DictReader(open(os.path.join(root, 'data', 'derivs', f'{a}_funding_daily.csv'))):
        v = r.get('funding_mean')
        if v not in ('', None):
            fm[dt.date.fromisoformat(r['date'])] = float(v)
    return f, fm


def eth_funding_ok(f, fm, d):
    """The ETH sample's data-availability rule as written in grade_live.py (funding vs 90-day median
    computable on the entry date; 5+ of 7 days in both funding-cooling windows)."""
    back = [f.get(d - dt.timedelta(days=k)) for k in range(1, 91)]
    if d not in f or len([v for v in back if v is not None]) < 60:
        return False
    w7 = [d - dt.timedelta(days=k) for k in range(7) if d - dt.timedelta(days=k) in fm]
    w7b = [d - dt.timedelta(days=14 + k) for k in range(7) if d - dt.timedelta(days=14 + k) in fm]
    return len(w7) >= 5 and len(w7b) >= 5


class State:
    def __init__(self, name):
        self.name = name
        self.root, clk = STATES[name]
        feed = json.load(open(os.path.join(self.root, 'feed', 'ctzb_feed.json')))
        self.feed = feed
        self.now = clk or dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
        self.today = self.now.date()
        self.gate = load_gate(self.root)
        self.A = {a: Asset(self.root, a, self.today) for a in ('ETH', 'BTC')}
        self.vol = {a: Vol(self.A[a]) for a in self.A}
        self.sig = {}
        self.ct = {}
        for a in self.A:
            for tf in TFS:
                s, ct, K = signals(self.A[a], tf, self.gate)
                self.sig[(a, tf)] = s
                self.ct[(a, tf)] = (ct, K)
        self.fund = {a: funding(self.root, a) for a in self.A}
        # measures for every confirmed signal
        for (a, tf), lst in self.sig.items():
            for s in lst:
                s['m'] = measures(self.A[a], s['d0'], s['entry']) if s['confirmed'] else None
                s['sc'] = None
                if s['m'] is not None:
                    r = self.vol[a].ratio(s['d0'])
                    s['sc'] = None if r is None else (s['m']['up'] >= 20 * r)
        self.ledger = list(csv.DictReader(open(os.path.join(self.root, 'datasets', 'ledger.csv'))))

    def expected_ledger(self):
        out = []
        for a in ('ETH', 'BTC'):
            f, fm = self.fund[a]
            for tf in GRADED:
                for s in self.sig[(a, tf)]:
                    if s['m'] is None:
                        continue
                    if a == 'ETH' and not eth_funding_ok(f, fm, s['d0']):
                        continue
                    out.append(s)
        return out
