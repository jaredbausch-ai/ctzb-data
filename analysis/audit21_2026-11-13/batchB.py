"""Audit 21 -- group B: replay real dates through tests/replay_at.sh (no file tampering), then run every data
and page check on the result. One gz of checks per replay; the replay copy is deleted."""
import csv, datetime as dt, gzip, json, os, shutil, subprocess, sys, time, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import datacheck as D, pagerun as PR
from playwright.sync_api import sync_playwright

SRC = os.path.join(HERE, 'src_current')

def one(pw, date, clock, reason, outdir):
    name = f"replay {date}" + (f" @{clock[11:16]}" if clock else '')
    root = os.path.join(HERE, 'rp', f"{date}{('_' + clock[11:16].replace(':', '')) if clock else ''}")
    cmd = ['bash', os.path.join(SRC, 'tests', 'replay_at.sh'), date, root] + ([clock] if clock else [])
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    now = dt.datetime.fromisoformat((clock or f'{date}T04:14:00Z').replace('Z', '+00:00'))
    info = dict(state=name, date=date, clock=clock or f'{date}T04:14:00Z', reason=reason, replay_ok=r.returncode == 0)
    ck = D.Checks(name)
    try:
        if r.returncode != 0:
            msg = (r.stdout + r.stderr).strip().splitlines()
            ck.flag('pipeline', 'replay of a real date runs clean', 'FAILED: ' + ' | '.join(msg[-4:])[:400], 'runs clean', 'the pipeline fails on a real date with real candles')
            info['fail'] = ' | '.join(msg[-4:])[:400]
        else:
            ck, mine = D.run(root, name, now)
            f = mine['feed']
            info.update(cards=len(f.get('cards') or []), top_forming=sum(1 for c in f.get('cards') or [] if c['grade'] == 'A+'), open=len(f.get('open_signals') or []),
                        open_top=sum(1 for o in f.get('open_signals') or [] if o['grade'] == 'A+'), regime=f.get('market_regime'), withheld=f.get('cards_withheld'),
                        forming_any=len(mine['forming']), example=f.get('example_card') is not None, ledger=len(mine['ledger']),
                        top_status=[o['edge_status'] for o in f.get('open_signals') or [] if o['grade'] == 'A+'],
                        nobest=sum(1 for o in f.get('open_signals') or [] if o.get('best_so_far_pct') is None), elapsed60=sum(1 for o in f.get('open_signals') or [] if o.get('days_elapsed') == 60))
            ck.add('pipeline', 'feed not withheld on a clean run', bool(f.get('cards_withheld')), False, 'cards withheld although every step passed')
            nd = ck.n
            PR.page_state(pw, ck, mine, root)
            info['page_checks'] = ck.n - nd
    except Exception as e:
        ck.flag('audit', 'checker ran', f'{type(e).__name__}: {e}', 'ran', 'AUDIT CODE ERROR (not a site finding): ' + traceback.format_exc()[-600:])
        info['error'] = f'{type(e).__name__}: {e}'
    info.update(checks=ck.n, diffs=len(ck.bad), secs=round(time.time() - t0, 1))
    fn = os.path.join(outdir, name.replace(' ', '_').replace('@', 'at').replace(':', '') + '.csv.gz')
    with gzip.open(fn, 'wt', newline='') as fh: csv.writer(fh).writerows(ck.rows)
    shutil.rmtree(root, ignore_errors=True)
    return info

if __name__ == '__main__':
    lst = json.load(open(sys.argv[1])); w = int(sys.argv[2]); nw = int(sys.argv[3]); tag = sys.argv[4]
    outdir = os.path.join(HERE, 'checks_B'); os.makedirs(outdir, exist_ok=True)
    mine_ = [x for i, x in enumerate(lst) if i % nw == w]
    with sync_playwright() as pw:
        for i, (date, clock, reason) in enumerate(mine_):
            info = one(pw, date, clock, reason, outdir)
            with open(os.path.join(HERE, f'summary_B_{tag}.jsonl'), 'a') as fh: fh.write(json.dumps(info) + '\n')
            if w == 0 and (i + 1) % 10 == 0:
                import glob
                rows = [json.loads(l) for fn in glob.glob(os.path.join(HERE, 'summary_B_*.jsonl')) for l in open(fn)]
                with open(os.path.join(HERE, 'progress.log'), 'a') as fh:
                    fh.write(f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} stage=replays in progress: {len(rows)} replays done, {sum(r['checks'] for r in rows)} comparisons, {sum(r['diffs'] for r in rows)} disagreements so far (A: 61111 comparisons, 0 disagreements)\n")
