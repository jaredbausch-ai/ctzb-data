"""Raw-data consistency for the frozen states: 2D-8D bars = my own bucketing of the daily candles (days within a calendar year,
restart 1 January); datasets/candles_* = the last 70 raw bars; the flash-print clamp list."""
import csv, os, sys, gzip, datetime as dt
from decimal import Decimal as Dc
from adata import Checks
out = []
for st in ('replay_0414', 'current'):
    root = os.path.abspath(f'../a20/{st}'); C = Checks(st)
    for a in ('ETH', 'BTC'):
        rows = list(csv.DictReader(open(f'{root}/data/{a}_1D.csv')))
        day = [(dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date(), *(Dc(r[k]) for k in ('open', 'high', 'low', 'close'))) for r in rows]
        C.add(f'candles {a} 1D', 'last daily bar is the clock date', str(day[-1][0]), {'replay_0414': '2026-11-12', 'current': '2026-11-13'}[st], 'last bar not today')
        C.add(f'candles {a} 1D', 'duplicate or out-of-order days', sum(1 for i in range(1, len(day)) if day[i][0] <= day[i - 1][0]), 0, 'daily order')
        C.add(f'candles {a} 1D', 'bars with high < low or close/open outside the range', sum(1 for d, o, h, l, c in day if h < l or not (l <= o <= h) or not (l <= c <= h)), 0, 'bad bar')
        for tf in (2, 3, 5, 8):
            g = {}
            for d, o, h, l, c in day:
                key = (d.year, (d - dt.date(d.year, 1, 1)).days // tf); g.setdefault(key, []).append((d, o, h, l, c))
            mine = {v[0][0]: (v[0][1], max(x[2] for x in v), min(x[3] for x in v), v[-1][4]) for v in g.values()}
            theirs = {dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date(): tuple(Dc(r[k]) for k in ('open', 'high', 'low', 'close')) for r in csv.DictReader(open(f'{root}/data/{a}_{tf}D.csv'))}
            first = min(theirs)
            mine = {d: v for d, v in mine.items() if d >= first}
            C.add(f'candles {a} {tf}D', 'bar count', len(theirs), len(mine), 'bar bucketing')
            C.add(f'candles {a} {tf}D', 'bars differing from my bucketing of the daily candles', sum(1 for d in mine if theirs.get(d) != mine[d]) + sum(1 for d in theirs if d not in mine), 0, 'bar bucketing')
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            raw = list(csv.DictReader(open(f'{root}/data/{a}_{tf}.csv')))[-70:]
            ds = list(csv.DictReader(open(f'{root}/datasets/candles_{a.lower()}_{tf.lower()}.csv')))
            C.add(f'chart file {a} {tf}', 'rows differing from the last 70 raw bars', sum(1 for x, y in zip(raw, ds) if any(x[k] != y[k] for k in ('time', 'open', 'high', 'low', 'close'))) + abs(len(raw) - len(ds)), 0, 'chart file')
    with gzip.open(f'frozen/checks_{st}_candles.csv.gz', 'wt', newline='') as f: csv.writer(f).writerows(C.rows)
    print(st, C.n(), len(C.bad()), C.bad()[:5])
