"""Conviction grade AUDIT: every documented entry read not yet tried as a lens.
DECLARED 28 Oct 2026 00:10 ET, before running. Jared, 27 Oct: "double check
everything... make sure you grab everything." Going through docs/PRETRADE.md
and CONTEXT.md, these documented reads had not been put through the grade's
lens rules (grade.py tried GAP HIGH AGREE UP8 BTC3 FUND; grade2.py tried DIVS
DIVH BTCX):

  PRIMEGAP  CT above its Signal line AND a prime dot      (PRETRADE Tier 1 #2)
  DIAGAP    CT above its Signal line AND a diamond        (Tier 1 #3)
  MARKER    a diamond or a prime dot, either              (the old dashboard
            "standard" check #1)
  SHALLOW   entry close in the top third of entry / 30-day high close, cut
            points per chart from 2016-21 signals          (Promising, sweep F5)
  FCOOL     funding NOT cooling: 7-day mean funding at or above its level 14
            days earlier (the inverse of the vetotest P3 veto; 2020 on)
  VOLRISE   volume rising into confirmation, top third per chart (sweep F2,
            near miss)
  OTHCT     the other asset's 1D CT above its Signal line at entry (sweep F16,
            near miss)
  WKMOM     weekly CT above its own Signal line, last closed week (joeideas 5b,
            ETH forward-watch)

RULES, identical to grade2.py: STEP 1 per-period keep rule (cut -30% by >= 2
or lift +20% by >= 5, other no more than 3 worse, both periods, n >= 15 each);
STEP 2 overlap against the asset's current lenses (ETH: GAP HIGH AGREE BTC3
FUND; BTC: GAP UP8 BTCX) and against earlier survivors; PLACEBO (flag shuffled
within year, 40 times, real beats p95).
NEW ADOPTION RULE, declared here: ordering score = how many of the 8 checks
"A+ beats B, A+ beats C, A beats B, A beats C" x 2 periods hold, where "beats"
means higher +20% AND lower touched -30%, each cell n >= 8. A survivor is
COUNTED in the grade only if, with it added, the ordering score is at least the
score without it AND A+ beats C in both periods. Otherwise it is reported as a
separate flag beside the grade (as DIVH was). The current grade's own score is
printed first.
ENTRY QUALITY ONLY. Computed signals, never fills.
  python3 -I analysis/grade3.py -> analysis/RESULTS_grade3.txt, grade3.json
"""
import sys, os, json, random, bisect, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E
import grokpack as GP
import pcrtest as PT
import grade as G1
from tagstats import bucket_end
from confirmlag import weekly
from sweep import vols

HERE = os.path.dirname(os.path.abspath(__file__))
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)
CUR = json.load(open(os.path.join(HERE, 'grade.json')))['lenses']
for a, ks in json.load(open(os.path.join(HERE, 'grade2.json'))).items():
    CUR[a] = CUR[a] + [k for k in ks if k != 'DIVH']
CANDS = ['PRIMEGAP', 'DIAGAP', 'MARKER', 'SHALLOW', 'FCOOL', 'VOLRISE', 'OTHCT', 'WKMOM']


def funding_series(a):
    import csv
    out = {}
    for r in csv.DictReader(open(f'data/derivs/{a}_funding_daily.csv')):
        v = r.get('funding_mean')
        if v not in ('', None): out[dt.date.fromisoformat(r['date'])] = float(v)
    return out


