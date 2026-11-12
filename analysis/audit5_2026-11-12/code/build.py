"""Audit 5: build my own record of every signal for one state, from raw candles.
Pickled to audit5/work/<state>.pkl for the checkers."""
import sys, os, pickle, json, datetime as dt
from fractions import Fraction as Fr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as K

S = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'
STATES = {'REPLAY': (f'{S}/a5/replay_0414', dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc)),
          'CURRENT': (f'{S}/a5/current', None)}
TFS = ('1D', '2D', '3D', '5D', '8D')


def now_of(name):
    root, now = STATES[name]
    if now is None:
        f = json.load(open(f'{root}/feed/ctzb_feed.json'))
        now = dt.datetime.fromisoformat(f['generated_at'].replace('Z', '+00:00'))
    return root, now


def build(name):
    root, now = now_of(name)
    day = {a: K.Daily(root, a) for a in ('ETH', 'BTC')}
    sig = {}
    charts = {}
    for a in ('ETH', 'BTC'):
        for tf in TFS:
            ss, b, ct, kk = K.signals(root, a, tf, now)
            charts[(a, tf)] = dict(b=b, ct=ct, K=kk)
            for s in ss:
                dd = day[a]
                # entry close vs the daily close on the entry date
                db = dd.bar(s['d0'])
                s['daily_close_d0'] = db[2] if db else None
                s['complete'] = s['confirmed'] and dd.complete(s['d0'], now)
                if s['complete']:
                    w = dd.window(s['d0'], now)
                    s['w'] = w
                    s['e'] = s['entry']
                    s['m'] = K.measure(s['entry'], w)
                    s['vr'] = K.vol_ratio(root, a, s['d0'])
                    s['scaled20'] = None if s['vr'] is None else float(s['m']['up']) >= 20 * s['vr']
                # trough bar's low day: lowest DAILY low within the bar's own days
                ti = s['ti']; t0 = b.D[ti]; t1 = b.end_date(ti)
                cand = []
                d = t0
                while d <= t1:
                    x = dd.bar(d)
                    if x: cand.append((x[1], d))
                    d += K.ONE_DAY
                s['low_day'] = min(cand)[1] if cand else None
                s['low_day_ties'] = [d for l, d in cand if cand and l == min(cand)[0]]
            sig[(a, tf)] = ss
    return dict(root=root, now=now, sig=sig, charts=charts)


if __name__ == '__main__':
    os.makedirs(f'{S}/audit5/work', exist_ok=True)
    for nm in STATES:
        r = build(nm)
        ch = r.pop('charts')
        # keep bars for later (pickle-able)
        r['bars'] = {k: v['b'] for k, v in ch.items()}
        r['ct'] = {k: v['ct'] for k, v in ch.items()}
        pickle.dump(r, open(f'{S}/audit5/work/{nm}.pkl', 'wb'))
        n = sum(len(v) for v in r['sig'].values())
        print(nm, r['now'], n, 'gated signals', sum(1 for v in r['sig'].values() for s in v if s['complete']), 'complete')
