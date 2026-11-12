import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from model8 import *
import chk
LABEL = ("Computed signal, not a fill. No trade was taken. Entry quality only: "
         "the data has no exits, so this is not a strategy return or a track record.")
for st in ('REPLAY', 'CURRENT'):
    P = json.load(open(f'{chk.OUT}/code/page_{st}.json'))
    feed = json.load(open(STATES[st] + '/feed/ctzb_feed.json'))
    rd = P['read']
    liq = F(1) / F(33, 10) - F(5, 100)
    chk.add(st, 'page how-to-read', '3.3x with 5% maintenance liquidates at -25.3%', '25.3', rhaz(liq * 100, 1), 'how to read')
    for frag in ['How many past signals like this one rose 10% within 60 days of the entry close',
                 'without ever falling 25.3% below the entry close, where 3.3x leverage with 5% maintenance margin liquidates',
                 'The median best price within 60 days, from the entry close', 'The median deepest dip within 60 days',
                 'after it first falls 5%, 10%, 15% or 20%, how many of its past signals still rose 10% before ever falling 25.3%',
                 "The first fall at which this setup's odds drop below our 70% bar",
                 'Of the past signals that did not rise 10% within 60 days, how many went above entry at some point in the 60 days, and the median of their best price within the 60 days',
                 'over the next 60 days. They measure the quality of the entry, not a trading result']:
        chk.add(st, 'page how-to-read', f'text present: {frag[:60]}', frag in rd, True, 'how to read')
    # feed labels on every record
    objs = [('cards', x) for x in feed['cards']] + [('prints', x) for x in feed['prints']] + [('open_signals', x) for x in feed['open_signals']] + \
           [('grade_odds', x) for x in feed['grade_odds']] + [('if_it_misses', x) for x in feed['if_it_misses']] + [('past_paths', x) for x in feed['past_paths']] + \
           [('example_past_paths', feed['example_past_paths']), ('odds_fade', feed['odds_fade']), ('example_card', feed['example_card']), ('top', feed)] + \
           [('open_signals.card', x['card']) for x in feed['open_signals']]
    badl = [k for k, x in objs if x.get('label') != LABEL]
    chk.add(st, 'feed labels', f'every record carries the computed-signal label ({len(objs)} records)', len(badl), 0, 'entry quality only')
    chk.add(st, 'feed', 'cards_withheld / extras_withheld / alerts_withheld all false', f"{feed['cards_withheld']}/{feed['extras_withheld']}/{feed['alerts_withheld']}", 'False/False/False', 'feed state')
    chk.add(st, 'feed', 'scored_as_of', feed['scored_as_of'], str(TODAY[st]), 'feed state')
    chk.add(st, 'feed', 'market_regime', feed['market_regime'], 'Bullish' if gate(st)(TODAY[st]) else 'Bearish', 'regime')
    # shaded zones span entry slot to day-60 slot: hline x1/x2 equal entry and day-60 vline x
    for sid, d in P['sel'].items():
        for mode, ch in d['chart'].items():
            svg = ch['svg']
            v = {svg[i + 1]['text']: float(x['x1']) for i, x in enumerate(svg) if x['tag'] == 'line' and x.get('y1') == '24' and x.get('y2') == '480' and x['x1'] == x['x2']}
            xE = v.get('Entry', next((xv for t, xv in v.items() if t.startswith('Confirms')), None))
            x60 = v.get('Day 60')
            hl = [x for x in svg if x['tag'] == 'line' and x.get('x1') != x.get('x2') and x.get('stroke-width') == '2']
            bad = sum(1 for x in hl if abs(float(x['x1']) - xE) > 0.01 or abs(float(x['x2']) - x60) > 0.01)
            chk.add(st, f'page chart {sid} [{mode}]', 'level lines and zones run from the entry slot to the day-60 slot', bad, 0, 'chart zones')
            rects = [x for x in svg if x['tag'] == 'rect' and x.get('opacity') in ('0.07', '0.1')]
            badr = sum(1 for x in rects if abs(float(x['x']) - xE) > 0.01 or abs(float(x['x']) + float(x['width']) - x60) > 0.01)
            chk.add(st, f'page chart {sid} [{mode}]', 'shaded high/drop zones span entry slot to day-60 slot', badr, 0, 'chart zones', ok=badr == 0 and len(rects) == 2)
chk.dump('_extra.csv')
bad = [c for c in chk.CHECKS if c['ok'] == 'no']
print(len(chk.CHECKS), 'checks', len(bad), 'bad')
for c in bad[:40]: print(c)
