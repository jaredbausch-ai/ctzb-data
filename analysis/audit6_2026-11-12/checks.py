"""Checks 1-7: ledger, grade_odds, if_it_misses, odds_fade, cards, open_signals, past_paths."""
import csv, datetime as dt, json, math, os, sys, statistics
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *  # noqa
from state import State, eth_funding_ok

PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
UNPLAIN = {v: k for k, v in PLAIN.items()}


class Checker:
    def __init__(self, state):
        self.st = state
        self.rows = []

    def add(self, loc, label, shown, yours, ok=None, cause=''):
        if ok is None:
            ok = eq(shown, yours)
        self.rows.append(dict(state=self.st, location=loc, label=label, shown=fmtv(shown), yours=fmtv(yours),
                              ok='yes' if ok else 'NO', cause='' if ok else cause))
        return ok


def fmtv(v):
    if v is None:
        return 'null'
    if isinstance(v, float):
        return repr(v)
    return str(v)


def eq(a, b):
    if a is None or a == '':
        return b is None or b == ''
    if b is None or b == '':
        return False
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def num(v):
    if v in (None, ''):
        return None
    try:
        return float(v)
    except ValueError:
        return v


# ------------------------------------------------------------------ 1. ledger
def check_ledger(S, ck):
    exp = S.expected_ledger()
    key = lambda s: (f"{s['a']} {s['tf']}", str(s['d0']))
    E = {key(s): s for s in exp}
    L = {(r['chart'], r['entry']): r for r in S.ledger}
    for k in sorted(set(E) - set(L)):
        ck.add('ledger membership', f'{k[0]} {k[1]}', 'absent', 'present', False, 'signal with a closed 60-day window missing from ledger')
    for k in sorted(set(L) - set(E)):
        ck.add('ledger membership', f'{k[0]} {k[1]}', 'present', 'absent', False, 'ledger row with no matching closed gated signal')
    ck.add('ledger membership', 'row count', len(L), len(E))
    for k in sorted(set(E) & set(L)):
        s, r = E[k], L[k]; m = s['m']; loc = f'ledger {k[0]} {k[1]}'
        yn = lambda b: 'yes' if b else 'no'
        ck.add(loc, 'low (trough bar open date)', r['low'], str(s['tdate']), cause='trough date')
        ck.add(loc, 'entryPrice', float(r['entryPrice']), rh(s['entry'], 2), cause='entry close')
        ck.add(loc, 'tags', r['tags'], tagstr(s), cause='tag')
        ck.add(loc, 'reached20', r['reached20'], yn(m['r20']), cause='+20% test')
        ck.add(loc, 'touched30', r['touched30'], yn(m['t30']), cause='-30% test')
        ck.add(loc, 'bestMove', float(r['bestMove']), rh(m['up'], 6), cause='best move')
        ck.add(loc, 'maxDrawdown', float(r['maxDrawdown']), rh(m['dd'], 6), cause='deepest dip')
        ck.add(loc, 'dipBeforeHigh', float(r['dipBeforeHigh']), rh(m['ddpk'], 6), cause='dip before high')
        ck.add(loc, 'return60d', float(r['return60d']), rh(m['ret'], 6), cause='day-60 return')
        ck.add(loc, 'daysToHigh', int(r['daysToHigh']), m['dpk'], cause='day of high')
        ck.add(loc, 'year', int(r['year']), s['d0'].year)
        ck.add(loc, 'reached10', r['reached10'], yn(m['r10']), cause='+10% test')
        ck.add(loc, 'reached15', r['reached15'], yn(m['r15']), cause='+15% test')
        ck.add(loc, 'surv10', r['surv10'], yn(m['surv10']), cause='surv10 test')
        ck.add(loc, 'scaled20', r['scaled20'], '' if s['sc'] is None else yn(s['sc']), cause='scaled20 test')
    return E, L


