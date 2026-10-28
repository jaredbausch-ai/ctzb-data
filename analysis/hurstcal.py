"""Fine-tuning the Hurst cycle-low projection to modern crypto, without fitting
the past. DECLARED 27 Oct 2026 23:00 ET, before running. Follows hurstlow.py,
which found 160D projections land a median 0.33 period LATE relative to the real
low (the low comes early) and 80D 0.15-0.27 late. A consistent bias is
correctable; the question is whether a correction made only from the past holds
on data it never saw.

VARIANTS (all causal: at bar i they use only lows already confirmed by bar i):
  V0  current (hurstlow.py): period = median of last 3 gaps, clamp 0.8-1.6 tgt
  V1  V0 + running bias correction: shift the projection by the median error of
      all projections already resolved (needs >= 3), measured in periods
  V2  period = autocorrelation-measured cycle at bar i (fld.measure_period on
      the swing-low degree), falling back to V0 when unmeasurable
  V3  period = median of the last 6 gaps (longer memory)
  V4  V3 + V1's running bias correction
  V5  swing-low detection window scaled to the measured crypto length
      (1.25 x nominal) instead of nominal, otherwise V0
  V6  V5 + V1's running bias correction
Degrees 160D and 80D; ETH and BTC 1D, 2D, 3D, 5D (the 2D-5D lows are largely
the same lows seen on coarser bars; reported per chart, judged on 1D and 2D).

SCORE: for every swing low, the projection standing the bar before it was
confirmed; error = (actual low bar - projected bar) / period. Median |error| and
share within +/-0.2 period. Discovery = lows before 2022-01-01, holdout = 2022 on.
RULE: choose, per degree, the variant with the lowest discovery median |error|
pooled over ETH 1D, ETH 2D, BTC 1D, BTC 2D. It is ADOPTED into the indicator
only if its HOLDOUT median |error| is lower than V0's holdout AND its holdout
within-window share is higher than V0's. Otherwise V0 stays. Holdout numbers are
reported for every variant but do not choose the winner.
Accuracy only; no signal outcomes are scored here.
RERUN NOTE: first run used hurstlow.swing_lows(), which resolved replacements
with hindsight. Rerun on the causal hurstlow.stream() (identical to the Pine),
same variants and rule; both outputs are in RESULTS_hurstcal.txt.
  python3 -I analysis/hurstcal.py -> analysis/RESULTS_hurstcal.txt
"""
import sys, os, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import fld as F
import hurstlow as H

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
TFD = {'1D': 1, '2D': 2, '3D': 3, '5D': 5}
SPLIT = dt.date(2022, 1, 1)
VARS = ['V0', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']


def run(b, tgt, var, deg_days, tfd):
    low = list(b['low']); n = len(low)
    det = tgt * (1.25 if var in ('V5', 'V6') else 1.0)
    snap, ev = H.stream(low, det)
    per_ac = F.measure_period(b, deg_days * (1.25 if var in ('V5', 'V6') else 1.0), tfd) if var == 'V2' else None
    nmem = 6 if var in ('V3', 'V4') else 3
    bias_on = var in ('V1', 'V4', 'V6')
    errs = []; resolved = []
    proj_prev = None
    for i in range(n):
        known = snap[i]
        if ev[i] == 'new' and proj_prev is not None:      # error recorded on a new low only, as in Pine
            j = known[-1]
            e = (j - proj_prev[0]) / proj_prev[1]
            errs.append((b['date'][j], e)); resolved.append(e)
        if not known:
            proj_prev = None; continue
        sp = [known[k] - known[k - 1] for k in range(max(1, len(known) - nmem), len(known))]
        per = st.median(sp) if len(sp) >= 2 else 1.25 * det
        if var == 'V2' and per_ac and per_ac[i]:
            per = per_ac[i]
        per = min(max(per, 0.8 * det), 1.6 * det)
        nxt = known[-1] + per
        if bias_on and len(resolved) >= 3:
            nxt += st.median(resolved) * per
        while nxt < i - 0.5 * per: nxt += per
        proj_prev = (nxt, per)
    return errs


def score(E_):
    if not E_: return None
    a = [abs(e) for _, e in E_]
    return dict(n=len(E_), mae=st.median(a), win=100 * sum(x <= 0.2 for x in a) / len(a), bias=st.median(e for _, e in E_))


def fs(s):
    return '   -   ' if not s else f'n={s["n"]:>2} |err| {s["mae"]:.2f} in-window {s["win"]:3.0f}% bias {s["bias"]:+.2f}'


def main():
    P('HURST CYCLE-LOW CALIBRATION -- declared 27 Oct 2026, run', dt.date.today(), '| accuracy only\n')
    OUT = {}
    for deg in ('160D', '80D'):
        dd = F.NOMINAL[deg]
        P(f'{deg}')
        pooled = {v: {'disc': [], 'hold': []} for v in VARS}
        for a in ('ETH', 'BTC'):
            for tf in ('1D', '2D', '3D', '5D'):
                b = E.load(f'data/{a}_{tf}.csv'); tgt = dd / TFD[tf]
                line = []
                for v in VARS:
                    er = run(b, tgt, v, dd, TFD[tf])
                    d_ = [x for x in er if x[0] < SPLIT]; h_ = [x for x in er if x[0] >= SPLIT]
                    if tf in ('1D', '2D'):
                        pooled[v]['disc'] += d_; pooled[v]['hold'] += h_
                    s = score(er)
                    line.append(f'{v} {s["mae"]:.2f}/{s["win"]:.0f}%' if s else f'{v} -')
                P(f'  {a} {tf}: ' + '  '.join(line))
        P('  pooled ETH/BTC 1D+2D:            discovery (to 2021)                     | holdout (2022 on)')
        for v in VARS:
            P(f'    {v}: {fs(score(pooled[v]["disc"]))} | {fs(score(pooled[v]["hold"]))}')
        best = min(VARS, key=lambda v: score(pooled[v]['disc'])['mae'] if score(pooled[v]['disc']) else 9)
        hb, h0 = score(pooled[best]['hold']), score(pooled['V0']['hold'])
        adopt = best != 'V0' and hb and h0 and hb['mae'] < h0['mae'] and hb['win'] > h0['win']
        P(f'  chosen on discovery: {best} -> holdout {fs(hb)} vs V0 {fs(h0)} -> {"ADOPT " + best if adopt else "KEEP V0"}\n')
        OUT[deg] = dict(best=best, adopt=bool(adopt))
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_hurstcal.txt'), 'w').write('\n'.join(L) + '\n')
    return OUT


if __name__ == '__main__':
    main()
