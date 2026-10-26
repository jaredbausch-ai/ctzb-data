"""A-bucket clusters and the CT RSI 50 line. Jared's question, 26 Oct 2026:
"Do failed A clusters ever break the 50 CT RSI? I think they get rejected off
the 50, and that is a good indicator the cluster is failing."

DECLARED BEFORE RUNNING.
Universe: regime-on signals, gate R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41),
bucket A only (CT at the trough < 40), entry = confirmation close (ei = ti + 3),
dated bucket_end. ETH and BTC, 1D 2D 3D 5D 8D. Win = daily high reaches +20%
above entry within 60 days. Full 60-day windows only. Periods 2016-21 / 2022-26.
CT is the chart's own RSI(14) on closes, read at each bar close of that chart.

A CLUSTER = a run of consecutive A signals on one chart (no B/C/D signal between
them in that chart's regime-on list), each entering within 60 days of the one
before. Size >= 2. A cluster FAILED if none of its signals reached +20%.

PART 1 (descriptive, what was asked). For failed vs working clusters: did the
chart's CT close at or above 50 at any bar from the first entry to the end of
the last signal's 60-day window (working clusters: to the day +20% was first
reached)? Highest CT close in that span.

PART 2 (usable in real time). For every A signal, walk the chart's bars after
entry, inside the 60-day window, and take whichever comes first:
  BREAK  = CT closes >= 50
  REJECT = CT turns down (closes below the previous bar) from a previous bar
           that closed in 40-50, with no break yet
  NEITHER = no break and no reject in the window
The event is known at that bar's close. Only signals that had NOT already
reached +20% by that date are scored (otherwise the outcome is already known).
Outcome: still reaches +20% from the original entry within its 60 days.
Also: price at the event vs entry, and days from entry to the event.

PASS (as a hold check, like the hold-check table in docs/PRETRADE.md):
  - REJECT wins at least 15 points less than BREAK, pooled, on BOTH assets
  - the gap holds in both periods on both assets (each group n >= 8)
  - REJECT below BREAK on at least 6 of the charts that have n >= 5 in both groups
  - the gap survives inside price state at the event (close above vs below
    entry), each >= +10, so it is not just "the trade is red" read off CT.
ENTRY QUALITY ONLY. Signals are computed, never fills. No exit is implied.
  python3 -I analysis/aclusters.py -> analysis/RESULTS_aclusters.txt, aclusters.json
"""
import sys, os, json, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D')
SPLIT = dt.date(2022, 1, 1)
DAY = {a: E.load(f'data/{a}_1D.csv') for a in ASSETS}
POS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in ASSETS}
LINES = []
P = lambda *x: (LINES.append(' '.join(str(i) for i in x)), print(*x))


def hit_date(a, d0, c0):
    day = DAY[a]; i = POS[a][d0]; end = d0 + dt.timedelta(days=60)
    for k in range(i + 1, len(day['date'])):
        if day['date'][k] > end: return None
        if day['high'][k] >= 1.2 * c0: return day['date'][k]
    return None


