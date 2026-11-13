"""Audit 21 -- data checks 1-7 for one state folder. Returns (checks, mine) where mine is my own
model of everything a member sees (used by the page checks)."""
import csv, datetime as dt, json, math, os, statistics as st, sys
from fractions import Fraction
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C
from core import rnd, D1

EX_DATE = dt.date(2024, 9, 22)
SPLIT = dt.date(2022, 1, 1)
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
UNPLAIN = {v: k for k, v in PLAIN.items()}
LABEL = ("Computed signal, not a fill. No trade was taken. Entry quality only: "
         "the data has no exits, so this is not a strategy return or a track record.")
gp = lambda g: 'the top grade' if g == 'A+' else 'the same grade'


def norm(v):
    if v is None or v == '': return None
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)):
        f = float(v)
        return 0.0 if f == 0 else f
    if isinstance(v, str):
        try:
            f = float(v)
            return 0.0 if f == 0 else f
        except ValueError:
            return v
    return v


class Checks:
    def __init__(self, state):
        self.state = state; self.rows = []

    def add(self, loc, label, shown, mine, cause=''):
        a, b = norm(shown), norm(mine)
        ok = a == b
        if not ok and isinstance(a, float) and isinstance(b, float) and (math.isnan(a) and math.isnan(b)): ok = True
        self.rows.append([self.state, loc, label, '' if shown is None else shown, '' if mine is None else mine, 'ok' if ok else 'DIFF', '' if ok else cause])
        return ok

    def flag(self, loc, label, shown, mine, cause):
        self.rows.append([self.state, loc, label, shown, mine, 'DIFF', cause])

    @property
    def n(self): return len(self.rows)

    @property
    def bad(self): return [r for r in self.rows if r[5] != 'ok']


def rcsv(p):
    if not os.path.exists(p): return []
    with open(p, newline='') as f: return list(csv.DictReader(f))


def share(k, n): return rnd(100 * k / n) if n else None


def funding(root, a):
    anyv, mean = {}, {}
    p = os.path.join(root, 'data', 'derivs', f'{a}_funding_daily.csv')
    if not os.path.exists(p): return anyv, mean
    for r in rcsv(p):
        d = dt.date.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): anyv[d] = float(v)
        if r.get('funding_mean') not in ('', None): mean[d] = float(r['funding_mean'])
    return anyv, mean


