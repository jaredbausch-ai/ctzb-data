"""USDT dominance (CRYPTOCAP:USDT.D) through the CTZB system: the full grid.
DECLARED 10 Nov 2026, before running. Requested by Jared: "Tether dominance ...
I feel that there has to be an edge somewhere in here ... try 1,000 different
ways of putting this through our system."

Earlier work: usdtd_div.py / usdtd_div2.py (28 Oct) tested one 2D pattern
(Stoch divergence + CT rejected at 50) as context only. Nothing broader has run.

DATA
  data/tradingview/usdtd/USDT.D_{1D,2D,3D,5D,8D,10D}.csv, TradingView exports,
  10 Nov 2026. 1D starts 2018-11-15 (TradingView bar limit); the rest 2015-03.
  CT RSI, Signal, %K, %D recomputed here with engine.py from the closes.
  A USDT.D bar is read only once it has CLOSED by the end of the entry day
  (sweep.closed_index). The last bar of each file is never read.

POPULATION (Family A)
  datasets/ledger.csv: regime-gated ETH and BTC signals on 1D/2D/3D/5D, entry =
  close of the confirmation bar (ei = ti + 3), dated the day that bar closes.
  Only full 60-day windows (entry on or before 2026-09-10).
  win = reached +20% within 60 days; t30 = touched -30% within 60 days.
  Periods: to 2021 / 2022 on. For 1D USDT.D reads "to 2021" means 2019-2021.

FAMILY A -- USDT.D state at the signal's entry, as a lens. 75 reads x 6 USDT.D
timeframes x 2 assets = 900, plus 12 multi-timeframe reads x 2 assets = 24.
  CTGE x     USDT.D CT >= x, x in 50 55 60 65 70                          5
  CTLE x     USDT.D CT <= x, x in 30 35 40 45 50                          5
  GAPDN g    USDT.D CT below its Signal by more than g, g in 0 2 5 8 10   5
  GAPUP g    USDT.D CT above its Signal by more than g, same g            5
  CTFALL n   USDT.D CT lower than n bars ago, n in 1 2 3 5                4
  KGE80 KGE60 KLE20 KLE40   USDT.D %K level                               4
  PXDN n     USDT.D close below its close n bars ago, n in 1 3 5 10 20    5
  PXDROP p   USDT.D close down p% or more over 5 bars, p in 2 5 10        3
  BELOW20 BELOW50 ABOVE20 ABOVE50   close vs its 20 / 50-bar average      4
  PH W L     a USDT.D CT pivot high (3,3) with CT >= L, its confirmation
             bar closed within W days before entry; W 10 20 30, L 50 60 70 9
  PHDIV W    pivot high whose CT and %K moved opposite ways vs the previous
             pivot high (the mirror of the CTZB diamond), W 10 20 30      3
  PHBELOW W  pivot high (any level) within W days AND CT now below Signal 3
  NEARHI x   close within x% of its 365-day high, x 5 10 20               3
  FARHI x    close x% or more below its 365-day high, x 20 30             2
  USIG W     a CTZB signal (pivot LOW, ungated) on USDT.D itself confirmed
             within W days, W 10 20 -- crypto-bearish by construction     2
  USIGD W    the same, with a diamond, W 10 20                            2
  CTX50 n    USDT.D CT crossed down through 50 within the last n bars,
             n 1 3 5                                                      3
  SLOPE s    USDT.D CT fell s points or more over 3 bars, s 3 5 10        3
  OFFPEAK d  USDT.D CT d points or more under its 20-bar max, d 10 15 20  3
  KXD n      USDT.D %K crossed below %D within the last n bars, n 1 3     2
                                                                   total 75
  MULTI (6 timeframes): CT below Signal on >= 3 4 5 6; CT >= 60 on >= 2 3 4;
  CT falling (1 bar) on >= 4 5 6; a pivot high within 20 days on >= 2 3.  12

RULES, Family A (per asset)
  STEP 1  SELECTOR: in BOTH periods win(on) - win(off) >= +5 and
          t30(on) - t30(off) <= +3.  CAUTION: in BOTH periods
          win(on) - win(off) <= -5 and t30 not better by more than 3, OR
          t30(on) - t30(off) >= +5 and win not better by more than 3.
          Each side n >= 15 in each period.
  STEP 2  CHART: the step-1 direction holds on >= 2/3 of the asset's charts
          where each side has n >= 5.
  STEP 3  YEAR: the step-1 direction holds in >= 2/3 of years where each side
          has n >= 3.
  STEP 4  PLACEBO, two kinds.
          (a) Whole grid: the full Family A grid re-run 20 times with the
              USDT.D dates shifted by a random 180-1,460 days (either way).
              The real grid's count of step 1-3 passes must beat the shifted
              95th percentile, or the passes are what 924 tries produce by
              chance.
          (b) Per survivor: its flag shuffled within year 200 times; the real
              lift (or cut, for a caution) must beat the shuffled 95th pct.
  STEP 5  OVERLAP: inside each half of every live lens of the asset (ETH: GAP
          HIGH AGREE BTC3 FUND FCOOL; BTC: GAP UP8 BTCX FASTCT) and inside
          bucket A vs not-A, if both its win lift and t30 cut are under 1
          point in either half, it is that read counted twice: dropped.
  STEP 6  USDT.D reads are date-anchored, so ETH and BTC are ONE sample: a
          read passing on both assets is one finding, not two.
  A survivor is a candidate for PRETRADE "Promising", never Tier 1 or a lens,
  without a forward period.

FAMILY B -- USDT.D's own turn as a standalone entry. Mirror of CTZB: a pivot
HIGH of USDT.D CT (3,3), confirmed 3 bars later; entry = the asset's daily close
on the day the USDT.D confirmation bar closes.
  6 timeframes x level (any, >= 60, >= 65, >= 70) x (any, mirror diamond)
  x (regime gate on, all days) x 2 assets = 192.
  Baseline: every day in the same set (gate on / all) with a full 60-day window.
RULES, Family B
  PASS: win lift >= +10 over the baseline and t30 not more than 3 worse, in
  BOTH periods, n >= 15 per period; ahead in >= 2/3 of years with n >= 2.
  Placebo: the same whole-grid date shift as 4(a), 20 shifts.
  Reported beside the asset's own regime-gated CTZB signals' win rate.

Total configurations: 900 + 24 + 192 = 1,116.

ENTRY QUALITY ONLY. No exit in the data, so no strategy return or track record.
Computed signals, never fills.
  python3 -I analysis/usdtd_grid.py -> analysis/RESULTS_usdtd_grid.txt, usdtd_grid.json
"""
import sys, os, csv, json, random, bisect, datetime as dt, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
os.chdir(ROOT)
import engine as E, regimes as R
from tagstats import bucket_end
from sweep import closed_index

