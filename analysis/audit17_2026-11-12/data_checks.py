"""Audit 17 stage 1: the raw candle files themselves, and the files the page draws from.
usage: data_checks.py <state root> <now ISO> <state name> <out csv>"""
import csv, datetime as dt, json, os, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C

root, now, name, out = sys.argv[1:5]
now = dt.datetime.fromisoformat(now.replace('Z', '+00:00')); today = now.date()
L = C.Log(name)
raw = {(a, tf): C.Chart(os.path.join(root, 'data', f'{a}_{tf}.csv'), clamp=False) for a in C.ASSETS for tf in C.TFS}
for a in C.ASSETS:
    d = raw[(a, '1D')]
    L.chk(f'data {a}_1D', 'bar opens are 00:00 UTC', all(t % 86400 == 0 for t in d.t), True)
    gaps = [f'{d.d[i-1]}..{d.d[i]}' for i in range(1, d.n) if (d.d[i] - d.d[i - 1]).days != 1]
    L.chk(f'data {a}_1D', 'dates strictly increasing; gaps (only the known 2016-05-21/22 ETH gap, before any signal)', ' '.join(gaps), {'ETH': '2016-05-20..2016-05-23'}.get(a, ''))
    L.chk(f'data {a}_1D', 'high >= max(open, close) and low <= min(open, close) on every bar', all(d.h[i] >= max(d.o[i], d.c[i]) and d.l[i] <= min(d.o[i], d.c[i]) for i in range(d.n)), True)
    L.chk(f'data {a}_1D', 'last bar is today (UTC) or yesterday', (today - d.d[-1]).days in (0, 1), True, f'last bar {d.d[-1]}, today {today}')
    L.chk(f'data {a}_1D', 'every price has at most 2 decimals', all((x * 100).denominator == 1 for i in range(d.n) for x in (d.o[i], d.h[i], d.l[i], d.c[i])), True)
    cl = C.Chart(os.path.join(root, 'data', f'{a}_1D.csv')).clamped
    L.chk(f'data {a}_1D', 'flash-print clamps (documented: one 2017 bar per asset)', '; '.join(f'{x[0]} {x[1]}' for x in cl), {'ETH': '2017-06-21 low', 'BTC': '2017-04-15 low'}.get(a), 'clamp list')
    for tf in C.TFS[1:]:
        c = raw[(a, tf)]; bad = 0; n = C.tfdays(tf)
        groups = {}
        for i, x in enumerate(d.d):
            groups.setdefault((x.year, (x - dt.date(x.year, 1, 1)).days // n), []).append(i)
        exp = []
        for k in sorted(groups):
            ix = groups[k]
            exp.append((d.d[ix[0]], d.o[ix[0]], max(d.h[i] for i in ix), min(d.l[i] for i in ix), d.c[ix[-1]]))
        exp = [e for e in exp if e[0] >= c.d[0]]
        got = [(c.d[i], c.o[i], c.h[i], c.l[i], c.c[i]) for i in range(c.n)]
        L.chk(f'data {a}_{tf}', f'bar count equals the 1D file bucketed within each calendar year', len(got), len(exp))
        bad = [str(g[0]) for g, e in zip(got, exp) if g != e]
        L.chk(f'data {a}_{tf}', 'every bar (open date, o, h, l, c) equals its days of the 1D file', ' '.join(bad[:5]), '', 'multi-day bar differs from the daily candles')
        L.chk(f'data {a}_{tf}', 'last bar contains the last daily bar', C.bar_open_of(d.d[-1], tf), c.d[-1])
    # 4H cross-check (information): daily high/low/close rebuilt from the 4H file
    p4 = os.path.join(root, 'data', f'{a}_4H.csv')
    if os.path.exists(p4):
        g = {}
        for r in csv.DictReader(open(p4)):
            g.setdefault(C.utc_date(r['time']), []).append(r)
        full = [x for x in d.d[:-1] if x in g and len(g[x]) == 6]
        hi = sum(1 for x in full if max(F(r['high']) for r in g[x]) != d.h[d.pos[x]])
        lo = sum(1 for x in full if min(F(r['low']) for r in g[x]) != d.l[d.pos[x]])
        clz = sum(1 for x in full if F(g[x][-1]['close']) != d.c[d.pos[x]])
        L.chk(f'data {a}_4H', f'closed days with 6 four-hour bars: daily high / low / close that differ from the 1D file', f'{hi}/{lo}/{clz} of {len(full)}', f'0/0/0 of {len(full)}', '4H and 1D candles disagree')
    # the page's candle files: the last 70 bars of each chart
    for tf in C.TFS:
        p = os.path.join(root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        rows = list(csv.DictReader(open(p))) if os.path.exists(p) else None
        src = raw[(a, tf)].raw[-70:]
        L.chk(f'datasets candles_{a.lower()}_{tf.lower()}', 'equals the last 70 bars of the data file', rows is not None and [[r[k] for k in ('time', 'open', 'high', 'low', 'close')] for r in rows] == [[r[k] for k in ('time', 'open', 'high', 'low', 'close')] for r in src], True)
# the worked example's chart file
ex = json.load(open(os.path.join(root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')), parse_float=lambda s: F(s))
c = raw[('ETH', '2D')]
ok = True; idx = []
for b in ex['bars']:
    i = c.pos.get(C.utc_date(b['t']))
    idx.append(i)
    if i is None or (F(str(b['o'])), F(str(b['h'])), F(str(b['l'])), F(str(b['c']))) != (c.o[i], c.h[i], c.l[i], c.c[i]): ok = False
L.chk('example json', 'every bar equals the ETH 2D data file', ok, True)
E_ = ex['entry_index']
L.chk('example json', 'entry_index is the bar that closes on 2024-09-22', str(C.next_open(c.d[idx[E_]], '2D') - dt.timedelta(days=1)), '2024-09-22')
L.chk('example json', 'entry_close is that bar close', ex['entry_close'], c.c[idx[E_]])
L.chk('example json', 'bars are consecutive', all(idx[i] == idx[0] + i for i in range(len(idx))), True)
L.chk('example json', 'bars after entry cover day 60 (30 two-day bars)', len(idx) - 1 - E_ >= 30, True, f'{len(idx)-1-E_} bars after entry')
L.chk('example json', 'signal_id', ex['signal_id'], 'ETH-2D-2024-09-22')
# gate history as CONTEXT states it
sys.path.insert(0, root)
import regimes
ok_, days = regimes.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41, ret_series=True)
flips = [(days[i], ok_[days[i]]) for i in range(1, len(days)) if ok_[days[i]] != ok_[days[i - 1]]]
rec = [f"{d}:{'on' if v else 'off'}" for d, v in flips if d >= dt.date(2025, 1, 1)]
L.chk('gate', 'CONTEXT: "on to 2025-12-04, off 2025-12-05 to 2026-09-01, on again from 2026-09-02" (2D bar open dates of the flips since 2025)', ' '.join(rec), '2025-12-05:off 2026-09-02:on', 'gate history differs from CONTEXT')
with open(out, 'w', newline='') as f:
    csv.writer(f).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + L.rows)
print(name, len(L.rows), 'data checks,', len(L.bad()), 'disagreements')
for r in L.rows:
    if r[5] != 'ok': print('  ', r[1], '|', r[2], '|', r[3], '|', r[4], '|', r[5])
