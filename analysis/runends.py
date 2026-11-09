"""What ends a long run of losing signals?

Jared's question, 9 Nov 2026. CANDIDATES DECLARED BEFORE RUNNING, all reads
that already exist in the repo:

  1 REGIME   was the gate off during the run and on at the breaker, i.e. do
             long runs simply end when the regime flips?
  2 GRADE    is the run-breaker a better grade than the signals inside the run?
  3 CHART    does a particular timeframe break them?
  4 CTLOW    is the breaker's CT trough lower than the run's median trough?
  5 DDATH    drawdown from the running all-time high at the breaker vs the run
  6 CLOCK    do long runs end after a characteristic number of DAYS, as opposed
             to a number of signals?

SELECTION TRAP, stated up front: the run-breaker is BY DEFINITION a winner, so
any read that merely separates winners from losers will look like it explains
the ending when it explains nothing about timing. Each candidate is therefore
compared against the SAME read measured on all winners, not against the run.
A candidate only means something if the breaker differs from ordinary winners.

Long run = 7 or more consecutive losers (the fat tail; 19% of runs).
Entry quality only.
"""
import csv, os, statistics as st, collections, datetime as dt, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import regimes as R

LONG = 7
rows = list(csv.DictReader(open(os.path.join(ROOT, 'datasets', 'ledger.csv'))))
rows.sort(key=lambda x: (x['entry'], x['chart']))
seq = [x for x in rows if x['reached20'] in ('yes', 'no')]

runs, cur = [], []
for i, x in enumerate(seq):
    if x['reached20'] == 'yes':
        if cur:
            runs.append((cur, x))      # the run, and the signal that broke it
            cur = []
    else:
        cur.append(x)

long_runs = [(r, b) for r, b in runs if len(r) >= LONG]
winners = [x for x in seq if x['reached20'] == 'yes']
breakers = [b for _, b in long_runs]

print(f'closed runs: {len(runs)}   long runs (>={LONG}): {len(long_runs)}')
print(f'all winners: {len(winners)}   long-run breakers: {len(breakers)}\n')

g = R.rsi_regime(os.path.join(ROOT, 'data', 'BTC_2D.csv'), 8, 13, 60, 41)

def num(x, k):
    try: return float(x[k])
    except (ValueError, TypeError, KeyError): return None

print('--- 1 REGIME: was the gate off inside the run and on at the breaker? ---')
flip = 0
for r, b in long_runs:
    on_in_run = sum(1 for x in r if g(dt.date.fromisoformat(x['entry'])))
    on_at_break = g(dt.date.fromisoformat(b['entry']))
    if on_in_run < len(r) and on_at_break: flip += 1
print(f'  the ledger is already gate-on only, so every signal in it has the gate ON.')
print(f'  gate-on at the breaker: {sum(1 for b in breakers if g(dt.date.fromisoformat(b["entry"])))}/{len(breakers)}')
print(f'  -> the gate cannot explain these endings: it never turned off inside them.\n')

print('--- 2 GRADE: breaker vs ordinary winner ---')
def gdist(rs):
    c = collections.Counter(x['grade'] for x in rs)
    n = len(rs)
    return '  '.join(f'{k} {100*c.get(k,0)/n:.0f}%' for k in ('A+','A','B','C'))
print(f'  long-run breakers ({len(breakers)}): {gdist(breakers)}')
print(f'  all winners      ({len(winners)}): {gdist(winners)}')
inside = [x for r, _ in long_runs for x in r]
print(f'  inside long runs ({len(inside)}): {gdist(inside)}\n')

print('--- 3 CHART: which timeframe breaks them? ---')
cb = collections.Counter(b['chart'] for b in breakers)
cw = collections.Counter(x['chart'] for x in winners)
print(f'  {"chart":9} {"breakers":>9} {"share":>7} {"share of all winners":>21}')
for ch in sorted(set(list(cb)+list(cw))):
    print(f'  {ch:9} {cb.get(ch,0):>9} {100*cb.get(ch,0)/len(breakers):>6.0f}% {100*cw.get(ch,0)/len(winners):>20.0f}%')
print()

print('--- 6 CLOCK: how long do long runs last in DAYS? ---')
ds = []
for r, b in long_runs:
    d0 = dt.date.fromisoformat(r[0]['entry']); d1 = dt.date.fromisoformat(b['entry'])
    ds.append((d1 - d0).days)
    print(f'  {r[0]["entry"]} -> {b["entry"]}   {len(r):>3} signals   {(d1-d0).days:>4} days   breaker {b["chart"]} {b["grade"]}')
if ds:
    print(f'\n  days: median {st.median(ds):.0f}   mean {st.mean(ds):.0f}   range {min(ds)}-{max(ds)}')
