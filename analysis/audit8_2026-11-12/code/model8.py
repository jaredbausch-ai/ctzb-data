"""My own expected values for everything the page shows (no feed numbers used except texts given as lens/grade)."""
import sys, json, pickle
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from cards8 import *
from fmt8 import *

EXD = dt.date(2024, 9, 22)


def misses_of(G):
    M = [x for x in G if not x['m']['r10']]
    if not M: return None
    return dict(signals=len(G), misses=len(M), up_first=sum(x['m']['up'] > 0 for x in M), median_peak=med([x['m']['up'] for x in M]),
                median_worst=med([x['m']['dd'] for x in M]), median_day60=med([x['m']['ret'] for x in M]))


def ladder_rows(G):
    M = [x['m'] for x in G]; n = len(M)
    base = F(sum(m['l0'] == 'ok' for m in M), n)
    rows = []
    for th in (5, 10, 15, 20):
        hits = [m['lad'][th] for m in M if m['lad'][th] is not None]
        rows.append(dict(fell=th, n=len(hits), v=F(sum(h[1] == 'ok' for h in hits), len(hits)) if hits else None))
    return base, rows


def edge_of(G):
    """(edge, exact-based) and (edge, rounded-based): 0 = below bar from entry; -X = first fall below bar; None = holds."""
    base, rows = ladder_rows(G)
    out = {}
    for mode in ('exact', 'rounded'):
        b = base * 100 if mode == 'exact' else rhaz(base * 100)
        if b < 70: out[mode] = 0; continue
        e = None
        for r in rows:
            if r['v'] is None: continue
            v = r['v'] * 100 if mode == 'exact' else rhaz(r['v'] * 100)
            if v < 70: e = -r['fell']; break
        out[mode] = e
    return out, base, rows


class State:
    def __init__(self, st):
        self.st = st
        self.L = ledger_with_grades(st)
        self.S = all_signals(st)
        self.feed = json.load(open(STATES[st] + '/feed/ctzb_feed.json'))
        self.today = TODAY[st]

    def group(self, a, g, known_by=None):
        return [x for x in self.L.values() if x['asset'] == a and x['grade'] == g and (known_by is None or x['d0'] + dt.timedelta(days=60) <= known_by)]

    def open_sigs(self):
        out = []
        for a in ('ETH', 'BTC'):
            for tf in ('1D', '2D', '3D', '5D'):
                for s in self.S[(a, tf)]['tr']:
                    if s['gated'] and s['closed'] and 0 <= (self.today - s['d0']).days <= 60:
                        w = window(self.st, a, s['d0']); E = s['entry']
                        s = dict(s, days=(self.today - s['d0']).days,
                                 best=(max(x['h'] for d, x in w) / E - 1) * 100 if w else None,
                                 worst=(min(x['l'] for d, x in w) / E - 1) * 100 if w else None,
                                 day10=next(((x['c'] / E - 1) * 100 for d, x in w if d == 10), None))
                        out.append(s)
        return out

    def card_model(self, c, kind):
        """kind: forming/open/example. c = the feed card (only grade/confirmations/chart are taken from it)."""
        a, tf = c['asset'], c['timeframe']; chart = f'{a} {tf}'
        lenses = frozenset() if c['confirmations'] == 'none' else frozenset(PLAIN[x] for x in c['confirmations'].split('; '))
        kb = EXD if kind == 'example' else None
        basis, G = choose(self.L, chart, a, tf, c['grade'], lenses, known_by=kb)
        f = figures(self.st, G)
        mu, mp, md = f['_exact']
        ed, base, rows = edge_of(G)
        m = dict(asset=a, tf=tf, chart=chart, grade=c['grade'], basis=basis, G=G, f=f, mu=mu, mp=mp, md=md, edge=ed, base=base, rows=rows)
        if kind == 'example':
            sig = self.L[('ETH 2D', '2024-09-22')]
            m.update(entry=sig['entry'], d0=sig['d0'], sig=sig, mi=misses_of(self.group('ETH', 'A+', EXD)))
        elif kind == 'open':
            d0 = dt.date.fromisoformat(c['confirms_on'])
            sig = next(s for s in self.open_sigs() if s['asset'] == a and s['tf'] == tf and s['d0'] == d0)
            m.update(entry=sig['entry'], d0=d0, sig=sig, mi=misses_of(self.group(a, c['grade'])))
        else:
            p = provisional(self.st, a, tf)
            bars = self.S[(a, tf)]['bars']
            cd = conf_close_day(bars, p['ti'], tf)
            kc = kill_close(self.st, a, tf, p)
            m.update(entry=bars[-1]['c'], d0=cd, p=p, kill=None if kc is None else rhaz(F(kc), 2),
                     low_day=dt.date.fromisoformat(low_day(self.st, a, tf, p['tdate'])), tdate=p['tdate'],
                     mi=misses_of(self.group(a, c['grade'])))
        return m
