"""Audit 15 -- extra checks: the worked example's chart file against the raw candles, the gate re-derived
with my own RSI (cross-check only; the audit uses regimes.rsi_regime as instructed), next_buy_date.
Usage: python3 extra_checks.py <state dir> <name>"""
import sys, json, csv, datetime as dt
from fractions import Fraction as Fr
from decimal import Decimal
from core import *
S, NAME = sys.argv[1], sys.argv[2]
now, feed = now_of(S); W = World(S, now); C = Checks(NAME)
# 1. example chart file
ex = json.load(open(f'{S}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
raw = {dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date(): r for r in csv.DictReader(open(f'{S}/data/ETH_2D.csv'))}
C.add('example chart file', 'chart', ex['chart'], 'ETH 2D'); C.add('example chart file', 'signal_id', ex['signal_id'], 'ETH-2D-2024-09-22')
eb = ex['bars'][ex['entry_index']]; ed = dt.datetime.fromtimestamp(eb['t'], dt.timezone.utc).date()
C.add('example chart file', 'entry_index is the bar that closes on 2024-09-22', str(bucket_span(ed, 2)[1]), '2024-09-22')
s = next(x for x in W.sig[('ETH', '2D')] if str(x['d0']) == '2024-09-22')
C.add('example chart file', 'entry_close', ex['entry_close'], s['entry'])
prev = None
for i, b in enumerate(ex['bars']):
    d = dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date(); r = raw.get(d)
    C.add('example chart file', f'bar {i} ({d}) exists in the raw 2D candles', 'yes' if r else 'no', 'yes')
    if not r: continue
    for k, kk in (('o', 'open'), ('h', 'high'), ('l', 'low'), ('c', 'close')):
        C.add('example chart file', f'bar {i} ({d}) {kk}', b[k], Fr(Decimal(r[kk])))
    if prev is not None: C.add('example chart file', f'bar {i} follows bar {i - 1} with no gap', str(d), str(bucket_span(prev, 2)[1] + dt.timedelta(days=1)))
    prev = d
last = dt.datetime.fromtimestamp(ex['bars'][-1]['t'], dt.timezone.utc).date()
C.add('example chart file', 'bars reach day 60 after entry', 'yes' if bucket_span(last, 2)[1] >= dt.date(2024, 11, 21) else 'no', 'yes')
C.add('example chart file', 'bars after the entry bar (page reads 30 two-day bars to day 60)', 'at least 30' if len(ex['bars']) - 1 - ex['entry_index'] >= 30 else 'fewer', 'at least 30')
# 2. the gate, re-derived
b = Candles(f'{S}/data/BTC_2D.csv')
import math
ct = wilder_rsi([float(Decimal(r['close'])) for r in csv.DictReader(open(f'{S}/data/BTC_2D.csv'))])
state = False; up = dn = 0; mine = {}
for d, v in zip(b.date, ct):
    if v is not None:
        up = up + 1 if v >= 60 else 0; dn = dn + 1 if v < 41 else 0
        if not state and up >= 8: state = True; dn = 0
        elif state and dn >= 13: state = False; up = 0
    mine[d] = state
diff = [d for d in b.date if W.gate(d) != mine[d]]
C.add('regime gate', 'regimes.rsi_regime(BTC_2D, 8, 13, 60, 41) equals my own state machine on every BTC 2D bar (bars that differ)', len(diff), 0)
flips = []; prevs = None
d = dt.date(2025, 1, 1)
while d <= W.today:
    g = W.gate(d)
    if prevs is not None and g != prevs: flips.append(f"{'on' if g else 'off'} from {d}")
    prevs = g; d += dt.timedelta(days=1)
if W.today >= dt.date(2026, 9, 3):
    C.add('regime gate', 'CONTEXT: "on to 2025-12-04, off 2025-12-05 to 2026-09-01, on again from 2026-09-02"', '; '.join(flips), 'off from 2025-12-05; on from 2026-09-02')
print(len(C.rows), [x[1:5] for x in C.rows if x[5] == 'NO'])
csv.writer(open(f'checks_extra_{NAME}.csv', 'w', newline='')).writerows(C.rows)
