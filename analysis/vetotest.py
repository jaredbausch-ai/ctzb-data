"""Can perp positioning tell us which CTZB signals to SKIP?

DECLARED BEFORE RUNNING (25 Oct 2026). analysis/derivtest.py asked whether
positioning finds winners and required a rule to keep >= 80% of winners, which
structurally rules out a veto -- a veto is allowed to drop winners provided it
drops proportionally more losers. This script asks the opposite question on the
same rows, the same gate, the same charts and the same discovery/holdout split.

  veto       a feature is read as "skip the signal when true". Both polarities
             are tested: P and NOT P.
  scored     EXCLUDED set: n, win rate, -30% touch rate (want low win, high -30%)
             KEPT set: n, win rate, safe win, -30% touch (want better than base)
             trade-off: % of all losers removed vs % of all winners removed
  bar        A veto PASSES only if, in BOTH periods, with n >= 15 excluded:
             kept win rate > baseline win rate, kept -30% touch < baseline, and
             losers removed > winners removed (in percentage-of-pool terms).
             He trades ~3.3x, so the -30% column is the one that matters.
  caution    OI exists only from Sep 2022, so OI features use the later split.
             Entry quality only; no strategy return. Many combos, both periods
             required, and a veto that passes still has to survive a per-chart
             split before it goes near docs/PRETRADE.md.

Run from the repo root:  python3 -I analysis/vetotest.py
"""
import sys, os, itertools, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end, measure
from sweep import closed_index
from derivtest import CHARTS, FL_D, FL_H0, OI_D, OI_H0, OI_FEATS, series, back

PF = ['P1','P2','P3','P4','P5','P6','P7','P8','P9','P10']
NAMES = {'P1':'funding negative','P2':'funding 7d low third','P3':'funding cooling',
         'P4':'funding below 90d median','P5':'L/S below 90d median','P6':'L/S falling 14d',
         'P7':'OI 14d change low third','P8':'price down, OI up','P9':'OI vs 30d avg low third',
         'P10':'OI fell more than price'}


def build_rows():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    pos = {a: dict(fund=series(f'data/derivs/{a}_funding_daily.csv','funding_mean'),
                   ls=series(f'data/derivs/{a}_lsratio_daily.csv','ls_ratio_mean'),
                   oi=series(f'data/derivs/{a}_oi_daily.csv','oi_usd_total')) for a in ('ETH','BTC')}
    rows = []
    for ch in CHARTS:
        a, tf = ch.split('_')
        day = E.load(f'data/{a}_1D.csv'); P = {d:i for i,d in enumerate(day['date'])}; last = day['date'][-2]
        cl = dict(zip(day['date'], day['close']))
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        for s in sig:
            d0 = bucket_end(b['date'], s['ei'])
            if d0 is None or d0 not in P or d0 < FL_D[0] or d0 + dt.timedelta(days=61) > last:
                continue
            m = measure(day, P, d0, s['entry'], 60)
            if not m: continue
            e0 = s['entry']; sw = False
            for k in range(1, 61):
                j = P.get(d0 + dt.timedelta(days=k))
                if j is None: continue
                if day['low'][j] <= e0*0.8: break
                if day['high'][j] >= e0*1.2: sw = True; break
            S = pos[a]; raw = {}
            fd = S['fund']
            if d0 in fd:
                raw['P1'] = fd[d0] < 0
                w7 = back(fd,d0,7); w7b = back(fd,d0-dt.timedelta(days=14),7); w90 = back(fd,d0-dt.timedelta(days=1),90)
                if len(w7) >= 5:
                    raw['f7'] = float(np.mean(w7))
                    if len(w7b) >= 5: raw['P3'] = np.mean(w7) < np.mean(w7b)
                if len(w90) >= 60: raw['P4'] = fd[d0] < statistics.median(w90)
            ls = S['ls']
            if d0 in ls:
                w90 = back(ls,d0-dt.timedelta(days=1),90); p14 = ls.get(d0-dt.timedelta(days=14))
                if len(w90) >= 60: raw['P5'] = ls[d0] < statistics.median(w90)
                if p14 is not None: raw['P6'] = ls[d0] < p14
            oi = S['oi']; d14 = d0 - dt.timedelta(days=14)
            if d0 in oi and d14 in oi and d14 in cl:
                oc = oi[d0]/oi[d14]-1; pc = cl[d0]/cl[d14]-1
                raw['oi14'] = oc; raw['P8'] = pc < 0 and oc > 0; raw['P10'] = oc < pc
                w30 = back(oi,d0,30)
                if len(w30) >= 20: raw['oir'] = oi[d0]/np.mean(w30)
            rows.append(dict(ch=ch, a=a, d=d0, win=m['up']>=20, sw=sw, d30=m['dd']<=-30, raw=raw, f={}))
    for a in ('ETH','BTC'):
        for key, feat, per in (('f7','P2',FL_D), ('oi14','P7',OI_D), ('oir','P9',OI_D)):
            v = [r['raw'][key] for r in rows if r['a']==a and per[0] <= r['d'] <= per[1] and key in r['raw']]
            if len(v) < 9: continue
            q1 = np.percentile(v, 100/3)
            for r in rows:
                if r['a']==a and key in r['raw']: r['raw'][feat] = r['raw'][key] <= q1
    for r in rows:
        for k in PF:
            if k in r['raw']: r['f'][k] = bool(r['raw'][k])
    return rows


