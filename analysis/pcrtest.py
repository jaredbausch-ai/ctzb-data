"""Options put/call ratio at the signal -- DECLARED 27 Oct 2026, before any
put/call data existed in the repo (fetch_pcr.py was pushed the same evening and
had not completed a run when this was written and committed).

DATA. data/options/{ETH,BTC}_pcr_daily.csv from Deribit trade history
(fetch_pcr.py). Volume put/call = put contracts / call contracts traded that UTC
day. BTC from late 2016, ETH from March 2019. ETF options are not included.

UNIVERSE. analysis/grokpack.py rows: regime-on signals, gate
R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41), confirmation entry dated
bucket_end, 60-day window on daily candles. Charts 1D 2D 3D 5D (8D too thin).
Each signal uses its own asset's put/call. Only days with put/call data count.

READ AT ENTRY (all known at the entry day's close, day d0 inclusive):
  pcr7    = mean of the daily ratio over d0-6..d0
  pct100  = percentile rank of pcr7 among the 100 daily pcr7 values before d0
  pcr1    = the daily ratio on d0
CANDIDATES, declared, nothing added after:
  P1  put-heavy:  pct100 >= 80
  P2  call-heavy: pct100 <= 20
  P3  put/call rising: pcr7 above pcr7 seven days earlier
  P4  put spike: pcr1 > 1.25 x pcr7
  P5  premium put-heavy: same as P1 on the premium ratio (pcr_prem)

REPORTED, per the 27 Oct standing rule, for every candidate: touched -30%
(LIQ30), touched -20% (LIQ20), median worst dip in the window, and reach +20%
(win), with and without, n beside each. Splits: asset, period (to 2021 /
2022 on), year, chart. Collinearity: inside funding below / at-or-above its
90-day median (data/derivs, posread.py's rule) and inside gap>5 / not.

PASS as a RISK read (the kind that matters at ~3.3x) if, for the asset:
  - LIQ30 at least 5 points lower with the feature than without, AND win rate
    no more than 3 points lower,
  - in both periods (each group n >= 8),
  - in a majority of years that have n >= 5 in both groups,
  - and the LIQ30 cut stays >= 3 points inside both halves of gap>5 and inside
    both halves of the funding read.
PASS as a WIN read if win is >= 10 points higher with LIQ30 no worse, under the
same period / year / collinearity conditions.
PLACEBO for anything that passes: shift every put/call date by a random 30-180
days, 40 times; the real effect must beat the 95th percentile of the shuffles.
ETH and BTC are one sample for anything date-anchored -- put/call is
date-anchored, so agreement between the two assets is NOT independent evidence.
ENTRY QUALITY ONLY. Signals are computed, never fills.
  python3 -I analysis/pcrtest.py -> analysis/RESULTS_pcrtest.txt
"""
import sys, os, csv, random, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import grokpack as GP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = dt.date(2022, 1, 1)
L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))


def load_pcr(a, col='pcr_amt'):
    p = os.path.join(ROOT, f'data/options/{a}_pcr_daily.csv')
    if not os.path.exists(p): return {}
    out = {}
    for r in csv.DictReader(open(p)):
        if r.get(col) not in ('', None):
            out[dt.date.fromisoformat(r['date'])] = float(r[col])
    return out


def reads(series, shift=0):
    """pcr7, pct100, pcr1 per date, optionally with the series shifted by `shift` days."""
    s = {d + dt.timedelta(days=shift): v for d, v in series.items()}
    days = sorted(s); p7 = {}
    for d in days:
        w = [s.get(d - dt.timedelta(days=k)) for k in range(7)]
        if all(v is not None for v in w): p7[d] = sum(w) / 7
    out = {}
    for d in sorted(p7):
        hist = [p7.get(d - dt.timedelta(days=k)) for k in range(1, 101)]
        hist = [v for v in hist if v is not None]
        if len(hist) < 80: continue
        prev = p7.get(d - dt.timedelta(days=7))
        out[d] = dict(pcr7=p7[d], pct=100 * sum(v < p7[d] for v in hist) / len(hist),
                      rise=prev is not None and p7[d] > prev, pcr1=s[d])
    return out


def funding_below():
    out = {}
    for a in ('ETH', 'BTC'):
        p = os.path.join(ROOT, f'data/derivs/{a}_funding_daily.csv'); f = {}
        for r in csv.DictReader(open(p)):
            v = r.get('funding_oi_weighted') or r.get('funding_mean')
            if v not in ('', None): f[dt.date.fromisoformat(r['date'])] = float(v)
        for d in f:
            back = [f.get(d - dt.timedelta(days=k)) for k in range(1, 91)]
            back = [v for v in back if v is not None]
            if len(back) >= 60: out[(a, d)] = f[d] < st.median(back)
    return out


def summ(G):
    if not G: return None
    n = len(G)
    return dict(n=n, liq30=100 * sum(r['t30'] for r in G) / n, liq20=100 * sum(r['t20'] for r in G) / n,
                dd=st.median(r['m']['dd'] for r in G), win=100 * sum(r['win'] for r in G) / n)


def fs(s):
    return 'n=   0' if not s else f'n={s["n"]:>4} -30% {s["liq30"]:3.0f}% -20% {s["liq20"]:3.0f}% dip {s["dd"]:+6.1f}% win {s["win"]:3.0f}%'


FEATS = [('P1 put-heavy (pct>=80)', lambda x, xp: x['pct'] >= 80),
         ('P2 call-heavy (pct<=20)', lambda x, xp: x['pct'] <= 20),
         ('P3 put/call rising 7d', lambda x, xp: x['rise']),
         ('P4 put spike (day > 1.25x 7d)', lambda x, xp: x['pcr1'] > 1.25 * x['pcr7']),
         ('P5 premium put-heavy (pct>=80)', lambda x, xp: xp is not None and xp['pct'] >= 80)]


