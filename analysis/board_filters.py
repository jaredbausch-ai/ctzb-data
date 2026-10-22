import sys; sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E, regimes as R, datetime as dt
gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
CH=[('ETH','1D'),('ETH','2D'),('ETH','3D'),('ETH','5D'),('ETH','8D'),
    ('BTC','1D'),('BTC','2D'),('BTC','3D'),('BTC','5D'),('BTC','8D')]
print(f"{'chart':<8}{'last bar':<12}{'close':>10}{'CT':>7}{'Sig':>7}{'gap':>7}{'K':>6}{'bk':>4}   {'last signal':<12}{'tags':<16}{'step':>8}")
rows=[]
for sym,tf in CH:
    p=f'data/{sym}_{tf}.csv'
    try: sg,b=E.signals(p, regime=gate)
    except Exception as ex: print(f'{sym} {tf}: {ex}'); continue
    c=b['close']; ct=E.rsi(c,14); em=E.ema([x for x in ct],14)
    st=E.stoch_of(ct,14); k=E.sma(st,3)
    i=len(c)-1
    g = (ct[i]-em[i]) if (ct[i] is not None and em[i] is not None) else None
    bk = 'A' if ct[i]<40 else 'B' if ct[i]<55 else 'C' if ct[i]<65 else 'D'
    s=sg[-1] if sg else None
    tags=[]
    step=None
    if s:
        if s['dis']: tags.append('hollow dmd' if not s['strong'] else 'filled dmd')
        if s['prime']: tags.append('prime')
        if len(sg)>1: step=(s['entry']/sg[-2]['entry']-1)*100
    print(f"{sym+' '+tf:<8}{str(b['date'][i]):<12}{c[i]:>10,.0f}{ct[i]:>7.1f}{em[i]:>7.1f}{g:>+7.2f}{k[i]:>6.1f}{bk:>4}   "
          f"{str(s['edate']) if s else '-':<12}{s['bk']+' '+','.join(tags) if s else '-':<16}"
          f"{(f'{step:+.1f}%' if step is not None else '-'):>8}")
    rows.append((sym,tf,ct[i],em[i],g,k[i],bk,s))
print()
print('REGIME: on since 2026-09-02 =', (dt.date(2026,10,22)-dt.date(2026,9,2)).days, 'days  (0-60 band: step filter carries ~+3, not +19)')