def ledger_extra(S, ck, E, L):
    """grade-record and odds-on-the-day columns, from the ledger's own grades (given) and my outcomes."""
    by = {}
    for k, r in L.items():
        if k in E:
            by.setdefault((r['asset'], r['grade']), []).append(E[k])
    rec = {}
    for (a, g), G in by.items():
        n = len(G)
        rec[(a, g)] = (share(sum(s['m']['r20'] for s in G), n), share(sum(s['m']['t30'] for s in G), n),
                       rh(med([s['m']['dd'] for s in G]), 1))
    hist = sorted([(r['asset'], E[k]['d0'], r['grade'], E[k]) for k, r in L.items() if k in E], key=lambda x: x[1])
    for k, r in sorted(L.items()):
        if k not in E:
            continue
        loc = f"ledger {k[0]} {k[1]}"
        g = rec[(r['asset'], r['grade'])]
        ck.add(loc, 'gradeReach20', num(r['gradeReach20']), g[0], cause='grade record')
        ck.add(loc, 'gradeTouched30', num(r['gradeTouched30']), g[1], cause='grade record')
        ck.add(loc, 'gradeMedDrawdown', num(r['gradeMedDrawdown']), g[2], cause='grade record')
        d0 = E[k]['d0']
        prior = [h for h in hist if h[0] == r['asset'] and h[1] + dt.timedelta(days=61) <= d0]
        G = [h for h in prior if h[2] == r['grade']]
        ck.add(loc, 'dayN', int(r['dayN']), len(G), cause='odds-on-the-day sample')
        if len(G) < 10 or not prior:
            for c in ('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'daySurv10', 'dayScaled20'):
                ck.add(loc, c, r[c], '', cause='odds on the day')
            continue

        def rate(fn):
            base = Fraction(sum(fn(h[3]) for h in prior), len(prior))
            return rh((Fraction(sum(fn(h[3]) for h in G)) + 5 * base) * 100 / (len(G) + 5))
        up = lambda s: s['m']['up']
        ck.add(loc, 'dayReach10', num(r['dayReach10']), rate(lambda s: s['m']['r10']), cause='odds on the day')
        ck.add(loc, 'dayReach20', num(r['dayReach20']), rate(lambda s: s['m']['r20']), cause='odds on the day')
        ck.add(loc, 'dayReach30', num(r['dayReach30']), rate(lambda s: s['m']['up'] >= 30), cause='odds on the day')
        ck.add(loc, 'dayTouched30', num(r['dayTouched30']), rate(lambda s: s['m']['t30']), cause='odds on the day')
        ck.add(loc, 'daySurv10', num(r['daySurv10']), rate(lambda s: s['m']['surv10']), cause='odds on the day')
        ck.add(loc, 'dayScaled20', num(r['dayScaled20']), rate(lambda s: bool(s['sc'])), cause='odds on the day')


# ------------------------------------------------------------------ 2. grade_odds
def check_grade_odds(S, ck, E, L):
    rows = [(r, E[k]) for k, r in L.items() if k in E]
    for go in S.feed['grade_odds']:
        a, g = go['asset'], go['grade']
        loc = f'feed grade_odds {a} {g}'
        if g in ('A+', 'A', 'B', 'C'):
            G = [s for r, s in rows if r['asset'] == a and r['grade'] == g]
        elif g == 'diamond or prime dot':
            G = [s for r, s in rows if r['asset'] == a and (s['dis'] or s['prime'])]
        elif g == 'no diamond or prime dot':
            G = [s for r, s in rows if r['asset'] == a and not (s['dis'] or s['prime'])]
        else:
            continue      # (h) HTF-divergence rows: lens logic, out of scope
        n = len(G)
        ck.add(loc, 'past_trades', go['past_trades'], n, cause='grade sample size')
        if not n:
            continue
        ck.add(loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], share(sum(s['m']['r10'] for s in G), n), cause='+10% share')
        ck.add(loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], share(sum(s['m']['surv10'] for s in G), n), cause='surv10 share')
        ck.add(loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], share(sum(s['m']['r20'] for s in G), n), cause='+20% share')
        ck.add(loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], rh(med([s['m']['dd'] for s in G]), 1), cause='median deepest dip')
        ck.add(loc, 'sample', go['sample'], f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}", cause='sample dates')


