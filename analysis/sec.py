"""Seller Exhaustion Constant — proxy + backtest. Declared 1 Nov 2026.

DEFINITION, confirmed from Glassnode's indicator page (ARK Invest / David Puell,
2021):   SEC = Percent Supply in Profit x Volatility
         Volatility = 30-day rolling standard deviation of price / price

It bottoms when BOTH terms are low: few holders in profit AND a quiet tape.
Glassnode's own description -- "volatility is low, but losses realized on-chain
are high".

WHAT WE CAN AND CANNOT DO. The volatility term is exact -- it is pure price. The
supply-in-profit term is the same UTXO-level problem as before, so it uses the
volume-weighted proxy from analysis/sthprofit.py:

    pct_in_profit(t) = sum(volume on days where close < close(t)) / sum(volume)

Two windows, because the published metric uses ALL supply while our STH work used
155 days:
    SEC_all   proxy over the full trailing history (closest to the real metric)
    SEC_sth   proxy over the trailing 155 days

THE HALF THAT IS EXACT MATTERS. Unlike the STH test -- which collapsed into
momentum -- volatility is a genuinely different axis from price direction. That
is the reason to expect anything here at all; CONTEXT.md: "Price transforms keep
failing; different axes keep working."

DECLARED FEATURES at the entry bar, all using the TRAILING z-score so the bands
are causal (2-year window):
  X1  SEC in the bottom decile of its trailing 2y
  X2  SEC z < -1
  X3  SEC z < -1.5
  X4  SEC in the top decile          (the opposite extreme)
  X5  volatility term alone, bottom third   -- to separate the two halves
  X6  profit term alone, bottom third       -- ditto

X5 and X6 exist specifically to answer: is any edge coming from the NEW half
(volatility) or just restating the supply-in-profit half we already scrapped?

Scored on win / LIQ30 / median drawdown together.

Run from the repo root:  python3 -I analysis/sec.py
"""
import sys, os, csv, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
CH = ['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']


def load(sym):
    out=[]
    for r in csv.DictReader(open(f'data/{sym}_1D.csv')):
        out.append((dt.datetime.fromtimestamp(int(r['time']),dt.UTC).date(),
                    float(r['close']), float(r.get('volume') or 0.0)))
    return out


def series(sym, sth_days=None):
    rows=load(sym); n=len(rows); out={}
    cum_v=[0.0]
    for _,_,v in rows: cum_v.append(cum_v[-1]+v)
    for i in range(200,n):
        px=rows[i][1]
        lo = max(0, i-sth_days) if sth_days else 0
        w=rows[lo:i+1]
        tot=sum(v for _,_,v in w)
        if tot<=0: continue
        prof=sum(v for _,c,v in w if c<px)/tot
        # volatility: 30d rolling sd of price / price
        px30=[rows[j][1] for j in range(max(0,i-29),i+1)]
        if len(px30)<30: continue
        vol=statistics.pstdev(px30)/px
        out[rows[i][0]]=(prof*vol, prof, vol)
    return out


def bands(ser, win=730):
    ks=sorted(ser); out={}
    for i,d in enumerate(ks):
        w=[ser[x][0] for x in ks[max(0,i-win):i+1]]
        if len(w)<300: continue
        m=statistics.mean(w); s=statistics.pstdev(w)
        dec=sorted(w)[max(0,int(len(w)*0.10))]
        dec9=sorted(w)[min(len(w)-1,int(len(w)*0.90))]
        out[d]=(m,s,dec,dec9)
    return out


def main():
    print('SELLER EXHAUSTION CONSTANT = pct supply in profit x (30d sd of price / price)\n')
    SA={s:series(s) for s in ('BTC','ETH')}
    BA={s:bands(SA[s]) for s in ('BTC','ETH')}
    for sym in ('BTC','ETH'):
        ks=sorted(SA[sym]); d=ks[-1]; v,p,vol=SA[sym][d]
        m,s,dec,dec9=BA[sym][d]
        print(f'{sym}: NOW SEC {v:.4f}  (profit {p*100:.0f}% x vol {vol:.4f})   z {(v-m)/s:+.2f}')
        print(f'   trailing-2y mean {m:.4f}  10th pct {dec:.4f}  90th pct {dec9:.4f}   '
              f'-> {"BOTTOM DECILE" if v<=dec else ("top decile" if v>=dec9 else "middle")}')
        print(f'   last 10 days SEC: ' + ', '.join(f'{SA[sym][k][0]:.3f}' for k in ks[-10:]))
    print('\nSHAPE CHECK — SEC at known turning points (BTC):')
    ks=sorted(SA['BTC'])
    b=E.load('data/BTC_1D.csv'); px=dict(zip(b['date'],b['close']))
    for lab,dd in (('2026 cycle low',dt.date(2026,6,30)),('2025 high',dt.date(2025,10,6)),
                   ('2022 bear low',dt.date(2022,11,21)),('2021 Nov top',dt.date(2021,11,9)),
                   ('2020 Mar crash',dt.date(2020,3,13)),('2018 Dec low',dt.date(2018,12,15))):
        near=min((k for k in ks if abs((k-dd).days)<=5), key=lambda k:abs((k-dd).days), default=None)
        if near:
            v,p,vol=SA['BTC'][near]
            m,s,_,_=BA['BTC'].get(near,(0,1,0,0))
            print(f'   {lab:<16}{near}  px {px.get(near,0):>9,.0f}   SEC {v:.4f}  z {(v-m)/s if s else 0:+.2f}   '
                  f'(profit {p*100:>3.0f}%, vol {vol:.3f})')
    return SA,BA


if __name__ == '__main__':
    main()
