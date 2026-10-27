"""Front-running a forming low: buying one bar after the CT low instead of at
the confirmation close. Pre-trade read for 27 Oct 2026 (Jared considering an
entry at tonight's close), kept general so it can be rerun for any date.

DESCRIPTIVE, NOT A FILTER TEST. Regime gate R.rsi_regime('data/BTC_2D.csv',
8, 13, 60, 41) on the low's date. A "forming low" is a bar whose CT is
strictly below the three bars before it and below the next bar's close CT
(the state after one bar has held). P1 = buy at the close of that next bar.
C3 = the normal confirmation close (three bars held), only for lows that
confirm. Outcomes on daily candles over 60 days from each entry's own date:
reach +20%, median worst dip before the high, touched -20% / -30%.
Splits: by bucket of the low (A < 40, B 40-55); whether a BTC 3D signal
confirmed 0-10 days before the entry; 2016-21 / 2022-26.
ENTRY QUALITY ONLY. Signals are computed, never fills. No exit is implied.
  python3 -I analysis/frontrun.py -> analysis/RESULTS_frontrun.txt
"""
import sys, os, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
SPLIT = dt.date(2022, 1, 1)
DAY = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
POS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in DAY}
S3, b3 = E.signals('data/BTC_3D.csv', regime=GATE)
BTC3 = [bucket_end(b3['date'], s['ei']) for s in S3]
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))


def rows_for(a, tf):
    b = E.load(f'data/{a}_{tf}.csv'); ct = E.rsi(b['close'], 14); d = b['date']; n = len(d); out = []
    for ti in range(3, n - 4):
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)): continue
        if any(ct[j] <= v for j in range(ti - 3, ti)): continue
        if ct[ti + 1] <= v: continue
        if not GATE(d[ti]): continue
        conf = all(ct[j] > v for j in range(ti + 1, ti + 4))
        bk = 'A' if v < 40 else 'B' if v < 55 else 'C+'
        for lab, ei in (('P1', ti + 1), ('C3', ti + 3)):
            if lab == 'C3' and not conf: continue
            d0 = bucket_end(d, ei)
            if d0 is None or d0 not in POS[a]: continue
            m = measure(DAY[a], POS[a], d0, b['close'][ei], 60)
            if not m: continue
            out.append(dict(lab=lab, conf=conf, bk=bk, per='16-21' if d0 < SPLIT else '22-26',
                            btc3=any(0 <= (d0 - x).days <= 10 for x in BTC3),
                            win=m['up'] >= 20, ddpk=m['ddpk'], t20=m['dd'] <= -20, t30=m['dd'] <= -30,
                            px=(b['close'][ei] / b['close'][ti + 1] - 1) * 100))
    return out


def s(G):
    if not G: return 'n=   0'
    n = len(G); w = lambda x: f'{100 * sum(r["win"] for r in x) / len(x):3.0f}%({len(x):>3})' if x else '   -    '
    return (f'n={n:>4} +20% {100 * sum(r["win"] for r in G) / n:3.0f}% '
            f'[{w([r for r in G if r["per"] == "16-21"])} {w([r for r in G if r["per"] == "22-26"])}] '
            f'dip {st.median(r["ddpk"] for r in G):+5.1f}%  -20% {100 * sum(r["t20"] for r in G) / n:3.0f}%  '
            f'-30% {100 * sum(r["t30"] for r in G) / n:3.0f}%')


def main():
    P('FRONT-RUNNING A FORMING LOW (buy one bar after the low) vs the confirmation close -- run', dt.date.today())
    P('entry quality only, computed signals, not fills\n')
    for a, tf in (('ETH', '1D'), ('ETH', '2D'), ('BTC', '2D')):
        R_ = rows_for(a, tf)
        P(f'{a} {tf}')
        for bk in ('ALL', 'A', 'B'):
            G = [r for r in R_ if bk == 'ALL' or r['bk'] == bk]
            p1 = [r for r in G if r['lab'] == 'P1']; c3 = [r for r in G if r['lab'] == 'C3']
            nc = [r for r in p1 if not r['conf']]
            px = [r['px'] for r in c3]
            P(f'  {bk:3} buy 1 bar after the low   {s(p1)}   never confirmed {100 * len(nc) / len(p1) if p1 else 0:3.0f}%')
            P(f'      of those, never confirmed  {s(nc)}')
            P(f'      confirmation close         {s(c3)}   paid {st.median(px) if px else 0:+.1f}% over the 1-bar price')
        if a == 'ETH':
            for bk in ('A', 'B'):
                G = [r for r in R_ if r['bk'] == bk and r['btc3']]
                P(f'  {bk} with a BTC 3D signal 0-10 days before: 1 bar after {s([r for r in G if r["lab"] == "P1"])}')
                P(f'                                       confirmation {s([r for r in G if r["lab"] == "C3"])}')
        P('')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_frontrun.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
