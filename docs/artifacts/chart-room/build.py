"""Build docs/artifacts/chart-room.html (29 Oct 2026): candles, CT RSI and Stoch from data/,
every regime-gated signal (grokpack), grades and outcomes from datasets/ledger.csv, open signals graded from datasets/liveread.csv, forming lows from datasets/cards.csv.
Artifact https://claude.ai/artifact/NFqH4MVWYjxZRHpakMUxgc.  python3 -I docs/artifacts/chart-room/build.py"""
import sys, os, json, csv, datetime as dt
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))); os.chdir(R); sys.path.insert(0, R)
import engine as E
H = os.path.dirname(os.path.abspath(__file__))
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed', 'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median', 'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
sys.path.insert(0, os.path.join(R, 'analysis'))
import grokpack as GP
import measures as MS
led = {(r['chart'], r['low']): r for r in csv.DictReader(open('datasets/ledger.csv'))}
cards = {c['chart']: c for c in csv.DictReader(open('datasets/cards.csv'))}
# open signals (inside their 60 days) are not in the ledger yet: their grade comes from the live stack
OPEN = {}
for r in csv.DictReader(open('datasets/liveread.csv')):
    s0 = r['subject']
    if ' open, day ' in s0 and r['status'] == 'grade':
        ch = ' '.join(s0.split()[:2]); d0 = s0.rsplit('entry ', 1)[1]
        g, _, names = r['read'][6:].partition(': ')
        OPEN[(ch, d0)] = (g, '' if names == 'no lenses' else names.replace(' + ', '; '))
rows, allsig = GP.build()
RM = {(r['a'], r['tf'], str(r['tdate'])): r for r in rows if 'm' in r}
stamp = open('datasets/stack_status.txt').readline()[:20].strip()   # when the pipeline last scored the data
today = max(E.load('data/ETH_1D.csv')['date'])
out = {'charts': {}, 'built': stamp}
plain = lambda names, sep: '; '.join(PLAIN[x] for x in names.split(sep) if x in PLAIN) or 'none'
for a in ('ETH', 'BTC'):
    for tf in ('1D', '2D', '3D', '5D'):
        b = E.load(f'data/{a}_{tf}.csv'); ct = E.rsi(b['close'], 14); em = E.ema(ct, 14); D = [str(d) for d in b['date']]
        st_ = E.stoch_of(ct, 14); k = E.sma(st_, 3); dd_ = E.sma(k, 3)
        r2 = lambda v: None if v is None else round(v, 2)
        bars = [[D[i], round(b['open'][i], 2), round(b['high'][i], 2), round(b['low'][i], 2), round(b['close'][i], 2), r2(ct[i]), r2(em[i]), r2(st_[i]), r2(k[i]), r2(dd_[i])] for i in range(len(D))]
        sig = []
        for s in allsig[(a, tf)]:
            low, d0 = str(s['tdate']), str(s['d0'])
            tags = ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))
            x = dict(low=low, entry=d0, px=round(s['entry'], 2), tags=tags, grade='', lenses='', state='done', day='', dayN='')
            L = led.get((f'{a} {tf}', low)); O = OPEN.get((f'{a} {tf}', d0)); m = RM.get((a, tf, low), {}).get('m')
            if L:
                x.update(grade=L['grade'], lenses=plain(L['lenses'], ' + '), day=L['daySurv10'], dayN=L['dayN'])
            elif O:
                x.update(grade=O[0], lenses=plain(O[1], '; ') if O[1] else 'none')
            if m:
                x.update(best=round(m['up'], 1), dd=round(m['dd'], 1), dip=round(m['ddpk'], 1), surv=bool(MS.surv10(m)), r20=m['up'] >= 20)
            else:
                x.update(state='open', age=(today - s['d0']).days)
            sig.append(x)
        out['charts'][f'{a} {tf}'] = dict(bars=bars, sig=sig, card=cards.get(f'{a} {tf}'))
html = open(os.path.join(H, 'head.html')).read() + 'const DATA=' + json.dumps(out, separators=(',', ':')) + ';' + open(os.path.join(H, 'tail.html')).read()
open('docs/artifacts/chart-room.html', 'w').write(html); print('wrote docs/artifacts/chart-room.html', len(html))
