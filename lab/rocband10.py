"""ROC+ lower band -- ADDENDUM on the card's measure.
DECLARED 25 Nov 2026, before running, after lab/rocband.py (which judged on +20%,
the grade's measure). Jared: the measure that matters is the card's -- rose 10%
and never fell 25.3% within 60 days -- and, for the ones that failed, whether
there was upside from entry first.

SAME read, population, candidates (B60, B30, OWN60 x ETH, BTC) and four rules as
lab/rocband.py, with:
  win  = surv10: rose 10% AND never fell 25.3% (measures.LIQ) within 60 days
  risk = fell 25.3% within 60 days (replaces touched -30% in rule 1)
Also reported, not rules:
  rose 10% (the card's big number);
  MISSES (did not rise 10%): share whose best price went above entry, median
  best move -- the card's "If it misses" definition;
  FELL 25.3%: the best move from entry before the first daily low at -25.3%,
  from 1D candles.

ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I lab/rocband10.py -> lab/RESULTS_rocband10.txt
"""
import sys, os, csv, random, bisect, statistics as S, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'analysis')); sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E
from measures import LIQ
import rocband as RB

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)

random.seed(20261125)
SPLIT, LAST, LIVE = RB.SPLIT, RB.LAST, RB.LIVE
CANDS = ('B60', 'B30', 'OWN60')


def rate(g, k): return 100 * sum(x[k] for x in g) / len(g) if g else None
def med(g, k):
    v = [x[k] for x in g if x[k] is not None]
    return S.median(v) if v else None


def up_before_fall(day, pos, d0, c0):
    i = pos[d0]; end = d0 + dt.timedelta(days=60); best = 0.0
    for k in range(i + 1, len(day['date'])):
        if day['date'][k] > end: break
        if 100 * (day['low'][k] / c0 - 1) <= LIQ:
            return best  # the fall bar's own high is not counted: order inside the day is unknown
        best = max(best, 100 * (day['high'][k] / c0 - 1))
    return None


