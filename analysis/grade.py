"""Conviction grade for every CTZB signal. DECLARED 27 Oct 2026 23:25 ET,
before running. Jared: lenses grade conviction and size; they do not exclude
trades. Ordinary signals are still taken, smaller; the grade says how much the
history supports each one. Odds, not certainty.

UNIVERSE. analysis/grokpack.py rows: regime-on, confirmation entry dated
bucket_end, 60-day window on daily candles. ETH and BTC, 1D 2D 3D 5D.

CANDIDATE LENSES (all previously tested here; nothing new is introduced):
  GAP   CT more than 5 above its Signal line at entry       (PRETRADE Tier 1 #1)
  HIGH  entry above the previous signal's entry, same chart  (Tier 1 #4)
  AGREE 2+ other same-asset charts confirmed 0-10 days before (Tier 1 #5)
  UP8   the asset's 8D CT rising on its last closed bar      (Promising)
  BTC3  ETH 1D/2D only: a BTC 3D signal confirmed 0-10 days before (Promising)
  FUND  funding at or above its 90-day median at entry (the "not cooling" side
        of the positioning caution); data from 2020 only

STEP 1  KEEP / DROP, per asset. A lens is kept for an asset if, against its
        absence, it cuts touched -30% by >= 2 points OR lifts +20% by >= 5,
        with the other measure no more than 3 points worse, in BOTH periods
        (2016-21, 2022-26; FUND: 2020-21 and 2022-26), each group n >= 15.
STEP 2  OVERLAP. For every pair of kept lenses: co-occurrence vs chance, and
        each lens's effect inside both halves of the other. A lens whose
        -30% cut AND +20% lift both fall below 1 point inside either half of
        another lens is that lens counted twice: drop the one with the smaller
        pooled effect.
STEP 3  GRADE = number of surviving lenses present, equal weights (no fitted
        weights). Grades, fixed now: C = 0 or 1, B = 2, A = 3, A+ = 4 or more.
        Built twice: without FUND (full history) and with FUND (2020 on).
STEP 4  REPORT per grade and asset: signals per regime-on year, +20% in 60
        days with its worst plausible rate (95% Wilson lower bound), touched
        -30%, touched -20%, median worst dip; by period; by year.
        (Added 27 Oct 23:25 at Jared's request, reporting only: median dip
        before the high, and the dip that 1 in 4 / 1 in 10 signals exceeded;
        then the highest high within 60 days of entry: median, the top
        quarter's threshold, and the largest.)
        The grade WORKS if, per asset, touched -30% falls and +20% rises from C
        to A/A+ in both periods, and the A/A+ vs C ordering holds in most years
        with n >= 5 in both.
STEP 5  LOSING CLUSTERS. Of signals that missed +20% and of signals that
        touched -30%, the share in each grade, against the share of all signals.
ENTRY QUALITY ONLY. Signals are computed, never fills. A grade is a
historical rate for that kind of setup, not a forecast.
  python3 -I analysis/grade.py -> analysis/RESULTS_grade.txt, grade.json
"""
import sys, os, json, math, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import grokpack as GP
import pcrtest as PT

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)
LENS = {
    'GAP':   lambda r: r['gap'] is not None and r['gap'] > 5,
    'HIGH':  lambda r: r['higher'],
    'AGREE': lambda r: r['agree'] >= 2,
    'UP8':   lambda r: r['up8'],
    'BTC3':  lambda r: r['btc3'],
    'FUND':  lambda r: r['fund'] is True,
}


