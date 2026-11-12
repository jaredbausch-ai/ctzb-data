"""Collect every comparison into all_checks.csv and print counts per check."""
import csv, json, os
OUT = os.path.dirname(os.path.abspath(__file__))
F = json.load(open('/home/claude/ctzb-data/feed/ctzb_feed.json'))
rows = []
# check 1
c1 = json.load(open(os.path.join(OUT, 'check1.json')))
d1 = list(csv.DictReader(open(os.path.join(OUT, 'ledger_diffs.csv'))))
n1 = c1['n_checked'] * 16
for d in d1: rows.append(dict(check=1, where=f"ledger {d['chart']} {d['entry']}", field=d['field'], shown=d['shown'], mine=d['mine'], ok=False))
cnt = {1: [n1, len(d1)]}
# 2,3,6
for x in json.load(open(os.path.join(OUT, 'check236.json'))):
    k = int(x['check']); cnt.setdefault(k, [0, 0]); cnt[k][0] += 1; cnt[k][1] += (not x['ok'])
    if not x['ok']: rows.append(dict(check=k, where=x['where'][3:], field=x['field'], shown=x['shown'], mine=x['mine'], ok=False))
# 4
c4 = json.load(open(os.path.join(OUT, 'check4.json')))
of = F['odds_fade']; cnt[4] = [0, 0]
for kind, lst, key in (('early_dip', of['early_dip'], 'band'), ('day10', of['day10'], 'check')):
    for r in lst:
        mb = next(x for x in c4['rows'] if x['band'] == r[key] and x['method'].startswith('chart bars'))
        md = next(x for x in c4['rows'] if x['band'] == r[key] and x['method'].startswith('daily'))
        for fld, shown, mine in (('past_trades', r['past_trades'], mb['n']), ('rose20_within60d_pct', r['rose20_within60d_pct'], mb['r20']),
                                 ('rose10_within60d_pct', r.get('rose10_within60d_pct'), mb['r10']), ('edge (on +10%)', r['edge'], mb['edge_on_r10'])):
            ok = shown == mine or (shown is not None and not isinstance(shown, str) and abs(shown - mine) < 1e-9)
            cnt[4][0] += 1; cnt[4][1] += (not ok)
            if not ok: rows.append(dict(check=4, where=f'odds_fade {kind} {r[key]}', field=fld, shown=shown, mine=f'{mine} (CONTEXT daily method: n {md["n"]}, r10 {md["r10"]}, r20 {md["r20"]})', ok=False))
# 5
c5 = [x for x in json.load(open(os.path.join(OUT, 'check5.json'))) if x['field'] != '_sample']
cnt[5] = [len(c5), sum(not x['ok'] for x in c5)]
for x in c5:
    if not x['ok']: rows.append(dict(check=5, where=x['where'][3:], field=x['field'], shown=x['shown'], mine=x['mine'], ok=False))
# 7
p = list(csv.DictReader(open(os.path.join(OUT, 'page_checks.csv'))))
tab = next(x for x in p if x['label'].endswith('x 7 figures'))
cnt[7] = [len(p) - 1 + int(tab['shown']), sum(x['ok'] == 'False' for x in p)]
for x in p:
    if x['ok'] == 'False': rows.append(dict(check=7, where=x['where'], field=x['label'], shown=x['shown'], mine=x['mine'], ok=False, cause=x['cause']))
with open(os.path.join(OUT, 'all_disagreements.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['check', 'where', 'field', 'shown', 'mine', 'cause', 'ok']); w.writeheader(); w.writerows(rows)
print(cnt, 'total', sum(v[0] for v in cnt.values()), 'disagree', sum(v[1] for v in cnt.values()))
for r in rows:
    if r['check'] == 4: print(r)