def build():
    sigs, clusters = [], []
    for a in ASSETS:
        for tf in TFS:
            S, b = E.signals(f'data/{a}_{tf}.csv', regime=GATE)
            ct = E.rsi(b['close'], 14); dates = b['date']; n = len(dates)
            rows = []
            for s in S:
                ei = s['ei']; d0 = bucket_end(dates, ei)
                if d0 is None or d0 not in POS[a]: continue
                m = measure(DAY[a], POS[a], d0, s['entry'], 60)
                if not m: continue
                rows.append(dict(a=a, tf=tf, ch=f'{a} {tf}', bk=s['bk'], ei=ei, d0=d0, c0=s['entry'],
                                 win=m['up'] >= 20, hd=hit_date(a, d0, s['entry']),
                                 per='16-21' if d0 < SPLIT else '22-26', yr=d0.year))
            # per-bar walk for A signals
            for r in rows:
                if r['bk'] != 'A': continue
                end = r['d0'] + dt.timedelta(days=60); ev = None
                for j in range(r['ei'] + 1, n):
                    dj = bucket_end(dates, j)
                    if dj is None or dj > end or ct[j] is None: break
                    if ct[j] >= 50: ev = ('BREAK', j, dj); break
                    if ct[j - 1] is not None and 40 <= ct[j - 1] < 50 and ct[j] < ct[j - 1]:
                        ev = ('REJECT', j, dj); break
                if ev:
                    k = ev[1]; r.update(ev=ev[0], edate=ev[2], epx=(b['close'][k] / r['c0'] - 1) * 100,
                                        edays=(ev[2] - r['d0']).days,
                                        known=(r['hd'] is not None and r['hd'] <= ev[2]))
                else:
                    r.update(ev='NEITHER', edate=None, epx=None, edays=None, known=False)
                maxct = []
                for j in range(r['ei'] + 1, n):
                    dj = bucket_end(dates, j)
                    if dj is None or dj > end or ct[j] is None: break
                    maxct.append((dj, ct[j]))
                r['ctpath'] = maxct
                sigs.append(r)
            # clusters
            cur = []
            for r in rows:
                if r['bk'] == 'A' and (not cur or (r['d0'] - cur[-1]['d0']).days <= 60):
                    cur.append(r); continue
                if len(cur) >= 2: clusters.append(cur)
                cur = [r] if r['bk'] == 'A' else []
            if len(cur) >= 2: clusters.append(cur)
    return sigs, clusters


def pct(x, n): return f'{100 * x / n:3.0f}%' if n else '  - '


def grp(G):
    n = len(G)
    if not n: return dict(n=0)
    o = dict(n=n, win=100 * sum(r['win'] for r in G) / n)
    for p in ('16-21', '22-26'):
        x = [r for r in G if r['per'] == p]
        o[p] = (100 * sum(r['win'] for r in x) / len(x) if x else None, len(x))
    e = [r['epx'] for r in G if r['epx'] is not None]
    o['epx'] = st.median(e) if e else None
    d = [r['edays'] for r in G if r['edays'] is not None]
    o['edays'] = st.median(d) if d else None
    return o


def fg(o):
    if not o['n']: return 'n=   0'
    g = lambda p: '   -    ' if o[p][0] is None else f'{o[p][0]:3.0f}%({o[p][1]:>3})'
    s = f'n={o["n"]:>4} win {o["win"]:3.0f}% [{g("16-21")} {g("22-26")}]'
    if o.get('epx') is not None: s += f' price at event {o["epx"]:+5.1f}% day {o["edays"]:.0f}'
    return s


