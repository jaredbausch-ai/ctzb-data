"""Conviction grade, audit 2: every read that tested well but was never tried as a lens.
DECLARED 28 Oct 2026 20:35 ET, before running, from the repo-wide inventory of
everything ever tested (Jared: "we're missing shit"). Same rules as grade2.py.

CANDIDATES (all known at the entry close)
  B3E3   BTC 3D signal confirmed 0-10 days before an ETH 3D entry (BTC3 today covers
         only ETH 1D/2D). xmap 23 Oct: 63% vs 39%, n 59, 5/6 years. ETH 3D only.
  E3B3   ETH 3D signal confirmed 0-10 days before a BTC 3D entry. xmap: +13, n 55.
         BTC 3D only.
  K1     BTC put/call (Deribit volume) 100-day percentile of the 7-day mean >= 95 at
         the last weekly close (Sunday) on or before entry. pcrtest K1: 64% vs 47%,
         touched -30% 3% vs 17%, n 39. BTC only (2017 on).
  VOLC   volatility not expanding: 30-day / 180-day realised daily volatility at
         entry below the chart's top-third cut point from 2016-21 (sweep F11:
         the top third had 12 pts more -20% touches in both periods). Both assets.
  FASTCT fast CT recovery: CT at confirmation minus CT at the trough in the chart's
         top third, cut from 2016-21 (sweep F17: +11 / +11). Both assets.
  MFIS   money flow above its own signal line: MFI(14) on the chart's bars above
         its EMA(14) at the entry bar (CONTEXT 19 Oct: 67% vs 58%, n 121,
         independence untested). Both assets.
RULES (unchanged from grade2.py)
  STEP 1 keep for an asset if it cuts touched -30% by >= 2 points OR lifts +20% by
  >= 5, the other no more than 3 worse, in BOTH periods (to 2021 / 2022 on), each
  group n >= 15.
  STEP 2 overlap against every live lens of that asset (ETH: GAP HIGH AGREE BTC3
  FUND FCOOL; BTC: GAP UP8 BTCX) and earlier survivors: with both its -30% cut and
  +20% lift under 1 point inside either half of another lens, it is that lens
  counted twice and is dropped.
  PLACEBO flag reshuffled within each year, 40 times; the real effect on the
  qualifying measure must beat the shuffled 95th percentile.
  STEP 3 grade rebuilt with survivors added, same cut points, reported beside the
  live grade, with the ordering check by period.
ALSO DECLARED
  8D GRADING: 8D signals are not graded today. Report the live grade applied to ETH
  and BTC 8D signals by period. Graded from now on only if A/A+ beats C on +20% and
  on touched -30% in both periods, each group n >= 5.
  The flows test (whaletest.py, declared 25 Oct, never run) is run as declared,
  separately; its own bars apply.
Entry quality only. Computed signals, not fills.
  python3 -I analysis/grade6.py -> analysis/RESULTS_grade6.txt, grade6.json
"""
import sys, os, json, math, random, datetime as dt, statistics as st, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import grokpack as GP
import pcrtest as PT
import grade as G1
from grade3 import funding_series

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = {'ETH': ['GAP', 'HIGH', 'AGREE', 'BTC3', 'FUND', 'FCOOL'], 'BTC': ['GAP', 'UP8', 'BTCX']}


def mfi_sig(path):
    rows = list(csv.DictReader(open(path)))
    h = [float(r['high']) for r in rows]; l = [float(r['low']) for r in rows]; c = [float(r['close']) for r in rows]
    v = [float(r.get('volume') or 0) for r in rows]
    tp = [(h[i] + l[i] + c[i]) / 3 for i in range(len(c))]
    m = [None] * len(c)
    for i in range(14, len(c)):
        pos = sum(tp[j] * v[j] for j in range(i - 13, i + 1) if tp[j] > tp[j - 1])
        neg = sum(tp[j] * v[j] for j in range(i - 13, i + 1) if tp[j] < tp[j - 1])
        m[i] = 100.0 if neg == 0 else 100 - 100 / (1 + pos / neg)
    em = E.ema(m, 14)
    return [m[i] is not None and em[i] is not None and m[i] > em[i] for i in range(len(c))], sum(1 for x in v if x > 0)


