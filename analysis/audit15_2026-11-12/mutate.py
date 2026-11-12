"""Audit 15 -- self-test of the auditor: change numbers in a COPY of the replay state's feed and ledger and
confirm my checks flag each one. Usage: python3 mutate.py"""
import json, csv, random, os, shutil, subprocess, sys
random.seed(15)
SRC = os.path.abspath('../a15/replay_0414'); DST = os.path.abspath('states/mut')
shutil.rmtree(DST, ignore_errors=True); os.makedirs(DST)
for x in os.listdir(SRC):
    if x in ('feed', 'datasets'): shutil.copytree(f'{SRC}/{x}', f'{DST}/{x}')
    else: os.symlink(f'{SRC}/{x}', f'{DST}/{x}')
feed = json.load(open(f'{DST}/feed/ctzb_feed.json'))
leaves = []
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('label', 'note', 'active_confluences', 'past_signals', 'signals_a_year'): continue
            walk(v, path + [k])
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, path + [i])
    elif isinstance(o, (int, float)) and not isinstance(o, bool): leaves.append(path)
for sec in ('cards', 'example_card', 'open_signals', 'prints', 'if_it_misses', 'example_if_it_misses', 'odds_fade', 'past_paths', 'example_past_paths'):
    walk(feed[sec], [sec])
for i, g in enumerate(feed['grade_odds']):
    if 'HTF' not in g['grade']: walk(g, ['grade_odds', i])
picks = random.sample(leaves, 120); done = []
for p in picks:
    o = feed
    for k in p[:-1]: o = o[k]
    old = o[p[-1]]; o[p[-1]] = old + (1 if isinstance(old, int) else 0.1); done.append(('feed', '/'.join(map(str, p)), old, o[p[-1]]))
json.dump(feed, open(f'{DST}/feed/ctzb_feed.json', 'w'), indent=1)
rows = list(csv.reader(open(f'{DST}/datasets/ledger.csv'))); h = rows[0]
cols = ['entryPrice', 'bestMove', 'maxDrawdown', 'dipBeforeHigh', 'return60d', 'daysToHigh', 'gradeReach20', 'gradeTouched30', 'gradeMedDrawdown', 'dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10', 'dayScaled20']
lm = []
while len(lm) < 60:
    r = random.randrange(1, len(rows)); c = random.choice(cols); j = h.index(c)
    if rows[r][j] == '' or (r, j) in [(a, b) for a, b, *_ in lm]: continue
    old = rows[r][j]; new = repr(round(float(old) + (1 if '.' not in old else 0.000001), 6)) if '.' in old else str(int(old) + 1)
    rows[r][j] = new; lm.append((r, j, f'{rows[r][1]} {rows[r][3]} {c}', old, new))
flip = []
while len(flip) < 20:
    r = random.randrange(1, len(rows)); c = random.choice(['reached20', 'touched30', 'reached10', 'reached15', 'surv10']); j = h.index(c)
    if (r, j) in [(a, b) for a, b, *_ in flip]: continue
    rows[r][j] = 'no' if rows[r][j] == 'yes' else 'yes'; flip.append((r, j, f'{rows[r][1]} {rows[r][3]} {c}'))
csv.writer(open(f'{DST}/datasets/ledger.csv', 'w', newline='')).writerows(rows)
json.dump(dict(feed=done, ledger=[x[2:] for x in lm], flips=[x[2] for x in flip]), open('states/mut_list.json', 'w'), indent=1)
print('mutated', len(done), 'feed numbers,', len(lm), 'ledger numbers,', len(flip), 'ledger yes/no cells')
