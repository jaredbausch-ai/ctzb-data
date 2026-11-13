"""One group-B replay: build it with tests/replay_at.sh from the base copy, check it, delete it.
Usage: python3 one.py <index> (reads plan.json)"""
import sys, os, json, subprocess, shutil, gzip, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check, page, pagecheck

plan = json.load(open(os.path.join(A, 'plan.json')))
i = int(sys.argv[1]); P = plan[i]
rid = P['date'] + ('' if not P['clock'] else '_' + P['clock'].replace(':', '').replace('-', ''))
out_dir = os.path.join(A, 'rp', rid)
res_csv = os.path.join(A, 'replays', rid + '.csv.gz')
os.makedirs(os.path.join(A, 'replays'), exist_ok=True)
failclosed = any(k.startswith('fail closed') for k in P['kinds'])
cmd = ['bash', 'tests/replay_at.sh', P['date'], out_dir] + ([P['clock']] if P['clock'] else []) + (['--keep-going'] if failclosed else [])
r = subprocess.run(cmd, cwd=os.path.join(A, 'base'), capture_output=True, text=True)
summ = dict(i=i, id=rid, date=P['date'], clock=P['clock'], kinds=P['kinds'], replay_rc=r.returncode, replay_tail=(r.stdout + r.stderr)[-300:])
try:
    feed = json.load(open(os.path.join(out_dir, 'feed', 'ctzb_feed.json')))
    name = f'B:{rid}'
    if r.returncode != 0 and not failclosed:
        ck = check.Ck(name)
        ck.note('replay pipeline', 'run outcome on real data', 'withheld: ' + (feed.get('feed_error') or r.stdout[-200:]), 'published', False, 'pipeline fails closed on real data')
        summ.update(withheld_real=True, feed_error=feed.get('feed_error'))
    if failclosed or r.returncode != 0:
        ck = ck if r.returncode != 0 and not failclosed else check.Ck(name)
        ck.cmp('fail closed', 'cards_withheld', feed.get('cards_withheld'), True)
        ck.cmp('fail closed', 'cards', len(feed.get('cards') or []), 0)
        ck.cmp('fail closed', 'open_signals', len(feed.get('open_signals') or []), 0)
        ck.cmp('fail closed', 'example_card', feed.get('example_card'), None)
        dump = page.dump(out_dir, res_csv.replace('.csv.gz', '_page.json'), preview_off_too=False)
        ck.cmp('fail closed page', 'card state', dump['initial_card']['state'], 'Setups held back')
        ck.cmp('fail closed page', 'footer', 'checks FAILED, cards held back' in (dump['frame']['feedState'] or ''), True)
        ck.cmp('fail closed page', 'no live or forming buttons', sum(len([b for b in row['buttons'] if b['sel'] != 'example']) for row in dump['frame']['picker']), 0)
        summ.update(withheld=feed.get('cards_withheld'))
    else:
        ck, S, X, feed = check.run(out_dir, name)
        dump = page.dump(out_dir, res_csv.replace('.csv.gz', '_page.json'))
        pagecheck.run(ck, out_dir, dump, S, X, feed)
        summ.update(regime=feed.get('market_regime'), forming=[(c['signal_id'], c['grade']) for c in feed['cards']],
                    open=len(feed['open_signals']), open_aplus=sum(1 for o in feed['open_signals'] if o['grade'] == 'A+'),
                    example=feed.get('example_card') is not None, quiet=('quiet_card' in dump),
                    shown_card=dump['initial_card']['state'])
    pj = res_csv.replace('.csv.gz', '_page.json')
    if os.path.exists(pj):
        with open(pj, 'rb') as f, gzip.open(pj + '.gz', 'wb') as g:
            g.write(f.read())
        os.remove(pj)
    check.write(ck.rows, res_csv)
    bad = [x for x in ck.rows if x['ok'] != 'yes']
    summ.update(n=len(ck.rows), bad=len(bad), bad_rows=bad[:30])
except Exception as e:  # noqa
    import traceback
    summ.update(error=repr(e), tb=traceback.format_exc()[-1500:])
finally:
    shutil.rmtree(out_dir, ignore_errors=True)
with open(os.path.join(A, 'replays', 'summary.jsonl'), 'a') as f:
    f.write(json.dumps(summ) + '\n')
L = [json.loads(x) for x in open(os.path.join(A, 'replays', 'summary.jsonl'))]
if len(L) % 20 == 0:
    with open(os.path.join(A, 'progress.log'), 'a') as f:
        f.write(f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} replays: {len(L)} done, {sum(x.get('n') or 0 for x in L)} comparisons, "
                f"{sum(x.get('bad') or 0 for x in L)} disagreements, {sum(1 for x in L if x.get('error'))} errors\n")
print(rid, summ.get('n'), summ.get('bad'), summ.get('error', ''))
