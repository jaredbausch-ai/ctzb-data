"""Narrowing the 160D cycle-low window from months to about two weeks.
DECLARED 27 Oct 2026 23:15 ET, before running. Jared: a 160-day window is not
useful; how do we get it to ~2 weeks? Two ways, both measured here. Accuracy and
coincidence only; no strategy return.

LOWS. 160D swing lows on the 1D chart, hurstlow.stream() (the Pine construct),
final list. Dated by the low's day. ETH and BTC. Lows that sit inside the data's
first 200 days or last 60 days are skipped.

T1  OUR SIGNALS AS THE TIMING TRIGGER. For each 160D low: did a CTZB signal on
    the same asset's 1D or 2D chart CONFIRM within the 21 days after the low
    (confirmation lags the low by design), and how many days after? Run twice:
    regime-gated signals (the ones we trade) and ungated (every confirmed low,
    to see the timing ability with the gate out of the way).
    BASELINE: the same question for every day in the data -- the chance that a
    signal confirms within 21 days of a random day. A signal confirming after a
    160D low means something only if it beats that.
    Also the reverse: of all signals, the share confirming within 21 days after
    a 160D low, inside vs outside a 160D DUE window (dist between -0.5 and +0.2,
    no roll-forward, causal).
T2  NESTED SMALLER CYCLE. 20D degree (nominal 17 days) on the 1D chart, same
    construct. For each 160D low: the projected 20D low standing the day before
    it -- error in days -- and whether the 160D low fell inside that 20D
    projection's +/-0.2-period window (about +/- 4-5 days). Baseline: the same
    error for every 20D low.
Descriptive. Nothing adopted; the indicator is not changed from this run.
  python3 -I analysis/hurstnest.py -> analysis/RESULTS_hurstnest.txt
"""
import sys, os, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
import fld as F
import hurstlow as H
from tagstats import bucket_end

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))


def proj_noroll(low, tgt):
    """per bar: (projected bar, period) from known lows, no roll-forward."""
    snap, ev = H.stream(low, tgt); n = len(low); out = [None] * n
    for i in range(n):
        kn = snap[i]
        if not kn: continue
        sp = [kn[k] - kn[k - 1] for k in range(max(1, len(kn) - 3), len(kn))]
        per = st.median(sp) if len(sp) >= 2 else 1.25 * tgt
        per = min(max(per, 0.8 * tgt), 1.6 * tgt)
        out[i] = (kn[-1] + per, per)
    return out, snap, ev


def sig_dates(a, gated):
    out = []
    for tf in ('1D', '2D'):
        S, b = E.signals(f'data/{a}_{tf}.csv', regime=GATE if gated else (lambda d: True))
        for s in S:
            d0 = bucket_end(b['date'], s['ei'])
            if d0: out.append(d0)
    return sorted(set(out))


def main():
    P('NARROWING THE 160D WINDOW -- declared 27 Oct 2026, run', dt.date.today(), '| descriptive, nothing adopted\n')
    for a in ('ETH', 'BTC'):
        b = E.load(f'data/{a}_1D.csv'); low = list(b['low']); d = b['date']; n = len(d)
        pr160, snap, ev = proj_noroll(low, F.NOMINAL['160D'])
        lows = [j for j in snap[-1] if 200 <= j <= n - 61]
        P(f'{a}: {len(lows)} 160D lows: {", ".join(str(d[j]) for j in lows)}')
        for gated in (True, False):
            S = sig_dates(a, gated); lab = 'gated' if gated else 'ungated'
            hits = []
            for j in lows:
                after = [(s - d[j]).days for s in S if 0 <= (s - d[j]).days <= 21]
                hits.append(min(after) if after else None)
            base = [any(0 <= (s - d[i]).days <= 21 for s in S) for i in range(200, n - 61)]
            h = [x for x in hits if x is not None]
            P(f'  T1 {lab:7}: signal confirmed within 21 days after the low on {len(h)}/{len(lows)} lows'
              f' (median {st.median(h) if h else float("nan"):.0f} days after) | any random day: {100 * sum(base) / len(base):.0f}%')
            P(f'     per low: {", ".join(f"{d[j]} " + (f"+{x}d" if x is not None else "none") for j, x in zip(lows, hits))}')
            # reverse: signals inside vs outside a DUE window
            pos = {dd: i for i, dd in enumerate(d)}
            ins, outs = [], []
            for s in S:
                i = pos.get(s)
                if i is None or i < 200 or i > n - 61 or pr160[i] is None: continue
                p, per = pr160[i]; dist = (p - i) / per
                near = any(0 <= (s - d[j]).days <= 21 for j in snap[-1])
                (ins if -0.5 <= dist < 0.2 else outs).append(near)
            P(f'     signals within 21 days after a real 160D low: inside DUE window {100 * sum(ins) / len(ins) if ins else 0:.0f}% (n {len(ins)})'
              f' vs outside {100 * sum(outs) / len(outs) if outs else 0:.0f}% (n {len(outs)})')
        pr20, snap20, ev20 = proj_noroll(low, F.NOMINAL['20D'])
        errs, inw = [], []
        for j in lows:
            p = pr20[j - 1]
            if p:
                errs.append(j - p[0]); inw.append(abs(j - p[0]) <= 0.2 * p[1])
        base = []
        for i in range(1, n):
            if ev20[i] == 'new' and pr20[i - 1]:
                jj = snap20[i][-1]; p = pr20[i - 1]; base.append(abs(jj - p[0]))
        P(f'  T2 20D projection the day before each 160D low: median miss {st.median(abs(e) for e in errs):.0f} days'
          f' (signed {st.median(errs):+.0f}), inside its +/-0.2 window on {sum(inw)}/{len(inw)}'
          f' | all 20D lows: median miss {st.median(base):.0f} days (n {len(base)})')
        P(f'     per low (days, + = low came after the 20D projection): {", ".join(f"{e:+.0f}" for e in errs)}\n')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_hurstnest.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
