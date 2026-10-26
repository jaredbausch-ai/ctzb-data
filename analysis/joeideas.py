"""Joe's seven "extra edge" ideas (his 24 Oct email), tested 25 Oct 2026.

DECLARED BEFORE RUNNING. Same scorecard as analysis/grokpack.py: gate
R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41); entry = close of the bar the
signal is taken on, dated the day it closes; outcomes on daily candles over 60
days, full windows only; win = reach +20%; periods 2016-21 and 2022 on. Charts:
ETH and BTC 1D 2D 3D 5D 8D (10 charts).

IDEA 1  Live cycle length (Ehlers dominant cycle, Hilbert-transform homodyne
        discriminator on (high+low)/2, as published in "Rocket Science for
        Traders"). The momentum line and its stochastic use a length that
        changes every bar with the measured cycle, instead of the fixed one.
          1a  length = half the dominant cycle (Ehlers' convention for RSI),
              rounded, clamped 6-30
          1b  length = the full dominant cycle, rounded, clamped 6-50
        Wilder smoothing with a per-bar length; stochastic lookback = same
        length; K smoothing unchanged (3). Trough rules unchanged.
        PASS if, against the current signal, the variant's win rate is higher
        in BOTH periods (each period n >= 8) on at least 7 of 10 charts, it
        keeps at least 80% of the signal count, and it is not later on the
        troughs both versions catch (median entry difference <= 0 bars).

IDEA 2  Ehlers super smoother on the stochastic line (replaces the 3-bar
        average). Troughs do not change; only the tags the stochastic drives
        (prime dot, diamond) change.
          2a  super smoother period 3     2b  period 10 (Ehlers' default)
        PASS if the prime dot's and the diamond's lift (tag win minus the
        chart's base) is higher than with the current stochastic in BOTH
        periods, pooled per asset for both ETH and BTC, and on at least 6 of
        10 charts overall.

IDEA 3  Phase-difference entry. The two lines are the momentum line and its
        stochastic. For every current signal's trough:
          3a  enter at the close of the first bar after the trough where the
              gap between the two lines narrows (the "phase gap peaks and
              starts closing"), taken whether or not the low later confirms
          3b  enter at the close where the stochastic crosses up through the
              momentum line (the "full cross"), if within 15 bars
        compared with the confirmation entry on the same troughs.
        PASS if win rate >= confirmation's in both periods on at least 7 of
        10 charts, with median drawdown before the high no worse.

IDEA 4  Funding / open interest / volume: NOT re-run. On the do-not-re-test
        list (analysis/derivtest.py and analysis/sweep.py, 23 Oct). Cited.

IDEA 5  Weekly-chart agreement before a signal. Weekly bars built from the
        daily file (Monday weeks), last weekly bar closed by the entry day.
          5a  weekly momentum rising (last closed weekly bar above the one before)
          5b  weekly momentum above its signal line (EMA 14 of the momentum)
        On 1D 2D 3D 5D both assets. PASS if lift >= +10 points pooled for
        each asset, positive in both periods on at least 6 of 8 charts, AND
        still >= +5 points inside each half of the existing 8D-rising filter
        (otherwise it is the 8D filter under another name).

IDEA 6  Stepped volatility exits: NOT tested. Exits are discretionary and
        settled; five mechanical exit rules lost to holding. Cited.

IDEA 7  Timing entries around funding resets: cost, not signal. Measured on
        the Binance USDT perpetuals (8-hour funding, the longest continuous
        series in data/derivs): funding per interval at signal entries, and
        the funding a long pays over a 60-day hold (180 intervals). One
        interval is the most that timing an entry around a reset can save.

ENTRY QUALITY ONLY. Signals are computed, never fills.
  python3 -I analysis/joeideas.py   -> analysis/RESULTS_joeideas.txt, joeideas.json
"""
import sys, os, json, math, datetime as dt, statistics as st, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure
from sweep import closed_index
from confirmlag import weekly

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D')
SPLIT = dt.date(2022, 1, 1)
OUT = {}


