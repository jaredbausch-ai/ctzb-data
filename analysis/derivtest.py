"""Does perp positioning (funding, long/short ratio, open interest) sort CTZB signals?

DECLARED BEFORE RUNNING (23 Oct 2026). Data: data/derivs/ from Coinalyze (13 perp
markets per asset). Judged against Jared's standard (CONTEXT.md, Standing
instructions): nothing below 70%; a change to the stack should reach ~80% while
keeping >= 80% of winners. He trades ~3.3x, so drawdown below entry is scored too.

  signals    regime-gated signals, ETH 1D/2D/3D/5D and BTC 1D/2D/3D/5D, entry =
             confirmation close (d0), daily candles, full 60-day window only
  periods    funding and long/short: DISCOVERY entries 2020-06-01..2022-12-31,
             HOLDOUT 2023-01-01 on. Open interest exists only from 2022-09-13, so
             OI features: DISCOVERY 2022-10-01..2024-06-30, HOLDOUT 2024-07-01 on.
  outcomes   win = reach +20% within 60d; safe win = +20% before touching -20%;
             deep = touched -20% within 60d; also -30% touch
  positioning features at d0 (all from data up to and including d0; tercile cut
  points from DISCOVERY only, per asset):
    P1  funding (simple mean across markets) negative           (shorts paying)
    P2  7-day mean funding in the bottom third
    P3  7-day mean funding lower than it was 14 days earlier    (cooling)
    P4  funding below its own prior-90-day median
    P5  long/short ratio below its prior-90-day median          (crowd leaning short)
    P6  long/short ratio fell over the prior 14 days
    P7  open interest 14-day change in the bottom third         (deleveraged)
    P8  price down and open interest up over the prior 14 days  (shorts building)
    P9  open interest / its 30-day average in the bottom third
    P10 open interest fell more than price over 14 days         (washout)
  stack features (as analysis/standard.py): gap>5, CT>Signal, prime, diamond,
    bucket A, higher entry, own agree 2+, other asset 10d, 8D rising
  combos     every P alone; every P AND a stack feature; every P AND another P
  groups     ETH pooled, BTC pooled, all charts pooled
  verdicts   MEETS STANDARD: win >= 70% and keeps >= 80% of winners in BOTH
             periods (n >= 15 kept in each)
             A-GRADE CANDIDATE: win >= 70% AND safe win >= 65% in BOTH periods,
             n >= 15 kept in each, any retention (a narrow setup)
  correction after the first run: funding was first read from the OI-weighted
             column, which is blank before Sep 2022 (no OI), so every funding
             feature came back n/a for 2020-22. Switched to the simple mean across
             markets; no other change.
  caution    many combos; both periods are required. Short history: 2022-26 for
             OI is one market cycle. Entry quality only, no strategy return.

Run from the repo root:  python3 -I analysis/derivtest.py
"""
import sys, os, csv, itertools, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end, measure
from sweep import closed_index

CHARTS = ['ETH_1D', 'ETH_2D', 'ETH_3D', 'ETH_5D', 'BTC_1D', 'BTC_2D', 'BTC_3D', 'BTC_5D']
FL_D = (dt.date(2020, 6, 1), dt.date(2022, 12, 31)); FL_H0 = dt.date(2023, 1, 1)
OI_D = (dt.date(2022, 10, 1), dt.date(2024, 6, 30)); OI_H0 = dt.date(2024, 7, 1)
OI_FEATS = {'P7', 'P8', 'P9', 'P10'}


def series(path, col):
    out = {}
    with open(path) as f:
        rd = csv.DictReader(f)
        for r in rd:
            v = r.get(col, '')
            if v not in ('', None):
                out[dt.date.fromisoformat(r['date'])] = float(v)
    return out


