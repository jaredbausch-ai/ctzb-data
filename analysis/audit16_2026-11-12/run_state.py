"""Run every check on one state folder: run_state.py <name> <root> <now ISO> ; writes checks_all_<name>.csv"""
import sys, json, datetime as dt, traceback, csv, os
from common import *
import chk_ledger, chk_feed, chk_page, render

def run(name, root, now, keep_dump=True):
    register(name, root, dt.datetime.fromisoformat(now.replace('Z', '+00:00')))
    rows = []; err = []
    try:
        S, C, mine, G = chk_ledger.run(name); rows += C.rows
    except Exception as e: err.append('ledger: ' + traceback.format_exc()[-600:])
    try:
        S, C, mine = chk_feed.run(name); rows += C.rows
    except Exception as e: err.append('feed: ' + traceback.format_exc()[-600:])
    dump = os.path.join(OUT, 'dumps', f'page_{name}.json'); os.makedirs(os.path.dirname(dump), exist_ok=True)
    try:
        r = render.render(root); json.dump(r, open(dump, 'w'))
        S, C, mine, pg = chk_page.run(name, dump=dump); rows += C.rows
    except Exception as e: err.append('page: ' + traceback.format_exc()[-900:])
    return rows, err

if __name__ == '__main__':
    name, root, now = sys.argv[1:4]
    rows, err = run(name, root, now)
    os.makedirs(os.path.join(OUT, 'replays'), exist_ok=True)
    with open(os.path.join(OUT, 'replays', f'checks_{name}.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'group', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(rows)
    bad = [r for r in rows if not r['ok']]
    print(f'{name}: {len(rows)} checks, {len(bad)} bad' + (f' ERR {err}' if err else ''))
    for b in bad[:30]: print('   BAD', b['location'], '|', b['label'], '|', str(b['shown'])[:160], '|', str(b['yours'])[:160], '|', b['cause'][:120])
