"""Build my own model of one state: every gated signal, its measures, ledger membership and the
derived tables. python3 build.py <state_dir> <now_iso> <out.pkl>"""
import sys, os, pickle, datetime as dt, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L

root, now_iso, outp = sys.argv[1:4]
now = dt.datetime.fromisoformat(now_iso.replace('Z', '+00:00'))
M = L.Market(root, now)
fm = L.funding_maps(root)
sig = {}
notes = []
for a in ('ETH', 'BTC'):
    for tf in (1, 2, 3, 5, 8):
        s, ct, K = M.troughs(a, tf)
        sig[(a, tf)] = s
        for x in s:
            if x['closed'] and not x['nxt_ok']:
                notes.append(f'{x["ch"]} {x["d0"]}: next bar open != bucket close + 1')
            if x['closed']:
                i = M.pos[a].get(x['d0'])
                if i is None:
                    notes.append(f'{x["ch"]} {x["d0"]}: no daily bar on entry date')
                elif abs(M.day[a]['close'][i] - x['entry']) > 1e-9:
                    notes.append(f'{x["ch"]} {x["d0"]}: chart close {x["entry"]} != daily close {M.day[a]["close"][i]}')
# measures
for k, lst in sig.items():
    for x in lst:
        x['m'] = M.measure(x['a'], x['d0'], x['entry']) if x['closed'] else None
        x['vr'] = M.volratio(x['a'], x['d0']) if x['closed'] else None
        if x['m'] is not None:
            x['sc'] = None if x['vr'] is None else x['m']['up'] >= 20 * x['vr']
        x['member'] = bool(x['m']) and x['tf'] in (1, 2, 3, 5) and (x['a'] != 'ETH' or L.eth_member(fm, x['d0']))
clamps = {f'{a} {tf}D': M.chart(a, tf)['clamps'] for a in ('ETH', 'BTC') for tf in (1, 2, 3, 5, 8)}
pickle.dump(dict(sig=sig, notes=notes, clamps=clamps, today=M.today, now=now), open(outp, 'wb'))
print('signals', {f'{a}{tf}': len(v) for (a, tf), v in sig.items()}, 'members', sum(x['member'] for v in sig.values() for x in v))
print('notes', notes[:20], len(notes))
print('clamps', {k: v for k, v in clamps.items() if v})
