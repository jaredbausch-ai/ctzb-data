"""Build docs/artifacts/chart-room.html (dry run, 29 Oct 2026): candles + CT RSI from data/,
every graded signal from datasets/ledger.csv, forming lows from datasets/cards.csv.
Artifact https://claude.ai/artifact/NFqH4MVWYjxZRHpakMUxgc.  python3 -I docs/artifacts/chart-room/build.py"""
import sys, os, json, csv, datetime as dt
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))); os.chdir(R); sys.path.insert(0, R)
import engine as E
H = os.path.dirname(os.path.abspath(__file__))
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed', 'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median', 'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
led = list(csv.DictReader(open('datasets/ledger.csv'))); cards = {c['chart']: c for c in csv.DictReader(open('datasets/cards.csv'))}
stamp = open('datasets/stack_status.txt').readline()[:20].strip()   # when the pipeline last scored the data
out = {'charts': {}, 'built': stamp}
for a in ('ETH', 'BTC'):
    for tf in ('1D', '2D', '3D', '5D'):
        b = E.load(f'data/{a}_{tf}.csv'); ct = E.rsi(b['close'], 14); em = E.ema(ct, 14); D = [str(d) for d in b['date']]
        bars = [[D[i], round(b['open'][i], 2), round(b['high'][i], 2), round(b['low'][i], 2), round(b['close'][i], 2), None if ct[i] is None else round(ct[i], 2), None if em[i] is None else round(em[i], 2)] for i in range(len(D))]
        sig = [dict(low=r['low'], entry=r['entry'], px=float(r['entryPrice']), tags=r['tags'], grade=r['grade'], lenses='; '.join(PLAIN[x] for x in r['lenses'].split(' + ') if x in PLAIN) or 'none',
                    best=float(r['bestMove']), dd=float(r['maxDrawdown']), dip=float(r['dipBeforeHigh']), surv=r['surv10'] == 'yes', r20=r['reached20'] == 'yes', day=r['daySurv10'], dayN=r['dayN'])
               for r in led if r['chart'] == f'{a} {tf}']
        out['charts'][f'{a} {tf}'] = dict(bars=bars, sig=sig, card=cards.get(f'{a} {tf}'))
html = open(os.path.join(H, 'head.html')).read() + 'const DATA=' + json.dumps(out, separators=(',', ':')) + ';' + open(os.path.join(H, 'tail.html')).read()
open('docs/artifacts/chart-room.html', 'w').write(html); print('wrote docs/artifacts/chart-room.html', len(html))
