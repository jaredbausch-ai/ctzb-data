"""Tests for .github/scripts/check_candles.py (item 17a). Kraken is simulated; no network.

Run: python tests/test_check_candles.py   -- exits 1 if any case fails.
"""
import sys, os, csv, random, datetime as dt, json, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.github', 'scripts'))
import check_candles as C
import tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
for f in [f'{a_}_{tf}' for a_ in ('ETH','BTC') for tf in ('1D','2D','3D','5D','8D','4H')]: shutil.copy(f'{ROOT}/data/{f}.csv', T)
today = dt.datetime.now(dt.timezone.utc).date()
def cb(asset, path=T):
    return {dt.datetime.fromtimestamp(t, dt.timezone.utc).date(): v for t, v in C.load(f'{path}/{asset}_1D.csv').items()}
def fake(noise=0.0005, bad=None):
    random.seed(1)
    def k(asset):
        d = {x: v[3] * (1 + random.uniform(-noise, noise)) for x, v in cb(asset).items() if x < today and x >= today - dt.timedelta(days=720)}
        if bad and asset == bad[0]: d[bad[1]] = d[bad[1]] * (1 + bad[2])
        return d
    return k
out = f'{T}/out.json'
results = []
def run(name, expect, argv, kraken, data=T):
    rc = C.main([data, '--out', out] + argv, kraken=kraken, today=today)
    ok = (rc == expect); results.append(ok)
    print(f"  {'PASS' if ok else '*** FAIL ***'}  {name}: exit {rc} (expected {expect})")
    return json.load(open(out))
print('--- 1. real data, structural only ---')
r = run('structural on today\'s real data', 0, [], fake())
print('     problems:', r['structural_problems'][:3])
print('--- 2. cross-source, report mode ---')
r = run('normal small gaps, report', 0, [], fake())
print('     ETH all:', {k: r['cross']['ETH']['all'][k] for k in ('days_compared','median_pct','max_pct')})
bad_day = today - dt.timedelta(days=5)
r = run('5% bad close, REPORT mode must not fail', 0, [], fake(bad=('ETH', bad_day, 0.05)))
print('     worst ETH day recorded:', r['cross']['ETH']['all']['worst_days'][0])
print('--- 3. cross-source, enforce mode ---')
r = run('5% bad close, enforce at 1%', 1, ['--cross','enforce','--max-close-gap','1'], fake(bad=('ETH', bad_day, 0.05)))
print('     over:', r['cross']['ETH']['over_threshold'])
old = today - dt.timedelta(days=200)
r = run('5% bad close 200 days ago, enforce (outside 30d window)', 0, ['--cross','enforce','--max-close-gap','1'], fake(bad=('ETH', old, 0.05)))
run('normal gaps, enforce at 1%', 0, ['--cross','enforce','--max-close-gap','1'], fake())
print('--- 3b. the live threshold (0.5%, set 11 Nov 2026 from 720 measured days) ---')
LIVE = ['--cross','enforce','--max-close-gap','0.5']
run('normal gaps, enforce at the live 0.5%', 0, LIVE, fake())
run('worst real gap ever seen (0.164%) passes at 0.5%', 0, LIVE, fake(noise=0.00164))
run('0.3% bad close yesterday passes at 0.5%', 0, LIVE, fake(bad=('BTC', today - dt.timedelta(days=1), 0.003)))
r = run('0.6% bad close yesterday FAILS at 0.5%', 1, LIVE, fake(bad=('BTC', today - dt.timedelta(days=1), 0.006)))
print('     over:', r['cross']['BTC']['over_threshold'][:1])
print('--- 4. Kraken unreachable ---')
r = run('Kraken down must NOT fail', 0, ['--cross','enforce','--max-close-gap','1'], lambda a: None)
print('     cross:', r['cross'])
print('--- 5. structural faults injected ---')
def mutate(fn, label):
    M = f'{T}/m'; shutil.rmtree(M, ignore_errors=True); shutil.copytree(T, M, ignore=shutil.ignore_patterns('m','*.py','*.json'))
    with open(f'{M}/ETH_1D.csv') as fh: rows = list(csv.DictReader(fh))
    fn(rows)
    with open(f'{M}/ETH_1D.csv','w',newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    r = run(label, 1, [], fake(), data=M); print('     ', r['structural_problems'][:1])
mutate(lambda rows: rows.pop(-10), 'missing day')
mutate(lambda rows: rows[-5].update(low=str(float(rows[-5]['high'])*1.01)), 'low above high')
mutate(lambda rows: rows[-7].update(close='0'), 'zero close')
mutate(lambda rows: rows[-3].update(volume='0'), 'zero volume on a closed day')
print('--- 6. whole-history faults (13 Nov 2026 audit #20) ---')
def cut(name, keep, label, want):
    M = f'{T}/m'; shutil.rmtree(M, ignore_errors=True); shutil.copytree(T, M, ignore=shutil.ignore_patterns('m','*.py','*.json'))
    with open(f'{M}/{name}.csv') as fh: lines = fh.read().split('\n')
    body = [x for x in lines[1:] if x]
    with open(f'{M}/{name}.csv','w') as fh: fh.write('\n'.join([lines[0]] + keep(body)) + '\n')
    r = run(label, 1, [], fake(), data=M)
    ok = any(want in p for p in r['structural_problems']); results.append(ok)
    print(f"  {'PASS' if ok else '*** FAIL ***'}  ... and the report names it: {[p for p in r['structural_problems'] if want in p][:1]}")
cut('BTC_1D', lambda b: b[-40:], 'BTC daily file cut to its last 40 bars', 'history is missing')
cut('ETH_2D', lambda b: b[:len(b)//2], 'ETH 2D file cut to its first half', 'ETH_2D bars differ from the daily candles')
cut('ETH_5D', lambda b: b[:-1], 'ETH 5D file missing its last bar', 'ETH_5D bars differ from the daily candles')
cut('ETH_1D', lambda b: b[:1500] + b[1501:], 'ETH daily file missing one day years back', 'ETH_1D has 1 missing day')
print(f"\n{sum(results)}/{len(results)} passed")

sys.exit(0 if all(results) else 1)
