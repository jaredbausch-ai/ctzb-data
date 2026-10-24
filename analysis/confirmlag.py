"""Does waiting for the 3-bar confirmation cost more than it saves?

Asked 23 Oct 2026 about ETH 2W: "if you bought on the symbol printing, the
two-week would be pretty astonishing ... profitable at some point from the
symbol printing at that moment of buying."

The symbol is drawn on the trough bar (v15 line 487, label.new(pvB, ...)) but
it only appears 3 bars later. On 2W that is 6 weeks. So the price under the
symbol was never buyable when the symbol was on the chart.

DECLARED BEFORE RUNNING
  Entry points, each measured from its own price:
    T0  close of the trough bar. Hindsight: only troughs that went on to
        confirm, which is unknowable on that bar. Shown because it is what the
        chart appears to show.
    P1  close of trough+1, when CT has turned up for one bar. Includes the
        ones that never confirmed.
    P2  close of trough+2, CT held above the low for two bars. Includes fails.
    C3  close of trough+3 = the confirmation bar. Today's rule.
  Charts: ETH and BTC 1D 2D 3D 5D 8D (data/), 1W and 2W built from the
  Coinbase daily file. TradingView's 2W anchor is unverified, so 2W is run on
  both week pairings (2W-a, 2W-b).
  Gate: R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41) on the trough date,
  same as engine.signals. Ungated shown for 2W only, as a labelled variant.
  Metrics, daily candles, window 365 days after entry, full windows only:
    ever above entry, ever +10%, ever +20%, median peak gain, median worst
    drawdown below entry before the peak, share that fell 20% / 30% below
    entry before the peak.
  Also: share of P1 / P2 entries that never confirmed, and how much cheaper
  each early entry was than the confirmation close when it did confirm.

ENTRY QUALITY ONLY. No exit, so no strategy return. Signals are computed,
never fills.
  python3 -I analysis/confirmlag.py
"""
import sys, os, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end

WIN = 365
GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)


def from_file(path):
    b = E.load(path)
    ends = [bucket_end(b['date'], j) for j in range(len(b['date']))]
    return dict(date=b['date'], end=ends, high=b['high'], low=b['low'], close=b['close'])


