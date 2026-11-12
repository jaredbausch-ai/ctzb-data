"""Audit 13 part 1: ledger, grade_odds, if_it_misses, past_paths, odds_fade (both states)."""
import csv, datetime as dt, json, os, pickle, sys, statistics
from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib13 import *
from model13 import Model, GRADED, ASSETS
import rec13 as R

OUT = os.path.dirname(os.path.abspath(__file__))


def rfrac(num, den, nd=0):
    """exact rational num/den rounded half away from zero."""
    if den == 0:
        return None
    f = Fraction(num) / Fraction(den)
    d = Decimal(f.numerator) / Decimal(f.denominator) if False else None
    # exact: scale then round
    sc = Fraction(10) ** nd
    v = f * sc
    sign = -1 if v < 0 else 1
    v = abs(v)
    q, r = divmod(v.numerator, v.denominator)
    if 2 * r >= v.denominator:
        q += 1
    res = sign * q
    return int(res) if nd == 0 else float(Fraction(res) / sc)


def share(k, n, nd=0):
    return rfrac(100 * k, n, nd) if n else None


def r6(x):
    return None if x is None else rha_bin(x, 6)


def r1from6(x):
    return None if x is None else rha(Decimal(repr(r6(x))), 1)


def yn(b):
    return 'yes' if b else 'no'


def num(s):
    if s is None or s == '':
        return None
    try:
        return float(s)
    except ValueError:
        return s


def build(st, now):
    M = Model(st, now)
    led = list(csv.DictReader(open(os.path.join(M.S, 'datasets', 'ledger.csv'))))
    L = {(r['chart'], r['entry']): r for r in led}
    mine = {(s['chart'], str(s['d0'])): s for s in M.closed_signals()}
    # attach the ledger's grade and lenses (out of scope: taken as given) to my signals
    for k, s in mine.items():
        if k in L:
            s['grade'] = L[k]['grade']
            s['lenses'] = set(x for x in L[k]['lenses'].split(' + ') if x != '-')
    M.ledgerset = [mine[k] for k in sorted(mine, key=lambda k: (k[1], k[0].split()[1])) if k in L]
    M.L = L
    return M


