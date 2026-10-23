"""Search for entry filters that meet Jared's standard (23 Oct 2026).

THE STANDARD, from Jared: nothing below a 70% win rate; for a change to the
stack, ~80% win rate with it, cutting no more than 20% of the winners.

DECLARED BEFORE RUNNING.
  win        reach +20% within 60 days of entry (the PRETRADE metric)
  signals    regime-gated (R.rsi_regime(BTC_2D,8,13,60,41)) on ETH 1D/2D/3D/5D and
             BTC 1D/2D/3D/5D, entry = confirmation close at the day it closes
  groups     each chart alone, ETH pooled, BTC pooled
  features   (binary, all knowable at entry)
    stack:   CT > Signal by 5+ | CT above Signal | prime dot | diamond | bucket A |
             bucket A or B | higher entry than the previous signal | 2+ other
             same-asset charts confirmed within 10d | other asset confirmed any of
             1D-5D within 10d | asset's 8D CT rising
    outside indicators (standard settings, never tuned):
             MACD(12,26,9) histogram rising on the confirmation bar |
             MACD line above its signal | ADX(14) >= 25 | Bollinger(20,2) %B < 0
             on the trough bar | close above its 50-day average (daily) | close
             above the chart's EMA(20) | OBV above its 20-bar average |
             close above the Ichimoku cloud (9,26,52) | Williams %R(14) < -80 on
             the trough bar | CCI(20) < -100 on the trough bar
  combos     every single feature and every AND-pair of features
  verdict    a combo MEETS THE STANDARD in a group only if, in BOTH 2016-2021 and
             2022 onward separately:
               win rate >= 70%   (the floor)
               keeps >= 80% of that group's winners in that period
               at least 15 signals kept in each period
             and is reported as MEETS 80 if the win rate is >= 80% in both.
  also       the best few by worst-period win rate, for distance to the bar

SECOND DECLARED BLOCK (23 Oct 2026, before running it): Jared trades at ~3.3x,
so a drawdown below entry can end the trade before any target. Same signals,
features and combos, scored a second way:
  safe win   reached +20% BEFORE touching -20% below entry (daily candles; a day
             touching both counts as the drawdown), within 60 days
  deep loss  touched -20% below entry at any point within 60 days
  standard   (S1) safe-win rate >= 70% and keeps >= 80% of safe winners, and
             (S2) Jared's ratio: keeps >= 80% of safe winners AND removes >= 80%
             of deep losses -- both in BOTH periods, n >= 15 kept in each
  also       the closest combos on each, and -25% / -30% touch rates for them

Many combos x many groups: some will clear one period by luck; requiring both
periods is the guard. Entry quality only: no exit, no strategy return.

Run from the repo root:  python3 -I analysis/standard.py
"""
import sys, os, itertools, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R
from tagstats import bucket_end, measure
from sweep import closed_index, vols

CHARTS = ['ETH_1D', 'ETH_2D', 'ETH_3D', 'ETH_5D', 'BTC_1D', 'BTC_2D', 'BTC_3D', 'BTC_5D']
SPLIT = dt.date(2022, 1, 1)


def ema(x, n):
    out = [None] * len(x); a = 2 / (n + 1); p = None
    for i, v in enumerate(x):
        p = v if p is None else p + a * (v - p); out[i] = p
    return out


