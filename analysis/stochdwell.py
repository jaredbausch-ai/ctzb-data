"""Stoch RSI lines PINNED (staying at the same value) -- how long, and where. Declared 31 Oct 2026.

Jared's question, 31 Oct evening: backtest the blue line (Stoch %K) and the red
line (Stoch %D) on every ETH and BTC chart, every timeframe, for a run of bars
where the line stays at the same value, and where that happens (bearish control
zone vs bullish control zone). Looking for a new lens.

Builds on analysis/flatk.py (31 Oct, same day): K below 5 for 3 bars with CT < 40,
1D-3D only, 10 bars forward. That test found ETH 1D only, and every 2D/3D cell
was 3-8 events. This one widens the question; it does not re-run flatk's cells
as new findings.

DEFINITIONS (fixed before running)
  CT  = RSI(close, 14)                                   (engine.rsi)
  K   = sma(stoch(CT, CT, CT, 14), 3)  the BLUE line     (v15 line 176)
  D   = sma(K, 3)                      the RED line      (v15 line 177)
  A stochastic of RSI only "stays the same value" when it is pinned at its floor
  or ceiling, so "same value" = PINNED:
    FLOOR   line <= 5   -- the line sits in the bearish control band (0-40)
    CEILING line >= 95  -- the line sits in the bullish control band (60-100)
  run[i] = consecutive bars ending at bar i with the line pinned.
  CT zone at a bar: BEAR CT < 40, NEUTRAL 40-60, BULL CT >= 60 (v15 zBear / rzBull).
  Regime gate: R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41), at the bar's date.

OUTCOME (the card measure, CARD_SPEC): from the close of the event bar,
  SURV10  rose 10% AND never fell 25.3% within 60 days
  LIQ30   fell 30% or more within 60 days
  1D-8D charts measure on the 1D series from the bar's last day (tagstats.measure);
  4H/12H measure on their own bars over 60 days (360 / 120 bars).
  Secondary, descriptive only: 10-bar return on the chart's own bars.

PART B -- EVENT STUDY (all 14 charts: 4H 12H 1D 2D 3D 5D 8D x ETH BTC)
  24 configs = line {K, D} x pin {FLOOR, CEILING} x N {3, 5, 8} x type:
    ONSET-N    the bar where the run reaches exactly N
    RELEASE-N  the first bar off the pin after a run of N or more
  Regime ON at the event bar. De-duplicated per chart: an event within 20 days
  of the previous kept event of the same config is dropped.
  Baselines per chart: every regime-ON bar (one per calendar day on 4H/12H), and
  the same split by CT zone. LIFT = event SURV10 minus the baseline SURV10 of
  the same chart AND the same CT zone (so a pin is not credited for the zone it
  sits in). Averaged over events.
  A config PASSES only if ALL of:
    B1 n >= 40 de-duplicated events, pooled
    B2 |LIFT| >= 8 points
    B3 same sign before 2022 and 2022 on (each n >= 10)
    B4 same sign on ETH and on BTC (each n >= 10)
    B5 same sign on at least 2/3 of charts with n >= 8
    B6 same sign in at least 60% of years with n >= 5
  A negative LIFT that passes is a caution read, not a buy read.

PART A -- LENS ON CTZB SIGNALS (the 10 system charts, 1D-8D, regime-gated
  signals from engine.signals, entry = confirmation close ei = ti + 3).
  Every feature uses bars <= ti, so it is known at entry.
    L1 K_FLOOR3     K floor run >= 3 bars inside [ti-10, ti]
    L2 D_FLOOR3     D floor run >= 3 inside [ti-10, ti]
    L3 K_FLOOR6     K floor run >= 6 inside [ti-10, ti]
    L4 D_FLOOR6     D floor run >= 6 inside [ti-10, ti]
    L5 K_CEIL3_PRE  K ceiling run >= 3 inside [ti-30, ti-1]
    L6 D_CEIL3_PRE  D ceiling run >= 3 inside [ti-30, ti-1]
    L7 K_FLOOR3_CTUP  L1 with CT >= 40 on every bar of that run (pinned K, CT not in bear control)
    L8 K_FLOOR3_CTDN  L1 with CT < 40 at the trough (overlaps bucket A; collinearity reported)
  A lens PASSES only if ALL of:
    A1 n with >= 40 and n without >= 40
    A2 SURV10 with minus without >= +8 points pooled (or <= -8 for a caution lens)
    A3 LIQ30 with no higher than without (caution lens: no lower)
    A4 same sign in both periods (before 2022 / 2022 on)
    A5 same sign on at least 2/3 of charts with n >= 8 on both sides
    A6 same sign in at least 60% of years with n >= 5 on both sides
    A7 the lift holds at >= +5 (caution: <= -5) stratified by bucket and by prime
       (weighted within-stratum difference), so it is not bucket A or the prime dot
       in disguise. Phi against bucket A, prime and diamond printed beside it.
  Anything that passes is then checked inside the grade on the ledger before it
  is called anything but a candidate. Entry quality only: no exit in the data.

Run from the repo root:  python3 -I analysis/stochdwell.py
"""
import sys, os, statistics, datetime as dt
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, engine as E, regimes as R
from tagstats import bucket_end, measure

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
ALL_TF = ('4H', '12H', '1D', '2D', '3D', '5D', '8D')
SYS_TF = ('1D', '2D', '3D', '5D', '8D')
PER_DAY = {'4H': 6, '12H': 2}
FLOOR, CEIL = 5.0, 95.0
CUT = dt.date(2022, 1, 1)

