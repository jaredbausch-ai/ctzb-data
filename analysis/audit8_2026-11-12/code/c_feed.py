import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from sigs import *
import chk

TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]


def zser(ct):
    out, z = [], None
    for v in ct:
        if v is None: out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        out.append(z)
    return out


def sig_tags(s, zm):
    t = {s['bk'], 'any trough'}
    if s['dis']: t |= {'diamond', 'filled' if s['strong'] else 'hollow'}
    if s['prime']: t.add('prime dot')
    if s['dis'] and s['prime']: t.add('diamond+dot')
    if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: t.add('zone-exit B')
    return t


def tier(state, upto):
    S = all_signals(state)
    keep = []; rows = []
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        v = S[('ETH', tf)]; bars = v['bars']; zm = zser(v['ct'])
        for s in v['tr']:
            if not s['gated']: continue
            ei = s['ei']; e = bars[ei]['c']; end = bars[ei]['d'] + dt.timedelta(days=60)
            if bars[-1]['d'] < end: continue
            last = None
            for j in range(ei + 1, len(bars)):
                if bars[j]['d'] > end: break
                last = bars[j]['c']
            if last is None: continue
            rows.append(dict(tf=tf, s=s, tg=sig_tags(s, zm), win=last > e))
        for t in TAGS:
            sub = [r for r in rows if r['tf'] == tf and t in r['tg']
                   and r['s']['conf_open'] + dt.timedelta(days=TFD[tf] - 1 + 60) < upto]
            if len(sub) >= 8 and F(sum(r['win'] for r in sub), len(sub)) >= F(7, 10):
                keep.append((tf, t))
    return keep


def fade(state):
    keep = tier(state, dt.date(TODAY[state].year, 1, 1))
    S = all_signals(state)
    pool = []
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        v = S[('ETH', tf)]; zm = zser(v['ct'])
        for s in v['tr']:
            if not s['gated'] or s['next_open'] is None: continue
            tg = sig_tags(s, zm)
            if not any(k[0] == tf and k[1] in tg for k in keep): continue
            d0 = s['d0']
            b, pos, _ = daily(state, 'ETH')
            if d0 not in pos: continue
            e = b[pos[d0]]['c']
            w = window(state, 'ETH', d0)
            if not w or w[-1][0] != 60: continue
            dip = (min(x['l'] for d, x in w if d <= 10) / e - 1) * 100
            run = (max(x['h'] for d, x in w if d > 10) / e - 1) * 100
            k10 = [x for d, x in w if d == 10]
            pool.append(dict(s=s, dip=dip, run=run, cl10=None if not k10 else (k10[0]['c'] / e - 1) * 100))
    return keep, pool


BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]

