# Audit 15: raw candle integrity (my own code). Usage: python3 rawcheck.py <state dir>
import csv, sys, datetime as dt
from decimal import Decimal as D
S = sys.argv[1]
def rd(p):
    out = []
    for r in csv.DictReader(open(p)):
        d = dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc)
        out.append((d, r['open'], r['high'], r['low'], r['close']))
    return out
for a in ('ETH', 'BTC'):
    d1 = rd(f'{S}/data/{a}_1D.csv')
    dates = [x[0].date() for x in d1]
    assert all(x[0].hour == 0 and x[0].minute == 0 for x in d1)
    gaps = [(dates[i-1], dates[i]) for i in range(1, len(dates)) if (dates[i]-dates[i-1]).days != 1]
    print(a, '1D bars', len(d1), dates[0], dates[-1], 'gaps', gaps)
    maxdec = max(len(v.split('.')[1]) if '.' in v else 0 for x in d1 for v in x[1:])
    print('  max decimals', maxdec, [x for x in d1 if any(('.' in v and len(v.split('.')[1]) > 2) for v in x[1:])][:5])
    bad = [(x[0].date(), x[1:]) for x in d1 if not (D(x[3]) <= min(D(x[1]), D(x[4])) and D(x[2]) >= max(D(x[1]), D(x[4])))]
    print('  ohlc inconsistent', bad[:5])
    fl = [(x[0].date(), x[1:]) for x in d1 if D(x[3]) < D('0.5')*min(D(x[1]), D(x[4])) or D(x[2]) > 2*max(D(x[1]), D(x[4]))]
    print('  flash', fl)
    by = {x[0].date(): x for x in d1}
    for tf in (2, 3, 5, 8):
        g = {}
        for d in dates:
            g.setdefault((d.year, (d - dt.date(d.year, 1, 1)).days // tf), []).append(d)
        mine = []
        for k in sorted(g):
            ds = g[k]
            mine.append((ds[0], D(by[ds[0]][1]), max(D(by[x][2]) for x in ds), min(D(by[x][3]) for x in ds), D(by[ds[-1]][4])))
        theirs = [(x[0].date(), D(x[1]), D(x[2]), D(x[3]), D(x[4])) for x in rd(f'{S}/data/{a}_{tf}D.csv')]
        diff = [(m, t) for m, t in zip(mine, theirs) if m != t]
        print(f'  {tf}D bars mine {len(mine)} file {len(theirs)} mismatches {len(diff)}', diff[:3])
        fl = [x for x in theirs if x[3] < D('0.5')*min(x[1], x[4]) or x[2] > 2*max(x[1], x[4])]
        print('    flash', fl)
    # datasets candles = last 70 bars
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        src = list(csv.DictReader(open(f'{S}/data/{a}_{tf}.csv')))[-70:]
        dst = list(csv.DictReader(open(f'{S}/datasets/candles_{a.lower()}_{tf.lower()}.csv')))
        ok = len(src) == len(dst) and all(all(s[k] == t[k] for k in ('time', 'open', 'high', 'low', 'close')) for s, t in zip(src, dst))
        print(f'    candles_{a.lower()}_{tf.lower()}.csv == last 70 raw bars: {ok}')
