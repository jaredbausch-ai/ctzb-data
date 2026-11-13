"""Find quiet days (no forming low on any of the 10 charts and no signal inside its 60 days) with my own code."""
import sys, os, csv, datetime as dt
from fractions import Fraction as Fr
from decimal import Decimal as Dc
import alib as A
root = os.path.abspath('base')
sys.path.insert(0, root); import regimes as R
os.chdir(root); gate = R.rsi_regime(os.path.join(root, 'data', 'BTC_2D.csv'), 8, 13, 60, 41); os.chdir('..')
daily = {}
for a in A.ASSETS:
    daily[a] = [(dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date(), float(r['close'])) for r in csv.DictReader(open(f'{root}/data/{a}_1D.csv'))]
# full-history signals for "open" test
W = A.World(root, dt.datetime(2026, 11, 13, 4, tzinfo=dt.timezone.utc))
d0s = sorted(s['d0'] for k, v in W.sig.items() if k[1] in A.GRADED for s in v if s['d0'])
def forming_any(day):
    out = []
    for a in A.ASSETS:
        rows = [(d, c) for d, c in daily[a] if d <= day]
        for tf in (1, 2, 3, 5, 8):
            closes = {}
            for d, c in rows:
                key = (d.year, (d - dt.date(d.year, 1, 1)).days // tf); closes[key] = c
            cs = [closes[k] for k in sorted(closes)]
            ct = A.rsi14(cs); n = len(cs)
            for back in (1, 2, 3):
                ti = n - 1 - back; v = ct[ti]
                if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)) or any(ct[j] < v for j in range(ti + 1, n)): continue
                out.append(f'{a} {tf}D'); break
    return out
quiet = []
d = dt.date(2020, 9, 1)
while d <= dt.date(2026, 11, 12):
    if not any(0 <= (d - x).days <= 60 for x in d0s):
        f = forming_any(d)
        if not f: quiet.append(str(d))
    d += dt.timedelta(days=1)
print(len(quiet), quiet)
