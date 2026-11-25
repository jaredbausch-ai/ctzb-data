"""The live-card divergence note is dated by the CLOSE of the divergence's confirmation bar (24 Nov 2026).

analysis/htfdiv.py confirmed_closes() must give, for every divergence divergences() finds, the last day of its
confirmation bar (the bar's open date plus its length, minus a day, or the day before the next bar when a year-end
bar is short), and leave out one whose bar has not closed.
stack_live's div_after() must keep only a higher chart of the same asset, confirmed after entry and before today.

    python3 tests/test_divergence_dates.py     -> exit 1 if any case fails
"""
import datetime as dt, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'analysis'))
os.chdir(ROOT)
from htfdiv import divergences, confirmed_closes
import engine as E
import stack_live as SL

res = []
def check(name, ok, detail=''):
    res.append(bool(ok)); print(f"  {'PASS' if ok else '*** FAIL ***'}  {name}" + ('' if ok else f'  -- {detail}'))

LEN = {'1D': 1, '2D': 2, '3D': 3, '5D': 5, '8D': 8}
for a in ('ETH', 'BTC'):
    for tf in ('2D', '3D', '5D', '8D'):
        path = f'data/{a}_{tf}.csv'
        dates = E.load(path)['date']
        opens = [c for c, _ in divergences(path, 'k')]
        closes = [c for c, _ in confirmed_closes(path, 'k')]
        # a bar ends LEN-1 days after it opens, or sooner when the next bar starts early (multi-day bars restart each
        # 1 January, so the last bar of a year can be short)
        nxt = {dates[i]: dates[i + 1] for i in range(len(dates) - 1)}
        want = [min(c + dt.timedelta(days=LEN[tf] - 1), nxt[c] - dt.timedelta(days=1)) for c in opens if c in nxt]
        check(f'{a} {tf}: every divergence dated by the last day of its confirmation bar ({len(closes)})', closes == want,
              f'{[str(x) for x in closes[-3:]]} vs {[str(x) for x in want[-3:]]}')

d = dt.date
DVC = {(a, tf): [] for a in ('ETH', 'BTC') for tf in SL.TFS}
DVC[('ETH', '5D')] = [d(2026, 11, 20), d(2026, 11, 26)]
DVC[('ETH', '1D')] = [d(2026, 11, 25)]
DVC[('BTC', '8D')] = [d(2026, 11, 25)]
check('the latest higher-chart divergence after entry', SL.div_after(DVC, 'ETH', '2D', d(2026, 11, 10), d(2026, 11, 27)) == 'ETH 5D 2026-11-26')
check('one before today only (the bar must have closed)', SL.div_after(DVC, 'ETH', '2D', d(2026, 11, 10), d(2026, 11, 26)) == 'ETH 5D 2026-11-20')
check('none on or before the entry day', SL.div_after(DVC, 'ETH', '2D', d(2026, 11, 26), d(2026, 11, 30)) == '')
check('a lower or same chart never counts', SL.div_after(DVC, 'ETH', '5D', d(2026, 11, 10), d(2026, 11, 30)) == '')
check('another asset never counts', SL.div_after(DVC, 'BTC', '2D', d(2026, 11, 10), d(2026, 11, 30)) == 'BTC 8D 2026-11-25')
check('past the 60 days never counts', SL.div_after(DVC, 'ETH', '2D', d(2026, 9, 1), d(2026, 11, 30)) == '')

print(f'\n{sum(res)}/{len(res)} passed')
sys.exit(0 if all(res) else 1)
