"""Krown PCR calibration: does our Deribit-only put/call percentile fire in the
weeks his indicator marked? Descriptive, 28 Oct 2026. Reference points from
docs/reference/krown_pcr_reference.md (read off his screenshots).

Ours: pct100 = percentile of the 7-day average volume put/call among the prior
100 days (analysis/pcrtest.reads), BTC. Also the open-interest-free premium
ratio. For each of his labelled red-line weeks (Monday), the highest daily
pct100 in that Mon-Sun week and the week either side, and whether it reached
the top band (>= 95). Baseline: the share of all weeks reaching >= 95.
His panel on 2026-10-25: day 0.60, 7d 0.76, percentile 83.
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pcrtest as PT
L = []; P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))
WEEKS = ['2021-04-19', '2021-12-06', '2023-09-11', '2023-12-18', '2024-07-08', '2025-03-03', '2025-12-08',
         '2026-03-02', '2026-04-06', '2026-06-08', '2026-08-03', '2026-08-17', '2026-10-19']

def main():
    for col, lab in (('pcr_amt', 'volume'), ('pcr_prem', 'premium')):
        s = PT.load_pcr('BTC', col); R = PT.reads(s)
        P(f'\nBTC {lab} put/call, our 100-day percentile of the 7-day average')
        hits = 0
        for w in WEEKS:
            m = dt.date.fromisoformat(w)
            wk = [R[m + dt.timedelta(days=k)]['pct'] for k in range(7) if m + dt.timedelta(days=k) in R]
            nb = [R[m + dt.timedelta(days=k)]['pct'] for k in range(-7, 14) if m + dt.timedelta(days=k) in R]
            top = max(wk) if wk else None; topn = max(nb) if nb else None
            hit = topn is not None and topn >= 95; hits += hit
            P(f'  his week {w}: our max in that week {top if top is None else round(top)} | within a week either side {topn if topn is None else round(topn)} {"TOP BAND" if hit else ""}')
        mondays = sorted({d - dt.timedelta(days=d.weekday()) for d in R if d >= dt.date(2021, 1, 1)})
        base = 0; nw = 0
        for m in mondays:
            nb = [R[m + dt.timedelta(days=k)]['pct'] for k in range(-7, 14) if m + dt.timedelta(days=k) in R]
            if nb: nw += 1; base += max(nb) >= 95
        P(f'  his weeks reaching our top band (+/- a week): {hits}/{len(WEEKS)} | any random week since 2021: {100 * base / nw:.0f}%')
        d = dt.date(2026, 10, 25)
        if d in R: P(f'  25 Oct 2026: ours day {s[d]:.2f}, 7d {R[d]["pcr7"]:.2f}, pct {R[d]["pct"]:.0f} | Krown day 0.60, 7d 0.76, pct 83')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_krowncal.txt'), 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    main()
