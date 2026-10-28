"""Krown-style put/call events, as context next to CTZB. DECLARED 27 Oct 2026
21:35 ET, before any put/call data was in the repo. Jared's framing: not a
filter, not a win-rate hunt. Two questions:

 Q1 CONFLUENCE. When one of our better-graded setups prints, how often is a
    Krown-style put/call extreme also firing, and how do the overlaps turn out?
 Q2 HIS DOWNSIDE SIGNALS. When put/call sits at the call-heavy extreme (bottom
    band), how often does price drop, how far, and how fast -- even when the
    drop is short-lived? And the same event study for the put-heavy extreme
    (top band), for symmetry.

DATA. data/options/{BTC,ETH}_pcr_daily.csv (fetch_pcr.py, Deribit, no ETF
options). pct100 = percentile of the 7-day average volume put/call among the
prior 100 days (same construction as analysis/pcrtest.py). Price: daily
candles, data/{BTC,ETH}_1D.csv.

EVENTS (Krown's panel: weekly chart, bands at ~95 and ~5).
  Sampled at each weekly close (Sunday UTC).
  TOP event    = pct100 >= 95 at a weekly close, and it was < 95 the week before
  BOTTOM event = pct100 <= 5  at a weekly close, and it was > 5  the week before
  Each asset's events use its own put/call; BTC events are also read against
  ETH price, since Krown's panel is BTC.

Q2 MEASURES, from the event's weekly close, at 7 / 14 / 30 / 60 days:
  largest rise and largest drop (daily highs / lows), close-to-close change,
  share that drop 5% / 10% before rising 5% / 10%, and days to the low.
  Baseline: every weekly close in the same years, same measures, so "he called
  the drop" is judged against how often any week drops that much. Split by
  regime gate on / off and by year.

Q1 SETUPS (from analysis/grokpack.py, regime-on, confirmation entry), each
  split by whether a TOP event (and, separately, a BOTTOM event) happened in
  the 14 days up to and including the entry -- backward only, so it is knowable
  at entry:
    all signals; CT > Signal by 5+; CT > Signal + prime; CT > Signal + diamond;
    higher entry than the previous signal; 2+ other same-asset charts before;
    8D CT rising; ETH 1D/2D with a BTC 3D signal before.
  Reported: share of the setup's signals that overlap, and for with / without:
  touched -30%, touched -20%, median worst dip, reach +20% in 60 days, n.

NO PASS RULE: this is a measurement for context. Nothing is adopted. ETH and
BTC are one sample for date-anchored events. ENTRY QUALITY ONLY for Q1;
Q2 is a price event study, not a strategy. Signals are computed, never fills.
  python3 -I analysis/pcrevents.py -> analysis/RESULTS_pcrevents.txt
"""
import sys, os, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import grokpack as GP
import pcrtest as PT

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
H = (7, 14, 30, 60)


def events(R):
    suns = sorted(d for d in R if d.weekday() == 6)
    top, bot = [], []
    for i in range(1, len(suns)):
        d, p = suns[i], suns[i - 1]
        if (d - p).days != 7: continue
        if R[d]['pct'] >= 95 and R[p]['pct'] < 95: top.append(d)
        if R[d]['pct'] <= 5 and R[p]['pct'] > 5: bot.append(d)
    return suns, top, bot


def fwd(day, pos, d):
    i = pos.get(d)
    if i is None: return None
    c0 = day['close'][i]; out = {}
    for h in H:
        j = i + h
        if j >= len(day['close']): return None
        hi = max(day['high'][i + 1:j + 1]); lo = min(day['low'][i + 1:j + 1])
        out[h] = dict(up=(hi / c0 - 1) * 100, dn=(lo / c0 - 1) * 100, ret=(day['close'][j] / c0 - 1) * 100,
                      lowday=1 + min(range(h), key=lambda k: day['low'][i + 1 + k]))
    # first-touch races over 60 days
    for a, b, key in ((5, 5, 'dn5_first'), (10, 10, 'dn10_first')):
        res = None
        for k in range(i + 1, i + 61):
            if day['low'][k] <= c0 * (1 - b / 100): res = True; break
            if day['high'][k] >= c0 * (1 + a / 100): res = False; break
        out[key] = res
    return out


def ev_table(lab, ds, day, pos, gate):
    F = [(d, fwd(day, pos, d)) for d in ds]
    F = [(d, f) for d, f in F if f]
    if not F:
        P(f'  {lab}: n=0'); return
    n = len(F)
    line = f'  {lab:34} n={n:>3}'
    for h in H:
        line += f' | {h}d dn {st.median(f[h]["dn"] for d, f in F):+5.1f} up {st.median(f[h]["up"] for d, f in F):+5.1f} ret {st.median(f[h]["ret"] for d, f in F):+5.1f}'
    P(line)
    d5 = [f['dn5_first'] for d, f in F if f['dn5_first'] is not None]
    d10 = [f['dn10_first'] for d, f in F if f['dn10_first'] is not None]
    P(f'  {"":34}       -5% before +5%: {100 * sum(d5) / len(d5) if d5 else 0:3.0f}% ({len(d5)})   '
      f'-10% before +10%: {100 * sum(d10) / len(d10) if d10 else 0:3.0f}% ({len(d10)})   '
      f'30d drop of 10%+: {100 * sum(f[30]["dn"] <= -10 for d, f in F) / n:3.0f}%   '
      f'median day of the 30d low {st.median(f[30]["lowday"] for d, f in F):.0f}')
    return F


