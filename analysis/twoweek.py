"""Two-week market-state rating — nearest-neighbour analogs on the CTZB state.

WHAT THIS MEASURES. Given how the CTZB indicator reads TODAY across the
1D/2D/3D/5D charts (forming bars included, exactly what the chart shows live),
find the past days that read most alike inside regime-on periods and report
what the asset did over the next 14 calendar days. It rates the MARKET STATE,
not a trade: there is no exit, no sizing, no strategy return. It is a new
measurement — nothing in docs/PRETRADE.md measures a 14-day horizon or
non-signal days — so its output is a first-run figure, not a Tier 1 finding.

DECLARED BEFORE THE FIRST RUN (22 Oct 2026). Do not add a feature, subset or
outcome after seeing results; add a new declared block and report both.

  universe   every day D on which the mechanical gate is ON:
             R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41), read on the last
             COMPLETED BTC 2D bar as of the close of D (no peek)
  state      per chart in 1D/2D/3D/5D of the same asset, as of the close of D
             with the multi-day bar still forming (what the chart shows live):
               CT   rsi(close,14)
               gap  CT - ema(CT,14)          (the Signal line)
               K    sma(stoch(CT,14),3)
             12 numbers, each standardised by its std over the analog pool
  primary    k=40 nearest days by Euclidean distance on all 12, declustered so
             no two analogs sit within 10 days of each other; days within 30
             days of the rating date and days without a full 14-day outcome
             are excluded
  outcomes   from the close of D over the next 14 calendar days, daily candles:
             ret14   close-to-close return
             up      ret14 > 0
             t+10    high reached +10%
             t-10    low reached -10%
             first   +10% reached before -10% (same-day both counts as -10%)
             mfe     best high, mae  worst low
  subsets    S12 all twelve | S2D CT/gap/K on 2D only | SGAP the four gaps only
  k          20 / 40 / 80
  guards     G1 walk-forward skill: every 7th regime-on day from 2019-01-01,
                analogs drawn only from days whose 14-day outcome had already
                closed, standardised on that pool; Brier score for P(up) and
                P(+10 first) against the pool base rate; realised outcome by
                tercile of the forecast; per year
             G2 the primary analogs broken out by year
             G3 ETH and BTC both run; they are ONE sample for anything dated,
                so agreement between them is not confirmation
  also       what is forming now on each chart (pivot low waiting on bars),
             read straight off the engine — reported, not scored

Run from the repo root:  python3 -I analysis/twoweek.py [--asof YYYY-MM-DD]
"""
import sys, os, math, datetime as dt, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R

CHARTS = [('1D', 1), ('2D', 2), ('3D', 3), ('5D', 5)]
HORIZON = 14
KS = (20, 40, 80)
K_PRIMARY = 40
DECLUSTER = 10
EXCLUDE_RECENT = 30
SUBSETS = {
    'S12': [(tf, f) for tf, _ in CHARTS for f in ('ct', 'gap', 'k')],
    'S2D': [('2D', 'ct'), ('2D', 'gap'), ('2D', 'k')],
    'SGAP': [(tf, 'gap') for tf, _ in CHARTS],
}
WF_START = dt.date(2019, 1, 1)
WF_STEP = 7


def wilder(close, n=14):
    """rsi(close,n) plus the running averages, so a forming bar can be stepped."""
    m = len(close)
    ag = [None] * m; al = [None] * m; ct = [None] * m
    if m < n + 1:
        return ct, ag, al
    g = l = 0.0
    for i in range(1, n + 1):
        ch = close[i] - close[i - 1]; g += max(ch, 0.0); l += max(-ch, 0.0)
    ag[n] = g / n; al[n] = l / n
    for i in range(n + 1, m):
        ch = close[i] - close[i - 1]
        ag[i] = (ag[i - 1] * (n - 1) + max(ch, 0.0)) / n
        al[i] = (al[i - 1] * (n - 1) + max(-ch, 0.0)) / n
    for i in range(n, m):
        ct[i] = 100.0 if al[i] == 0 else 100 - 100 / (1 + ag[i] / al[i])
    return ct, ag, al


