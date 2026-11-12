import pickle, sys, json, os, csv
sys.path.insert(0, '.')
from core import *
for NAME in ('replay_0414', 'current'):
    P = pickle.load(open(f'sig_{NAME}.pkl', 'rb')); SIG = P['SIG']
    feed = json.load(open(f'../a9/{NAME}/feed/ctzb_feed.json'))
    shown = sorted(c['signal_id'] for c in feed['cards'])
    mine = []
    for (a, tf), V in SIG.items():
        ct = V['ct']; bars = V['bars']; n = len(bars)
        for back in (1, 2, 3):
            ti = n - 1 - back
            v = ct[ti]
            if all(ct[j] > v for j in range(ti - 3, ti)) and all(ct[j] >= v for j in range(ti + 1, n)):
                need = 3 - back + 1 - 1
                need = 3 - ((n - 1) - ti)
                d = bars[-1]['end']
                for _ in range(need): d = bucket_end(d + dt.timedelta(days=1), tf)
                strict = all(ct[j] > v for j in range(ti + 1, n))
                mine.append(f'{a}-{tf}-{d}' + ('' if strict else ' (tie)'))
                break
    print(NAME, 'feed', shown, 'mine', sorted(mine))
