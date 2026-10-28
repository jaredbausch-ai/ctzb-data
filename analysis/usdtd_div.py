"""USDT dominance 2D: bearish stochastic divergence and CT RSI rejected at the 50 line.
DECLARED 28 Oct 2026 15:30 ET, before running. Jared's question: USDT.D on the 2D is
showing stochastic divergence and CT RSI failing at 50 from below; does that play out?

DATA  data/ext/USDT.D_2D.csv, his TradingView export (CRYPTOCAP:USDT.D, 2D) with his
      CT RSI and Stoch %K columns as plotted. Bar time = bar open; a bar's close date is
      open + 2 days. Only closed bars are tested. ETH and BTC daily closes from data/.
EVENTS (all known at the close of bar t)
  DIV  bearish stochastic divergence: bar p is a Stoch %K peak (K[p] > K[p-1] and
       K[p] >= K[p+1]), K[p] >= 70, confirmed at t = p+1. The previous such peak q lies
       3-20 bars earlier, K[q] > K[p], and the highest high of bars p-2..p is above the
       highest high of bars q-2..q (price higher high, Stoch lower high).
  REJ  CT RSI rejected at 50 from below: CT[t] < 50; the highest CT of bars t-3..t-1 is
       between 48 and 53 (it reached the 50 line); CT was below 45 on at least one of
       the 15 bars before that (it came up from below); and CT[t] is at least 2 points
       under that high.
  BOTH a DIV and a REJ both fired within the last 3 bars (t-2..t), dated at the later.
  Events of the same kind within 10 bars of a previous one are the same episode; only
  the first counts.
OUTCOMES from the close of bar t, against every closed 2D bar as the baseline:
  USDT.D close change after 10 / 20 / 30 bars (20 / 40 / 60 days), and % lower.
  ETH and BTC close change after 20 / 40 / 60 days, % higher, and for 60 days the
  largest rise and the largest drop from that close.
SPLITS  to 2021 vs 2022 on; list every BOTH event with its date.
READ    descriptive. Nothing is adopted into the grade from this. This is not an entry
        signal and says nothing about exits.
  python3 -I analysis/usdtd_div.py -> analysis/RESULTS_usdtd_div.txt
"""
import csv, os, sys, datetime as dt, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
SPLIT = dt.date(2022, 1, 1)


def load_dom():
    B = []
    for r in list(csv.reader(open(os.path.join(ROOT, 'data/ext/USDT.D_2D.csv'))))[1:]:
        if r[8] == '' or r[10] == '': continue
        o = dt.datetime.fromtimestamp(int(r[0]), dt.timezone.utc).date()
        B.append(dict(d=o + dt.timedelta(days=2), h=float(r[2]), c=float(r[4]), ct=float(r[8]), k=float(r[10])))
    return B[:-1]          # last bar is still forming


def load_px(a):
    out = {}
    for r in csv.DictReader(open(os.path.join(ROOT, f'data/{a}_1D.csv'))):
        out[dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date()] = (float(r['high']), float(r['low']), float(r['close']))
    return out


def events(B):
    n = len(B); div, rej = set(), set()
    peaks = [p for p in range(1, n - 1) if B[p]['k'] > B[p - 1]['k'] and B[p]['k'] >= B[p + 1]['k'] and B[p]['k'] >= 70]
    for j, p in enumerate(peaks):
        for q in reversed(peaks[:j]):
            if p - q < 3: continue
            if p - q > 20: break
            hp = max(B[i]['h'] for i in range(max(0, p - 2), p + 1)); hq = max(B[i]['h'] for i in range(max(0, q - 2), q + 1))
            if B[q]['k'] > B[p]['k'] and hp > hq: div.add(p + 1)
            break
    for t in range(18, n):
        hi = max(B[i]['ct'] for i in range(t - 3, t))
        ti = max(range(t - 3, t), key=lambda i: B[i]['ct'])
        if B[t]['ct'] < 50 and 48 <= hi <= 53 and B[t]['ct'] <= hi - 2 and any(B[i]['ct'] < 45 for i in range(ti - 15, ti)):
            rej.add(t)
    both = {t for t in range(n) if any(i in div for i in range(t - 2, t + 1)) and any(i in rej for i in range(t - 2, t + 1)) and (t in div or t in rej)}
    def dedupe(s):
        out, last = [], -99
        for t in sorted(s):
            if t - last > 10: out.append(t)
            last = t
        return out
    return dict(DIV=dedupe(div), REJ=dedupe(rej), BOTH=dedupe(both))


