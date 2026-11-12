"""Check 1: every ledger row and membership. Also check 2 (grade_odds), 3 (if_it_misses), 6 (past_paths)."""
import pickle, sys, json, statistics as st
import numpy as np
from mine import *
from checks import rec, num_eq, dump, ROWS

GRADED = ('1D', '2D', '3D', '5D')
CL = 'documented flash-print clamp: repo pulls the BTC 2017-04-15 $0.06 low back to the bar body; raw data gives -99.99%'
for state in ('REPLAY', 'CURRENT'):
    root = STATES[state]
    U = pickle.load(open(f'{S}/audit3/universe_{state}.pkl', 'rb'))
    led = list(csv.DictReader(open(f'{root}/datasets/ledger.csv')))
    feed = json.load(open(f'{root}/feed/ctzb_feed.json'))
    mine_led = {}
    for (a, tf), sig in U['sig'].items():
        if tf not in GRADED: continue
        for s in sig:
            if s['gated'] and s.get('m') and s['funded']:
                mine_led[(s['chart'], str(s['d0']))] = s
    keys_l = {(r['chart'], r['entry']) for r in led}
    for k in sorted(set(mine_led) - keys_l):
        rec(state, '1', f'ledger membership {k[0]} {k[1]}', 'row present', 'absent', 'present', False, 'missing from ledger')
    for k in sorted(keys_l - set(mine_led)):
        rec(state, '1', f'ledger membership {k[0]} {k[1]}', 'row present', 'present', 'absent', False, 'not a qualifying signal by my computation')
    rec(state, '1', 'ledger membership', 'row count', len(led), len(mine_led), len(keys_l ^ set(mine_led)) == 0, 'membership differs')
    # dates on the wrong side: is any ledger row whose 60th day closed only after 'now'? (covered by membership)
    yn = lambda b: 'yes' if b else 'no'
    for r in led:
        s = mine_led.get((r['chart'], r['entry']))
        if not s: continue
        m = s['m']; loc = f"ledger {r['chart']} {r['entry']}"
        # entry is the close of the confirmation bar (ti+3) and equals the daily close on the entry date
        rec(state, '1', loc, 'low (trough date)', r['low'], str(s['tdate']), r['low'] == str(s['tdate']), 'trough date differs')
        rec(state, '1', loc, 'entryPrice', r['entryPrice'], s['entry'], num_eq(r['entryPrice'], s['entry'], 2), 'entry close differs')
        rec(state, '1', loc, 'entry = daily close on entry date', s['daily_close_d0'], s['entry'],
            s['daily_close_d0'] is not None and abs(s['daily_close_d0'] - s['entry']) < 1e-9, 'confirmation close != daily close on its last day')
        rec(state, '1', loc, 'tags', r['tags'], tagstr(s), r['tags'] == tagstr(s), 'tag differs')
        rec(state, '1', loc, 'year', r['year'], s['d0'].year, int(r['year']) == s['d0'].year, 'year differs')
        for lab, val in (('reached10', m['r10']), ('reached15', m['r15']), ('reached20', m['r20']), ('touched30', m['t30']),
                         ('surv10', m['surv10'])):
            rec(state, '1', loc, lab, r[lab], yn(val), r[lab] == yn(val), CL if (r[lab] != yn(val) and s.get('mc') and r[lab] == yn(s['mc'][{'reached10':'r10','reached15':'r15','reached20':'r20','touched30':'t30','surv10':'surv10'}[lab]])) else f'{lab} differs')
        for lab, key in (('bestMove', 'up'), ('maxDrawdown', 'dd'), ('dipBeforeHigh', 'ddpk'), ('return60d', 'ret')):
            ok = abs(float(r[lab]) - m[key]) < 1.5e-6
            cause = f'{lab} differs'
            if not ok and s.get('mc') and abs(float(r[lab]) - s['mc'][key]) < 1.5e-6:
                cause = CL
            rec(state, '1', loc, lab, r[lab], round(m[key], 6), ok, cause)
        rec(state, '1', loc, 'daysToHigh', r['daysToHigh'], m['dpk'], int(r['daysToHigh']) == m['dpk'], 'daysToHigh differs')
        sc = None if s['vr'] is None else m['up'] >= 20 * s['vr']
        rec(state, '1', loc, 'scaled20', r['scaled20'], '' if sc is None else yn(sc), r['scaled20'] == ('' if sc is None else yn(sc)), 'scaled20 differs')
        if m['n'] != 60:
            rec(state, '1', loc, 'daily bars in window', '', m['n'], False, 'daily candle gap inside the 60-day window')
        # boundary cases where % comparison and price comparison disagree
        if (m['up'] >= 10) != m['r10'] or (m['up'] >= 20) != m['r20']:
            rec(state, '1', loc, 'threshold boundary', '', m['up'], False, 'percent vs price comparison disagree at the +10/+20 line')
    # grade odds per ledger grade (as given)
    rows_by = {}
    for r in led:
        s = mine_led.get((r['chart'], r['entry']))
        if s: rows_by.setdefault((r['asset'], r['grade']), []).append((r, s))
    # check 1b: ledger gradeReach20 / gradeTouched30 / gradeMedDrawdown (grade's whole-sample odds)
    for r in led:
        G = rows_by.get((r['asset'], r['grade']), [])
        if not G: continue
        n = len(G)
        loc = f"ledger {r['chart']} {r['entry']}"
        for lab, f_ in (('gradeReach20', lambda K: 100 * sum(x[1][K]['r20'] for x in G) / n),
                       ('gradeTouched30', lambda K: 100 * sum(x[1][K]['t30'] for x in G) / n)):
            v = f_('m'); ok = num_eq(r[lab], v, 0)
            rec(state, '1', loc, lab, r[lab], v, ok, CL if (not ok and num_eq(r[lab], f_('mc'), 0)) else f'{lab} differs')
        v = st.median(x[1]['m']['dd'] for x in G); ok = num_eq(r['gradeMedDrawdown'], v, 1)
        v2 = st.median(x[1]['mc']['dd'] for x in G)
        rec(state, '1', loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], v, ok, CL if (not ok and num_eq(r['gradeMedDrawdown'], v2, 1)) else 'gradeMedDrawdown differs')
    # ---- check 2: grade_odds
    for g in feed['grade_odds']:
        a, gr = g['asset'], g['grade']
        loc = f'feed grade_odds {a} {gr}'
        if gr in ('A+', 'A', 'B', 'C'):
            G = [x[1] for x in rows_by.get((a, gr), [])]
        elif gr in ('diamond or prime dot', 'no diamond or prime dot'):
            want = gr == 'diamond or prime dot'
            G = [x[1] for k, v in rows_by.items() if k[0] == a for x in v if (x[1]['dis'] or x[1]['prime']) == want]
        else:
            rec(state, '2', loc, 'all fields', json.dumps({k: g[k] for k in g if k not in ('label', 'note')}), 'not recomputed', True)
            continue
        n = len(G)
        rec(state, '2', loc, 'past_trades', g['past_trades'], n, g['past_trades'] == n, 'count differs')
        for lab, fn in (('rose10_within60d_pct', lambda m: m['r10']), ('rose10_never_fell25_within60d_pct', lambda m: m['surv10']),
                        ('rose20_within60d_pct', lambda m: m['r20'])):
            v = 100 * sum(fn(s['m']) for s in G) / n; v2 = 100 * sum(fn(s['mc']) for s in G) / n; ok = num_eq(g[lab], v, 0)
            rec(state, '2', loc, lab, g[lab], v, ok, CL if (not ok and num_eq(g[lab], v2, 0)) else f'{lab} differs')
        v = st.median(s['m']['dd'] for s in G); v2 = st.median(s['mc']['dd'] for s in G); ok = num_eq(g['median_deepest_dip_pct'], v, 1)
        rec(state, '2', loc, 'median_deepest_dip_pct', g['median_deepest_dip_pct'], v, ok, CL if (not ok and num_eq(g['median_deepest_dip_pct'], v2, 1)) else 'median differs')
        smp = f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}"
        rec(state, '2', loc, 'sample', g['sample'], smp, g['sample'] == smp, 'sample range differs')
    # ---- check 3: if_it_misses
    for mm in feed['if_it_misses']:
        a, gr = mm['asset'], mm['grade']; loc = f'feed if_it_misses {a} {gr}'
        G = [x[1] for x in rows_by.get((a, gr), [])]
        M = [s for s in G if not s['m']['r10']]
        best = [s['m']['up'] for s in M]
        vals = dict(signals=len(G), misses=len(M), up_first=sum(b > 0 for b in best),
                    peaked_5_or_more=sum(b >= 5 for b in best), peaked_10_or_more=sum(b >= 10 for b in best))
        for k_, v in vals.items():
            rec(state, '3', loc, k_, mm[k_], v, mm[k_] == v, f'{k_} differs')
        for k_, v, v2 in (('median_peak_pct', st.median(best), None), ('mean_peak_pct', st.mean(best), None),
                      ('median_worst_drop_pct', st.median(s['m']['dd'] for s in M), st.median(s['mc']['dd'] for s in M)),
                      ('median_day60_pct', st.median(s['m']['ret'] for s in M), None)):
            ok = num_eq(mm[k_], v, 1)
            rec(state, '3', loc, k_, mm[k_], v, ok, CL if (not ok and v2 is not None and num_eq(mm[k_], v2, 1)) else f'{k_} differs')
        rec(state, '3', loc, 'miss_rule', mm.get('miss_rule'), 'did not rise 10% within 60 days',
            mm.get('miss_rule') == 'did not rise 10% within 60 days', 'rule text')
    # ---- check 6: past_paths
    day = {a: Daily(U['day'][a]) for a in U['day']}
    for pp in feed['past_paths']:
        a = pp['asset']; G = [x[1] for x in rows_by.get((a, 'A+'), [])]
        paths = []
        for s in G:
            p = [0.0]
            okp = True
            for kk in range(1, 61):
                j = day[a].pos.get(s['d0'] + dt.timedelta(days=kk))
                if j is None: okp = False; break
                p.append((day[a].b[j]['c'] / s['entry'] - 1) * 100)
            if okp: paths.append(p)
        rec(state, '6', f'feed past_paths {a}', 'signals', pp['signals'], len(paths), pp['signals'] == len(paths), 'count differs')
        P = np.array(paths)
        for drow in pp['days']:
            d = drow['day']
            for lab, qq in (('q25_pct', 25), ('median_pct', 50), ('q75_pct', 75)):
                v = float(np.percentile(P[:, d], qq))
                ok = num_eq(drow[lab], v, 1)
                cause = 'quantile differs'
                if not ok:
                    v2 = float(np.percentile(np.array([[rhaz(x, 2) for x in p] for p in paths])[:, d], qq))
                    if num_eq(drow[lab], v2, 1): cause = 'double rounding: path values rounded to 2 places before the quantile'
                rec(state, '6', f'feed past_paths {a} day {d}', lab, drow[lab], round(v, 4), ok, cause)
    pickle.dump({'mine_led': mine_led, 'rows_by': rows_by}, open(f'{S}/audit3/ledger_{state}.pkl', 'wb'))
dump('part1.csv')
bad = [r for r in ROWS if r['ok'] == 'no']
print(len(ROWS), 'checks', len(bad), 'bad')
from collections import Counter
print(Counter((r['state'], r['check'], r['label']) for r in bad).most_common(40))
for r in bad[:40]: print(r)
