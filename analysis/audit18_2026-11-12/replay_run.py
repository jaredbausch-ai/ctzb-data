"""Audit 18 replays: for each date, replay the pipeline (tests/replay_at.sh on my copy of the current state), then run my
whole audit (feed + ledger + page) on the result. usage: replay_run.py <tag> <date[@clock]> ..."""
import csv, datetime as dt, json, os, shutil, subprocess, sys, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_page as RP
REP = os.path.join(HERE, 'rep'); SRC = os.path.join(REP, 'src')
tag = sys.argv[1]
summ = open(os.path.join(REP, f'summary_{tag}.jsonl'), 'a')
for spec in sys.argv[2:]:
    date, _, clock = spec.partition('@')
    d = os.path.join(REP, 'r_' + spec.replace(':', '').replace('@', '_'))
    args = ['bash', os.path.join(SRC, 'tests', 'replay_at.sh'), date, d] + ([clock] if clock else [])
    r = subprocess.run(args, capture_output=True, text=True, timeout=1200)
    rec = dict(spec=spec, rc=r.returncode, out=r.stdout.strip()[-400:])
    if r.returncode == 0:
        try:
            today = dt.date.fromisoformat((clock or date)[:10])
            C, ctx, dumps = RP.run('replay ' + spec, d, today)
            f = ctx['feed']
            with open(os.path.join(REP, f'checks_{spec.replace(":", "").replace("@", "_")}.csv'), 'w', newline='') as fh:
                csv.writer(fh).writerows(C.rows)
            n, b = C.summary()
            rec.update(n=n, bad=b, regime=f['market_regime'], cards=[(c['signal_id'], c['grade'], c['bars_to_confirm']) for c in f['cards']],
                       open=[(o['signal_id'], o['grade'], o['days_elapsed'], o['edge_status'], o['best_so_far_pct']) for o in f['open_signals']],
                       forming_prints=[(p['chart'], p['note']) for p in f['prints'] if p['provisional']], withheld=f['cards_withheld'], example=bool(f.get('example_card')),
                       ledger=len(ctx['led']), misses0=[(m['asset'], m['grade']) for m in f['if_it_misses'] if not m['misses']],
                       disagreements=[r_[1:5] + [r_[6]] for r_ in C.rows if r_[5] != 'ok'][:60])
        except Exception as e:
            rec.update(error=traceback.format_exc()[-1500:])
    summ.write(json.dumps(rec, default=str) + '\n'); summ.flush()
    print(spec, rec.get('rc'), rec.get('n'), rec.get('bad'), rec.get('regime'), len(rec.get('cards', [])), 'cards', len(rec.get('open', [])), 'open', rec.get('error', '')[-300:], flush=True)
    if r.returncode == 0 and 'error' not in rec:
        shutil.rmtree(d, ignore_errors=True)
