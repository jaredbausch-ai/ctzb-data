"""Collect group A and group B results into all_checks.csv, disagreements.csv and coverage numbers."""
import csv, gzip, json, os, glob, collections
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']


def cls(loc):
    w = loc.split()
    if w[0] == 'page':
        return 'page ' + (w[1] if w[1] not in ('past',) else 'past signals')
    return w[0]


allw = csv.DictWriter(open(os.path.join(OUT, 'all_checks.csv'), 'w', newline=''), fieldnames=F + ['group'])
allw.writeheader()
disw = csv.DictWriter(open(os.path.join(OUT, 'disagreements.csv'), 'w', newline=''), fieldnames=F + ['group'])
disw.writeheader()
stats = collections.Counter()
byclass = {'A': collections.Counter(), 'B': collections.Counter()}
badclass = {'A': collections.Counter(), 'B': collections.Counter()}
for st in ('replay_0414', 'current'):
    for r in csv.DictReader(open(os.path.join(OUT, 'checks', st + '.csv'))):
        r['group'] = 'A'; allw.writerow(r); stats['A cmp'] += 1; byclass['A'][cls(r['location'])] += 1
        if r['ok'] != 'yes':
            disw.writerow(r); stats['A bad'] += 1; badclass['A'][cls(r['location'])] += 1
summ = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(OUT, 'replays', '*.json')))]
for s in summ:
    p = os.path.join(OUT, 'replays', s['id'] + '.csv.gz')
    if not os.path.exists(p):
        continue
    c = collections.Counter(); b = collections.Counter()
    for r in csv.DictReader(gzip.open(p, 'rt')):
        k = cls(r['location']); c[k] += 1; byclass['B'][k] += 1; stats['B cmp'] += 1
        if r['ok'] != 'yes':
            r['group'] = 'B'; disw.writerow(r); b[k] += 1; badclass['B'][k] += 1; stats['B bad'] += 1
    for k in sorted(c):
        allw.writerow(dict(state='replay ' + s['id'], location=k + ' (all checks in this area; detail in replays/' + s['id'] + '.csv.gz)',
                           label='comparisons', shown=c[k], yours=c[k] - b[k], ok='yes' if not b[k] else 'NO', cause='' if not b[k] else 'see disagreements.csv', group='B'))
json.dump(dict(stats=stats, byclass={k: dict(v) for k, v in byclass.items()}, badclass={k: dict(v) for k, v in badclass.items()},
               n_replays=len(summ)), open(os.path.join(OUT, 'aggregate.json'), 'w'), indent=1)
print(stats, len(summ))
