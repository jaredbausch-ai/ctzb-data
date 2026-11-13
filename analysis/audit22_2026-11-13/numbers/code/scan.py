"""Pick replay dates: filter episodes, forming lows, quiet days, from the auditor's own engine on full data
(the open bar on each date rebuilt from that date's daily close)."""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mine
from mine import TFS, GRADED

BASE = sys.argv[1]
S = mine.State(BASE, dt.datetime(2026, 11, 13, 12, tzinfo=dt.timezone.utc))
start, end = dt.date(2020, 9, 1), dt.date(2026, 11, 12)
days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
gate = {d: bool(S.gate(d)) for d in days + [start - dt.timedelta(days=40)]}
# episodes
eps = []; cur = None
for d in days:
    g = gate[d]
    if cur is None or cur[0] != g:
        cur = [g, d, d]; eps.append(cur)
    else:
        cur[2] = d
a14 = 1 / 14
prov = {d: [] for d in days}
for a in ('ETH', 'BTC'):
    for tf in TFS:
        B = S.bars[(a, tf)]; ind = S.ind[(a, tf)]; ct = ind['ct']; rst = ind['rst']; c = ind['c']
        dd = S.daily[a]
        j = 0
        for D in days:
            while j + 1 < len(B) and B[j + 1]['open'] <= D:
                j += 1
            if D not in dd['pos'] or j < 20:
                continue
            pc_ = dd['c'][dd['pos'][D]]
            ag, al = rst[j - 1]; cp = c[j - 1]
            g_ = max(pc_ - cp, 0); l_ = max(cp - pc_, 0)
            ag2 = a14 * g_ + (1 - a14) * ag; al2 = a14 * l_ + (1 - a14) * al
            cto = 100.0 if al2 == 0 else 100 - 100 / (1 + ag2 / al2)
            cts = ct[:j] + [cto]; n = j + 1
            for back in (1, 2, 3):
                ti = n - 1 - back
                v = cts[ti]
                if v is None or any(cts[k] is None or cts[k] <= v for k in range(ti - 3, ti)):
                    continue
                if any(cts[k] < v for k in range(ti + 1, n)):
                    continue
                prov[D].append(dict(chart=f'{a} {tf}', tdate=str(B[ti]['open']), need=3 - back, gated=bool(S.gate(B[ti]['open']))))
                break
openq = {}
for D in days:
    n = 0
    for a in ('ETH', 'BTC'):
        for tf in GRADED:
            n += sum(1 for s in S.sig[(a, tf)] if 0 <= (D - s['d0']).days <= 60)
    openq[D] = n
out = dict(episodes=[(g, str(s), str(e)) for g, s, e in eps],
           gate={str(d): g for d, g in gate.items()},
           prov={str(d): v for d, v in prov.items()}, open={str(d): n for d, n in openq.items()},
           sigs=[dict(chart=f"{s['a']} {s['tf']}", tdate=str(s['tdate']), d0=str(s['d0'])) for (a, tf), lst in S.sig.items() for s in lst if tf in GRADED and s['d0'] >= start])
json.dump(out, open(sys.argv[2], 'w'))
print(len(eps), 'episodes'); [print(e) for e in out['episodes']]
print('quiet days (nothing open on graded charts, nothing forming on any chart):', sum(1 for d in days if not prov[d] and not openq[d]))
print('filter-off days:', sum(1 for d in days if not gate[d]))