def run(root, state, now, deep=True):
    """now: aware datetime (the clock). deep=False skips nothing; kept for symmetry."""
    today = now.date()
    ck = Checks(state)
    S = C.State(root, today)
    feed = json.load(open(os.path.join(root, 'feed', 'ctzb_feed.json')))
    led = rcsv(os.path.join(root, 'datasets', 'ledger.csv'))
    mine = dict(today=today, now=now, feed=feed, ledger=led)

    # ---------------------------------------------------------------- my signal table
    sig = {}
    for (a, tf), c in S.ch.items():
        for s in c.sig:
            if s['d0'] is not None: sig[(s['chart'], str(s['d0']))] = s
    comp = {k: s for k, s in sig.items() if s['m'] is not None and s['tf'] in C.GRADED}

    # ---------------------------------------------------------------- 1. ledger
    FA, FM = {a: funding(root, a)[0] for a in C.ASSETS}, {a: funding(root, a)[1] for a in C.ASSETS}
    def eth_ok(d0):
        f = FA['ETH']
        if d0 not in f or sum(1 for k in range(1, 91) if d0 - dt.timedelta(days=k) in f) < 60: return False
        m = FM['ETH']
        return sum(1 for k in range(7) if d0 - dt.timedelta(days=k) in m) >= 5 and sum(1 for k in range(7) if d0 - dt.timedelta(days=14 + k) in m) >= 5
    expect = {k for k, s in comp.items() if s['a'] == 'BTC' or eth_ok(s['d0'])}
    have = {(r['chart'], r['entry']) for r in led}
    ck.add('ledger', 'row count', len(led), len(expect), 'ledger membership')
    for k in sorted(expect - have): ck.flag('ledger', f'missing signal {k[0]} {k[1]}', 'absent', 'present', 'a complete gated signal is not in the ledger')
    for k in sorted(have - expect): ck.flag('ledger', f'extra row {k[0]} {k[1]}', 'present', 'absent', 'ledger row is not a complete gated signal by my engine')
    ck.add('ledger', 'duplicate rows', len(led) - len(have), 0)
    ck.add('ledger', 'sorted by entry then chart within asset', [(r['asset'] != 'ETH', r['entry']) for r in led] == sorted((r['asset'] != 'ETH', r['entry']) for r in led), True)
    L = []   # ledger rows joined to my signal
    for r in led:
        s = comp.get((r['chart'], r['entry']))
        if s is None: continue
        L.append((r, s))
    # grade stats from my measures, the ledger's grade as given
    G = {}
    for r, s in L: G.setdefault((r['asset'], r['grade']), []).append((r, s))
    gstat = {}
    for (a, g), xs in G.items():
        n = len(xs); ms = [s['m'] for _, s in xs]
        gstat[(a, g)] = dict(n=n, r10=share(sum(m['r10'] for m in ms), n), surv=share(sum(m['surv10'] for m in ms), n), r20=share(sum(m['r20'] for m in ms), n),
                             t30=share(sum(m['t30'] for m in ms), n), meddd=rnd(st.median(m['dd'] for m in ms), 1),
                             sample=f"{min(s['d0'] for _, s in xs)} to {max(s['d0'] for _, s in xs)}")
    hist = sorted(L, key=lambda x: x[1]['d0'])
    for r, s in L:
        loc = f"ledger {r['chart']} {r['entry']}"; m = s['m']; a = r['asset']
        ck.add(loc, 'asset', r['asset'], s['a']); ck.add(loc, 'low', r['low'], str(s['tdate']), 'trough bar open date')
        ck.add(loc, 'entryPrice', r['entryPrice'], rnd(s['entry'], 2), 'confirmation close')
        ck.add(loc, 'tags', r['tags'], s['tags'], 'tags'); ck.add(loc, 'year', r['year'], s['d0'].year)
        yn = lambda v: 'yes' if v else 'no'
        ck.add(loc, 'reached20', r['reached20'], yn(m['r20']), 'daily high >= entry x 1.20')
        ck.add(loc, 'touched30', r['touched30'], yn(m['t30']), 'daily low <= entry x 0.70')
        ck.add(loc, 'reached10', r['reached10'], yn(m['r10']), 'daily high >= entry x 1.10')
        ck.add(loc, 'reached15', r['reached15'], yn(m['r15']), 'daily high >= entry x 1.15')
        ck.add(loc, 'surv10', r['surv10'], yn(m['surv10']), 'rose 10% and never fell 25.3%')
        ck.add(loc, 'scaled20', r['scaled20'], None if m['sc'] is None else yn(m['sc']), 'beat a normal move')
        ck.add(loc, 'bestMove', r['bestMove'], rnd(m['up'], 6)); ck.add(loc, 'maxDrawdown', r['maxDrawdown'], rnd(m['dd'], 6))
        ck.add(loc, 'dipBeforeHigh', r['dipBeforeHigh'], rnd(m['ddpk'], 6)); ck.add(loc, 'return60d', r['return60d'], rnd(m['ret'], 6))
        ck.add(loc, 'daysToHigh', r['daysToHigh'], m['dpk'])
        gs = gstat[(a, r['grade'])]
        ck.add(loc, 'gradeReach20', r['gradeReach20'], gs['r20'], 'grade record'); ck.add(loc, 'gradeTouched30', r['gradeTouched30'], gs['t30'], 'grade record')
        ck.add(loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], gs['meddd'], 'grade record')
        # odds on the day: priors of the same asset whose 60th day had closed by this entry date
        prior = [x for x in hist if x[0]['asset'] == a and x[1]['d0'] + dt.timedelta(days=60) <= s['d0']]
        Gp = [x for x in prior if x[0]['grade'] == r['grade']]
        ck.add(loc, 'dayN', r['dayN'], len(Gp), 'known-by-then count')
        def rate(fn, ok=lambda m: True):
            P = [x for x in prior if ok(x[1]['m'])]; Gk = [x for x in Gp if ok(x[1]['m'])]
            if not P or not Gk: return None
            base = sum(fn(x[1]['m']) for x in P) / len(P)
            return rnd(100 * (sum(fn(x[1]['m']) for x in Gk) + 5 * base) / (len(Gk) + 5))
        if len(Gp) < 10 or not prior: exp = [None] * 6
        else: exp = [rate(lambda m: m['r10']), rate(lambda m: m['r20']), rate(lambda m: m['r30']), rate(lambda m: m['t30']),
                     rate(lambda m: m['surv10']), rate(lambda m: bool(m['sc']), ok=lambda m: m['sc'] is not None)]
        for col, v in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'daySurv10', 'dayScaled20'), exp):
            ck.add(loc, col, r[col], v, 'odds on the day')

    # ---------------------------------------------------------------- 2. grade_odds
    my_go = []
    for go in feed.get('grade_odds') or []:
        a, g = go['asset'], go['grade']; loc = f'grade_odds {a} {g}'
        if g in ('A+', 'A', 'B', 'C'): xs = G.get((a, g), [])
        elif g == 'diamond or prime dot': xs = [x for x in L if x[0]['asset'] == a and (x[1]['dis'] or x[1]['prime'])]
        elif g == 'no diamond or prime dot': xs = [x for x in L if x[0]['asset'] == a and not (x[1]['dis'] or x[1]['prime'])]
        else:
            ck.add(loc, 'label', go.get('label'), LABEL); continue        # HTF-divergence rows: lens logic, out of scope
        n = len(xs); ms = [s['m'] for _, s in xs]
        mg = dict(asset=a, grade=g, past_trades=n, past_signals=n,
                  rose10_within60d_pct=share(sum(m['r10'] for m in ms), n), rose10_never_fell25_within60d_pct=share(sum(m['surv10'] for m in ms), n),
                  rose20_within60d_pct=share(sum(m['r20'] for m in ms), n), median_deepest_dip_pct=rnd(st.median(m['dd'] for m in ms), 1) if n else None,
                  sample=f"{min(s['d0'] for _, s in xs)} to {max(s['d0'] for _, s in xs)}" if n else None, label=LABEL)
        for k, v in mg.items(): ck.add(loc, k, go.get(k), v, 'grade record')
        my_go.append(mg)
    for a in C.ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            if any(r['asset'] == a for r in led) and not any(x['asset'] == a and x['grade'] == g for x in feed.get('grade_odds') or []):
                ck.flag(f'grade_odds {a} {g}', 'row present', 'absent', 'expected', 'grade row missing')
    mine['grade_odds'] = my_go

    # ---------------------------------------------------------------- 3. if_it_misses
    def miss_stats(xs):
        mm = [s['m'] for _, s in xs if not s['m']['r10']]
        m1 = lambda v: rnd(st.median(v), 1) if v else None
        return dict(signals=len(xs), misses=len(mm), up_first=sum(m['above'] for m in mm), median_peak_pct=m1([m['up'] for m in mm]),
                    mean_peak_pct=rnd(st.mean(m['up'] for m in mm), 1) if mm else None, peaked_5_or_more=sum(m['up'] >= 5 for m in mm),
                    peaked_10_or_more=sum(m['r10'] for m in mm), median_worst_drop_pct=m1([m['dd'] for m in mm]), median_day60_pct=m1([m['ret'] for m in mm]))
    my_miss = []
    exp_rows = [(a, g) for a in C.ASSETS if G.get((a, 'A+')) for g in ('A+', 'A', 'B', 'C') if G.get((a, g))]
    fm = feed.get('if_it_misses') or []
    ck.add('if_it_misses', 'rows (asset, grade)', json.dumps([[x['asset'], x['grade']] for x in fm]), json.dumps([list(x) for x in exp_rows]))
    for x in fm:
        a, g = x['asset'], x['grade']; loc = f'if_it_misses {a} {g}'
        ms = miss_stats(G.get((a, g), [])); ms.update(asset=a, grade=g, label=LABEL, miss_rule='did not rise 10% within 60 days')
        for k, v in ms.items(): ck.add(loc, k, x.get(k), v, 'misses')
        my_miss.append(ms)
    mine['if_it_misses'] = my_miss
    known = [x for x in L if x[1]['d0'] + dt.timedelta(days=60) <= EX_DATE]
    exk = [x for x in known if x[0]['asset'] == 'ETH' and x[0]['grade'] == 'A+']
    xm = feed.get('example_if_it_misses')
    my_xm = None
    if exk:
        my_xm = miss_stats(exk); my_xm.pop('mean_peak_pct'); my_xm.pop('peaked_5_or_more'); my_xm.pop('peaked_10_or_more')
        my_xm.update(asset='ETH', grade='A+', label=LABEL, miss_rule='did not rise 10% within 60 days')
    if xm is None or my_xm is None: ck.add('example_if_it_misses', 'present', xm is not None, my_xm is not None)
    else:
        for k, v in my_xm.items(): ck.add('example_if_it_misses', k, xm.get(k), v, 'example misses (known by 2024-09-22)')
    mine['example_if_it_misses'] = my_xm

    # ---------------------------------------------------------------- 4. odds_fade (walk-forward tier, own code)
    TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
    pool = []
    for tf in C.TFS:
        c = S.ch[('ETH', tf)]; b = c.b
        z = None; zm = []
        for v in c.ct:
            if v is None: zm.append(None); continue
            z = None if v >= 60 else (v if z is None else min(z, v)); zm.append(z)
        for s in c.sig:
            t = {s['bk'], 'any trough'}
            if s['dis']: t |= {'diamond', 'filled' if s['strong'] else 'hollow'}
            if s['prime']: t.add('prime dot')
            if s['dis'] and s['prime']: t.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: t.add('zone-exit B')
            s['tg'] = t
            end = b.date[s['ei']] + dt.timedelta(days=60)
            if b.date[-1] < end: continue
            js = [j for j in range(s['ei'] + 1, b.n) if b.date[j] <= end]
            if not js: continue
            pool.append(dict(chart=s['chart'], tf=tf, tags=t, d=b.date[s['ei']], win=b.cc[js[-1]] > s['entry_c'], s=s))
    anchor = dt.date(today.year, 1, 1)
    keep = []
    for tf in C.TFS:
        for t in TAGS:
            sub = [r for r in pool if r['tf'] == tf and t in r['tags'] and r['d'] + dt.timedelta(days=C.bar_len(tf) - 1 + 60) < anchor]
            if len(sub) >= 8 and Fraction(sum(r['win'] for r in sub), len(sub)) >= Fraction(70, 100): keep.append((f'ETH {tf}', t))
    mine['tier'] = keep
    T = [r for r in pool if any(r['chart'] == c_ and t in r['tags'] for c_, t in keep)]
    of = feed.get('odds_fade') or {}
    data_end = max(S.ch[('ETH', tf)].b.date[-1] for tf in C.TFS)
    if len(T) >= 4:
        span = max(0.25, ((data_end - dt.timedelta(days=60)) - min(r['d'] for r in T)).days / 365.25)
        tay = f'{rnd(len(T) / span)} on average'
    else: tay = '—'
    wins = []
    dayb = S.day['ETH']
    for tf in C.TFS:
        for s in S.ch[('ETH', tf)].sig:
            if s['d0'] is None or s['d0'] not in dayb.pos: continue
            if not any(c_ == s['chart'] and t in s['tg'] for c_, t in keep): continue
            w = S.window('ETH', s['d0'])
            if not w or (dayb.date[w[-1]] - s['d0']).days < 60 or dayb.date[w[-1]] >= today: continue
            wins.append((s, w))
    bands = [("shallower than -2%", None, 98), ("-2% to -5%", 98, 95), ("-5% to -10%", 95, 90), ("-10% to -20%", 90, 80), ("worse than -20%", 80, None)]
    my_fade = dict(posting_bar_pct=70, tier_fixed_on=str(anchor), early_dip=[], day10=[], edge_measured_on='rose 10% after day 10 (days 11 to 60)', label=LABEL)
    grp = {b_[0]: [] for b_ in bands}; g10 = {'green on day 10': [], 'red on day 10': []}
    for s, w in wins:
        ec = s['entry_c']; d0 = s['d0']
        first = [k for k in w if (dayb.date[k] - d0).days <= 10]; after = [k for k in w if (dayb.date[k] - d0).days > 10]
        lo = min(dayb.lc[k] for k in first); hi = max(dayb.hc[k] for k in after)
        res = (hi * 100 >= ec * 110, hi * 100 >= ec * 120)
        for name, upper, lower in bands:   # upper/lower as percent of entry: lower < low <= upper
            if (upper is None or lo * 100 <= ec * upper) and (lower is None or lo * 100 > ec * lower): grp[name].append(res)
        k10 = [k for k in w if (dayb.date[k] - d0).days == 10]
        if k10: g10['green on day 10' if dayb.cc[k10[0]] >= ec else 'red on day 10'].append(res)
    def frow(key, name, g):
        n = len(g); k10 = sum(x[0] for x in g); k20 = sum(x[1] for x in g)
        return {key: name, 'past_trades': n, 'past_signals': n, 'rose10_after_day10_pct': share(k10, n), 'rose20_after_day10_pct': share(k20, n),
                'rose10_within60d_pct': share(k10, n), 'rose20_within60d_pct': share(k20, n), 'edge': 'intact' if Fraction(100 * k10, n) >= 70 else 'gone'}
    my_fade['early_dip'] = [frow('band', name, grp[name]) for name, _, _ in bands if len(grp[name]) >= 5]
    my_fade['day10'] = [frow('check', name, g10[name]) for name in g10 if len(g10[name]) >= 5]
    mine['odds_fade'] = my_fade; mine['trades_a_year'] = tay
    if feed.get('extras_withheld') or not of.get('early_dip'):
        ck.add('odds_fade', 'present', bool(of.get('early_dip')), bool(my_fade['early_dip']) and not feed.get('extras_withheld'))
    else:
        for k in ('posting_bar_pct', 'tier_fixed_on', 'edge_measured_on', 'label'): ck.add('odds_fade', k, of.get(k), my_fade[k], 'odds fade')
        ck.add('odds_fade', 'sample names the tier date', f"{anchor.day} {anchor:%b %Y}" in (of.get('sample') or ''), True)
        for key, lst in (('band', 'early_dip'), ('check', 'day10')):
            ck.add(f'odds_fade {lst}', 'rows', json.dumps([x.get(key) for x in of.get(lst, [])]), json.dumps([x[key] for x in my_fade[lst]]), 'odds fade rows')
            for x in of.get(lst, []):
                mrow = next((y for y in my_fade[lst] if y[key] == x.get(key)), None)
                if mrow is None: continue
                for k, v in mrow.items(): ck.add(f'odds_fade {lst} {x.get(key)}', k, x.get(k), v, 'odds fade')

    # ---------------------------------------------------------------- 5. cards
    def low_day(a, tf, tdate):
        b = S.ch[(a, tf)].b; i = b.pos[tdate]
        nxt = b.date[i + 1] if i + 1 < b.n else C.next_open(tdate, C.bar_len(tf))
        cand = [(S.day[a].l[S.day[a].pos[tdate + dt.timedelta(days=j)]], tdate + dt.timedelta(days=j)) for j in range((nxt - tdate).days) if tdate + dt.timedelta(days=j) in S.day[a].pos]
        return str(min(cand)[1]) if cand else str(tdate)

    def lens_set(txt, plain):
        if txt in ('', '-', 'none', None): return frozenset()
        if plain: return frozenset(UNPLAIN.get(x, x) for x in txt.split('; '))
        return frozenset(txt.split(' + '))

    def sample_for(a, tf, grade, lenses, base, example=False):
        chart = f'{a} {tf}'
        ex = [x for x in base if x[0]['chart'] == chart and lens_set(x[0]['lenses'], False) == lenses]
        sg = [x for x in base if x[0]['chart'] == chart and x[0]['grade'] == grade]
        ag = [x for x in base if x[0]['asset'] == a and x[0]['grade'] == grade]
        if not example:
            if len(ex) >= 15: return f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex
            if len(sg) >= 15: return f'all {len(sg)} past {a} {tf} signals of {gp(grade)} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
            return f'all {len(ag)} past signals of {gp(grade)} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag
        if len(ex) >= 15: return f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', ex
        if len(sg) >= 15: return f'all {len(sg)} {a} {tf} signals of {gp(grade)} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
        return f'all {len(ag)} signals of {gp(grade)} across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', ag

    def figures(xs):
        ss = [s for _, s in xs]; ms = [s['m'] for s in ss]; n = len(ss)
        sc = [m['sc'] for m in ms if m['sc'] is not None]
        old = [s for s in ss if s['d0'] < SPLIT]; new = [s for s in ss if s['d0'] >= SPLIT]
        sv = lambda X: share(sum(s['m']['surv10'] for s in X), len(X)) if X else None
        mround = lambda v: rnd(st.median(v)) if v else None
        fe = [S.from_entry(s) for s in ss]
        out = dict(past_trades=n, past_signals=n,
                   rose10_never_fell25_within60d_pct=share(sum(m['surv10'] for m in ms), n), beat_normal_move_pct=share(sum(sc), len(sc)) if sc else None,
                   rose20_within60d_pct=share(sum(m['r20'] for m in ms), n), rose10_within60d_pct=share(sum(m['r10'] for m in ms), n),
                   typical_biggest_rise_pct=rnd(st.median(m['up'] for m in ms), 1) if n else None, typical_dip_before_rise_pct=rnd(st.median(m['ddpk'] for m in ms), 1) if n else None,
                   typical_deepest_dip_pct=rnd(st.median(m['dd'] for m in ms), 1) if n else None,
                   typical_biggest_rise_exact_pct=rnd(st.median(m['up'] for m in ms), 6) if n else None, typical_dip_before_rise_exact_pct=rnd(st.median(m['ddpk'] for m in ms), 6) if n else None,
                   typical_deepest_dip_exact_pct=rnd(st.median(m['dd'] for m in ms), 6) if n else None,
                   fell30_within60d_pct=share(sum(m['t30'] for m in ms), n),
                   before_2022=dict(past_trades=len(old), past_signals=len(old), rose10_never_fell25_within60d_pct=sv(old)),
                   since_2022=dict(past_trades=len(new), past_signals=len(new), rose10_never_fell25_within60d_pct=sv(new)),
                   typical_day_first_rose10=mround([m['t10'] for m in ms if m['t10'] is not None]), typical_day_first_rose20=mround([m['t20d'] for m in ms if m['t20d'] is not None]),
                   typical_day_of_60d_high=mround([m['dpk'] for m in ms]), typical_day_of_deepest_dip=mround([m['ddday'] for m in ms]),
                   from_entry=dict(past_trades=n, past_signals=n, still_rose10_pct=share(fe.count('ok'), n), went_on_to_fall25_pct=share(fe.count('liq'), n),
                                   still_rose10_exact_pct=rnd(100 * fe.count('ok') / n, 6) if n else None),
                   if_it_falls_first=[])
        fr = [Fraction(100 * fe.count('ok'), n) if n else None]
        for th in (5, 10, 15, 20):
            ff = [x for x in (S.falls_first(s, th) for s in ss) if x is not None]; hit = len(ff)
            out['if_it_falls_first'].append(dict(fell_pct=th, past_trades=hit, past_signals=hit, still_rose10_pct=share(ff.count('ok'), hit), went_on_to_fall25_pct=share(ff.count('liq'), hit),
                                                 still_rose10_exact_pct=rnd(100 * ff.count('ok') / hit, 6) if hit else None))
            fr.append(Fraction(100 * ff.count('ok'), hit) if hit else None)
        edge = 0 if (fr[0] is not None and fr[0] < 70) else next((-th for th, f in zip((5, 10, 15, 20), fr[1:]) if f is not None and f < 70), None)
        out['_edge'] = edge
        return out

    def cmp_card(loc, fc, mc):
        for k, v in mc.items():
            if k.startswith('_'): continue
            if isinstance(v, dict):
                for k2, v2 in v.items(): ck.add(loc, f'{k}.{k2}', (fc.get(k) or {}).get(k2), v2, 'card figure')
            elif isinstance(v, list):
                fl = fc.get(k) or []
                ck.add(loc, f'{k} rows', len(fl), len(v))
                for i, row in enumerate(v):
                    for k2, v2 in row.items(): ck.add(loc, f'{k}[{row["fell_pct"]}].{k2}', fl[i].get(k2) if i < len(fl) else None, v2, 'ladder')
            else: ck.add(loc, k, fc.get(k), v, 'card figure')
        for x in fc.get('active_confluences') or []:   # counts are lens logic; the window dates are checkable
            ck.add(loc, f"confluence {x.get('after')} window_closes", x.get('window_closes'), str(dt.date.fromisoformat(x['after_confirmed']) + dt.timedelta(days=10)), 'confluence window = confirmation + 10 days')

    withheld = bool(feed.get('cards_withheld'))
    # forming lows by my engine
    forming = {}
    for (a, tf), c in S.ch.items():
        p = c.forming()
        if p: forming[f'{a} {tf}'] = p
    mine['forming'] = forming
    my_cards = []
    fcards = feed.get('cards') or []
    for fc in fcards:
        ch = fc.get('chart'); loc = f"card forming {fc.get('signal_id')}"
        p = forming.get(ch)
        if p is None:
            ck.flag(loc, 'forming low exists', 'card', 'no forming low', 'card without a forming low by my engine'); continue
        a, tf = p['a'], p['tf']
        ck.add(loc, 'graded chart', tf in C.GRADED, True, 'cards only on 1D-5D'); ck.add(loc, 'gate on at the trough date', bool(S.gate(p['tdate'])), True, 'forming card with the gate off at its trough')
        basis, xs = sample_for(a, tf, fc['grade'], lens_set(fc['confirmations'], True), L)
        mc = dict(label=LABEL, signal_id=f"{a}-{tf}-{p['confirms']}", chart=ch, asset=a, timeframe=tf, low_date=str(p['tdate']), low_day=low_day(a, tf, p['tdate']),
                  confirms_on=str(p['confirms']), bars_to_confirm=p['need'], must_close_above=p['kill'], price_now=rnd(p['price'], 2), entry_close=None, sample=basis)
        mc.update(figures(xs)); mc['grade'] = fc['grade']; mc['_kind'] = 'forming'
        ck.add(loc, 'sample non-empty', len(xs) > 0, True, 'forming card with an empty sample')
        ck.add(loc, 'filter on, on the day the low printed (the card\'s "Low" date; How to read: "on the day its low printed")', bool(S.gate(dt.date.fromisoformat(mc['low_day']))), True,
               f"label vs meaning: the gate is read on the trough bar's open date {p['tdate']} (on), but the low printed on {mc['low_day']}, when the filter was off")
        cmp_card(loc, fc, mc); my_cards.append(mc)
    if not withheld:
        for ch, p in forming.items():
            if p['tf'] in C.GRADED and S.gate(p['tdate']) and not any(fc.get('chart') == ch for fc in fcards):
                pools = [len(G.get((p['a'], g), [])) for g in ('A+', 'A', 'B', 'C')]
                if all(pools): ck.flag(f'card forming {ch}', 'card exists', 'no card', 'expected', 'forming low on a graded chart, gate on, every grade pool non-empty, but no card')
    mine['cards'] = my_cards

    # example card
    fx = feed.get('example_card'); my_ex = None
    exrow = next((x for x in L if x[0]['chart'] == 'ETH 2D' and x[0]['entry'] == str(EX_DATE)), None)
    if exrow is not None:
        r, s = exrow
        basis, xs = sample_for('ETH', '2D', r['grade'], lens_set(r['lenses'], False), known, example=True)
        my_ex = dict(label=LABEL, signal_id='ETH-2D-2024-09-22', chart='ETH 2D', asset='ETH', timeframe='2D', low_date=str(s['tdate']), low_day=low_day('ETH', '2D', s['tdate']),
                     confirms_on=str(s['d0']), bars_to_confirm=None, must_close_above=None, price_now=None, entry_close=rnd(s['entry'], 2), sample=basis, example=True)
        my_ex.update(figures(xs)); my_ex['grade'] = r['grade']; my_ex['_kind'] = 'example'
        my_ex['confirmations'] = '; '.join(PLAIN.get(k, k) for k in r['lenses'].split(' + ')) if r['lenses'] not in ('-', '') else 'none'
    if withheld: ck.add('example_card', 'withheld', fx is None, True)
    elif fx is None or my_ex is None: ck.add('example_card', 'present', fx is not None, my_ex is not None, 'example card presence (needs the 2024-09-22 signal complete)')
    else:
        ck.add('example_card', 'only signals known by 2024-09-22', True, all(x[1]['d0'] + dt.timedelta(days=60) <= EX_DATE for x in xs))
        cmp_card('example_card', fx, my_ex)
    mine['example_card'] = my_ex if (fx is not None or not withheld) else None

    # ---------------------------------------------------------------- 6. open signals
    exp_open = sorted([s for (a, tf), c in S.ch.items() if tf in C.GRADED for s in c.sig if s['d0'] is not None and 0 <= (today - s['d0']).days <= 60],
                      key=lambda s: (str(s['d0']), s['chart']))
    fo = feed.get('open_signals') or []
    my_open = []
    if withheld: ck.add('open_signals', 'withheld (empty)', len(fo), 0)
    else:
        ck.add('open_signals', 'ids in order', json.dumps([o.get('signal_id') for o in fo]), json.dumps([f"{s['a']}-{s['tf']}-{s['d0']}" for s in exp_open]), 'open signals = gated signals on 1D-5D within 60 days of the entry date')
        for o in fo:
            s = sig.get((o.get('chart'), o.get('entry_date'))); loc = f"open {o.get('signal_id')}"
            if s is None: continue
            a = s['a']; b = S.day[a]; ec = s['entry_c']; e = s['entry']; d0 = s['d0']
            win = [k for k in S.window(a, d0) if b.date[k] < today]
            mark = lambda mday: next((rnd((b.c[k] / e - 1) * 100, 1) for k in win if (b.date[k] - d0).days == mday), None)
            if o.get('card') is None:
                ck.flag(loc, 'card', 'none', 'expected', 'live signal without a card'); continue
            oc = o['card']
            lenses = lens_set(o.get('confirmations'), False)
            basis, xs = sample_for(a, s['tf'], o['grade'], lenses, L)
            mc = dict(label=LABEL, signal_id=f"{a}-{s['tf']}-{d0}", chart=s['chart'], asset=a, timeframe=s['tf'], low_date=str(s['tdate']), low_day=low_day(a, s['tf'], s['tdate']),
                      confirms_on=str(d0), bars_to_confirm=None, must_close_above=None, price_now=rnd(b.c[-1], 2), entry_close=rnd(e, 2), sample=basis)
            mc.update(figures(xs)); mc['grade'] = o['grade']; mc['_kind'] = 'open'
            ck.add(loc, 'card.grade = signal grade', oc.get('grade'), o['grade']); ck.add(loc, 'card.confirmations = signal lenses', json.dumps(sorted(lens_set(oc.get('confirmations'), True))), json.dumps(sorted(lenses)))
            cmp_card(loc + ' card', oc, mc)
            lvl = mc['_edge']
            if lvl == 0: status = 'lost'
            else:
                status = 'intact'
                for k in win:
                    if lvl is not None and b.lc[k] * 100 <= ec * (100 + lvl): status = 'lost'; break
                    if b.hc[k] * 100 >= ec * 110: status = 'rose10'; break
            mo = dict(label=LABEL, signal_id=mc['signal_id'], chart=s['chart'], entry_date=str(d0), entry_close=rnd(e, 2), tags=s['tags'], days_elapsed=(today - d0).days,
                      day10_pct=mark(10), day30_pct=mark(30), day60_pct=mark(60),
                      best_so_far_pct=rnd((max(b.h[k] for k in win) / e - 1) * 100, 1) if win else None, worst_so_far_pct=rnd((min(b.l[k] for k in win) / e - 1) * 100, 1) if win else None,
                      edge_level_pct=lvl, edge_status=status)
            for k, v in mo.items(): ck.add(loc, k, o.get(k), v, 'open signal')
            lr = next((r for r in led if r['chart'] == s['chart'] and r['entry'] == str(d0)), None)
            mo.update(grade=o['grade'], confirmations=o.get('confirmations'), card=mc); my_open.append(mo)
    mine['open_signals'] = my_open

    # prints
    exp_pr = []
    for a in C.ASSETS:
        for tf in C.TFS:
            c = S.ch[(a, tf)]
            for s in [x for x in c.sig if x['d0'] is not None][-3:]:
                exp_pr.append(dict(signal_id=f"{a}-{tf}-{s['d0']}", chart=s['chart'], state='confirmed', provisional=False, low_date=str(s['tdate']), confirms_on=str(s['d0']),
                                   entry_close=rnd(s['entry'], 2), tags=s['tags'], note='regime on' if S.gate(s['tdate']) else 'regime off', label=LABEL))
            p = forming.get(f'{a} {tf}')
            if p: exp_pr.append(dict(signal_id=f"{a}-{tf}-{p['confirms']}", chart=p['chart'], state='forming', provisional=True, low_date=str(p['tdate']), confirms_on=str(p['confirms']),
                                     entry_close=rnd(p['price'], 2), tags=p['tags'], note=('regime on' if S.gate(p['tdate']) else 'regime off') + f"; {p['need']} bar(s) to confirm", label=LABEL))
    fp = feed.get('prints') or []
    if fp or not feed.get('feed_error'):
        ck.add('prints', 'ids in order', json.dumps([x.get('signal_id') + ':' + x.get('state', '') for x in fp]), json.dumps([x['signal_id'] + ':' + x['state'] for x in exp_pr]), 'last 3 confirmed per chart plus any forming low')
        for x, y in zip(fp, exp_pr):
            if x.get('signal_id') != y['signal_id']: continue
            for k, v in y.items(): ck.add(f"print {y['signal_id']} {y['state']}", k, x.get(k), v, 'print')
    mine['prints'] = exp_pr

    # top level
    if not feed.get('feed_error'):
        ck.add('top', 'schema_version', feed.get('schema_version'), 6); ck.add('top', 'posting_bar_pct', feed.get('posting_bar_pct'), 70)
        ck.add('top', 'trades_a_year', feed.get('trades_a_year'), tay, 'tier signals per year'); ck.add('top', 'signals_a_year', feed.get('signals_a_year'), tay, 'alias')
        ck.add('top', 'market_regime', feed.get('market_regime'), 'Bullish' if S.gate(today) else 'Bearish', 'gate today')
        ck.add('top', 'scored_as_of', feed.get('scored_as_of'), str(today)); ck.add('top', 'label', feed.get('label'), LABEL)
        ck.add('top', 'generated_at date', (feed.get('generated_at') or '')[:10], str(today))
        ck.add('top', 'last daily bar is today (both assets)', all(S.day[a].date[-1] == today for a in C.ASSETS), True, 'envelope')
        ck.add('top', 'no -0.0 in the feed', '-0.0' in json.dumps(feed), False)
    mine['market_on'] = bool(S.gate(today))

    # ---------------------------------------------------------------- 7. past paths
    def paths(xs, a):
        b = S.day[a]; ps = []
        for r, s in xs:
            p = [0.0]
            for k in range(1, 61):
                j = b.pos.get(s['d0'] + dt.timedelta(days=k))
                if j is None: break
                p.append((b.c[j] / s['entry'] - 1) * 100)
            if len(p) == 61: ps.append(p)
        if not ps: return None
        return dict(asset=a, grade='A+', signals=len(ps), label=LABEL,
                    days=[dict(day=d, q25_pct=rnd(C.quant([p[d] for p in ps], 0.25), 1), median_pct=rnd(C.quant([p[d] for p in ps], 0.5), 1), q75_pct=rnd(C.quant([p[d] for p in ps], 0.75), 1)) for d in range(61)])
    def cmp_paths(loc, fpp, mp):
        if fpp is None or mp is None: ck.add(loc, 'present', fpp is not None, mp is not None, 'paths presence'); return
        for k in ('asset', 'grade', 'signals', 'label'): ck.add(loc, k, fpp.get(k), mp[k], 'paths')
        ck.add(loc, 'days rows', len(fpp.get('days', [])), 61)
        for x, y in zip(fpp.get('days', []), mp['days']):
            for k in ('day', 'q25_pct', 'median_pct', 'q75_pct'): ck.add(loc, f"day {y['day']} {k}", x.get(k), y[k], 'path quantile')
    my_pp = []
    if not feed.get('extras_withheld'):
        for a in C.ASSETS:
            mp = paths(G.get((a, 'A+'), []), a)
            fpp = next((x for x in feed.get('past_paths') or [] if x.get('asset') == a), None)
            if mp is None and fpp is None: continue
            cmp_paths(f'past_paths {a}', fpp, mp)
            if mp: my_pp.append(mp)
        mxp = paths(exk, 'ETH') if exk else None
        cmp_paths('example_past_paths', feed.get('example_past_paths'), mxp)
        mine['example_past_paths'] = mxp
    mine['past_paths'] = my_pp
    mine['L'] = L; mine['S'] = S; mine['sig'] = sig
    return ck, mine


if __name__ == '__main__':
    root, state, now = sys.argv[1], sys.argv[2], sys.argv[3]
    now = dt.datetime.fromisoformat(now.replace('Z', '+00:00'))
    ck, mine = run(root, state, now)
    print(state, 'checks', ck.n, 'diffs', len(ck.bad))
    for r in ck.bad[:60]: print('  ', r[1:])