def check_ledger(M):
    st = M.st
    L = M.L
    mine = {(s['chart'], str(s['d0'])): s for s in M.closed_signals()}
    # membership
    for k in sorted(set(mine) | set(L)):
        inL, inM = k in L, k in mine
        eth_pre = k[0].startswith('ETH') and k[1] < '2020-03-21'
        if inM and not inL and eth_pre:
            continue   # before ETH's funding data exists (CARD_SPEC); counted below as one check
        R.add(st, 'ledger membership', f'{k[0]} {k[1]} in ledger', yn(inL), yn(inM), 'membership differs')
    pre = [k for k in mine if k not in L and k[0].startswith('ETH') and k[1] < '2020-03-21']
    R.add(st, 'ledger membership', 'ETH signals before 2020-03-21 left out (funding data starts)', len(pre),
          len([k for k in mine if k[0].startswith('ETH') and k[1] < '2020-03-21']), 'pre-2020 ETH row in ledger')
    S = M.ledgerset
    by_asset = {a: [s for s in S if s['a'] == a] for a in ASSETS}
    # grade-level whole-sample odds (gradeReach20 etc.)
    gstat = {}
    for a in ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            G = [s for s in by_asset[a] if s['grade'] == g]
            if G:
                gstat[(a, g)] = (share(sum(s['m']['r20'] for s in G), len(G)), share(sum(s['m']['t30'] for s in G), len(G)),
                                 rha_bin(median([s['m']['dd'] for s in G]), 1))
    for s in S:
        r = L[(s['chart'], str(s['d0']))]
        loc = f"ledger {s['chart']} {s['d0']}"
        m = s['m']
        R.add(st, loc, 'low (trough bar open date)', r['low'], str(s['tdate']), 'trough date')
        R.add(st, loc, 'entryPrice', num(r['entryPrice']), rha_bin(s['entry'], 2), 'entry price')
        R.add(st, loc, 'tags', r['tags'], s['tags'], 'tags')
        R.add(st, loc, 'year', r['year'], str(s['d0'].year), 'year')
        R.add(st, loc, 'reached20', r['reached20'], yn(m['r20']), 'reached20')
        R.add(st, loc, 'touched30', r['touched30'], yn(m['t30']), 'touched30')
        R.add(st, loc, 'reached10', r['reached10'], yn(m['r10']), 'reached10')
        R.add(st, loc, 'reached15', r['reached15'], yn(m['r15']), 'reached15')
        R.add(st, loc, 'surv10', r['surv10'], yn(m['surv']), 'surv10')
        R.add(st, loc, 'scaled20', r['scaled20'], '' if s['sc'] is None else yn(s['sc']), 'scaled20')
        for col, key in (('bestMove', 'up'), ('maxDrawdown', 'dd'), ('dipBeforeHigh', 'ddpk'), ('return60d', 'ret')):
            R.add(st, loc, col, num(r[col]), r6(m[key]), f'{col} 6-place value')
        R.add(st, loc, 'daysToHigh', num(r['daysToHigh']), m['dpk'], 'day of high')
        gs = gstat.get((s['a'], s['grade']))
        R.add(st, loc, 'gradeReach20', num(r['gradeReach20']), gs[0], 'grade reach20')
        R.add(st, loc, 'gradeTouched30', num(r['gradeTouched30']), gs[1], 'grade touched30')
        R.add(st, loc, 'gradeMedDrawdown', num(r['gradeMedDrawdown']), gs[2], 'grade median drawdown')
        # odds on the day
        prior = [h for h in by_asset[s['a']] if h['d0'] + dt.timedelta(days=60) <= s['d0']]
        G = [h for h in prior if h['grade'] == s['grade']]
        if len(G) < 10 or not prior:
            exp = ['', '', '', '', len(G), '', '']
        else:
            def rate(fn, ok=lambda h: True):
                P = [h for h in prior if ok(h)]; Gk = [h for h in G if ok(h)]
                if not P or not Gk:
                    return ''
                base = Fraction(sum(fn(h) for h in P), len(P))
                return rfrac(100 * (sum(fn(h) for h in Gk) + 5 * base), len(Gk) + 5)
            exp = [rate(lambda h: h['m']['r10']), rate(lambda h: h['m']['r20']), rate(lambda h: h['m']['r30']),
                   rate(lambda h: h['m']['t30']), len(G), rate(lambda h: h['m']['surv']),
                   rate(lambda h: bool(h['sc']), ok=lambda h: h['sc'] is not None)]
        for col, v in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10', 'dayScaled20'), exp):
            R.add(st, loc, col, num(r[col]), v, 'odds on the day')
    return gstat


def check_grade_odds(M, feed):
    st = M.st
    S = M.ledgerset
    rows = {(g['asset'], g['grade']): g for g in feed['grade_odds']}
    groups = []
    for a in ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            groups.append((a, g, [s for s in S if s['a'] == a and s['grade'] == g]))
    E = [s for s in S if s['a'] == 'ETH']
    groups.append(('ETH', 'diamond or prime dot', [s for s in E if s['prime'] or s['dis']]))
    groups.append(('ETH', 'no diamond or prime dot', [s for s in E if not (s['prime'] or s['dis'])]))
    for a, g, G in groups:
        f = rows.get((a, g))
        loc = f'feed grade_odds {a} {g}'
        if f is None:
            R.add(st, loc, 'row present', 'missing', 'present', 'row missing'); continue
        n = len(G)
        R.add(st, loc, 'past_trades', f['past_trades'], n, 'n')
        R.add(st, loc, 'past_signals', f.get('past_signals'), n, 'n')
        R.add(st, loc, 'rose10_within60d_pct', f['rose10_within60d_pct'], share(sum(s['m']['r10'] for s in G), n), 'rose10')
        R.add(st, loc, 'rose10_never_fell25_within60d_pct', f['rose10_never_fell25_within60d_pct'], share(sum(s['m']['surv'] for s in G), n), 'surv10')
        R.add(st, loc, 'rose20_within60d_pct', f['rose20_within60d_pct'], share(sum(s['m']['r20'] for s in G), n), 'rose20')
        R.add(st, loc, 'median_deepest_dip_pct', f['median_deepest_dip_pct'], rha_bin(median([s['m']['dd'] for s in G]), 1), 'median dd')
        R.add(st, loc, 'sample', f['sample'], f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}", 'sample range')
        R.add(st, loc, 'label', f['label'], feed['label'], 'label')


