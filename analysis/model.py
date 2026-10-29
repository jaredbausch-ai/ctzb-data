"""Every trade its own odds. DECLARED 28 Oct 2026 21:05 ET, before running.

Jared, 28 Oct: "every trade should be its own kind of thing, not crushed into a
bucket" -- use every edge that makes sense, in every combination, and keep only what
holds up. The guard against fitting history is walk-forward: each year's signals are
scored only by a model trained on signals whose 60 days had finished before that year
began.

DATA  every regime-gated, completed signal on ETH and BTC, 1D 2D 3D 5D 8D, with the
      same features the live stack computes (stack_live.py, read through its hook).
INPUTS (0/1; a missing read counts 0 and has its own "missing" input)
  lenses and reads: GAP HIGH AGREE BTC3 FUND FCOOL UP8 BTCX DIVH PRIME DIAMOND SHALLOW
  FASTCT B3E3 E3B1 K1 W5B, plus long/short ratio falling and OBV above its average;
  tags: bucket A / B / C; chart: asset and timeframe.
MODELS
  G   the live grade's own odds: each (asset, grade) group's rate in the training years
  M1  logistic regression on the inputs, L2 penalty 1.0 (fixed in advance, not tuned)
  M2  M1 plus every pair of reads multiplied together and every read times asset,
      L2 penalty 5.0 (fixed in advance)
TARGETS  reached +10%, +20%, +30% within 60 days; touched -30% within 60 days.
TEST YEARS  2019 to 2025, one at a time.
PASS RULE (per target, set now)
  A model replaces the grade's odds for a target if, over all test years pooled, it
  has a lower Brier score AND a higher AUC than G on BOTH assets separately, AND a
  lower Brier score than G in at least 4 of the 7 test years. If both models pass,
  M2 is used only if its pooled Brier is lower than M1's.
WRITES  analysis/RESULTS_model.txt; analysis/model.json (weights of the passing model
        per target, refit on all completed signals, for the live stack);
        datasets/ledger_odds.csv (each past signal's walk-forward odds: what the model
        would have said on the day, out of sample).
Entry quality only. Computed signals, not fills.
  python3 -I analysis/model.py
"""
import os, sys, json, math, csv, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
os.chdir(ROOT)
import stack_live as SL

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
READS = ['GAP', 'HIGH', 'AGREE', 'BTC3', 'FUND', 'FCOOL', 'UP8', 'BTCX', 'DIVH', 'PRIME', 'DIAMOND',
         'SHALLOW', 'FASTCT', 'B3E3', 'E3B1', 'K1', 'W5B', 'LSF', 'OBV']
NA = ['FUND', 'FCOOL', 'K1', 'W5B', 'LSF', 'OBV', 'SHALLOW', 'FASTCT']
TARGETS = {'reach10': lambda r: r['m']['up'] >= 10, 'reach20': lambda r: r['m']['up'] >= 20,
           'reach30': lambda r: r['m']['up'] >= 30, 'touch30': lambda r: r['m']['dd'] <= -30}
YEARS = list(range(2019, 2026))
LAM = {'M1': 1.0, 'M2': 5.0}


def capture(loc):
    return loc


def raw(r, F):
    v = dict(F)
    v['LSF'] = r.get('lsfall'); v['OBV'] = r.get('obv')
    return v


def vec(r, F, kind):
    v = raw(r, F); x = {}
    for k in READS:
        x[k] = 1.0 if v.get(k) else 0.0
    for k in NA:
        x['NA_' + k] = 1.0 if v.get(k) is None else 0.0
    for b in ('A', 'B', 'C'):
        x['BK_' + b] = 1.0 if r['bk'] == b else 0.0
    x['ETH'] = 1.0 if r['a'] == 'ETH' else 0.0
    for tf in ('2D', '3D', '5D', '8D'):
        x['TF_' + tf] = 1.0 if r['tf'] == tf else 0.0
    if kind == 'M2':
        for i, p in enumerate(READS):
            for q in READS[i + 1:]:
                x[p + '*' + q] = x[p] * x[q]
            x['ETH*' + p] = x['ETH'] * x[p]
    return x


