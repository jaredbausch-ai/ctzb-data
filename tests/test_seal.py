"""Tests for the run seal (seal.py, 13 Nov 2026): nothing in datasets/ may change between pipeline steps.

Part 1 works on a small folder of stand-in files (fast). Part 2 runs the real pipeline in a copy of the repo:
a clean run, an extras step that fails part-way (cards must still publish), a dataset cut between two steps (the next step
refuses to run) and a dataset changed after the last step (the feed is withheld).
    python3 tests/test_seal.py
"""
import os, shutil, subprocess, sys, tempfile, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import seal  # noqa: E402

results = []


def ok(label, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f'  -- {detail}' if not cond and detail else ''))


def broken(fn):
    try:
        fn(); return None
    except SystemExit as e:
        return str(e)


# ---------------------------------------------------------------- part 1: stand-in files
d = tempfile.mkdtemp(prefix='ctzb_seal_')
w = lambda n, t: open(os.path.join(d, n), 'w').write(t)
ok('no seal at all: a later step refuses to run', broken(lambda: seal.check(d, 'grade')))
seal.start(d); w('setups.csv', 'a\n1\n'); seal.done(d, 'refresh')
ok('after refresh: grade may run', broken(lambda: seal.check(d, 'grade')) is None)
ok('after refresh: stack may not (grade has not finished)', 'grade' in (broken(lambda: seal.check(d, 'stack')) or ''))
w('ledger.csv', 'a\n1\n'); seal.done(d, 'grade')
w('setups.csv', 'a\n2\n')
ok("a file edited after the step that wrote it: the next step refuses", 'changed' in (broken(lambda: seal.check(d, 'extras')) or ''))
w('setups.csv', 'a\n1\n')
ok('...and runs once it is back as written', broken(lambda: seal.check(d, 'extras')) is None)
os.rename(os.path.join(d, 'ledger.csv'), os.path.join(d, 'ledger.bak'))
ok('a file deleted between steps: refused', 'missing' in (broken(lambda: seal.check(d, 'extras')) or ''))
os.rename(os.path.join(d, 'ledger.bak'), os.path.join(d, 'ledger.csv'))
w('stray.csv', 'x\n')
ok('a file that appeared between steps: refused', 'appeared' in (broken(lambda: seal.check(d, 'extras')) or ''))
os.remove(os.path.join(d, 'stray.csv'))
ok('a step run twice in one run: refused', 'already ran' in (broken(lambda: seal.check(d, 'grade')) or ''))
w('pastpaths.csv', 'half a fil')   # extras failed part-way: it wrote one file and never finished
ok('extras failed part-way: stack still runs (its files are not held against the gating steps)', broken(lambda: seal.check(d, 'stack')) is None)
seal.done(d, 'stack'); w('cards_check.txt', 'ok\n'); seal.done(d, 'cards')
p = seal.problems(d, need=('refresh', 'grade', 'stack', 'cards'), ignore=seal.EXTRAS_FILES)
ok('...and the finished run is intact for feed_live', not p, str(p))
ok('...but a run that claims extras succeeded is not', seal.problems(d, need=('refresh', 'grade', 'extras', 'stack', 'cards')))
m = json.load(open(os.path.join(d, 'manifest.json'))); m['steps'] = ['refresh', 'stack', 'grade', 'cards']
json.dump(m, open(os.path.join(d, 'manifest.json'), 'w'))
ok('steps recorded out of order: refused', 'out of order' in ' '.join(seal.problems(d)))
open(os.path.join(d, 'manifest.json'), 'w').write('{not json')
ok('a damaged seal: refused', seal.problems(d))
seal.start(d)
ok('a new run starts a new seal: the last run\'s steps do not count', 'did not finish' in ' '.join(seal.problems(d, need=('refresh',))))
import datetime as dt
seal.start(d); s0 = dt.datetime.strptime(json.load(open(os.path.join(d, 'manifest.json')))['started_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
ok('a seal names when its run started: fresh within the run', seal.age_problem(d, now=s0 + dt.timedelta(minutes=5)) is None)
ok('...from an earlier run (3 h before): refused (audit #25)', 'earlier run' in (seal.age_problem(d, now=s0 + dt.timedelta(hours=3)) or ''))
ok('...started after now (a clock behind): refused', 'future' in (seal.age_problem(d, now=s0 - dt.timedelta(minutes=5)) or ''))
m = json.load(open(os.path.join(d, 'manifest.json'))); m.pop('started_at'); json.dump(m, open(os.path.join(d, 'manifest.json'), 'w'))
ok('...a seal with no start time: refused', 'does not say' in (seal.age_problem(d) or ''))
shutil.rmtree(d)

# ---------------------------------------------------------------- part 2: the real pipeline in a copy
t = tempfile.mkdtemp(prefix='ctzb_seal_repo_')
R = os.path.join(t, 'repo')
shutil.copytree(ROOT, R, ignore=shutil.ignore_patterns('.git', 'analysis', 'node_modules', '__pycache__'))
shutil.copytree(os.path.join(ROOT, 'analysis'), os.path.join(R, 'analysis'), ignore=shutil.ignore_patterns('audit*', '__pycache__'))
OK = 'refresh=success,grade=success,stack=success,cards=success,regress=success'


def step(s, *args):
    p = subprocess.run([sys.executable, s, *args], cwd=R, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def feed(outc):
    env = dict(os.environ, CTZB_STEP_OUTCOMES=outc)
    p = subprocess.run([sys.executable, 'feed_live.py'], cwd=R, capture_output=True, text=True, env=env)
    return p.returncode, json.load(open(os.path.join(R, 'feed', 'ctzb_feed.json'))), p.stdout + p.stderr


codes = [step(s)[0] for s in ('refresh.py', 'grade_live.py', 'extras_live.py', 'stack_live.py', 'verify_cards.py')]
rc, f, out = feed(OK + ',extras=success')
ok('a clean run: every step passes and the feed is published', codes == [0] * 5 and rc == 0 and not f['cards_withheld'], f'{codes} {out[-200:]}')

step('refresh.py'); step('grade_live.py')
open(os.path.join(R, 'datasets', 'pastpaths.csv'), 'w').write('half')     # extras dies part-way
c3 = [step(s)[0] for s in ('stack_live.py', 'verify_cards.py')]
rc, f, out = feed(OK + ',extras=failure')
ok('extras failed part-way: cards still publish, the extras fields are withheld', c3 == [0, 0] and rc == 0 and not f['cards_withheld'] and f['extras_withheld'], f'{c3} {out[-300:]}')

step('refresh.py'); step('grade_live.py'); step('extras_live.py')
lp = os.path.join(R, 'datasets', 'ledger.csv'); led = open(lp, 'rb').read()
open(lp, 'wb').write(led.rsplit(b'\n', 2)[0] + b'\n')                      # the ledger loses its last row between steps
rc_s, out_s = step('stack_live.py')
ok("a dataset cut between two steps: the next step refuses to run", rc_s != 0 and 'seal' in out_s, out_s[-200:])
open(lp, 'wb').write(led)
step('stack_live.py'); step('verify_cards.py')
later = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
p = subprocess.run([sys.executable, 'feed_live.py'], cwd=R, capture_output=True, text=True, env={k: v for k, v in dict(os.environ, CTZB_NOW=later).items() if k != 'CTZB_STEP_OUTCOMES'})
f = json.load(open(os.path.join(R, 'feed', 'ctzb_feed.json')))
ok('feed_live run again on its own a day later: the last run is not published as fresh (audit #25)', p.returncode == 1 and f['cards_withheld'] and 'earlier run' in p.stdout + p.stderr, (p.stdout + p.stderr)[-200:])
shutil.copy(os.path.join(R, 'datasets', 'grades.csv'), os.path.join(t, 'g'))
open(os.path.join(R, 'datasets', 'grades.csv'), 'a').write('\n')
rc, f, out = feed(OK + ',extras=success')
ok('a dataset changed after the last step: feed_live publishes the withheld feed and exits 1', rc == 1 and f['cards_withheld'] and 'seal' in out, out[-200:])
shutil.rmtree(t)

print(f'\n{sum(results)}/{len(results)} passed')
sys.exit(0 if all(results) else 1)