# ---------- indicator variants ----------
def dominant_cycle(H, L):
    n = len(H); P = [(h + l) / 2 for h, l in zip(H, L)]
    sm = [0.0] * n; de = [0.0] * n; q1 = [0.0] * n; i1 = [0.0] * n; ji = [0.0] * n; jq = [0.0] * n
    i2 = [0.0] * n; q2 = [0.0] * n; re = [0.0] * n; im = [0.0] * n; per = [0.0] * n; sp = [0.0] * n
    for t in range(n):
        if t < 6:
            per[t] = 15.0; sp[t] = 15.0; continue
        sm[t] = (4 * P[t] + 3 * P[t - 1] + 2 * P[t - 2] + P[t - 3]) / 10
        adj = 0.075 * per[t - 1] + 0.54
        hil = lambda x: (0.0962 * x[t] + 0.5769 * x[t - 2] - 0.5769 * x[t - 4] - 0.0962 * x[t - 6]) * adj
        de[t] = hil(sm); q1[t] = hil(de); i1[t] = de[t - 3]
        ji[t] = hil(i1); jq[t] = hil(q1)
        a = i1[t] - jq[t]; b = q1[t] + ji[t]
        i2[t] = 0.2 * a + 0.8 * i2[t - 1]; q2[t] = 0.2 * b + 0.8 * q2[t - 1]
        r = i2[t] * i2[t - 1] + q2[t] * q2[t - 1]; m = i2[t] * q2[t - 1] - q2[t] * i2[t - 1]
        re[t] = 0.2 * r + 0.8 * re[t - 1]; im[t] = 0.2 * m + 0.8 * im[t - 1]
        p = per[t - 1]
        if im[t] != 0 and re[t] != 0:
            p = 360.0 / math.degrees(math.atan(im[t] / re[t]))
        p = min(p, 1.5 * per[t - 1]); p = max(p, 0.67 * per[t - 1]); p = min(max(p, 6.0), 50.0)
        per[t] = 0.2 * p + 0.8 * per[t - 1]
        sp[t] = 0.33 * per[t] + 0.67 * sp[t - 1]
    return sp


def rsi_var(src, L):
    n0 = 14; out = [None] * len(src)
    if len(src) < n0 + 1: return out
    g = l = 0.0
    for i in range(1, n0 + 1):
        ch = src[i] - src[i - 1]; g += max(ch, 0.0); l += max(-ch, 0.0)
    ag, al = g / n0, l / n0
    out[n0] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n0 + 1, len(src)):
        n = L[i]; ch = src[i] - src[i - 1]
        ag = (ag * (n - 1) + max(ch, 0.0)) / n; al = (al * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def stoch_var(src, L):
    out = [None] * len(src)
    for i in range(len(src)):
        n = L[i]; w = src[max(0, i - n + 1):i + 1]
        if len(w) < n or any(x is None for x in w): continue
        hi, lo = max(w), min(w); out[i] = 0.0 if hi == lo else 100 * (src[i] - lo) / (hi - lo)
    return out


def supersmoother(x, P):
    a1 = math.exp(-1.414 * math.pi / P); b1 = 2 * a1 * math.cos(1.414 * math.pi / P)
    c2, c3 = b1, -a1 * a1; c1 = 1 - c2 - c3
    out = [None] * len(x); f1 = f2 = None
    for i in range(len(x)):
        if x[i] is None or i == 0 or x[i - 1] is None:
            f1 = f2 = None; continue
        if f1 is None:
            f = x[i]
        else:
            f = c1 * (x[i] + x[i - 1]) / 2 + c2 * f1 + c3 * (f2 if f2 is not None else f1)
        out[i] = f; f2, f1 = f1, f
    return out


# ---------- signals from arbitrary momentum / stochastic series ----------
def signals_from(b, ct, kL, ungated=True):
    dates = b['date']; c = b['close']; n = len(c); out = []; pCt = pK = None
    for conf in range(n):
        ti = conf - 3
        if ti - 3 < 0: continue
        v = ct[ti]
        if v is None or any(ct[j] is None for j in range(ti - 3, ti + 4)): continue
        if any(ct[j] <= v for j in range(ti - 3, ti)): continue
        if any(ct[j] <= v for j in range(ti + 1, ti + 4)): continue
        tk = kL[ti]
        if tk is None: continue
        hasPrev = pCt is not None
        dCt = v - pCt if hasPrev else None; dK = tk - pK if hasPrev else None
        dis = bool(hasPrev and ((dCt > 0 and dK < 0) or (dCt < 0 and dK > 0)))
        if GATE(dates[ti]):
            out.append(dict(ti=ti, ei=conf, ct=v, k=tk, bk='A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D',
                            dis=dis, strong=dis and v < 50, prime=20 <= tk < 50, entry=c[conf]))
        pCt, pK = v, tk
    return out


DAY = {a: E.load(f'data/{a}_1D.csv') for a in ASSETS}
POS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in ASSETS}


