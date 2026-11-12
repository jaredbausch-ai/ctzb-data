"""Build my own signal universe and per-signal 60-day measurements for one state; pickle it."""
import pickle, sys, datetime as dt
from mine import *

state = sys.argv[1]
root = STATES[state]; now = NOWS[state]
gate = gate_fn(root)
out = {'sig': {}, 'charts': {}}
day = {a: Daily(load(root, a, '1D')) for a in ('ETH', 'BTC')}
dayc = {a: Daily(load(root, a, '1D', clamp=True)) for a in ('ETH', 'BTC')}
fund = {a: funding(root, a) for a in ('ETH', 'BTC')}
vr = {a: vol_ratio_fn(root, a) for a in ('ETH', 'BTC')}
for a in ('ETH', 'BTC'):
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        bars = load(root, a, tf)
        sig, ct, k = signals(bars, gate)
        sig_c, _, _ = signals(bars, gate, gate_on='confirm')
        for s, sc in zip(sig, sig_c):
            s['gated_conf'] = sc['gated']
            s['a'] = a; s['tf'] = tf; s['chart'] = f'{a} {tf}'
            if s['d0'] is not None:
                # entry close equals the daily close on d0?
                j = day[a].pos.get(s['d0'])
                s['daily_close_d0'] = day[a].b[j]['c'] if j is not None else None
                w = window(day[a], s['d0'], s['entry'], now)
                s['m'] = metrics(w, s['d0'], s['entry']) if w else None
                wc = window(dayc[a], s['d0'], s['entry'], now)
                s['mc'] = metrics(wc, s['d0'], s['entry']) if wc else None
                s['funded'] = eth_funded(*fund[a], s['d0']) if a == 'ETH' else True
                s['vr'] = vr[a](s['d0'])
        out['sig'][(a, tf)] = sig
        out['charts'][(a, tf)] = dict(bars=bars, ct=ct, k=k)
out['day'] = {a: day[a].b for a in day}
pickle.dump(out, open(f'{S}/audit3/universe_{state}.pkl', 'wb'))
for key, v in out['sig'].items():
    g = [s for s in v if s['gated']]
    print(key, 'troughs', len(v), 'gated', len(g), 'scored', sum(1 for s in g if s.get('m')))
