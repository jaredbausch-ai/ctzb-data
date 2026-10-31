"""Checks on the one stochdwell survivor, K_FLOOR3_CTDN. 31 Oct 2026.

stochdwell.py's declaration says anything that passes is checked inside the grade
on the ledger before it is called anything but a candidate. K_FLOOR3_CTDN is a
CAUTION lens (SURV10 lower, LIQ30 higher) and by construction a subset of bucket A
(CT < 40 at the trough), so the real question is: inside bucket A, is a K pinned at
the floor for 3+ bars in the 10 bars to the trough worse than bucket A without it?

Checks (the project's standing ones):
  1. by asset (ETH and BTC are one sample for anything date-anchored; reported apart)
  2. by chart, by period, by year -- inside bucket A only
  3. inside the grade, on the graded ledger (grade letter held fixed)
  4. de-duplicated: ETH and BTC signals within 5 days of each other counted once
  5. the near miss D_FLOOR3 (failed only the year rule) shown the same way

Run from the repo root:  python3 -I analysis/stochdwell_check.py
"""
import sys, os, csv, statistics
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stochdwell as S

CUT = S.CUT


def pct(v): return 100 * statistics.mean(v) if v else float('nan')


def table(rows, lens, key, label, minn=1):
    g = defaultdict(lambda: ([], []))
    for r in rows: g[key(r)][0 if r[lens] else 1].append(r)
    print(f'  {label:<10}{"n with":>7}{"SURV":>6}{"LIQ":>5}{"n w/o":>7}{"SURV":>6}{"LIQ":>5}{"diff":>6}')
    for k in sorted(g):
        w, wo = g[k]
        if len(w) < minn: continue
        sw, so = pct([r['surv'] for r in w]), pct([r['surv'] for r in wo])
        print(f'  {str(k):<10}{len(w):>7}{sw:>6.0f}{pct([r["liq"] for r in w]):>5.0f}'
              f'{len(wo):>7}{so:>6.0f}{pct([r["liq"] for r in wo]):>5.0f}{sw - so:>+6.0f}')


def main():
    charts = S.load_charts(S.SYS_TF)
    rows = S.signal_rows(charts)
    A = [r for r in rows if r['bk'] == 'A']
    print(f'Bucket A signals (CT < 40 at the trough): n={len(A)}')
    for lens in ('K_FLOOR3', 'D_FLOOR3'):
        print(f'\n=== {lens} inside bucket A (with = line pinned >= 3 bars in the 10 to the trough) ===')
        table(A, lens, lambda r: 'all', 'pooled')
        table(A, lens, lambda r: r['asset'], 'asset')
        table(A, lens, lambda r: 'old' if r['date'] < CUT else '2022+', 'period')
        table(A, lens, lambda r: r['chart'], 'chart')
        table(A, lens, lambda r: r['date'].year, 'year')
        # de-dup across assets: a with-event on one asset within 5 days of one on the other counts once
        w = sorted([r for r in A if r[lens]], key=lambda r: r['date'])
        keep = []
        for r in w:
            if keep and (r['date'] - keep[-1]['date']).days <= 5 and r['asset'] != keep[-1]['asset']:
                continue
            keep.append(r)
        print(f'  de-duplicated across assets: n with {len(w)} -> {len(keep)}, SURV {pct([r["surv"] for r in keep]):.0f}%'
              f', LIQ {pct([r["liq"] for r in keep]):.0f}%')

    # inside the grade, on the graded ledger
    led = list(csv.DictReader(open('datasets/ledger.csv')))
    idx = {(r['chart'], r['date'].isoformat()): r for r in rows}
    idx.update({(r['chart'], r['end'].isoformat()): r for r in rows if r['end']})
    import datetime as dt
    j = []
    for L in led:
        r = idx.get((L['chart'], L['entry']))
        if r and r['bk'] == 'A':
            j.append(dict(r, grade=L['grade']))
    print(f'\n=== inside the grade (graded ledger, bucket A only, matched {len(j)} of '
          f'{sum(1 for L in led if L["tags"].startswith("A"))} ledger bucket-A rows) ===')
    for lens in ('K_FLOOR3', 'D_FLOOR3'):
        print(f'  {lens}')
        table(j, lens, lambda r: r['grade'], 'grade')


if __name__ == '__main__':
    main()
