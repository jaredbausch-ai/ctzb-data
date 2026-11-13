"""Choose the replay dates (declared before running). Writes dates.json: list of {date, clock, kinds}."""
import sys, os, json, random, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mycalc import *

base, scanf, out = sys.argv[1:4]
now = dt.datetime(2026, 11, 13, 15, 45, 32, tzinfo=dt.timezone.utc)
S = State(base, now)
scan = {x['date']: x for x in json.load(open(scanf))}
rng = random.Random(23)
START, END = dt.date(2020, 9, 1), dt.date(2026, 11, 13)
P = {}


def add(d, kind, clock=None):
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    if not (START <= d <= END):
        return
    key = (str(d), clock)
    P.setdefault(key, set()).add(kind)


days = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]
# (1) 40 dates with the market filter off
off = [d for d in days if not scan[str(d)]['gate']]
for d in sorted(rng.sample(off, 40)):
    add(d, 'filter off')
# (2) first and last day of every filter episode and the days either side
flips = [d for d in days[1:] if scan[str(d)]['gate'] != scan[str(d - ONE_DAY)]['gate']]
for f in flips:
    for k in (-2, -1, 0, 1):
        add(f + dt.timedelta(days=k), 'filter episode edge')
# (3) year-ends, 26 Dec to 4 Jan, every year
for y in range(2020, 2026):
    for k in range(10):
        add(dt.date(y, 12, 26) + dt.timedelta(days=k), 'year-end')
# signals (mine, hindsight) with the pipeline's grade where the ledger has one
graded = [s for a in ASSETS for tf in GRADED for s in S.ch[(a, tf)].sig if s['d0'] and s['d0'] >= START]
gr = {(s['ch'], s['d0']): s['grade'] for s in S.led}
aplus = [s for s in graded if gr.get((s['ch'], s['d0'])) == 'A+']
# (4) top-grade forming lows: the confirmation day itself and the day before (grade decided by the pipeline then)
for s in sorted(rng.sample(aplus, min(30, len(aplus))), key=lambda s: s['d0']):
    add(s['d0'], 'top-grade forming (candidate)')
    add(s['d0'] - ONE_DAY, 'top-grade forming (candidate)')
# (5) nothing live or forming on any chart
def open_on(d):
    return [s for s in graded if 0 <= (d - s['d0']).days <= 60]
quiet = [d for d in days if not scan[str(d)]['forming'] and not open_on(d)]
for d in quiet[:: max(1, len(quiet) // 12)][:12]:
    add(d, 'nothing live or forming')
# (6) 20 signals: day 60 in progress and the day after it closes
fin = lambda L: [s for s in L if s['d0'] + dt.timedelta(days=61) <= END]
pool = sorted(rng.sample(fin(aplus), 14) + rng.sample(fin([s for s in graded if s not in aplus]), 6), key=lambda s: s['d0'])
for s in pool:
    add(s['d0'] + dt.timedelta(days=60), 'day 60 in progress')
    add(s['d0'] + dt.timedelta(days=61), 'day after day 60 closes')
# (7) days just after a confirmation
for s in sorted(rng.sample(aplus, 15), key=lambda s: s['d0']):
    add(s['d0'] + ONE_DAY, 'day after a confirmation')
# (8) other clock times of day
clocks = ['00:00:30', '00:05:00', '00:20:00', '01:00:00', '03:59:59', '06:30:00', '12:00:00', '16:13:00', '20:43:00', '23:59:00']
for c, d in zip(clocks, sorted(rng.sample([d for d in days if scan[str(d)]['forming']], len(clocks)))):
    add(d, f'clock {c}', f'{d}T{c}Z')
# (9) every date within a forming low's reach of a filter flip (a forming low whose trough's filter reading differs from today's)
for d in days:
    if any(f['gate_trough'] != scan[str(d)]['gate'] for f in scan[str(d)]['forming']):
        add(d, 'forming low across a filter flip')
L = [dict(date=k[0], clock=k[1], kinds=sorted(v)) for k, v in sorted(P.items(), key=lambda kv: (kv[0][0], kv[0][1] or ""))]
json.dump(L, open(out, 'w'), indent=0)
import collections
print(len(L), 'replays'); print(collections.Counter(x for r in L for x in r['kinds']))
print('flips', [str(f) for f in flips])
