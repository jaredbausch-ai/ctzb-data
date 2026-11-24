"""Statistical exercise (Jared, 24 Nov 2026): a 1D signal that a 2D signal on the same asset then
confirms 1-10 days AFTER. Hindsight by construction when measured from the 1D entry -- not knowable
at entry, not a lens. Also shown from the 2D confirmation day (knowable then).
Population: regime-gated 1D signals (ledger), full 60-day windows. 2D signals: regime-gated, any tag,
and with a diamond. Outcomes on daily candles: +20% / +10% / -30% within 60 days.
ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I analysis/followon2d.py -> analysis/RESULTS_followon2d.txt
"""
import sys, os, csv, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E, regimes as R
from tagstats import bucket_end
G = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41); LAST = dt.date(2026, 9, 10); out = []
def outc(day, pos, d, c0=None):
    i = pos.get(d)
    if i is None or i + 60 >= len(day['date']): return None
    c0 = c0 or day['close'][i]
    hi = max(day['high'][i + 1:i + 61]) / c0 - 1; lo = min(day['low'][i + 1:i + 61]) / c0 - 1
    return hi >= .2, hi >= .1, lo <= -.3
def row(lab, g):
    n = len(g)
    if not n: return f'{lab:<62} n   0'
    return f'{lab:<62} n {n:3d}  +20% {100*sum(x[0] for x in g)/n:3.0f}%  +10% {100*sum(x[1] for x in g)/n:3.0f}%  -30% {100*sum(x[2] for x in g)/n:3.0f}%'
for a in ('ETH', 'BTC'):
    day = E.load(f'data/{a}_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}
    s2, b2 = E.signals(f'data/{a}_2D.csv', regime=G)
    two = [(bucket_end(b2['date'], s['ei']), s['dis']) for s in s2]; two = [x for x in two if x[0]]
    led = [x for x in csv.DictReader(open('datasets/ledger.csv')) if x['chart'] == f'{a} 1D' and dt.date.fromisoformat(x['entry']) <= LAST]
    groups = {}
    for x in led:
        d0 = dt.date.fromisoformat(x['entry']); o = outc(day, pos, d0)
        if o is None: continue
        after = [d for d, dis in two if 1 <= (d - d0).days <= 10]
        afterd = [d for d, dis in two if 1 <= (d - d0).days <= 10 and dis]
        isAd = x['tags'].startswith('A') and 'filled diamond' in x['tags']; isA = x['tags'].startswith('A')
        for key, cond in (('all', True), ('bucket A', isA), ('A + filled diamond', isAd)):
            if not cond: continue
            groups.setdefault((key, 'no 2D after'), []).append(o) if not after else None
            if after: groups.setdefault((key, '2D confirmed 1-10d after'), []).append(o)
            if afterd: groups.setdefault((key, '2D with a diamond 1-10d after'), []).append(o)
            if after:
                o2 = outc(day, pos, after[0])
                if o2: groups.setdefault((key, 'FROM THE 2D CONFIRM DAY (knowable then)'), []).append(o2)
    out.append(f'== {a} 1D signals (regime-gated), outcomes from the 1D entry unless marked')
    for key in ('all', 'bucket A', 'A + filled diamond'):
        for sub in ('no 2D after', '2D confirmed 1-10d after', '2D with a diamond 1-10d after', 'FROM THE 2D CONFIRM DAY (knowable then)'):
            out.append(row(f'{key}: {sub}', groups.get((key, sub), [])))
out.append('Hindsight: "after" is not knowable at the 1D entry. ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
open(os.path.join(HERE, 'RESULTS_followon2d.txt'), 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