def main():
    R = {a: PT.reads(PT.load_pcr(a)) for a in ('BTC', 'ETH')}
    if not R['BTC']:
        print('no put/call data yet'); return
    DAY = {a: E.load(f'data/{a}_1D.csv') for a in ('BTC', 'ETH')}
    POS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in DAY}
    P('KROWN-STYLE PUT/CALL EVENTS -- declared 27 Oct 2026, run', dt.date.today())
    P('Deribit only, no ETF options. Context, not a filter. Signals are computed, never fills.\n')

    P('Q2  EVENT STUDY: medians of the largest drop (dn), largest rise (up) and close change (ret) after each event')
    EV = {}
    for src in ('BTC', 'ETH'):
        suns, top, bot = events(R[src])
        EV[src] = (top, bot)
        for px in (('BTC', 'ETH') if src == 'BTC' else ('ETH',)):
            yrs = {d.year for d in top + bot}
            base = [d for d in suns if d.year in yrs]
            P(f'\n  {src} put/call events, {px} price ({suns[0]} to {suns[-1]})')
            ev_table('BOTTOM band (call-heavy) events', bot, DAY[px], POS[px], GP.GATE)
            ev_table('TOP band (put-heavy) events', top, DAY[px], POS[px], GP.GATE)
            ev_table('every weekly close (baseline)', base, DAY[px], POS[px], GP.GATE)
            for g, gl in ((True, 'regime on'), (False, 'regime off')):
                ev_table(f'BOTTOM events, {gl}', [d for d in bot if bool(GP.GATE(d)) == g], DAY[px], POS[px], GP.GATE)
            P(f'  bottom-band event dates: {", ".join(str(d) for d in bot)}')
            P(f'  top-band event dates:    {", ".join(str(d) for d in top)}')
            for y in sorted(yrs):
                b = [d for d in bot if d.year == y]; F = [fwd(DAY[px], POS[px], d) for d in b]; F = [f for f in F if f]
                if F: P(f'    {y}: {len(F)} bottom events, 30d median drop {st.median(f[30]["dn"] for f in F):+5.1f}%, close {st.median(f[30]["ret"] for f in F):+5.1f}%')

    P('\nQ1  CONFLUENCE: our setups with a put/call band event in the 14 days up to entry (own asset)')
    rows = [r for r in GP.build()[0]]
    b3 = [x['d0'] for x in GP.build()[1][('BTC', '3D')]]
    for r in rows:
        r['btc3'] = r['a'] == 'ETH' and r['tf'] in ('1D', '2D') and any(0 <= (r['d0'] - d).days <= 10 for d in b3)
    SET = [('all signals', lambda r: True),
           ('CT > Signal by 5+', lambda r: r['gap'] is not None and r['gap'] > 5),
           ('CT > Signal + prime', lambda r: r['gap'] is not None and r['gap'] > 0 and r['prime']),
           ('CT > Signal + diamond', lambda r: r['gap'] is not None and r['gap'] > 0 and r['dis']),
           ('higher entry', lambda r: r['higher']),
           ('2+ own charts before', lambda r: r['agree'] >= 2),
           ('8D CT rising', lambda r: r['up8']),
           ('ETH 1D/2D + BTC 3D before', lambda r: r['btc3'])]
    for a in ('ETH', 'BTC'):
        top, bot = EV[a]; first = min(R[a])
        A = [r for r in rows if r['a'] == a and r['d0'] >= first + dt.timedelta(days=110)]
        for r in A:
            r['top14'] = any(0 <= (r['d0'] - d).days <= 13 for d in top)
            r['bot14'] = any(0 <= (r['d0'] - d).days <= 13 for d in bot)
        P(f'\n  {a} ({len(A)} signals with put/call history)')
        for lab, fn in SET:
            G = [r for r in A if fn(r)]
            if not G: continue
            for ek, en in (('top14', 'put-heavy TOP'), ('bot14', 'call-heavy BOTTOM')):
                W = [r for r in G if r[ek]]; O = [r for r in G if not r[ek]]
                P(f'    {lab:26} {en:18} overlap {100 * len(W) / len(G):3.0f}%  with {PT.fs(PT.summ(W))}')
                P(f'    {"":26} {"":18}               w/o  {PT.fs(PT.summ(O))}')
    P('\n  Context only. Nothing adopted. ETH and BTC are one sample for date-anchored events.')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_pcrevents.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
