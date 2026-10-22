import sys, datetime as dt, json
sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E, regimes as R

TODAY   = dt.date(2026,10,20)
REG_ON  = dt.date(2026,9,2)
TF = {'1D':1,'2D':2,'3D':3,'5D':5,'8D':8,'10D':10,'12D':12,'15D':15,'1M':30}
gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
O = json.load(open('odds.json'))

def marker(s):
    """The odds-table marker key this signal maps to, most specific first."""
    ks=[]
    if s['dis'] and s['prime']: ks.append('Diamond + prime dot')
    if s['dis']: ks.append('GOLD diamond <50' if s['ct']<50 else 'HOLLOW diamond >=50')
    if s['dis']: ks.append('Any diamond')
    if s['prime']: ks.append('Prime K 20-50')
    ks.append({'A':'A  trough <40','B':'B  trough 40-55','C':'C  trough 55-65','D':'D  trough >65'}[s['bk']])
    ks.append('ALL troughs')
    return ks

rows=[]
for tf,td in TF.items():
    sig,b = E.signals(f'data/tradingview/ETH_{tf}_tv.csv', regime=gate, ungated=True)
    px_now = b['close'][-1]
    for i,s in enumerate(sig):
        if s['date'] < REG_ON: continue
        prevlow = None
        if i>0:
            pti = sig[i-1]['ti']
            prevlow = b['low'][pti]
        thislow = b['low'][s['ti']]
        hl = None if prevlow is None else (thislow/prevlow - 1)*100
        rows.append(dict(tf=tf, td=td, s=s, px_now=px_now, hl=hl,
                         trough_low=thislow, prev_low=prevlow,
                         last_bar=b['date'][-1]))

rows.sort(key=lambda r: r['s']['edate'], reverse=True)
print(f"SETUPS SINCE THE REGIME TURNED ON ({REG_ON}, day {(TODAY-REG_ON).days})")
print(f"{len(rows)} signals across nine ETH charts\n")

for r in rows:
    s=r['s']; tf=r['tf']
    age=(TODAY-s['edate']).days
    live=(r['px_now']/s['entry']-1)*100
    fill='filled' if s['ct']<50 else 'hollow'
    tags=[]
    if s['dis']: tags.append('DIAMOND'+(' strong' if s['strong'] else ''))
    if s['prime']: tags.append('PRIME DOT')
    if not tags: tags=['plain']
    print(f"ETH {tf:<4} trough {s['date']}  ->  entry {s['edate']} @ ${s['entry']:,.2f}   ({age}d ago, lag {r['td']*3}d)")
    print(f"         bucket {s['bk']}  CT RSI {s['ct']:.1f} ({fill})  K {s['k']:.1f}   {', '.join(tags)}")
    if r['hl'] is not None:
        print(f"         trough low ${r['trough_low']:,.2f} vs prior signal's ${r['prev_low']:,.2f}  ->  {'HIGHER low' if r['hl']>0 else 'lower low'} {r['hl']:+.1f}%")
    chart=f'ETH {tf}'
    if chart in O['D']:
        for mk in marker(s):
            v=O['D'][chart].get(mk)
            if v and v.get('n',0)>=8:
                h=v['h']['60']
                print(f"         odds [{mk}] n={v['n']}: +10% {h[3]}%  +20% {h[4]}%  +30% {h[5]}%  "
                      f"med dd {v['r']}%  worst {v['rw']}%")
                break
    else:
        print(f"         odds: no table for {chart}")
    print(f"         now ${r['px_now']:,.2f}  ->  {live:+.1f}% from entry")
    print()
