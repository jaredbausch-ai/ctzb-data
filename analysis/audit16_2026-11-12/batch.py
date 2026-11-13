"""Replay a list of dates (my_replay.py), run every check on each, keep the feed + page dump, delete the copy."""
import sys, os, subprocess, json, shutil, csv, datetime as dt
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
dates = [l.split()[0] for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
tags = {l.split()[0]: ' '.join(l.split()[1:]) for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')}
extra = sys.argv[2:] 

def one(date):
    name = 'R' + date + ('raw' if '--raw' in extra else '')
    out = f'{HERE}/work/{name}'
    r = subprocess.run(['python3', f'{HERE}/my_replay.py', f'{HERE}/work/src', date, out] + extra, capture_output=True, text=True)
    if 'ok' not in r.stdout:
        return name, 'REPLAY FAILED: ' + (r.stdout + r.stderr)[-300:].replace('\n', ' '), ''
    f = json.load(open(out + '/feed/ctzb_feed.json'))
    os.makedirs(f'{HERE}/replays', exist_ok=True)
    shutil.copy(out + '/feed/ctzb_feed.json', f'{HERE}/replays/feed_{name}.json')
    desc = (f"regime {f['market_regime']}; cards {[(c['signal_id'], c['grade'], c['bars_to_confirm']) for c in f['cards']]}; "
            f"open {len(f['open_signals'])} (top {[(o['signal_id'], o['days_elapsed'], o['edge_status']) for o in f['open_signals'] if o['grade'] == 'A+']}); "
            f"forming prints {[p['signal_id'] + ' ' + p['note'][:10] for p in f['prints'] if p['state'] == 'forming']}; example {f['example_card'] is not None}")
    r = subprocess.run(['python3', f'{HERE}/run_state.py', name, out, f'{date}T04:14:00Z'], capture_output=True, text=True, cwd=HERE)
    shutil.rmtree(out, ignore_errors=True)
    return name, (r.stdout + r.stderr[-800:]).strip(), desc

with ThreadPoolExecutor(2) as ex:
    for name, res, desc in ex.map(one, dates):
        print(f'### {name} [{tags.get(name[1:11], "")}]\n    {desc}\n    {res}', flush=True)