def back(s, d, n):
    return [s[d - dt.timedelta(days=k)] for k in range(n) if (d - dt.timedelta(days=k)) in s]


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    dated = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            s, b = E.signals(f'data/{a}_{tf}.csv', regime=gate)
            dated[(a, tf)] = [bucket_end(b['date'], x['ei']) for x in s if bucket_end(b['date'], x['ei'])]
    pos = {}
    for a in ('ETH', 'BTC'):
        pos[a] = dict(fund=series(f'data/derivs/{a}_funding_daily.csv', 'funding_mean'),
                      ls=series(f'data/derivs/{a}_lsratio_daily.csv', 'ls_ratio_mean'),
                      oi=series(f'data/derivs/{a}_oi_daily.csv', 'oi_usd_total'))
    rows = []
    for ch in CHARTS:
        a, tf = ch.split('_'); o = 'BTC' if a == 'ETH' else 'ETH'
        day = E.load(f'data/{a}_1D.csv'); P = {d: i for i, d in enumerate(day['date'])}; last = day['date'][-2]
        cl = dict(zip(day['date'], day['close']))
        b8 = E.load(f'data/{a}_8D.csv'); ct8 = E.rsi(b8['close'], 14)
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
        prev_entry = None
        for s in sig:
            d0 = bucket_end(b['date'], s['ei']); ei = s['ei']
            pe, prev_entry = prev_entry, s['entry']
            if d0 is None or d0 not in P or d0 < FL_D[0] or d0 + dt.timedelta(days=61) > last:
                continue
            m = measure(day, P, d0, s['entry'], 60)
            if not m:
                continue
            e0 = s['entry']; sw = False
            for k in range(1, 61):
                j = P.get(d0 + dt.timedelta(days=k))
                if j is None:
                    continue
                if day['low'][j] <= e0 * 0.8:
                    break
                if day['high'][j] >= e0 * 1.2:
                    sw = True; break
            g = ct[ei] - em[ei] if ct[ei] is not None and em[ei] is not None else None
            k8 = closed_index(b8['date'], d0)
            f = {'gap>5': g is not None and g > 5, 'CT>Signal': g is not None and g > 0, 'prime': s['prime'],
                 'diamond': s['dis'], 'bucket A': s['bk'] == 'A', 'higher entry': pe is not None and e0 > pe,
                 'own agree 2+': sum(1 for t in ('1D', '2D', '3D', '5D', '8D') if t != tf and
                                     any(0 <= (d0 - x).days <= 10 for x in dated[(a, t)])) >= 2,
                 'other asset 10d': any(any(0 <= (d0 - x).days <= 10 for x in dated[(o, t)]) for t in ('1D', '2D', '3D', '5D')),
                 '8D rising': k8 >= 1 and ct8[k8] is not None and ct8[k8 - 1] is not None and ct8[k8] > ct8[k8 - 1]}
            S = pos[a]; raw = {}
            fd = S['fund']
            if d0 in fd:
                raw['P1'] = fd[d0] < 0
                w7 = back(fd, d0, 7); w7b = back(fd, d0 - dt.timedelta(days=14), 7); w90 = back(fd, d0 - dt.timedelta(days=1), 90)
                if len(w7) >= 5:
                    raw['f7'] = float(np.mean(w7))
                    if len(w7b) >= 5:
                        raw['P3'] = np.mean(w7) < np.mean(w7b)
                if len(w90) >= 60:
                    raw['P4'] = fd[d0] < statistics.median(w90)
            ls = S['ls']
            if d0 in ls:
                w90 = back(ls, d0 - dt.timedelta(days=1), 90); p14 = ls.get(d0 - dt.timedelta(days=14))
                if len(w90) >= 60:
                    raw['P5'] = ls[d0] < statistics.median(w90)
                if p14 is not None:
                    raw['P6'] = ls[d0] < p14
            oi = S['oi']; d14 = d0 - dt.timedelta(days=14)
            if d0 in oi and d14 in oi and d14 in cl:
                oc = oi[d0] / oi[d14] - 1; pc = cl[d0] / cl[d14] - 1
                raw['oi14'] = oc
                raw['P8'] = pc < 0 and oc > 0
                raw['P10'] = oc < pc
                w30 = back(oi, d0, 30)
                if len(w30) >= 20:
                    raw['oir'] = oi[d0] / np.mean(w30)
            rows.append(dict(ch=ch, a=a, d=d0, win=m['up'] >= 20, sw=sw, deep=m['dd'] <= -20, d30=m['dd'] <= -30,
                             f=f, raw=raw))
    # tercile features from discovery cut points, per asset
    for a in ('ETH', 'BTC'):
        for key, feat, per in (('f7', 'P2', FL_D), ('oi14', 'P7', OI_D), ('oir', 'P9', OI_D)):
            v = [r['raw'][key] for r in rows if r['a'] == a and per[0] <= r['d'] <= per[1] and key in r['raw']]
            if len(v) < 9:
                continue
            q1 = np.percentile(v, 100 / 3)
            for r in rows:
                if r['a'] == a and key in r['raw']:
                    r['raw'][feat] = r['raw'][key] <= q1
    for r in rows:
        for k in ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10'):
            if k in r['raw']:
                r['f'][k] = bool(r['raw'][k])
    PF = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10']
    SF = ['gap>5', 'CT>Signal', 'prime', 'diamond', 'bucket A', 'higher entry', 'own agree 2+', 'other asset 10d', '8D rising']
    names = {'P1': 'funding negative', 'P2': 'funding 7d low third', 'P3': 'funding cooling', 'P4': 'funding below 90d median',
             'P5': 'L/S below 90d median', 'P6': 'L/S falling 14d', 'P7': 'OI 14d change low third',
             'P8': 'price down, OI up', 'P9': 'OI vs 30d avg low third', 'P10': 'OI fell more than price'}
    combos = [(p,) for p in PF] + [(p, s) for p in PF for s in SF] + list(itertools.combinations(PF, 2))
    groups = {'ETH': [r for r in rows if r['a'] == 'ETH'], 'BTC': [r for r in rows if r['a'] == 'BTC'], 'ALL': rows}

    def periods(cb):
        if any(c in OI_FEATS for c in cb):
            return (OI_D[0], OI_D[1]), (OI_H0, dt.date(2100, 1, 1))
        return (FL_D[0], FL_D[1]), (FL_H0, dt.date(2100, 1, 1))

    print('Baseline (no positioning filter), win / safe win / touched -20% / touched -30%:')
    for gname, G in groups.items():
        t = []
        for lab, (a0, a1) in (('2020-22', FL_D), ('2023-26', (FL_H0, dt.date(2100, 1, 1))),
                              ('OI 2022-24', OI_D), ('OI 2024-26', (OI_H0, dt.date(2100, 1, 1)))):
            x = [r for r in G if a0 <= r['d'] <= a1]
            if x:
                t.append(f'{lab}: {100*np.mean([r["win"] for r in x]):.0f}/{100*np.mean([r["sw"] for r in x]):.0f}/'
                         f'{100*np.mean([r["deep"] for r in x]):.0f}/{100*np.mean([r["d30"] for r in x]):.0f} n={len(x)}')
        print(f'  {gname:<4} ' + '   '.join(t))
    print('\nSingle positioning features, ALL charts pooled (win yes vs no, discovery | holdout):')
    for p in PF:
        (a0, a1), (h0, h1) = periods((p,))
        out = []
        for lo, hi in ((a0, a1), (h0, h1)):
            y = [r for r in rows if lo <= r['d'] <= hi and r['f'].get(p) is True]
            n = [r for r in rows if lo <= r['d'] <= hi and r['f'].get(p) is False]
            if y and n:
                out.append(f'{100*np.mean([r["win"] for r in y]):3.0f}% vs {100*np.mean([r["win"] for r in n]):3.0f}% '
                           f'(n {len(y)}/{len(n)}), -20% {100*np.mean([r["deep"] for r in y]):.0f} vs {100*np.mean([r["deep"] for r in n]):.0f}')
            else:
                out.append('n/a')
        print(f'  {p:<4}{names[p]:<26} ' + '  |  '.join(out))
    meets, agrade, closest = [], [], []
    for gname, G in groups.items():
        for cb in combos:
            res = {}
            for lab, (lo, hi) in zip(('D', 'H'), periods(cb)):
                x = [r for r in G if lo <= r['d'] <= hi and all(c in r['f'] for c in cb)]
                W = sum(r['win'] for r in x)
                k = [r for r in x if all(r['f'][c] for c in cb)]
                if not x or not W or not k:
                    res = None; break
                res[lab] = dict(win=100 * np.mean([r['win'] for r in k]), sw=100 * np.mean([r['sw'] for r in k]),
                                keep=100 * sum(r['win'] for r in k) / W, n=len(k),
                                deep=100 * np.mean([r['deep'] for r in k]), d30=100 * np.mean([r['d30'] for r in k]))
            if res is None or not all(res[p]['n'] >= 15 for p in res):
                continue
            if all(res[p]['win'] >= 70 and res[p]['keep'] >= 80 for p in res):
                meets.append((gname, cb, res))
            if all(res[p]['win'] >= 70 and res[p]['sw'] >= 65 for p in res):
                agrade.append((gname, cb, res))
            closest.append((gname, cb, res))
    nm = lambda cb: ' + '.join(names.get(c, c) for c in cb)
    fm = lambda r: (f'win {r["win"]:.0f}% safe {r["sw"]:.0f}% keeps {r["keep"]:.0f}% of winners, '
                    f'-20% {r["deep"]:.0f}% -30% {r["d30"]:.0f}% (n={r["n"]})')
    print(f'\nTested {len(combos)} combos x {len(groups)} groups')
    print('\nMEETS STANDARD (>=70% win, keeps >=80% of winners, both periods): ' + ('none' if not meets else ''))
    for g, cb, r in meets:
        print(f'  {g:<4} {nm(cb):<48} D: {fm(r["D"])}\n  {"":<53}H: {fm(r["H"])}')
    print('\nA-GRADE CANDIDATES (>=70% win and >=65% safe win, both periods, n>=15 each): ' + ('none' if not agrade else ''))
    for g, cb, r in sorted(agrade, key=lambda x: -min(x[2]['D']['sw'], x[2]['H']['sw'])):
        print(f'  {g:<4} {nm(cb):<48} D: {fm(r["D"])}\n  {"":<53}H: {fm(r["H"])}')
    print('\nCLOSEST by worst-period win rate (n>=15 both):')
    for g, cb, r in sorted(closest, key=lambda x: -min(x[2]['D']['win'], x[2]['H']['win']))[:12]:
        print(f'  {g:<4} {nm(cb):<48} D: {fm(r["D"])}\n  {"":<53}H: {fm(r["H"])}')


if __name__ == '__main__':
    main()