# ------------------------------------------------------------------ 3. if_it_misses
def misses_of(G):
    ms = [s for s in G if not s['m']['r10']]
    b = [s['m']['up'] for s in ms]
    return dict(signals=len(G), misses=len(ms), up_first=sum(x > 0 for x in b),
                median_peak_pct=rh(med(b), 1) if b else None, mean_peak_pct=rh(sum(b) / len(b), 1) if b else None,
                peaked_5_or_more=sum(x >= 5 for x in b), peaked_10_or_more=sum(Fraction(1) for s in ms if s['m']['r10']),
                median_worst_drop_pct=rh(med([s['m']['dd'] for s in ms]), 1) if ms else None,
                median_day60_pct=rh(med([s['m']['ret'] for s in ms]), 1) if ms else None)


def check_misses(S, ck, E, L):
    rows = [(r, E[k]) for k, r in L.items() if k in E]
    seen = set()
    for x in S.feed['if_it_misses']:
        a, g = x['asset'], x['grade']; seen.add((a, g))
        G = [s for r, s in rows if r['asset'] == a and r['grade'] == g]
        mine = misses_of(G)
        for f in ('signals', 'misses', 'up_first', 'median_peak_pct', 'mean_peak_pct', 'peaked_5_or_more',
                  'peaked_10_or_more', 'median_worst_drop_pct', 'median_day60_pct'):
            ck.add(f'feed if_it_misses {a} {g}', f, x[f], mine[f], cause='miss statistics')
        ck.add(f'feed if_it_misses {a} {g}', 'miss_rule', x['miss_rule'], 'did not rise 10% within 60 days')
    for a in ('ETH', 'BTC'):
        for g in ('A+', 'A', 'B', 'C'):
            if (a, g) not in seen and any(r['asset'] == a and r['grade'] == g for r, s in rows):
                ck.add('feed if_it_misses', f'{a} {g}', 'absent', 'present', False, 'row missing')


# ------------------------------------------------------------------ 4. odds_fade
TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
EARLY_BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"),
               (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]


def chart_tags(S, a, tf, s):
    ct, K = S.ct[(a, tf)]
    t = [s['bk'], 'any trough']
    if s['dis']:
        t += ['diamond', 'filled' if s['strong'] else 'hollow']
    if s['prime']:
        t.append('prime dot')
    if s['dis'] and s['prime']:
        t.append('diamond+dot')
    # zone-exit B: bucket B, CT < 60, and CT's running minimum since it was last >= 60 is >= 50
    z = None
    for i in range(s['ti'] + 1):
        v = ct[i]
        if v is None:
            continue
        z = None if v >= 60 else (v if z is None else min(z, v))
    if s['bk'] == 'B' and s['ct'] < 60 and z is not None and z >= 50:
        t.append('zone-exit B')
    return t


