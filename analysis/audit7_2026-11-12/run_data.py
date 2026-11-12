import datetime as dt, pickle, collections
import audit as A
from build import State
res = {}
for name, clk in (('replay_0414', dt.datetime(2026,11,12,4,14,tzinfo=dt.timezone.utc)), ('current', dt.datetime(2026,11,12,17,7,11,tzinfo=dt.timezone.utc))):
    S = State(name, clk); F = S.feed()
    n0 = len(A.CK.rows)
    A.check_ledger(S); A.check_grade_odds(S, F); A.check_misses(S, F); A.check_fade(S, F); A.check_all_paths(S, F); A.check_cards(S, F)
    # market filter shown on the page
    A.CK.add(name, 'feed top level', 'market_regime', F['market_regime'], 'Bullish' if S.gate(S.today) else 'Bearish', 'value')
    A.CK.add(name, 'feed top level', 'scored_as_of', F['scored_as_of'], str(S.today), 'value')
    rows = A.CK.rows[n0:]
    print(name, len(rows), 'checks', sum(r['ok']=='no' for r in rows), 'bad')
    print(collections.Counter(r['location'].split()[0] for r in rows))
    res[name] = dict(miss_alt=S.miss_alt, kill=getattr(S,'kill',{}), fade_n=len(S.fade_pool), keep=sorted(S.keep),
                     led=[(s['chart'], str(s['d0']), s['grade'], s['entry'], s['m']['up'], s['m']['dd'], s['m']['ret'], s['m']['dpk'], s['m']['ddpk']) for s in S.led],
                     example_n=len(S.example_G))
pickle.dump(A.CK.rows, open('data_checks.pkl','wb')); pickle.dump(res, open('data_res.pkl','wb'))
for r in A.CK.rows:
    if r['ok']=='no': print(r)