def bucket(d, tf):
    return (d.year, (d.timetuple().tm_yday - 1) // tf)


def live_state(sym):
    """{date: {tf: (ct, gap, k)}} as of each daily close, forming bars included."""
    day = E.load(f'data/{sym}_1D.csv')
    dd, dc = day['date'], day['close']
    out = {d: {} for d in dd}
    for tf, n in CHARTS:
        b = E.load(f'data/{sym}_{tf}.csv')
        bd, bc = b['date'], b['close']
        idx = {bucket(d, n): j for j, d in enumerate(bd)}
        ct, ag, al = wilder(bc)
        em = E.ema(ct, 14)
        st = E.stoch_of(ct, 14)
        a = 2.0 / 15
        for d, c in zip(dd, dc):
            j = idx.get(bucket(d, n))
            if j is None or j < 30 or ag[j - 1] is None or em[j - 1] is None:
                continue
            ch = c - bc[j - 1]
            g = (ag[j - 1] * 13 + max(ch, 0.0)) / 14
            l = (al[j - 1] * 13 + max(-ch, 0.0)) / 14
            cp = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
            ep = em[j - 1] + a * (cp - em[j - 1])
            w = ct[j - 13:j] + [cp]
            if any(x is None for x in w) or st[j - 1] is None or st[j - 2] is None:
                continue
            hi, lo = max(w), min(w)
            sp = 0.0 if hi == lo else 100 * (cp - lo) / (hi - lo)
            kp = (st[j - 2] + st[j - 1] + sp) / 3
            out[d][tf] = (cp, cp - ep, kp)
    return day, out


def outcomes(day):
    dd, c, h, l = day['date'], day['close'], day['high'], day['low']
    pos = {d: i for i, d in enumerate(dd)}
    res = {}
    for i, d in enumerate(dd):
        end = d + dt.timedelta(days=HORIZON)
        j = i + 1; hs = []; ls = []; last = None; first = None
        while j < len(dd) and dd[j] <= end:
            hs.append(h[j]); ls.append(l[j]); last = c[j]
            if first is None:
                up = h[j] >= c[i] * 1.10; dn = l[j] <= c[i] * 0.90
                if dn: first = 0
                elif up: first = 1
            j += 1
        if last is None or dd[j - 1] < end:
            continue
        res[d] = dict(ret=(last / c[i] - 1) * 100, mfe=(max(hs) / c[i] - 1) * 100,
                      mae=(min(ls) / c[i] - 1) * 100,
                      first=0 if first is None else first)
    return res, pos


def gate_daily():
    g = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    # state of the last BTC 2D bar that had CLOSED by the end of day d
    b = E.load('data/BTC_2D.csv')
    ends = []
    for j, d in enumerate(b['date']):
        nxt = b['date'][j + 1] if j + 1 < len(b['date']) else None
        ends.append((nxt - dt.timedelta(days=1)) if nxt else None)
    import bisect
    closed = [e for e in ends if e is not None]
    def f(d):
        k = bisect.bisect_right(closed, d) - 1
        return g(b['date'][k]) if k >= 0 else False
    return f


def vec(st, feats):
    v = []
    for tf, f in feats:
        t = st.get(tf)
        if t is None:
            return None
        v.append(t[('ct', 'gap', 'k').index(f)])
    return v


def pick(pool_days, X, x0, k):
    sd = X.std(axis=0); sd[sd == 0] = 1
    dist = np.sqrt((((X - x0) / sd) ** 2).sum(axis=1))
    order = np.argsort(dist)
    chosen = []
    for o in order:
        d = pool_days[o]
        if all(abs((d - c).days) > DECLUSTER for c in chosen):
            chosen.append(d)
            if len(chosen) == k:
                break
    return chosen


def summ(days, oc):
    r = [oc[d] for d in days]
    if not r:
        return None
    rets = sorted(x['ret'] for x in r)
    return dict(n=len(r), up=100 * np.mean([x['ret'] > 0 for x in r]),
                t10=100 * np.mean([x['mfe'] >= 10 for x in r]),
                d10=100 * np.mean([x['mae'] <= -10 for x in r]),
                first=100 * np.mean([x['first'] == 1 for x in r]),
                med=float(np.median(rets)), q25=float(np.percentile(rets, 25)),
                q75=float(np.percentile(rets, 75)),
                mfe=float(np.median([x['mfe'] for x in r])),
                mae=float(np.median([x['mae'] for x in r])))


def fmt(s):
    return (f"n={s['n']:>3}  up {s['up']:4.0f}%  +10 {s['t10']:4.0f}%  -10 {s['d10']:4.0f}%  "
            f"+10 first {s['first']:4.0f}%  med {s['med']:+5.1f}% (IQR {s['q25']:+.1f}/{s['q75']:+.1f})  "
            f"mfe {s['mfe']:+.1f}%  mae {s['mae']:+.1f}%")


def forming(sym):
    rows = []
    for tf, n in CHARTS + [('8D', 8)]:
        b = E.load(f'data/{sym}_{tf}.csv')
        ct = E.rsi(b['close'], 14); st = E.stoch_of(ct, 14); kL = E.sma(st, 3)
        m = len(ct)
        for back in (1, 2, 3):
            ti = m - 1 - back
            v = ct[ti]
            if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)):
                continue
            if any(ct[j] < v for j in range(ti + 1, m)):
                continue
            need = 3 - back
            rows.append((tf, b['date'][ti], v, kL[ti], need))
            break
    return rows


