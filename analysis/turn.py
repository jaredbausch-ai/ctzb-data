"""Is the selling over? Telling a real turn from a false one at the low.
DECLARED 10 Nov 2026, before running. Jared: "there just has to be a way to
figure out that the selling's over and there's a new leg starting ... the
market has to leave some sort of clue." The open problem CONTEXT has carried
since Hurst closed: weeding out losing clusters.

POPULATION
  Every CTZB signal on ETH and BTC 1D 2D 3D 5D, UNGATED (big lows often come
  with the regime off), entry = close of the confirmation bar (ei = ti + 3),
  dated the day that bar closes. 2016 on, full 120-day windows only.
  The regime-gated subset is reported beside it, not judged separately.

OUTCOME -- TURN (the selling ended and a new leg started)
  The trough bar's low is never undercut by a daily low in the 90 days after
  entry, AND the daily high reaches +40% (ETH) / +30% (BTC) above the entry
  within 120 days. Everything else is a FALSE turn.

WHEN IT IS JUDGED -- check day k = 0 (entry), 5 and 10 days after entry.
  At day k only signals still ALIVE are scored: trough low not yet undercut
  and target not yet reached by the end of day k. Reads use only what was
  known at the end of day d0 + k.

READS (continuous; each tested as its top third and its bottom third, cut
points from the asset's 2016-21 signals at that check day)
  Price, own asset (1D candles):
    DD365   close vs the 365-day high          DUR     days since the 90-day high
    VOLR    30-day / 180-day realised vol      SMA200  close vs its 200-day average
    VOLX    day volume / 30-day median volume
    CT1D CT2D CT3D CT5D CT8D   CT RSI of each chart at its last closed bar
    CT8CHG  8D CT change on its last bar       B40     days 1D CT < 40 in the last 30
    ODD365  the OTHER asset's DD365            RATIOCT ETH/BTC ratio daily CT RSI
  Positioning:
    F7      funding, 7-day mean                F7M90   F7 minus its 90-day median
    LS7     long/short ratio, 7-day mean       PCRPCT  put/call 7-day mean, 100-day pct
  On-chain and flows (Coin Metrics, read with a 1-day lag):
    NET7    exchange net inflow over 7 days / exchange supply
    NET30   the same over 30 days              EXS30   exchange supply 30-day % change
    MVRV    market / realised value            MVRV30  MVRV change over 30 days
    ADR     active addresses, 30-day / 180-day mean
    STAB30  stablecoin supply 30-day % change  PREM7   Coinbase premium, 7-day mean
  USDT dominance:
    U8CT    USDT.D 8D CT      U2GAP  USDT.D 2D CT minus Signal    U2HI  USDT.D 2D vs its 1y high
  Signal's own (not date-shiftable):
    GAP     the chart's CT minus Signal at entry    CLUST   signals on the same chart in the prior 60 days
    LL      trough low vs the previous signal's trough low, same chart
    CTT     CT at the trough
  33 reads x 2 tails x 3 check days x 2 assets = 396 configurations.
  (Open interest is excluded: it starts Sep 2022, so it has no first period.)

RULES
  STEP 1  TURN rate, flag on minus off: >= +10 points in BOTH periods (a
          SELECTOR) or <= -10 in both (a WARNING, marks false turns). Each side
          n >= 15 in each period.
  STEP 2  Same sign on >= 2/3 of charts with n >= 5 per side, and in >= 2/3 of
          years with n >= 3 per side.
  STEP 3  PLACEBO. (a) The 29 dated reads re-run 20 times with every read date
          shifted 180-1,460 days; the real count of step 1-2 passes among those
          reads must beat the shifted 95th percentile, or they are chance.
          (b) Each survivor's flag shuffled within year 200 times; its real gap
          must beat the shuffled 95th percentile.
  STEP 4  OVERLAP with what we already know. Day 0: inside each half of
          GAP > 5 and of CT at the trough < 40. Days 5 and 10: inside each half
          of "price above entry at the check". If the gap shrinks under 3 points
          in either half, it is the known read counted twice: dropped.
  STEP 5  ETH and BTC are one sample for date-anchored reads.
  A survivor is a candidate for the in-trade reads, never a rule, without a
  forward period.

ENTRY QUALITY ONLY. No exit in the data, so no strategy return or track record.
Computed signals, never fills.
  python3 -I analysis/turn.py -> analysis/RESULTS_turn.txt, turn.json
"""
import sys, os, csv, json, math, random, bisect, datetime as dt, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E, regimes as R
from tagstats import bucket_end
from sweep import closed_index
import pcrtest as PT
from usdtd_grid import U

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)

