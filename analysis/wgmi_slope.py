"""WGMI histogram ONLY (the 110-day slope of DIRECTION) as a lens on CTZB signals.
DECLARED 15 Nov 2026, before running. Jared, 15 Nov: test only the histogram part
of WGMI v4 as an additional lens. A one-off exception to the 26 Oct "no WGMI in
any analysis" rule, for this histogram only.

THIS IS A CEILING, NOT AN ESTIMATE. The global M2 behind it is revised after
publication; every value here is what the indicator shows today for past dates.
A fail is final (it did not help even with hindsight data). A pass cannot become
a lens: point-in-time M2 for 21 countries does not exist.

DATA
  data/tradingview/wgmi/BTC_2D_wgmi_tv.csv, column "DIRECTION unshifted (for
  export)", BTC 2D, to 2026-09-12. Slope = DIRECTION minus DIRECTION 55 bars
  earlier (55 x 2D = 110 days, the script's slopeLen scaled to 2D). Read at the
  last 2D bar CLOSED by the entry day. The export predates v4; v4's header says
  the engine is unchanged from v3.1, not verified against this file.

POPULATION
  datasets/ledger.csv: regime-gated ETH and BTC signals, 1D 2D 3D 5D, entry =
  confirmation close, full 60-day windows. win = +20% within 60 days, t30 =
  touched -30% within 60 days. Periods to 2021 / 2022 on. ETH and BTC are one
  sample (date-anchored).

CANDIDATES (4 x 2 assets = 8)
  S_GT1   slope > +1   (the script's 87% band)
  S_GT0   slope > 0
  S_LT0   slope < 0    (tested as a warning)
  S_LTM1  slope < -1   (tested as a warning)

RULES (PRETRADE)
  1  SELECTOR: win lift >= +5 in BOTH periods, t30 not more than 3 worse.
     WARNING: win lift <= -5 in both periods (or t30 >= +5 worse with win not
     better by more than 3). n >= 15 per side per period.
  2  same direction on >= 2/3 of charts (n >= 5 per side) and >= 2/3 of years
     (n >= 3 per side).
  3  within-year shuffle 200x: real beats the 95th percentile.
  4  overlap: inside each half of every live lens of the asset and of bucket A,
     effect under 1 point on both win and t30 -> counted twice, dropped.

ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I analysis/wgmi_slope.py -> analysis/RESULTS_wgmi_slope.txt
"""
import sys, os, csv, random, bisect, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); os.chdir(ROOT)

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)

SPLIT = dt.date(2022, 1, 1); LAST = dt.date(2026, 9, 10)
LIVE = {'ETH': ['GAP', 'HIGH', 'AGREE', 'BTC3', 'FUND', 'FCOOL'], 'BTC': ['GAP', 'UP8', 'BTCX', 'FASTCT']}
CANDS = {'S_GT1': ('SEL', lambda s: s > 1), 'S_GT0': ('SEL', lambda s: s > 0),
         'S_LT0': ('WARN', lambda s: s < 0), 'S_LTM1': ('WARN', lambda s: s < -1)}
random.seed(20261115)


def slope_series():
    rows = list(csv.reader(open('data/tradingview/wgmi/BTC_2D_wgmi_tv.csv')))
    hdr = rows[0]; j = hdr.index('DIRECTION unshifted (for export)')
    t = [dt.datetime.utcfromtimestamp(int(r[0])).date() for r in rows[1:]]
    v = [float(r[j]) if r[j] not in ('', 'NaN') else None for r in rows[1:]]
    ends, sl = [], []
    for i in range(len(t) - 1):          # last row never read (not known closed)
        ends.append(t[i + 1] - dt.timedelta(days=1))
        sl.append(v[i] - v[i - 55] if i >= 55 and v[i] is not None and v[i - 55] is not None else None)
    return ends, sl


def rate(g, k): return 100 * sum(x[k] for x in g) / len(g) if g else None


