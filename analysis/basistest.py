"""Can TradingView rebuild the ETH funding confirmations from the perp-vs-spot gap?
(29 Oct 2026, for CT Zone Bounce v16 / Scanner v10)

Jared: the ETH asterisk grade is "way too much of a discrepancy... there has to be
another solution". TradingView cannot read the 12-exchange funding, but it can read
BINANCE:ETHUSDT.P and BINANCE:ETHUSDT. Funding is set from the perp's premium over
spot, so a basis-built FUND and FCOOL might reproduce the real ones.

DECLARED before the data was fetched. Basis = perp close / spot close - 1, Binance
ETHUSDT, hourly (fetch_basis.py). Two candidates, nothing else tried:
  P1  daily MEAN of the 24 hourly basis values (what Pine can build from 1H bars)
  P2  basis at the daily CLOSE only (what Pine can build from 1D bars)
Each candidate builds the two confirmations exactly as the official ones are built
(pcrtest.funding_below, stack_live.fcool_at), with basis in place of funding:
  FUND*   the day's basis >= the median of the prior 90 days (60+ values needed)
  FCOOL*  mean of the last 7 days >= mean of days 14-20 back (5+ values in each)
Scored against the official FUND / FCOOL:
  1 day by day, 2020 to now, by year
  2 on every graded ETH 1D-5D signal (its entry date): FUND, FCOOL, and the GRADE
    LETTER (the four price confirmations plus the two funding ones), by chart, by year
PASS (declared): grade letter matches on 95%+ of signals AND no year below 90%.
A pass means the scripts can show the console's ETH grade and odds without the
asterisk. A fail keeps the asterisk. ETH and BTC are not mixed: ETH only.
  python3 -I analysis/basistest.py
"""
import csv, os, sys, datetime as dt, statistics as st
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'analysis'))
os.chdir(HERE)
import stack_live as SL

PRICE = ['GAP', 'HIGH', 'AGREE', 'BTC3']
gof = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'


def build(series):
    """{date: (fund, fcool)} from a {date: value} series, the official recipes"""
    out = {}
    for d in series:
        back = [series.get(d - dt.timedelta(days=k)) for k in range(1, 91)]
        back = [v for v in back if v is not None]
        fund = series[d] >= st.median(back) if len(back) >= 60 else None
        w7 = [series[d - dt.timedelta(days=k)] for k in range(7) if d - dt.timedelta(days=k) in series]
        w7b = [series[d - dt.timedelta(days=14 + k)] for k in range(7) if d - dt.timedelta(days=14 + k) in series]
        fc = (sum(w7) / len(w7) >= sum(w7b) / len(w7b)) if len(w7) >= 5 and len(w7b) >= 5 else None
        out[d] = (fund, fc)
    return out


def main():
    B = {}
    for r in csv.DictReader(open('data/ext/ETH_basis_daily.csv')):
        if int(r['hours']) >= 20:
            B[dt.date.fromisoformat(r['date'])] = (float(r['basis_mean']), float(r['basis_close']))
    P = {'P1 daily mean': build({d: v[0] for d, v in B.items()}), 'P2 daily close': build({d: v[1] for d, v in B.items()})}

    cap = {}
    SL._HOOK = lambda L: cap.update(L) or L
    SL.main()
    rows, feats, fb, FS, fcool_at = cap['rows'], cap['feats'], cap['fb'], cap['FS'], cap['fcool_at']
    out = []; pr = lambda *a: out.append(' '.join(str(x) for x in a))
    pr(f'# Basis-built funding vs the real thing (analysis/basistest.py, run {dt.date.today()})\n')
    pr(f'Basis days: {len(B)}, {min(B)} to {max(B)}.\n')

    # ---- 1. day by day ----
    pr('## 1. Day by day: share of days the basis version agrees with the official one\n')
    pr('| Year | days | P1 FUND | P1 FCOOL | P2 FUND | P2 FCOOL |'); pr('|---|---|---|---|---|---|')
    days = sorted(d for d in B if ('ETH', d) in fb)
    for y in sorted({d.year for d in days}) + ['all']:
        D = [d for d in days if y == 'all' or d.year == y]
        cells = []
        for name in P:
            for j, off in ((0, lambda d: not fb[('ETH', d)]), (1, lambda d: fcool_at('ETH', d))):
                pairs = [(P[name][d][j], off(d)) for d in D if P[name].get(d) and P[name][d][j] is not None and off(d) is not None]
                cells.append(f'{round(100 * sum(a == b for a, b in pairs) / len(pairs))}%' if pairs else '-')
        pr(f'| {y} | {len(D)} | ' + ' | '.join(cells) + ' |')
    pr('')

    # ---- 2. on the signals ----
    S = [r for r in rows if r['a'] == 'ETH' and r['tf'] in ('1D', '2D', '3D', '5D') and r.get('fund') is not None and r.get('fcool') is not None]
    pr(f'## 2. On every graded ETH 1D-5D signal ({len(S)} with official funding)\n')
    res = {}
    for name in P:
        rec = []
        for r in S:
            pv = P[name].get(r['d0'])
            if not pv or pv[0] is None or pv[1] is None: continue
            f = feats(r); npx = sum(bool(f.get(k)) for k in PRICE)
            off = gof(npx + bool(r['fund']) + bool(r['fcool'])); bas = gof(npx + pv[0] + pv[1])
            rec.append((r, pv[0] == bool(r['fund']), pv[1] == bool(r['fcool']), off == bas))
        res[name] = rec
    pr('| Version | signals | FUND agrees | FCOOL agrees | GRADE LETTER agrees |'); pr('|---|---|---|---|---|')
    for name, rec in res.items():
        n = len(rec)
        pr(f'| {name} | {n} | ' + ' | '.join(f'{round(100 * sum(x[i] for x in rec) / n)}%' for i in (1, 2, 3)) + ' |')
    pr('\nGrade letter agreement by chart and by year:\n')
    pr('| Split | ' + ' | '.join(f'{n} (n)' for n in P) + ' |'); pr('|---|' + '---|' * len(P))
    splits = [(f'ETH {tf}', lambda r, tf=tf: r['tf'] == tf) for tf in ('1D', '2D', '3D', '5D')] + \
             [(str(y), lambda r, y=y: r['d0'].year == y) for y in sorted({x[0]['d0'].year for x in res['P1 daily mean']})]
    worst = {n: 100 for n in P}
    for lab, fn in splits:
        cells = []
        for name, rec in res.items():
            X = [x for x in rec if fn(x[0])]
            if X:
                p = round(100 * sum(x[3] for x in X) / len(X)); cells.append(f'{p}% ({len(X)})')
                if lab[0].isdigit() and len(X) >= 10: worst[name] = min(worst[name], p)
            else: cells.append('-')
        pr(f'| {lab} | ' + ' | '.join(cells) + ' |')
    pr('\n## Verdict against the declared bar (95%+ overall, no year with 10+ signals below 90%)\n')
    for name, rec in res.items():
        p = 100 * sum(x[3] for x in rec) / len(rec)
        pr(f'- {name}: {p:.0f}% overall, worst year {worst[name]}% -> {"PASS" if p >= 95 and worst[name] >= 90 else "FAIL"}')
    pr('\nEntry quality only: computed signals, never fills.')
    txt = '\n'.join(out) + '\n'
    open('analysis/RESULTS_basistest.md', 'w').write(txt); print(txt)


if __name__ == '__main__':
    main()
