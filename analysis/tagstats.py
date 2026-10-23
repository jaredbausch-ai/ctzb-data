"""Entry-quality statistics for one tag on one chart, against that chart's baseline.

  python3 -I analysis/tagstats.py --chart BTC_5D --bucket C --diamond hollow

Signals: engine.signals(data/<chart>.csv, regime = R.rsi_regime(BTC_2D,8,13,60,41)),
entry = close of the confirmation bar (ei = ti + 3), dated by the confirmation
bar. Paths are measured on DAILY candles from the day that bar closes (the last
day of its bucket), so drawdown depth and day counts are exact to the day.

Per signal, for H = 30 / 60 / 90 calendar days (only if the window is complete):
  ret     close H days after entry vs entry
  up      best high within H days (max favourable)
  dd      worst low within H days (max adverse)          <- drawdown from entry
  ddpk    worst low BEFORE the H-day high                <- what you sit through
  dpk     days to the H-day high
  ddday   days to the worst low
  hit     reached +10 / +20 / +30% within H days
  dead    fell -30% before ever gaining +5% (troughs.py definition), within 365d
Also the -10% / -20% touch rate within H days.

Entry quality only: there is no exit, so nothing here is a strategy return.
Signals are computed, never fills.
"""
import sys, os, argparse, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine as E, regimes as R

HS = (30, 60, 90)


def bucket_end(bdates, j):
    return bdates[j + 1] - dt.timedelta(days=1) if j + 1 < len(bdates) else None


def measure(day, pos, d0, c0, H):
    i = pos[d0]; end = d0 + dt.timedelta(days=H)
    w = [k for k in range(i + 1, len(day['date'])) if day['date'][k] <= end]
    if not w or day['date'][w[-1]] < end or w[-1] == len(day['date']) - 1 and day['date'][-1] == end and False:
        return None
    hi = [day['high'][k] for k in w]; lo = [day['low'][k] for k in w]
    kp = w[int(np.argmax(hi))]; kl = w[int(np.argmin(lo))]
    pre = [day['low'][k] for k in w if k <= kp]
    return dict(ret=(day['close'][w[-1]] / c0 - 1) * 100, up=(max(hi) / c0 - 1) * 100,
                dd=(min(lo) / c0 - 1) * 100, ddpk=(min(pre) / c0 - 1) * 100 if pre else 0.0,
                dpk=(day['date'][kp] - d0).days, ddday=(day['date'][kl] - d0).days)


