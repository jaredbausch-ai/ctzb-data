"""Audit 17: on which past days would there have been NO subject at all (no low forming on any of the 10
charts, no gated signal confirmed in the last 60 days)? Uses my own model on candles cut at each day."""
import csv, datetime as dt, os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
BASE = sys.argv[1]; start = dt.date.fromisoformat(sys.argv[2]); end = dt.date.fromisoformat(sys.argv[3]); step = int(sys.argv[4]) if len(sys.argv) > 4 else 1
raw = {a: list(csv.DictReader(open(f'{BASE}/data/{a}_1D.csv'))) for a in C.ASSETS}
first = {(a, tf): C.utc_date(next(csv.DictReader(open(f'{BASE}/data/{a}_{tf}.csv')))['time']) for a in C.ASSETS for tf in C.TFS}
tmp = tempfile.mkdtemp(prefix='a17scan_'); os.makedirs(tmp + '/data')
for f in ('regimes.py', 'engine.py'): shutil.copy(f'{BASE}/{f}', tmp)
out = []
d = start
while d <= end:
    for a in C.ASSETS:
        rows = [r for r in raw[a] if C.utc_date(r['time']) <= d]
        for tf in C.TFS:
            n = C.tfdays(tf); bars = {}
            for r in rows:
                x = C.utc_date(r['time'])
                if x < first[(a, tf)]: continue
                k = C.bar_open_of(x, tf)
                o, h, l, c = float(r['open']), float(r['high']), float(r['low']), float(r['close'])
                if k not in bars: bars[k] = [o, h, l, c]
                else:
                    b = bars[k]; b[1] = max(b[1], h); b[2] = min(b[2], l); b[3] = c
            with open(f'{tmp}/data/{a}_{tf}.csv', 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
                for k in sorted(bars):
                    w.writerow([int(dt.datetime.combine(k, dt.time(), dt.timezone.utc).timestamp())] + [repr(v) for v in bars[k]] + [0])
    for m in [m for m in sys.modules if m in ('regimes', 'engine')]: del sys.modules[m]
    sys.path = [p for p in sys.path if p != tmp]
    S = C.State(tmp, dt.datetime.combine(d, dt.time(4, 14), dt.timezone.utc))
    nf = sum(1 for a in C.ASSETS for tf in C.TFS if S.forming(a, tf))
    nr = sum(1 for a in C.ASSETS for tf in C.TFS for s in S.signals(a, tf) if 0 <= (d - s['d0']).days <= 60)
    ncard = sum(1 for a in C.ASSETS for tf in C.GRADED if (S.forming(a, tf) or {}).get("gate"))
    out.append((d, S.gate(d), nf, nr)); print(d, "gate", S.gate(d), "forming", nf, "cards", ncard, flush=True)
    d += dt.timedelta(days=step)
shutil.rmtree(tmp)
z = [x for x in out if x[2] == 0 and x[3] == 0]
print(f'{start}..{end} step {step}: {len(out)} days scanned, {len(z)} with no subject at all (no forming low on any chart, no signal in 60 days)')
print('  first/last such days:', ' '.join(str(x[0]) for x in z[:12]), '...', ' '.join(str(x[0]) for x in z[-3:]))
print('  days with nothing forming but signals still inside 60 days:', sum(1 for x in out if x[2] == 0 and x[3] > 0))