def outcome(B, t, PX):
    o = {}
    for h in (10, 20, 30):
        if t + h < len(B): o[f'dom{h}'] = 100 * (B[t + h]['c'] / B[t]['c'] - 1)
    d0 = B[t]['d']
    for a, px in PX.items():
        if d0 not in px: continue
        c0 = px[d0][2]
        for h in (20, 40, 60):
            d = d0 + dt.timedelta(days=h)
            if d in px: o[f'{a}{h}'] = 100 * (px[d][2] / c0 - 1)
        win = [px[d0 + dt.timedelta(days=k)] for k in range(1, 61) if d0 + dt.timedelta(days=k) in px]
        if len(win) == 60:
            o[f'{a}up'] = 100 * (max(x[0] for x in win) / c0 - 1); o[f'{a}dn'] = 100 * (min(x[1] for x in win) / c0 - 1)
    return o


def summ(name, idx, B, PX):
    O = [outcome(B, t, PX) for t in idx]
    def med(k): v = [o[k] for o in O if k in o]; return (st.median(v), len(v)) if v else (None, 0)
    def pct(k, sign): v = [o[k] for o in O if k in o]; return (100 * sum((x < 0) if sign < 0 else (x > 0) for x in v) / len(v)) if v else None
    m = lambda k: '   -  ' if med(k)[0] is None else f'{med(k)[0]:+6.1f}'
    p = lambda k, s: '  - ' if pct(k, s) is None else f'{pct(k, s):3.0f}%'
    P(f'  {name:26} n={len(idx):4} | USDT.D 20d {m("dom10")} 40d {m("dom20")} 60d {m("dom30")} lower@60d {p("dom30", -1)}')
    for a in ('ETH', 'BTC'):
        P(f'  {"":26}        | {a} 20d {m(a+"20")} 40d {m(a+"40")} 60d {m(a+"60")} up@60d {p(a+"60", 1)} | 60d best {m(a+"up")} worst {m(a+"dn")}')


def main():
    B = load_dom(); PX = {a: load_px(a) for a in ('ETH', 'BTC')}
    E = events(B)
    P('USDT DOMINANCE 2D: STOCH DIVERGENCE + CT RSI REJECTED AT 50 -- declared 28 Oct 2026, run', dt.date.today())
    P(f'{B[0]["d"]} to {B[-1]["d"]} ({len(B)} closed 2D bars). Descriptive context, not an entry signal.\n')
    allb = list(range(len(B)))
    for lab, sel in (('ALL YEARS', lambda t: True), ('to 2021', lambda t: B[t]['d'] < SPLIT), ('2022 on', lambda t: B[t]['d'] >= SPLIT)):
        P(lab)
        summ('every 2D bar (baseline)', [t for t in allb if sel(t)], B, PX)
        for k in ('DIV', 'REJ', 'BOTH'):
            summ({'DIV': 'stoch divergence', 'REJ': 'CT rejected at 50', 'BOTH': 'both together'}[k], [t for t in E[k] if sel(t)], B, PX)
        P('')
    P('EVERY "BOTH" EVENT (close date | USDT.D 60d | ETH 60d, best, worst | BTC 60d)')
    for t in E['BOTH']:
        o = outcome(B, t, PX); f = lambda k: f'{o[k]:+6.1f}' if k in o else '    - '
        P(f'  {B[t]["d"]}  CT {B[t]["ct"]:4.1f} K {B[t]["k"]:5.1f} | {f("dom30")} | {f("ETH60")} {f("ETHup")} {f("ETHdn")} | {f("BTC60")}')
    P('\n  Context only. Nothing adopted. Entry quality work is unaffected.')
    open(os.path.join(ROOT, 'analysis/RESULTS_usdtd_div.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