_DAY = {}


def day_series(sym):
    if sym not in _DAY:
        d = E.load(f'data/{sym}_1D.csv')
        _DAY[sym] = (d, {x: i for i, x in enumerate(d['date'])})
    return _DAY[sym]


class Chart:
    def __init__(self, sym, tf):
        self.sym, self.tf, self.name = sym, tf, f'{sym} {tf}'
        b = E.load(f'data/{sym}_{tf}.csv')
        self.b = b
        c = b['close']
        self.ct = E.rsi(c, 14)
        self.k = E.sma(E.stoch_of(self.ct, 14), 3)
        self.d = E.sma(self.k, 3)
        self.n = len(c)
        self._out = {}

    def outcome(self, i):
        """SURV10 / LIQ30 within 60 days from the close of bar i, plus 10-bar return."""
        if i in self._out:
            return self._out[i]
        b = self.b; c0 = b['close'][i]; r = None
        if self.tf in PER_DAY:
            w = 60 * PER_DAY[self.tf]
            if i + w < self.n:
                hi = max(b['high'][i + 1:i + 1 + w]); lo = min(b['low'][i + 1:i + 1 + w])
                r = dict(up=(hi / c0 - 1) * 100, dd=(lo / c0 - 1) * 100)
        else:
            de = bucket_end(b['date'], i)
            day, pos = day_series(self.sym)
            if de is not None and de in pos:
                m = measure(day, pos, de, c0, 60)
                if m:
                    r = dict(up=m['up'], dd=m['dd'])
        if r is not None:
            r['surv'] = r['up'] >= 10 and r['dd'] > -25.3
            r['liq'] = r['dd'] <= -30
            r['r10'] = (b['close'][i + 10] / c0 - 1) * 100 if i + 10 < self.n else None
        self._out[i] = r
        return r

    def zone(self, i):
        v = self.ct[i]
        if v is None: return None
        return 'BEAR' if v < 40 else 'BULL' if v >= 60 else 'NEUT'

    def runs(self, line, pin):
        x = self.k if line == 'K' else self.d
        out = [0] * self.n
        for i in range(self.n):
            v = x[i]
            ok = v is not None and (v <= FLOOR if pin == 'FLOOR' else v >= CEIL)
            out[i] = (out[i - 1] + 1 if i else 1) if ok else 0
        return out


def load_charts(tfs):
    return [Chart(s, t) for s in ('ETH', 'BTC') for t in tfs]


# ------------------------------------------------------------------ PART B
def baselines(ch):
    """Regime-ON baseline SURV10 per CT zone, one bar per calendar day."""
    acc = defaultdict(list); seen = set()
    for i in range(30, ch.n):
        dte = ch.b['date'][i]
        if ch.tf in PER_DAY:
            # last bar of each calendar day
            if i + 1 < ch.n and ch.b['date'][i + 1] == dte: continue
        if dte in seen: continue
        seen.add(dte)
        if not GATE(dte): continue
        z = ch.zone(i); o = ch.outcome(i)
        if z is None or o is None: continue
        acc[z].append(o['surv']); acc['ALL'].append(o['surv'])
    return {z: 100 * sum(v) / len(v) for z, v in acc.items() if v}


def events(ch, line, pin, N, kind, rcache):
    key = (line, pin)
    if key not in rcache: rcache[key] = ch.runs(line, pin)
    r = rcache[key]; out = []; last = None
    for i in range(31, ch.n):
        if kind == 'ONSET':
            hit = r[i] == N
        else:
            hit = r[i] == 0 and r[i - 1] >= N
        if not hit: continue
        dte = ch.b['date'][i]
        if not GATE(dte): continue
        if last is not None and (dte - last).days <= 20: continue
        o = ch.outcome(i); z = ch.zone(i)
        if o is None or z is None: continue
        last = dte
        out.append(dict(i=i, date=dte, zone=z, **o))
    return out