def main():
    P('ROC+ LOWER BAND, ADDENDUM ON THE CARD MEASURE -- declared 25 Nov 2026 (lab/rocband10.py)')
    BR = {a: RB.breaks(f'data/{a}_5D.csv')[0] for a in ('ETH', 'BTC')}
    OWN = {f'{a} {tf}': RB.breaks(f'data/{a}_{tf}.csv')[0] for a in ('ETH', 'BTC') for tf in ('1D', '2D', '3D', '5D')}
    day = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
    pos = {a: {d: i for i, d in enumerate(day[a]['date'])} for a in day}

    def within(ends, d0, days):
        j = bisect.bisect_right(ends, d0)
        return j > 0 and (d0 - ends[j - 1]).days <= days

    rows = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > LAST or not x['reached20']: continue
        a = x['asset']; dd = float(x['maxDrawdown']); up = float(x['bestMove'])
        fell = dd <= LIQ
        rows.append(dict(a=a, ch=x['chart'], d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1,
                         win=x['surv10'] == 'yes', r10=x['reached10'] == 'yes', t=fell, up=up, dd=dd,
                         ubf=up_before_fall(day[a], pos[a], d0, float(x['entryPrice'])) if fell else None,
                         bkA=x['tags'][:1] == 'A', lens=set(t.strip() for t in x['lenses'].split('+')),
                         f=dict(B60=within(BR[a], d0, 60), B30=within(BR[a], d0, 30), OWN60=within(OWN[x['chart']], d0, 60))))

    P('')
    P('SUMMARY  cand asset | n on/off | rose 10% & never fell 25.3% on/off | rose 10% on/off | fell 25.3% on/off')
    for a in ('ETH', 'BTC'):
        for c in CANDS:
            g = [r for r in rows if r['a'] == a]; on = [r for r in g if r['f'][c]]; off = [r for r in g if not r['f'][c]]
            P(f'{c:<5} {a} | {len(on)}/{len(off)} | {rate(on,"win"):.0f}/{rate(off,"win"):.0f} | {rate(on,"r10"):.0f}/{rate(off,"r10"):.0f} | '
              f'{rate(on,"t"):.0f}/{rate(off,"t"):.0f}')

    P('')
    P('RULES  cand asset | to 2021: n on/off win on/off fell25 on/off | 2022 on: same | charts years | shuffle real/p95 | overlap | verdict')
    for a in ('ETH', 'BTC'):
        for c in CANDS:
            g = [r for r in rows if r['a'] == a]; st_ = []; ok = True
            for p in (0, 1):
                on = [r for r in g if r['per'] == p and r['f'][c]]; off = [r for r in g if r['per'] == p and not r['f'][c]]
                st_.append((len(on), len(off), rate(on, 'win'), rate(off, 'win'), rate(on, 't'), rate(off, 't')))
                if len(on) < 15 or len(off) < 15: ok = False
                elif not (rate(on, 'win') - rate(off, 'win') >= 5 and rate(on, 't') - rate(off, 't') <= 3): ok = False

            def split(key, nmin):
                grp = {}
                for r in g: grp.setdefault(r[key], []).append(r)
                k_ = t_ = 0
                for gg in grp.values():
                    on = [r for r in gg if r['f'][c]]; off = [r for r in gg if not r['f'][c]]
                    if len(on) < nmin or len(off) < nmin: continue
                    t_ += 1; k_ += rate(on, 'win') > rate(off, 'win')
                return k_, t_
            ch = split('ch', 5); yr = split('yr', 3)
            if ch[1] == 0 or ch[0] / ch[1] < 2 / 3 or yr[1] == 0 or yr[0] / yr[1] < 2 / 3: ok = False

            def lift(pp):
                on = [r for r, v in pp if v]; off = [r for r, v in pp if not v]
                return rate(on, 'win') - rate(off, 'win') if on and off else 0
            real = lift([(r, r['f'][c]) for r in g]); byy = {}
            for r in g: byy.setdefault(r['yr'], []).append(r)
            sims = []
            for _ in range(200):
                pp = []
                for gg in byy.values():
                    fl = [r['f'][c] for r in gg]; random.shuffle(fl); pp += list(zip(gg, fl))
                sims.append(lift(pp))
            sims.sort(); p95 = sims[190]
            if real <= p95: ok = False
            ov = '-'
            for ln in LIVE[a] + ['BUCKET_A']:
                for half in (True, False):
                    gg = [r for r in g if (r['bkA'] if ln == 'BUCKET_A' else ln in r['lens']) == half]
                    on = [r for r in gg if r['f'][c]]; off = [r for r in gg if not r['f'][c]]
                    if len(on) < 5 or len(off) < 5: continue
                    if rate(on, 'win') - rate(off, 'win') < 1 and rate(off, 't') - rate(on, 't') < 1:
                        ov = f'{ln}={"on" if half else "off"}'; break
                if ov != '-': break
            if ov != '-': ok = False
            s0, s1 = st_
            f_ = lambda v: '  -' if v is None else f'{v:3.0f}'
            P(f'{c:<5} {a} | {s0[0]:3d}/{s0[1]:<3d} {f_(s0[2])}/{f_(s0[3])} {f_(s0[4])}/{f_(s0[5])} | '
              f'{s1[0]:3d}/{s1[1]:<3d} {f_(s1[2])}/{f_(s1[3])} {f_(s1[4])}/{f_(s1[5])} | {ch[0]}/{ch[1]} {yr[0]}/{yr[1]} | '
              f'{real:+.1f}/{p95:+.1f} | {ov} | {"PASS" if ok else "fail"}')

    for c in ('B60',):
        P('')
        P(f'BY CHART ({c})  chart | n on/off | win on/off | fell25 on/off')
        for chn in sorted({r['ch'] for r in rows}):
            g = [r for r in rows if r['ch'] == chn]; on = [r for r in g if r['f'][c]]; off = [r for r in g if not r['f'][c]]
            P(f'{chn} | {len(on)}/{len(off)} | ' + (f'{rate(on,"win"):.0f}/{rate(off,"win"):.0f} | {rate(on,"t"):.0f}/{rate(off,"t"):.0f}' if on and off else '-'))
        P('')
        P(f'BY EPISODE ({c})  asset episode | n | win | rose 10% | fell25')
        for a in ('ETH', 'BTC'):
            eps = []
            for e in BR[a]:
                if eps and (e - eps[-1][-1]).days <= 60: eps[-1].append(e)
                else: eps.append([e])
            for ep in eps:
                g = []
                for r in rows:
                    if r['a'] != a or not r['f'][c]: continue
                    j = bisect.bisect_right(BR[a], r['d0'])
                    if ep[0] <= BR[a][j - 1] <= ep[-1]: g.append(r)
                if g: P(f'{a} {ep[0]}..{ep[-1]} | {len(g)} | {rate(g,"win"):.0f}% | {rate(g,"r10"):.0f}% | {rate(g,"t"):.0f}%')

    P('')
    P('FAILURES, B60 on/off  asset | MISSES (no +10%): n, went above entry, median best move | FELL 25.3%: n, median best move before the fall, share up 5%+ first')
    for a in ('ETH', 'BTC'):
        for side, nm in ((True, 'on'), (False, 'off')):
            g = [r for r in rows if r['a'] == a and r['f']['B60'] == side]
            ms = [r for r in g if not r['r10']]; fl = [r for r in g if r['t']]
            above = 100 * sum(r['up'] > 0 for r in ms) / len(ms) if ms else None
            u5 = 100 * sum((r['ubf'] or 0) >= 5 for r in fl) / len(fl) if fl else None
            P(f'{a} {nm} | {len(ms)}, ' + (f'{above:.0f}%, {med(ms,"up"):+.1f}%' if ms else '-') +
              f' | {len(fl)}, ' + (f'{med(fl,"ubf"):+.1f}%, {u5:.0f}%' if fl else '-'))
    P('')
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_rocband10.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
