"""Projected cycle-low window AND cross-timeframe confluence. 27 Oct 2026.

Jared's idea: a print landing inside a projected cycle-low window, with other
timeframes confirming, should resolve differently from a descending staircase.
This is the direct form of the failed-cluster question.

Confluence is BACKWARD-ONLY (other timeframes that have ALREADY printed within
10 days). CONTEXT.md: the symmetric window credits charts that print up to ten
days AFTER entry and inflates every rate built on it.
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R, fld as F
from tagstats import bucket_end, measure
from proj import dist_series

TFS = ('1D','2D','3D','5D','8D')
CH = ['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']

def build(degree):
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    dated = {}
    for a in ('ETH','BTC'):
        for tf in TFS:
            s,b = E.signals(f'data/{a}_{tf}.csv', regime=gate)
            dated[(a,tf)] = sorted(x for x in (bucket_end(b['date'], y['ei']) for y in s) if x)
    rows=[]
    for ch in CH:
        a,tf = ch.split('_'); td = F.TF_DAYS[tf]
        sig,b = E.signals(f'data/{ch}.csv', regime=gate)
        day = E.load(f'data/{a}_1D.csv'); P={d:i for i,d in enumerate(day['date'])}; last=day['date'][-2]
        ds = dist_series(b, F.NOMINAL[degree], td)
        c=b['close']; ct=E.rsi(c,14); em=E.ema(ct,14)
        for s in sig:
            i=s['ei']; d0=bucket_end(b['date'], i)
            if d0 is None or d0 not in P or d0+dt.timedelta(days=61)>last or ds[i] is None: continue
            m = measure(day,P,d0,s['entry'],60)
            if not m: continue
            conf = sum(1 for t in TFS if t!=tf and any(0 <= (d0-x).days <= 10 for x in dated[(a,t)]))
            g = ct[i]-em[i] if (ct[i] is not None and em[i] is not None) else None
            rows.append(dict(ch=ch,a=a,yr=d0.year,due=ds[i]<0.2,conf=conf,
                             win=m['up']>=20, d30=m['dd']<=-30,
                             g5=(g is not None and g>5)))
    return rows

def W(S): return 100*sum(r['win'] for r in S)/len(S) if S else float('nan')
def D(S): return 100*sum(r['d30'] for r in S)/len(S) if S else float('nan')

def report(rows, label):
    print(f'\n{"="*78}\n{label}   n={len(rows)}  baseline win {W(rows):.0f}%  -30% {D(rows):.0f}%\n{"="*78}')
    for scope,S in (('ALL',rows), ('ETH',[r for r in rows if r['a']=='ETH']),
                    ('BTC',[r for r in rows if r['a']=='BTC'])):
        if len(S)<80: continue
        print(f'\n  {scope}  (baseline {W(S):.0f}%)')
        print(f'    {"":<26}{"n":>6}{"win":>7}{"-30%":>7}{"vs base":>9}')
        cells = [('due + 2 or more agree', [r for r in S if r['due'] and r['conf']>=2]),
                 ('due + 0 or 1 agree',    [r for r in S if r['due'] and r['conf']<2]),
                 ('not due + 2 or more',   [r for r in S if not r['due'] and r['conf']>=2]),
                 ('not due + 0 or 1',      [r for r in S if not r['due'] and r['conf']<2])]
        for nm,c in cells:
            if len(c)<15: print(f'    {nm:<26}{len(c):>6}{"-":>7}{"-":>7}{"-":>9}'); continue
            print(f'    {nm:<26}{len(c):>6}{W(c):>6.0f}%{D(c):>6.0f}%{W(c)-W(S):>+9.0f}')

def main():
    for deg in ('160D','80D'):
        rows = build(deg)
        report(rows, f'{deg} projected low x backward-only confluence')
        if deg=='160D':
            print('\n  STACKED ON gap>5 (ETH only, where confluence works):')
            S=[r for r in rows if r['a']=='ETH' and r['g5']]
            print(f'    gap>5                      n={len(S):<5} win {W(S):.0f}%  -30% {D(S):.0f}%')
            for nm,c in (('gap>5 + due', [r for r in S if r['due']]),
                         ('gap>5 + due + 2 agree', [r for r in S if r['due'] and r['conf']>=2])):
                if len(c)>=15:
                    print(f'    {nm:<27}n={len(c):<5} win {W(c):.0f}%  -30% {D(c):.0f}%')
                else:
                    print(f'    {nm:<27}n={len(c):<5} too thin')

if __name__ == '__main__':
    main()