def odds_fade_mine(S):
    """(g) tier by refresh.py's original rule on each ETH chart's own bars; groupings and outcomes on
    daily candles from the entry close."""
    upto = dt.date(S.today.year, 1, 1)
    rows = []
    for tf in TFS:
        bars = S.A['ETH'].bars[tf]
        D = [b['t'] for b in bars]
        for s in S.sig[('ETH', tf)]:
            i = s['ei']
            end = D[i] + dt.timedelta(days=60)
            if D[-1] < end:
                continue
            j, last = i + 1, None
            while j < len(D) and D[j] <= end:
                last = bars[j]['c']; j += 1
            if last is None:
                continue
            rows.append(dict(tf=tf, s=s, d=D[i], win=last / bars[i]['c'] - 1 > 0, tags=set(chart_tags(S, 'ETH', tf, s))))
    keep = []
    for tf in TFS:
        for t in TAGS:
            sub = [r for r in rows if r['tf'] == tf and t in r['tags']
                   and r['d'] + dt.timedelta(days=int(tf[:-1]) - 1 + 60) < upto]
            if len(sub) >= 8 and Fraction(sum(r['win'] for r in sub) * 100, len(sub)) >= 70:
                keep.append((tf, t))
    A = S.A['ETH']
    pool, hold = [], {'green on day 10': [], 'red on day 10': []}
    for tf in TFS:
        for s in S.sig[('ETH', tf)]:
            if not s['confirmed']:
                continue
            tg = set(chart_tags(S, 'ETH', tf, s))
            if not any(k[0] == tf and k[1] in tg for k in keep):
                continue
            if not complete(A, s['d0']):
                continue
            w = window(A, s['d0'])
            e = A.C[A.pos[s['d0']]]
            E_ = Fraction(e)
            lo10 = min(x[2] for x in w if x[0] <= 10)
            hi_after = max(x[1] for x in w if x[0] > 10)
            pool.append(dict(dip=Fraction(lo10) / E_ * 100 - 100, mfe=Fraction(hi_after) / E_ * 100 - 100))
            c10 = next(x[3] for x in w if x[0] == 10)
            hold['green on day 10' if c10 >= e else 'red on day 10'].append(dict(run=Fraction(hi_after) / E_ * 100 - 100))
    early = []
    for hi, lo, lab in EARLY_BANDS:
        g = [p for p in pool if lo < p['dip'] <= hi]
        if len(g) < 5:
            continue
        early.append(dict(band=lab, n=len(g), r10=share(sum(p['mfe'] >= 10 for p in g), len(g)),
                          r20=share(sum(p['mfe'] >= 20 for p in g), len(g))))
    d10 = []
    for lab in ('green on day 10', 'red on day 10'):
        g = hold[lab]
        if len(g) < 5:
            continue
        d10.append(dict(check=lab, n=len(g), r10=share(sum(x['run'] >= 10 for x in g), len(g)),
                        r20=share(sum(x['run'] >= 20 for x in g), len(g))))
    return keep, early, d10