def stat(S):
    if not S: return None
    n = len(S)
    return dict(n=n, win=100*sum(r['win'] for r in S)/n, sw=100*sum(r['sw'] for r in S)/n,
                d30=100*sum(r['d30'] for r in S)/n)


def score(pool, fire):
    """fire(r) -> True means SKIP this signal."""
    have = [r for r in pool if fire(r) is not None]
    if not have: return None
    exc = [r for r in have if fire(r)]; kep = [r for r in have if not fire(r)]
    if not exc or not kep: return None
    base = stat(have); E_, K = stat(exc), stat(kep)
    W = sum(r['win'] for r in have); L = len(have) - W
    D = sum(r['d30'] for r in have)
    return dict(base=base, exc=E_, kep=K,
                lost_w=100*sum(r['win'] for r in exc)/W if W else 0,
                cut_l=100*sum(1 for r in exc if not r['win'])/L if L else 0,
                cut_d30=100*sum(r['d30'] for r in exc)/D if D else 0)


def main():
    rows = build_rows()
    print(f'{len(rows)} regime-gated signals with positioning data, 8 charts, entries from {FL_D[0]}\n')
    groups = {'ETH':[r for r in rows if r['a']=='ETH'], 'BTC':[r for r in rows if r['a']=='BTC'], 'ALL':rows}
    for gname, g in groups.items():
        b = stat([r for r in g if r['f']])
        if b: print(f'  baseline {gname:<4} n={b["n"]:<4} win {b["win"]:.0f}%   safe {b["sw"]:.0f}%   touched -30% {b["d30"]:.0f}%')
    print()

    cands = []
    for p in PF:
        for pol, lab in ((True,''), (False,' (NOT)')):
            D0,D1,H0 = (OI_D[0],OI_D[1],OI_H0) if p in OI_FEATS else (FL_D[0],FL_D[1],FL_H0)
            fire = lambda r, p=p, pol=pol: (r['f'][p] == pol) if p in r['f'] else None
            out = {}
            ok = True
            for per, sel in (('D', lambda r: D0 <= r['d'] <= D1), ('H', lambda r: r['d'] >= H0)):
                s = score([r for r in rows if sel(r)], fire)
                if not s or s['exc']['n'] < 15: ok = False; break
                out[per] = s
            if not ok: continue
            passes = all(out[q]['kep']['win'] > out[q]['base']['win'] and
                         out[q]['kep']['d30'] < out[q]['base']['d30'] and
                         out[q]['cut_l'] > out[q]['lost_w'] for q in ('D','H'))
            cands.append((p+lab, NAMES[p], out, passes))

    print('EVERY POSITIONING FEATURE READ AS A VETO (skip the signal when true), all charts pooled')
    print('EXCLUDED = what the veto throws away.  Good veto: low win, high -30%, cuts more losers than winners.\n')
    hdr = (f'{"veto":<9}{"":<26}{"per":<4}{"n exc":>6}{"exc win":>9}{"base win":>9}{"kept win":>9}'
           f'{"base -30":>9}{"kept -30":>9}{"losers":>8}{"winners":>9}{"-30s":>7}')
    print(hdr); print('-'*len(hdr))
    print(f'{"":<39}{"":<6}{"":>9}{"":>9}{"":>9}{"":>9}{"":>9}{"  <-- share of each REMOVED by the veto"}')
    for nm, desc, out, passes in sorted(cands, key=lambda c: min(c[2][q]['exc']['win'] for q in ('D','H'))):
        for q in ('D','H'):
            s = out[q]
            lead = f'{nm:<9}{desc:<26}' if q=='D' else ' '*35
            print(f'{lead}{q:<4}{s["exc"]["n"]:>6}{s["exc"]["win"]:>8.0f}%{s["base"]["win"]:>8.0f}%{s["kep"]["win"]:>8.0f}%'
                  f'{s["base"]["d30"]:>8.0f}%{s["kep"]["d30"]:>8.0f}%'
                  f'{s["cut_l"]:>7.0f}%{s["lost_w"]:>8.0f}%{s["cut_d30"]:>6.0f}%')
        edge = min(out[q]['kep']['win'] - out[q]['base']['win'] for q in ('D','H'))
        print(f'{"":<35}{"PASSES" if passes else "fails"} the bar   worst-period kept-win edge {edge:+.0f} pts')
        print()
    print('\nPASSING VETOES: ' + (', '.join(c[0] for c in cands if c[3]) or 'none'))
    print('\n(losers cut = share of ALL losing signals this veto removes; winners cut = share of all winners it costs)')


