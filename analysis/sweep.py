"""Discovery / holdout sweep: what else sorts good CTZB signals from bad?

DECLARED BEFORE RUNNING (23 Oct 2026). Free rein from Jared to look for edges
he hasn't thought of. Testing many ideas on one history manufactures winners,
so every feature below is fixed here, cut points come from the DISCOVERY years
only, and nothing counts unless it holds on years it never saw.

  signals    regime-gated signals on ETH 1D/2D/3D/5D and BTC 1D/2D/3D/5D (gate
             R.rsi_regime(BTC_2D,8,13,60,41)); entry = confirmation close at the
             day that bar closes (d0); outcomes on daily candles.
  periods    DISCOVERY entries 2016-2021, HOLDOUT entries 2022 onward (complete
             60-day windows only).
  outcomes   primary  reach +20% within 60 days
             second   touched -20% within 60 days (depth risk at 3.3x)
  entry features (all knowable at d0). Continuous ones are split into terciles
  per chart using DISCOVERY cut points; compared top third vs bottom third:
    F1  volume spike: trough bar volume / mean of the prior 20 bars
    F2  volume into confirmation: mean volume of the 3 confirmation bars /
        trough bar volume
    F3  cluster: 2+ earlier signals on the same chart in the prior 30 days
        (binary, vs none)
    F4  days since the previous signal on the same chart
    F5  pullback depth: entry close / highest close of the prior 30 days
    F6  rebound already paid: entry close / trough bar low
    F7  capitulation wick: trough bar (min(open,close) - low) / (high - low)
    F8  asset oversold vs the other asset: ETH/BTC ratio 1D CT < 40 for ETH
        signals, > 60 for BTC signals (binary)
    F9  asset leading the other: ratio above its 50-day average for ETH
        signals, below it for BTC signals (binary)
    F10 realised volatility: stdev of 30 daily log returns at d0
    F11 volatility compression: 30-day vol / 180-day vol
    F12 higher timeframe: the asset's 8D CT RSI >= 50 at d0 (binary; last
        completed 8D bar)
    F13 higher timeframe rising: 8D CT last completed bar > the one before
    F14 asset above its own 200-day average (binary)
    F15 extension: close / 200-day average
    F16 other asset's 1D CT above its Signal line at d0 (binary)
    F17 recovery speed: chart CT at confirmation minus CT at the trough
  in-trade tells (knowable N days after entry; only trades that had NOT yet
  reached +20% by day N are scored, outcome still +20% within 60d of entry):
    T1  green (close >= entry) on day 5
    T2  green on day 10
    T3  chart CT above its Signal line on day 10 (last completed bar)
    T4  price undercut the trough bar's low by day 10
    T5  drawdown deeper than -10% by day 10
  PASS (primary): lift >= +8 points in DISCOVERY and >= +5 in HOLDOUT, same
             sign; each compared group n >= 30 in discovery, >= 20 in holdout;
             same sign on >= 5 of 8 charts over the full period.
  PASS (risk):    the same rule on the -20% touch rate, sign reversed
             (a feature that cuts deep drawdowns).
  survivors  are then checked inside Tier 1 #1 (CT > 5 above the Signal line)
             yes / no, so a restatement of it is caught.

Entry quality only: no exit, no strategy return. Signals computed, never fills.

Run from the repo root:  python3 -I analysis/sweep.py
"""
import sys, os, csv, math, bisect, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end, measure

CHARTS = ['ETH_1D', 'ETH_2D', 'ETH_3D', 'ETH_5D', 'BTC_1D', 'BTC_2D', 'BTC_3D', 'BTC_5D']
SPLIT = dt.date(2022, 1, 1)


def vols(path):
    with open(path) as f:
        rd = csv.reader(f); next(rd)
        return [float(r[5]) if len(r) > 5 and r[5] else None for r in rd]


