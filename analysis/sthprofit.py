"""Short-Term Holder Supply in Profit -- a volume-weighted PROXY. 1 Nov 2026.

Jared sent the Checkonchain chart. The real metric is UTXO-level: for every coin
last moved within 155 days, is its cost basis below spot? That needs chain data
with coin age and realized price. We cannot compute it, same wall as the whale
metrics -- Glassnode and Checkonchain derive it by tracking the chain.

THE PROXY. Assume a coin traded on day d has cost basis = close(d), and that
exchange volume approximates how many coins changed hands at that price. Then:

    sth_profit(t) = sum of volume on days d in [t-155, t] where close(d) < close(t)
                    -------------------------------------------------------------
                                sum of volume over the same window

That is the same QUESTION the on-chain metric asks -- what fraction of recent
buyers are above water -- computed from the price/volume record instead of the
chain. 155 days is the standard short-term-holder threshold.

WHERE IT DIFFERS FROM THE REAL THING, stated so nobody mistakes one for the other:
  - exchange volume is not on-chain coin movement
  - the same coin traded ten times counts ten times; the chain counts it once
  - coins that moved on-chain without trading are invisible
  - wash volume inflates the denominator
  - it cannot see HODLed supply re-entering the short-term cohort

So: directionally the same, numerically its own thing. Validate the SHAPE against
the published chart before trusting any level.

DECLARED FEATURES, before running:
  S1  below 25%            deep -- most recent buyers underwater
  S2  below its own mean-1sd (trailing 2y)
  S3  below 50%
  S4  above its own mean+1sd    the "not buying" euphoria zone on the chart
  S5  crossed UP through 50 within the last 5 bars
  S6  rising over 10 bars

Scored with win / LIQ30 / median drawdown together, per the standing change.

Run from the repo root:  python3 -I analysis/sthprofit.py
"""
import sys, os, csv, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
STH_DAYS = 155


def load_vol(sym):
    out = []
    for r in csv.DictReader(open(f'data/{sym}_1D.csv')):
        out.append((dt.datetime.fromtimestamp(int(r['time']), dt.UTC).date(),
                    float(r['close']), float(r.get('volume') or 0.0)))
    return out


def sth_series(sym):
    rows = load_vol(sym)
    n = len(rows)
    out = {}
    for i in range(STH_DAYS, n):
        px = rows[i][1]
        w = rows[i - STH_DAYS:i + 1]
        tot = sum(v for _, _, v in w)
        if tot <= 0: continue
        inp = sum(v for _, c, v in w if c < px)
        out[rows[i][0]] = inp / tot * 100
    return out


def zscore_bands(ser, dates, win_days=730):
    """trailing mean and sd, so the bands are causal."""
    ks = sorted(ser)
    out = {}
    for i, d in enumerate(ks):
        lo = d - dt.timedelta(days=win_days)
        w = [ser[x] for x in ks[max(0, i - win_days):i + 1] if x >= lo]
        if len(w) < 200: continue
        m = statistics.mean(w); s = statistics.pstdev(w)
        out[d] = (m, s)
    return out


def main():
    print('STH SUPPLY IN PROFIT (volume-weighted proxy, 155-day window)\n')
    S = {}; B = {}
    for sym in ('BTC', 'ETH'):
        S[sym] = sth_series(sym); B[sym] = zscore_bands(S[sym], None)
        ks = sorted(S[sym]); last = ks[-1]
        m, sd = B[sym].get(last, (None, None))
        allv = [S[sym][k] for k in ks]
        print(f'{sym}: {len(ks)} days, {ks[0]} -> {last}')
        print(f'   NOW {S[sym][last]:.1f}%   full-history mean {statistics.mean(allv):.1f}%  sd {statistics.pstdev(allv):.1f}')
        if m: print(f'   trailing-2y mean {m:.1f}%  +1sd {m+sd:.1f}%  -1sd {m-sd:.1f}%   '
                    f'-> z = {(S[sym][last]-m)/sd:+.2f}')
        # recent path
        print('   last 10 days: ' + ', '.join(f'{S[sym][k]:.0f}' for k in ks[-10:]))
        print()
    # SHAPE VALIDATION against the published chart: did it spike near the cycle top
    # and bottom near the lows?
    print('SHAPE CHECK -- does the proxy behave like the published metric?')
    for sym in ('BTC',):
        ser = S[sym]; ks = sorted(ser)
        b = E.load(f'data/{sym}_1D.csv'); px = dict(zip(b['date'], b['close']))
        marks = [('2026 cycle low', dt.date(2026,6,30)), ('2025 high area', dt.date(2025,10,6)),
                 ('2022 bear low', dt.date(2022,11,21)), ('2021 Nov top', dt.date(2021,11,9)),
                 ('2020 Mar crash', dt.date(2020,3,13))]
        for lab, d in marks:
            near = min((k for k in ks if abs((k-d).days) <= 5), key=lambda k: abs((k-d).days), default=None)
            if near: print(f'   {lab:<16} {near}  price {px.get(near,0):>9,.0f}   STH profit {ser[near]:>5.1f}%')
    print()
    return S, B


