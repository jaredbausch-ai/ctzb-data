import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from model8 import *
import chk
for st in ('REPLAY', 'CURRENT'):
    P = json.load(open(f'{chk.OUT}/code/page_{st}.json'))
    feed = json.load(open(STATES[st] + '/feed/ctzb_feed.json'))
    ex = json.load(open(STATES[st] + '/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
    for sid, d in P['sel'].items():
        for mode, ch in d['chart'].items():
            svg = ch['svg']; loc = f'page chart {sid} [{mode}]'
            g = [(float(x['y']) - 5, float(x['text'][1:].replace(',', ''))) for x in svg if x['tag'] == 'text' and x.get('x') == '968']
            (y1, p1), (y2, p2) = g[0], g[-1]
            k = (y2 - y1) / (p2 - p1)
            badg = sum(1 for y, p in g if abs(y1 + (p - p1) * k - y) > 0.01)
            chk.add(st, loc, f'price gridline labels on one scale ({len(g)})', badg, 0, 'axis scaling')
            # candle bodies and colours, from my own bars
            if sid == 'example':
                myb = {b['d']: b for b in all_signals(st)[('ETH', '2D')]['bars']}
                bars = [myb[fdate(b['t'])] for b in ex['bars']]
            else:
                a, tf = sid.split('-')[0], sid.split('-')[1]
                bars = all_signals(st)[(a, tf)]['bars'][-70:]
            Y = lambda p: y1 + (float(p) - p1) * k
            rects = [x for x in svg if x['tag'] == 'rect' and x.get('css', '').startswith('fill: var(--high)') or (x['tag'] == 'rect' and x.get('css', '').startswith('fill: var(--drop)'))]
            rects = [x for x in rects if 'opacity' not in x and 'rx' not in x]
            bad = 0
            for i, x in enumerate(rects):
                b = bars[i]
                top = Y(max(b['o'], b['c'])); hgt = max(1, abs(Y(b['o']) - Y(b['c'])))
                col = 'var(--high)' if b['c'] >= b['o'] else 'var(--drop)'
                if abs(float(x['y']) - top) > 0.02 or abs(float(x['height']) - hgt) > 0.02 or col not in x['css']: bad += 1
            chk.add(st, loc, f'candle bodies at my open/close, colour by close vs open ({len(rects)})', bad, 0, 'candle position')
chk.dump('_extra2.csv')
bad = [c for c in chk.CHECKS if c['ok'] == 'no']
print(len(chk.CHECKS), 'checks', len(bad), 'bad')
for c in bad[:20]: print(c)
