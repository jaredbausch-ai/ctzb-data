import json, statistics as st
R=[r for r in json.load(open('/home/claude/ctzb-data/analysis/ctema.json')) if r['up60'] is not None]

# ---- pre-declared candidate features. Written before looking at any result. ----
FEATS=[
 ('A  CT above EMA',              lambda r: r['above']),
 ('B  CT below EMA',              lambda r: not r['above']),
 ('C  gap > +5',                  lambda r: r['gap']>5),
 ('D  gap 0 to +5',               lambda r: 0<r['gap']<=5),
 ('E  gap -5 to 0',               lambda r: -5<r['gap']<=0),
 ('F  gap < -5',                  lambda r: r['gap']<=-5),
 ('G  EMA rising (1 bar)',        lambda r: (r['em_slope'] or 0)>0),
 ('H  EMA falling (1 bar)',       lambda r: (r['em_slope'] or 0)<=0),
 ('I  EMA rising (3 bar)',        lambda r: (r['em_slope3'] or 0)>0),
 ('J  EMA above 50',              lambda r: r['em_above50']),
 ('K  EMA below 50',              lambda r: not r['em_above50']),
 ('L  CT turning up',             lambda r: (r['ct_slope'] or 0)>0),
 ('M  episode age <=2 bars',      lambda r: r['age'] is not None and r['age']<=2),
 ('N  episode age >=8 bars',      lambda r: r['age'] is not None and r['age']>=8),
 ('O  above AND EMA rising',      lambda r: r['above'] and (r['em_slope'] or 0)>0),
 ('P  above AND EMA above 50',    lambda r: r['above'] and r['em_above50']),
 ('Q  above AND gap<=5 (fresh)',  lambda r: r['above'] and r['gap']<=5),
 ('R  below AND EMA falling',     lambda r: (not r['above']) and (r['em_slope'] or 0)<=0),
 ('S  below AND CT turning up',   lambda r: (not r['above']) and (r['ct_slope'] or 0)>0),
 ('T  above AND diamond',         lambda r: r['above'] and r['dis']),
 ('U  above AND prime',           lambda r: r['above'] and r['prime']),
]
def row(S):
    if len(S)<8: return None
    up=[r['up60'] for r in S]; ret=[r['ret60'] for r in S]; dd=[r['dd60'] for r in S]
    return dict(n=len(S),
        t10=sum(1 for x in up if x>=10)/len(S)*100,
        t20=sum(1 for x in up if x>=20)/len(S)*100,
        t30=sum(1 for x in up if x>=30)/len(S)*100,
        mup=st.median(up), mret=st.median(ret), mdd=st.median(dd))
base=row(R)
print(f"BASELINE  all {base['n']} gated signals, 9 charts:  +10% {base['t10']:.0f}%  +20% {base['t20']:.0f}%  +30% {base['t30']:.0f}%  med up {base['mup']:+.1f}%  med ret60 {base['mret']:+.1f}%  med dd {base['mdd']:+.1f}%")
print()
print('POOLED ACROSS ALL CHARTS - every candidate, including the ones that do nothing')
print(f"{'feature':<28}{'n':>5}{'+10%':>7}{'+20%':>7}{'+30%':>7}{'med up':>9}{'med ret60':>11}{'med dd':>9}{'  edge vs base (+20%)':>22}")
res={}
for name,fn in FEATS:
    s=row([r for r in R if fn(r)])
    if not s: print(f'{name:<28}  (too few)'); continue
    res[name]=s
    edge=s['t20']-base['t20']
    print(f"{name:<28}{s['n']:>5}{s['t10']:>6.0f}%{s['t20']:>6.0f}%{s['t30']:>6.0f}%{s['mup']:>+8.1f}%{s['mret']:>+10.1f}%{s['mdd']:>+8.1f}%{edge:>+20.0f}")