L = []
def P(*x):
    s = ' '.join(str(i) for i in x); L.append(s); print(s)

SPLIT = dt.date(2022, 1, 1)
LAST_FULL = dt.date(2026, 9, 10)
UTFS = ['1D', '2D', '3D', '5D', '8D', '10D']
LIVE = {'ETH': ['GAP', 'HIGH', 'AGREE', 'BTC3', 'FUND', 'FCOOL'], 'BTC': ['GAP', 'UP8', 'BTCX', 'FASTCT']}
GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
random.seed(20261110)


# ---------------------------------------------------------------- USDT.D reads
class U:
    def __init__(self, tf):
        b = E.load(f'data/tradingview/usdtd/USDT.D_{tf}.csv')
        self.tf = tf; self.b = b; self.d = b['date']; c = b['close']; self.c = c
        self.ct = E.rsi(c, 14); self.sg = E.ema(self.ct, 14)
        k = E.sma(E.stoch_of(self.ct, 14), 3); self.k = k; self.kd = E.sma(k, 3)
        self.s20 = E.sma(c, 20); self.s50 = E.sma(c, 50)
        L_ = int(tf[:-1]); self.yb = max(2, round(365 / L_))
        self.ends = [self.d[j + 1] - dt.timedelta(days=1) for j in range(len(self.d) - 1)]
        # pivot highs of CT (3,3), with the mirror-diamond flag
        self.ph = []   # (confirm close date, ct at pivot, mirror diamond)
        prev = None
        for t in range(3, len(c) - 3):
            v = self.ct[t]
            w = self.ct[t - 3:t + 4]
            if v is None or any(x is None for x in w): continue
            if any(self.ct[j] >= v for j in range(t - 3, t)): continue
            if any(self.ct[j] >= v for j in range(t + 1, t + 4)): continue
            if self.k[t] is None: continue
            dis = False
            if prev is not None:
                dct, dk = v - prev[0], self.k[t] - prev[1]
                dis = (dct > 0 and dk < 0) or (dct < 0 and dk > 0)
            prev = (v, self.k[t])
            ce = bucket_end(self.d, t + 3)
            if ce is not None:
                self.ph.append((ce, v, dis))
        self.phd = [x[0] for x in self.ph]
        # CTZB signals on USDT.D itself (pivot LOWS, ungated)
        sig, bb = E.signals(f'data/tradingview/usdtd/USDT.D_{tf}.csv', regime=lambda d: True)
        self.us = [(bucket_end(bb['date'], s['ei']), s['dis']) for s in sig]
        self.us = [x for x in self.us if x[0] is not None]

    def idx(self, day):
        return bisect.bisect_right(self.ends, day) - 1

    def ph_within(self, day, W, lvl=None, div=False):
        lo = bisect.bisect_left(self.phd, day - dt.timedelta(days=W))
        hi = bisect.bisect_right(self.phd, day)
        for j in range(lo, hi):
            ce, v, dis = self.ph[j]
            if lvl is not None and v < lvl: continue
            if div and not dis: continue
            return True
        return False

    def us_within(self, day, W, div=False):
        return any(0 <= (day - ce).days <= W and (dis or not div) for ce, dis in self.us)

    def reads(self, day):
        """dict name -> bool for this USDT.D timeframe at the end of `day`, or None"""
        if day > self.ends[-1]: return None   # fix 10 Nov (after first run): no closed bar beyond the data
        k = self.idx(day)
        if k < 60 or k >= len(self.c): return None
        ct, sg, K, KD, c = self.ct, self.sg, self.k, self.kd, self.c
        if None in (ct[k], sg[k], K[k], KD[k], ct[k - 5], self.s50[k]): return None
        r = {}
        for x in (50, 55, 60, 65, 70): r[f'CTGE{x}'] = ct[k] >= x
        for x in (30, 35, 40, 45, 50): r[f'CTLE{x}'] = ct[k] <= x
        for g in (0, 2, 5, 8, 10):
            r[f'GAPDN{g}'] = sg[k] - ct[k] > g
            r[f'GAPUP{g}'] = ct[k] - sg[k] > g
        for n in (1, 2, 3, 5): r[f'CTFALL{n}'] = ct[k] < ct[k - n]
        r['KGE80'] = K[k] >= 80; r['KGE60'] = K[k] >= 60; r['KLE20'] = K[k] <= 20; r['KLE40'] = K[k] <= 40
        for n in (1, 3, 5, 10, 20): r[f'PXDN{n}'] = c[k] < c[k - n]
        for p in (2, 5, 10): r[f'PXDROP{p}'] = c[k] / c[k - 5] - 1 <= -p / 100
        r['BELOW20'] = c[k] < self.s20[k]; r['BELOW50'] = c[k] < self.s50[k]
        r['ABOVE20'] = c[k] > self.s20[k]; r['ABOVE50'] = c[k] > self.s50[k]
        for W in (10, 20, 30):
            for lv in (50, 60, 70): r[f'PH{W}_{lv}'] = self.ph_within(day, W, lv)
            r[f'PHDIV{W}'] = self.ph_within(day, W, div=True)
            r[f'PHBELOW{W}'] = self.ph_within(day, W) and ct[k] < sg[k]
        hi = max(c[max(0, k - self.yb + 1):k + 1])
        for x in (5, 10, 20): r[f'NEARHI{x}'] = c[k] >= hi * (1 - x / 100)
        for x in (20, 30): r[f'FARHI{x}'] = c[k] <= hi * (1 - x / 100)
        for W in (10, 20):
            r[f'USIG{W}'] = self.us_within(day, W)
            r[f'USIGD{W}'] = self.us_within(day, W, div=True)
        for n in (1, 3, 5):
            r[f'CTX50_{n}'] = any(ct[j - 1] is not None and ct[j - 1] >= 50 > ct[j] for j in range(k - n + 1, k + 1))
        for s in (3, 5, 10): r[f'SLOPE{s}'] = ct[k] - ct[k - 3] <= -s
        mx = max(x for x in ct[k - 19:k + 1] if x is not None)
        for d in (10, 15, 20): r[f'OFFPEAK{d}'] = mx - ct[k] >= d
        for n in (1, 3):
            r[f'KXD{n}'] = any(K[j - 1] is not None and KD[j - 1] is not None and K[j - 1] >= KD[j - 1] and K[j] < KD[j]
                               for j in range(k - n + 1, k + 1))
        return r