if __name__ == '__main__':
    main()


def followup():
    """Per-chart split and stack overlap for the vetoes that passed the pooled bar."""
    rows = build_rows()
    import engine as E2
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    # attach gap>5 so we can ask whether the veto is already covered by the stack
    for ch in CHARTS:
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        ct = E.rsi(b['close'],14); em = E.ema(ct,14)
        gm = {}
        for s in sig:
            d0 = bucket_end(b['date'], s['ei'])
            if d0 and ct[s['ei']] is not None and em[s['ei']] is not None:
                gm[d0] = ct[s['ei']] - em[s['ei']]
        for r in rows:
            if r['ch']==ch and r['d'] in gm: r['gap'] = gm[r['d']]
    print('\n' + '='*96)
    print('PER-CHART SPLIT of the two funding vetoes (the guard that killed four findings)')
    print('='*96)
    for p in ('P3','P4'):
        print(f'\n{p}  {NAMES[p]}  -- skip the signal when true')
        print(f'  {"chart":<9}{"n":>5}{"base win":>10}{"kept win":>10}{"edge":>7}{"base -30":>10}{"kept -30":>10}{"n kept":>8}')
        inv = 0
        for ch in CHARTS:
            S = [r for r in rows if r['ch']==ch and p in r['f']]
            if len(S) < 20: continue
            kept = [r for r in S if not r['f'][p]]
            if len(kept) < 10: continue
            b_, k_ = stat(S), stat(kept)
            e = k_['win']-b_['win']
            if e <= 0: inv += 1
            print(f'  {ch:<9}{b_["n"]:>5}{b_["win"]:>9.0f}%{k_["win"]:>9.0f}%{e:>+7.0f}{b_["d30"]:>9.0f}%{k_["d30"]:>9.0f}%{k_["n"]:>8}')
        print(f'  -> {inv} of 8 charts flat or inverted')
    print('\n' + '='*96)
    print('IS THE VETO ALREADY DOING THE STACK\'S JOB?  overlap with gap>5')
    print('='*96)
    for p in ('P3','P4'):
        S = [r for r in rows if p in r['f'] and 'gap' in r]
        fires = [r for r in S if r['f'][p]]
        g5 = [r for r in S if r['gap'] > 5]
        both = [r for r in S if r['f'][p] and r['gap'] > 5]
        exp = len(fires)/len(S)*len(g5)/len(S)*len(S)
        print(f'  {p}: veto fires on {len(fires)}/{len(S)}, gap>5 on {len(g5)}, both on {len(both)} '
              f'(chance would be {exp:.0f}) -- {"independent" if abs(len(both)-exp) < 0.2*exp else "correlated"}')
        kept_g5 = [r for r in g5 if not r['f'][p]]
        a, b2 = stat(g5), stat(kept_g5)
        if a and b2 and b2['n'] >= 15:
            print(f'      gap>5 alone: n={a["n"]} win {a["win"]:.0f}% -30% {a["d30"]:.0f}%   '
                  f'| gap>5 AND veto applied: n={b2["n"]} win {b2["win"]:.0f}% -30% {b2["d30"]:.0f}%')
