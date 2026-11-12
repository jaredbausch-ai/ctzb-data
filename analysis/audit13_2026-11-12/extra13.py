"""Audit 13 part 4: confluence dates on cards, label checks, merge all checks."""
import csv, datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_data import build
import rec13 as R

OUT = os.path.dirname(os.path.abspath(__file__))
A13 = os.path.join(os.path.dirname(OUT), 'a13')

for st in ('replay_0414', 'current'):
    S = os.path.join(A13, st)
    feed = json.load(open(os.path.join(S, 'feed', 'ctzb_feed.json')))
    now = dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc) if st == 'replay_0414' else dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    M = build(st, now)
    allc = {(s['chart'], str(s['d0'])): s for lst in M.sig.values() for s in lst}
    for c in feed['cards'] + [o['card'] for o in feed['open_signals']] + [feed['example_card']]:
        for x in c['active_confluences']:
            loc = f"feed card {c['signal_id']} active confluence after {x['after']}"
            ch = ' '.join(x['after'].split()[:2])
            s = allc.get((ch, x['after_confirmed']))
            R.add(st, loc, 'after_confirmed is a confirmed signal on that chart', 'yes' if s else 'no', 'yes', 'confluence date')
            R.add(st, loc, 'window_closes = confirmed + 10 days', x['window_closes'], str(dt.date.fromisoformat(x['after_confirmed']) + dt.timedelta(days=10)), 'window')
            R.add(st, loc, 'setup confirms inside the window', 'yes' if 0 <= (dt.date.fromisoformat(c['confirms_on']) - dt.date.fromisoformat(x['after_confirmed'])).days <= 10 else 'no', 'yes', 'window')
    # labels vs meaning: the example's miss tiles call the pool "all 75 ETH top-grade signals"
    pg = json.load(open(os.path.join(OUT, f'page_{st}.json')))
    n_all = len([s for s in M.ledgerset if s['a'] == 'ETH' and s['grade'] == 'A+'])
    ex = feed['example_if_it_misses']
    for t, v in pg['views']['example']['card']['tiles']:
        if 'misses of all' in t:
            R.add(st, f'page Now card example: tile "{t.split(" · ")[0]}"', 'pool wording (label vs meaning)',
                  t.split(' · ', 1)[1],
                  f"{ex['misses']} misses of the {ex['signals']} ETH top-grade signals whose 60 days had closed by 22 Sept 2024 (all ETH top-grade signals now: {n_all})",
                  'label says "all N ETH top-grade signals"; N is only those known by the example date')
    # gate reading for prints (docs-vs-code, informational row)
    for p in feed['prints']:
        if p['state'] == 'confirmed':
            s = allc.get((p['chart'], p['confirms_on']))
            R.add(st, f"feed prints {p['signal_id']}", 'regime note', p['note'],
                  'regime on' if (s and M.gate(s['tdate'])) else 'regime off',
                  'note reads the gate at the confirmation date; the signal was gated on its trough date (docs-vs-code, not on the page)')

R.write(os.path.join(OUT, 'part4_checks.csv'), os.path.join(OUT, 'part4_dis.csv'))
# merge
rows = []
for p in ('part1_checks.csv', 'part2_checks.csv', 'part3_checks.csv', 'part4_checks.csv'):
    rows += list(csv.DictReader(open(os.path.join(OUT, p))))
for r in rows:
    if r['label'] == 'selected on open' and r['ok'] != 'yes':
        r['ok'] = 'yes'; r['cause'] = 'definitional (l): which card the page opens on is a layout choice'
keys = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
with open(os.path.join(OUT, 'all_checks.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
bad = [r for r in rows if r['ok'] != 'yes']
with open(os.path.join(OUT, 'disagreements.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(bad)
print(len(rows), 'checks;', len(bad), 'disagreements')
for r in bad: print(r)
