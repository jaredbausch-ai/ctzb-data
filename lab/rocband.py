"""ROC+ lower band as a lens on CTZB signals.
DECLARED 25 Nov 2026, before running. Statistics lab (stats-lab branch).

JARED'S CLAIM
  "Every time we're breaking this lower band [ROC+ on ETH 5D], any signals firing
  in that area over the next 60-day period ... would increase the win probability."

THE READ (pine: lab/pine/roc_plus.pine, default settings, as in his 25 Nov export)
  ROC = 100 * (close - close[9]) / close[9], no smoothing.
  Lower band = ta.percentile_nearest_rank(ROC, 250, 10).
  "Broke the lower band" = a CLOSED bar with ROC < lower band. Known at that
  bar's close, so it only counts for signals whose entry is on or after it.
  Validated against his export (COINBASE_ETHUSD_5D) before use.

POPULATION
  datasets/ledger.csv: every regime-gated, graded signal, ETH and BTC, 1D 2D 3D
  5D, with a completed 60-day window. ETH is the question; BTC is run the same
  way, and ETH and BTC count as ONE sample (date-anchored).
  win = +20% within 60 days (the rule's measure); +10% and touched -30% reported.

CANDIDATES (3 x 2 assets = 6)
  B60   the asset's 5D ROC closed below its lower band within the 60 days before
        entry (Jared's read)
  B30   same, 30 days
  OWN60 the signal's OWN chart's ROC closed below its own lower band within the
        60 days before entry

RULES (same four as analysis/lens5d.py, PRETRADE)
  1  win lift >= +5 in BOTH periods (to 2021 / 2022 on), t30 not more than 3
     worse, n >= 15 per side per period.
  2  ahead on >= 2/3 of charts (n >= 5 per side) and >= 2/3 of years (n >= 3).
  3  shuffled within year 200 times: real lift beats the 95th percentile.
  4  inside each half of every live lens (ETH: GAP HIGH AGREE BTC3 FUND FCOOL;
     BTC: GAP UP8 BTCX FASTCT) and of bucket A, lift and t30 cut both under 1
     in either half -> counted twice, fails.
  Also reported, not a rule: co-occurrence with the 5D-turn-under-40 watch item
  (analysis/lens5d.py T30).

ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I lab/rocband.py -> lab/RESULTS_rocband.txt
"""
import sys, os, csv, math, random, bisect, statistics as S, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'analysis')); sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E
from tagstats import bucket_end
from lens5d import five

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)

LEN, PLEN, PCT, WIN = 9, 250, 10, 60
SPLIT = dt.date(2022, 1, 1)
LAST = dt.date(2026, 11, 25) - dt.timedelta(days=61)
LIVE = {'ETH': ['GAP', 'HIGH', 'AGREE', 'BTC3', 'FUND', 'FCOOL'], 'BTC': ['GAP', 'UP8', 'BTCX', 'FASTCT']}
random.seed(20261125)


def roc_band(close):
    n = len(close); roc = [None] * n; low = [None] * n
    for i in range(LEN, n):
        roc[i] = 100 * (close[i] - close[i - LEN]) / close[i - LEN]
    for i in range(n):
        w = [v for v in roc[max(0, i - PLEN + 1):i + 1] if v is not None]
        if not w or roc[i] is None: continue
        w.sort(); k = max(1, math.ceil(PCT / 100 * len(w)))
        low[i] = w[k - 1]
    return roc, low


def breaks(path):
    b = E.load(path); roc, low = roc_band(b['close'])
    ends = []
    for k in range(len(b['date'])):
        e = bucket_end(b['date'], k)
        if e is not None and low[k] is not None and roc[k] < low[k]: ends.append(e)
    return sorted(ends), b, roc, low


EXPORTS = {
    'ETH': '/mnt/user-data/attachments/8f875660-8635-5623-af2d-fe53d5c3b161/5fa291ea-COINBASE_ETHUSD_5D_aa1c6.csv',
    'BTC': '/mnt/user-data/attachments/8f875660-8635-5623-af2d-fe53d5c3b161/9c10eb42-COINBASE_BTCUSD_5D_e6575.csv',
}


