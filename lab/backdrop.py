"""The market BACKDROP: do signals fired while several 5D washout reads are on do better?
DECLARED 25 Nov 2026, before running. Statistics lab (stats-lab branch). Jared approved
step 1 of the plan: test the backdrop before anything is shown anywhere.

POPULATION
  datasets/ledger.csv: every regime-gated, graded signal, ETH and BTC, 1D 2D 3D 5D,
  completed 60-day window. ETH is the question; BTC is run the same way for the
  record. ETH and BTC are ONE sample (every read here is date-anchored).

MEASURES (the card's)
  win  = surv10: rose 10% AND never fell 25.3% within 60 days
  risk = fell 25.3% within 60 days
  also reported: rose 10%, rose 20%

THE BACKDROP READS (the asset's own 5D chart, closed bars only, known at entry)
  BAND   ROC+ (Percent, 9, 10th percentile of 250 bars) closed below its lower band
         within the 60 days before entry                         [lab/rocband.py B60]
  TURN   a 5D CTZB signal (ungated) with trough CT < 40 confirmed in the 30 days
         before entry                                  [analysis/lens5d.py T30, watch item]
  HLB    higher low than the last band visit (Jared, 25 Nov). Band visits = 5D bars
         closed below the band, grouped into one visit when under 60 days apart.
         The current visit's low = the lowest 5D low from its first break bar to the
         last 5D bar closed by entry. The previous visit's low = the lowest 5D low
         from its first to its last break bar. HLB = current low > previous low.
         Only defined when BAND is on (no visit, no comparison).
  COUNT  = BAND + TURN + HLB, 0 to 3.

TESTS, declared
  T1  the gradient: signals with COUNT 0 / 1 / 2+ . Reported, both periods.
  T2  COUNT >= 2 vs COUNT <= 1 as a lens, judged by the four rules of
      lab/rocband.py on surv10 (rule 1: lift >= +5 in BOTH periods, fell 25.3% not
      more than 3 worse, n >= 15 per side per period; rule 2: ahead on >= 2/3 of
      charts n>=5 and >= 2/3 of years n>=3; rule 3: beats the 95th pct of 200
      within-year shuffles; rule 4: no collapse inside either half of any live lens
      or bucket A).
  T3  HLB inside BAND: among signals with BAND on, HLB on vs off. Passes if surv10
      lift >= +5, fell 25.3% not more than 3 worse, n >= 15 per side, ahead on
      >= 2/3 of charts (n >= 5 per side). Too few periods/episodes for a year split:
      the episodes are listed instead.
  A pass on ETH goes to PRETRADE "Watch items" at most, never the grade or the card,
  until it holds on signals after today. A fail is logged.

ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I lab/backdrop.py -> lab/RESULTS_backdrop.txt
"""
import sys, os, csv, random, bisect, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'analysis')); sys.path.insert(0, ROOT); os.chdir(ROOT)
from measures import LIQ
from tagstats import bucket_end
from lens5d import five
import rocband as RB

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)

random.seed(20261125)
SPLIT, LAST, LIVE = RB.SPLIT, RB.LAST, RB.LIVE


def rate(g, k): return 100 * sum(x[k] for x in g) / len(g) if g else None
def f_(v): return '  -' if v is None else f'{v:3.0f}'


def backdrop_reader(a):
    ends, b, roc, low = RB.breaks(f'data/{a}_5D.csv')
    E5 = [bucket_end(b['date'], k) for k in range(len(b['date']))]
    brk_k = [k for k in range(len(b['date'])) if E5[k] is not None and low[k] is not None and roc[k] < low[k]]
    visits = []
    for k in brk_k:
        if visits and (E5[k] - E5[visits[-1][-1]]).days <= 60: visits[-1].append(k)
        else: visits.append([k])
    turns = five(a)[2]

    def at(d0):
        # BAND
        j = bisect.bisect_right(ends, d0)
        band = j > 0 and (d0 - ends[j - 1]).days <= 60
        # TURN
        jt = bisect.bisect_right(turns, d0)
        turn = jt > 0 and (d0 - turns[jt - 1]).days <= 30
        # HLB
        hlb = False; cur = prev = None
        if band:
            vi = max(i for i, v in enumerate(visits) if E5[v[0]] <= d0)
            v = visits[vi]
            kl = max(k for k in range(len(E5)) if E5[k] is not None and E5[k] <= d0)
            cur = min(b['low'][k] for k in range(v[0], kl + 1))
            if vi > 0:
                pv = visits[vi - 1]
                prev = min(b['low'][k] for k in range(pv[0], pv[-1] + 1))
                hlb = cur > prev
        return dict(BAND=band, TURN=turn, HLB=hlb, cur=cur, prev=prev)
    return at, visits, E5, b