SPLIT = dt.date(2022, 1, 1); START = dt.date(2016, 1, 1)
TFS = ['1D', '2D', '3D', '5D']; CTF = ['1D', '2D', '3D', '5D', '8D']
TGT = {'ETH': 0.40, 'BTC': 0.30}
GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
DAYS = (0, 5, 10)
SIGREADS = ['GAP', 'CLUST', 'LL', 'CTT']
random.seed(20261110)


def dseries(path, key, val, conv=float):
    out = {}
    for r in csv.DictReader(open(path)):
        v = r.get(val)
        if v in ('', None): continue
        try: out[dt.date.fromisoformat(r[key])] = conv(v)
        except ValueError: pass
    return out


def asof(series, days_sorted, d):
    j = bisect.bisect_right(days_sorted, d) - 1
    return series[days_sorted[j]] if j >= 0 else None


def panel(a, other):
    """date -> dict of the 29 dated reads for asset a, known at the end of that date"""
    day = E.load(f'data/{a}_1D.csv'); od = E.load(f'data/{other}_1D.csv')
    vol = [float(r['volume']) if r.get('volume') not in ('', None) else None for r in csv.DictReader(open(f'data/{a}_1D.csv'))]
    dts = day['date']; c = day['close']; h = day['high']
    pos = {d: i for i, d in enumerate(dts)}
    ct1 = E.rsi(c, 14)
    charts = {}
    for tf in CTF:
        b = E.load(f'data/{a}_{tf}.csv'); charts[tf] = (b['date'], E.rsi(b['close'], 14))
    ocl = dict(zip(od['date'], od['close'])); oh = dict(zip(od['date'], od['high']))
    rd = [d for d in dts if d in ocl] if a == 'ETH' else [d for d in od['date'] if d in dict(zip(dts, c))]
    ecl = dict(zip(dts, c)) if a == 'ETH' else ocl; bcl = ocl if a == 'ETH' else dict(zip(dts, c))
    rr = [ecl[d] / bcl[d] for d in rd]; rct = dict(zip(rd, E.rsi(rr, 14)))
    lr = [None] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
    s200 = E.sma(c, 200)
    fund = dseries(f'data/derivs/{a}_funding_daily.csv', 'date', 'funding_mean'); fd = sorted(fund)
    ls = dseries(f'data/derivs/{a}_lsratio_daily.csv', 'date', 'ls_ratio_mean'); lsd = sorted(ls)
    pcr = PT.reads(PT.load_pcr(a))
    cm = list(csv.DictReader(open(f'data/onchain/{a}_cm_daily.csv')))
    cmd = {}
    for r in cm:
        try:
            cmd[dt.date.fromisoformat(r['date'])] = {k: (float(r[k]) if r[k] not in ('', None) else None)
                                                    for k in ('CapMVRVCur', 'AdrActCnt', 'SplyExNtv', 'FlowInExNtv', 'FlowOutExNtv')}
        except ValueError: pass
    stab = dseries('data/flows/stablecoin_supply_daily.csv', 'date', 'd30_pct')
    prem = dseries(f'data/flows/{a}_premium_daily.csv', 'date', 'premium_pct')
    u8, u2 = U('8D'), U('2D')
    oidx = {d: i for i, d in enumerate(od['date'])}
    out = {}
    for i, d in enumerate(dts):
        if d < dt.date(2015, 9, 1) or i < 365: continue
        r = {}
        r['DD365'] = c[i] / max(h[i - 364:i + 1]) - 1
        w = h[i - 89:i + 1]; r['DUR'] = 89 - max(range(90), key=lambda j: w[j])
        a30 = [x for x in lr[i - 29:i + 1] if x is not None]; a180 = [x for x in lr[i - 179:i + 1] if x is not None]
        r['VOLR'] = st.pstdev(a30) / st.pstdev(a180) if len(a180) > 100 and st.pstdev(a180) > 0 else None
        r['SMA200'] = c[i] / s200[i] - 1 if s200[i] else None
        vv = [x for x in vol[i - 29:i + 1] if x]
        r['VOLX'] = vol[i] / st.median(vv) if vol[i] and len(vv) > 20 else None
        for tf in CTF:
            ds, ct = charts[tf]; k = closed_index(ds, d)
            r[f'CT{tf}'] = ct[k] if 0 <= k < len(ct) else None
            if tf == '8D':
                r['CT8CHG'] = ct[k] - ct[k - 1] if k >= 1 and ct[k] is not None and ct[k - 1] is not None else None
        r['B40'] = sum(1 for x in ct1[i - 29:i + 1] if x is not None and x < 40)
        oi = oidx.get(d)
        r['ODD365'] = od['close'][oi] / max(od['high'][max(0, oi - 364):oi + 1]) - 1 if oi is not None and oi >= 364 else None
        r['RATIOCT'] = rct.get(d)
        if fd and d >= fd[0]:
            f7 = [fund.get(d - dt.timedelta(days=j)) for j in range(7)]; f90 = [fund.get(d - dt.timedelta(days=j)) for j in range(90)]
            f7 = [x for x in f7 if x is not None]; f90 = [x for x in f90 if x is not None]
            r['F7'] = st.mean(f7) if len(f7) >= 5 else None
            r['F7M90'] = r['F7'] - st.median(f90) if r['F7'] is not None and len(f90) >= 60 else None
        else: r['F7'] = r['F7M90'] = None
        l7 = [ls.get(d - dt.timedelta(days=j)) for j in range(7)]; l7 = [x for x in l7 if x is not None]
        r['LS7'] = st.mean(l7) if len(l7) >= 5 else None
        r['PCRPCT'] = pcr[d]['pct'] if d in pcr else None
        d1 = d - dt.timedelta(days=1)
        def cmv(dd, k):
            x = cmd.get(dd); return x[k] if x else None
        def net(n):
            s = 0
            for j in range(n):
                fi, fo = cmv(d1 - dt.timedelta(days=j), 'FlowInExNtv'), cmv(d1 - dt.timedelta(days=j), 'FlowOutExNtv')
                if fi is None or fo is None: return None
                s += fi - fo
            sx = cmv(d1, 'SplyExNtv'); return s / sx if sx else None
        r['NET7'] = net(7); r['NET30'] = net(30)
        s0, s30 = cmv(d1, 'SplyExNtv'), cmv(d1 - dt.timedelta(days=30), 'SplyExNtv')
        r['EXS30'] = s0 / s30 - 1 if s0 and s30 else None
        m0, m30 = cmv(d1, 'CapMVRVCur'), cmv(d1 - dt.timedelta(days=30), 'CapMVRVCur')
        r['MVRV'] = m0; r['MVRV30'] = m0 - m30 if m0 is not None and m30 is not None else None
        a30_ = [cmv(d1 - dt.timedelta(days=j), 'AdrActCnt') for j in range(30)]; a180_ = [cmv(d1 - dt.timedelta(days=j), 'AdrActCnt') for j in range(180)]
        a30_ = [x for x in a30_ if x]; a180_ = [x for x in a180_ if x]
        r['ADR'] = st.mean(a30_) / st.mean(a180_) if len(a30_) > 25 and len(a180_) > 150 else None
        r['STAB30'] = stab.get(d)
        p7 = [prem.get(d - dt.timedelta(days=j)) for j in range(7)]; p7 = [x for x in p7 if x is not None]
        r['PREM7'] = st.mean(p7) if len(p7) >= 5 else None
        x8 = u8.reads(d); x2 = u2.reads(d)
        k8 = u8.idx(d); k2 = u2.idx(d)
        r['U8CT'] = u8.ct[k8] if x8 is not None else None
        r['U2GAP'] = u2.ct[k2] - u2.sg[k2] if x2 is not None else None
        r['U2HI'] = u2.c[k2] / max(u2.c[max(0, k2 - u2.yb + 1):k2 + 1]) - 1 if x2 is not None else None
        out[d] = r
    return out


