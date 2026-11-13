"""Audit #20 -- gather every check file into all_checks.csv / disagreements.csv and print the counts."""
import csv, gzip, glob, os, json, re
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
HDR = ['group', 'state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
groups = {'A': sorted(glob.glob(f'{HERE}/frozen/checks_*.csv.gz')), 'B': sorted(glob.glob(f'{HERE}/replays/checks_*.csv.gz')),
          'C': sorted(glob.glob(f'{HERE}/synthetic/checks_*.csv.gz'))}
tot = {}; dis = []; allrows = 0
cats = defaultdict(Counter)
with open(f'{HERE}/all_checks.csv', 'w', newline='') as fa:
    wa = csv.writer(fa); wa.writerow(HDR)
    for g, files in groups.items():
        n = bad = 0; fig = set(); states = set()
        for fp in files:
            with gzip.open(fp, 'rt', newline='') as f: rows = list(csv.reader(f))
            st_n = len(rows); st_bad = [r for r in rows if r[5] != 'ok']
            n += st_n; bad += len(st_bad); states |= {r[0] for r in rows}
            for r in rows:
                key = r[1].split(' ')[0] if not r[1].startswith(('card', 'page', 'open ', 'print ')) else ' '.join(r[1].split(' ')[:2])
                cats[g][key] += 1
            for r in st_bad:
                dis.append([g] + r); fig.add((re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', r[1]), r[2]))
            if g == 'B':
                # full rows stay in the per-replay .csv.gz; all_checks.csv carries one summary row per replay plus its disagreements
                wa.writerow([g, rows[0][0] if rows else os.path.basename(fp), '(summary)', f'{st_n} comparisons; full rows in replays/{os.path.basename(fp)}', '', '', 'ok' if not st_bad else 'DIFF', f'{len(st_bad)} disagreements'])
                for r in st_bad: wa.writerow([g] + r)
            else:
                for r in rows: wa.writerow([g] + r)
        tot[g] = dict(states=len(states), files=len(files), comparisons=n, rows=bad, figures=len(fig))
with open(f'{HERE}/disagreements.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(HDR); w.writerows(dis)
print(json.dumps(tot, indent=1))
for g in cats: print(g, dict(cats[g].most_common(40)))
json.dump(dict(tot=tot, cats={g: dict(c) for g, c in cats.items()}), open(f'{HERE}/totals.json', 'w'), indent=1)