def closed_index(dates, d):
    """index of the last bar of this chart that had CLOSED by the end of day d"""
    ends = [dates[j + 1] - dt.timedelta(days=1) for j in range(len(dates) - 1)]
    return bisect.bisect_right(ends, d) - 1


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    day = {a: E.load(f'data/{a}_1D.csv') for a in ('ETH', 'BTC')}
    pos = {a: {d: i for i, d in enumerate(day[a]['date'])} for a in day}
    cl = {a: dict(zip(day[a]['date'], day[a]['close'])) for a in day}
    # ratio ETH/BTC daily, its CT and 50d average
    rd = [d for d in day['ETH']['date'] if d in cl['BTC']]
    rr = [cl['ETH'][d] / cl['BTC'][d] for d in rd]
    rct = E.rsi(rr, 14); rma = E.sma(rr, 50)
    ratio = {d: (rct[i], rr[i], rma[i]) for i, d in enumerate(rd)}
    # per-asset daily helpers
    helper = {}
    for a in ('ETH', 'BTC'):
        C = day[a]['close']; D = day[a]['date']
        lr = [None] + [math.log(C[i] / C[i - 1]) for i in range(1, len(C))]
        v30 = [None] * len(C); v180 = [None] * len(C)
        for i in range(len(C)):
            if i >= 30:
                v30[i] = float(np.std(lr[i - 29:i + 1]))
            if i >= 180:
                v180[i] = float(np.std(lr[i - 179:i + 1]))
        sma200 = E.sma(C, 200)
        ct1 = E.rsi(C, 14); em1 = E.ema(ct1, 14)
        b8 = E.load(f'data/{a}_8D.csv'); ct8 = E.rsi(b8['close'], 14)
        helper[a] = dict(v30=v30, v180=v180, sma=sma200, ct1=ct1, em1=em1, b8=b8, ct8=ct8)
    rows = []
    for ch in CHARTS:
        a = ch.split('_')[0]; o = 'BTC' if a == 'ETH' else 'ETH'
        H = helper[a]; dd_ = day[a]; P = pos[a]
        last_closed = dd_['date'][-2]
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        V = vols(f'data/{ch}.csv')
        ctc = E.rsi(b['close'], 14); emc = E.ema(ctc, 14)
        prev_d = []
        for s in sig:
            d0 = bucket_end(b['date'], s['ei'])
            if d0 is None or d0 > last_closed or d0 not in P:
                continue
            m = measure(dd_, P, d0, s['entry'], 60)
            if not m:
                prev_d.append(d0); continue
            ti, ei = s['ti'], s['ei']; i0 = P[d0]
            f = {}
            vw = [x for x in V[max(0, ti - 20):ti] if x]
            f['F1'] = V[ti] / np.mean(vw) if vw and V[ti] else None
            cv = [x for x in V[ti + 1:ei + 1] if x]
            f['F2'] = np.mean(cv) / V[ti] if cv and V[ti] else None
            prior = [x for x in prev_d if 0 < (d0 - x).days <= 30]
            f['F3'] = True if len(prior) >= 2 else (False if len(prior) == 0 else None)
            f['F4'] = (d0 - prev_d[-1]).days if prev_d else None
            hi30 = max(dd_['close'][max(0, i0 - 30):i0 + 1])
            f['F5'] = s['entry'] / hi30
            f['F6'] = s['entry'] / b['low'][ti]
            rng = b['high'][ti] - b['low'][ti]
            f['F7'] = (min(b['open'][ti], b['close'][ti]) - b['low'][ti]) / rng if rng > 0 else None
            rt = ratio.get(d0)
            if rt and rt[0] is not None:
                f['F8'] = (rt[0] < 40) if a == 'ETH' else (rt[0] > 60)
            if rt and rt[2] is not None:
                f['F9'] = (rt[1] > rt[2]) if a == 'ETH' else (rt[1] < rt[2])
            f['F10'] = H['v30'][i0]
            f['F11'] = H['v30'][i0] / H['v180'][i0] if H['v180'][i0] else None
            k8 = closed_index(H['b8']['date'], d0)
            if k8 >= 1 and H['ct8'][k8] is not None and H['ct8'][k8 - 1] is not None:
                f['F12'] = H['ct8'][k8] >= 50
                f['F13'] = H['ct8'][k8] > H['ct8'][k8 - 1]
            if H['sma'][i0]:
                f['F14'] = dd_['close'][i0] > H['sma'][i0]
                f['F15'] = dd_['close'][i0] / H['sma'][i0]
            oi = pos[o].get(d0)
            ho = helper[o]
            if oi is not None and ho['ct1'][oi] is not None and ho['em1'][oi] is not None:
                f['F16'] = ho['ct1'][oi] > ho['em1'][oi]
            f['F17'] = ctc[ei] - ctc[ti] if ctc[ei] is not None else None
            # in-trade tells
            def close_at(n):
                j = P.get(d0 + dt.timedelta(days=n)); return dd_['close'][j] if j is not None else None
            def peak_by(n):
                js = [P.get(d0 + dt.timedelta(days=k)) for k in range(1, n + 1)]
                return max(dd_['high'][j] for j in js if j is not None)
            def low_by(n):
                js = [P.get(d0 + dt.timedelta(days=k)) for k in range(1, n + 1)]
                return min(dd_['low'][j] for j in js if j is not None)
            t = {}
            for n, key in ((5, 'T1'), (10, 'T2')):
                c_ = close_at(n)
                if c_ is not None and peak_by(n) < s['entry'] * 1.2:
                    t[key] = c_ >= s['entry']
            if peak_by(10) < s['entry'] * 1.2:
                kc = closed_index(b['date'], d0 + dt.timedelta(days=10))
                if 0 <= kc < len(ctc) and ctc[kc] is not None and emc[kc] is not None:
                    t['T3'] = ctc[kc] > emc[kc]
                t['T4'] = low_by(10) < b['low'][ti]
                t['T5'] = low_by(10) <= s['entry'] * 0.9
            gap = ctc[ei] - emc[ei] if ctc[ei] is not None and emc[ei] is not None else None
            rows.append(dict(ch=ch, d=d0, y=d0.year, disc=d0 < SPLIT, hit=m['up'] >= 20, deep=m['dd'] <= -20,
                             f=f, t=t, gap5=gap is not None and gap > 5))
            prev_d.append(d0)

    cont = ['F1', 'F2', 'F4', 'F5', 'F6', 'F7', 'F10', 'F11', 'F15', 'F17']
    binf = ['F3', 'F8', 'F9', 'F12', 'F13', 'F14', 'F16']
    # tercile labels per chart from DISCOVERY cut points: 'hi' top third, 'lo' bottom third
    for k in cont:
        for ch in CHARTS:
            vals = [r['f'][k] for r in rows if r['ch'] == ch and r['disc'] and r['f'].get(k) is not None]
            if len(vals) < 9:
                continue
            q1, q2 = np.percentile(vals, [100 / 3, 200 / 3])
            for r in rows:
                if r['ch'] == ch and r['f'].get(k) is not None:
                    v = r['f'][k]
                    r['f'][k + 'g'] = True if v >= q2 else (False if v <= q1 else None)
    feats = [(k + 'g', k, 'top third vs bottom third') for k in cont] + [(k, k, 'yes vs no') for k in binf] + \
            [(k, k, 'yes vs no (in-trade)') for k in ('T1', 'T2', 'T3', 'T4', 'T5')]
    names = {'F1': 'volume spike at trough', 'F2': 'volume rising into confirmation', 'F3': 'third+ signal in 30 days',
             'F4': 'long gap since last signal', 'F5': 'shallow pullback (near 30d high)', 'F6': 'big rebound already paid',
             'F7': 'long lower wick on trough bar', 'F8': 'asset oversold vs the other', 'F9': 'asset leading the other',
             'F10': 'high realised volatility', 'F11': 'volatility expanding (not compressed)', 'F12': '8D CT >= 50',
             'F13': '8D CT rising', 'F14': 'above own 200d average', 'F15': 'extended above 200d average',
             'F16': 'other asset CT above its Signal', 'F17': 'fast CT recovery trough->entry',
             'T1': 'green on day 5', 'T2': 'green on day 10', 'T3': 'CT above Signal on day 10',
             'T4': 'undercut trough low by day 10', 'T5': 'down 10%+ by day 10'}

    def getv(r, key):
        src = r['t'] if key.startswith('T') else r['f']
        return src.get(key)

    def rate(sel, k):
        return 100 * np.mean([r[k] for r in sel]) if sel else float('nan')

    print(f'{len(rows)} gated signals with full 60d outcomes: discovery {sum(r["disc"] for r in rows)}, '
          f'holdout {sum(not r["disc"] for r in rows)}. +20% rate disc {rate([r for r in rows if r["disc"]],"hit"):.0f}%, '
          f'hold {rate([r for r in rows if not r["disc"]],"hit"):.0f}%\n')
    print(f'{"feature":<36}{"compare":<26}{"DISC +20% yes/no (n)":>26}{"lift":>6}{"HOLD +20% yes/no (n)":>26}{"lift":>6}'
          f'{"charts":>8}{"-20% lift D/H":>15}  verdict')
    survivors = []
    for key, base, cmpl in feats:
        out = {}
        for per, flag in (('D', True), ('H', False)):
            y = [r for r in rows if r['disc'] == flag and getv(r, key) is True]
            n = [r for r in rows if r['disc'] == flag and getv(r, key) is False]
            out[per] = (y, n)
        lD = rate(out['D'][0], 'hit') - rate(out['D'][1], 'hit'); lH = rate(out['H'][0], 'hit') - rate(out['H'][1], 'hit')
        rD = rate(out['D'][0], 'deep') - rate(out['D'][1], 'deep'); rH = rate(out['H'][0], 'deep') - rate(out['H'][1], 'deep')
        same = 0
        for ch in CHARTS:
            y = [r for r in rows if r['ch'] == ch and getv(r, key) is True]; n = [r for r in rows if r['ch'] == ch and getv(r, key) is False]
            if y and n and np.sign(rate(y, 'hit') - rate(n, 'hit')) == np.sign(lD):
                same += 1
        nok = len(out['D'][0]) >= 30 and len(out['D'][1]) >= 30 and len(out['H'][0]) >= 20 and len(out['H'][1]) >= 20
        p_hit = nok and abs(lD) >= 8 and abs(lH) >= 5 and np.sign(lD) == np.sign(lH) and same >= 5
        same_r = sum(1 for ch in CHARTS
                     if (lambda y, n: y and n and np.sign(rate(y, 'deep') - rate(n, 'deep')) == np.sign(rD))(
                         [r for r in rows if r['ch'] == ch and getv(r, key) is True],
                         [r for r in rows if r['ch'] == ch and getv(r, key) is False]))
        p_risk = nok and abs(rD) >= 8 and abs(rH) >= 5 and np.sign(rD) == np.sign(rH) and same_r >= 5
        v = []
        if p_hit:
            v.append('PASS odds'); survivors.append((key, names[base]))
        if p_risk:
            v.append('PASS risk'); survivors.append((key + ' (risk)', names[base]))
        fy = lambda sel: f'{rate(sel[0],"hit"):3.0f}/{rate(sel[1],"hit"):3.0f} ({len(sel[0])}/{len(sel[1])})'
        print(f'{names[base]:<36}{cmpl:<26}{fy(out["D"]):>26}{lD:>+6.0f}{fy(out["H"]):>26}{lH:>+6.0f}{same:>6}/8'
              f'{f"{rD:+.0f}/{rH:+.0f}":>15}  {", ".join(v) if v else "-"}')
    print('\nSURVIVORS: ' + ('; '.join(f'{k} {n}' for k, n in survivors) if survivors else 'none'))
    for key, nm in survivors:
        k = key.split(' ')[0]
        print(f'\n  {k} {nm}: inside Tier 1 #1 (CT > 5 above Signal) yes / no, full period')
        for lab, flag in (('gap>5 yes', True), ('gap>5 no ', False)):
            y = [r for r in rows if r['gap5'] == flag and getv(r, k) is True]; n = [r for r in rows if r['gap5'] == flag and getv(r, k) is False]
            print(f'    {lab}: +20% {rate(y,"hit"):.0f}% (n={len(y)}) vs {rate(n,"hit"):.0f}% (n={len(n)}); '
                  f'-20% touch {rate(y,"deep"):.0f}% vs {rate(n,"deep"):.0f}%')
        print('    per chart (+20% yes/no): ' + '  '.join(
            f'{ch.replace("_"," ")} {rate([r for r in rows if r["ch"]==ch and getv(r,k) is True],"hit"):.0f}/'
            f'{rate([r for r in rows if r["ch"]==ch and getv(r,k) is False],"hit"):.0f}' for ch in CHARTS))
        yrs = sorted({r['y'] for r in rows}); ah = tt = 0; tx = []
        for yv in yrs:
            y = [r for r in rows if r['y'] == yv and getv(r, k) is True]; n = [r for r in rows if r['y'] == yv and getv(r, k) is False]
            if len(y) >= 3 and len(n) >= 3:
                tt += 1; d_ = rate(y, 'hit') - rate(n, 'hit'); ah += d_ > 0; tx.append(f'{yv}:{d_:+.0f}')
        print('    by year (lift): ' + ' '.join(tx) + f'   positive {ah} of {tt}')


if __name__ == '__main__':
    main()