def check_odds_fade(S, ck):
    keep, early, d10 = odds_fade_mine(S)
    of = S.feed['odds_fade']
    ck.add('feed odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70)
    ck.add('feed odds_fade', 'early_dip row count', len(of['early_dip']), len(early), cause='band count')
    for x, y in zip(of['early_dip'], early):
        loc = f"feed odds_fade early_dip {y['band']}"
        ck.add(loc, 'band', x['band'], y['band'])
        ck.add(loc, 'past_trades', x['past_trades'], y['n'], cause='odds-fade grouping')
        ck.add(loc, 'rose10_within60d_pct', x['rose10_within60d_pct'], y['r10'], cause='odds-fade outcome')
        ck.add(loc, 'rose20_within60d_pct', x['rose20_within60d_pct'], y['r20'], cause='odds-fade outcome')
        ck.add(loc, 'edge', x['edge'], 'intact' if y['r10'] >= 70 else 'gone', cause='edge mark')
    ck.add('feed odds_fade', 'day10 row count', len(of['day10']), len(d10))
    for x, y in zip(of['day10'], d10):
        loc = f"feed odds_fade day10 {y['check']}"
        ck.add(loc, 'check', x['check'], y['check'])
        ck.add(loc, 'past_trades', x['past_trades'], y['n'], cause='odds-fade grouping')
        ck.add(loc, 'rose10_within60d_pct', x['rose10_within60d_pct'], y['r10'], cause='odds-fade outcome')
        ck.add(loc, 'rose20_within60d_pct', x['rose20_within60d_pct'], y['r20'], cause='odds-fade outcome')
        ck.add(loc, 'edge', x['edge'], 'intact' if y['r10'] >= 70 else 'gone', cause='edge mark')
    return keep, early, d10


# ------------------------------------------------------------------ 5. cards
def card_figures(G):
    n = len(G)
    M = lambda k: [s['m'][k] for s in G]
    sc = [s['sc'] for s in G if s['sc'] is not None]
    old = [s for s in G if s['d0'] < SPLIT]; new = [s for s in G if s['d0'] >= SPLIT]
    sv = lambda X: share(sum(s['m']['surv10'] for s in X), len(X)) if X else None
    out = dict(past_trades=n,
               rose10_never_fell25_within60d_pct=share(sum(M('surv10')), n),
               beat_normal_move_pct=share(sum(sc), len(sc)) if sc else None,
               rose20_within60d_pct=share(sum(M('r20')), n),
               rose10_within60d_pct=share(sum(M('r10')), n),
               typical_biggest_rise_pct=rh(med(M('up')), 1), typical_dip_before_rise_pct=rh(med(M('ddpk')), 1),
               typical_deepest_dip_pct=rh(med(M('dd')), 1),
               typical_biggest_rise_exact_pct=rh(med(M('up')), 6), typical_dip_before_rise_exact_pct=rh(med(M('ddpk')), 6),
               typical_deepest_dip_exact_pct=rh(med(M('dd')), 6),
               fell30_within60d_pct=share(sum(M('t30')), n))
    out['before_2022'] = dict(past_trades=len(old), rose10_never_fell25_within60d_pct=sv(old))
    out['since_2022'] = dict(past_trades=len(new), rose10_never_fell25_within60d_pct=sv(new))
    t10 = [x for x in M('d10') if x is not None]; t20 = [x for x in M('d20') if x is not None]
    out['typical_day_first_rose10'] = rh(med_exact(t10)) if t10 else None
    out['typical_day_first_rose20'] = rh(med_exact(t20)) if t20 else None
    out['typical_day_of_60d_high'] = rh(med_exact(M('dpk')))
    out['typical_day_of_deepest_dip'] = rh(med_exact(M('ddday')))
    out['from_entry'] = dict(past_trades=n, still_rose10_pct=share(sum(x == 'ok' for x in M('fe')), n),
                             went_on_to_fall25_pct=share(sum(x == 'liq' for x in M('fe')), n))
    lad = []
    for th in (5, 10, 15, 20):
        r = [s['m']['lad'][th] for s in G]
        hit = sum(x is not None for x in r)
        lad.append(dict(fell_pct=th, past_trades=hit, still_rose10_pct=share(sum(x == 'ok' for x in r), hit),
                        went_on_to_fall25_pct=share(sum(x == 'liq' for x in r), hit)))
    out['if_it_falls_first'] = lad
    return out


def card_sample(S, E, L, a, tf, grade, lenses, known_by=None, example=False):
    rows = [(r, E[k]) for k, r in L.items() if k in E]
    if known_by is not None:
        rows = [(r, s) for r, s in rows if s['d0'] + dt.timedelta(days=60) <= known_by]
    ls = lambda r: frozenset(x for x in r['lenses'].split(' + ') if x and x != '-')
    ex = [s for r, s in rows if r['chart'] == f'{a} {tf}' and ls(r) == lenses]
    sg = [s for r, s in rows if r['chart'] == f'{a} {tf}' and r['grade'] == grade]
    ag = [s for r, s in rows if r['asset'] == a and r['grade'] == grade]
    tail = ' whose 60 days had closed by then' if example else ''
    if len(ex) >= 15:
        basis = (f'all {len(ex)} {a} {tf} signals with exactly the same confirmations{tail}' if example
                 else f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations')
        return basis, ex
    if len(sg) >= 15:
        only = 'none' if not ex else f'only {len(ex)}'
        basis = (f'all {len(sg)} {a} {tf} signals graded {grade}{tail} ({only} had exactly the same confirmations, too few to use)' if example
                 else f'all {len(sg)} past {a} {tf} signals graded {grade} ({only} had exactly the same confirmations, too few to use)')
        return basis, sg
    basis = (f'all {len(ag)} grade {grade} signals across all {a} charts{tail} ({a} {tf} alone had only {len(sg)}, too few to use)' if example
             else f'all {len(ag)} past grade {grade} signals across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)')
    return basis, ag


def compare_card(ck, loc, c, mine):
    for f in ('past_trades', 'rose10_never_fell25_within60d_pct', 'beat_normal_move_pct', 'rose20_within60d_pct',
              'rose10_within60d_pct', 'typical_biggest_rise_pct', 'typical_dip_before_rise_pct', 'typical_deepest_dip_pct',
              'typical_biggest_rise_exact_pct', 'typical_dip_before_rise_exact_pct', 'typical_deepest_dip_exact_pct',
              'fell30_within60d_pct', 'typical_day_first_rose10', 'typical_day_first_rose20', 'typical_day_of_60d_high',
              'typical_day_of_deepest_dip'):
        ck.add(loc, f, c.get(f), mine[f], cause='card figure')
    for era in ('before_2022', 'since_2022'):
        for f in ('past_trades', 'rose10_never_fell25_within60d_pct'):
            ck.add(loc, f'{era}.{f}', c[era][f], mine[era][f], cause='era split')
    for f in ('past_trades', 'still_rose10_pct', 'went_on_to_fall25_pct'):
        ck.add(loc, f'from_entry.{f}', c['from_entry'][f], mine['from_entry'][f], cause='from-entry row')
    for x, y in zip(c['if_it_falls_first'], mine['if_it_falls_first']):
        for f in ('fell_pct', 'past_trades', 'still_rose10_pct', 'went_on_to_fall25_pct'):
            ck.add(loc, f"ladder {y['fell_pct']}%.{f}", x[f], y[f], cause='ladder')


def low_day_mine(S, a, tf, tdate):
    bars = S.A[a].bars[tf]
    b = next((x for x in bars if x['t'] == tdate), None)
    if b is None:
        return None
    A = S.A[a]
    return str(min(b['days'], key=lambda d: (A.L[A.pos[d]], d)))


def kill_close(S, a, tf, ti):
    """Smallest confirmation close at which CT at ti+3 stays above CT at the trough, the open bar taken at
    its current price (d). Returns the exact boundary."""
    bars = S.A[a].bars[tf]
    C = [b['c'] for b in bars]
    n = len(C)
    ct = rsi(C)
    v = ct[ti]
    if n - 1 == ti + 3:
        base = C[:-1]
    elif n - 1 == ti + 2:
        base = C[:]
    else:
        return None
    lo, hi = C[-1] * 0.3, C[-1] * 2.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if rsi(base + [mid])[-1] > v:
            hi = mid
        else:
            lo = mid
    return hi


def check_cards(S, ck, E, L):
    f = S.feed
    # forming cards
    forming = []
    for a in ('ETH', 'BTC'):
        for tf in TFS:
            bars = S.A[a].bars[tf]
            tr, ct, K = troughs(bars)
            n = len(bars)
            # a provisional low: pivot whose right side is not yet complete (1-3 bars), every later CT above it
            for back in (1, 2, 3):
                ti = n - 1 - back
                v = ct[ti]
                if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)):
                    continue
                if any(ct[j] <= v for j in range(ti + 1, n)):
                    continue
                forming.append(dict(a=a, tf=tf, ti=ti, need=3 - back, tdate=bars[ti]['t'], ct=v, k=K[ti]))
                break
    shown = {c['signal_id']: c for c in f['cards']}
    mine_ids = {}
    for p in forming:
        a, tf = p['a'], p['tf']
        bars = S.A[a].bars[tf]
        # confirmation bar = ti+3; its close date by the 1-January bucket rule
        tdays = int(tf[:-1])
        o = bars[p['ti']]['t']
        for _ in range(3):
            o = bucket_span(o, tdays)[1] + dt.timedelta(days=1)
        conf = bucket_span(o, tdays)[1]
        sid = f'{a}-{tf}-{conf}'
        mine_ids[sid] = (p, conf)
    for sid in sorted(set(shown) | set(mine_ids)):
        if sid not in mine_ids:
            ck.add('feed cards', sid, 'present', 'no forming low', False, 'forming card not reproduced'); continue
        p, conf = mine_ids[sid]
        if sid not in shown:
            # cards are only built for graded and ungraded charts alike in stack_live; flag
            ck.add('feed cards', sid, 'absent', 'forming low', False, 'forming low without a card'); continue
        c = shown[sid]; a, tf = p['a'], p['tf']; loc = f'feed card {sid}'
        ck.add(loc, 'low_date', c['low_date'], str(p['tdate']), cause='trough bar date')
        ck.add(loc, 'low_day', c['low_day'], low_day_mine(S, a, tf, p['tdate']), cause='low day')
        ck.add(loc, 'confirms_on', c['confirms_on'], str(conf), cause='confirmation date')
        ck.add(loc, 'bars_to_confirm', c['bars_to_confirm'], p['need'], cause='bars to confirm')
        kc = kill_close(S, a, tf, p['ti'])
        ck.add(loc, 'must_close_above', c['must_close_above'], None if kc is None else rh(kc, 2), cause='kill close')
        ck.add(loc, 'price_now', c['price_now'], rh(S.A[a].C[-1], 2), cause='latest price')
        ck.add(loc, 'entry_close', c['entry_close'], None)
        lens = frozenset(UNPLAIN[x] for x in c['confirmations'].split('; ') if x != 'none')
        basis, G = card_sample(S, E, L, a, tf, c['grade'], lens)
        ck.add(loc, 'sample', c['sample'], basis, cause='sample rule')
        compare_card(ck, loc, c, card_figures(G))
    # example card
    x = f['example_card']
    if x:
        k = ('ETH 2D', '2024-09-22')
        r = L[k]
        lens = frozenset(y for y in r['lenses'].split(' + ') if y != '-')
        loc = 'feed example_card'
        s = E[k]
        ck.add(loc, 'grade', x['grade'], r['grade'], cause='grade (ledger)')
        ck.add(loc, 'confirmations', x['confirmations'], '; '.join(PLAIN[l] for l in r['lenses'].split(' + ')), cause='lenses (ledger)')
        ck.add(loc, 'low_date', x['low_date'], str(s['tdate']))
        ck.add(loc, 'low_day', x['low_day'], low_day_mine(S, 'ETH', '2D', s['tdate']), cause='low day')
        ck.add(loc, 'confirms_on', x['confirms_on'], str(s['d0']))
        ck.add(loc, 'entry_close', x['entry_close'], rh(s['entry'], 2))
        ck.add(loc, 'price_now', x['price_now'], None)
        basis, G = card_sample(S, E, L, 'ETH', '2D', r['grade'], lens, known_by=dt.date(2024, 9, 22), example=True)
        ck.add(loc, 'sample', x['sample'], basis, cause='sample rule')
        compare_card(ck, loc, x, card_figures(G))
    return forming


