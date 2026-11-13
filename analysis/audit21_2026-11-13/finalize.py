"""Audit 21 -- gather every check into all_checks.csv (groups A and C in full; group B stays in checks_B/*.csv.gz,
same columns, to keep the folder small), disagreements.csv (every group) and replays.csv; print the counts."""
import csv, glob, gzip, json, os, sys, datetime as dt, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
HDR = ['group', 'state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']


def item(loc, label):
    if loc.startswith('ledger'): return 1
    if loc.startswith('grade_odds'): return 2
    if 'if_it_misses' in loc: return 3
    if loc.startswith('odds_fade'): return 4
    if loc.startswith('page'):
        if any(k in label for k in ('strategy', 'entry-quality', 'computed, never traded', 'foot')): return 10
        if label.endswith(' label') or label.startswith(('where', 'state', 'lbls', 'headSmall', 'ladderFine', 'title', 'subtitle', 'banner text', 'label:', 'numbers typed')) or 'label' in label: return 9
        return 8
    if loc.startswith('card ') or loc.startswith('example_card') or (loc.startswith('open ') and loc.endswith(' card')): return 5
    if loc.startswith(('open', 'print', 'top')): return 6
    if 'past_paths' in loc: return 7
    return 0


def main(rerun_a=True):
    rows_a = []
    if rerun_a:
        import datacheck as D, pagerun as PR
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            for st, root, now in (('replay_0414', os.path.join(HERE, '..', 'a21', 'replay_0414'), '2026-11-12T04:14:00+00:00'), ('current', os.path.join(HERE, '..', 'a21', 'current'), '2026-11-13T05:39:41+00:00')):
                ck, mine = D.run(root, st, dt.datetime.fromisoformat(now)); nd = ck.n
                PR.page_state(pw, ck, mine, root)
                print(st, 'data', nd, 'page', ck.n - nd, 'diffs', len(ck.bad))
                rows_a += ck.rows
        with gzip.open(os.path.join(HERE, 'checks_A.csv.gz'), 'wt', newline='') as fh: csv.writer(fh).writerows(rows_a)
    else:
        with gzip.open(os.path.join(HERE, 'checks_A.csv.gz'), 'rt') as fh: rows_a = list(csv.reader(fh))
    rows_c = []
    for fn in ('checks_C_page.csv.gz', 'checks_C_pipe.csv.gz', 'checks_C_stale.csv.gz', 'checks_C_cc.csv.gz'):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            with gzip.open(p, 'rt') as fh: rows_c += list(csv.reader(fh))
    nb = 0; bad_b = []; per = []; items_b = collections.Counter(); label_rows = []
    for fn in sorted(glob.glob(os.path.join(HERE, 'checks_B', '*.csv.gz'))):
        with gzip.open(fn, 'rt') as fh:
            n = d = 0; st = None; opn = collections.defaultdict(dict)
            for r in csv.reader(fh):
                n += 1; st = r[0]; items_b[item(r[1], r[2])] += 1
                if r[5] != 'ok': d += 1; bad_b.append(r)
                if r[1].startswith('open '):
                    if r[1].endswith(' card'):
                        if r[2] == 'grade': opn[r[1][:-5]]['grade'] = r[4]
                    elif r[2] in ('edge_status', 'edge_level_pct', 'worst_so_far_pct'): opn[r[1]][r[2]] = r[4]
            # label vs meaning, derived here: the Previous-signals heading over each live top-grade setup
            for k, v in opn.items():
                if v.get('grade') != 'A+': continue
                n += 1; items_b[9] += 1
                if v.get('edge_status') == 'rose10' and v.get('edge_level_pct') not in ('', None) and v.get('worst_so_far_pct') not in ('', None) and float(v['worst_so_far_pct']) <= float(v['edge_level_pct']):
                    d += 1; label_rows.append([st, 'page previous ' + k[5:], 'group heading over a live top-grade setup', f"listed under \"Edge intact\" (badge Rose 10%); worst so far {v['worst_so_far_pct']}%, its edge level {v['edge_level_pct']}%",
                                               'not "edge intact": after rising 10% it fell to its edge level', 'DIFF', 'label vs meaning (wording, no figure is wrong): edge_status rose10 is grouped under the heading Edge intact'])
        nb += n; per.append([st, n, d])
    bad_b += label_rows
    with open(os.path.join(HERE, 'all_checks.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(HDR)
        for r in rows_a: w.writerow(['A'] + r)
        for r in rows_c: w.writerow(['C'] + r)
    bad_a = [r for r in rows_a if r[5] != 'ok']; bad_c = [r for r in rows_c if r[5] != 'ok']
    with open(os.path.join(HERE, 'disagreements.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(HDR)
        for g, rs in (('A', bad_a), ('B', bad_b), ('C', bad_c)):
            for r in rs: w.writerow([g] + r)
    info = {}
    for fn in sorted(glob.glob(os.path.join(HERE, 'old', 'summary_B_*.jsonl'))) + sorted(glob.glob(os.path.join(HERE, 'summary_B_*.jsonl'))):
        for l in open(fn):
            x = json.loads(l); info[x['state']] = x
    with open(os.path.join(HERE, 'replays.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['state', 'clock', 'why chosen', 'filter', 'forming cards', 'top-grade forming', 'live signals', 'live top grade', 'worked example', 'comparisons', 'disagreements'])
        for st, n, d in per:
            x = info.get(st, {})
            w.writerow([st, x.get('clock'), x.get('reason'), x.get('regime'), x.get('cards'), x.get('top_forming'), x.get('open'), x.get('open_top'), x.get('example'), n, d])
    print(json.dumps(dict(A=dict(states=len({r[0] for r in rows_a}), comparisons=len(rows_a), diffs=len(bad_a)), B=dict(replays=len(per), comparisons=nb, diffs=len(bad_b)),
                          C=dict(states=len({r[0] for r in rows_c}), comparisons=len(rows_c), diffs=len(bad_c)))))
    X = list(info.values())
    cov = dict(replays=len(X), filter_off=sum(1 for x in X if x.get('regime') == 'Bearish'), filter_off_with_cards_or_live_top=sum(1 for x in X if x.get('regime') == 'Bearish' and (x.get('cards') or x.get('open_top'))),
               top_grade_forming=sum(1 for x in X if x.get('top_forming')), forming_cards=sum(1 for x in X if x.get('cards')), no_card_no_live_top=sum(1 for x in X if not x.get('cards') and not x.get('open_top')),
               nothing_live_or_forming_any_chart=sum(1 for x in X if x.get('forming_any') == 0 and x.get('open') == 0), day60_in_progress=sum(1 for x in X if x.get('elapsed60')), live_with_no_closed_bar=sum(1 for x in X if x.get('nobest')),
               other_clock=sum(1 for x in X if not x['clock'].endswith('T04:14:00Z')), no_worked_example=sum(1 for x in X if x.get('example') is False), year_end=sum(1 for x in X if x['date'][5:] in ('12-26', '12-27', '12-28', '12-29', '12-30', '12-31', '01-01', '01-02', '01-03', '01-04')),
               live_top_statuses=dict(collections.Counter(s_ for x in X for s_ in x.get('top_status', []))), failed=sum(1 for x in X if not x.get('replay_ok')), audit_errors=sum(1 for x in X if x.get('error')),
               first=min(x['date'] for x in X) if X else None, last=max(x['date'] for x in X) if X else None)
    print('coverage B', json.dumps(cov))
    json.dump(dict(A=dict(states=len({r[0] for r in rows_a}), comparisons=len(rows_a), diffs=len(bad_a), items=sorted(collections.Counter(item(r[1], r[2]) for r in rows_a).items()),
                          by_state={st_: [sum(1 for r in rows_a if r[0] == st_), sum(1 for r in rows_a if r[0] == st_ and r[1].startswith('page'))] for st_ in ('replay_0414', 'current')}),
                   B=dict(replays=len(per), comparisons=nb, diffs=len(bad_b), items=sorted(items_b.items()), coverage=cov,
                          lowday=sorted({(r[0], r[1]) for r in bad_b if 'low printed' in r[2]}), heading=len(label_rows), heading_states=len({r[0] for r in label_rows}),
                          other=[r for r in bad_b if 'low printed' not in r[2] and r not in label_rows][:20]),
                   C=dict(states=len({r[0] for r in rows_c}), comparisons=len(rows_c), diffs=len(bad_c), by_state=sorted(collections.Counter(r[0] for r in bad_c).items()),
                          files={fn: 0 for fn in ()})), open(os.path.join(HERE, 'counts.json'), 'w'), indent=1, default=str)
    print('items A', sorted(collections.Counter(item(r[1], r[2]) for r in rows_a).items()))
    print('items A by state', {st: sorted(collections.Counter(item(r[1], r[2]) for r in rows_a if r[0] == st).items()) for st in ('replay_0414', 'current')})
    print('items B', sorted(items_b.items()))
    for g, rs in (('A', bad_a), ('B', bad_b), ('C', bad_c)):
        c = collections.Counter((r[2].split(' ')[0] if g == 'B' else '', r[2], r[6][:90]) for r in rs)
        for k, v in c.most_common(60): print(g, v, k)


if __name__ == '__main__':
    main(rerun_a='--no-a' not in sys.argv)