def rules(g, key, name):
    st_ = []; ok = True
    for p in (0, 1):
        on = [r for r in g if r['per'] == p and r[key]]; off = [r for r in g if r['per'] == p and not r[key]]
        st_.append((len(on), len(off), rate(on, 'win'), rate(off, 'win'), rate(on, 't'), rate(off, 't')))
        if len(on) < 15 or len(off) < 15: ok = False
        elif not (rate(on, 'win') - rate(off, 'win') >= 5 and rate(on, 't') - rate(off, 't') <= 3): ok = False

    def split(k2, nmin):
        grp = {}
        for r in g: grp.setdefault(r[k2], []).append(r)
        k_ = t_ = 0
        for gg in grp.values():
            on = [r for r in gg if r[key]]; off = [r for r in gg if not r[key]]
            if len(on) < nmin or len(off) < nmin: continue
            t_ += 1; k_ += rate(on, 'win') > rate(off, 'win')
        return k_, t_
    ch = split('ch', 5); yr = split('yr', 3)
    if ch[1] == 0 or ch[0] / ch[1] < 2 / 3 or yr[1] == 0 or yr[0] / yr[1] < 2 / 3: ok = False

    def lift(pp):
        on = [r for r, v in pp if v]; off = [r for r, v in pp if not v]
        return rate(on, 'win') - rate(off, 'win') if on and off else 0
    real = lift([(r, r[key]) for r in g]); byy = {}
    for r in g: byy.setdefault(r['yr'], []).append(r)
    sims = []
    for _ in range(200):
        pp = []
        for gg in byy.values():
            fl = [r[key] for r in gg]; random.shuffle(fl); pp += list(zip(gg, fl))
        sims.append(lift(pp))
    sims.sort(); p95 = sims[190]
    if real <= p95: ok = False
    a = g[0]['a']; ov = '-'
    for ln in LIVE[a] + ['BUCKET_A']:
        for half in (True, False):
            gg = [r for r in g if (r['bkA'] if ln == 'BUCKET_A' else ln in r['lens']) == half]
            on = [r for r in gg if r[key]]; off = [r for r in gg if not r[key]]
            if len(on) < 5 or len(off) < 5: continue
            if rate(on, 'win') - rate(off, 'win') < 1 and rate(off, 't') - rate(on, 't') < 1:
                ov = f'{ln}={"on" if half else "off"}'; break
        if ov != '-': break
    if ov != '-': ok = False
    s0, s1 = st_
    P(f'{name:<10} {a} | {s0[0]:3d}/{s0[1]:<3d} {f_(s0[2])}/{f_(s0[3])} {f_(s0[4])}/{f_(s0[5])} | '
      f'{s1[0]:3d}/{s1[1]:<3d} {f_(s1[2])}/{f_(s1[3])} {f_(s1[4])}/{f_(s1[5])} | {ch[0]}/{ch[1]} {yr[0]}/{yr[1]} | '
      f'{real:+.1f}/{p95:+.1f} | {ov} | {"PASS" if ok else "fail"}')


