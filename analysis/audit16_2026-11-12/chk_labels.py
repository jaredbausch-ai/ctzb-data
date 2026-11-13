"""Checks 9-10 on the frozen states: labels on every feed record; member-facing words on the rendered page."""
import json, re, csv
from common import *
out = []
for name in ('REPLAY', 'CURRENT'):
    root = STATES[name][0]; C = Checks(name)
    f = json.load(open(root + '/feed/ctzb_feed.json'))
    recs = [('cards', c) for c in f['cards']] + [('prints', p) for p in f['prints']] + [('open_signals', o) for o in f['open_signals']] + [('open_signals.card', o['card']) for o in f['open_signals']] + \
           [('grade_odds', g) for g in f['grade_odds']] + [('if_it_misses', m) for m in f['if_it_misses']] + [('past_paths', p) for p in f['past_paths']] + \
           [('example_card', f['example_card']), ('example_if_it_misses', f['example_if_it_misses']), ('example_past_paths', f['example_past_paths']), ('odds_fade', f['odds_fade']), ('feed', f)]
    for k, r in recs:
        lab = r.get('label', '')
        C.add(f"feed.{k} {r.get('signal_id') or r.get('asset', '')} {r.get('grade', '')} {r.get('state', '')}".strip(), 'label: computed signal, not a fill, entry quality only, not a track record',
              all(t in lab for t in ('Computed signal, not a fill', 'No trade was taken', 'Entry quality only', 'not a strategy return or a track record')), True, group='10 feed labels')
    pg = json.load(open(f'{OUT}/page_{name}.json'))
    texts = {'Now (initial)': pg['bodyNow'], 'How to read': pg['bodyRead']}
    for sid, d in pg['sel'].items():
        texts[f'Now card {sid}'] = d['card']['text']
        for k in ('chart', 'chart_happened'):
            if k in d: texts[f'{k} {sid}'] = d[k]['title'] + ' ' + d[k]['sub'] + ' ' + d[k]['sideText'] + ' ' + d[k]['cloudSub'] + ' ' + d[k]['cloudNote'] + ' ' + ' '.join(e.get('text') or '' for e in d[k]['svg'])
    for a, r in pg['record'].items():
        texts[f'Past signals {a}'] = r['title'] + ' ' + r['fine'] + ' ' + r['count'] + ' ' + ' '.join(' '.join(x) for b in r['sum'] for x in b) + ' ' + ' '.join(r['head'])
    # words that would read as a result, a trade taken or a track record
    risky = re.compile(r"\b(profit|profits|P&L|PnL|return|returns|win rate|won|winner|track record|our trades|we bought|we sold|performance|gain|gains|backtest|strategy)\b", re.I)
    ok_ctx = re.compile(r"not a (trade or a )?(return or a )?track record|not a return or a track record|not a trade or a track record|no exit", re.I)
    for k, t in texts.items():
        hits = [(m.group(0), t[max(0, m.start() - 45):m.end() + 25].replace('\n', ' ')) for m in risky.finditer(t) if not ok_ctx.search(t[max(0, m.start() - 60):m.end() + 30])]
        C.add(f'page {k}', 'no wording that reads as a strategy return, a trade taken or a track record', hits[:3], [], group='10 page wording')
        C.add(f'page {k}', "no grade letter shown ('A+', 'grade A/B/C')", re.findall(r"A\+|[Gg]rade [ABC]\b|graded [ABC]\b", t)[:3], [], group='9 page wording')
        tr = [(m.group(0), t[max(0, m.start() - 40):m.end() + 30].replace('\n', ' ')) for m in re.finditer(r"\btrades?\b", t, re.I)]
        tr = [x for x in tr if not re.search(r"lead trader|real trades|not (real )?trades|never traded|not a trade|his real|trades his own|every trade is posted|no trades posted", x[1], re.I)]
        C.add(f'page {k}', "'trade(s)' only for the lead trader or in a denial", tr[:3], [], group='10 page wording')
    for k, d in pg['sel'].items():
        C.add(f'page Now card {k}', 'card ends with the entry-quality disclaimer', 'Entry quality only: no exit, not a trade or a track record' in d['card']['foot'], True, group='10 page wording')
    C.add('page footer', 'footer disclaimer', 'computed statistics, not personal advice' in pg['page']['foot'] and 'entry quality only' in pg['page']['foot'], True, group='10 page wording')
    C.save(f'checks_labels_{name}.csv'); out.append(C)
    print(name, len(C.rows), len(C.bad()))
    for b in C.bad(): print('  BAD', b['location'], '|', b['label'], '|', b['shown'][:400] if isinstance(b['shown'], str) else b['shown'])