def main():
    rows, allsig = GP.build()
    every = [r for lst in allsig.values() for r in lst]
    rows = [r for r in rows if r['tf'] in ('1D', '2D', '3D', '5D', '8D')]
    D0 = {k: [x['d0'] for x in v] for k, v in allsig.items()}
    near = lambda d0, k: any(0 <= (d0 - d).days <= 10 for d in D0[k])
    fb = PT.funding_below(); FSr = {a: funding_series(a) for a in ('ETH', 'BTC')}
    PCR = PT.reads(PT.load_pcr('BTC'))
    DAY = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
    DPOS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in ('ETH', 'BTC')}
    LR = {a: [None] + [math.log(DAY[a]['close'][i] / DAY[a]['close'][i - 1]) for i in range(1, len(DAY[a]['close']))] for a in ('ETH', 'BTC')}
    MF = {}; volok = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            MF[(a, tf)], volok[(a, tf)] = mfi_sig(f'data/{a}_{tf}.csv')
    CT = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            b = E.load(f'data/{a}_{tf}.csv'); CT[(a, tf)] = E.rsi(b['close'], 14)
    for r in rows:
        a, tf, d0 = r['a'], r['tf'], r['d0']
        r['btc3'] = a == 'ETH' and tf in ('1D', '2D') and near(d0, ('BTC', '3D'))
        r['btcx'] = a == 'BTC' and tf in ('1D', '2D') and near(d0, ('ETH', '2D'))
        r['b3e3'] = a == 'ETH' and tf == '3D' and near(d0, ('BTC', '3D'))
        r['e3b3'] = a == 'BTC' and tf == '3D' and near(d0, ('ETH', '3D'))
        v = fb.get((a, d0)); r['fund'] = None if v is None else (not v)
        f = FSr[a]
        w7 = [f[d0 - dt.timedelta(days=k)] for k in range(7) if d0 - dt.timedelta(days=k) in f]
        w7b = [f[d0 - dt.timedelta(days=14 + k)] for k in range(7) if d0 - dt.timedelta(days=14 + k) in f]
        r['fcool'] = (sum(w7) / len(w7) >= sum(w7b) / len(w7b)) if len(w7) >= 5 and len(w7b) >= 5 else None
        sun = d0 - dt.timedelta(days=(d0.weekday() + 1) % 7); x = PCR.get(sun)
        r['k1'] = None if a != 'BTC' or x is None else x['pct'] >= 95
        i = DPOS[a].get(d0)
        if i is not None and i >= 181:
            v30 = st.pstdev(LR[a][i - 29:i + 1]); v180 = st.pstdev(LR[a][i - 179:i + 1])
            r['f11'] = v30 / v180 if v180 else None
        else:
            r['f11'] = None
        ct = CT[(a, tf)]; ei = r['ei']; ti = ei - 3
        r['f17'] = ct[ei] - ct[ti] if ct[ei] is not None and ct[ti] is not None else None
        r['mfis'] = MF[(a, tf)][ei] if volok[(a, tf)] > 50 else None
    # discovery cut points per chart
    for key, fld, top in (('volc', 'f11', 'below'), ('fastct', 'f17', 'above')):
        for a in ('ETH', 'BTC'):
            for tf in ('1D', '2D', '3D', '5D', '8D'):
                vals = sorted(r[fld] for r in rows if r['a'] == a and r['tf'] == tf and r[fld] is not None and r['d0'] < SPLIT)
                cut = vals[int(2 * len(vals) / 3)] if len(vals) >= 9 else None
                for r in rows:
                    if r['a'] == a and r['tf'] == tf:
                        r[key] = None if cut is None or r[fld] is None else (r[fld] < cut if top == 'below' else r[fld] >= cut)
    LENS = {'GAP': lambda r: r['gap'] is not None and r['gap'] > 5, 'HIGH': lambda r: bool(r['higher']),
            'AGREE': lambda r: r['agree'] >= 2, 'UP8': lambda r: bool(r['up8']), 'BTC3': lambda r: bool(r['btc3']),
            'FUND': lambda r: r['fund'] is True, 'FCOOL': lambda r: r['fcool'] is True, 'BTCX': lambda r: bool(r['btcx']),
            'B3E3': lambda r: bool(r['b3e3']), 'E3B3': lambda r: bool(r['e3b3']), 'K1': lambda r: r['k1'] is True,
            'VOLC': lambda r: r['volc'] is True, 'FASTCT': lambda r: r['fastct'] is True, 'MFIS': lambda r: r['mfis'] is True}
    NEED = {'FUND': 'fund', 'FCOOL': 'fcool', 'K1': 'k1', 'VOLC': 'volc', 'FASTCT': 'fastct', 'MFIS': 'mfis'}
    G1.LENS.update(LENS)
    has = lambda r, k: k not in NEED or r[NEED[k]] is not None
    P('GRADE AUDIT 2: B3E3 E3B3 K1 VOLC FASTCT MFIS + 8D grading -- declared 28 Oct 2026, run', dt.date.today(),
      '| entry quality only, computed signals, not fills\n')
    added = {}
    graded = [r for r in rows if r['tf'] in ('1D', '2D', '3D', '5D')]
    for a in ('ETH', 'BTC'):
        A = [r for r in graded if r['a'] == a]
        cands = {'ETH': ['B3E3', 'VOLC', 'FASTCT', 'MFIS'], 'BTC': ['E3B3', 'K1', 'VOLC', 'FASTCT', 'MFIS']}[a]
        P(a); keep = []
        for k in cands:
            U = [r for r in A if has(r, k)]
            if k == 'B3E3': U = [r for r in U if r['tf'] == '3D']
            if k == 'E3B3': U = [r for r in U if r['tf'] == '3D']
            per = [G1.eff([r for r in U if sel(r)], k) for sel in (lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT)]
            ok = all(e and e['nw'] >= 15 and e['no'] >= 15 and ((e['cut'] >= 2 and e['lift'] >= -3) or (e['lift'] >= 5 and e['cut'] >= -3)) for e in per)
            tot = G1.eff(U, k)
            P(f'  STEP 1 {k}: ' + ' | '.join(f'{lab} cut {e["cut"]:+5.1f} lift {e["lift"]:+5.1f} (n {e["nw"]}/{e["no"]})' if e else f'{lab} -'
                                             for lab, e in zip(('to 2021', '2022 on'), per))
              + (f' | pooled cut {tot["cut"]:+.1f} lift {tot["lift"]:+.1f} (n {tot["nw"]}/{tot["no"]})' if tot else '') + f'  -> {"pass" if ok else "drop"}')
            if not ok: continue
            twice = False
            for other in LIVE[a] + keep:
                UU = [r for r in U if has(r, other)]
                for hv in (True, False):
                    e = G1.eff([r for r in UU if LENS[other](r) == hv], k)
                    if e is None or (e['cut'] < 1 and e['lift'] < 1):
                        P(f'  STEP 2 {k} adds nothing inside {other}={hv}: dropped'); twice = True; break
                if twice: break
            if twice: continue
            metric = 'cut' if tot['cut'] >= 2 else 'lift'; real = tot[metric]; sh = []; rnd = random.Random(6)
            for _ in range(40):
                byy = {}
                for r in U: byy.setdefault(r['yr'], []).append(r)
                flag = {}
                for y, lst in byy.items():
                    m = sum(LENS[k](r) for r in lst); pick = set(id(x) for x in rnd.sample(lst, m))
                    for r in lst: flag[id(r)] = id(r) in pick
                W = [r for r in U if flag[id(r)]]; O = [r for r in U if not flag[id(r)]]
                sw, so = G1.S(W), G1.S(O)
                sh.append((so['l30'] - sw['l30']) if metric == 'cut' else (sw['win'] - so['win']))
            sh.sort(); p95 = sh[int(0.95 * len(sh)) - 1]
            okp = real > p95
            P(f'  PLACEBO {k} on {metric}: real {real:+.1f} vs shuffled median {st.median(sh):+.1f}, p95 {p95:+.1f} -> {"KEEP" if okp else "drop"}')
            if okp: keep.append(k)
        added[a] = keep
        P(f'  {a} lenses added: {", ".join(keep) or "none"}\n')
    gr = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'
    for a in ('ETH', 'BTC'):
        for label, lens in (('live lenses', LIVE[a]), ('with additions', LIVE[a] + added[a])):
            if label == 'with additions' and not added[a]: continue
            A = [r for r in graded if r['a'] == a and all(has(r, k) for k in lens)]
            P(f'STEP 3 {a}, {label} ({", ".join(lens)}; {len(A)} signals)')
            for pl, sel in (('all', lambda r: True), ('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
                parts = []
                for g in ('A+', 'A', 'B', 'C'):
                    Gs = [r for r in A if sel(r) and gr(sum(LENS[k](r) for k in lens)) == g]
                    if not Gs: parts.append(f'{g} n=0'); continue
                    s = G1.S(Gs); parts.append(f'{g} n={s["n"]:3} +20% {s["win"]:3.0f}% -30% {s["l30"]:3.0f}% dd {s["dd"]:+5.1f}%')
                P(f'    {pl:8} ' + ' | '.join(parts))
    P('\n8D GRADING (live lenses applied to 8D signals)')
    g8 = {}
    for a in ('ETH', 'BTC'):
        A = [r for r in rows if r['a'] == a and r['tf'] == '8D' and all(has(r, k) for k in LIVE[a])]
        ok = True
        for pl, sel in (('all', lambda r: True), ('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
            parts = []; hi = [r for r in A if sel(r) and gr(sum(LENS[k](r) for k in LIVE[a])) in ('A', 'A+')]
            lo = [r for r in A if sel(r) and gr(sum(LENS[k](r) for k in LIVE[a])) == 'C']
            for g in ('A+', 'A', 'B', 'C'):
                Gs = [r for r in A if sel(r) and gr(sum(LENS[k](r) for k in LIVE[a])) == g]
                parts.append(f'{g} n=0' if not Gs else f'{g} n={len(Gs):2} +20% {G1.S(Gs)["win"]:3.0f}% -30% {G1.S(Gs)["l30"]:3.0f}%')
            P(f'  {a} 8D {pl:8} ' + ' | '.join(parts))
            if pl != 'all':
                if len(hi) < 5 or len(lo) < 5: ok = False
                else:
                    sh, sl = G1.S(hi), G1.S(lo)
                    if not (sh['win'] > sl['win'] and sh['l30'] < sl['l30']): ok = False
        g8[a] = ok
        P(f'  {a} 8D graded from now on: {"YES" if ok else "no"}')
    P('\n  ENTRY QUALITY ONLY. Computed signals, not fills.')
    json.dump({'added': added, 'grade8D': g8}, open(os.path.join(HERE, 'grade6.json'), 'w'))
    open(os.path.join(HERE, 'RESULTS_grade6.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