def same_sign_share(groups, sign, minn):
    vals = [v for v in groups.values() if v[1] >= minn]
    if not vals: return None, 0
    good = sum(1 for lift, n in vals if (lift > 0) == (sign > 0) and lift != 0)
    return good / len(vals), len(vals)


def part_b(charts):
    print('=' * 100)
    print('PART B  EVENT STUDY  pinned K / D, every chart, regime ON, 60-day card measure')
    print('=' * 100)
    base = {ch.name: baselines(ch) for ch in charts}
    print('\nRegime-ON baseline SURV10 by CT zone (one bar per day):')
    print(f'  {"chart":<9}{"ALL":>7}{"BEAR":>7}{"NEUT":>7}{"BULL":>7}')
    for ch in charts:
        bz = base[ch.name]
        print(f'  {ch.name:<9}' + ''.join(f'{bz.get(z, float("nan")):>7.0f}' for z in ('ALL', 'BEAR', 'NEUT', 'BULL')))
    rcache = {ch.name: {} for ch in charts}
    rows = []
    for line in ('K', 'D'):
        for pin in ('FLOOR', 'CEILING'):
            for kind in ('ONSET', 'RELEASE'):
                for N in (3, 5, 8):
                    ev = []
                    for ch in charts:
                        for e in events(ch, line, pin, N, kind, rcache[ch.name]):
                            bz = base[ch.name]
                            if e['zone'] not in bz: continue
                            e['chart'] = ch.name; e['asset'] = ch.sym
                            e['lift'] = 100 * e['surv'] - bz[e['zone']]
                            e['liftall'] = 100 * e['surv'] - bz['ALL']
                            ev.append(e)
                    rows.append(((line, pin, kind, N), ev))
    print(f'\n  {"config":<26}{"n":>5}{"SURV10":>8}{"LIFTz":>7}{"LIFTall":>8}{"LIQ30":>7}'
          f'{"<2022":>7}{"2022+":>7}{"ETH":>6}{"BTC":>6}{"charts":>8}{"years":>7}  zones B/N/U  verdict')
    passed = []
    for cfg, ev in rows:
        n = len(ev)
        name = f'{cfg[0]} {cfg[1]} {cfg[2]}-{cfg[3]}'
        if n == 0:
            print(f'  {name:<26}{0:>5}'); continue
        lift = statistics.mean(e['lift'] for e in ev)
        la = statistics.mean(e['liftall'] for e in ev)
        sv = 100 * statistics.mean(e['surv'] for e in ev)
        lq = 100 * statistics.mean(e['liq'] for e in ev)
        def grp(f):
            g = defaultdict(list)
            for e in ev: g[f(e)].append(e['lift'])
            return {k: (statistics.mean(v), len(v)) for k, v in g.items()}
        per = grp(lambda e: 'old' if e['date'] < CUT else 'new')
        ast = grp(lambda e: e['asset'])
        chs = grp(lambda e: e['chart'])
        yrs = grp(lambda e: e['date'].year)
        sgn = 1 if lift > 0 else -1
        def f(g, k):
            v = g.get(k); return f'{v[0]:+.0f}' if v and v[1] >= 10 else '  -'
        cshare, cn = same_sign_share(chs, sgn, 8)
        yshare, yn = same_sign_share(yrs, sgn, 5)
        zs = defaultdict(int)
        for e in ev: zs[e['zone']] += 1
        checks = [n >= 40, abs(lift) >= 8]
        po, pn = per.get('old', (0, 0)), per.get('new', (0, 0))
        checks.append(po[1] >= 10 and pn[1] >= 10 and po[0] * sgn > 0 and pn[0] * sgn > 0)
        ae, ab = ast.get('ETH', (0, 0)), ast.get('BTC', (0, 0))
        checks.append(ae[1] >= 10 and ab[1] >= 10 and ae[0] * sgn > 0 and ab[0] * sgn > 0)
        checks.append(cshare is not None and cshare >= 2 / 3)
        checks.append(yshare is not None and yshare >= 0.6)
        failed = [f'B{j + 1}' for j, ok in enumerate(checks) if not ok]
        verdict = 'PASS' if not failed else 'fail ' + ','.join(failed)
        if not failed: passed.append((name, ev, lift))
        cs = f'{cshare * 100:.0f}%/{cn}' if cshare is not None else '-'
        ys = f'{yshare * 100:.0f}%/{yn}' if yshare is not None else '-'
        print(f'  {name:<26}{n:>5}{sv:>8.0f}{lift:>+7.0f}{la:>+8.0f}{lq:>7.0f}'
              f'{f(per, "old"):>7}{f(per, "new"):>7}{f(ast, "ETH"):>6}{f(ast, "BTC"):>6}{cs:>8}{ys:>7}'
              f'  {zs["BEAR"]}/{zs["NEUT"]}/{zs["BULL"]}  {verdict}')
    return passed, rows


