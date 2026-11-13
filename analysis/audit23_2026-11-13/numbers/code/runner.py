"""Run every declared replay: replay_at.sh on a copy, my data + page checks, gzip the check file, delete the copy."""
import json, os, sys, subprocess, gzip, shutil, csv, threading, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
BASE = os.path.join(OUT, 'base')
WORK = os.path.join(OUT, 'work')
RD = os.path.join(OUT, 'replays')
os.makedirs(RD, exist_ok=True); os.makedirs(WORK, exist_ok=True)
lock = threading.Lock()
done = {'n': 0, 'cmp': 0, 'bad': 0}


def one(job):
    date, clock, kinds = job['date'], job['clock'], job['kinds']
    rid = date + ('' if not clock else '_' + clock[11:19].replace(':', ''))
    summ = os.path.join(RD, rid + '.json')
    if os.path.exists(summ):
        return json.load(open(summ))
    d = os.path.join(WORK, rid)
    clk = clock or f'{date}T04:14:00Z'
    t0 = time.time()
    r = subprocess.run(['bash', os.path.join(BASE, 'tests', 'replay_at.sh'), date, d, clk, '--keep-going'], capture_output=True, text=True)
    res = dict(id=rid, date=date, clock=clk, kinds=kinds, replay_rc=r.returncode, replay_out=r.stdout[-300:] + r.stderr[-300:])
    try:
        feed = json.load(open(os.path.join(d, 'feed', 'ctzb_feed.json')))
        res.update(withheld=feed.get('cards_withheld'), failed_steps=feed['checks'].get('failed_steps'),
                   regime=feed.get('market_regime'), n_cards=len(feed.get('cards', [])),
                   card_grades=[c['grade'] for c in feed.get('cards', [])],
                   card_ids=[c['signal_id'] for c in feed.get('cards', [])],
                   open_aplus=[o['signal_id'] for o in feed.get('open_signals', []) if o['grade'] == 'A+'],
                   n_open=len(feed.get('open_signals', [])), example=feed.get('example_card') is not None,
                   forming_prints=[p['signal_id'] + ' ' + p['note'] for p in feed.get('prints', []) if p['state'] == 'forming'],
                   live_card_status=[(o['signal_id'], o['edge_status'], o['days_elapsed']) for o in feed.get('open_signals', [])])
        hv = os.path.join(d, 'harvest.json')
        p1 = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pagerun.py'), d, hv], capture_output=True, text=True, timeout=300)
        res['page_run'] = p1.stdout[-300:] + p1.stderr[-500:]
        ck = os.path.join(d, 'checks.csv')
        p2 = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pagecheck.py'), d, clk, 'replay ' + rid, hv, ck], capture_output=True, text=True, timeout=600)
        res['check_out'] = p2.stdout[-3000:] + p2.stderr[-1500:]
        if os.path.exists(ck):
            rows = list(csv.DictReader(open(ck)))
            res['comparisons'] = len(rows); res['disagreements'] = sum(r['ok'] != 'yes' for r in rows)
            res['page_comparisons'] = sum(r['location'].startswith('page ') for r in rows)
            with open(ck, 'rb') as fi, gzip.open(os.path.join(RD, rid + '.csv.gz'), 'wb') as fo:
                shutil.copyfileobj(fi, fo)
            shutil.copy(hv, os.path.join(RD, rid + '.harvest.json')); subprocess.run(['gzip', '-f', os.path.join(RD, rid + '.harvest.json')])
    except Exception as e:  # noqa
        res['error'] = repr(e)
    res['secs'] = round(time.time() - t0)
    shutil.rmtree(d, ignore_errors=True)
    json.dump(res, open(summ, 'w'))
    with lock:
        done['n'] += 1; done['cmp'] += res.get('comparisons', 0); done['bad'] += res.get('disagreements', 0)
        if done['n'] % 20 == 0:
            open(os.path.join(OUT, 'progress.log'), 'a').write(
                f"{dt.datetime.utcnow():%Y-%m-%dT%H:%M:%SZ} replays: {done['n']} run this session, {done['cmp']} comparisons, {done['bad']} disagreements so far\n")
    return res


if __name__ == '__main__':
    jobs = json.load(open(sys.argv[1]))
    with ThreadPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 2) as ex:
        for r in ex.map(one, jobs):
            print(r['id'], r.get('withheld'), r.get('comparisons'), r.get('disagreements'), r.get('error', ''), flush=True)
