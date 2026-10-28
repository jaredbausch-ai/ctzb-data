"""Conviction grade on the dashboard. Runs in the GitHub Action after refresh.py.

The grade is defined and tested in analysis/grade.py (declared 27 Oct 2026; see
docs/PRETRADE.md "Conviction grade"). This script only APPLIES it; it does not
re-choose lenses. The lens list is read from analysis/grade.json.

  Grade = number of the asset's lenses present at entry: C 0-1, B 2, A 3, A+ 4+.
  ETH lenses: GAP (CT > Signal by 5+), HIGH (entry above the previous signal),
  AGREE (2+ other ETH charts confirmed 0-10 days before), BTC3 (BTC 3D
  confirmed 0-10 days before; ETH 1D/2D), FUND (funding at or above its 90-day
  median). BTC lenses: GAP, UP8 (8D CT rising). 8D signals are not graded.

Writes / changes, in datasets/:
  grades.csv     the record of each grade: signals per year, +20% in 60 days
                 with its worst plausible rate, touched -30% / -20%, median dip
                 in 60 days, median dip before the high, the 1-in-4 and 1-in-10
                 dips, median / top-quarter / largest upside. ETH from 2020
                 (where funding exists), BTC full history. Completed 60-day
                 windows only.
  forward.csv    adds `grade` and `lenses` to every row (matched by chart and
                 entry bar).
  live.csv       adds `formingGrade` and `formingLenses`: the grade a forming
                 low would carry if it confirmed now. PROVISIONAL: CT vs its
                 Signal line, price vs the last entry and funding all move
                 until it confirms.
A grade is a historical rate for that kind of setup, not a forecast. Entry
quality only: computed signals, never fills.
"""
import csv, json, math, os, sys, datetime as dt, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'analysis'))
import engine as E
import grokpack as GP
import pcrtest as PT
from sweep import closed_index

OUT = os.path.join(HERE, 'datasets')
LENSES = json.load(open(os.path.join(HERE, 'analysis', 'grade.json')))['lenses']
GRADED_TF = ('1D', '2D', '3D', '5D')


def lens_flags(r):
    return {
        'GAP': r['gap'] is not None and r['gap'] > 5,
        'HIGH': bool(r['higher']),
        'AGREE': r['agree'] >= 2,
        'UP8': bool(r['up8']),
        'BTC3': bool(r['btc3']),
        'FUND': r['fund'] is True,
    }


def grade_of(r):
    if r['tf'] not in GRADED_TF:
        return '', ''
    f = lens_flags(r); have = [k for k in LENSES[r['a']] if f[k]]
    c = len(have)
    return ('C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'), ' + '.join(have)


