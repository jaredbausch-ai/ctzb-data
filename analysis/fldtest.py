"""Do Hurst FLDs sort CTZB signals? DECLARED BEFORE RUNNING, 26 Oct 2026.

An FLD is a transform of price and nothing else, which is the family that has
failed here repeatedly (fibs, moving averages, Elliott wave, opens/closes, money
flow). Elliott in particular is cycle counting and it came back empty. The prior
is low; this is tested because it is cheap, and because the measured-period work
is reusable whatever the answer.

MEASURED FIRST, before any feature was scored: crypto cycles run 1.15-1.34x
Hurst's nominal wavelengths on both assets at all four degrees, and a clean
in-band period exists only 36-60% of the time. So the nominal model is the wrong
input here and the ADAPTIVE FLD is the one that gets tested properly.

DECLARED FEATURES at the entry bar (close vs FLD, FLD from midpoints only):
  H1  above 20D FLD, nominal wavelength       H5  crossed above 20D adaptive <= 3 bars ago
  H2  above 20D FLD, adaptive (measured)      H6  above BOTH 20D and 40D adaptive
  H3  above 40D FLD, adaptive                 H7  above 20D, 40D AND 80D adaptive
  H4  above 80D FLD, adaptive                 H8  a clean 20D period exists at entry

Each scored as SELECTOR (take only when true) and VETO (skip when true), both
polarities, because the 23 Oct run proved a selector bar can hide an exclusion
effect. Survivors face the per-chart split and the regime-age strata.

Run from the repo root:  python3 -I analysis/fldtest.py
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
import fld as F
from tagstats import bucket_end, measure

CHARTS = ['ETH_1D','ETH_2D','ETH_3D','ETH_5D','BTC_1D','BTC_2D','BTC_3D','BTC_5D']
HF = ['H1','H2','H3','H4','H5','H6','H7','H8']
NAMES = {'H1':'above 20D FLD (nominal)','H2':'above 20D FLD (adaptive)',
         'H3':'above 40D FLD (adaptive)','H4':'above 80D FLD (adaptive)',
         'H5':'crossed 20D FLD <=3 bars','H6':'above 20D AND 40D','H7':'above 20D,40D,80D',
         'H8':'clean 20D period exists'}


def build():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    rows = []
    for ch in CHARTS:
        a, tf = ch.split('_'); td = F.TF_DAYS[tf]
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        day = E.load(f'data/{a}_1D.csv'); P = {d:i for i,d in enumerate(day['date'])}; last = day['date'][-2]
        c = b['close']
        f20n, _ = F.fld(b, F.NOMINAL['20D'], td)
        f20, p20, _ = F.adaptive_fld(b, F.NOMINAL['20D'], td)
        f40, _, _ = F.adaptive_fld(b, F.NOMINAL['40D'], td)
        f80, _, _ = F.adaptive_fld(b, F.NOMINAL['80D'], td)
        for s in sig:
            i = s['ei']; d0 = bucket_end(b['date'], i)
            if d0 is None or d0 not in P or d0 + dt.timedelta(days=61) > last: continue
            m = measure(day, P, d0, s['entry'], 60)
            if not m: continue
            ab = lambda s_: (c[i] > s_[i]) if (s_ and s_[i] is not None) else None
            f = {}
            f['H1'] = ab(f20n); f['H2'] = ab(f20); f['H3'] = ab(f40); f['H4'] = ab(f80)
            if f20 and f20[i] is not None:
                prev = [j for j in range(max(0,i-3), i) if f20[j] is not None]
                f['H5'] = bool(f['H2']) and any(c[j] <= f20[j] for j in prev) if prev else None
            f['H6'] = (f['H2'] and f['H3']) if (f['H2'] is not None and f['H3'] is not None) else None
            f['H7'] = (f['H2'] and f['H3'] and f['H4']) if None not in (f['H2'],f['H3'],f['H4']) else None
            f['H8'] = p20[i] is not None
            rows.append(dict(ch=ch, a=a, d=d0, yr=d0.year, win=m['up']>=20, d30=m['dd']<=-30,
                             f={k:v for k,v in f.items() if v is not None}))
    return rows


def st(S):
    return None if not S else dict(n=len(S), win=100*sum(r['win'] for r in S)/len(S),
                                   d30=100*sum(r['d30'] for r in S)/len(S))


def main():
    rows = build()
    print(f'{len(rows)} regime-gated signals, 8 charts, {min(r["d"] for r in rows)} -> {max(r["d"] for r in rows)}')
    b = st(rows); print(f'baseline: n={b["n"]} win {b["win"]:.0f}%  touched -30% {b["d30"]:.0f}%\n')
    print(f'{"feat":<5}{"":<28}{"n true":>7}{"win|T":>7}{"win|F":>7}{"edge":>6}{"-30|T":>7}{"-30|F":>7}{"cover":>7}')
    print('-'*81)
    res = []
    for h in HF:
        S = [r for r in rows if h in r['f']]
        if len(S) < 40: continue
        T = [r for r in S if r['f'][h]]; Fl = [r for r in S if not r['f'][h]]
        if len(T) < 15 or len(Fl) < 15: continue
        a_, c_ = st(T), st(Fl)
        e = a_['win'] - c_['win']
        res.append((h, e, a_, c_, len(S)/len(rows)*100))
        print(f'{h:<5}{NAMES[h]:<28}{a_["n"]:>7}{a_["win"]:>6.0f}%{c_["win"]:>6.0f}%{e:>+6.0f}'
              f'{a_["d30"]:>6.0f}%{c_["d30"]:>6.0f}%{len(S)/len(rows)*100:>6.0f}%')
    best = sorted(res, key=lambda x: -abs(x[1]))[:3]
    print(f'\nLargest absolute edges: ' + ', '.join(f'{h} {e:+.0f}' for h,e,_,_,_ in best))
    print('\nPER-CHART for those three (edge = win|true minus win|false):')
    print(f'  {"chart":<9}' + ''.join(f'{h:>12}' for h,_,_,_,_ in best))
    for ch in CHARTS:
        line = f'  {ch:<9}'
        for h,_,_,_,_ in best:
            S = [r for r in rows if r['ch']==ch and h in r['f']]
            T=[r for r in S if r['f'][h]]; Fl=[r for r in S if not r['f'][h]]
            line += f'{(f"{st(T)[chr(119)+chr(105)+chr(110)]-st(Fl)[chr(119)+chr(105)+chr(110)]:+.0f}" if len(T)>=8 and len(Fl)>=8 else "-"):>12}'
        print(line)


if __name__ == '__main__':
    main()
