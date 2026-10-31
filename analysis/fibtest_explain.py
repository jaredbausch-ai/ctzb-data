"""What R4_BROKE@180 actually is. 31 Oct 2026. Characterisation of the fibtest survivor, not a new search.

R4_BROKE@180 = the signal low is under L0, the low the prior 180-day swing started from.
When the 180-day high sits near the start of the window, L0 is just the low of the first
few bars, so "broke" then means "price has fallen below where it was ~6 months ago".
This prints how often that degenerate case occurs and compares the lens with two plain
readings: (a) the signal low is the lowest low of the past 180 days, (b) the signal low is
under the low of the bar 180 days earlier.

Run from the repo root:  python3 -I analysis/fibtest_explain.py
"""
import sys, os, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, stochdwell as S, fibtest as F

def pct(v): return 100 * statistics.mean(v) if v else float('nan')

rows = []
for ch in S.load_charts(S.SYS_TF):
    sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=S.GATE)
    d, lo, hi = ch.b['date'], ch.b['low'], ch.b['high']
    for s in sig:
        ti, ei = s['ti'], s['ei']; o = ch.outcome(ei)
        if o is None: continue
        start = d[ti] - dt.timedelta(days=180)
        js = [j for j in range(max(0, ti - 400), ti) if d[j] >= start]
        if len(js) < 3: continue
        h = max(js, key=lambda j: hi[j]); L0 = min(lo[j] for j in js if j <= h)
        broke = lo[ti] < L0
        early = (d[h] - start).days <= 20
        low180 = lo[ti] <= min(lo[j] for j in js)
        under_start = lo[ti] < lo[js[0]]
        rows.append(dict(o, broke=broke, early=early, low180=low180, under_start=under_start, asset=ch.sym))

def show(name, f):
    w = [r for r in rows if f(r)]; wo = [r for r in rows if not f(r)]
    print(f'  {name:<48}{len(w):>5}{pct([r["surv"] for r in w]):>6.0f}{pct([r["liq"] for r in w]):>5.0f}'
          f'{len(wo):>6}{pct([r["surv"] for r in wo]):>6.0f}{pct([r["liq"] for r in wo]):>5.0f}'
          f'{pct([r["surv"] for r in w]) - pct([r["surv"] for r in wo]):>+6.0f}')

print(f'  {"reading":<48}{"n":>5}{"SURV":>6}{"LIQ":>5}{"n w/o":>6}{"SURV":>6}{"LIQ":>5}{"diff":>6}')
show('R4_BROKE@180 (the lens)', lambda r: r['broke'])
show('  of which: 180d high in the first 20 days', lambda r: r['broke'] and r['early'])
show('  of which: 180d high later (a real swing)', lambda r: r['broke'] and not r['early'])
show('signal low = lowest low of the past 180 days', lambda r: r['low180'])
show('signal low under the low of the bar 180d earlier', lambda r: r['under_start'])