def weekly(day, weeks, offset=0):
    """Monday-anchored weeks from the daily file; 2W pairs weeks by
    (week_number + offset) // 2. Drops the forming bar."""
    ep = dt.date(1970, 1, 5)  # a Monday
    g = {}
    for k, d in enumerate(day['date']):
        w = ((d - ep).days // 7 + offset) // weeks
        g.setdefault(w, []).append(k)
    out = dict(date=[], end=[], high=[], low=[], close=[])
    for w in sorted(g):
        ks = g[w]
        start = ep + dt.timedelta(days=7 * (w * weeks - offset))
        end = start + dt.timedelta(days=7 * weeks - 1)
        if day['date'][ks[-1]] != end:
            continue  # partial (first or forming) bar
        out['date'].append(start); out['end'].append(end)
        out['high'].append(max(day['high'][k] for k in ks))
        out['low'].append(min(day['low'][k] for k in ks))
        out['close'].append(day['close'][ks[-1]])
    return out


def entries(b, gate):
    c = b['close']; n = len(c)
    ct = E.rsi(c, 14); kL = E.sma(E.stoch_of(ct, 14), 3)
    rows = []
    for t in range(3, n):
        v = ct[t]
        if v is None or kL[t] is None or any(ct[j] is None for j in range(t - 3, t)):
            continue
        if any(ct[j] <= v for j in range(t - 3, t)):
            continue
        if gate and not GATE(b['date'][t]):
            continue
        held = 0
        for j in range(t + 1, min(t + 4, n)):
            if ct[j] is None or ct[j] <= v:
                break
            held += 1
        if t + 3 >= n and held == n - 1 - t:
            continue  # still undecided
        conf = held >= 3
        cp = c[t + 3] if conf else None
        for lab, off in (('T0', 0), ('P1', 1), ('P2', 2), ('C3', 3)):
            if off > held or (lab == 'T0' and not conf):
                continue
            if t + off >= n or b['end'][t + off] is None:
                continue
            rows.append(dict(kind=lab, t=t, end=b['end'][t + off], px=c[t + off],
                             conf=conf, cp=cp, bk='A' if v < 40 else 'B' if v < 55 else 'C' if v < 65 else 'D'))
    return rows


def measure(day, pos, d0, c0):
    i = pos.get(d0)
    if i is None:
        return None
    end = d0 + dt.timedelta(days=WIN)
    w = [k for k in range(i + 1, len(day['date'])) if day['date'][k] <= end]
    if not w or day['date'][w[-1]] < end:
        return None
    hi = [day['high'][k] for k in w]
    kp = w[max(range(len(hi)), key=lambda x: hi[x])]
    pre = min(day['low'][k] for k in w if k <= kp)
    pk = max(hi)
    return dict(green=pk > c0, g10=pk >= c0 * 1.1, g20=pk >= c0 * 1.2,
                peak=100 * (pk / c0 - 1), dd=min(0.0, 100 * (pre / c0 - 1)))


def summarise(rows, day, pos):
    res = {}
    for lab in ('T0', 'P1', 'P2', 'C3'):
        rs = [r for r in rows if r['kind'] == lab]
        m = [(r, measure(day, pos, r['end'], r['px'])) for r in rs]
        m = [(r, x) for r, x in m if x]
        if not m:
            res[lab] = None; continue
        X = [x for _, x in m]; N = len(X)
        fails = sum(1 for r, _ in m if not r['conf'])
        cheap = [100 * (r['cp'] / r['px'] - 1) for r, _ in m if r['conf'] and lab != 'C3']
        res[lab] = dict(n=N, green=100 * sum(x['green'] for x in X) / N,
                        g10=100 * sum(x['g10'] for x in X) / N, g20=100 * sum(x['g20'] for x in X) / N,
                        peak=st.median(x['peak'] for x in X), dd=st.median(x['dd'] for x in X),
                        dd20=100 * sum(x['dd'] <= -20 for x in X) / N, dd30=100 * sum(x['dd'] <= -30 for x in X) / N,
                        fail=100 * fails / N, saved=st.median(cheap) if cheap else None,
                        failrows=[x for r, x in m if not r['conf']])
    return res


def table(title, res):
    print(f'\n{title}')
    print(f'  {"entry":<6}{"n":>4}{"ever green":>12}{"ever +10%":>11}{"ever +20%":>11}{"med peak":>10}'
          f'{"med dd":>9}{"dd<=-20":>9}{"dd<=-30":>9}{"never conf":>12}{"conf px above":>15}')
    for lab, r in res.items():
        if not r:
            print(f'  {lab:<6}   0'); continue
        sv = f'{r["saved"]:+.1f}%' if r['saved'] is not None else '-'
        print(f'  {lab:<6}{r["n"]:>4}{r["green"]:>11.0f}%{r["g10"]:>10.0f}%{r["g20"]:>10.0f}%{r["peak"]:>+9.0f}%'
              f'{r["dd"]:>+8.1f}%{r["dd20"]:>8.0f}%{r["dd30"]:>8.0f}%{r["fail"]:>11.0f}%{sv:>15}')
    for lab in ('P1', 'P2'):
        r = res.get(lab)
        if r and r['failrows']:
            F = r['failrows']
            print(f'    {lab} that never confirmed: n={len(F)}  ever green {100*sum(x["green"] for x in F)/len(F):.0f}%  '
                  f'ever +20% {100*sum(x["g20"] for x in F)/len(F):.0f}%  med dd {st.median(x["dd"] for x in F):+.1f}%  '
                  f'dd<=-30 {100*sum(x["dd"]<=-30 for x in F)/len(F):.0f}%')


def listing(rows, day, pos, b):
    print('  trough bar   T0 price  P1 price  C3 price  conf   T0 peak/dd     C3 peak/dd')
    by = {}
    for r in rows:
        by.setdefault(r['t'], {})[r['kind']] = r
    for t in sorted(by):
        g = by[t]
        def s(k):
            r = g.get(k)
            if not r: return '-'
            x = measure(day, pos, r['end'], r['px'])
            return 'open' if not x else f'{x["peak"]:+.0f}% / {x["dd"]:+.0f}%'
        px = lambda k: f'{g[k]["px"]:,.0f}' if k in g else '-'
        anyr = next(iter(g.values()))
        print(f'  {b["date"][t]}  {px("T0"):>9} {px("P1"):>9} {px("C3"):>9}  {"yes" if anyr["conf"] else "no ":<4}  '
              f'{s("T0"):<14} {s("C3")}')


def main():
    for a in ('ETH', 'BTC'):
        day = E.load(f'data/{a}_1D.csv'); pos = {d: k for k, d in enumerate(day['date'])}
        charts = [(tf, from_file(f'data/{a}_{tf}.csv')) for tf in ('1D', '2D', '3D', '5D', '8D')]
        charts += [('1W', weekly(day, 1)), ('2W-a', weekly(day, 2, 0)), ('2W-b', weekly(day, 2, 1))]
        print(f'\n==================== {a}  (gated, {WIN}-day window, full windows only)')
        for tf, b in charts:
            table(f'{a} {tf}', summarise(entries(b, True), day, pos))
        for tf, b in charts[-2:]:
            table(f'{a} {tf} UNGATED (variant)', summarise(entries(b, False), day, pos))
        if a == 'ETH':
            for tf, b in charts[-2:]:
                print(f'\n{a} {tf} every gated trough')
                listing(entries(b, True), day, pos, b)


if __name__ == '__main__':
    main()