def score(a, b, sigs, ei_key='ei', px_key='entry'):
    rows = []
    for s in sigs:
        ei = s[ei_key]
        if ei is None or ei >= len(b['date']): continue
        d0 = bucket_end(b['date'], ei)
        if d0 is None or d0 not in POS[a]: continue
        m = measure(DAY[a], POS[a], d0, s[px_key], 60)
        if not m: continue
        r = dict(s); r.update(d0=d0, per='16-21' if d0 < SPLIT else '22-26', yr=d0.year, win=m['up'] >= 20,
                             ddpk=m['ddpk'], t20=m['dd'] <= -20, t30=m['dd'] <= -30)
        rows.append(r)
    return rows


def st_(G):
    if not G: return None
    n = len(G); o = dict(n=n, win=100 * sum(r['win'] for r in G) / n, ddpk=st.median(r['ddpk'] for r in G),
                         t20=100 * sum(r['t20'] for r in G) / n, t30=100 * sum(r['t30'] for r in G) / n)
    for p in ('16-21', '22-26'):
        x = [r for r in G if r['per'] == p]
        o[p] = (100 * sum(r['win'] for r in x) / len(x) if x else None, len(x))
    return o


def f(s):
    if not s: return 'n=0'
    g = lambda p: '   -  ' if s[p][0] is None else f'{s[p][0]:3.0f}%({s[p][1]:>3})'
    return f'n={s["n"]:>4} win {s["win"]:3.0f}% [{g("16-21")} {g("22-26")}] ddpk {s["ddpk"]:+5.1f}% t30 {s["t30"]:3.0f}%'


def better_both(sv, sb):
    ok = lambda s, p: s and s[p][1] >= 8 and s[p][0] is not None
    if not (ok(sv, '16-21') and ok(sv, '22-26') and ok(sb, '16-21') and ok(sb, '22-26')): return False
    return sv['16-21'][0] > sb['16-21'][0] and sv['22-26'][0] > sb['22-26'][0]


def load(a, tf):
    b = E.load(f'data/{a}_{tf}.csv')
    ct = E.rsi(b['close'], 14); kL = E.sma(E.stoch_of(ct, 14), 3)
    return b, ct, kL