def indicators(b, V):
    C, H, L = b['close'], b['high'], b['low']; n = len(C)
    e12, e26 = ema(C, 12), ema(C, 26)
    macd = [a - c for a, c in zip(e12, e26)]; sig = ema(macd, 9); hist = [a - c for a, c in zip(macd, sig)]
    tr = [H[0] - L[0]] + [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, n)]
    pdm = [0] + [max(H[i] - H[i - 1], 0) if H[i] - H[i - 1] > L[i - 1] - L[i] else 0 for i in range(1, n)]
    mdm = [0] + [max(L[i - 1] - L[i], 0) if L[i - 1] - L[i] > H[i] - H[i - 1] else 0 for i in range(1, n)]
    def wild(x):
        out = [None] * n; s = None
        for i in range(1, n):
            if i < 14: continue
            s = sum(x[1:15]) if s is None else s - s / 14 + x[i]
            out[i] = s
        return out
    atr, pdi_, mdi_ = wild(tr), wild(pdm), wild(mdm)
    dx = [None] * n
    for i in range(n):
        if atr[i]:
            p, m = 100 * pdi_[i] / atr[i], 100 * mdi_[i] / atr[i]
            dx[i] = 0 if p + m == 0 else 100 * abs(p - m) / (p + m)
    adx = [None] * n; s = None; cnt = 0
    for i in range(n):
        if dx[i] is None: continue
        cnt += 1
        if cnt == 14: s = np.mean([d for d in dx[:i + 1] if d is not None][-14:])
        elif cnt > 14: s = (s * 13 + dx[i]) / 14
        adx[i] = s
    sma20 = E.sma(C, 20); pb = [None] * n
    for i in range(19, n):
        sd = float(np.std(C[i - 19:i + 1]))
        if sd > 0: pb[i] = (C[i] - (sma20[i] - 2 * sd)) / (4 * sd)
    ema20 = ema(C, 20)
    obv = [0.0]
    for i in range(1, n):
        v = V[i] or 0
        obv.append(obv[-1] + (v if C[i] > C[i - 1] else -v if C[i] < C[i - 1] else 0))
    obvs = E.sma(obv, 20)
    def mid(i, k):
        if i - k + 1 < 0: return None
        return (max(H[i - k + 1:i + 1]) + min(L[i - k + 1:i + 1])) / 2
    span_a = [None] * n; span_b = [None] * n
    for i in range(n):
        t, kj = mid(i, 9), mid(i, 26)
        if t is not None and kj is not None: span_a[i] = (t + kj) / 2
        span_b[i] = mid(i, 52)
    wr = [None] * n; cci = [None] * n
    tp = [(H[i] + L[i] + C[i]) / 3 for i in range(n)]
    for i in range(n):
        if i >= 13:
            hh, ll = max(H[i - 13:i + 1]), min(L[i - 13:i + 1])
            wr[i] = -100 * (hh - C[i]) / (hh - ll) if hh > ll else None
        if i >= 19:
            w = tp[i - 19:i + 1]; m = np.mean(w); md = np.mean([abs(x - m) for x in w])
            cci[i] = (tp[i] - m) / (0.015 * md) if md > 0 else None
    return dict(hist=hist, macd=macd, sig=sig, adx=adx, pb=pb, ema20=ema20, obv=obv, obvs=obvs,
                sa=span_a, sb=span_b, wr=wr, cci=cci)


