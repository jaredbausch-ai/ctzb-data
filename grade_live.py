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
  dipdist.csv    every graded signal's largest dip from entry within 60 days, so
                 the console can show the share of past setups that reached a
                 given liquidation point (sizing basis set by Jared 28 Oct: the
                 median drawdown from entry).
  grades.csv     the record of each grade (worstTenthMedian = the median dip
                 among the worst 10% of that grade's signals, the "worst-case
                 median" the dashboard sizes against, at Jared's request 28 Oct):
                 signals per year, +20% in 60 days
                 with its worst plausible rate, touched -30% / -20%, median dip
                 in 60 days, median dip before the high, the 1-in-4 and 1-in-10
                 dips, median / top-quarter / largest upside. ETH from 2020
                 (where funding exists), BTC full history. Completed 60-day
                 windows only.
  forward.csv    adds `grade` and `lenses` to every row (matched by chart and
                 entry bar).
  (liveread.csv, prints.csv and windows.csv come from stack_live.py, which
   runs next and checks every documented read.)
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
from htfdiv import divergences
ORDER = ('1D', '2D', '3D', '5D', '8D')

OUT = os.path.join(HERE, 'datasets')
LENSES = json.load(open(os.path.join(HERE, 'analysis', 'grade.json')))['lenses']
# Addendum (analysis/grade2.py, 27 Oct 2026): BTCX passed every step and its
# placebo, so it joins the BTC grade (BTC can now reach A). DIVH (bullish Stoch
# divergence on a higher chart, ETH) also passed, but folded into the count it
# put ETH grade A below B in 2022-26, so it is shown as a separate flag next to
# the grade, with its own record, not counted as a star.
ADD = json.load(open(os.path.join(HERE, 'analysis', 'grade2.json')))
for _a, _ks in ADD.items():
    LENSES[_a] = LENSES[_a] + [k for k in _ks if k != 'DIVH']
# Audit (analysis/grade3.py, 28 Oct 2026): FCOOL (funding not cooling) counted
# on ETH; MARKER (diamond or prime dot) passed but is a flag, not a star.
AUD = json.load(open(os.path.join(HERE, 'analysis', 'grade3.json')))
for _a, _ks in AUD['counted'].items():
    LENSES[_a] = LENSES[_a] + _ks
FLAGS = {'DIVH': 'HTF divergence', 'MARKER': 'diamond or prime dot'}
GRADED_TF = ('1D', '2D', '3D', '5D')


def lens_flags(r):
    return {
        'GAP': r['gap'] is not None and r['gap'] > 5,
        'HIGH': bool(r['higher']),
        'AGREE': r['agree'] >= 2,
        'UP8': bool(r['up8']),
        'BTC3': bool(r['btc3']),
        'FUND': r['fund'] is True,
        'BTCX': bool(r.get('btcx')),
        'FCOOL': bool(r.get('fcool')),
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
    e2 = [x['d0'] for x in allsig[('ETH', '2D')]]
    DV = {(a, tf): [d for d, _ in divergences(f'data/{a}_{tf}.csv', osc='k')] for a in ('ETH', 'BTC') for tf in ORDER}

    from grade3 import funding_series
    FS = {a: funding_series(a) for a in ('ETH', 'BTC')}

    def flags_at(a, tf, d0):
        near = lambda lst: any(0 <= (d0 - d).days <= 10 for d in lst)
        f = FS[a]
        w7 = [f[d0 - dt.timedelta(days=k)] for k in range(7) if d0 - dt.timedelta(days=k) in f]
        w7b = [f[d0 - dt.timedelta(days=14 + k)] for k in range(7) if d0 - dt.timedelta(days=14 + k) in f]
        ok = len(w7) >= 5 and len(w7b) >= 5
        return dict(btcx=a == 'BTC' and tf in ('1D', '2D') and near(e2),
                    divh=any(near(DV[(a, t)]) for t in ORDER[ORDER.index(tf) + 1:]),
                    fcool_ok=ok, fcool=ok and sum(w7) / len(w7) >= sum(w7b) / len(w7b))
    every = [r for lst in allsig.values() for r in lst]
    for r in rows:
        r.update(flags_at(r['a'], r['tf'], r['d0']))
    for r in every:
        r.update(flags_at(r['a'], r['tf'], r['d0']))
        if 'agree' not in r:
            r['agree'] = sum(1 for t in GP.TFS if t != r['tf'] and
                             any(0 <= (r['d0'] - x['d0']).days <= 10 for x in allsig[(r['a'], t)]))
        r['btc3'] = r['a'] == 'ETH' and r['tf'] in ('1D', '2D') and any(0 <= (r['d0'] - d).days <= 10 for d in b3)
        v = fb.get((r['a'], r['d0']))
        r['fund'] = None if v is None else (not v)
        r['grade'], r['lensnames'] = grade_of(r)

    def extra(G):
        n = len(G); pk = sorted(r['m']['ddpk'] for r in G)
        return [round(100 * sum(r['m']['up'] >= 10 for r in G) / n), round(100 * sum(r['m']['up'] >= 30 for r in G) / n),
                round(100 * sum(bool(r.get('safe')) for r in G) / n), round(100 * sum(r['m']['ret'] > 0 for r in G) / n),
                round(pk[int(0.10 * (n - 1))], 1), round(st.median(r['m']['dpk'] for r in G))]

    # ---- grades.csv: the record of each grade ----
    out = []
    dist = []      # dipdist.csv: every graded signal's largest 60-day dip from entry, for the console's liquidation odds
    for a in ('ETH', 'BTC'):
        G0 = [r for r in rows if r['a'] == a and r['tf'] in GRADED_TF]
        if 'FUND' in LENSES[a]:
            G0 = [r for r in G0 if r['fund'] is not None]
        if 'FCOOL' in LENSES[a]:
            G0 = [r for r in G0 if r['fcool_ok']]
        for r in G0:
            r['grade'], _ = grade_of(r)
            dist.append([a, r['grade'], round(r['m']['dd'], 2)])
        yrs = max(1, len({r['yr'] for r in G0}))
        for g in ('A+', 'A', 'B', 'C'):
            G = [r for r in G0 if r['grade'] == g]
            n = len(G)
            if not n:
                out.append([a, g, 0, '', '', '', '', '', '', '', '', '', '', '', '', f'{min(r["d0"] for r in G0)} to {max(r["d0"] for r in G0)}', '', '', '', '', '', '', '', '']); continue
            k = sum(r['win'] for r in G); dds = sorted(r['m']['dd'] for r in G); ups = sorted(r['m']['up'] for r in G)
            out.append([a, g, n, round(n / yrs, 1), round(100 * k / n), round(wilson_lo(k, n)),
                        round(100 * sum(r['t30'] for r in G) / n), round(100 * sum(r['t20'] for r in G) / n),
                        round(st.median(dds), 1), round(st.median(r['m']['ddpk'] for r in G), 1),
                        round(dds[int(0.25 * (n - 1))], 1), round(dds[int(0.10 * (n - 1))], 1),
                        round(st.median(ups), 1), round(ups[int(0.75 * (n - 1))], 1), round(max(ups), 1),
                        f'{min(r["d0"] for r in G0)} to {max(r["d0"] for r in G0)}', round(dds[0], 1),
                        round(st.median(dds[:max(1, round(0.10 * n))]), 1)] + extra(G))
    G0 = [r for r in rows if r['a'] == 'ETH' and r['tf'] in GRADED_TF and r['fund'] is not None and r['fcool_ok']]
    yrs = max(1, len({r['yr'] for r in G0}))
    for r in rows: r['marker'] = bool(r['prime'] or r['dis'])
    for lab, sel in (('HTF divergence', lambda r: r['divh']), ('no HTF divergence', lambda r: not r['divh']),
                     ('diamond or prime dot', lambda r: r['marker']), ('no diamond or prime dot', lambda r: not r['marker'])):
        G = [r for r in G0 if sel(r)]; n = len(G)
        if not n: continue
        k = sum(r['win'] for r in G); dds = sorted(r['m']['dd'] for r in G); ups = sorted(r['m']['up'] for r in G)
        out.append(['ETH', lab, n, round(n / yrs, 1), round(100 * k / n), round(wilson_lo(k, n)),
                    round(100 * sum(r['t30'] for r in G) / n), round(100 * sum(r['t20'] for r in G) / n),
                    round(st.median(dds), 1), round(st.median(r['m']['ddpk'] for r in G), 1),
                    round(dds[int(0.25 * (n - 1))], 1), round(dds[int(0.10 * (n - 1))], 1),
                    round(st.median(ups), 1), round(ups[int(0.75 * (n - 1))], 1), round(max(ups), 1),
                    f'{min(r["d0"] for r in G0)} to {max(r["d0"] for r in G0)}', round(dds[0], 1),
                    round(st.median(dds[:max(1, round(0.10 * n))]), 1)] + extra(G))
    wcsv(os.path.join(OUT, 'grades.csv'),
         ['asset', 'grade', 'n', 'perYear', 'reach20', 'worstPlausible', 'touched30', 'touched20', 'medDip',
          'medDipBeforeHigh', 'dip1in4', 'dip1in10', 'medUpside', 'upsideTopQuarter', 'upsideLargest', 'sample', 'worstDip', 'worstTenthMedian',
          'reach10', 'reach30', 'safe20', 'green60', 'dipBeforeHigh1in10', 'daysToHigh'], out)
    wcsv(os.path.join(OUT, 'dipdist.csv'), ['asset', 'grade', 'maxDip60'], dist)

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
        h = [c for c in h if c not in ('grade', 'lenses', 'htfDiv', 'marker')]
        rs = [x[:len(h)] for x in rs]
        ci, ei = h.index('chart'), h.index('entry')
        new = []
        for x in rs:
            r = by_key.get((x[ci], x[ei]))
            dv = ('yes' if r['divh'] else 'no') if (r and r['a'] == 'ETH') else ''
            mk = ('yes' if (r['prime'] or r['dis']) else 'no') if (r and r['a'] == 'ETH') else ''
            new.append(x + ([r['grade'], r['lensnames'], dv, mk] if r else ['', 'not matched', '', '']))
        wcsv(fp, h + ['grade', 'lenses', 'htfDiv', 'marker'], new)

    # ---- live.csv: provisional grade of a forming low ----
    lp = os.path.join(OUT, 'live.csv')
    forming_now = []
    if os.path.exists(lp):
        h, rs = rcsv(lp)
        h = [c for c in h if c not in ('formingGrade', 'formingLenses', 'formingHtfDiv', 'formingMarker', 'closeNow', 'closeDate')]
        rs = [x[:len(h)] for x in rs]
        today = {}
        new = []
        for x in rs:
            ch = x[h.index('chart')]; a, tf = ch.split()
            if x[h.index('forming')] != 'yes' or tf not in GRADED_TF:
                new.append(x + ['', '', '', '']); continue
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
            r.update(flags_at(a, tf, d0))
            g, names = grade_of(r)
            r['_grade'], r['_names'] = g, [k for k in names.split(' + ') if k]
            ft = x[h.index('formingTag')].lower()
            mk = ('yes' if ('diamond' in ft or 'prime' in ft) else 'no') if a == 'ETH' else ''
            new.append(x + [g + ' (provisional)', names, ('yes' if r['divh'] else 'no') if a == 'ETH' else '', mk])
            forming_now.append((a, tf, d0, r, x[h.index('formingTag')]))
        dd1 = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
        new = [x + [round(dd1[x[0].split()[0]]['close'][-1], 2), str(dd1[x[0].split()[0]]['date'][-1])] for x in new]
        wcsv(lp, h + ['formingGrade', 'formingLenses', 'formingHtfDiv', 'formingMarker', 'closeNow', 'closeDate'], new)

    # liveread.csv moved to stack_live.py (28 Oct 2026): the whole registry, every run.
    print('grades.csv written; forward.csv and live.csv graded')


if __name__ == '__main__':
    main()
