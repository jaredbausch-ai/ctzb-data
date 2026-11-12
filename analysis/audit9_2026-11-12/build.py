"""Build my own signal set, ledger and measures for one state. Pickled for the comparison scripts."""
import csv, datetime as dt, json, os, pickle, sys, statistics as st, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *

STATE = sys.argv[1]
NAME = os.path.basename(STATE.rstrip('/'))
feed = json.load(open(os.path.join(STATE, 'feed', 'ctzb_feed.json')))
NOW = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
G = gate(STATE)
TODAY = NOW.date()

daily = {a: Daily(STATE, a, NOW) for a in ('ETH', 'BTC')}

# funding availability (ETH ledger membership)
def funding(a):
    fo, fm = {}, {}
    for r in csv.DictReader(open(os.path.join(STATE, 'data', 'derivs', f'{a}_funding_daily.csv'))):
        d = dt.date.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): fo[d] = float(v)
        v2 = r.get('funding_mean')
        if v2 not in ('', None): fm[d] = float(v2)
    return fo, fm
FUND = {a: funding(a) for a in ('ETH', 'BTC')}

def fund_ok(a, d):
    fo, fm = FUND[a]
    if d not in fo: return False
    back = sum(1 for k in range(1, 91) if d - dt.timedelta(days=k) in fo)
    if back < 60: return False
    w7 = sum(1 for k in range(7) if d - dt.timedelta(days=k) in fm)
    w7b = sum(1 for k in range(7) if d - dt.timedelta(days=14 + k) in fm)
    return w7 >= 5 and w7b >= 5

# vol ratio for scaled20 (365-day pstdev of daily log returns at entry / 2016-21 median)
VOL = {}
for a in ('ETH', 'BTC'):
    b = load(STATE, a, '1D', clamp=False); c = [x['c'] for x in b]
    lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
    vol = {b[i]['date']: st.pstdev(lr[i - 364:i + 1]) for i in range(365, len(c))}
    med = st.median(v for k, v in vol.items() if k.year <= 2021)
    VOL[a] = (vol, med)

SIG = {}       # (asset, tf) -> list of all troughs with status
for a in ('ETH', 'BTC'):
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        bars = load(STATE, a, tf)
        tr, ct, k = troughs(bars)
        lst = []
        for s in tr:
            if s['ei'] >= len(bars):
                continue
            cb = bars[s['ei']]
            s.update(a=a, tf=tf, chart=f'{a} {tf}', tdate=bars[s['ti']]['date'], tend=bars[s['ti']]['end'],
                     copen=cb['date'], d0=cb['end'], e=cb['c'], closed=cb['end'] < TODAY,
                     gated=bool(G(bars[s['ti']]['date'])), tlow=bars[s['ti']]['l'])
            dd = daily[a]
            s['dclose'] = dd.b[dd.pos[s['d0']]]['c'] if s['d0'] in dd.pos else None
            s['m'] = measure(dd, s['d0'], s['e']) if s['closed'] else None
            v = VOL[a][0].get(s['d0'])
            s['sc20'] = None if (v is None or s['m'] is None) else s['m']['up'] >= 20 * v / VOL[a][1]
            s['fund_ok'] = fund_ok(a, s['d0'])
            lst.append(s)
        SIG[(a, tf)] = dict(sig=lst, bars=bars, ct=ct, k=k)

pickle.dump(dict(NOW=NOW, SIG=SIG), open(f'/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit9/sig_{NAME}.pkl', 'wb'))
print(NAME, NOW, {k: (len(v['sig']), sum(s['gated'] and s['closed'] for s in v['sig'])) for k, v in SIG.items()})
