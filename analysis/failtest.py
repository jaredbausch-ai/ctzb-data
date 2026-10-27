"""WHAT PREDICTS THE BLOWUP? Declared 27 Oct 2026.

A REDIRECT, in Jared's words: "we have really good winning odds already... what
would hurt us the most is getting liquidated. We're buying too early or buying
into a failing cluster." Every filter in this repo has been ranked on win rate --
reached +20% in 60 days. At ~3.3x a "win" that first draws down 28% is not a win;
he is liquidated or shaken out long before the +20% arrives. So win rate
OVERSTATES the real result and every ranking built on it is measuring the wrong
thing.

This scores the same features against FAILURE instead.

TARGETS (lower is better, unlike every other script here):
  LIQ30   max drawdown <= -30% within 60d. Liquidation proxy at 3.3x.
  LIQ20   max drawdown <= -20%. The shake-out level.
  EARLY   drawdown BEFORE the peak <= -15% (measure()['ddpk']). This is
          "bought too early" stated precisely: the pain came first.
  MEDDD   median max drawdown. The distribution, not just the tail.

FEATURES: everything already established, plus the two from this week.
  gap>5, CT>Signal, prime, diamond, bucket A, step up vs previous entry,
  own-TF confluence 2+, funding cooling (the 23 Oct veto), 160D trough DUE,
  2D/3D stochastic bullish divergence.

Each is reported as: failure rate when TRUE vs when FALSE. A feature that cuts
LIQ30 materially is worth more here than one that lifts win rate, because the
win rate is already good and the drawdown is what ends the account.

Run from the repo root:  python3 -I analysis/failtest.py
"""
import sys, os, csv, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, engine as E, regimes as R, fld as F
from tagstats import bucket_end, measure
from proj import dist_series
from htfdiv import divergences

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
CH = ['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']
TFS = ('1D','2D','3D','5D','8D')


def fundseries(a):
    out = {}
    p = f'data/derivs/{a}_funding_daily.csv'
    if not os.path.exists(p): return out
    for r in csv.DictReader(open(p)):
        v = r.get('funding_mean','')
        if v not in ('', None):
            out[dt.date.fromisoformat(r['date'])] = float(v)
    return out


def build():
    dated = {}
    for a in ('ETH','BTC'):
        for tf in TFS:
            s,b = E.signals(f'data/{a}_{tf}.csv', regime=GATE)
            dated[(a,tf)] = sorted(x for x in (bucket_end(b['date'], y['ei']) for y in s) if x)
    div = {(a,tf): divergences(f'data/{a}_{tf}.csv','stoch') for a in ('ETH','BTC') for tf in ('2D','3D')}
    fund = {a: fundseries(a) for a in ('ETH','BTC')}
    rows = []
    for ch in CH:
        a,tf = ch.split('_'); td = F.TF_DAYS[tf]
        sig,b = E.signals(f'data/{ch}.csv', regime=GATE)
        day = E.load(f'data/{a}_1D.csv'); P={d:i for i,d in enumerate(day['date'])}; last=day['date'][-2]
        c=b['close']; ct=E.rsi(c,14); em=E.ema(ct,14)
        ds = dist_series(b, F.NOMINAL['160D'], td)
        prev = None
        for s in sig:
            i=s['ei']; d0=bucket_end(b['date'], i)
            pe, prev = prev, s['entry']
            if d0 is None or d0 not in P or d0+dt.timedelta(days=61)>last: continue
            m = measure(day,P,d0,s['entry'],60)
            if not m: continue
            g = ct[i]-em[i] if (ct[i] is not None and em[i] is not None) else None
            fd = fund[a]; cool = None
            if d0 in fd:
                w7=[fd[d0-dt.timedelta(days=k)] for k in range(7) if d0-dt.timedelta(days=k) in fd]
                w7b=[fd[d0-dt.timedelta(days=14+k)] for k in range(7) if d0-dt.timedelta(days=14+k) in fd]
                if len(w7)>=5 and len(w7b)>=5: cool = float(np.mean(w7)) < float(np.mean(w7b))
            f = {
              'gap>5': (g is not None and g>5), 'CT>Signal': (g is not None and g>0),
              'prime': s['prime'], 'diamond': s['dis'], 'bucket A': s['bk']=='A',
              'step UP vs prev': (pe is not None and s['entry']>pe),
              'confluence 2+': sum(1 for t in TFS if t!=tf and
                                   any(0<=(d0-x).days<=10 for x in dated[(a,t)]))>=2,
              '160D trough DUE': (ds[i]<0.2) if ds[i] is not None else None,
              '2D/3D stoch div': any(any(0<=(d0-cd).days<=10 for cd,_ in div[(a,h)]) for h in ('2D','3D')),
              'funding NOT cooling': (not cool) if cool is not None else None,
            }
            rows.append(dict(ch=ch,a=a,yr=d0.year,f={k:v for k,v in f.items() if v is not None},
                             liq30=m['dd']<=-30, liq20=m['dd']<=-20, early=m['ddpk']<=-15,
                             dd=m['dd'], win=m['up']>=20))
    return rows


def rate(S,k): return 100*sum(r[k] for r in S)/len(S) if S else float('nan')


def main():
    rows = build()
    print(f'{len(rows)} regime-gated signals, 8 charts\n')
    print('BASELINE FAILURE RATES (this is what we are trying to cut)')
    for scope,S in (('ALL',rows),('ETH',[r for r in rows if r['a']=='ETH']),('BTC',[r for r in rows if r['a']=='BTC'])):
        print(f'  {scope:<4} n={len(S):<5} LIQ30 {rate(S,"liq30"):>4.0f}%   LIQ20 {rate(S,"liq20"):>4.0f}%   '
              f'EARLY {rate(S,"early"):>4.0f}%   median dd {statistics.median([r["dd"] for r in S]):>6.1f}%   win {rate(S,"win"):.0f}%')
    keys = ['gap>5','CT>Signal','prime','diamond','bucket A','step UP vs prev','confluence 2+',
            '160D trough DUE','2D/3D stoch div','funding NOT cooling']
    for scope,S in (('ALL',rows),('ETH',[r for r in rows if r['a']=='ETH']),('BTC',[r for r in rows if r['a']=='BTC'])):
        base30, base20, baseE = rate(S,'liq30'), rate(S,'liq20'), rate(S,'early')
        print(f'\n{"="*96}\n{scope}  n={len(S)}   baseline LIQ30 {base30:.0f}%  LIQ20 {base20:.0f}%  EARLY {baseE:.0f}%\n{"="*96}')
        print(f'  {"feature TRUE":<22}{"n":>6}{"LIQ30":>8}{"cut":>6}{"LIQ20":>8}{"cut":>6}{"EARLY":>8}{"cut":>6}{"med dd":>9}{"win":>7}')
        out=[]
        for k in keys:
            T=[r for r in S if k in r['f'] and r['f'][k]]
            if len(T)<25: continue
            out.append((rate(T,'liq30')-base30, k, T))
        for d30,k,T in sorted(out):
            print(f'  {k:<22}{len(T):>6}{rate(T,"liq30"):>7.0f}%{d30:>+6.0f}{rate(T,"liq20"):>7.0f}%'
                  f'{rate(T,"liq20")-base20:>+6.0f}{rate(T,"early"):>7.0f}%{rate(T,"early")-baseE:>+6.0f}'
                  f'{statistics.median([r["dd"] for r in T]):>8.1f}%{rate(T,"win"):>6.0f}%')


if __name__ == '__main__':
    main()