def dead(day, pos, d0, c0):
    i = pos[d0]
    for k in range(i + 1, len(day['date'])):
        if (day['date'][k] - d0).days > 365:
            return None
        if day['high'][k] >= c0 * 1.05:
            return None
        if day['low'][k] <= c0 * 0.70:
            return (day['date'][k] - d0).days
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', default='BTC_5D'); ap.add_argument('--bucket', default='C')
    ap.add_argument('--diamond', default='hollow', choices=['hollow', 'filled', 'any', 'none'])
    a = ap.parse_args()
    sym = a.chart.split('_')[0]
    gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    sig, b = E.signals(f'data/{a.chart}.csv', regime=gate)
    day = E.load(f'data/{sym}_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}
    last_closed = day['date'][-2]
    rows = []
    for k, s in enumerate(sig):
        d0 = bucket_end(b['date'], s['ei'])
        if d0 is None or d0 > last_closed:
            continue
        c0 = s['entry']
        assert abs(day['close'][pos[d0]] - c0) < 1e-6 * c0, (s['edate'], d0)
        r = dict(s=s, d0=d0, c0=c0, step=(c0 / sig[k - 1]['entry'] - 1) * 100 if k else None,
                 dead=dead(day, pos, d0, c0))
        for H in HS:
            r[H] = measure(day, pos, d0, c0, H)
        rows.append(r)

    def want(r):
        s = r['s']
        if a.bucket != 'any' and s['bk'] != a.bucket:
            return False
        if a.diamond == 'none':
            return not s['dis']
        if a.diamond == 'any':
            return s['dis']
        if a.diamond == 'hollow':
            return s['dis'] and not s['strong']
        return s['dis'] and s['strong']

    tag = [r for r in rows if want(r)]
    name = f"{a.chart.replace('_', ' ')} {a.bucket} {a.diamond} diamond"

    def block(sel, H):
        x = [r[H] for r in sel if r[H]]
        if not x:
            return None
        g = lambda k: np.array([v[k] for v in x])
        ret, up, dd, ddpk = g('ret'), g('up'), g('dd'), g('ddpk')
        return dict(n=len(x), win=100 * np.mean(ret > 0), ret=np.median(ret), up=np.median(up),
                    dd=np.median(dd), ddw=dd.min(), ddq=np.percentile(dd, 25), ddpk=np.median(ddpk),
                    dpk=np.median(g('dpk')), ddday=np.median(g('ddday')),
                    h10=100 * np.mean(up >= 10), h20=100 * np.mean(up >= 20), h30=100 * np.mean(up >= 30),
                    l10=100 * np.mean(dd <= -10), l20=100 * np.mean(dd <= -20))

    print(f'{name}: {len(tag)} signals (gated), baseline all {a.chart.replace("_"," ")} signals: {len(rows)}')
    print(f'{"":<10}{"n":>4}{"up%":>6}{"medret":>8}{"medUp":>7}{"medDD":>7}{"DD25":>7}{"worstDD":>8}{"DDpk":>7}'
          f'{"dPk":>5}{"dDD":>5}{"+10":>5}{"+20":>5}{"+30":>5}{"-10":>5}{"-20":>5}')
    for H in HS:
        for lab, sel in (('TAG', tag), ('BASE', rows)):
            s = block(sel, H)
            if s:
                print(f'{lab+" "+str(H)+"d":<10}{s["n"]:>4}{s["win"]:>6.0f}{s["ret"]:>+8.1f}{s["up"]:>+7.1f}{s["dd"]:>+7.1f}'
                      f'{s["ddq"]:>+7.1f}{s["ddw"]:>+8.1f}{s["ddpk"]:>+7.1f}{s["dpk"]:>5.0f}{s["ddday"]:>5.0f}'
                      f'{s["h10"]:>5.0f}{s["h20"]:>5.0f}{s["h30"]:>5.0f}{s["l10"]:>5.0f}{s["l20"]:>5.0f}')
    for lab, sel in (('TAG', tag), ('BASE', rows)):
        dn = [r for r in sel if r['dead'] is not None]
        print(f'{lab} dead (-30% before +5%, within a year): {len(dn)} of {len(sel)}')
    print('\nEVERY SIGNAL')
    print(f'{"entry date":<12}{"entry":>10}{"CT":>6}{"K":>6} {"prime":<6}{"step":>7}  '
          f'{"60d ret":>8}{"60d up":>8}{"60d DD":>8}{"DD pre-pk":>10}{"90d ret":>8}{"90d DD":>8}')
    for r in tag:
        s = r['s']; m6 = r[60]; m9 = r[90]
        f = lambda m, k: f'{m[k]:+.1f}%' if m else '-'
        print(f'{str(s["edate"]):<12}{r["c0"]:>10,.0f}{s["ct"]:>6.1f}{s["k"]:>6.1f} {("yes" if s["prime"] else "no"):<6}'
              f'{(f"{r[chr(115)+chr(116)+chr(101)+chr(112)]:+.1f}%" if r["step"] is not None else "-"):>7}  '
              f'{f(m6,"ret"):>8}{f(m6,"up"):>8}{f(m6,"dd"):>8}{f(m6,"ddpk"):>10}{f(m9,"ret"):>8}{f(m9,"dd"):>8}')
    pend = [r for r in tag if not r[90]]
    if pend:
        print('signals without a full 90-day window: ' + ', '.join(str(r['s']['edate']) for r in pend))


if __name__ == '__main__':
    main()
