"""Raw-candle integrity on the frozen states: 2D-8D bars rebuild exactly from the daily candles by the calendar-year
bucket rule (1 January restart), served candle files = last 70 raw bars, no missing recent day, flash clamps."""
import csv, datetime as dt
from common import *
for name in ('REPLAY', 'CURRENT'):
    root = STATES[name][0]; C = Checks(name)
    for a in ('ETH', 'BTC'):
        rows = list(csv.DictReader(open(f'{root}/data/{a}_1D.csv')))
        days = [(L.udate(float(r['time'])), r) for r in rows]
        gaps = [(str(days[i - 1][0]), str(days[i][0])) for i in range(1, len(days)) if (days[i][0] - days[i - 1][0]).days != 1]
        C.add(f'data/{a}_1D.csv', 'missing days since 2017', [g for g in gaps if g[0] >= '2017'], [], group='0 raw candles')
        for tf in (2, 3, 5, 8):
            groups = {}
            for d, r in days: groups.setdefault((d.year, (d - dt.date(d.year, 1, 1)).days // tf), []).append((d, r))
            mine = {}
            for key in sorted(groups):
                g = groups[key]
                mine[g[0][0]] = (float(g[0][1]['open']), max(float(r['high']) for _, r in g), min(float(r['low']) for _, r in g), float(g[-1][1]['close']))
            theirs = {L.udate(float(r['time'])): (float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in csv.DictReader(open(f'{root}/data/{a}_{tf}D.csv'))}
            C.add(f'data/{a}_{tf}D.csv', 'bar open dates = calendar-year buckets of the daily candles', sorted(theirs) == sorted(mine), True, group='0 raw candles')
            for d in sorted(mine):
                C.add(f'data/{a}_{tf}D.csv {d}', 'open/high/low/close rebuilt from daily candles', theirs.get(d), mine[d], group='0 raw candles')
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            raw = [(int(float(r['time'])), float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in csv.DictReader(open(f'{root}/data/{a}_{tf}.csv'))][-70:]
            srv = [(int(float(r['time'])), float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in csv.DictReader(open(f'{root}/datasets/candles_{a.lower()}_{tf.lower()}.csv'))]
            C.add(f'datasets/candles_{a.lower()}_{tf.lower()}.csv', 'served chart candles = last 70 raw bars', srv == raw, True, group='0 raw candles')
        b = L.Bars(f'{root}/data/{a}_1D.csv')
        C.add(f'data/{a}_1D.csv', 'flash-print clamps', [(str(d), k) for d, k, _, _ in b.clamps], [('2017-06-21', 'low')] if a == 'ETH' else [('2017-04-15', 'low')], group='0 raw candles')
    C.save(f'checks_raw_{name}.csv'); print(name, len(C.rows), len(C.bad())); [print('  BAD', r['location'], r['label'], r['shown'], r['yours']) for r in C.bad()[:10]]