def multi(us, day):
    rs = {tf: us[tf].reads(day) for tf in UTFS}
    if any(v is None for v in rs.values()): return None
    below = sum(rs[t]['GAPDN0'] for t in UTFS)
    hi60 = sum(rs[t]['CTGE60'] for t in UTFS)
    fall = sum(rs[t]['CTFALL1'] for t in UTFS)
    ph = sum(us[t].ph_within(day, 20) for t in UTFS)
    r = {}
    for n in (3, 4, 5, 6): r[f'M_BELOW{n}'] = below >= n
    for n in (2, 3, 4): r[f'M_CT60_{n}'] = hi60 >= n
    for n in (4, 5, 6): r[f'M_FALL{n}'] = fall >= n
    for n in (2, 3): r[f'M_PH20_{n}'] = ph >= n
    return r


# ---------------------------------------------------------------- population
def ledger():
    out = []
    for x in csv.DictReader(open('datasets/ledger.csv')):
        d0 = dt.date.fromisoformat(x['entry'])
        if d0 > LAST_FULL: continue
        lens = set(t.strip() for t in x['lenses'].split('+')) - {'-', ''}
        out.append(dict(a=x['asset'], ch=x['chart'], d0=d0, yr=d0.year, per=0 if d0 < SPLIT else 1,
                        win=x['reached20'] == 'yes', t30=x['touched30'] == 'yes', s10=x['surv10'] == 'yes',
                        lens=lens, bkA=x['tags'][:1] == 'A'))
    return out


