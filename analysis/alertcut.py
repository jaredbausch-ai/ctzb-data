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

# --- Alerts per year for the recommended set (ETH A+, BTC A+, BTC A), 5 Nov 2026 ---
# Raw = every chart's signal. Merged = one trade per asset, a new one only when
# 10+ days have passed since the last kept entry on that asset (the same market
# low often fires on several charts in one week). 2020-2025 is the window where
# both assets are graded; 2022 had no regime-on signals.
import datetime as dt
from collections import Counter
keep = {('ETH', 'A+'), ('BTC', 'A+'), ('BTC', 'A')}
rows = sorted((r for r in csv.DictReader(open('datasets/ledger.csv'))
               if (r['asset'], r['grade']) in keep and r['surv10'] in ('yes', 'no')),
              key=lambda r: r['entry'])
last, merged = {}, []
for r in rows:
    d = dt.date.fromisoformat(r['entry'])
    if r['asset'] not in last or (d - last[r['asset']]).days >= 10:
        merged.append(r)
        last[r['asset']] = d
raw_c = Counter(int(r['entry'][:4]) for r in rows)
mer_c = Counter(int(r['entry'][:4]) for r in merged)
print('\nyear raw merged10d')
for y in range(2016, 2026):
    print(y, raw_c.get(y, 0), mer_c.get(y, 0))
yrs = range(2020, 2026)
print('avg 2020-2025 raw', round(sum(raw_c.get(y, 0) for y in yrs) / 6, 1),
      'merged', round(sum(mer_c.get(y, 0) for y in yrs) / 6, 1))