# ------------------------------------------------------------------ PART A
def maxrun(mask, lo, hi):
    best = run = 0
    for j in range(max(lo, 0), hi + 1):
        run = run + 1 if mask[j] else 0
        best = max(best, run)
    return best


def maxrun_ct(mask, ct, lo, hi, ctok):
    best = run = 0
    for j in range(max(lo, 0), hi + 1):
        ok = mask[j] and ct[j] is not None and ctok(ct[j])
        run = run + 1 if ok else 0
        best = max(best, run)
    return best


LENSES = ('K_FLOOR3', 'D_FLOOR3', 'K_FLOOR6', 'D_FLOOR6', 'K_CEIL3_PRE', 'D_CEIL3_PRE',
          'K_FLOOR3_CTUP', 'K_FLOOR3_CTDN')


def signal_rows(charts):
    rows = []
    for ch in charts:
        sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=GATE)
        kf = [v is not None and v <= FLOOR for v in ch.k]
        dfl = [v is not None and v <= FLOOR for v in ch.d]
        kc = [v is not None and v >= CEIL for v in ch.k]
        dc = [v is not None and v >= CEIL for v in ch.d]
        for s in sig:
            ti, ei = s['ti'], s['ei']
            o = ch.outcome(ei)
            if o is None: continue
            f = {}
            f['K_FLOOR3'] = maxrun(kf, ti - 10, ti) >= 3
            f['D_FLOOR3'] = maxrun(dfl, ti - 10, ti) >= 3
            f['K_FLOOR6'] = maxrun(kf, ti - 10, ti) >= 6
            f['D_FLOOR6'] = maxrun(dfl, ti - 10, ti) >= 6
            f['K_CEIL3_PRE'] = maxrun(kc, ti - 30, ti - 1) >= 3
            f['D_CEIL3_PRE'] = maxrun(dc, ti - 30, ti - 1) >= 3
            f['K_FLOOR3_CTUP'] = maxrun_ct(kf, ch.ct, ti - 10, ti, lambda v: v >= 40) >= 3
            f['K_FLOOR3_CTDN'] = f['K_FLOOR3'] and s['ct'] < 40
            rows.append(dict(chart=ch.name, asset=ch.sym, date=ch.b['date'][ei], end=bucket_end(ch.b['date'], ei), bk=s['bk'],
                             prime=s['prime'], dia=s['dis'], **o, **f))
    return rows


def phi(rows, a, b):
    n11 = sum(1 for r in rows if r[a] and r[b]); n10 = sum(1 for r in rows if r[a] and not r[b])
    n01 = sum(1 for r in rows if not r[a] and r[b]); n00 = len(rows) - n11 - n10 - n01
    den = ((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)) ** 0.5
    return (n11 * n00 - n10 * n01) / den if den else 0.0


def strat_lift(rows, lens, key):
    num = den = 0.0
    g = defaultdict(list)
    for r in rows: g[key(r)].append(r)
    for v in g.values():
        w = [r['surv'] for r in v if r[lens]]; wo = [r['surv'] for r in v if not r[lens]]
        if len(w) >= 5 and len(wo) >= 5:
            wt = 1 / (1 / len(w) + 1 / len(wo))
            num += wt * (100 * statistics.mean(w) - 100 * statistics.mean(wo)); den += wt
    return num / den if den else None


