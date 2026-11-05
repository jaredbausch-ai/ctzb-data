"""Which grades are sellable as alerts? (5 Nov 2026, Jared's question.)

Reads datasets/ledger.csv (graded signals, regime-gated, entry = confirmation
close). For each asset x grade, splits by entry year (before 2022 / since 2022)
and reports the card's big number (surv10: rose 10% and never fell 25.3% within
60 days), scaled20 (beat a normal move) and reached20 (+20% in 60 days).
Descriptive only: no new filter, no threshold fitted. Entry quality only;
not a track record. Output: analysis/RESULTS_alertcut.txt
"""
import csv
from collections import defaultdict

d = defaultdict(lambda: [0, 0, 0, 0])
for r in csv.DictReader(open('datasets/ledger.csv')):
    if r['surv10'] not in ('yes', 'no'):
        continue
    p = 'before2022' if int(r['year']) < 2022 else 'since2022'
    for k in [(r['asset'], r['grade'], p), (r['asset'], r['grade'], 'all')]:
        x = d[k]
        x[0] += 1
        x[1] += r['surv10'] == 'yes'
        x[2] += r['scaled20'] == 'yes'
        x[3] += r['reached20'] == 'yes'
print('asset grade period n surv10% scaled20% reached20%')
for k in sorted(d):
    n, s, sc, r20 = d[k]
    print(*k, n, round(100 * s / n), round(100 * sc / n), round(100 * r20 / n))