# ------------------------------------------------------------------ 6. open signals
def open_mine(S):
    out = []
    for a in ('ETH', 'BTC'):
        A = S.A[a]
        for tf in GRADED:
            for s in S.sig[(a, tf)]:
                if not s['confirmed']:
                    continue
                el = (S.today - s['d0']).days
                if not 0 <= el <= 60:
                    continue
                w = window(A, s['d0'])           # closed daily bars only
                e = s['entry']
                mk = lambda k: next((rh((x[3] / e - 1) * 100, 1) for x in w if x[0] == k), None)
                out.append(dict(s=s, sid=f"{a}-{tf}-{s['d0']}", el=el, d10=mk(10), d30=mk(30), d60=mk(60),
                                best=rh((max(x[1] for x in w) / e - 1) * 100, 1) if w else None,
                                worst=rh((min(x[2] for x in w) / e - 1) * 100, 1) if w else None))
    return out


def check_open(S, ck, E, L):
    mine = {o['sid']: o for o in open_mine(S)}
    shown = {o['signal_id']: o for o in S.feed['open_signals']}
    for sid in sorted(set(mine) | set(shown)):
        if sid not in shown:
            ck.add('feed open_signals', sid, 'absent', 'open', False, 'open signal missing'); continue
        if sid not in mine:
            ck.add('feed open_signals', sid, 'present', 'not open', False, 'not an open signal'); continue
        o, m = shown[sid], mine[sid]; s = m['s']; loc = f'feed open_signal {sid}'
        ck.add(loc, 'chart', o['chart'], f"{s['a']} {s['tf']}")
        ck.add(loc, 'entry_date', o['entry_date'], str(s['d0']))
        ck.add(loc, 'entry_close', o['entry_close'], rh(s['entry'], 2), cause='entry close')
        ck.add(loc, 'tags', o['tags'], tagstr(s), cause='tag')
        ck.add(loc, 'days_elapsed', o['days_elapsed'], m['el'], cause='day count')
        for f_, k in (('day10_pct', 'd10'), ('day30_pct', 'd30'), ('day60_pct', 'd60'), ('best_so_far_pct', 'best'), ('worst_so_far_pct', 'worst')):
            ck.add(loc, f_, o[f_], m[k], cause='open progress')
        c = o['card']
        if c is None:
            ck.add(loc, 'card', 'null', 'card', False, 'no card'); continue
        cl = f'feed open_signal {sid} card'
        ck.add(cl, 'signal_id', c['signal_id'], sid)
        ck.add(cl, 'grade', c['grade'], o['grade'], cause='card grade vs signal grade')
        ck.add(cl, 'low_date', c['low_date'], str(s['tdate']), cause='trough bar date')
        ck.add(cl, 'low_day', c['low_day'], low_day_mine(S, s['a'], s['tf'], s['tdate']), cause='low day')
        ck.add(cl, 'confirms_on', c['confirms_on'], str(s['d0']))
        ck.add(cl, 'bars_to_confirm', c['bars_to_confirm'], None)
        ck.add(cl, 'must_close_above', c['must_close_above'], None)
        ck.add(cl, 'price_now', c['price_now'], rh(S.A[s['a']].C[-1], 2), cause='latest price')
        ck.add(cl, 'entry_close', c['entry_close'], rh(s['entry'], 2), cause='entry close')
        lens = frozenset(UNPLAIN[x] for x in c['confirmations'].split('; ') if x != 'none')
        ck.add(cl, 'confirmations vs signal lenses', '+'.join(sorted(lens)) or '-',
               '+'.join(sorted(x for x in o['confirmations'].split(' + ') if x != '-')) or '-', cause='lens list mismatch')
        basis, G = card_sample(S, E, L, s['a'], s['tf'], c['grade'], lens)
        ck.add(cl, 'sample', c['sample'], basis, cause='sample rule')
        compare_card(ck, cl, c, card_figures(G))
    return mine