def part_a(charts):
    print('\n' + '=' * 100)
    print('PART A  LENS ON CTZB SIGNALS  10 system charts, regime-gated, entry = confirmation close')
    print('=' * 100)
    rows = signal_rows(charts)
    for r in rows: r['bkA'] = r['bk'] == 'A'
    allS = 100 * statistics.mean(r['surv'] for r in rows)
    allL = 100 * statistics.mean(r['liq'] for r in rows)
    print(f'\nAll signals: n={len(rows)}  SURV10 {allS:.0f}%  LIQ30 {allL:.0f}%\n')
    print(f'  {"lens":<15}{"n with":>7}{"SURV":>6}{"LIQ":>5}{"n w/o":>7}{"SURV":>6}{"LIQ":>5}{"lift":>6}'
          f'{"<2022":>7}{"2022+":>7}{"charts":>8}{"years":>7}{"bk-adj":>7}{"pr-adj":>7}'
          f'{"phiA":>6}{"phiPr":>6}{"phiDi":>6}  verdict')
    passed = []
    for L in LENSES:
        w = [r for r in rows if r[L]]; wo = [r for r in rows if not r[L]]
        if not w or not wo:
            print(f'  {L:<15}{len(w):>7}'); continue
        sw = 100 * statistics.mean(r['surv'] for r in w); so = 100 * statistics.mean(r['surv'] for r in wo)
        lw = 100 * statistics.mean(r['liq'] for r in w); lo = 100 * statistics.mean(r['liq'] for r in wo)
        lift = sw - so; sgn = 1 if lift > 0 else -1
        def split(key, minn):
            g = defaultdict(lambda: ([], []))
            for r in rows: g[key(r)][0 if r[L] else 1].append(r['surv'])
            return {k: (100 * statistics.mean(a) - 100 * statistics.mean(b), min(len(a), len(b)))
                    for k, (a, b) in g.items() if len(a) >= minn and len(b) >= minn}
        per = split(lambda r: 'old' if r['date'] < CUT else 'new', 10)
        chs = split(lambda r: r['chart'], 8)
        yrs = split(lambda r: r['date'].year, 5)
        cshare, cn = same_sign_share(chs, sgn, 0)
        yshare, yn = same_sign_share(yrs, sgn, 0)
        bka = strat_lift(rows, L, lambda r: r['bk'])
        pra = strat_lift(rows, L, lambda r: r['prime'])
        checks = [len(w) >= 40 and len(wo) >= 40, abs(lift) >= 8,
                  (lw <= lo) if sgn > 0 else (lw >= lo),
                  'old' in per and 'new' in per and per['old'][0] * sgn > 0 and per['new'][0] * sgn > 0,
                  cshare is not None and cshare >= 2 / 3,
                  yshare is not None and yshare >= 0.6,
                  bka is not None and pra is not None and bka * sgn >= 5 and pra * sgn >= 5]
        failed = [f'A{j + 1}' for j, ok in enumerate(checks) if not ok]
        verdict = 'PASS' if not failed else 'fail ' + ','.join(failed)
        if not failed: passed.append(L)
        fp = lambda k: f'{per[k][0]:+.0f}' if k in per else '  -'
        cs = f'{cshare * 100:.0f}%/{cn}' if cshare is not None else '-'
        ys = f'{yshare * 100:.0f}%/{yn}' if yshare is not None else '-'
        fx = lambda v: f'{v:+.0f}' if v is not None else '-'
        print(f'  {L:<15}{len(w):>7}{sw:>6.0f}{lw:>5.0f}{len(wo):>7}{so:>6.0f}{lo:>5.0f}{lift:>+6.0f}'
              f'{fp("old"):>7}{fp("new"):>7}{cs:>8}{ys:>7}{fx(bka):>7}{fx(pra):>7}'
              f'{phi(rows, L, "bkA"):>6.2f}{phi(rows, L, "prime"):>6.2f}{phi(rows, L, "dia"):>6.2f}  {verdict}')
    print('\nPer chart, n with / SURV10 with vs without:')
    for L in LENSES:
        parts = []
        for ch in charts:
            v = [r for r in rows if r['chart'] == ch.name]
            w = [r['surv'] for r in v if r[L]]; wo = [r['surv'] for r in v if not r[L]]
            if w and wo:
                parts.append(f'{ch.name} {len(w)}:{100 * statistics.mean(w):.0f}/{100 * statistics.mean(wo):.0f}')
        print(f'  {L:<15}' + '  '.join(parts))
    return passed, rows


def main():
    print(__doc__.split('Run from')[0])
    allc = load_charts(ALL_TF)
    passed_b, _ = part_b(allc)
    sysc = [c for c in allc if c.tf in SYS_TF]
    passed_a, _ = part_a(sysc)
    print('\nSUMMARY')
    print('  Part B configs passing every declared rule:', ', '.join(p[0] for p in passed_b) or 'none')
    print('  Part A lenses passing every declared rule:', ', '.join(passed_a) or 'none')
    print('  Entry quality only. No exit in the data; not a strategy return or a track record.')


if __name__ == '__main__':
    main()
