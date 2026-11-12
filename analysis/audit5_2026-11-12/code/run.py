import sys, os, pickle, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rec
import c_ledger

S = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'
OUT = f'{S}/audit5'
CTX = {}
for st in ('REPLAY', 'CURRENT'):
    W = pickle.load(open(f'{OUT}/work/{st}.pkl', 'rb'))
    root = W['root']
    feed = json.load(open(f'{root}/feed/ctzb_feed.json'))
    pairs, grec = c_ledger.check(st, W, root)
    CTX[st] = dict(W=W, root=root, feed=feed, pairs=pairs, grec=grec)
    mods = [m for m in sys.argv[1:]]
    for m in mods:
        __import__(m).check(st, CTX[st])
rec.write(OUT)
bad = [c for c in rec.CHECKS if c['ok'] == 'no']
print(len(rec.CHECKS), 'checks', len(bad), 'disagreements')
import collections
print(collections.Counter((c['state'], c['location'], c['cause']) for c in bad).most_common(40))
