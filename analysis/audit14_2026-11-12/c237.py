"""Checks 2, 3, 7: grade_odds, if_it_misses (+example), past_paths (+example)."""
from lib2 import *
EX = dt.date(2024, 9, 22)
for name in STATES:
    S = State(name); mine = build_mine(S); F = S.feed
    R = Rec(name, 'c2')
    L = list(mine.values())
    for go in F['grade_odds']:
        a, g = go['asset'], go['grade']; loc = f'feed.grade_odds {a} {g}'
        if g in ('A+', 'A', 'B', 'C'):
            G = [x for x in L if x['a'] == a and x['grade'] == g]
        elif g == 'diamond or prime dot':
            G = [x for x in L if x['a'] == a and (x['dis'] or x['prime'])]
        elif g == 'no diamond or prime dot':
            G = [x for x in L if x['a'] == a and not (x['dis'] or x['prime'])]
        else:
            continue   # the two HTF-divergence rows: lens logic, out of scope
        n = len(G)
        R.add(loc, 'past_trades', go['past_trades'], n)
        R.add(loc, 'past_signals', go['past_signals'], n)
        R.add(loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], share(sum(x['m']['r10'] for x in G), n))
        R.add(loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], share(sum(x['m']['surv10'] for x in G), n))
        R.add(loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], share(sum(x['m']['r20'] for x in G), n))
        R.add(loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], rnd(repr(st.median(x['m']['dd'] for x in G)), 1))
        R.add(loc, 'sample', go['sample'], f"{min(x['edate'] for x in G)} to {max(x['edate'] for x in G)}")
        R.add(loc, 'label says computed / entry quality only', 'yes' if 'Entry quality only' in go['label'] and 'not a fill' in go['label'] else 'no', 'yes')
    R.add('feed.grade_odds', 'rows (8 asset/grade + 4 ETH flag rows)', len(F['grade_odds']), 12)
    R.save()

    R = Rec(name, 'c3')
    for mi in F['if_it_misses']:
        a, g = mi['asset'], mi['grade']; loc = f'feed.if_it_misses {a} {g}'
        ms = miss_stats([x for x in L if x['a'] == a and x['grade'] == g])
        for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'mean_peak_pct', 'peaked_5_or_more', 'peaked_10_or_more', 'median_worst_drop_pct', 'median_day60_pct'):
            R.add(loc, k, mi.get(k), ms.get(k))
        R.add(loc, 'miss_rule', mi['miss_rule'], 'did not rise 10% within 60 days')
    R.add('feed.if_it_misses', 'rows', len(F['if_it_misses']), sum(1 for a in ASSETS for g in ('A+', 'A', 'B', 'C') if any(x['a'] == a and x['grade'] == g for x in L)))
    known = [x for x in L if x['a'] == 'ETH' and x['grade'] == 'A+' and x['edate'] + dt.timedelta(days=60) <= EX]
    ms = miss_stats(known); mi = F['example_if_it_misses']
    for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
        R.add('feed.example_if_it_misses', k, mi.get(k), ms.get(k))
    R.add('feed.example_if_it_misses', 'asset/grade', f"{mi['asset']} {mi['grade']}", 'ETH A+')
    R.save()

    R = Rec(name, 'c7')
    for pp in F['past_paths']:
        a = pp['asset']; loc = f'feed.past_paths {a}'
        n, q = paths(S, [x for x in L if x['a'] == a and x['grade'] == 'A+'])
        R.add(loc, 'signals', pp['signals'], n)
        R.add(loc, 'grade', pp['grade'], 'A+')
        R.add(loc, 'days listed', len(pp['days']), 61)
        for d in pp['days']:
            k = d['day']
            R.add(loc, f'day {k} q25_pct', d['q25_pct'], q[k][0]); R.add(loc, f'day {k} median_pct', d['median_pct'], q[k][1]); R.add(loc, f'day {k} q75_pct', d['q75_pct'], q[k][2])
    pp = F['example_past_paths']; n, q = paths(S, known)
    R.add('feed.example_past_paths', 'signals', pp['signals'], n)
    R.add('feed.example_past_paths', 'days listed', len(pp['days']), 61)
    for d in pp['days']:
        k = d['day']
        R.add('feed.example_past_paths', f'day {k} q25_pct', d['q25_pct'], q[k][0]); R.add('feed.example_past_paths', f'day {k} median_pct', d['median_pct'], q[k][1]); R.add('feed.example_past_paths', f'day {k} q75_pct', d['q75_pct'], q[k][2])
    R.save()
    # diagnostics: ties near rounding in path quantiles; entryPrice vs exact close
    d = [(k, x['sentry']) for k, x in mine.items() if Decimal(x['sentry']) != Decimal(str(rnd(x['sentry'], 2)))]
    print('entries with more than 2 decimals:', d[:10], len(d))
