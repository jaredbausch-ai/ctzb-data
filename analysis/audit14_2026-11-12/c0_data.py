"""Check 0: raw data integrity -- 2D+ bars rebuilt from 1D, 1D vs 4H, clamp list, gate cross-check, entry close = daily close."""
import sys, datetime as dt, csv
from lib import *
sys.path.insert(0, STATES['REPLAY'][0])
for name in STATES:
    S = State(name); R = Rec(name, 'c0')
    for a in ASSETS:
        d1 = S.day[a]
        # raw (unclamped) rebuild
        raw = list(csv.DictReader(open(f'{S.root}/data/{a}_1D.csv')))
        rd = {utcdate(r['time']): r for r in raw}
        # contiguous days?
        gaps = [(d1.date[i-1], d1.date[i]) for i in range(1, d1.n) if (d1.date[i]-d1.date[i-1]).days != 1]
        print(name, a, 'missing daily bars (informational):', gaps)
        R.add(f'data/{a}_1D.csv', 'missing daily bars from 2016-06-09 (first gate-on day) onward', len([g for g in gaps if g[1] >= dt.date(2016, 6, 9)]), 0, cause='informational: ' + str(gaps[:5]))
        for tf in TFS[1:]:
            n = int(tf[0]); ch = list(csv.DictReader(open(f'{S.root}/data/{a}_{tf}.csv')))
            groups = {}
            for d in sorted(rd):
                groups.setdefault((d.year, (d - dt.date(d.year,1,1)).days // n), []).append(d)
            exp = {}
            for key, days in groups.items():
                exp[days[0]] = (float(rd[days[0]]['open']), max(float(rd[x]['high']) for x in days), min(float(rd[x]['low']) for x in days), float(rd[days[-1]]['close']))
            got = {utcdate(r['time']): (float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in ch}
            bad = [d for d in sorted(set(exp)|set(got)) if exp.get(d) != got.get(d)]
            R.add(f'data/{a}_{tf}.csv', f'bars equal 1D rebuilt by calendar-year buckets (mismatching bars of {len(got)})', len(bad), 0, cause=str([(str(d), got.get(d), exp.get(d)) for d in bad[:3]]))
        # 4H vs 1D (where 4H exists): compare daily o/h/l/c from 4H
        h4 = list(csv.DictReader(open(f'{S.root}/data/{a}_4H.csv')))
        g = {}
        for r in h4: g.setdefault(utcdate(r['time']), []).append(r)
        nb = 0; worst = 0; ex = []
        for d, rs in g.items():
            if d not in rd or len(rs) != 6: continue
            e = (float(rs[0]['open']), max(float(x['high']) for x in rs), min(float(x['low']) for x in rs), float(rs[-1]['close']))
            q = (float(rd[d]['open']), float(rd[d]['high']), float(rd[d]['low']), float(rd[d]['close']))
            dev = max(abs(e[i]/q[i]-1) for i in range(4) if q[i] > 0)
            if dev > 0.005: nb += 1; ex.append((str(d), e, q))
            worst = max(worst, dev)
        print(name, a, '4H-vs-1D days compared', sum(1 for d, rs in g.items() if d in rd and len(rs) == 6), 'days differing >0.5%:', nb, 'worst', round(worst*100,3), ex[:4])
        print(name, a, 'clamps 1D:', S.day[a].clamped)
        for tf in TFS[1:]:
            print(name, a, tf, 'clamps:', S.ch[(a, tf)].clamped)
    # gate cross-check
    import regimes as RG
    g2 = RG.rsi_regime(f'{S.root}/data/BTC_2D.csv', 8, 13, 60, 41)
    d = dt.date(2016, 1, 1); diff = 0
    while d <= S.today:
        if g2(d) != S.gate(d): diff += 1
        d += DAY1
    R.add('regime gate', 'days where my gate state differs from regimes.rsi_regime(BTC_2D,8,13,60,41)', diff, 0)
    R.add('feed.market_regime', 'Bullish iff gate on today', S.feed['market_regime'], 'Bullish' if S.gate(S.today) else 'Bearish')
    # gate transitions
    d = dt.date(2016, 1, 1); prev = None; tr = []
    while d <= S.today:
        v = S.gate(d)
        if v != prev: tr.append((str(d), v)); prev = v
        d += DAY1
    print(name, 'gate transitions', tr)
    # entry close on chart == daily close on entry date
    nbad = 0; ns = 0
    for a in ASSETS:
        for tf in TFS:
            for s in S.signals(a, tf):
                ns += 1
                i = S.day[a].pos.get(s['edate'])
                if i is None or S.day[a].c[i] != s['entry']: nbad += 1; print('entry mismatch', s['chart'], s['edate'])
    R.add('all charts', f'confirmed signals whose chart close != daily close on the entry date (of {ns})', nbad, 0)
    R.save()