def misses_of(G):
    m = [s for s in G if not s['m']['r10']]
    if not m:
        return dict(signals=len(G), misses=0)
    best = [s['m']['up'] for s in m]
    return dict(signals=len(G), misses=len(m), up_first=sum(s['m']['upabove'] for s in m),
                median_peak_pct=rha_bin(median(best), 1), mean_peak_pct=rha_bin(sum(best) / len(best), 1),
                peaked_5_or_more=sum(s['m']['p5'] for s in m), peaked_10_or_more=sum(s['m']['p10'] for s in m),
                median_worst_drop_pct=rha_bin(median([s['m']['dd'] for s in m]), 1),
                median_day60_pct=rha_bin(median([s['m']['ret'] for s in m]), 1),
                median_peak_above_entry_only=rha_bin(median([s['m']['up'] for s in m if s['m']['upabove']]), 1) if any(s['m']['upabove'] for s in m) else None)


def check_misses(M, feed):
    st = M.st; S = M.ledgerset
    rows = {(x['asset'], x['grade']): x for x in feed['if_it_misses']}
    out = {}
    for a in ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            G = [s for s in S if s['a'] == a and s['grade'] == g]
            if not G: continue
            mm = misses_of(G); out[(a, g)] = mm
            f = rows.get((a, g)); loc = f'feed if_it_misses {a} {g}'
            if f is None:
                R.add(st, loc, 'row present', 'missing', 'present', 'row missing'); continue
            for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'mean_peak_pct', 'peaked_5_or_more',
                      'peaked_10_or_more', 'median_worst_drop_pct', 'median_day60_pct'):
                R.add(st, loc, k, f.get(k), mm.get(k), k)
            R.add(st, loc, 'miss_rule', f['miss_rule'], 'did not rise 10% within 60 days', 'wording')
    # example
    known = [s for s in S if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
    mm = misses_of(known); out['example'] = mm
    f = feed.get('example_if_it_misses'); loc = 'feed example_if_it_misses'
    if f is None:
        R.add(st, loc, 'present', 'missing', 'present', 'missing')
    else:
        for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
            R.add(st, loc, k, f.get(k), mm.get(k), k)
        R.add(st, loc, 'asset/grade', f"{f['asset']} {f['grade']}", 'ETH A+', 'scope')
    return out


def qtl(vals, f):
    s = sorted(vals); k = (len(s) - 1) * f; lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def paths_of(M, G, a):
    P = []
    for s in G:
        d = M.day[a]; i0 = d.pos[s['d0']]
        p = [0.0]
        for k in range(1, 61):
            j = i0 + k
            if j >= len(d.dates) or d.dates[j] != s['d0'] + dt.timedelta(days=k):
                break
            if not (d.dates[j] + dt.timedelta(days=1) <= M.today):
                break
            p.append((d.b['c'][j] / s['entry'] - 1) * 100)
        if len(p) == 61:
            P.append(p)
    days = [dict(day=k, q25_pct=rha_bin(qtl([p[k] for p in P], .25), 1), median_pct=rha_bin(qtl([p[k] for p in P], .5), 1),
                 q75_pct=rha_bin(qtl([p[k] for p in P], .75), 1)) for k in range(61)] if P else []
    return dict(signals=len(P), days=days)


def check_paths(M, feed):
    st = M.st; S = M.ledgerset
    out = {}
    pp = {x['asset']: x for x in feed['past_paths']}
    for a in ASSETS:
        G = [s for s in S if s['a'] == a and s['grade'] == 'A+']
        mine = paths_of(M, G, a); out[a] = mine
        f = pp.get(a); loc = f'feed past_paths {a}'
        if f is None:
            R.add(st, loc, 'present', 'missing', 'present', 'missing'); continue
        R.add(st, loc, 'signals', f['signals'], mine['signals'], 'n')
        R.add(st, loc, 'grade', f['grade'], 'A+', 'grade')
        R.add(st, loc, 'days count', len(f['days']), 61, 'days')
        for fd, md in zip(f['days'], mine['days']):
            for k in ('day', 'q25_pct', 'median_pct', 'q75_pct'):
                R.add(st, loc, f"day {md['day']} {k}", fd[k], md[k], 'path quantile')
    known = [s for s in S if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
    mine = paths_of(M, known, 'ETH'); out['example'] = mine
    f = feed.get('example_past_paths'); loc = 'feed example_past_paths'
    R.add(st, loc, 'signals', f['signals'], mine['signals'], 'n')
    R.add(st, loc, 'days count', len(f['days']), 61, 'days')
    for fd, md in zip(f['days'], mine['days']):
        for k in ('day', 'q25_pct', 'median_pct', 'q75_pct'):
            R.add(st, loc, f"day {md['day']} {k}", fd[k], md[k], 'path quantile')
    return out


# ---------------------------------------------------------------- odds fade
def zser(ct):
    out, z = [], None
    for v in ct:
        if v is None:
            out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        out.append(z)
    return out


def check_fade(M, feed):
    st = M.st
    rows = []          # pool for the tier (chart bars, refresh's original rule)
    sigs = {}
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        b = M.bars[('ETH', tf)]
        pv, ct, K = M.piv[('ETH', tf)]
        zm = zser(ct)
        C, D_ = b['c'], b['date']
        for s in M.sig[('ETH', tf)]:
            t = {s['bk'], 'any trough'}
            if s['dis']: t |= {'diamond', 'filled' if s['strong'] else 'hollow'}
            if s['prime']: t.add('prime dot')
            if s['dis'] and s['prime']: t.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: t.add('zone-exit B')
            s['tg'] = t
            ei = s['ei']; e = C[ei]; end = D_[ei] + dt.timedelta(days=60)
            if D_[-1] < end: continue
            j = ei + 1; last = None
            while j < len(D_) and D_[j] <= end:
                last = C[j]; j += 1
            if last is None: continue
            rows.append(dict(chart=f'ETH {tf}', tf=TFD[tf], tags=t, d=D_[ei], win=last / e - 1 > 0))
        sigs[tf] = M.sig[('ETH', tf)]
    upto = dt.date(2026, 1, 1)
    TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
    keep = []
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        for t in TAGS:
            sub = [r for r in rows if r['chart'] == f'ETH {tf}' and t in r['tags'] and r['d'] + dt.timedelta(days=r['tf'] - 1 + 60) < upto]
            if len(sub) >= 8 and 100 * sum(r['win'] for r in sub) / len(sub) >= 70:
                keep.append((f'ETH {tf}', t))
    day = M.day['ETH']
    early, d10 = [], {'green on day 10': [], 'red on day 10': []}
    for tf, lst in sigs.items():
        for s in lst:
            if not any(f'ETH {tf}' == k[0] and k[1] in s['tg'] for k in keep): continue
            d0 = s['d0']
            if d0 not in day.pos: continue
            m = s['m'] if tf in GRADED else measure(day, d0, s['entry'], M.today)
            if m is None: continue
            i0 = day.pos[d0]; e = day.b['c'][i0]
            hl = m['hl']; dys = m['days']; cl = m['closes']
            lo10 = min(l for (h, l), d in zip(hl, dys) if d <= 10)
            hia = max(h for (h, l), d in zip(hl, dys) if d > 10)
            early.append(dict(dip=(lo10 / e - 1) * 100, r10=hia >= e * 1.10, r20=hia >= e * 1.20))
            c10 = [c for c, d in zip(cl, dys) if d == 10]
            if c10:
                d10['green on day 10' if c10[0] >= e else 'red on day 10'].append(dict(r10=hia >= e * 1.10, r20=hia >= e * 1.20))
    BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
    mine_e = []
    for hi, lo, lab in BANDS:
        g = [p for p in early if lo < p['dip'] <= hi]
        if len(g) < 5: continue
        mine_e.append(dict(band=lab, n=len(g), r10=share(sum(p['r10'] for p in g), len(g)), r20=share(sum(p['r20'] for p in g), len(g)),
                           ex=Fraction(100 * sum(p['r10'] for p in g), len(g))))
    mine_d = []
    for lab in ('green on day 10', 'red on day 10'):
        g = d10[lab]
        if len(g) < 5: continue
        mine_d.append(dict(band=lab, n=len(g), r10=share(sum(p['r10'] for p in g), len(g)), r20=share(sum(p['r20'] for p in g), len(g)),
                           ex=Fraction(100 * sum(p['r10'] for p in g), len(g))))
    of = feed['odds_fade']
    R.add(st, 'feed odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70, 'bar')
    R.add(st, 'feed odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)', 'wording')
    R.add(st, 'feed odds_fade', 'early_dip rows', len(of['early_dip']), len(mine_e), 'row count')
    R.add(st, 'feed odds_fade', 'day10 rows', len(of['day10']), len(mine_d), 'row count')
    for kind, F, Mn, key in (('early_dip', of['early_dip'], mine_e, 'band'), ('day10', of['day10'], mine_d, 'check')):
        for f, m in zip(F, Mn):
            loc = f'feed odds_fade {kind} {m["band"]}'
            R.add(st, loc, key, f[key], m['band'], 'band label')
            R.add(st, loc, 'past_trades', f['past_trades'], m['n'], 'n')
            R.add(st, loc, 'past_signals', f.get('past_signals'), m['n'], 'n')
            for k in ('rose10_after_day10_pct', 'rose10_within60d_pct'):
                R.add(st, loc, k, f[k], m['r10'], 'rose10 after day 10')
            for k in ('rose20_after_day10_pct', 'rose20_within60d_pct'):
                R.add(st, loc, k, f[k], m['r20'], 'rose20 after day 10')
            R.add(st, loc, 'edge', f['edge'], 'intact' if m['ex'] >= 70 else 'gone', 'edge on the exact share')
    return dict(keep=keep, early=mine_e, d10=mine_d, n_early=len(early))


def main():
    res = {}
    for st, now in (('replay_0414', dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc)),
                    ('current', None)):
        S = os.path.join(os.path.dirname(OUT), 'a13', st)
        feed = json.load(open(os.path.join(S, 'feed', 'ctzb_feed.json')))
        if now is None:
            now = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
        M = build(st, now)
        gstat = check_ledger(M)
        check_grade_odds(M, feed)
        mi = check_misses(M, feed)
        pa = check_paths(M, feed)
        fa = check_fade(M, feed)
        res[st] = dict(misses=mi, paths=pa, fade=fa)
        print(st, 'tier', fa['keep'], 'early pool', fa['n_early'])
    pickle.dump(res, open(os.path.join(OUT, 'part1.pkl'), 'wb'))
    R.write(os.path.join(OUT, 'part1_checks.csv'), os.path.join(OUT, 'part1_dis.csv'))
    bad = [r for r in R.ROWS if r['ok'] != 'yes']
    print(len(R.ROWS), 'checks', len(bad), 'disagreements')
    for r in bad[:60]:
        print(r)


if __name__ == '__main__':
    main()