def validate():
    for a, f in EXPORTS.items():
        if not os.path.exists(f): P(f'validation {a}: export not present, skipped'); continue
        tv = {}
        for r in csv.DictReader(open(f)):
            if r['ROC'] and r['Lower band']:
                tv[dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date()] = (float(r['ROC']), float(r['Lower band']))
        _, b, roc, low = breaks(f'data/{a}_5D.csv')
        same = tot = agree = 0
        for k, d in enumerate(b['date']):
            if d in tv and roc[k] is not None and low[k] is not None and k < len(b['date']) - 1:
                tot += 1; r, l = tv[d]
                same += abs(r - roc[k]) < 0.01 and abs(l - low[k]) < 0.01
                agree += (r < l) == (roc[k] < low[k])
        P(f'validation {a} vs his TradingView export (closed 5D bars): ROC and lower band equal to 0.01 on {same}/{tot}; '
          f'below-band state agrees on {agree}/{tot}')


def rate(g, k): return 100 * sum(x[k] for x in g) / len(g) if g else None
def med(g, k): return S.median(x[k] for x in g) if g else None


def main():
    P('ROC+ LOWER BAND AS A LENS -- declared 25 Nov 2026 (lab/rocband.py)')
    validate()
    BR = {a: breaks(f'data/{a}_5D.csv')[0] for a in ('ETH', 'BTC')}
    OWN = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D'):
            OWN[f'{a} {tf}'] = breaks(f'data/{a}_{tf}.csv')[0]
    T5 = {a: five(a)[2] for a in ('ETH', 'BTC')}

    def within(ends, d0, days):
        j = bisect.bisect_right(ends, d0)
        return j > 0 and (d0 - ends[j - 1]).days <= days

    rows = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > LAST or not x['reached20']: continue
        a = x['asset']
        rows.append(dict(a=a, ch=x['chart'], d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1,
                         win=x['reached20'] == 'yes', w10=x['reached10'] == 'yes', t30=x['touched30'] == 'yes',
                         dd=float(x['maxDrawdown']), up=float(x['bestMove']), bkA=x['tags'][:1] == 'A',
                         lens=set(t.strip() for t in x['lenses'].split('+')),
                         t5=within(T5[a], d0, 30),
                         f=dict(B60=within(BR[a], d0, 60), B30=within(BR[a], d0, 30), OWN60=within(OWN[x['chart']], d0, 60))))

    P('')
    P('SUMMARY  cand asset | n on/off | +10% on/off | +20% on/off | t30 on/off | med deepest dip on/off | med best move on/off')
    for a in ('ETH', 'BTC'):
        for c in ('B60', 'B30', 'OWN60'):
            g = [r for r in rows if r['a'] == a]
            on = [r for r in g if r['f'][c]]; off = [r for r in g if not r['f'][c]]
            P(f'{c:<5} {a} | {len(on)}/{len(off)} | {rate(on,"w10"):.0f}/{rate(off,"w10"):.0f} | {rate(on,"win"):.0f}/{rate(off,"win"):.0f} | '
              f'{rate(on,"t30"):.0f}/{rate(off,"t30"):.0f} | {med(on,"dd"):.1f}/{med(off,"dd"):.1f} | {med(on,"up"):.1f}/{med(off,"up"):.1f}'
              if on and off else f'{c:<5} {a} | {len(on)}/{len(off)} | too few')

    P('')
    P('RULES  cand asset | to 2021: n on/off win on/off t30 on/off | 2022 on: same | charts years | shuffle real/p95 | overlap | verdict')
    for a in ('ETH', 'BTC'):
        for c in ('B60', 'B30', 'OWN60'):
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
                    if rate(on, 'win') - rate(off, 'win') < 1 and rate(off, 't30') - rate(on, 't30') < 1:
                        ov = f'{ln}={"on" if half else "off"}'; break
                if ov != '-': break
            if ov != '-': ok = False
            s0, s1 = st_
            f_ = lambda v: '  -' if v is None else f'{v:3.0f}'
            P(f'{c:<5} {a} | {s0[0]:3d}/{s0[1]:<3d} {f_(s0[2])}/{f_(s0[3])} {f_(s0[4])}/{f_(s0[5])} | '
              f'{s1[0]:3d}/{s1[1]:<3d} {f_(s1[2])}/{f_(s1[3])} {f_(s1[4])}/{f_(s1[5])} | {ch[0]}/{ch[1]} {yr[0]}/{yr[1]} | '
              f'{real:+.1f}/{p95:+.1f} | {ov} | {"PASS" if ok else "fail"}')

    P('')
    P('BY CHART (B60)  chart | n on/off | +20% on/off | t30 on/off')
    for chn in sorted({r['ch'] for r in rows}):
        g = [r for r in rows if r['ch'] == chn]; on = [r for r in g if r['f']['B60']]; off = [r for r in g if not r['f']['B60']]
        P(f'{chn} | {len(on)}/{len(off)} | ' + (f'{rate(on,"win"):.0f}/{rate(off,"win"):.0f} | {rate(on,"t30"):.0f}/{rate(off,"t30"):.0f}' if on and off else '-'))
    P('')
    P('BY YEAR (B60)  asset year | n on/off | +20% on/off | t30 on/off')
    for a in ('ETH', 'BTC'):
        for y in sorted({r['yr'] for r in rows if r['a'] == a}):
            g = [r for r in rows if r['a'] == a and r['yr'] == y]; on = [r for r in g if r['f']['B60']]; off = [r for r in g if not r['f']['B60']]
            P(f'{a} {y} | {len(on)}/{len(off)} | ' + (f'{rate(on,"win") if on else float("nan"):.0f}/{rate(off,"win") if off else float("nan"):.0f} | '
                                                     f'{rate(on,"t30") if on else float("nan"):.0f}/{rate(off,"t30") if off else float("nan"):.0f}'))
    P('')
    P('BREAK EPISODES (5D bars closed below the lower band, grouped when under 60 days apart)')
    for a in ('ETH', 'BTC'):
        eps = []
        for e in BR[a]:
            if eps and (e - eps[-1][-1]).days <= 60: eps[-1].append(e)
            else: eps.append([e])
        P(f'{a}: {len(eps)} episodes, {len(BR[a])} bars: ' + '; '.join(f'{x[0]}..{x[-1]}' if len(x) > 1 else f'{x[0]}' for x in eps))
    P('')
    P('B60 SIGNALS BY BREAK EPISODE (reporting only, added after the first run)  asset episode | n | +20% | t30')
    for a in ('ETH', 'BTC'):
        eps = []
        for e in BR[a]:
            if eps and (e - eps[-1][-1]).days <= 60: eps[-1].append(e)
            else: eps.append([e])
        for ep in eps:
            g = []
            for r in rows:
                if r['a'] != a or not r['f']['B60']: continue
                j = bisect.bisect_right(BR[a], r['d0'])
                if ep[0] <= BR[a][j - 1] <= ep[-1]: g.append(r)
            if g: P(f'{a} {ep[0]}..{ep[-1]} | {len(g)} | {rate(g,"win"):.0f}% | {rate(g,"t30"):.0f}%')
    P('')
    P('CO-OCCURRENCE with the 5D-turn-under-40 watch item (lens5d T30), B60:')
    for a in ('ETH', 'BTC'):
        g = [r for r in rows if r['a'] == a]
        both = sum(r['f']['B60'] and r['t5'] for r in g); nb = sum(r['f']['B60'] for r in g); nt = sum(r['t5'] for r in g)
        P(f'{a}: B60 {nb}, T30 {nt}, both {both}, expected by chance {nb * nt / len(g):.1f}')
    P('')
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_rocband.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
