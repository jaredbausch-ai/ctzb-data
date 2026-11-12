"""Check 4: odds_fade, recomputed independently (tier by the documented original rule on each chart's own bars;
groupings and outcomes on daily candles from the entry close, outcome days 11-60)."""
from lib import *
TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]

def chart_tags(S, tf):
    """gated ETH troughs on one chart (including ones not yet scoreable), with the refresh-style tag set."""
    ch = S.ch[('ETH', tf)]
    tr, ct, k = troughs(ch)
    # running minimum of CT since it was last >= 60
    zm = []; z = None
    for v in ct:
        if v is None: zm.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        zm.append(z)
    out = []
    for s in tr:
        if not S.gate(ch.date[s['ti']]): continue
        t = {s['bk'], 'any trough'}
        if s['dis']: t |= {'diamond', 'filled' if s['strong'] else 'hollow'}
        if s['prime']: t.add('prime dot')
        if s['dis'] and s['prime']: t.add('diamond+dot')
        if s['bk'] == 'B' and zm[s['ti']] is not None and zm[s['ti']] >= 50: t.add('zone-exit B')
        out.append(dict(s, tags=t))
    return ch, out

for name in STATES:
    S = State(name); R = Rec(name, 'c4'); F = S.feed['odds_fade']
    upto = dt.date(S.today.year, 1, 1)
    keep = []; allsig = {}
    for tf in TFS:
        ch, sg = chart_tags(S, tf); allsig[tf] = (ch, sg); n = int(tf[0])
        scored = []
        for s in sg:
            ei = s['ei']
            if ei >= ch.n: continue
            end = ch.date[ei] + dt.timedelta(days=60)
            if ch.date[-1] < end: continue                      # horizon not elapsed on this chart's bars
            js = [j for j in range(ei + 1, ch.n) if ch.date[j] <= end]
            if not js: continue
            win = ch.c[js[-1]] / ch.c[ei] - 1 > 0
            closed_before = ch.date[ei] + dt.timedelta(days=n - 1 + 60) < upto
            scored.append((s, win, closed_before))
        for t in TAGS:
            sub = [w for s, w, cb in scored if t in s['tags'] and cb]
            if len(sub) >= 8 and 100 * sum(sub) / len(sub) >= 70:
                keep.append((tf, t, len(sub), round(100 * sum(sub) / len(sub), 2)))
    print(name, 'my tier:', keep)
    # setups.csv names the kept pairs
    su = S.ds('setups.csv'); print(name, 'setups.csv:', [r['setup'] for r in su])
    # pool on daily candles
    dd = S.day['ETH']; pool = []
    for tf in TFS:
        ch, sg = allsig[tf]; kt = {t for f, t, _, _ in keep if f == tf}
        for s in sg:
            if not (s['tags'] & kt): continue
            ei = s['ei']
            if ei >= ch.n: continue
            d0 = bar_close_date(ch.date[ei], tf)
            if d0 >= S.today or d0 not in dd.pos: continue
            if not S.complete('ETH', d0): continue
            w = S.window('ETH', d0)
            if not w or w[-1][0] != 60: continue
            e = dd.c[dd.pos[d0]]; De = Decimal(dd.sc[dd.pos[d0]])
            lo10 = min(Decimal(dd.sl[k]) for n_, k in w if n_ <= 10)
            hi_after = max(Decimal(dd.sh[k]) for n_, k in w if n_ > 10)
            k10 = [k for n_, k in w if n_ == 10]
            pool.append(dict(dip=(lo10 / De - 1) * 100, r10=hi_after >= De * Decimal('1.10'), r20=hi_after >= De * Decimal('1.20'),
                             green=(Decimal(dd.sc[k10[0]]) >= De) if k10 else None, tf=tf, d0=d0))
    print(name, 'pool size', len(pool))
    bands = [(Decimal(100), Decimal(-2), 'shallower than -2%'), (Decimal(-2), Decimal(-5), '-2% to -5%'), (Decimal(-5), Decimal(-10), '-5% to -10%'),
             (Decimal(-10), Decimal(-20), '-10% to -20%'), (Decimal(-20), Decimal(-100), 'worse than -20%')]
    exp = []
    for hi, lo, lab in bands:
        g = [p for p in pool if lo < p['dip'] <= hi]
        if len(g) < 5: continue
        exp.append((lab, len(g), sum(p['r10'] for p in g), sum(p['r20'] for p in g)))
    R.add('feed.odds_fade', 'posting_bar_pct', F['posting_bar_pct'], 70)
    R.add('feed.odds_fade.early_dip', 'rows', len(F['early_dip']), len(exp))
    for row, (lab, n, k10, k20) in zip(F['early_dip'], exp):
        loc = f'feed.odds_fade.early_dip "{lab}"'
        R.add(loc, 'band', row['band'], lab)
        R.add(loc, 'past_trades', row['past_trades'], n); R.add(loc, 'past_signals', row['past_signals'], n)
        R.add(loc, 'rose10_after_day10_pct', row['rose10_after_day10_pct'], share(k10, n))
        R.add(loc, 'rose20_after_day10_pct', row['rose20_after_day10_pct'], share(k20, n))
        R.add(loc, 'rose10_within60d_pct (alias)', row['rose10_within60d_pct'], share(k10, n))
        R.add(loc, 'rose20_within60d_pct (alias)', row['rose20_within60d_pct'], share(k20, n))
        R.add(loc, 'edge (exact share vs 70)', row['edge'], 'intact' if Fraction(100 * k10, n) >= 70 else 'gone', cause=f'exact share {float(Fraction(100*k10,n)):.6f}')
    exp2 = []
    for lab, sel in (('green on day 10', True), ('red on day 10', False)):
        g = [p for p in pool if p['green'] is sel]
        if len(g) < 5: continue
        exp2.append((lab, len(g), sum(p['r10'] for p in g), sum(p['r20'] for p in g)))
    R.add('feed.odds_fade.day10', 'rows', len(F['day10']), len(exp2))
    for row, (lab, n, k10, k20) in zip(F['day10'], exp2):
        loc = f'feed.odds_fade.day10 "{lab}"'
        R.add(loc, 'check', row['check'], lab)
        R.add(loc, 'past_trades', row['past_trades'], n); R.add(loc, 'past_signals', row['past_signals'], n)
        R.add(loc, 'rose10_after_day10_pct', row['rose10_after_day10_pct'], share(k10, n))
        R.add(loc, 'rose20_after_day10_pct', row['rose20_after_day10_pct'], share(k20, n))
        R.add(loc, 'rose10_within60d_pct (alias)', row['rose10_within60d_pct'], share(k10, n))
        R.add(loc, 'rose20_within60d_pct (alias)', row['rose20_within60d_pct'], share(k20, n))
        R.add(loc, 'edge (exact share vs 70)', row['edge'], 'intact' if Fraction(100 * k10, n) >= 70 else 'gone', cause=f'exact share {float(Fraction(100*k10,n)):.6f}')
    R.add('feed.odds_fade', 'edge_measured_on', F['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)')
    R.add('feed.odds_fade', 'sample text says in-sample, tier fixed 1 Jan 2026, daily candles, days 11 to 60',
          'yes' if all(x in F['sample'] for x in ('In-sample', '1 Jan 2026', 'daily candles', 'days 11 to 60', 'General explainer')) else 'no', 'yes')
    print(name, 'early', exp, 'day10', exp2, 'sum early', sum(x[1] for x in exp), 'sum d10', sum(x[1] for x in exp2))
    print(name, 'dips near band edges:', [(str(p['d0']), p['tf'], float(p['dip'])) for p in pool if any(abs(p['dip'] - b) < Decimal('0.02') for b in (-2, -5, -10, -20))])
    R.save()