def attach(rows, shift=0):
    R = {a: reads(load_pcr(a), shift) for a in ('ETH', 'BTC')}
    RP = {a: reads(load_pcr(a, 'pcr_prem'), shift) for a in ('ETH', 'BTC')}
    out = []
    for r in rows:
        x = R[r['a']].get(r['d0'])
        if x is None: continue
        out.append(dict(r, x=x, xp=RP[r['a']].get(r['d0'])))
    return out


def verdict(G, fn):
    """Returns (risk_pass, win_pass, detail) for one asset's rows G."""
    W = [r for r in G if fn(r['x'], r['xp'])]; O = [r for r in G if not fn(r['x'], r['xp'])]
    sw, so = summ(W), summ(O)
    if not sw or not so: return False, False, {}
    cut = so['liq30'] - sw['liq30']; lift = sw['win'] - so['win']
    def ok_split(groups, need_cut, need_lift):
        for sel in groups:
            w = [r for r in W if sel(r)]; o = [r for r in O if sel(r)]
            if len(w) < 8 or len(o) < 8: return False
            a, b = summ(w), summ(o)
            if (b['liq30'] - a['liq30']) < need_cut or (a['win'] - b['win']) < need_lift: return False
        return True
    per = [lambda r: r['d0'] < SPLIT, lambda r: r['d0'] >= SPLIT]
    yrs = sorted({r['yr'] for r in G}); yr_ok = yr_n = 0
    for y in yrs:
        w = [r for r in W if r['yr'] == y]; o = [r for r in O if r['yr'] == y]
        if len(w) >= 5 and len(o) >= 5:
            yr_n += 1; yr_ok += (summ(o)['liq30'] - summ(w)['liq30']) > 0
    coll = [lambda r: r['gap'] is not None and r['gap'] > 5, lambda r: not (r['gap'] is not None and r['gap'] > 5),
            lambda r: r.get('fb') is True, lambda r: r.get('fb') is False]
    risk = (cut >= 5 and lift >= -3 and ok_split(per, 0.01, -3) and yr_n > 0 and yr_ok > yr_n / 2
            and ok_split(coll, 3, -100))
    win = (lift >= 10 and cut >= 0 and ok_split(per, 0, 0.01) and ok_split(coll, -100, 5))
    return risk, win, dict(cut=cut, lift=lift, years=f'{yr_ok}/{yr_n}')


def main():
    rows = [r for r in GP.build()[0] if r['tf'] in ('1D', '2D', '3D', '5D')]
    fb = funding_below()
    for r in rows: r['fb'] = fb.get((r['a'], r['d0']))
    G = attach(rows)
    if not G:
        print('no put/call data yet -- data/options/ is empty or too short'); return
    P('PUT/CALL AT THE SIGNAL -- declared 27 Oct 2026, run', dt.date.today(), '| entry quality only, signals not fills')
    for a in ('ETH', 'BTC'):
        A = [r for r in G if r['a'] == a]
        if not A: continue
        P(f'\n{a}: {len(A)} signals with put/call data, {min(r["d0"] for r in A)} to {max(r["d0"] for r in A)}')
        P(f'  baseline                         {fs(summ(A))}')
        for lab, fn in FEATS:
            W = [r for r in A if fn(r['x'], r['xp'])]; O = [r for r in A if not fn(r['x'], r['xp'])]
            risk, win, d = verdict(A, fn)
            P(f'  {lab:32} with {fs(summ(W))}')
            P(f'  {"":32} w/o  {fs(summ(O))}   -30% cut {d.get("cut", 0):+.0f}  win {d.get("lift", 0):+.0f}  years {d.get("years", "-")}'
              f'  -> {"RISK PASS" if risk else ""}{" WIN PASS" if win else ""}{"" if risk or win else "fail"}')
            for pl, sel in (('to 2021', lambda r: r['d0'] < SPLIT), ('2022 on', lambda r: r['d0'] >= SPLIT)):
                P(f'      {pl:8} with {fs(summ([r for r in W if sel(r)]))} | w/o {fs(summ([r for r in O if sel(r)]))}')
            for tf in ('1D', '2D', '3D', '5D'):
                w = summ([r for r in W if r['tf'] == tf]); o = summ([r for r in O if r['tf'] == tf])
                if w and o: P(f'      {a} {tf}   -30% {w["liq30"]:3.0f}% vs {o["liq30"]:3.0f}%  win {w["win"]:3.0f}% vs {o["win"]:3.0f}%  (n {w["n"]}/{o["n"]})')
            if risk or win:
                real = d['cut'] if risk else d['lift']; sh = []
                rnd = random.Random(7)
                for _ in range(40):
                    k = rnd.choice([-1, 1]) * rnd.randint(30, 180)
                    Gs = [r for r in attach([r for r in rows if r['a'] == a], k)]
                    W2 = [r for r in Gs if fn(r['x'], r['xp'])]; O2 = [r for r in Gs if not fn(r['x'], r['xp'])]
                    if summ(W2) and summ(O2):
                        sh.append(summ(O2)['liq30'] - summ(W2)['liq30'] if risk else summ(W2)['win'] - summ(O2)['win'])
                sh.sort(); p95 = sh[int(0.95 * len(sh)) - 1] if sh else None
                P(f'      PLACEBO: real {real:+.1f} vs shuffled p95 {p95:+.1f} -> {"PASS" if p95 is not None and real > p95 else "FAIL"}')
    P('\n  ENTRY QUALITY ONLY. Computed signals, not fills.')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_pcrtest.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