def rate(g, key):
    return 100 * sum(r[key] for r in g) / len(g) if g else None


def grid_A(sigs, us, shift=0):
    """name -> {asset: list of (signal, flag)}; shift moves the USDT.D read date back by `shift` days"""
    res = {}
    for s in sigs:
        day = s['d0'] - dt.timedelta(days=shift)
        for tf in UTFS:
            r = us[tf].reads(day)
            if r is None: continue
            for nm, v in r.items():
                res.setdefault(f'{tf} {nm}', {}).setdefault(s['a'], []).append((s, v))
        m = multi(us, day)
        if m:
            for nm, v in m.items():
                res.setdefault(nm, {}).setdefault(s['a'], []).append((s, v))
    return res


def step1(pairs):
    """returns (direction or None, per-period stats)"""
    st_ = []
    for p in (0, 1):
        on = [s for s, v in pairs if v and s['per'] == p]; off = [s for s, v in pairs if not v and s['per'] == p]
        if len(on) < 15 or len(off) < 15: return None, None
        st_.append((len(on), len(off), rate(on, 'win') - rate(off, 'win'), rate(on, 't30') - rate(off, 't30')))
    sel = all(w >= 5 and t <= 3 for _, _, w, t in st_)
    cau = all((w <= -5 and t >= -3) or (t >= 5 and w <= 3) for _, _, w, t in st_)
    return ('SEL' if sel else 'CAU' if cau else None), st_


