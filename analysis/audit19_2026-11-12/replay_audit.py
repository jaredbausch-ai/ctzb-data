"""run my data + page checks on one replayed state; append a summary line. usage: replay_audit.py <dir> <clock> <label>"""
import sys, os, csv, json, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import page_check as PC, audit_data as AD
root, clock, label = sys.argv[1:4]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get('A19_OUT', 'replays'))
feed = json.load(open(os.path.join(root, 'feed/ctzb_feed.json')))
summ = dict(label=label, gen=feed.get('generated_at'), withheld=feed.get('cards_withheld'), regime=feed.get('market_regime'), cards=[(c['signal_id'], c['grade'], c['bars_to_confirm']) for c in feed.get('cards') or []],
            open=len(feed.get('open_signals') or []), open_top=[(o['signal_id'], o['days_elapsed'], o['edge_status']) for o in feed.get('open_signals') or [] if o['grade'] == 'A+'], failed=feed.get('checks', {}).get('failed_steps'),
            status=open(os.path.join(root, 'datasets/stack_status.txt')).read().strip()[:200])
try:
    RD, info = AD.run(root, clock, label)
    with open(f'{out}/{label}_data.csv', 'w', newline='') as f: csv.writer(f).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + RD.rows)
    summ.update(data_n=len(RD.rows), data_bad=len(RD.bad()))
    if not feed.get('cards_withheld'):
        RP, info = PC.run(root, clock, label, f'{out}/{label}_page.csv')
        summ.update(page_n=len(RP.rows), page_bad=len(RP.bad()))
except Exception as e:
    summ['error'] = traceback.format_exc()[-600:]
json.dump(summ, open(f'{out}/{label}_summary.json', 'w'), default=str)
print(json.dumps({k: v for k, v in summ.items() if k not in ('status',)}, default=str)[:600])