for st in ('REPLAY', 'CURRENT'):
    feed = json.load(open(STATES[st] + '/feed/ctzb_feed.json'))
    L = my_ledger(st)
    led = {(r['chart'], r['entry']): r for r in csv.DictReader(open(STATES[st] + '/datasets/ledger.csv'))}
    for k in L: L[k]['grade'] = led[k]['grade']
    # ---------- grade_odds
    groups = {}
    for a in ('ETH', 'BTC'):
        for g in ('A+', 'A', 'B', 'C'):
            groups[(a, g)] = [x for x in L.values() if x['asset'] == a and x['grade'] == g]
    eth = [x for x in L.values() if x['asset'] == 'ETH']
    groups[('ETH', 'diamond or prime dot')] = [x for x in eth if x['prime'] or x['dis']]
    groups[('ETH', 'no diamond or prime dot')] = [x for x in eth if not (x['prime'] or x['dis'])]
    seen = set()
    for go in feed['grade_odds']:
        key = (go['asset'], go['grade']); loc = f"feed grade_odds {go['asset']} {go['grade']}"
        if key not in groups:
            chk.add(st, loc, '(out of scope: lens logic, definitional note h)', 'skipped', 'skipped'); continue
        seen.add(key)
        G = groups[key]; n = len(G)
        exp = dict(past_trades=n, past_signals=n, rose10_within60d_pct=pct(sum(x['m']['r10'] for x in G), n),
                   rose10_never_fell25_within60d_pct=pct(sum(x['m']['surv10'] for x in G), n),
                   rose20_within60d_pct=pct(sum(x['m']['r20'] for x in G), n),
                   median_deepest_dip_pct=rhaz(med([x['m']['dd'] for x in G]), 1),
                   sample=f"{min(x['d0'] for x in G)} to {max(x['d0'] for x in G)}")
        for f_, v in exp.items():
            chk.add(st, loc, f_, go.get(f_), v, 'grade odds')
    chk.add(st, 'feed grade_odds', 'all asset/grade groups present', len(seen), len(groups))
    # ---------- if_it_misses
    for mm in feed['if_it_misses']:
        G = groups[(mm['asset'], mm['grade'])]; loc = f"feed if_it_misses {mm['asset']} {mm['grade']}"
        M = [x for x in G if not x['m']['r10']]
        ups = [x['m']['up'] for x in M]
        exp = dict(signals=len(G), misses=len(M), up_first=sum(u > 0 for u in ups),
                   median_peak_pct=rhaz(med(ups), 1) if M else None, mean_peak_pct=rhaz(sum(ups) / len(ups), 1) if M else None,
                   peaked_5_or_more=sum(u >= 5 for u in ups), peaked_10_or_more=sum(u >= 10 for u in ups),
                   median_worst_drop_pct=rhaz(med([x['m']['dd'] for x in M]), 1) if M else None,
                   median_day60_pct=rhaz(med([x['m']['ret'] for x in M]), 1) if M else None,
                   miss_rule='did not rise 10% within 60 days')
        for f_, v in exp.items():
            chk.add(st, loc, f_, mm.get(f_), v, 'misses')
    chk.add(st, 'feed if_it_misses', 'rows', len(feed['if_it_misses']), 8)
    # ---------- past paths
    def paths(G):
        P = [x['m']['path'] for x in G if x['m']['days_present'] == list(range(1, 61))]
        return len(P), [(rhaz(quant([p[d] for p in P], F(1, 4)), 1), rhaz(quant([p[d] for p in P], F(1, 2)), 1), rhaz(quant([p[d] for p in P], F(3, 4)), 1)) for d in range(61)]
    for pp in feed['past_paths']:
        n, q = paths(groups[(pp['asset'], 'A+')]); loc = f"feed past_paths {pp['asset']}"
        chk.add(st, loc, 'signals', pp['signals'], n, 'paths')
        chk.add(st, loc, 'grade', pp['grade'], 'A+')
        chk.add(st, loc, 'days count', len(pp['days']), 61)
        for d in pp['days']:
            i = d['day']
            for j, f_ in enumerate(('q25_pct', 'median_pct', 'q75_pct')):
                chk.add(st, loc, f"day {i} {f_}", d[f_], q[i][j], 'path quantile')
    ex = [x for x in groups[('ETH', 'A+')] if x['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
    n, q = paths(ex); pp = feed['example_past_paths']; loc = 'feed example_past_paths'
    chk.add(st, loc, 'signals', pp['signals'], n, 'paths')
    for d in pp['days']:
        i = d['day']
        for j, f_ in enumerate(('q25_pct', 'median_pct', 'q75_pct')):
            chk.add(st, loc, f"day {i} {f_}", d[f_], q[i][j], 'path quantile')
    # ---------- odds fade
    keep, pool = fade(st)
    print(st, 'tier', sorted(keep), 'pool', len(pool))
    of = feed['odds_fade']; loc = 'feed odds_fade'
    chk.add(st, loc, 'posting_bar_pct', of['posting_bar_pct'], 70)
    exp_ed = []
    for hi, lo, lab in BANDS:
        g = [p for p in pool if lo < p['dip'] <= hi]
        if len(g) < 5: continue
        exp_ed.append((lab, len(g), pct(sum(p['run'] >= 10 for p in g), len(g)), pct(sum(p['run'] >= 20 for p in g), len(g)),
                       'intact' if F(sum(p['run'] >= 10 for p in g), len(g)) >= F(7, 10) else 'gone'))
    chk.add(st, loc, 'early_dip rows', len(of['early_dip']), len(exp_ed))
    for row, e in zip(of['early_dip'], exp_ed):
        l2 = f"{loc} early_dip {e[0]}"
        chk.add(st, l2, 'band', row['band'], e[0])
        for f_, v in (('past_trades', e[1]), ('past_signals', e[1]), ('rose10_after_day10_pct', e[2]), ('rose20_after_day10_pct', e[3]),
                      ('rose10_within60d_pct', e[2]), ('rose20_within60d_pct', e[3]), ('edge', e[4])):
            chk.add(st, l2, f_, row.get(f_), v, 'odds fade')
    grp = {'green on day 10': [p for p in pool if p['cl10'] is not None and p['cl10'] >= 0],
           'red on day 10': [p for p in pool if p['cl10'] is not None and p['cl10'] < 0]}
    exp_d = [(k, v) for k, v in grp.items() if len(v) >= 5]
    chk.add(st, loc, 'day10 rows', len(of['day10']), len(exp_d))
    for row, (lab, g) in zip(of['day10'], exp_d):
        l2 = f"{loc} day10 {lab}"; n = len(g)
        r10 = pct(sum(p['run'] >= 10 for p in g), n); r20 = pct(sum(p['run'] >= 20 for p in g), n)
        chk.add(st, l2, 'check', row['check'], lab)
        for f_, v in (('past_trades', n), ('past_signals', n), ('rose10_after_day10_pct', r10), ('rose20_after_day10_pct', r20),
                      ('rose10_within60d_pct', r10), ('rose20_within60d_pct', r20),
                      ('edge', 'intact' if F(sum(p['run'] >= 10 for p in g), n) >= F(7, 10) else 'gone')):
            chk.add(st, l2, f_, row.get(f_), v, 'odds fade')
    # fade in-sample share (for the label finding)
    ins = [p for p in pool if p['s']['d0'] < dt.date(TODAY[st].year, 1, 1)]
    print(st, 'fade pool', len(pool), 'of which confirmed before the tier anchor', len(ins), 'yrs', sorted({p['s']['d0'].year for p in pool}))
chk.dump('_feed.csv')
bad = [c for c in chk.CHECKS if c['ok'] == 'no']
print(len(chk.CHECKS), 'checks', len(bad), 'bad')
for c in bad[:60]: print(c)
