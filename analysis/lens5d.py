"""The 5D CT RSI zone as a lens on faster-chart signals.
DECLARED 11 Nov 2026, before running. Jared, after ct_swinglows / ct_reentry:
"Is this something that we could compute into the current entry strategy?"

POPULATION
  datasets/ledger.csv: regime-gated signals on 1D 2D 3D (the 5D chart's own
  signals excluded: a 5D lens on 5D signals is circular). Full 60-day windows
  (entry on or before 2026-09-10). ETH is the question; BTC (with BTC 5D) is
  run the same way, and ETH and BTC count as one sample (date-anchored).
  win = +20% within 60 days; t30 = touched -30% within 60 days.

CANDIDATES (the asset's own 5D chart, last bar CLOSED by the entry day)
  Z40    5D CT < 40
  Z35    5D CT < 35
  Z40UP  5D CT < 40 and higher than on the bar before (turning)
  T30    a 5D CTZB signal (ungated) with trough CT < 40 confirmed in the 30
         days before entry
  4 candidates x 2 assets = 8.

RULES (PRETRADE)
  1  win lift >= +5 in BOTH periods (to 2021 / 2022 on), t30 not more than 3
     worse, n >= 15 per side per period.
  2  ahead on >= 2/3 of charts (n >= 5 per side) and >= 2/3 of years
     (n >= 3 per side).
  3  shuffled within year 200 times: real lift beats the 95th percentile.
  4  inside each half of every live lens (ETH: GAP HIGH AGREE BTC3 FUND FCOOL;
     BTC: GAP UP8 BTCX FASTCT) and of the signal's own bucket A, lift and t30
     cut both under 1 in either half -> counted twice, dropped.
  A survivor goes to PRETRADE "Promising", not into the grade, until it holds
  on signals after today.

ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I analysis/lens5d.py -> analysis/RESULTS_lens5d.txt
"""
import sys, os, csv, random, bisect, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E
from tagstats import bucket_end
from sweep import closed_index

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)

SPLIT = dt.date(2022, 1, 1); LAST = dt.date(2026, 9, 10)
LIVE = {'ETH': ['GAP', 'HIGH', 'AGREE', 'BTC3', 'FUND', 'FCOOL'], 'BTC': ['GAP', 'UP8', 'BTCX', 'FASTCT']}
random.seed(20261111)


def five(a):
    b = E.load(f'data/{a}_5D.csv'); ct = E.rsi(b['close'], 14)
    sig, bb = E.signals(f'data/{a}_5D.csv', regime=lambda d: True)
    turns = sorted(bucket_end(bb['date'], s['ei']) for s in sig if ct[s['ti']] is not None and ct[s['ti']] < 40
                   and bucket_end(bb['date'], s['ei']) is not None)
    return b['date'], ct, turns


def flags(a, d0, F):
    ds, ct, turns = F[a]; k = closed_index(ds, d0)
    if k < 1 or k >= len(ct) or ct[k] is None or ct[k - 1] is None: return None
    j = bisect.bisect_right(turns, d0)
    t30 = j > 0 and (d0 - turns[j - 1]).days <= 30
    return dict(Z40=ct[k] < 40, Z35=ct[k] < 35, Z40UP=ct[k] < 40 and ct[k] > ct[k - 1], T30=t30)


def rate(g, k): return 100 * sum(x[k] for x in g) / len(g) if g else None


def main():
    F = {a: five(a) for a in ('ETH', 'BTC')}
    rows = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        if x['chart'].endswith('5D'): continue
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > LAST: continue
        f = flags(x['asset'], d0, F)
        if f is None: continue
        rows.append(dict(a=x['asset'], ch=x['chart'], d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1,
                         win=x['reached20'] == 'yes', t30=x['touched30'] == 'yes', f=f, bkA=x['tags'][:1] == 'A',
                         lens=set(t.strip() for t in x['lenses'].split('+'))))
    P('5D CT ZONE AS A LENS on 1D/2D/3D signals -- declared 11 Nov 2026 (analysis/lens5d.py)')
    P('cand  asset | to 2021: n on/off  win on/off  t30 on/off | 2022 on: n on/off  win on/off  t30 on/off | charts years | shuffle | overlap | verdict')
    for a in ('ETH', 'BTC'):
        for c in ('Z40', 'Z35', 'Z40UP', 'T30'):
            g = [r for r in rows if r['a'] == a]
            st_ = []; ok = True
            for p in (0, 1):
                on = [r for r in g if r['per'] == p and r['f'][c]]; off = [r for r in g if r['per'] == p and not r['f'][c]]
                st_.append((len(on), len(off), rate(on, 'win'), rate(off, 'win'), rate(on, 't30'), rate(off, 't30')))
                if len(on) < 15 or len(off) < 15: ok = False
                elif not (rate(on, 'win') - rate(off, 'win') >= 5 and rate(on, 't30') - rate(off, 't30') <= 3): ok = False
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
            if ok and (ch[1] == 0 or ch[0] / ch[1] < 2 / 3 or yr[1] == 0 or yr[0] / yr[1] < 2 / 3): ok = False
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
            if ok and real <= p95: ok = False
            ov = '-'
            for ln in LIVE[a] + ['BUCKET_A']:
                for half in (True, False):
                    gg = [r for r in g if (r['bkA'] if ln == 'BUCKET_A' else ln in r['lens']) == half]
                    on = [r for r in gg if r['f'][c]]; off = [r for r in gg if not r['f'][c]]
                    if len(on) < 5 or len(off) < 5: continue
                    if rate(on, 'win') - rate(off, 'win') < 1 and rate(off, 't30') - rate(on, 't30') < 1:
                        ov = f'{ln}={"on" if half else "off"}'; break
                if ov != '-': break
            if ok and ov != '-': ok = False
            s0, s1 = st_
            f_ = lambda v: '  -' if v is None else f'{v:3.0f}'
            P(f'{c:<5} {a} | {s0[0]:3d}/{s0[1]:<3d} {f_(s0[2])}/{f_(s0[3])} {f_(s0[4])}/{f_(s0[5])} | '
              f'{s1[0]:3d}/{s1[1]:<3d} {f_(s1[2])}/{f_(s1[3])} {f_(s1[4])}/{f_(s1[5])} | {ch[0]}/{ch[1]} {yr[0]}/{yr[1]} | '
              f'{real:+.1f}/{p95:+.1f} | {ov} | {"PASS" if ok else "fail"}')
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_lens5d.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
