"""Audit 15 -- assemble all_checks.csv, disagreements.csv, replays.csv and print the tallies.
Reads the check files the audit scripts write into this folder. After the run they were moved to work/ (the two
frozen states, the gate-off replay, the synthetic page tests) or deleted (the 55 replayed dates, 1.5 GB of state
copies): to repeat, run ./runstate.sh <date> per date and the scripts named in AUDIT15.md, then this."""
import csv, glob, os, re, collections
HDR = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
def cause(r):
    lab, loc = r[2], r[1]
    if 'tier date' in lab: return "feed_live.py:333 hard-codes 'as fixed on 1 Jan 2026'; refresh.py fixes the tier on 1 Jan of the CURRENT year (wrong text in any other year, and from 1 Jan 2027)"
    if 'quiet state' in loc and ('line 4' in lab or 'market filter is on' in lab): return "index.html:485: ${perYear()} sits inside a plain \"...\" string, so the placeholder prints raw"
    if 'synthetic: an era with no signals' in loc: return "index.html:558 appends % to n/a (cosmetic; only when an era has no signals)"
    if 'short year-end bar' in loc: return r[6]
    if r[0].startswith('d') or 'replay 20' in r[0]:
        return "stack_live.py:307-308 dates a forming low's confirmation with a fixed bar step (last bar + step x bars, + step - 1); 2D+ bars restart on 1 January, so across a year-end the date (and the signal_id built from it) is late"
    return r[6]
allrows = []; dis = []; rep = []
frozen = [('replay', 'REPLAY'), ('current', 'CURRENT')]
for key, nm in frozen:
    for f in (f'checks_data_{key}.csv', f'checks_page_{key}.csv', f'checks_extra_{key}.csv', f'checks_pagex_{key}.csv', f'checks_pageq_{key}.csv', f'checks_pages_{key}.csv'):
        for r in csv.reader(open(f)):
            r[0] = nm + r[0][len(key):] if r[0].startswith(key) else r[0]
            if r[5] == 'NO': r[6] = cause(r)
            allrows.append(r)
for f in ['checks_data_gateoff.csv', 'checks_page_gateoff.csv', 'checks_extra_gateoff.csv']:
    for r in csv.reader(open(f)):
        r[0] = 'replay 2026-06-11 (gate off, tests/test_gate_off.sh)'
        if r[5] == 'NO': r[6] = cause(r)
        allrows.append(r)
for f in sorted(glob.glob('checks_data_d20*.csv')):
    d = re.search(r'd(20\d\d-\d\d-\d\d)', f).group(1)
    rows = list(csv.reader(open(f))) + (list(csv.reader(open(f'checks_page_d{d}.csv'))) if os.path.exists(f'checks_page_d{d}.csv') else [])
    bad = [r for r in rows if r[5] == 'NO']
    for r in bad:
        r[6] = cause(r); r[0] = f'replay {d}'
    rep.append([f'replay {d}', len(rows), len(bad), len([r for r in bad if 'tier date' in r[2]]), len([r for r in bad if 'tier date' not in r[2]])])
    dis += bad
for r in csv.reader(open('checks_pagey.csv')):
    allrows.append(r); 
csv.writer(open('all_checks.csv', 'w', newline='')).writerows([HDR] + allrows)
bad_all = [r for r in allrows if r[5] == 'NO'] + dis
csv.writer(open('disagreements.csv', 'w', newline='')).writerows([HDR] + bad_all)
csv.writer(open('replays.csv', 'w', newline='')).writerows([['state', 'comparisons', 'disagreements', 'of which the hard-coded tier year', 'of which year-end confirmation date']] + rep)
by = collections.Counter(r[0] for r in allrows); byn = collections.Counter(r[0] for r in allrows if r[5] == 'NO')
for k in by: print(k, by[k], byn[k])
print('replayed dates', len(rep), 'comparisons', sum(x[1] for x in rep), 'disagreement rows', sum(x[2] for x in rep), 'tier-year rows', sum(x[3] for x in rep), 'year-end rows', sum(x[4] for x in rep), 'dates with year-end rows', [x[0] for x in rep if x[4]])
# counts by check number for the two frozen states
def num(r):
    loc = r[1]
    if loc.startswith('ledger'): return 1
    if loc.startswith('feed grade_odds'): return 2
    if loc.startswith(('feed if_it_misses', 'feed example_if_it_misses')): return 3
    if loc.startswith('feed odds_fade'): return 4
    if loc.startswith(('feed cards', 'feed example_card')) or (' card' in loc and loc.startswith('feed open_signals')): return 5
    if loc.startswith(('feed open_signals', 'feed prints', 'feed top level', 'feed confluence')): return 6
    if loc.startswith(('feed past_paths', 'feed example_past_paths')): return 7
    if loc.startswith(('page', 'example chart file')): return 8
    return 0
t = collections.Counter(); tb = collections.Counter()
for r in allrows:
    if r[0].startswith(('REPLAY', 'CURRENT')):
        k = (r[0].split(' (')[0] if '(synthetic' not in r[0] else 'synthetic', num(r)); t[k] += 1; tb[k] += r[5] == 'NO'
for k in sorted(t, key=str): print(k, t[k], tb[k])