# ------------------------------------------------------------------ 7. past paths
def paths_mine(S, E, L):
    out = {}
    for a in ('ETH', 'BTC'):
        A = S.A[a]
        P = []
        for k, r in L.items():
            if r['asset'] != a or r['grade'] != 'A+' or k not in E:
                continue
            s = E[k]
            p = [0.0]
            for d in range(1, 61):
                i = A.pos[s['d0'] + dt.timedelta(days=d)]
                p.append((A.C[i] / s['entry'] - 1) * 100)
            P.append(p)
        out[a] = P
    return out


def check_paths(S, ck, E, L):
    mine = paths_mine(S, E, L)
    for pp in S.feed['past_paths']:
        a = pp['asset']; P = mine[a]; loc = f'feed past_paths {a}'
        ck.add(loc, 'signals', pp['signals'], len(P), cause='path count')
        ck.add(loc, 'day rows', len(pp['days']), 61)
        for d in pp['days']:
            k = d['day']
            col = [p[k] for p in P]
            ck.add(loc, f'day {k} q25_pct', d['q25_pct'], rh(quant(col, 0.25), 1), cause='path quantile')
            ck.add(loc, f'day {k} median_pct', d['median_pct'], rh(quant(col, 0.5), 1), cause='path quantile')
            ck.add(loc, f'day {k} q75_pct', d['q75_pct'], rh(quant(col, 0.75), 1), cause='path quantile')
    return mine