def main():
    sigs, clusters = build()
    OUT = {}
    P('A CLUSTERS AND THE CT 50 LINE -- declared, run', dt.date.today(), '| entry quality only, signals not fills\n')

    P('PART 1  clusters (2+ consecutive A signals on one chart, each within 60 days of the last)')
    rowsP1 = []
    for a in ASSETS + ('ALL',):
        C = [c for c in clusters if a == 'ALL' or c[0]['a'] == a]
        for lab, sel in (('failed', lambda c: not any(r['win'] for r in c)), ('working', lambda c: any(r['win'] for r in c))):
            X = [c for c in C if sel(c)]
            broke, mx = 0, []
            for c in X:
                first = c[0]['d0']
                if lab == 'working':
                    stop = min(r['hd'] for r in c if r['hd'] is not None)
                else:
                    stop = c[-1]['d0'] + dt.timedelta(days=60)
                path = {}
                for r in c:
                    for d, v in r['ctpath']: path[d] = v
                vals = [v for d, v in path.items() if first < d <= stop]
                m = max(vals) if vals else None
                mx.append(m)
                broke += bool(m is not None and m >= 50)
            mm = [m for m in mx if m is not None]
            P(f'  {a:3} {lab:7} clusters n={len(X):>3}  CT closed >= 50 in the span: {pct(broke, len(X))} ({broke})'
              f'  median highest CT {st.median(mm) if mm else float("nan"):4.1f}')
            rowsP1.append(dict(asset=a, group=lab, n=len(X), broke50=broke, med_max_ct=st.median(mm) if mm else None))
    P('  by chart (failed clusters: broke 50 / n | working: broke 50 / n)')
    for a in ASSETS:
        for tf in TFS:
            C = [c for c in clusters if c[0]['ch'] == f'{a} {tf}']
            Fl = [c for c in C if not any(r['win'] for r in c)]; Wk = [c for c in C if any(r['win'] for r in c)]
            def brk(c, working):
                first = c[0]['d0']
                stop = min(r['hd'] for r in c if r['hd'] is not None) if working else c[-1]['d0'] + dt.timedelta(days=60)
                return any(v >= 50 for r in c for d, v in r['ctpath'] if first < d <= stop)
            P(f'    {a} {tf}: failed {sum(brk(c, False) for c in Fl)}/{len(Fl)}   working {sum(brk(c, True) for c in Wk)}/{len(Wk)}')
    OUT['part1'] = rowsP1

    P('\nPART 2  every A signal: which comes first after entry, CT closing >= 50 (BREAK) or CT turning down from 40-50 (REJECT)')
    P('  scored only if +20% had not already been reached by the event date')
    elig = [r for r in sigs if r['ev'] == 'NEITHER' or not r['known']]
    P(f'  A signals {len(sigs)}; already at +20% before the event (excluded) {sum(r["known"] for r in sigs)}')
    res = {}
    for a in ASSETS + ('ALL',):
        G = [r for r in elig if a == 'ALL' or r['a'] == a]
        for e in ('BREAK', 'REJECT', 'NEITHER'):
            o = grp([r for r in G if r['ev'] == e]); res[(a, e)] = o
            P(f'  {a:3} {e:7} {fg(o)}')
    P('  by chart')
    chart_ok = chart_n = 0; bychart = {}
    for a in ASSETS:
        for tf in TFS:
            G = [r for r in elig if r['ch'] == f'{a} {tf}']
            ob = grp([r for r in G if r['ev'] == 'BREAK']); orj = grp([r for r in G if r['ev'] == 'REJECT'])
            on = grp([r for r in G if r['ev'] == 'NEITHER'])
            flag = ''
            if ob['n'] >= 5 and orj['n'] >= 5:
                chart_n += 1; ok = orj['win'] < ob['win']; chart_ok += ok; flag = 'REJECT lower' if ok else 'REJECT NOT lower'
            P(f'    {a} {tf}  BREAK {fg(ob)}')
            P(f'           REJECT {fg(orj)}  {flag}')
            P(f'           NEITHER {fg(on)}')
            bychart[f'{a} {tf}'] = dict(BREAK=ob, REJECT=orj, NEITHER=on)
    P('  by year (both assets)')
    for y in sorted({r['yr'] for r in elig}):
        G = [r for r in elig if r['yr'] == y]
        ob = grp([r for r in G if r['ev'] == 'BREAK']); orj = grp([r for r in G if r['ev'] == 'REJECT'])
        P(f'    {y}  BREAK n={ob["n"]:>3} {ob.get("win", 0):3.0f}%   REJECT n={orj["n"]:>3} {orj.get("win", 0):3.0f}%')
    P('  inside price state at the event (close above vs below entry)')
    inside = {}
    for a in ASSETS + ('ALL',):
        for lab, sel in (('green', lambda r: r['epx'] is not None and r['epx'] > 0), ('red', lambda r: r['epx'] is not None and r['epx'] <= 0)):
            G = [r for r in elig if (a == 'ALL' or r['a'] == a) and sel(r)]
            ob = grp([r for r in G if r['ev'] == 'BREAK']); orj = grp([r for r in G if r['ev'] == 'REJECT'])
            gap = (ob['win'] - orj['win']) if ob['n'] and orj['n'] else None
            inside[(a, lab)] = gap
            P(f'    {a:3} {lab:5} BREAK {fg(ob)}')
            P(f'              REJECT {fg(orj)}   gap {gap:+.0f}' if gap is not None else f'              REJECT {fg(orj)}')

    gaps = {a: res[(a, 'BREAK')]['win'] - res[(a, 'REJECT')]['win'] for a in ASSETS}
    per_ok = all(res[(a, 'BREAK')][p][1] >= 8 and res[(a, 'REJECT')][p][1] >= 8 and
                 res[(a, 'BREAK')][p][0] - res[(a, 'REJECT')][p][0] >= 1 for a in ASSETS for p in ('16-21', '22-26'))
    ins_ok = all(inside[(a, l)] is not None and inside[(a, l)] >= 10 for a in ASSETS for l in ('green', 'red'))
    verdict = all(g >= 15 for g in gaps.values()) and per_ok and chart_ok >= 6 and ins_ok
    P(f'\n  VERDICT: gap ETH {gaps["ETH"]:+.0f} BTC {gaps["BTC"]:+.0f} (need +15 each); both periods both assets: {per_ok}; '
      f'REJECT lower on {chart_ok}/{chart_n} charts (need 6); inside price state >= +10: {ins_ok} -> {"PASS" if verdict else "FAIL"}')

    OUT['part2'] = {f'{k[0]} {k[1]}': v for k, v in res.items()}
    OUT['part2_by_chart'] = bychart
    OUT['inside_price_state'] = {f'{k[0]} {k[1]}': v for k, v in inside.items()}
    OUT['verdict'] = 'PASS' if verdict else 'FAIL'
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, 'RESULTS_aclusters.txt'), 'w').write('\n'.join(LINES) + '\n')
    json.dump(OUT, open(os.path.join(here, 'aclusters.json'), 'w'), indent=1, default=str)


