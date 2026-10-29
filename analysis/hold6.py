"""Does the low HOLDING for six days after entry tell you anything? 29 Oct 2026.

Jared's question. This is a POST-ENTRY read, not an entry filter -- by day six the
position is already on. So it is reported twice:

  FROM ENTRY   outcomes over the usual 60 days measured from the entry close.
               Useful for understanding, not actionable (you cannot go back).
  FROM DAY 6   outcomes measured from the day-6 close over the following 54 days.
               THIS is the actionable version: you are in, six days have passed,
               what happens next.

THREE READINGS of "the low holds for six days", all declared before running:
  H_low     no daily LOW in days 1-6 undercuts the entry bar's low
  H_close   all six daily CLOSES are at or above the entry price
  H_trough  no daily low in days 1-6 undercuts the TROUGH low (the pivot that
            produced the signal, which sits three bars before entry)

Scored on win / LIQ30 / LIQ20 / median drawdown together, per the standing change
in CONTEXT.md: a filter that lifts win rate while leaving drawdown alone is worth
less here than one that does the reverse.

NOT AN EXIT RULE. CONTEXT.md: exits are discretionary and that is settled, five
mechanical exits have been tested and all lost to holding. This is a read.

Run from the repo root:  python3 -I analysis/hold6.py
"""
import sys, os, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
CH = ['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']
HOLD = 6


def fwd_from(day, P, start_date, c0, horizon):
    """up / dd / ret over `horizon` days from start_date, measured against c0."""
    i = P.get(start_date)
    if i is None: return None
    end = start_date + dt.timedelta(days=horizon)
    w = [k for k in range(i + 1, len(day['date'])) if day['date'][k] <= end]
    if not w or day['date'][w[-1]] < end: return None
    hi = max(day['high'][k] for k in w); lo = min(day['low'][k] for k in w)
    return dict(up=(hi / c0 - 1) * 100, dd=(lo / c0 - 1) * 100,
                ret=(day['close'][w[-1]] / c0 - 1) * 100)


def build():
    rows = []
    for ch in CH:
        a, tf = ch.split('_')
        sig, b = E.signals(f'data/{ch}.csv', regime=GATE)
        day = E.load(f'data/{a}_1D.csv'); P = {d: i for i, d in enumerate(day['date'])}
        last = day['date'][-2]
        for s in sig:
            d0 = bucket_end(b['date'], s['ei'])
            if d0 is None or d0 not in P: continue
            if d0 + dt.timedelta(days=61) > last: continue
            i0 = P[d0]; e0 = s['entry']
            entry_low = b['low'][s['ei']]; trough_low = b['low'][s['ti']]
            w6 = [k for k in range(i0 + 1, len(day['date']))
                  if (day['date'][k] - d0).days <= HOLD]
            if len(w6) < 4: continue          # need a real six-day window
            h_low = all(day['low'][k] >= entry_low for k in w6)
            h_close = all(day['close'][k] >= e0 for k in w6)
            h_trough = all(day['low'][k] >= trough_low for k in w6)
            k6 = w6[-1]; d6 = day['date'][k6]; c6 = day['close'][k6]
            f0 = fwd_from(day, P, d0, e0, 60)
            f6 = fwd_from(day, P, d6, c6, 54)
            if not f0: continue
            rows.append(dict(ch=ch, a=a, yr=d0.year, h_low=h_low, h_close=h_close,
                             h_trough=h_trough,
                             win=f0['up'] >= 20, liq30=f0['dd'] <= -30, liq20=f0['dd'] <= -20,
                             dd=f0['dd'],
                             win6=(f6['up'] >= 20) if f6 else None,
                             liq30_6=(f6['dd'] <= -30) if f6 else None,
                             dd6=f6['dd'] if f6 else None,
                             ret6=f6['ret'] if f6 else None))
    return rows


def W(S, k='win'): return 100 * sum(bool(r[k]) for r in S) / len(S) if S else float('nan')
def M(S, k='dd'):
    v = [r[k] for r in S if r[k] is not None]
    return statistics.median(v) if v else float('nan')


def block(S, label):
    print(f'\n  {label}  n={len(S)}')
    print(f'    {"":<22}{"n":>6}{"win":>7}{"LIQ30":>8}{"LIQ20":>8}{"med dd":>9}'
          f'{"| win6":>9}{"LIQ30|6":>9}{"med dd6":>10}{"med ret6":>10}')
    base = S
    print(f'    {"BASELINE":<22}{len(base):>6}{W(base):>6.0f}%{W(base,"liq30"):>7.0f}%'
          f'{W(base,"liq20"):>7.0f}%{M(base):>8.1f}%{W([r for r in base if r["win6"] is not None],"win6"):>8.0f}%'
          f'{W([r for r in base if r["liq30_6"] is not None],"liq30_6"):>8.0f}%{M(base,"dd6"):>9.1f}%{M(base,"ret6"):>9.1f}%')
    for key, nm in (('h_low', 'entry low held 6d'), ('h_close', 'closes >= entry 6d'),
                    ('h_trough', 'trough low held 6d')):
        for val, tag in ((True, ''), (False, '  (NOT)')):
            c = [r for r in S if r[key] is val]
            if len(c) < 20: continue
            c6 = [r for r in c if r['win6'] is not None]
            print(f'    {nm+tag:<22}{len(c):>6}{W(c):>6.0f}%{W(c,"liq30"):>7.0f}%{W(c,"liq20"):>7.0f}%'
                  f'{M(c):>8.1f}%{W(c6,"win6"):>8.0f}%{W(c6,"liq30_6"):>8.0f}%{M(c,"dd6"):>9.1f}%{M(c,"ret6"):>9.1f}%')


def main():
    rows = build()
    print(f'{len(rows)} regime-gated signals with a complete six-day window and 60d outcomes')
    print('FROM ENTRY: win/LIQ30/LIQ20/med dd over 60d.   FROM DAY 6: win6/LIQ30|6/med dd6/med ret6 over the following 54d.')
    block(rows, 'ALL')
    block([r for r in rows if r['a'] == 'ETH'], 'ETH')
    block([r for r in rows if r['a'] == 'BTC'], 'BTC')
    print('\n  HOW OFTEN DOES EACH FIRE?')
    for key, nm in (('h_low','entry low held 6d'),('h_close','closes >= entry 6d'),('h_trough','trough low held 6d')):
        t = sum(1 for r in rows if r[key])
        print(f'    {nm:<22}{t:>5} of {len(rows)}  ({t/len(rows)*100:.0f}%)')


if __name__ == '__main__':
    main()