def wilson_lo(k, n, z=1.96):
    if n == 0: return 0.0
    p = k / n; d = 1 + z * z / n
    return 100 * (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def rcsv(path):
    with open(path) as f:
        rd = csv.reader(f); rows = list(rd)
    return rows[0], rows[1:]


def wcsv(path, header, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def main():
    rows, allsig = GP.build()
    fb = PT.funding_below()
    b3 = [x['d0'] for x in allsig[('BTC', '3D')]]
    last_fund = {a: max((d for (aa, d) in fb if aa == a), default=None) for a in ('ETH', 'BTC')}
    every = [r for lst in allsig.values() for r in lst]
    for r in every:
        if 'agree' not in r:
            r['agree'] = sum(1 for t in GP.TFS if t != r['tf'] and
                             any(0 <= (r['d0'] - x['d0']).days <= 10 for x in allsig[(r['a'], t)]))
        r['btc3'] = r['a'] == 'ETH' and r['tf'] in ('1D', '2D') and any(0 <= (r['d0'] - d).days <= 10 for d in b3)
        v = fb.get((r['a'], r['d0']))
        r['fund'] = None if v is None else (not v)
        r['grade'], r['lensnames'] = grade_of(r)

    # ---- grades.csv: the record of each grade ----
    out = []
    for a in ('ETH', 'BTC'):
        G0 = [r for r in rows if r['a'] == a and r['tf'] in GRADED_TF]
        if 'FUND' in LENSES[a]:
            G0 = [r for r in G0 if r['fund'] is not None]
        for r in G0:
            r['grade'], _ = grade_of(r)
        yrs = max(1, len({r['yr'] for r in G0}))
        for g in ('A+', 'A', 'B', 'C'):
            G = [r for r in G0 if r['grade'] == g]
            n = len(G)
            if not n:
                out.append([a, g, 0, '', '', '', '', '', '', '', '', '', '', '', '', f'{min(r["d0"] for r in G0)} to {max(r["d0"] for r in G0)}']); continue
            k = sum(r['win'] for r in G); dds = sorted(r['m']['dd'] for r in G); ups = sorted(r['m']['up'] for r in G)
            out.append([a, g, n, round(n / yrs, 1), round(100 * k / n), round(wilson_lo(k, n)),
                        round(100 * sum(r['t30'] for r in G) / n), round(100 * sum(r['t20'] for r in G) / n),
                        round(st.median(dds), 1), round(st.median(r['m']['ddpk'] for r in G), 1),
                        round(dds[int(0.25 * (n - 1))], 1), round(dds[int(0.10 * (n - 1))], 1),
                        round(st.median(ups), 1), round(ups[int(0.75 * (n - 1))], 1), round(max(ups), 1),
                        f'{min(r["d0"] for r in G0)} to {max(r["d0"] for r in G0)}'])
    wcsv(os.path.join(OUT, 'grades.csv'),
         ['asset', 'grade', 'n', 'perYear', 'reach20', 'worstPlausible', 'touched30', 'touched20', 'medDip',
          'medDipBeforeHigh', 'dip1in4', 'dip1in10', 'medUpside', 'upsideTopQuarter', 'upsideLargest', 'sample'], out)

    # ---- forward.csv: grade each row ----
    dates = {}
    for (a, tf) in allsig:
        dates[(a, tf)] = E.load(f'data/{a}_{tf}.csv')['date']
    by_key = {}
    for r in every:
        ed = dates[(r['a'], r['tf'])][r['ei']]
        by_key[(r['ch'], str(ed))] = r
    fp = os.path.join(OUT, 'forward.csv')
    if os.path.exists(fp):
        h, rs = rcsv(fp)
        h = [c for c in h if c not in ('grade', 'lenses')]
        rs = [x[:len(h)] for x in rs]
        ci, ei = h.index('chart'), h.index('entry')
        new = []
        for x in rs:
            r = by_key.get((x[ci], x[ei]))
            new.append(x + ([r['grade'], r['lensnames']] if r else ['', 'not matched']))
        wcsv(fp, h + ['grade', 'lenses'], new)

    # ---- live.csv: provisional grade of a forming low ----
    lp = os.path.join(OUT, 'live.csv')
    if os.path.exists(lp):
        h, rs = rcsv(lp)
        h = [c for c in h if c not in ('formingGrade', 'formingLenses')]
        rs = [x[:len(h)] for x in rs]
        today = {}
        new = []
        for x in rs:
            ch = x[h.index('chart')]; a, tf = ch.split()
            if x[h.index('forming')] != 'yes' or tf not in GRADED_TF:
                new.append(x + ['', '']); continue
            b = E.load(f'data/{a}_{tf}.csv'); ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
            i = len(b['close']) - 1; d0 = b['date'][i]
            sig = allsig[(a, tf)]
            prev = sig[-1]['entry'] if sig else None
            b8 = E.load(f'data/{a}_8D.csv'); c8 = E.rsi(b8['close'], 14); k8 = closed_index(b8['date'], d0)
            fu = last_fund[a]
            r = dict(a=a, tf=tf, gap=(ct[i] - em[i]) if ct[i] is not None and em[i] is not None else None,
                     higher=prev is not None and b['close'][i] > prev,
                     up8=k8 >= 1 and c8[k8] is not None and c8[k8 - 1] is not None and c8[k8] > c8[k8 - 1],
                     agree=sum(1 for t in GP.TFS if t != tf and any(0 <= (d0 - y['d0']).days <= 10 for y in allsig[(a, t)])),
                     btc3=a == 'ETH' and tf in ('1D', '2D') and any(0 <= (d0 - d).days <= 10 for d in b3),
                     fund=None if fu is None else (not fb[(a, fu)]))
            g, names = grade_of(r)
            new.append(x + [g + ' (provisional)', names])
        wcsv(lp, h + ['formingGrade', 'formingLenses'], new)
    print('grades.csv written; forward.csv and live.csv graded')


if __name__ == '__main__':
    main()