def tier1(sym, gate_on_since, asof):
    """Signals confirmed since the regime turned on, read against the Tier 1
    cells in docs/PRETRADE.md (reach +20% in 60 days). Reported, not re-scored:
    the odds quoted are the ones already validated there."""
    rows = []
    allconf = {}
    for tf, n in CHARTS:
        g = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
        sig, b = E.signals(f'data/{sym}_{tf}.csv', regime=g, ungated=True)
        ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
        allconf[tf] = [s['edate'] for s in sig]
        for i, s in enumerate(sig):
            if s['edate'] < gate_on_since:
                continue
            ei = s['ei']
            gap = ct[ei] - em[ei]
            step = (s['entry'] / sig[i - 1]['entry'] - 1) * 100 if i else None
            rows.append(dict(tf=tf, ed=s['edate'], bk=s['bk'], dia=s['dis'], hollow=s['dis'] and not s['strong'],
                             prime=s['prime'], gap=gap, step=step, entry=s['entry'],
                             now=b['close'][-1]))
    for r in rows:  # backward-only agreement: other charts that had ALREADY printed within 10 days
        r['cf'] = sum(1 for tf, ds in allconf.items() if tf != r['tf']
                      and any(0 <= (r['ed'] - d).days <= 10 for d in ds))
    return sorted(rows, key=lambda r: r['ed'])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--asof'); a = ap.parse_args()
    gate = gate_daily()
    for sym in ('ETH', 'BTC'):
        day, state = live_state(sym)
        oc, pos = outcomes(day)
        asof = dt.date.fromisoformat(a.asof) if a.asof else day['date'][-1]
        st0 = state[asof]
        on_days = [d for d in day['date'] if gate(d)]
        print(f'==================== {sym}  as of {asof}  close {day["close"][pos[asof]]:,.2f}  '
              f'gate {"ON" if gate(asof) else "OFF"}')
        for tf, _ in CHARTS:
            ct, gp, k = st0[tf]
            print(f'  {tf}  CT {ct:5.1f}  gap {gp:+6.2f}  K {k:5.1f}')
        fm = forming(sym)
        for tf, d, v, k, need in fm:
            print(f'  forming {tf}: pivot low {d} CT {v:.1f} K {k:.1f}, needs {need} more bar(s)')
        if not fm:
            print('  forming: no pivot low waiting on bars on 1D/2D/3D/5D/8D')
        on_since = max(d for d in day['date'] if d <= asof and gate(d) and not gate(d - dt.timedelta(days=1)))
        print(f'  regime on since {on_since} ({(asof - on_since).days} days)')
        print('  signals confirmed since then, Tier 1 read:')
        for r in tier1(sym, on_since, asof):
            tags = (['hollow dmd' if r['hollow'] else 'filled dmd'] if r['dia'] else []) + (['prime'] if r['prime'] else [])
            print(f"    {r['tf']} {r['ed']} {r['bk']} {','.join(tags) or 'plain':<18} gap at entry {r['gap']:+6.2f}  "
                  f"step {('%+.1f%%' % r['step']) if r['step'] is not None else '-':>7}  agree {r['cf']}  "
                  f"entry {r['entry']:,.2f}  now {(r['now']/r['entry']-1)*100:+.1f}%")

        base_days = [d for d in on_days if d in oc and (asof - d).days > EXCLUDE_RECENT]
        print(f'\n  BASELINE regime-on days, 14d: {fmt(summ(base_days, oc))}')
        all_days = [d for d in day['date'] if d in oc and (asof - d).days > EXCLUDE_RECENT]
        print(f'  BASELINE all days,       14d: {fmt(summ(all_days, oc))}')

        prim = None
        for sname, feats in SUBSETS.items():
            x0 = vec(st0, feats)
            pool = [d for d in base_days if vec(state[d], feats) is not None]
            X = np.array([vec(state[d], feats) for d in pool])
            for k in KS:
                ch = pick(pool, X, np.array(x0), k)
                s = summ(ch, oc)
                tag = '  <- PRIMARY' if (sname == 'S12' and k == K_PRIMARY) else ''
                print(f'  {sname:<4} k={k:<3} {fmt(s)}{tag}')
                if tag:
                    prim = ch
        print('\n  G2 primary analogs by year')
        for y in sorted({d.year for d in prim}):
            ys = [d for d in prim if d.year == y]
            s = summ(ys, oc)
            print(f'    {y}  n={s["n"]:>2}  up {s["up"]:4.0f}%  +10 first {s["first"]:4.0f}%  med {s["med"]:+5.1f}%')
        print('  primary analog dates:', ' '.join(str(d) for d in sorted(prim)))

        # G1 walk-forward skill
        feats = SUBSETS['S12']
        tests = [d for d in on_days if d >= WF_START and d in oc and (asof - d).days > HORIZON][::WF_STEP]
        rec = []
        for t in tests:
            pool = [d for d in on_days if d in oc and (t - d).days > HORIZON
                    and vec(state[d], feats) is not None]
            if len(pool) < 200 or vec(state[t], feats) is None:
                continue
            X = np.array([vec(state[d], feats) for d in pool])
            ch = pick(pool, X, np.array(vec(state[t], feats)), K_PRIMARY)
            pu = np.mean([oc[d]['ret'] > 0 for d in ch])
            pf = np.mean([oc[d]['first'] == 1 for d in ch])
            bu = np.mean([oc[d]['ret'] > 0 for d in pool])
            bf = np.mean([oc[d]['first'] == 1 for d in pool])
            yu = float(oc[t]['ret'] > 0); yf = float(oc[t]['first'] == 1)
            rec.append((t, pu, bu, yu, pf, bf, yf, oc[t]['ret']))
        R_ = np.array([r[1:] for r in rec])
        bs = lambda p, y: float(np.mean((p - y) ** 2))
        print(f'\n  G1 walk-forward, {len(rec)} test days {rec[0][0]} .. {rec[-1][0]}')
        print(f'    P(up)        Brier analog {bs(R_[:,0],R_[:,2]):.4f}  base {bs(R_[:,1],R_[:,2]):.4f}')
        print(f'    P(+10 first) Brier analog {bs(R_[:,3],R_[:,5]):.4f}  base {bs(R_[:,4],R_[:,5]):.4f}')
        q = np.quantile(R_[:, 0], [1 / 3, 2 / 3])
        for lab, m in (('low', R_[:, 0] <= q[0]), ('mid', (R_[:, 0] > q[0]) & (R_[:, 0] <= q[1])),
                       ('high', R_[:, 0] > q[1])):
            print(f'    forecast tercile {lab:<4} n={m.sum():>3}  mean P(up) {100*R_[m,0].mean():4.0f}%  '
                  f'realised up {100*R_[m,2].mean():4.0f}%  med ret {np.median(R_[m,6]):+5.1f}%')
        print('    by year (Brier analog vs base, P(up))')
        for y in sorted({r[0].year for r in rec}):
            m = np.array([r[0].year == y for r in rec])
            print(f'      {y}  n={m.sum():>3}  analog {bs(R_[m,0],R_[m,2]):.3f}  base {bs(R_[m,1],R_[m,2]):.3f}  '
                  f'{"analog better" if bs(R_[m,0],R_[m,2]) < bs(R_[m,1],R_[m,2]) else "base better"}')
        print()


if __name__ == '__main__':
    main()
