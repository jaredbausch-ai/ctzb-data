"""Label (item 9/10) and doc/code rows, then all_checks.csv and disagreements.csv."""
import csv, datetime as dt, json, os, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import rnd, median, pct
from mine import State
from check import Checks

OUT = os.path.dirname(os.path.abspath(__file__))
SC = os.path.dirname(OUT)
STATES = {'replay': (f'{SC}/audit4_replay_0414', '2026-11-12T04:14:00Z'), 'current': (f'{SC}/audit4_current', '2026-11-12T15:41:52Z')}
rows = []
for tag, (sdir, now_s) in STATES.items():
    rows += json.load(open(f'{OUT}/checks_{tag}.json')) + json.load(open(f'{OUT}/pagechecks_{tag}.json'))
    cap = json.load(open(f'{OUT}/page_{tag}.json')); notes = json.load(open(f'{OUT}/notes_{tag}.json'))
    now = dt.datetime.fromisoformat(now_s.replace('Z', '+00:00')); S = State(sdir, now); feed = S.feed
    C = Checks(tag)
    # "median peak before they failed" / "Misses: median peak first": literal reading = best price before the deepest low
    L = {(r['chart'], r['entry']): r for r in S.ledger}
    from mine import all_rows
    led = []
    for r in all_rows(S):
        x = L.get((r['chart'], str(r['d0'])))
        if x and r['m']: r['grade'] = x['grade']; led.append(r)
    def lit(ms):
        return rnd(median([pct(max(S.day[r['a']].h[j] for k, j in r['m']['w'] if k <= r['m']['ddday']), r['entry']) for r in ms]), 1)
    shown_pairs = []
    for sel in cap['selections']:
        sid = sel['sel']
        if sid == 'example':
            ms = [r for r in led if r['a'] == 'ETH' and r['grade'] == 'A+' and not r['m']['r10'] and r['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
        else:
            c = next((x for x in feed['cards'] if x['signal_id'] == sid), None) or next(o for o in feed['open_signals'] if o['signal_id'] == sid)['card']
            ms = [r for r in led if r['a'] == c['asset'] and r['grade'] == c['grade'] and not r['m']['r10']]
        lines = [x.strip() for x in sel['card'].split('\n') if x.strip()]
        t = lines[lines.index('If it misses: up first') + 1]
        shown = t.split('median peak ')[1]
        mine = lit(ms); exp = ('+' if mine > 0 else '') + f'{mine:.1f}%'.replace('-', '−')
        C.add(f'page card {sid}', '"If it misses ... median peak before they failed" (How to read): peak BEFORE the deepest low', shown, exp,
              'the figure is the best price over all 60 days, which for some misses came after the deepest drop')
    for a in ('ETH', 'BTC'):
        rec = cap['record']['all']['sum'].split('\n'); rec = [x.strip() for x in rec if x.strip()]
        i0 = rec.index(a); blk = rec[i0:i0 + 12]; shown = blk[blk.index('Misses: median peak first') + 1]
        ms = [r for r in led if r['a'] == a and r['grade'] == 'A+' and not r['m']['r10']]
        mine = lit(ms); exp = ('+' if mine > 0 else '') + f'{mine:.1f}%'.replace('-', '−')
        C.add(f'page past signals summary {a}', '"Misses: median peak first": median peak before the deepest low', shown, exp,
              'the figure is the best price over all 60 days, which for some misses came after the deepest drop')
    # "Best setup forming today" on every below-grade forming card
    forming = [c for c in feed['cards']]
    best = max(forming, key=lambda c: c['rose10_within60d_pct'])['signal_id'] if forming else None
    for sel in cap['selections']:
        if 'Best setup forming today' in sel['card']:
            C.add(f"page card {sel['sel']}", 'says "Best setup forming today"', 'best', 'best' if sel['sel'] == best else f'not the best (best is {best})',
                  'every below-grade forming card carries the line, not only the best one')
    # trough date on multi-day forming cards
    for sid, v in notes['trough_low_printed_on'].items():
        sel = next((s for s in cap['selections'] if s['sel'] == sid), None)
        if not sel or not any(c['signal_id'] == sid for c in feed['cards']): continue
        for where, txt in (('card header', sel['card']), ('chart subtitle', sel['chart']['bAlert']['sub']),
                           ('chart low label', ' '.join(t['text'] for t in sel['chart']['bAlert']['texts'] if t['text'].startswith('Low ')))):
            d = dt.date.fromisoformat(v['bar_open']); d2 = dt.date.fromisoformat(v['printed_on'][0])
            sh = f"Low {d.day} {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sept','Oct','Nov','Dec'][d.month-1]} {d.year}"
            ok = sh in txt
            C.add(f'page {where} {sid}', 'date of the low', sh if ok else txt[:60], f"Low {d2.day} Nov {d2.year} (the ${v['bar_low']:,.2f} low printed on {d2})",
                  'the 2D trough bar is labelled by its OPEN date; the low itself printed on the second day of the bar')
    # review banner
    nontop = [c for c in feed['cards'] if c['grade'] != 'A+']
    C.add('page review banner', '"Members see top-grade setups only"', 'top-grade only', 'top-grade only' if not nontop else f'{len(nontop)} below-grade forming setups are shown',
          'the picker and card show below-grade forming setups')
    # entry-quality wording: no member-facing text reads as a return / trade taken / track record
    import re
    alltxt = ' '.join([cap['initial_card'] or ''] + [s['card'] for s in cap['selections']] + [m['side'] + m['sub'] for s in cap['selections'] for m in s['chart'].values()]
                      + [cap['record']['all']['fine'], cap['read'], cap['prev_section']])
    bad = [w for w in ('profit', 'return of', 'win rate', 'P&L', 'we bought', 'we sold', 'took the trade', 'our trades', 'track record of') if w.lower() in alltxt.lower()]
    C.add('page (all views)', 'words that read as a return, a trade taken or a track record', ';'.join(bad), '', 'wording')
    C.add('page (all views)', 'card/record footers say entry quality only, not a track record',
          'yes' if all('not a trade or a track record' in s['card'] for s in cap['selections']) and 'not a return or a track record' in cap['record']['all']['fine'] else 'no', 'yes', 'wording')
    rows += C.rows

# documents vs code (state-independent)
D = Checks('docs')
D.add('docs/CARD_SPEC.md "Big number"', 'big number definition', 'surv10: rose 10% AND never fell 25.3%', 'page and CONTEXT (+10% switch): reach10, rose 10% within 60 days; surv10 is the line under it',
      'CARD_SPEC (and FEED_SPEC card table: surv10 "The big number") not updated for the +10% headline')
nt = json.load(open(f'{OUT}/notes_current.json'))
D.add('refresh.py walk-forward tier docstring', 'tier "as it stood on 1 January ... using only data available by then"', 'code: signals confirmed before 1 Jan, scored on 60-day outcomes that end after 1 Jan',
      'outcomes known by 1 Jan only: tier adds ETH 2D prime dot; odds_fade red-on-day-10 63% (n 64) vs 62% (n 58); shallower-than-2% 91%/85% (n 34) vs 90%/83% (n 29); worse-than-20% 42%/37% (n 19) vs 44%/44% (n 16)',
      'code and docstring disagree; feed follows the code')
D.add('docs/FEED_SPEC.md top-level table', 'open_signals source', 'forward.csv, status open', 'datasets/open.csv (stack_live.py), per the 12 Nov section and the code', 'stale row')
D.add('CONTEXT.md in both states', 'Audit #3 corrections paragraph', 'absent', 'present in /home/claude/ctzb-data/CONTEXT.md', 'the frozen states carry an older CONTEXT.md than the working repo')
D.add('docs/CARD_SPEC.md ladder row', 'ladder outcome wording', 'still rose 10% without falling 25.3%', 'code and page: rose 10% BEFORE falling 25.3% (some later fell 25.3% inside the 60 days, e.g. example 5% row: 2 signals)', 'wording')
D.add('docs/CARD_SPEC.md wording', 'sample unit', 'N past trades / (N trades) / trades that got there', 'signals (Audit #3 label rule; the page says signals)', 'stale wording')
rows += D.rows

hdr = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
with open(f'{OUT}/all_checks.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(rows)
bad = [r for r in rows if r['ok'] != 'yes']
with open(f'{OUT}/disagreements.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(bad)
import collections
print(len(rows), 'comparisons;', len(bad), 'disagreements')
for r in bad: print(r['state'], '|', r['location'], '|', r['label'], '|', r['shown'][:70], '|', r['yours'][:90])
cat = collections.Counter()
for r in rows:
    loc = r['location']
    k = ('1 ledger' if loc.startswith('ledger') else '2 grade_odds' if 'grade_odds' in loc else '3 if_it_misses' if 'if_it_misses' in loc else '4 odds_fade' if 'odds_fade' in loc
         else '5 cards' if loc.startswith('feed card') or loc.startswith('feed example') or (loc.startswith('feed open_signal') and 'card' in loc) else '6 open_signals' if 'open_signal' in loc
         else '7 past_paths' if 'past_paths' in loc else '8 page' if loc.startswith('page') else 'docs' if r['state'] == 'docs' else 'other')
    cat[(k, r['ok'])] += 1
for k in sorted(cat): print(k, cat[k])
