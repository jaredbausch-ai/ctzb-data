"""Add the qualitative label / entry-quality findings, then write all_checks.csv and disagreements.csv."""
import csv, json, re
from collections import Counter, defaultdict
from mine import S

rows = []
for p in ('part1', 'part4', 'part5', 'part7', 'part8'):
    rows += list(csv.DictReader(open(f'{S}/audit3/{p}.csv')))
P = {s: json.load(open(f'{S}/audit3/page_{s}.json')) for s in ('REPLAY', 'CURRENT')}


def add(state, check, loc, label, shown, yours, ok, cause):
    rows.append(dict(state=state, check=check, location=loc, label=label, shown=shown, yours=yours, ok='yes' if ok else 'no', cause='' if ok else cause))


for st_ in ('REPLAY', 'CURRENT'):
    ex = P[st_]['now:example']['card']
    add(st_, '8', 'example card odds-fade ladder', 'band label for "shallower than -2%"', 'Dip < −2%', 'Dip shallower than −2% (0 to −2%)',
        False, '"< −2%" reads as a dip deeper than 2%; the row is dips of 0 to 2%')
    add(st_, '8', 'example card', '"Where the odds fade" / "Edge gone below" source', 'pooled ETH walk-forward tier table (all grades)', "the setup's own record (CONTEXT 11 Nov: never the pooled early-dip table)",
        False, 'example card falls back to the pooled early-dip table, which CONTEXT says is only a general explainer; How to read defines Edge gone as this setup\'s own odds')
    add(st_, '8', 'example card', 'tile "Price on day 60"', '+22.4% (median of all 104 ETH A+ signals)', 'the example signal itself closed day 60 at +30.2%',
        False, 'tile label does not say typical/median; beside "Confirmed 22 Sept 2024" it reads as this signal\'s result')
    add(st_, '8', 'example card / chart', '"High lands around" / "High usually ~day"', 'Day 41', 'median of daysToHigh = 41', True, '')
    add(st_, '9', 'Record tab', 'tab title / link', 'Record; "The record · every top-grade signal"; "See the full record, misses included"', 'entry-quality wording',
        False, '"record" can read as a track record; the table footnote disclaims it, the tab and link do not')
    add(st_, '9', 'Lead trader panel', 'real trades with Move % and Account %', 'empty now ("No trades posted yet")', 'n/a',
        True, '')
for cid in ('ETH-1D-2026-11-13', 'ETH-2D-2026-11-16', 'BTC-1D-2026-11-13', 'BTC-2D-2026-11-16'):
    side = P['REPLAY'][f'chart-alert:{cid}']['side'].split('\n')[1]
    add('REPLAY', '9', f'chart {cid} side box', 'sample wording', side, 'computed signals, all of them',
        False, '"trades" for computed signals (none was taken), and "the last N" when it is every such signal in the sample period')
for cid, tfd, conf_open in (('ETH-2D-2026-11-16', 2, '15 Nov'), ('BTC-2D-2026-11-16', 2, '15 Nov')):
    add('REPLAY', '8', f'chart {cid}', '"Confirms 16 Nov 2026" vertical line position', 'slot of the bar opening 17 Nov (E + round(5/2) = E+3)', f'slot of the confirmation bar opening {conf_open} (E+2)',
        False, 'confIdx uses the close date of the confirmation bar divided by the bar length; on 2D it lands one bar late')
for cid in ('ETH-2D-2026-11-16', 'BTC-2D-2026-11-16', 'ETH-1D-2026-11-13', 'BTC-1D-2026-11-13'):
    late = '2 bars (4 days)' if '2D' in cid else '1 bar (1 day)'
    add('REPLAY', '8', f'chart {cid}', '"High usually ~day N" and "Day 60" lines', 'counted from today\'s forming bar', f'counted from the entry close ({late} later)',
        False, 'day counts are from entry, the lines are drawn from today; subtitle only says the price zones use today\'s price')
for st_ in ('REPLAY', 'CURRENT'):
    add(st_, '8', 'footer / review bar', '"Data through 12 Nov 2026"', '12 Nov 2026', 'last closed daily bar 11 Nov 2026 (12 Nov still forming)',
        True, '')

# collapse repeated grade-level ledger columns into one figure per asset+grade for the distinct count
led = {r['chart'] + ' ' + r['entry']: r for r in csv.DictReader(open(f'{S}/audit3_replay_0414/datasets/ledger.csv'))}
for r in rows:
    r['_fig'] = (r['location'], r['label'])
    if r['label'] in ('gradeReach20', 'gradeTouched30', 'gradeMedDrawdown'):
        lr = led[r['location'].replace('ledger ', '')]
        r['_fig'] = (f"ledger grade column {lr['asset']} {lr['grade']}", r['label'])
FIELDS = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
with open(f'{S}/audit3/all_checks.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
    for r in rows: w.writerow({**{k: r[k] for k in FIELDS}, 'location': f"[{r['check']}] {r['location']}"})
bad = [r for r in rows if r['ok'] == 'no']
with open(f'{S}/audit3/disagreements.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
    for r in bad: w.writerow({**{k: r[k] for k in FIELDS}, 'location': f"[{r['check']}] {r['location']}"})
clamp = [r for r in bad if 'clamp' in r['cause']]
print('checks', len(rows), 'bad rows', len(bad), 'distinct', len({r['_fig'] for r in bad}),
      'clamp rows', len(clamp), 'clamp distinct', len({r['_fig'] for r in clamp}))
print('non-clamp rows', len(bad) - len(clamp), 'distinct', len({r['_fig'] for r in bad if 'clamp' not in r['cause']}))
print(Counter(r['check'] for r in rows))
print(Counter((r['check'], r['ok']) for r in rows))
g = defaultdict(list)
for r in bad:
    g[(r['check'], r['cause'][:70])].append(r)
for k, v in sorted(g.items()):
    print(k, len(v), len({x['_fig'] for x in v}), Counter(x['state'] for x in v))
