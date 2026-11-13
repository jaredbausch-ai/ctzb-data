"""Group C: a run whose refresh step fails after the market filter has flipped. Day A = 2025-12-04 (last filter-on
day, clean run); day B = 2025-12-07 (filter off), same folder, ETH_3D.csv missing so refresh fails."""
import csv, datetime as dt, gzip, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import datacheck as D, pagecheck as P, synthC_pipe as SP
from playwright.sync_api import sync_playwright
SRC = os.path.join(HERE, 'src_current'); A = os.path.join(HERE, 'tmp_stale_a'); B = os.path.join(HERE, 'tmp_stale_b')
r = subprocess.run(['bash', os.path.join(SRC, 'tests', 'replay_at.sh'), '2025-12-04', A], capture_output=True, text=True); print(r.stdout.strip())
r = subprocess.run(['bash', os.path.join(SRC, 'tests', 'replay_at.sh'), '2025-12-07', B], capture_output=True, text=True); print(r.stdout.strip())
true_regime = json.load(open(os.path.join(B, 'feed', 'ctzb_feed.json')))['market_regime']
for d in ('datasets', 'feed'):
    shutil.rmtree(os.path.join(B, d)); shutil.copytree(os.path.join(A, d), os.path.join(B, d))
os.remove(os.path.join(B, 'data', 'ETH_3D.csv'))
env = dict(os.environ, CTZB_NOW='2025-12-07T04:14:00Z'); outc = []
for step, cmd in SP.STEPS:
    rr = subprocess.run(['python3'] + cmd.split(), cwd=B, env=env, capture_output=True, text=True); outc.append(f"{step}={'success' if rr.returncode == 0 else 'failure'}")
subprocess.run(['python3', 'feed_live.py'], cwd=B, env=dict(env, CTZB_STEP_OUTCOMES=','.join(outc) + ',regress=success'), capture_output=True, text=True)
f = json.load(open(os.path.join(B, 'feed', 'ctzb_feed.json')))
ck = D.Checks('C refresh fails three days after the last good run, the filter having turned off since')
with sync_playwright() as pw:
    s = P.Site(pw, B, '2025-12-07T04:20:00Z'); s.goto('now'); g = s.now(); s.close()
desc = f"steps {outc}; feed generated_at {f['generated_at']}, scored_as_of {f['scored_as_of']}, market_regime {f['market_regime']}, cards_withheld {f['cards_withheld']}; true filter on 7 Dec 2025: {true_regime}; page: {g['card']['state']} / {g['filter']} / banner {g['rv']} / footer {g['feedState']}"
print(desc)
ck.add('pipeline', 'published feed is withheld', f['cards_withheld'], True, desc)
ck.add('page', 'card state', g['card']['state'], 'Setups held back', desc)
ck.add('page', 'header does not state a filter reading from an earlier run as today\'s', g['filter'], f"Market filter: {'on' if true_regime == 'Bullish' else 'off'}",
       'a failed refresh leaves status.csv from the last good run; the fresh, withheld feed repeats its market_regime: ' + desc)
ck.add('page', 'footer "daily candles closed through" matches the data scored', '6 Dec 2025' in g['feedState'] and f['scored_as_of'] == '2025-12-07', True, 'footer derives the date from generated_at; the feed was scored on ' + str(f['scored_as_of']) + ': ' + desc)
with gzip.open(os.path.join(HERE, 'checks_C_stale.csv.gz'), 'wt', newline='') as fh: csv.writer(fh).writerows(ck.rows)
print('checks', ck.n, 'diffs', len(ck.bad))
shutil.rmtree(A, ignore_errors=True); shutil.rmtree(B, ignore_errors=True)
