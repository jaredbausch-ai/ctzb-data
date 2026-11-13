"""My replay of the pipeline as of a past date, on a copy. Same pattern as tests/replay_at.sh (candles cut at the end
of <date>, clock <date>T04:14Z) with one difference: 2D-8D bars are REBUILT from the cut daily candles (fetch.py's
documented rule: bucket days within each calendar year, restart on 1 January), so the bar still open on <date>
holds no later day. tests/replay_at.sh keeps that bar whole (it can contain days after <date>).
usage: my_replay.py <src> <date> <out> [--raw]   (--raw = exactly tests/replay_at.sh's cut)
"""
import csv, sys, glob, os, shutil, subprocess, datetime as dt

src, date, out = sys.argv[1], sys.argv[2], sys.argv[3]; raw = '--raw' in sys.argv
clock = next((a.split('=')[1] for a in sys.argv if a.startswith('--clock=')), f'{date}T04:14:00Z')
shutil.rmtree(out, ignore_errors=True)
shutil.copytree(src, out, ignore=shutil.ignore_patterns('.git', 'audit*', '__pycache__'))
cut = (dt.datetime.fromisoformat(date).replace(tzinfo=dt.timezone.utc) + dt.timedelta(days=1)).timestamp()
for p in glob.glob(out + '/data/*_*.csv'):
    rows = list(csv.reader(open(p))); h = rows[0]; ti = h.index('time')
    csv.writer(open(p, 'w', newline='')).writerows([h] + [r for r in rows[1:] if float(r[ti]) < cut])
if not raw:
    for a in ('ETH', 'BTC'):
        rows = list(csv.DictReader(open(f'{out}/data/{a}_1D.csv')))
        days = [(dt.datetime.fromtimestamp(int(float(r['time'])), dt.timezone.utc).date(), r) for r in rows]
        for tf in (2, 3, 5, 8):
            groups = {}
            for d, r in days:
                groups.setdefault((d.year, (d - dt.date(d.year, 1, 1)).days // tf), []).append((d, r))
            with open(f'{out}/data/{a}_{tf}D.csv', 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
                for key in sorted(groups):
                    g = groups[key]
                    num = lambda s: float(s)
                    o = g[0][1]['open']; c = g[-1][1]['close']
                    hi = max((num(r['high']), r['high']) for _, r in g)[1]; lo = min((num(r['low']), r['low']) for _, r in g)[1]
                    v = sum(float(r.get('volume') or 0) for _, r in g)
                    ts = int(dt.datetime.combine(g[0][0], dt.time(), dt.timezone.utc).timestamp())
                    w.writerow([ts, o, hi, lo, c, v])
env = dict(os.environ, CTZB_NOW=clock)
for s in ("refresh.py --data data --out datasets", "grade_live.py", "extras_live.py", "stack_live.py", "verify_cards.py"):
    r = subprocess.run(['python3'] + s.split(), cwd=out, env=env, capture_output=True, text=True)
    if r.returncode:
        print(f'FAIL {date}: {s}\n' + (r.stdout + r.stderr)[-600:]); sys.exit(1)
env['CTZB_STEP_OUTCOMES'] = "refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success"
r = subprocess.run(['python3', 'feed_live.py'], cwd=out, env=env, capture_output=True, text=True)
if r.returncode: print('FAIL feed', r.stderr[-400:]); sys.exit(1)
print('ok', date, clock)
