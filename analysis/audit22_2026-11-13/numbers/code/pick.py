"""Declare the replay list (group B) before running it. Writes plan.json: [{date, clock, kinds}]"""
import json, sys, random, datetime as dt, csv
J = json.load(open(sys.argv[1]))
led = list(csv.DictReader(open(sys.argv[2])))
D = dt.date.fromisoformat
random.seed(22)
LAST = D('2026-11-12')
plan = {}


def add(d, kind, clock=None):
    if isinstance(d, dt.date):
        d = str(d)
    if D(d) < D('2020-09-01') or D(d) > LAST:
        return
    k = (d, clock)
    plan.setdefault(k, set()).add(kind)


gate = J['gate']
# filter episodes: first/last day and either side
flips = [D(s) for g, s, e in J['episodes'][1:]]
for F in flips:
    for k in (-2, -1, 0, 1):
        add(F + dt.timedelta(days=k), 'filter flip edge')
# every date within a forming low's reach of a filter flip
for d, pv in J['prov'].items():
    for p in pv:
        if gate.get(p['tdate'], None) is not None and gate[p['tdate']] != gate[d]:
            add(d, 'forming low across a filter flip')
# 40 filter-off dates
off = sorted(d for d, g in gate.items() if not g and D(d) >= D('2020-09-01'))
for d in sorted(random.sample(off, 40)):
    add(d, 'filter off')
# year-ends
for y in range(2020, 2026):
    for k in range(10):
        add(D(f'{y}-12-26') + dt.timedelta(days=k), 'year-end')
# top-grade forming lows: A+ ledger signals since Sep 2020, the date the confirmation bar opens (and the day before)
aplus = [r for r in led if r['grade'] == 'A+' and D(r['entry']) >= D('2020-09-05')]
random.shuffle(aplus)
n = 0
for r in aplus:
    d0 = D(r['entry']); ch = r['chart']
    cand = [d for d, pv in J['prov'].items() if any(p['chart'] == ch and p['tdate'] == r['low'] for p in pv)]
    if not cand:
        continue
    add(random.choice(cand), 'top-grade forming low (candidate)')
    n += 1
    if n >= 48:
        break
# quiet days
quiet = sorted(d for d in J['prov'] if not J['prov'][d] and not J['open'][d])
for d in random.sample(quiet, min(12, len(quiet))):
    add(d, 'nothing live or forming')
# 20 signals: day 60 in progress and the day after it closes
sigs = [s for s in J['sigs'] if D(s['d0']) + dt.timedelta(days=61) <= LAST]
for s in random.sample(sigs, 20):
    add(D(s['d0']) + dt.timedelta(days=60), 'day 60 in progress')
    add(D(s['d0']) + dt.timedelta(days=61), 'day after day 60 closed')
# days just after a confirmation
for s in random.sample(sigs, 15):
    add(D(s['d0']) + dt.timedelta(days=1), 'day after a confirmation')
# other clock times
times = ['00:00:30', '00:13:00', '01:07:00', '03:59:00', '06:30:00', '08:13:00', '11:45:00', '12:13:00', '15:00:00', '16:13:00',
         '18:20:00', '20:13:00', '22:40:00', '23:30:00', '23:59:00']
pool = sorted({k[0] for k in plan})
for t in times:
    d = random.choice(pool)
    add(d, 'other clock time', f'{d}T{t}Z')
# fails closed: clock on D+1, candles end on D
for d in random.sample(pool, 5):
    add(d, 'fail closed (clock D+1)', f'{D(d) + dt.timedelta(days=1)}T00:10:00Z')
out = [dict(date=d, clock=c, kinds=sorted(k)) for (d, c), k in sorted(plan.items(), key=lambda x: (x[0][0], x[0][1] or ""))]
json.dump(out, open(sys.argv[3], 'w'), indent=0)
from collections import Counter
cnt = Counter(k for x in out for k in x['kinds'])
print(len(out), 'replays'); [print(f'  {k}: {v}') for k, v in sorted(cnt.items())]
