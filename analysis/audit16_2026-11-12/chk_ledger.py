"""Check 1 (ledger), 2 (grade_odds), 3 (if_it_misses / example_if_it_misses)."""
import sys, statistics as st, datetime as dt
from common import *
import funding as F

def run(name):
    S = load_state(name); C = Checks(name)
    led = S.ledger
    fund = {a: F.load(S.root, a) for a in L.ASSETS}
    # ---- membership
    mine = {}
    for s in S.sigs:
        if s['tf'] not in L.TFS_G or s['m'] is None: continue
        if s['asset'] == 'ETH':
            wt, mean = fund['ETH']
            if not (F.has_median(wt, s['d0']) and F.has_cooling(mean, s['d0'])): continue
        mine[(s['chart'], str(s['d0']))] = s
    theirs = {(r['chart'], r['entry']): r for r in led}
    C.add('ledger', 'row count', len(led), len(mine), group='1 ledger membership')
    for k in sorted(set(mine) | set(theirs)):
        C.add(f'ledger {k[0]} {k[1]}', 'membership', k in theirs, k in mine, group='1 ledger membership',
              cause='signal in one list only')
    C.add('ledger', 'duplicate rows', len(led) - len(theirs), 0, group='1 ledger membership')
    # ---- fields
    vol = S.vol
    for k, r in sorted(theirs.items()):
        s = mine.get(k)
        if s is None: continue
        m = s['m']; a = s['asset']; loc = f'ledger {k[0]} {k[1]}'; g = '1 ledger fields'
        C.add(loc, 'asset', r['asset'], a, group=g)
        C.add(loc, 'low (trough bar date)', r['low'], str(s['tdate']), group=g)
        C.add(loc, 'entryPrice', r['entryPrice'], L.rhaz(s['entry'], 2), group=g)
        # entry = daily close on the entry date
        C.add(loc, 'entry close = daily close on entry date', L.rhaz(s['entry'], 2), L.rhaz(S.day[a].c[S.day[a].pos[s['d0']]], 2), group=g)
        C.add(loc, 'tags', r['tags'], s['tags'], group=g)
        C.add(loc, 'reached20', r['reached20'], 'yes' if m['up'] >= 20 else 'no', group=g)
        C.add(loc, 'touched30', r['touched30'], 'yes' if m['dd'] <= -30 else 'no', group=g)
        C.add(loc, 'bestMove', r['bestMove'], L.rhaz(m['up'], 6), group=g)
        C.add(loc, 'maxDrawdown', r['maxDrawdown'], L.rhaz(m['dd'], 6), group=g)
        C.add(loc, 'dipBeforeHigh', r['dipBeforeHigh'], L.rhaz(m['ddpk'], 6), group=g)
        C.add(loc, 'return60d', r['return60d'], L.rhaz(m['ret'], 6), group=g)
        C.add(loc, 'daysToHigh', r['daysToHigh'], m['dpk'], group=g)
        C.add(loc, 'year', r['year'], s['d0'].year, group=g)
        C.add(loc, 'reached10', r['reached10'], 'yes' if m['up'] >= 10 else 'no', group=g)
        C.add(loc, 'reached15', r['reached15'], 'yes' if m['up'] >= 15 else 'no', group=g)
        sv = m['up'] >= 10 and m['dd'] > -25.3
        # exact-price version of the same test
        day = S.day[a]; hi = max(day.h[x] for x in m['ks']); lo = min(day.l[x] for x in m['ks'])
        sv_px = hi >= s['entry'] * 1.10 and not (lo <= s['entry'] * (1 - L.LIQ))
        C.add(loc, 'surv10', r['surv10'], 'yes' if sv_px else 'no', group=g, cause='' if sv == sv_px else 'pct-vs-price boundary')
        r10px = hi >= s['entry'] * 1.10
        C.add(loc, 'reached10 (exact price test)', r['reached10'], 'yes' if r10px else 'no', group=g)
        ra = vol[a].ratio(s['d0'])
        s['sc'] = None if ra is None else (m['up'] >= 20 * ra)
        C.add(loc, 'scaled20', r['scaled20'], '' if ra is None else ('yes' if s['sc'] else 'no'), group=g)
        s['grade'] = r['grade']; s['lenses'] = r['lenses']
        C.add(loc, 'window = 60 daily bars', m['ndays'], 60, group=g, cause='gap in daily candles inside the window')
    # ---- grade record columns on the ledger + grade_odds
    G = {}
    for k, s in mine.items():
        if 'grade' in s: G.setdefault((s['asset'], s['grade']), []).append(s)
    grec = {}
    for (a, gr), lst in G.items():
        n = len(lst)
        grec[(a, gr)] = dict(n=n, reach20=L.rhaz(100 * sum(x['m']['up'] >= 20 for x in lst) / n),
                             touched30=L.rhaz(100 * sum(x['m']['dd'] <= -30 for x in lst) / n),
                             medDip=L.rhaz(st.median(x['m']['dd'] for x in lst), 1),
                             reach10=L.rhaz(100 * sum(x['m']['up'] >= 10 for x in lst) / n),
                             surv10=L.rhaz(100 * sum(x['m']['up'] >= 10 and x['m']['dd'] > -25.3 for x in lst) / n),
                             sample=f"{min(x['d0'] for x in lst)} to {max(x['d0'] for x in lst)}")
    for k, r in sorted(theirs.items()):
        s = mine.get(k)
        if s is None: continue
        gr = grec[(s['asset'], r['grade'])]; loc = f'ledger {k[0]} {k[1]}'; g = '1 ledger grade-record cols'
        C.add(loc, 'gradeReach20', r['gradeReach20'], gr['reach20'], group=g)
        C.add(loc, 'gradeTouched30', r['gradeTouched30'], gr['touched30'], group=g)
        C.add(loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], gr['medDip'], group=g)
    # ---- odds on the day
    hist = sorted((s for s in mine.values() if 'grade' in s), key=lambda s: s['d0'])
    for k, r in sorted(theirs.items()):
        s = mine.get(k)
        if s is None: continue
        loc = f'ledger {k[0]} {k[1]}'; g = '1 ledger odds-on-the-day'
        prior = [h for h in hist if h['asset'] == s['asset'] and h['d0'] + dt.timedelta(days=60) <= s['d0']]
        same = [h for h in prior if h['grade'] == r['grade']]
        C.add(loc, 'dayN', r['dayN'], len(same), group=g)
        def rate(fn, P=prior, Gs=same):
            if len(same) < 10 or not P or not Gs: return ''
            base = sum(fn(h) for h in P) / len(P)
            return L.rhaz(100 * (sum(fn(h) for h in Gs) + 5 * base) / (len(Gs) + 5))
        C.add(loc, 'dayReach10', r['dayReach10'], rate(lambda h: h['m']['up'] >= 10), group=g)
        C.add(loc, 'dayReach20', r['dayReach20'], rate(lambda h: h['m']['up'] >= 20), group=g)
        C.add(loc, 'dayReach30', r['dayReach30'], rate(lambda h: h['m']['up'] >= 30), group=g)
        C.add(loc, 'dayTouched30', r['dayTouched30'], rate(lambda h: h['m']['dd'] <= -30), group=g)
        C.add(loc, 'daySurv10', r['daySurv10'], rate(lambda h: h['m']['up'] >= 10 and h['m']['dd'] > -25.3), group=g)
        P2 = [h for h in prior if h['sc'] is not None]; G2 = [h for h in same if h['sc'] is not None]
        C.add(loc, 'dayScaled20', r['dayScaled20'], rate(lambda h: bool(h['sc']), P2, G2), group=g)
    # ---- 2. grade_odds
    for go in S.feed['grade_odds']:
        if go['grade'] not in ('A+', 'A', 'B', 'C'): continue      # (h) lens logic rows out of scope
        gr = grec.get((go['asset'], go['grade'])); loc = f"feed.grade_odds {go['asset']} {go['grade']}"; g = '2 grade_odds'
        C.add(loc, 'past_trades', go['past_trades'], gr['n'], group=g)
        C.add(loc, 'past_signals', go['past_signals'], gr['n'], group=g)
        C.add(loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], gr['reach10'], group=g)
        C.add(loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], gr['surv10'], group=g)
        C.add(loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], gr['reach20'], group=g)
        C.add(loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], gr['medDip'], group=g)
        C.add(loc, 'sample', go['sample'], gr['sample'], group=g)
        C.add(loc, 'label says computed/not a fill', 'not a fill' in go['label'] and 'Entry quality only' in go['label'], True, group=g)
    C.add('feed.grade_odds', 'graded rows present', sorted((g['asset'], g['grade']) for g in S.feed['grade_odds'] if g['grade'] in ('A+', 'A', 'B', 'C')), sorted(grec), group='2 grade_odds')
    # ---- 3. if_it_misses
    def missfig(lst):
        ms = [x for x in lst if not x['m']['up'] >= 10]
        if not ms: return dict(signals=len(lst), misses=0)
        best = [x['m']['up'] for x in ms]
        return dict(signals=len(lst), misses=len(ms), up_first=sum(b > 0 for b in best), median_peak_pct=L.rhaz(st.median(best), 1),
                    mean_peak_pct=L.rhaz(sum(best) / len(best), 1), peaked_5_or_more=sum(b >= 5 for b in best), peaked_10_or_more=sum(b >= 10 for b in best),
                    median_worst_drop_pct=L.rhaz(st.median(x['m']['dd'] for x in ms), 1), median_day60_pct=L.rhaz(st.median(x['m']['ret'] for x in ms), 1))
    for mi in S.feed['if_it_misses']:
        mm = missfig(G[(mi['asset'], mi['grade'])]); loc = f"feed.if_it_misses {mi['asset']} {mi['grade']}"
        for f in ('signals', 'misses', 'up_first', 'median_peak_pct', 'mean_peak_pct', 'peaked_5_or_more', 'peaked_10_or_more', 'median_worst_drop_pct', 'median_day60_pct'):
            C.add(loc, f, mi.get(f), mm.get(f), group='3 if_it_misses')
        C.add(loc, 'miss_rule', mi['miss_rule'], 'did not rise 10% within 60 days', group='3 if_it_misses')
    C.add('feed.if_it_misses', 'rows present', sorted((m['asset'], m['grade']) for m in S.feed['if_it_misses']), sorted(G), group='3 if_it_misses')
    lim = dt.date(2024, 9, 22)
    known = [x for x in G.get(('ETH', 'A+'), []) if x['d0'] + dt.timedelta(days=60) <= lim]
    mi = S.feed['example_if_it_misses']
    C.add('feed.example_if_it_misses', 'present when there are known signals', mi is not None, bool(known), group='3 example_if_it_misses')
    if mi is not None and known:
        mm = missfig(known)
        for f in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
            C.add('feed.example_if_it_misses', f, mi.get(f), mm.get(f), group='3 example_if_it_misses')
        C.add('feed.example_if_it_misses', 'asset/grade', (mi['asset'], mi['grade']), ('ETH', 'A+'), group='3 example_if_it_misses')
    return S, C, mine, G

if __name__ == '__main__':
    for name in STATES:
        S, C, mine, G = run(name)
        C.save(f'checks_ledger_{name}.csv')
        from collections import Counter
        print(name, len(C.rows), 'checks', len(C.bad()), 'bad')
        print(Counter((r['group'], r['label']) for r in C.bad()).most_common(40))
        for r in C.bad()[:25]: print('  ', r['location'], r['label'], r['shown'], r['yours'], r['cause'])
