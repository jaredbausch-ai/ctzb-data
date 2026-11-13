"""Tests for .github/scripts/check_candles.py (item 17a). Kraken is simulated; no network.

Run: python tests/test_check_candles.py   -- exits 1 if any case fails.
"""
import sys, os, csv, random, datetime as dt, json, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.github', 'scripts'))
import check_candles as C
import tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
for f in [f'{a_}_{tf}' for a_ in ('ETH','BTC') for tf in ('1D','2D','3D','5D','8D','4H','12H')]: shutil.copy(f'{ROOT}/data/{f}.csv', T)
shutil.copytree(f'{ROOT}/data/derivs', f'{T}/derivs', ignore=lambda d, names: [n for n in names if 'funding_daily' not in n])   # the funding series is checked whole too (13 Nov 2026)
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
cut('BTC_1D', lambda b: b + [b[-1]], 'BTC daily file with its last row twice (audit #21)', 'BTC_1D: row(s) repeated or out of order')
cut('BTC_1D', lambda b: b[::-1], 'BTC daily file with its rows reversed (audit #21)', 'BTC_1D:')
cut('ETH_3D', lambda b: b[:200] + [b[199]] + b[200:], 'ETH 3D file with one row twice', 'ETH_3D: row(s) repeated or out of order')
print('--- 7. every row, the asset itself, the funding series (13 Nov 2026 audit #22) ---')
def cell(i, col, val):
    def f(b):
        hdr = 'time,open,high,low,close,volume'.split(','); c = b[i].split(','); c[hdr.index(col)] = val; b[i] = ','.join(c); return b
    return f
cut('ETH_1D', cell(1200, 'open', '0'), 'ETH daily, a 2019 open of 0', 'ETH_1D: row 1202 has a price at or below zero')
cut('ETH_1D', cell(1200, 'open', '-150'), 'ETH daily, a 2019 open of -150', 'at or below zero')
cut('ETH_1D', cell(1200, 'close', 'nan'), 'ETH daily, a 2019 close of nan', 'non-finite')
cut('BTC_1D', cell(900, 'volume', '-5000'), 'BTC daily, an old negative volume', 'negative volume')
def hi_low(b):
    c = b[1000].split(','); c[2] = str(min(float(c[1]), float(c[4])) * 0.99); b[1000] = ','.join(c); return b
cut('ETH_1D', hi_low, 'ETH daily, an old high below its open and close', 'high below')
cut('ETH_4H', cell(3000, 'open', '0'), 'ETH 4H, an old row at zero', 'ETH_4H: row')
def off_grid(b):
    c = b[500].split(','); c[0] = str(int(float(c[0])) + 3600); b[500] = ','.join(c); return b
cut('ETH_12H', off_grid, 'ETH 12H, a bar off the 12-hour grid', 'not on the 12-hour grid')
def swap(M):
    for tf in ('1D', '2D', '3D', '5D', '8D'): shutil.copy(f'{M}/BTC_{tf}.csv', f'{M}/ETH_{tf}.csv')
def whole(change, label, want):
    M = f'{T}/m'; shutil.rmtree(M, ignore_errors=True); shutil.copytree(T, M, ignore=shutil.ignore_patterns('m','*.py','*.json'))
    change(M); r = run(label, 1, [], fake(), data=M)
    ok = any(want in p for p in r['structural_problems']); results.append(ok)
    print(f"  {'PASS' if ok else '*** FAIL ***'}  ... and the report names it: {[p for p in r['structural_problems'] if want in p][:1]}")
whole(swap, "every ETH candle file replaced by BTC's", 'not ETH and BTC')
def fund(edit):
    def f(M):
        pth = f'{M}/derivs/ETH_funding_daily.csv'; rows = list(csv.DictReader(open(pth))); rows = edit(rows)
        with open(pth, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return f
whole(fund(lambda r: r[:-60]), 'ETH funding with its last 60 days cut', 'more than 3 days before')
whole(fund(lambda r: [dict(x, funding_mean='nan') if i >= len(r) - 40 else x for i, x in enumerate(r)]), 'ETH funding, last 40 days nan', 'not a number between -1 and 1')
whole(fund(lambda r: [dict(x, funding_mean='-100') if i >= len(r) - 10 else x for i, x in enumerate(r)]), 'ETH funding, last 10 days -100', 'not a number between -1 and 1')
whole(fund(lambda r: r[:500] + r[501:]), 'ETH funding missing one day', 'a day is missing')
whole(fund(lambda r: [dict(x, funding_mean='') if i == 700 else x for i, x in enumerate(r)]), 'ETH funding with one blank value', 'no readable')
whole(lambda M: os.remove(f'{M}/derivs/BTC_funding_daily.csv'), 'BTC funding file deleted', 'BTC_funding_daily is missing')
whole(lambda M: shutil.copy(f'{M}/ETH_12H.csv', f'{M}/ETH_4H.csv'), 'ETH 4H file holding 12H bars (audit #23)', 'not a 4H file')
whole(lambda M: shutil.copy(f'{M}/BTC_4H.csv', f'{M}/ETH_4H.csv'), "ETH 4H file replaced by BTC's (audit #23)", 'a file of another asset')
whole(lambda M: os.remove(f'{M}/ETH_12H.csv'), 'ETH 12H file missing (audit #23)', 'ETH_12H is missing')
print(f"\n{sum(results)}/{len(results)} passed")

sys.exit(0 if all(results) else 1)
