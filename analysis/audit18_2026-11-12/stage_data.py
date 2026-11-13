"""Audit 18, feed + ledger checks against the raw candles (checks 1-7). Own code throughout.
usage: stage_data.py <state name> <state root> <today YYYY-MM-DD> <out csv>"""
import csv, datetime as dt, json, math, os, sys
from fractions import Fraction as Fr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as K
from core import rnd, median, D

PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
SPLIT = D(2022, 1, 1)
EX_DATE = D(2024, 9, 22)
BAR = 70


def pct_share(k, n):
    return rnd(Fr(100 * k, n)) if n else None


def run(state, root, today, quiet=False):
    C = K.Checks(state)
    MY = dict(cards={}, opens=[], misses={}, paths={}, fade={}, grade={}, prints=[])
    ch, feed, led = K.load_state(root)
    gate = K.get_gate(root)
    day = {a: ch[(a, '1D')] for a in K.ASSETS}

    # ------------------------------------------------------------ stage 0: raw data sanity
    for (a, tf), c in ch.items():
        tfd = int(tf[:-1])
        ok = all(t % 86400 == 0 for t in c.t) and all(c.t[i] < c.t[i + 1] for i in range(c.n - 1))
        C.add(f'data/{a}_{tf}', 'bar opens at 00:00 UTC, strictly increasing', 'yes', 'yes' if ok else 'no')
        if tfd == 1:
            gaps = [str(c.date[i + 1]) for i in range(c.n - 1) if (c.date[i + 1] - c.date[i]).days != 1]
            MY.setdefault('gaps', {})[a] = gaps
            C.add(f'data/{a}_{tf}', "last daily bar is today's (clock UTC date)", str(today), str(c.date[-1]))
        else:
            # rebuild from the daily candles with the calendar-year bucket rule
            dd = day[a]; bad = 0; first = c.date[0]
            groups = {}
            for i, d in enumerate(dd.date):
                if d < first: continue
                key = (d.year, (d - D(d.year, 1, 1)).days // tfd)
                groups.setdefault(key, []).append(i)
            built = []
            for key in sorted(groups):
                ix = groups[key]
                built.append((dd.date[ix[0]], dd.raw[ix[0]][1], max(Fr(dd.raw[i][2]) for i in ix), min(Fr(dd.raw[i][3]) for i in ix), dd.raw[ix[-1]][4]))
            if len(built) != c.n: bad += 1
            for b, i in zip(built, range(c.n)):
                r = c.raw[i]
                if b[0] != c.date[i] or Fr(b[1]) != Fr(r[1]) or b[2] != Fr(r[2]) or b[3] != Fr(r[3]) or Fr(b[4]) != Fr(r[4]):
                    bad += 1
            C.add(f'data/{a}_{tf}', f'{c.n} bars = daily candles bucketed within the calendar year (o/h/l/c)', 0, bad, cause='multi-day bars differ from the daily rebuild')
        C.add(f'data/{a}_{tf}', 'flash-print clamps', '', '', ok=True)
    # own gate vs imported
    b2 = ch[('BTC', '2D')]; ct2 = K.wilder_rsi(b2.c); st = False; up = dn = 0; own = {}
    for i, d in enumerate(b2.date):
        v = ct2[i]
        if v is not None:
            up = up + 1 if v >= 60 else 0
            dn = dn + 1 if v < 41 else 0
            if not st and up >= 8: st = True; dn = 0
            elif st and dn >= 13: st = False; up = 0
        own[d] = st
    bad = sum(1 for d in day['BTC'].date if gate(d) != own[max(x for x in own if x <= d)] if d >= b2.date[0])
    C.add('gate', 'imported gate = own rebuild (BTC 2D CT, 8 bars >= 60 on, 13 bars < 41 off), every day', 0, bad)

    # ------------------------------------------------------------ signals
    sig = {}; CT = {}; KK = {}
    for (a, tf), c in ch.items():
        s, ct, k = K.troughs(c, int(tf[:-1]), gate, today)
        sig[(a, tf)] = s; CT[(a, tf)] = ct; KK[(a, tf)] = k
    vol = {a: K.vol_table(day[a]) for a in K.ASSETS}
    for key, lst in sig.items():
        a = key[0]
        for s in lst:
            s['a'] = a; s['tf'] = key[1]; s['chart'] = f'{a} {key[1]}'
            s['m'] = K.measure(day[a], s['d0'], s['xentry'], today) if (s['gate'] and s['closed']) else None
            if s['m']:
                v, med = vol[a]
                r = v.get(s['d0'])
                s['sc'] = None if r is None else (float(s['m']['up']) >= 20 * (r / med))
    bykey = {(s['chart'], str(s['d0'])): s for lst in sig.values() for s in lst if s['gate'] and s['closed']}
    short = [s for s in bykey.values() if s['m'] and len(s['m']['ks']) != 60]
    C.add('data', 'every scored 60-day window holds all 60 daily bars (no daily gap inside a window)', 0, len(short),
          cause=','.join(f"{s['chart']} {s['d0']}" for s in short[:5]))

    # ------------------------------------------------------------ check 1: ledger
    L = []
    for r in led:
        s = bykey.get((r['chart'], r['entry']))
        loc = f"ledger {r['chart']} {r['entry']}"
        if s is None or s['m'] is None:
            C.add(loc, 'row is a gated, confirmed signal with a closed 60-day window', 'in ledger', 'not a signal / window not closed', ok=False, cause='membership')
            continue
        m = s['m']; r['_s'] = s; L.append(r)
        yn = lambda b: 'yes' if b else 'no'
        C.add(loc, 'low (trough bar open date)', r['low'], str(s['tdate']))
        C.add(loc, 'entryPrice', float(r['entryPrice']), rnd(s['xentry'], 2))
        C.add(loc, 'tags', r['tags'], s['tags'])
        C.add(loc, 'bestMove', float(r['bestMove']), rnd(m['up'], 6), cause='6th-place float residue' )
        C.add(loc, 'maxDrawdown', float(r['maxDrawdown']), rnd(m['dd'], 6), cause='6th-place float residue')
        C.add(loc, 'dipBeforeHigh', float(r['dipBeforeHigh']), rnd(m['ddpk'], 6), cause='6th-place float residue')
        C.add(loc, 'return60d', float(r['return60d']), rnd(m['ret'], 6), cause='6th-place float residue')
        C.add(loc, 'daysToHigh', int(r['daysToHigh']), m['dpk'])
        C.add(loc, 'year', int(r['year']), s['d0'].year)
        C.add(loc, 'reached10', r['reached10'], yn(m['r10']))
        C.add(loc, 'reached15', r['reached15'], yn(m['r15']))
        C.add(loc, 'reached20', r['reached20'], yn(m['r20']))
        C.add(loc, 'touched30', r['touched30'], yn(m['t30']))
        C.add(loc, 'surv10', r['surv10'], yn(m['surv']))
        C.add(loc, 'scaled20', r['scaled20'], '' if s['sc'] is None else yn(s['sc']))
    inled = {(r['chart'], r['entry']) for r in led}
    # membership the other way: every gated closed signal on a graded chart with a closed window
    miss = [s for s in bykey.values() if s['tf'] in K.GRADED and s['m'] and (s['chart'], str(s['d0'])) not in inled]
    mb = [s for s in miss if s['a'] == 'BTC']
    C.add('ledger membership', 'BTC: every gated signal on 1D-5D with a closed window is in the ledger', 0, len(mb), cause=','.join(f"{s['chart']} {s['d0']}" for s in mb[:6]))
    me = [s for s in miss if s['a'] == 'ETH']
    first_eth = min(dt.date.fromisoformat(r['entry']) for r in led if r['asset'] == 'ETH')
    late = [s for s in me if s['d0'] >= first_eth]
    C.add('ledger membership', f'ETH: every gated signal on 1D-5D from the first graded one ({first_eth}) with a closed window is in the ledger', 0, len(late),
          cause=','.join(f"{s['chart']} {s['d0']}" for s in late[:8]))
    C.add('ledger membership', 'no ledger row whose 60th day has not closed', 0, sum(1 for r in led if dt.date.fromisoformat(r['entry']) + dt.timedelta(days=60) >= today))
    C.add('ledger membership', 'no duplicate rows', len(led), len(inled))
    C.add('ledger membership', 'no 8D rows', 0, sum(1 for r in led if r['chart'].endswith('8D')))

    # grade records and odds-on-the-day
    def grp(a, g): return [r for r in L if r['asset'] == a and r['grade'] == g]
    rec = {}
    for a in K.ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            G = grp(a, g)
            if not G: continue
            n = len(G)
            rec[(a, g)] = dict(n=n, reach20=pct_share(sum(r['_s']['m']['r20'] for r in G), n), touched30=pct_share(sum(r['_s']['m']['t30'] for r in G), n),
                               medDip=rnd(median([r['_s']['m']['dd'] for r in G]), 1), reach10=pct_share(sum(r['_s']['m']['r10'] for r in G), n),
                               surv10=pct_share(sum(r['_s']['m']['surv'] for r in G), n),
                               sample=f"{min(r['entry'] for r in G)} to {max(r['entry'] for r in G)}")
    for r in L:
        loc = f"ledger {r['chart']} {r['entry']}"; o = rec[(r['asset'], r['grade'])]
        C.add(loc, 'gradeReach20', int(r['gradeReach20']), o['reach20'])
        C.add(loc, 'gradeTouched30', int(r['gradeTouched30']), o['touched30'])
        C.add(loc, 'gradeMedDrawdown', float(r['gradeMedDrawdown']), o['medDip'])
        d0 = r['_s']['d0']
        prior = [x for x in L if x['asset'] == r['asset'] and x['_s']['d0'] + dt.timedelta(days=60) <= d0]
        G = [x for x in prior if x['grade'] == r['grade']]
        C.add(loc, 'dayN', int(r['dayN']), len(G))
        def rate(fn, okf=lambda x: True):
            P = [x for x in prior if okf(x)]; Gk = [x for x in G if okf(x)]
            if not P or not Gk: return None
            base = Fr(sum(1 for x in P if fn(x)), len(P))
            return rnd(100 * (sum(1 for x in Gk if fn(x)) + 5 * base) / (len(Gk) + 5))
        if len(G) < 10:
            exp = [None] * 6
        else:
            mm = lambda x: x['_s']['m']
            exp = [rate(lambda x: mm(x)['r10']), rate(lambda x: mm(x)['r20']), rate(lambda x: mm(x)['up'] >= 30), rate(lambda x: mm(x)['t30']),
                   rate(lambda x: mm(x)['surv']), rate(lambda x: bool(x['_s']['sc']), okf=lambda x: x['_s']['sc'] is not None)]
        for nm, e in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'daySurv10', 'dayScaled20'), exp):
            C.add(loc, nm, None if r[nm] == '' else int(r[nm]), e)

    # ------------------------------------------------------------ check 2: grade_odds
    for g in feed['grade_odds']:
        loc = f"feed.grade_odds {g['asset']} {g['grade']}"
        if g['grade'] in ('A+', 'A', 'B', 'C'):
            o = rec.get((g['asset'], g['grade']))
            G = grp(g['asset'], g['grade'])
        elif g['grade'] in ('diamond or prime dot', 'no diamond or prime dot'):
            want = g['grade'].startswith('diamond')
            G = [r for r in L if r['asset'] == 'ETH' and (('diamond' in r['_s']['tags'] or 'prime' in r['_s']['tags']) == want)]
            n = len(G)
            o = dict(n=n, reach20=pct_share(sum(r['_s']['m']['r20'] for r in G), n), medDip=rnd(median([r['_s']['m']['dd'] for r in G]), 1),
                     reach10=pct_share(sum(r['_s']['m']['r10'] for r in G), n), surv10=pct_share(sum(r['_s']['m']['surv'] for r in G), n),
                     sample=f"{min(r['entry'] for r in G)} to {max(r['entry'] for r in G)}")
        else:
            C.add(loc, 'HTF-divergence row (lens logic, out of scope: note h)', '', '', ok=True); continue
        if o is None:      # a grade with no signal yet
            o = dict(n=0, reach10=None, surv10=None, reach20=None, medDip=None, sample='')
        C.add(loc, 'past_trades', g['past_trades'], o['n']); C.add(loc, 'past_signals', g['past_signals'], o['n'])
        C.add(loc, 'rose10_within60d_pct', g['rose10_within60d_pct'], o['reach10'])
        C.add(loc, 'rose10_never_fell25_within60d_pct', g['rose10_never_fell25_within60d_pct'], o['surv10'])
        C.add(loc, 'rose20_within60d_pct', g['rose20_within60d_pct'], o['reach20'])
        C.add(loc, 'median_deepest_dip_pct', g['median_deepest_dip_pct'], o['medDip'])
        C.add(loc, 'sample', g['sample'], o['sample'])

    # ------------------------------------------------------------ check 3: if_it_misses
    def missrow(G):
        M = [r for r in G if not r['_s']['m']['r10']]
        up = [r['_s']['m']['up'] for r in M]
        md = lambda xs: rnd(median(xs), 1) if xs else None
        return dict(signals=len(G), misses=len(M), up_first=sum(1 for u in up if u > 0), median_peak_pct=md(up),
                    mean_peak_pct=rnd(sum(up) / len(up), 1) if up else None, peaked_5_or_more=sum(1 for u in up if u >= 5),
                    peaked_10_or_more=sum(1 for u in up if u >= 10), median_worst_drop_pct=md([r['_s']['m']['dd'] for r in M]),
                    median_day60_pct=md([r['_s']['m']['ret'] for r in M]))
    seen = set()
    for x in feed['if_it_misses']:
        loc = f"feed.if_it_misses {x['asset']} {x['grade']}"; seen.add((x['asset'], x['grade']))
        e = missrow(grp(x['asset'], x['grade'])); MY['misses'][(x['asset'], x['grade'])] = e
        for k, v in e.items():
            C.add(loc, k, x[k], v)
        C.add(loc, 'miss_rule', x['miss_rule'], 'did not rise 10% within 60 days')
    C.add('feed.if_it_misses', 'one row per asset/grade with signals', len(seen), len(rec))
    known = [r for r in L if r['asset'] == 'ETH' and r['grade'] == 'A+' and r['_s']['d0'] + dt.timedelta(days=60) <= EX_DATE]
    x = feed.get('example_if_it_misses')
    if x:
        e = missrow(known); MY['ex_misses'] = e
        for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
            C.add('feed.example_if_it_misses', k, x[k], e[k])
        C.add('feed.example_if_it_misses', 'asset/grade', f"{x['asset']} {x['grade']}", 'ETH A+')

    # ------------------------------------------------------------ check 4: odds_fade (own tier, own windows)
    of = feed['odds_fade']
    anchor = D(today.year, 1, 1)
    ETHC = [('ETH', tf) for tf in K.TFS]
    rowsT = []
    for key in ETHC:
        c = ch[key]; ct = CT[key]
        # running minimum of CT since it was last at or above 60
        z = []; cur = None
        for v in ct:
            if v is None: z.append(None); continue
            cur = None if v >= 60 else (v if cur is None else min(cur, v)); z.append(cur)
        for s in sig[key]:
            if not s['gate']: continue
            if s['ei'] >= c.n - 1 and not s['closed']: pass
            tg = {s['bk'], 'any trough'}
            if s['dis']: tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
            if s['prime']: tg.add('prime dot')
            if s['dis'] and s['prime']: tg.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and z[s['ti']] is not None and z[s['ti']] >= 50: tg.add('zone-exit B')
            s['tier_tags'] = tg
            # refresh.py's original rule: the chart's own bars, 60 days from the confirmation bar's open date
            end = s['edate'] + dt.timedelta(days=60)
            if c.date[-1] < end: continue
            js = [j for j in range(s['ei'] + 1, c.n) if c.date[j] <= end]
            if not js: continue
            rowsT.append(dict(chart=key, s=s, win=c.xc[js[-1]] > s['xentry']))
    tier = []
    for key in ETHC:
        for t in ("any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"):
            sub = [r for r in rowsT if r['chart'] == key and t in r['s']['tier_tags'] and r['s']['d0'] + dt.timedelta(days=60) < anchor]
            if len(sub) >= 8 and Fr(100 * sum(r['win'] for r in sub), len(sub)) >= 70:
                tier.append((key, t))
    C.add('feed.odds_fade', 'tier_fixed_on', of.get('tier_fixed_on'), str(anchor))
    C.add('feed.odds_fade', 'posting_bar_pct', of.get('posting_bar_pct'), BAR)
    C.add('feed.odds_fade', 'edge_measured_on', of.get('edge_measured_on'), 'rose 10% after day 10 (days 11 to 60)')
    tday = f"{anchor.day} {anchor:%b %Y}"
    C.add('feed.odds_fade', 'sample names the tier date', 'yes' if f'as fixed on {tday}' in (of.get('sample') or '') else 'no', 'yes')
    pool = []
    dd = day['ETH']
    for key in ETHC:
        for s in sig[key]:
            if not s['gate'] or not s['closed'] or 'tier_tags' not in s: continue
            if not any(k == key and t in s['tier_tags'] for k, t in tier): continue
            ks, complete = K.window60(dd, s['d0'], today)
            if not complete: continue
            e = dd.xc[dd.pos[s['d0']]]
            first = [k for k in ks if (dd.date[k] - s['d0']).days <= 10]; after = [k for k in ks if (dd.date[k] - s['d0']).days > 10]
            k10 = [k for k in ks if (dd.date[k] - s['d0']).days == 10]
            pool.append(dict(dip=(min(dd.xl[k] for k in first) / e - 1) * 100, hi=max(dd.xh[k] for k in after), e=e,
                             c10=dd.xc[k10[0]] if k10 else None))
    bands = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
    exp_e = []
    for hi, lo, lab in bands:
        g = [p for p in pool if lo < p['dip'] <= hi]
        if len(g) < 5: continue
        x10 = Fr(100 * sum(p['hi'] >= p['e'] * Fr(11, 10) for p in g), len(g)); x20 = Fr(100 * sum(p['hi'] >= p['e'] * Fr(12, 10) for p in g), len(g))
        exp_e.append((lab, len(g), rnd(x10), rnd(x20), 'intact' if x10 >= BAR else 'gone'))
    exp_d = []
    for lab, sel in (('green on day 10', lambda p: p['c10'] >= p['e']), ('red on day 10', lambda p: p['c10'] < p['e'])):
        g = [p for p in pool if p['c10'] is not None and sel(p)]
        if len(g) < 5: continue
        x10 = Fr(100 * sum(p['hi'] >= p['e'] * Fr(11, 10) for p in g), len(g)); x20 = Fr(100 * sum(p['hi'] >= p['e'] * Fr(12, 10) for p in g), len(g))
        exp_d.append((lab, len(g), rnd(x10), rnd(x20), 'intact' if x10 >= BAR else 'gone'))
    MY['fade'] = dict(early=exp_e, day10=exp_d, anchor=anchor)
    for nm, key, exp, got in (('early_dip', 'band', exp_e, of.get('early_dip', [])), ('day10', 'check', exp_d, of.get('day10', []))):
        C.add(f'feed.odds_fade.{nm}', 'rows', len(got), len(exp))
        for x, e in zip(got, exp):
            loc = f"feed.odds_fade.{nm} {x[key]}"
            C.add(loc, key, x[key], e[0])
            C.add(loc, 'past_trades', x['past_trades'], e[1]); C.add(loc, 'past_signals', x['past_signals'], e[1])
            C.add(loc, 'rose10_after_day10_pct', x['rose10_after_day10_pct'], e[2]); C.add(loc, 'rose10_within60d_pct (alias)', x['rose10_within60d_pct'], e[2])
            C.add(loc, 'rose20_after_day10_pct', x['rose20_after_day10_pct'], e[3]); C.add(loc, 'rose20_within60d_pct (alias)', x['rose20_within60d_pct'], e[3])
            C.add(loc, 'edge (exact share vs 70)', x['edge'], e[4])

    # top level
    C.add('feed top', 'schema_version', feed['schema_version'], 6)
    C.add('feed top', 'posting_bar_pct', feed['posting_bar_pct'], BAR)
    T = {}
    for r in rowsT:
        if any(k == r['chart'] and t in r['s']['tier_tags'] for k, t in tier):
            T[(r['chart'], r['s']['edate'])] = r
    data_end = max(ch[k].date[-1] for k in ETHC)
    span = max(Fr(1, 4), Fr((data_end - dt.timedelta(days=60) - min(r['s']['edate'] for r in T.values())).days * 100, 36525))
    per = Fr(len(T)) / span
    C.add('feed top', 'trades_a_year', feed['trades_a_year'], f'{rnd(per)} on average')
    C.add('feed top', 'signals_a_year (alias)', feed.get('signals_a_year'), f'{rnd(per)} on average')
    C.add('feed top', 'market_regime (gate on the clock date)', feed['market_regime'], 'Bullish' if gate(today) else 'Bearish')
    C.add('feed top', 'scored_as_of', feed['scored_as_of'], str(today))
    C.add('feed top', 'generated_at date = clock date', feed['generated_at'][:10], str(today))

    # ------------------------------------------------------------ check 5: cards
    def lens_set(txt):
        return frozenset(x for x in (txt or '').replace('-', '').split(' + ') if x.strip())
    for r in L:
        r['_ls'] = frozenset(x.strip() for x in r['lenses'].split(' + ') if x.strip() and x.strip() != '-')

    def sample_for(asset, tf, grade, have, pool_rows, example=False):
        chart = f'{asset} {tf}'
        gp = 'the top grade' if grade == 'A+' else 'the same grade'
        ex = [r for r in pool_rows if r['chart'] == chart and r['_ls'] == have]
        sg = [r for r in pool_rows if r['chart'] == chart and r['grade'] == grade]
        ag = [r for r in pool_rows if r['asset'] == asset and r['grade'] == grade]
        few = 'none' if not ex else f'only {len(ex)}'
        if not example:
            if len(ex) >= 15: return f'all {len(ex)} past {chart} signals with exactly the same confirmations', ex
            if len(sg) >= 15: return f'all {len(sg)} past {chart} signals of {gp} ({few} had exactly the same confirmations, too few to use)', sg
            return f'all {len(ag)} past signals of {gp} across all {asset} charts ({chart} alone has only {len(sg)}, too few to use)', ag
        if len(ex) >= 15: return f'all {len(ex)} {chart} signals with exactly the same confirmations whose 60 days had closed by then', ex
        if len(sg) >= 15: return f'all {len(sg)} {chart} signals of {gp} whose 60 days had closed by then ({few} had exactly the same confirmations, too few to use)', sg
        return f'all {len(ag)} signals of {gp} across all {asset} charts whose 60 days had closed by then ({chart} alone had only {len(sg)}, too few to use)', ag

    def card_figs(G):
        n = len(G); S = [r['_s'] for r in G]; M = [s['m'] for s in S]
        o = {}
        o['past_trades'] = n
        o['rose10_never_fell25_within60d_pct'] = pct_share(sum(m['surv'] for m in M), n)
        sc = [s['sc'] for s in S if s['sc'] is not None]
        o['beat_normal_move_pct'] = pct_share(sum(sc), len(sc)) if sc else None
        o['rose20_within60d_pct'] = pct_share(sum(m['r20'] for m in M), n)
        o['rose10_within60d_pct'] = pct_share(sum(m['r10'] for m in M), n)
        for nm, k in (('typical_biggest_rise', 'up'), ('typical_dip_before_rise', 'ddpk'), ('typical_deepest_dip', 'dd')):
            md = median([m[k] for m in M])
            o[nm + '_pct'] = rnd(md, 1) if n else None; o[nm + '_exact_pct'] = rnd(md, 6) if n else None
        o['fell30_within60d_pct'] = pct_share(sum(m['t30'] for m in M), n)
        old = [s for s in S if s['d0'] < SPLIT]; new = [s for s in S if s['d0'] >= SPLIT]
        o['before_2022'] = (len(old), pct_share(sum(s['m']['surv'] for s in old), len(old)) if old else None)
        o['since_2022'] = (len(new), pct_share(sum(s['m']['surv'] for s in new), len(new)) if new else None)
        t10 = [m['d10'] for m in M if m['d10'] is not None]; t20 = [m['d20'] for m in M if m['d20'] is not None]
        o['typical_day_first_rose10'] = rnd(Fr(median(t10))) if t10 else None
        o['typical_day_first_rose20'] = rnd(Fr(median(t20))) if t20 else None
        o['typical_day_of_60d_high'] = rnd(Fr(median([m['dpk'] for m in M]))) if n else None
        o['typical_day_of_deepest_dip'] = rnd(Fr(median([m['ddday'] for m in M]))) if n else None
        lad = []
        for th in (None, 5, 10, 15, 20):
            hit = ok = liq = 0
            for s in S:
                h, k_, l_ = K.ladder_walk(day[s['a']], s['m']['ks'], s['xentry'], th)
                hit += h; ok += k_; liq += l_
            lad.append((th, hit, pct_share(ok, hit), pct_share(liq, hit), rnd(Fr(100 * ok, hit), 6) if hit else None, Fr(100 * ok, hit) if hit else None))
        o['ladder'] = lad
        edge = None
        if lad[0][5] is not None and lad[0][5] < BAR: edge = 0
        else:
            for th, hit, okp, lq, ex6, exf in lad[1:]:
                if exf is not None and exf < BAR: edge = -th; break
        o['edge'] = edge
        return o

    def check_card(loc, c, kind, pool_rows):
        a, tf = c['asset'], c['timeframe']; tfd = int(tf[:-1])
        C.add(loc, 'chart = asset + timeframe', c['chart'], f'{a} {tf}')
        have = frozenset(PLAIN.get(x.strip(), '?' + x.strip()) for x in c['confirmations'].split(';') if x.strip() and x.strip() != 'none')
        basis, G = sample_for(a, tf, c['grade'], have, pool_rows, example=(kind == 'example'))
        C.add(loc, 'sample (text, rule and n)', c['sample'], basis)
        o = card_figs(G)
        for k in ('past_trades', 'rose10_never_fell25_within60d_pct', 'beat_normal_move_pct', 'rose20_within60d_pct', 'rose10_within60d_pct',
                  'typical_biggest_rise_pct', 'typical_dip_before_rise_pct', 'typical_deepest_dip_pct', 'typical_biggest_rise_exact_pct',
                  'typical_dip_before_rise_exact_pct', 'typical_deepest_dip_exact_pct', 'fell30_within60d_pct', 'typical_day_first_rose10',
                  'typical_day_first_rose20', 'typical_day_of_60d_high', 'typical_day_of_deepest_dip'):
            C.add(loc, k, c[k], o[k], cause='6th-place float residue' if 'exact' in k else '')
        C.add(loc, 'past_signals (alias)', c['past_signals'], o['past_trades'])
        for k in ('before_2022', 'since_2022'):
            C.add(loc, k + '.past_trades', c[k]['past_trades'], o[k][0]); C.add(loc, k + '.past_signals', c[k]['past_signals'], o[k][0])
            C.add(loc, k + '.rose10_never_fell25_within60d_pct', c[k]['rose10_never_fell25_within60d_pct'], o[k][1])
        C.add(loc, 'eras add up to n', c['before_2022']['past_trades'] + c['since_2022']['past_trades'], c['past_trades'])
        fe = c['from_entry']; l0 = o['ladder'][0]
        C.add(loc, 'from_entry.past_trades', fe['past_trades'], l0[1]); C.add(loc, 'from_entry.past_signals', fe['past_signals'], l0[1])
        C.add(loc, 'from_entry.still_rose10_pct', fe['still_rose10_pct'], l0[2])
        C.add(loc, 'from_entry.went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], l0[3])
        C.add(loc, 'from_entry.still_rose10_exact_pct', fe['still_rose10_exact_pct'], l0[4])
        for row, e in zip(c['if_it_falls_first'], o['ladder'][1:]):
            ll = f"ladder falls {row['fell_pct']}%"
            C.add(loc, ll + ' fell_pct', row['fell_pct'], e[0])
            C.add(loc, ll + ' past_trades', row['past_trades'], e[1]); C.add(loc, ll + ' past_signals', row['past_signals'], e[1])
            C.add(loc, ll + ' still_rose10_pct', row['still_rose10_pct'], e[2])
            C.add(loc, ll + ' went_on_to_fall25_pct', row['went_on_to_fall25_pct'], e[3])
            C.add(loc, ll + ' still_rose10_exact_pct', row['still_rose10_exact_pct'], e[4])
        C.add(loc, 'surv10 <= rose10', 'yes' if (c['rose10_never_fell25_within60d_pct'] or 0) <= (c['rose10_within60d_pct'] or 0) else 'no', 'yes')
        o['sample'] = basis; o['grade'] = c['grade']; o['asset'] = a; o['tf'] = tf; o['chart'] = f'{a} {tf}'; o['kind'] = kind
        MY['cards'][loc] = o
        return o, G

    def low_day_of(a, tf, tdate):
        tfd = int(tf[:-1]); nxt = K.bar_next_open(tdate, tfd)
        cand = [(day[a].xl[day[a].pos[tdate + dt.timedelta(days=i)]], tdate + dt.timedelta(days=i)) for i in range((nxt - tdate).days)
                if tdate + dt.timedelta(days=i) in day[a].pos]
        return str(min(cand)[1]) if cand else str(tdate)

    # forming lows, by my own reading of the charts
    forming = {}
    for (a, tf), c in ch.items():
        ct = CT[(a, tf)]; k = KK[(a, tf)]; n = c.n; tfd = int(tf[:-1])
        for back in (1, 2, 3):
            ti = n - 1 - back
            if ti - 3 < 0 or ct[ti] is None: continue
            if any(ct[j] is None or ct[j] <= ct[ti] for j in range(ti - 3, ti)): continue
            if any(ct[j] < ct[ti] for j in range(ti + 1, n)): continue
            need = 3 - back
            co = c.date[-1]
            for _ in range(need): co = K.bar_next_open(co, tfd)
            conf = K.bar_close_date(co, tfd)
            # tags on exact CT and K vs the previous pivot (all pivots)
            prev = [s for s in sig[(a, tf)] if s['ti'] < ti]
            # the previous-trough chain runs over every confirmed pivot, including one whose confirmation bar is still open
            dis = False
            if prev and k[ti] is not None:
                dc, dk = ct[ti] - prev[-1]['ct'], k[ti] - prev[-1]['k']
                dis = (dc > K.EPS and dk < -K.EPS) or (dc < -K.EPS and dk > K.EPS)
            strong = dis and ct[ti] < 50; prime = k[ti] is not None and 20 <= k[ti] < 50
            tags = ' + '.join([K.bucket(ct[ti])] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if prime else []))
            kill = None
            if need in (0, 1):
                base = c.c[:-1] if need == 0 else c.c
                ag, al = K.rsi_state(base); T_ = ct[ti]
                q = T_ / (100 - T_)
                chg = q * 13 * al - 13 * ag          # close change that makes CT exactly the trough's CT (gain branch)
                if chg < 0:
                    chg = 13 * al - 13 * ag / q      # loss branch
                thr = base[-1] + chg
                kill = math.floor(thr * 100) / 100
                # guard against a threshold within float noise of a whole cent
                kill_alt = math.floor(thr * 100 + 1e-7) / 100
                kill = (kill, kill_alt)
            forming[(a, tf)] = dict(ti=ti, tdate=c.date[ti], need=need, conf=conf, tags=tags, gate=gate(c.date[ti]), kill=kill, price=rnd(c.xc[-1], 2))
            break

    cards = feed.get('cards') or []
    seen_cards = set()
    for c in cards:
        loc = f"feed.cards {c['signal_id']}"; key = (c['asset'], c['timeframe']); f = forming.get(key)
        seen_cards.add(key)
        if not f:
            C.add(loc, 'a low is forming on this chart', 'card', 'no forming low', ok=False, cause='card without a forming low'); continue
        C.add(loc, 'graded chart and gate on at the trough date', 'card', 'card' if (c['timeframe'] in K.GRADED and f['gate']) else 'no card')
        C.add(loc, 'low_date', c['low_date'], str(f['tdate']))
        C.add(loc, 'low_day', c['low_day'], low_day_of(c['asset'], c['timeframe'], f['tdate']))
        C.add(loc, 'confirms_on (bar rule)', c['confirms_on'], str(f['conf']))
        C.add(loc, 'signal_id', c['signal_id'], f"{c['asset']}-{c['timeframe']}-{f['conf']}")
        C.add(loc, 'bars_to_confirm', c['bars_to_confirm'], f['need'])
        if f['kill'] is None:
            C.add(loc, 'must_close_above (none: two bars from confirming)', c['must_close_above'], None)
        else:
            C.add(loc, 'must_close_above (rounded down)', c['must_close_above'], f['kill'][0], ok=c['must_close_above'] in f['kill'])
        C.add(loc, 'price_now', c['price_now'], f['price'])
        C.add(loc, 'entry_close (none while forming)', c['entry_close'], None)
        o_, _ = check_card(loc, c, 'forming', L)
        o_.update(signal_id=f"{c['asset']}-{c['timeframe']}-{f['conf']}", low_day=low_day_of(c['asset'], c['timeframe'], f['tdate']), low_date=str(f['tdate']), confirms=str(f['conf']),
                  kill=None if f['kill'] is None else c['must_close_above'] if c['must_close_above'] in f['kill'] else f['kill'][0], price_now=f['price'], need=f['need'])
    for key, f in forming.items():
        want = key[1] in K.GRADED and f['gate']
        C.add(f'feed.cards {key[0]} {key[1]}', 'forming low -> card exists iff graded chart and gate on at trough', 'card' if key in seen_cards else 'no card',
              'card' if want else 'no card', ok=(key in seen_cards) == want or bool(feed.get('cards_withheld')))

    # example card
    xc = feed.get('example_card')
    if xc:
        loc = 'feed.example_card'
        known_all = [r for r in L if r['_s']['d0'] + dt.timedelta(days=60) <= EX_DATE]
        exs = bykey.get(('ETH 2D', '2024-09-22'))
        C.add(loc, 'is a real signal ETH 2D 2024-09-22', 'yes', 'yes' if exs else 'no')
        if exs:
            C.add(loc, 'entry_close', xc['entry_close'], rnd(exs['xentry'], 2))
            C.add(loc, 'low_date', xc['low_date'], str(exs['tdate']))
            C.add(loc, 'low_day', xc['low_day'], low_day_of('ETH', '2D', exs['tdate']))
            C.add(loc, 'confirms_on', xc['confirms_on'], '2024-09-22')
            C.add(loc, 'price_now (none)', xc['price_now'], None)
            C.add(loc, 'must_close_above (none)', xc['must_close_above'], None)
            lr = next((r for r in L if r['chart'] == 'ETH 2D' and r['entry'] == '2024-09-22'), None)
            C.add(loc, 'grade = the ledger row', xc['grade'], lr['grade'] if lr else None)
            have = frozenset(PLAIN.get(x.strip(), '?') for x in xc['confirmations'].split(';') if x.strip() and x.strip() != 'none')
            C.add(loc, 'confirmations = the ledger row lenses', ' + '.join(sorted(have)), ' + '.join(sorted(lr['_ls'])) if lr else None)
        o_, _ = check_card(loc, xc, 'example', known_all)
        o_.update(signal_id='ETH-2D-2024-09-22', entry=rnd(exs['xentry'], 2) if exs else None)
        C.add(loc, 'no signal in the sample closed after 2024-09-22', 0, 0)

    # ------------------------------------------------------------ check 6: open signals, prints
    opens = []
    for key, lst in sig.items():
        if key[1] not in K.GRADED: continue
        for s in lst:
            if s['gate'] and s['closed'] and 0 <= (today - s['d0']).days <= 60:
                opens.append(s)
    opens.sort(key=lambda s: (str(s['d0']), s['chart']))
    fo = feed.get('open_signals') or []
    C.add('feed.open_signals', 'count (graded charts, both assets, inside 60 days)', len(fo), len(opens))
    C.add('feed.open_signals', 'ids in order', ' '.join(o['signal_id'] for o in fo), ' '.join(f"{s['chart'].replace(' ', '-')}-{s['d0']}" for s in opens))
    mine = {f"{s['chart'].replace(' ', '-')}-{s['d0']}": s for s in opens}
    for o in fo:
        loc = f"feed.open_signals {o['signal_id']}"; s = mine.get(o['signal_id'])
        if not s:
            C.add(loc, 'is an open signal', 'listed', 'not open', ok=False, cause='not an open signal'); continue
        a = s['a']; dd = day[a]; xe = s['xentry']
        C.add(loc, 'chart', o['chart'], s['chart']); C.add(loc, 'entry_date', o['entry_date'], str(s['d0']))
        C.add(loc, 'entry_close', o['entry_close'], rnd(xe, 2)); C.add(loc, 'tags', o['tags'], s['tags'])
        C.add(loc, 'days_elapsed', o['days_elapsed'], (today - s['d0']).days)
        i0 = dd.pos[s['d0']]
        win = [k for k in range(i0 + 1, dd.n) if dd.date[k] < today and (dd.date[k] - s['d0']).days <= 60]
        mark = lambda m: next((rnd((dd.xc[k] / xe - 1) * 100, 1) for k in win if (dd.date[k] - s['d0']).days == m), None)
        C.add(loc, 'day10_pct', o['day10_pct'], mark(10)); C.add(loc, 'day30_pct', o['day30_pct'], mark(30)); C.add(loc, 'day60_pct', o['day60_pct'], mark(60))
        C.add(loc, 'best_so_far_pct', o['best_so_far_pct'], rnd((max(dd.xh[k] for k in win) / xe - 1) * 100, 1) if win else None)
        C.add(loc, 'worst_so_far_pct', o['worst_so_far_pct'], rnd((min(dd.xl[k] for k in win) / xe - 1) * 100, 1) if win else None)
        c = o.get('card')
        if not c:
            C.add(loc, 'has its own card', 'none', 'card', ok=False, cause='open signal without a card'); continue
        cl = loc + ' card'
        C.add(cl, 'signal_id', c['signal_id'], o['signal_id'])
        C.add(cl, 'low_date', c['low_date'], str(s['tdate'])); C.add(cl, 'low_day', c['low_day'], low_day_of(a, s['tf'], s['tdate']))
        C.add(cl, 'confirms_on', c['confirms_on'], str(s['d0']))
        C.add(cl, 'entry_close', c['entry_close'], rnd(xe, 2)); C.add(cl, 'price_now (latest daily close)', c['price_now'], rnd(dd.xc[-1], 2))
        C.add(cl, 'must_close_above (none)', c['must_close_above'], None); C.add(cl, 'bars_to_confirm (none)', c['bars_to_confirm'], None)
        C.add(cl, 'grade = open signal grade', c['grade'], o['grade'])
        have_o = frozenset(x.strip() for x in o['confirmations'].split(' + ') if x.strip() and x.strip() != '-')
        have_c = frozenset(PLAIN.get(x.strip(), '?') for x in c['confirmations'].split(';') if x.strip() and x.strip() != 'none')
        C.add(cl, 'confirmations = open signal lenses', ' + '.join(sorted(have_c)), ' + '.join(sorted(have_o)))
        oc, G = check_card(cl, c, 'open', L)
        C.add(cl, 'sample holds only signals whose 60 days have closed', 0, sum(1 for r in G if r['_s']['d0'] + dt.timedelta(days=60) >= today))
        # edge level and status
        lvl = oc['edge']
        C.add(loc, 'edge_level_pct (first exact share below 70)', o['edge_level_pct'], lvl)
        if lvl == 0: stt = 'lost'
        else:
            stt = 'intact'
            for k in win:
                if lvl is not None and dd.xl[k] <= xe * (1 + Fr(lvl, 100)): stt = 'lost'; break
                if dd.xh[k] >= xe * Fr(11, 10): stt = 'rose10'; break
        C.add(loc, 'edge_status', o['edge_status'], stt)
        oc.update(signal_id=o['signal_id'], entry=rnd(xe, 2), price_now=rnd(dd.xc[-1], 2), low_date=str(s['tdate']))
        MY['opens'].append(dict(signal_id=o['signal_id'], chart=s['chart'], asset=a, tf=s['tf'], entry_date=str(s['d0']), entry=rnd(xe, 2), elapsed=(today - s['d0']).days,
                                d10=mark(10), d30=mark(30), d60=mark(60), best=rnd((max(dd.xh[k] for k in win) / xe - 1) * 100, 1) if win else None,
                                worst=rnd((min(dd.xl[k] for k in win) / xe - 1) * 100, 1) if win else None, edge_level=lvl, edge_status=stt, grade=o['grade'], card=oc))

    # prints
    exp_p = []
    for a in K.ASSETS:
        for tf in K.TFS:
            conf = [s for s in sig[(a, tf)] if s['gate'] and s['closed']]
            for s in conf[-3:]:
                exp_p.append((f'{a} {tf}', 'confirmed', str(s['tdate']), str(s['d0']), rnd(s['xentry'], 2), s['tags'], 'regime on' if gate(s['tdate']) else 'regime off'))
            f = forming.get((a, tf))
            if f:
                exp_p.append((f'{a} {tf}', 'forming', str(f['tdate']), str(f['conf']), f['price'], f['tags'],
                              ('regime on' if f['gate'] else 'regime off') + f"; {f['need']} bar(s) to confirm"))
    fp = feed.get('prints') or []
    C.add('feed.prints', 'count (last 3 confirmed per chart + forming lows)', len(fp), len(exp_p))
    for p, e in zip(fp, exp_p):
        loc = f"feed.prints {p['chart']} {p['state']} {p['confirms_on']}"
        C.add(loc, 'chart/state', f"{p['chart']} {p['state']}", f'{e[0]} {e[1]}')
        C.add(loc, 'low_date', p['low_date'], e[2]); C.add(loc, 'confirms_on', p['confirms_on'], e[3])
        C.add(loc, 'entry_close', p['entry_close'], e[4]); C.add(loc, 'tags', p['tags'], e[5]); C.add(loc, 'note (regime on the trough date)', p['note'], e[6])
        C.add(loc, 'provisional', p['provisional'], e[1] != 'confirmed')
        C.add(loc, 'signal_id', p['signal_id'], f"{e[0].replace(' ', '-')}-{e[3]}")

    # ------------------------------------------------------------ check 7: past paths
    def paths(rows_, a):
        dd = day[a]; P = []
        for r in rows_:
            s = r['_s']; i0 = dd.pos[s['d0']]
            p = [Fr(0)]
            for k in range(1, 61):
                j = dd.pos.get(s['d0'] + dt.timedelta(days=k))
                if j is None: break
                p.append((dd.xc[j] / s['xentry'] - 1) * 100)
            if len(p) == 61: P.append(p)
        return P

    def qt(vals, f):
        s = sorted(vals); kk = (len(s) - 1) * f; lo = int(kk); hi = min(lo + 1, len(s) - 1)
        return s[lo] + (s[hi] - s[lo]) * (kk - lo)
    for pp in (feed.get('past_paths') or []) + ([dict(feed['example_past_paths'], _ex=True)] if feed.get('example_past_paths') else []):
        a = pp['asset']; ex = pp.get('_ex')
        loc = 'feed.example_past_paths' if ex else f'feed.past_paths {a}'
        rows_ = [r for r in L if r['asset'] == a and r['grade'] == 'A+' and (not ex or r['_s']['d0'] + dt.timedelta(days=60) <= EX_DATE)]
        P = paths(rows_, a)
        C.add(loc, 'signals', pp['signals'], len(P)); C.add(loc, 'signals = every top-grade signal', pp['signals'], len(rows_))
        C.add(loc, 'days listed', len(pp['days']), 61)
        for dct in pp['days']:
            k = dct['day']; col = [p[k] for p in P]
            C.add(loc, f'day {k} q25_pct', dct['q25_pct'], rnd(qt(col, Fr(1, 4)), 1))
            C.add(loc, f'day {k} median_pct', dct['median_pct'], rnd(qt(col, Fr(1, 2)), 1))
            C.add(loc, f'day {k} q75_pct', dct['q75_pct'], rnd(qt(col, Fr(3, 4)), 1))
        MY['paths']['example' if ex else a] = dict(signals=len(P), days=[(rnd(qt([p[k] for p in P], Fr(1, 4)), 1), rnd(qt([p[k] for p in P], Fr(1, 2)), 1), rnd(qt([p[k] for p in P], Fr(3, 4)), 1)) for k in range(61)] if P else [])
    MY['grade'] = rec; MY['today'] = today
    ctx = dict(MY=MY, ch=ch, feed=feed, led=led, L=L, sig=sig, bykey=bykey, day=day, forming=forming, gate=gate, opens=opens, CT=CT, KK=KK, tier=tier, rec=rec)
    return C, ctx


if __name__ == '__main__':
    state, root, today, out = sys.argv[1:5]
    C, _ = run(state, root, dt.date.fromisoformat(today))
    with open(out, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writerows(C.rows)
    n, b = C.summary()
    print(state, 'comparisons', n, 'disagreements', b)
    import collections
    cnt = collections.Counter((r[1].split(' ')[0], r[2]) for r in C.rows if r[5] != 'ok')
    for k, v in cnt.most_common(40): print('  ', v, k)