def fit(X, y, lam):
    X1 = np.hstack([np.ones((X.shape[0], 1)), X]); w = np.zeros(X1.shape[1])
    pen = np.full(X1.shape[1], lam); pen[0] = 0.0
    for _ in range(50):
        z = np.clip(X1 @ w, -30, 30); p = 1 / (1 + np.exp(-z))
        g = X1.T @ (p - y) + pen * w
        H = (X1.T * (p * (1 - p))) @ X1 + np.diag(pen) + 1e-9 * np.eye(len(w))
        step = np.linalg.solve(H, g); w -= step
        if np.max(np.abs(step)) < 1e-6: break
    return w


def predict(w, X):
    X1 = np.hstack([np.ones((X.shape[0], 1)), X]); return 1 / (1 + np.exp(-np.clip(X1 @ w, -30, 30)))


def auc(p, y):
    pos = p[y == 1]; neg = p[y == 0]
    if len(pos) == 0 or len(neg) == 0: return float('nan')
    order = np.argsort(np.concatenate([pos, neg])); ranks = np.empty(len(order)); ranks[order] = np.arange(1, len(order) + 1)
    # average ties
    allv = np.concatenate([pos, neg])
    for v in np.unique(allv):
        idx = np.where(allv == v)[0]
        if len(idx) > 1: ranks[idx] = ranks[idx].mean()
    return (ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def brier(p, y): return float(np.mean((p - y) ** 2))


def main():
    SL._HOOK = capture
    C = SL.main()
    feats, rows = C['feats'], C['rows']
    LENS = json.load(open('analysis/grade.json'))['lenses']
    for k, v in json.load(open('analysis/grade2.json')).items(): LENS[k] = LENS[k] + [x for x in v if x != 'DIVH']
    for k, v in json.load(open('analysis/grade3.json'))['counted'].items(): LENS[k] = LENS[k] + v
    for k, v in json.load(open('analysis/grade6.json'))['added'].items(): LENS[k] = LENS[k] + v
    gof = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'
    S = [r for r in rows if 'm' in r]
    for r in S:
        F = feats(r); r['_F'] = F
        r['_g'] = gof(sum(1 for k in LENS[r['a']] if F.get(k)))
    keys = {k: sorted(vec(S[0], S[0]['_F'], k).keys()) for k in ('M1', 'M2')}
    Xm = {k: np.array([[vec(r, r['_F'], k)[c] for c in keys[k]] for r in S]) for k in ('M1', 'M2')}
    d0 = np.array([r['d0'].toordinal() for r in S]); yr = np.array([r['d0'].year for r in S])
    asset = np.array([r['a'] for r in S])
    P('EVERY TRADE ITS OWN ODDS -- declared 28 Oct 2026, run', dt.date.today(), f'| {len(S)} completed signals, ETH+BTC 1D-8D | entry quality only\n')
    adopt = {}; oos = {}
    for t, fn in TARGETS.items():
        y = np.array([1.0 if fn(r) else 0.0 for r in S])
        pred = {m: np.full(len(S), np.nan) for m in ('G', 'M1', 'M2')}
        for Y in YEARS:
            cut = dt.date(Y, 1, 1).toordinal() - 61
            tr = d0 < cut; te = yr == Y
            if te.sum() == 0 or tr.sum() < 50: continue
            for m in ('M1', 'M2'):
                w = fit(Xm[m][tr], y[tr], LAM[m]); pred[m][te] = predict(w, Xm[m][te])
            rate = {}
            for i in np.where(tr)[0]: rate.setdefault((S[i]['a'], S[i]['_g']), []).append(y[i])
            base = y[tr].mean()
            for i in np.where(te)[0]:
                v = rate.get((S[i]['a'], S[i]['_g'])); pred['G'][i] = (sum(v) + base * 5) / (len(v) + 5) if v else base
        mask = ~np.isnan(pred['G'])
        oos[t] = {m: pred[m] for m in pred}
        P(f'TARGET {t}: {int(mask.sum())} out-of-sample signals, base rate {y[mask].mean():.0%}')
        res = {}
        for m in ('G', 'M1', 'M2'):
            line = []; ok_assets = True
            for a in ('ETH', 'BTC'):
                mm = mask & (asset == a)
                b = brier(pred[m][mm], y[mm]); u = auc(pred[m][mm], y[mm])
                res[(m, a)] = (b, u); line.append(f'{a} Brier {b:.4f} AUC {u:.3f}')
            bp = brier(pred[m][mask], y[mask]); up = auc(pred[m][mask], y[mask]); res[(m, 'all')] = (bp, up)
            yrs_better = 0
            if m != 'G':
                for Y in YEARS:
                    mm = mask & (yr == Y)
                    if mm.sum() and brier(pred[m][mm], y[mm]) < brier(pred['G'][mm], y[mm]): yrs_better += 1
            # top vs bottom fifth by predicted odds
            pr = pred[m][mask]; yy = y[mask]; q = np.argsort(pr); n5 = len(q) // 5
            top = yy[q[-n5:]].mean(); bot = yy[q[:n5]].mean()
            P(f'  {m:2}  pooled Brier {bp:.4f} AUC {up:.3f} | ' + ' | '.join(line)
              + (f' | beats G on Brier in {yrs_better}/{len(YEARS)} years' if m != 'G' else '')
              + f' | top fifth {top:.0%} vs bottom fifth {bot:.0%}')
            res[(m, 'yrs')] = yrs_better
        passed = [m for m in ('M1', 'M2') if all(res[(m, a)][0] < res[('G', a)][0] and res[(m, a)][1] > res[('G', a)][1] for a in ('ETH', 'BTC')) and res[(m, 'yrs')] >= 4]
        pick = None
        if 'M1' in passed and 'M2' in passed: pick = 'M2' if res[('M2', 'all')][0] < res[('M1', 'all')][0] else 'M1'
        elif passed: pick = passed[0]
        adopt[t] = pick
        P(f'  -> {"ADOPT " + pick if pick else "keep the grade"} for {t}\n')
    # calibration of the adopted reach20 model, by predicted band
    if adopt.get('reach20'):
        m = adopt['reach20']; y = np.array([1.0 if TARGETS['reach20'](r) else 0.0 for r in S]); pr = oos['reach20'][m]; mask = ~np.isnan(pr)
        P(f'CALIBRATION reach20 ({m}, out of sample): predicted band -> actual')
        for lo, hi in ((0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.01)):
            mm = mask & (pr >= lo) & (pr < hi)
            if mm.sum(): P(f'  {lo:.0%}-{min(hi, 1):.0%}: n={int(mm.sum()):4}  predicted {pr[mm].mean():.0%}  actual {y[mm].mean():.0%}')
    # refit adopted models on all completed signals for live use
    model = {'declared': '2026-10-28', 'targets': {}}
    for t, m in adopt.items():
        if not m: continue
        y = np.array([1.0 if TARGETS[t](r) else 0.0 for r in S]); w = fit(Xm[m], y, LAM[m])
        model['targets'][t] = {'kind': m, 'keys': keys[m], 'w': [float(x) for x in w]}
    json.dump(model, open('analysis/model.json', 'w'))
    with open('datasets/ledger_odds.csv', 'w', newline='') as f:
        wr = csv.writer(f); wr.writerow(['chart', 'entry', 'grade'] + [f'{t}_{m}' for t in TARGETS for m in ('G', 'M1', 'M2')])
        for i, r in enumerate(S):
            if np.isnan(oos['reach20']['G'][i]): continue
            wr.writerow([r['ch'], str(r['d0']), r['_g']] + [round(100 * oos[t][m][i]) for t in TARGETS for m in ('G', 'M1', 'M2')])
    P('\n  Adopted:', {t: m for t, m in adopt.items()})
    P('  ENTRY QUALITY ONLY. Computed signals, not fills.')
    open('analysis/RESULTS_model.txt', 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