def agrees(direction, w, t):
    return (w > 0 and t <= 3) if direction == 'SEL' else (w < 0 or t > 0)


def split_check(pairs, direction, key, nmin):
    groups = {}
    for s, v in pairs: groups.setdefault(s[key], []).append((s, v))
    ok = tot = 0
    for g in groups.values():
        on = [s for s, v in g if v]; off = [s for s, v in g if not v]
        if len(on) < nmin or len(off) < nmin: continue
        tot += 1
        ok += agrees(direction, rate(on, 'win') - rate(off, 'win'), rate(on, 't30') - rate(off, 't30'))
    return ok, tot


def passes_A(res):
    out = []
    for nm, by in res.items():
        for a, pairs in by.items():
            d, s1 = step1(pairs)
            if not d: continue
            c_ok, c_tot = split_check(pairs, d, 'ch', 5)
            y_ok, y_tot = split_check(pairs, d, 'yr', 3)
            if c_tot == 0 or y_tot == 0: continue
            if c_ok / c_tot < 2 / 3 or y_ok / y_tot < 2 / 3: continue
            out.append(dict(nm=nm, a=a, d=d, s1=s1, ch=(c_ok, c_tot), yr=(y_ok, y_tot)))
    return out


def shuffle_p95(pairs, direction, n=200):
    """flag reshuffled within year; returns (real, p95) of the qualifying measure, pooled across periods"""
    def meas(pp):
        on = [s for s, v in pp if v]; off = [s for s, v in pp if not v]
        if not on or not off: return 0
        w = rate(on, 'win') - rate(off, 'win'); t = rate(on, 't30') - rate(off, 't30')
        return w if direction == 'SEL' else max(-w, t)
    real = meas(pairs)
    byy = {}
    for s, v in pairs: byy.setdefault(s['yr'], []).append((s, v))
    sims = []
    for _ in range(n):
        pp = []
        for g in byy.values():
            fl = [v for _, v in g]; random.shuffle(fl)
            pp += [(g[i][0], fl[i]) for i in range(len(g))]
        sims.append(meas(pp))
    sims.sort()
    return real, sims[int(0.95 * n)]


def overlap(pairs, a, direction):
    """lenses inside whose either half the read adds < 1 pt on both win and t30"""
    killers = []
    for ln in LIVE[a] + ['BUCKET_A']:
        for half in (True, False):
            g = [(s, v) for s, v in pairs if ((s['bkA'] if ln == 'BUCKET_A' else ln in s['lens']) == half)]
            on = [s for s, v in g if v]; off = [s for s, v in g if not v]
            if len(on) < 5 or len(off) < 5: continue
            w = rate(on, 'win') - rate(off, 'win'); t = rate(off, 't30') - rate(on, 't30')
            if direction == 'CAU': w, t = -w, -t
            if w < 1 and t < 1:
                killers.append(f'{ln}={"on" if half else "off"}'); break
    return killers