def main():
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    dated = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            s, b = E.signals(f'data/{a}_{tf}.csv', regime=gate)
            dated[(a, tf)] = [bucket_end(b['date'], x['ei']) for x in s if bucket_end(b['date'], x['ei'])]
    rows = []
    for ch in CHARTS:
        a, tf = ch.split('_'); o = 'BTC' if a == 'ETH' else 'ETH'
        day = E.load(f'data/{a}_1D.csv'); P = {d: i for i, d in enumerate(day['date'])}; last = day['date'][-2]
        sma50 = E.sma(day['close'], 50)
        b8 = E.load(f'data/{a}_8D.csv'); ct8 = E.rsi(b8['close'], 14)
        sig, b = E.signals(f'data/{ch}.csv', regime=gate)
        V = vols(f'data/{ch}.csv'); I = indicators(b, V)
        ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
        prev_entry = None
        for s in sig:
            d0 = bucket_end(b['date'], s['ei']); ei, ti = s['ei'], s['ti']
            if d0 is None or d0 not in P or d0 + dt.timedelta(days=61) > last:
                prev_entry = s['entry']; continue
            m = measure(day, P, d0, s['entry'], 60)
            if not m:
                prev_entry = s['entry']; continue
            f = {}
            g = ct[ei] - em[ei] if ct[ei] is not None and em[ei] is not None else None
            f['gap>5'] = g is not None and g > 5
            f['CT>Signal'] = g is not None and g > 0
            f['prime'] = s['prime']; f['diamond'] = s['dis']
            f['bucket A'] = s['bk'] == 'A'; f['bucket A/B'] = s['bk'] in ('A', 'B')
            f['higher entry'] = prev_entry is not None and s['entry'] > prev_entry
            f['own agree 2+'] = sum(1 for t in ('1D', '2D', '3D', '5D', '8D') if t != tf and
                                    any(0 <= (d0 - x).days <= 10 for x in dated[(a, t)])) >= 2
            f['other asset 10d'] = any(any(0 <= (d0 - x).days <= 10 for x in dated[(o, t)]) for t in ('1D', '2D', '3D', '5D'))
            k8 = closed_index(b8['date'], d0)
            f['8D rising'] = k8 >= 1 and ct8[k8] is not None and ct8[k8 - 1] is not None and ct8[k8] > ct8[k8 - 1]
            f['MACD hist rising'] = I['hist'][ei] > I['hist'][ei - 1]
            f['MACD > signal'] = I['macd'][ei] > I['sig'][ei]
            f['ADX >= 25'] = I['adx'][ei] is not None and I['adx'][ei] >= 25
            f['BB %B < 0 at trough'] = I['pb'][ti] is not None and I['pb'][ti] < 0
            i0 = P[d0]
            f['above 50d avg'] = sma50[i0] is not None and day['close'][i0] > sma50[i0]
            f['above EMA20'] = b['close'][ei] > I['ema20'][ei]
            f['OBV > its avg'] = I['obvs'][ei] is not None and I['obv'][ei] > I['obvs'][ei]
            j = ei - 26
            f['above Ichimoku cloud'] = j >= 0 and I['sa'][j] is not None and I['sb'][j] is not None and \
                b['close'][ei] > max(I['sa'][j], I['sb'][j])
            f['W%R < -80 at trough'] = I['wr'][ti] is not None and I['wr'][ti] < -80
            f['CCI < -100 at trough'] = I['cci'][ti] is not None and I['cci'][ti] < -100
            e0 = s['entry']; sw = False
            for k in range(1, 61):
                j = P.get(d0 + dt.timedelta(days=k))
                if j is None:
                    continue
                if day['low'][j] <= e0 * 0.8:
                    break
                if day['high'][j] >= e0 * 1.2:
                    sw = True; break
            rows.append(dict(ch=ch, a=a, per='D' if d0 < SPLIT else 'H', win=m['up'] >= 20, f=f,
                             sw=sw, deep=m['dd'] <= -20, dd=m['dd']))
            prev_entry = s['entry']
    feats = list(rows[0]['f'].keys())
    combos = [(x,) for x in feats] + list(itertools.combinations(feats, 2))
    groups = {c.replace('_', ' '): [r for r in rows if r['ch'] == c] for c in CHARTS}
    groups['ETH pooled'] = [r for r in rows if r['a'] == 'ETH']; groups['BTC pooled'] = [r for r in rows if r['a'] == 'BTC']
    print('Unfiltered win rate (reach +20% in 60d) and winners, by group')
    for gname, G in groups.items():
        t = ''
        for per in ('D', 'H'):
            x = [r for r in G if r['per'] == per]
            t += f'  {"2016-21" if per=="D" else "2022-26"}: {100*np.mean([r["win"] for r in x]):.0f}% of {len(x)} ({sum(r["win"] for r in x)} winners)'
        print(f'  {gname:<11}' + t)
    meets = []; best = []
    for gname, G in groups.items():
        for cb in combos:
            res = {}
            for per in ('D', 'H'):
                x = [r for r in G if r['per'] == per]; W = sum(r['win'] for r in x)
                k = [r for r in x if all(r['f'][c] for c in cb)]
                if not k or not W:
                    res = None; break
                res[per] = (100 * np.mean([r['win'] for r in k]), 100 * sum(r['win'] for r in k) / W, len(k))
            if res is None:
                continue
            ok70 = all(res[p][0] >= 70 and res[p][1] >= 80 and res[p][2] >= 15 for p in res)
            ok80 = ok70 and all(res[p][0] >= 80 for p in res)
            if ok70:
                meets.append((gname, cb, res, ok80))
            if all(res[p][2] >= 15 for p in res):
                best.append((min(res['D'][0], res['H'][0]), gname, cb, res))
    print(f'\nTested {len(combos)} combos x {len(groups)} groups = {len(combos)*len(groups)}')
    print('\nMEETS THE STANDARD (>=70% win, keeps >=80% of winners, both periods):')
    if not meets:
        print('  none')
    for gname, cb, res, ok80 in meets:
        print(f'  {gname:<11} {" + ".join(cb):<45} 2016-21 {res["D"][0]:.0f}% keeps {res["D"][1]:.0f}% (n={res["D"][2]})  '
              f'2022-26 {res["H"][0]:.0f}% keeps {res["H"][1]:.0f}% (n={res["H"][2]})' + ('  MEETS 80' if ok80 else ''))
    print('\nCLOSEST: best worst-period win rate with n>=15 in both periods (any winner retention)')
    for w, gname, cb, res in sorted(best, key=lambda x: -x[0])[:15]:
        print(f'  {gname:<11} {" + ".join(cb):<45} 2016-21 {res["D"][0]:.0f}% keeps {res["D"][1]:.0f}% (n={res["D"][2]})  '
              f'2022-26 {res["H"][0]:.0f}% keeps {res["H"][1]:.0f}% (n={res["H"][2]})')
    print('\n==================== SECOND BLOCK: leverage-aware')
    print('Unfiltered: safe-win rate (+20% before -20%), deep-loss rate (touched -20%), by group')
    for gname, G in groups.items():
        t = ''
        for per in ('D', 'H'):
            x = [r for r in G if r['per'] == per]
            t += (f'  {"2016-21" if per=="D" else "2022-26"}: safe win {100*np.mean([r["sw"] for r in x]):.0f}%, '
                  f'deep {100*np.mean([r["deep"] for r in x]):.0f}%, -30% {100*np.mean([r["dd"]<=-30 for r in x]):.0f}% (n={len(x)})')
        print(f'  {gname:<11}' + t)
    s1 = []; s2 = []; fr = []
    for gname, G in groups.items():
        for cb in combos:
            res = {}
            for per in ('D', 'H'):
                x = [r for r in G if r['per'] == per]
                SW = sum(r['sw'] for r in x); DP = sum(r['deep'] for r in x)
                k = [r for r in x if all(r['f'][c] for c in cb)]
                if not k or not SW or not DP:
                    res = None; break
                res[per] = dict(rate=100 * np.mean([r['sw'] for r in k]), keep=100 * sum(r['sw'] for r in k) / SW,
                                cut=100 - 100 * sum(r['deep'] for r in k) / DP, n=len(k),
                                d30=100 * np.mean([r['dd'] <= -30 for r in k]), deep=100 * np.mean([r['deep'] for r in k]))
            if res is None or not all(res[p]['n'] >= 15 for p in res):
                continue
            if all(res[p]['rate'] >= 70 and res[p]['keep'] >= 80 for p in res):
                s1.append((gname, cb, res))
            if all(res[p]['keep'] >= 80 and res[p]['cut'] >= 80 for p in res):
                s2.append((gname, cb, res))
            fr.append((gname, cb, res))
    fmt = lambda r: (f'safe win {r["rate"]:.0f}% keeps {r["keep"]:.0f}% of safe winners, cuts {r["cut"]:.0f}% of deep losses, '
                     f'touched -20% {r["deep"]:.0f}% / -30% {r["d30"]:.0f}% (n={r["n"]})')
    print('\nS1 (>=70% safe win, keeps >=80% of safe winners, both periods): ' + ('none' if not s1 else ''))
    for g, cb, r in s1:
        print(f'  {g:<11} {" + ".join(cb):<40} 2016-21 {fmt(r["D"])}\n  {"":<52}2022-26 {fmt(r["H"])}')
    print('S2 (keeps >=80% of safe winners AND cuts >=80% of deep losses, both periods): ' + ('none' if not s2 else ''))
    for g, cb, r in s2:
        print(f'  {g:<11} {" + ".join(cb):<40} 2016-21 {fmt(r["D"])}\n  {"":<52}2022-26 {fmt(r["H"])}')
    print('\nCLOSEST on the ratio: highest worst-period (deep losses cut - safe winners lost), n>=15 both periods')
    sc = lambda r: min(r['D']['cut'] - (100 - r['D']['keep']), r['H']['cut'] - (100 - r['H']['keep']))
    for g, cb, r in sorted(fr, key=lambda x: -sc(x[2]))[:12]:
        print(f'  {g:<11} {" + ".join(cb):<40} 2016-21 {fmt(r["D"])}\n  {"":<52}2022-26 {fmt(r["H"])}')
    print('\nCLOSEST on safe-win rate: highest worst-period safe-win rate, n>=15 both periods')
    for g, cb, r in sorted(fr, key=lambda x: -min(x[2]['D']['rate'], x[2]['H']['rate']))[:10]:
        print(f'  {g:<11} {" + ".join(cb):<40} 2016-21 {fmt(r["D"])}\n  {"":<52}2022-26 {fmt(r["H"])}')
    print('\nCLOSEST that keep >= 80% of winners in both periods (any win rate)')
    k80 = [x for x in best if x[3]['D'][1] >= 80 and x[3]['H'][1] >= 80 and len(x[2]) >= 1]
    for w, gname, cb, res in sorted(k80, key=lambda x: -x[0])[:10]:
        print(f'  {gname:<11} {" + ".join(cb):<45} 2016-21 {res["D"][0]:.0f}% keeps {res["D"][1]:.0f}% (n={res["D"][2]})  '
              f'2022-26 {res["H"][0]:.0f}% keeps {res["H"][1]:.0f}% (n={res["H"][2]})')


if __name__ == '__main__':
    main()