if __name__ == '__main__' and len(sys.argv) == 1:
    main()


ADDENDUM = """ADDENDUM, declared 26 Oct 2026 after Part 1/2 ran, before this ran.
Inside a cluster, the bounce between two consecutive A signals: the highest CT
close from the earlier signal's entry to the later signal's trough bar. Known
at the later signal's entry. Split the LATER signal by whether that bounce
peaked below 50 ("rejected under 50") or closed at/above 50 ("broke 50").
Also per cluster: did any bounce inside the cluster (first entry to last
trough) close >= 50, failed vs working. Descriptive only; no pass rule, and
it is not adopted from this run whatever it shows."""


def addendum():
    sigs, clusters = build()
    L = ['\nADDENDUM  bounce between consecutive A signals inside a cluster (known at the later entry)']
    pairs = []
    for c in clusters:
        a = c[0]['a']; tf = c[0]['tf']
        S, b = E.signals(f'data/{a}_{tf}.csv', regime=GATE)
        ct = E.rsi(b['close'], 14)
        for p, q in zip(c, c[1:]):
            ti = q['ei'] - 3
            pk = max(ct[j] for j in range(p['ei'], ti + 1) if ct[j] is not None)
            pairs.append(dict(q, pk=pk))
    for a in ASSETS + ('ALL',):
        for lab, sel in (('rejected under 50', lambda r: r['pk'] < 50), ('broke 50', lambda r: r['pk'] >= 50)):
            G = [r for r in pairs if (a == 'ALL' or r['a'] == a) and sel(r)]
            L.append(f'  {a:3} later signal, bounce {lab:17} {fg(grp(G))}')
    L.append('  by chart (later signal win: rejected under 50 | broke 50)')
    for a in ASSETS:
        for tf in TFS:
            G = [r for r in pairs if r['ch'] == f'{a} {tf}']
            if not G: continue
            u = grp([r for r in G if r['pk'] < 50]); o = grp([r for r in G if r['pk'] >= 50])
            fmt = lambda x: f'{x["win"]:3.0f}% (n={x["n"]})' if x['n'] else '  -  (n=0)'
            L.append(f'    {a} {tf}: {fmt(u)} | {fmt(o)}')
    L.append('  per cluster: any bounce inside the cluster closed >= 50 (first entry to last trough)')
    for a in ASSETS + ('ALL',):
        for lab, sel in (('failed', lambda c: not any(r['win'] for r in c)), ('working', lambda c: any(r['win'] for r in c))):
            X = [c for c in clusters if (a == 'ALL' or c[0]['a'] == a) and sel(c)]
            k = 0
            for c in X:
                S, b = E.signals(f'data/{c[0]["a"]}_{c[0]["tf"]}.csv', regime=GATE); ct = E.rsi(b['close'], 14)
                k += any(ct[j] is not None and ct[j] >= 50 for j in range(c[0]['ei'], c[-1]['ei'] - 3 + 1))
            L.append(f'  {a:3} {lab:7} n={len(X):>3}  a bounce inside closed >= 50: {pct(k, len(X))} ({k})')
    for l in L: print(l)
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, 'RESULTS_aclusters.txt'), 'a').write('\n'.join(L) + '\n')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'addendum':
    addendum()