# ---------------------------------------------------------------- Family B
def family_B(us, day, shift=0):
    out = []
    for a in ('ETH', 'BTC'):
        dy = day[a]; pos = {d: i for i, d in enumerate(dy['date'])}
        def outcome(d0):
            i = pos.get(d0)
            if i is None or i + 60 >= len(dy['date']) or d0 > LAST_FULL: return None
            c0 = dy['close'][i]
            hi = max(dy['high'][i + 1:i + 61]); lo = min(dy['low'][i + 1:i + 61])
            return (hi / c0 - 1) * 100 >= 20, (lo / c0 - 1) * 100 <= -30
        base = {}
        for gm in ('gate', 'all'):
            rows = []
            for d0 in dy['date']:
                if d0 < dt.date(2016, 1, 1): continue
                if gm == 'gate' and not GATE(d0): continue
                o = outcome(d0)
                if o: rows.append(dict(d0=d0, per=0 if d0 < SPLIT else 1, yr=d0.year, win=o[0], t30=o[1]))
            base[gm] = rows
        for tf in UTFS:
            for lv in (None, 60, 65, 70):
                for dv in (False, True):
                    for gm in ('gate', 'all'):
                        ev = []
                        for ce, v, dis in us[tf].ph:
                            if lv is not None and v < lv: continue
                            if dv and not dis: continue
                            d0 = ce + dt.timedelta(days=shift)
                            if d0 < dt.date(2016, 1, 1): continue
                            if gm == 'gate' and not GATE(d0): continue
                            o = outcome(d0)
                            if o: ev.append(dict(d0=d0, per=0 if d0 < SPLIT else 1, yr=d0.year, win=o[0], t30=o[1]))
                        nm = f'B {a} {tf} lvl{lv or "any"} {"div" if dv else "any"} {gm}'
                        out.append((nm, a, gm, ev, base[gm]))
    return out


def judge_B(ev, base):
    st_ = []
    for p in (0, 1):
        e = [x for x in ev if x['per'] == p]; b = [x for x in base if x['per'] == p]
        if len(e) < 15: return False, None
        st_.append((len(e), rate(e, 'win') - rate(b, 'win'), rate(e, 't30') - rate(b, 't30')))
    if not all(w >= 10 and t <= 3 for _, w, t in st_): return False, st_
    ok = tot = 0
    for y in sorted(set(x['yr'] for x in ev)):
        e = [x for x in ev if x['yr'] == y]; b = [x for x in base if x['yr'] == y]
        if len(e) < 2 or not b: continue
        tot += 1; ok += rate(e, 'win') > rate(b, 'win')
    return tot > 0 and ok / tot >= 2 / 3, st_


def fmt(v):
    return '   -' if v is None else f'{v:+5.1f}'