if __name__ == '__main__':
    main()


def backtest():
    S, B = {}, {}
    for sym in ('BTC','ETH'):
        S[sym]=sth_series(sym); B[sym]=zscore_bands(S[sym],None)
    CH=['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']
    rows=[]
    for ch in CH:
        a,tf=ch.split('_')
        sig,b=E.signals(f'data/{ch}.csv',regime=GATE)
        day=E.load(f'data/{a}_1D.csv'); P={d:i for i,d in enumerate(day['date'])}; last=day['date'][-2]
        ser=S[a]; bands=B[a]; ks=sorted(ser)
        for s in sig:
            d0=bucket_end(b['date'],s['ei'])
            if d0 is None or d0 not in P or d0+dt.timedelta(days=61)>last: continue
            if d0 not in ser or d0 not in bands: continue
            m=measure(day,P,d0,s['entry'],60)
            if not m: continue
            v=ser[d0]; mu,sd=bands[d0]
            prev=[ser[k] for k in ks if k<d0][-11:]
            rows.append(dict(ch=ch,a=a,yr=d0.year,v=v,z=(v-mu)/sd if sd else 0,
                             win=m['up']>=20, liq30=m['dd']<=-30, dd=m['dd'],
                             cross50=(len(prev)>=6 and v>=50 and min(prev[-5:])<50),
                             rising=(len(prev)>=11 and v>prev[0])))
    def W(Sx,k='win'): return 100*sum(bool(r[k]) for r in Sx)/len(Sx) if Sx else float('nan')
    def M(Sx): return statistics.median([r['dd'] for r in Sx]) if Sx else float('nan')
    print(f'\n{"="*92}\nBACKTEST: STH-profit proxy at the signal entry bar, {len(rows)} gated signals\n{"="*92}')
    for scope,Sx in (('ALL',rows),('ETH',[r for r in rows if r['a']=='ETH']),('BTC',[r for r in rows if r['a']=='BTC'])):
        print(f'\n  {scope}  n={len(Sx)}  baseline win {W(Sx):.0f}%  LIQ30 {W(Sx,"liq30"):.0f}%  med dd {M(Sx):.1f}%')
        print(f'    {"condition":<30}{"n":>6}{"win":>7}{"edge":>7}{"LIQ30":>8}{"cut":>6}{"med dd":>9}')
        cells=[('S1  below 25%',          lambda r: r['v']<25),
               ('S2  below -1sd (z<-1)',  lambda r: r['z']<-1),
               ('S3  below 50%',          lambda r: r['v']<50),
               ('S4  above +1sd (z>+1)',  lambda r: r['z']>1),
               ('S5  crossed up thru 50', lambda r: r['cross50']),
               ('S6  rising over 10d',    lambda r: r['rising']),
               ('    25-75% (middle)',    lambda r: 25<=r['v']<=75)]
        for nm,fn in cells:
            c=[r for r in Sx if fn(r)]
            if len(c)<20: print(f'    {nm:<30}{len(c):>6}{"too thin":>7}'); continue
            print(f'    {nm:<30}{len(c):>6}{W(c):>6.0f}%{W(c)-W(Sx):>+7.0f}{W(c,"liq30"):>7.0f}%'
                  f'{W(c,"liq30")-W(Sx,"liq30"):>+6.0f}{M(c):>8.1f}%')
    # quintiles -- is there a gradient?
    print(f'\n  GRADIENT: outcomes by STH-profit quintile (ALL)')
    srt=sorted(rows,key=lambda r:r['v']); q=len(srt)//5
    print(f'    {"quintile":<22}{"range":<16}{"n":>5}{"win":>7}{"LIQ30":>8}{"med dd":>9}')
    for i in range(5):
        c=srt[i*q:(i+1)*q] if i<4 else srt[4*q:]
        print(f'    {f"Q{i+1}":<22}{f"{c[0][chr(118)]:.0f}-{c[-1][chr(118)]:.0f}%":<16}{len(c):>5}'
              f'{W(c):>6.0f}%{W(c,"liq30"):>7.0f}%{M(c):>8.1f}%')


if __name__ == '__main__':
    backtest()