DATED = ['DD365', 'DUR', 'VOLR', 'SMA200', 'VOLX', 'CT1D', 'CT2D', 'CT3D', 'CT5D', 'CT8D', 'CT8CHG', 'B40', 'ODD365',
         'RATIOCT', 'F7', 'F7M90', 'LS7', 'PCRPCT', 'NET7', 'NET30', 'EXS30', 'MVRV', 'MVRV30', 'ADR', 'STAB30', 'PREM7',
         'U8CT', 'U2GAP', 'U2HI']


def signals():
    out = []
    for a in ('ETH', 'BTC'):
        day = E.load(f'data/{a}_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}; last = day['date'][-1]
        for tf in TFS:
            sig, b = E.signals(f'data/{a}_{tf}.csv', regime=lambda d: True)
            ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
            hist = []
            for s in sig:
                d0 = bucket_end(b['date'], s['ei'])
                if d0 is None or d0 < START or (last - d0).days < 121 or d0 not in pos: continue
                i = pos[d0]; c0 = s['entry']; tl = b['low'][s['ti']]
                lows = day['low'][i + 1:i + 91]; highs = day['high'][i + 1:i + 121]
                held = min(lows) >= tl
                hit = [k for k, x in enumerate(highs, 1) if x >= c0 * (1 + TGT[a])]
                turn = held and bool(hit)
                und = [k for k, x in enumerate(day['low'][i + 1:i + 121], 1) if x < tl]
                first_hit = hit[0] if hit else 999; first_und = und[0] if und else 999
                prevs = [x for x in hist if 0 < (d0 - x[0]).days <= 60]
                prev_tl = hist[-1][1] if hist else None
                g = ct[s['ei']] - em[s['ei']] if ct[s['ei']] is not None and em[s['ei']] is not None else None
                sr = dict(GAP=g, CLUST=len(prevs), LL=(tl / prev_tl - 1) if prev_tl else None, CTT=ct[s['ti']])
                closes = {k: day['close'][i + k] for k in DAYS if i + k < len(day['close'])}
                out.append(dict(a=a, ch=f'{a} {tf}', d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1, turn=turn,
                                gate=GATE(d0), hit=first_hit, und=first_und, sr=sr, c0=c0,
                                green={k: closes.get(k, 0) > c0 for k in DAYS}))
                hist.append((d0, tl))
    return out


def alive(s, k):
    return s['hit'] > k and s['und'] > k


def flags(sigs, pan, k, shift=0, reads=None):
    """returns {(read, tail, asset): [(signal, flag)]} for check day k; cut points from 2016-21"""
    reads = reads or DATED + SIGREADS
    vals = {}
    for s in sigs:
        if not alive(s, k): continue
        pr = pan[s['a']].get(s['d0'] + dt.timedelta(days=k - shift))
        for nm in reads:
            v = s['sr'][nm] if nm in SIGREADS else (pr or {}).get(nm)
            if v is None: continue
            vals.setdefault((nm, s['a']), []).append((s, v))
    out = {}
    for (nm, a), pv in vals.items():
        disc = sorted(v for s, v in pv if s['per'] == 0)
        if len(disc) < 30: continue
        lo, hi = disc[len(disc) // 3], disc[2 * len(disc) // 3]
        out[(nm, 'top', a)] = [(s, v >= hi) for s, v in pv]
        out[(nm, 'bot', a)] = [(s, v <= lo) for s, v in pv]
    return out


def tr(g):
    return 100 * sum(s['turn'] for s in g) / len(g) if g else None


def judge(pairs):
    st_ = []
    for p in (0, 1):
        on = [s for s, f in pairs if f and s['per'] == p]; off = [s for s, f in pairs if not f and s['per'] == p]
        if len(on) < 15 or len(off) < 15: return None, None
        st_.append((len(on), len(off), tr(on), tr(off)))
    gaps = [a - b for _, _, a, b in st_]
    d = 'SEL' if all(x >= 10 for x in gaps) else 'WARN' if all(x <= -10 for x in gaps) else None
    if not d: return None, st_
    sign = 1 if d == 'SEL' else -1
    for key, nmin in (('ch', 5), ('yr', 3)):
        grp = {}
        for s, f in pairs: grp.setdefault(s[key], []).append((s, f))
        ok = tot = 0
        for g in grp.values():
            on = [s for s, f in g if f]; off = [s for s, f in g if not f]
            if len(on) < nmin or len(off) < nmin: continue
            tot += 1; ok += sign * (tr(on) - tr(off)) > 0
        if tot == 0 or ok / tot < 2 / 3: return None, st_
    return d, st_


def grid(sigs, pan, shift=0, reads=None):
    res = {}
    for k in DAYS:
        for key, pairs in flags(sigs, pan, k, shift, reads).items():
            d, s = judge(pairs)
            res[(k,) + key] = (d, s, pairs)
    return res


def shuffle_ok(pairs, d, n=200):
    def gap(pp):
        on = [s for s, f in pp if f]; off = [s for s, f in pp if not f]
        return (tr(on) - tr(off)) * (1 if d == 'SEL' else -1) if on and off else 0
    real = gap(pairs); byy = {}
    for s, f in pairs: byy.setdefault(s['yr'], []).append((s, f))
    sims = []
    for _ in range(n):
        pp = []
        for g in byy.values():
            fl = [f for _, f in g]; random.shuffle(fl); pp += [(g[i][0], fl[i]) for i in range(len(g))]
        sims.append(gap(pp))
    sims.sort(); return real, sims[int(0.95 * n)]


def overlap(pairs, d, k, pan):
    sign = 1 if d == 'SEL' else -1
    halves = []
    if k == 0:
        halves += [('GAP>5', lambda s: (s['sr']['GAP'] or -99) > 5), ('CTT<40', lambda s: (s['sr']['CTT'] or 99) < 40)]
    else:
        halves += [(f'green d{k}', lambda s: s['green'][k])]
    for nm, fn in halves:
        for half in (True, False):
            g = [(s, f) for s, f in pairs if fn(s) == half]
            on = [s for s, f in g if f]; off = [s for s, f in g if not f]
            if len(on) < 5 or len(off) < 5: continue
            if sign * (tr(on) - tr(off)) < 3: return f'{nm}={"yes" if half else "no"}'
    return None


def main():
    sigs = signals()
    pan = {'ETH': panel('ETH', 'BTC'), 'BTC': panel('BTC', 'ETH')}
    P('IS THE SELLING OVER? -- declared 10 Nov 2026 (analysis/turn.py docstring). Ungated CTZB signals 1D-5D.')
    for a in ('ETH', 'BTC'):
        for p, lab in ((0, '2016-21'), (1, '2022 on')):
            g = [s for s in sigs if s['a'] == a and s['per'] == p]; gg = [s for s in g if s['gate']]
            P(f'  {a} {lab}: {len(g)} signals, TURN {tr(g):.0f}% | regime-gated only: {len(gg)}, TURN {tr(gg):.0f}%')
        for k in DAYS:
            al = [s for s in sigs if s['a'] == a and alive(s, k)]
            P(f'    alive on day {k:2d}: {len(al)}, TURN {tr(al):.0f}%')
    res = grid(sigs, pan)
    tested = sum(1 for v in res.values() if v[1] is not None)
    passed = {k: v for k, v in res.items() if v[0]}
    dated_pass = sum(1 for k in passed if k[1] in DATED)
    P(f'\n{len(res)} configurations built, {tested} with n >= 15 per side in both periods; passed steps 1-2: {len(passed)} '
      f'({dated_pass} dated reads, {len(passed) - dated_pass} signal-own reads)')
    sh = []
    for i in range(20):
        off = random.randint(180, 1460) * random.choice((1, -1))
        r2 = grid(sigs, pan, shift=off, reads=DATED)
        sh.append(sum(1 for v in r2.values() if v[0]))
    sh.sort(); p95 = sh[int(0.95 * len(sh))]
    beats = dated_pass > p95
    P(f'PLACEBO (dated reads, 20 date shifts 180-1,460 days): passes {sh}; 95th pct {p95}; real {dated_pass} -> '
      f'{"BEATS the placebo" if beats else "does NOT beat the placebo"}')
    P('\nEvery config passing steps 1-2 (TURN % on / off, by period):')
    P('  day read     tail asset dir  | 2016-21 n on/off  on%  off% | 2022 on n on/off  on%  off% | shuffle real/p95 | overlap')
    surv = []
    for key in sorted(passed, key=lambda x: (x[3], x[0], x[1])):
        k, nm, tail, a = key; d, s, pairs = passed[key]
        rv, p = shuffle_ok(pairs, d); ov = overlap(pairs, d, k, pan)
        dated_ok = beats if nm in DATED else True
        ok = rv > p and not ov and dated_ok
        if ok: surv.append(key)
        on = [x for x, f in pairs if f]; turns = sum(x['turn'] for x, f in pairs)
        prec = tr(on); rec = 100 * sum(x['turn'] for x in on) / turns if turns else 0
        P(f'  d{k:<2} {nm:<8} {tail} {a} {d:<4} | {s[0][0]:4d}/{s[0][1]:<4d} {s[0][2]:4.0f} {s[0][3]:4.0f} | '
          f'{s[1][0]:4d}/{s[1][1]:<4d} {s[1][2]:4.0f} {s[1][3]:4.0f} | {rv:+5.1f}/{p:+5.1f} | {ov or "-"}'
          f'{"   <- SURVIVES" if ok else ""}   [flagged: {prec:.0f}% turns, catches {rec:.0f}% of turns]')
    P(f'\nsurvivors: {len(surv)}')
    if not beats:
        P('  Step 3(a) failed: the dated reads pass no more often than with their dates shifted, so none of them counts.')
    P('\nENTRY QUALITY ONLY. No exit in the data, so no strategy return or track record. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_turn.txt'), 'w').write('\n'.join(L) + '\n')
    json.dump(dict(passed=[list(map(str, k)) + [passed[k][0]] for k in passed], survivors=[list(map(str, k)) for k in surv],
                   shifts=sh, real_dated=dated_pass), open(os.path.join(HERE, 'turn.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
