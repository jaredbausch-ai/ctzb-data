"""Do 1D/2D signal prints line up with bullish divergence on higher timeframes?
DECLARED BEFORE RUNNING, 27 Oct 2026 (Jared's idea).

NOT the same construct as the diamond. The diamond compares CT RSI against Stoch
across consecutive troughs -- oscillator vs oscillator. This is PRICE vs
OSCILLATOR: at a confirmed CT RSI trough on the higher timeframe, price makes a
LOWER low while the oscillator makes a HIGHER low.

Bullish divergence has been tested here once, as a marker for the end of a flush,
and failed at 1 hit in 36. That was a different question (when does the flush
end). This asks whether divergence ALREADY CONFIRMED on a higher timeframe makes
a lower-timeframe print better, which is a confluence question, and confluence
works on ETH.

CAUSALITY. A divergence is only known at the confirmation bar of its second
trough (ti+3, the same lag as a CTZB signal). Only divergences whose confirmation
date is on or before the signal's entry date are counted. Nothing reaches forward.

DECLARED FEATURES at a 1D or 2D entry:
  D_<tf>    a bullish divergence confirmed on <tf> within the prior 10 days
  DCOUNT    how many of 2D/3D/5D/8D have one
  variants  CT RSI divergence, and Stoch-K divergence, scored separately
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
HTF = ('2D', '3D', '5D', '8D')
LOW = ('1D', '2D')
WIN = 10            # days, same window the confluence work uses


def divergences(path, osc='ct'):
    """(confirmation_date, trough_date) for each confirmed bullish divergence.
    Lower low in PRICE, higher low in the oscillator, vs the previous trough."""
    b = E.load(path)
    c = b['close']; lo = b['low']; dates = b['date']
    ct = E.rsi(c, 14)
    k = E.sma(E.stoch_of(ct, 14), 3)
    series = ct if osc == 'ct' else k
    n = len(c); out = []
    prev = None                      # (index, price_low, osc_value)
    for conf in range(n):
        ti = conf - 3
        if ti - 3 < 0: continue
        v = series[ti]
        if v is None: continue
        w = [series[j] for j in range(ti - 3, ti + 4)]
        if any(x is None for x in w): continue
        if any(series[j] <= v for j in range(ti - 3, ti)): continue
        if any(series[j] <= v for j in range(ti + 1, ti + 4)): continue
        if prev is not None:
            pl, pv = prev[1], prev[2]
            if lo[ti] < pl and v > pv:
                out.append((dates[conf], dates[ti]))
        prev = (ti, lo[ti], v)
    return out


def build(osc):
    div = {}
    for a in ('ETH', 'BTC'):
        for tf in HTF:
            div[(a, tf)] = divergences(f'data/{a}_{tf}.csv', osc)
    rows = []
    for a in ('ETH', 'BTC'):
        for tf in LOW:
            sig, b = E.signals(f'data/{a}_{tf}.csv', regime=GATE)
            day = E.load(f'data/{a}_1D.csv'); P = {d: i for i, d in enumerate(day['date'])}
            last = day['date'][-2]
            c = b['close']; ct = E.rsi(c, 14); em = E.ema(ct, 14)
            for s in sig:
                i = s['ei']; d0 = bucket_end(b['date'], i)
                if d0 is None or d0 not in P or d0 + dt.timedelta(days=61) > last: continue
                m = measure(day, P, d0, s['entry'], 60)
                if not m: continue
                act = {h: any(0 <= (d0 - cd).days <= WIN for cd, _ in div[(a, h)]) for h in HTF}
                g = ct[i] - em[i] if (ct[i] is not None and em[i] is not None) else None
                rows.append(dict(a=a, tf=tf, ch=f'{a}_{tf}', yr=d0.year, win=m['up'] >= 20,
                                 d30=m['dd'] <= -30, act=act, nd=sum(act.values()),
                                 g5=(g is not None and g > 5), prime=s['prime'], dis=s['dis']))
    return rows


def W(S): return 100 * sum(r['win'] for r in S) / len(S) if S else float('nan')
def D(S): return 100 * sum(r['d30'] for r in S) / len(S) if S else float('nan')


def report(rows, osc):
    print(f'\n{"="*74}\nBULLISH DIVERGENCE on higher TFs, oscillator = {osc.upper()}'
          f'   n={len(rows)}  baseline {W(rows):.0f}%  -30% {D(rows):.0f}%\n{"="*74}')
    for scope, S in (('ALL', rows), ('ETH', [r for r in rows if r['a'] == 'ETH']),
                     ('BTC', [r for r in rows if r['a'] == 'BTC'])):
        if len(S) < 60: continue
        print(f'\n  {scope}  baseline {W(S):.0f}%')
        print(f'    {"divergence on":<16}{"n yes":>7}{"win":>7}{"-30%":>7}{"n no":>7}{"win":>7}{"edge":>7}')
        for h in HTF:
            A = [r for r in S if r['act'][h]]; B = [r for r in S if not r['act'][h]]
            if len(A) < 15 or len(B) < 15: continue
            print(f'    {h:<16}{len(A):>7}{W(A):>6.0f}%{D(A):>6.0f}%{len(B):>7}{W(B):>6.0f}%{W(A)-W(B):>+7.0f}')
        print(f'    {"count of TFs":<16}')
        for lo, hi, nm in ((0, 1, '0'), (1, 2, '1'), (2, 3, '2'), (3, 5, '3 or 4')):
            c = [r for r in S if lo <= r['nd'] < hi]
            if len(c) < 15: continue
            print(f'      {nm:<14}{len(c):>7}{W(c):>6.0f}%{D(c):>6.0f}%{"":>7}{"":>7}{W(c)-W(S):>+7.0f}')


def main():
    for osc in ('ct', 'stoch'):
        rows = build(osc)
        report(rows, osc)
        if osc == 'ct':
            print('\n  STACKED ON gap>5 (ALL):')
            S = [r for r in rows if r['g5']]
            print(f'    gap>5                    n={len(S):<5} win {W(S):.0f}%  -30% {D(S):.0f}%')
            for nm, c in (('gap>5 + any HTF div', [r for r in S if r['nd'] >= 1]),
                          ('gap>5 + 2+ HTF div', [r for r in S if r['nd'] >= 2])):
                print(f'    {nm:<25}n={len(c):<5} ' +
                      (f'win {W(c):.0f}%  -30% {D(c):.0f}%' if len(c) >= 15 else 'too thin'))


if __name__ == '__main__':
    main()