def main():
    us = {tf: U(tf) for tf in UTFS}
    sigs = ledger()
    day = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
    P('USDT.D THROUGH CTZB -- full grid, declared 10 Nov 2026 (analysis/usdtd_grid.py docstring)')
    P(f'signals with a full 60-day window: {len(sigs)} '
      f'(ETH {sum(s["a"]=="ETH" for s in sigs)}, BTC {sum(s["a"]=="BTC" for s in sigs)})')
    for tf in UTFS:
        P(f'  USDT.D {tf}: {us[tf].d[0]} to {us[tf].d[-1]}, {len(us[tf].ph)} CT pivot highs, {len(us[tf].us)} CTZB signals on USDT.D')

    # ---- Family A, real
    res = grid_A(sigs, us)
    n_cfg = sum(len(v) for v in res.values())
    real = passes_A(res)
    P(f'\nFAMILY A: {n_cfg} configurations (read x asset) evaluated')
    tested = sum(1 for nm, by in res.items() for a, pp in by.items() if step1(pp)[1] is not None)
    s1 = sum(1 for nm, by in res.items() for a, pp in by.items() if step1(pp)[0])
    P(f'  had n >= 15 per side in both periods: {tested}; passed step 1: {s1}; passed steps 1-3: {len(real)}')

    # ---- whole-grid placebo
    shifts = []
    for i in range(20):
        off = random.randint(180, 1460) * random.choice((1, -1))
        shifts.append((off, len(passes_A(grid_A(sigs, us, shift=off)))))
    cnt = sorted(c for _, c in shifts)
    p95 = cnt[int(0.95 * len(cnt))] if len(cnt) > 1 else cnt[0]
    P(f'  SHIFT PLACEBO (20 random date shifts of USDT.D, 180-1,460 days): passes steps 1-3 '
      f'mean {st.mean(cnt):.1f}, median {st.median(cnt)}, 95th pct {p95}, max {max(cnt)}')
    P(f'  real grid {len(real)} vs shifted 95th pct {p95}: '
      f'{"BEATS the placebo" if len(real) > p95 else "does NOT beat the placebo -- the passes are what this many tries produce by chance"}')

    P('\n  every config passing steps 1-3 (win / t30 = on minus off, percentage points):')
    P('  read                      asset dir | to 2021: n on/off  win  t30 | 2022 on: n on/off  win  t30 | charts years | shuffle real/p95 | overlap')
    surv = []
    for r in sorted(real, key=lambda r: (r['a'], r['nm'])):
        pairs = res[r['nm']][r['a']]
        rv, p = shuffle_p95(pairs, r['d'])
        ov = overlap(pairs, r['a'], r['d'])
        (n0, f0, w0, t0), (n1, f1, w1, t1) = r['s1']
        ok = rv > p and not ov
        if ok: surv.append(r)
        P(f'  {r["nm"]:<25} {r["a"]} {r["d"]} | {n0:4d}/{f0:<4d} {fmt(w0)} {fmt(t0)} | {n1:4d}/{f1:<4d} {fmt(w1)} {fmt(t1)} '
          f'| {r["ch"][0]}/{r["ch"][1]} {r["yr"][0]:2d}/{r["yr"][1]:<2d} | {rv:+5.1f}/{p:+5.1f} | {",".join(ov) or "-"}'
          f'{"   <- SURVIVES 1-5" if ok else ""}')
    both = {}
    for r in surv: both.setdefault((r['nm'], r['d']), set()).add(r['a'])
    P(f'\n  survivors of steps 1-5: {len(surv)}; distinct findings after step 6 (ETH and BTC one sample): {len(both)}')
    if len(real) <= p95:
        P('  Step 4(a) failed at the grid level, so no survivor counts as a finding whatever its own shuffle says.')

    # ---- Family B
    fb = family_B(us, day)
    passB = []
    P('\nFAMILY B: USDT.D CT pivot highs as standalone entries (192 configurations)')
    P('  config                                 | to 2021: n  win  t30 | 2022 on: n  win  t30 (vs every day in the same set)')
    for nm, a, gm, ev, base in fb:
        ok, s = judge_B(ev, base)
        if s is None: continue
        if ok: passB.append(nm)
        P(f'  {nm:<38} | {s[0][0]:4d} {fmt(s[0][1])} {fmt(s[0][2])} | {s[1][0]:4d} {fmt(s[1][1])} {fmt(s[1][2])}{"  PASS" if ok else ""}')
    nb = sum(1 for nm, a, gm, ev, base in fb if judge_B(ev, base)[1] is not None)
    P(f'  testable (n >= 15 both periods): {nb} of {len(fb)}; passed: {len(passB)}')
    shB = []
    for i in range(20):
        off = random.randint(180, 1460) * random.choice((1, -1))
        shB.append(sum(1 for nm, a, gm, ev, base in family_B(us, day, shift=off) if judge_B(ev, base)[0]))
    shB.sort()
    P(f'  SHIFT PLACEBO: passes mean {st.mean(shB):.1f}, 95th pct {shB[int(0.95*len(shB))]}, max {max(shB)}; real {len(passB)}')
    # the asset's own CTZB signals, for scale
    for a in ('ETH', 'BTC'):
        for p, lab in ((0, 'to 2021'), (1, '2022 on')):
            g = [s for s in sigs if s['a'] == a and s['per'] == p]
            P(f'  for scale: {a} regime-gated CTZB signals {lab}: win {rate(g, "win"):.0f}% (n {len(g)}), t30 {rate(g, "t30"):.0f}%')

    P('\nENTRY QUALITY ONLY. No exit in the data, so no strategy return or track record. Computed signals, never fills.')
    open(os.path.join(HERE, 'RESULTS_usdtd_grid.txt'), 'w').write('\n'.join(L) + '\n')
    json.dump(dict(configs_A=n_cfg, configs_B=len(fb), passA=[(r['nm'], r['a'], r['d']) for r in real],
                   survivors=[(r['nm'], r['a'], r['d']) for r in surv], shiftA=shifts, passB=passB, shiftB=shB),
              open(os.path.join(HERE, 'usdtd_grid.json'), 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
