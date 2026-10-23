"""Python mirror of pine/ctzb_forecast_cone.pine, bar for bar.

Exists so the Pine indicator can be checked against known numbers: paste the
indicator on COINBASE:ETHUSD 1D and its table should match what this prints,
apart from the few days the chart has gained since the date given here.

Semantics, identical to the Pine:
  bars      ETH daily bars; the horizon H is H bars (crypto trades every day)
  clamp     a low below half the bar's body, or a high above twice it, is
            pulled back to the body (engine.load does this; the Pine repeats it)
  vol       population stdev of the last 30 daily log returns. The scale
            cancels between the pool and the forecast, so sample vs population
            makes no difference to any output
  gate      R.rsi_regime state machine on BTC 2D CT RSI (8 bars >= 60 on,
            13 bars < 41 off), read from the PREVIOUS completed 2D bar of the
            one containing the day -- request.security(..., st[1],
            lookahead_on). This lags analysis/fullhistory.py by one day on the
            last day of each 2D bucket
  forecast  on bar i: pool = past outcomes of the same gate state, inserted
            only after their H bars closed, so the newest pool day is i-H-1.
            Quantiles use numpy's linear method on z = log-return / (vol*sqrt H),
            rescaled by today's vol. Shown once the pool holds 200
  score     on bar i, the forecast made at i-H is scored against close[i]
  insert    after forecasting, the outcome of bar i-H joins its gate's pool

Differences from TradingView that cannot be removed here: TradingView's BTC
history starts in 2014 and this repo's in 2016, so the gate's RSI warm-up can
differ in early 2016; the ETH 1D bars were checked identical to the cent.

Run from the repo root:  python3 -I analysis/cone_mirror.py [--asof YYYY-MM-DD]
"""
import sys, os, math, bisect, argparse, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E

HS = (14, 30, 60, 90)
VOLN = 30
MINPOOL = 200


def gate_series(day_dates):
    b = E.load('data/BTC_2D.csv')
    ct = E.rsi(b['close'], 14)
    st = False; up = dn = 0; states = []
    for v in ct:
        up = up + 1 if (v is not None and v >= 60) else 0
        dn = dn + 1 if (v is not None and v < 41) else 0
        if not st and up >= 8:
            st = True; dn = 0
        elif st and dn >= 13:
            st = False; up = 0
        states.append(st)
    key = lambda d: (d.year, (d.timetuple().tm_yday - 1) // 2)
    idx = {key(d): j for j, d in enumerate(b['date'])}
    out = []
    for d in day_dates:
        j = idx.get(key(d))
        out.append(states[j - 1] if j is not None and j >= 1 else None)
    return out


def qlin(a, p):
    n = len(a); pos = p / 100 * (n - 1); lo = int(math.floor(pos)); hi = min(lo + 1, n - 1)
    return a[lo] + (a[hi] - a[lo]) * (pos - lo)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--asof'); a = ap.parse_args()
    day = E.load('data/ETH_1D.csv')
    D, c, h, l = day['date'][:-1], day['close'][:-1], day['high'][:-1], day['low'][:-1]  # drop the forming bar
    if a.asof:
        k = D.index(dt.date.fromisoformat(a.asof)) + 1
        D, c, h, l = D[:k], c[:k], h[:k], l[:k]
    n = len(D)
    lr = [None] + [math.log(c[i] / c[i - 1]) for i in range(1, n)]
    vol = [None] * n
    for i in range(VOLN, n):
        vol[i] = float(np.std(lr[i - VOLN + 1:i + 1]))
    gate = gate_series(D)
    pools = {(H, g): ([], [], []) for H in HS for g in (True, False)}
    fc = {H: [None] * n for H in HS}
    stats = {H: dict(n=0, mid=0, wide=0, below=0, above=0) for H in HS}
    for i in range(n):
        for H in HS:
            g = gate[i]
            if g is not None and vol[i] is not None:
                zr, zf, za = pools[(H, g)]
                if len(zr) >= MINPOOL:
                    s0 = vol[i] * math.sqrt(H)
                    q = {p: c[i] * math.exp(qlin(zr, p) * s0) for p in (5, 25, 50, 75, 95)}
                    q['u10'] = (len(zf) - bisect.bisect_left(zf, math.log(1.10) / s0)) / len(zf)
                    q['d10'] = bisect.bisect_right(za, math.log(0.90) / s0) / len(za)
                    q['u20'] = (len(zf) - bisect.bisect_left(zf, math.log(1.20) / s0)) / len(zf)
                    q['d20'] = bisect.bisect_right(za, math.log(0.80) / s0) / len(za)
                    fc[H][i] = q
            if i >= H and fc[H][i - H] is not None:
                f = fc[H][i - H]; s = stats[H]; s['n'] += 1
                if f[25] <= c[i] <= f[75]:
                    s['mid'] += 1
                if c[i] < f[5]:
                    s['below'] += 1
                elif c[i] > f[95]:
                    s['above'] += 1
                else:
                    s['wide'] += 1
            j = i - H
            if j >= 0 and vol[j] is not None and gate[j] is not None:
                sd = vol[j] * math.sqrt(H)
                zr, zf, za = pools[(H, gate[j])]
                bisect.insort(zr, math.log(c[i] / c[j]) / sd)
                bisect.insort(zf, math.log(max(h[j + 1:i + 1]) / c[j]) / sd)
                bisect.insort(za, math.log(min(l[j + 1:i + 1]) / c[j]) / sd)
    i = n - 1
    print(f'ETH as of the {D[i]} close  {c[i]:,.2f}   gate {"ON" if gate[i] else "OFF"}   '
          f'30d vol {100*vol[i]:.2f}%/day')
    print(f'{"H":>3} {"p5":>8} {"p25":>8} {"median":>8} {"p75":>8} {"p95":>8}  +10% -10% +20% -20%   '
          f'track record: in middle half / in wide band / below / above  (n)')
    for H in HS:
        q = fc[H][i]; s = stats[H]
        print(f'{H:>3} {q[5]:>8,.0f} {q[25]:>8,.0f} {q[50]:>8,.0f} {q[75]:>8,.0f} {q[95]:>8,.0f}  '
              f'{100*q["u10"]:3.0f}% {100*q["d10"]:3.0f}% {100*q["u20"]:3.0f}% {100*q["d20"]:3.0f}%   '
              f'{100*s["mid"]/s["n"]:5.1f}% / {100*s["wide"]/s["n"]:5.1f}% / {100*s["below"]/s["n"]:4.1f}% / '
              f'{100*s["above"]/s["n"]:4.1f}%  ({s["n"]})')


if __name__ == '__main__':
    main()
