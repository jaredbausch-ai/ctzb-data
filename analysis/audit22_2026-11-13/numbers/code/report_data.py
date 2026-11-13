"""Aggregate group A and group B results into all_checks.csv, disagreements.csv and a stats JSON for the report."""
import os, csv, json, gzip, glob, re, collections
A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']


def rd(p):
    op = gzip.open if p.endswith('.gz') else open
    with op(p, 'rt', newline='') as f:
        return list(csv.DictReader(f))


def cat(loc):
    l = loc
    for k, v in (('ledger', 'ledger rows'), ('grade_odds', 'grade_odds'), ('if_it_misses', 'if_it_misses'), ('example_if_it_misses', 'if_it_misses'),
                 ('odds_fade', 'odds_fade'), ('top level', 'top-level fields'), ('prints', 'prints'), ('cards', 'forming cards'),
                 ('example_card', 'example card'), ('open_signals', 'open signals and their cards'), ('past_paths', 'past paths'),
                 ('example_past_paths', 'past paths'), ('data/', 'candle files'), ('page chart', 'page: Chart tab'), ('page card', 'page: cards'),
                 ('page picker', 'page: picker'), ('page Previous', 'page: Previous signals'), ('page Past signals', 'page: Past signals tab'),
                 ('page quiet', 'page: quiet card'), ('page', 'page: header, banner, footer, How to read'), ('fail closed', 'fail-closed runs'),
                 ('replay pipeline', 'pipeline run outcome')):
        if l.startswith(k):
            return v
    return 'other'


def main():
    allrows = []
    for p in ('a_replay.csv', 'a_current.csv'):
        allrows += rd(os.path.join(A, p))
    summ = [json.loads(l) for l in open(os.path.join(A, 'replays', 'summary.jsonl'))]
    Bbad = []; Bcat = collections.Counter(); Bcat_bad = collections.Counter(); Bn = 0
    for s in summ:
        p = os.path.join(A, 'replays', s['id'] + '.csv.gz')
        if not os.path.exists(p):
            continue
        rows = rd(p); Bn += len(rows)
        c = collections.Counter(cat(r['location']) for r in rows)
        cb = collections.Counter(cat(r['location']) for r in rows if r['ok'] != 'yes')
        Bcat.update(c); Bcat_bad.update(cb)
        for k, n in sorted(c.items()):
            allrows.append(dict(state=f"B:{s['id']}", location=k, label=f'{n} comparisons (rows in replays/{s["id"]}.csv.gz)', shown=n - cb.get(k, 0),
                                yours=n, ok='yes' if not cb.get(k) else 'NO', cause='' if not cb.get(k) else 'see disagreements.csv'))
        Bbad += [dict(r, state=f"B:{s['id']}") for r in rows if r['ok'] != 'yes']
    Abad = [r for r in allrows if r['state'].startswith('A:') and r['ok'] != 'yes']
    with open(os.path.join(A, 'all_checks.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(allrows)
    with open(os.path.join(A, 'disagreements.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['group'] + FIELDS); w.writeheader()
        for r in Abad:
            w.writerow(dict(r, group='A'))
        for r in Bbad:
            w.writerow(dict(r, group='B'))
    Acat = collections.Counter(cat(r['location']) for r in allrows if r['state'].startswith('A:'))
    Acat_bad = collections.Counter(cat(r['location']) for r in Abad)
    distinctB = collections.Counter((r['location'].split(' ')[0] + ' ' + r['label'], r['cause']) for r in Bbad)
    json.dump(dict(A_n=sum(Acat.values()), A_bad=len(Abad), Acat=Acat, Acat_bad=Acat_bad, B_n=Bn, B_bad=len(Bbad), Bcat=Bcat, Bcat_bad=Bcat_bad,
                   B_replays=len(summ), B_errors=[s['id'] for s in summ if s.get('error')], distinctB=[[k[0], k[1], v] for k, v in distinctB.items()]),
              open(os.path.join(A, 'stats.json'), 'w'), indent=1)
    print(len(allrows), 'rows in all_checks.csv;', len(Abad), 'A disagreements;', len(Bbad), 'B disagreements')


if __name__ == '__main__':
    main()
