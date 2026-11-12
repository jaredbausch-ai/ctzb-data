"""Checks 2, 3, 4, 7: grade_odds, if_it_misses, odds_fade, past_paths."""
import datetime as dt
from fractions import Fraction as Fr
import core as K
from rec import chk

TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
ETH_CHARTS = ('1D', '2D', '3D', '5D', '8D')


def check(st, C):
    feed, pairs, W = C['feed'], C['pairs'], C['W']
    # ---------------- 2. grade_odds
    by = {}
    for r, s in pairs:
        by.setdefault((r['asset'], r['grade']), []).append((r, s))
    flag = {('ETH', 'diamond or prime dot'): lambda r, s: s['dis'] or s['prime'],
            ('ETH', 'no diamond or prime dot'): lambda r, s: not (s['dis'] or s['prime'])}
    for (a, g), f in flag.items():
        by[(a, g)] = [(r, s) for r, s in pairs if r['asset'] == a and f(r, s)]
    for go in feed['grade_odds']:
        key = (go['asset'], go['grade'])
        loc = f"feed.grade_odds[{go['asset']} {go['grade']}]"
        if key not in by:
            continue  # HTF divergence flag rows: lens logic, out of scope
        rows = by[key]; n = len(rows); ms = [s['m'] for _, s in rows]
        chk(st, loc, 'past_trades', go['past_trades'], n, 'count')
        chk(st, loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], K.share(sum(m['r10'] for m in ms), n), 'share')
        chk(st, loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], K.share(sum(m['surv10'] for m in ms), n), 'share')
        chk(st, loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], K.share(sum(m['r20'] for m in ms), n), 'share')
        chk(st, loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], K.rhaz(K.median([m['dd'] for m in ms]), 1), 'median')
        chk(st, loc, 'sample (first to last signal of the group)', go['sample'], f"{min(s['d0'] for _, s in rows)} to {max(s['d0'] for _, s in rows)}", 'sample range')
        chk(st, loc, 'label is the computed-signal label', go['label'], feed['label'], 'label')

    # ---------------- 3. if_it_misses
    for mi in feed['if_it_misses']:
        loc = f"feed.if_it_misses[{mi['asset']} {mi['grade']}]"
        rows = by.get((mi['asset'], mi['grade']), [])
        ms = [s['m'] for _, s in rows]
        miss = [m for m in ms if not m['r10']]
        best = [m['up'] for m in miss]
        chk(st, loc, 'signals', mi['signals'], len(ms), 'count')
        chk(st, loc, 'misses (did not rise 10% in 60 days)', mi['misses'], len(miss), 'count')
        chk(st, loc, 'up_first (best above entry)', mi['up_first'], sum(b > 0 for b in best), 'count')
        chk(st, loc, 'median_peak_pct', mi['median_peak_pct'], K.rhaz(K.median(best), 1) if best else None, 'median')
        chk(st, loc, 'mean_peak_pct', mi['mean_peak_pct'], K.rhaz(sum(best) / len(best), 1) if best else None, 'mean')
        chk(st, loc, 'peaked_5_or_more', mi['peaked_5_or_more'], sum(b >= 5 for b in best), 'count')
        chk(st, loc, 'peaked_10_or_more', mi['peaked_10_or_more'], sum(b >= 10 for b in best), 'count')
        chk(st, loc, 'median_worst_drop_pct', mi['median_worst_drop_pct'], K.rhaz(K.median([m['dd'] for m in miss]), 1) if miss else None, 'median')
        chk(st, loc, 'median_day60_pct', mi['median_day60_pct'], K.rhaz(K.median([m['ret'] for m in miss]), 1) if miss else None, 'median')
        chk(st, loc, 'miss_rule', mi['miss_rule'], 'did not rise 10% within 60 days', 'wording')
    have = {(m['asset'], m['grade']) for m in feed['if_it_misses']}
    for a in ('ETH', 'BTC'):
        for g in ('A+', 'A', 'B', 'C'):
            chk(st, 'feed.if_it_misses', f'row present {a} {g}', 'present' if (a, g) in have else 'absent', 'present' if by.get((a, g)) else 'absent', 'row')

    # ---------------- 7. past_paths
    for pp in feed['past_paths']:
        a = pp['asset']; loc = f'feed.past_paths[{a}]'
        rows = [(r, s) for r, s in pairs if r['asset'] == a and r['grade'] == 'A+']
        dd = K.Daily(W['root'], a)
        paths = []
        for r, s in rows:
            p = [Fr(0)]
            for k in range(1, 61):
                b = dd.bar(s['d0'] + dt.timedelta(days=k))
                p.append(None if b is None else (b[2] / s['entry'] - 1) * 100)
            if None in p:
                continue
            paths.append(p)
        C.setdefault('pp', {})[a] = dict(n=len(paths), med=[K.quantile([p[k] for p in paths], 0.5) for k in range(61)],
                                          q25=[K.quantile([p[k] for p in paths], 0.25) for k in range(61)], q75=[K.quantile([p[k] for p in paths], 0.75) for k in range(61)])
        chk(st, loc, 'signals', pp['signals'], len(paths), 'count')
        chk(st, loc, 'grade', pp['grade'], 'A+', 'grade')
        chk(st, loc, 'days listed', len(pp['days']), 61, 'days')
        for d in pp['days']:
            k = d['day']
            vals = [p[k] for p in paths]
            for f, key in ((0.25, 'q25_pct'), (0.5, 'median_pct'), (0.75, 'q75_pct')):
                chk(st, loc, f'day {k} {key}', d[key], K.rhaz(K.quantile(vals, f), 1), 'quantile')

    # ---------------- 4. odds_fade (ETH walk-forward tier as of 1 Jan, daily from the entry close)
    of = feed['odds_fade']
    root, now = W['root'], W['now']
    upto = dt.date(now.year, 1, 1)
    rows_all = []           # (tf, signal, tags, win_chartbars, closed_by_upto_exact, closed_by_upto_code, win_daily, daily_closed)
    dd = K.Daily(root, 'ETH')
    for tf in ETH_CHARTS:
        b = W['bars'][('ETH', tf)]; ct = W['ct'][('ETH', tf)]
        z, zm = None, []
        for v in ct:
            if v is None: zm.append(None); continue
            z = None if v >= 60 else (v if z is None else min(z, v)); zm.append(z)
        for s in W['sig'][('ETH', tf)]:
            tg = {s['bk'], 'any trough'}
            if s['dis']:
                tg |= {'diamond', 'filled' if s['filled'] else 'hollow'}
            if s['prime']:
                tg.add('prime dot')
            if s['dis'] and s['prime']:
                tg.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50:
                tg.add('zone-exit B')
            s['tg'] = tg
            ei = s['ei']; d_open = b.D[ei]; end = d_open + dt.timedelta(days=60)
            # the tier's own outcome (refresh.py fw): chart bars opened after the confirmation bar, up to its open + 60 days
            if b.D[-1] < end:
                continue
            js = [j for j in range(ei + 1, b.n) if b.D[j] <= end]
            if not js:
                continue
            win = b.C[js[-1]] > b.C[ei]
            closed_exact = b.end_date(js[-1]) < upto
            closed_code = d_open + dt.timedelta(days=int(tf.rstrip('D')) - 1 + 60) < upto
            wd = dd.bar(s['d0'] + dt.timedelta(days=60))
            rows_all.append(dict(tf=tf, s=s, tg=tg, win=win, ce=closed_exact, cc=closed_code,
                                 wind=(wd[2] > s['entry']) if wd else None, dclosed=s['d0'] + dt.timedelta(days=60) < upto))

    def tier(sel_closed, win_key):
        keep = []
        for tf in ETH_CHARTS:
            for t in TAGS:
                sub = [x for x in rows_all if x['tf'] == tf and t in x['tg'] and x[sel_closed] and x[win_key] is not None]
                if len(sub) >= 8 and Fr(100 * sum(x[win_key] for x in sub), len(sub)) >= 70:
                    keep.append((tf, t))
        return keep
    keep = tier('ce', 'win')
    keep_code = tier('cc', 'win')
    keep_daily = tier('dclosed', 'wind')
    C['tier'] = dict(keep=keep, keep_code=keep_code, keep_daily=keep_daily)
    chk(st, 'odds_fade tier (as of 1 Jan)', 'tier set: exact closed-by-1-Jan vs the code\'s approximation', str(sorted(keep_code)), str(sorted(keep)), 'tier set differs')
    pool = []
    for tf in ETH_CHARTS:
        for s in W['sig'][('ETH', tf)]:
            if not any(tf == k[0] and k[1] in s.get('tg', ()) for k in keep):
                continue
            if not s['complete']:
                continue
            pool.append(s)
    C['fade_pool'] = pool
    eb = [((100, -2), 'shallower than -2%'), ((-2, -5), '-2% to -5%'), ((-5, -10), '-5% to -10%'), ((-10, -20), '-10% to -20%'), ((-20, -100), 'worse than -20%')]
    pts = []
    for s in pool:
        e, w = s['entry'], s['w']
        lo10 = min(x[2] for x in w if x[0] <= 10)
        after = [x for x in w if x[0] > 10]
        hi_after = max(x[1] for x in after)
        d10 = next((x for x in w if x[0] == 10), None)
        pts.append(dict(dip=(lo10 / e - 1) * 100, r10=hi_after >= e * Fr(11, 10), r20=hi_after >= e * Fr(6, 5),
                        run=(hi_after / e - 1) * 100, green=None if d10 is None else d10[3] >= e,
                        dip60=(min(x[2] for x in w) / e - 1) * 100, yr=s['d0'].year))
    chk(st, 'feed.odds_fade', 'sample says "2016 on": first year in the pool', '2016', str(min(p['yr'] for p in pts)), 'sample start')
    shown = {r['band']: r for r in of['early_dip']}
    for (hi, lo), lab in eb:
        g = [p for p in pts if lo < p['dip'] <= hi]
        r = shown.get(lab)
        loc = f'feed.odds_fade.early_dip[{lab}]'
        if len(g) < 5:
            chk(st, loc, 'row present', 'present' if r else 'absent', 'absent', 'row')
            continue
        if not r:
            chk(st, loc, 'row present', 'absent', 'present', 'row'); continue
        r10 = K.share(sum(p['r10'] for p in g), len(g))
        chk(st, loc, 'past_trades', r['past_trades'], len(g), 'count')
        chk(st, loc, 'rose10_within60d_pct', r['rose10_within60d_pct'], r10, 'share')
        chk(st, loc, 'rose20_within60d_pct', r['rose20_within60d_pct'], K.share(sum(p['r20'] for p in g), len(g)), 'share')
        chk(st, loc, 'edge', r['edge'], 'intact' if Fr(100 * sum(p['r10'] for p in g), len(g)) >= 70 else 'gone', 'edge mark')
    shown = {r['check']: r for r in of['day10']}
    for lab, f in (('green on day 10', lambda p: p['green'] is True), ('red on day 10', lambda p: p['green'] is False)):
        g = [p for p in pts if f(p)]
        r = shown.get(lab); loc = f'feed.odds_fade.day10[{lab}]'
        chk(st, loc, 'past_trades', r['past_trades'], len(g), 'count')
        chk(st, loc, 'rose10_within60d_pct', r['rose10_within60d_pct'], K.share(sum(p['r10'] for p in g), len(g)), 'share')
        chk(st, loc, 'rose20_within60d_pct', r['rose20_within60d_pct'], K.share(sum(p['r20'] for p in g), len(g)), 'share')
        chk(st, loc, 'edge', r['edge'], 'intact' if Fr(100 * sum(p['r10'] for p in g), len(g)) >= 70 else 'gone', 'edge mark')
    chk(st, 'feed.odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70, 'bar')
    chk(st, 'feed.odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% within 60 days', 'wording')
    # the same tables with the tier chosen on daily-from-entry outcomes (definitional variant, reported, not counted)
    C['fade_pts'] = pts
