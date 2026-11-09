"""Median statistics for every A+ signal, and how they decay over time.

Asked for by Jared, 9 Nov 2026: medians only, drawdown from entry and high
from entry, split per asset and over time to show diminishing returns.

Reads datasets/ledger.csv (the graded record). Entry quality only: there is no
exit in the data, so none of these are strategy returns.
"""
import csv, statistics as st, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = [x for x in csv.DictReader(open(os.path.join(ROOT, 'datasets', 'ledger.csv')))
     if x['grade'] == 'A+']

def num(x, k):
    try: return float(x[k])
    except (ValueError, KeyError, TypeError): return None

def med(rows, k):
    v = [num(x, k) for x in rows]; v = [y for y in v if y is not None]
    return st.median(v) if v else None

def rate(rows, k):
    v = [x[k] for x in rows if x.get(k) in ('yes', 'no')]
    return 100 * sum(1 for y in v if y == 'yes') / len(v) if v else None

COLS = [('bestMove', 'high'), ('maxDrawdown', 'drawdown'),
        ('dipBeforeHigh', 'dip b/4 hi'), ('return60d', '60d ret')]

def line(lab, rows):
    if not rows: return
    cells = ' '.join(f'{med(rows,k):>+9.1f}%' for k, _ in COLS)
    print(f'{lab:22} {len(rows):>4} {cells} {rate(rows,"reached20"):>7.0f}% '
          f'{rate(rows,"touched30"):>7.0f}% {med(rows,"daysToHigh"):>6.0f}')

def head():
    print(f'{"":22} {"n":>4} ' + ' '.join(f'{n:>10}' for _, n in COLS) +
          f' {"+20%":>8} {"-30%":>8} {"d2hi":>6}')

if __name__ == '__main__':
    print(f'A+ signals, n={len(R)}\n')
    head(); line('ALL', R); print()
    for a in ('ETH', 'BTC'):
        line(a, [x for x in R if x['asset'] == a])
    print('\n--- by year ---'); head()
    for y in sorted({x['entry'][:4] for x in R}):
        line(y, [x for x in R if x['entry'][:4] == y])
    print('\n--- by era, per asset ---'); head()
    for a in ('ETH', 'BTC'):
        for lab, lo, hi in (('2016-2021', '2016', '2021'), ('2022-2026', '2022', '2026')):
            line(f'{a} {lab}', [x for x in R if x['asset'] == a and lo <= x['entry'][:4] <= hi])