def main():
    ends, sl = slope_series()
    rows = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > LAST: continue
        k = bisect.bisect_right(ends, d0) - 1
        if k < 0 or sl[k] is None: continue
        rows.append(dict(a=x['asset'], ch=x['chart'], d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1, s=sl[k],
                         win=x['reached20'] == 'yes', t30=x['touched30'] == 'yes', bkA=x['tags'][:1] == 'A',
                         lens=set(t.strip() for t in x['lenses'].split('+'))))
    P('WGMI HISTOGRAM (110-day slope) AS A LENS -- declared 15 Nov 2026 (analysis/wgmi_slope.py)')
    P('CEILING: M2 is revised after publication. A pass cannot become a lens; a fail is final.')
    P(f'signals with a slope read: {len(rows)} (ETH {sum(r["a"]=="ETH" for r in rows)}, BTC {sum(r["a"]=="BTC" for r in rows)}), '
      f'{min(r["d0"] for r in rows)} to {max(r["d0"] for r in rows)}')
    P('cand    asset dir  | to 2021: n on/off  win on/off  t30 on/off | 2022 on: n on/off  win on/off  t30 on/off | charts years | shuffle | overlap | verdict')
    f_ = lambda v: '  -' if v is None else f'{v:3.0f}'
    for a in ('ETH', 'BTC'):
        g = [r for r in rows if r['a'] == a]
        for c, (d, fn) in CANDS.items():
            sign = 1 if d == 'SEL' else -1
            st_ = []; ok = True
            for p in (0, 1):
                on = [r for r in g if r['per'] == p and fn(r['s'])]; off = [r for r in g if r['per'] == p and not fn(r['s'])]
                st_.append((len(on), len(off), rate(on, 'win'), rate(off, 'win'), rate(on, 't30'), rate(off, 't30')))
                if len(on) < 15 or len(off) < 15: ok = False; continue
                w = rate(on, 'win') - rate(off, 'win'); t = rate(on, 't30') - rate(off, 't30')
                if d == 'SEL' and not (w >= 5 and t <= 3): ok = False
                if d == 'WARN' and not ((w <= -5 and t >= -3) or (t >= 5 and w <= 3)): ok = False
            def split(key, nmin):
                grp = {}
                for r in g: grp.setdefault(r[key], []).append(r)
                k_ = t_ = 0
                for gg in grp.values():
                    on = [r for r in gg if fn(r['s'])]; off = [r for r in gg if not fn(r['s'])]
                    if len(on) < nmin or len(off) < nmin: continue
                    t_ += 1; k_ += sign * (rate(on, 'win') - rate(off, 'win')) > 0
                return k_, t_
            ch = split('ch', 5); yr = split('yr', 3)
            if ok and (ch[1] == 0 or ch[0] / ch[1] < 2 / 3 or yr[1] == 0 or yr[0] / yr[1] < 2 / 3): ok = False
            def lift(pp):
                on = [r for r, v in pp if v]; off = [r for r, v in pp if not v]
                return sign * (rate(on, 'win') - rate(off, 'win')) if on and off else 0
            real = lift([(r, fn(r['s'])) for r in g]); byy = {}
            for r in g: byy.setdefault(r['yr'], []).append(r)
            sims = []
            for _ in range(200):
                pp = []
                for gg in byy.values():
                    fl = [fn(r['s']) for r in gg]; random.shuffle(fl); pp += list(zip(gg, fl))
                sims.append(lift(pp))
            sims.sort(); p95 = sims[190]
            if ok and real <= p95: ok = False
            ov = '-'
            for ln in LIVE[a] + ['BUCKET_A']:
                for half in (True, False):
                    gg = [r for r in g if (r['bkA'] if ln == 'BUCKET_A' else ln in r['lens']) == half]
                    on = [r for r in gg if fn(r['s'])]; off = [r for r in gg if not fn(r['s'])]
                    if len(on) < 5 or len(off) < 5: continue
                    if sign * (rate(on, 'win') - rate(off, 'win')) < 1 and sign * (rate(off, 't30') - rate(on, 't30')) < 1:
                        ov = f'{ln}={"on" if half else "off"}'; break
                if ov != '-': break
            if ok and ov != '-': ok = False
            s0, s1 = st_
            P(f'{c:<7} {a} {d:<4} | {s0[0]:3d}/{s0[1]:<3d} {f_(s0[2])}/{f_(s0[3])} {f_(s0[4])}/{f_(s0[5])} | '
              f'{s1[0]:3d}/{s1[1]:<3d} {f_(s1[2])}/{f_(s1[3])} {f_(s1[4])}/{f_(s1[5])} | {ch[0]}/{ch[1]} {yr[0]}/{yr[1]} | '
              f'{real:+.1f}/{p95:+.1f} | {ov} | {"PASS (ceiling)" if ok else "fail"}')
    P('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_wgmi_slope.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
