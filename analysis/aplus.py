"""A+ signals only: the full record. Descriptive, 28 Oct 2026 (Jared asked for
strictly the A+ statistics). Grade as applied by grade_live.py (ETH lenses GAP,
HIGH, AGREE, BTC3, FUND, FCOOL; A+ = 4 or more), ETH 1D-5D, 2020 on (funding
data). Episodes = A+ signals within 10 days of each other merged.
ENTRY QUALITY ONLY. Computed signals, never fills.
  python3 -I analysis/aplus.py -> analysis/RESULTS_aplus.txt
"""
import sys, os, datetime as dt, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import grade_live as GL, grokpack as GP, pcrtest as PT
from grade3 import funding_series
L = []; P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)

def summ(lab, G):
    if not G: P(f'  {lab:14} n=0'); return
    n = len(G); dd = sorted(r['m']['dd'] for r in G); pk = sorted(r['m']['ddpk'] for r in G); up = sorted(r['m']['up'] for r in G)
    P(f'  {lab:14} n={n:>3} | +10% {100*sum(r["m"]["up"]>=10 for r in G)/n:3.0f}% +20% {100*sum(r["win"] for r in G)/n:3.0f}% +30% {100*sum(r["m"]["up"]>=30 for r in G)/n:3.0f}% '
      f'| +20% before -20% {100*sum(bool(r.get("safe")) for r in G)/n:3.0f}% | green at 60d {100*sum(r["m"]["ret"]>0 for r in G)/n:3.0f}% '
      f'| best move median {st.median(up):+.1f}% | dip first median {st.median(pk):+.1f}% 1-in-10 {pk[int(0.1*(n-1))]:+.1f}% '
      f'| 60d dip median {st.median(dd):+.1f}% 1-in-10 {dd[int(0.1*(n-1))]:+.1f}% | touched -20% {100*sum(r["t20"] for r in G)/n:3.0f}% -30% {100*sum(r["t30"] for r in G)/n:3.0f}% '
      f'| days to high {st.median(r["m"]["dpk"] for r in G):.0f}')

def main():
    rows, allsig = GP.build(); fb = PT.funding_below(); f = funding_series('ETH')
    b3 = [x['d0'] for x in allsig[('BTC', '3D')]]; A = []
    for r in rows:
        if r['a'] != 'ETH' or r['tf'] not in ('1D', '2D', '3D', '5D'): continue
        d0 = r['d0']; r['btc3'] = r['tf'] in ('1D', '2D') and any(0 <= (d0 - d).days <= 10 for d in b3)
        v = fb.get(('ETH', d0)); r['fund'] = None if v is None else (not v)
        w7 = [f[d0 - dt.timedelta(days=k)] for k in range(7) if d0 - dt.timedelta(days=k) in f]
        w7b = [f[d0 - dt.timedelta(days=14 + k)] for k in range(7) if d0 - dt.timedelta(days=14 + k) in f]
        r['fcool_ok'] = len(w7) >= 5 and len(w7b) >= 5; r['fcool'] = r['fcool_ok'] and sum(w7) / len(w7) >= sum(w7b) / len(w7b)
        if r['fund'] is None or not r['fcool_ok']: continue
        g, names = GL.grade_of(r); r['lensnames'] = names
        if g == 'A+': A.append(r)
    A.sort(key=lambda r: r['d0'])
    P('A+ ONLY -- ETH 1D-5D, 2020 on |', len(A), 'signals | entry quality only, computed signals, not fills\n')
    summ('all A+', A)
    summ('2020-21', [r for r in A if r['d0'] < SPLIT]); summ('2022-26', [r for r in A if r['d0'] >= SPLIT])
    for tf in ('1D', '2D', '3D', '5D'): summ('ETH ' + tf, [r for r in A if r['tf'] == tf])
    P('\nBy year (signals | episodes):')
    eps = []
    for r in A:
        if eps and (r['d0'] - eps[-1][-1]['d0']).days <= 10: eps[-1].append(r)
        else: eps.append([r])
    for y in sorted({r['yr'] for r in A}):
        G = [r for r in A if r['yr'] == y]; E_ = [e for e in eps if e[0]['d0'].year == y]
        summ(f'{y} ({len(E_)} ep.)', G)
    P(f'\nEpisodes: {len(eps)} | at least one signal reached +20%: {sum(any(x["win"] for x in e) for e in eps)} | every signal in it touched -30%: {sum(all(x["t30"] for x in e) for e in eps)}')
    P('Episode list (first signal date, charts, best move of the best signal, worst 60d dip of the first signal):')
    for e in eps:
        P(f'  {e[0]["d0"]}  {", ".join(sorted({x["tf"] for x in e}))}  best {max(x["m"]["up"] for x in e):+.0f}%  first-signal 60d dip {e[0]["m"]["dd"]:+.0f}%  +20%: {"yes" if any(x["win"] for x in e) else "no"}')
    c = collections.Counter(r['lensnames'] for r in A)
    P('\nLens combinations behind A+:'); [P(f'  {k}: {v}') for k, v in c.most_common()]
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_aplus.txt'), 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    main()