def main():
    rows, allsig = GP.build()
    rows = [r for r in rows if r['tf'] in ('1D', '2D', '3D', '5D')]
    b3 = [x['d0'] for x in allsig[('BTC', '3D')]]; e2 = [x['d0'] for x in allsig[('ETH', '2D')]]
    fb = PT.funding_below()
    DAY = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
    POS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in DAY}
    CT1 = {a: (E.rsi(DAY[a]['close'], 14)) for a in DAY}
    EM1 = {a: E.ema(CT1[a], 14) for a in DAY}
    FS = {a: funding_series(a) for a in DAY}
    WK = {}
    for a in DAY:
        w = weekly(DAY[a], 1); ctw = E.rsi(w['close'], 14); WK[a] = (w['end'], ctw, E.ema(ctw, 14))
    SIG = {}
    for a in DAY:
        for tf in ('1D', '2D', '3D', '5D'):
            S, b = E.signals(f'data/{a}_{tf}.csv', regime=GP.GATE)
            SIG[(a, tf)] = (b, vols(f'data/{a}_{tf}.csv'), {bucket_end(b['date'], s['ei']): s for s in S})
    for r in rows:
        a, tf, d0 = r['a'], r['tf'], r['d0']
        r['btc3'] = a == 'ETH' and tf in ('1D', '2D') and any(0 <= (d0 - d).days <= 10 for d in b3)
        r['btcx'] = a == 'BTC' and tf in ('1D', '2D') and any(0 <= (d0 - d).days <= 10 for d in e2)
        v = fb.get((a, d0)); r['fund'] = None if v is None else (not v)
        r['primegap'] = r['gap'] is not None and r['gap'] > 0 and r['prime']
        r['diagap'] = r['gap'] is not None and r['gap'] > 0 and r['dis']
        r['marker'] = bool(r['prime'] or r['dis'])
        i0 = POS[a][d0]; c = DAY[a]['close']
        r['f5'] = r['entry'] / max(c[max(0, i0 - 30):i0 + 1])
        b, V, smap = SIG[(a, tf)]; s = smap.get(d0)
        r['f2'] = None
        if s:
            ti, ei = s['ti'], s['ei']
            cv = [x for x in V[ti + 1:ei + 1] if x]
            if cv and V[ti]: r['f2'] = float(np.mean(cv)) / V[ti]
        o = 'BTC' if a == 'ETH' else 'ETH'; oi = POS[o].get(d0)
        r['othct'] = oi is not None and CT1[o][oi] is not None and EM1[o][oi] is not None and CT1[o][oi] > EM1[o][oi]
        f = FS[a]
        w7 = [f[d0 - dt.timedelta(days=k)] for k in range(7) if d0 - dt.timedelta(days=k) in f]
        w7b = [f[d0 - dt.timedelta(days=14 + k)] for k in range(7) if d0 - dt.timedelta(days=14 + k) in f]
        r['fcool_ok'] = len(w7) >= 5 and len(w7b) >= 5
        r['fcool'] = r['fcool_ok'] and np.mean(w7) >= np.mean(w7b)
        ends, ctw, emw = WK[a]; k = bisect.bisect_right(ends, d0) - 1
        r['wkmom'] = k >= 0 and ctw[k] is not None and emw[k] is not None and ctw[k] > emw[k]
    for key, out in (('f5', 'shallow'), ('f2', 'volrise')):
        for a in DAY:
            for tf in ('1D', '2D', '3D', '5D'):
                vals = [r[key] for r in rows if r['a'] == a and r['tf'] == tf and r['d0'] < SPLIT and r[key] is not None]
                q2 = float(np.percentile(vals, 200 / 3)) if len(vals) >= 9 else None
                for r in rows:
                    if r['a'] == a and r['tf'] == tf:
                        r[out] = q2 is not None and r[key] is not None and r[key] >= q2
    LK = {'PRIMEGAP': 'primegap', 'DIAGAP': 'diagap', 'MARKER': 'marker', 'SHALLOW': 'shallow', 'FCOOL': 'fcool',
          'VOLRISE': 'volrise', 'OTHCT': 'othct', 'WKMOM': 'wkmom', 'BTCX': 'btcx'}
    for k, f in LK.items():
        G1.LENS[k] = (lambda f: (lambda r: bool(r[f])))(f)
    P('GRADE AUDIT -- declared 28 Oct 2026, run', dt.date.today(), '| entry quality only, computed signals, not fills\n')
    P('Current lenses: ETH ' + ', '.join(CUR['ETH']) + ' | BTC ' + ', '.join(CUR['BTC']) + '\n')
    added = {}; flags = {}
    for a in ('ETH', 'BTC'):
        A = [r for r in rows if r['a'] == a]
        keep = []; P(a)
        for k in CANDS:
            U = [r for r in A if r['fcool_ok']] if k == 'FCOOL' else A
            per = [G1.eff([r for r in U if sel(r)], k) for sel in (lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT)]
            ok = all(e and e['nw'] >= 15 and e['no'] >= 15 and
                     ((e['cut'] >= 2 and e['lift'] >= -3) or (e['lift'] >= 5 and e['cut'] >= -3)) for e in per)
            tot = G1.eff(U, k)
            P(f'  STEP 1 {k:8} ' + ' | '.join(f'{lab} cut {e["cut"]:+5.1f} lift {e["lift"]:+5.1f} (n {e["nw"]}/{e["no"]})' if e else f'{lab} -'
                                               for lab, e in zip(('to 2021', '2022 on'), per))
              + (f' | pooled cut {tot["cut"]:+.1f} lift {tot["lift"]:+.1f}' if tot else '') + f'  -> {"pass" if ok else "drop"}')
            if not ok: continue
            twice = None
            for other in CUR[a] + keep:
                UU = [r for r in U if (other != 'FUND' or r['fund'] is not None)]
                for h in (True, False):
                    e = G1.eff([r for r in UU if G1.LENS[other](r) == h], k)
                    if e is None or (e['cut'] < 1 and e['lift'] < 1):
                        twice = (other, h); break
                if twice: break
            if twice:
                P(f'  STEP 2 {k} adds nothing inside {twice[0]}={twice[1]}: dropped (that lens already covers it)'); continue
            metric = 'cut' if tot['cut'] >= 2 else 'lift'
            real = tot[metric]; sh = []; rnd = random.Random(5)
            byy = {}
            for r in U: byy.setdefault(r['yr'], []).append(r)
            for _ in range(40):
                flag = {}
                for y, lst in byy.items():
                    m = sum(G1.LENS[k](r) for r in lst); pick = set(id(x) for x in rnd.sample(lst, m))
                    for r in lst: flag[id(r)] = id(r) in pick
                W = [r for r in U if flag[id(r)]]; O = [r for r in U if not flag[id(r)]]
                sw, so = G1.S(W), G1.S(O)
                sh.append((so['l30'] - sw['l30']) if metric == 'cut' else (sw['win'] - so['win']))
            sh.sort(); p95 = sh[int(0.95 * len(sh)) - 1]
            P(f'  PLACEBO {k} on {metric}: real {real:+.1f} vs shuffled median {st.median(sh):+.1f}, p95 {p95:+.1f} -> {"pass" if real > p95 else "drop"}')
            if real > p95: keep.append(k)
        # adoption: ordering with each survivor added one at a time
        def order(lens):
            Ab = [r for r in A if ('FUND' not in lens or r['fund'] is not None) and ('FCOOL' not in lens or r['fcool_ok'])]
            for r in Ab:
                c = sum(G1.LENS[x](r) for x in lens); r['g'] = 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'
            score = 0; apc = True; detail = []
            for pl, sel in (('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
                cells = {g: G1.S([r for r in Ab if r['g'] == g and sel(r)]) for g in ('A+', 'A', 'B', 'C')}
                detail.append(pl + ' ' + ' '.join(f'{g} {s["win"]:.0f}%/{s["l30"]:.0f}% (n{s["n"]})' if s else f'{g} -' for g, s in cells.items()))
                for top in ('A+', 'A'):
                    for low in ('B', 'C'):
                        t, l = cells[top], cells[low]
                        good = t is not None and l is not None and t['n'] >= 8 and l['n'] >= 8 and t['win'] > l['win'] and t['l30'] < l['l30']
                        score += good
                        if top == 'A+' and low == 'C' and not good: apc = False
            return score, apc, detail
        base_score, base_apc, base_detail = order(CUR[a])
        P(f'  ORDER, current grade: score {base_score}/8 | ' + ' | '.join(base_detail))
        counted = []
        for k in keep:
            sc, apc, detail = order(CUR[a] + counted + [k])
            okord = sc >= base_score and apc
            P(f'  ORDER with {k} counted: score {sc}/8 | ' + ' | '.join(detail) + f' -> {"COUNT IT" if okord else "flag only"}')
            if okord: counted.append(k); base_score = sc
            else: flags.setdefault(a, []).append(k)
        added[a] = counted
        P(f'  {a}: counted {", ".join(counted) or "none"}; flag only {", ".join(flags.get(a, [])) or "none"}\n')
    P('  ENTRY QUALITY ONLY. Computed signals, not fills.')
    json.dump(dict(counted=added, flags=flags), open(os.path.join(HERE, 'grade3.json'), 'w'))
    open(os.path.join(HERE, 'RESULTS_grade3.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