def wilson_lo(k, n, z=1.96):
    if n == 0: return 0.0
    p = k / n; d = 1 + z * z / n
    return 100 * (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def S(G):
    if not G: return None
    n = len(G); k = sum(r['win'] for r in G)
    dds = sorted(r['m']['dd'] for r in G)
    return dict(n=n, win=100 * k / n, lo=wilson_lo(k, n), l30=100 * sum(r['t30'] for r in G) / n,
                l20=100 * sum(r['t20'] for r in G) / n, dd=st.median(dds),
                ddpk=st.median(r['m']['ddpk'] for r in G),
                dd75=dds[int(0.25 * (n - 1))], dd90=dds[int(0.10 * (n - 1))],
                up=st.median(r['m']['up'] for r in G),
                up75=sorted(r['m']['up'] for r in G)[int(0.75 * (n - 1))],
                upmax=max(r['m']['up'] for r in G))


def fs(s):
    return 'n=   0' if not s else (f'n={s["n"]:>4} +20% {s["win"]:3.0f}% (worst plausible {s["lo"]:3.0f}%) '
                                  f'-30% {s["l30"]:3.0f}% -20% {s["l20"]:3.0f}% dip {s["dd"]:+6.1f}% '
                                  f'dip-before-high {s["ddpk"]:+5.1f}% dip 1-in-4 {s["dd75"]:+6.1f}% 1-in-10 {s["dd90"]:+6.1f}% '
                                  f'| max upside median {s["up"]:+6.1f}% top quarter {s["up75"]:+6.1f}% largest {s["upmax"]:+6.1f}%')


def eff(G, k):
    W = [r for r in G if LENS[k](r)]; O = [r for r in G if not LENS[k](r)]
    a, b = S(W), S(O)
    if not a or not b: return None
    return dict(cut=b['l30'] - a['l30'], lift=a['win'] - b['win'], nw=a['n'], no=b['n'])


def main():
    rows, allsig = GP.build()
    rows = [r for r in rows if r['tf'] in ('1D', '2D', '3D', '5D')]
    b3 = [x['d0'] for x in allsig[('BTC', '3D')]]
    fb = PT.funding_below()
    for r in rows:
        r['btc3'] = r['a'] == 'ETH' and r['tf'] in ('1D', '2D') and any(0 <= (r['d0'] - d).days <= 10 for d in b3)
        v = fb.get((r['a'], r['d0']))
        r['fund'] = None if v is None else (not v)
    years = lambda G: max(1, len({(r['yr']) for r in G}))
    OUT = {}
    P('CONVICTION GRADE -- declared 27 Oct 2026, run', dt.date.today(), '| entry quality only, computed signals, not fills\n')
    keep = {}
    P('STEP 1  lens effect vs its absence: -30% cut / +20% lift, by period')
    for a in ('ETH', 'BTC'):
        A = [r for r in rows if r['a'] == a]; keep[a] = []
        for k in LENS:
            if k == 'BTC3' and a == 'BTC': continue
            U = [r for r in A if (r['fund'] is not None)] if k == 'FUND' else A
            if k == 'BTC3': U = [r for r in A if r['tf'] in ('1D', '2D')]
            per = []
            for sel in (lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT):
                per.append(eff([r for r in U if sel(r)], k))
            ok = all(e and e['nw'] >= 15 and e['no'] >= 15 and
                     ((e['cut'] >= 2 and e['lift'] >= -3) or (e['lift'] >= 5 and e['cut'] >= -3)) for e in per)
            if ok: keep[a].append(k)
            P(f'  {a} {k:5} ' + ' | '.join(f'{lab} cut {e["cut"]:+5.1f} lift {e["lift"]:+5.1f} (n {e["nw"]}/{e["no"]})' if e else f'{lab} -'
                                           for lab, e in zip(('to 2021', '2022 on'), per)) + f'  -> {"KEEP" if ok else "drop"}')
    P('\nSTEP 2  overlap between kept lenses')
    for a in ('ETH', 'BTC'):
        A = [r for r in rows if r['a'] == a and (r['fund'] is not None or 'FUND' not in keep[a])]
        ks = keep[a]; dropped = set()
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                x, y = ks[i], ks[j]
                if x in dropped or y in dropped: continue
                U = [r for r in A if (x != 'FUND' and y != 'FUND') or r['fund'] is not None]
                px = sum(LENS[x](r) for r in U) / len(U); py = sum(LENS[y](r) for r in U) / len(U)
                both = sum(LENS[x](r) and LENS[y](r) for r in U) / len(U)
                inside = {}
                for k1, k2 in ((x, y), (y, x)):
                    halves = [eff([r for r in U if LENS[k2](r) == h], k1) for h in (True, False)]
                    inside[k1] = halves
                twice = [k1 for k1, hv in inside.items() if any(e is None or (e['cut'] < 1 and e['lift'] < 1) for e in hv)]
                msg = ''
                if twice:
                    tot = {k1: eff(U, k1) for k1 in (x, y)}
                    score = lambda k1: (tot[k1]['cut'] if tot[k1] else 0) + (tot[k1]['lift'] if tot[k1] else 0)
                    d = min(twice, key=score) if len(twice) == 2 else twice[0]
                    dropped.add(d); msg = f'  -> {d} adds nothing inside {y if d == x else x}: DROP {d}'
                P(f'  {a} {x}+{y}: together {100 * both:3.0f}% of signals vs {100 * px * py:3.0f}% by chance; '
                  + ' | '.join(f'{k1} inside {(y if k1 == x else x)} yes/no: ' + ', '.join(
                      f'cut {e["cut"]:+.0f} lift {e["lift"]:+.0f}' if e else '-' for e in hv) for k1, hv in inside.items()) + msg)
        keep[a] = [k for k in ks if k not in dropped]
        P(f'  {a} lenses in the grade: {", ".join(keep[a]) or "none"}')
    OUT['lenses'] = keep

    def grade(r, a, with_fund):
        ks = [k for k in keep[a] if with_fund or k != 'FUND']
        c = sum(LENS[k](r) for k in ks)
        return 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'

    for with_fund in (False, True):
        P(f'\nSTEP 3-4  GRADES {"WITH" if with_fund else "WITHOUT"} FUND' + (' (2020 on)' if with_fund else ' (full history)'))
        res = {}
        for a in ('ETH', 'BTC'):
            A = [r for r in rows if r['a'] == a and (not with_fund or r['fund'] is not None)]
            if with_fund and 'FUND' not in keep[a]:
                P(f'  {a}: FUND not kept, same as without'); continue
            for r in A: r['g'] = grade(r, a, with_fund)
            ny = years(A)
            P(f'  {a} ({len(A)} signals, {ny} regime-on years; lenses {", ".join(k for k in keep[a] if with_fund or k != "FUND")})')
            for g in ('C', 'B', 'A', 'A+'):
                G = [r for r in A if r['g'] == g]
                P(f'    {g:2} {len(G) / ny:5.1f}/yr  {fs(S(G))}')
                for pl, sel in (('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
                    P(f'         {pl}: {fs(S([r for r in G if sel(r)]))}')
            top = [r for r in A if r['g'] in ('A', 'A+')]; bot = [r for r in A if r['g'] == 'C']
            good_p = []
            for sel in (lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT):
                t, c = S([r for r in top if sel(r)]), S([r for r in bot if sel(r)])
                good_p.append(bool(t and c and t['l30'] < c['l30'] and t['win'] > c['win']))
            yrs = sorted({r['yr'] for r in A}); yok = yn = 0; yl = []
            for y in yrs:
                t, c = S([r for r in top if r['yr'] == y]), S([r for r in bot if r['yr'] == y])
                if t and c and t['n'] >= 5 and c['n'] >= 5:
                    yn += 1; ok = t['win'] >= c['win'] and t['l30'] <= c['l30']; yok += ok
                    yl.append(f'{y} A/A+ {t["win"]:.0f}%/{t["l30"]:.0f}% vs C {c["win"]:.0f}%/{c["l30"]:.0f}%')
            works = all(good_p) and yn > 0 and yok > yn / 2
            P(f'    by year (+20% / -30%): ' + '; '.join(yl))
            P(f'    -> both periods ordered: {good_p}, years ordered {yok}/{yn}: {"GRADE WORKS" if works else "GRADE DOES NOT HOLD"}')
            P(f'  STEP 5  {a} where the failures sit (share of each group in each grade)')
            groups = (('all signals', A), ('missed +20%', [r for r in A if not r['win']]), ('touched -30%', [r for r in A if r['t30']]))
            for lab, G in groups:
                P(f'    {lab:13} ' + '  '.join(f'{g} {100 * sum(r["g"] == g for r in G) / len(G):3.0f}%' for g in ('C', 'B', 'A', 'A+')) + f'  (n {len(G)})')
            res[a] = dict(works=works)
        OUT['with_fund' if with_fund else 'no_fund'] = res
    P('\n  ENTRY QUALITY ONLY. Computed signals, not fills. Grades are historical rates, not forecasts.')
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, 'RESULTS_grade.txt'), 'w').write('\n'.join(L) + '\n')
    json.dump(OUT, open(os.path.join(here, 'grade.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
