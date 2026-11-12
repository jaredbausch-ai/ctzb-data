"""Check 1: every ledger row against raw candles. Writes ledger_recomputed.csv and ledger_diffs.csv."""
import csv, json, os, datetime as dt, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C

OUT = os.path.dirname(os.path.abspath(__file__))
led = list(csv.DictReader(open(os.path.join(C.REPO, 'datasets', 'ledger.csv'))))
G = C.gate()

T = {}
for a in ('ETH', 'BTC'):
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        T[(a, tf)] = C.troughs(a, tf)

diffs, rec, notes = [], [], []
n_checked = 0
for r in led:
    a, tf = r['chart'].split()
    tr, bars = T[(a, tf)]
    e_date = dt.date.fromisoformat(r['entry'])
    # bar whose period ends at the entry date
    idx = [i for i in range(len(bars)) if C.bar_end(bars, i, tf) == e_date]
    if not idx:
        diffs.append(dict(chart=r['chart'], entry=r['entry'], field='entry bar', shown='', mine='no bar ends on this date', cause='unmatched'))
        continue
    i = idx[0]
    close = bars[i]['c']
    if abs(round(close, 2) - float(r['entryPrice'])) > 0.006:
        diffs.append(dict(chart=r['chart'], entry=r['entry'], field='entryPrice', shown=r['entryPrice'], mine=round(close, 2), cause='close mismatch'))
    # is it ti+3 of a pivot low dated `low`, and gate on?
    t = next((x for x in tr if x['ei'] == i), None)
    if t is None:
        diffs.append(dict(chart=r['chart'], entry=r['entry'], field='signal', shown='in ledger', mine='bar is not ti+3 of any CT pivot low', cause='entry definition'))
    else:
        if str(t['tdate']) != r['low']:
            diffs.append(dict(chart=r['chart'], entry=r['entry'], field='low', shown=r['low'], mine=str(t['tdate']), cause='trough date'))
        if not G(t['tdate']):
            diffs.append(dict(chart=r['chart'], entry=r['entry'], field='gate', shown='kept', mine='gate off at trough date', cause='gate'))
        bk_ok = r['tags'].split(' + ')[0] == t['bk']
        if not bk_ok:
            diffs.append(dict(chart=r['chart'], entry=r['entry'], field='bucket', shown=r['tags'], mine=t['bk'], cause='bucket'))
        dia = 'filled diamond' if t['strong'] else 'hollow diamond' if t['dis'] else None
        has = [x for x in r['tags'].split(' + ')[1:]]
        mine_tags = ([dia] if dia else []) + (['prime dot'] if t['prime'] else [])
        if has != mine_tags:
            diffs.append(dict(chart=r['chart'], entry=r['entry'], field='tags', shown=r['tags'], mine=' + '.join([t['bk']] + mine_tags), cause='tag'))
    e = float(r['entryPrice'])
    m = C.fwd(a, e_date, close)
    mr = C.fwd(a, e_date, close, clamp=False)
    if m is None:
        diffs.append(dict(chart=r['chart'], entry=r['entry'], field='window', shown='complete', mine='60 daily bars not all present', cause='window'))
        continue
    n_checked += 1
    yn = lambda b: 'yes' if b else 'no'
    mine = dict(reached10=yn(m['up'] >= 10), reached15=yn(m['up'] >= 15), reached20=yn(m['up'] >= 20), touched30=yn(m['dd'] <= -30),
                surv10=yn(C.surv10(m)), bestMove=m['up'], maxDrawdown=m['dd'], dipBeforeHigh=m['ddpk'], return60d=m['ret'],
                daysToHigh=m['dpk'])
    for k, v in mine.items():
        s = r[k]
        if isinstance(v, str):
            if s != v:
                diffs.append(dict(chart=r['chart'], entry=r['entry'], field=k, shown=s, mine=v, cause=f"up {m['up']:.3f} dd {m['dd']:.3f}"))
        elif k == 'daysToHigh':
            if int(s) != v:
                diffs.append(dict(chart=r['chart'], entry=r['entry'], field=k, shown=s, mine=v, cause='day of max high'))
        else:
            if abs(float(s) - v) > 0.1 + 1e-9:
                diffs.append(dict(chart=r['chart'], entry=r['entry'], field=k, shown=s, mine=round(v, 2), cause=''))
    # raw (unclamped) candles: does the clamp matter for this row?
    if mr and (abs(mr['dd'] - m['dd']) > 0.05 or abs(mr['up'] - m['up']) > 0.05):
        notes.append(dict(chart=r['chart'], entry=r['entry'], clamped_dd=round(m['dd'], 1), raw_dd=round(mr['dd'], 1), clamped_up=round(m['up'], 1), raw_up=round(mr['up'], 1)))
    rec.append(dict(asset=a, chart=r['chart'], entry=r['entry'], grade=r['grade'], lenses=r['lenses'], year=r['year'], e=close,
                    up=m['up'], dd=m['dd'], ret=m['ret'], ddpk=m['ddpk'], dpk=m['dpk'], ddday=m['ddday'], t10=m['t10'], t20=m['t20'],
                    surv10=C.surv10(m), surv10_25=m['up'] >= 10 and m['dd'] > -25.0, lastday=str(m['lastday']),
                    closes=json.dumps([round(x, 6) for x in m['closes']]), highs=json.dumps(m['highs']), lows=json.dumps(m['lows'])))

with open(os.path.join(OUT, 'ledger_recomputed.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rec[0].keys())); w.writeheader(); w.writerows(rec)
with open(os.path.join(OUT, 'ledger_diffs.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['chart', 'entry', 'field', 'shown', 'mine', 'cause']); w.writeheader(); w.writerows(diffs)

# membership: gated signals with a complete 60-day window not in the ledger (graded charts)
inled = {(r['chart'], r['entry']) for r in led}
miss = []
lastday = {a: C.daily(a)[0][-1]['d'] for a in ('ETH', 'BTC')}
for (a, tf), (tr, bars) in T.items():
    if tf == '8D': continue
    for t in tr:
        if not G(t['tdate']): continue
        if t['d0'] + dt.timedelta(days=60) > lastday[a]: continue
        if (f'{a} {tf}', str(t['d0'])) not in inled:
            miss.append((a, tf, str(t['d0'])))
from collections import Counter
print('rows checked', n_checked, 'of', len(led))
print('diffs', len(diffs), Counter(d['field'] for d in diffs))
print('clamp-sensitive rows', len(notes), notes[:5])
print('gated signals not in ledger', Counter((a, tf, d[:4] < '2020') for a, tf, d in miss))
print('BTC missing', [m for m in miss if m[0] == 'BTC'][:20])
# entry-date gating vs trough-date gating
alt = sum(1 for (a, tf), (tr, b) in T.items() if tf != '8D' for t in tr if G(t['tdate']) != G(t['d0']))
print('signals where gate at trough date != gate at confirmation date', alt)
# rows whose window ends on the last (still-open) daily bar
print('rows whose 60th day is the last daily bar in the file', [(x['chart'], x['entry']) for x in rec if x['lastday'] == str(lastday[x['asset']])])
print('surv10 differs between -25.3 and -25.0', [(x['chart'], x['entry'], round(x['dd'], 2)) for x in rec if x['surv10'] != x['surv10_25']])
json.dump(dict(n_checked=n_checked, n_led=len(led), diffs=len(diffs), clamp=notes,
               missing=miss), open(os.path.join(OUT, 'check1.json'), 'w'), default=str)
