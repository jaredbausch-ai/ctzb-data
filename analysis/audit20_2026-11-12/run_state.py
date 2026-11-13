"""Run data + page checks on one state. usage: run_state.py <root> <now iso> <state name> [--nopage] [--out dir]"""
import sys, json, csv, datetime as dt, time, gzip, os
from collections import Counter
import adata, apagecheck
from playwright.sync_api import sync_playwright
root, nowiso, state = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '.'
now = dt.datetime.fromisoformat(nowiso.replace('Z', '+00:00'))
t = time.time()
C, M, W, feed = adata.build(root, now, state)
nd = C.n(); bd = len(C.bad())
if '--nopage' not in sys.argv:
    with sync_playwright() as pw:
        apagecheck.run_page(C, M, W, feed, root, pw)
bad = C.bad()
print(f'{state}: data {nd} checks {bd} diffs; page {C.n()-nd} checks {len(bad)-bd} diffs; {round(time.time()-t,1)}s; forming {len(M["forming"])} cards {len(M["cards"])} open {len(M["open_signals"])} '
      f'topopen {sum(1 for o in M["open_signals"] if o["grade"]=="A+")} regime {M["market_regime"]} example {"y" if M["example_card"] else "n"} quiet {M.get("_quiet", False)} init {M.get("_initial")}')
for r in bad[:int(os.environ.get('SHOW', '25'))]: print('   ', r[1:])
os.makedirs(out, exist_ok=True)
with gzip.open(os.path.join(out, f'checks_{state}.csv.gz'), 'wt', newline='') as f: csv.writer(f).writerows(C.rows)
json.dump(dict(state=state, n=C.n(), bad=bad, forming=M['forming'], n_cards=len(M['cards']), n_open=len(M['open_signals']), regime=M['market_regime'],
               top_open=[o['signal_id'] + ':' + str(o['edge_status']) for o in M['open_signals'] if o['grade'] == 'A+'], quiet=M.get('_quiet', False), example=bool(M['example_card'])),
          open(os.path.join(out, f'summary_{state}.json'), 'w'))