def main():
    P('THE BACKDROP: BAND + TURN + HLB -- declared 25 Nov 2026 (lab/backdrop.py)')
    R = {a: backdrop_reader(a) for a in ('ETH', 'BTC')}
    rows = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > LAST or not x['reached20']: continue
        a = x['asset']; bd = R[a][0](d0)
        cnt = bd['BAND'] + bd['TURN'] + bd['HLB']
        rows.append(dict(a=a, ch=x['chart'], d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1,
                         win=x['surv10'] == 'yes', r10=x['reached10'] == 'yes', r20=x['reached20'] == 'yes',
                         t=float(x['maxDrawdown']) <= LIQ, bkA=x['tags'][:1] == 'A',
                         lens=set(t.strip() for t in x['lenses'].split('+')), cnt=cnt, two=cnt >= 2, **bd))

    P('')
    P('T1 GRADIENT  asset count | all: n  surv10  rose10  rose20  fell25.3 | to 2021: n surv10 fell | 2022 on: n surv10 fell')
    for a in ('ETH', 'BTC'):
        for lab, sel in (('0', lambda r: r['cnt'] == 0), ('1', lambda r: r['cnt'] == 1), ('2+', lambda r: r['cnt'] >= 2), ('3', lambda r: r['cnt'] == 3)):
            g = [r for r in rows if r['a'] == a and sel(r)]
            if not g: P(f'{a} {lab:<2} | 0'); continue
            p0 = [r for r in g if r['per'] == 0]; p1 = [r for r in g if r['per'] == 1]
            P(f'{a} {lab:<2} | {len(g):3d} {f_(rate(g,"win"))} {f_(rate(g,"r10"))} {f_(rate(g,"r20"))} {f_(rate(g,"t"))} | '
              f'{len(p0):3d} {f_(rate(p0,"win"))} {f_(rate(p0,"t"))} | {len(p1):3d} {f_(rate(p1,"win"))} {f_(rate(p1,"t"))}')

    P('')
    P('T2 RULES (COUNT >= 2 vs <= 1)  name asset | to 2021: n on/off win on/off fell on/off | 2022 on: same | charts years | shuffle | overlap | verdict')
    for a in ('ETH', 'BTC'):
        rules([r for r in rows if r['a'] == a], 'two', 'COUNT>=2')
    P('')
    P('T2 by chart (COUNT >= 2)  chart | n on/off | surv10 on/off | fell25.3 on/off')
    for chn in sorted({r['ch'] for r in rows}):
        g = [r for r in rows if r['ch'] == chn]; on = [r for r in g if r['two']]; off = [r for r in g if not r['two']]
        P(f'{chn} | {len(on)}/{len(off)} | ' + (f'{f_(rate(on,"win"))}/{f_(rate(off,"win"))} | {f_(rate(on,"t"))}/{f_(rate(off,"t"))}' if on and off else '-'))
    P('')
    P('T2 by year (COUNT >= 2)  asset year | n on/off | surv10 on/off | fell25.3 on/off')
    for a in ('ETH', 'BTC'):
        for y in sorted({r['yr'] for r in rows if r['a'] == a}):
            g = [r for r in rows if r['a'] == a and r['yr'] == y]; on = [r for r in g if r['two']]; off = [r for r in g if not r['two']]
            if on: P(f'{a} {y} | {len(on)}/{len(off)} | {f_(rate(on,"win"))}/{f_(rate(off,"win"))} | {f_(rate(on,"t"))}/{f_(rate(off,"t"))}')

    P('')
    P('T3 HLB INSIDE BAND  asset | n HLB on/off | surv10 on/off | fell25.3 on/off | charts ahead | verdict')
    for a in ('ETH', 'BTC'):
        g = [r for r in rows if r['a'] == a and r['BAND']]
        on = [r for r in g if r['HLB']]; off = [r for r in g if not r['HLB']]
        ok = len(on) >= 15 and len(off) >= 15 and on and off and rate(on, 'win') - rate(off, 'win') >= 5 and rate(on, 't') - rate(off, 't') <= 3
        k_ = t_ = 0
        for chn in {r['ch'] for r in g}:
            o = [r for r in on if r['ch'] == chn]; f = [r for r in off if r['ch'] == chn]
            if len(o) >= 5 and len(f) >= 5: t_ += 1; k_ += rate(o, 'win') > rate(f, 'win')
        if t_ == 0 or k_ / t_ < 2 / 3: ok = False
        P(f'{a} | {len(on)}/{len(off)} | {f_(rate(on,"win"))}/{f_(rate(off,"win"))} | {f_(rate(on,"t"))}/{f_(rate(off,"t"))} | {k_}/{t_} | {"PASS" if ok else "fail"}')

    P('')
    P('BAND VISITS and HLB  asset visit | visit low | previous visit low | higher low | signals in its windows: n, surv10, fell25.3')
    for a in ('ETH', 'BTC'):
        at, visits, E5, b = R[a]
        for i, v in enumerate(visits):
            lo = min(b['low'][k] for k in range(v[0], v[-1] + 1))
            plo = min(b['low'][k] for k in range(visits[i - 1][0], visits[i - 1][-1] + 1)) if i else None
            g = [r for r in rows if r['a'] == a and r['BAND'] and E5[v[0]] <= r['d0'] <= E5[v[-1]] + dt.timedelta(days=60)]
            P(f'{a} {E5[v[0]]}..{E5[v[-1]]} | {lo:,.2f} | ' + ('-' if plo is None else f'{plo:,.2f}') +
              f' | {"-" if plo is None else ("yes" if lo > plo else "no")} | ' +
              (f'{len(g)}, {rate(g,"win"):.0f}%, {rate(g,"t"):.0f}%' if g else '0'))

    P('')
    P('NOW (last closed 5D bar, not a result)')
    for a in ('ETH', 'BTC'):
        at, visits, E5, b = R[a]
        kl = max(k for k in range(len(E5)) if E5[k] is not None)
        bd = at(E5[kl])
        P(f'{a} as of {E5[kl]}: BAND {bd["BAND"]}, TURN {bd["TURN"]}, HLB {bd["HLB"]} (visit low {bd["cur"]}, previous visit low {bd["prev"]})')
    P('')
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_backdrop.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
