import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
root = sys.argv[1]
for a in ('ETH','BTC'):
    d = L.load(f'{root}/data/{a}_1D.csv', clamp=False)
    gaps = [(d['date'][i-1], d['date'][i]) for i in range(1,len(d['date'])) if (d['date'][i]-d['date'][i-1]).days != 1]
    print(a, '1D', d['date'][0], d['date'][-1], 'gaps', gaps[:5], len(gaps))
    pos = {x:i for i,x in enumerate(d['date'])}
    for tf in (2,3,5,8):
        b = L.load(f'{root}/data/{a}_{tf}D.csv', clamp=False); bad=[]
        for i, od in enumerate(b['date']):
            # expected bucket start
            doy = (od - dt.date(od.year,1,1)).days
            if doy % tf: bad.append(('start', od)); continue
            cd = L.bar_close_date(tf, od)
            days = [od + dt.timedelta(days=k) for k in range((cd-od).days+1)]
            idx = [pos[x] for x in days if x in pos]
            last = i == len(b['date'])-1
            if not last and len(idx) != len(days): bad.append(('missing', od)); continue
            o=d['open'][idx[0]]; c=d['close'][idx[-1]]; h=max(d['high'][k] for k in idx); l=min(d['low'][k] for k in idx)
            if (o,h,l,c) != (b['open'][i],b['high'][i],b['low'][i],b['close'][i]):
                bad.append(('ohlc', od, (o,h,l,c), (b['open'][i],b['high'][i],b['low'][i],b['close'][i])))
        print(a, tf, 'D bars', len(b['date']), 'bad', len(bad), bad[:6])