def main():
    P = print
    P('JOE IDEAS -- declared tests, run', dt.date.today(), '| entry quality only, signals not fills\n')
    # baseline check against engine.signals
    base = {}
    for a in ASSETS:
        for tf in TFS:
            b, ct, kL = load(a, tf)
            mine = signals_from(b, ct, kL); ref, _ = E.signals(f'data/{a}_{tf}.csv', regime=GATE)
            same = [(x['ti'], x['bk'], x['dis'], x['prime']) for x in mine] == [(x['ti'], x['bk'], x['dis'], x['prime']) for x in ref]
            if not same: raise SystemExit(f'baseline mismatch {a} {tf}')
            base[(a, tf)] = (b, ct, kL, mine, score(a, b, mine))
    P('baseline: array engine reproduces engine.signals exactly on all 10 charts\n')

    # ---------- IDEA 1 ----------
    P('IDEA 1  live cycle length')
    I1 = {}
    for var, fn in (('1a half cycle', lambda dc: min(30, max(6, round(dc / 2)))), ('1b full cycle', lambda dc: min(50, max(6, round(dc))))):
        wins = 0; cnt_v = cnt_b = 0; lags = []; rows_out = []
        for a in ASSETS:
            for tf in TFS:
                b, ct0, kL0, sb, rb = base[(a, tf)]
                dc = dominant_cycle(b['high'], b['low']); L = [fn(x) for x in dc]
                ct = rsi_var(b['close'], L); kL = E.sma(stoch_var(ct, L), 3)
                sv = signals_from(b, ct, kL); rv = score(a, b, sv)
                sV, sB = st_(rv), st_(rb); bb = better_both(sV, sB); wins += bb
                cnt_v += len(sv); cnt_b += len(sb)
                bt = [x['ti'] for x in sb]
                lag = [min((x['ti'] - t for t in bt), key=abs) for x in sv if bt and min(abs(x['ti'] - t) for t in bt) <= 3]
                ov = len(lag) / len(sv) if sv else 0
                lags += lag
                medL = st.median(L[200:]) if len(L) > 200 else None
                P(f'  {var:<13} {a} {tf:<3} variant {f(sV)}\n  {"":<13} {a} {tf:<3} current {f(sB)}  better both periods: {"YES" if bb else "no"}'
                  f'  | {len(sv)} vs {len(sb)} signals, {100*ov:.0f}% within 3 bars of a current trough, median length {medL}')
                rows_out.append(dict(chart=f'{a} {tf}', variant=sV, current=sB, better_both=bb, n_variant=len(sv), n_current=len(sb),
                                     overlap=round(100 * ov), median_length=medL))
        ml = st.median(lags) if lags else None
        verdict = wins >= 7 and cnt_v >= 0.8 * cnt_b and (ml is not None and ml <= 0)
        P(f'  {var}: better in both periods on {wins}/10 charts; signals {cnt_v} vs {cnt_b} ({100*cnt_v/cnt_b:.0f}%); '
          f'median timing vs current on shared troughs {ml:+} bars -> {"PASS" if verdict else "FAIL"}\n')
        I1[var] = dict(charts=rows_out, better_charts=wins, signals=cnt_v, signals_current=cnt_b, median_lag=ml, verdict='PASS' if verdict else 'FAIL')
    OUT['idea1'] = I1

    # ---------- IDEA 2 ----------
    P('IDEA 2  super smoother on the stochastic (troughs unchanged; tags change)')
    I2 = {}
    for var, Pss in (('2a period 3', 3), ('2b period 10', 10)):
        res = {'prime': [], 'diamond': []}; pooled = {}
        for tag in ('prime', 'diamond'):
            key = 'prime' if tag == 'prime' else 'dis'
            charts_better = 0; detail = []
            for a in ASSETS:
                pv = {'16-21': [], '22-26': []}
                for tf in TFS:
                    b, ct, kL0, sb, rb = base[(a, tf)]
                    kS = supersmoother(E.stoch_of(ct, 14), Pss)
                    sv = signals_from(b, ct, kS); rv = score(a, b, sv)
                    baseS = st_(rb)
                    tv = st_([r for r in rv if r[key]]); tb = st_([r for r in rb if r[key]])
                    def lift(t, p):
                        return None if (not t or t[p][1] < 5 or t[p][0] is None) else t[p][0] - baseS[p][0]
                    lv = (lift(tv, '16-21'), lift(tv, '22-26')); lb = (lift(tb, '16-21'), lift(tb, '22-26'))
                    ok = None not in lv + lb and lv[0] > lb[0] and lv[1] > lb[1]
                    charts_better += ok
                    detail.append(dict(chart=f'{a} {tf}', smoothed=tv, current=tb, better_both=ok))
                    P(f'  {var:<12} {tag:<7} {a} {tf:<3} smoothed {f(tv)}\n  {"":<12} {"":<7} {a} {tf:<3} current  {f(tb)}  better both: {"YES" if ok else "no"}')
                # pooled per asset
                allv = []; allb = []; allbase = []
                for tf in TFS:
                    b, ct, kL0, sb, rb = base[(a, tf)]
                    kS = supersmoother(E.stoch_of(ct, 14), Pss); rv = score(a, b, signals_from(b, ct, kS))
                    allv += [r for r in rv if r[key]]; allb += [r for r in rb if r[key]]; allbase += rb
                pv_, pb_, pbase = st_(allv), st_(allb), st_(allbase)
                okp = all(pv_[p][0] - pbase[p][0] > pb_[p][0] - pbase[p][0] for p in ('16-21', '22-26'))
                pooled[(tag, a)] = okp
                P(f'  {var:<12} {tag:<7} {a} pooled smoothed {f(pv_)}\n  {"":<12} {"":<7} {a} pooled current  {f(pb_)}  better both: {"YES" if okp else "no"}')
            res[tag] = dict(charts_better=charts_better, detail=detail)
        verdict = all(pooled.values()) and all(res[t]['charts_better'] >= 6 for t in res)
        P(f'  {var}: prime better on {res["prime"]["charts_better"]}/10, diamond on {res["diamond"]["charts_better"]}/10; '
          f'pooled {pooled} -> {"PASS" if verdict else "FAIL"}\n')
        I2[var] = dict(prime_charts=res['prime']['charts_better'], diamond_charts=res['diamond']['charts_better'],
                       pooled={f'{k[0]} {k[1]}': v for k, v in pooled.items()}, verdict='PASS' if verdict else 'FAIL',
                       detail=res)
    OUT['idea2'] = I2

    # ---------- IDEA 3 ----------
    P('IDEA 3  phase-difference entry vs the confirmation entry, same troughs')
    I3 = {}
    for var in ('3a gap starts closing', '3b full cross'):
        wins = 0; ddok = 0; rows_out = []; nc_all = []
        for a in ASSETS:
            for tf in TFS:
                b, ct, kL, sb, rb = base[(a, tf)]
                n = len(ct); c = b['close']
                # every gated trough candidate with the left side satisfied, plus whether it confirmed
                cand = []
                conf_ti = {x['ti'] for x in sb}
                for ti in range(3, n - 1):
                    v = ct[ti]
                    if v is None or kL[ti] is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)): continue
                    if ct[ti + 1] is None or ct[ti + 1] <= v: continue
                    if not GATE(b['date'][ti]): continue
                    cand.append(ti)
                ent = []
                for ti in cand:
                    j = None
                    if var.startswith('3a'):
                        for jj in range(ti + 1, min(ti + 4, n)):
                            if ct[jj] is None or kL[jj] is None or ct[jj - 1] is None or kL[jj - 1] is None: break
                            if abs(ct[jj] - kL[jj]) < abs(ct[jj - 1] - kL[jj - 1]): j = jj; break
                        conf = ti in conf_ti
                    else:
                        if ti not in conf_ti: continue
                        for jj in range(ti + 1, min(ti + 16, n)):
                            if kL[jj] is None or ct[jj] is None or kL[jj - 1] is None or ct[jj - 1] is None: continue
                            if kL[jj - 1] <= ct[jj - 1] and kL[jj] > ct[jj]: j = jj; break
                        conf = True
                    if j is not None:
                        ent.append(dict(ti=ti, ei=j, entry=c[j], conf=conf))
                rv = score(a, b, ent)
                sV, sB = st_(rv), st_(rb)
                bb = sV and sB and all(sV[p][1] >= 8 and sB[p][1] >= 8 and sV[p][0] >= sB[p][0] for p in ('16-21', '22-26'))
                dk = sV and sB and sV['ddpk'] >= sB['ddpk']
                wins += bool(bb); ddok += bool(dk)
                nc = 100 * sum(1 for r in rv if not r['conf']) / len(rv) if rv else 0
                lag = st.median([r['ei'] - (r['ti'] + 3) for r in rv]) if rv else None
                nc_all.append(nc)
                P(f'  {var:<21} {a} {tf:<3} entry   {f(sV)}  never confirmed {nc:3.0f}%  median bars vs confirmation {lag:+}\n'
                  f'  {"":<21} {a} {tf:<3} confirm {f(sB)}  at least as good both periods: {"YES" if bb else "no"}')
                rows_out.append(dict(chart=f'{a} {tf}', entry=sV, confirmation=sB, ok=bool(bb), never_confirmed=round(nc), median_bars_vs_confirmation=lag))
        verdict = wins >= 7 and ddok >= 7
        P(f'  {var}: at least as good in both periods on {wins}/10 charts, drawdown no worse on {ddok}/10 -> {"PASS" if verdict else "FAIL"}\n')
        I3[var] = dict(charts=rows_out, ok_charts=wins, dd_ok=ddok, verdict='PASS' if verdict else 'FAIL')
    OUT['idea3'] = I3

    # ---------- IDEA 5 ----------
    P('IDEA 5  weekly-chart agreement before the signal')
    I5 = {}
    wk = {}
    for a in ASSETS:
        w = weekly(DAY[a], 1); ctw = E.rsi(w['close'], 14); emw = E.ema(ctw, 14)
        b8 = E.load(f'data/{a}_8D.csv'); ct8 = E.rsi(b8['close'], 14)
        wk[a] = (w, ctw, emw, b8, ct8)
    import bisect
    for var in ('5a weekly momentum rising', '5b weekly momentum above its signal line'):
        lifts = {}; good = 0; inside = {}; rows_out = []
        for a in ASSETS:
            w, ctw, emw, b8, ct8 = wk[a]; ends = w['end']
            pooled_W, pooled_A = [], []
            for tf in ('1D', '2D', '3D', '5D'):
                b, ct, kL, sb, rb = base[(a, tf)]
                for r in rb:
                    k = bisect.bisect_right(ends, r['d0']) - 1
                    if var.startswith('5a'):
                        r['wk'] = k >= 1 and ctw[k] is not None and ctw[k - 1] is not None and ctw[k] > ctw[k - 1]
                    else:
                        r['wk'] = k >= 0 and ctw[k] is not None and emw[k] is not None and ctw[k] > emw[k]
                    k8 = closed_index(b8['date'], r['d0'])
                    r['u8'] = k8 >= 1 and ct8[k8] is not None and ct8[k8 - 1] is not None and ct8[k8] > ct8[k8 - 1]
                W = [r for r in rb if r['wk']]; A = [r for r in rb if not r['wk']]
                sW, sA = st_(W), st_(A)
                pos = sW and sA and all(sW[p][0] is not None and sA[p][0] is not None and sW[p][1] >= 5 and sW[p][0] > sA[p][0] for p in ('16-21', '22-26'))
                good += bool(pos)
                P(f'  {var:<41} {a} {tf:<3} with {f(sW)}\n  {"":<41} {a} {tf:<3} w/o  {f(sA)}  ahead both periods: {"YES" if pos else "no"}')
                rows_out.append(dict(chart=f'{a} {tf}', with_=sW, without=sA, ahead_both=bool(pos)))
                pooled_W += W; pooled_A += A
            sW, sA = st_(pooled_W), st_(pooled_A); lifts[a] = sW['win'] - sA['win']
            allr = pooled_W + pooled_A
            for half in (True, False):
                X = [r for r in allr if r['u8'] == half]
                xw, xa = st_([r for r in X if r['wk']]), st_([r for r in X if not r['wk']])
                inside[(a, half)] = (xw['win'] - xa['win']) if xw and xa else None
                P(f'  {"":<41} {a} inside 8D {"rising" if half else "not rising"}: with {f(xw)} | w/o {f(xa)}')
            P(f'  {var:<41} {a} pooled lift {lifts[a]:+.0f}  with {f(sW)}')
        verdict = all(l >= 10 for l in lifts.values()) and good >= 6 and all(v is not None and v >= 5 for v in inside.values())
        P(f'  {var}: pooled lift ETH {lifts["ETH"]:+.0f} BTC {lifts["BTC"]:+.0f}; ahead in both periods on {good}/8 charts; '
          f'inside 8D halves {{{", ".join(f"{k[0]} {"up" if k[1] else "dn"}: {v:+.0f}" for k, v in inside.items() if v is not None)}}} -> {"PASS" if verdict else "FAIL"}\n')
        I5[var] = dict(charts=rows_out, pooled_lift=lifts, charts_ahead=good, inside_8d={f'{k[0]} {"8D up" if k[1] else "8D not up"}': v for k, v in inside.items()},
                       verdict='PASS' if verdict else 'FAIL')
    OUT['idea5'] = I5

    # ---------- IDEA 7 ----------
    P('IDEA 7  funding cost around resets (Binance USDT perpetual, 8-hour funding)')
    I7 = {}
    for a in ASSETS:
        col = f'{a}USDT_PERP.A'; fr = {}
        with open(f'data/derivs/{a}_funding_daily.csv') as fh:
            for r in csv.DictReader(fh):
                if r.get(col): fr[dt.date.fromisoformat(r['date'])] = float(r[col])
        at, hold = [], []
        for tf in TFS:
            for r in base[(a, tf)][4]:
                if r['d0'] in fr:
                    at.append(fr[r['d0']])
                    days = [fr.get(r['d0'] + dt.timedelta(days=k)) for k in range(1, 61)]
                    days = [x for x in days if x is not None]
                    if len(days) >= 55: hold.append(sum(days) / len(days) * 180)
        allv = list(fr.values())
        I7[a] = dict(per_interval_at_entry_median=st.median(at), per_interval_all_days_median=st.median(allv),
                     hold60_total_median=st.median(hold), hold60_total_p90=sorted(hold)[int(0.9 * len(hold))], n_entries=len(at),
                     since=str(min(fr)))
        P(f'  {a}: {len(at)} signal entries since {min(fr)}; funding per 8h interval at entry median {st.median(at):.4f}% '
          f'(all days {st.median(allv):.4f}%); a 60-day hold pays median {st.median(hold):.2f}% of position, 90th pct {I7[a]["hold60_total_p90"]:.2f}%')
    OUT['idea7'] = I7
    json.dump(OUT, open('analysis/joeideas.json', 'w'), default=str, indent=1)


if __name__ == '__main__':
    main()
